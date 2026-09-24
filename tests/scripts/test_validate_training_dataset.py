import json
import subprocess
import sys
from pathlib import Path

from scripts.validate_training_dataset import main

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "tests/training/fixtures/valid.jsonl"


def test_schema_only_reports_its_limit(capsys):
    assert main(["--dataset", str(DATASET), "--schema-only"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "SCHEMA_VALID"
    assert report["token_validation"] == "not_run"
    assert report["examples"] == 3
    assert report["eval_tasks"] == 25


def test_cross_file_checks_and_human_review(capsys):
    assert main(["--dataset", str(DATASET), str(DATASET), "--schema-only"]) == 1
    assert "duplicate id" in capsys.readouterr().err
    assert (
        main(["--dataset", str(DATASET), "--schema-only", "--require-human-review"])
        == 1
    )
    assert "human acceptance" in capsys.readouterr().err


def test_report_write_is_exclusive(tmp_path, capsys):
    report = tmp_path / "new/report.json"
    args = ["--dataset", str(DATASET), "--schema-only", "--report", str(report)]
    assert main(args) == 0
    before = report.read_bytes()
    assert main(args) == 1
    assert report.read_bytes() == before
    assert "already exists" in capsys.readouterr().err


def test_direct_script_and_required_mode():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_training_dataset.py",
            "--dataset",
            str(DATASET),
            "--schema-only",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_training_dataset.py",
            "--dataset",
            str(DATASET),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


def test_missing_dataset_is_readable_error(tmp_path, capsys):
    assert main(["--dataset", str(tmp_path / "missing"), "--schema-only"]) == 1
    assert "ERROR:" in capsys.readouterr().err
