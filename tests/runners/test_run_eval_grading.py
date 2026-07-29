import json
from pathlib import Path
from typing import Any

import pytest

from harness.graders.base import Grader
from harness.runners.base import ModelRunner
from harness.runners.run_eval import write_results
from harness.schemas.task import Task


class FakeRunner(ModelRunner):
    name = "fake-runner"

    def __init__(self, outputs: dict[str, str]) -> None:
        self.outputs = outputs

    def generate(self, prompt: str, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": "fake-model",
            "output": self.outputs[prompt],
            "latency_ms": 12,
            "input_tokens": 3,
            "output_tokens": 5,
            "cost_estimate": 0.0,
            "raw_result": {"source": "fake"},
        }


class ExplodingGrader(Grader):
    def grade(self, task: dict[str, Any], output: str):
        raise RuntimeError("grader exploded")


def make_task(
    task_id: str,
    category: str,
    grader: str,
    **grader_data: Any,
) -> Task:
    return Task(
        id=task_id,
        category=category,
        prompt=f"prompt-{task_id}",
        grader=grader,
        expected_behavior="Expected behavior.",
        difficulty="easy",
        tags=["test"],
        claim_scope="Test only.",
        quality_status="draft",
        **grader_data,
    )


def read_results(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_write_results_grades_all_supported_task_types(tmp_path: Path):
    tasks = [
        make_task(
            "coding",
            "coding",
            "unit_test",
            tests=["assert answer() == 42"],
        ),
        make_task(
            "factuality",
            "factuality",
            "exact_match",
            accepted_answers=["Au"],
        ),
        make_task(
            "instruction",
            "instruction_following",
            "rule_based",
            rules={"exact_sentence_count": 1},
        ),
        make_task(
            "reasoning",
            "reasoning",
            "rubric",
            rubric={
                "passing_score": 1.0,
                "criteria": [
                    {"name": "answer", "weight": 1.0, "requires_any": ["yes"]}
                ],
            },
        ),
    ]
    runner = FakeRunner(
        {
            "prompt-coding": "def answer(): return 42",
            "prompt-factuality": " Au ",
            "prompt-instruction": "One sentence.",
            "prompt-reasoning": "Yes.",
        }
    )
    results_path = tmp_path / "results.jsonl"

    write_results(
        tasks=tasks,
        runner=runner,
        results_path=results_path,
        run_id="test-run",
        runner_name="fake",
    )

    results = read_results(results_path)
    assert len(results) == len(tasks)
    assert [result["grader"] for result in results] == [
        "unit_test",
        "exact_match",
        "rule_based",
        "rubric",
    ]
    assert all(result["passed"] is True for result in results)
    assert all(result["score"] == 1.0 for result in results)

    required_fields = {
        "grader",
        "score",
        "passed",
        "reason",
        "failure_mode",
        "grader_confidence",
        "run_id",
        "task_id",
        "category",
        "model",
        "prompt",
        "output",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "cost_estimate",
        "raw_result",
    }
    assert required_fields <= results[0].keys()
    assert results[0]["run_id"] == "test-run"
    assert results[0]["model"] == "fake-model"
    assert results[0]["latency_ms"] == 12
    assert results[0]["raw_result"] == {"source": "fake"}


def test_grader_exception_is_recorded_and_later_tasks_continue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    tasks = [
        make_task("broken", "factuality", "broken"),
        make_task(
            "later",
            "factuality",
            "exact_match",
            accepted_answers=["Au"],
        ),
    ]
    runner = FakeRunner({"prompt-broken": "ignored", "prompt-later": "Au"})
    results_path = tmp_path / "results.jsonl"

    from harness.runners import run_eval

    original_get_grader = run_eval.get_grader

    def fake_get_grader(name: str):
        if name == "broken":
            return ExplodingGrader()
        return original_get_grader(name)

    monkeypatch.setattr(run_eval, "get_grader", fake_get_grader)

    write_results(
        tasks=tasks,
        runner=runner,
        results_path=results_path,
        run_id="failure-run",
        runner_name="fake",
    )

    results = read_results(results_path)
    assert len(results) == len(tasks)
    assert results[0]["score"] == 0.0
    assert results[0]["passed"] is False
    assert results[0]["failure_mode"] == "grader_error"
    assert results[0]["grader_confidence"] == "low"
    assert "RuntimeError" in results[0]["reason"]
    assert results[1]["passed"] is True


def test_unsupported_grader_is_recorded_without_stopping_run(tmp_path: Path):
    tasks = [
        make_task("unknown", "factuality", "not_registered"),
        make_task(
            "supported",
            "factuality",
            "exact_match",
            accepted_answers=["Au"],
        ),
    ]
    runner = FakeRunner({"prompt-unknown": "ignored", "prompt-supported": "Au"})
    results_path = tmp_path / "results.jsonl"

    write_results(
        tasks=tasks,
        runner=runner,
        results_path=results_path,
        run_id="unsupported-run",
        runner_name="fake",
    )

    results = read_results(results_path)
    assert len(results) == 2
    assert results[0]["failure_mode"] == "grader_error"
    assert results[0]["grader_confidence"] == "low"
    assert results[1]["passed"] is True
