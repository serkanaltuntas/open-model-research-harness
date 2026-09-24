# SFT-v1 data contract (A3)

This contract implements A3 of the [August specification](august_2026_sft_experiment.md).
It validates data and completion-only targets; it does not train a model or
create the A4 curated dataset. The [three test fixtures](../tests/training/fixtures/valid.jsonl)
are synthetic, unreviewed software fixtures, not research training data.

## JSONL schema

UTF-8, one object per physical line, no blank records, duplicate JSON keys or
non-finite numbers. Unknown fields are errors, including inside nested objects.

| Field | Contract |
| --- | --- |
| `schema_version` | Exactly `sft-v1` |
| `id` | Globally unique, stable ASCII ID: letters, digits, `._:/-`; starts alphanumeric |
| `messages` | Exactly two objects, `user` then `assistant`; each has only `role` and nonblank `content` |
| `behavior` | `instruction_following`, `structured_output`, `concise_factual`, or `reasoning_format` |
| `source_group` | Stable ID for source/prompt/template family, same ID syntax; a group may occur in only one split |
| `split` | `train` or `validation`; assigned by data preparation, never randomly reassigned by validation |
| `provenance` | Object described below |
| `review` | Object described below |

The v1 restriction excludes system messages, multi-turn chats, tool calls and
explicit reasoning traces. Chat/control markers inside content are rejected.
Ordinary code and JSON remain plain strings. A later format needs a new version.

### Provenance

Every provenance object contains exactly:

- `kind`: `human-written`, `public-source`, `synthetic`, or `transformed`.
- `source`: a nonempty source locator or generation record reference.
- `license`: a nonempty license/permission identifier.
- `rights_basis`: the basis for training and redistribution rights.
- `generation`: null unless applicable; mandatory for synthetic examples.
  The object contains nonempty `producer`, `model_revision`, and `recipe`
  references. Retain this object for transformations of synthetic material.
- `transformation`: mandatory for transformed examples, otherwise null.
  Contains nonempty `parent_source` and `method`; the parent record must retain
  upstream provenance, including generation if applicable.

The validator checks declarations, not legal permission or whether an upstream
record exists. A4 must examine those records and content quality. Test fixtures
explicitly mark the generating model revision as unrecorded; that is not a
suitable provenance record for a reproducible real generation run.

### Review

Exactly `status`, `method`, `reviewer`, `reviewed_at`, and `note`:

- `status`: `unreviewed`, `accepted`, or `rejected`.
- `method`: `none`, `human`, or `automated`.
- Unreviewed rows require `none`, null reviewer, and null timestamp.
- Accepted/rejected rows require a nonempty reviewer, a timezone-bearing ISO
  datetime, and human or automated method. `note` is always a string.
- Rejected rows cannot enter a validated collection.
- `--require-human-review` requires **both** accepted status and human method.
  Automated acceptance is never upgraded to human acceptance. Actual reviewer
  identity and quality still require an external record.

## Deterministic separation and contamination checks

Pass all training/validation files in one command. IDs are globally unique;
source groups cannot cross splits. Repeated normalized user prompts are rejected
within and across splits, including conflicting answers to the same prompt.
Repeated assistant answers alone are permitted (for example classification labels).

Normalization is fixed: Unicode NFKC, casefold, then retain alphanumerics only.
It is used for comparison, never to rewrite data. Each user and assistant message
is checked for equality with July prompts; normalized July prompts of at least
40 characters are also searched inside messages to catch wrapper instructions.
The CLI checks the July dataset's frozen manifest hash before any validation.

These are conservative lexical checks. They can reject distinct punctuation-
sensitive code prompts and miss semantic paraphrases, partial copies, answer-only
leakage or incorrectly assigned source groups. They are not contamination-free
certification. Review suspects and correct data/grouping; do not silently tune
the rule against July scores. Additional development/confirmation suites and
research-success interpretation remain separate design decisions.

## Exact Qwen3 rendering and loss contract

