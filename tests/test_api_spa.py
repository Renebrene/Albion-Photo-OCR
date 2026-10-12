"""
The built SPA (frontend/dist) is served by the API when present, without
shadowing /api routes. Skipped when the frontend has not been built.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"

pytestmark = pytest.mark.skipif(
    not (DIST / "index.html").is_file(),
    reason="frontend/dist not built",
)

client = TestClient(app, raise_server_exceptions=False)


def test_root_serves_index():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="app"' in response.text


def test_spa_route_falls_back_to_index():
    response = client.get("/processing")
    assert response.status_code == 200
    assert 'id="app"' in response.text


def test_api_health_is_not_shadowed():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
