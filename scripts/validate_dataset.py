import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_TASK_COUNT = 25
EXPECTED_CATEGORY_COUNT = 5
GRADER_BY_CATEGORY = {
    "coding": "unit_test",
    "reasoning": "rubric",
    "factuality": "exact_match",
    "instruction_following": "rule_based",
    "safety_lite": "rubric",
}
SUPPORTED_GRADERS = {"unit_test", "exact_match", "rule_based", "rubric"}
QUALITY_STATUSES = {"draft", "reviewed", "stable", "deprecated"}
REQUIRED_BASE_FIELDS = {
    "id",
    "category",
    "prompt",
    "grader",
    "expected_behavior",
    "difficulty",
    "tags",
    "claim_scope",
    "quality_status",
}


class DatasetValidationError(ValueError):
    """Raised when an evaluation dataset is invalid."""


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant {value}")


def _load_tasks(path: Path) -> list[tuple[int, Any]]:
    if not path.is_file():
        raise DatasetValidationError(f"{path}: file does not exist")

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise DatasetValidationError(f"{path}: invalid UTF-8: {error}") from error

    tasks: list[tuple[int, Any]] = []
    for row_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise DatasetValidationError(f"{path}: row {row_number}: empty JSONL row")
        try:
            task = json.loads(line, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, ValueError) as error:
            raise DatasetValidationError(
                f"{path}: row {row_number}: invalid JSON: {error}"
            ) from error
        tasks.append((row_number, task))
    return tasks


def _validate_grader_data(task: dict[str, Any], location: str) -> None:
    grader = task["grader"]
    if grader == "unit_test":
        tests = task.get("tests")
        if not isinstance(tests, list) or not tests:
            raise DatasetValidationError(
                f"{location}: field 'tests' must be a non-empty list"
            )
    elif grader == "exact_match":
        accepted_answers = task.get("accepted_answers")
        if not isinstance(accepted_answers, list) or not accepted_answers:
            raise DatasetValidationError(
                f"{location}: field 'accepted_answers' must be a non-empty list"
            )
    elif grader == "rule_based":
        rules = task.get("rules")
        if not isinstance(rules, dict) or not rules:
            raise DatasetValidationError(
                f"{location}: field 'rules' must be a non-empty object"
            )
    elif grader == "rubric":
        rubric = task.get("rubric")
        if not isinstance(rubric, dict) or not rubric:
            raise DatasetValidationError(
                f"{location}: field 'rubric' must be a non-empty object"
            )
        criteria = rubric.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            raise DatasetValidationError(
                f"{location}: field 'rubric.criteria' must be a non-empty list"
            )
        passing_score = rubric.get("passing_score")
        if isinstance(passing_score, bool) or not isinstance(
            passing_score, int | float
        ):
            raise DatasetValidationError(
                f"{location}: field 'rubric.passing_score' must be numeric"
            )


def validate_dataset(path: Path) -> Counter[str]:
    numbered_tasks = _load_tasks(path)
    if len(numbered_tasks) != EXPECTED_TASK_COUNT:
        raise DatasetValidationError(
            f"{path}: expected exactly {EXPECTED_TASK_COUNT} tasks, "
            f"found {len(numbered_tasks)}"
        )

    seen_ids: set[str] = set()
    category_counts: Counter[str] = Counter()
    for row_number, task in numbered_tasks:
        location = f"{path}: row {row_number}"
        if not isinstance(task, dict):
            raise DatasetValidationError(f"{location}: task must be a JSON object")

        missing_fields = sorted(REQUIRED_BASE_FIELDS - task.keys())
        if missing_fields:
            raise DatasetValidationError(
                f"{location}: missing required field '{missing_fields[0]}'"
            )

        task_id = task["id"]
        if not isinstance(task_id, str) or not task_id:
            raise DatasetValidationError(
                f"{location}: field 'id' must be a non-empty string"
            )
        if task_id in seen_ids:
            raise DatasetValidationError(
                f"{location}: field 'id' is duplicated: {task_id!r}"
            )
        seen_ids.add(task_id)

        category = task["category"]
        if category not in GRADER_BY_CATEGORY:
            supported = ", ".join(sorted(GRADER_BY_CATEGORY))
            raise DatasetValidationError(
                f"{location}: unsupported category {category!r}; supported: {supported}"
            )
        category_counts[category] += 1

        grader = task["grader"]
        if grader not in SUPPORTED_GRADERS:
            supported = ", ".join(sorted(SUPPORTED_GRADERS))
            raise DatasetValidationError(
                f"{location}: unsupported grader {grader!r}; supported: {supported}"
            )
        expected_grader = GRADER_BY_CATEGORY[category]
        if grader != expected_grader:
            raise DatasetValidationError(
                f"{location}: grader {grader!r} does not match category "
                f"{category!r}; expected {expected_grader!r}"
            )

        quality_status = task["quality_status"]
        if quality_status not in QUALITY_STATUSES:
            supported = ", ".join(sorted(QUALITY_STATUSES))
            raise DatasetValidationError(
                f"{location}: field 'quality_status' must be one of: {supported}"
            )

        _validate_grader_data(task, location)

    wrong_counts = {
        category: category_counts[category]
        for category in GRADER_BY_CATEGORY
        if category_counts[category] != EXPECTED_CATEGORY_COUNT
    }
    if wrong_counts:
        details = ", ".join(
            f"{category}={count}" for category, count in sorted(wrong_counts.items())
        )
        raise DatasetValidationError(
            f"{path}: expected exactly {EXPECTED_CATEGORY_COUNT} tasks per category; "
            f"found {details}"
        )

    return category_counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the July eval dataset.")
    parser.add_argument("--dataset", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        category_counts = validate_dataset(args.dataset)
    except DatasetValidationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"OK: validated {sum(category_counts.values())} tasks")
    for category in GRADER_BY_CATEGORY:
        print(f"{category}: {category_counts[category]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
