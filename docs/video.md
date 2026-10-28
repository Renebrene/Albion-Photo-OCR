# Видео в PhotoBAse

## Текущая реализация

Durable-видео хранится отдельно от фото. Временный video-файл, загруженный для `MEDIA_SEARCH`, остаётся отдельным transient query и удаляется worker после поиска; в `video_assets` он не копируется автоматически.

`INGEST_DIR` теперь выполняет фото-путь как раньше и дополнительно обрабатывает поддерживаемые видео через отдельную ветку:

- `.mp4`, `.m4v`, `.mov`, `.mpeg`, `.mpg` (регистр не важен);
- регистрация и отображение не ограничены размером и длительностью;
- `ffprobe` читает контейнер, видеокодек, размер, длительность, fps/frame count и best-effort `creation_time`;
- ID новых видео — `VI_` + первые 24 hex SHA-256 от канонического JSON tuple `[basename, UTC-дата YYYY-MM-DD, size_bytes]`; это hash только метаданных, полный файл не читается. Дата берётся из `creation_time`, иначе из UTC-дня mtime. Старые content-hash IDs и их значения сохраняются как legacy;
- INSPECT читает stat + ffprobe метаданные и повторяет stat после probe, но не вычисляет content SHA и не декодирует видеопоток целиком;
- `taken_at` сохраняется UTC из встроенного `creation_time`, если тот есть; иначе NULL. `created_at` — время регистрации в БД;
- source-файл только читается. Poster JPEG пишется атомарно в отдельный `SCENE_VIDEO_PREVIEW_ROOT`, не рядом с исходником;
- DINO, HYBRID, QWEN и photo fingerprint jobs на video assets не запускаются.

`POST /v1/ingest/run` продолжает ставить тот же `INGEST_DIR`; worker summary сохраняет прежние photo counters и добавляет секцию `videos` с отдельными `discovered/valid/invalid/registered/existing/conflicts/posters_created`.

## Модель доступа и API

- `GET /v1/videos` — cursor paging, `q`, `date_from/date_to`, `date_mode=upload|capture`. Каждый элемент несёт `available`: `true`/`false` по `os.path.isfile()` записанного `source_path`. Признак вычисляется в обработчике для выданной страницы, отдельного обхода диска нет; записанный путь наружу не уходит (`VideoSummary` его не объявляет).
- `GET /v1/videos/{video_id}` — сведения из реестра без абсолютного source path.
- `PUT /v1/videos/{video_id}/title` — одно пользовательское display title (max 300 символов). Scope `videos:write`.
- `GET /v1/videos/{video_id}/poster` — JPEG из отдельного preview root, scope `read`.
- `POST /v1/videos/{video_id}/playback-ticket` — scope `videos:read`; выдаёт 5-минутный HttpOnly/SameSite cookie. URL не содержит bearer token. HTML `<video>` использует cookie для Range playback.
- `POST /v1/videos/{video_id}/download-ticket` — scope `videos:download`; возвращает cookie capability для attachment-download оригинала.
- Stream/download endpoint проверяет ticket и path внутри `SCENE_ORIGINALS_ROOTS`, поддерживает single byte-range (206/416) и не загружает целый ролик в память. Cookie `Secure` определяется scheme запроса; за TLS-терминирующим proxy можно явно задать `SCENE_COOKIE_SECURE=1`.
- `GET /v1/media/statistics` — фото/видео по периодам регистрации; `/v1/stats` совместимо добавляет `videos` и `last_video_at` для статус-бара.

Scope `videos:read`, `videos:write`, `videos:download` выданы Менеджеру; Администратор имеет `*`; Гость остаётся только read-only по метаданным/poster. Доступ к исходному видео остаётся отдельным `videos:download` scope и проверкой `SCENE_ORIGINALS_ROOTS`. В UI Гость не видит кнопок «Скачать»/«Сжать», выбора для действий, редактирования названия и trim-редактора; playback не запрашивается, вместо плеера показывается «Просмотр доступен сотрудникам».

## Интерфейс

`/videos` — отдельная вкладка рядом с «Фотогалерея»; собственный store и API, без адресных/клиентских фото-панелей. Переход обратно на фото возвращает исходный grid. Фильтр даты работает по registration (`upload`) или встроенной дате съёмки (`capture`).

Плитка: исходное имя файла и безопасный каталог относительно разрешённого originals root, display title жирным, дата съёмки курсивом, длительность/MB курсивом. Список показывает те же сведения. Абсолютный путь на клиент не передаётся. Можно выбрать только один видео-asset; кнопок «Выделить всё/Снять» нет. Карточка открывает просмотр и редактирование title. Оригинал скачивается по кнопке «Скачать».

Предварительная проверка папки в техническом разделе теперь тоже учитывает видео:
показывает количество фото/видео, общий объём, расширения и до 20 примеров
пустых/нечитаемых файлов. Это shallow stat-walk без декодирования; полная
проверка остаётся в `INGEST_DIR`.

Статус-бар показывает photo/video counts и последние даты инспектирования. Кнопка «Статистика» открывает месячные photo/video counts, период базы, текущий месяц, сегодня/вчера/позавчера и последние 7 дней.

### Запись осталась, файла нет

`video_assets` может ссылаться на файл, которого больше нет: корпус удалён, том не смонтирован, путь остался от прежнего расположения. Запись при этом не пропадает — она часть истории ingest, а удаление реестра необратимо. Такую запись видно и объяснимо:

