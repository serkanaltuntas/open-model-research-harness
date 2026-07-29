import json
from pathlib import Path
from typing import Any

from scripts.validate_dataset import main


REPOSITORY_ROOT = Path(__file__).parents[2]
FINAL_DATASET = REPOSITORY_ROOT / "datasets/evals/july_eval_v1.jsonl"


def load_final_tasks() -> list[dict[str, Any]]:
    return [json.loads(line) for line in FINAL_DATASET.read_text().splitlines()]


def write_tasks(path: Path, tasks: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(f"{json.dumps(task)}\n" for task in tasks),
        encoding="utf-8",
    )


def test_valid_final_dataset(capsys):
    assert main(["--dataset", str(FINAL_DATASET)]) == 0
    output = capsys.readouterr().out
    assert "OK: validated 25 tasks" in output
    for category in (
        "coding",
        "reasoning",
        "factuality",
        "instruction_following",
        "safety_lite",
    ):
        assert f"{category}: 5" in output


def test_duplicate_id_fails(tmp_path: Path, capsys):
    tasks = load_final_tasks()
    tasks[1]["id"] = tasks[0]["id"]
    dataset = tmp_path / "duplicate.jsonl"
    write_tasks(dataset, tasks)

    assert main(["--dataset", str(dataset)]) == 1
    error = capsys.readouterr().err
    assert "row 2" in error
    assert "duplicated" in error


def test_wrong_category_count_fails(tmp_path: Path, capsys):
    tasks = load_final_tasks()
    task = tasks[-1]
    task["category"] = "reasoning"
    task["grader"] = "rubric"
    dataset = tmp_path / "wrong-count.jsonl"
    write_tasks(dataset, tasks)

    assert main(["--dataset", str(dataset)]) == 1
    error = capsys.readouterr().err
    assert "exactly 5 tasks per category" in error
    assert "reasoning=6" in error
    assert "safety_lite=4" in error


def test_missing_grader_specific_field_fails(tmp_path: Path, capsys):
    tasks = load_final_tasks()
    del tasks[0]["tests"]
    dataset = tmp_path / "missing-tests.jsonl"
    write_tasks(dataset, tasks)

    assert main(["--dataset", str(dataset)]) == 1
    error = capsys.readouterr().err
    assert "row 1" in error
    assert "tests" in error


def test_unsupported_grader_fails(tmp_path: Path, capsys):
    tasks = load_final_tasks()
    tasks[0]["grader"] = "unknown"
    dataset = tmp_path / "unsupported-grader.jsonl"
    write_tasks(dataset, tasks)

    assert main(["--dataset", str(dataset)]) == 1
    error = capsys.readouterr().err
    assert "row 1" in error
    assert "unsupported grader" in error


def test_malformed_jsonl_fails(tmp_path: Path, capsys):
    dataset = tmp_path / "malformed.jsonl"
    dataset.write_text("{not valid json}\n", encoding="utf-8")

    assert main(["--dataset", str(dataset)]) == 1
    error = capsys.readouterr().err
    assert "row 1" in error
    assert "invalid JSON" in error
