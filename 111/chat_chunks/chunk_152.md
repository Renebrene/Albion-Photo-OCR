## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 👤 **User** — 2026-08-19 01:06:44

scripts/qwen4b_output_v01.py:178:            WHERE qwen_status = 'processing'
scripts/qwen4b_output_v01.py:203:        qwen_status = pending
scripts/qwen4b_output_v01.py:221:                qwen_status = 'pending'
scripts/qwen4b_output_v01.py:242:                qwen_status = 'processing',
scripts/qwen4b_output_v01.py:246:                AND qwen_status = 'pending'
scripts/qwen4b_output_v01.py:336:                qwen_status = 'done',
scripts/qwen4b_output_v01.py:429:    Ошибка Qwen меняет только qwen_status.
scripts/qwen4b_output_v01.py:440:                qwen_status = 'error',
scripts/qwen4b_output_v01.py:720:                WHERE qwen_status = 'pending'
scripts/migrate_sqlite_to_postgres.py:75:                qwen_status,
scripts/migrate_sqlite_to_postgres.py:111:                row["qwen_status"],
scripts/migrate_sqlite_to_postgres.py:165:                    qwen_status,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
cat app/web/components/technical_modules/photo_processing.py
import asyncio
import re
from pathlib import Path

from nicegui import ui

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"

DAILY_SCRIPT = (
    PROJECT
    / "scripts"
    / "run_daily_hybrid_v12.sh"
)

