## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 👤 **User** — 2026-08-19 01:36:33

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '280,530p' app/web/components/technical_modules/automation.py
                    status_label.text = (
                        "● Режим: автоматический"
                        " — запуск в "
                        f"{current.auto_time.strftime('%H:%M')}"
                    )
                else:
                    status_label.text = (
                        "● Режим: автоматический"
                    )

            # -----------------------------------------------
            # CONTROLS
            # -----------------------------------------------

            watcher_enabled = (
                current.mode == MODE_WATCHER
            )

            automatic_enabled = (
                current.mode == MODE_AUTOMATIC
            )

            watcher_path_input.enabled = (
                watcher_enabled
            )

            time_select.enabled = (
                automatic_enabled
            )

            # -----------------------------------------------
            # RADIO STATE
            # -----------------------------------------------

            manual_radio.value = (
                MODE_MANUAL
                if current.mode == MODE_MANUAL
                else None
            )

            watcher_radio.value = (
                MODE_WATCHER
                if current.mode == MODE_WATCHER
                else None
            )

            automatic_radio.value = (
                MODE_AUTOMATIC
                if current.mode == MODE_AUTOMATIC
                else None
            )

        # ====================================================
        # MODE CHANGE
        # ====================================================

        def select_mode(mode: str):

            try:

                if mode == MODE_MANUAL:

                    set_manual()

                elif mode == MODE_WATCHER:

                    watcher_path = (
                        watcher_path_input.value or ""
                    ).strip()

                    if not watcher_path:
                        ui.notify(
                            "Укажите папку для Watcher",
                            type="warning",
                        )
                        refresh_ui()
                        return

                    set_watcher(
                        watcher_path
                    )

                elif mode == MODE_AUTOMATIC:

                    selected_time = _parse_time(
                        time_select.value
                    )

                    set_automatic(
                        selected_time
                    )

                refresh_ui()

            except Exception as exc:

                print(
                    "[AUTOMATION] MODE ERROR:",
                    repr(exc),
                    flush=True,
                )

                ui.notify(
                    f"Ошибка режима: {exc}",
                    type="negative",
                )

                refresh_ui()

        # ====================================================
        # EVENTS
        # ====================================================

        manual_radio.on(
            "update:model-value",
            lambda event: (
                select_mode(MODE_MANUAL)
                if event.value == MODE_MANUAL
                else None
            ),
        )

        watcher_radio.on(
            "update:model-value",
            lambda event: (
                select_mode(MODE_WATCHER)
                if event.value == MODE_WATCHER
                else None
            ),
        )

        automatic_radio.on(
            "update:model-value",
            lambda event: (
                select_mode(MODE_AUTOMATIC)
                if event.value == MODE_AUTOMATIC
                else None
            ),
        )

        # ====================================================
        # WATCHER PATH CHANGE
        # ====================================================

        def watcher_path_changed(event):

            current = get_state()

            if current.mode != MODE_WATCHER:
                return

            path = (
                event.value or ""
            ).strip()

            if not path:

                ui.notify(
                    "Путь Watcher не может быть пустым",
                    type="warning",
                )

                refresh_ui()
                return

            try:

                set_watcher(path)

                refresh_ui()

            except Exception as exc:

                print(
                    "[AUTOMATION] WATCHER PATH ERROR:",
                    repr(exc),
                    flush=True,
                )

                ui.notify(
                    f"Ошибка пути Watcher: {exc}",
                    type="negative",
                )

                refresh_ui()

        watcher_path_input.on(
            "update:model-value",
            watcher_path_changed,
        )

        # ====================================================
        # AUTOMATIC TIME CHANGE
        # ====================================================

        def time_changed(event):

            current = get_state()

            if current.mode != MODE_AUTOMATIC:
                return

            try:

                selected_time = _parse_time(
                    event.value
                )

                set_automatic(
                    selected_time
                )

                refresh_ui()

            except Exception as exc:

                print(
                    "[AUTOMATION] TIME ERROR:",
                    repr(exc),
                    flush=True,
                )

                ui.notify(
                    f"Ошибка времени: {exc}",
                    type="negative",
                )

                refresh_ui()

        time_select.on(
            "update:model-value",
            time_changed,
        )

        # ====================================================
        # INITIAL STATE
        # ====================================================

        refresh_ui()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'watchdog|Observer|FileSystemEvent|schedule|scheduler|auto_time|watcher_path|watcher_enabled|start_automatic|start_watcher' \
