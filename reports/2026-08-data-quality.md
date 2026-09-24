# August data quality — A4 pilot baseline

Milestone: `2026-08`. Actual work and verification: **2026-09-24** on Nightblade
Linux CPU. **A4 complete; A10 comparison pending.** This report records dataset
construction and acceptance, not a training result or a model-quality gain.

## Accepted artifact

The [dataset card](../docs/august_sft_dataset.md) defines provenance, rights,
coverage, review limitations, regeneration commands and the A10 handoff.
The [canonical data](../datasets/sft/august_sft_v1.jsonl),
[split manifest](../datasets/sft/august_sft_v1.manifest.json),
[automated decisions](../datasets/sft/august_sft_v1.review.jsonl) and
[assistant inspection](../datasets/sft/august_sft_v1.assistant-review.json) are
small, explicitly tracked artifacts.

Dataset SHA-256:
`bdc8d479735f7ba0eb6c195105127b3ad523c79d92ff92b74ee007f53a1a9de4`.

| Acceptance evidence | Observed result |
| --- | --- |
| Training / validation | 200 / 40 examples; 50 / 10 per each of four behaviors |
| Smoke subset | 24 training IDs; six per behavior; all 20 training families represented |
| Source separation | 20 training families / eight validation families; zero shared groups |
| Origin and rights | 240 original procedural synthetic examples; per-row provenance and project CC BY 4.0 attribution |
| Answer checks | 240 accepted by a separate prompt-derived content/format checker |
| Additional inspection | 67 distinct rows inspected by the assistant, covering all 28 families and ten nearest similarity pairs |
| Human review | **0**; rows explicitly say automated acceptance; human-only gate rejects the set |
| Exact and normalized checks | A3 schema, duplicate, source-group and July-overlap checks passed |
| Lexical similarity scan | 6,000 dataset/July pairs and 8,000 train/validation pairs; zero flags at word Jaccard >= 0.50 or character ratio >= 0.65 |
| Real tokenizer | All 240 examples passed pinned Qwen3 chat/mask/EOS/round-trip and length checks |
| Token bounds | 512-token rejection ceiling; longest sequence 112; zero truncation/overflow |
| Reproduction | Canonical data, manifest and automated review regenerate byte-for-byte |
| Regression suite | **119 passed**, including 16 opt-in real-tokenizer tests and eight A4 tests |
| July preservation | All 16 tracked-file SHA-256 values in the frozen manifest verified unchanged |

The first candidate review found two wording issues (rotation singular/plural and
threshold answer wording). Both were corrected before the accepted artifact;
final automated rejection count is zero. The ten closest lexical pairs were
inspected despite falling below the thresholds and retained with findings in the
inspection record. Shared task vocabulary did not imply identical input/answer
content. These checks do not prove semantic independence or absence of answer-only
leakage.

| Split | Sequence tokens | Supervised loss tokens | Min / median / max length |
| --- | ---: | ---: | --- |
| Train | 14,726 | 3,700 | 54 / 72 / 100 |
| Validation | 3,042 | 733 | 60 / 70.5 / 112 |

## Verification and evidence locations

The snapshot is `mlx-community/Qwen3-8B-4bit` revision
`545dc4251c05440727734bcd94334791f6ab0192`, using the A2/A3 template and file
hashes. Python 3.12.14, Transformers 5.16.1, Tokenizers 0.23.1 and Jinja2 3.1.6
were used. No model weights were loaded and no training update was performed.

Commands for data and similarity checks are in the dataset card. Full test run:

```sh
A3_TOKENIZER_SNAPSHOT="$PWD/.cache/huggingface/models--mlx-community--Qwen3-8B-4bit/snapshots/545dc4251c05440727734bcd94334791f6ab0192" \
  HF_HUB_OFFLINE=1 uv run python -m pytest -q \
  --junitxml=reports/generated/a4/pytest-final.xml
```

The suite also rejects corrupted answers for every row, checks JSON boolean versus
integer types, refuses a false human-review claim and refuses output overwrites.
Ruff passed for all five new Python files; `git diff --check` passed.

Raw outputs remain local under `reports/generated/a4/`: `pytest-final.xml`,
`token-validation-final.json` and `final-audit.json`. The final audit SHA-256 is
`a98b02c5da23a4cc0e88b6fcfb2427cba466bebd66f9432d2120d08367585bed`.
Earlier local candidate/validation outputs are superseded and are not evidence
for the accepted dataset hash. Scripts and tracked artifacts permit fresh runs.

## Interpretation and next gate

This is a narrow pilot: 28 correlated templates, short answers, invented context,
and an English-heavy mixture. Automated checks and assistant inspection are not
human acceptance or broad data-quality evidence. A4 closes the small-data gate;
A10 still needs the separately controlled quality comparison described in the card.

Next is **A5: real LoRA update, adapter save and reload** on the supported Apple
Silicon MLX environment, using the declared smoke IDs and preserving A3 masking.
MLX data export and actual adapter acceptance are A5 work. No Base/SFT comparison,
new frozen evaluation set, training-cost claim or August-stage closure is reported.