def build_photo_processing():

    # ============================================================
    # STATE
    # ============================================================

    process = None

    # ============================================================
    # HELPERS
    # ============================================================

    def resolve_path(value: str) -> Path:

        path = Path(
            value
        ).expanduser()

        if not path.is_absolute():
            path = PROJECT / path

        return path

    def set_status(
        text: str,
        color: str = "text-grey-7",
    ):
        status_label.text = text

        status_label.classes(
            remove=(
                "text-grey-7 "
                "text-positive "
                "text-warning "
                "text-negative"
            )
        )

        status_label.classes(
            add=color
        )

    # ============================================================
    # RUN
    # ============================================================

    async def run_pipeline():

        nonlocal process

        input_dir = resolve_path(
            source_input.value
        )

        if not input_dir.exists():
            ui.notify(
                f"Папка не найдена: {input_dir}",
                type="negative",
            )
            set_status(
                "● Ошибка",
                "text-negative",
            )
            return

        if not input_dir.is_dir():
            ui.notify(
                f"Источник не является папкой: {input_dir}",
                type="negative",
            )
            set_status(
                "● Ошибка",
                "text-negative",
            )
            return

        images = [
            p
            for p in input_dir.iterdir()
            if (
                p.is_file()
                and p.suffix.lower()
                in {
                    ".jpg",
                    ".jpeg",
                    ".png",
                }
            )
        ]

        if not images:
            ui.notify(
                "В папке нет фотографий",
                type="negative",
            )
            set_status(
                "● Ошибка",
                "text-negative",
            )
            return

        if not DAILY_SCRIPT.exists():
            ui.notify(
                f"Не найден скрипт: {DAILY_SCRIPT}",
                type="negative",
            )
            set_status(
                "● Ошибка",
                "text-negative",
            )
            return

        run_button.disable()
        stop_button.enable()

        set_status(
            f"● Обработка · {len(images)} фото",
            "text-warning",
        )

        try:

            env = {
                "PATH": (
                    f"{Path.home() / '.local/bin'}:"
                    "/usr/local/sbin:"
                    "/usr/local/bin:"
                    "/usr/sbin:"
                    "/usr/bin:"
                    "/sbin:"
                    "/bin"
                ),
                "HOME": str(Path.home()),
                "PYTHONUNBUFFERED": "1",
            }

            process = await asyncio.create_subprocess_exec(
                "bash",
                str(DAILY_SCRIPT),
                cwd=str(PROJECT),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            output_lines = []

            while True:

                line = await process.stdout.readline()

                if not line:
                    break

                text = line.decode(
                    "utf-8",
                    errors="replace",
                ).rstrip()

                if text:
                    output_lines.append(text)

                    set_status(
                        text[-180:],
                        "text-warning",
                    )

            returncode = await process.wait()

            output = "\n".join(
                output_lines
            )

            if returncode != 0:

                set_status(
                    f"● Ошибка · код {returncode}",
                    "text-negative",
                )

                ui.notify(
                    "Обработка завершилась ошибкой",
                    type="negative",
                    timeout=8000,
                )

                return

            # ----------------------------------------------------
            # RESULT DIRECTORY
            # ----------------------------------------------------

            match = re.search(
                r"Output\s*:\s*(.+)",
                output,
            )

            result_dir = None

            if match:
                candidate = Path(
                    match.group(1).strip()
                )

                if candidate.exists():
                    result_dir = candidate

            # fallback
            if result_dir is None:

                daily_root = (
                    PROJECT
                    / "data"
                    / "output"
                    / "daily"
                )

                if daily_root.exists():

                    runs = [
                        p
                        for p in daily_root.iterdir()
                        if p.is_dir()
                    ]

                    if runs:
                        result_dir = max(
                            runs,
                            key=lambda p: p.name,
                        )

            if result_dir is not None:

                output_input.value = str(
                    result_dir
                )

                set_status(
                    "● Готово",
                    "text-positive",
                )

                ui.notify(
                    "Обработка завершена",
                    type="positive",
                    timeout=5000,
                )

            else:

                set_status(
                    "● Готово",
                    "text-positive",
                )

                ui.notify(
                    "Обработка завершена, "
                    "но папка результата не определена",
                    type="warning",
                    timeout=8000,
                )

        except Exception as exc:

            set_status(
                "● Ошибка",
                "text-negative",
            )

            ui.notify(
                f"Ошибка запуска: {exc}",
                type="negative",
                timeout=8000,
            )

        finally:

            process = None

            run_button.enable()
            stop_button.disable()

    # ============================================================
    # STOP
    # ============================================================

    async def stop_pipeline():

        nonlocal process

        if process is None:
            return

        try:

            process.terminate()

            set_status(
                "● Остановка...",
                "text-warning",
            )

            ui.notify(
                "Обработка останавливается",
                type="warning",
                timeout=4000,
            )

        except ProcessLookupError:
            pass

        except Exception as exc:

            ui.notify(
                f"Ошибка остановки: {exc}",
                type="negative",
                timeout=8000,
            )

    # ============================================================
    # SOURCE PICKER
    # ============================================================

    async def choose_source():

        ui.notify(
            "Выбор папки источника подключим отдельно.",
            type="info",
            timeout=3000,
        )

    # ============================================================
    # UI
    # ============================================================

    with ui.card().classes(
        "w-full"
    ):

        # --------------------------------------------------------
        # TITLE
        # --------------------------------------------------------

        ui.label(
            "ФОТООБРАБОТКА"
        ).classes(
            "text-lg font-bold"
        )

        ui.label(
            "Главная рабочая операция"
        ).classes(
            "text-sm text-grey-6"
        )

        ui.separator().classes(
            "my-3"
        )

        # --------------------------------------------------------
        # PATHS
        # --------------------------------------------------------

        with ui.row().classes(
            "w-full items-end gap-3"
        ):

            with ui.column().classes(
                "flex-1 gap-1"
            ):

                ui.label(
                    "Источник фотографий"
                ).classes(
                    "text-sm font-medium"
                )

                with ui.row().classes(
                    "w-full items-center gap-2"
                ):

                    source_input = ui.input(
                        value=str(
                            PROJECT
                            / "data"
                            / "input"
                            / "daily"
                        ),
                    ).props(
                        "outlined dense"
                    ).classes(
                        "flex-1"
                    )

                    source_button = ui.button(
                        "Выбрать",
                        icon="folder_open",
                        on_click=choose_source,
                    ).props(
                        "outline dense"
                    )

            with ui.column().classes(
                "flex-1 gap-1"
            ):

                ui.label(
                    "Результат"
                ).classes(
                    "text-sm font-medium"
                )

                output_input = ui.input(
                    value=str(
                        PROJECT
                        / "data"
                        / "output"
                        / "daily"
                    ),
                ).props(
                    "outlined dense readonly"
                ).classes(
                    "w-full"
                )

        # --------------------------------------------------------
        # CONTROLS
        # --------------------------------------------------------

        with ui.row().classes(
            "w-full items-center gap-3 mt-4"
        ):

            run_button = ui.button(
                "▶  ЗАПУСТИТЬ",
                on_click=run_pipeline,
            ).props(
                "unelevated"
            ).classes(
                "flex-1"
            )

            stop_button = ui.button(
                "■  ОСТАНОВИТЬ",
                on_click=stop_pipeline,
            ).props(
                "outline color=negative"
            ).classes(
                "flex-1"
            )

            stop_button.disable()

        # --------------------------------------------------------
        # STATUS
        # --------------------------------------------------------

        with ui.row().classes(
            "w-full justify-center items-center mt-3"
        ):

            status_label = ui.label(
                "● Готов"
            ).classes(
                "text-sm text-grey-7"
            )

        ui.separator().classes(
            "my-3"
        )

        ui.label(
            "DINO v33 / Hybrid v12 и Qwen3-VL 4B "
            "работают независимо и управляются ниже."
        ).classes(
            "text-xs text-grey-6"
        )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:06:45

Да. Теперь картина полная.

**Этот `photo_processing.py` сейчас действительно запускает backend**, а нам нужно его превратить именно в **панель управления + мониторинг**, не трогая существующую обработку.

Причём пути я бы оставил именно такими:

```text
Источник:  [ /data/input/daily                         ] [Выбрать]
Результат: [ /data/output/daily                        ]
```

в одной строке.

А ниже — две независимые ветки:

```text
DINO v33 / Hybrid v12
[▶ Запустить] [■ Остановить]
██████████████░░░░░░  142 / 200
Готово: 142   В работе: 1   Очередь: 57   Ошибки: 0

Qwen3-VL 4B
[▶ Запустить] [■ Остановить]
████████░░░░░░░░░░░░  83 / 200
Готово: 83   В работе: 1   Очередь: 116   Ошибки: 0
```

Но есть важный момент: **не надо вычислять прогресс по stdout `run_daily_hybrid_v12.sh`**. У нас уже есть правильный источник истины — `photos`.

Из твоего grep видно:

```text
dino_status = pending
dino_status = processing
dino_status = done
dino_status = error
```

и аналогично:

```text
qwen_status = pending
qwen_status = processing
qwen_status = done
qwen_status = error
```

То есть UI может просто регулярно делать агрегат:

```sql
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE dino_status = 'done')       AS done,
    COUNT(*) FILTER (WHERE dino_status = 'processing') AS processing,
    COUNT(*) FILTER (WHERE dino_status = 'pending')    AS pending,
    COUNT(*) FILTER (WHERE dino_status = 'error')      AS error
FROM photos;
```

и то же для Qwen.

### Поэтому архитектура UI будет такая

```text
                 ФОТООБРАБОТКА

Источник [.........................] [Выбрать]
Результат [.................................]

          [ ▶ ЗАПУСТИТЬ ] [ ■ ОСТАНОВИТЬ ]

                    🟠 ИДЁТ ОБРАБОТКА

DINO v33 / Hybrid v12

[ ▶ Запустить ] [ ■ Остановить ]

██████████████░░░░░░  142 / 200

Готово 142    В работе 1    Очередь 57    Ошибки 0

Qwen3-VL 4B

[ ▶ Запустить ] [ ■ Остановить ]

████████░░░░░░░░░░░░  83 / 200

Готово 83     В работе 1    Очередь 116   Ошибки 0
```

При этом:

- **главная `ЗАПУСТИТЬ`** запускает существующий общий pipeline;
- **главная `ОСТАНОВИТЬ`** останавливает его;
- индивидуальные кнопки управляют соответствующими backend-ветками;
- статистика **не зависит от того, какой процесс был запущен из UI**;
- после перезагрузки страницы статистика снова читается из БД;
- после STOP значения `done/error/pending` сохраняются;
- никаких изменений в `dino_worker.py`, `qwen_worker.py`, `photo_ingest.py` и `run_daily_hybrid_v12.sh` не требуется.

**Следующий шаг — посмотреть, откуда сейчас UI получает подключение к PostgreSQL/SQLite.** Не будем придумывать новое подключение.

Дай команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat app/web/photo_db.py
```

И после этого я дам тебе **полный `photo_processing.py` одной командой**, уже с реальной статистикой из `photos`, автообновлением прогресса и нужной разметкой.

---

### 👤 **User** — 2026-08-19 01:07:22

)

        ui.label(
            "DINO v33 / Hybrid v12 и Qwen3-VL 4B "
            "работают независимо и управляются ниже."
        ).classes(
            "text-xs text-grey-6"
        )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
cat app/web/photo_db.py
import psycopg2

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

def get_photo_records() -> list[dict]:
    """
    Загружает все записи фотографий из PostgreSQL.
    """

    sql = """
        SELECT
            id,
            photo_id,
            address,
            filename,
            path,
            source_path,
            original_filename,
            preview_path,
            client,
            brand,
            category,
            description,
            confidence,
            qwen_status,
            qwen_time_sec,
            text_json,
            colors_json,
            objects_json,
            environment_json,
            image_quality_json,
            camera_view_json,
            scene_objects_json,
            analysis_quality_json,
            raw_json,
            created_at,
            dino_fingerprint,
            dino_score,
            dino_second_score,
            dino_margin,
            hybrid_original_id,
            hybrid_final_id,
            hybrid_changed,
            hybrid_old_score,
            hybrid_score,
            hybrid_margin,
            hybrid_neighbors,
            status,
            dino_status,
            sort_status
        FROM photos
        ORDER BY id
    """

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:

            cur.execute(sql)

            columns = [
                desc[0]
                for desc in cur.description
            ]

            rows = cur.fetchall()

    return [
        dict(zip(columns, row))
        for row in rows
    ]

def build_photo_record_index(project_root):
    """
    Создаёт индекс PostgreSQL-записей по абсолютному пути файла.
    """

    records = get_photo_records()

    index = {}

    for record in records:

        path = record.get("path")

        if not path:
            continue

        from pathlib import Path

        db_path = Path(path)

        if not db_path.is_absolute():
            db_path = project_root / db_path

        # Основной индекс: полный абсолютный путь
        index[str(db_path.resolve())] = record

        # Fallback для daily/test_sorted_v2 и других
        # запусков, где один и тот же файл имеет разные
        # корневые каталоги.
        #
        # Ключ: адрес + имя файла
        address = str(record.get("address") or "").strip()
        filename = db_path.name

        if address and filename:
            index[f"__ADDR_FILE__:{address}:{filename}"] = record

    return index
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:07:24

Отлично. Тогда **PostgreSQL уже является готовым источником статистики**, и новый backend для UI вообще не нужен.

Я бы сейчас сделал `photo_processing.py` так:

- существующий запуск `run_daily_hybrid_v12.sh` **оставляем**;
- источник — редактируемый + `Выбрать`;
- результат — **readonly**, без кнопки;
- обе строки путей — в один ряд;
- DINO и Qwen — отдельные панели;
- статистика берётся из `photos.dino_status` / `photos.qwen_status`;
- прогресс обновляется автоматически, например раз в 1 секунду;
- `processing` показывает текущую работу;
- `pending` — очередь;
- `done` — готово;
- `error` — ошибки;
- главный индикатор определяется по состоянию обеих веток;
- никаких изменений backend-воркеров.

И ещё важный момент: у тебя `photo_db.py` уже импортирует `psycopg2`, поэтому **не надо дублировать настройки БД в `photo_processing.py`**. Лучше использовать существующий `PG_CONFIG` или добавить маленькую функцию статистики в `photo_db.py`.

Для статистики достаточно отдельного запроса:

```sql
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE dino_status = 'done') AS done,
    COUNT(*) FILTER (WHERE dino_status = 'processing') AS processing,
    COUNT(*) FILTER (WHERE dino_status = 'pending') AS pending,
    COUNT(*) FILTER (WHERE dino_status = 'error') AS error