app \
--include="*.py" | grep -v '__pycache__'
app/web/components/technical_modules/automation.py:130:            watcher_path_input = ui.input(
app/web/components/technical_modules/automation.py:132:                value=state.watcher_path or "",
app/web/components/technical_modules/automation.py:139:            watcher_path_input.tooltip(
app/web/components/technical_modules/automation.py:164:                    state.auto_time.strftime("%H:%M")
app/web/components/technical_modules/automation.py:165:                    if state.auto_time
app/web/components/technical_modules/automation.py:270:                path = current.watcher_path or "—"
app/web/components/technical_modules/automation.py:279:                if current.auto_time:
app/web/components/technical_modules/automation.py:283:                        f"{current.auto_time.strftime('%H:%M')}"
app/web/components/technical_modules/automation.py:294:            watcher_enabled = (
app/web/components/technical_modules/automation.py:302:            watcher_path_input.enabled = (
app/web/components/technical_modules/automation.py:303:                watcher_enabled
app/web/components/technical_modules/automation.py:346:                    watcher_path = (
app/web/components/technical_modules/automation.py:347:                        watcher_path_input.value or ""
app/web/components/technical_modules/automation.py:350:                    if not watcher_path:
app/web/components/technical_modules/automation.py:359:                        watcher_path
app/web/components/technical_modules/automation.py:424:        def watcher_path_changed(event):
app/web/components/technical_modules/automation.py:466:        watcher_path_input.on(
app/web/components/technical_modules/automation.py:468:            watcher_path_changed,
app/web/components/technical.py:73:            if (card.__albionResizeObserver) {{
app/web/components/technical.py:74:                card.__albionResizeObserver.disconnect();
app/web/components/technical.py:77:            card.__albionResizeObserver = new ResizeObserver(() => {{
app/web/components/technical.py:94:            card.__albionResizeObserver.observe(card);
app/pipeline/modes.py:25:    auto_time: Optional[time] = None
app/pipeline/modes.py:27:    watcher_enabled: bool = False
app/pipeline/modes.py:28:    watcher_path: Optional[str] = None
app/pipeline/modes.py:47:        auto_time=None,
app/pipeline/modes.py:48:        watcher_enabled=False,
app/pipeline/modes.py:49:        watcher_path=None,
app/pipeline/modes.py:56:    auto_time: time,
app/pipeline/modes.py:62:        auto_time=auto_time,
app/pipeline/modes.py:63:        watcher_enabled=False,
app/pipeline/modes.py:64:        watcher_path=None,
app/pipeline/modes.py:71:    watcher_path: str,
app/pipeline/modes.py:74:    if not watcher_path:
app/pipeline/modes.py:82:        auto_time=None,
app/pipeline/modes.py:83:        watcher_enabled=True,
app/pipeline/modes.py:84:        watcher_path=watcher_path,
app/pipeline/controller.py:59:                    auto_time,
app/pipeline/controller.py:60:                    watcher_enabled,
app/pipeline/controller.py:61:                    watcher_path,
app/pipeline/controller.py:79:        auto_time=row["auto_time"],
app/pipeline/controller.py:80:        watcher_enabled=bool(row["watcher_enabled"]),
app/pipeline/controller.py:81:        watcher_path=row["watcher_path"],
app/pipeline/controller.py:98:                    auto_time = %s,
app/pipeline/controller.py:99:                    watcher_enabled = %s,
app/pipeline/controller.py:100:                    watcher_path = %s,
app/pipeline/controller.py:109:                    state.auto_time,
app/pipeline/controller.py:110:                    state.watcher_enabled,
app/pipeline/controller.py:111:                    state.watcher_path,
app/pipeline/controller.py:126:def set_automatic(auto_time: time):
app/pipeline/controller.py:127:    state = build_automatic_mode(auto_time)
app/pipeline/controller.py:132:def set_watcher(watcher_path: str):
app/pipeline/controller.py:133:    state = build_watcher_mode(watcher_path)
app/pipeline/controller.py:174:def start_automatic():
app/pipeline/controller.py:208:def start_watcher():
app/pipeline/controller.py:269:                    auto_time = NULL,
app/pipeline/controller.py:270:                    watcher_enabled = FALSE,
app/pipeline/controller.py:271:                    watcher_path = NULL,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:36:34

Да. Теперь картина полная.

**Сейчас у нас есть важный разрыв:** UI уже умеет выбрать `manual / automatic / watcher` и сохраняет это в PostgreSQL, но **самого механизма, который реально запускает pipeline по времени или следит за папкой, в проекте нет**.

То есть:

- `set_automatic()` — только записывает режим и время.
- `set_watcher()` — только записывает путь.
- `start_automatic()` существует, но **никто его не вызывает**.
- `start_watcher()` существует, но **никто его не вызывает**.
- `watcher_enabled` нигде реально не используется для наблюдения.
- `auto_time` нигде не проверяется планировщиком.
- `recovery.py` умеет только вернуть зависшие jobs `processing → pending`.
- `photo_processing.py` сейчас запускает workers напрямую из UI.
- При этом мы уже запретили ручной запуск DINO/Qwen, если режим не `manual`.

### Поэтому следующий патч я бы делал не в UI

Нужен отдельный **pipeline supervisor**, который работает независимо от открытого технического окна:

```text
PostgreSQL pipeline_control
          │
          ▼
   Pipeline Supervisor
          │
     ┌────┴────┐
     │         │
 automatic   watcher
     │         │
  время       новые
     │         │
     └────┬────┘
          ▼
     запуск pipeline
          │
     ┌────┴────┐
     ▼         ▼
   DINO      Qwen
```

И главное — **UI перестаёт быть владельцем процесса**.

Сейчас `photo_processing.py` фактически является владельцем `asyncio.create_subprocess_exec()`. Это нормально для временного ручного MVP, но для автоматизации плохо: закрыл браузер/перезапустил NiceGUI — состояние процессов теряется.

### Я предлагаю следующий шаг

Сделать:

```text
app/pipeline/supervisor.py
```

Он будет:

1. читать `pipeline_control`;
2. если `manual` — ничего автоматически не запускать;
3. если `automatic`:
   - проверять текущее время;
   - запускать обработку один раз в заданное время;
4. если `watcher`:
   - проверять появление новых файлов;
   - запускать обработку;
5. перед запуском вызывать `recover_stale_jobs()`;
6. не запускать второй экземпляр, если `running = TRUE`;
7. корректно выставлять `running`;
8. после завершения возвращать состояние;
9. учитывать `stop_requested`;
10. работать независимо от вкладки «Технический раздел».

Но есть **один архитектурный момент**, который надо решить до патча:

Сейчас DINO/Qwen запускаются так:

```python
uv run python app/workers/dino_worker.py
uv run python app/workers/qwen_worker.py
```

а `photo_processing.py` запускает их **параллельно**.

Поэтому supervisor лучше не дублировать эту логику, а вынести общий запуск в отдельный модуль, например:

```text
app/pipeline/runner.py
```

Тогда получится:

```text
                 runner.py
                /        \
               /          \
        manual UI       supervisor
           │                │
           └──────┬─────────┘
                  ▼
             DINO + Qwen
```

И UI будет только командовать контроллером, а supervisor — выполнять автоматические команды.

**Я бы сейчас именно так и продолжил: сначала `runner.py + supervisor.py`, а `photo_processing.py` потом перевести на этот же runner.** Это уберёт дублирование и не сломает уже работающий ручной режим.

---

### 👤 **User** — 2026-08-19 01:36:56

продолжаем

---

### 🤖 **Assistant** — 2026-08-19 01:36:57

Да. Мы дошли до важного места: **режимы в БД и UI уже есть, но реального механизма автоматического запуска и Watcher пока нет**.

Сейчас картина такая:

- `manual / automatic / watcher` — реализованы в `modes.py`;
- переключение режимов — реализовано в `automation.py`;
- состояние сохраняется в PostgreSQL — реализовано в `controller.py`;
- `start_automatic()` и `start_watcher()` существуют, **но нигде не вызываются**;
- `watchdog`, scheduler и вообще отдельный процесс/цикл автоматизации в проекте не обнаружены;
- DINO/Qwen сейчас запускаются непосредственно из UI через `asyncio.create_subprocess_exec`;
- ручной запуск уже правильно ограничен `state.mode == "manual"`;
- остановка уже связана с `request_stop()` → ожидание завершения процессов → `finish_stop()`.

### Что я предлагаю сделать сейчас

Не ломать существующую обработку фото, а добавить отдельный **Pipeline Supervisor**:

```text
                    PostgreSQL
                        │
                        ▼
               pipeline_control
                        │
              ┌─────────┴─────────┐
              │ Pipeline Supervisor│
              └─────────┬─────────┘
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       manual       automatic       watcher
          │             │             │
          │          время          папка
          │             │             │
          └─────────────┴─────────────┘
                        │
                        ▼
                  DINO worker
                        │
                        ▼
                  Qwen worker
```

При этом **UI не должен быть самим планировщиком**. Это важно: если браузер закрылся, NiceGUI перезапустился или пользователь ушёл со страницы — автоматизация всё равно должна продолжать работать.

И ещё один момент: `start_automatic()` и `start_watcher()` сейчас только меняют `running=True`. Они **не запускают worker сами**. Значит, Supervisor должен быть владельцем реального запуска процессов.

### Следующий шаг

Давай сначала посмотрим существующий `app/pipeline/worker.py` и `app/pipeline/queue.py`, чтобы не создавать второй механизм очереди поверх уже имеющегося.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PIPELINE WORKER ================" && \
cat app/pipeline/worker.py && \
echo "================ PIPELINE QUEUE ================" && \
cat app/pipeline/queue.py && \
echo "================ DINO WORKER ================" && \
sed -n '1,260p' app/workers/dino_worker.py && \
echo "================ QWEN WORKER ================" && \
sed -n '1,260p' app/workers/qwen_worker.py
```

**После этого уже сделаем конкретный патч**, а не будем добавлять абстрактный scheduler.

---

### 👤 **User** — 2026-08-19 01:37:21

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PIPELINE WORKER ================" && \
cat app/pipeline/worker.py && \
echo "================ PIPELINE QUEUE ================" && \
cat app/pipeline/queue.py && \
echo "================ DINO WORKER ================" && \
sed -n '1,260p' app/workers/dino_worker.py && \
echo "================ QWEN WORKER ================" && \
sed -n '1,260p' app/workers/qwen_worker.py
================ PIPELINE WORKER ================
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
================ PIPELINE QUEUE ================
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class JobQueue:
    """
    Persistent SQLite job queue.

    States:
        PENDING
        PROCESSING
        DONE
        FAILED
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
        )

        connection.row_factory = sqlite3.Row

        return connection

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).isoformat()

    def _init_db(self):
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    source_folder TEXT NOT NULL,
                    fingerprint_id TEXT NOT NULL,

                    status TEXT NOT NULL
                        DEFAULT 'PENDING',

                    priority INTEGER NOT NULL
                        DEFAULT 0,

                    attempts INTEGER NOT NULL
                        DEFAULT 0,

                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,

                    error TEXT
                )
                """
            )

            db.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_jobs_status_priority
                ON jobs(status, priority DESC, id)
                """
            )

    def add(
        self,
        source_folder: str | Path,
        fingerprint_id: str,
        priority: int = 0,
    ):
        created_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO jobs (
                    source_folder,
                    fingerprint_id,
                    status,
                    priority,
                    attempts,
                    created_at
                )
                VALUES (?, ?, 'PENDING', ?, 0, ?)
                """,
                (
                    str(source_folder),
                    str(fingerprint_id),
                    int(priority),
                    created_at,
                ),
            )

            return int(cursor.lastrowid)

    def list(
        self,
        status: str | None = None,
    ):
        with self._connect() as db:

            if status is None:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    ORDER BY
                        priority DESC,
                        id ASC
                    """
                )
            else:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE status = ?
                    ORDER BY
                        priority DESC,
                        id ASC
                    """,
                    (status,),
                )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    def claim(self):
        """
        Atomically take the next PENDING job.

        Returns:
            dict with job data, or None if queue is empty.
        """

        with self._connect() as db:

            db.execute("BEGIN IMMEDIATE")

            cursor = db.execute(
                """
                SELECT *
                FROM jobs
                WHERE status = 'PENDING'
                ORDER BY
                    priority DESC,
                    id ASC
                LIMIT 1
                """
            )

            row = cursor.fetchone()

            if row is None:
                db.commit()
                return None

            job_id = row["id"]
            started_at = self._now()

            db.execute(
                """
                UPDATE jobs
                SET
                    status = 'PROCESSING',
                    attempts = attempts + 1,
                    started_at = ?,
                    error = NULL
                WHERE
                    id = ?
                    AND status = 'PENDING'
                """,
                (
                    started_at,
                    job_id,
                ),
            )

            db.commit()

            return dict(
                db.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE id = ?
                    """,
                    (job_id,),
                ).fetchone()
            )

    def complete(self, job_id):
        """
        Mark a processing job as DONE.
        """

        finished_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE jobs
                SET
                    status = 'DONE',
                    finished_at = ?,
                    error = NULL
                WHERE
                    id = ?
                    AND status = 'PROCESSING'
                """,
                (
                    finished_at,
                    int(job_id),
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Cannot complete job {job_id}"
                )

    def fail(self, job_id, error):
        """
        Mark a processing job as FAILED.
        """

        finished_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE jobs
                SET
                    status = 'FAILED',
                    finished_at = ?,
                    error = ?
                WHERE
                    id = ?
                    AND status = 'PROCESSING'
                """,
                (
                    finished_at,
                    str(error),
                    int(job_id),
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Cannot fail job {job_id}"
                )

    def counts(self):
        with self._connect() as db:
            cursor = db.execute(
                """
                SELECT
                    status,
                    COUNT(*) AS count
                FROM jobs
                GROUP BY status
                """
            )

            return {
                row["status"]: row["count"]
                for row in cursor.fetchall()
            }

if __name__ == "__main__":
    queue = JobQueue(
        "data/jobs.db"
    )

    print("Queue:", queue.db_path)
    print("Counts:", queue.counts())
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

================ QWEN WORKER ================
from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

# ============================================================
# DATABASE
# ============================================================

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

# ============================================================
# QWEN
# ============================================================

MODEL = "qwen3-vl:4b-instruct"
OLLAMA_URL = "http://localhost:11434/api/chat"

NUM_CTX = 16384
TEMPERATURE = 0

# ============================================================
# PROMPT
# ============================================================

PROMPT = r"""
Ты анализируешь фотографию с улицы для базы наружной рекламы.

Найди рекламный баннер и верни ТОЛЬКО JSON.
Не добавляй пояснений вне JSON.
Не повторяй информацию.
Не придумывай отсутствующую информацию.

Формат:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "banner_type": "видеоэкран",

  "environment": {
    "weather": "",
    "precipitation": "",
    "lighting": ""
  },

  "image_quality": {
    "overall": "",
    "sharpness": "",
    "exposure": "",
    "visibility": "",
    "banner_visible": true,
    "banner_readability": "",
    "motion_blur": false,
    "occlusion": false
  },

  "camera_view": {
    "distance": "",
    "angle": ""
  },

  "analysis_quality": {
    "banner_analysis": "",
    "text_analysis": ""
  },

  "confidence": 0
}

БАННЕР:
client — компания, организация или заказчик.
brand — торговая марка, имя кандидата или рекламируемый бренд.
category — категория рекламы.
text — читаемые надписи на баннере.
colors — основные цвета самого баннера.
objects — основные изображения и предметы НА БАННЕРЕ.
description — краткое описание композиции баннера, максимум 300 символов.
banner_type — на данном этапе "видеоэкран".

ОКРУЖЕНИЕ:
Определи ТОЛЬКО:
weather — солнечно / пасмурно / облачно / туман / неизвестно.
precipitation — нет / дождь / снег / мокрый снег / неизвестно.
lighting — яркий день / дневной свет / сумерки / ночь / искусственное освещение / неизвестно.

Не описывай окружающую сцену.
Не описывай здания, дороги, автомобили, автобусы, людей,
дорожные знаки, провода или растительность.

КАЧЕСТВО:
Оцени только качество фотографии и видимость баннера.

overall — хорошее / удовлетворительное / плохое.
sharpness — резкое / слегка размыто / сильно размыто / неизвестно.
exposure — нормальная / пересвечено / недоэкспонировано / очень тёмное / неизвестно.
visibility — хорошо виден / частично виден / плохо виден / не виден.
banner_visible — true или false.
banner_readability — высокая / средняя / низкая / невозможно определить.
motion_blur — true или false.
occlusion — true или false.

КАМЕРА:
distance — далеко / средняя дистанция / близко / неизвестно.
angle — прямо / слева / справа / сверху / снизу / косой ракурс / неизвестно.

Если баннер не виден:
client = ""
brand = ""
category = ""
text = []
colors = []
objects = []
description = ""
banner_visible = false

Массивы должны содержать только действительно важные элементы.
Не более 10 элементов в каждом массиве.
Не повторяй элементы.

confidence — уверенность в анализе от 0 до 100.
"""

# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def claim_photo(conn):
    """
    Берём следующую фотографию, которая ещё не обработана Qwen.

    ВАЖНО:
        Qwen работает независимо от DINO.

    Единственная связь:
        photo_id -> результат Qwen

    address_id здесь НЕ используется.
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:

        cur.execute(
            """
            SELECT
                id,
                photo_id,
                source_path,
                filename
            FROM photos
            WHERE qwen_status = 'pending'
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
                qwen_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND qwen_status = 'pending'
            """,
            (row["id"],),
        )

        conn.commit()

        return row

def mark_done(
    conn,
    db_id,
    result,
    elapsed,
):
    """
    Сохраняет результат Qwen.

    db_id — внутренний bigint photos.id.

    photo_id остаётся постоянным идентификатором
    фотографии и не зависит от адреса.
    """

    text_json = result.get("text", [])
    colors_json = result.get("colors", [])
    objects_json = result.get("objects", [])
    environment_json = result.get("environment", {})
    image_quality_json = result.get("image_quality", {})
    camera_view_json = result.get("camera_view", {})
    analysis_quality_json = result.get(
        "analysis_quality",
        {},
    )

    raw_json = dict(result)
    raw_json.pop("_time_sec", None)

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'done',

                client = %s,
                brand = %s,
                category = %s,
                description = %s,
                confidence = %s,

                qwen_time_sec = %s,

                text_json = %s::jsonb,
                colors_json = %s::jsonb,
                objects_json = %s::jsonb,
                environment_json = %s::jsonb,
                image_quality_json = %s::jsonb,
                camera_view_json = %s::jsonb,
                analysis_quality_json = %s::jsonb,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:37:22

> **Remembering**
>
>
> ****
>
> 
>
> **Identified automation architecture gaps and planned the next patch**
>
> 
>
> Worked for 9s

Да. Теперь картина стала полной.

**Главная проблема сейчас:** у нас есть три уровня, но они пока не соединены в рабочий контур:

1. `controller.py` умеет хранить режимы и флаги `running / stop_requested`.
2. `automation.py` умеет менять режим в PostgreSQL.
3. `photo_processing.py` **самостоятельно** запускает `dino_worker.py` и `qwen_worker.py` через `asyncio.create_subprocess_exec()`.

При этом **реального автоматического запуска по времени и Watcher пока нет** - поиск это подтвердил: нет scheduler/watchdog/observer и нет вызовов `start_automatic()` / `start_watcher()` из рабочего цикла.

И ещё важнее: `start_dino()` и `start_qwen()` сейчас специально проверяют:

```python
if state.mode != "manual":
```

То есть даже если мы создадим автоматический запуск, текущие функции UI его заблокируют.

### Что я предлагаю сделать следующим патчем

Не ломать уже работающую обработку, а разделить ответственность:

**PostgreSQL `pipeline_control`**
→ является источником режима.

**Контроллер**
→ разрешает/запрещает запуск и фиксирует `running/stop_requested`.

**Supervisor**
→ отдельный постоянный процесс/задача:
- `manual` - ничего сам не запускает;
- `automatic` - в заданное время запускает DINO + Qwen;
- `watcher` - следит за папкой и запускает обработку при появлении новых фото;
- после остановки корректно возвращает состояние в `manual`.

**UI**
→ только управляет режимом и показывает состояние.

**DINO/Qwen workers**
→ остаются независимыми очередями PostgreSQL, как сейчас.

Это особенно хорошо ложится на уже существующую архитектуру: DINO и Qwen действительно не должны зависеть друг от друга.

Но перед патчем я бы сделал **одну последнюю проверку конца `dino_worker.py` и `qwen_worker.py`**, потому что нам нужно точно знать, что они делают после опустошения очереди: завершаются или остаются ждать новые фотографии.

Дай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DINO END ================" && \
sed -n '240,520p' app/workers/dino_worker.py && \
echo "================ QWEN END ================" && \
sed -n '240,520p' app/workers/qwen_worker.py
```

После этого уже можно дать **конкретный патч supervisor + controller**, не переделывая рабочие DINO/Qwen.

---

### 👤 **User** — 2026-08-19 01:38:00

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DINO END ================" && \
sed -n '240,520p' app/workers/dino_worker.py && \
echo "================ QWEN END ================" && \
sed -n '240,520p' app/workers/qwen_worker.py
================ DINO END ================
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
================ QWEN END ================
        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'done',

                client = %s,
                brand = %s,
                category = %s,
                description = %s,
                confidence = %s,

                qwen_time_sec = %s,

                text_json = %s::jsonb,
                colors_json = %s::jsonb,
                objects_json = %s::jsonb,
                environment_json = %s::jsonb,
                image_quality_json = %s::jsonb,
                camera_view_json = %s::jsonb,
                analysis_quality_json = %s::jsonb,
                raw_json = %s::jsonb,

                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = %s
            """,
            (
                result.get("client") or None,
                result.get("brand") or None,
                result.get("category") or None,
                result.get("description") or None,
                result.get("confidence"),

                elapsed,

                json.dumps(
                    text_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    colors_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    objects_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    environment_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    image_quality_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    camera_view_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    analysis_quality_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    raw_json,
                    ensure_ascii=False,
                ),

                db_id,
            ),
        )

    conn.commit()

def mark_error(
    conn,
    db_id,
    error,
):
    message = str(error)

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'error',
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
# IMAGE
# ============================================================

def image64(path: Path):
    with open(path, "rb") as f:
        return base64.b64encode(
            f.read()
        ).decode()

# ============================================================
# QWEN REQUEST
# ============================================================

def ask(path: Path):

    max_attempts = 2

    for attempt in range(
        1,
        max_attempts + 1,
    ):

        payload = {
            "model": MODEL,

            "messages": [
                {
                    "role": "user",
                    "content": PROMPT,
                    "images": [
                        image64(path)
                    ],
                }
            ],

            "stream": False,

            "options": {
                "num_ctx": NUM_CTX,
                "temperature": TEMPERATURE,
                "num_predict": 800,
            },
        }

        started = time.time()

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=1800,
        )

        elapsed = time.time() - started

        if response.status_code != 200:
            raise RuntimeError(
                response.text
            )

        data = response.json()

        print(
            "[OLLAMA]",
            {
                "total_duration_sec":
                    round(
                        data.get(
                            "total_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "load_duration_sec":
                    round(
                        data.get(
                            "load_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "prompt_eval_duration_sec":
                    round(
                        data.get(
                            "prompt_eval_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "eval_duration_sec":
                    round(
                        data.get(
                            "eval_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "prompt_eval_count":
                    data.get(
                        "prompt_eval_count"
                    ),
                "eval_count":
                    data.get(
                        "eval_count"
                    ),
            },
            flush=True,
        )

        answer = data[
            "message"
        ][
            "content"
        ]

        cleaned = answer.strip()

        if cleaned.startswith("```"):

            cleaned = cleaned.replace(
                "```json",
                "",
                1,
            )

            cleaned = cleaned.replace(
                "```",
                "",
            ).strip()

        try:

            result = json.loads(
                cleaned
            )

            description = str(
                result.get(
                    "description"
                ) or ""
            ).strip()

            if description:
                result["_time_sec"] = round(
                    elapsed,
                    2,
                )

                return result

            if attempt < max_attempts:

                print(
                    "[QWEN RETRY]",
                    "description empty",
                    "| attempt:",
                    attempt + 1,
                    flush=True,
                )

                continue

            result["_time_sec"] = round(
                elapsed,
                2,
            )

            return result

        except Exception as exc:

            print(
                "[QWEN JSON ERROR]",
                repr(exc),
                "| attempt:",
                attempt,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:38:01

> **Inspecting Controller and Automation Code**
>
>
> **Inspecting Controller and Automation Code**
>
> 
>
> Worked for 4s

Отлично. Теперь можно уверенно двигаться дальше.

Из вывода видно важное:

- **DINO и Qwen — одноразовые workers**: обработали текущую очередь → `Queue empty` → завершились.
- Это **идеально подходит для supervisor**: ему не нужно держать workers постоянно запущенными.
- `reset_processing()` у DINO уже есть, а у Qwen аналогичного recovery сейчас нет — это надо добавить отдельно.
- `controller.py` уже хранит режим и `stop_requested`, поэтому его не нужно переделывать с нуля.
- `photo_processing.py` пока остаётся ручным UI-запуском.

### Следующий шаг

Я бы сейчас **не патчил вслепую**. Нам нужно увидеть точную реализацию `controller.py`, особенно как там сохраняются `running` и `stop_requested`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat app/pipeline/controller.py
```

И после этого я дам **готовый патч** сразу для:

1. `app/pipeline/supervisor.py`
2. `app/pipeline/controller.py`
3. recovery Qwen
4. подключения supervisor к `photo_processing.py`

При этом **DINO/Qwen recognition-алгоритм вообще не трогаем**. Их очереди и независимость сохраняем.

---

### 👤 **User** — 2026-08-19 01:38:29

int_mvp_v02 && \
cat app/pipeline/controller.py
from __future__ import annotations

import os
from datetime import time

import psycopg2
from psycopg2.extras import RealDictCursor

from app.pipeline.modes import (
    MODE_AUTOMATIC,
    MODE_MANUAL,
    MODE_WATCHER,
    PipelineMode,
    build_automatic_mode,
    build_manual_mode,
    build_watcher_mode,
    validate_mode,
)

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_row(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_control (id)
            VALUES (1)
            ON CONFLICT (id) DO NOTHING
            """
        )

    conn.commit()

def get_state() -> PipelineMode:
    with get_connection() as conn:
        ensure_row(conn)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    mode,
                    auto_enabled,
                    auto_time,
                    watcher_enabled,
                    watcher_path,
                    running,
                    stop_requested
                FROM pipeline_control
                WHERE id = 1
                """
            )

            row = cur.fetchone()

    if row is None:
        return build_manual_mode()

    mode = validate_mode(row["mode"])

    return PipelineMode(
        mode=mode,
        auto_enabled=bool(row["auto_enabled"]),
        auto_time=row["auto_time"],
        watcher_enabled=bool(row["watcher_enabled"]),
        watcher_path=row["watcher_path"],
        running=bool(row["running"]),
        stop_requested=bool(row["stop_requested"]),
    )

def _save_state(state: PipelineMode):
    validate_mode(state.mode)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    mode = %s,
                    auto_enabled = %s,
                    auto_time = %s,
                    watcher_enabled = %s,
                    watcher_path = %s,
                    running = %s,
                    stop_requested = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                (
                    state.mode,
                    state.auto_enabled,
                    state.auto_time,
                    state.watcher_enabled,
                    state.watcher_path,
                    state.running,
                    state.stop_requested,
                ),
            )

        conn.commit()

def set_manual():
    state = build_manual_mode()
    _save_state(state)
    return state

def set_automatic(auto_time: time):
    state = build_automatic_mode(auto_time)
    _save_state(state)
    return state

def set_watcher(watcher_path: str):
    state = build_watcher_mode(watcher_path)
    _save_state(state)
    return state

def start_manual():
    state = get_state()

    if state.mode != MODE_MANUAL:
        raise RuntimeError(
            "Manual start is available only in manual mode"
        )

    if state.running:
        raise RuntimeError(
            "Pipeline is already running"
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    state.running = True
    state.stop_requested = False

    return state

def start_automatic():
    state = get_state()

    if state.mode != MODE_AUTOMATIC:
        raise RuntimeError(
            "Automatic start requested while mode is not automatic"
        )

    if state.running:
        return state

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    state.running = True
    state.stop_requested = False

    return state

def start_watcher():
    state = get_state()

    if state.mode != MODE_WATCHER:
        raise RuntimeError(
            "Watcher start requested while mode is not watcher"
        )

    if state.running:
        return state

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    state.running = True
    state.stop_requested = False

    return state

def request_stop():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    stop_requested = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

def finish_stop():
    state = build_manual_mode()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    mode = 'manual',
                    auto_enabled = FALSE,
                    auto_time = NULL,
                    watcher_enabled = FALSE,
                    watcher_path = NULL,
                    running = FALSE,
                    stop_requested = FALSE,
                    stopped_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    return state

def is_stop_requested() -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT stop_requested
                FROM pipeline_control
                WHERE id = 1
                """
            )

            row = cur.fetchone()

    return bool(row and row[0])

def is_running() -> bool:
    return get_state().running

def manual_start_allowed() -> bool:
    state = get_state()

    return (
        state.mode == MODE_MANUAL
        and not state.running
    )

def get_mode() -> str:
    return get_state().mode
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:38:30

Да. Теперь у нас достаточно информации, чтобы сделать следующий слой правильно.

### Что уже есть

`controller.py` уже фактически готов как **центральное состояние pipeline**:

- `manual` → запуск только кнопкой;
- `automatic` → `start_automatic()`;
- `watcher` → `start_watcher()`;
- `request_stop()` → выставляет остановку;
- `finish_stop()` → возвращает всё в `manual`;
- состояние хранится в PostgreSQL.

И workers сами завершаются после опустошения очереди. Поэтому **не надо превращать workers в бесконечные демоны**.

### Но есть один важный архитектурный момент

Сейчас `start_automatic()` и `start_watcher()` только меняют:

```text
running = TRUE
```

Они **не запускают DINO/Qwen**.

А `photo_processing.py` запускает их напрямую:

```text
UI button
   ↓
start_dino()
   ↓
create_subprocess_exec(dino_worker.py)

UI button
   ↓
start_qwen()
   ↓
create_subprocess_exec(qwen_worker.py)
```

Нам нужен слой между ними:

```text
                 PostgreSQL
              pipeline_control
                     │
                     ▼
              ┌──────────────┐
              │   SUPERVISOR │
              └──────┬───────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   dino_worker.py            qwen_worker.py
        │                         │
        └──────────┬──────────────┘
                   ▼
               PostgreSQL
                 photos
```

И тогда:

**Manual**

```text
Кнопка Запустить
      ↓
start_manual()
      ↓
supervisor запускает workers
```

**Automatic**

```text
MODE_AUTOMATIC
      ↓
supervisor ждёт auto_time
      ↓
start_automatic()
      ↓
DINO + Qwen
```

**Watcher**

```text
MODE_WATCHER
      ↓
supervisor смотрит watcher_path
      ↓
появились новые фото
      ↓
DINO + Qwen
```

### Важное изменение

Я бы **не стал пока подключать supervisor прямо к NiceGUI**.

Лучше сделать его независимым:

```text
app/pipeline/supervisor.py
```

Его можно будет запускать отдельно:

```bash
uv run python -m app.pipeline.supervisor
```

А NiceGUI только меняет настройки в PostgreSQL.

Это даст нам очень хороший результат: **если веб-интерфейс упал или браузер закрыли — автоматизация продолжает работать**.

---

## Следующий патч

Сейчас я предлагаю сделать только первый кусок — **supervisor для manual/automatic**, без Watcher.

Почему: Watcher требует определить, что считать «новой фотографией» и как не запускать повторно один и тот же каталог. Это лучше добавить после того, как автоматический цикл заработает.

Первый патч будет:

```text
app/pipeline/supervisor.py
```

Он будет:

1. читать `pipeline_control`;
2. видеть `manual / automatic / watcher`;
3. для manual ждать ручного `running=True`;
4. для automatic ждать `auto_time`;
5. запускать существующие:
   - `dino_worker.py`
   - `qwen_worker.py`
6. ждать их завершения;
7. при `stop_requested` корректно завершать процессы;
8. вызывать `finish_stop()`;
9. после завершения автоматического запуска возвращать `running=False`, **но не сбрасывать automatic mode** — это важно для следующего запуска по времени.

И вот здесь я бы **не использовал существующий `start_dino()` / `start_qwen()` из UI**. Supervisor должен иметь собственный `subprocess`-launcher.

Если согласен с такой схемой, следующим сообщением дам **готовую команду `cat > app/pipeline/supervisor.py <<'PY' ... PY`**, чтобы ты просто вставил и запустил проверку.

---

### 👤 **User** — 2026-08-19 01:38:47

да

---

