import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness.config import ConfigError, load_mlx_model_config
from scripts.check_mlx_training_compatibility import (
    CompatibilityError,
    run_compatibility_check,
    verify_chat_template,
)


REPOSITORY_ROOT = Path(__file__).parents[2]
CONFIG_PATH = REPOSITORY_ROOT / "configs/models/qwen3_8b_mlx_4bit.yaml"
REVISION = "545dc4251c05440727734bcd94334791f6ab0192"
CHAT_TEMPLATE = (
    "{% for message in messages %}"
    "<|im_start|>{{ message['role'] }}\n{{ message['content'] }}<|im_end|>\n"
    "{% endfor %}"
    "{% if add_generation_prompt %}<|im_start|>assistant\n{% endif %}"
)


class FakeTokenizer:
    chat_template = CHAT_TEMPLATE

    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        assert tokenize is False
        assert add_generation_prompt is True
        message = messages[0]
        return (
            f"<|im_start|>{message['role']}\n{message['content']}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )


def make_snapshot(tmp_path: Path, config) -> Path:
    snapshot = tmp_path / REVISION
    snapshot.mkdir()
    (snapshot / config.model_artifact.path).write_bytes(
        b"x" * config.model_artifact.size_bytes
    )
    (snapshot / config.tokenizer_artifact.path).write_bytes(
        b"x" * config.tokenizer_artifact.size_bytes
    )
    (snapshot / config.chat_template_file).write_text(
        json.dumps({"chat_template": CHAT_TEMPLATE}),
        encoding="utf-8",
    )
    return snapshot


def test_pinned_mlx_model_config_loads():
    config = load_mlx_model_config(CONFIG_PATH)

    assert config.backend == "mlx"
    assert config.repository == "mlx-community/Qwen3-8B-4bit"
    assert config.revision == REVISION
    assert (config.quantization_bits, config.quantization_group_size) == (4, 64)
    assert config.model_artifact.sha256.startswith("f2d29621")


def test_script_entrypoint_can_import_repository_package():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_mlx_training_compatibility.py",
            "--help",
        ],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--model-config" in result.stdout


def test_mlx_model_config_rejects_mutable_revision(tmp_path: Path):
    text = CONFIG_PATH.read_text(encoding="utf-8").replace(REVISION, "main")
    path = tmp_path / "model.yaml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigError, match="40-character commit hash"):
        load_mlx_model_config(path)


def test_chat_template_must_match_pinned_tokenizer(tmp_path: Path):
    config = load_mlx_model_config(CONFIG_PATH)
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / config.chat_template_file).write_text(
        json.dumps({"chat_template": "different"}),
        encoding="utf-8",
    )

    with pytest.raises(CompatibilityError, match="does not match"):
        verify_chat_template(
            tokenizer=FakeTokenizer(),
            snapshot=snapshot,
            config=config,
        )


def test_compatibility_check_uses_pinned_snapshot_without_training(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    original = load_mlx_model_config(CONFIG_PATH)
    config = replace(
        original,
        model_artifact=replace(original.model_artifact, size_bytes=4),
        tokenizer_artifact=replace(original.tokenizer_artifact, size_bytes=4),
    )
    snapshot = make_snapshot(tmp_path, config)
    # This is an offline dependency-injected test, not an MLX installation check.
    monkeypatch.setattr(
        "scripts.check_mlx_training_compatibility._package_version",
        lambda name: "test-version",
    )
    monkeypatch.setattr(
        "scripts.check_mlx_training_compatibility._macos_version",
        lambda: "test-macos",
    )
    calls = {}

    def fake_snapshot_download(**kwargs):
        calls["snapshot"] = kwargs
        return str(snapshot)

    def fake_load(path, *, lazy, return_config):
        calls["load"] = (path, lazy, return_config)
        return SimpleNamespace(), FakeTokenizer(), {"model_type": "qwen3"}

    def fake_generate(model, tokenizer, **kwargs):
        calls["generate"] = kwargs
        return "OK"

    result = run_compatibility_check(
        config,
        snapshot_download_fn=fake_snapshot_download,
        load_fn=fake_load,
        generate_fn=fake_generate,
        sampler_fn=lambda **kwargs: kwargs,
        lora_check_fn=lambda: {"available": True},
    )

    assert result["status"] == "GO"
    assert calls["snapshot"]["revision"] == REVISION
    assert calls["load"] == (str(snapshot), False, True)
    assert calls["generate"]["max_tokens"] == 8
    assert result["tokenizer"]["custom_template_supplied"] is False
