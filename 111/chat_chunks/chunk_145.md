## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 👤 **User** — 2026-08-19 00:08:04

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== CONTROLLER ====="
cat app/pipeline/controller.py

echo
echo "===== DINO WORKER ====="
sed -n '1,460p' app/workers/dino_worker.py

echo
echo "===== PHOTO INGEST ====="
cat scripts/photo_ingest.py

echo
echo "===== SORT STATUS REFERENCES ====="
grep -RniE \
'sort_status|hybrid_final_id|hybrid_original_id|hybrid_score|hybrid_margin|hybrid_neighbors' \
app scripts \
--include="*.py" | head -250

echo
echo "===== PREVIEW REFERENCES ====="
grep -RniE \
--include="*.py" | head -250|create_previews|preview' \
===== CONTROLLER =====
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

===== DINO WORKER =====
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

===== PHOTO INGEST =====
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg2

PROJECT = Path(__file__).resolve().parent.parent

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

# ============================================================
# ID
# ============================================================

def get_next_photo_number(conn):
    """
    Следующий постоянный PHOTO_ID.

    PH_00000001
    PH_00000002
    ...
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT photo_id
            FROM photos
            WHERE photo_id LIKE 'PH_%'
            """
        )

        rows = cur.fetchall()

    max_number = 0

    for (photo_id,) in rows:

        if not photo_id:
            continue

        value = str(photo_id)

        if not value.startswith("PH_"):
            continue

        try:
            number = int(
                value[3:]
            )
        except ValueError:
            continue

        max_number = max(
            max_number,
            number,
        )

    return max_number + 1

def get_next_initial_number(conn):
    """
    Следующий внутренний INITIAL_ID.

    IN_00000001
    IN_00000002
    ...

    INITIAL_ID не зависит от адреса,
    DINO и Qwen.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT initial_id
            FROM photos
            WHERE initial_id LIKE 'IN_%'
            """
        )

        rows = cur.fetchall()

    max_number = 0

    for (initial_id,) in rows:

        if not initial_id:
            continue

        value = str(initial_id)

        if not value.startswith("IN_"):
            continue

        try:
            number = int(
                value[3:]
            )
        except ValueError:
            continue

        max_number = max(
            max_number,
            number,
        )

    return max_number + 1

def make_photo_id(number):
    return f"PH_{number:08d}"

def make_initial_id(number):
    return f"IN_{number:08d}"

# ============================================================
# PATHS
# ============================================================

def normalize_path(path):
    return str(
        Path(path)
        .expanduser()
        .resolve()
    )

def get_existing_source_paths(conn):
    """
    Уже зарегистрированные source_path.

    Используется для безопасного продолжения
    после прерывания ingest.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT source_path
            FROM photos
            WHERE source_path IS NOT NULL
              AND source_path <> ''
            """
        )

        return {
            normalize_path(row[0])
            for row in cur.fetchall()
            if row[0]
        }

def find_images(input_dir):
    """
    Сканирует только файлы непосредственно
    во входной папке.

    Подкаталоги пока не трогаем.
    """

    return sorted(
        (
            p
            for p in input_dir.iterdir()
            if (
                p.is_file()
                and p.suffix.lower()
                in IMAGE_EXTENSIONS
            )
        ),
        key=lambda p: p.name.casefold(),
    )

# ============================================================
# REGISTER
# ============================================================

def register_photo(
    conn,
    photo_id,
    initial_id,
    source_path,
):
    """
    Создаёт единую первичную запись фотографии.

    На этом этапе НЕ происходит:

        - DINO
        - Qwen
        - сортировка
        - определение адреса
        - создание превью

    Здесь только создаётся объект PHOTО.
    """

    source = Path(source_path)

    filename = source.name

    with conn.cursor() as cur:

        cur.execute(
            """
            INSERT INTO photos (
                photo_id,
                initial_id,

                source_path,
                path,

                filename,
                original_filename,

                status,

                dino_status,
                qwen_status,
                sort_status,
                preview_status
            )
            VALUES (
                %s,
                %s,

                %s,
                %s,

                %s,
                %s,

                'pending',

                'pending',
                'pending',
                'pending',
                'pending'
            )
            """,
            (
                photo_id,
                initial_id,

                source_path,
                source_path,

                filename,
                filename,
            ),
        )

# ============================================================
# INGEST
# ============================================================

def ingest(input_dir):

    input_dir = (
        input_dir
        .expanduser()
        .resolve()
    )

    if not input_dir.exists():

        raise RuntimeError(
            "Input directory does not exist:\n"
            f"{input_dir}"
        )

    if not input_dir.is_dir():

        raise RuntimeError(
            "Input path is not a directory:\n"
            f"{input_dir}"
        )

    images = find_images(
        input_dir
    )

    print("=" * 80)
    print("PHOTO INGEST")
    print("=" * 80)
    print()
    print("INPUT :", input_dir)
    print("FILES :", len(images))
    print()

    if not images:

        print(
            "No images found."
        )

        return

    with psycopg2.connect(
        **DB_CONFIG
    ) as conn:

        # ----------------------------------------------------
        # Existing
        # ----------------------------------------------------

        existing_paths = (
            get_existing_source_paths(
                conn
            )
        )

        # ----------------------------------------------------
        # Next IDs
        # ----------------------------------------------------

        next_photo_number = (
            get_next_photo_number(
                conn
            )
        )

        next_initial_number = (
            get_next_initial_number(
                conn
            )
        )

        registered = 0
        skipped = 0

        # ----------------------------------------------------
        # REGISTER
        # ----------------------------------------------------

        for image in images:

            source_path = (
                normalize_path(
                    image
                )
            )

            # -----------------------------------------------
            # Already registered
            # -----------------------------------------------

            if source_path in existing_paths:

                print(
                    f"[SKIP]      {image.name}"
                    " — already registered"
                )

                skipped += 1

                continue

            # -----------------------------------------------
            # Create IDs
            # -----------------------------------------------

            photo_id = make_photo_id(
                next_photo_number
            )

            initial_id = make_initial_id(
                next_initial_number
            )

            # -----------------------------------------------
            # DB record
            # -----------------------------------------------

            register_photo(
                conn,
                photo_id,
                initial_id,
                source_path,
            )

            existing_paths.add(
                source_path
            )

            print(
                f"[REGISTER] "
                f"{photo_id}"
                f" | initial={initial_id}"
                f" | {image.name}"
            )

            registered += 1

            next_photo_number += 1
            next_initial_number += 1

        conn.commit()

    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("=" * 80)
    print("INGEST FINISHED")
    print("=" * 80)
    print()

    print(
        "Found      :",
        len(images),
    )

    print(
        "Registered :",
        registered,
    )

    print(
        "Skipped    :",
        skipped,
    )

    print()

    print(
        "New photos are now available to:"
    )

    print(
        "  DINO : dino_status = pending"
    )

    print(
        "  QWEN : qwen_status = pending"
    )

    print()

    print(
        "No address has been assigned yet."
    )

# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Register new photos, "
            "assign photo_id and initial_id, "
            "and put them into independent "
            "DINO/Qwen queues."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help=(
            "Directory with incoming photos"
        ),
    )

    args = parser.parse_args()

    ingest(
        args.input
    )

if __name__ == "__main__":
    main()

===== SORT STATUS REFERENCES =====
scripts/photo_ingest.py:249:                sort_status,
scripts/run_hybrid_v12.py:373:        result["hybrid_score"] = new_score
scripts/run_hybrid_v12.py:375:        result["hybrid_margin"] = margin
scripts/run_hybrid_v12.py:376:        result["hybrid_neighbors"] = dict(neighbors)
scripts/run_hybrid_v12.py:481:                "hybrid_score": item.get(
scripts/run_hybrid_v12.py:482:                    "hybrid_score"

===== PREVIEW REFERENCES =====
app/web/components/photos.py:13:# PHOTO PREVIEWS
app/web/components/photos.py:16:PREVIEW_ROOT = (
app/web/components/photos.py:19:    / "preview"
app/web/components/photos.py:51:def get_latest_preview_root():
app/web/components/photos.py:52:    """Return the newest daily preview directory."""
app/web/components/photos.py:53:    if not PREVIEW_ROOT.exists():
app/web/components/photos.py:58:        for path in PREVIEW_ROOT.iterdir()
app/web/components/photos.py:71:def get_preview_path(photo_path):
app/web/components/photos.py:72:    """Map daily output photo to its preview image."""
app/web/components/photos.py:73:    preview_root = get_latest_preview_root()
app/web/components/photos.py:76:    if preview_root is None or daily_root is None:
app/web/components/photos.py:84:    preview_path = preview_root / relative
app/web/components/photos.py:86:    if preview_path.exists():
app/web/components/photos.py:87:        return preview_path
app/web/components/photos.py:1148:                                    # В ГРИДЕ показываем PREVIEW.
app/web/components/photos.py:1151:                                    preview_path = (
app/web/components/photos.py:1152:                                        get_preview_path(
app/web/components/photos.py:1158:                                        preview_path
app/web/components/photos.py:1159:                                        if preview_path
app/web/photo_db.py:25:            preview_path,
scripts/create_previews_v01.py:19:def create_preview(source: Path, destination: Path):
scripts/create_previews_v01.py:48:        description="Create web previews for processed photos"
scripts/create_previews_v01.py:60:        help="Preview output directory",
scripts/create_previews_v01.py:84:    print("PHOTO PREVIEW WORKER V01")
scripts/create_previews_v01.py:109:            result = create_preview(
scripts/create_previews_v01.py:139:    print("PREVIEW FINISHED")
scripts/photo_ingest.py:250:                preview_status
scripts/qwen_prompt_ablation.py:202:        print("ANSWER PREVIEW:")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 00:08:07

Да. Теперь картина уже достаточно ясная. **Главное — мы нашли место, где старая архитектура `daily` ещё сидит в UI, а новая архитектура БД уже фактически готова.**

### Что сейчас уже правильно

`photos` уже является постоянным каталогом:

```text
photo_id
initial_id
source_path
filename
original_filename

dino_status
qwen_status
sort_status
preview_status

address_id
dino_*
hybrid_*
qwen_*
preview_path
created_at
updated_at
```

То есть **пересчитывать саму БД концептуально не нужно**. Нужно изменить способ её наполнения и обработки.

---

## Что сейчас мешает

### 1. Ingest пока смотрит только один уровень

Сейчас:

```python
input_dir.iterdir()
```

Поэтому:

```text
input/
├── 01/
│   ├── a.jpg
│   └── b.jpg
├── 02/
│   ├── c.jpg
│   └── d.jpg
```

не будет найдено.

Но мы это **пока не трогаем**, как договорились.

---

### 2. DINO уже практически является правильным постоянным worker

Вот это очень хорошо:

```sql
WHERE dino_status = 'pending'
```

и:

```sql
FOR UPDATE SKIP LOCKED
```

То есть DINO уже работает по принципу:

> «Дай мне следующую фотографию, которая ещё не обработана».

Ему вообще не нужен `daily`.

После обработки:

```text
dino_status = done
address_id = ...
dino_score = ...
dino_margin = ...
```

И повторно эта фотография не берётся.

**Это именно та модель, которая нам нужна.**

---

### 3. Qwen сделан по той же правильной модели

Мы уже видели:

```sql
WHERE qwen_status = 'pending'
```

То есть Qwen также независим:

```text
photo
  ↓
qwen_status=pending
  ↓
Qwen
  ↓
qwen_status=done
```

И он не обязан знать, когда фотография поступила — сегодня или три месяца назад.

---

# А вот SORT сейчас ещё старый

Это видно очень хорошо:

```text
scripts/run_hybrid_v12.py
```

работает с результатом запуска:

```text
data/output/daily/20260816_230042
```

а затем считает Hybrid для этого набора.

То есть сейчас у нас две разные философии:

```text
DINO worker
    ↓
постоянная БД
    ↓
pending → processing → done
```

и:

```text
Hybrid v12
    ↓
взяли daily-папку
    ↓
обработали запуск целиком
    ↓
создали output/daily/TIMESTAMP
```

**Вот это и надо будет устранить.**

---

# И preview сейчас тоже привязан к daily

Особенно показательно:

```python
def get_latest_preview_root():
    """Return the newest daily preview directory."""
```

и:

```python
def get_preview_path(photo_path):
    """Map daily output photo to its preview image."""
```

То есть Grid сейчас фактически говорит:

> «Найди последний daily output и возьми оттуда preview».

А нам нужно:

> «У этой записи `photos.photo_id = PH_00000526` есть `preview_path`. Покажи его».

Это принципиально важное изменение.

---

# Целевая архитектура

Я бы сейчас зафиксировал её именно так:

```text
                    INPUT
                      │
                      │ ingest
                      ▼
              ┌─────────────────┐
              │   PostgreSQL     │
              │     photos       │
              └────────┬────────┘
                       │
          ┌────────────┼─────────────┐
          │            │             │
          ▼            ▼             ▼
       DINO          SORT          QWEN
       worker        worker        worker
          │            │             │
          └────────────┼─────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   PostgreSQL    │
              │ результаты      │
              └────────┬────────┘
                       │
                       ▼
                     GRID
```

А физически:

```text
data/input/
│
├── 2026-08/
│   ├── 01/
│   │   ├── photo1.jpg
│   │   ├── photo2.jpg
│   │   └── ...
│   ├── 02/
│   ├── 03/
│   └── ...
│
├── 2026-09/
│   ├── 01/
│   └── ...
│
└── ...
```

**Input остаётся архивом исходных фотографий.**

---

# И самое важное — Grid

Grid вообще не должен думать о `daily`.

Он делает примерно:

```sql
SELECT ...
FROM photos
WHERE ...
ORDER BY ...
```

и получает:

```text
PH_00000526
source_path = .../2026-08/18/Шолохова 127 А (9).JPG
preview_path = ...
address_id = ...
client = ...
brand = ...
...
```

То есть **фотография существует в системе независимо от запуска обработки**.

---

# Что делать с `output`

Вот здесь я бы предложил важное решение.

Не делать:

```text
output/
└── daily/
    ├── 20260818_...
    ├── 20260819_...
    └── ...
```

как основное хранилище.

Вместо этого:

```text
data/
├── input/
│   └── постоянный архив исходников
│
├── catalog/
│   ├── previews/
│   ├── metadata/
│   └── ...
│
├── fingerprints/
└── ...
```

А **результаты обработки хранить прежде всего в PostgreSQL**.

При необходимости физические файлы:

```text
catalog/previews/PH_00000526.webp
catalog/previews/PH_00000527.webp
...
```

И в БД:

```text
preview_path
```

---

# Ещё одно важное следствие

Тогда кнопка:

> **ЗАПУСТИТЬ ОБРАБОТКУ**

больше не должна означать:

> «запусти `run_daily_hybrid_v12.sh`».

Она должна означать:

> **«обработай очередь новых/необработанных фотографий»**.

Например:

```text
Найдено в input:       12 540
В базе:                12 500
Новых:                    40

DINO:
pending                  40
processing                0
done                  12 460

Qwen:
pending                   40
done                   ...
```

И запуск обработает именно эти 40.

---

## Поэтому я предлагаю следующий шаг

**Пока ничего не менять.**

Следующим посмотрим именно:

```bash
sed -n '1,560p' scripts/run_hybrid_v12.py
```

и затем:

```bash
sed -n '1,180p' app/web/components/photos.py
sed -n '1120,1180p' app/web/components/photos.py
```

Нам нужно понять две вещи:

1. **как сейчас Hybrid использует DINO-результаты и соседние фотографии** — это особенно важно, потому что мы уже решили, что соседняя логика должна сохраниться;
2. **как Grid сейчас получает фотографии и preview**.

После этого уже можно будет точно сказать, **какие 2–3 места переписываем, а какие вообще не трогаем**.

---

### 👤 **User** — 2026-08-19 00:09:14

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '1,560p' scripts/run_hybrid_v12.py
#!/usr/bin/env python3

import argparse
import json
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder

PROJECT = Path(__file__).resolve().parent.parent

SUB_DIR = PROJECT / "data/fingerprints_sub_exp"

# ============================================================
# HYBRID V12 — FROZEN CONTROL LOGIC
# ============================================================

MARGIN_LIMIT = 0.02

GLOBAL_WEIGHT = 10.0
SUB_WEIGHT = 2.5
NEIGHBOR_WEIGHT = 6.0

def normalize(x):
    x = np.asarray(x, dtype=np.float32)

    n = np.linalg.norm(x)

    if n > 0:
        x = x / n

    return x

def load_subs():
    result = {}

    if not SUB_DIR.exists():
        print(f"[Hybrid] WARNING: sub directory not found: {SUB_DIR}")
        return result

    for d in sorted(SUB_DIR.iterdir()):

        if not d.is_dir():
            continue

        f = d / "embeddings.npy"

        if not f.exists():
            continue

        emb = np.load(f)

        emb = np.array(
            [
                normalize(x)
                for x in emb
            ],
            dtype=np.float32,
        )

        result[d.name] = emb

    return result

def get_neighbor_votes(rows, index):
    votes = Counter()

    if index <= 0:
        return votes

    if index >= len(rows) - 1:
        return votes

    left = rows[index - 1]["top1"]
    right = rows[index + 1]["top1"]

    # FROZEN V12 RULE:
    # only complete agreement
    if left == right:
        votes[left] = 1

    return votes

def run_recognition(input_dir, fingerprints):
    """
    Run the existing DINO v33 recognizer.

    The recognizer itself is NOT modified.
    """

    fp_arg = ",".join(fingerprints)

    cmd = [
        "uv",
        "run",
        "scene-fingerprint",
        "recognize",
        str(input_dir),
        "--top-k",
        "5",
        "--threshold",
        "0.0",
        "--fingerprints",
        fp_arg,
        "--json",
    ]

    print("=" * 80)
    print("DINO v33 RECOGNITION")
    print("=" * 80)
    print("Input:", input_dir)
    print("Fingerprints:", ", ".join(fingerprints))
    print()

    start = time.perf_counter()

    process = subprocess.run(
        cmd,
        cwd=PROJECT,
        capture_output=True,
        text=True,
    )

    elapsed = time.perf_counter() - start

    if process.returncode != 0:
        print(process.stdout)
        print(process.stderr)

        raise RuntimeError(
            f"recognize завершился с кодом {process.returncode}"
        )

    combined = process.stdout + "\n" + process.stderr

    decoder = json.JSONDecoder()
    data = None

    for i, ch in enumerate(combined):

        if ch != "[":
            continue

        try:
            candidate, _ = decoder.raw_decode(
                combined[i:]
            )

            if isinstance(candidate, list):
                data = candidate
                break

        except json.JSONDecodeError:
            pass

    if data is None:
        raise RuntimeError(
            "Не удалось найти JSON-массив в выводе recognition"
        )

    print("Images:", len(data))
    print(f"Recognition time: {elapsed:.2f} sec")

    return data, elapsed

def adapt_recognizer_rows(rows):
    """
    Convert current recognizer output into the legacy
    top1..top5 format required by frozen Hybrid v12.
    """

    adapted = []

    for row in rows:
        item = dict(row)

        candidates = row.get("candidates", [])

        for n in range(1, 6):
            item[f"top{n}"] = None
            item[f"top{n}_score"] = 0.0

        for n, candidate in enumerate(candidates[:5], start=1):
            item[f"top{n}"] = candidate.get("id")
            item[f"top{n}_score"] = float(
                candidate.get("score", 0.0)
            )

        adapted.append(item)

    return adapted

def hybrid_v12(rows, embedder, subs):
    """
    Exact production adaptation of the frozen Hybrid v12 logic.

    Input:
        recognizer rows containing top1..top5.

    Output:
        rows with final best_id.
    """

    changed = []
    results = []
    sub_count = 0

    for i, row in enumerate(rows):

        old = row.get("top1")

        scores = defaultdict(float)

        # ====================================================
        # GLOBAL TOP-5
        # ====================================================

        for k in range(1, 6):

            fp = row.get(f"top{k}")
            sc = row.get(f"top{k}_score")

            if fp:
                scores[fp] += (
                    float(sc)
                    * GLOBAL_WEIGHT
                )

        # ====================================================
        # SUB ONLY BORDER CASES
        # ====================================================

        margin = row.get(
            "margin",
            1,
        )

        if margin < MARGIN_LIMIT:

            sub_count += 1

            image = Path(
                row["file"]
            )

            query = embedder.embed_paths(
                [image]
            )[0]

            query = normalize(query)

            # FROZEN V12:
            # only TOP1 and TOP2
            candidates = [
                row.get("top1"),
                row.get("top2"),
            ]

            for parent in candidates:

                if not parent:
                    continue

                for sub_id, sub_emb in subs.items():

                    if not sub_id.startswith(parent):
                        continue

                    sim = max(
                        sub_emb @ query
                    )

                    if sim > 0.88:

                        if sim > 0.92:
                            bonus = 2.5
                        else:
                            bonus = 1.0

                        scores[parent] += (
                            float(sim)
                            * bonus
                        )

        # ====================================================
        # SEQUENCE CONSENSUS
        # ====================================================

        neighbors = get_neighbor_votes(
            rows,
            i,
        )

        left_fp = None
        right_fp = None

        if i > 0:
            left_fp = rows[i - 1].get("top1")

        if i < len(rows) - 1:
            right_fp = rows[i + 1].get("top1")

        if (
            left_fp
            and right_fp
            and left_fp == right_fp
        ):
            # FROZEN V12:
            # actual implementation uses +3.0
            scores[left_fp] += 3.0

        # ====================================================
        # FINAL DECISION V12
        # ====================================================

        best = old

        ranked = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        if ranked:

            candidate = ranked[0][0]

            gain = (
                scores[candidate]
                - scores.get(old, 0)
            )

            if (
                candidate != old
                and gain > 1.5
            ):
                best = candidate

        old_score = scores.get(
            old,
            0,
        )

        new_score = scores.get(
            best,
            0,
        )

        hybrid_changed = best != old

        result = dict(row)

        result["original_best_id"] = old
        result["best_id"] = best

        result["hybrid_changed"] = hybrid_changed

        result["hybrid_old_score"] = old_score
        result["hybrid_score"] = new_score

        result["hybrid_margin"] = margin
        result["hybrid_neighbors"] = dict(neighbors)

        results.append(result)

        if (
            best != old
            and new_score > old_score
        ):
            changed.append(
                {
                    "file": Path(
                        row["file"]
                    ).name,
                    "old": old,
                    "new": best,
                    "margin": margin,
                    "neighbors": dict(neighbors),
                    "old_score": scores[old],
                    "new_score": scores[best],
                }
            )

    return results, changed, sub_count

def sort_results(rows, output_dir):
    """
    Copy photos according to FINAL Hybrid best_id.
    """

    print()
    print("=" * 80)
    print("SORTING")
    print("=" * 80)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    counters = Counter()
    sorted_rows = []

    for item in rows:

        source = Path(
            item["file"]
        )

        assigned_id = item.get(
            "best_id"
        )

        if not assigned_id:
            continue

        destination_dir = (
            output_dir / assigned_id
        )

        destination_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            destination_dir / source.name
        )

        shutil.copy2(
            source,
            destination,
        )

        counters[assigned_id] += 1

        sorted_rows.append(
            {
                "file": str(source),
                "filename": source.name,
                "assigned_id": assigned_id,
                "original_best_id": item.get(
                    "original_best_id"
                ),
                "hybrid_changed": item.get(
                    "hybrid_changed"
                ),
                "score": item.get("score"),
                "second_score": item.get(
                    "second_score"
                ),
                "margin": item.get("margin"),
                "confidence": item.get(
                    "confidence"
                ),
                "status": item.get("status"),
                "best_image": item.get(
                    "best_image"
                ),
                "best_image_score": item.get(
                    "best_image_score"
                ),
                "hybrid_old_score": item.get(
                    "hybrid_old_score"
                ),
                "hybrid_score": item.get(
                    "hybrid_score"
                ),
            }
        )

    for k in sorted(
        counters,
        key=lambda x: int(
            x.split("_")[0]
        ),
    ):
        print(
            f"{k:10s} {counters[k]:4d}"
        )

    return sorted_rows, counters

def main():

    parser = argparse.ArgumentParser(
        description="Production runner for frozen Hybrid v12"
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--first-address",
        type=int,
        default=78,
    )

    parser.add_argument(
        "--last-address",
        type=int,
        default=95,
    )

    args = parser.parse_args()

    input_dir = args.input
    output_dir = args.output

    if not input_dir.exists():
        raise RuntimeError(
            f"Нет папки: {input_dir}"
        )

    fingerprints = [
        f"{i}_v33"
        for i in range(
            args.first_address,
            args.last_address + 1,
        )
    ]

    print()
    print("=" * 80)
    print("SCENE FINGERPRINT — HYBRID V12 RUNNER")
    print("=" * 80)
    print()
    print("INPUT :", input_dir)
    print("OUTPUT:", output_dir)
    print()
    print("CONTROL:")
    print("  DINO        : v33")
    print("  HYBRID      : v12")
    print("  ADDRESSES   :", f"{args.first_address}-{args.last_address}")
    print()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '1,180p' app/web/components/photos.py
sed -n '1120,1180p' app/web/components/photos.py
from pathlib import Path
import json
import sqlite3
import zipfile
import tempfile

from nicegui import ui

from app.web.config import PHOTO_ROOT, DB_PATH, PROJECT_ROOT

# ============================================================
# PHOTO PREVIEWS
# ============================================================

PREVIEW_ROOT = (
    PROJECT_ROOT
    / "data"
    / "preview"
    / "daily"
)

DAILY_ROOT = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "daily"
)

def get_latest_daily_root():
    """Return the newest daily output directory."""
    if not DAILY_ROOT.exists():
        return None

    runs = [
        path
        for path in DAILY_ROOT.iterdir()
        if path.is_dir()
    ]

    if not runs:
        return None

    return max(
        runs,
        key=lambda path: path.name,
    )

def get_latest_preview_root():
    """Return the newest daily preview directory."""
    if not PREVIEW_ROOT.exists():
        return None

    runs = [
        path
        for path in PREVIEW_ROOT.iterdir()
        if path.is_dir()
    ]

    if not runs:
        return None

    return max(
        runs,
        key=lambda path: path.name,
    )

def get_preview_path(photo_path):
    """Map daily output photo to its preview image."""
    preview_root = get_latest_preview_root()
    daily_root = get_latest_daily_root()

    if preview_root is None or daily_root is None:
        return None

    try:
        relative = photo_path.relative_to(daily_root)
    except ValueError:
        return None

    preview_path = preview_root / relative

    if preview_path.exists():
        return preview_path

    return None
from app.web.state import STATE, Photo
from app.web.photo_db import build_photo_record_index

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

# ============================================================
# PHOTO INDEX
# ============================================================

PHOTO_INDEX: dict[str, list[Path]] = {}

PHOTO_RECORD_INDEX: dict[str, dict] = {}

def build_photo_index():

    PHOTO_INDEX.clear()
    PHOTO_RECORD_INDEX.clear()

    try:
        PHOTO_RECORD_INDEX.update(
            build_photo_record_index(PROJECT_ROOT)
        )

        print(
            "[PHOTO RECORD INDEX]",
            "records=",
            len(PHOTO_RECORD_INDEX),
            flush=True,
        )

    except Exception as exc:

        print(
            "[PHOTO RECORD INDEX ERROR]",
            repr(exc),
            flush=True,
        )

    daily_root = get_latest_daily_root()

    if daily_root is None:
        print(
            "[DAILY PHOTO ROOT] not found",
            flush=True,
        )
        return

    print(
        "[DAILY PHOTO ROOT]",
        daily_root,
        flush=True,
    )

    # --------------------------------------------------------
    # ADDRESSES FROM CURRENT DAILY RUN
    # --------------------------------------------------------

    daily_addresses = sorted(
        (
            path.name[:-4]
            for path in daily_root.iterdir()
            if (
                path.is_dir()
                and path.name.endswith("_v33")
                and path.name[:-4].isdigit()
            )
        ),
        key=lambda value: int(value),
    )

    STATE.addresses = daily_addresses

    # Сбрасываем выбранные адреса, которых больше нет
    STATE.selected_addresses.intersection_update(
        STATE.addresses
    )

    print(
        "[DAILY ADDRESSES]",
        STATE.addresses,
        flush=True,
    )

                    ):

                        for photo in STATE.photos:

                            with ui.card().classes(
                                "overflow-hidden "
                                "cursor-pointer "
                                "hover:shadow-lg"
                            ):

                                # ----------------------------
                                # IMAGE
                                # ----------------------------

                                with ui.element(
                                    "div"
                                ).classes(
                                    "relative "
                                    "w-full h-44 "
                                    "bg-grey-2 "
                                    "flex items-center "
                                    "justify-center"
                                ).on(
                                    "contextmenu.prevent",
                                    lambda e, p=photo:
                                        photo_menu(p),
                                ):

                                    # В ГРИДЕ показываем PREVIEW.
                                    # Оригинал открывается только
                                    # после клика.
                                    preview_path = (
                                        get_preview_path(
                                            photo.path
                                        )
                                    )

                                    display_path = (
                                        preview_path
                                        if preview_path
                                        else photo.path
                                    )

                                    ui.image(
                                        str(display_path)
                                    ).classes(
                                        "w-full h-full "
                                        "object-contain"
                                    ).on(
                                        "click",
                                        lambda e, p=photo:
                                            open_photo(p),
                                    )

                                # ----------------------------
                                # NAME
                                # ----------------------------

                                with ui.row().classes(
                                    "w-full "
                                    "items-center "
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 00:09:16

Да. Теперь картина достаточно ясная, и я бы **не стал сейчас переделывать DINO/Hybrid-логику**. Основная проблема уже видна в слое хранения и отображения.

### Что у нас сейчас

Сейчас архитектура фактически такая:

```text
INPUT/daily
      │
      ▼
photo_ingest.py
      │
      ▼
PostgreSQL photos
      │
      ├── DINO
      │
      ├── Hybrid
      │
      └── Qwen
      │
      ▼
OUTPUT/daily/YYYYMMDD_HHMMSS/
      ├── 78_v33/
      ├── 79_v33/
      └── ...
```

А Grid пока делает наоборот:

```text
OUTPUT/daily/последний запуск
        │
        ▼
      Grid
```

и только параллельно смотрит в БД.

Это как раз надо поменять.

---

# Новая логика

База `photos` должна стать **главным каталогом всей фототеки**.

Не:

> «вот фотографии последнего daily-запуска»

а:

> «вот все фотографии, которые когда-либо поступали в систему, и состояние обработки каждой».

То есть:

```text
                 PostgreSQL photos
                       │
        ┌──────────────┼──────────────┐
        │              │              │
       DINO           Hybrid         Qwen
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
                     GRID
```

---

# И самое важное — структура файлов

Ты описал конечную модель:

```text
INPUT
│
├── 2026-08
│   ├── 01
│   │   ├── фото1.JPG
│   │   ├── фото2.JPG
│   │   └── фото3.JPG
│   │
│   ├── 02
│   │   ├── фото1.JPG
│   │   └── ...
│   │
│   └── ...
│
├── 2026-09
│   ├── 01
│   └── ...
│
└── 2027-01
    └── ...
```

При этом **файлы не являются источником истины для Grid**.

База знает:

```text
photo_id
source_path
original_filename
created_at
address_id
client
...
dino_status
sort_status
qwen_status
preview_status
...
```

Поэтому можно иметь огромный каталог за несколько лет.

---

# Повторная обработка

И вот здесь твоя мысль про базу очень правильная.

Допустим:

```text
2026-08/18/
    001.JPG
    002.JPG
    003.JPG
```

Сегодня добавились:

```text
2026-08/18/
    004.JPG
    005.JPG
```

Запускаем ingest.

Он видит:

```text
001 → уже есть в БД → SKIP
002 → уже есть в БД → SKIP
003 → уже есть в БД → SKIP
004 → новая → REGISTER
005 → новая → REGISTER
```

И только:

```text
004
005
```

получают:

```text
dino_status = pending
qwen_status = pending
sort_status = pending
preview_status = pending
```

После этого DINO worker сам забирает только pending.

То есть **ежедневного полного пересчёта вообще не требуется**.

---

# Но сейчас есть одна важная проблема

`photo_ingest.py` сейчас проверяет:

```python
source_path
```

и это хорошо для первоначального варианта.

Но если мы начнём работать с настоящим каталогом:

```text
2026-08/18/001.JPG
```

то нужно, чтобы **путь оставался постоянным**.

Например:

```text
/home/alexice/.../data/input/2026-08/18/001.JPG
```

Тогда база сможет надёжно сказать:

> этот файл уже зарегистрирован.

Если файл физически переместили, это уже отдельный вопрос — его пока не трогаем.

---

# Что ещё обязательно поменять

## 1. `photo_ingest.py`

Сейчас:

```python
input_dir.iterdir()
```

и:

> подкаталоги пока не трогаем.

Это **пока оставляем**, как ты сказал.

Но в будущей версии меняем на рекурсивный скан:

```python
input_dir.rglob("*")
```

Тогда:

```text
input/
├── 2026-08/
│   ├── 01/
│   ├── 02/
│   └── 03/
└── 2026-09/
    ├── 01/
    └── 02/
```

будет одним большим источником фотографий.

---

# 2. `run_daily_hybrid_v12.sh`

Вот это уже надо постепенно убрать из архитектуры.

Сейчас он создаёт:

```text
data/output/daily/20260818_230042/
```

и запускает Hybrid на **всех фотографиях входной папки**.

Для нового варианта это неправильно.

Будет:

```text
Новые фотографии
       ↓
PostgreSQL
       ↓
DINO pending
       ↓
Hybrid
       ↓
Qwen
       ↓
База
```

А не:

```text
daily folder
   ↓
полный Hybrid
   ↓
новая daily-папка
```

---

# 3. `run_hybrid_v12.py`

Сам алгоритм пока **замораживаем как есть**.

Особенно это:

```python
GLOBAL_WEIGHT = 10.0
SUB_WEIGHT = 2.5
NEIGHBOR_WEIGHT = 6.0
```

и соседние фотографии:

```python
left_fp = rows[i - 1].get("top1")
right_fp = rows[i + 1].get("top1")
```

Но есть архитектурный нюанс.

Сейчас соседями являются фотографии **внутри одного запуска**.

В новой системе соседями должны стать фотографии из **последовательности каталога**:

```text
2026-08/18/001
2026-08/18/002
2026-08/18/003
2026-08/18/004
2026-08/18/005
```

Причём это особенно важно, потому что ты раньше отдельно отметил:

> сортировка смотрит на соседние фото и их результаты.

Это нельзя потерять при переходе от daily к постоянной базе.

---

# 4. `photos.py` — здесь изменение самое очевидное

Сейчас у нас есть:

```python
get_latest_daily_root()
```

и:

```python
get_latest_preview_root()
```

и дальше:

```python
daily_root = get_latest_daily_root()
```

То есть Grid буквально говорит:

> дай мне последний daily.

Это больше не должно быть основой Grid.

Должно быть:

```text
PostgreSQL
   ↓
выбранные записи photos
   ↓
photo.path / source_path
   ↓
Grid
```

То есть **Grid вообще не должен знать, какой был последний запуск Hybrid**.

---

# 5. Preview

Тут тоже нужно изменить концепцию.

Сейчас:

```text
preview/daily/
    20260818_230042/
        78_v33/
        79_v33/
```

и затем:

```python
get_latest_preview_root()
```

Это опять привязка к daily.

В новой архитектуре правильнее:

```text
data/preview/
    PH_00000524.jpg
    PH_00000525.jpg
    PH_00000526.jpg
```

или, если хочется сохранить структуру:

```text
data/preview/
    2026-08/
        18/
            PH_00000524.jpg
            PH_00000525.jpg
```

А в БД:

```text
photo_id = PH_00000524
preview_path = ...
preview_status = done
```

И Grid получает preview **не по последнему запуску**, а непосредственно из записи фотографии.

---

# База у нас для этого уже практически готова

Особенно хорошие поля:

```text
photo_id
initial_id

source_path
path
filename
original_filename

address
address_id

client
brand
category
description

status

dino_status
qwen_status
sort_status
preview_status

dino_fingerprint
dino_score
dino_second_score
dino_margin

hybrid_original_id
hybrid_final_id
hybrid_changed
hybrid_old_score
hybrid_score
hybrid_margin
hybrid_neighbors

text_json
colors_json
objects_json
...
preview_path

created_at
updated_at
```

То есть **не нужно создавать новую базу для каталога**.

Нужно сделать существующую `photos` настоящим постоянным индексом фототеки.

---

## Я бы сейчас зафиксировал архитектуру именно так

```text
                 ПАПКА INPUT
                      │
             рекурсивный ingest
                      │
                      ▼
              ┌───────────────┐
              │  PostgreSQL   │
              │    photos     │
              └───────┬───────┘
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       DINO        HYBRID       QWEN
          │           │           │
          └───────────┼───────────┘
                      ▼
                  PostgreSQL
                      │
                      ▼
                    GRID
```

А физически:

```text
data/input/
├── 2026-08/
│   ├── 01/
│   ├── 02/
│   ├── ...
│   └── 18/
├── 2026-09/
│   ├── 01/
│   └── ...
└── 2027-01/
```

И главное:

**`daily` перестаёт быть понятием фототеки.**

Он может остаться как временное имя старых скриптов на этапе перехода, но новая система должна мыслить не «daily», а **«новые записи в постоянном каталоге»**.

И тогда твоя формулировка становится точной:

> **База хранит информацию обо всех поступивших фотографиях. Обработка выполняется только для новых или повторно поставленных в очередь. Grid показывает фотографии из базы.**

Следующий технический шаг я бы сделал очень узким: **переделать `photo_ingest.py` так, чтобы он мог рекурсивно сканировать будущий каталог, но пока ничего больше не менять.** Затем уже отдельно переделать Grid с `latest_daily` на БД.

---

### 👤 **User** — 2026-08-19 00:11:09

далее

---

### 🤖 **Assistant** — 2026-08-19 00:11:10

Да. Следующий шаг — **не трогаем DINO, Hybrid и Qwen**, а сначала переводим **источник фотографий и Grid на постоянный каталог**.

Я бы пошёл в таком порядке:

### Шаг 1 — `photo_ingest.py`

Сделать его рекурсивным:

```text
data/input/
├── 2026-08/
│   ├── 01/
│   │   ├── 001.JPG
│   │   └── 002.JPG
│   ├── 02/
│   └── 18/
├── 2026-09/
│   └── ...
```

Он должен:

- находить фото во всех вложенных папках;
- проверять `source_path` в PostgreSQL;
- уже зарегистрированные пропускать;
- новые добавлять;
- выдавать новые `PH_...` и `IN_...`;
- **ничего не обрабатывать сам**.

То есть ingest становится просто:

```text
СКАНИРОВАНИЕ → БАЗА
```

---

### Шаг 2 — очередь DINO

У нас здесь уже почти всё правильно.

`dino_worker.py` делает:

```sql
WHERE dino_status = 'pending'
```

поэтому ему вообще не важно, откуда фотография пришла:

```text
2026-08/01
2026-08/18
2027-03/05
```

Он просто берёт новые записи.

Это **оставляем**.

---

### Шаг 3 — Hybrid

Вот здесь будет основная переделка.

Сейчас:

```text
run_hybrid_v12.py
        ↓
берёт папку
        ↓
DINO recognition
        ↓
Hybrid
        ↓
копирование в output/daily
```

Нам нужно:

```text
photos WHERE ...
        ↓
DINO уже имеет результаты
        ↓
Hybrid
        ↓
UPDATE photos
```

То есть Hybrid перестаёт быть файловым сортировщиком.

Он должен записывать:

```text
hybrid_original_id
hybrid_final_id
hybrid_changed
hybrid_old_score
hybrid_score
hybrid_margin
hybrid_neighbors
sort_status
```

прямо в `photos`.

---

### Шаг 4 — физическая сортировка

И здесь важный момент.

Я бы **не удалял физическую сортировку вообще**.

Можно иметь:

```text
data/input/
    2026-08/18/...

data/catalog/
    78/
    79/
    80/
```

Но это уже будет **производное представление**, а не источник истины.

Источник истины:

```text
PostgreSQL
```

Например:

```text
PH_00000526
source_path = /data/input/2026-08/18/Шолохова 127 А (9).JPG
address_id = 78
hybrid_final_id = 78_v33
```

---

### Шаг 5 — Preview

После этого:

```text
photo_ingest
      ↓
DINO
      ↓
Hybrid
      ↓
Qwen
      ↓
preview
```

и `preview_path` записывается в БД.

Тогда Grid делает просто:

```text
SELECT ...
FROM photos
WHERE ...
```

и получает:

```text
photo_id
source_path
preview_path
address
client
...
```

---

### Шаг 6 — Grid

Вот это будет очень приятное изменение.

Сейчас:

```python
daily_root = get_latest_daily_root()
```

и:

```python
STATE.addresses = daily_addresses
```

будет заменено на запрос типа:

```sql
SELECT DISTINCT hybrid_final_id
FROM photos
WHERE hybrid_final_id IS NOT NULL
ORDER BY ...
```

А фотографии:

```sql
SELECT ...
FROM photos
WHERE ...
```

То есть Grid автоматически увидит:

```text
2026-08
2026-09
2026-10
...
```

и не будет зависеть от того, запускался сегодня Hybrid или нет.

---

## И ещё один принцип я бы зафиксировал

**Не пересчитывать базу каждый день.**

База постоянно накапливается:

```text
2026
 ├─ август       5 000
 ├─ сентябрь     7 000
 ├─ октябрь      6 000
 └─ ...

2027
 └─ ...
```

При новом запуске:

```text
10 000 старых
      +
   137 новых
      ↓
обработать только 137
```

А если нужно повторно обработать старые:

```text
dino_status = pending
```

или соответствующий статус конкретного этапа.

Это даст нам **постоянную фотобазу**, а не набор независимых daily-запусков.

### Поэтому сейчас я предлагаю сделать только первый реальный кодовый шаг:

**переделать `photo_ingest.py` на рекурсивное сканирование вложенных каталогов**, не меняя пока остальную систему.

После этого проверим на существующей базе, что он корректно показывает `SKIP` для уже зарегистрированных и `REGISTER` только для новых.

---

### 👤 **User** — 2026-08-19 00:12:41

на данном этапе физическая сортировка не нужно - лишь удваивает место

---

### 🤖 **Assistant** — 2026-08-19 00:12:42

Да, согласен. **Физическую сортировку вообще убираем из новой архитектуры.** Это как раз сильно упрощает систему и экономит место.

### Фиксируем окончательно

```text
INPUT — единственное физическое хранилище фотографий
        │
        ▼
     INGEST
        │
        ▼
   PostgreSQL
        │
        ├── DINO
        ├── Hybrid
        ├── Qwen
        └── Preview
        │
        ▼
      GRID
```

То есть **никакого**:

```text
data/output/daily/
data/output/78_v33/
data/output/79_v33/
...
```

для самих фотографий больше не требуется.

---

### Файл существует только один раз

Например:

```text
data/input/
└── 2026-08/
    └── 18/
        ├── Шолохова 127 А (7).JPG
        ├── Шолохова 127 А (8).JPG
        └── Шолохова 127 А (9).JPG
```

В БД:

```text
PH_00000524
source_path = .../2026-08/18/Шолохова 127 А (7).JPG
address_id = 78
hybrid_final_id = 78_v33
client = ...
...
```

**Фото не копируется.**

---

### Тогда `hybrid` становится не сортировщиком

Сейчас:

```python
shutil.copy2(
    source,
    destination,
)
```

эта логика нам больше не нужна.

Hybrid должен сделать только:

```text
DINO result
     ↓
Hybrid decision
     ↓
UPDATE photos
```

Например:

```text
dino_fingerprint = 78_v33

hybrid_original_id = 78_v33
hybrid_final_id    = 78_v33

hybrid_score       = 12.73
hybrid_margin      = 0.014
hybrid_neighbors   = {...}

sort_status = done
```

Причём поле `sort_status` можно пока оставить для совместимости, но фактически это будет уже не «копирование», а **статус определения итогового адреса**.

Позже можно переименовать концептуально, например в `classification_status`, но **прямо сейчас лучше не ломать существующую схему**.

---

### Grid

Grid получает:

```text
photos
```

и строит представление:

```text
Адрес 78
 ├─ фото 1
 ├─ фото 2
 ├─ фото 3
 └─ ...

Адрес 79
 ├─ фото 1
 ├─ фото 2
 └─ ...
```

Но физически все они остаются там, куда были загружены.

Можно одновременно иметь фильтры:

```text
Месяц
День
Адрес
Клиент
Бренд
Категория
Статус
DINO
Qwen
```

И это уже **виртуальная сортировка**.

---

### Preview тоже можно оставить отдельным

Preview — единственное дополнительное физическое содержимое, которое имеет смысл создавать:

```text
data/preview/
    PH_00000524.webp
    PH_00000525.webp
```

Оригинал:

```text
data/input/2026-08/18/...
```

Preview:

```text
data/preview/PH_00000524.webp
```

А связь:

```text
photos.preview_path
```

То есть даже превью не нужно раскладывать по адресам и daily.

---

## И получается очень чистая модель

```text
                 ┌──────────────────────┐
                 │      INPUT           │
                 │                      │
                 │ 2026-08/01/...       │
                 │ 2026-08/02/...       │
                 │ 2026-09/01/...       │
                 │ 2027-...             │
                 └──────────┬───────────┘
                            │
                         INGEST
                            │
                            ▼
                 ┌──────────────────────┐
                 │      POSTGRES        │
                 │                      │
                 │ вся история фото     │
                 │ результаты DINO      │
                 │ Hybrid               │
                 │ Qwen                 │
                 │ метаданные           │
                 │ preview_path         │
                 └──────────┬───────────┘
                            │
                            ▼
                         GRID
```

**Оригинальный файл один. Запись в БД одна. Preview — при необходимости одна дополнительная копия.**

И да — `data/output/daily` в новой схеме нам фактически больше не нужен.

Следующим шагом логично переделать **`photo_ingest.py`**, а затем **Grid**, и только после этого убрать `run_daily_hybrid_v12.sh` из рабочего пути.

---

### 👤 **User** — 2026-08-19 00:13:30

далее

---

### 🤖 **Assistant** — 2026-08-19 00:13:32

Да. Тогда архитектура становится заметно чище.

### Фиксируем принцип

**1. `data/input` — единственное физическое хранилище фотографий.**

Никакого:

```text
data/output/daily/78_v33/...
data/output/daily/79_v33/...
```

для обычной работы больше не нужно.

DINO определяет:

```text
photo_id
→ address_id
→ score
→ margin
→ hybrid...
```

и **записывает это в PostgreSQL**.

Физически файл остаётся там, где он поступил.

---

### 2. PostgreSQL — это каталог всей фотобазы

У нас уже практически всё необходимое есть в `photos`.

Например:

```text
PH_00000526
source_path = .../input/daily/Шолохова 127 А (9).JPG
filename = Шолохова 127 А (9).JPG
address_id = ...
dino_status = done
dino_score = ...
hybrid_final_id = ...
created_at = ...
```

То есть база становится **историческим реестром всех поступивших фотографий**, а не базой только текущего daily-запуска.

---

### 3. Новые фотографии ищутся по базе

Механика должна быть именно такой:

```text
INPUT
  ↓
сканирование
  ↓
source_path
  ↓
есть в photos?
 ├── ДА → пропустить
 └── НЕТ
       ↓
     создать PH_...
       ↓
     dino_status = pending
       ↓
     DINO
       ↓
     результат в БД
```

Причём это уже почти реализовано в `photo_ingest.py`:

```python
existing_paths = get_existing_source_paths(conn)
```

и:

```python
if source_path in existing_paths:
    ...
    continue
```

То есть **сам принцип не надо переделывать**, надо только позже расширить сканирование на вложенные каталоги.

---

## 4. Грид больше вообще не должен смотреть на `daily`

Вот это сейчас устаревшая логика:

```python
DAILY_ROOT = PROJECT_ROOT / "data" / "output" / "daily"
```

и:

```python
get_latest_daily_root()
```

и особенно:

```python
daily_addresses = ...
```

Грид должен строиться **от PostgreSQL**.

Например пользователь выбирает:

```text
2026
 └── август
      ├── 18
      │    ├── фото 1
      │    ├── фото 2
      │    ├── фото 3
      │    └── ...
      │
      └── 19
           ├── фото 1
           ├── фото 2
           └── ...
```

Это **виртуальная структура каталога**, физически её создавать не надо.

---

### 5. И здесь важный момент: какую дату используем

Сейчас в таблице есть:

```text
created_at
updated_at
```

`created_at` — это дата, когда фотография была **занесена в БД**.

Это подходит, если каталог должен означать:

> «когда фотография поступила в фотобазу».

Но если каталог должен означать:

> «когда фотография была снята / когда она лежала во входной папке»,

то лучше отдельно завести, например:

```text
photo_date
```

или:

```text
source_created_at
```

И уже по нему строить:

```text
2026
 └── 08
      └── 18
```

Я бы **не использовал `updated_at`** для этого вообще — он будет постоянно меняться.

---

## 6. `sort_status` тоже пока не нужен для физической сортировки

Сейчас:

```text
sort_status
hybrid_original_id
hybrid_final_id
hybrid_score
hybrid_margin
hybrid_neighbors
```

Это можно сохранить.

Но смысл меняется:

```text
sort_status
```

не означает:

> «файл физически отсортирован».

В будущем это лучше трактовать как статус **логической классификации**:

```text
pending
processing
done
error
```

А:

```text
hybrid_final_id
```

— это просто:

> **адрес, который система назначила фотографии.**

Файл никуда не копируется.

---

# Итого получается правильная схема

```text
                  ┌─────────────────────┐
                  │     INPUT           │
                  │                     │
                  │  2026/08/18/...     │
                  │  2026/08/19/...     │
                  │  новые папки         │
                  └──────────┬──────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │     INGEST     │
                    │ найти новые    │
                    │ source_path    │
                    └───────┬────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │     PostgreSQL      │
                  │                     │
                  │ PH_00000001         │
                  │ PH_00000002         │
                  │ PH_00000526         │
                  │ ...                 │
                  │                     │
                  │ вся история         │
                  └──────────┬──────────┘
                             │
                  ┌──────────▼──────────┐
                  │       DINO          │
                  │                     │
                  │ address_id          │
                  │ score               │
                  │ margin              │
                  │ fingerprint         │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   ВИРТУАЛЬНЫЙ       │
                  │      КАТАЛОГ         │
                  │                     │
                  │ 2026                │
                  │  └─08               │
                  │    ├─18             │
                  │    │ ├─ photo 1     │
                  │    │ ├─ photo 2     │
                  │    │ └─ ...         │
                  │    └─19             │
                  └──────────┬──────────┘
                             │
                             ▼
                         ГРИД
```

И самое важное: **одна фотография физически существует только один раз**.

Все остальные представления — адрес, клиент, дата, статус, превью, результаты DINO/Hybrid и т.д. — это данные БД.

---

### Следующий шаг

Теперь я бы **не трогал `photo_ingest.py` и DINO**.

Сначала надо переделать один слой — `app/web/photo_db.py` + `build_photo_index()` в `photos.py`, чтобы понять, **как сейчас из PostgreSQL формируется `PHOTO_RECORD_INDEX` и `STATE.photos`**.

Дай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat app/web/photo_db.py
```

и следующим шагом разберём именно его.

---

### 👤 **User** — 2026-08-19 00:14:17

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

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
            imported_at
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

