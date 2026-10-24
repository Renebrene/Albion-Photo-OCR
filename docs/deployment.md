# Развёртывание на сервере с сетевым хранилищем

Дата: 2026-10-22

Дополняет `deploy/systemd/README.md` (службы, первый вход, миграции). Здесь —
то, что специфично для сервера, у которого **оригиналы лежат на отдельном
томе**: подмонтированный диск, гигабитная LAN-шара или USB-NAS.

Целевой сценарий владельца:

- проект живёт в локальной сети, иногда доступен снаружи через туннель;
- сервер сначала **без GPU**, GPU (если появится) — на другой машине сети через
  Ollama;
- основная масса данных — на NAS, скорость не критична, тяжёлая работа идёт
  фоном;
- переименование рабочей БД (`photobase_ingest_test`) не планируется.

## 1. Что где должно лежать

Ключевое правило: **на сетевой том выносится только то, что можно читать
последовательно.** Всё, что требует блокировок файлов или случайного доступа,
остаётся на локальном диске сервера.

| Данные | Где | Почему |
|---|---|---|
| Оригиналы фото/видео | сетевой том (NAS/шар) | только чтение, последовательный доступ |
| `SCENE_DATA` (`data/`) — fingerprints, FAISS-индексы | **локальный диск** | mmap и случайный доступ; по сети деградация и риск порчи индекса |
| `SCENE_PREVIEW_ROOT` (`data/preview`) | локальный диск; при 57k фото ~18 ГБ | читается гридом постоянно, задержка видна сразу |
| `SCENE_CROPS_ROOT` (`data/crops`) | локальный диск | временные файлы, удаляются после QWEN |
| `SCENE_INBOX` (`data/inbox`) | локальный диск | загрузка пользователем |
| SQLite-очередь сборки fingerprint | локальный диск | `app/pipeline/queue.py` — файловая БД, блокировки по сети небезопасны |
| PostgreSQL | **не NAS** | БД на сетевом томе — отдельный класс проблем |
| Бэкапы `pg_dump` | NAS — можно | последовательная запись большими блоками |

Если локального места мало и `SCENE_DATA` всё же выносится на NAS, это надо
делать осознанно: FAISS-индекс и `data/pipeline/queue.sqlite` на CIFS/NFS
работают нестабильно (нет нормального `fcntl`-лочения).

## 2. Монтирование хранилища

### 2.1 Постоянная шара (`/etc/fstab`)

CIFS/SMB (типичный USB-NAS или Windows-шара):

```
//nas.local/photos  /mnt/photos  cifs  credentials=/etc/scene-cifs.cred,uid=scene,gid=scene,file_mode=0640,dir_mode=0750,iocharset=utf8,vers=3.0,_netdev,nofail,x-systemd.automount,x-systemd.idle-timeout=10min  0 0
```

NFS:

```
nas.local:/export/photos  /mnt/photos  nfs  ro,soft,timeo=100,retrans=2,rsize=1048576,wsize=1048576,_netdev,nofail,x-systemd.automount  0 0
```

Что здесь важно:

- `_netdev` + `nofail` + `x-systemd.automount` — сервер поднимается и работает,
  даже если NAS выключен или сеть ещё не готова. Без этого загрузка висит.
- `x-systemd.idle-timeout` — том отмонтируется, когда никто не читает.
- `ro` для NFS: оригиналы не должны изменяться, режим только для чтения
  подкрепляет это на уровне ядра.
- Для CIFS права задаются `uid`/`gid`/`file_mode`/`dir_mode`, потому что
  POSIX-прав в SMB нет. Владелец — пользователь службы (`scene`).
- `credentials=/etc/scene-cifs.cred`, режим `0600`, root:root:

```
username=photobase
password=<пароль NAS>
domain=WORKGROUP
```

