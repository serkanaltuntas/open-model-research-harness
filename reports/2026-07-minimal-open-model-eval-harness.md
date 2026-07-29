# Open Model Research Harness: July 2026 Milestone Report

## Executive Summary

July 2026 produced a reproducible open-model evaluation harness for the Open
Model Lab. The harness can load a versioned JSONL task suite, run local Ollama
models, automatically select graders, record scored task results, validate run
artifacts, compare multiple runs deterministically, and audit likely grader and
runtime failures.

The completed work is a minimal research harness, not a frontier benchmark or a
production-grade evaluation system. Its results establish a traceable baseline
for this repository's August SFT work, subject to the scope and limitations
documented below.

## July Objective

The July research question was:

> Can three open models be evaluated on the same small task suite with
> reproducible score, latency, token, grader, and failure-mode reporting?

Yes. The final 25-task dataset, shared run configuration, three scored Ollama
runs, validators, deterministic comparison report, and failure audit demonstrate
the complete workflow. The main supporting artifacts are
`datasets/evals/july_eval_v1.jsonl`, `configs/runs/july_final.yaml`, the three
model configurations under `configs/models/`, the local runs under
`results/july_final/`, and the reports under `reports/`.

## Scope and Claim Boundary

- The evaluation suite contains 25 draft tasks.
- Results apply only to this specific suite and do not establish general model
  quality.
- The graders are early deterministic and heuristic implementations. Their
  decisions are reproducible but not necessarily semantically complete.
- Latency and throughput measurements reflect one local runtime environment.
- Recorded API cost is zero for these local runs, but that does not imply zero
  compute or energy cost.
- The failure audit identified likely grader false negatives. These
  interpretations do not replace or modify the recorded grader results.
- No leaderboard or statistically representative benchmark claim is being made.

## Harness Architecture

The implemented evaluation flow is:

```text
dataset
  -> Task schema
  -> model runner
  -> model output
  -> grader registry
  -> grader
  -> scored result
  -> run validator
  -> deterministic comparison report
  -> failure audit
```

Task loading and serialization are defined in `harness/schemas/task.py`. Runner
orchestration and scored-result generation are implemented in
`harness/runners/run_eval.py`. The supported runners are `EchoRunner`, used for
deterministic development checks, and `OllamaRunner`, used for local model
generation, in `harness/runners/echo.py` and `harness/runners/ollama.py`.

The grader registry in `harness/graders/registry.py` maps task grader names to
four implementations: `unit_test`, `exact_match`, `rule_based`, and `rubric`.
Run artifacts are checked by `scripts/validate_run.py`; compatible runs are
aggregated by `harness/reporting/compare_runs.py`; the resulting model comparison
and the separate manual failure audit complete the July analysis chain.

## Evaluation Dataset

The final dataset is `datasets/evals/july_eval_v1.jsonl`. It contains 25 tasks,
with exactly five tasks in each category:

| Category | Tasks | Grader |
|---|---:|---|
| `coding` | 5 | `unit_test` |
| `reasoning` | 5 | `rubric` |
| `factuality` | 5 | `exact_match` |
| `instruction_following` | 5 | `rule_based` |
| `safety_lite` | 5 | `rubric` |

Each task carries grader-specific metadata such as tests, accepted answers,
rules, or rubric criteria. All 25 tasks have `quality_status: draft`. This small,
balanced suite is useful for diagnostic comparison, but it is not statistically
representative of model capability in general.

## Runner and Model Configuration

The final evaluation recorded these local model artifacts exactly:

| Report name | Ollama model | Ollama ID |
|---|---|---|
| `lfm2.5-8b` | `lfm2.5:8b` | `9cf756159fc2` |
| `gpt-oss` | `gpt-oss:latest` | `17052f91a42e` |
| `qwen3.6` | `qwen3.6:latest` | `07d35212591f` |

The shared configuration in `configs/runs/july_final.yaml` and each run's
`run.json` was:

- Dataset: `datasets/evals/july_eval_v1.jsonl`
- Temperature: `0.0`
- Maximum output tokens: `1024`
- Seed: `42`
- Timeout: `300` seconds

No parameter count or quantization format is inferred. The recorded Ollama ID
identifies the local artifact used for the run even where the model reference
uses a mutable `latest` tag.

## Grader Design

- `UnitTestGrader` executes deterministic tests for coding tasks.
- `ExactMatchGrader` normalizes short responses and compares them with accepted
  factual answers.
- `RuleBasedGrader` checks explicit formatting and instruction-following rules.
- `RubricGrader` applies weighted textual criteria to reasoning and safety-lite
  responses.

`get_grader()` in `harness/graders/registry.py` selects the implementation from
the task's grader name. Grading occurs per task after model generation. A grader
exception is recorded as a task-level `grader_error`, allowing later tasks in the
same run to continue. This design is deterministic, but its literal checks and
code extraction are not semantically complete.

## Validation and Reproducibility

`scripts/validate_dataset.py` verifies JSONL structure, task count, category
distribution, identifiers, supported grader pairings, and grader-specific
metadata. `scripts/validate_run.py` verifies scored-result structure, count,
identifiers, score ranges, pass states, confidence values, and failure modes.

