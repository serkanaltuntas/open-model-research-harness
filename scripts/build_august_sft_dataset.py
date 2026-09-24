"""Build A4 original data, independently review answers, and write immutable manifests."""

import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.training.august_dataset import build_candidates
from harness.training.august_review import check_content
from harness.training.data import read_jsonl, sha256, validate_collection

RECIPE = ROOT / "configs/data/august_sft_v1.json"
DATASET_NAME = "august_sft_v1.jsonl"


def jsonl_bytes(rows):
    return "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    ).encode()


def build(
    output_dir: Path, *, recipe_path: Path = RECIPE, reviewed_at: str | None = None
):
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(
            "output directory is not empty; use a new directory for regeneration"
        )
    recipe = json.loads(recipe_path.read_text())
    families = recipe["families"]
    if len({f["name"] for f in families}) != len(families):
        raise ValueError("duplicate recipe family")
    generator = ROOT / "harness/training/august_dataset.py"
    reviewer = ROOT / "harness/training/august_review.py"
    candidate = build_candidates(recipe, sha256(recipe_path), sha256(generator))
    candidate_hash = hashlib.sha256(jsonl_bytes(candidate)).hexdigest()
    # The complete candidate list exists before eval data is read. Eval is not
    # an argument to the generator and cannot influence generated targets.
    frozen = json.loads((ROOT / "releases/july_2026_manifest.json").read_text())[
        "dataset"
    ]
    eval_path = ROOT / frozen["path"]
    if sha256(eval_path) != frozen["sha256"]:
        raise ValueError("July hash mismatch")
    validation = validate_collection(candidate, read_jsonl(eval_path))
    reviews = [check_content(row) for row in candidate]
    timestamp = reviewed_at or datetime.now(UTC).isoformat(timespec="seconds")
    if datetime.fromisoformat(timestamp).utcoffset() is None:
        raise ValueError("review timestamp requires timezone")
    rows = copy.deepcopy(candidate)
    for row in rows:
        row["review"] = {
            "status": "accepted",
            "method": "automated",
            "reviewer": "a4-prompt-derived-check-v1",
            "reviewed_at": timestamp,
            "note": f"Content and required format checked from prompt; reviewer sha256:{sha256(reviewer)}. No human review claimed.",
        }
    validate_collection(rows, read_jsonl(eval_path))
    groups = sorted({row["source_group"] for row in rows if row["split"] == "train"})
    smoke = []
    # Cover every train family, then one extra per behavior: 20 + 4 = 24.
    for group in groups:
        smoke.append(next(row["id"] for row in rows if row["source_group"] == group))
    for behavior in sorted({row["behavior"] for row in rows}):
        smoke.append(
            next(
                row["id"]
                for row in rows
                if row["split"] == "train"
                and row["behavior"] == behavior
                and row["id"] not in smoke
            )
        )
    if len(smoke) != recipe["smoke_count"]:
        raise ValueError("smoke count inconsistent with family design")
    encoded = jsonl_bytes(rows)
    split_info = {}
    for split in ["train", "validation"]:
        selected = [row for row in rows if row["split"] == split]
        split_info[split] = {
            "count": len(selected),
            "ids": [row["id"] for row in selected],
            "source_groups": sorted({row["source_group"] for row in selected}),
            "behavior_counts": dict(
                sorted(Counter(row["behavior"] for row in selected).items())
            ),
            "canonical_subset_sha256": hashlib.sha256(
                jsonl_bytes(selected)
            ).hexdigest(),
        }
    smoke_rows = [
        next(row for row in rows if row["id"] == identity) for identity in smoke
    ]
    manifest = {
        "schema_version": "a4-manifest-v1",
        "dataset_id": recipe["dataset_id"],
        "dataset_file": DATASET_NAME,
        "dataset_sha256": hashlib.sha256(encoded).hexdigest(),
        "candidate_sha256_before_review": candidate_hash,
        "recipe": {
            "path": str(recipe_path.relative_to(ROOT))
            if recipe_path.is_relative_to(ROOT)
            else str(recipe_path),
            "sha256": sha256(recipe_path),
        },
        "generator_sha256": sha256(generator),
        "reviewer_sha256": sha256(reviewer),
        "builder_sha256": sha256(Path(__file__)),
        "reviewed_at": timestamp,
        "splits": split_info,
        "smoke": {
            "count": len(smoke),
            "ids": smoke,
            "canonical_subset_sha256": hashlib.sha256(
                jsonl_bytes(smoke_rows)
            ).hexdigest(),
            "training_subset_only": True,
        },
        "provenance_counts": dict(Counter(row["provenance"]["kind"] for row in rows)),
        "review": {
            "automated_content_checks": len(reviews),
            "human_reviewed": 0,
            "rejected": 0,
            "per_example_file": "august_sft_v1.review.jsonl",
        },
        "separation_check": validation,
        "frozen_eval_sha256": frozen["sha256"],
        "limitations": [
            "Procedural microtask pilot; 28 templates, not 240 independent task families.",
            "No human acceptance or broad factual/capability claim.",
            "Validation holds out template families, but shares vocabulary and task design process.",
            "Lexical checks cannot prove absence of paraphrase or answer-only contamination.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        DATASET_NAME: encoded,
        "august_sft_v1.review.jsonl": jsonl_bytes(reviews),
        "august_sft_v1.manifest.json": (
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        ).encode(),
    }
    for name, data in outputs.items():
        with (output_dir / name).open("xb") as file:
            file.write(data)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--reviewed-at",
        help="Original timestamp when reproducing; omit for a new review run.",
    )
    args = parser.parse_args(argv)
    try:
        manifest = build(args.output_dir, reviewed_at=args.reviewed_at)
    except (OSError, ValueError, KeyError, IndexError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "dataset_sha256": manifest["dataset_sha256"],
                "train": manifest["splits"]["train"]["count"],
                "validation": manifest["splits"]["validation"]["count"],
                "smoke": manifest["smoke"]["count"],
                "human_reviewed": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
