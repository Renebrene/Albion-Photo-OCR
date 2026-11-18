"""CLIP-поиск похожих объявлений по кропам щитов (визуальная близость).

Индекс файловый, продуктовая зона ``data/clip/`` (SCENE_CLIP_ROOT):

- ``clip_index.faiss`` — IndexFlatIP, L2-нормализованные 512-d векторы
  (inner product == косинус);
- ``clip_meta.jsonl`` — строка на вектор: region_id, photo_id, crop_path;
  строка i соответствует вектору i индекса;
- ``index_info.json`` — модель, время сборки, число векторов.

Запрос по сохранённому region_id не требует модели: вектор достаётся из
индекса (IndexFlatIP.reconstruct). Модель openai/clip-vit-base-patch32
загружается лениво и только для поиска по загруженному файлу; всегда CPU —
GPU остаётся за DINO/QWEN (см. docs/clip_search.txt).
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from app.core.config import settings
from app.ingest.database import get_connection

CLIP_DIR = Path(os.getenv("SCENE_CLIP_ROOT", str(settings.data_dir / "clip")))
INDEX_FILE = CLIP_DIR / "clip_index.faiss"
META_FILE = CLIP_DIR / "clip_meta.jsonl"
INFO_FILE = CLIP_DIR / "index_info.json"
# Очередь реального времени: воркеры дописывают векторы новых кропов,
# сервис поглощает их при первом же поиске (docs/clip_search.txt §5).
PENDING_FILE = CLIP_DIR / "pending.jsonl"

MODEL_ID = "openai/clip-vit-base-patch32"
EMB_DIM = 512
UPLOAD_LIMIT_BYTES = 10 * 1024 * 1024

# Порог сброса поглощённого из pending на диск: векторы или секунды. До
# порога новые векторы живут только в памяти процесса (поиск их уже видит),
# pending-файл очищается только после успешной публикации — падение процесса
# ничего не теряет.
PERSIST_THRESHOLD_VECTORS = 100
PERSIST_INTERVAL_SEC = 600
# Пул кандидатов при дата-фильтре: ближайшие top_k могут не попасть в
# диапазон, поэтому ищем с запасом и режем после фильтрации.
DAYS_POOL_MULTIPLIER = 4
DAYS_POOL_MAX = 200


class ClipIndexUnavailable(RuntimeError):
    """Индекс не собран или повреждён — поиск невозможен."""


class _State:
    """Ленивый синглтон: индекс + мета грузятся при первом запросе."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.index = None
        self.rows: list[dict] = []
        self.by_region: dict[int, int] = {}
        # Первый кроп каждого фото (минимальный region_id встречается первым:
        # мета собирается ORDER BY region_id) — для поиска «Похожие» по фото.
        self.by_photo: dict[str, int] = {}
        self.info: dict = {}
        self.loaded = False
        # Поглощено из pending, но ещё не сброшено на диск.
        self.pending_absorbed = 0
        self.pending_first_ts: float | None = None

    def ensure(self) -> None:
        if self.loaded:
            return
        with self.lock:
            if self.loaded:
                return
            if not INDEX_FILE.is_file() or not META_FILE.is_file():
                # Пути наружу не раскрываем: только имя отсутствующего файла.
                raise ClipIndexUnavailable(
                    f"CLIP-индекс не собран: нет {INDEX_FILE.name} "
                    "(scripts/clip_rebuild.py)"
                )
            import faiss

            index = faiss.read_index(str(INDEX_FILE))
            rows: list[dict] = []
            by_region: dict[int, int] = {}
            by_photo: dict[str, int] = {}
            with META_FILE.open(encoding="utf-8") as handle:
                for position, line in enumerate(handle):
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    rows.append(row)
                    by_region[int(row["region_id"])] = position
                    by_photo.setdefault(str(row["photo_id"]), position)
            if index.ntotal != len(rows):
                # Частично заменённые файлы после сбоя ребилда: поиск по
                # рассогласованному индексу даёт неверные region_id.
                raise ClipIndexUnavailable(
                    f"CLIP-индекс рассогласован: векторов {index.ntotal}, "
                    f"мета-строк {len(rows)} — пересоберите (scripts/clip_rebuild.py)"
                )
            info: dict = {}
            if INFO_FILE.is_file():
                try:
                    info = json.loads(INFO_FILE.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    info = {}
            self.index = index
            self.rows = rows
            self.by_region = by_region
            self.by_photo = by_photo
            self.info = info
            self.loaded = True


_state = _State()


def _ensure_model():
    """CLIP-модель на CPU; импорт torch ленивый — только для поиска по файлу."""

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor

    holder = getattr(_ensure_model, "_holder", None)
    if holder is not None:
        return holder

    with _state.lock:
        holder = getattr(_ensure_model, "_holder", None)
        if holder is not None:
            return holder

        model = CLIPModel.from_pretrained(MODEL_ID).to("cpu").eval()
        processor = CLIPProcessor.from_pretrained(MODEL_ID)
        holder = (model, processor, torch, Image)
        _ensure_model._holder = holder
        return holder


def embed_image(path: str | Path) -> list[float]:
    """L2-нормализованный 512-d вектор загруженного изображения."""

    model, processor, torch, Image = _ensure_model()
    with Image.open(path) as image:
        inputs = processor(images=image.convert("RGB"), return_tensors="pt")
    with torch.inference_mode():
        output = model.get_image_features(**inputs)
        # transformers 5.x: проекция в pooler_output.
        vector = getattr(output, "pooler_output", output)
        vector = vector[0]
    normalized = torch.nn.functional.normalize(vector, dim=-1)
    return [float(x) for x in normalized.tolist()]


def queue_region(
    region_id: int,
    photo_id: str,
    crop_path: str,
    vector: list[float],
) -> None:
    """Вектор нового кропа → pending-очередь (append под fcntl-lock).

    Вызывается из воркеров сразу после создания кропа; одиночный append
    защищён блокировкой, чтобы параллельные воркеры не перемешали строки.
    Ошибки не глотаются здесь — решение (продолжить детекцию) принимает
    вызывающий код.
    """

    import base64
    import fcntl

    import numpy as np

    raw = np.asarray(vector, dtype="<f4").tobytes()
    line = json.dumps(
        {
            "region_id": int(region_id),
            "photo_id": str(photo_id),
            "crop_path": str(crop_path),
            "vector": base64.b64encode(raw).decode("ascii"),
        },
        ensure_ascii=False,
    )
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    with PENDING_FILE.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(line + "\n")
        handle.flush()
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_pending() -> tuple[list[dict], int]:
    """Строки pending-файла и конечное смещение (для вычёркивания)."""

    if not PENDING_FILE.is_file():
        return [], 0

    items: list[dict] = []
    with PENDING_FILE.open("rb") as handle:
        data = handle.read()
        end_offset = handle.tell()

    for line in data.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except ValueError:
            continue  # битая строка от сбоя записи — просто пропустить

    return items, end_offset


def _consume_pending_prefix(end_offset: int) -> None:
    """Вычеркнуть поглощённый префикс pending-файла, сохранив новые строки."""

    import fcntl

    if not PENDING_FILE.is_file() or end_offset <= 0:
        return

    with PENDING_FILE.open("r+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            if size > end_offset:
                handle.seek(end_offset)
                rest = handle.read()
                handle.seek(0)
                handle.truncate(0)
                handle.write(rest)
            else:
                handle.truncate(0)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _persist_state_locked() -> None:
    """Сбросить текущее состояние индекса на диск. Lock _state уже держится."""

    import faiss
    import numpy as np
    from datetime import datetime as _dt, timezone as _tz

    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_emb = CLIP_DIR / "clip_embeddings.tmp.npy"
    tmp_meta = CLIP_DIR / "clip_meta.jsonl.tmp"
    tmp_index = CLIP_DIR / "clip_index.faiss.tmp"
    tmp_info = CLIP_DIR / "index_info.json.tmp"

    # IndexFlat хранит сырые векторы: полная матрица достаётся одним вызовом.
    emb = _state.index.reconstruct_n(0, _state.index.ntotal)
    np.save(tmp_emb, emb)
    with tmp_meta.open("w", encoding="utf-8") as handle:
        for row in _state.rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    faiss.write_index(_state.index, str(tmp_index))
    info = {
        **_state.info,
        "model": _state.info.get("model", MODEL_ID),
        "built_at": _dt.now(_tz.utc).isoformat(timespec="seconds"),
        "vectors": int(_state.index.ntotal),
        "mode": "live-append",
    }
    tmp_info.write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    os.replace(tmp_emb, CLIP_DIR / "clip_embeddings.npy")
    os.replace(tmp_meta, META_FILE)
    os.replace(tmp_index, INDEX_FILE)
    os.replace(tmp_info, INFO_FILE)


def _absorb_pending() -> None:
    """Догнать pending-очередь: в память сразу, на диск — порогом.

    Идемпотентно по region_id: повторные строки пропускаются, поэтому сбой
    между поглощением и публикацией безопасен — при следующем заходе строки
    просто пропустятся, а pending очищается только после успешной записи
    файлов индекса на диск.
    """

    if not PENDING_FILE.is_file():
        return

    import base64

    import numpy as np

    try:
        _state.ensure()
    except ClipIndexUnavailable:
        # Индекса нет — пусть ночной ребилд собирает с нуля.
        return

    items, end_offset = _read_pending()
    if not items:
        return

    with _state.lock:
        fresh_rows: list[dict] = []
        fresh_vecs: list[np.ndarray] = []

        for item in items:
            try:
                region_id = int(item["region_id"])
            except (KeyError, TypeError, ValueError):
                continue
            if region_id in _state.by_region:
                continue
            try:
                vec = np.frombuffer(
                    base64.b64decode(item["vector"]), dtype="<f4"
                ).astype("float32")
            except (KeyError, ValueError):
                continue
            if vec.shape[0] != int(_state.index.d):
                continue
            fresh_rows.append(
                {
                    "region_id": region_id,
                    "photo_id": str(item.get("photo_id") or ""),
                    "crop_path": str(item.get("crop_path") or ""),
                }
            )
            fresh_vecs.append(vec)

        if not fresh_rows:
            if _state.pending_absorbed == 0:
                # В файле только строки, уже лежащие в индексе на диске
                # (пережиток сбоя между публикацией и вычёркиванием):
                # можно безопасно вычеркнуть.
                _consume_pending_prefix(end_offset)
            return

        _state.index.add(np.stack(fresh_vecs))
        base_position = len(_state.rows)
        for offset, row in enumerate(fresh_rows):
            position = base_position + offset
            _state.rows.append(row)
            _state.by_region[row["region_id"]] = position
            _state.by_photo.setdefault(row["photo_id"], position)

        _state.pending_absorbed += len(fresh_rows)
        if _state.pending_first_ts is None:
            _state.pending_first_ts = time.time()

        if not _persist_if_due_locked():
            return
        _consume_pending_prefix(end_offset)


def _persist_if_due_locked() -> bool:
    """Сброс на диск по порогу; False = пока рано или сброс не удался.

    Вызывается с уже захваченным lock _state. Отдельно обрабатывает случай
    «новых строк нет, но память уже содержит непublished векторы» — без этого
    хвост очереди мог бы не сбрасываться, пока не придёт следующий кроп.
    """

    now = time.time()
    due = (
        _state.pending_absorbed >= PERSIST_THRESHOLD_VECTORS
        or (
            _state.pending_absorbed > 0
            and _state.pending_first_ts is not None
            and now - _state.pending_first_ts >= PERSIST_INTERVAL_SEC
        )
    )
    if not due:
        return False

    try:
        _persist_state_locked()
    except Exception:  # noqa: BLE001 - поиск живёт в памяти и так
        return False

    _state.pending_absorbed = 0
    _state.pending_first_ts = None
    return True


def _search(vector, top_k: int, *, exclude_photo_id: str | None = None) -> list[dict]:
    """Косинусный поиск по индексу; меты строки маппятся на результат."""

    import numpy as np

    _state.ensure()
    with _state.lock:
        query = np.asarray(vector, dtype="float32")[None, :]
        # +1 запас на сам запрос, отфильтрованный ниже.
        scores, hits = _state.index.search(query, max(1, top_k) + 1)

    matches: list[dict] = []
    for score, position in zip(scores[0].tolist(), hits[0].tolist()):
        if position < 0 or position >= len(_state.rows):
            continue
        row = _state.rows[position]
        if exclude_photo_id is not None and str(row.get("photo_id")) == exclude_photo_id:
            continue
        matches.append(
            {
                "region_id": int(row["region_id"]),
                "photo_id": str(row["photo_id"]),
                "crop_path": str(row.get("crop_path") or ""),
                "score": round(float(score), 4),
            }
        )
        if len(matches) >= top_k:
            break
    return matches


def _enrich(matches: list[dict]) -> list[dict]:
    """Адрес, поля QWEN и даты для найденных регионов (один запрос на батч)."""

    if not matches:
        return matches

    region_ids = [match["region_id"] for match in matches]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.region_id, r.crop_index,
                       COALESCE(
                           ov.address_id,
                           (
                               SELECT af.address_id
                               FROM public.hybrid_results AS h
                               JOIN public.address_fingerprints AS af
                                 ON af.fingerprint_id = h.hybrid_final_id
                                AND af.active
                               WHERE h.photo_id = r.photo_id
                                 AND h.status = 'DONE'
                               ORDER BY h.finished_at DESC NULLS LAST,
                                        h.hybrid_run_id DESC
                               LIMIT 1
                           )
                       ) AS address_id,
                       ad.legal_address,
                       ad.simple_address,
                       q.brand,
                       q.client,
                       p.taken_at,
                       p.created_at
                FROM public.photo_regions AS r
                JOIN public.photos AS p
                      ON p.photo_id = r.photo_id
                LEFT JOIN public.photo_address_overrides AS ov
                       ON ov.photo_id = r.photo_id
                LEFT JOIN public.address_directory AS ad
                       ON ad.address_id = COALESCE(
                           ov.address_id,
                           (
                               SELECT af.address_id
                               FROM public.hybrid_results AS h
                               JOIN public.address_fingerprints AS af
                                 ON af.fingerprint_id = h.hybrid_final_id
                                AND af.active
                               WHERE h.photo_id = r.photo_id
                                 AND h.status = 'DONE'
                               ORDER BY h.finished_at DESC NULLS LAST,
                                        h.hybrid_run_id DESC
                               LIMIT 1
                           )
                       )
                LEFT JOIN public.photo_qwen AS q
                       ON q.photo_id = r.photo_id
                WHERE r.region_id = ANY(%s)
                """,
                (region_ids,),
            )
            rows = {int(row[0]): row for row in cur.fetchall()}

    for match in matches:
        row = rows.get(match["region_id"])
        if row is None:
            continue
        match.update(
            {
                "crop_index": int(row[1] or 0),
                "address_id": int(row[2]) if row[2] is not None else None,
                "address": row[3] or row[4],
                "brand": row[5],
                "client": row[6],
                # Даты съёмки и загрузки — для карточки «Похожие».
                "taken_at": _iso(row[7]),
                "created_at": _iso(row[8]),
            }
        )
    return matches


def _iso(value: object) -> str | None:
    """datetime → строка ISO (JSON-безопасно); None проходит насквозь."""

    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat(timespec="seconds")
    return str(value)


def _filter_by_days(
    matches: list[dict], days: int, *, top_k: int
) -> list[dict]:
    """Оставить совпадения с датой съёмки в окне `days`; потом резать top_k."""

    if days <= 0:
        return matches[:top_k]

    cutoff = (datetime.now() - timedelta(days=days)).date()
    kept: list[dict] = []
    for match in matches:
        taken = match.get("taken_at")
        if not taken:
            continue  # без EXIF-даты в диапазон не попадает
        try:
            taken_date = datetime.fromisoformat(taken).date()
        except ValueError:
            continue
        if taken_date >= cutoff:
            kept.append(match)
        if len(kept) >= top_k:
            break
    return kept


def search_by_region(
    region_id: int, *, top_k: int = 24, days: int = 0
) -> dict:
    """Похожие кропы для сохранённого региона: модель не нужна."""

    import numpy as np

    _absorb_pending()
    _state.ensure()
    position = _state.by_region.get(int(region_id))
    if position is None:
        raise KeyError(f"region {region_id} отсутствует в CLIP-индексе")

    return _similar_for_row(
        position, top_k, days=days, query_region_id=int(region_id)
    )


def search_by_photo(
    photo_id: str, *, top_k: int = 24, days: int = 0
) -> dict:
    """Похожие кропы для фото: берётся его первый кроп (минимальный region_id)."""

    _absorb_pending()
    _state.ensure()
    position = _state.by_photo.get(str(photo_id))
    if position is None:
        raise KeyError(
            f"у фото {photo_id} нет кропов щитов в CLIP-индексе "
            "(нет детекции или индекс не пересобран)"
        )

    return _similar_for_row(
        position, top_k, days=days, query_photo_id=str(photo_id)
    )


def _similar_for_row(
    position: int, top_k: int, *, days: int = 0, **query_id
) -> dict:
    """Вектор строки из индекса → поиск с исключением самого фото."""

    import numpy as np

    with _state.lock:
        vector = _state.index.reconstruct(int(position))

    photo_id = str(_state.rows[position]["photo_id"])
    # С дата-фильтром ищем с запасом: ближайшие top_k могут не попасть
    # в диапазон съёмки.
    pool = top_k if days <= 0 else min(
        DAYS_POOL_MAX, max(top_k, top_k * DAYS_POOL_MULTIPLIER)
    )
    matches = _search(
        np.asarray(vector, dtype="float32"),
        pool,
        # Та же кампания в других кадрах этого фото — шум для карточки
        # «Похожие»: исключаем всё фото запроса.
        exclude_photo_id=photo_id,
    )
    matches = _filter_by_days(_enrich(matches), days, top_k=top_k)
    result = {
        "matches": matches,
        "count": len(matches),
        **query_id,
    }
    return result


def search_by_image(
    path: str | Path, *, top_k: int = 24, days: int = 0
) -> dict:
    """Похожие кропы для загруженного изображения (кодирование на CPU)."""

    _absorb_pending()
    vector = embed_image(path)
    pool = top_k if days <= 0 else min(
        DAYS_POOL_MAX, max(top_k, top_k * DAYS_POOL_MULTIPLIER)
    )
    matches = _search(vector, pool)
    matches = _filter_by_days(_enrich(matches), days, top_k=top_k)
    return {
        "query_image": str(path),
        "matches": matches,
        "count": len(matches),
    }


def status() -> dict:
    """Состояние индекса: число векторов, отставание от БД, сборка."""

    try:
        _absorb_pending()
        _state.ensure()
    except ClipIndexUnavailable:
        return {"available": False}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*) FROM public.photo_regions
                WHERE kind = 'billboard' AND crop_path IS NOT NULL
                """
            )
            db_regions = int(cur.fetchone()[0])

    return {
        "available": True,
        "vectors": len(_state.rows),
        "dim": int(_state.index.d),
        "model": _state.info.get("model", MODEL_ID),
        "built_at": _state.info.get("built_at"),
        "db_regions": db_regions,
        "stale": db_regions > len(_state.rows),
        # Поглощено из pending и ещё не сброшено на диск (наблюдаемость).
        "pending": _state.pending_absorbed,
    }
