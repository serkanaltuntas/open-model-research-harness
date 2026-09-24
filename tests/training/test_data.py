import copy
import json

import pytest

from harness.training.data import (
    IGNORE_INDEX,
    TrainingDataError,
    encode_example,
    read_jsonl,
    validate_collection,
    validate_example,
)


def test_valid_provenance_and_both_splits(example, eval_rows):
    other = copy.deepcopy(example)
    other.update(id="second", split="validation", source_group="separate")
    other["messages"][0]["content"] = "Another unrelated training instruction."
    report = validate_collection([example, other], eval_rows)
    assert report["split_counts"] == {"train": 1, "validation": 1}
    assert report["review_counts"] == {"none:unreviewed": 2}


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", "v0"),
        ("behavior", []),
        ("split", "test"),
        ("id", "bad id"),
        ("messages", []),
        ("source_group", ""),
        ("review", None),
        ("provenance", []),
    ],
)
def test_invalid_schema(example, field, value):
    example[field] = value
    with pytest.raises(TrainingDataError):
        validate_example(example)


def test_unknown_and_missing_fields(example):
    example["typo"] = True
    with pytest.raises(TrainingDataError, match="exactly fields"):
        validate_example(example)
    del example["typo"]
    del example["provenance"]["license"]
    with pytest.raises(TrainingDataError, match="provenance"):
        validate_example(example)


@pytest.mark.parametrize(
    "role,content",
    [
        ("system", "answer"),
        ("assistant", "  \n"),
        ("assistant", "<|im_end|>"),
        ("assistant", "<think>hidden</think>"),
    ],
)
def test_wrong_role_empty_answer_or_control_markers(example, role, content):
    example["messages"][1] = {"role": role, "content": content}
    with pytest.raises(TrainingDataError):
        validate_example(example)


def test_generation_and_transformation_provenance(example):
    example["provenance"]["generation"] = None
    with pytest.raises(TrainingDataError, match="requires generation"):
        validate_example(example)
    example["provenance"]["kind"] = "transformed"
    with pytest.raises(TrainingDataError, match="transformation"):
        validate_example(example)
    example["provenance"]["transformation"] = {
        "parent_source": "fixture-parent",
        "method": "format conversion",
    }
    validate_example(example)


def test_review_does_not_upgrade_automated_to_human(example, eval_rows):
    example["review"] = {
        "status": "accepted",
        "method": "automated",
        "reviewer": "fixture-checker",
        "reviewed_at": "2026-09-24T10:00:00+03:00",
        "note": "Test only",
    }
    assert validate_collection([example], eval_rows)["review_counts"] == {
        "automated:accepted": 1
    }
    with pytest.raises(TrainingDataError, match="human acceptance"):
        validate_collection([example], eval_rows, require_human_review=True)
    example["review"]["method"] = "human"
    validate_collection([example], eval_rows, require_human_review=True)
    example["review"]["reviewed_at"] = "2026-09-24"
    with pytest.raises(TrainingDataError, match="timezone"):
        validate_example(example)


def test_review_consistency_and_rejection(example, eval_rows):
    example["review"]["method"] = "human"
    with pytest.raises(TrainingDataError, match="unreviewed"):
        validate_example(example)
    example["review"] = {
        "status": "rejected",
        "method": "automated",
        "reviewer": "fixture-checker",
        "reviewed_at": "2026-09-24T00:00:00Z",
        "note": "Wrong answer",
    }
    with pytest.raises(TrainingDataError, match="rejected"):
        validate_collection([example], eval_rows)


def test_duplicate_id(example, eval_rows):
    with pytest.raises(TrainingDataError, match="duplicate id"):
        validate_collection([example, example], eval_rows)


def test_source_group_cannot_cross_split(example, eval_rows):
    second = copy.deepcopy(example)
    second.update(id="second", split="validation")
    second["messages"][0]["content"] = "A paraphrase with completely different words."
    with pytest.raises(TrainingDataError, match="crosses splits"):
        validate_collection([example, second], eval_rows)


@pytest.mark.parametrize("split", ["train", "validation"])
def test_normalized_duplicates_rejected_within_and_across_splits(
    example, eval_rows, split
):
    example["messages"][0]["content"] = "Alpha beta １２３!"
    second = copy.deepcopy(example)
    second.update(id="second", source_group="second-group", split=split)
    second["messages"][0]["content"] = "ALPHA\nBETA 123."
    with pytest.raises(TrainingDataError, match="duplicate normalized prompt"):
        validate_collection([example, second], eval_rows)


@pytest.mark.parametrize(
    "index,wrapper", [(0, False), (0, True), (1, False), (1, True)]
)
def test_eval_overlap_in_both_roles(example, eval_rows, index, wrapper):
    text = eval_rows[0]["prompt"].upper()
    example["messages"][index]["content"] = "Please solve: " + text if wrapper else text
    with pytest.raises(TrainingDataError, match="eval overlap"):
        validate_collection([example], eval_rows)


