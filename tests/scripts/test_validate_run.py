import json
from pathlib import Path
from typing import Any

from scripts.validate_run import main


def valid_result(task_id: str, *, passed: bool = True) -> dict[str, Any]:
    return {
        "run_id": "test-run",
        "task_id": task_id,
        "category": "factuality",
        "model": "fake-model",
        "output": "Au",
        "latency_ms": 10,
        "input_tokens": 4,
        "output_tokens": 1,
        "cost_estimate": 0.0,
        "raw_result": {},
        "grader": "exact_match",
        "score": 1.0 if passed else 0.0,
        "passed": passed,
        "reason": "Output matched." if passed else "Output did not match.",
        "failure_mode": None if passed else "format_failure",
        "grader_confidence": "high",
    }


def write_run(run_dir: Path, results: list[dict[str, Any]], task_count: int | None = None):
    run_dir.mkdir()
    run_data = {
        "run_id": "test-run",
        "dataset": {"task_count": len(results) if task_count is None else task_count},
    }
    (run_dir / "run.json").write_text(json.dumps(run_data), encoding="utf-8")
    (run_dir / "results.jsonl").write_text(
        "".join(f"{json.dumps(result)}\n" for result in results),
        encoding="utf-8",
    )


def test_valid_scored_run_prints_summary(tmp_path: Path, capsys):
    run_dir = tmp_path / "valid"
    write_run(run_dir, [valid_result("task-1"), valid_result("task-2", passed=False)])

    assert main(["--run-dir", str(run_dir)]) == 0

    output = capsys.readouterr().out
    assert "OK: validated 2 scored results" in output
    assert "Passed: 1" in output
    assert "Failed: 1" in output
    assert "Grader errors: 0" in output


def test_missing_required_field_fails_with_row_and_field(tmp_path: Path, capsys):
    run_dir = tmp_path / "missing-field"
    result = valid_result("task-1")
    del result["reason"]
    write_run(run_dir, [result])

    assert main(["--run-dir", str(run_dir)]) == 1
    error = capsys.readouterr().err
    assert "results.jsonl: row 1" in error
    assert "reason" in error


def test_duplicate_task_id_fails(tmp_path: Path, capsys):
    run_dir = tmp_path / "duplicate"
    write_run(run_dir, [valid_result("same"), valid_result("same")])

    assert main(["--run-dir", str(run_dir)]) == 1
    error = capsys.readouterr().err
    assert "row 2" in error
    assert "task_id" in error
    assert "duplicated" in error


def test_invalid_score_range_fails(tmp_path: Path, capsys):
    run_dir = tmp_path / "invalid-score"
    result = valid_result("task-1")
    result["score"] = 1.1
    write_run(run_dir, [result])

    assert main(["--run-dir", str(run_dir)]) == 1
    error = capsys.readouterr().err
    assert "row 1" in error
    assert "score" in error
    assert "between 0.0 and 1.0" in error


def test_failed_task_without_failure_mode_fails(tmp_path: Path, capsys):
    run_dir = tmp_path / "missing-failure-mode"
    result = valid_result("task-1", passed=False)
    result["failure_mode"] = None
    write_run(run_dir, [result])

    assert main(["--run-dir", str(run_dir)]) == 1
    error = capsys.readouterr().err
    assert "row 1" in error
    assert "failure_mode" in error


def test_result_count_mismatch_fails(tmp_path: Path, capsys):
    run_dir = tmp_path / "count-mismatch"
    write_run(run_dir, [valid_result("task-1")], task_count=2)

    assert main(["--run-dir", str(run_dir)]) == 1
    error = capsys.readouterr().err
    assert "result count 1" in error
    assert "dataset.task_count" in error
