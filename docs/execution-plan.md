# Local-first execution plan

Current revision: **2026-11-08 — independent development and compute workstreams**.
This supersedes the fixed target-month calendars and the original August SFT
handoff as the current execution order. It does not rewrite the frozen July
baseline, prepared datasets, model identities, measured results or evidence gates.
No replacement release date is committed before representative local runs.

## Operating principle

**Develop the next ready component while long local compute runs.** Code,
rubrics, dataset preparation, fixtures, schemas and tests do not wait for an
entire model release or a whole evaluation batch. Actual model/data dependencies
still gate the affected experiment. Scaffolding is not a completed experiment.

There are two separate backlogs, initially managed as a working protocol, not
an installed autonomous scheduler:

| Workstream | Contents | Progress evidence |
|---|---|---|
| Development | Evaluators, graders, adapters, loss masks, datasets, agent tools, trace/replay tests, report code | Tests and reviewed/versioned definitions |
| Compute | Generation, smoke updates, training, checkpoint comparisons, judging and final measurements | Resumable jobs and actual versioned runs |

One GPU production queue serves the projects sharing the worker. Run only one
memory-intensive job there at a time; preempt long jobs at safe boundaries for
short enabling tests rather than starve development. CPU/data preparation may
proceed separately. Queue state never fabricates a scored run.

## Hardware and spending policy

- Use the provided local Apple Silicon worker for all fitting jobs, including
  long training, teacher generation and judging. `gpt-oss:120b` is a local
  candidate reported usable by the owner; record its exact artifact, context,
  memory and throughput instead of assuming fit or impossibility from a label.
- Use the CPU/data host for feasible parsing, indexes, grading, statistics,
  orchestration and backups. Protect the owner's main workstation from required
  sustained production work.
- Default cloud-compute allocation is **zero**. A slow local run is not an
  automatic overflow rental or permission to weaken model/data/eval scope.
- Real CUDA/NCCL or named-device measurements require their actual hardware.
  Keep them pending until separately approved/available; Metal results are not
  NVIDIA validation. No provider account, paid volume or rental is set up by
  this plan.

## Stage map: develop ahead, measure after prerequisites

Stage names and slugs stay independent of dates. Every report retains its
claim boundary, and stages become completed only with evidence.

| Stage | Development can proceed with | Actual compute/report gate |
|---|---|---|
| 1 Foundation + Eval Harness | Completed July implementation | Completed 2026-07-29; frozen artifacts unchanged |
| 2 Eval Suite v2 | Public IFEval/GSM8K/HumanEval/MBPP/XSTest subsets; grader/bootstrap/manifest fixtures | Versioned complete suite, selected base/instruct artifacts, controlled runtime/precision, repeated baseline runs and smoke update |
| 3 SFT + Data Quality | Existing pilot schema/data and tiny smoke fixtures | Exact selected base scored on v2; accepted smoke save/reload; matched SFT/ablation runs and uncertainty |
| 4 Preference Optimization / DPO | Pair schema, rubric, objective/unit tests | Stage 3's chosen SFT checkpoint and valid pairs; base/SFT/DPO runs on the same eval identity |
| 5 Agent Harness / Tool Use | Usable versioned İzci orchestration/trace interfaces; fixture tool calls | Sandboxed file editing/execution/tests and replayable actual traces; no need to wait for İzci V1 as a whole |
| 6 Long-Horizon Agent Evals | Public task subset, failure taxonomy and replay fixtures | Working stage 5 loop and selected variants; actual held-out task attempts |
| 7 Safety / Refusal Quality | Contrast pairs and rubric/grader checks | Real selected checkpoints/agent variants; refusal/over-refusal results with intervals |
| Release 1 | Packaging/docs and dashboard code | Evidence from stages 1–7; dashboards from real runs only |
| 8 Multimodal / UI | Screenshot/OCR/grounding fixtures and metrics | Available identified VLMs and project VLM for real comparisons |
| 9 Data Efficiency / Scaling | Natural-text manifests, curve-fitting and compute-accounting code | One shared training ladder, not duplicate model families; fixed data/model/compute identities |
| 10 Systems Efficiency | Profiling/benchmark interfaces, KV/cache/batching tests | Actual comparable runs on the selected hardware and runtimes |
| 11 Reasoning / Process Eval | Verifiable rewards and process/failure rubrics | Suitable reasoning checkpoints and actual outcomes; no claims about private reasoning access |
| 12 Monitorability | Probe/activation schemas and tiny extraction fixtures | Selected real checkpoints/activations and held-out failure splits |
| 13 Final Integration | Report/reproduction skeleton and package checks | Completed claimed artifacts; unrun local-scale or hardware branches stay explicitly pending |

Eval v2 reuses suitable versioned İzci sets/tooling when available, not an
entire release date. Record source licenses and hashes. If a source subset or
public redistribution is unavailable, prepare the other subsets and keep the
affected run pending; do not claim missing data exists. Internal runs may use
authorized private inputs, but published reproduction claims need obtainable
artifacts or an explicit access limitation.

July is historical context, not the causal control for a different MLX artifact.
Do not reuse its scores as new base measurements. `august_sft_v1` and the old
specification filenames remain immutable artifact names, not execution dates.
The pinned Qwen3-8B MLX work is preparation evidence, not a successful fine-tune.

## Resumable compute protocol

For each requested job, record owner, job ID, input hashes, model/tokenizer/
runtime/precision, complete experiment matrix, output/checkpoint locations,
progress unit, measured throughput/memory, restart point and real prerequisites.
Discussion states are `ready`, `running`, `paused`, `blocked`, `accepted`.
Do not add invented run records merely to represent a future job.

- Training checkpoints contain model/adapter, optimizer, scheduler, completed
  update, RNG, data position and accumulation state (or save at an update boundary).
- Generation/judging persists task IDs, inputs, completed outputs and errors;
  continue pending items instead of silently sampling replacement questions.
- Preload local datasets/models. Test stop/sleep/offline recovery against an
  uninterrupted short run before a long job. Do not assume a process survives
  transport/restart or keep a hot laptop running in a bag.
- Pilot a complete optimizer step and end-to-end generation/update workload;
  runtime includes prefill, references, rejected examples, checkpointing and
  quality checks. Inference support alone is not training compatibility.
- Keep runtime/precision controlled in each comparison. A backend/model change
  creates a recorded identity/caveat, not an invisible performance optimization.

If a full working set or backend is infeasible, document it and continue another
ready development item. Present waiting, unchanged-semantics local techniques,
borrowed hardware or bounded rental as separate choices. Only the owner approves
spending, scope changes or weaker model/data substitutions.

## Current position and next steps

- **Completed evidence:** July foundation and reports; MLX load/generation
  compatibility report. Preserve exact published evidence, not inferred later work.
- **Prepared inputs:** existing versioned SFT pilot referenced by the project;
  verify its actual source revision before use. Do not invent a missing dataset.
- **Next development:** inventory the evaluator/MLX adapter and dataset validators;
  define v2 input identities and resumable generation/checkpoint requirements.
- **Next compute:** verify the actual local worker, selected artifacts and
  complete-step memory; prove smoke update/save/reload and recovery before long
  runs. Production baselines precede production SFT claims.
- **Review:** update current task/evidence/queue state after each accepted artifact.
  Forecast remaining work only from measured throughput and useful availability;
  the old May 2027–August 2028 targets are historical, not overdue obligations.
