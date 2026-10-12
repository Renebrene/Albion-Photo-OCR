## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 👤 **User** — 2026-08-18 23:54:43

int_mvp_v02

echo "===== queue.py ====="
cat app/pipeline/queue.py

echo
echo "===== worker.py ====="
cat app/pipeline/worker.py

echo
echo "===== recovery.py ====="
cat app/pipeline/recovery.py

echo
echo "===== qwen_worker.py ====="
sed -n '1,420p' app/workers/qwen_worker.py
===== queue.py =====
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

===== worker.py =====
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

===== recovery.py =====
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

import psycopg2

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def recover_stale_jobs(
    timeout_minutes: int = 30,
):
    """
    Возвращает зависшие worker jobs:

        PROCESSING -> PENDING

    Только если worker находился в PROCESSING
    дольше timeout_minutes.

    DONE не затрагивается.
    ERROR не затрагивается.
    """

    cutoff = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) - timedelta(
        minutes=timeout_minutes
    )

    recovered_dino = 0
    recovered_qwen = 0

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE photos
                SET
                    dino_status = 'pending',
                    dino_started_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE
                    dino_status = 'processing'
                    AND dino_started_at < %s
                """,
                (cutoff,),
            )

            recovered_dino = cur.rowcount

            cur.execute(
                """
                UPDATE photos
                SET
                    qwen_status = 'pending',
                    qwen_started_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE
                    qwen_status = 'processing'
                    AND qwen_started_at < %s
                """,
                (cutoff,),
            )

            recovered_qwen = cur.rowcount

        conn.commit()

    return {
        "dino": recovered_dino,
        "qwen": recovered_qwen,
    }

if __name__ == "__main__":

    result = recover_stale_jobs()

    print(
        "RECOVERY:",
        result,
    )

===== qwen_worker.py =====
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:54:44

Да, теперь картина полная. И здесь видно важный момент: **`app/pipeline/worker.py` сейчас старый worker для создания fingerprint**, поэтому его нельзя просто подключить как главный worker фотобазы.

Нам нужен **новый оркестратор**, а существующие:

- `app/workers/dino_worker.py`
- `app/workers/qwen_worker.py`
- `app/pipeline/recovery.py`

оставляем отдельными исполнителями.

### Следующий шаг

Сначала сделаем `pipeline/worker.py` именно диспетчером фотобазы:

```text
pipeline_control
      │
      ▼
pipeline/worker.py
      │
      ├── recovery
      │
      ├── DINO
      │
      ├── Qwen
      │
      ├── sort
      │
      └── preview
```

Но **не будем запускать DINO/Qwen через `subprocess` на каждую фотографию**. Они уже сами имеют PostgreSQL-очереди:

```text
photos
 ├── dino_status
 ├── qwen_status
 ├── sort_status
 └── preview_status
```

Это намного правильнее.

---

## 1. Сначала сделаем общий запуск одного этапа

Создай резервную копию старого worker:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp app/pipeline/worker.py \
   app/pipeline/worker.py.bak_fingerprint_worker
```

Теперь **полностью замени** `app/pipeline/worker.py`:

```bash
cat > app/pipeline/worker.py <<'PY'
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from app.pipeline.controller import (
    finish_stop,
    get_state,
    is_stop_requested,
)
from app.pipeline.recovery import recover_stale_jobs

PROJECT = Path(__file__).resolve().parents[2]

DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
QWEN_WORKER = PROJECT / "app" / "workers" / "qwen_worker.py"

POLL_INTERVAL = float(
    os.getenv(
        "PIPELINE_POLL_INTERVAL",
        "2",
    )
)

class PipelineWorker:

    def __init__(self):
        self.children: list[subprocess.Popen] = []

        self.stop_requested = False

        signal.signal(
            signal.SIGINT,
            self._handle_signal,
        )

        signal.signal(
            signal.SIGTERM,
            self._handle_signal,
        )

    # ========================================================
    # SIGNAL
    # ========================================================

    def _handle_signal(
        self,
        signum,
        frame,
    ):
        print(
            f"[PIPELINE] Signal received: {signum}",
            flush=True,
        )

        self.stop_requested = True

        self.stop_children()

    # ========================================================
    # RECOVERY
    # ========================================================

    def recover(self):
        print(
            "[PIPELINE] Running recovery...",
            flush=True,
        )

        result = recover_stale_jobs()

        print(
            "[PIPELINE] Recovery:",
            result,
            flush=True,
        )

    # ========================================================
    # STOP
    # ========================================================

    def should_stop(self) -> bool:

        if self.stop_requested:
            return True

        try:
            return is_stop_requested()

        except Exception as exc:
            print(
                "[PIPELINE] Cannot read stop flag:",
                exc,
                flush=True,
            )

            return False

    def stop_children(self):

        if not self.children:
            return

        print(
            "[PIPELINE] Stopping child workers...",
            flush=True,
        )

        for process in self.children:

            if process.poll() is None:

                try:
                    process.terminate()

                except Exception:
                    pass

        deadline = time.time() + 10

        for process in self.children:

            while (
                process.poll() is None
                and time.time() < deadline
            ):
                time.sleep(0.2)

            if process.poll() is None:

                try:
                    process.kill()

                except Exception:
                    pass

        self.children.clear()

    # ========================================================
    # START CHILD
    # ========================================================

    def start_child(
        self,
        script: Path,
        name: str,
    ):

        print(
            f"[PIPELINE] Starting {name}...",
            flush=True,
        )

        process = subprocess.Popen(
            [
                sys.executable,
                str(script),
            ],
            cwd=PROJECT,
        )

        self.children.append(
            process
        )

        return process

    # ========================================================
    # DINO
    # ========================================================

    def run_dino(self):

        if self.should_stop():
            return

        process = self.start_child(
            DINO_WORKER,
            "DINO",
        )

        while process.poll() is None:

            if self.should_stop():

                self.stop_children()

                return

            time.sleep(
                POLL_INTERVAL
            )

        self.children.remove(
            process
        )

        print(
            "[PIPELINE] DINO finished:",
            process.returncode,
            flush=True,
        )

    # ========================================================
    # QWEN
    # ========================================================

    def run_qwen(self):

        if self.should_stop():
            return

        process = self.start_child(
            QWEN_WORKER,
            "QWEN",
        )

        while process.poll() is None:

            if self.should_stop():

                self.stop_children()

                return

            time.sleep(
                POLL_INTERVAL
            )

        self.children.remove(
            process
        )

        print(
            "[PIPELINE] QWEN finished:",
            process.returncode,
            flush=True,
        )

    # ========================================================
    # PIPELINE
    # ========================================================

    def run(self):

        print("=" * 70)
        print("PHOTOBASE PIPELINE WORKER")
        print("=" * 70)

        state = get_state()

        print(
            "[PIPELINE] mode:",
            state.mode,
        )

        print(
            "[PIPELINE] running:",
            state.running,
        )

        if not state.running:

            print(
                "[PIPELINE] Pipeline is not marked as running."
            )

            return

        self.recover()

        try:

            # ------------------------------------------------
            # DINO
            # ------------------------------------------------

            if not self.should_stop():

                self.run_dino()

            # ------------------------------------------------
            # QWEN
            # ------------------------------------------------

            if not self.should_stop():

                self.run_qwen()

            # ------------------------------------------------
            # FINISH
            # ------------------------------------------------

            if self.should_stop():

                print(
                    "[PIPELINE] Stop requested.",
                    flush=True,
                )

            else:

                print(
                    "[PIPELINE] All current stages finished.",
                    flush=True,
                )

        finally:

            self.stop_children()

            try:

                finish_stop()

            except Exception as exc:

                print(
                    "[PIPELINE] "
                    "Cannot reset controller:",
                    exc,
                    flush=True,
                )

        print(
            "[PIPELINE] Worker stopped.",
            flush=True,
        )

def main():

    worker = PipelineWorker()

    worker.run()

if __name__ == "__main__":
    main()
PY
```

Проверяем:

```bash
uv run python -m py_compile \
    app/pipeline/worker.py \
    app/pipeline/controller.py \
    app/pipeline/modes.py \
    app/pipeline/recovery.py
```

---

### Важный момент

Сейчас я намеренно сделал запуск:

```text
DINO → завершился → QWEN → завершился
```

а **не одновременно**.

Это первый безопасный вариант для проверки управляющего слоя.

При этом сами очереди DINO/Qwen остаются независимыми. Следующим шагом мы можем сделать:

```text
                 PIPELINE
                    │
          ┌─────────┴─────────┐
          │                   │
        DINO                QWEN
          │                   │
       pending             pending
          │                   │
          └─────────┬─────────┘
                    │
                 SORT
                    │
                PREVIEW
```

и тогда DINO и Qwen смогут работать **параллельно**, что для RTX 3060 особенно важно настроить аккуратно.

Но пока **не запускай полный pipeline**.

Сначала выполни только:

```bash
uv run python -m py_compile app/pipeline/worker.py
```

Если ошибок нет — следующим шагом подключим **кнопку «Запустить» из UI к этому worker**, чтобы нажатие кнопки реально меняло `pipeline_control.running` и запускало весь конвейер.

---

### 👤 **User** — 2026-08-18 23:55:02

int_mvp_v02

echo "===== PHOTO PROCESSING ====="
sed -n '1,280p' app/web/components/technical_modules/photo_processing.py

echo
echo "===== TECHNICAL ====="
sed -n '180,270p' app/web/components/technical.py
===== PHOTO PROCESSING =====
import asyncio
import re
from pathlib import Path

from nicegui import ui

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"
DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"

def build_photo_processing():

    source_input = ui.input(
        label="Источник фотографий",
        value=str(PROJECT / "data/input/daily"),
    ).props(
        "outlined dense"
    ).classes("flex-1")

    output_input = ui.input(
        label="Результат",
        value=str(PROJECT / "data/output/daily"),
    ).props(
        "outlined dense"
    ).classes("flex-1")

    status_label = ui.label(
        "Готов к запуску"
    ).classes(
        "text-sm text-grey-6"
    )

    run_button = None

    async def run_pipeline():

        input_dir = Path(
            source_input.value
        ).expanduser()

        if not input_dir.is_absolute():
            input_dir = PROJECT / input_dir

        if not input_dir.exists():
            ui.notify(
                f"Папка не найдена: {input_dir}",
                type="negative",
            )
            return

        images = [
            p for p in input_dir.iterdir()
            if p.is_file()
            and p.suffix.lower() in {
                ".jpg",
                ".jpeg",
                ".png",
            }
        ]

        if not images:
            ui.notify(
                "В папке нет фотографий",
                type="negative",
            )
            return

        if not DAILY_SCRIPT.exists():
            ui.notify(
                f"Не найден скрипт: {DAILY_SCRIPT}",
                type="negative",
            )
            return

        run_button.disable()

        status_label.text = (
            f"Запуск Hybrid v12... "
            f"Фотографий: {len(images)}"
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

                output_lines.append(text)

                if text:
                    status_label.text = text[-180:]

            returncode = await process.wait()

            output = "\n".join(output_lines)

            if returncode != 0:

                status_label.text = (
                    f"✗ Hybrid v12: ошибка ({returncode})"
                )

                ui.notify(
                    "Распознавание завершилось ошибкой",
                    type="negative",
                    timeout=8000,
                )

                return

            match = re.search(
                r"Output\s*:\s*(.+)",
                output,
            )

            if match:

                result_dir = Path(
                    match.group(1).strip()
                )

            else:

                result_dir = None

            if not result_dir or not result_dir.exists():

                status_label.text = (
                    "⚠ Hybrid завершён, "
                    "папка результата не найдена"
                )

                ui.notify(
                    "Hybrid завершён, "
                    "но папка результата не определена.",
                    type="warning",
                    timeout=8000,
                )

                return

            output_input.value = str(
                result_dir
            )

            status_label.text = (
                "✓ Hybrid v12: сортировка завершена"
            )

            ui.notify(
                f"Сортировка завершена: {result_dir}",
                type="positive",
                timeout=5000,
            )

            # ====================================================
            # QWEN3-VL 4B
            # ====================================================

            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"

            if not qwen_script.exists():

                status_label.text = (
                    "✓ Hybrid завершён → Qwen script не найден"
                )

                ui.notify(
                    f"Не найден Qwen script: {qwen_script}",
                    type="warning",
                    timeout=8000,
                )

                return

            # Имя папки Hybrid запуска:
            # 20260816_230042
            run_name = result_dir.name

            qwen_output = (
                PROJECT
                / "data"
                / "metadata"
                / "qwen4b"
                / run_name
            )

            qwen_output.mkdir(
                parents=True,
                exist_ok=True,
            )

            status_label.text = (
                "▶ Qwen3-VL 4B: выполняется..."
            )

            ui.notify(
                "▶ Сортировка завершена. "
                "Запускается Qwen3-VL 4B.",
                type="info",
                timeout=5000,
            )

            try:

                qwen_process = await asyncio.create_subprocess_exec(
                    str(PROJECT / ".venv" / "bin" / "python"),
                    str(qwen_script),
                    "--input",
                    str(result_dir),
                    "--output",
                    str(qwen_output),
                    cwd=str(PROJECT),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )

                qwen_lines = []

                while True:

                    line = await qwen_process.stdout.readline()

                    if not line:
                        break

                    text = line.decode(
                        "utf-8",
                        errors="replace",
                    ).rstrip()

                    qwen_lines.append(text)

                    if status_label:
                        status_label.text = text[-160:]

                qwen_returncode = await qwen_process.wait()

                if qwen_returncode != 0:

                    status_label.text = (
                        "✗ Hybrid v12: ✓  "
                        "Qwen3-VL 4B: ошибка"
                    )

                    ui.notify(

===== TECHNICAL =====
                ui.tab(
                    "data",
                    label="Данные",
                    icon="storage",
                )

                ui.tab(
                    "system",
                    label="Система",
                    icon="computer",
                )

                ui.tab(
                    "fingerprints",
                    label="Fingerprints",
                    icon="fingerprint",
                )

                ui.tab(
                    "users",
                    label="Пользователи",
                    icon="people",
                )

            ui.separator()

            # ====================================================
            # TAB CONTENT
            # ====================================================

            with ui.scroll_area().classes(
                "w-full flex-1"
            ):

                with ui.tab_panels(
                    tabs,
                    value="photo_processing",
                ).classes(
                    "w-full"
                ):

                    with ui.tab_panel("photo_processing"):
                        build_photo_processing()

                    with ui.tab_panel("last_run"):
                        build_last_run()

                    with ui.tab_panel("automation"):
                        build_automation()

                    with ui.tab_panel("qwen"):
                        build_qwen()

                    with ui.tab_panel("data"):
                        build_data()

                    with ui.tab_panel("system"):
                        build_system()

                    with ui.tab_panel("fingerprints"):
                        build_fingerprints()

                    with ui.tab_panel("users"):
                        build_users()

    dialog.open()

    # Открываем нужную вкладку сразу.
    if initial_tab:
        ui.timer(
            0.05,
            lambda: tabs.set_value(initial_tab),
            once=True,
        )

    _restore_and_watch_size()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:55:04

Да. Теперь картина полностью складывается.

**Сейчас у нас есть три разных уровня, и они пока не соединены:**

1. **`pipeline_control`** — уже работает как центральное состояние режима:
   - `manual`
   - `automatic`
   - `watcher`
   - `running`
   - `stop_requested`

2. **UI «Автоматика»** — уже правильно пишет это состояние в PostgreSQL:
   - чекбокс → `set_automatic()` / `set_manual()`
   - время → `auto_time`
   - состояние после перезапуска читается из БД.

3. **Фактический запуск обработки** пока живёт отдельно в `photo_processing.py`:
   ```python
   DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
   ```
   и кнопка напрямую запускает:
   ```python
   asyncio.create_subprocess_exec(
       "bash",
       str(DAILY_SCRIPT),
       ...
   )
   ```

То есть **контроллер пока не управляет реальным процессом**.

### Что особенно важно

`FingerprintWorker` из `app/pipeline/worker.py` — это очередь создания fingerprint:

```text
JobQueue
   ↓
FingerprintWorker
   ↓
FingerprintManager.create()
```

А текущая ежедневная обработка:

```text
photo_processing.py
       ↓
run_daily_hybrid_v12.sh
       ↓
Hybrid v12
       ↓
Qwen3-VL
```

и отдельно существует новый:

```text
pipeline_control
       ↓
controller.py
```

Поэтому сейчас **не надо пытаться притянуть `JobQueue` к ежедневной обработке**. Это другая очередь/задача.

---

## Что я предлагаю сделать следующим этапом

Сначала не менять алгоритм обработки вообще.

Сделать слой:

```text
                 pipeline_control
                       │
          ┌────────────┼────────────┐
          ↓            ↓            ↓
       MANUAL       AUTOMATIC      WATCHER
          │            │            │
          └────────────┼────────────┘
                       ↓
                PipelineRunner
                       ↓
             run_daily_hybrid_v12.sh
                       ↓
                    Qwen
```

### В ручном режиме

Существующая кнопка должна делать:

```text
Запустить
   ↓
controller.start_manual()
   ↓
running = true
   ↓
запуск Hybrid
   ↓
Hybrid завершён
   ↓
Qwen завершён
   ↓
controller.finish_stop()
```

### В автоматическом

Отдельный scheduler смотрит:

```text
mode = automatic
auto_enabled = true
auto_time = 06:00
running = false
```

и в 06:00 запускает **тот же самый PipelineRunner**.

То есть алгоритм обработки один, отличается только источник запуска.

### В watcher

Позже:

```text
mode = watcher
watcher_path = ...
        ↓
появились новые фотографии
        ↓
PipelineRunner
```

---

## И ещё один важный момент

Сейчас `request_stop()` только выставляет:

```text
stop_requested = true
```

но `photo_processing.py` **вообще не проверяет это состояние**.

Поэтому кнопка «Остановить» пока может сказать БД:

```text
stop_requested = true
```

но запущенный:

```text
run_daily_hybrid_v12.sh
```

продолжит работать.

Это надо исправить аккуратно, особенно потому что ты раньше хотел **реальную остановку без ожидания завершения тяжёлого Qwen**.

---

### Поэтому сейчас я бы ничего не переписывал

Следующий шаг — посмотреть **реальный `run_daily_hybrid_v12.sh` и оставшуюся часть `photo_processing.py`**, чтобы определить точные границы процесса.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== DAILY SCRIPT ====="
cat scripts/run_daily_hybrid_v12.sh

echo
echo "===== PHOTO PROCESSING 1 ====="
sed -n '1,260p' app/web/components/technical_modules/photo_processing.py

echo
echo "===== PHOTO PROCESSING 2 ====="
sed -n '261,560p' app/web/components/technical_modules/photo_processing.py
```

После этого уже можно будет сделать **один общий `PipelineRunner`**, не ломая текущий Hybrid v12 и Qwen.

---

### 👤 **User** — 2026-08-18 23:56:21

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== DAILY SCRIPT ====="
cat scripts/run_daily_hybrid_v12.sh

echo
echo "===== PHOTO PROCESSING 1 ====="
sed -n '1,260p' app/web/components/technical_modules/photo_processing.py

echo
echo "===== PHOTO PROCESSING 2 ====="
sed -n '261,560p' app/web/components/technical_modules/photo_processing.py
===== DAILY SCRIPT =====
#!/usr/bin/env bash

set -euo pipefail

PROJECT="$HOME/projects/scene_fingerprint_mvp_v02"

INPUT="$PROJECT/data/input/daily"

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"

OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"

echo
echo "================================================================================"
echo "SCENE FINGERPRINT — DAILY HYBRID V12"
echo "================================================================================"
echo
echo "INPUT : $INPUT"
echo "OUTPUT: $OUTPUT"
echo

if [ ! -d "$INPUT" ]; then
    echo "ERROR: input directory does not exist:"
    echo "$INPUT"
    exit 1
fi

COUNT=$(find "$INPUT" -maxdepth 1 -type f \
    $ -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" $ \
    | wc -l)

echo "Images: $COUNT"
echo

if [ "$COUNT" -eq 0 ]; then
    echo "ERROR: no images found in $INPUT"
    exit 1
fi

mkdir -p "$OUTPUT"

/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
    --input "$INPUT" \
    --output "$OUTPUT" \
    --first-address 78 \
    --last-address 95

echo
echo "================================================================================"
echo "DAILY PIPELINE FINISHED"
echo "================================================================================"
echo
echo "Images : $COUNT"
echo "Output : $OUTPUT"
echo

===== PHOTO PROCESSING 1 =====
import asyncio
import re
from pathlib import Path

from nicegui import ui

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"
DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"

def build_photo_processing():

    source_input = ui.input(
        label="Источник фотографий",
        value=str(PROJECT / "data/input/daily"),
    ).props(
        "outlined dense"
    ).classes("flex-1")

    output_input = ui.input(
        label="Результат",
        value=str(PROJECT / "data/output/daily"),
    ).props(
        "outlined dense"
    ).classes("flex-1")

    status_label = ui.label(
        "Готов к запуску"
    ).classes(
        "text-sm text-grey-6"
    )

    run_button = None

    async def run_pipeline():

        input_dir = Path(
            source_input.value
        ).expanduser()

        if not input_dir.is_absolute():
            input_dir = PROJECT / input_dir

        if not input_dir.exists():
            ui.notify(
                f"Папка не найдена: {input_dir}",
                type="negative",
            )
            return

        images = [
            p for p in input_dir.iterdir()
            if p.is_file()
            and p.suffix.lower() in {
                ".jpg",
                ".jpeg",
                ".png",
            }
        ]

        if not images:
            ui.notify(
                "В папке нет фотографий",
                type="negative",
            )
            return

        if not DAILY_SCRIPT.exists():
            ui.notify(
                f"Не найден скрипт: {DAILY_SCRIPT}",
                type="negative",
            )
            return

        run_button.disable()

        status_label.text = (
            f"Запуск Hybrid v12... "
            f"Фотографий: {len(images)}"
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

                output_lines.append(text)

                if text:
                    status_label.text = text[-180:]

            returncode = await process.wait()

            output = "\n".join(output_lines)

            if returncode != 0:

                status_label.text = (
                    f"✗ Hybrid v12: ошибка ({returncode})"
                )

                ui.notify(
                    "Распознавание завершилось ошибкой",
                    type="negative",
                    timeout=8000,
                )

                return

            match = re.search(
                r"Output\s*:\s*(.+)",
                output,
            )

            if match:

                result_dir = Path(
                    match.group(1).strip()
                )

            else:

                result_dir = None

            if not result_dir or not result_dir.exists():

                status_label.text = (
                    "⚠ Hybrid завершён, "
                    "папка результата не найдена"
                )

                ui.notify(
                    "Hybrid завершён, "
                    "но папка результата не определена.",
                    type="warning",
                    timeout=8000,
                )

                return

            output_input.value = str(
                result_dir
            )

            status_label.text = (
                "✓ Hybrid v12: сортировка завершена"
            )

            ui.notify(
                f"Сортировка завершена: {result_dir}",
                type="positive",
                timeout=5000,
            )

            # ====================================================
            # QWEN3-VL 4B
            # ====================================================

            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"

            if not qwen_script.exists():

                status_label.text = (
                    "✓ Hybrid завершён → Qwen script не найден"
                )

                ui.notify(
                    f"Не найден Qwen script: {qwen_script}",
                    type="warning",
                    timeout=8000,
                )

                return

            # Имя папки Hybrid запуска:
            # 20260816_230042
            run_name = result_dir.name

            qwen_output = (
                PROJECT
                / "data"
                / "metadata"
                / "qwen4b"
                / run_name
            )

            qwen_output.mkdir(
                parents=True,
                exist_ok=True,
            )

            status_label.text = (
                "▶ Qwen3-VL 4B: выполняется..."
            )

            ui.notify(
                "▶ Сортировка завершена. "
                "Запускается Qwen3-VL 4B.",
                type="info",
                timeout=5000,
            )

            try:

                qwen_process = await asyncio.create_subprocess_exec(
                    str(PROJECT / ".venv" / "bin" / "python"),
                    str(qwen_script),
                    "--input",
                    str(result_dir),
                    "--output",
                    str(qwen_output),
                    cwd=str(PROJECT),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )

                qwen_lines = []

                while True:

                    line = await qwen_process.stdout.readline()

                    if not line:
                        break

===== PHOTO PROCESSING 2 =====
                    text = line.decode(
                        "utf-8",
                        errors="replace",
                    ).rstrip()

                    qwen_lines.append(text)

                    if status_label:
                        status_label.text = text[-160:]

                qwen_returncode = await qwen_process.wait()

                if qwen_returncode != 0:

                    status_label.text = (
                        "✗ Hybrid v12: ✓  "
                        "Qwen3-VL 4B: ошибка"
                    )

                    ui.notify(
                        "Hybrid завершён успешно, "
                        "но Qwen3-VL 4B завершился с ошибкой.",
                        type="negative",
                        timeout=10000,
                    )

                    return

                status_label.text = (
                    "✓ Hybrid v12 + Qwen3-VL 4B: готово"
                )

                output_input.value = str(
                    result_dir
                )

                ui.notify(
                    "✓ Полная обработка завершена: "
                    "Hybrid v12 + Qwen3-VL 4B.",
                    type="positive",
                    timeout=8000,
                )

            except Exception as qwen_error:

                status_label.text = (
                    "✗ Hybrid: ✓  "
                    "Qwen3-VL 4B: ошибка запуска"
                )

                ui.notify(
                    f"Ошибка запуска Qwen: {qwen_error}",
                    type="negative",
                    timeout=10000,
                )

        except Exception as e:

            status_label.text = (
                "✗ Ошибка запуска"
            )

            ui.notify(
                f"Ошибка запуска: {e}",
                type="negative",
                timeout=8000,
            )

        finally:

            run_button.enable()

    # ============================================================
    # UI
    # ============================================================

    with ui.card().classes("w-full"):

        ui.label(
            "ФОТООТЧЁТ"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        ui.label(
            "Источник фотографий"
        )

        with ui.row().classes(
            "w-full items-center gap-2"
        ):

            source_input

            ui.button(
                "Выбрать",
                icon="folder_open",
            ).props(
                "flat dense"
            )

        ui.label(
            "Результат"
        )

        with ui.row().classes(
            "w-full items-center gap-2"
        ):

            output_input

            ui.button(
                "Выбрать",
                icon="folder_open",
            ).props(
                "flat dense"
            )

        ui.separator().classes("my-2")

        ui.label(
            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
        ).classes(
            "text-sm"
        )

        run_button = ui.button(
            "▶  ЗАПУСТИТЬ ОБРАБОТКУ",
            on_click=run_pipeline,
        ).props(
            "unelevated"
        ).classes(
            "w-full text-lg font-bold"
        )

        status_label

        ui.label(
            "Главная рабочая операция"
        ).classes(
            "text-xs text-grey-6"
        )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:56:24

Да. Теперь видно точное место интеграции. И я бы **не трогал `run_daily_hybrid_v12.sh` и сам Hybrid/Qwen**.

У нас уже есть всё необходимое для следующего шага.

### Текущая цепочка

```text
[Кнопка ЗАПУСТИТЬ]
        │
        ▼
photo_processing.run_pipeline()
        │
        ├── run_daily_hybrid_v12.sh
        │       │
        │       └── run_hybrid_v12.py
        │
        └── qwen4b_output_v01.py
```

А новая система управления пока существует сбоку:

```text
pipeline_control
       │
       ▼
controller.py
       │
       ├── manual
       ├── automatic
       └── watcher
```

### Поэтому следующий правильный шаг

Сделать **единый `PipelineRunner`**, который будет отвечать только за фактическую обработку:

```text
PipelineRunner
    │
    ├── запуск Hybrid
    ├── получение OUTPUT
    ├── запуск Qwen
    ├── отслеживание stop_requested
    ├── корректное завершение
    └── запись состояния в pipeline_control
```

А уже кто его вызывает — неважно:

```text
MANUAL ───────┐
              │
AUTOMATIC ────┼──► PipelineRunner
              │
WATCHER ──────┘
```

Это существенно лучше, чем сейчас, потому что иначе нам пришлось бы копировать весь огромный `run_pipeline()` для автоматического режима.

---

## Но есть важный нюанс с остановкой

Сейчас:

```python
request_stop()
```

только делает:

```sql
stop_requested = TRUE
```

А `asyncio` ждёт:

```python
await process.stdout.readline()
```

пока Hybrid сам не закончится.

Поэтому нам нужно сделать остановку **между этапами и во время выполнения процесса**.

Например:

```text
Hybrid работает
     │
     ├── stop_requested = false → продолжаем
     │
     └── stop_requested = true
              ↓
       terminate Hybrid
              ↓
       terminate Qwen
              ↓
       finish_stop()
```

И при этом не оставить:

```text
running = TRUE
```

после аварийного/ручного останова.

---

# Ещё одна вещь, которую я бы поправил сейчас

В `run_daily_hybrid_v12.sh` источник жёстко задан:

```bash
INPUT="$PROJECT/data/input/daily"
```

Хотя UI уже имеет:

```text
Источник фотографий
```

То есть сейчас поле источника **фактически не управляет Hybrid**.

То же самое с `OUTPUT`: скрипт сам создаёт:

```text
data/output/daily/YYYYMMDD_HHMMSS
```

а UI только потом получает этот путь из:

```text
Output : ...
```

Это нормально для текущего ручного запуска, но для автоматизации лучше сделать так, чтобы `PipelineRunner` передавал:

```text
input_dir
```

а скрипт использовал его.

**Но это можно сделать без изменения алгоритма Hybrid.**

---

## Я предлагаю архитектуру следующего шага

Создать:

```text
app/pipeline/runner.py
```

примерно:

```text
PipelineRunner
│
├── run(input_dir)
│
├── _run_hybrid()
│
├── _run_qwen()
│
├── _check_stop()
│
└── _terminate_process()
```

А `photo_processing.py` превратить из места, где находится вся бизнес-логика, в UI:

```text
UI
 ↓
runner.run(...)
```

После этого:

### Ручной запуск

```text
Кнопка
 ↓
start_manual()
 ↓
runner.run()
 ↓
finish_stop()
```

### Автоматический

```text
scheduler
 ↓
auto_time
 ↓
start_automatic()
 ↓
runner.run()
 ↓
finish_stop()
```

### Watcher

```text
папка
 ↓
новые файлы
 ↓
start_watcher()
 ↓
runner.run()
 ↓
finish_stop()
```

---

**И самое главное:** сейчас у нас уже подтверждено, что PostgreSQL-контроллер работает. Мы проверили переход:

```text
manual
   ↓
automatic / 07:00
   ↓
manual
```

и состояние корректно сохраняется в `pipeline_control`.

Поэтому **не надо сейчас заново переделывать `modes.py` или `controller.py`**. Они уже выполняют свою роль.

Следующим изменением я бы сделал именно `app/pipeline/runner.py`, а затем подключил к нему `photo_processing.py`. Это даст нам основу, на которую потом без переделки можно навесить автоматический запуск и watcher.

---

### 👤 **User** — 2026-08-18 23:57:33

наверно выход надо сделать общим - не только daily - там должна собираться информация о фото за долгое время

---

### 🤖 **Assistant** — 2026-08-18 23:57:34

Да, **это правильнее**. Я бы сейчас зафиксировал это как архитектурное решение: `daily` — это **не хранилище**, а только текущий вход/запуск обработки.

Нам нужен **единый постоянный OUTPUT**, куда постепенно накапливается информация о фотографиях.

### Я бы разделил так

```text
data/
├── input/
│   └── daily/                 ← сюда попадают новые фото
│
├── output/
│   └── ...                    ← временные результаты конкретного запуска
│
└── metadata/
    ├── photos/
    ├── qwen/
    ├── fingerprints/
    └── ...
```

Но если мы хотим именно **долговременную базу**, то ещё лучше:

```text
                    ┌─────────────────────┐
                    │   ФОТОГРАФИИ         │
                    │   input / архив      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    PIPELINE          │
                    │ DINO → сортировка   │
                    │ Qwen → анализ        │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
        PostgreSQL         JSON/metadata       previews
        photobase          долгосрочные         миниатюры
                           результаты
```

### То есть `output` лучше не делать главным хранилищем

У нас уже есть PostgreSQL `photobase` и таблица `photos`.

И судя по `qwen_worker.py`, мы уже специально строим именно такую модель:

```text
photos.id
photo_id
source_path
filename

dino_status
qwen_status

client
brand
category
description
confidence

text_json
colors_json
objects_json
environment_json
image_quality_json
camera_view_json
analysis_quality_json
raw_json
```

Это как раз **долговременная база знаний по фотографии**.

---

## А результаты конкретного запуска можно хранить отдельно

Например:

```text
data/output/
    20260818_061500/
    20260818_093200/
    20260818_142100/
```

Каждый запуск получает свой `run_id`.

Но после обработки информация попадает в общую БД:

```text
                 RUN 20260818_061500
                         │
                         ├── photo A ──┐
                         ├── photo B ──┤
                         └── photo C ──┤
                                       ▼
                                ┌─────────────┐
                                │   photos    │
                                │ PostgreSQL   │
                                └─────────────┘
                                       ▲
                                ┌──────┴──────┐
                 RUN 20260819... │             │ RUN 20260820...
```

Таким образом **одна фотография не привязана к "daily"**.

---

### И это особенно хорошо для нашей будущей логики

Например, сегодня пришло:

```text
Иванов_01.jpg
```

DINO определил:

```text
address = 83
```

Qwen определил:

```text
brand = X
client = Y
```

Через месяц пришло другое фото того же экрана.

Мы уже можем иметь:

```text
photo #10452
2026-08-18
address 83
brand X

photo #14821
2026-09-17
address 83
brand X

photo #19274
2026-10-21
address 83
brand X
```

И потом строить:

```text
Адрес 83
   │
   ├── август
   ├── сентябрь
   ├── октябрь
   └── ...
```

То есть получается **история фотографий**, а не набор независимых `daily` запусков.

---

## Поэтому я бы сейчас немного поменял наше решение

Не делать:

```text
PipelineRunner → output/daily
```

А сделать:

```text
PipelineRunner
    │
    ├── run_id
    ├── input
    ├── processing
    │
    ├── DINO
    ├── Qwen
    │
    └── persistent storage
           │
           ├── PostgreSQL
           ├── previews
           └── raw metadata
```

А `output/20260818_...` оставить как **артефакты конкретного запуска**, которые при необходимости можно чистить или архивировать.

**И я бы вообще убрал слово `daily` из архитектуры Pipeline.** Оно описывает способ поступления фотографий сегодня, но не сущность системы.

Это хорошо согласуется с тем, что мы сейчас строим: **не "ежедневную обработку", а постоянную фотобазу, которая пополняется новыми фотографиями и накапливает историю.**

---

### 👤 **User** — 2026-08-18 23:58:06

грид берет фото из базы, а в базе хранятся данные обо всех поступивших фото

---

### 🤖 **Assistant** — 2026-08-18 23:58:06

Да. **Именно так я бы сейчас зафиксировал архитектуру.**

### Главный принцип

**База — единственный источник для Грида.**

```text
                    НОВЫЕ ФОТО
                        │
                        ▼
                 INPUT / ПАПКА
                        │
                        ▼
                 PIPELINE
          DINO → сортировка → Qwen
                        │
                        ▼
                 ┌───────────────┐
                 │   PostgreSQL  │
                 │   photobase   │
                 │               │
                 │ ВСЕ ФОТО      │
                 │ ВСЕ ДАННЫЕ    │
                 │ ВСЯ ИСТОРИЯ   │
                 └───────┬───────┘
                         │
                         ▼
                      ГРИД
```

То есть **Грид вообще не должен искать фотографии по `data/output/daily`**.

Он делает запрос к БД:

```sql
SELECT ...
FROM photos
WHERE ...
ORDER BY ...
```

и получает:

- фотографию;
- путь к оригиналу;
- адрес;
- клиента;
- дату;
- результат DINO;
- результат Qwen;
- бренд;
- категорию;
- текст;
- качество;
- и т.д.

---

## Тогда `daily` становится только входом

Например:

```text
data/input/daily/
    IMG001.jpg
    IMG002.jpg
    IMG003.jpg
```

Обработали.

После этого информация о них появляется в:

```text
photobase.photos
```

И завтра:

```text
data/input/daily/
    IMG004.jpg
    IMG005.jpg
```

Они добавляются **в ту же таблицу `photos`**.

В результате:

```text
photos
────────────────────────────────────────
id   photo_id   date        address ...
1    ...        18.08.26    78
2    ...        18.08.26    83
3    ...        18.08.26    91
4    ...        19.08.26    78
5    ...        19.08.26    83
...
50000 ...
```

А Грид видит всё это как **единую фотобазу**.

---

## И это хорошо совпадает с нашей текущей БД

В `qwen_worker.py` уже есть правильная концепция:

```text
photos.id
photo_id
source_path
filename
```

и дальше результаты обработки:

```text
dino_status
qwen_status

client
brand
category
description
confidence

text_json
colors_json
objects_json
environment_json
image_quality_json
camera_view_json
analysis_quality_json
raw_json
```

То есть **мы уже фактически строим именно эту модель**.

---

### А `output` тогда нужен только для технических результатов

Например:

```text
data/output/
    20260818_120001/
        ...
    20260818_153422/
        ...
```

Это не источник Грида.

Можно даже позже сделать:

```text
data/runs/
    20260818_120001/
    20260818_153422/
```

и хранить там:

- лог запуска;
- список обработанных файлов;
- ошибки;
- промежуточные результаты;
- отчёт.

А **постоянные данные — в PostgreSQL**.

---

## Это также решает вопрос виртуального Грида

То, о чём мы говорили раньше:

> можно файлы сохранять даже в input — работать с ними на виртуальном уровне

Да.

Грид может вообще **не загружать все фотографии в память**.

Например:

```text
БД
 ↓
запрос 50 записей
 ↓
Грид показывает 50
 ↓
прокрутка
 ↓
следующие 50
```

Это уже виртуализация.

И главное — настройки отображения могут зависеть от пользователя:

```text
Пользователь
    ↓
его настройки
    ↓
SQL-фильтр
    ↓
БД
    ↓
Грид
```

То есть твоя предыдущая идея:

> **грид сразу начинает отображать фото, а настройки берёт из положения чекбоксов, которые зависят от выбранного пользователя**

отлично ложится на эту архитектуру.

---

### Поэтому я бы сейчас зафиксировал 4 правила

**1. PostgreSQL `photos` — главный реестр всех поступивших фотографий.**

**2. Грид читает фотографии только через БД.**

**3. `input/daily` — временная точка поступления новых фотографий, а не база.**

**4. `output` — артефакты конкретных запусков, а не источник данных Грида.**

И тогда следующий `PipelineRunner` должен в конце не просто сказать **«Hybrid + Qwen завершены»**, а обеспечить:

```text
новые фото
   ↓
обработка
   ↓
запись/обновление photos
   ↓
готово
   ↓
Грид автоматически видит новые записи
```

**Вот эту схему я бы и взял за основу дальнейшей работы.**

---

### 👤 **User** — 2026-08-19 00:00:24

и по факту будет не daily. а каталог вида: месяц - 01 число - фото 1,2,3 и т.д, 02 число - фото 1,2,3 и т.д. в базе будет инфа о уже проверыенных и нужно будет искать новые пропуская сделанные

---

### 🤖 **Assistant** — 2026-08-19 00:00:25

Да. Тогда `daily` действительно лучше убрать из логики. У нас получается **постоянный фотокаталог + база состояния обработки**.

### Физическая структура архива

Например:

```text
ФОТОАРХИВ/
├── 2026-08/
│   ├── 01/
│   │   ├── 001.jpg
│   │   ├── 002.jpg
│   │   ├── 003.jpg
│   │   └── ...
│   ├── 02/
│   │   ├── 001.jpg
│   │   ├── 002.jpg
│   │   └── ...
│   ├── 03/
│   └── ...
├── 2026-09/
│   ├── 01/
│   ├── 02/
│   └── ...
└── ...
```

При этом **имя и физическое расположение файла не являются главным идентификатором**. Главный реестр — PostgreSQL.

---

## Что происходит при новом запуске

Не:

```text
взяли сегодняшние фото
→ обработали всё
```

А:

```text
                ФОТОАРХИВ
                    │
                    ▼
              СКАНИРОВАНИЕ
                    │
                    ▼
           сравнение с photos
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
     уже есть в БД        нет в БД
          │                   │
       пропустить             ▼
                         обработать
                              │
                              ▼
                         записать в БД
```

То есть обработчик можно запускать хоть 10 раз подряд — **уже обработанные фотографии повторно не гоняем**.

---

## Что хранить в `photos`

Минимально я бы обязательно имел:

```text
id
photo_id
source_path
filename

captured_at
archive_month
archive_day

dino_status
qwen_status

dino_result / address_id
qwen_result
...
```

Но самое важное — способ определения:

> **«Эта фотография уже была обработана?»**

Лучше не полагаться только на имя файла.

Например:

```text
photo_id
```

может быть стабильным ID, а дополнительно:

```text
file_size
mtime
sha256
```

или другой fingerprint файла.

Тогда если фотографию случайно переименовали:

```text
IMG001.jpg
```

→

```text
IMG001_новая.jpg
```

мы всё равно понимаем:

**это уже известная фотография.**

---

## Причём здесь очень удобно разделить состояния

Например:

```text
photo
 │
 ├── найдено
 │
 ├── DINO обработан
 │
 ├── адрес определён
 │
 ├── Qwen обработан
 │
 └── полностью готово
```

Поэтому база сможет отвечать на вопросы:

```text
Какие фото вообще есть?
Какие новые?
Какие уже проверены DINO?
Какие не проверены?
Какие требуют Qwen?
Какие завершены?
Какие упали с ошибкой?
```

---

# И тогда автоматизация становится намного проще

Watcher обнаружил новые файлы:

```text
2026-08/19/
    001.jpg
    002.jpg
    003.jpg
```

Pipeline делает:

```text
SCAN
 ↓
сравнение с PostgreSQL
 ↓
001 → уже есть → SKIP
002 → уже есть → SKIP
003 → новая → QUEUE
```

Обрабатывается только:

```text
003.jpg
```

После обработки:

```text
photos
────────────────────────────
photo_id   status
001        done
002        done
003        done
```

При следующем запуске:

```text
001 → skip
002 → skip
003 → skip
004 → process
```

---

## И я бы сделал ещё лучше

Не привязывать Pipeline к слову **daily** вообще.

Например:

```text
app/pipeline/
    controller.py
    modes.py
    runner.py
    scanner.py
    queue.py
    recovery.py
```

### `scanner.py`

Отвечает только за:

> найти новые фотографии в архиве.

### `queue.py`

Отвечает:

> какие фотографии надо обработать.

### `runner.py`

Отвечает:

> DINO → сортировка → Qwen → запись результата.

### `controller.py`

Отвечает:

> когда запускать.

Получаем:

```text
                    CONTROLLER
                         │
              ┌──────────┼──────────┐
              │          │          │
            MANUAL    AUTOMATIC   WATCHER
              │          │          │
              └──────────┼──────────┘
                         ▼
                       SCANNER
                         │
                   новые фото?
                         │
                         ▼
                       QUEUE
                         │
                         ▼
                      RUNNER
                  ┌──────┴──────┐
                  ▼             ▼
                 DINO          QWEN
                  │             │
                  └──────┬──────┘
                         ▼
                    PostgreSQL
                         │
                         ▼
                       GRID
```

**Вот это уже, на мой взгляд, правильная конечная архитектура проекта.**

И тогда автоматический режим в 06:00 будет означать не «обработать `daily`», а **«просканировать весь каталог и обработать только то, чего ещё нет/что не завершено в БД»**.

Watcher будет делать то же самое, только не по расписанию, а при появлении новых файлов.

---

### 👤 **User** — 2026-08-19 00:01:06

да

---

### 🤖 **Assistant** — 2026-08-19 00:01:10

Да. Тогда **`daily` как основная концепция нам больше не нужен**. Правильнее сейчас перестроить модель вокруг **единого постоянного фотокаталога + PostgreSQL как источника истины**.

### Как я бы зафиксировал архитектуру

```text
ВХОДЯЩИЕ ФОТО
    │
    ▼
┌──────────────────────────┐
│ Постоянный каталог       │
│                          │
│ 2026-08/                 │
│   01/                    │
│      photo_001.jpg       │
│      photo_002.jpg       │
│   02/                    │
│      photo_001.jpg       │
│      photo_002.jpg       │
│   03/                    │
│      ...                 │
│                          │
│ 2026-09/                 │
│   ...                    │
└────────────┬─────────────┘
             │
             ▼
      PostgreSQL
      photobase
             │
      ┌──────┴──────┐
      ▼             ▼
   DINO v33       Qwen 4B
      │             │
      └──────┬──────┘
             ▼
        данные фото
             │
             ▼
          ГРИД
```

### Главное изменение

**Файл на диске становится постоянным объектом каталога**, а не результатом конкретного запуска.

В БД для каждой фотографии примерно:

```text
photo
├── id
├── photo_id
├── source_path
├── filename
├── date
├── month
├── day
│
├── dino_status
├── dino_result
│
├── qwen_status
├── qwen_result
│
├── address_id
├── client
├── brand
├── ...
│
├── created_at
└── updated_at
```

И тогда обработчик работает не так:

```text
запустили daily
→ обработали всё из daily
→ создали новый output
```

а так:

```text
нашли входящие фотографии
        ↓
сравнили с БД
        ↓
уже есть photo_id?
    │           │
   ДА          НЕТ
    │           │
пропустить     добавить
                  │
                  ▼
             обработать
```

### Что это даст

Например, в каталог сегодня попало:

```text
2026-08/
    18/
        001.jpg
        002.jpg
        003.jpg
```

Завтра пришло:

```text
2026-08/
    18/
        001.jpg
        002.jpg
        003.jpg
        004.jpg
        005.jpg
```

Система видит:

```text
001 → уже есть → SKIP
002 → уже есть → SKIP
003 → уже есть → SKIP
004 → новая → DINO
005 → новая → DINO
```

А если Qwen для `003` ещё не был выполнен:

```text
DINO = done
QWEN = pending
```

то он **не будет заново гонять DINO**, а Qwen спокойно заберёт эту фотографию отдельно.

Это очень хорошо согласуется с уже существующей у нас схемой:

```text
dino_status
    pending
    processing
    done
    error

qwen_status
    pending
    processing
    done
    error
```

и с `recovery.py`.

---

## А грид действительно должен смотреть только БД

Это важный момент.

**Грид вообще не должен сканировать файловую систему в поисках фотографий.**

Он делает:

```text
PostgreSQL
    ↓
SELECT фотографии по фильтрам
    ↓
source_path / preview_path
    ↓
Grid
```

Поэтому:

- новый файл появился → его сначала регистрируем в БД;
- DINO распознал → обновили запись;
- Qwen проанализировал → обновили запись;
- пользователь выбрал клиента → SQL-фильтр;
- выбрал месяц → SQL-фильтр;
- выбрал число → SQL-фильтр;
- выбрал адрес → SQL-фильтр.

Именно это позволит потом сделать **виртуальный грид** без загрузки тысяч фотографий сразу.

---

# Я бы сейчас разделил систему на 4 независимых этапа

### 1. INGEST — принять фотографии

```text
incoming/
    ↓
проверка
    ↓
вычисление уникального идентификатора
    ↓
копирование в постоянный каталог
    ↓
INSERT в photos
```

Например:

```text
catalog/
├── 2026-08/
│   ├── 18/
│   │   ├── 001.jpg
│   │   ├── 002.jpg
│   │   └── ...
│   └── 19/
│       └── ...
└── 2026-09/
```

---

### 2. DINO

Берёт:

```sql
WHERE dino_status = 'pending'
```

и работает **только с новыми/необработанными фотографиями**.

---

### 3. Qwen

Независимо берёт:

```sql
WHERE qwen_status = 'pending'
```

То есть DINO и Qwen не обязаны идти строго последовательно.

---

### 4. GRID

Только читает:

```text
PostgreSQL → Grid
```

---

## И тогда автоматический режим становится очень простым

Вместо:

> «Запустить Daily Hybrid v12»

будет:

> **Автоматическая обработка**

Например:

```text
Автоматическая обработка       ☑

Время запуска:                 06:00

Источник новых фотографий:     [........]

Каталог:                       [........]

Если компьютер был выключен:
○ Запустить при следующем включении
○ Пропустить пропущенный запуск
```

А внутри:

```text
06:00
 ↓
INGEST
 ↓
найти новые фото
 ↓
зарегистрировать
 ↓
DINO pending
 ↓
Qwen pending
```

И всё.

---

### И самое важное

Я бы **не удалял пока `run_daily_hybrid_v12.sh` и старую цепочку**.

Мы сначала построим новый постоянный каталог и INGEST поверх существующей БД, проверим его на копии нескольких дней, и только потом заменим:

```text
PHOTO PROCESSING
DINO v33 → Hybrid v12 → Qwen
```

на новую архитектуру:

```text
ФОТОКАТАЛОГ
    ↓
INGEST
    ↓
QUEUE
    ├── DINO
    └── Qwen
    ↓
POSTGRES
    ↓
GRID
```

**Это уже будет не `daily`, а постоянная фотобаза.**

И я считаю, что это сейчас правильное направление: существующие `pipeline_control`, `queue`, `recovery`, `dino_status/qwen_status` и грид как раз позволяют перейти к нему без переписывания всего проекта с нуля.

---

### 👤 **User** — 2026-08-19 00:01:36

далее

---

