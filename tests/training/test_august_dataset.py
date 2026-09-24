import copy
import json
from collections import Counter

import pytest

from harness.training.august_dataset import build_candidates
from harness.training.august_review import (
    ContentReviewError,
    check_content,
    content_hash,
)
from harness.training.data import (
    TrainingDataError,
    read_jsonl,
    sha256,
    validate_collection,
)
from scripts.build_august_sft_dataset import RECIPE, ROOT, build, jsonl_bytes

DATA = ROOT / "datasets/sft"


@pytest.fixture(scope="module")
def rows():
    return read_jsonl(DATA / "august_sft_v1.jsonl")


def test_recorded_dataset_hashes_and_group_split(rows):
    manifest = json.loads((DATA / "august_sft_v1.manifest.json").read_text())
    assert sha256(DATA / "august_sft_v1.jsonl") == manifest["dataset_sha256"]
    assert len(rows) == 240
    assert Counter(row["split"] for row in rows) == {"train": 200, "validation": 40}
    assert Counter((row["split"], row["behavior"]) for row in rows) == {
        (split, behavior): count
        for split, count in [("train", 50), ("validation", 10)]
        for behavior in [
            "instruction_following",
            "structured_output",
            "concise_factual",
            "reasoning_format",
        ]
    }
    train_groups = {row["source_group"] for row in rows if row["split"] == "train"}
    val_groups = {row["source_group"] for row in rows if row["split"] == "validation"}
    assert (len(train_groups), len(val_groups)) == (20, 8)
    assert train_groups.isdisjoint(val_groups)
    for split in ["train", "validation"]:
        selected = [row for row in rows if row["split"] == split]
        assert manifest["splits"][split]["ids"] == [row["id"] for row in selected]
        import hashlib

        assert (
            hashlib.sha256(jsonl_bytes(selected)).hexdigest()
            == manifest["splits"][split]["canonical_subset_sha256"]
        )


def test_smoke_is_balanced_training_subset(rows):
    manifest = json.loads((DATA / "august_sft_v1.manifest.json").read_text())
    smoke = manifest["smoke"]["ids"]
    by_id = {row["id"]: row for row in rows}
    assert len(smoke) == len(set(smoke)) == 24
    assert all(by_id[identity]["split"] == "train" for identity in smoke)
    assert set(Counter(by_id[identity]["behavior"] for identity in smoke).values()) == {
        6
    }
    assert len({by_id[identity]["source_group"] for identity in smoke}) == 20


def test_all_answers_and_content_review_hashes(rows):
    reviews = read_jsonl(DATA / "august_sft_v1.review.jsonl")
    assert len(reviews) == len(rows)
    for row, review in zip(rows, reviews):
        assert check_content(row) == review
        assert content_hash(row) == review["content_sha256"]
        assert row["provenance"]["kind"] == "synthetic"
        assert row["review"]["method"] == "automated"


def test_every_corrupted_target_is_rejected(rows):
    for original in rows:
        row = copy.deepcopy(original)
        row["messages"][1]["content"] = "Incorrect answer with extra commentary."
        with pytest.raises(ContentReviewError):
            check_content(row)


def test_json_boolean_is_not_accepted_as_integer(rows):
    row = copy.deepcopy(
        next(row for row in rows if row["source_group"] == "aug26-family-mapping")
    )
    answer = json.loads(row["messages"][1]["content"])
    answer[next(iter(answer))] = True
    row["messages"][1]["content"] = json.dumps(answer)
    with pytest.raises(ContentReviewError, match="types"):
        check_content(row)


def test_cannot_claim_human_review(rows):
    evals = read_jsonl(ROOT / "datasets/evals/july_eval_v1.jsonl")
    with pytest.raises(TrainingDataError, match="human acceptance"):
        validate_collection(rows, evals, require_human_review=True)


def test_byte_exact_reproduction(tmp_path):
    manifest = json.loads((DATA / "august_sft_v1.manifest.json").read_text())
    dest = tmp_path / "rebuild"
    build(dest, reviewed_at=manifest["reviewed_at"])
    for name in [
        "august_sft_v1.jsonl",
        "august_sft_v1.review.jsonl",
        "august_sft_v1.manifest.json",
    ]:
        assert (dest / name).read_bytes() == (DATA / name).read_bytes()
    with pytest.raises(ValueError, match="not empty"):
        build(dest)


def test_generator_is_deterministic_and_never_marks_reviewed():
    recipe = json.loads(RECIPE.read_text())
    first = build_candidates(recipe, "recipe-hash", "generator-hash")
    assert first == build_candidates(recipe, "recipe-hash", "generator-hash")
    assert all(row["review"]["status"] == "unreviewed" for row in first)
