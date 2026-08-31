# August 2026 SFT Experiment Specification

## 1. Objective

The August 2026 research question is:

> Can supervised fine-tuning improve selected measurable behaviors of an open
> model while preserving visibility into regressions?

July 2026 answered:

> Can model behavior be measured reproducibly?

August 2026 asks:

> Can model behavior be deliberately changed and measured against a frozen
> baseline?

This specification defines the experiment before training dependencies,
training data, model artifacts, adapters, or checkpoints are created. The work
combines supervised fine-tuning (SFT) with explicit data-quality controls and
uses the frozen July evaluation system as its diagnostic measurement baseline.

## 2. Frozen July Baseline

The July 2026 baseline is defined by:

- `releases/july_2026_manifest.json`
- `releases/july_2026_baseline.md`
- `datasets/evals/july_eval_v1.jsonl`
- `reports/2026-07-minimal-open-model-eval-harness.md`
- `reports/2026-07-model-comparison.md`
- `reports/2026-07-failure-audit.md`

The following controls are mandatory:

- The July dataset must not be modified for an August comparison.
- July grader behavior must not be silently changed.
- July recorded results must not be overwritten.
- August runs must use new run IDs and result directories.
- Any grader or dataset improvement requires a new version rather than a
  rewrite of the July baseline.

The July three-model results remain historical context. They are not the causal
pre-SFT control for the newly selected trainable model.

## 3. Base Model Decision

The initial August setup is:

| Field | Decision |
|---|---|
| Base model | `mlx-community/Qwen3-8B-4bit` |
| Model family | Qwen3-8B |
| Backend | MLX-LM |
| Training method | LoRA supervised fine-tuning |
| Target machine | Apple Silicon M4 Max |

Qwen3-8B is selected because it is a newer model generation than Qwen2.5, is a
manageable size for repeated local experimentation, is practical for the
available Apple Silicon system, has MLX ecosystem support, and offers a better
balance between model freshness and training-stack maturity than immediately
moving to a less proven newest-generation model. It is also small enough for
local smoke tests and repeated experiments.

Before the first smoke run, A2 must verify and record:

- the exact Hugging Face repository;
- an immutable revision or commit hash;
- the upstream model identity;
- the applicable license;
- the tokenizer identity and revision;
- the chat template and how it is applied;
- compatibility with the pinned MLX-LM version;
- LoRA training support for the model architecture;
- quantization metadata and its training implications;
- a reproducible local artifact identity.

None of these unresolved values is inferred by this specification. The model
decision may be revisited only if smoke-stage verification demonstrates a
concrete incompatibility. Such a failure must be documented before another
model is selected.

## 4. Experimental Hypotheses

**Primary hypothesis:** A small, curated SFT dataset focused on instruction
adherence, structured output, concise factual responses, and simple reasoning
response format will produce measurable improvements in corresponding
evaluation behaviors relative to the exact same unmodified base-model artifact.

**Secondary hypothesis:** SFT may introduce regressions in unrelated
capabilities, and those regressions must remain visible.

**Null result:** No measurable improvement, or an overall regression, remains a
valid research result when the experiment is reproducible and reported within
its claim boundary.

## 5. Target Behaviors

The first SFT experiment primarily targets:

- instruction following;
- structured output;
- concise factual answers;
- simple reasoning response discipline.

Coding and safety-lite are not primary training targets in the first
experiment. They remain primarily regression-monitoring categories.

Training data must not contain July evaluation prompts or trivial paraphrases
constructed around July answers. Targeting the same behavior is allowed;
targeting the held-out item content is not.

## 6. Experimental Controls

### Independent Variable

- LoRA SFT applied versus not applied.

### Main Comparison

The comparison is between:

```text
exact Qwen3-8B MLX base artifact
```

and:

```text
the same base artifact + the August LoRA adapter
```

### Controlled Factors

- exact base-model revision;
- tokenizer;
- chat template;
- evaluation dataset;
- evaluation graders;
- evaluation harness;
- evaluation generation configuration where technically possible;
- prompt construction;
- model-loading path where technically possible.

Any factor that cannot remain equivalent must be recorded as a comparability
caveat before results are interpreted.

### Dependent Measurements

- overall pass rate;
- category pass rate;
- category mean score;
- failure-mode distribution;
- output length;
- regression count;
- targeted-behavior improvement count;
- latency only when inference paths are sufficiently comparable.

## 7. Critical Base Evaluation Requirement

The exact trainable Qwen3-8B MLX base artifact must be evaluated before SFT.
The existing July `qwen3.6` Ollama result must not be used as the causal pre-SFT
baseline because it is not the same model artifact or inference path.