- в плитке/списке под названием стоит «файл не найден»;
- в карточке — баннер «Оригинал видео недоступен: запись осталась, файла по записанному пути нет»;
- билет на воспроизведение не запрашивается (сервер ответил бы 404), в плеере вместо «Не удалось открыть видео» показывается та же причина;
- `trim`/`transcode` заблокированы с причиной «Файл оригинала не найден — редактирование невозможно» (тот же `editLimitReason`, что и для лимитов размера/длительности). Название (`PUT /title`) править по-прежнему можно: оно живёт только в реестре.

Восстановление — перенос путей (`scripts/remap_source_root.py`, `docs/deployment.md` §3.1) или бэкап; повторный ingest сам по себе путь не починит (`ON CONFLICT DO NOTHING`).

Удаление мёртвых записей — `scripts/purge_missing_videos.py`: без флагов показывает список (режим по умолчанию, ничего не меняет), с `--apply` удаляет строки, у которых файла нет ни по одному разрешённому корню, вместе с производными и билетами (каскад внешних ключей). Перед удалением полные строки и связанные производные сохраняются в `data/reports/video_records_removed_<штамп>.json` — это след, а не откат: восстановить строку можно вставкой в `video_assets`, но идентификаторы производных и билетов были свои. Проверка «файла нет» повторяется внутри удаления: если том вернулся между показом и `--apply`, строка остаётся.

28.10.2026 так удалены 10 записей (осталось 27, все с файлом): 9 из удалённого тестового корпуса `…/scene_fingerprint_RELEASE_v38_1_v33_20260815_1912 (2)/test/` и `VI_b8b4fb7fff3a9dac6ef105a0` (`MVI_6762_копия.mp4`, производная оттуда же, её родитель `VI_1c54e45c531f03ae856d4b6f` остался). След: `data/reports/video_records_removed_20261028_105136.json`. Производных и билетов у этих записей не было, ссылок из подборок, облачных ссылок и заданий — тоже.

## Сжатие, мини-редактор и runtime

- «Сжать» предлагает 720p/1080p/1440p, ставит `VIDEO_TRANSCODE` job; original остаётся read-only, derivative публикуется отдельно в управляемом derivatives root после ffprobe/decode validation и атомарной замены. Лимит для редактирования: не более 1,5 GiB (1 610 612 736 байт) и не более 10 минут; равенство допускается. Превышение любого порога блокирует только trim/transcode, но не ingest, grid, poster, playback, link или download. Сервер проверяет пределы при постановке job и непосредственно перед обработкой в worker. Профили H.264/MP4 + AAC, 25 fps, aspect ratio/no-upscale. NVENC используется только при runtime smoke; CPU `libx264` остаётся fallback.
- Trim-only editor: ограниченный storyboard из 8 JPEG кадров (≤480 px, ≤8 MiB каждый, bounded timeout), ввод/ползунки начала и конца, source preview до выбранного end через HTTP byte ranges (`preload=metadata`, без загрузки всего файла в браузер), фоновый `VIDEO_TRIM`, progress/cancel. Edit workers не считают full-content SHA: перед/после обработки сверяют stat и probe metadata; output валидируется через ffprobe, codec, размеры, FPS и длительность. Это не криптографическое доказательство неизменности: замена содержимого с теми же именем/датой/размером/метаданными может остаться незамеченной. Каждая готовая trim/transcode копия регистрируется как отдельный `video_assets` и появляется в видео-гриде с обычными download/cloud-link действиями; filename получает суффикс `_копия` (при конфликте — уникальный суффикс). Файл хранится в managed derivatives root, не рядом с original; API разрешает playback/download только при root containment. Poster создаётся отдельно. Trim использует accurate input seek + H.264/MP4 re-encode; фактическая длительность округляется до frame boundary (≤0.25 с). Crop/multitrack/effects не включены.
- `video_derivatives` хранит trim operation key и start/end; различные ranges не конфликтуют между собой или с compression profiles. Повтор идентичной обрезки переиспользует активный/готовый output. Storyboard frames keyed to source SHA лежат отдельно от originals/derivatives.
- FFmpeg 9.0.2 найден в Cherry/mise managed toolchain; direct binary paths записаны в `~/.config/scene-fingerprint.env` для user `alexice` (другим пользователям путь закрыт правами `~/.config`). CPU trim/storyboard roundtrip и NVENC 320×240 smoke прошли на синтетическом клипе; source hash не изменился.
- **Rollout 2026-10-16.** Migration `030_video_trim` применена к `photobase_ingest_test` (сделан backup `photobase_ingest_test_before_030_*.dump`, повторный запуск — no-op). Установлен и включён `scene-video-worker.service` (`--only VIDEO_TRANSCODE,VIDEO_TRIM,VIDEO_STORYBOARD`); `scene-api`/`scene-worker` перезапущены. Synthetic smoke в сервис-контексте (`systemd-run --user`) прошёл: FFmpeg найден, запись в derivatives root удалась; `choose_worker_mode()` вернул `h264_nvenc` (GPU, parallel=1), CPU `libx264` — fallback. На момент rollout `video_assets=0` и video-jobs нет, поэтому реальные пользовательские ролики не обрабатывались.
- Замечание при rollout: ExecStart video-worker в шаблоне не содержал `VIDEO_STORYBOARD` — storyboard-задания не были бы обработаны общим worker (он исключает video-типы). Исправлено: `--only VIDEO_TRANSCODE,VIDEO_TRIM,VIDEO_STORYBOARD`.
- `deploy/systemd/user/scene.env.example` указывает абсолютные direct Cherry/mise binaries и отдельные preview/storyboard/derivative roots; roots не пересекаются с `SCENE_ORIGINALS_ROOTS`. Если NVENC не проходит runtime smoke, остаётся CPU `libx264`.
