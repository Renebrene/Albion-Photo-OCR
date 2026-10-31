"""Rebuild public.qwen_value_frequencies from the QWEN base.

One photo contributes at most one vote per value, per kind:
  client, brand, tag  — where the value appears;
  any                 — union of the three, used to rank advertisers when a
                        frame has several billboards.

Dry-run by default: prints the top values and writes nothing. Pass --apply to
replace the table contents in one transaction.

    .venv/bin/python scripts/recompute_qwen_frequencies.py
    .venv/bin/python scripts/recompute_qwen_frequencies.py --apply
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict

from app.ingest.database import get_connection
from app.qwen.crop_aggregation import _compact


def _alias_maps() -> dict[str, dict[str, str]]:
    """kind -> casefold(alias) -> canonical."""

    result: dict[str, dict[str, str]] = {"client": {}, "brand": {}}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(
                "SELECT kind, alias, canonical FROM public.client_aliases"
            )
            for kind, alias, canonical in cur.fetchall():
                if kind in result and alias and canonical:
                    result[kind][str(alias).casefold()] = str(canonical).strip()

    return result


def build_frequencies() -> dict[str, dict[str, tuple[str, int]]]:
    """kind -> key -> (display value, number of distinct photos)."""

    aliases = _alias_maps()
    votes: dict[str, dict[str, set[str]]] = {
        "client": defaultdict(set),
        "brand": defaultdict(set),
        "tag": defaultdict(set),
        "any": defaultdict(set),
    }
    display: dict[str, Counter] = {
        "client": Counter(),
        "brand": Counter(),
        "tag": Counter(),
        "any": Counter(),
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(
                "SELECT photo_id, client, brand, tags "
                "FROM public.photo_qwen WHERE status='DONE'"
            )
            rows = cur.fetchall()

    for photo_id, client, brand, tags in rows:
        values: dict[str, set[str]] = {"client": set(), "brand": set(), "tag": set()}

        for kind, raw in (("client", client), ("brand", brand)):
            text = str(raw or "").strip()
            if text:
                text = aliases[kind].get(text.casefold(), text)
                values[kind].add(text)

        for raw in tags or []:
            text = str(raw or "").strip()
            if text:
                values["tag"].add(text)

        combined = values["client"] | values["brand"] | values["tag"]

        for kind, items in values.items():
            for text in items:
                key = _compact(text)
                votes[kind][key].add(str(photo_id))
                display[kind][(key, text)] += 1

        for text in combined:
            key = _compact(text)
            votes["any"][key].add(str(photo_id))
            display["any"][(key, text)] += 1

    result: dict[str, dict[str, tuple[str, int]]] = {}

    for kind, items in votes.items():
        result[kind] = {}
        for key, photo_ids in items.items():
            spellings = [
                (count, text)
                for (item_key, text), count in display[kind].items()
                if item_key == key
            ]
            # Most frequent spelling becomes the displayed value.
            value = max(spellings, key=lambda item: (item[0], item[1]))[1]
            result[kind][key] = (value, len(photo_ids))

    return result


def write_frequencies(data: dict[str, dict[str, tuple[str, int]]]) -> int:
    rows = [
        (kind, key, value, count)
        for kind, values in data.items()
        for key, (value, count) in values.items()
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.qwen_value_frequencies")
            cur.executemany(
                """
                INSERT INTO public.qwen_value_frequencies
                    (kind, value_key, value, photo_count, computed_at)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                """,
                rows,
            )

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="replace qwen_value_frequencies (default: dry-run)",
    )
    parser.add_argument("--top", type=int, default=10, help="top values to print")
    args = parser.parse_args()

    data = build_frequencies()

    for kind in ("client", "brand", "tag", "any"):
        print(f"\n[{kind}] values: {len(data[kind])}")
        for key, (value, count) in sorted(
            data[kind].items(), key=lambda item: item[1][1], reverse=True
        )[: args.top]:
            print(f"  {count:6d}  {value}  (key={key})")

    if not args.apply:
        print("\nDRY RUN: nothing written. Use --apply to rebuild the table.")
        return

    written = write_frequencies(data)
    print(f"\nWROTE {written} rows to public.qwen_value_frequencies")


if __name__ == "__main__":
    main()
