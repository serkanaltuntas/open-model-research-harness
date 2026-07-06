from abc import ABC, abstractmethod
from typing import Any, Literal, TypedDict


GraderConfidence = Literal["low", "medium", "high"]


class GraderResult(TypedDict):
    score: float
    passed: bool
    reason: str
    failure_mode: str | None
    grader_confidence: GraderConfidence


class Grader(ABC):
    @abstractmethod
    def grade(self, task: dict[str, Any], output: str) -> GraderResult:
        raise NotImplementedError
