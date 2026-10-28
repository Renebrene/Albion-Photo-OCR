"""
Заголовки кеша для собранного интерфейса (28.10.2026).

Симптом, который это лечит: подсказка «Доступна новая сборка» висела после
каждого обновления страницы — браузер или прокси держал старую оболочку, а
`build.json` рядом отдавался без указаний кеширования.
"""

from __future__ import annotations

from app.api.main import static_cache_control


def test_the_shell_is_never_cached():
    for path in ("/", "/index.html", "/build.json"):
        assert static_cache_control(path) == "no-store, no-cache, must-revalidate, max-age=0"


def test_hashed_bundles_are_cached_forever():
    """В имени бандла стоит хеш: его содержимое не меняется под тем же адресом."""

    value = static_cache_control("/assets/index-4msb1TM.js")

    assert value == "public, max-age=31536000, immutable"


def test_other_files_get_no_policy():
    """Логотип и прочие файлы без хеша в имени: политику не навязываем."""

    assert static_cache_control("/logo.png") is None
    assert static_cache_control("/api/v1/photos") is None


def test_the_route_for_the_root_keeps_its_own_headers():
    """Фолбэк SPA сам ставит no-store: middleware не должен его переписать."""

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/index.html")
    def shell():
        from fastapi.responses import Response

        return Response(
            "<html></html>",
            media_type="text/html",
            headers={"Cache-Control": "no-store"},
        )

    assert TestClient(app).get("/index.html").headers["cache-control"] == "no-store"