**Не используйте NTFS/exFAT** для локально подключённого USB-диска: нет
POSIX-прав и символических ссылок, имена с юникодом и регистром ведут себя
непредсказуемо, а `fsck` после сбоя питания может оставить том только для
чтения. Формат — ext4 или XFS.

`soft,timeo` у NFS: если шара отвалится, чтение вернёт ошибку вместо
бесконечного ожидания. Для монтажа **источника фото** это правильно (файлы
только читаются). Для NFS-тома с базой такой режим недопустим — но база на
NAS и не выносится.

### 2.2 Проверка перед запуском служб

```bash
findmnt /mnt/photos
sudo -u scene test -r /mnt/photos/inbox && echo "читается службой"
df -h /mnt/photos /home
```

Служба работает под `scene`, поэтому проверять доступ надо **от её имени**, а
не от своего: смонтированный том может быть доступен root, но не сервисному
пользователю.

## 3. Переменные окружения

В `/etc/scene-fingerprint.env` (или `~/.config/scene-fingerprint.env` для
пользовательских юнитов):

```ini
# --- база ---
INGEST_DB_HOST=127.0.0.1
INGEST_DB_NAME=photobase_ingest_test
INGEST_DB_USER=lora_ingest
INGEST_DB_PASSWORD=...            # только здесь, не в git

# --- источник и доступ к оригиналам ---
SCENE_SOURCE_FOLDER=/mnt/photos/inbox
SCENE_SOURCE_ROOTS=/mnt/photos     # что вообще разрешено выбирать
SCENE_ORIGINALS_ROOTS=/mnt/photos  # откуда отдавать оригинал по HTTP

# --- локальные производные ---
SCENE_DATA=/var/lib/scene-fingerprint/data
SCENE_PREVIEW_ROOT=/var/lib/scene-fingerprint/data/preview
SCENE_CROPS_ROOT=/var/lib/scene-fingerprint/data/crops
SCENE_INBOX=/var/lib/scene-fingerprint/data/inbox

# --- сеть ---
SCENE_API_HOST=127.0.0.1           # наружу через прокси
SCENE_API_PORT=8010
SCENE_CORS_ORIGINS=http://<адрес-сервера>
SCENE_TRUST_PROXY=1                # только если перед API стоит прокси
```

`SCENE_SOURCE_ROOTS` и `SCENE_ORIGINALS_ROOTS` — не одно и то же:
первый ограничивает, какие папки можно указать как источник сканирования,
второй — из каких корней разрешено отдавать файл оригинала. Пустой
`SCENE_ORIGINALS_ROOTS` означает «оригиналы не отдаются вообще» (ответ 503),
это безопасное состояние по умолчанию.

**Пустой `SCENE_SOURCE_ROOTS` = «любой путь»** (так и настроено на этой
машине): инспектору можно указать любую существующую папку — и вручную
набранным путём, и выбором в окне (там есть переход к родительской папке, так
что до `/media/...` можно дойти без набора). Если стенд открыт наружу, список
корней лучше задать явно: тогда чужие пути отклоняются ответом 403.

### 3.1. Переезд корпуса на другой том или NAS

В базе хранятся абсолютные `source_path` (фотографии — `photos.source_path`,
видео — `video_assets.source_path`). Если файлы переехали с локального диска на
NAS, пути нужно заменить префиксом. Делает это
`scripts/remap_source_root.py`: он меняет только строки в БД, файлы не читает и
не изменяет.

```bash
.venv/bin/python scripts/remap_source_root.py \
    --from /media/alexice/TEST/БАЗАФОТО \
    --to /mnt/photos/БАЗАФОТО            # без --confirm это только отчёт

.venv/bin/python scripts/remap_source_root.py ... --confirm
```

Порядок переезда:

1. Смонтировать новый том и убедиться, что структура каталогов внутри корня
   совпадает со старой (скрипту нужен только неизменный хвост пути).
