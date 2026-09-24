# August SFT v1 — dataset card

**A4 procedural pilot:** 200 training examples, 40 validation examples, and a
24-example smoke subset of training. The canonical dataset is
[`datasets/sft/august_sft_v1.jsonl`](../datasets/sft/august_sft_v1.jsonl).
Split IDs, source groups, subset hashes and provenance are in the adjacent
[`manifest`](../datasets/sft/august_sft_v1.manifest.json). Subsets are selections
from this one source; the smoke set is not additional training data.

## Purpose and coverage

The pilot supplies small, inspectable targets for instruction adherence, JSON
structure, concise context-grounded factual responses, and brief arithmetic
presentation. It supports the A5 training plumbing check and later controlled
Base/SFT comparisons. It is not a broad instruction corpus or a benchmark.

| Behavior | Train | Validation | Smoke | Task families |
| --- | ---: | ---: | ---: | --- |
| Instruction following | 50 | 10 | 6 | Train: token position, label ordering, wrapping, deduplication, prefix selection. Validation: token removal, rotation. |
| Structured output | 50 | 10 | 6 | Train: key/value mapping, record arrays, nesting, booleans, projection. Validation: grouping, singleton arrays. |
| Concise factual | 50 | 10 | 6 | Train: fictional cards, maximum lookup, catalog, schedule, habitat. Validation: missing information, location chain. |
| Reasoning format | 50 | 10 | 6 | Train: stock, package totals, elapsed time, discounts, distance. Validation: full-box packing, threshold counts. |

All factual inputs are explicitly fictional and self-contained. This measures
short answers based on supplied context, not external-world factual knowledge.
There are 20 Turkish training examples and 220 English examples (180 train,
40 validation). Language coverage is unbalanced; validation does not measure
Turkish generalization. Reasoning examples contain short visible arithmetic,
not hidden reasoning traces. Coding and safety are not training targets.

## Origin, rights and reproducibility

The original project templates were authored with assistant help; Python computes
all task inputs and target answers using a fixed recipe and seed. No external
corpus, paid API, or model-inference generation call is involved. Every row is
`synthetic`. Its generator model revision is explicitly not applicable; the
recipe and generator hashes provide the reproducible source identity instead.
The assistant used to author code has no immutable model revision recorded here.

Original project microtasks use the repository's CC BY 4.0 data policy, with
attribution to Open Model Research Harness by Serkan Altuntaş. No third-party
content is imported or relicensed. Source, license, rights basis and generation
method are present on every example. See [LICENSE-DATA](../LICENSE-DATA).

The generator does not read July data, prompts, answers or scores. Generation
finishes before the builder loads July for separation checks. July is never
passed as an example to an inference generator. This separation does not assert
that the authoring assistant has never encountered any July material elsewhere.

```sh
# Regenerate into a NEW directory. Use the recorded review timestamp for
# byte-identical reproduction of the canonical data and manifest.
uv run python scripts/build_august_sft_dataset.py \
  --output-dir datasets/generated/a4-reproduction \
  --reviewed-at TIMESTAMP_FROM_MANIFEST

# Full data/token validation; the pinned snapshot was downloaded during A3.
uv run python scripts/validate_training_dataset.py \
  --dataset datasets/sft/august_sft_v1.jsonl \
  --tokenizer-snapshot .cache/huggingface/models--mlx-community--Qwen3-8B-4bit/snapshots/545dc4251c05440727734bcd94334791f6ab0192 \
  --max-length 512 --report reports/generated/a4/new-token-validation.json

uv run python scripts/audit_august_sft_dataset.py \
  --tokenizer-snapshot .cache/huggingface/models--mlx-community--Qwen3-8B-4bit/snapshots/545dc4251c05440727734bcd94334791f6ab0192 \
  --report reports/generated/a4/new-audit.json
```

The builder refuses to overwrite existing files. Its three outputs reproduce
byte-for-byte; the supplementary assistant inspection is an actual review record,
not regenerated or fabricated by that builder. The small canonical dataset,
manifest and review records are explicitly tracked; caches and generated run
reports remain ignored. Files are available in Git rather than only by hash.

## Separation and review

Twenty template/source families belong only to training, eight only to validation.
Families are assigned before generation; splitting individual templated examples
randomly is avoided. All 20 training families occur in the smoke selection.
The vocabulary and overall task-design process are shared, so the validation set
is neither fully independent research confirmation nor a new frozen test suite.
No extra dev/confirmation set has been added.

All 240 targets passed a separate checker that derives the required answer from
the actual prompt; it does not import the producer. Checks include JSON types,
lookup correctness, arithmetic and requested formatting. Per-row content hashes
and decisions are in [`august_sft_v1.review.jsonl`](../datasets/sft/august_sft_v1.review.jsonl).
All rows say **accepted / automated**, not human accepted.

The assistant inspected 56 first/last examples covering every family and the ten
nearest pairs from the similarity scan: 67 distinct dataset rows. Findings and
content hashes are in the [assistant inspection record](../datasets/sft/august_sft_v1.assistant-review.json).
Two wording issues were fixed before acceptance. **Human-reviewed count: 0.**
`--require-human-review` intentionally rejects this dataset. A human-only policy
would require a new review step; that is not the A4 plan's current acceptance rule.

The exact/normalized A3 checks pass. Additional thresholds, set before the scan,
flag word-set Jaccard >= 0.50 or normalized-character similarity >= 0.65.
All 6,000 dataset/July pairs and 8,000 train/validation pairs were checked; zero
pairs met these thresholds. The nearest pairs were inspected despite not being
flagged: they share task vocabulary but use different input/answer content.
Lexical checks cannot rule out semantic paraphrases or answer-only leakage.

## Token bounds and downstream use

The pinned Qwen3 tokenizer from A2/A3 validated every row, including native chat
formatting, target masks, EOS, NFC round-trip and length. Training has 14,726
sequence tokens / 3,700 loss tokens; validation has 3,042 / 733. The longest
sequence is 112 tokens. No truncation, overflow or normalization was needed.
The checked ceiling is 512; this is a data acceptance bound, not the final A5
training configuration. Recompute lengths if template/generation settings change.

Keep training and validation separate using manifest IDs. Train only on the
training split; smoke only on the declared 24 training IDs. The canonical file
contains review/provenance fields and must be adapted explicitly for MLX-LM in
A5. A3 masks include the native empty thinking block and EOS; A5 must preserve
that contract or document and verify a compatible adapter.

## Limitations and A10 handoff

There are 240 rows but only 28 task templates. Numeric/word variants are correlated,
answers are short, the factual slice is extractive, and automated reference checks
may share design blind spots. No improvement, generalization or model capability
has been measured. The set is suitable as a bounded first experiment, not evidence
that data is universally high quality.

For A10, retain this clean version and its hashes. A later controlled quality
condition should be a separately named artifact with a logged per-example change,
matched source-family mixture and comparable target-token/update budget. Select
that intervention before running the comparison, after A9; do not modify this
baseline or use July answers to design the degraded condition. No degraded set,
training run or causal quality comparison was created in A4.
