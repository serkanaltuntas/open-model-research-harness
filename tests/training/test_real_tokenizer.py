"""Opt-in, local files only: A3_TOKENIZER_SNAPSHOT=/.../<revision> uv run pytest ..."""

import os
import shutil
from pathlib import Path

import pytest

from harness.config import load_mlx_model_config
from harness.training.data import IGNORE_INDEX, TrainingDataError, encode_example
from harness.training.tokenizer import load_tokenizer

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = os.environ.get("A3_TOKENIZER_SNAPSHOT")
pytestmark = pytest.mark.skipif(
    not SNAPSHOT,
    reason="explicit local A3_TOKENIZER_SNAPSHOT required; never downloads in tests",
)


@pytest.fixture(scope="module")
def real_tokenizer():
    config = load_mlx_model_config(ROOT / "configs/models/qwen3_8b_mlx_4bit.yaml")
    return load_tokenizer(
        config, ROOT / "configs/training/sft_tokenizer_v1.json", snapshot=Path(SNAPSHOT)
    )[0]


@pytest.mark.parametrize(
    "answer",
    [
        "Merhaba, dünya!",
        '{"a": [1, 2], "ok": true}',
        " leading space",
        "line one\nline two\n",
        "你好，世界。",
        "🙂 café é",
        "3",
        "  indented",
    ],
)
def test_real_completion_boundaries_and_padding(example, real_tokenizer, answer):
    example["messages"][1]["content"] = answer
    encoded = encode_example(example, real_tokenizer, max_length=512, pad_to_length=512)
    start, end = encoded.target_start, encoded.target_end
    expected = "<think>\n\n</think>\n\n" + answer + "<|im_end|>"
    assert (
        real_tokenizer.decode(
            encoded.input_ids[start:end], clean_up_tokenization_spaces=False
        )
        == expected
    )
    assert all(x == IGNORE_INDEX for x in encoded.labels[:start])
    assert encoded.labels[end - 1] == 151645
    assert all(x == IGNORE_INDEX for x in encoded.labels[end:])
    assert sum(encoded.loss_mask[1:]) == end - start
    assert sum(encoded.attention_mask) == encoded.unpadded_length
    assert encoded.labels[1:][start - 1] == encoded.input_ids[start]


def test_real_overflow_and_template_rewrite(example, real_tokenizer):
    length = encode_example(example, real_tokenizer, max_length=512).unpadded_length
    encode_example(example, real_tokenizer, max_length=length)
    with pytest.raises(TrainingDataError, match="truncation forbidden"):
        encode_example(example, real_tokenizer, max_length=length - 1)
    example["messages"][1]["content"] = "\nanswer"
    with pytest.raises(TrainingDataError, match="changed response"):
        encode_example(example, real_tokenizer, max_length=512)


def test_real_unicode_normalization_is_not_silent(example, real_tokenizer):
    # The pinned tokenizer has an NFC normalizer. Data preparation must record
    # this transformation explicitly; validation must not silently rewrite it.
    example["messages"][1]["content"] = "e\u0301"
    assert (
        real_tokenizer.decode(
            real_tokenizer.encode("e\u0301", add_special_tokens=False)
        )
        == "é"
    )
    with pytest.raises(TrainingDataError, match="round-trip"):
        encode_example(example, real_tokenizer, max_length=512)


@pytest.mark.parametrize(
    "filename",
    [
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "added_tokens.json",
        "config.json",
    ],
)
def test_real_snapshot_tampering_fails_before_load(tmp_path, filename):
    snapshot = Path(SNAPSHOT)
    copy = tmp_path / snapshot.name
    shutil.copytree(snapshot, copy)
    with (copy / filename).open("ab") as file:
        file.write(b" ")
    config = load_mlx_model_config(ROOT / "configs/models/qwen3_8b_mlx_4bit.yaml")
    with pytest.raises(TrainingDataError, match="hash mismatch"):
        load_tokenizer(
            config, ROOT / "configs/training/sft_tokenizer_v1.json", snapshot=copy
        )


def test_real_extra_template_file_rejected(tmp_path):
    snapshot = Path(SNAPSHOT)
    copy = tmp_path / snapshot.name
    shutil.copytree(snapshot, copy)
    (copy / "chat_template.jinja").write_text("unverified override")
    config = load_mlx_model_config(ROOT / "configs/models/qwen3_8b_mlx_4bit.yaml")
    with pytest.raises(TrainingDataError, match="unexpected files"):
        load_tokenizer(
            config, ROOT / "configs/training/sft_tokenizer_v1.json", snapshot=copy
        )