The main August causal comparison is:

```text
Qwen3-8B MLX base artifact
        -> unchanged July frozen evaluation

same Qwen3-8B MLX base artifact + August LoRA adapter
        -> same unchanged July frozen evaluation
```

The old July three-model comparison remains useful context only. The new base
and adapted runs require distinct August run IDs and result directories.

## 8. SFT Dataset Requirements

The August SFT dataset must:

- remain completely separate from July evaluation data;
- contain no July prompts;
- contain no trivial paraphrases designed around July answers;
- record example provenance;
- use a versioned JSONL format;
- support deterministic validation;
- apply the intended Qwen3 chat template correctly;
- distinguish user and assistant content;
- define deterministic train and validation splits;
- identify every example as `human-written`, `public-source`, `synthetic`, or
  `transformed`;
- support contamination checks against `datasets/evals/july_eval_v1.jsonl`.

The initial real-dataset target is approximately 200-500 high-quality examples.
The smoke subset is approximately 20-50 examples. Neither dataset is created by
this specification package.

Dataset provenance must include enough information to establish redistribution
and training rights. Public-source and transformed examples must retain source
and license metadata; synthetic examples must record their generation and review
provenance.

## 9. Data Quality Principle

August is both an SFT implementation milestone and a data-quality investigation.
It tests the proposition that training-example quality matters independently of
training quantity.

A later controlled comparison should use the same base model and approximately
equal training budget while varying a documented data-quality condition. That
comparison is planned but is not implemented in this package. Dataset size alone
must not be treated as a proxy for quality.

## 10. Smoke Training Stage

Before a real SFT run, a smoke experiment must use approximately:

- 20-50 training examples;
- very few optimization steps;
- one LoRA adapter.

Smoke success requires all of the following:

- the exact model artifact loads;
- the dataset loads;
- chat formatting is correct and inspectable;
- training loss remains finite;
- at least one backward/update step completes;
- the adapter is written;
- the adapter can be reloaded onto the same base artifact;
- at least one inference output can be generated after reload.

Smoke success validates plumbing only. It does not mean model quality improved
and must not be reported as an evaluation result.

## 11. Real SFT Configuration

The real training configuration must eventually version at least:

- exact base-model repository;
- exact base-model revision;
- dataset version;
- dataset SHA256;
- train/validation split definition;
- LoRA rank;
- LoRA alpha, if applicable;
- target modules;
- learning rate;
- batch size;
- gradient accumulation;
- epochs or maximum steps;
- random seed;
- maximum sequence length;
- validation cadence;
- checkpoint policy;
- adapter output path;
- MLX and MLX-LM versions;
- Python version;
- machine and backend metadata.

This specification does not choose final hyperparameters. The implementation
package must select conservative defaults and document the source or rationale
for each choice. Smoke settings and real-run settings must be separately
identified.

## 12. Evaluation Path

Both the base and SFT artifacts must be evaluated through the Open Model
Research Harness using the most equivalent inference path possible.

If the trained model must be exported or imported into Ollama, that conversion
must be versioned and documented. It must not silently change prompt formatting,
generation behavior, quantization, tokenizer behavior, or adapter application.

If direct MLX evaluation is required, a dedicated `ModelRunner` must later be
implemented explicitly. `OllamaRunner` must not be made to represent an MLX
backend. The evaluation adapter and any new runner are outside this package.

Regardless of path, the base and adapted artifacts must share prompt
construction, generation controls, and model-loading behavior wherever
technically possible. Latency comparisons are permitted only when the paths are
sufficiently comparable.

## 13. Success Criteria

### Infrastructure Success

- The exact model artifact is pinned.
- The training environment is reproducible.
- The SFT dataset validates.
- The contamination check passes.
- Smoke training completes.
- The adapter saves.
- The adapter reloads.
- Inference succeeds.
- Base and SFT artifacts can both be evaluated.

### Research Success

- A valid base-versus-SFT comparison exists.
- At least one target behavior changes measurably.
- Improvements and regressions are both reported.
- Failures are audited.
- Claims remain restricted to the experiment.

The experiment remains successful as research even when SFT makes the model
worse. Reproducible negative evidence is an acceptable result.

## 14. Stop and Investigation Conditions

Stop the current stage and investigate if:

- training loss becomes NaN or Inf;
- MLX-LM cannot train this model reliably;
- the adapter cannot be reloaded;
- the base revision cannot be pinned;
- a tokenizer or chat-template mismatch exists;
- training data overlaps the July evaluation set;
- base and SFT evaluation paths are materially incomparable;
- training mutates the base artifact;
- output quality collapses unexpectedly;
- the architecture requires unsupported MLX training behavior.