The model/tokenizer revision stays
`mlx-community/Qwen3-8B-4bit@545dc4251c05440727734bcd94334791f6ab0192`.
[Tokenizer identity](../configs/training/sft_tokenizer_v1.json) pins all five
downloaded tokenizer/config files and the A2 chat-template hash. Loading checks
those hashes, revision directory, EOS/padding identity and loaded template. It
uses a dedicated tokenizer-only snapshot; extra files that might override the
template are rejected. Remote code is disabled; only explicit download mode
contacts Hugging Face. No weights or model runtime are needed.

`encode_example` renders the native template with `enable_thinking=True`, making
the A2 default explicit. For v1 plain responses, the template creates an empty
`<think>\n\n</think>\n\n` block. The target is that native assistant completion,
the answer, and `<|im_end|>` (151645). The user text, assistant role header,
terminal newline and right-padding are excluded from loss. A6/A8 must preserve
the same generation/thinking control in both evaluation arms.

Prompt-prefix and through-EOS tokenizations must match the full sequence exactly.
No custom chat template or assumed `assistant_masks` support is used. Full
decode must reproduce the rendered text. The pinned tokenizer normalizes NFC;
decomposed text that changes under tokenization is therefore rejected. A4 can
normalize such text as an explicit recorded preparation operation. The native
template also strips initial assistant newlines; these rows are rejected instead
of silently changing the requested target.

`EncodedExample` returns `input_ids`, `attention_mask`, unshifted `labels`,
`loss_mask`, `target_start`, exclusive `target_end` (through EOS), and
`unpadded_length`. Masked labels are `-100`. A causal trainer must compare
`logits[:, :-1]` with `labels[:, 1:]` (or shift internally once), and average loss
over selected target tokens. The first answer token is predicted from the last
prompt token. Masking is positional, so EOS remains trainable even when pad ID
equals EOS. The current pinned pad ID is 151643.

`max_length` is mandatory for token validation. Any overflow fails; there is no
truncation. Optional `pad_to_length` must fit the entire sequence and must not
exceed the maximum. Training hyperparameters and MLX trainer integration are A5
work; passing A3 does not prove a backward/update/save/reload path works.

## Commands and reports

`uv sync --locked` installs CPU tokenizer/test dependencies on Linux. MLX/MLX-LM
remain installed by default on Apple Silicon macOS, at the unchanged locked
versions. Nightblade used its installed Python 3.12.14; the M4 A2 environment was
not modified. The A2 mocked unit test now also mocks package/OS metadata so the
offline suite does not require an actual Mac.

```sh
# Explicitly partial validation: no tokenizer download or token pass claimed.
uv run python scripts/validate_training_dataset.py \
  --dataset tests/training/fixtures/valid.jsonl --schema-only

# Five tokenizer/config files only; use a new report path on each run.
uv run python scripts/validate_training_dataset.py \
  --dataset tests/training/fixtures/valid.jsonl \
  --download-tokenizer --max-length 512 \
  --report reports/generated/a3/new-validation.json

# Local/offline verification after that explicit download.
A3_TOKENIZER_SNAPSHOT="$PWD/.cache/huggingface/models--mlx-community--Qwen3-8B-4bit/snapshots/545dc4251c05440727734bcd94334791f6ab0192" \
  HF_HUB_OFFLINE=1 uv run python -m pytest -q
```

For actual data, pass all splits together, e.g. `--dataset TRAIN.jsonl VALID.jsonl`,
and add `--require-human-review` when human review is the acceptance gate.
`SCHEMA_VALID` means structural/separation checks only. `DATA_VALID` also means
token checks passed; neither means a curated dataset is ready, model training
worked, rights are verified, or human review occurred. Reports include input and
eval hashes, split/review counts, tokenizer identity, token counts and limits.
Output files are created exclusively; failed validation does not create a success
report. Default pytest runs never download a tokenizer; real-file checks are
explicitly skipped until `A3_TOKENIZER_SNAPSHOT` is supplied.

Sources: [pinned tokenizer configuration](https://huggingface.co/mlx-community/Qwen3-8B-4bit/blob/545dc4251c05440727734bcd94334791f6ab0192/tokenizer_config.json),
[Transformers chat templates](https://huggingface.co/docs/transformers/main/chat_templating),
[A2 report](../reports/2026-08-a2-mlx-compatibility.md).
