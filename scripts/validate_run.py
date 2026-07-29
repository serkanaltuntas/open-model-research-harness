import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


REQUIRED_RESULT_FIELDS = {
    "run_id",
    "task_id",
    "category",
    "model",
    "output",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "cost_estimate",
    "raw_result",
    "grader",
    "score",
    "passed",
    "reason",
    "failure_mode",
    "grader_confidence",
}
GRADER_CONFIDENCE_VALUES = {"low", "medium", "high"}


class RunValidationError(ValueError):
    """Raised when a completed evaluation run is invalid."""


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant {value}")


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise RunValidationError(f"{path}: file does not exist")

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
        raise RunValidationError(f"{path}: invalid JSON: {error}") from error


def _load_jsonl(path: Path) -> list[tuple[int, Any]]:
    if not path.is_file():
        raise RunValidationError(f"{path}: file does not exist")

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise RunValidationError(f"{path}: invalid UTF-8: {error}") from error

    rows: list[tuple[int, Any]] = []
    for row_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise RunValidationError(f"{path}: row {row_number}: empty JSONL row")
        try:
            row = json.loads(line, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, ValueError) as error:
            raise RunValidationError(
                f"{path}: row {row_number}: invalid JSON: {error}"
            ) from error
        rows.append((row_number, row))

    return rows


def _run_metadata(run_path: Path) -> tuple[str, int]:
    run_data = _load_json(run_path)
    if not isinstance(run_data, dict):
        raise RunValidationError(f"{run_path}: root must be a JSON object")

    run_id = run_data.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise RunValidationError(f"{run_path}: field 'run_id' must be a non-empty string")

    dataset = run_data.get("dataset")
    if not isinstance(dataset, dict):
        raise RunValidationError(f"{run_path}: field 'dataset' must be an object")

    task_count = dataset.get("task_count")
    if isinstance(task_count, bool) or not isinstance(task_count, int):
        raise RunValidationError(
            f"{run_path}: field 'dataset.task_count' must be an integer"
        )
    if task_count < 0:
        raise RunValidationError(
            f"{run_path}: field 'dataset.task_count' must not be negative"
        )

    return run_id, task_count


def _validate_result(
    *,
    result: Any,
    row_number: int,
    results_path: Path,
    run_id: str,
) -> None:
    location = f"{results_path}: row {row_number}"
    if not isinstance(result, dict):
        raise RunValidationError(f"{location}: result must be a JSON object")

    missing_fields = sorted(REQUIRED_RESULT_FIELDS - result.keys())
    if missing_fields:
        raise RunValidationError(
            f"{location}: missing required field '{missing_fields[0]}'"
        )

    if result["run_id"] != run_id:
        raise RunValidationError(
            f"{location}: field 'run_id' does not match run.json run_id {run_id!r}"
        )

    score = result["score"]
    if isinstance(score, bool) or not isinstance(score, int | float):
        raise RunValidationError(f"{location}: field 'score' must be numeric")
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise RunValidationError(
            f"{location}: field 'score' must be between 0.0 and 1.0"
        )

    passed = result["passed"]
    if not isinstance(passed, bool):
        raise RunValidationError(f"{location}: field 'passed' must be boolean")

    confidence = result["grader_confidence"]
    if confidence not in GRADER_CONFIDENCE_VALUES:
        supported = ", ".join(sorted(GRADER_CONFIDENCE_VALUES))
        raise RunValidationError(
            f"{location}: field 'grader_confidence' must be one of: {supported}"
        )

    if not passed:
        failure_mode = result["failure_mode"]
        if not isinstance(failure_mode, str) or not failure_mode.strip():
            raise RunValidationError(
                f"{location}: field 'failure_mode' must be non-empty when passed is false"
            )


def validate_run(run_dir: Path) -> dict[str, int]:
    run_path = run_dir / "run.json"
    results_path = run_dir / "results.jsonl"
    run_id, expected_count = _run_metadata(run_path)
    numbered_results = _load_jsonl(results_path)

    if not numbered_results:
        raise RunValidationError(f"{results_path}: result count must not be zero")

    seen_task_ids: list[Any] = []
    results: list[dict[str, Any]] = []
    for row_number, result in numbered_results:
        _validate_result(
            result=result,
            row_number=row_number,
            results_path=results_path,
            run_id=run_id,
        )
        task_id = result["task_id"]
        if task_id in seen_task_ids:
            raise RunValidationError(
                f"{results_path}: row {row_number}: field 'task_id' is duplicated: "
                f"{task_id!r}"
            )
        seen_task_ids.append(task_id)
        results.append(result)

    if len(results) != expected_count:
        raise RunValidationError(
            f"{results_path}: result count {len(results)} does not match "
            f"run.json field 'dataset.task_count' ({expected_count})"
        )

    passed_count = sum(result["passed"] for result in results)
    failed_count = len(results) - passed_count
    grader_error_count = sum(
        result["failure_mode"] == "grader_error" for result in results
    )
    return {
        "result_count": len(results),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "grader_error_count": grader_error_count,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a completed eval run.")
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        summary = validate_run(args.run_dir)
    except RunValidationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"OK: validated {summary['result_count']} scored results")
    print(f"Passed: {summary['passed_count']}")
    print(f"Failed: {summary['failed_count']}")
    print(f"Grader errors: {summary['grader_error_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
