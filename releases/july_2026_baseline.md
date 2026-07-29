# July 2026 Evaluation Baseline

## Baseline Identity

This document freezes the July 2026 evaluation baseline for the Open Model
Research Harness and its public Open Model Lab section. The machine-readable
definition is `releases/july_2026_manifest.json`.

- Git commit: `0b6a236ee1f1440a7aca6d84249fd6af0b582c0d`
- Dataset: `datasets/evals/july_eval_v1.jsonl`
- Dataset SHA256:
  `38c646401b74f92deac04c5e225dfeabd822f72c3e30ce52dfaa24d817375760`
- Dataset size: 25 tasks
- Final runs: 3 local Ollama runs, 25 scored results each
- Total scored results: 75

No git tag is created by this baseline package. The commit and content hashes in
the manifest provide the repository and artifact identity.

## What Is Frozen

The baseline consists of the exact dataset content, three model configurations,
shared run configuration, registered grader implementations, validator and
comparison implementations, three final local run identities, and the published
comparison, failure audit, and milestone report listed in the manifest.

The recorded scores, pass states, failure modes, latency and token measurements,
and raw model outputs in the expected local run directories are historical July
results. The failure audit is an interpretation layer; it does not replace or
correct those recorded results.

The local run directories are expected at:

- `results/july_final/lfm2_5_8b`
- `results/july_final/gpt_oss`
- `results/july_final/qwen3_6`

These local artifacts may be excluded from git by repository policy. Their run
IDs, expected result counts, model identities, configurations, and related
tracked reports are recorded in the manifest.

## Why It Is Frozen

Freezing the baseline establishes a stable point of comparison before August
SFT and data-quality work begins. It prevents later grader, dataset, extraction,
or runtime improvements from silently changing the meaning of the July results.
It also preserves known imperfections, including likely grader false negatives
and token-limit effects, so future comparisons remain honest and reproducible.

The baseline is diagnostic and applies only to the 25-task July suite. It is not
a general model ranking, a statistically representative benchmark, or a
production-grade evaluation claim.

## Future Comparison Policy

Future experiments must identify this baseline explicitly and compare new
results against the recorded July artifacts without overwriting them. A valid
comparison should disclose changes to the model artifact, dataset, grader,
runner, generation settings, runtime environment, or reporting logic.

When the dataset and grading contract remain unchanged, task-level and
category-level changes can be compared directly while retaining the July claim
boundary. When any frozen input or interpretation changes, the new run must use
a distinct run ID and preserve the original July result. Regrading must produce
a separate artifact rather than rewriting July `results.jsonl` files.

Content hashes and Ollama IDs should be checked before claiming exact baseline
compatibility. Mutable model tags such as `latest` are not sufficient by
themselves; the recorded local Ollama IDs identify the evaluated artifacts.

## Changes Requiring a New Baseline

A new baseline is required for any change that alters evaluation meaning or
reproducibility, including:

- changing, adding, removing, or reclassifying dataset tasks;
- changing accepted answers, tests, rules, rubrics, or task quality status;
- changing grader behavior, registry mappings, or output extraction;
- changing runner behavior that affects prompts, outputs, tokens, or timing;
- changing temperature, maximum tokens, seed, timeout, or backend;
- replacing a model artifact or using a different Ollama ID;
- changing scored-result semantics, validation rules, or comparison aggregation;
- correcting or regenerating any final July result artifact.

Documentation that only clarifies the existing baseline without changing its
meaning may reference this baseline, but must not modify the manifest's frozen
artifact identities.

## Validation Record

The baseline manifest records the dataset validator at
`scripts/validate_dataset.py`, the run validator at `scripts/validate_run.py`,
and the deterministic comparison implementation at
`harness/reporting/compare_runs.py`. At freeze time, the repository automated
test suite contains 40 tests.

The three final runs contain 75 scored results in total and record zero grader
errors. Their recorded outcomes remain unchanged by this release documentation.

## Known Limitations

The frozen baseline retains the limitations documented in the July milestone
report: a small draft suite, narrow deterministic graders, literal matching and
code-extraction sensitivity, model-specific thinking-output behavior, a fixed
1024-token limit that affected qwen3.6, one local runtime environment, no
repeated-run variance analysis, no human evaluation panel, and no statistical
significance claim. Zero recorded API cost does not mean zero local compute or
energy cost.

## August 2026 Begins From This Baseline

August 2026 SFT and data-quality work begins from this frozen July baseline.
Behavior changes, category improvements, regressions, format-following changes,
and known grader limitations should be measured against it. Improvements may be
introduced in new versioned evaluations, but the July inputs and recorded results
must remain intact.

## Baseline Artifacts

- Manifest: `releases/july_2026_manifest.json`
- Final dataset: `datasets/evals/july_eval_v1.jsonl`
- Model configurations: `configs/models/lfm2_5_8b.yaml`,
  `configs/models/gpt_oss.yaml`, `configs/models/qwen3_6.yaml`
- Shared run configuration: `configs/runs/july_final.yaml`
- Model comparison: `reports/2026-07-model-comparison.md`
- Failure audit: `reports/2026-07-failure-audit.md`
- July milestone report: `reports/2026-07-minimal-open-model-eval-harness.md`
