"""Validate SFT-v1 data and, explicitly, real-tokenizer loss masks."""

import argparse
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from harness.config import load_mlx_model_config
from harness.training.data import (
    TrainingDataError,
    encode_example,
    read_jsonl,
    sha256,
    validate_collection,
)
from harness.training.tokenizer import load_tokenizer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        nargs="+",
        help="All splits together; validation checks across files.",
    )
    parser.add_argument("--require-human-review", action="store_true")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--schema-only",
        action="store_true",
        help="No token validation; never a full A3 data pass.",
    )
    modes.add_argument("--tokenizer-snapshot", type=Path)
    modes.add_argument(
        "--download-tokenizer",
        action="store_true",
        help="Explicitly download five pinned tokenizer/config files only.",
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=REPOSITORY_ROOT / ".cache/huggingface"
    )
    parser.add_argument(
        "--max-length",
        type=int,
        help="Required for token validation; no silent truncation.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="New output file; existing reports are not overwritten.",
    )
    args = parser.parse_args(argv)
    if not args.schema_only and (args.max_length is None or args.max_length <= 0):
        parser.error("token validation requires positive --max-length")
    if args.schema_only and args.max_length is not None:
        parser.error("--max-length requires token validation")
    try:
        if args.report and (args.report.exists() or args.report.is_symlink()):
            raise TrainingDataError("report already exists; select a new path")
        manifest = json.loads(
            (REPOSITORY_ROOT / "releases/july_2026_manifest.json").read_text()
        )
        eval_path = REPOSITORY_ROOT / manifest["dataset"]["path"]
        if sha256(eval_path) != manifest["dataset"]["sha256"]:
            raise TrainingDataError("frozen July evaluation hash mismatch")
        rows = []
        inputs = []
        for path in args.dataset:
            rows.extend(read_jsonl(path))
            inputs.append({"path": str(path), "sha256": sha256(path)})
        report = validate_collection(
            rows, read_jsonl(eval_path), require_human_review=args.require_human_review
        )
        report.update(
            {
                "status": "SCHEMA_VALID",
                "inputs": inputs,
                "eval_sha256": sha256(eval_path),
                "token_validation": "not_run",
                "validator_files": {
                    path: sha256(REPOSITORY_ROOT / path)
                    for path in (
                        "harness/training/data.py",
                        "harness/training/tokenizer.py",
                        "scripts/validate_training_dataset.py",
                        "configs/training/sft_tokenizer_v1.json",
                        "configs/models/qwen3_8b_mlx_4bit.yaml",
                        "uv.lock",
                    )
                },
                "environment": {
                    "python": platform.python_version(),
                    **{
                        package: importlib.metadata.version(package)
                        for package in ("transformers", "tokenizers", "jinja2")
                    },
                },
            }
        )
        if not args.schema_only:
            config = load_mlx_model_config(
                REPOSITORY_ROOT / "configs/models/qwen3_8b_mlx_4bit.yaml"
            )
            tokenizer, identity = load_tokenizer(
                config,
                REPOSITORY_ROOT / "configs/training/sft_tokenizer_v1.json",
                snapshot=args.tokenizer_snapshot,
                download=args.download_tokenizer,
                cache_dir=args.cache_dir,
            )
            encoded = []
            for row in rows:
                try:
                    encoded.append(
                        encode_example(row, tokenizer, max_length=args.max_length)
                    )
                except TrainingDataError as error:
                    raise TrainingDataError(f"{row['id']}: {error}") from error
            report.update(
                {
                    "status": "DATA_VALID",
                    "token_validation": "passed",
                    "tokenizer": identity,
                    "max_length": args.max_length,
                    "sequence_tokens": sum(x.unpadded_length for x in encoded),
                    "loss_tokens": sum(sum(x.loss_mask) for x in encoded),
                    "longest_sequence": max(x.unpadded_length for x in encoded),
                }
            )
        serialized = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open("x", encoding="utf-8") as output:
                output.write(serialized)
        print(serialized, end="")
        return 0
    except (TrainingDataError, OSError, ValueError, ImportError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
