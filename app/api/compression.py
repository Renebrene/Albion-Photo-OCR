"""
Селективное gzip-сжатие ответов (аудит 28.10.2026).

Зачем: JSON-ответы API и текстовые файлы сборки сжимаются в 3-10 раз, а первый
заход по сети снаружи — это как раз бандлы SPA (0,84 МБ) и ответы панелей.
На локальной сети выигрыш незаметен, по интернету — в разы меньше байт.

Почему свой middleware, а не `starlette.middleware.gzip.GZipMiddleware`: тот
сжимает всё подряд, включая потоковую отдачу видео. Для `/v1/videos/.../stream`
с Range-запросами это и лишний CPU, и сломанная семантика частичного контента.
Здесь сжатие включается только для перечисленных типов содержимого и только
для ответов с известной длиной в допустимых границах:

* `application/json`, `application/javascript`, `text/*`, `image/svg+xml`,
  `application/xml` — сжимаем;
* видео, изображения, шрифты (woff2 уже сжаты) — не трогаем;
* `StreamingResponse`/`FileResponse` не попадают в белый список типов, а ответы
  с частичным содержимым (206), пустые (204) и «не изменилось» (304) пропускаем;
* тела меньше `minimum_size` не сжимаем — заголовок дороже выигрыша;
* ответ уже с `Content-Encoding` (например, gzip от внешнего прокси) не трогаем.

Тело буферизуется только когда решение «сжимать» уже принято и длина известна
(не больше `maximum_size`), поэтому потоки видео и файлы проходят мимо без
копирования.
"""

from __future__ import annotations

import gzip
import os

# Типы, которые имеет смысл сжимать. Сравнение по префиксу: `text/` покрывает
# html, css, plain, csv.
COMPRESSIBLE_PREFIXES = (
    "application/json",
    "application/javascript",
    "application/xml",
    "application/x-ndjson",
    "image/svg+xml",
    "text/",
)

# Коды, для которых сжатие бессмысленно или вредно (нет тела либо частичное
# содержимое, где важна побайтовая нумерация).
SKIP_STATUS = frozenset({204, 205, 206, 304})

DEFAULT_MINIMUM_SIZE = 1024
# Верхняя граница: столько можно позволить буферизовать ради сжатия. Бандлы
# сборки (~340 КБ) и ответы API в неё укладываются с запасом.
DEFAULT_MAXIMUM_SIZE = 4 * 1024 * 1024


def _enabled() -> bool:
    raw = os.getenv("SCENE_API_GZIP", "1").strip().lower()

    return raw not in {"0", "false", "no", "off"}


class SelectiveGZipMiddleware:
    """Сжимает только текстовые и JSON-ответы с известной длиной."""

    def __init__(
        self,
        app,
        *,
        minimum_size: int = DEFAULT_MINIMUM_SIZE,
        maximum_size: int = DEFAULT_MAXIMUM_SIZE,
    ) -> None:
        self.app = app
        self.minimum_size = minimum_size
        self.maximum_size = maximum_size

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not _enabled():
            await self.app(scope, receive, send)
            return

        headers = _header_map(scope.get("headers") or [])

        if "gzip" not in headers.get("accept-encoding", "").lower():
            await self.app(scope, receive, send)
            return

        state: dict = {"compress": False, "chunks": []}

        async def send_wrapper(message):
            kind = message["type"]

            if kind == "http.response.start":
                state["status"] = message["status"]
                state["headers"] = list(message["headers"])
                state["compress"] = self._should_compress(message, state["headers"])

                if not state["compress"]:
                    await send(message)

                return

            if kind == "http.response.body":
                if not state["compress"]:
                    await send(message)
                    return

                state["chunks"].append(message.get("body", b""))

                if message.get("more_body"):
                    return

                await self._send_compressed(send, state)
                return

            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _should_compress(self, message: dict, headers: list) -> bool:
        if message["status"] in SKIP_STATUS or not 200 <= message["status"] < 300:
            return False

        values = _header_map(headers)

        if values.get("content-encoding"):
            return False

        content_type = values.get("content-type", "").split(";")[0].strip().lower()

        if not content_type.startswith(COMPRESSIBLE_PREFIXES):
            return False

        raw_length = values.get("content-length")

        if not raw_length or not raw_length.isdigit():
            # Длина неизвестна (поток) — не буферизуем.
            return False

        length = int(raw_length)

        return self.minimum_size <= length <= self.maximum_size

    async def _send_compressed(self, send, state: dict) -> None:
        body = b"".join(state["chunks"])
        packed = gzip.compress(body, compresslevel=6)

        if len(packed) >= len(body):
            # Сжатие ничего не дало: отдаём исходное тело.
            await send(
                {
                    "type": "http.response.start",
                    "status": state["status"],
                    "headers": state["headers"],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        headers = [
            (name, value)
            for name, value in state["headers"]
            if name.lower() not in {b"content-length", b"content-encoding"}
        ]
        headers.append((b"content-encoding", b"gzip"))
        headers.append((b"content-length", str(len(packed)).encode()))
        # Кэши обязаны различать сжатый и несжатый ответ.
        if not any(name.lower() == b"vary" for name, _ in headers):
            headers.append((b"vary", b"accept-encoding"))

        await send(
            {
                "type": "http.response.start",
                "status": state["status"],
                "headers": headers,
            }
        )
        await send({"type": "http.response.body", "body": packed})


def _header_map(headers) -> dict[str, str]:
    """Заголовки как словарь в нижнем регистре: сравнение без регистра."""

    result: dict[str, str] = {}

    for name, value in headers:
        key = (name.decode() if isinstance(name, bytes) else str(name)).lower()
        text = value.decode() if isinstance(value, bytes) else str(value)

        if key in result:
            result[key] = f"{result[key]}, {text}"
        else:
            result[key] = text

    return result
