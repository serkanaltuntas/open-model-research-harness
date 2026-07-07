import json
import re
from typing import Any

from harness.graders.base import Grader, GraderResult


SUPPORTED_RULES = {
    "must_be_valid_json",
    "required_keys",
    "no_extra_text",
    "exact_bullet_count",
    "max_words_per_bullet",
}
BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(?P<text>.+?)\s*$")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)?")


class RuleBasedGrader(Grader):
    def grade(self, task: dict[str, Any], output: str) -> GraderResult:
        if task.get("category") != "instruction_following":
            return self._result(
                score=0.0,
                passed=False,
                reason="RuleBasedGrader only supports instruction_following tasks.",
                failure_mode="grader_error",
            )

        rules = task.get("rules")
        if not isinstance(rules, dict) or not rules:
            return self._result(
                score=0.0,
                passed=False,
                reason="No rule-based checks found for task.",
                failure_mode="grader_error",
            )

        failures: list[tuple[str, str]] = []
        unsupported_rules = sorted(set(rules) - SUPPORTED_RULES)
        if unsupported_rules:
            return self._result(
                score=0.0,
                passed=False,
                reason=f"Unsupported rules: {', '.join(unsupported_rules)}.",
                failure_mode="grader_error",
            )

        if self._has_json_rules(rules):
            failures.extend(self._check_json_rules(output, rules))

        if self._has_bullet_rules(rules):
            failures.extend(self._check_bullet_rules(output, rules))

        if not failures:
            return self._result(
                score=1.0,
                passed=True,
                reason="All rule-based checks passed.",
                failure_mode=None,
            )

        reason, failure_mode = failures[0]
        return self._result(
            score=0.0,
            passed=False,
            reason=reason,
            failure_mode=failure_mode,
        )

    def _check_json_rules(
        self,
        output: str,
        rules: dict[str, Any],
    ) -> list[tuple[str, str]]:
        stripped_output = output.strip()
        failures: list[tuple[str, str]] = []

        try:
            parsed = json.loads(stripped_output)
        except json.JSONDecodeError:
            return [("Output is not valid JSON.", "format_failure")]

        if not isinstance(parsed, dict):
            failures.append(("Output JSON is not an object.", "format_failure"))
            return failures

        required_keys = rules.get("required_keys")
        if isinstance(required_keys, list):
            missing_keys = [key for key in required_keys if key not in parsed]
            if missing_keys:
                failures.append(
                    (
                        f"Missing required keys: {', '.join(missing_keys)}.",
                        "instruction_miss",
                    )
                )

        return failures

    def _check_bullet_rules(
        self,
        output: str,
        rules: dict[str, Any],
    ) -> list[tuple[str, str]]:
        bullet_texts = [
            match.group("text")
            for line in output.splitlines()
            if (match := BULLET_RE.match(line))
        ]
        failures: list[tuple[str, str]] = []

        exact_count = rules.get("exact_bullet_count")
        if isinstance(exact_count, int) and len(bullet_texts) != exact_count:
            failures.append(
                (
                    f"Expected {exact_count} bullets, found {len(bullet_texts)}.",
                    "instruction_miss",
                )
            )

        max_words = rules.get("max_words_per_bullet")
        if isinstance(max_words, int):
            for index, bullet_text in enumerate(bullet_texts, start=1):
                word_count = len(WORD_RE.findall(bullet_text))
                if word_count > max_words:
                    failures.append(
                        (
                            f"Bullet {index} has {word_count} words; maximum is {max_words}.",
                            "over_answering",
                        )
                    )
                    break

        return failures

    def _has_json_rules(self, rules: dict[str, Any]) -> bool:
        return any(
            rule_name in rules
            for rule_name in ("must_be_valid_json", "required_keys", "no_extra_text")
        )

    def _has_bullet_rules(self, rules: dict[str, Any]) -> bool:
        return any(
            rule_name in rules
            for rule_name in ("exact_bullet_count", "max_words_per_bullet")
        )

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
