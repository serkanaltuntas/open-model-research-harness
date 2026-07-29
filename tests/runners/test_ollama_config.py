from typing import Any

import pytest

from harness.runners import ollama
from harness.runners.ollama import OllamaRunner


class FakeResponse:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return {
            "model": "custom:latest",
            "response": "generated text",
            "total_duration": 2_500_000,
            "prompt_eval_count": 8,
            "eval_count": 4,
            "eval_duration": 1_000_000_000,
            "done": True,
        }


def test_ollama_payload_maps_generation_config(monkeypatch: pytest.MonkeyPatch):
    request: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        request["url"] = url
        request.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(ollama.requests, "post", fake_post)
    runner = OllamaRunner(model="custom:latest")

    result = runner.generate(
        "Hello",
        config={
            "temperature": 0.0,
            "seed": 42,
            "max_tokens": 1024,
            "timeout_seconds": 300,
        },
    )

    assert request["url"] == "http://localhost:11434/api/generate"
    assert request["json"] == {
        "model": "custom:latest",
        "prompt": "Hello",
        "stream": False,
        "options": {
            "temperature": 0.0,
            "seed": 42,
            "num_predict": 1024,
        },
    }
    assert request["timeout"] == 300
    assert "timeout_seconds" not in request["json"]["options"]
    assert result["output"] == "generated text"
    assert result["latency_ms"] == 2
    assert result["input_tokens"] == 8
    assert result["output_tokens"] == 4
    assert result["cost_estimate"] == 0.0
    assert "response" not in result["raw_result"]


def test_unsupported_generation_option_fails_before_request(
    monkeypatch: pytest.MonkeyPatch,
):
    def unexpected_post(*args: Any, **kwargs: Any):
        pytest.fail("HTTP request should not be made")

    monkeypatch.setattr(ollama.requests, "post", unexpected_post)
    runner = OllamaRunner(model="custom:latest")

    with pytest.raises(ValueError, match="Unsupported Ollama generation option"):
        runner.generate("Hello", config={"top_p": 0.9})
