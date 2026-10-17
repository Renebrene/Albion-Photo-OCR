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

Предварительная проверка папки в техническом разделе теперь тоже учитывает видео:
показывает количество фото/видео, общий объём, расширения и до 20 примеров
пустых/нечитаемых файлов. Это shallow stat-walk без декодирования; полная
проверка остаётся в `INGEST_DIR`.

Статус-бар показывает photo/video counts и последние даты ingest. Кнопка «Статистика» открывает месячные photo/video counts, период базы, текущий месяц, сегодня/вчера/позавчера и последние 7 дней.

## Сжатие, мини-редактор и runtime

- «Сжать» предлагает 720p/1080p/1440p, ставит `VIDEO_TRANSCODE` job; original остаётся read-only, derivative публикуется отдельно после ffprobe/decode validation и атомарной замены. Профили H.264/MP4 + AAC, 25 fps, aspect ratio/no-upscale. NVENC используется только при runtime smoke; CPU `libx264` остаётся fallback. В UI доступны progress/cancel/скачивание derivative.
- Trim-only editor добавлен в просмотр видео: ограниченный storyboard из 8 JPEG кадров (≤480 px, ≤8 MiB каждый, общая генерация bounded timeout), ввод/ползунки начала и конца, source preview до выбранного end, фоновый `VIDEO_TRIM`, progress/cancel и download нового derivative. Trim использует accurate input seek + H.264/MP4 re-encode; фактическая длительность округляется до frame boundary (≤0.25 с). Crop/multitrack/effects не включены.
- `video_derivatives` хранит trim operation key и start/end; различные ranges не конфликтуют между собой или с compression profiles. Повтор идентичной обрезки переиспользует активный/готовый output. Storyboard frames keyed to source SHA лежат отдельно от originals/derivatives.
- FFmpeg 9.0.2 найден в Cherry/mise managed toolchain; direct binary paths записаны в `~/.config/scene-fingerprint.env` для user `alexice` (другим пользователям путь закрыт правами `~/.config`). CPU trim/storyboard roundtrip и NVENC 320×240 smoke прошли на синтетическом клипе; source hash не изменился.
- **Rollout 2026-10-16.** Migration `030_video_trim` применена к `photobase_ingest_test` (сделан backup `photobase_ingest_test_before_030_*.dump`, повторный запуск — no-op). Установлен и включён `scene-video-worker.service` (`--only VIDEO_TRANSCODE,VIDEO_TRIM,VIDEO_STORYBOARD`); `scene-api`/`scene-worker` перезапущены. Synthetic smoke в сервис-контексте (`systemd-run --user`) прошёл: FFmpeg найден, запись в derivatives root удалась; `choose_worker_mode()` вернул `h264_nvenc` (GPU, parallel=1), CPU `libx264` — fallback. На момент rollout `video_assets=0` и video-jobs нет, поэтому реальные пользовательские ролики не обрабатывались.
- Замечание при rollout: ExecStart video-worker в шаблоне не содержал `VIDEO_STORYBOARD` — storyboard-задания не были бы обработаны общим worker (он исключает video-типы). Исправлено: `--only VIDEO_TRANSCODE,VIDEO_TRIM,VIDEO_STORYBOARD`.
- `deploy/systemd/user/scene.env.example` указывает абсолютные direct Cherry/mise binaries и отдельные preview/storyboard/derivative roots; roots не пересекаются с `SCENE_ORIGINALS_ROOTS`. Если NVENC не проходит runtime smoke, остаётся CPU `libx264`.
