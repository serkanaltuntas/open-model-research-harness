# Task Schema

This document defines the task schema used by Open Model Research Harness.

The purpose of this schema is to make small open-model evaluations reproducible,
comparable, and easy to inspect. The schema is intentionally simple for July 2026
and may evolve after the first evaluation runs.

## Scope

The July 2026 task suite is not a general benchmark. It is a small internal evaluation
set used to validate the harness, grader flow, reporting format, and failure-mode
tracking.

## JSONL Format

Each task is stored as one JSON object per line.

```json
{
  "id": "coding_001",
  "category": "coding",
  "prompt": "Write a Python function named is_prime(n).",
  "grader": "unit_test",
  "expected_behavior": "The function should return true for prime numbers and false otherwise.",
  "difficulty": "easy",
  "tags": ["python", "unit-test", "deterministic"],
  "tests": [
    "assert is_prime(2) is True",
    "assert is_prime(4) is False",
    "assert is_prime(1) is False"
  ],
  "claim_scope": "This task measures basic coding correctness only.",
  "quality_status": "draft"
}
```

## Required Fields

| Field               | Type          | Description                                       |
| ------------------- | ------------- | ------------------------------------------------- |
| `id`                | string        | Stable task identifier.                           |
| `category`          | string        | Task category.                                    |
| `prompt`            | string        | Prompt sent to the model.                         |
| `grader`            | string        | Grader type used to evaluate the output.          |
| `expected_behavior` | string        | Human-readable description of desired behavior.   |
| `difficulty`        | string        | Rough difficulty label.                           |
| `tags`              | array[string] | Search/filter tags.                               |
| `claim_scope`       | string        | What this task can and cannot support as a claim. |
| `quality_status`    | string        | Review status of the task.                        |

## Optional Fields

| Field   | Type          | Description                              |
| ------- | ------------- | ---------------------------------------- |
| `tests` | array[string] | Executable checks for `unit_test` tasks. |