2. Прогнать скрипт без `--confirm`, проверить счётчики строк и примеры путей.
3. Выполнить с `--confirm` (одна транзакция на обе таблицы).
4. Добавить новый корень в `SCENE_ORIGINALS_ROOTS` и перезапустить API: без
   этого оригиналы будут считаться недоступными (`original_availability != ok`).
5. Проверить несколько фото/видео через UI (инспектор, скачивание оригинала).

Откат — тот же скрипт с обратными `--from`/`--to`. Уникальность пути не
нарушается, `photo_id`/`video_id` привязаны к содержимому файла (SHA-256 или
metadata-v1), а не к пути, поэтому слепки и результаты распознавания
остаются валидными. Пока не удалён старый том, старые пути в истории
прогонов (`runs`) остаются как есть — они отражают, откуда читали в тот
момент.

### 3.2. После правки env перезапустите юниты

Переменные читаются один раз при старте процесса. Правка
`~/.config/scene-fingerprint.env` сама по себе ничего не меняет: работающий
воркер продолжает жить со старым окружением, и это выглядит как непонятная
ошибка. Реальный случай: `/media/alexice/Win10` добавлен в
`SCENE_ORIGINALS_ROOTS`, API перезапущен, а видео-воркер (запущенный раньше)
отвечал «исходное видео недоступно в разрешённом корне» — правки путей для
видео вступают в силу только после его перезапуска.

```bash
systemctl --user restart scene-api scene-worker scene-preview-worker \
    scene-qwen-worker scene-video-worker scene-billboard-worker \
    scene-pipeline-worker
```

То же правило действует и для **правок кода**: API и воркеры держат модули
в памяти с момента старта. Если изменился `app/api/*` — перезапускается
`scene-api`; если `app/dino`, `app/hybrid`, `app/preview`, `app/qwen`,
`app/refine` или `app/jobs` — соответствующий воркер. Реальный случай: поля
`jobs` и `batch` добавлены в `/v1/qwen/stats`, а API не перезапустили — шапка
показывала старое число, потому что процесс отвечал прежней версией кода.

Проверка, что воркер видит нужные корни (пример для видео):

```bash
set -a && . ~/.config/scene-fingerprint.env && set +a
.venv/bin/python -c "
from app.api.config import ORIGINALS_ROOTS
from app.api.file_access import allowed_media_path
print(ORIGINALS_ROOTS)
print(allowed_media_path('/media/alexice/Win10/БАЗАФОТО/февраль/5,02/MVI_6762.MP4', ORIGINALS_ROOTS))
"
```

Оригиналы фото и видео проверяются одним списком `SCENE_ORIGINALS_ROOTS`:
отдельного «видео-списка» нет. Но корни постеров, сторибордов и производных
видео (`SCENE_VIDEO_PREVIEW_ROOT`, `SCENE_VIDEO_STORYBOARD_ROOT`,
`SCENE_VIDEO_DERIVATIVES_ROOT`) обязаны лежать ВНЕ исходных корней — иначе
генерация останавливается с ошибкой «storyboard root must be separate from
source roots».

## 4. Пропускная способность сети

Гигабитная LAN даёт ~110 МБ/с в идеале, реально 70–90 МБ/с. Это влияет на
INSPECT: SHA-256 считается по всему файлу, то есть **инспектирование читает
каждое новое фото целиком по сети**.

Ориентир для 57 000 фото по 4 МБ (228 ГБ):

| Этап | Где узкое место | Оценка |
|---|---|---|
| INSPECT (чтение + SHA-256) | сеть | 45–60 мин при 90 МБ/с |
| PREVIEW | CPU | 2–2.5 ч |
| DINO / HYBRID | CPU | 3 ч / 5 мин |
| QWEN | CPU/GPU | 40–48 ч локально |

Практика:

- запускать инспектирование большими пачками в нерабочее время;
- не поднимать одновременно INSPECT и массовый QWEN, если NAS один и тот же —
  они конкурируют за сеть;