FROM photos;
```

и такой же для Qwen.

### Я бы не трогал `get_photo_records()`

Он нужен остальному интерфейсу и уже достаточно тяжёлый — тянуть всю таблицу каждую секунду для прогресса совершенно не нужно.

Лучше добавить в `photo_db.py`:

```python
def get_processing_stats() -> dict:
    ...
```

с двумя лёгкими агрегатными запросами.

А `photo_processing.py` будет вызывать только эту функцию через `ui.timer(1.0, refresh_stats)`.

То есть получится правильное разделение:

```text
                    PostgreSQL
                         │
             ┌───────────┴───────────┐
             │                       │
       существующий backend       Web UI
             │                       │
       DINO / Qwen workers       статистика
             │                       │
             └──────── photos ───────┘
```

**Backend не меняем. UI только наблюдает и управляет.**

Если хочешь сделать это прямо сейчас, следующая команда:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nano app/web/photo_db.py
```

и туда добавим только функцию статистики. Затем я дам одной командой полный `photo_processing.py`.

---

### 👤 **User** — 2026-08-19 01:07:39

давай

---

### 🤖 **Assistant** — 2026-08-19 01:07:40

Да. Делаем минимально: **backend не трогаем**, добавляем статистику в `photo_db.py`, затем полностью заменяем UI-компонент.

### 1. Добавляем функцию статистики

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python - <<'PY'
from pathlib import Path

p = Path("app/web/photo_db.py")
text = p.read_text()

marker = "\n\ndef build_photo_record_index(project_root):"

if "def get_processing_stats()" in text:
    print("get_processing_stats() уже существует")
    raise SystemExit

func = r'''

def get_processing_stats() -> dict:
    """
    Быстрая статистика независимых веток DINO и Qwen.
    Источник истины — PostgreSQL таблица photos.
    """

    sql = """
        SELECT
            COUNT(*) AS total,

            COUNT(*) FILTER (
                WHERE dino_status = 'done'
            ) AS dino_done,

            COUNT(*) FILTER (
                WHERE dino_status = 'processing'
            ) AS dino_processing,

            COUNT(*) FILTER (
                WHERE dino_status = 'pending'
            ) AS dino_pending,

            COUNT(*) FILTER (
                WHERE dino_status = 'error'
            ) AS dino_error,

            COUNT(*) FILTER (
                WHERE qwen_status = 'done'
            ) AS qwen_done,

            COUNT(*) FILTER (
                WHERE qwen_status = 'processing'
            ) AS qwen_processing,

            COUNT(*) FILTER (
                WHERE qwen_status = 'pending'
            ) AS qwen_pending,

            COUNT(*) FILTER (
                WHERE qwen_status = 'error'
            ) AS qwen_error

        FROM photos
    """

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()

    return {
        "total": row[0] or 0,

        "dino": {
            "done": row[1] or 0,
            "processing": row[2] or 0,
            "pending": row[3] or 0,
            "error": row[4] or 0,
        },

        "qwen": {
            "done": row[5] or 0,
            "processing": row[6] or 0,
            "pending": row[7] or 0,
            "error": row[8] or 0,
        },
    }
'''

text = text.replace(marker, func + marker)

p.write_text(text)

print("OK: get_processing_stats() добавлена")
PY
```

Проверяем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python - <<'PY'
from app.web.photo_db import get_processing_stats
import pprint
pprint.pp(get_processing_stats())
PY
```

Должно получиться примерно:

```text
{
    'total': 200,
    'dino': {
        'done': 142,
        'processing': 1,
        'pending': 57,
        'error': 0
    },
    'qwen': {
        'done': 83,
        'processing': 1,
        'pending': 116,
        'error': 0
    }
}
```

### 2. После успешной проверки заменяем `photo_processing.py`

Пока **не запускай второй шаг**, если первый тест выдаст ошибку. Пришли его вывод — поправим подключение.

Если статистика вернулась нормально, следующим сообщением дам готовую замену `photo_processing.py` с:

- одной строкой **Источник / Результат**;
- кнопкой выбора только для источника;
- общей `ЗАПУСТИТЬ / ОСТАНОВИТЬ`;
- отдельными DINO/Qwen кнопками;
- двумя progress bar;
- `Готово / В работе / Очередь / Ошибки`;
- автообновлением раз в секунду;
- 🟢 / 🟠 / 🔴 состоянием;
- без изменения существующего backend.

---

### 👤 **User** — 2026-08-19 01:08:09

uv

---

### 🤖 **Assistant** — 2026-08-19 01:08:10

Да, у нас проект запускается через **uv**, поэтому тест тоже через `uv run`.

Замени предыдущую проверочную команду на:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.photo_db import get_processing_stats
import pprint

pprint.pp(get_processing_stats())
PY
```

И саму установку функции тоже лучше выполнить через `uv run python`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/photo_db.py")
text = p.read_text()

if "def get_processing_stats()" in text:
    print("get_processing_stats() уже существует")
    raise SystemExit

marker = "\n\ndef build_photo_record_index(project_root):"

func = r'''

def get_processing_stats() -> dict:
    """
    Статистика независимых веток DINO и Qwen.
    Источник истины — PostgreSQL таблица photos.
    """

    sql = """
        SELECT
            COUNT(*) AS total,

            COUNT(*) FILTER (
                WHERE dino_status = 'done'
            ) AS dino_done,

            COUNT(*) FILTER (
                WHERE dino_status = 'processing'
            ) AS dino_processing,

            COUNT(*) FILTER (
                WHERE dino_status = 'pending'
            ) AS dino_pending,

            COUNT(*) FILTER (
                WHERE dino_status = 'error'
            ) AS dino_error,

            COUNT(*) FILTER (
                WHERE qwen_status = 'done'
            ) AS qwen_done,

            COUNT(*) FILTER (
                WHERE qwen_status = 'processing'
            ) AS qwen_processing,

            COUNT(*) FILTER (
                WHERE qwen_status = 'pending'
            ) AS qwen_pending,

            COUNT(*) FILTER (
                WHERE qwen_status = 'error'
            ) AS qwen_error

        FROM photos
    """

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()

    return {
        "total": row[0] or 0,
        "dino": {
            "done": row[1] or 0,
            "processing": row[2] or 0,
            "pending": row[3] or 0,
            "error": row[4] or 0,
        },
        "qwen": {
            "done": row[5] or 0,
            "processing": row[6] or 0,
            "pending": row[7] or 0,
            "error": row[8] or 0,
        },
    }
'''

if marker not in text:
    raise SystemExit("Не найдено место вставки")

text = text.replace(marker, func + marker)

p.write_text(text)

print("OK")
PY
```

