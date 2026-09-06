#!/usr/bin/env python3

import csv
import json
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPORT = PROJECT / "output/neighbor_v37/neighbor_decision.csv"

MODEL = "qwen3:4b"

# Порог для явной неопределенности
MARGIN_HARD = 0.005

# Сколько кадров брать вокруг спорной точки
CONTEXT = 5


def load_rows():
    with open(REPORT, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    rows.sort(
        key=lambda r: int(
            "".join(c for c in Path(r["image"]).stem if c.isdigit())
        )
    )

    return rows


def find_uncertain_zones(rows):
    """
    Ищем:
      1. очень маленький margin
      2. короткие скачки TOP1
      3. oscillation между двумя кандидатами
    """

    triggers = set()

    # 1. Очень маленький margin
    for i, r in enumerate(rows):
        if float(r["margin"]) < MARGIN_HARD:
            triggers.add(i)

    # 2. TOP1 меняется между соседними кадрами
    for i in range(1, len(rows)):
        a = int(rows[i - 1]["v33"])
        b = int(rows[i]["v33"])

        if a != b:
            triggers.add(i)
            triggers.add(i - 1)

    # Объединяем близкие точки в зоны
    if not triggers:
        return []

    indices = sorted(triggers)

    zones = []
    start = indices[0]
    prev = indices[0]

    for idx in indices[1:]:
        if idx - prev <= 3:
            prev = idx
        else:
            zones.append((start, prev))
            start = idx
            prev = idx

    zones.append((start, prev))

    # Расширяем контекст
    result = []

    for start, end in zones:
        start = max(0, start - CONTEXT)
        end = min(len(rows) - 1, end + CONTEXT)

        # Не создаём дубликаты пересекающихся зон
        if result and start <= result[-1][1] + 1:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))

    return result


def build_zone(rows, start, end):
    zone = []

    for i in range(start, end + 1):
        r = rows[i]

        zone.append({
            "index": i,
            "image": r["image"],
            "top1": int(r["v33"]),
            "top2": int(r["second"]),
            "margin": round(float(r["margin"]), 6),
        })

    return zone


def ask_llm(zone):
    candidates = sorted({
        x["top1"] for x in zone
    } | {
        x["top2"] for x in zone
    })

    payload = {
        "task": (
            "Determine the most likely address/fingerprint for the "
            "uncertain sequence. The numbers are candidate address IDs. "
            "Choose ONLY from the supplied candidates. "
            "Use sequence continuity and TOP1/TOP2 margins. "
            "Do not invent an ID."
        ),
        "candidates": candidates,
        "sequence": zone,
        "output_format": {
            "decision": "integer candidate ID or null",
            "confidence": "number from 0 to 1",
            "action": "keep_original or override"
        }
    }

    prompt = f"""
You are a post-processing judge for an image recognition system.

The primary vision system has already produced TOP1 and TOP2 candidates.

Your job is NOT to recognize the image.
Your job is ONLY to resolve ambiguity using the sequence.

Rules:
1. Choose only an ID from the supplied candidate list.
2. Prefer a stable sequence over an isolated TOP1 outlier.
3. If the evidence is insufficient, use action="keep_original".
4. Never invent a new ID.
5. Return ONLY valid JSON.
6. "decision" is the address ID you believe is correct for the
   central uncertain area.
7. Confidence must be between 0 and 1.

Candidate IDs:
{json.dumps(candidates, ensure_ascii=False)}

Sequence:
{json.dumps(zone, ensure_ascii=False, indent=2)}

Return:
{{
  "decision": null,
  "confidence": 0.0,
  "action": "keep_original"
}}
"""

    result = subprocess.run(
        [
            "ollama",
            "run",
            MODEL,
            prompt,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return result.stdout.strip()


def main():
    print("=" * 80)
    print("LLM RESOLVER V01 — DRY RUN")
    print("=" * 80)
    print(f"Model: {MODEL}")
    print(f"Input: {REPORT}")
    print()

    rows = load_rows()

    print(f"Images: {len(rows)}")

    zones = find_uncertain_zones(rows)

    print(f"Candidate zones: {len(zones)}")
    print()

    for n, (start, end) in enumerate(zones, 1):

        zone = build_zone(rows, start, end)

        print("=" * 80)
        print(f"ZONE {n}/{len(zones)}")
        print(
            f"frames: {start}-{end} "
            f"({len(zone)} images)"
        )
        print("=" * 80)

        for x in zone:
            print(
                f"{x['index']:3d} "
                f"{x['image']:15s} "
                f"TOP1={x['top1']:>2} "
                f"TOP2={x['top2']:>2} "
                f"margin={x['margin']:.6f}"
            )

        print()
        print("--- QWEN3:4B ---")

        answer = ask_llm(zone)

        print(answer)
        print()

    print("=" * 80)
    print("DRY RUN COMPLETE")
    print("NO FILES WERE MODIFIED")
    print("=" * 80)


if __name__ == "__main__":
    main()
