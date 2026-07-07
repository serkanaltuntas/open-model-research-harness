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
    "exact_sentence_count",
    "max_words_per_sentence",
    "no_extra_keys",
    "indent_spaces",
}
BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(?P<text>.+?)\s*$")
SENTENCE_RE = re.compile(r"[^.!?]+[.!?]")
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

        if self._has_sentence_rules(rules):
            failures.extend(self._check_sentence_rules(output, rules))

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

            if rules.get("no_extra_keys"):
                extra_keys = [key for key in parsed if key not in required_keys]
                if extra_keys:
                    failures.append(
                        (
                            f"Found extra keys: {', '.join(extra_keys)}.",
                            "over_answering",
                        )
                    )

        indent_spaces = rules.get("indent_spaces")
        if isinstance(indent_spaces, int):
            pretty_output = json.dumps(parsed, indent=indent_spaces, ensure_ascii=False)
            if stripped_output != pretty_output:
                failures.append(
                    (
                        f"JSON is not pretty-printed with {indent_spaces} spaces.",
                        "format_failure",
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

    def _check_sentence_rules(
        self,
        output: str,
        rules: dict[str, Any],
    ) -> list[tuple[str, str]]:
        sentences = [match.group(0).strip() for match in SENTENCE_RE.finditer(output)]
        failures: list[tuple[str, str]] = []

        exact_count = rules.get("exact_sentence_count")
        if isinstance(exact_count, int) and len(sentences) != exact_count:
            failures.append(
                (
                    f"Expected {exact_count} sentences, found {len(sentences)}.",
                    "instruction_miss",
                )
            )

        max_words = rules.get("max_words_per_sentence")
        if isinstance(max_words, int):
            for index, sentence in enumerate(sentences, start=1):
                word_count = len(WORD_RE.findall(sentence))
                if word_count > max_words:
                    failures.append(
                        (
                            f"Sentence {index} has {word_count} words; maximum is {max_words}.",
                            "over_answering",
                        )
                    )
                    break

        return failures

    def _has_json_rules(self, rules: dict[str, Any]) -> bool:
        return any(
            rule_name in rules
            for rule_name in (
                "must_be_valid_json",
                "required_keys",
                "no_extra_text",
                "no_extra_keys",
                "indent_spaces",
            )
        )

    def _has_bullet_rules(self, rules: dict[str, Any]) -> bool:
        return any(
            rule_name in rules
            for rule_name in ("exact_bullet_count", "max_words_per_bullet")
        )

    def _has_sentence_rules(self, rules: dict[str, Any]) -> bool:
        return any(
            rule_name in rules
            for rule_name in ("exact_sentence_count", "max_words_per_sentence")
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
