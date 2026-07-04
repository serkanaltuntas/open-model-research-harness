# Run Schema

This document defines the metadata and result schema for evaluation runs.

The goal is to make every run inspectable and reproducible enough for later comparison.

## Run Metadata

Each evaluation run should include a `run.json` file.

```json
{
  "run_id": "2026-07-final-model-a",
  "project": "Open Model Research Harness",
  "lab_section": "Open Model Lab",
  "month_gate": "2026-07-foundation-eval-harness",
  "model": {
    "name": "model-a",
    "provider": "local",
    "version": "unknown",
    "params": "unknown",
    "quantization": "none"
  },
  "dataset": {
    "name": "july_eval_v1",
    "version": "v1",
    "task_count": 25
  },
  "config": {
    "temperature": 0.2,
    "max_tokens": 512,
    "seed": 42
  },
  "started_at": "2026-07-xxT20:00:00+03:00",
  "finished_at": "2026-07-xxT20:15:00+03:00"
}
```

## Per-Task Result

Each task result should be stored as one JSON object per line.

```json
{
  "run_id": "2026-07-final-model-a",
  "task_id": "reasoning_003",
  "category": "reasoning",
  "model": "model-a",
  "prompt_hash": "sha256...",
  "output_hash": "sha256...",
  "output": "...",
  "score": 0.4,
  "passed": false,
  "grader": "llm_as_judge",
  "grader_confidence": "medium",
  "failure_mode": "incomplete_answer",
  "latency_ms": 2100,
  "input_tokens": 140,
  "output_tokens": 220,
  "cost_estimate": 0.0004,
  "caveats": ["Missing one required detail."]
}
```

| Field           | Description                                |
| --------------- | ------------------------------------------ |
| `run_id`        | Stable run identifier.                     |
| `task_id`       | Task identifier from the eval dataset.     |
| `category`      | Task category.                             |
| `model`         | Model name used for this result.           |
| `output`        | Raw model output.                          |
| `score`         | Numeric score between 0 and 1.             |
| `passed`        | Boolean pass/fail value.                   |
| `grader`        | Grader used for scoring.                   |
| `failure_mode`  | Controlled failure-mode label or null.     |
| `latency_ms`    | Measured latency in milliseconds.          |
| `input_tokens`  | Prompt token count if available.           |
| `output_tokens` | Output token count if available.           |
| `cost_estimate` | Estimated API cost or local runtime proxy. |
| `caveats`       | Known caveats for this result.             |

## Notes

Local cost estimates are approximate.
Some model backends may not support deterministic seeds.
LLM-as-judge scores are diagnostic unless validated manually.
Raw outputs should be preserved for inspection.
