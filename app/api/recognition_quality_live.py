"""
Живая сводка качества распознавания по последнему прогону гибрида.

Отличие от курируемого снимка (`app/api/recognition_quality.py`): здесь нет
файла-снимка и экспериментов — данные берутся из базы по последнему
завершённому HYBRID-прогону.

Что считается:

* эталон адреса — по **имени файла** (правила сопоставления те же, что в
  `scripts/evaluate_sorting.py`, владелец 17.11.2026); фото без адреса в
  имени в знаменатель точности не входят;
* предсказание — `hybrid_final_id` (адрес после контекста соседей);
* влияние на результат — что решило фото: DINO (лучший кандидат), соседи
  (HYBRID переголосовал) или «DINO не дал ответа» (решили серия/соседи);
* «фото в слепке» — сумма `fingerprints.images_count` активных слепков
  адреса (слепков у адреса может быть несколько);
* «с каким адресом путается» — самый частый неверный адрес среди фото,
  подписанных этим адресом.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.ingest.database import get_connection


def classify_influence(original_fp: str | None, changed: bool) -> str:
    """
    Что определило адрес фото.

    * `dino` — HYBRID оставил выбор DINO (лучший кандидат);
    * `neighbors` — соседи переголосовали (`hybrid_changed`);
    * `no_dino` — DINO не дал ответа, адрес выбрали серия/соседи.
    """

    if original_fp is None:
        return "no_dino"

    return "neighbors" if changed else "dino"


def build_snapshot(
    rows: list[dict[str, Any]],
    *,
    address_names: dict[int, str],
    fingerprint_photos: dict[int, int],
    run_info: dict[str, Any] | None = None,
) -> dict:
    """
    Собрать сводку из строк прогона.

    *rows* — по фото: `photo_id`, `filename`, `expected` (address_id по имени
    файла или None), `predicted` (address_id из `hybrid_final_id` или None),
    `original` (address_id DINO или None), `changed`.
    """

    assigned: Counter[int] = Counter()
    labelled: Counter[int] = Counter()
    correct: Counter[int] = Counter()
    wrong: Counter[int] = Counter()
    influence: dict[int, Counter[str]] = defaultdict(Counter)
    confusion: dict[int, Counter[Any]] = defaultdict(Counter)

    for row in rows:
        predicted = row.get("predicted")
        expected = row.get("expected")

        if predicted is not None:
            assigned[predicted] += 1
            influence[predicted][
                classify_influence(row.get("original"), bool(row.get("changed")))
            ] += 1

        if expected is None:
            continue

        labelled[expected] += 1

        if predicted == expected:
            correct[expected] += 1
        else:
            wrong[expected] += 1
            confusion[expected][predicted] += 1

    addresses: list[dict[str, Any]] = []

    for address_id in set(assigned) | set(labelled):
        total_labelled = labelled.get(address_id, 0)
        total_correct = correct.get(address_id, 0)
        counts = influence.get(address_id) or Counter()

        top_kind = None
        top_share = None

        if counts:
            top_kind, top_count = counts.most_common(1)[0]
            top_share = round(top_count / sum(counts.values()), 3)

        confused = confusion.get(address_id) or Counter()
        confused_with = None

        if confused:
            confused_id, confused_count = confused.most_common(1)[0]
            confused_with = {
                "address_id": confused_id,
                "name": address_names.get(confused_id) if confused_id is not None else "без адреса",
                "count": int(confused_count),
            }

        addresses.append(
            {
                "address_id": int(address_id),
                "name": address_names.get(address_id, str(address_id)),
                "photos": int(assigned.get(address_id, 0)),
                "fingerprint_photos": int(fingerprint_photos.get(address_id, 0)),
                "labelled": int(total_labelled),
                "correct": int(total_correct),
                "wrong": int(wrong.get(address_id, 0)),
                "accuracy": (
                    round(total_correct / total_labelled, 4)
                    if total_labelled
                    else None
                ),
                "influence": (
                    {
                        "kind": top_kind,
                        "share": top_share,
                        "counts": dict(counts),
                    }
                    if top_kind
                    else None
                ),
                "confused_with": confused_with,
            }
        )

    # Ранжирование — по проценту совпадений; адреса без подписанных фото
    # (accuracy None) уходят в конец, дальше — по числу фото и имени.
    addresses.sort(
        key=lambda item: (
            item["accuracy"] is None,
            -(item["accuracy"] or 0.0),
            -item["photos"],
            item["name"].casefold(),
        )
    )

    total_labelled = sum(labelled.values())
    total_correct = sum(correct.values())
    total_wrong = sum(wrong.values())
    no_prediction = sum(1 for row in rows if row.get("predicted") is None)

    return {
        "run": run_info or {},
        "totals": {
            "photos": len(rows),
            "labelled": total_labelled,
            "correct": total_correct,
            "wrong": total_wrong,
            "no_label": len(rows) - total_labelled,
            "no_prediction": no_prediction,
            "accuracy": (
                round(total_correct / total_labelled, 4) if total_labelled else None
            ),
        },
        "addresses": addresses,
    }


class AddressMatcher:
    """
    Быстрое сопоставление имени файла с адресом.

    `expected_address` из `scripts/evaluate_sorting.py` перебирает все адреса;
    на 57 тысячах фото и двух тысячах адресов это минуты. Индекс по первому
    значимому слову оставляет десятки кандидатов — правила те же.
    """

    def __init__(self, addresses: list[tuple[int, str]]) -> None:
        # Приватный токенизатор скрипта: он и задаёт правила сопоставления.
        from scripts.evaluate_sorting import _address_tokens

        self._tokens = _address_tokens
        self.by_token: dict[str, list[tuple[int, str]]] = defaultdict(list)

        for address_id, normalized in addresses:
            for token in set(_address_tokens(normalized)):
                self.by_token[token].append((address_id, normalized))

    def match(self, filename: str) -> int | None:
        from scripts.evaluate_sorting import expected_address

        tokens = set(self._tokens(filename))
        candidates: list[tuple[int, str]] = []
        seen: set[int] = set()

        for token in tokens:
            for item in self.by_token.get(token, ()):
                if item[0] in seen:
                    continue

                seen.add(item[0])
                candidates.append(item)

        if not candidates:
            return None

        return expected_address(filename, candidates)


def _load_rows(hybrid_run_id: int) -> tuple[list[dict[str, Any]], dict[int, str], dict[int, int]]:
    from scripts.evaluate_sorting import load_addresses

    matcher = AddressMatcher(load_addresses())
    address_names = {
        int(address_id): name
        for address_id, name in _address_display_names().items()
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, hybrid_final_id, hybrid_original_id,
                       hybrid_changed
                FROM public.hybrid_results
                WHERE hybrid_run_id = %s AND status = 'DONE'
                """,
                (hybrid_run_id,),
            )
            result_rows = cur.fetchall()

            # Имя файла нужно для эталона, а он — только по подписи.
            photo_ids = [row[0] for row in result_rows]
            filenames: dict[str, str] = {}

            if photo_ids:
                cur.execute(
                    "SELECT photo_id, filename FROM public.photos"
                    " WHERE photo_id = ANY(%s)",
                    (photo_ids,),
                )
                filenames = {row[0]: row[1] for row in cur.fetchall()}

            cur.execute(
                """
                SELECT fingerprint_id, address_id
                FROM public.address_fingerprints
                WHERE active
                """
            )
            fp_to_address = {
                str(fingerprint_id): int(address_id)
                for fingerprint_id, address_id in cur.fetchall()
            }

            cur.execute(
                """
                SELECT af.address_id, COALESCE(sum(f.images_count), 0)
                FROM public.address_fingerprints AS af
                JOIN public.fingerprints AS f
                  ON f.fingerprint_id = af.fingerprint_id AND f.active
                WHERE af.active
                GROUP BY af.address_id
                """
            )
            fingerprint_photos = {
                int(address_id): int(count) for address_id, count in cur.fetchall()
            }

    rows: list[dict[str, Any]] = []

    for photo_id, final_fp, original_fp, changed in result_rows:
        filename = filenames.get(photo_id) or ""
        rows.append(
            {
                "photo_id": photo_id,
                "filename": filename,
                "expected": matcher.match(filename) if filename else None,
                "predicted": fp_to_address.get(str(final_fp)) if final_fp else None,
                "original": fp_to_address.get(str(original_fp)) if original_fp else None,
                "changed": bool(changed),
            }
        )

    return rows, address_names, fingerprint_photos


