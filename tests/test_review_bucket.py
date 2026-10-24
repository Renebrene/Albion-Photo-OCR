"""
Корзина «Требуют проверки»: порог уверенности распознавания.

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


def test_threshold_sql_handles_each_criterion(monkeypatch):
    monkeypatch.setattr(hybrid_config, "low_score", lambda: 0.0)
    monkeypatch.setattr(hybrid_config, "min_margin", lambda: 0.0)

    assert repository._address_threshold_sql("conf", "margin") == "TRUE"

    monkeypatch.setattr(hybrid_config, "min_margin", lambda: 0.02)

    only_margin = repository._address_threshold_sql("conf", "margin")

    assert "margin >= 0.02" in only_margin
    assert "conf" not in only_margin


def test_verdict_source_takes_the_verdict_once(monkeypatch):
    """
    Сходство, отрыв и адрес берутся одним LATERAL-соединением.

    Регрессия: раньше это были три коррелированных подзапроса, и каждый заново
    проходил цепочку `hybrid_results` → `dino_candidates` на каждое фото.
    На корпусе это давало 2.72 с против 0.70 с на панели адресов.
    """

    monkeypatch.setattr(hybrid_config, "low_score", lambda: 0.9)
    monkeypatch.setattr(hybrid_config, "min_margin", lambda: 0.0)

    sql = repository._verdict_source_sql()

    assert sql.count("LEFT JOIN LATERAL") == 1
    # Ни одного прежнего подзапроса «сходство/отрыв/адрес».
    assert "SELECT c.score FROM" not in sql
    assert "SELECT h.hybrid_final_id FROM" not in sql
    assert "v.confidence" in sql
    assert "v.final_id" in sql
    # Отрыв забирается тем же соединением и пригодится, когда порог включён.
    assert "h.hybrid_margin AS margin" in sql
    # Фото без вердикта обязано остаться в выборке: иначе оно пропадёт из
    # счётчиков.
    assert "LEFT JOIN LATERAL" in sql and "ON TRUE" in sql
    assert "public.photo_previews" in sql


def test_counters_do_not_use_the_dino_fallback():
    """
    Фото с одним лишь DINO не считается распознанным в счётчиках.

    Запасной адрес по `dino_best_id` нужен только для показа в корзине
    «Требуют проверки» (`_PHOTO_BASE`). Распознанным фото делает
    `_recognized_sql` — без запасного пути, и грид с `recognized_only` такое
    фото не покажет. Иначе панель адресов показала бы счётчик, которого нет
    в выдаче.
    """

    sql = repository._verdict_source_sql()

    assert "dino_runs" not in sql
    assert "dino_best_id" not in sql
    # Показ адреса в карточке запасной путь сохраняет.
    assert "dino_best_id" in repository._dino_fallback_address_sql("p")


def test_verdict_source_adds_the_client_only_when_asked():
    without = repository._verdict_source_sql()
    with_client = repository._verdict_source_sql(with_client=True)

    assert "photo_qwen" not in without
    assert "q.client AS client" in with_client
    assert "LEFT JOIN public.photo_qwen AS q" in with_client


def test_address_map_is_one_row_per_fingerprint():
    """
    Карта «слепок → адрес» строится один раз и не размножает фото.

    Без группировки слепок с двумя привязками дал бы два фото вместо одного и
    счётчик адреса вырос бы вдвое.
    """

    sql = repository._ADDRESS_MAP_SQL

    assert "GROUP BY af.fingerprint_id" in sql
    assert "min(af.address_id)" in sql
    assert "reg.active" in sql


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

    from tests.conftest import (
        ensure_preview_row,
        forget_recognized_photo,
        recognize_photo,
    )

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

    # Превью нужно всем трём: без него фото нет ни в адресах, ни в «Требуют
    # проверки» (см. repository._PREVIEW_READY_SQL).
    for photo_id in ids.values():
        ensure_preview_row(photo_id)

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
        lambda value=None, margin=None: calls.append((value, margin)) or 300,
    )

    response = TestClient(app).get("/api/v1/hybrid/settings/preview?low_score=0.9")

    assert response.status_code == 200
    assert response.json() == {
        "low_score": 0.9,
        "min_margin": 0.0,
        "review_count": 300,
    }
    assert calls == [(0.9, 0.0)]


def test_preview_route_accepts_the_margin(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import routes
    from app.api.main import app

    calls = []
    monkeypatch.setattr(
        routes.repository,
        "review_count",
        lambda value=None, margin=None: calls.append((value, margin)) or 41,
    )

    response = TestClient(app).get(
        "/api/v1/hybrid/settings/preview?low_score=0&min_margin=0.015"
    )

    assert response.status_code == 200
    assert response.json()["review_count"] == 41
    assert calls == [(0.0, 0.015)]


def test_margin_is_validated():
    from app.hybrid import config as hybrid_config

    for value in (-0.1, 1.5, "много"):
        with pytest.raises(ValueError):
            hybrid_config.set_min_margin(value)


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
