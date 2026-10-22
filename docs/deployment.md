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

## 7. Бэкап на NAS

`scripts/backup_db.py` пишет `pg_dump -Fc` в `SCENE_BACKUP_DIR`; его можно
направить на сетевой том — запись последовательная, проблем не создаёт:

```bash
SCENE_BACKUP_DIR=/mnt/photos/backups .venv/bin/python scripts/backup_db.py --json
```

Но восстановление с сетевого тома медленнее, и пока он недоступен, бэкапа не
будет. Поэтому практичная схема — **две цели**: локально (быстрый restore) и на
NAS (переживает смерть сервера). Таймер `scene-backup.timer` запускается
ежедневно; retention (GFS) описан в `docs/backup_restore.md`.

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
SRC="/home/alexice/projects/PhotoBAse/scene_fingerprint_RELEASE_v38_1_v33_20260815_1912 (2)"
DST="/home/alexice/projects/albion-photobase"
git clone --branch feature/video-ingest-editor-layout "$SRC" "$DST"
ln -sfn "$SRC/.venv" "$DST/.venv"                     # или свой venv
ln -sfn "$SRC/frontend/node_modules" "$DST/frontend/node_modules"
cd "$DST" && .venv/bin/python -c "import app; print(app.__file__)"
cd frontend && bun run build

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

Результат такой проверки на 2026-10-22 (копия в
`/home/alexice/projects/albion-photobase`): `/api/health` → `ok`, SPA отдаётся
(`assets/index-*.js`), вход выполнен, `/api/v1/photos` вернул 583 записи,
`/api/v1/system` — карточка GPU и 0 алертов. Службы рабочего стенда не
затрагивались, миграции не применялись.

Ограничение метода: копия читает **ту же** рабочую БД и те же артефакты, потому
что окружение берётся из общего env-файла. Это годится для проверки сборки и
маршрутов, но не заменяет приёмочный прогон на отдельной БД (см. §10).

## 10. Что ещё нужно для «настоящего» приёмочного прогона

- отдельная тестовая БД (`photobase_test`) — сейчас локальная роль
  `lora_ingest` не имеет `CREATEDB`, поэтому интеграционные тесты пропускаются;
- TLS-прокси перед API: сейчас API слушает `0.0.0.0:8010`, `/docs` открыт,
  rate-limit логина отсутствует (см. `docs/roadmap_albion_20261022.md`, этап 1);
- установка таймеров `scene-maintenance` и `scene-backup` на сервере;
- применение pending-миграций 043 и 044 после бэкапа.

## 11. Откат

- Службы: `systemctl disable --now` (для пользовательских — `systemctl --user`).
- Монтирование: убрать строку из `/etc/fstab`, `umount /mnt/photos`; `nofail`
  означает, что до этого сервер работает и без тома.
- Данные: `scripts/restore_db.py --backup <дамп> --target-db <бд>`; восстановление
  поверх рабочей БД требует `--allow-production` и делается только осознанно.
- Производные (preview/crops/fingerprints) пересоздаются повторным запуском
  соответствующих заданий; оригиналы при откате не изменяются.
