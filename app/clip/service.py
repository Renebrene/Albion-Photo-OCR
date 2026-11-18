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
from pathlib import Path

from app.core.config import settings
from app.ingest.database import get_connection

CLIP_DIR = Path(os.getenv("SCENE_CLIP_ROOT", str(settings.data_dir / "clip")))
INDEX_FILE = CLIP_DIR / "clip_index.faiss"
META_FILE = CLIP_DIR / "clip_meta.jsonl"
INFO_FILE = CLIP_DIR / "index_info.json"

MODEL_ID = "openai/clip-vit-base-patch32"
EMB_DIM = 512
UPLOAD_LIMIT_BYTES = 10 * 1024 * 1024


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
    """Адрес и поля QWEN для найденных регионов (один запрос на батч)."""

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
                       q.client
                FROM public.photo_regions AS r
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
            }
        )
    return matches


def search_by_region(region_id: int, *, top_k: int = 24) -> dict:
    """Похожие кропы для сохранённого региона: модель не нужна."""

    import numpy as np

    _state.ensure()
    position = _state.by_region.get(int(region_id))
    if position is None:
        raise KeyError(f"region {region_id} отсутствует в CLIP-индексе")

    return _similar_for_row(position, top_k, query_region_id=int(region_id))


def search_by_photo(photo_id: str, *, top_k: int = 24) -> dict:
    """Похожие кропы для фото: берётся его первый кроп (минимальный region_id)."""

    _state.ensure()
    position = _state.by_photo.get(str(photo_id))
    if position is None:
        raise KeyError(
            f"у фото {photo_id} нет кропов щитов в CLIP-индексе "
            "(нет детекции или индекс не пересобран)"
        )

    return _similar_for_row(position, top_k, query_photo_id=str(photo_id))


def _similar_for_row(position: int, top_k: int, **query_id) -> dict:
    """Вектор строки из индекса → поиск с исключением самого фото."""

    import numpy as np

    with _state.lock:
        vector = _state.index.reconstruct(int(position))

    photo_id = str(_state.rows[position]["photo_id"])
    matches = _search(
        np.asarray(vector, dtype="float32"),
        top_k,
        # Та же кампания в других кадрах этого фото — шум для карточки
        # «Похожие»: исключаем всё фото запроса.
        exclude_photo_id=photo_id,
    )
    result = {
        "matches": _enrich(matches),
        "count": len(matches),
        **query_id,
    }
    return result


def search_by_image(path: str | Path, *, top_k: int = 24) -> dict:
    """Похожие кропы для загруженного изображения (кодирование на CPU)."""

    vector = embed_image(path)
    matches = _search(vector, top_k)
    return {
        "query_image": str(path),
        "matches": _enrich(matches),
        "count": len(matches),
    }


def status() -> dict:
    """Состояние индекса: число векторов, отставание от БД, сборка."""

    try:
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
    }