If Qwen3-8B is technically unsuitable during smoke validation, record the exact
failure, environment, and attempted configuration before selecting another
model. Do not reinterpret an infrastructure failure as a model-quality result.

## 15. Expected Future August Artifacts

The following artifacts are planned but are not created by this specification:

```text
configs/training/august_sft_smoke.yaml
configs/training/august_sft_v1.yaml

datasets/sft/august_sft_v1.jsonl

docs/training_schema.md

harness/training/
scripts/validate_training_dataset.py

tests/training/

reports/2026-08-sft-comparison.md
reports/2026-08-data-quality.md
reports/2026-08-final-report.md

releases/august_2026_manifest.json
```

Large checkpoints, adapters, downloaded model files, caches, and generated
training artifacts must remain local and uncommitted unless repository policy
explicitly states otherwise. Tracked metadata must identify them reproducibly
without placing the large artifacts in git.

## 16. August Package Sequence

1. **A1 - Experiment specification:** define the research design, controls,
   boundaries, stage gates, and expected artifacts.
2. **A2 - MLX training environment and model compatibility verification:** pin
   the environment and exact model artifact, then verify licensing, loading,
   chat formatting, quantization, and LoRA support.
3. **A3 - SFT dataset schema and validator:** define provenance, messages,
   splits, validation, and contamination rules.
4. **A4 - Initial curated SFT dataset:** create and review versioned training
   examples without using July evaluation content.
5. **A5 - LoRA smoke training:** validate the complete minimal training,
   adapter-save, reload, and inference path.
6. **A6 - Exact base-model evaluation:** evaluate the pinned trainable artifact
   against the unchanged July suite before SFT.
7. **A7 - First real SFT run:** train one versioned adapter with a documented
   configuration and data artifact.
8. **A8 - Post-SFT evaluation:** evaluate the adapted artifact using the same
   frozen suite and comparable inference path.
9. **A9 - Base-versus-SFT regression and failure analysis:** report gains,
   regressions, grader effects, and root-cause hypotheses separately.
10. **A10 - Data-quality controlled experiment:** compare data-quality
    conditions under approximately equal training budgets.
11. **A11 - August final report and frozen release manifest:** document claims,
    limitations, hashes, artifacts, and the next immutable baseline.

Each package must satisfy its validation and stop conditions before the next
package depends on it.

## 17. July Knowledge Reinforcement

August work revisits July concepts in the context of a real intervention:

- **Frozen baseline:** historical inputs and results remain immutable while new
  runs receive new identities.
- **Evaluation versus benchmark:** the July suite diagnoses selected behaviors;
  it does not establish general capability.
- **Contamination:** training and held-out evaluation content must remain
  meaningfully separate.
- **Grader limitations:** deterministic grader behavior is reproducible but may
  not be semantically complete.
- **Failure mode versus root cause:** a recorded grader label and a later audit
  interpretation are distinct evidence layers.
- **Reproducibility:** model, data, environment, configuration, and artifacts
  require stable identities.
- **Claim boundaries:** conclusions apply only to measured behaviors under the
  documented setup.
- **Release manifests:** hashes and provenance define what constitutes a frozen
  experimental baseline.

These concepts are reinforced during August packages rather than deferred to a
separate review period.

## 18. Claim Boundary

- This experiment does not aim to create a generally superior model.
- This is not a frontier-model training claim.
- The July suite is small and diagnostic.
- Measured improvements apply only to the evaluated behaviors.
- Regression is a valid outcome.
- No broad conclusion about Qwen3 capability may be derived from this
  experiment.

Any result must identify the exact base artifact, adapter, training data,
training configuration, evaluation path, and comparability caveats. Claims must
distinguish recorded measurements from failure-audit interpretations and must
not extend beyond this experiment.

## Unresolved Design Questions

The following questions belong to subsequent packages and must be resolved with
recorded evidence rather than assumptions:

- Which immutable revision of `mlx-community/Qwen3-8B-4bit` will be pinned?
- What upstream model, license, tokenizer revision, chat template, and
  quantization metadata apply to that artifact?
- Which Python, MLX, and MLX-LM versions form the compatible environment?
- Does MLX-LM support LoRA training for this exact quantized architecture and
  which target modules are valid?
- What training-example schema best preserves provenance and exact rendered
  chat text for deterministic validation?
- What similarity methods and review thresholds are sufficient for July
  contamination detection?
- Can both artifacts use a direct MLX evaluation runner, or is a documented
  export/import step required?
- Which conservative smoke and real-run hyperparameters are supported by the
  selected toolchain and available memory?
