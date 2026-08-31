# August 2026 A2 MLX Compatibility Report

## Decision

**GO** for A3 dataset-schema work and the later A5 LoRA smoke stage.

A2 verified environment, artifact, tokenizer, inference, and MLX-LM LoRA entry
compatibility. No training was performed, and this decision is not evidence of
model quality or successful fine-tuning.

## Environment

| Field | Verified value |
|---|---|
| Machine | Apple M4 Max |
| Architecture | `arm64` |
| macOS | `26.6.2` |
| Python | `3.13.12` |
| MLX | `0.32.2` |
| MLX-LM | `0.31.3` |
| Environment manager | `uv 0.9.30` |

Python 3.13 remained usable. The resolved MLX release supplies a matching
macOS arm64 CPython 3.13 wheel, and the complete compatibility command ran in
the repository environment.

Only `mlx` and `mlx-lm` were added as direct project dependencies. MLX-LM
resolved its required runtime dependencies, including Transformers. PyTorch,
PEFT, TRL, Accelerate, bitsandbytes, and datasets remain absent.

## Pinned Model

| Field | Verified value |
|---|---|
| Repository | `mlx-community/Qwen3-8B-4bit` |
| Revision | `545dc4251c05440727734bcd94334791f6ab0192` |
| Upstream identity | `Qwen/Qwen3-8B` |
| License | `apache-2.0` |
| MLX model type | `qwen3` |
| Quantization | 4 bits, group size 64 |
| Source conversion | MLX-LM `0.24.0` |
| Runtime tested | MLX-LM `0.31.3` |

The repository name is not used as the sole identity. The immutable revision
is recorded in `configs/models/qwen3_8b_mlx_4bit.yaml` and was also the resolved
local snapshot directory identity.

## Artifact Identity

| Artifact | Size | Hugging Face LFS SHA256 | Xet hash |
|---|---:|---|---|
| `model.safetensors` | 4,607,835,174 bytes | `f2d29621aab300336ad645567ff38c42aac755513006ef4e8a579cf7ef5256d8` | `09490e15102da38dc1bae3b089e137ef86c835fe4c4a497c5ecdbe19dd69ce62` |
| `tokenizer.json` | 11,422,654 bytes | `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` | `6aec39639a0a2d1ca966356b8c2b8426a484f80ff80731f44fa8482040713bdf` |

The compatibility script verified the downloaded file sizes against the pinned
metadata. It relies on the immutable Hugging Face revision and published
LFS/Xet identities instead of repeatedly hashing the multi-gigabyte local
weight file.

## Model Load and Inference

- Pinned snapshot download: passed.
- Snapshot revision identity: passed.
- Local artifact presence and size checks: passed.
- MLX-LM model load: passed.
- Loaded model class: `Model`.
- Deterministic short inference: passed.
- Generation configuration: temperature `0.0`, maximum 8 tokens.
- Result: non-empty, 32 characters.

The generated text is intentionally not retained in this report. This check
only establishes that inference executes; it makes no quality claim.

## Tokenizer and Chat Template

The tokenizer loaded as `TokenizerWrapper`. Its active chat template exactly
matched `tokenizer_config.json` from the pinned snapshot. No custom template
was supplied.

The short rendered verification example was:

```text
<|im_start|>user
A2 compatibility check.<|im_end|>
<|im_start|>assistant
```

Verified properties:

- the user role and content are represented correctly;
- `add_generation_prompt=True` adds the assistant generation prompt;
- the loaded template comes from the pinned tokenizer metadata;
- no silent template substitution occurred.

Template SHA256:
`87a2728cb8dc9fe424d624542f6060ec05a1d285ebbec578bb078900e33396b5`.

Rendered example SHA256:
`0aef1a4082ca5dac83cf0f6215c1fc3beeedc250aa41b032e597847b55c27754`.

## LoRA Path Availability

The installed MLX-LM package exposes:

- console command `mlx_lm.lora`, targeting `mlx_lm.lora:main`;
- `mlx_lm.lora.build_parser`;
- `mlx_lm.lora.run`;
- `mlx_lm.lora.train_model`.

This confirms that the required LoRA training entry path is present. It does
not prove that an optimization step, adapter save, or adapter reload succeeds;
those are A5 smoke-stage gates.

## Known Caveats

- The model was converted with MLX-LM `0.24.0` and tested here with MLX-LM
  `0.31.3`. Loading and inference succeeded, but training behavior remains an
  A5 validation item.
- The model weights are quantized. The smoke run must confirm that the current
  MLX-LM LoRA path handles this exact artifact reliably.
- MLX-LM's optional training dependency set was not added in A2. A5 must add
  only dependencies demonstrably required by the local JSONL training path.
- The Open Model Research Harness has no direct MLX `ModelRunner`. Base and
  adapted evaluation-path equivalence remains unresolved for A6/A8.
- The short inference used the tokenizer's default Qwen3 thinking behavior.
  Prompt and thinking controls must be fixed identically for base and adapted
  evaluations.
- The cached model is a local generated artifact and is not tracked by git.

## Verification Scope

The command executed was:

```sh
uv run python scripts/check_mlx_training_compatibility.py \
  --model-config configs/models/qwen3_8b_mlx_4bit.yaml
```

It returned `status: GO` after all required checks. No LoRA adapter, SFT
dataset, training config, checkpoint, or July evaluation result was created or
modified.