Потом:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.photo_db import get_processing_stats
import pprint
pprint.pp(get_processing_stats())
PY
```

**Backend обработки при этом вообще не меняем.** `photo_processing.py` будет только читать состояние из PostgreSQL и отображать его в интерфейсе.

---

### 👤 **User** — 2026-08-19 01:08:23

command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.photo_db import get_processing_stats
import pprint

pprint.pp(get_processing_stats())
PY
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/photo_db.py", line 1
    cd ~/projects/scene_fingerprint_mvp_v02 && \
       ^
SyntaxError: invalid syntax
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:08:25

Да, вижу ошибку. **В `app/web/photo_db.py` случайно попали строки shell-команды**:

```text
cd ~/projects/scene_fingerprint_mvp_v02 && \
```

Поэтому Python пытается интерпретировать их как код.

Ничего страшного. Сначала восстановим `photo_db.py`, затем добавим статистику правильно.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,25p' app/web/photo_db.py
```

Пришли вывод. **Пока ничего больше не запускай и не исправляй вручную** — я дам одну команду, которая аккуратно восстановит файл и добавит `get_processing_stats()`.

---

### 👤 **User** — 2026-08-19 01:08:37

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.photo_db import get_processing_stats
import pprint

pprint.pp(get_processing_stats())
PY
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/photo_db.py", line 1
    cd ~/projects/scene_fingerprint_mvp_v02 && \
       ^
SyntaxError: invalid syntax
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,25p' app/web/photo_db.py
cd ~/projects/scene_fingerprint_mvp_v02 && \
python - <<'PY'
from pathlib import Path

p = Path("app/web/photo_db.py")
text = p.read_text()

marker = "\n\ndef build_photo_record_index(project_root):"

if "def get_processing_stats()" in text:
    print("get_processing_stats() уже существует")
    raise SystemExit