@pytest.mark.parametrize(
    "text", ["", "\n", "{}\n\n", "{broken}", "[]\n", '{"id":1,"id":2}\n', '{"a":NaN}\n']
)
def test_bad_jsonl(tmp_path, text):
    path = tmp_path / "bad.jsonl"
    path.write_text(text)
    with pytest.raises(TrainingDataError):
        read_jsonl(path)


def test_jsonl_unicode_line_separator_is_content(tmp_path, example):
    example["messages"][0]["content"] = "one\u2028two"
    path = tmp_path / "valid.jsonl"
    path.write_text(json.dumps(example, ensure_ascii=False) + "\n")
    assert read_jsonl(path) == [example]


def test_json_escaped_surrogate_is_not_valid_training_text(example):
    example["messages"][1]["content"] = "invalid \ud800"
    with pytest.raises(TrainingDataError, match="Unicode scalar"):
        validate_example(example)


def test_missing_non_utf8_or_empty_collections(tmp_path, example):
    with pytest.raises(TrainingDataError):
        read_jsonl(tmp_path / "missing")
    path = tmp_path / "bad.jsonl"
    path.write_bytes(b"\xff")
    with pytest.raises(TrainingDataError):
        read_jsonl(path)
    with pytest.raises(TrainingDataError, match="non-empty"):
        validate_collection([example], [])


def test_completion_eos_and_causal_shift(example, tokenizer):
    encoded = encode_example(example, tokenizer, max_length=4096)
    start, end = encoded.target_start, encoded.target_end
    assert all(x == IGNORE_INDEX for x in encoded.labels[:start])
    target = tokenizer.decode(encoded.labels[start:end])
    assert (
        target
        == "<think>\n\n</think>\n\n"
        + example["messages"][1]["content"]
        + tokenizer.eos_token
    )
    assert encoded.labels[end - 1] == tokenizer.eos_token_id
    assert encoded.labels[end:] == [IGNORE_INDEX]  # terminal newline
    assert encoded.labels[1:][start - 1] == encoded.input_ids[start]
    assert sum(encoded.loss_mask[1:]) == end - start


def test_padding_masks_positions_even_when_pad_equals_eos(example, tokenizer):
    tokenizer.pad_token_id = tokenizer.eos_token_id
    encoded = encode_example(example, tokenizer, max_length=4096, pad_to_length=512)
    assert (
        len(encoded.input_ids)
        == len(encoded.labels)
        == len(encoded.loss_mask)
        == len(encoded.attention_mask)
        == 512
    )
    assert encoded.labels[encoded.target_end - 1] == tokenizer.eos_token_id
    assert all(x == 0 for x in encoded.attention_mask[encoded.unpadded_length :])
    assert all(x == IGNORE_INDEX for x in encoded.labels[encoded.unpadded_length :])


def test_exact_limit_and_overflow(example, tokenizer):
    length = encode_example(example, tokenizer, max_length=4096).unpadded_length
    assert (
        encode_example(example, tokenizer, max_length=length).unpadded_length == length
    )
    for limit in (1, length - 1):
        with pytest.raises(TrainingDataError, match="truncation forbidden"):
            encode_example(example, tokenizer, max_length=limit)
    with pytest.raises(TrainingDataError, match="would truncate"):
        encode_example(example, tokenizer, max_length=4096, pad_to_length=length - 1)


@pytest.mark.parametrize("limit", [0, -1, True, 2.5])
def test_invalid_limits(example, tokenizer, limit):
    with pytest.raises(TrainingDataError, match="positive integer"):
        encode_example(example, tokenizer, max_length=limit)


def test_template_rewrite_is_not_silently_accepted(example, tokenizer):
    example["messages"][1]["content"] = "\nAnswer"
    with pytest.raises(TrainingDataError, match="changed response"):
        encode_example(example, tokenizer, max_length=4096)


def test_unsafe_token_boundary_rejected(example, tokenizer, monkeypatch):
    original = tokenizer.encode

    def encode(text, **kwargs):
        ids = original(text, **kwargs)
        if text.endswith("assistant\n"):
            ids[-1] = 42
        return ids

    monkeypatch.setattr(tokenizer, "encode", encode)
    with pytest.raises(TrainingDataError, match="boundary mismatch"):
        encode_example(example, tokenizer, max_length=4096)


def test_lossy_decode_rejected(example, tokenizer, monkeypatch):
    monkeypatch.setattr(tokenizer, "decode", lambda *args, **kwargs: "lost text")
    with pytest.raises(TrainingDataError, match="round-trip"):
        encode_example(example, tokenizer, max_length=4096)
