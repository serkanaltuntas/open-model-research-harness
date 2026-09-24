"""Deterministic original microtasks for A4; this module never reads eval data."""

import json
import random
from typing import Any

WORDS = (
    "velrin",
    "tavora",
    "nespil",
    "korven",
    "lumira",
    "felton",
    "darsil",
    "ponvek",
    "rulven",
    "mastek",
    "zivora",
    "belkir",
    "sovrin",
    "halvek",
    "tirpon",
    "vaskel",
    "melkur",
    "nivren",
    "solpek",
    "verdan",
    "kalpon",
    "rimvek",
    "lorpin",
    "zenvar",
)


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def make_task(family: str, rng: random.Random, index: int) -> tuple[str, str]:
    """Produce prompt/answer pairs from explicit finite task definitions."""
    w = rng.sample(WORDS, 6)
    a, b, c = rng.sample(range(11, 97), 3)
    if family == "position":
        pos = index % 5 + 1
        return (
            f"Tokens: {' / '.join(w[:5])}\nReturn only token number {pos}, counting from 1 on the left. Do not add punctuation.",
            w[pos - 1],
        )
    if family == "label_join":
        return (
            f"Use these values: first={w[0]}, second={w[1]}, third={w[2]}.\nOutput exactly first:<value>|third:<value>|second:<value>, substituting the values. No spaces or commentary.",
            f"first:{w[0]}|third:{w[2]}|second:{w[1]}",
        )
    if family == "wrap":
        value = f"{w[0]}-{a}"
        left, right = ("[[", "]]") if index % 2 else ("{", "}")
        return (
            f"Metin: {value}\nMetni değiştirmeden başına {left} ve sonuna {right} koy. Yalnızca sonucu yaz; boşluk ekleme.",
            left + value + right,
        )
    if family == "deduplicate":
        seq = [w[0], w[1], w[0], w[2], w[1], w[3], w[2]]
        return (
            f"Sequence: {','.join(seq)}\nKeep only the first occurrence of each token, preserving order. Respond as comma-separated tokens without spaces.",
            ",".join(w[:4]),
        )
    if family == "prefix_filter":
        seq = [f"R-{a}", f"S-{b}", f"R-{c}", f"T-{a + b}"]
        return (
            f"Codes: {','.join(seq)}\nKeep only codes whose prefix is R-, in the given order. Reply with the selected codes separated by one semicolon, with no spaces.",
            f"R-{a};R-{c}",
        )
    if family == "remove_token":
        seq = [w[0], w[1], w[2], w[1], w[3]]
        return (
            f"Input: {' '.join(seq)}\nDelete every occurrence of {w[1]}. Preserve the other tokens and their order. Return only the remaining tokens separated by single spaces.",
            " ".join([w[0], w[2], w[3]]),
        )
    if family == "rotate":
        k = index % 3 + 1
        seq = w[:5]
        return (
            f"Items: {','.join(seq)}\nMove the first {k} {'item' if k == 1 else 'items'} to the end, keeping their relative order. Return only the resulting items joined with |.",
            "|".join(seq[k:] + seq[:k]),
        )
    if family == "mapping":
        values = {w[0]: a, w[1]: b, w[2]: c}
        return (
            f"Pairs: {w[0]}={a};{w[1]}={b};{w[2]}={c}\nConvert the pairs to one JSON object. Values must be integers. Return JSON only.",
            compact(values),
        )
    if family == "records":
        return (
            f"Rows (label,count):\n{w[0]},{a}\n{w[1]},{b}\nReturn a JSON array of objects with exactly label (string) and count (integer), preserving row order. No Markdown.",
            compact([{"label": w[0], "count": a}, {"label": w[1], "count": b}]),
        )
    if family == "nested":
        return (
            f"Flat fields: {w[0]}.code={w[1]};{w[0]}.units={a}\nReturn one JSON object nested under {w[0]}; code is a string and units an integer. Include no other fields or text.",
            compact({w[0]: {"code": w[1], "units": a}}),
        )
    if family == "boolean":
        flag = index % 2 == 0
        return (
            f"Record: name={w[0]}; active={'yes' if flag else 'no'}; stock={a}\nReturn JSON with name as a string, active as a JSON boolean (yes=true, no=false), and stock as an integer. JSON only.",
            compact({"name": w[0], "active": flag, "stock": a}),
        )
    if family == "project":
        obj = {"code": w[0], "units": a, "color": w[1], "aisle": b}
        return (
            f"Input JSON: {compact(obj)}\nReturn a JSON object containing only the code and aisle fields, preserving their values and types. No explanation.",
            compact({"code": w[0], "aisle": b}),
        )
    if family == "group":
        return (
            f"Entries: {w[0]}:{a}, {w[1]}:{b}, {w[0]}:{c}\nGroup integers by key in a JSON object whose values are arrays. Preserve encounter order within each array. JSON only.",
            compact({w[0]: [a, c], w[1]: [b]}),
        )
    if family == "singleton_arrays":
        return (
            f"Object: {compact({w[0]: a, w[1]: b})}\nWrap each value in a one-element JSON array while keeping the keys. Return only the converted JSON object.",
            compact({w[0]: [a], w[1]: [b]}),
        )
    if family == "card":
        return (
            f"Fictional equipment card: code={w[0]}; material={w[1]}; mass={a} grams; shelf={b}.\nAccording only to this card, what is the material? Answer with the material value only.",
            w[1],
        )
    if family == "largest":
        values = {w[0]: a, w[1]: b, w[2]: c}
        return (
            f"Fictional tank capacities in litres: {w[0]}={a}, {w[1]}={b}, {w[2]}={c}.\nWhich tank has the largest capacity? Return its name only.",
            max(values, key=values.get),
        )
    if family == "catalog":
        return (
            f"Invented catalog: item {w[0]} was designed by {w[1]}; item {w[2]} was designed by {w[3]}.\nWho designed item {w[2]} according to the catalog? Answer only with the designer name.",
            w[3],
        )
    if family == "schedule":
        return (
            f"Fictional event board: session {w[0]} is in room {a}; session {w[1]} is in room {b}; session {w[2]} is in room {c}.\nWhat room is assigned to session {w[1]}? Reply with the room number only.",
            str(b),
        )
    if family == "habitat":
        return (
            f"Kurgu rehber: {w[0]} türü {w[1]} bölgesinde, {w[2]} türü {w[3]} bölgesinde yaşar.\nYalnızca bu rehbere göre {w[0]} türünün yaşadığı bölgenin adını yaz.",
            w[1],
        )
    if family == "missing":
        return (
            f"Fictional parcel card: code={w[0]}; mass={a} grams; color={w[1]}. No other information is available.\nWhat is the parcel's destination? If the card does not state it, reply exactly unknown. Otherwise give only the destination.",
            "unknown",
        )
    if family == "location_chain":
        return (
            f"Fictional storage facts: item {w[0]} is in bin {w[1]}; bin {w[1]} is in zone {w[2]}; item {w[3]} is in zone {w[4]}.\nWhich zone contains item {w[0]}? Return the zone name only.",
            w[2],
        )
    if family == "stock":
        start, incoming, outgoing = a + 100, b, c
        total = start + incoming - outgoing
        return (
            f"A fictional store starts with {start} clips, receives {incoming}, then ships {outgoing}. How many clips remain?\nUse exactly two lines: Calculation: <arithmetic>; then Answer: <integer> clips. Do not add other text.",
            f"Calculation: {start} + {incoming} - {outgoing} = {total}\nAnswer: {total} clips",
        )
    if family == "packages":
        boxes, per, loose = index + 3, a, b
        total = boxes * per + loose
        return (
            f"There are {boxes} sealed boxes with {per} beads each and {loose} loose beads. Find the total number of beads.\nUse exactly two lines: Calculation: <arithmetic>; then Answer: <integer> beads.",
            f"Calculation: {boxes} * {per} + {loose} = {total}\nAnswer: {total} beads",
        )
    if family == "elapsed":
        start = 8 * 60 + a
        duration = b + 20
        end = start + duration
        start_text = f"{start // 60:02d}:{start % 60:02d}"
        end_text = f"{end // 60:02d}:{end % 60:02d}"
        return (
            f"A machine runs from {start_text} to {end_text} on the same morning. How many minutes does it run?\nUse exactly two lines: Calculation: <end minutes since midnight> - <start minutes since midnight> = <difference>; then Answer: <integer> minutes.",
            f"Calculation: {end} - {start} = {duration}\nAnswer: {duration} minutes",
        )
    if family == "discount":
        price = (index + 2) * 100
        rate = [10, 15, 20, 25, 30][index % 5]
        reduction = price * rate // 100
        total = price - reduction
        return (
            f"An item costs {price} credits before a {rate}% discount. There are no other charges. What is the final price?\nUse exactly two lines: Calculation: <original> - <discount amount> = <final>; then Answer: <integer> credits.",
            f"Calculation: {price} - {reduction} = {total}\nAnswer: {total} credits",
        )
    if family == "distance":
        speed = a
        hours = index + 2
        total = speed * hours
        return (
            f"A cart travels at a constant {speed} metres per hour for {hours} hours without stopping. Find its distance.\nUse exactly two lines: Calculation: <speed> * <hours> = <distance>; then Answer: <integer> metres.",
            f"Calculation: {speed} * {hours} = {total}\nAnswer: {total} metres",
        )
    if family == "packing":
        total = a + 50
        size = index + 6
        q, r = divmod(total, size)
        return (
            f"Pack {total} items into boxes that each hold exactly {size} items. Count only full boxes and leave the rest unpacked.\nUse exactly two lines: Calculation: <total> = <size> * <full boxes> + <leftover>; then Answer: <full boxes> full boxes, <leftover> items left.",
            f"Calculation: {total} = {size} * {q} + {r}\nAnswer: {q} full boxes, {r} items left",
        )
    if family == "threshold":
        vals = [a, b, c, a + 100]
        threshold = index + 40
        selected = [v for v in vals if v >= threshold]
        return (
            f"Measurements: {','.join(map(str, vals))}. Count readings greater than or equal to {threshold}.\nUse exactly two lines: Selected: <comma-separated qualifying readings in input order, no spaces>; then Answer: <integer>.",
            f"Selected: {','.join(map(str, selected))}\nAnswer: {len(selected)}",
        )
    raise ValueError(f"unknown family {family}")


