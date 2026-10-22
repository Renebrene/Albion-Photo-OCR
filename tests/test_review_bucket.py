"""
Корзина «Уточнить»: порог уверенности распознавания.

Порог живёт в настройках и применяется при чтении, поэтому проверяется и без
базы (правила и валидация), а поведение выборок — на одноразовой базе
(`SCENE_TEST_DB=1`, см. docs/testing.md).
"""

from __future__ import annotations

import os

import pytest

from app.api import repository
from app.hybrid import config as hybrid_config


# ---- порог: правила и валидация (без базы) --------------------------------


@pytest.fixture(autouse=True)
def reset_cache():
    hybrid_config.invalidate()
    yield
    hybrid_config.invalidate()


def test_default_threshold_is_085():
    assert hybrid_config.DEFAULT_LOW_SCORE == 0.85


def test_threshold_can_be_switched_off():
    # 0 — прежнее поведение: адрес получает любое совпадение.
    assert hybrid_config.MIN_LOW_SCORE == 0.0


def test_threshold_rejects_out_of_range_values(monkeypatch):
    for value in (-0.01, 1.5, 42):
        with pytest.raises(ValueError):
            hybrid_config.set_low_score(value)


def test_threshold_rejects_junk(monkeypatch):
    for value in ("порог", None, [1]):
        with pytest.raises(ValueError):
            hybrid_config.set_low_score(value)


def test_resolve_settings_shape(monkeypatch):
    monkeypatch.setattr(hybrid_config, "low_score", lambda: 0.85)

    settings = hybrid_config.resolve_settings()

    assert settings["low_score"] == 0.85
    assert settings["enabled"] is True


# ---- SQL-выражения (без базы) --------------------------------------------


def test_address_sql_is_plain_when_the_threshold_is_off(monkeypatch):
    monkeypatch.setattr(hybrid_config, "low_score", lambda: 0.0)

    sql = repository._address_sql("p")

    assert "CASE WHEN" not in sql
    assert "hybrid_final_id" in sql


def test_address_sql_gates_on_confidence(monkeypatch):
    monkeypatch.setattr(hybrid_config, "low_score", lambda: 0.85)

    sql = repository._address_sql("p")

    assert "CASE WHEN" in sql
    assert ">= 0.85" in sql
    assert "dino_candidates" in sql


def test_review_filter_is_recognised():
    assert repository.REVIEW_ADDRESS_ID == "review"
    assert repository.REVIEW_ADDRESS_VALUE == "addr:review"


# ---- поведение выборок (нужна одноразовая база) ---------------------------


def _db_available() -> bool:
    if os.getenv("SCENE_TEST_DB") != "1":
        return False
    try:
        with repository.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.photos')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(), reason="нужна одноразовая база (SCENE_TEST_DB=1)"
)


@pytest.fixture()
def corpus():
    """
    Три фото: уверенное (0.95), слабое (0.70) и без совпадения вовсе.

    Убирается за собой: батч удаляется каскадом вместе с прогонами.
    """

    from tests.conftest import forget_recognized_photo, recognize_photo

    from app.ingest.database import get_connection

    ids = {
        "strong": "PH_" + "1" * 24,
        "weak": "PH_" + "2" * 24,
        "none": "PH_" + "3" * 24,
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            for photo_id in ids.values():
                cur.execute(
                    """INSERT INTO public.photos
                           (photo_id, source_path, filename, sha256,
                            container_format, frame_count, width, height)
                       VALUES (%s, %s, %s, %s, 'JPEG', 1, 10, 10)
                       ON CONFLICT (photo_id) DO NOTHING""",
                    (photo_id, f"/tmp/{photo_id}.jpg", f"{photo_id}.jpg", photo_id[3:] * 2),
                )

    strong = recognize_photo(ids["strong"], "78_v33")
    weak = recognize_photo(ids["weak"], "78_v33")

    # Уверенность задаётся оценкой кандидата первого ранга.
    with get_connection() as conn:
        with conn.cursor() as cur:
            for run_id, score in ((strong["dino_run_id"], 0.95), (weak["dino_run_id"], 0.70)):
                cur.execute(
                    """INSERT INTO public.dino_candidates
                           (run_id, rank, fingerprint_id, score, global_score,
                            environment_score, color_score, spatial_score, best_image_score)
                       VALUES (%s, 1, '78_v33', %s, %s, %s, %s, %s, %s)""",
                    (run_id, score, score, score, score, score, score),
                )

    yield ids

    for rows in (strong, weak):
        forget_recognized_photo(rows)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.photos WHERE photo_id = ANY(%s)",
                (list(ids.values()),),
            )


