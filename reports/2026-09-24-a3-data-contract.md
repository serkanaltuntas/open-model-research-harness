# A3 SFT data contract — verification, 24 September 2026

**Result: A3 verified; ready for A4 curated data preparation.** The schema,
cross-file validator, frozen-July overlap checks and completion-only token
encoding are implemented. This is software/data-contract evidence, not a
training result or a model-quality claim.

## Source and environment

- Started from clean `main`, `471a38a36ca7dea869c3631c20bca675ca771d26`.
  Implementation branch: `feat/a3-sft-data-contract`; no pre-existing user diff.
- Linux x86_64 CPU; Python 3.12.14 (already installed), Transformers 5.16.1,
  tokenizers 0.23.1, Jinja2 3.1.6. No Mac/GPU training run.
- `uv sync --locked` succeeds with MLX dependencies selected only on Apple
  Silicon macOS. All locked package versions are unchanged; dependency markers
  and direct tokenizer/template dependencies changed. The existing A2 fake test
  now mocks OS/package metadata as well as its fake model runtime.
- Exact tokenizer revision, five file hashes and A2 template identity are in
  [the manifest](../configs/training/sft_tokenizer_v1.json). Tokenizer SHA256 is
  `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4`;
  native template SHA256 is
  `87a2728cb8dc9fe424d624542f6060ec05a1d285ebbec578bb078900e33396b5`.

## Acceptance evidence

All final commands below exited **0**:

| Check | Observed result |
| --- | --- |
| `uv run python -m compileall -q harness scripts` | Passed |
| `HF_HUB_OFFLINE=1 uv run python -m pytest -q` | 95 passed, 16 explicit real-tokenizer tests skipped |
| Same suite with `A3_TOKENIZER_SNAPSHOT` and `HF_HUB_OFFLINE=1` | **111 passed**, including all 16 real-tokenizer cases |
| CLI on three test fixtures, real pinned tokenizer, `--max-length 512` | `DATA_VALID`; 2 train / 1 validation; 111 sequence tokens, 35 loss tokens, longest sequence 46 |
| SHA256 audit of frozen July manifest paths | All **16** tracked file hashes match |
| Changed Python files: Ruff check; `git diff --check` | Passed |

The CLI fixtures have **three unreviewed** declarations; neither the run nor this
report claims a human-accepted dataset. The test maximum 512 is not a selected
SFT training hyperparameter.

Unit tests cover invalid schema/provenance/review, duplicate JSON keys and IDs,
cross-file duplicates, source-group split leakage, normalized eval prompts in
both message roles, empty targets, chat markers, causal shifting, padding with
EOS-as-pad, overflows, unsafe token boundaries and lossy decode. Real-file tests
cover Turkish, Chinese, emoji, JSON, whitespace/newlines, EOS and padding,
overflow, native template rewriting, NFC transformation, each pinned file's
tampering, and alternate template injection.

Two actual tokenizer findings are enforced rather than hidden:

1. The native Qwen3 template inserts an empty thinking block. The full native
   assistant completion plus EOS is trained; prompt/header and padding are masked.
2. The tokenizer normalizes NFC and the template strips leading response
   newlines. Inputs changed by either behavior are rejected; any preparation
   transformation belongs in the explicit A4 provenance record.

## Reproduction and retained local artifacts

The commands and semantics are in [the contract](../docs/training_schema.md).
The real run used the dedicated tokenizer-only cache under
`.cache/huggingface/models--mlx-community--Qwen3-8B-4bit/snapshots/545dc4251c05440727734bcd94334791f6ab0192`.
Only five tokenizer/config files were downloaded, with no weights. Cache files
and generated outputs remain local and ignored; they can be regenerated from the
pinned revision, tracked test fixtures and lockfile. No external backup is claimed.

- `reports/generated/a3/fixture-validation-final.json`: input/eval/tokenizer/code/
  lock hashes, exact runtime and observed token counts.
- `reports/generated/a3/pytest-final.xml`: 111-test result, including local-file
  integration checks. Earlier failed/intermediate runs did not become acceptance
  results; final commands above are the acceptance runs.
- CLI fixture SHA256:
  `e842123ba9962711f92674d048c90e7993a4131373c1df160851e91468b314cd`.
- Training module SHA256:
  `84a6b7ceaf4cd2714eff427eb334c533da17707210ae2412498ad7071ff08780`.

## Limits and next gate

Lexical checks do not establish absence of paraphrase/answer-only contamination;
provenance and reviewer fields are declarations. The A4 data still needs source,
rights, grouping and content review. No A4 dataset, MLX trainer integration,
backward/update, adapter save/reload, or Base/SFT comparison was performed.
Those remain subsequent gates. Extra dev/confirmation datasets and the A1
research-success interpretation were not silently added or rewritten.

The only next package enabled by this result is **A4: small reviewed SFT data**.
Source publication and public release are separate from local A3 verification.
