from typing import Any

from harness.graders.base import Grader, GraderResult


class ExactMatchGrader(Grader):
    def grade(self, task: dict[str, Any], output: str) -> GraderResult:
        if task.get("category") != "factuality":
            return self._result(
                score=0.0,
                passed=False,
                reason="ExactMatchGrader only supports factuality tasks.",
                failure_mode="grader_error",
            )

        accepted_answers = self._accepted_answers(task)
        if not accepted_answers:
            return self._result(
                score=0.0,
                passed=False,
                reason="No accepted answers found for task.",
                failure_mode="grader_error",
            )

        normalized_output = self._normalize(output)
        if normalized_output in accepted_answers:
            return self._result(
                score=1.0,
                passed=True,
                reason="Output matched an accepted answer.",
                failure_mode=None,
            )

        return self._result(
            score=0.0,
            passed=False,
            reason="Output did not match any accepted answer.",
            failure_mode="format_failure",
        )

    def _accepted_answers(self, task: dict[str, Any]) -> set[str]:
        accepted_answers = task.get("accepted_answers")
        if not isinstance(accepted_answers, list):
            return set()

        return {
            self._normalize(answer)
            for answer in accepted_answers
            if isinstance(answer, str)
        }

    def _normalize(self, value: str) -> str:
        return value.strip().casefold()

    def _result(
        self,
        *,
        score: float,
        passed: bool,
        reason: str,
        failure_mode: str | None,
    ) -> GraderResult:
        return {
            "score": score,
            "passed": passed,
            "reason": reason,
            "failure_mode": failure_mode,
            "grader_confidence": "high",
        }