func = r'''

def get_processing_stats() -> dict:
    """
    Быстрая статистика независимых веток DINO и Qwen.
    Источник истины — PostgreSQL таблица photos.
    """

    sql = """
        SELECT
            COUNT(*) AS total,

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:08:38

Да, теперь понятно. Мы **записали саму команду в `photo_db.py` вместо выполнения команды**. Поэтому файл сейчас повреждён.

Сделаем безопасно: восстановим `photo_db.py` из того содержимого, которое ты уже показывал, и сразу добавим статистику.

Выполни **целиком одну команду**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && cat > app/web/photo_db.py <<'PY'
import psycopg2

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

def get_photo_records() -> list[dict]:
    """
    Загружает все записи фотографий из PostgreSQL.
    """

    sql = """
        SELECT
            id,
            photo_id,
            address,
            filename,
            path,
            source_path,
            original_filename,
            preview_path,
            client,
            brand,
            category,
            description,
            confidence,
            qwen_status,
            qwen_time_sec,
            text_json,
            colors_json,
            objects_json,
            environment_json,
            image_quality_json,
            camera_view_json,
            scene_objects_json,
            analysis_quality_json,
            raw_json,
            created_at,
            dino_fingerprint,
            dino_score,
            dino_second_score,
            dino_margin,
            hybrid_original_id,
            hybrid_final_id,
            hybrid_changed,
            hybrid_old_score,
            hybrid_score,
            hybrid_margin,
            hybrid_neighbors,
            status,
            dino_status,
            sort_status
        FROM photos
        ORDER BY id
    """

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)

            columns = [
                desc[0]
                for desc in cur.description
            ]

            rows = cur.fetchall()

    return [
        dict(zip(columns, row))
        for row in rows
    ]

def get_processing_stats() -> dict:
    """
    Быстрая статистика независимых веток DINO и Qwen.
    Источник истины — PostgreSQL таблица photos.
    """

    sql = """
        SELECT
            COUNT(*) AS total,

            COUNT(*) FILTER (
                WHERE dino_status = 'done'
            ) AS dino_done,

            COUNT(*) FILTER (
                WHERE dino_status = 'processing'
            ) AS dino_processing,

            COUNT(*) FILTER (
                WHERE dino_status = 'pending'
            ) AS dino_pending,

            COUNT(*) FILTER (
                WHERE dino_status = 'error'
            ) AS dino_error,

            COUNT(*) FILTER (
                WHERE qwen_status = 'done'
            ) AS qwen_done,

            COUNT(*) FILTER (
                WHERE qwen_status = 'processing'
            ) AS qwen_processing,

            COUNT(*) FILTER (
                WHERE qwen_status = 'pending'
            ) AS qwen_pending,

            COUNT(*) FILTER (
                WHERE qwen_status = 'error'
            ) AS qwen_error

        FROM photos
    """

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()

    return {
        "total": row[0] or 0,

        "dino": {
            "done": row[1] or 0,
            "processing": row[2] or 0,
            "pending": row[3] or 0,
            "error": row[4] or 0,
        },

        "qwen": {
            "done": row[5] or 0,
            "processing": row[6] or 0,
            "pending": row[7] or 0,
            "error": row[8] or 0,
        },
    }

def build_photo_record_index(project_root):
    """
    Создаёт индекс PostgreSQL-записей по абсолютному пути файла.
    """

    records = get_photo_records()

    index = {}

    for record in records:

        path = record.get("path")

        if not path:
            continue

        from pathlib import Path

        db_path = Path(path)

        if not db_path.is_absolute():
            db_path = project_root / db_path

        # Основной индекс: полный абсолютный путь
        index[str(db_path.resolve())] = record

        # Fallback для daily/test_sorted_v2 и других
        # запусков, где один и тот же файл имеет разные
        # корневые каталоги.
        #
        # Ключ: адрес + имя файла
        address = str(record.get("address") or "").strip()
        filename = db_path.name

        if address and filename:
            index[f"__ADDR_FILE__:{address}:{filename}"] = record

    return index
PY
```

Теперь **обязательно проверяем**, что файл нормальный:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile app/web/photo_db.py
```

Если команда ничего не вывела — синтаксис исправлен.

И только потом:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.photo_db import get_processing_stats
import pprint

pprint.pp(get_processing_stats())
PY
```

После этого получим реальные значения DINO/Qwen из PostgreSQL и уже перейдём к `photo_processing.py`.

---

### 👤 **User** — 2026-08-19 01:09:05

int_mvp_v02 && \
uv run python - <<'PY'
from app.web.photo_db import get_processing_stats
import pprint

pprint.pp(get_processing_stats())
PY
{'total': 526,
 'dino': {'done': 526, 'processing': 0, 'pending': 0, 'error': 0},
 'qwen': {'done': 1, 'processing': 0, 'pending': 525, 'error': 0}}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:09:06

Отлично. **Статистика из PostgreSQL уже работает**, и теперь можно не трогать backend обработки вообще.

Сейчас база показывает:

- **Всего:** 526
- **DINO:** 526 / 526 - готово
- **Qwen:** 1 / 526 - готово, 525 - в очереди
- Ошибок нет
- `processing = 0`

То есть веб-интерфейсу осталось только **читать эти состояния и показывать прогресс**.

Следующий шаг - переделать `photo_processing.py` так, чтобы он был именно панелью управления/мониторинга:

```text
ФОТООБРАБОТКА

Источник [ /data/input/daily                    ] [Выбрать]
Результат [ /data/output/daily                  ]

[ ▶ ЗАПУСТИТЬ ]                         [ ■ ОСТАНОВИТЬ ]

                    🟠 ИДЁТ ОБРАБОТКА

DINO v33 / Hybrid v12
[ ▶ Запустить ] [ ■ Остановить ]

████████████████████████████████  526 / 526

Готово: 526    В работе: 0    В очереди: 0    Ошибки: 0

Qwen3-VL 4B
[ ▶ Запустить ] [ ■ Остановить ]

░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  1 / 526

Готово: 1      В работе: 0    В очереди: 525   Ошибки: 0
```

Причём **DINO и Qwen не должны запускаться из этого компонента заново**, если существующие worker/controller уже умеют ими управлять. Мы подключаемся к ним через существующий backend.

И главное - прогресс надо получать **не из stdout скрипта**, как сейчас делает `photo_processing.py`, а непосредственно из `photos.dino_status` / `photos.qwen_status`.

Я бы сейчас сделал именно это:

1. убрать из `photo_processing.py` самостоятельный `create_subprocess_exec()` для основной обработки;
2. оставить выбор **только источника**;
3. результат сделать `readonly`;
4. добавить общую кнопку запуска/остановки;
5. добавить отдельные DINO/Qwen кнопки;
6. добавить две независимые progress bar;
7. каждые ~1 секунду читать `get_processing_stats()`;
8. автоматически обновлять:
   - `%`
   - `готово`
   - `в работе`
   - `очередь`
   - `ошибки`;
9. общий индикатор:
   - 🟢 готово;
   - 🟠 работает;
   - 🔴 ошибка.

**Backend распознавания при этом вообще не меняем.**

И ещё важный момент: текущий результат

```text
DINO done = 526
Qwen pending = 525
```

идеально подтверждает нашу новую архитектуру: **DINO уже полностью закончил свою ветку, а Qwen независимо стоит в очереди.**

---

### 👤 **User** — 2026-08-19 01:09:23

lfktt

---

### 🤖 **Assistant** — 2026-08-19 01:09:24

Да, теперь всё правильно: **статистика из PostgreSQL читается**.

Сейчас backend показывает:

- **Всего:** 526 фото
- **DINO:** 526 / 526 готово
- **Qwen:** 1 готово, 525 в очереди
- Ошибок нет
- Сейчас ничего не выполняется

То есть `get_processing_stats()` уже можно напрямую подключать к веб-интерфейсу.

Следующий шаг — **не трогать backend обработки**, а сделать UI:

```text
DINO v33 / Hybrid v12
[ ▶ ЗАПУСТИТЬ ] [ ■ ОСТАНОВИТЬ ]

████████████████████ 526 / 526
Готово: 526   В работе: 0   В очереди: 0   Ошибки: 0

Qwen3-VL 4B
[ ▶ ЗАПУСТИТЬ ] [ ■ ОСТАНОВИТЬ ]

░░░░░░░░░░░░░░░░░░░░ 1 / 526
Готово: 1   В работе: 0   В очереди: 525   Ошибки: 0
```

И эти значения должны **автоматически обновляться**, пока работают воркеры.

При этом кнопка **«ФОТООБРАБОТКА → ЗАПУСТИТЬ»** остаётся главным запуском, а DINO/Qwen получают свои отдельные кнопки управления.

---

### 👤 **User** — 2026-08-19 01:09:35

ghjljk;fq

---

### 🤖 **Assistant** — 2026-08-19 01:09:35

Похоже, раскладка клавиатуры переключилась 🙂  
Если ты имел в виду **«продолжай»** — продолжаем с `photo_processing.py`.

---

### 👤 **User** — 2026-08-19 01:09:46

да

---

### 🤖 **Assistant** — 2026-08-19 01:09:47

> **Searching the web**
>
>
> **Searching the web**
>
> 
>
> Worked for a couple of seconds

Тогда идём дальше. Сейчас **не будем придумывать API управления DINO/Qwen** - сначала найдём уже существующий controller/worker API и подключим UI к нему.

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'start.*(dino|qwen)|stop.*(dino|qwen)|dino.*(start|stop)|qwen.*(start|stop)|subprocess|Popen|create_subprocess' \
app/pipeline app/workers app/web \
--include="*.py" | head -300
```

**Backend не меняем.** Нам нужно только увидеть, чем уже управляются процессы, чтобы `photo_processing.py` стал чистым UI-монитором с:

- общим `▶ ЗАПУСТИТЬ / ■ ОСТАНОВИТЬ`;
- отдельным DINO;
- отдельным Qwen;
- прогрессом из `photos`;
- статистикой `done / processing / pending / error`;
- автоматическим обновлением примерно раз в секунду.

---

### 👤 **User** — 2026-08-19 01:10:01

int_mvp_v02 && \
uv run python - <<'PY'
from app.web.photo_db import get_processing_stats
import pprint

pprint.pp(get_processing_stats())
PY
{'total': 526,
 'dino': {'done': 526, 'processing': 0, 'pending': 0, 'error': 0},
 'qwen': {'done': 1, 'processing': 0, 'pending': 525, 'error': 0}}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'start.*(dino|qwen)|stop.*(dino|qwen)|dino.*(start|stop)|qwen.*(start|stop)|subprocess|Popen|create_subprocess' \
app/pipeline app/workers app/web \
--include="*.py" | head -300
app/pipeline/recovery.py:55:                    dino_started_at = NULL,
app/pipeline/recovery.py:59:                    AND dino_started_at < %s
app/pipeline/recovery.py:71:                    qwen_started_at = NULL,
app/pipeline/recovery.py:75:                    AND qwen_started_at < %s
app/workers/qwen_worker.py:745:        print("QWEN WORKER STOPPED")
app/workers/dino_worker.py:428:        print("DINO WORKER STOPPED")
app/web/components/technical_modules/photo_processing.py:153:            process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:158:                stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/photo_processing.py:159:                stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/qwen.py:295:    qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:297:    async def stop_qwen():
app/web/components/technical_modules/qwen.py:299:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:304:        qwen_stop_requested = True
app/web/components/technical_modules/qwen.py:307:            f"[QWEN MANUAL] STOP REQUESTED PID={qwen_process.pid}",
app/web/components/technical_modules/qwen.py:317:                f"[QWEN MANUAL] STOP FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:324:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:326:        print("[QWEN MANUAL] START", flush=True)
app/web/components/technical_modules/qwen.py:328:        qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:440:            process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/qwen.py:453:                stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/qwen.py:454:                stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/qwen.py:617:                if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:632:            if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:690:            qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:773:    stop_button.on_click(stop_qwen)
app/web/system/monitor.py:3:import subprocess
app/web/system/monitor.py:27:        result = subprocess.run(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:10:03

Отлично. Теперь картина ясная.

**Qwen уже имеет управление в `app/web/components/technical_modules/qwen.py`** — там есть `start` и `stop`. А DINO, судя по результату, пока управляется через worker, но отдельного UI-controller в найденных местах нет.

Поэтому сейчас **не надо писать новый механизм запуска**. Сначала посмотрим существующий Qwen-компонент и DINO worker, чтобы не дублировать логику.

Дай сразу два файла:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '250,360p' app/web/components/technical_modules/qwen.py && \
echo "================ DINO WORKER ================" && \
sed -n '1,240p' app/workers/dino_worker.py
```

После этого я дам **готовую замену `photo_processing.py`**, которая будет использовать существующую архитектуру и только добавит нужный UI + статистику.

---

### 👤 **User** — 2026-08-19 01:10:25

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '250,360p' app/web/components/technical_modules/qwen.py && \
echo "================ DINO WORKER ================" && \
sed -n '1,240p' app/workers/dino_worker.py
            ui.label("Ошибок")
            errors_label = ui.label("0")

            ui.label("Адресов")
            addresses_label = ui.label("0")

            ui.label("Среднее время")
            avg_time_label = ui.label("0.00 сек")

            ui.label("Средняя уверенность")
            avg_confidence_label = ui.label("0.0%")

        ui.separator().classes("my-2")

        with ui.row().classes(
            "gap-2"
        ):

            run_button = ui.button(
                "▶ Запустить Qwen",
            ).props(
                "unelevated"
            )

            stop_button = ui.button(
                "■ Остановить Qwen",
            ).props(
                "unelevated color=negative"
            )

            stop_button.disable()

            refresh_button = ui.button(
                "↻ Обновить",
            ).props(
                "flat"
            )

        source_label = ui.label(
            "Источник: —"
        ).classes(
            "text-xs text-grey-6"
        )

    qwen_process = None
    qwen_stop_requested = False

    async def stop_qwen():
        nonlocal qwen_process
        nonlocal qwen_stop_requested

        if qwen_process is None:
            return

        qwen_stop_requested = True

        print(
            f"[QWEN MANUAL] STOP REQUESTED PID={qwen_process.pid}",
            flush=True,
        )

        try:
            qwen_process.terminate()
        except ProcessLookupError:
            pass
        except Exception as exc:
            print(
                f"[QWEN MANUAL] STOP FAILED: {exc!r}",
                flush=True,
            )

    async def run_qwen():

        nonlocal qwen_process
        nonlocal qwen_stop_requested

        print("[QWEN MANUAL] START", flush=True)

        qwen_stop_requested = False

        run_button.disable()
        stop_button.enable()

        try:

            if not QWEN_SCRIPT.exists():

                print(
                    f"[QWEN MANUAL] SCRIPT NOT FOUND: {QWEN_SCRIPT}",
                    flush=True,
                )

                ui.notify(
                    f"Не найден Qwen script: {QWEN_SCRIPT}",
                    type="negative",
                    timeout=8000,
                )

                return

            result_dir = _find_latest_hybrid()

            if result_dir is None:

                print(
                    "[QWEN MANUAL] HYBRID RUN NOT FOUND",
                    flush=True,
                )

                ui.notify(
                    "Не найден ни один запуск Hybrid.",
================ DINO WORKER ================
from __future__ import annotations

import os
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def reset_processing(conn):
    """
    Возвращает зависшие DINO-задачи обратно в очередь.

    Это позволяет продолжить работу после:
        - остановки процесса
        - перезагрузки
        - падения Python
        - аварии машины
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'pending',
                updated_at = CURRENT_TIMESTAMP
            WHERE dino_status = 'processing'
            """
        )

        count = cur.rowcount

    conn.commit()

    if count:
        print(
            f"[DINO] Reset stale processing jobs: {count}"
        )

def claim_photo(conn):
    """
    Забирает следующую фотографию из DINO-очереди.

    ВАЖНО:

    Qwen здесь вообще не учитывается.

    DINO получает фотографию только потому,
    что у неё уже существует photo_id и
    dino_status = pending.
    """

    with conn.cursor(
        cursor_factory=RealDictCursor
    ) as cur:

        cur.execute(
            """
            SELECT
                id,
                photo_id,
                initial_id,
                source_path,
                filename
            FROM photos
            WHERE
                dino_status = 'pending'
                AND source_path IS NOT NULL
                AND source_path <> ''
            ORDER BY id
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )

        row = cur.fetchone()

        if row is None:
            conn.commit()
            return None

        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE
                id = %s
                AND dino_status = 'pending'
            """,
            (row["id"],),
        )

        conn.commit()

        return row

# ============================================================
# RESULT
# ============================================================

def mark_done(
    conn,
    db_id,
    result,
    elapsed,
):
    """
    Сохраняет результат DINO.

    Главный результат нового слоя:

        address_id = адрес, определённый DINO.

    photo_id остаётся независимым идентификатором фотографии.
    """

    address_id = result.get("best_id")

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'done',

                address_id = %s,

                dino_fingerprint = %s,
                dino_score = %s,
                dino_second_score = %s,
                dino_margin = %s,
                dino_time_sec = %s,

                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = %s
            """,
            (
                address_id,

                # Старое поле оставляем для совместимости
                # со старым кодом и статистикой.
                address_id,

                result.get("score"),
                result.get("second_score"),
                result.get("margin"),

                elapsed,

                db_id,
            ),
        )

    conn.commit()

def mark_error(
    conn,
    db_id,
    error,
):
    """
    Фиксирует ошибку конкретной фотографии.

    Qwen-status при этом НЕ меняется.
    """

    message = str(error)

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'error',
                error_message = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                message[:4000],
                db_id,
            ),
        )

    conn.commit()

# ============================================================
# WORKER
# ============================================================

def main():

    settings = Settings()

    print("=" * 70)
    print("DINO WORKER")
    print("=" * 70)
    print("device  :", settings.device)
    print("database:", DB_CONFIG["dbname"])
    print("=" * 70)

    # --------------------------------------------------------
    # MODEL
    # --------------------------------------------------------

    print("[DINO] Loading SceneEmbedder...")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:10:43

Да. Теперь видно главное: **Qwen уже имеет UI-управление**, а DINO — самостоятельный worker. Поэтому `photo_processing.py` не должен запускать старый `run_daily_hybrid_v12.sh` напрямую, иначе мы получаем вторую параллельную систему управления.

Сейчас предлагаю сделать **только UI-слой** поверх существующей БД и процессов.

Но для DINO нужно ещё найти, **как именно он сейчас запускается** — worker сам по себе не содержит функции `start/stop`.

Выполни:

```bash id="c5d1y2"
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'dino_worker|qwen_worker|run_daily_hybrid_v12|workers\.dino|workers\.qwen' \
. \
--exclude-dir=.venv \
--exclude-dir=.git \
--exclude='*.json' \
--exclude='*.log' | head -250
```

Это последний поиск, который нужен перед переписыванием `photo_processing.py`.

После него я дам **одну команду через `cat > app/web/components/technical_modules/photo_processing.py <<'PY'`**, чтобы целиком заменить компонент.

В нём сделаем:

- источник + `[Выбрать]` **в одну строку**;
- результат **readonly**, без выбора;
- общую кнопку запуска;
- общую кнопку остановки;
- DINO-панель;
- Qwen-панель;
- независимые progress bar;
- `готово / работа / очередь / ошибки`;
- общий цвет состояния;
- автообновление статистики из PostgreSQL;
- без изменения DINO/Qwen backend.

---

### 👤 **User** — 2026-08-19 01:11:21

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'dino_worker|qwen_worker|run_daily_hybrid_v12|workers\.dino|workers\.qwen' \
. \
--exclude-dir=.venv \
--exclude-dir=.git \
--exclude='*.json' \
--exclude='*.log' | head -250
grep: ./app/web/components/technical_modules/__pycache__/photo_processing.cpython-312.pyc: binary file matches
./app/web/components/technical_modules/photo_processing.py.broken_backup:9:DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
./app/web/components/technical_modules/photo_processing.py:13:    / "run_daily_hybrid_v12.sh"
./app/web/components/technical_modules/photo_processing.py.bak:9:DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
./app/web/components/technical_modules/photo_processing.py.bak_before_qwen_integration:9:DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
./app/web/components/technical_modules/photo_processing.py.bak_button_error_debug:9:DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
grep: ./app/workers/__pycache__/dino_worker.cpython-312.pyc: binary file matches
./app/web/components/technical_modules/photo_processing.py.bak_before_path_fix:9:DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
./app/pipeline/worker.py::22:DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
./app/pipeline/worker.py::23:QWEN_WORKER = PROJECT / "app" / "workers" / "qwen_worker.py"
./app/pipeline/worker.py::187:            DINO_WORKER,
./app/pipeline/worker.py::223:            QWEN_WORKER,
grep: ./app/workers/__pycache__/qwen_worker.cpython-312.pyc: binary file matche

---

### 🤖 **Assistant** — 2026-08-19 01:11:22

Отлично. Вот оно — **существующий `app/pipeline/worker.py` уже является диспетчером двух независимых workers**:

- `dino_worker.py`
- `qwen_worker.py`

Значит, `photo_processing.py` действительно нужно **отвязать от `run_daily_hybrid_v12.sh`**. Старый компонент сейчас запускает монолитный daily-script, а это не соответствует нашей новой архитектуре.

Нам осталось посмотреть API самого `worker.py`, особенно его start/stop/state. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,280p' app/pipeline/worker.py
```

После этого уже можно без гадания написать новый `photo_processing.py`: **только веб-интерфейс + статистика + прогресс + управление существующим pipeline worker**, без изменения самого backend.

---

### 👤 **User** — 2026-08-19 01:11:39

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,280p' app/pipeline/worker.py
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.pipeline.queue import JobQueue

class FingerprintWorker:

    def __init__(self):
        self.queue = JobQueue(
            settings.data_dir / "jobs.db"
        )

        print("[Worker] Loading SceneEmbedder...")

        self.embedder = SceneEmbedder(
            settings
        )

        self.manager = FingerprintManager(
            settings,
            self.embedder,
        )

    def run_once(self):
        job = self.queue.claim()

        if job is None:
            return False

        job_id = job["id"]
        fingerprint_id = job["fingerprint_id"]
        source_folder = Path(
            job["source_folder"]
        )

        print()
        print("=" * 60)
        print(f"[Worker] Job {job_id}")
        print(f"[Worker] Fingerprint: {fingerprint_id}")
        print(f"[Worker] Folder: {source_folder}")
        print("=" * 60)

        try:
            self.manager.create(
                fingerprint_id,
                source_folder,
                self.embedder,
            )

            self.queue.complete(
                job_id
            )

            print(
                f"[Worker] DONE: {fingerprint_id}"
            )

            return True

        except Exception as exc:
            self.queue.fail(
                job_id,
                repr(exc),
            )

            print(
                f"[Worker] FAILED: "
                f"{fingerprint_id}: {exc}"
            )

            return True

    def run(self):
        print("[Worker] Starting batch processing")

        processed = 0

        while True:
            result = self.run_once()

            if not result:
                break

            processed += 1

        print()
        print("=" * 60)
        print(
            f"[Worker] Batch complete. "
            f"Processed: {processed}"
        )
        print("=" * 60)

def main():
    worker = FingerprintWorker()
    worker.run()

if __name__ == "__main__":
    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:11:41

Вот теперь важный момент: **этот `app/pipeline/worker.py` — не тот worker**, который нам нужен для управления DINO/Qwen.

Он работает со старой очередью:

```text
JobQueue → FingerprintManager → создание fingerprint
```

А наша текущая параллельная обработка фотографий устроена иначе:

```text
photos
  │
  ├── dino_status → app/workers/dino_worker.py
  │
  └── qwen_status → app/workers/qwen_worker.py
```

И статистика уже подтверждает, что именно эта схема сейчас работает:

```text
526 фото

DINO:
  done       526
  processing   0
  pending      0
  error        0

Qwen:
  done         1
  processing   0
  pending    525
  error        0
```

Поэтому **`app/pipeline/worker.py` вообще не трогаем**.

Нам нужно найти, каким способом сейчас запускаются именно:

```text
app/workers/dino_worker.py
app/workers/qwen_worker.py
```

И уже этот существующий механизм подключить к веб-интерфейсу.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'uv run.*dino_worker|uv run.*qwen_worker|python.*dino_worker|python.*qwen_worker|dino_worker.py|qwen_worker.py' \
scripts app \
--exclude-dir=__pycache__ \
--include="*.sh" \
--include="*.py" | head -200
```

**После этого уже не будем дальше искать архитектуру.** По найденному запуску я дам готовую замену `photo_processing.py`, которая будет:

- не запускать старый `run_daily_hybrid_v12.sh`;
- не вмешиваться в backend;
- запускать/останавливать **реальные DINO и Qwen workers**;
- показывать прогресс непосредственно из `photos`;
- показывать `готово / в работе / очередь / ошибки`;
- иметь общую кнопку **«ЗАПУСТИТЬ»**;
- иметь отдельные **DINO / Qwen Запустить / Остановить**;
- источник — выбираемый;
- результат — readonly;
- источник и результат — **в одной строке**, как ты задал.

---

### 👤 **User** — 2026-08-19 01:11:56

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'uv run.*dino_worker|uv run.*qwen_worker|python.*dino_worker|python.*qwen_worker|dino_worker.py|qwen_worker.py' \
scripts app \
--exclude-dir=__pycache__ \
--include="*.sh" \
--include="*.py" | head -200
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:11:58

Да. Это означает, что **DINO/Qwen workers сейчас не запускаются из `scripts/` или `app/` найденным прямым вызовом**. Поэтому не будем придумывать новый механизм запуска.

У нас уже есть рабочий ручной запуск Qwen внутри `qwen.py`, а для DINO нужно посмотреть конец самого worker — там обычно находится `main()` и бесконечный цикл.

Сейчас нужны **только два небольших фрагмента**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DINO ================" && \
sed -n '200,460p' app/workers/dino_worker.py && \
echo "================ QWEN ================" && \
sed -n '520,780p' app/workers/qwen_worker.py
```

После этого я смогу сделать `photo_processing.py` именно как **панель управления существующей параллельной системой**, а не создавать третью систему обработки.

---

### 👤 **User** — 2026-08-19 01:12:28

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DINO ================" && \
sed -n '200,460p' app/workers/dino_worker.py && \
echo "================ QWEN ================" && \
sed -n '520,780p' app/workers/qwen_worker.py
================ DINO ================

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'error',
                error_message = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                message[:4000],
                db_id,
            ),
        )

    conn.commit()

# ============================================================
# WORKER
# ============================================================

def main():

    settings = Settings()

    print("=" * 70)
    print("DINO WORKER")
    print("=" * 70)
    print("device  :", settings.device)
    print("database:", DB_CONFIG["dbname"])
    print("=" * 70)

    # --------------------------------------------------------
    # MODEL
    # --------------------------------------------------------

    print("[DINO] Loading SceneEmbedder...")

    embedder = SceneEmbedder(settings)

    manager = FingerprintManager(
        settings,
        embedder,
    )

    recognizer = SceneRecognizer(
        settings,
        embedder,
        manager,
    )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    conn = get_connection()

    print("[DINO] Database connected.")

    # --------------------------------------------------------
    # RECOVERY
    # --------------------------------------------------------

    reset_processing(conn)

    print("[DINO] Worker ready.")

    max_items = int(
        os.getenv(
            "DINO_MAX_ITEMS",
            "0",
        )
    )

    processed = 0
    errors = 0

    try:

        while True:

            # ------------------------------------------------
            # LIMIT
            # ------------------------------------------------

            if (
                max_items > 0
                and processed >= max_items
            ):
                print(
                    f"[DINO] "
                    f"Reached max_items={max_items}."
                )
                break

            # ------------------------------------------------
            # CLAIM
            # ------------------------------------------------

            row = claim_photo(conn)

            if row is None:

                print(
                    "[DINO] Queue empty."
                )

                break

            db_id = row["id"]
            photo_id = row["photo_id"]
            initial_id = row["initial_id"]
            source_path = Path(
                row["source_path"]
            )

            print()
            print("-" * 70)

            print(
                "[DINO]",
                photo_id,
                "| initial_id:",
                initial_id,
                "| file:",
                source_path.name,
            )

            started = time.perf_counter()

            # ------------------------------------------------
            # PROCESS
            # ------------------------------------------------

            try:

                if not source_path.exists():
                    raise FileNotFoundError(
                        f"Photo not found: {source_path}"
                    )

                if not source_path.is_file():
                    raise FileNotFoundError(
                        f"Not a file: {source_path}"
                    )

                result = recognizer.recognize_one(
                    source_path,
                    top_k=5,
                    threshold=0.65,
                )

                elapsed = (
                    time.perf_counter()
                    - started
                )

                # ------------------------------------------------
                # SAVE
                # ------------------------------------------------

                mark_done(
                    conn,
                    db_id,
                    result,
                    elapsed,
                )

                address_id = result.get(
                    "best_id"
                )

                print(
                    f"[DINO] DONE "
                    f"{photo_id}"
                    f" -> address_id={address_id}"
                    f" score={result.get('score', 0):.6f}"
                    f" margin={result.get('margin', 0):.6f}"
                    f" time={elapsed:.2f}s"
                )

                processed += 1

            # ------------------------------------------------
            # ERROR
            # ------------------------------------------------

            except Exception as exc:

                errors += 1

                elapsed = (
                    time.perf_counter()
                    - started
                )

                print(
                    f"[DINO] ERROR "
                    f"{photo_id}: {exc}"
                    f" time={elapsed:.2f}s"
                )

                try:

                    mark_error(
                        conn,
                        db_id,
                        exc,
                    )

                except Exception as db_error:

                    print(
                        "[DINO] "
                        "DB ERROR while marking error:",
                        db_error,
                    )

    finally:

        conn.close()

        print()
        print("=" * 70)
        print("DINO WORKER STOPPED")
        print("=" * 70)

        print(
            "PROCESSED:",
            processed,
        )

        print(
            "ERRORS:",
            errors,
        )

if __name__ == "__main__":
    main()
================ QWEN ================
                attempt,
                flush=True,
            )

            if attempt < max_attempts:
                continue

            result = {
                "raw_answer": answer,
            }

            result["_time_sec"] = round(
                elapsed,
                2,
            )

            return result

# ============================================================
# WORKER
# ============================================================

def main():

    print("=" * 80)
    print("QWEN3-VL 4B — DATABASE WORKER")
    print("=" * 80)
    print("MODEL   :", MODEL)
    print("DATABASE:", DB_CONFIG["dbname"])
    print()
    print(
        "[QWEN] Works independently from DINO."
    )
    print(
        "[QWEN] Source: photos.source_path"
    )
    print(
        "[QWEN] Identity: photos.photo_id"
    )
    print()

    conn = get_connection()

    processed = 0
    errors = 0

    max_items = int(
        os.getenv(
            "QWEN_MAX_ITEMS",
            "0",
        )
    )

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT COUNT(*)
                FROM photos
                WHERE qwen_status = 'pending'
                """
            )

            pending = cur.fetchone()[0]

        print(
            "PENDING:",
            pending,
        )
        print()

        while True:

            if (
                max_items > 0
                and processed >= max_items
            ):

                print(
                    "[QWEN] Reached "
                    f"max_items={max_items}."
                )

                break

            row = claim_photo(
                conn
            )

            if row is None:

                print(
                    "[QWEN] Queue empty."
                )

                break

            db_id = row["id"]
            photo_id = row["photo_id"]
            source_path = Path(
                row["source_path"]
            )

            print("=" * 80)
            print(
                f"[QWEN] {photo_id}"
            )
            print(
                "SOURCE:",
                source_path,
            )

            started = time.time()

            try:

                if not source_path.exists():
                    raise FileNotFoundError(
                        f"Photo not found: "
                        f"{source_path}"
                    )

                if not source_path.is_file():
                    raise FileNotFoundError(
                        f"Not a file: "
                        f"{source_path}"
                    )

                result = ask(
                    source_path
                )

                elapsed = (
                    time.time()
                    - started
                )

                mark_done(
                    conn,
                    db_id,
                    result,
                    elapsed,
                )

                print(
                    "[QWEN] DONE",
                    photo_id,
                    "| time:",
                    round(
                        elapsed,
                        2,
                    ),
                    "sec",
                    "| client:",
                    result.get(
                        "client",
                        "",
                    ),
                    "| brand:",
                    result.get(
                        "brand",
                        "",
                    ),
                    "| confidence:",
                    result.get(
                        "confidence",
                        "",
                    ),
                )

                print(
                    "DESCRIPTION:",
                    result.get(
                        "description",
                        "",
                    ),
                )

                processed += 1

            except Exception as exc:

                errors += 1

                elapsed = (
                    time.time()
                    - started
                )

                print(
                    "[QWEN] ERROR",
                    photo_id,
                    ":",
                    exc,
                    "| time:",
                    round(
                        elapsed,
                        2,
                    ),
                )

                try:

                    mark_error(
                        conn,
                        db_id,
                        exc,
                    )

                except Exception as db_error:

                    print(
                        "[QWEN] DB ERROR:",
                        db_error,
                    )

    finally:

        conn.close()

        print()
        print("=" * 80)
        print("QWEN WORKER STOPPED")
        print("=" * 80)
        print(
            "PROCESSED:",
            processed,
        )
        print(
            "ERRORS:",
            errors,
        )

if __name__ == "__main__":
    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:12:31

Да. Теперь картина полная.

**Сам backend менять не нужно.**  
`photos` уже является общей очередью, и статистика у нас получается напрямую:

- всего: `526`
- DINO: `526 done`
- Qwen: `1 done / 525 pending`
- обе ветки независимы;
- `photo_id` общий;
- `source_path` общий;
- `dino_status` и `qwen_status` независимы.

Поэтому `photo_processing.py` должен быть **только UI-контроллером и монитором**.

И я бы сейчас убрал из него запуск `run_daily_hybrid_v12.sh`: это как раз старая логика, которая противоречит новой архитектуре.

Сделаем:

```text
ФОТООБРАБОТКА

Источник [/data/input/daily................] [Выбрать]
Результат [/data/output/daily..............]   ← readonly

[ ▶ ЗАПУСТИТЬ ] [ ■ ОСТАНОВИТЬ ]

🟠 ИДЁТ ОБРАБОТКА

────────────────────────────────────────────

DINO v33 / Hybrid v12

[ ▶ Запустить ] [ ■ Остановить ]

████████████████░░░░  526 / 526

Готово: 526   В работе: 0   В очереди: 0   Ошибки: 0

Qwen3-VL 4B

[ ▶ Запустить ] [ ■ Остановить ]

██░░░░░░░░░░░░░░░░░░  1 / 526

Готово: 1   В работе: 0   В очереди: 525   Ошибки: 0
```

Главная кнопка запускает **обе ветки**, индивидуальные — только свою.

### Сначала проверим одну вещь

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python app/workers/dino_worker.py
```

Если DINO действительно запускается и начинает обрабатывать/видит `Queue empty`, **сразу останови `Ctrl+C`**.

После этого я дам тебе **одну команду `cat > app/web/components/technical_modules/photo_processing.py <<'PY'`**, которая полностью заменит текущий файл на нормальный интерфейс со статистикой, прогресс-барами, цветными состояниями и управлением обеими существующими workers.

---

### 👤 **User** — 2026-08-19 01:13:01

database: photobase
======================================================================
[DINO] Loading SceneEmbedder...
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8830.28it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[DINO] Database connected.
[DINO] Worker ready.
[DINO] Queue empty.

======================================================================
DINO WORKER STOPPED
======================================================================
PROCESSED: 0
ERRORS: 0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

