from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Task:
    id: str
    category: str
    prompt: str
    grader: str
    expected_behavior: str
    difficulty: str
    tags: list[str]
    claim_scope: str
    quality_status: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            id=data["id"],
            category=data["category"],
            prompt=data["prompt"],
            grader=data["grader"],
            expected_behavior=data["expected_behavior"],
            difficulty=data["difficulty"],
            tags=list(data["tags"]),
            claim_scope=data["claim_scope"],
            quality_status=data["quality_status"],
        )