def _address_display_names() -> dict[int, str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT address_id, COALESCE(NULLIF(btrim(simple_address), ''),"
                " legal_address) FROM public.address_directory WHERE active"
            )
            return {
                int(address_id): (name or "").strip()
                for address_id, name in cur.fetchall()
            }


def recent_runs(limit: int = 20) -> list[dict]:
    """Последние завершённые HYBRID-прогоны для выбора в интерфейсе."""

    limit = max(1, min(int(limit), 100))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT hybrid_run_id, dino_batch_id, total_count,
                       completed_count, finished_at
                FROM public.hybrid_runs
                WHERE status = 'DONE'
                ORDER BY hybrid_run_id DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "hybrid_run_id": int(run_id),
            "dino_batch_id": int(batch_id) if batch_id is not None else None,
            "photos": int(total or 0),
            "completed": int(completed or 0),
            "finished_at": finished_at.isoformat() if finished_at else None,
        }
        for run_id, batch_id, total, completed, finished_at in rows
    ]


def live_snapshot(hybrid_run_id: int | None = None) -> dict:
    """
    Сводка по прогону HYBRID: указанному или последнему завершённому.

    Последний прогон может быть маленьким (сортировка только новых фото),
    поэтому интерфейс даёт выбрать и предыдущий, более полный.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            if hybrid_run_id is not None:
                cur.execute(
                    """
                    SELECT hybrid_run_id, dino_batch_id, finished_at,
                           total_count
                    FROM public.hybrid_runs
                    WHERE hybrid_run_id = %s AND status = 'DONE'
                    """,
                    (int(hybrid_run_id),),
                )
            else:
                cur.execute(
                    """
                    SELECT hybrid_run_id, dino_batch_id, finished_at,
                           total_count
                    FROM public.hybrid_runs
                    WHERE status = 'DONE'
                    ORDER BY hybrid_run_id DESC
                    LIMIT 1
                    """
                )
            run = cur.fetchone()

            cur.execute(
                "SELECT max(finished_at) FROM public.dino_batches"
                " WHERE status = 'DONE'"
            )
            last_sort_at = cur.fetchone()[0]

            cur.execute(
                "SELECT max(finished_at) FROM public.hybrid_runs"
                " WHERE status = 'DONE'"
            )
            last_hybrid_at = cur.fetchone()[0]

    run_info = {
        "hybrid_run_id": int(run[0]) if run else None,
        "dino_batch_id": int(run[1]) if run and run[1] is not None else None,
        "photos": int(run[3] or 0) if run else 0,
        "hybrid_finished_at": run[2].isoformat() if run and run[2] else None,
        "last_sort_at": last_sort_at.isoformat() if last_sort_at else None,
        "last_hybrid_at": last_hybrid_at.isoformat() if last_hybrid_at else None,
    }

    if run is None:
        return build_snapshot([], address_names={}, fingerprint_photos={}, run_info=run_info)

    rows, address_names, fingerprint_photos = _load_rows(int(run[0]))

    return build_snapshot(
        rows,
        address_names=address_names,
        fingerprint_photos=fingerprint_photos,
        run_info=run_info,
    )
