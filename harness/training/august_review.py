"""Independent prompt-derived checks for A4. Does not import its generator."""

import hashlib
import json
import re
from collections import defaultdict
from decimal import Decimal
from typing import Any


class ContentReviewError(ValueError):
    """An example cannot be accepted by the declared task checker."""


def content_hash(row: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            row["messages"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def _match(pattern: str, text: str):
    match = re.search(pattern, text)
    if not match:
        raise ContentReviewError("prompt does not match its declared task family")
    return match.groups()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def check_content(row: dict[str, Any]) -> dict[str, Any]:
    family = row["source_group"].removeprefix("aug26-family-")
    prompt, answer = [message["content"] for message in row["messages"]]
    expected: str | dict | list
    if family == "position":
        tokens, position = _match(
            r"Tokens: (.+)\nReturn only token number (\d+),", prompt
        )
        expected = tokens.split(" / ")[int(position) - 1]
    elif family == "label_join":
        first, second, third = _match(
            r"first=(\w+), second=(\w+), third=(\w+)\.", prompt
        )
        expected = "|".join([f"first:{first}", f"third:{third}", f"second:{second}"])
    elif family == "wrap":
        value, left, right = _match(
            r"Metin: (.+)\nMetni değiştirmeden başına (.+) ve sonuna (.+) koy\.", prompt
        )
        expected = f"{left}{value}{right}"
    elif family == "deduplicate":
        (seq,) = _match(r"Sequence: (.+)\n", prompt)
        expected = ",".join(dict.fromkeys(seq.split(",")))
    elif family == "prefix_filter":
        (codes,) = _match(r"Codes: (.+)\n", prompt)
        expected = ";".join(code for code in codes.split(",") if code.startswith("R-"))
    elif family == "remove_token":
        seq, remove = _match(r"Input: (.+)\nDelete every occurrence of (\w+)\.", prompt)
        expected = " ".join(word for word in seq.split() if word != remove)
    elif family == "rotate":
        seq, count = _match(r"Items: (.+)\nMove the first (\d+) items?", prompt)
        words = seq.split(",")
        count = int(count)
        from collections import deque

        rotated = deque(words)
        rotated.rotate(-count)
        expected = "|".join(rotated)
    elif family == "mapping":
        (pairs,) = _match(r"Pairs: (.+)\n", prompt)
        expected = {
            key: int(value)
            for key, value in (pair.split("=") for pair in pairs.split(";"))
        }
    elif family == "records":
        (lines,) = _match(r"Rows \(label,count\):\n([\s\S]+)\nReturn", prompt)
        expected = [
            {"label": line.split(",")[0], "count": int(line.split(",")[1])}
            for line in lines.splitlines()
        ]
    elif family == "nested":
        root, code, units = _match(
            r"Flat fields: (\w+)\.code=(\w+);\w+\.units=(\d+)\n", prompt
        )
        expected = {root: {"code": code, "units": int(units)}}
    elif family == "boolean":
        name, active, stock = _match(
            r"Record: name=(\w+); active=(yes|no); stock=(\d+)\n", prompt
        )
        expected = {"name": name, "active": active == "yes", "stock": int(stock)}
    elif family == "project":
        (data,) = _match(r"Input JSON: (.+)\n", prompt)
        original = json.loads(data)
        expected = {key: original[key] for key in ["code", "aisle"]}
    elif family == "group":
        (entries,) = _match(r"Entries: (.+)\n", prompt)
        result = defaultdict(list)
        for entry in entries.split(", "):
            key, value = entry.split(":")
            result[key].append(int(value))
        expected = dict(result)
    elif family == "singleton_arrays":
        (data,) = _match(r"Object: (.+)\n", prompt)
        expected = {key: [value] for key, value in json.loads(data).items()}
    elif family == "card":
        (expected,) = _match(r"; material=(\w+);", prompt)
    elif family == "largest":
        pairs = re.findall(r"(\w+)=(\d+)", prompt.split("\n")[0])
        maximum = max(int(value) for _, value in pairs)
        winners = [key for key, value in pairs if int(value) == maximum]
        if len(winners) != 1:
            raise ContentReviewError("ambiguous maximum")
        expected = winners[0]
    elif family == "catalog":
        people = dict(re.findall(r"item (\w+) was designed by (\w+)", prompt))
        (item,) = _match(r"Who designed item (\w+)", prompt)
        expected = people[item]
    elif family == "schedule":
        rooms = dict(re.findall(r"session (\w+) is in room (\d+)", prompt))
        (session,) = _match(r"assigned to session (\w+)\?", prompt)
        expected = rooms[session]
    elif family == "habitat":
        pairs = dict(re.findall(r"(\w+) türü (\w+) bölgesinde", prompt))
        (species,) = _match(r"rehbere göre (\w+) türünün", prompt)
        expected = pairs[species]
    elif family == "missing":
        if "destination=" in prompt:
            raise ContentReviewError("destination unexpectedly present")
        expected = "unknown"
    elif family == "location_chain":
        item_bins = dict(re.findall(r"item (\w+) is in bin (\w+)", prompt))
        bin_zones = dict(re.findall(r"bin (\w+) is in zone (\w+)", prompt))
        (item,) = _match(r"contains item (\w+)\?", prompt)
        expected = bin_zones[item_bins[item]]
    elif family == "stock":
        start, incoming, outgoing = map(
            int,
            _match(
                r"starts with (\d+) clips, receives (\d+), then ships (\d+)", prompt
            ),
        )
        total = sum([start, incoming, -outgoing])
        expected = f"Calculation: {start} + {incoming} - {outgoing} = {total}\nAnswer: {total} clips"
    elif family == "packages":
        boxes, size, loose = map(
            int,
            _match(
                r"(\d+) sealed boxes with (\d+) beads each and (\d+) loose beads",
                prompt,
            ),
        )
        total = sum([size] * boxes) + loose
        expected = (
            f"Calculation: {boxes} * {size} + {loose} = {total}\nAnswer: {total} beads"
        )
    elif family == "elapsed":
        h1, m1, h2, m2 = map(int, _match(r"from (\d+):(\d+) to (\d+):(\d+)", prompt))
        start, end = h1 * 60 + m1, h2 * 60 + m2
        if end < start:
            raise ContentReviewError("unsupported midnight crossing")
        expected = f"Calculation: {end} - {start} = {end - start}\nAnswer: {end - start} minutes"
    elif family == "discount":
        price, rate = map(
            int, _match(r"costs (\d+) credits before a (\d+)% discount", prompt)
        )
        reduction = Decimal(price) * Decimal(rate) / 100
        if reduction != int(reduction):
            raise ContentReviewError("noninteger discount")
        reduction = int(reduction)
        expected = f"Calculation: {price} - {reduction} = {price - reduction}\nAnswer: {price - reduction} credits"
    elif family == "distance":
        speed, hours = map(
            int, _match(r"constant (\d+) metres per hour for (\d+) hours", prompt)
        )
        total = sum([speed for _ in range(hours)])
        expected = f"Calculation: {speed} * {hours} = {total}\nAnswer: {total} metres"
    elif family == "packing":
        total, size = map(
            int,
            _match(
                r"Pack (\d+) items into boxes that each hold exactly (\d+) items",
                prompt,
            ),
        )
        full = total // size
        left = total - size * full
        expected = f"Calculation: {total} = {size} * {full} + {left}\nAnswer: {full} full boxes, {left} items left"
    elif family == "threshold":
        measurements, threshold = _match(
            r"Measurements: ([\d,]+)\. Count readings greater than or equal to (\d+)",
            prompt,
        )
        selected = [
            value for value in measurements.split(",") if int(value) >= int(threshold)
        ]
        expected = f"Selected: {','.join(selected)}\nAnswer: {len(selected)}"
    else:
        raise ContentReviewError(f"unknown family {family}")
    if isinstance(expected, (dict, list)):
        try:
            observed = json.loads(answer)
        except ValueError as error:
            raise ContentReviewError("invalid JSON answer") from error
        if _json(observed) != _json(expected):
            raise ContentReviewError("wrong JSON values, types or structure")
    elif answer != expected:
        raise ContentReviewError(
            "answer does not satisfy prompt-derived content/format check"
        )
    return {
        "id": row["id"],
        "content_sha256": content_hash(row),
        "family": family,
        "result": "accepted",
        "method": "automated",
        "check": "prompt-derived reference and required output format",
    }