The automated test suite covers schemas, configuration loading, graders, runner
integration, validators, and comparison reporting. The comparison implementation
checks shared dataset and run configuration, matching task sets, prompt hashes,
and result schema before aggregating runs. Its JSON and Markdown output is
deterministic for unchanged inputs.

Local generated results remain excluded from version control where repository
policy requires it. Reproducible tracked inputs and reports are kept separately
from the local model-output artifacts.

## Final Model Runs

Three models completed the same 25-task suite. Each run contains 25 scored
results, for 75 scored result rows in total. The final runs recorded zero grader
errors.

The source run directories are:

- `results/july_final/lfm2_5_8b/`
- `results/july_final/gpt_oss/`
- `results/july_final/qwen3_6/`

## Results

The recorded overall results are:

| Model | Passed | Failed | Pass rate | Mean score |
|---|---:|---:|---:|---:|
| `lfm2.5-8b` | 12 | 13 | 48.0% | 0.452 |
| `gpt-oss` | 23 | 2 | 92.0% | 0.920 |
| `qwen3.6` | 12 | 13 | 48.0% | 0.540 |

Within this specific 25-task July suite, gpt-oss recorded the highest pass rate.
This is a suite-specific observation, not a general model ranking.

Category results show different failure profiles. LFM passed all five reasoning
and all five safety-lite tasks, but none of the factuality or
instruction-following tasks; its visible think blocks strongly affected strict
format checks. GPT-OSS passed all coding, factuality, and reasoning tasks and four
of five tasks in each of instruction following and safety-lite. Qwen passed all
five factuality tasks, three of five instruction-following tasks, three of five
safety-lite tasks, one reasoning task, and no coding tasks under the recorded
1024-token configuration.

These are the original grader outcomes. The audit interpretations below explain
likely causes but do not retroactively change any score or pass state.

## Failure Audit Findings

The failure audit reviewed all 28 initially failed result rows. Its primary
labels classified 11 as likely format or instruction failures, 7 as likely
grader false negatives, 10 as truncation or runtime related, 0 as ambiguous
cases requiring manual review, and 0 as likely substantive model failures.

Important findings include:

- LFM outputs included visible think blocks. These violated strict answer
  formats and produced three likely code-extraction false negatives where usable
  code followed the think block.
- One GPT-OSS JSON response contained the correct object inside a Markdown code
  fence, violating the bare-JSON requirement.
- One GPT-OSS safety response was likely missed by literal rubric matching,
  including sensitivity to the apostrophe form in `can't`.
- Ten Qwen failures reached the fixed 1024-token limit.
- In several Qwen cases, generated content remained in Ollama thinking metadata
  while the final output was empty or incomplete.

The recorded results remain authoritative for the July run artifacts. The audit
is a separate diagnostic interpretation and does not rewrite them.

## Known Limitations

- The suite is small, contains only draft tasks, and is not representative.
- Deterministic graders are narrow and sensitive to exact or literal matching.
- Code extraction does not fully handle think-prefixed responses.
- Models expose or retain thinking output differently.
- The fixed 1024-token limit materially affected Qwen results.
- Runtime measurements come from one local machine and environment.
- No repeated-run variance analysis was performed.
- No human evaluation panel was used.
- No statistical significance claim can be made.
- Ollama tags may be mutable; recorded local IDs mitigate, but do not eliminate,
  artifact-provenance risk.

## July Completion Criteria

- [x] Versioned task suite
- [x] 25 tasks
- [x] Five categories
- [x] Local model runner
- [x] Automated grader selection
- [x] Scored results
- [x] Run validation
- [x] Three comparable model runs
- [x] Deterministic comparison
- [x] Failure audit
- [x] Reproducible configurations
- [x] Explicit claim boundary
- [ ] Frozen release baseline

The frozen release baseline is intentionally not marked complete. It belongs to
the next packaging step rather than this July implementation report.

## August Handoff

August work will focus on supervised fine-tuning (SFT) and data quality. The
July suite and three final runs provide a diagnostic baseline for measuring
behavior changes after SFT, category-level improvements, regressions,
format-following changes, and grader limitations that must remain visible.

The July results should not be silently corrected before the baseline freeze.
Grader improvements may be developed later, but any changed grader or dataset
version must be evaluated separately and identified explicitly rather than used
to rewrite the frozen July result.

## Source Artifacts

- Final dataset: `datasets/evals/july_eval_v1.jsonl`
- Model configurations: `configs/models/lfm2_5_8b.yaml`,
  `configs/models/gpt_oss.yaml`, `configs/models/qwen3_6.yaml`
- Shared run configuration: `configs/runs/july_final.yaml`
- Dataset validator: `scripts/validate_dataset.py`
- Run validator: `scripts/validate_run.py`
- Reporting implementation: `harness/reporting/compare_runs.py`
- Model comparison: `reports/2026-07-model-comparison.md`
- Failure audit: `reports/2026-07-failure-audit.md`
- Local LFM run: `results/july_final/lfm2_5_8b/`
- Local GPT-OSS run: `results/july_final/gpt_oss/`
- Local Qwen run: `results/july_final/qwen3_6/`
- Local deterministic comparison data: `results/july_final/comparison.json`