def build_candidates(
    recipe: dict[str, Any], recipe_hash: str, generator_hash: str
) -> list[dict[str, Any]]:
    rows = []
    for family_index, family in enumerate(recipe["families"]):
        count = recipe[f"{family['split']}_per_family"]
        rng = random.Random(recipe["seed"] + family_index * 1009)
        for index in range(count):
            prompt, answer = make_task(family["name"], rng, index)
            identity = f"aug26-{family['name']}-{index + 1:03d}"
            rows.append(
                {
                    "schema_version": "sft-v1",
                    "id": identity,
                    "messages": [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": answer},
                    ],
                    "behavior": family["behavior"],
                    "source_group": f"aug26-family-{family['name']}",
                    "split": family["split"],
                    "provenance": {
                        "kind": "synthetic",
                        "source": f"harness/training/august_dataset.py#{family['name']}:{index + 1}",
                        "license": "CC-BY-4.0",
                        "rights_basis": "Original project microtasks and programmatically computed answers; no imported corpus. See LICENSE-DATA and dataset card.",
                        "generation": {
                            "producer": "august-deterministic-generator-v1",
                            "model_revision": "not-applicable: no model inference; templates authored with assistant help",
                            "recipe": f"configs/data/august_sft_v1.json sha256:{recipe_hash}; generator sha256:{generator_hash}",
                        },
                        "transformation": None,
                    },
                    "review": {
                        "status": "unreviewed",
                        "method": "none",
                        "reviewer": None,
                        "reviewed_at": None,
                        "note": "Candidate; automated content review runs separately.",
                    },
                }
            )
    return rows
