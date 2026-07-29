import json
from pathlib import Path
from typing import Any

import pytest

from harness.reporting.compare_runs import ComparisonError, compare_runs


SHARED_CONFIG = {
    "temperature": 0.0,
    "max_tokens": 128,
    "seed": 42,
    "timeout_seconds": 30,
}


def make_result(
    task_id: str,
    category: str,
    passed: bool,
    *,
    score: float | None = None,
    latency_ms: int | None = 10,
    input_tokens: int | None = 5,
    output_tokens: int | None = 4,
    failure_mode: str = "test_failure",
) -> dict[str, Any]:
    resolved_score = (1.0 if passed else 0.0) if score is None else score
    raw_result = (
        {"eval_count": output_tokens, "eval_duration": 1_000_000_000}
        if output_tokens is not None
        else {}
    )
    return {
        "run_id": "placeholder",
        "task_id": task_id,
        "category": category,
        "model": "placeholder",
        "prompt_hash": f"hash-{task_id}",
        "output": f"output-{task_id}",
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_estimate": 0.0,
        "raw_result": raw_result,
        "grader": "unit_test" if category == "coding" else "exact_match",
        "score": resolved_score,
        "passed": passed,
        "reason": "Passed." if passed else "Failed.",
        "failure_mode": None if passed else failure_mode,
        "grader_confidence": "high",
    }


def write_run(
    root: Path,
    model_name: str,
    results: list[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
) -> Path:
    run_dir = root / model_name
    run_dir.mkdir()
    run_id = f"run-{model_name}"
    for result in results:
        result["run_id"] = run_id
        result["model"] = f"{model_name}:latest"

    metadata = {
        "run_id": run_id,
        "month_gate": "test-gate",
        "model": {
            "name": model_name,
            "model": f"{model_name}:latest",
            "ollama_id": f"id-{model_name}",
            "backend": "ollama",
            "provider": "Test",
            "quantization": "unknown",
            "known_caveats": [],
        },
        "dataset": {
            "name": "fixture",
            "version": "v1",
            "path": "fixture.jsonl",
            "task_count": len(results),
        },
        "config": config or SHARED_CONFIG,
    }
    (run_dir / "run.json").write_text(json.dumps(metadata), encoding="utf-8")
    (run_dir / "results.jsonl").write_text(
        "".join(json.dumps(result) + "\n" for result in results),
        encoding="utf-8",
    )
    return run_dir


@pytest.fixture
def comparable_run_dirs(tmp_path: Path) -> list[Path]:
    task_specs = [
        ("all-pass", "coding"),
        ("all-fail", "coding"),
        ("one-pass", "factuality"),
        ("two-pass", "factuality"),
    ]
    status_by_model = {
        "model-a": [True, False, True, True],
        "model-b": [True, False, False, True],
        "model-c": [True, False, False, False],
    }
    run_dirs = []
    for model_name, statuses in status_by_model.items():
        results = [
            make_result(task_id, category, passed)
            for (task_id, category), passed in zip(task_specs, statuses)
        ]
        if model_name == "model-a":
            results[2]["latency_ms"] = None
            results[2]["input_tokens"] = None
            results[2]["output_tokens"] = None
            results[2]["raw_result"] = {}
        run_dirs.append(write_run(tmp_path, model_name, results))
    return run_dirs


def test_comparable_runs_aggregate_correctly(comparable_run_dirs: list[Path]):
    comparison = compare_runs(comparable_run_dirs)
    model = comparison["models"]["model-a"]

    assert model["task_count"] == 4
    assert model["passed_count"] == 3
    assert model["failed_count"] == 1
    assert model["pass_rate"] == 0.75
    assert model["score_sum"] == 3.0
    assert model["grader_error_count"] == 0


def test_category_and_failure_metrics_are_correct(
    comparable_run_dirs: list[Path],
):
    comparison = compare_runs(comparable_run_dirs)
    model = comparison["models"]["model-b"]

    assert model["category_metrics"]["coding"] == {
        "task_count": 2,
        "passed_count": 1,
        "failed_count": 1,
        "pass_rate": 0.5,
        "mean_score": 0.5,
    }
    assert model["category_metrics"]["factuality"]["passed_count"] == 1
    assert model["failure_mode_counts"] == {"test_failure": 2}


def test_missing_numeric_data_is_tracked_not_zeroed(
    comparable_run_dirs: list[Path],
):
    comparison = compare_runs(comparable_run_dirs)
    model = comparison["models"]["model-a"]

    assert model["latency_ms"]["available_count"] == 3
    assert model["latency_ms"]["missing_count"] == 1
    assert model["latency_ms"]["average"] == 10.0
    assert model["tokens"]["input_missing_count"] == 1
    assert model["tokens"]["total_input_tokens"] == 15
    assert model["tokens"]["output_missing_count"] == 1
    assert model["tokens"]["total_output_tokens"] == 12
    assert model["generation_throughput"]["missing_task_count"] == 1


def test_task_level_pass_patterns_are_classified(
    comparable_run_dirs: list[Path],
):
    comparison = compare_runs(comparable_run_dirs)
    patterns = {
        task["task_id"]: task["pattern"]
        for task in comparison["task_comparisons"]
    }

    assert patterns == {
        "all-pass": "passed_by_all_models",
        "all-fail": "failed_by_all_models",
        "one-pass": "passed_only_by_one_model",
        "two-pass": "passed_by_exactly_two_models",
    }


def test_incompatible_configuration_is_rejected(tmp_path: Path):
    results = [make_result("task", "coding", True)]
    first = write_run(tmp_path, "first", results)
    incompatible_config = {**SHARED_CONFIG, "seed": 7}
    second = write_run(
        tmp_path,
        "second",
        [make_result("task", "coding", True)],
        config=incompatible_config,
    )

    with pytest.raises(ComparisonError, match="incompatible shared configuration"):
        compare_runs([first, second])


def test_comparison_json_is_deterministic(comparable_run_dirs: list[Path]):
    first = json.dumps(compare_runs(comparable_run_dirs), sort_keys=True)
    second = json.dumps(compare_runs(comparable_run_dirs), sort_keys=True)

    assert first == second


def test_malformed_result_fails_clearly(tmp_path: Path):
    first = write_run(tmp_path, "first", [make_result("task", "coding", True)])
    second = write_run(tmp_path, "second", [make_result("task", "coding", True)])
    (second / "results.jsonl").write_text("{invalid json}\n", encoding="utf-8")

    with pytest.raises(ComparisonError, match="row 1: invalid JSON"):
        compare_runs([first, second])


def test_duplicate_task_result_fails_clearly(tmp_path: Path):
    first = write_run(tmp_path, "first", [make_result("task", "coding", True)])
    duplicate = make_result("task", "coding", True)
    second = write_run(tmp_path, "second", [duplicate, duplicate.copy()])

    with pytest.raises(ComparisonError, match="duplicate task_id"):
        compare_runs([first, second])