- `ionice`/`Nice` в юните уже снижают приоритет фоновых задач; для самого
  INSPECT это делает `scene-worker`;
- при повторном инспектировании файлы, уже зарегистрированные с той же парой
  (имя, размер), **не хэшируются** — повторный проход по неизменной папке
  почти не читает сеть. Это главный аргумент против «пересканировать всё
  заново» без необходимости.

Если шара отвалилась посреди инспектирования, задание упадёт с ошибкой чтения;
это безопасно: исходники только читаются, частичных записей в них нет. После
восстановления тома задание ставится повторно.

## 5. Юниты systemd и сетевой том

В юниты добавляется доступ к смонтированному тому. Для пользовательских
юнитов (`~/.config/systemd/user/`) путь доступен как есть; для системных
(`/etc/systemd/system/`) с `ProtectSystem=full` нужно явно разрешить чтение:

```ini
[Unit]
After=network-online.target remote-fs.target
# Ждать появления тома (autofs) — иначе первый INSPECT упадёт.
RequiresMountsFor=/mnt/photos

[Service]
ReadOnlyPaths=/mnt/photos
ReadWritePaths=/var/lib/scene-fingerprint/data
```

`RequiresMountsFor` подтягивает automount до старта службы — без него первый
скан после перезагрузки может не увидеть папку.

API должен читать `SCENE_ORIGINALS_ROOTS` (только чтение), worker — читать
источник и писать в `SCENE_DATA`/preview/crops. Права на tom разделяются:
источник — чтение, производные — запись.

## 6. Без GPU и с удалённым GPU

На сервере без GPU:

- DINO/HYBRID остаются на CPU (это поддерживаемый режим, см.
  `docs/pipeline_performance.md`);
- QWEN идёт в Ollama. Если Ollama на другой машине сети, в «Техническом
  разделе → Распознавание» указывается её адрес; локальная модель на сервере
  не нужна;
- GPU-алерты в «Система» показывают карточки только там, где есть
  `nvidia-smi` — на сервере без GPU их просто не будет, это нормально.

## 6.1. Развёртывание на этой машине (2026-10-24)

Код, venv и данные лежат в одной папке без пробелов:

| Что | Где |
| --- | --- |
| Код + venv + данные | `/home/alexice/projects/albion-photobase` |
| Данные (previews, crops, input, fingerprints, logs, models, reports) | `/home/alexice/projects/albion-photobase/data` |
| Симлинк для человека | `/home/alexice/scene-fingerprint` → `/home/alexice/projects/albion-photobase` |
| Бэкапы | `/media/alexice/TEST/albion-photobase-backups` — отдельный диск `/dev/sda` |
| env (пароли, токены) | `/home/alexice/.config/scene-fingerprint.env` |

Юниты обращаются к коду **напрямую** по этому пути (пути с пробелами systemd
в `WorkingDirectory` не принимает, поэтому папка такая). Данные ищутся
относительно рабочего каталога (`SCENE_DATA` не задан), поэтому лежат
внутри — `data/`; абсолютные пути видео-производных и теневого журнала тоже
указывают на новую папку. Симлинк `/home/alexice/scene-fingerprint` остался
только как удобный ярлык для человека: ни один юнит через него не ходит.

Порядок переезда: остановить юниты → перенести каталог проекта (переименование
внутри диска, без копирования) → поправить пути в юнитах (в `deploy/systemd/user/`
и `~/.config/systemd/user/`, не забыть drop-in `scene-preview-worker.service.d/`),
env и `SCENE_BACKUP_DIR` → `daemon-reload` → запустить юниты → проверить
`/v1/photos`, число слепков и кадров. Откат — вернуть пути и перенести каталог
обратно.

24.10.2026, днём: старая папка
`~/projects/PhotoBAse/scene_fingerprint_RELEASE_v38_1_v33_20260815_1912 (2)`
удалена (вместе с ненужным корпусом `test/`), путь корпуса убран из
`SCENE_ORIGINALS_ROOTS`.

