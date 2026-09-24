"""Post-generation A4 overlap/length audit. Never generates training targets."""

import argparse
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.config import load_mlx_model_config
from harness.training.august_review import check_content
from harness.training.data import (
    encode_example,
    normalize,
    read_jsonl,
    sha256,
    validate_collection,
)
from harness.training.tokenizer import load_tokenizer


def tokens(text):
    return set(re.findall(r"\w+", text.casefold()))


def compare(left, right):
    a, b = (
        left["messages"][0]["content"],
        right.get("prompt") or right["messages"][0]["content"],
    )
    at, bt = tokens(a), tokens(b)
    jaccard = len(at & bt) / len(at | bt)
    ratio = SequenceMatcher(None, normalize(a), normalize(b), autojunk=False).ratio()
    return {
        "left": left["id"],
        "right": right["id"],
        "word_jaccard": round(jaccard, 6),
        "character_ratio": round(ratio, 6),
    }


def audit(dataset: Path, snapshot: Path):
    rows = read_jsonl(dataset)
    frozen = json.loads((ROOT / "releases/july_2026_manifest.json").read_text())[
        "dataset"
    ]
    eval_path = ROOT / frozen["path"]
    if sha256(eval_path) != frozen["sha256"]:
        raise ValueError("July hash mismatch")
    evals = read_jsonl(eval_path)
    basic = validate_collection(rows, evals)
    for row in rows:
        check_content(row)
    config = load_mlx_model_config(ROOT / "configs/models/qwen3_8b_mlx_4bit.yaml")
    tokenizer, identity = load_tokenizer(
        config, ROOT / "configs/training/sft_tokenizer_v1.json", snapshot=snapshot
    )
    recipe = json.loads((ROOT / "configs/data/august_sft_v1.json").read_text())
    encoded = {
        row["id"]: encode_example(row, tokenizer, max_length=recipe["max_length"])
        for row in rows
    }
    splits = {}
    for split in ["train", "validation"]:
        selected = [encoded[row["id"]] for row in rows if row["split"] == split]
        lengths = [item.unpadded_length for item in selected]
        splits[split] = {
            "rows": len(selected),
            "sequence_tokens": sum(lengths),
            "loss_tokens": sum(sum(item.loss_mask) for item in selected),
            "min_length": min(lengths),
            "median_length": median(lengths),
            "max_length": max(lengths),
        }
    scopes = {
        "versus_july": [(a, b) for a in rows for b in evals],
        "train_vs_validation": [
            (a, b)
            for a in rows
            if a["split"] == "train"
            for b in rows
            if b["split"] == "validation"
        ],
    }
    scans = {}
    for name, pairs in scopes.items():
        measurements = [compare(a, b) for a, b in pairs]
        flags = [
            x
            for x in measurements
            if x["word_jaccard"] >= 0.50 or x["character_ratio"] >= 0.65
        ]
        scans[name] = {
            "pairs": len(pairs),
            "flagged_pairs": flags,
            "top_5_character_pairs": sorted(
                measurements, key=lambda x: x["character_ratio"], reverse=True
            )[:5],
        }
    return {
        "dataset_sha256": sha256(dataset),
        "audit_script_sha256": sha256(Path(__file__)),
        "schema_and_exact_overlap": basic,
        "tokenizer": identity,
        "token_limits": {
            "max_length": recipe["max_length"],
            "overflow_policy": "reject",
        },
        "split_tokens": splits,
        "source_groups": len({row["source_group"] for row in rows}),
        "duplicate_answer_counts": {
            k: v
            for k, v in Counter(row["messages"][1]["content"] for row in rows).items()
            if v > 1
        },
        "similarity_rules": {
            "word_jaccard_flag": 0.50,
            "normalized_character_ratio_flag": 0.65,
            "chosen_before_scan": True,
            "interpretation": "Flags require content review; passing does not prove semantic independence.",
        },
        "scans": scans,
        "human_reviewed": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "datasets/sft/august_sft_v1.jsonl"
    )
    parser.add_argument("--tokenizer-snapshot", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.report.exists():
            raise ValueError("report already exists")
        report = audit(args.dataset, args.tokenizer_snapshot)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x") as file:
            file.write(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(
            json.dumps(
                {
                    "split_tokens": report["split_tokens"],
                    "scans": {
                        k: {
                            "pairs": v["pairs"],
                            "flagged_pairs": len(v["flagged_pairs"]),
                        }
                        for k, v in report["scans"].items()
                    },
                },
                indent=2,
            )
        )
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
