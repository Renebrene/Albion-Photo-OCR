# Видео в PhotoBAse

## Текущая реализация

Durable-видео хранится отдельно от фото. Временный video-файл, загруженный для `MEDIA_SEARCH`, остаётся отдельным transient query и удаляется worker после поиска; в `video_assets` он не копируется автоматически.

`INGEST_DIR` теперь выполняет фото-путь как раньше и дополнительно обрабатывает поддерживаемые видео через отдельную ветку:

- `.mp4`, `.m4v`, `.mov`, `.mpeg`, `.mpg` (регистр не важен);
- defaults: не более 300 MiB и 20 секунд, значения можно изменить через `SCENE_INGEST_MAX_VIDEO_BYTES` и `SCENE_INGEST_MAX_VIDEO_SECONDS`;
- `ffprobe` читает контейнер, видеокодек, размер, длительность, fps/frame count и best-effort `creation_time`;
- SHA-256 вычисляется по целому физическому файлу, ID — `VI_` + первые 24 hex; `public.video_assets.sha256` хранит полный hash и UNIQUE;
- затем `ffmpeg -xerror` декодирует видеопоток до конца, чтобы выявить обрыв/ошибку декодирования;
- `taken_at` сохраняется UTC из встроенного `creation_time`, если тот есть; иначе NULL. `created_at` — время регистрации в БД;
- source-файл только читается. Poster JPEG пишется атомарно в отдельный `SCENE_VIDEO_PREVIEW_ROOT`, не рядом с исходником;
- DINO, HYBRID, QWEN и photo fingerprint jobs на video assets не запускаются.

`POST /v1/ingest/run` продолжает ставить тот же `INGEST_DIR`; worker summary сохраняет прежние photo counters и добавляет секцию `videos` с отдельными `discovered/valid/invalid/registered/existing/conflicts/posters_created`.

## Модель доступа и API

- `GET /v1/videos` — cursor paging, `q`, `date_from/date_to`, `date_mode=upload|capture`.
- `GET /v1/videos/{video_id}` — сведения из реестра без абсолютного source path.
- `PUT /v1/videos/{video_id}/title` — одно пользовательское display title (max 300 символов). Scope `videos:write`.
- `GET /v1/videos/{video_id}/poster` — JPEG из отдельного preview root, scope `read`.
- `POST /v1/videos/{video_id}/playback-ticket` — scope `videos:read`; выдаёт 5-минутный HttpOnly/SameSite cookie. URL не содержит bearer token. HTML `<video>` использует cookie для Range playback.
- `POST /v1/videos/{video_id}/download-ticket` — scope `videos:download`; возвращает cookie capability для attachment-download оригинала.
- Stream/download endpoint проверяет ticket и path внутри `SCENE_ORIGINALS_ROOTS`, поддерживает single byte-range (206/416) и не загружает целый ролик в память. Cookie `Secure` определяется scheme запроса; за TLS-терминирующим proxy можно явно задать `SCENE_COOKIE_SECURE=1`.
- `GET /v1/media/statistics` — фото/видео по периодам регистрации; `/v1/stats` совместимо добавляет `videos` и `last_video_at` для статус-бара.

Scope `videos:read`, `videos:write`, `videos:download` выданы Менеджеру; Администратор имеет `*`; Гость остаётся только read-only по метаданным/poster. Доступ к исходному видео остаётся отдельным `videos:download` scope и проверкой `SCENE_ORIGINALS_ROOTS`.

## Интерфейс

`/videos` — отдельная вкладка рядом с «Фотогалерея»; собственный store и API, без адресных/клиентских фото-панелей. Переход обратно на фото возвращает исходный grid. Фильтр даты работает по registration (`upload`) или встроенной дате съёмки (`capture`).

Плитка: оригинальное имя файла обычным, display title жирным, дата съёмки курсивом, длительность/MB курсивом. Список: poster, имя, дата, длительность и MB в первой строке; display title во второй. Можно выбрать только один видео-asset; кнопок «Выделить всё/Снять» нет. Карточка открывает просмотр и редактирование title. Оригинал скачивается по кнопке «Скачать».

Статус-бар показывает photo/video counts и последние даты ingest. Кнопка «Статистика» открывает месячные photo/video counts, период базы, текущий месяц, сегодня/вчера/позавчера и последние 7 дней.

## Ещё не готово / runtime prerequisite

- Кнопка «Сжать» пока отключена; очереди transcoding и профили появятся отдельным этапом.
- Миниредактор обрезки не включён. Реалистичный первый вариант — playback + лента poster frames, начало/конец и асинхронное H.264 сохранение как отдельного derivative; это не полноценный монтажный редактор.
- На текущем хосте во время реализации не найдены `ffmpeg`/`ffprobe`, поэтому реальные video fixtures не декодировались. Для работы INGEST бинарные файлы должны быть установлены и доступны systemd. Укажите пути в `/etc/scene-fingerprint.env` как `SCENE_FFMPEG_BIN` / `SCENE_FFPROBE_BIN` (пример в `deploy/systemd/scene.env.example`). Установка системных бинарей и проверка NVENC — операционная часть; Cherry-managed CLI в изолированной среде не используется сервисами.
- Миграции 026 и 027 не запускались на `photobase_ingest_test`; они требуют сначала проверки на disposable PostgreSQL через migration runner.
- Видеозаписи, title update, ticket/playback, poster и stream проверены unit/API tests с временными файлами и mock ffprobe/ffmpeg; сквозной прогон реального видео и рабочая миграция ещё не подтверждены.