def _photos(address_filter, monkeypatch, threshold):
    monkeypatch.setattr(hybrid_config, "low_score", lambda: threshold)

    items, _ = repository.list_photos(
        limit=50, addresses=[address_filter], recognized_only=True
    )

    return {photo.photo_id for photo in items}


@requires_db
def test_weak_match_leaves_its_address(corpus, monkeypatch):
    strong = corpus["strong"]
    weak = corpus["weak"]

    assert _photos("addr:review", monkeypatch, 0.85) == {weak, corpus["none"]}
    # Уверенное фото остаётся распознанным и в корзину не попадает.
    assert strong not in _photos("addr:review", monkeypatch, 0.85)


@requires_db
def test_threshold_can_be_lowered_to_accept_the_match(corpus, monkeypatch):
    weak = corpus["weak"]

    # Порог ниже уверенности слабого фото — оно снова получает адрес.
    assert weak not in _photos("addr:review", monkeypatch, 0.60)


@requires_db
def test_threshold_zero_keeps_the_old_behaviour(corpus, monkeypatch):
    # Проверка выключена: в корзине только фото без совпадения вовсе.
    assert _photos("addr:review", monkeypatch, 0) == {corpus["none"]}


@requires_db
def test_confidence_is_reported_for_each_photo(corpus, monkeypatch):
    monkeypatch.setattr(hybrid_config, "low_score", lambda: 0.85)

    recognized, _ = repository.list_photos(limit=50, recognized_only=True)
    by_id = {photo.photo_id: photo for photo in recognized}

    # Уверенное фото остаётся в гриде: адрес на месте, уверенность видна.
    assert by_id[corpus["strong"]].confidence == pytest.approx(0.95)
    assert by_id[corpus["strong"]].address == "78_v33"

    # Слабое в грид не попадает — оно в корзине, и уверенность видна там.
    assert corpus["weak"] not in by_id

    review, _ = repository.list_photos(
        limit=50, addresses=[repository.REVIEW_ADDRESS_VALUE], recognized_only=True
    )
    in_review = {photo.photo_id: photo for photo in review}

    assert in_review[corpus["weak"]].confidence == pytest.approx(0.70)
    assert in_review[corpus["weak"]].address is None
    # Фото без совпадения вовсе: уверенности нет, адреса нет.
    assert in_review[corpus["none"]].confidence is None
    assert in_review[corpus["none"]].address is None


# ---- предпросмотр порога (оператор подбирает значение) --------------------


def test_explicit_threshold_reaches_the_sql(monkeypatch):
    monkeypatch.setattr(hybrid_config, "low_score", lambda: 0.85)

    explicit = repository._address_sql("p", 0.9)

    assert ">= 0.9" in explicit
    assert ">= 0.85" in repository._address_sql("p")


def test_preview_route_returns_the_count(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import routes
    from app.api.main import app

    calls = []
    monkeypatch.setattr(
        routes.repository,
        "review_count",
        lambda value=None: calls.append(value) or 300,
    )

    response = TestClient(app).get("/api/v1/hybrid/settings/preview?low_score=0.9")

    assert response.status_code == 200
    assert response.json() == {"low_score": 0.9, "review_count": 300}
    assert calls == [0.9]


def test_preview_route_rejects_out_of_range():
    from fastapi.testclient import TestClient

    from app.api.main import app

    for value in (1.5, -0.1):
        assert (
            TestClient(app)
            .get(f"/api/v1/hybrid/settings/preview?low_score={value}")
            .status_code
            == 422
        )


@requires_db
def test_review_count_matches_the_threshold(corpus):
    strong, weak, none = corpus["strong"], corpus["weak"], corpus["none"]

    # Порог между уверенностями слабого (0.70) и уверенного (0.95) фото.
    assert repository.review_count(0.85) == len({weak, none})
    # Порог ниже слабого: в корзине остаётся только фото без совпадения.
    assert repository.review_count(0.60) == len({none})
