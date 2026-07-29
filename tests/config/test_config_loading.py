from pathlib import Path

import pytest

from harness.config import ConfigError, load_model_config, load_run_config


REPOSITORY_ROOT = Path(__file__).parents[2]
MODEL_CONFIGS = {
    "lfm2_5_8b.yaml": ("lfm2.5:8b", "9cf756159fc2"),
    "gpt_oss.yaml": ("gpt-oss:latest", "17052f91a42e"),
    "qwen3_6.yaml": ("qwen3.6:latest", "07d35212591f"),
}


@pytest.mark.parametrize(("filename", "expected"), MODEL_CONFIGS.items())
def test_model_configs_load(filename: str, expected: tuple[str, str]):
    config = load_model_config(REPOSITORY_ROOT / "configs/models" / filename)

    assert config.backend == "ollama"
    assert (config.model, config.ollama_id) == expected
    assert config.known_caveats


def test_july_run_config_loads():
    config = load_run_config(REPOSITORY_ROOT / "configs/runs/july_final.yaml")

    assert config.dataset == "datasets/evals/july_eval_v1.jsonl"
    assert config.temperature == 0.0
    assert config.max_tokens == 1024
    assert config.seed == 42
    assert config.timeout_seconds == 300


def test_missing_required_field_has_clear_error(tmp_path: Path):
    path = tmp_path / "missing.yaml"
    path.write_text(
        "dataset: tasks.jsonl\n"
        "temperature: 0.0\n"
        "max_tokens: 128\n"
        "seed: null\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="missing required field 'timeout_seconds'"):
        load_run_config(path)


def test_unknown_field_is_rejected(tmp_path: Path):
    path = tmp_path / "unknown.yaml"
    path.write_text(
        "dataset: tasks.jsonl\n"
        "temperature: 0.0\n"
        "max_tokens: 128\n"
        "seed: null\n"
        "timeout_seconds: 30\n"
        "extra_option: true\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="unknown field 'extra_option'"):
        load_run_config(path)
