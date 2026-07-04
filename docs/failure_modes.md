# Failure Modes

This document defines the controlled failure-mode vocabulary used by Open Model Research
Harness.

Failure modes are diagnostic labels. They are not final explanations of model behavior.

## Initial Vocabulary

| Failure Mode | Description |
|---|---|
| `hallucination` | The model invents unsupported facts or details. |
| `wrong_reasoning` | The model reaches an invalid conclusion or uses faulty reasoning. |
| `instruction_miss` | The model fails to follow an explicit instruction. |
| `format_failure` | The model fails to produce the requested format. |
| `over_answering` | The model gives more than requested or violates brevity constraints. |
| `unsafe_answer` | The model gives an unsafe response in a safety-lite task. |
| `judge_uncertainty` | The grader cannot confidently determine correctness. |
| `looping` | The model repeats itself or gets stuck in a loop. |
| `premature_success` | The model claims success before satisfying the task. |
| `context_loss` | The model loses or ignores important context. |
| `tool_misuse` | The model misuses an available tool. |
| `over_refusal` | The model refuses a harmless request. |
| `under_refusal` | The model complies with a request it should safely refuse. |
| `factuality_drift` | The answer drifts away from factual accuracy over time. |
| `style_collapse` | The model loses the requested style or structure. |
| `incomplete_answer` | The model gives a partial answer. |
| `test_failure` | Generated code fails one or more tests. |
| `timeout` | Evaluation or generated code times out. |
| `grader_error` | The grader fails or returns an invalid result. |

## July 2026 Notes

The July 2026 suite mainly uses:

- `test_failure`
- `wrong_reasoning`
- `hallucination`
- `instruction_miss`
- `format_failure`
- `incomplete_answer`
- `judge_uncertainty`
- `over_refusal`
- `under_refusal`

Agent-specific labels such as `tool_misuse`, `looping`, and `premature_success` are
included for future months but may not appear in July results.

## Usage Rule

Each failed task should receive at most one primary failure mode in July 2026.
Secondary labels can be added later if the reporting format needs them.