24.10.2026, вечером: проект перенесён в `~/projects/albion-photobase`, каталог
бэкапов — на `/dev/sda` (`/media/alexice/TEST/albion-photobase-backups`), история
бэкапов переехала вместе с ним. Проверено: слепков 38, фото в базе 56 870 — как
до переезда, все восемь юнитов активны и работают из нового пути.

## 7. Бэкап

Бэкап состоит из двух частей, и обе делает `scene-backup.timer` ежедневно
(02:30, oneshot-юнит с двумя `ExecStart`):

* `scripts/backup_db.py` — `pg_dump -Fc` PostgreSQL (схема, результаты,
  очереди, история). Восстановление — `docs/backup_restore.md`;
* `scripts/backup_data.py` — всё, что не в базе: `data/fingerprints/`
  (пересобрать их — часы работы), `data/logs/`, `data/reports/` и env-файл с
  секретами. Архив пишется во временный файл, проверяется (`tar -tz` должен
  показать все корни), хэшируется и только потом публикуется; права 600, потому
  что внутри env. Retention: последние 14 архивов и по одному за месяц.

Каталог бэкапов задаёт `SCENE_BACKUP_DIR` (в `scene-backup.service` —
`/media/alexice/TEST/albion-photobase-backups`, диск `/dev/sda`). Бэкап
намеренно лежит **на другом томе**, чем проект: бэкап внутри того, что он
сохраняет, не спасает от смерти диска. Обе части можно направить и на сетевой
том:

```bash
SCENE_BACKUP_DIR=/mnt/photos/backups .venv/bin/python scripts/backup_data.py --json
SCENE_BACKUP_DIR=/mnt/photos/backups .venv/bin/python scripts/backup_db.py --json
```

Скрипты создают каталог только тогда, когда это безопасно: отсутствующий
каталог создаётся лишь под существующей точкой монтирования, а каталог на томе
проекта отклоняется (осознанно — `--allow-same-filesystem`). Поэтому отключённый
диск даёт **ошибку и упавший юнит** (`systemctl --failed`, журнал
`scene-backup.service`), а не молчаливый бэкап на системный раздел.

**Требуется действие владельца.** `/dev/sda` монтируется udisks при входе в
графическую сессию, и в `/etc/fstab` его нет. Пока строки в fstab нет, после
перезагрузки без входа в сессию таймер 02:30 диска не найдёт и юнит упадёт (это
и есть ожидаемое «громко, а не молча»), но бэкапа не будет. Строка для
`/etc/fstab` (перед `mount -a` проверить `sudo findmnt --verify`):

```
UUID=a6aa2b04-308b-4580-95b6-8ae5ac461b52  /media/alexice/TEST  ext4  defaults,nofail,x-systemd.device-timeout=10  0  2
```

После добавления: `sudo systemctl daemon-reload && sudo mount -a && findmnt /media/alexice/TEST`.
`nofail` оставлен намеренно — из-за бэкап-диска машина не должна уходить в
аварийную загрузку.

### 7.1. Две цели: диск бэкапов и NAS

Восстановление с сетевого тома медленнее, и пока он недоступен, бэкапа не
будет. Поэтому практичная схема — **две цели**: диск `/dev/sda` (быстрый
restore) и NAS (переживает смерть машины). Сейчас настроена первая: отдельный
том уже спасает от смерти системного диска, но не от смерти сервера. Таймер
`scene-backup.timer` запускается ежедневно; retention (GFS) описан в
`docs/backup_restore.md`.

Перед изменением схемы (миграции 043/044 и далее) — бэкап обязателен, см.
`docs/maintenance.md`.

## 8. Порядок развёртывания (с нуля)

