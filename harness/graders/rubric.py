from typing import Any

from harness.graders.base import Grader, GraderResult


SUPPORTED_RUBRIC_FIELDS = {"passing_score", "criteria"}
SUPPORTED_CRITERION_FIELDS = {
    "name",
    "weight",
    "requires_any",
    "requires_all",
    "forbids_any",
}


class RubricGrader(Grader):
    def grade(self, task: dict[str, Any], output: str) -> GraderResult:
        rubric = task.get("rubric")
        if not isinstance(rubric, dict):
            return self._result(
                score=0.0,
                passed=False,
                reason="No rubric found for task.",
                failure_mode="grader_error",
            )

        unsupported_rubric_fields = sorted(set(rubric) - SUPPORTED_RUBRIC_FIELDS)
        if unsupported_rubric_fields:
            return self._result(
                score=0.0,
                passed=False,
                reason=f"Unsupported rubric fields: {', '.join(unsupported_rubric_fields)}.",
                failure_mode="grader_error",
            )

        passing_score = rubric.get("passing_score")
        criteria = rubric.get("criteria")
        if not isinstance(passing_score, int | float):
            return self._result(
                score=0.0,
                passed=False,
                reason="Rubric passing_score must be numeric.",
                failure_mode="grader_error",
            )
        if not isinstance(criteria, list) or not criteria:
            return self._result(
                score=0.0,
                passed=False,
                reason="Rubric criteria must be a non-empty list.",
                failure_mode="grader_error",
            )

        output_text = output.casefold()
        matched_criteria = 0
        score = 0.0

        for criterion in criteria:
            if not isinstance(criterion, dict):
                return self._result(
                    score=0.0,
                    passed=False,
                    reason="Rubric criterion must be an object.",
                    failure_mode="grader_error",
                )

            unsupported_criterion_fields = sorted(
                set(criterion) - SUPPORTED_CRITERION_FIELDS
            )
            if unsupported_criterion_fields:
                return self._result(
                    score=0.0,
                    passed=False,
                    reason=(
                        "Unsupported criterion fields: "
                        f"{', '.join(unsupported_criterion_fields)}."
                    ),
                    failure_mode="grader_error",
                )

            weight = criterion.get("weight")
            if not isinstance(weight, int | float):
                return self._result(
                    score=0.0,
                    passed=False,
                    reason="Rubric criterion weight must be numeric.",
                    failure_mode="grader_error",
                )

            for field_name in ("requires_any", "requires_all", "forbids_any"):
                if field_name in criterion and not isinstance(
                    criterion[field_name],
                    list,
                ):
                    return self._result(
                        score=0.0,
                        passed=False,
                        reason=f"Rubric criterion {field_name} must be a list.",
                        failure_mode="grader_error",
                    )

            if self._criterion_matches(criterion, output_text):
                matched_criteria += 1
                score += float(weight)

        score = round(score, 4)
        passed = score >= float(passing_score)
        if passed:
            return self._result(
                score=score,
                passed=True,
                reason=f"Matched {matched_criteria} of {len(criteria)} rubric criteria.",
                failure_mode=None,
            )

        return self._result(
            score=score,
            passed=False,
            reason="Missing required rubric criteria.",
            failure_mode="wrong_reasoning",
        )

    def _criterion_matches(self, criterion: dict[str, Any], output_text: str) -> bool:
        requires_any = criterion.get("requires_any")
        if isinstance(requires_any, list) and not self._contains_any(
            output_text,
            requires_any,
        ):
            return False

        requires_all = criterion.get("requires_all")
        if isinstance(requires_all, list) and not self._contains_all(
            output_text,
            requires_all,
        ):
            return False

        forbids_any = criterion.get("forbids_any")
        if isinstance(forbids_any, list) and self._contains_any(
            output_text,
            forbids_any,
        ):
            return False

        return True

    def _contains_any(self, output_text: str, values: list[Any]) -> bool:
        return any(str(value).casefold() in output_text for value in values)

    def _contains_all(self, output_text: str, values: list[Any]) -> bool:
        return all(str(value).casefold() in output_text for value in values)

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
            "grader_confidence": "medium",
        }
