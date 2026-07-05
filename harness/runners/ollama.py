from typing import Any
import requests

from harness.runners.base import ModelRunner


class OllamaRunner(ModelRunner):
    name = "ollama-runner"

    def __init__(self, model) -> None:
        self.model = model

    def generate(self, prompt: str, config: dict[str, Any]) -> dict[str, Any]:
        output = self._request_generation(prompt)

        return {
            "model": self.model,
            "output": output["output"],
            "latency_ms": output["latency_ms"],
            "input_tokens": output["input_tokens"],
            "output_tokens": output["output_tokens"],
            "cost_estimate": output["cost_estimate"],
            "raw_result": output["raw_result"],
        }

    def _tokens_per_second(self, token_count: int | None, duration_ns: int | None) -> float | None:
        if not token_count or not duration_ns or duration_ns <= 0:
            return None

        return token_count / (duration_ns / 1_000_000_000)

    def _request_generation(self, prompt: str) -> dict[str, Any]:
        response = requests.post(
            "http://localhost:11434/api/generate", json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            })

        response.raise_for_status()
        payload = response.json()

        eval_count = payload.get("eval_count")
        eval_duration = payload.get("eval_duration")
        prompt_eval_count = payload.get("prompt_eval_count")
        latency_ms = int(payload.get("total_duration", 0) / 1_000_000)

        return {
            "model": self.model,
            "output": payload.get("response", ""),
            "latency_ms": latency_ms,
            "input_tokens": prompt_eval_count,
            "output_tokens": eval_count,
            "cost_estimate": 0.0,
            "output_tokens_per_sec": self._tokens_per_second(eval_count, eval_duration),
            "raw_result": {k: v for k, v in payload.items() if k != "response"},
        }