```bash
# 1. Код
sudo mkdir -p /opt/scene-fingerprint
sudo git clone <repo> /opt/scene-fingerprint      # или checkout + symlink без пробелов
cd /opt/scene-fingerprint
python3 -m venv .venv && .venv/bin/pip install -e .

# 2. Хранилище
# /etc/fstab -> mount -a -> проверить findmnt и доступ от пользователя службы

# 3. Окружение
sudo install -m 0640 -o root -g scene deploy/systemd/scene.env.example /etc/scene-fingerprint.env
sudo "${EDITOR:-vi}" /etc/scene-fingerprint.env   # пути, БД, корни

# 4. Схема БД
sudo -u scene .venv/bin/python scripts/migrate.py            # см. docs/db_setup.md

# 5. Первый пароль (иначе вход запрещён: паролей у сидов нет)
sudo -u scene .venv/bin/python scripts/set_password.py Администратор

# 6. SPA
cd frontend && bun install --frozen-lockfile && bun run build

# 7. Службы
sudo cp deploy/systemd/scene-api.service deploy/systemd/scene-worker.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now scene-api scene-worker

# 8. Проверка
curl -fsS http://127.0.0.1:8010/api/health
systemctl status scene-api scene-worker
```

Дополнительные юниты (preview, qwen, billboard, video, builder, maintenance,
backup) включаются **по одному** и только после проверки их предусловий —
они описаны в `deploy/systemd/README.md`.

## 9. Проверка развёртывания без остановки рабочего стенда

Развернуть копию рядом и убедиться, что она поднимается, можно **не трогая**
рабочие службы: достаточно поднять API на другом порту и не запускать ни одного
worker'а (иначе два процесса начнут разбирать одну и ту же очередь).

```bash
SRC="/home/alexice/projects/albion-photobase"          # рабочий каталог
DST="/tmp/scene-check"                                  # одноразовая копия
git clone --branch feature/video-ingest-editor-layout "$SRC" "$DST"
ln -sfn "$SRC/.venv" "$DST/.venv"                       # свой venv не нужен
ln -sfn "$SRC/frontend/node_modules" "$DST/frontend/node_modules"
cd "$DST" && .venv/bin/python -c "import app; print(app.__file__)"
cd frontend && bun run build
# копия одноразовая: БД берётся из общего env-файла (то есть рабочая),
# а артефакты — из ./data самой копии; чтобы увидеть настоящие превью,
# копию надо запускать с SCENE_DATA=<рабочий каталог>/data

cd "$DST" && set -a && . ~/.config/scene-fingerprint.env && set +a
SCENE_API_PORT=8020 nohup .venv/bin/python -m uvicorn app.api.main:app \
    --host 127.0.0.1 --port 8020 > /tmp/scene-check.log 2>&1 &

curl -fsS http://127.0.0.1:8020/api/health
curl -fsS http://127.0.0.1:8020/ | grep -o 'assets/index-[^"]*\.js'   # сборка SPA отдаётся
# вход и выборка данных через API (пример — гостевая учётка)
curl -s -X POST http://127.0.0.1:8020/api/v1/auth/login \
     -H 'Content-Type: application/json' -d '{"name":"гость","password":"альбион"}'
# затем: /api/v1/photos?limit=1, /api/v1/system

kill %1     # проверить, что порт освободился: ss -ltn | grep 8020
```

Результат такой проверки на 2026-10-22: `/api/health` → `ok`, SPA отдаётся
(`assets/index-*.js`), вход выполнен, `/api/v1/photos` вернул 583 записи,
`/api/v1/system` — карточка GPU и 0 алертов. Службы рабочего стенда не
затрагивались, миграции не применялись. Копию после проверки удалять: она
ссылается на рабочий venv и `node_modules` симлинками и сбивает с толку —
её легко принять за второй стенд (так и вышло 24.10.2026).

Ограничение метода: копия читает **ту же** рабочую БД, потому что окружение
берётся из общего env-файла. Это годится для проверки сборки и маршрутов, но не
заменяет приёмочный прогон на отдельной БД (см. §10).

