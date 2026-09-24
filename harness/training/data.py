"""A3 single-turn SFT contract and fail-closed completion-only encoding."""

import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "sft-v1"
IGNORE_INDEX = -100
BEHAVIORS = {
    "instruction_following",
    "structured_output",
    "concise_factual",
    "reasoning_format",
}
KINDS = {"human-written", "public-source", "synthetic", "transformed"}
REVIEW_STATUSES = {"unreviewed", "accepted", "rejected"}
REVIEW_METHODS = {"none", "human", "automated"}
FIELDS = {
    "schema_version",
    "id",
    "messages",
    "behavior",
    "provenance",
    "review",
    "source_group",
    "split",
}


class TrainingDataError(ValueError):
    """Invalid or unsafe-to-train data, formatting, or identity."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _keys(value: Any, fields: set[str], where: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise TrainingDataError(f"{where}: expected exactly fields {sorted(fields)}")


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TrainingDataError(f"{where}: expected non-empty string")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise TrainingDataError(f"{where}: invalid Unicode scalar value") from error
    return value


def _choice(value: Any, choices: set[str], where: str) -> None:
    if not isinstance(value, str) or value not in choices:
        raise TrainingDataError(f"{where}: expected one of {sorted(choices)}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise TrainingDataError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise TrainingDataError(f"non-finite JSON constant {value}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        # Split physical JSONL lines only; U+2028 is valid inside JSON strings.
        lines = path.read_text(encoding="utf-8").split("\n")
    except (OSError, UnicodeError) as error:
        raise TrainingDataError(f"{path}: {error}") from error
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise TrainingDataError(f"{path}: empty dataset")
    rows = []
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(
                line, object_pairs_hook=_unique_object, parse_constant=_reject_constant
            )
            if not isinstance(row, dict):
                raise TrainingDataError("expected JSON object")
        except (ValueError, RecursionError) as error:
            raise TrainingDataError(f"{path}: row {number}: {error}") from error
        rows.append(row)
    return rows


def validate_example(row: Any) -> None:
    _keys(row, FIELDS, "example")
    if row["schema_version"] != SCHEMA_VERSION:
        raise TrainingDataError(f"schema_version: expected {SCHEMA_VERSION}")
    for field in ("id", "source_group"):
        value = _text(row[field], field)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", value):
            raise TrainingDataError(f"{field}: expected stable ASCII identifier")
    _choice(row["behavior"], BEHAVIORS, "behavior")
    _choice(row["split"], {"train", "validation"}, "split")
    messages = row["messages"]
    if not isinstance(messages, list) or len(messages) != 2:
        raise TrainingDataError("messages: expected exactly user then assistant")
    for message, role in zip(messages, ("user", "assistant")):
        _keys(message, {"role", "content"}, "message")
        if message["role"] != role:
            raise TrainingDataError(f"messages: expected {role} role")
        content = _text(message["content"], f"{role}.content")
        if any(
            marker in content
            for marker in (
                "<|",
                "<think>",
                "</think>",
                "<tool_call>",
                "</tool_call>",
                "<tool_response>",
                "</tool_response>",
            )
        ):
            raise TrainingDataError(f"{role}.content: reserved chat/control marker")

    provenance = row["provenance"]
    _keys(
        provenance,
        {"kind", "source", "license", "rights_basis", "generation", "transformation"},
        "provenance",
    )
    _choice(provenance["kind"], KINDS, "provenance.kind")
    for field in ("source", "license", "rights_basis"):
        _text(provenance[field], f"provenance.{field}")
    generation = provenance["generation"]
    if provenance["kind"] == "synthetic" and generation is None:
        raise TrainingDataError("synthetic provenance requires generation")
    if generation is not None:
        _keys(generation, {"producer", "model_revision", "recipe"}, "generation")
        for field, value in generation.items():
            _text(value, f"generation.{field}")
    transformation = provenance["transformation"]
    if provenance["kind"] == "transformed":
        _keys(transformation, {"parent_source", "method"}, "transformation")
        for field, value in transformation.items():
            _text(value, f"transformation.{field}")
    elif transformation is not None:
        raise TrainingDataError(
            "transformation must be null unless kind is transformed"
        )
    if (
        provenance["kind"] in {"human-written", "public-source"}
        and generation is not None
    ):
        raise TrainingDataError("generated examples must be synthetic or transformed")

    review = row["review"]
    _keys(review, {"status", "method", "reviewer", "reviewed_at", "note"}, "review")
    _choice(review["status"], REVIEW_STATUSES, "review.status")
    _choice(review["method"], REVIEW_METHODS, "review.method")
    if not isinstance(review["note"], str):
        raise TrainingDataError("review.note: expected string")
    if review["status"] == "unreviewed":
        if (
            review["method"] != "none"
            or review["reviewer"] is not None
            or review["reviewed_at"] is not None
        ):
            raise TrainingDataError(
                "unreviewed examples must have method none and null reviewer/date"
            )
    else:
        if review["method"] == "none":
            raise TrainingDataError("reviewed examples require a review method")
        _text(review["reviewer"], "review.reviewer")
        timestamp = _text(review["reviewed_at"], "review.reviewed_at")
        try:
            if datetime.fromisoformat(timestamp).utcoffset() is None:
                raise ValueError("timezone required")
        except ValueError as error:
            raise TrainingDataError(
                "review.reviewed_at: expected ISO datetime with timezone"
            ) from error


def normalize(text: str) -> str:
    """Fixed NFKC/casefold/alphanumeric normalizer, independent of eval data."""
    return "".join(
        char
        for char in unicodedata.normalize("NFKC", text).casefold()
        if char.isalnum()
    )


def validate_collection(
    rows: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    *,
    require_human_review: bool = False,
) -> dict[str, Any]:
    if not rows or not eval_rows:
        raise TrainingDataError("training and evaluation collections must be non-empty")
    eval_prompts = []
    for task in eval_rows:
        prompt = _text(task.get("prompt"), "eval.prompt")
        eval_prompts.append((_text(task.get("id"), "eval.id"), normalize(prompt)))
    ids: set[str] = set()
    prompts: dict[str, str] = {}
    groups: dict[str, str] = {}
    for number, row in enumerate(rows, 1):
        try:
            validate_example(row)
            identity, split = row["id"], row["split"]
            if identity in ids:
                raise TrainingDataError(f"duplicate id {identity}")
            ids.add(identity)
            group = row["source_group"]
            if group in groups and groups[group] != split:
                raise TrainingDataError(f"source_group {group} crosses splits")
            groups[group] = split
            prompt = normalize(row["messages"][0]["content"])
            if not prompt:
                raise TrainingDataError("user prompt has no normalized text")
            if prompt in prompts:
                raise TrainingDataError(
                    f"duplicate normalized prompt with {prompts[prompt]}"
                )
            prompts[prompt] = identity
            for message in row["messages"]:
                text = normalize(message["content"])
                for eval_id, eval_prompt in eval_prompts:
                    if text == eval_prompt or (
                        len(eval_prompt) >= 40 and eval_prompt in text
                    ):
                        raise TrainingDataError(
                            f"eval overlap with {eval_id} in {message['role']}"
                        )
            if row["review"]["status"] == "rejected":
                raise TrainingDataError("rejected example cannot enter training data")
            if require_human_review and (
                row["review"]["status"],
                row["review"]["method"],
            ) != ("accepted", "human"):
                raise TrainingDataError(
                    "human acceptance required; automated acceptance is insufficient"
                )
        except TrainingDataError as error:
            raise TrainingDataError(f"row {number}: {error}") from error
    return {
        "examples": len(rows),
        "split_counts": dict(sorted(Counter(row["split"] for row in rows).items())),
        "review_counts": dict(
            sorted(
                Counter(
                    f"{row['review']['method']}:{row['review']['status']}"
                    for row in rows
                ).items()
            )
        ),
        "source_groups": len(groups),
        "eval_tasks": len(eval_rows),
        "human_review_required": require_human_review,
        "overlap_policy": "NFKC/casefold/alphanumeric equality; eval prompt containment when length >= 40",
        "limitations": "No semantic/paraphrase or answer-only leakage proof; provenance/review are declarations, not independently verified rights or human identity.",
    }


@dataclass(frozen=True)
class EncodedExample:
    input_ids: list[int]
    attention_mask: list[int]
    labels: list[int]
    loss_mask: list[int]
    target_start: int
    target_end: int  # exclusive, includes EOS and excludes terminal newline/padding
    unpadded_length: int


def encode_example(
    row: dict[str, Any],
    tokenizer: Any,
    *,
    max_length: int,
    pad_to_length: int | None = None,
) -> EncodedExample:
    """Unshifted labels: causal trainers use logits[:-1] vs labels[1:]."""
    validate_example(row)
    if type(max_length) is not int or max_length <= 0:
        raise TrainingDataError("max_length must be a positive integer")
    if pad_to_length is not None and (
        type(pad_to_length) is not int or not 0 < pad_to_length <= max_length
    ):
        raise TrainingDataError(
            "pad_to_length must be a positive integer <= max_length"
        )
    for message in row["messages"]:
        if any(token in message["content"] for token in tokenizer.all_special_tokens):
            raise TrainingDataError("message contains tokenizer special token")
    options = {"tokenize": False, "enable_thinking": True}
    prefix = tokenizer.apply_chat_template(
        row["messages"][:1], add_generation_prompt=True, **options
    )
    rendered = tokenizer.apply_chat_template(
        row["messages"], add_generation_prompt=False, **options
    )
    eos = tokenizer.eos_token
    if not eos or not rendered.startswith(prefix) or not rendered.endswith(eos + "\n"):
        raise TrainingDataError(
            "unsupported template: missing exact prompt prefix or EOS/newline suffix"
        )
    answer = row["messages"][1]["content"]
    # The pinned Qwen3 template adds an empty thinking block to plain responses.
    completion = "<think>\n\n</think>\n\n" + answer
    if rendered != prefix + completion + eos + "\n":
        raise TrainingDataError(
            "template changed response content or unsupported thinking/control format"
        )
    ids = list(tokenizer.encode(rendered, add_special_tokens=False))
    prefix_ids = list(tokenizer.encode(prefix, add_special_tokens=False))
    through_eos = list(tokenizer.encode(rendered[:-1], add_special_tokens=False))
    start, end = len(prefix_ids), len(through_eos)
    if not start or ids[:start] != prefix_ids or ids[:end] != through_eos:
        raise TrainingDataError(
            "token boundary mismatch; prompt/target masking would be unsafe"
        )
    if start >= end - 1 or through_eos[-1] != tokenizer.eos_token_id:
        raise TrainingDataError("empty loss target or missing EOS")
    # Catch non-roundtripping/unknown-token loss before accepting training text.
    if (
        tokenizer.decode(
            ids, skip_special_tokens=False, clean_up_tokenization_spaces=False
        )
        != rendered
    ):
        raise TrainingDataError("tokenizer does not round-trip rendered chat")
    length = len(ids)
    if length > max_length:
        raise TrainingDataError(
            f"sequence length {length} exceeds max_length {max_length}; truncation forbidden"
        )
    if pad_to_length is not None and pad_to_length < length:
        raise TrainingDataError("pad_to_length would truncate sequence")
    mask = [int(start <= index < end) for index in range(length)]
    labels = [token if selected else IGNORE_INDEX for token, selected in zip(ids, mask)]
    attention = [1] * length
    padding = (pad_to_length or length) - length
    if padding:
        if tokenizer.pad_token_id is None:
            raise TrainingDataError("tokenizer has no padding token")
        ids += [tokenizer.pad_token_id] * padding
        labels += [IGNORE_INDEX] * padding
        mask += [0] * padding
        attention += [0] * padding
    return EncodedExample(ids, attention, labels, mask, start, end, length)
