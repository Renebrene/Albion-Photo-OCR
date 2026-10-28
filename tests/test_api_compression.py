"""
Селективное gzip-сжатие (аудит 28.10.2026).

Проверяем и выигрыш, и границы: видео и Range-ответы не должны попадать под
сжатие, иначе поток ломается, а клиент получает мусор.
"""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.testclient import TestClient

from app.api.compression import SelectiveGZipMiddleware

BIG_TEXT = "фото " * 2000  # ~10 КБ: заведомо больше порога


def make_app(**kwargs) -> FastAPI:
    app = FastAPI()
    app.add_middleware(SelectiveGZipMiddleware, **kwargs)

    @app.get("/v1/photos")
    def photos():
        return JSONResponse({"items": [{"filename": BIG_TEXT}]})

    @app.get("/v1/videos/stream")
    def stream():
        def chunks():
            for _ in range(4):
                yield b"\x00" * 4096

        return StreamingResponse(
            chunks(),
            media_type="video/mp4",
            headers={"Content-Length": str(4 * 4096)},
        )

    @app.get("/v1/photos/tiny")
    def tiny():
        return JSONResponse({"ok": True})

    @app.get("/v1/photos/nothing")
    def nothing():
        return Response(status_code=204)

    @app.get("/v1/photos/already")
    def already():
        return Response(
            content=b"x" * 4096,
            media_type="application/json",
            headers={"Content-Encoding": "br"},
        )

    @app.get("/v1/photos/partial")
    def partial():
        return Response(
            content=b"x" * 4096,
            media_type="application/json",
            status_code=206,
            headers={"Content-Range": "bytes 0-4095/10000"},
        )

    @app.get("/v1/photos/image")
    def image():
        return Response(content=b"\x89PNG" + b"\x00" * 4096, media_type="image/png")

    return app


def test_json_response_is_compressed():
    client = TestClient(make_app())

    plain = client.get("/v1/photos", headers={"Accept-Encoding": "identity"})

    response = client.get("/v1/photos", headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert response.headers["vary"] == "accept-encoding"
    # httpx распаковывает gzip прозрачно, поэтому сравниваем по заголовку:
    # в content-length лежит размер сжатого тела.
    assert int(response.headers["content-length"]) < len(plain.content) / 2
    # Тело читается как обычный JSON: распаковка на стороне клиента.
    assert json.loads(response.content)["items"][0]["filename"] == BIG_TEXT


def test_a_client_without_gzip_gets_plain_json():
    client = TestClient(make_app())

    response = client.get("/v1/photos", headers={"Accept-Encoding": "identity"})

    assert "content-encoding" not in response.headers
    assert json.loads(response.content)["items"]


def test_video_stream_is_not_compressed():
    """Поток видео отдаётся байт в байт: у него свой Content-Length."""

    client = TestClient(make_app())

    response = client.get("/v1/videos/stream", headers={"Accept-Encoding": "gzip"})

    assert "content-encoding" not in response.headers
    assert len(response.content) == 4 * 4096


def test_a_small_body_is_left_alone():
    client = TestClient(make_app())

    response = client.get("/v1/photos/tiny", headers={"Accept-Encoding": "gzip"})

    assert "content-encoding" not in response.headers


def test_partial_and_empty_responses_are_left_alone():
    client = TestClient(make_app())

    empty = client.get("/v1/photos/nothing", headers={"Accept-Encoding": "gzip"})
    partial = client.get("/v1/photos/partial", headers={"Accept-Encoding": "gzip"})

    assert "content-encoding" not in empty.headers
    # Частичное содержимое нумеруется побайтово: сжимать его нельзя.
    assert "content-encoding" not in partial.headers
    assert partial.headers["content-range"] == "bytes 0-4095/10000"


def test_an_already_encoded_response_is_left_alone():
    client = TestClient(make_app())

    response = client.get("/v1/photos/already", headers={"Accept-Encoding": "gzip, br"})

    assert response.headers["content-encoding"] == "br"


def test_binary_types_are_left_alone():
    client = TestClient(make_app())

    response = client.get("/v1/photos/image", headers={"Accept-Encoding": "gzip"})

    assert "content-encoding" not in response.headers


def test_incompressible_body_is_sent_as_is(monkeypatch):
    """Если сжатие не уменьшило тело, отдаём исходное."""

    app = FastAPI()
    app.add_middleware(SelectiveGZipMiddleware, minimum_size=1)

    # Псевдослучайные байты: повторяющийся шаблон deflate сжал бы отлично.
    import random

    payload = random.Random(0).randbytes(10240)

    @app.get("/v1/photos/random")
    def random_bytes():
        return Response(content=payload, media_type="application/json")

    response = TestClient(app).get(
        "/v1/photos/random", headers={"Accept-Encoding": "gzip"}
    )

    assert "content-encoding" not in response.headers
    assert response.content == payload


def test_the_switch_turns_compression_off(monkeypatch):
    monkeypatch.setenv("SCENE_API_GZIP", "0")
    client = TestClient(make_app())

    response = client.get("/v1/photos", headers={"Accept-Encoding": "gzip"})

    assert "content-encoding" not in response.headers


def test_the_size_ceiling_stops_compression():
    """Выше потолка тело не буферизуем: отдаём как есть."""

    client = TestClient(make_app(maximum_size=100))

    response = client.get("/v1/photos", headers={"Accept-Encoding": "gzip"})

    assert "content-encoding" not in response.headers

    assert client.get("/v1/photos").status_code == 200