## 9.1. Модель доступа: локальная сеть и VPN/туннель

Целевой режим: постоянная работа в LAN, изредка — снаружи через VPN или
туннель. Для такого режима **не нужно** прятать API на loopback: тогда он
недоступен из локальной сети. Правильная граница — сеть и аутентификация.

Что уже сделано (проверено на рабочем стенде):

- `SCENE_AUTH_REQUIRED=1` — без учётных данных API отвечает 401;
- `/docs` и `/openapi.json` закрыты (`SCENE_ENABLE_DOCS=0` по умолчанию);
- CORS не открыт: разрешены только dev-origins `localhost:5173`; сама SPA
  работает same-origin и CORS не использует;
- Ollama слушает только `127.0.0.1:11434`;
- lockout логина включён (`SCENE_LOGIN_LOCKOUT=1`), общий rate-limit API
  выключен (`SCENE_API_RATE_LIMIT=0`);
- сессионная кука `HttpOnly`, `SameSite=Lax`, принимается только на GET/HEAD.

Рекомендации для этой модели:

1. **Не пробрасывать 8010 на роутере.** Снаружи — только VPN (WireGuard,
   Tailscale) или туннель с собственной аутентификацией (Cloudflare Tunnel).
2. **Ограничить порт на файрволе** локальной подсетью и VPN-интерфейсом:
   ```bash
   sudo ufw allow from 192.168.0.0/16 to any port 8010 proto tcp
   sudo ufw allow in on tailscale0 to any port 8010 proto tcp
   sudo ufw deny 8010/tcp
   sudo ufw status numbered
   ```
   `ufw` уже активен; правила нужно проверить и, если нужно, добавить.
3. **TLS.** Внутри доверенной LAN допустим HTTP: трафик не выходит за
   пределы сети, а снаружи его шифрует VPN/туннель. Если появится HTTPS-
   прокси, TLS завершается на нём. `SCENE_COOKIE_SECURE=1` ставить только
   когда браузер обращается к сайту **по HTTPS**; при внутреннем HTTP и
   `Secure=1` кука просто не будет сохраняться.
4. **Пароли.** У всех ролей свои пароли; гостевой доступ read-only, но слабый
   пароль гостя всё равно даёт чтение всей базы.
5. **Rate-limit** имеет смысл включить при доступе через туннель
   (`SCENE_API_RATE_LIMIT`, запросов в минуту на IP), внутри LAN он не
   обязателен и может мешать опросу статусов.
6. **Проверка снаружи** — только через туннель; прямой проброс порта и
   `SCENE_CORS_ORIGINS=*` не использовать.

## 10. Что ещё нужно для «настоящего» приёмочного прогона

- отдельная тестовая БД (`photobase_test`) — сейчас локальная роль
  `lora_ingest` не имеет `CREATEDB`, поэтому интеграционные тесты пропускаются;
- TLS — по модели доступа из §9.1: внутри LAN не обязателен, снаружи его
  даёт VPN/туннель. `/docs` закрыт, lockout логина включён; общий rate-limit
  включается только при доступе через туннель;
- таймеры `scene-maintenance` и `scene-backup` установлены и активны
  (проверено `systemctl --user list-timers`);
- миграции применены по `schema/048` включительно (включая 043–047),
  `schema_migrations` содержит 49 записей.

## 11. Откат

- Службы: `systemctl disable --now` (для пользовательских — `systemctl --user`).
- Монтирование: убрать строку из `/etc/fstab`, `umount /mnt/photos`; `nofail`
  означает, что до этого сервер работает и без тома.
- Данные: `scripts/restore_db.py --backup <дамп> --target-db <бд>`; восстановление
  поверх рабочей БД требует `--allow-production` и делается только осознанно.
- Производные (preview/crops/fingerprints) пересоздаются повторным запуском
  соответствующих заданий; оригиналы при откате не изменяются.
