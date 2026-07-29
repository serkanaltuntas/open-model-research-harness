from pathlib import Path

from harness.config import ModelConfig, load_model_config, load_run_config
from harness.runners.run_eval import build_run_metadata, resolve_evaluation_config


REPOSITORY_ROOT = Path(__file__).parents[2]


def test_cli_overrides_take_precedence_over_yaml_values():
    model_config = load_model_config(
        REPOSITORY_ROOT / "configs/models/lfm2_5_8b.yaml"
    )
    run_config = load_run_config(
        REPOSITORY_ROOT / "configs/runs/july_final.yaml"
    )

    resolved = resolve_evaluation_config(
        model_config=model_config,
        run_config=run_config,
        model_override="override:latest",
        dataset_override="override/tasks.jsonl",
        temperature_override=0.25,
        max_tokens_override=256,
        seed_override=7,
        timeout_seconds_override=45,
    )

    assert resolved.model_tag == "override:latest"
    assert resolved.dataset == "override/tasks.jsonl"
    assert resolved.temperature == 0.25
    assert resolved.max_tokens == 256
    assert resolved.seed == 7
    assert resolved.timeout_seconds == 45


def test_unlisted_model_name_is_accepted():
    model_config = ModelConfig(
        name="unlisted-model",
        backend="ollama",
        model="unlisted:latest",
        provider="Local test",
        ollama_id="test-id",
        quantization="unknown",
        known_caveats=(),
    )
    run_config = load_run_config(
        REPOSITORY_ROOT / "configs/runs/july_final.yaml"
    )

    resolved = resolve_evaluation_config(
        model_config=model_config,
        run_config=run_config,
    )

    assert resolved.model_tag == "unlisted:latest"


def test_resolved_run_metadata_contains_configured_provenance():
    model_config = load_model_config(
        REPOSITORY_ROOT / "configs/models/qwen3_6.yaml"
    )
    run_config = load_run_config(
        REPOSITORY_ROOT / "configs/runs/july_final.yaml"
    )
    resolved = resolve_evaluation_config(
        model_config=model_config,
        run_config=run_config,
    )

    metadata = build_run_metadata(
        resolved=resolved,
        run_id="test-run",
        task_count=25,
        started_at="2026-07-01T00:00:00+00:00",
    )

    assert metadata["model"]["name"] == "qwen3.6"
    assert metadata["model"]["model"] == "qwen3.6:latest"
    assert metadata["model"]["ollama_id"] == "07d35212591f"
    assert metadata["model"]["backend"] == "ollama"
    assert metadata["model"]["provider"] == "Qwen"
    assert metadata["model"]["quantization"] == "unknown"
    assert metadata["model"]["known_caveats"]
    assert metadata["dataset"]["path"] == "datasets/evals/july_eval_v1.jsonl"
    assert metadata["dataset"]["task_count"] == 25
    assert metadata["config"] == {
        "temperature": 0.0,
        "max_tokens": 1024,
        "seed": 42,
        "timeout_seconds": 300,
    }
