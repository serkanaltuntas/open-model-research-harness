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
    tests: list[str] | None = None
    rules: dict[str, object] | None = None
    rubric: dict[str, object] | None = None
    accepted_answers: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "prompt": self.prompt,
            "grader": self.grader,
            "expected_behavior": self.expected_behavior,
            "difficulty": self.difficulty,
            "tags": list(self.tags),
            "claim_scope": self.claim_scope,
            "quality_status": self.quality_status,
            "tests": self.tests,
            "rules": self.rules,
            "rubric": self.rubric,
            "accepted_answers": self.accepted_answers,
        }

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
            tests=data.get("tests"),
            rules=data.get("rules"),
            rubric=data.get("rubric"),
            accepted_answers=data.get("accepted_answers"),
        )
