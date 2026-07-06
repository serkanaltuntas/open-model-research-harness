import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from harness.graders.base import Grader, GraderResult


FENCED_CODE_RE = re.compile(
    r"```(?P<lang>[A-Za-z0-9_-]*)\s*\n(?P<code>.*?)```",
    re.DOTALL,
)
FORMAT_FAILURE_MARKERS = ("SyntaxError", "IndentationError", "TabError")


class UnitTestGrader(Grader):
    def __init__(
        self,
        timeout_seconds: float = 5.0,
        python_executable: str = sys.executable,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.python_executable = python_executable

    def grade(self, task: dict[str, Any], output: str) -> GraderResult:
        if task.get("category") != "coding":
            return self._result(
                score=0.0,
                passed=False,
                reason="UnitTestGrader only supports coding tasks.",
                failure_mode="grader_error",
            )

        tests = self._task_tests(task)
        if not tests:
            return self._result(
                score=0.0,
                passed=False,
                reason="No unit tests found for task.",
                failure_mode="grader_error",
            )

        candidate_code = self._extract_python_code(output)
        if not candidate_code:
            return self._result(
                score=0.0,
                passed=False,
                reason="Generated code failed to execute.",
                failure_mode="format_failure",
            )

        with tempfile.TemporaryDirectory(prefix="omh-unit-test-") as tmp_dir:
            script_path = Path(tmp_dir) / "candidate_test.py"
            script_path.write_text(
                f"{candidate_code}\n\n{tests}\n",
                encoding="utf-8",
            )

            try:
                completed = subprocess.run(
                    [self.python_executable, "-I", str(script_path)],
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return self._result(
                    score=0.0,
                    passed=False,
                    reason="Execution timed out.",
                    failure_mode="timeout",
                )

        if completed.returncode == 0:
            return self._result(
                score=1.0,
                passed=True,
                reason="All tests passed.",
                failure_mode=None,
            )

        if self._is_format_failure(completed):
            return self._result(
                score=0.0,
                passed=False,
                reason="Generated code failed to execute.",
                failure_mode="format_failure",
            )

        return self._result(
            score=0.0,
            passed=False,
            reason="One or more tests failed.",
            failure_mode="test_failure",
        )

    def _task_tests(self, task: dict[str, Any]) -> str:
        tests = task.get("tests")
        if isinstance(tests, str):
            return tests.strip()
        if isinstance(tests, list):
            return "\n".join(test.strip() for test in tests if test.strip())
        return ""

    def _extract_python_code(self, output: str) -> str:
        matches = list(FENCED_CODE_RE.finditer(output))

        for match in matches:
            if match.group("lang").lower() in {"python", "py"}:
                return match.group("code").strip()

        for match in matches:
            if not match.group("lang").strip():
                return match.group("code").strip()

        return output.strip()

    def _is_format_failure(
        self,
        completed: subprocess.CompletedProcess[str],
    ) -> bool:
        stderr = completed.stderr or ""
        return any(marker in stderr for marker in FORMAT_FAILURE_MARKERS)

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
