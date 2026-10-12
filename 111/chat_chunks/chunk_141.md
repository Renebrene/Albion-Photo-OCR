## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 🤖 **Assistant** — 2026-08-18 23:45:28

Да. Тогда следующий шаг — **общий диспетчер запуска**, но пока без изменения UI. Сначала делаем правильный backend-слой, чтобы потом UI только управлял им.

### 1. Что должно получиться

После `photo_ingest`:

```text
НОВЫЙ ФАЙЛ
    │
    ▼
photo_id = PH_00000001
    │
    ├──────────────► DINO queue
    │                    │
    │                    ▼
    │                address_id
    │
    └──────────────► QWEN queue
                         │
                         ▼
                    description
```

При этом:

```text
photo_id        создаётся первым
initial_id      псевдоним/ключ исходного набора
address_id      появляется только после DINO
```

И Grid:

```text
address_id IS NOT NULL
        │
        ▼
      GRID
        │
        └── JOIN по photo_id ──► Qwen-данные
```

### 2. Диспетчер

Создадим:

```text
app/pipeline/controller.py
```

Он будет единственной точкой, которая решает, что запускать:

```text
MANUAL
    ├── кнопка DINO
    ├── кнопка QWEN
    └── кнопка ОБЩИЙ

WATCHER
    └── только watcher

SCHEDULE
    └── автоматический запуск по времени
```

И очень важно: при `WATCHER` и `SCHEDULE` ручные кнопки блокируются.

При `STOP`:

```text
любое состояние
      │
      ▼
    STOP
      │
      ▼
   MANUAL
```

То есть именно то, что мы договорились.

---

## 3. Сначала создаём контроллер

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/pipeline/controller.py <<'PY'
from __future__ import annotations

import enum
import threading
from dataclasses import dataclass

class RunMode(str, enum.Enum):
    MANUAL = "manual"
    WATCHER = "watcher"
    SCHEDULE = "schedule"

class Process(str, enum.Enum):
    ALL = "all"
    DINO = "dino"
    QWEN = "qwen"

@dataclass
class PipelineState:
    mode: RunMode = RunMode.MANUAL

    running: bool = False

    dino_running: bool = False
    qwen_running: bool = False

    watcher_running: bool = False
    schedule_running: bool = False

    stop_requested: bool = False

class PipelineController:

    def __init__(self):
        self._lock = threading.RLock()

        self.state = PipelineState()

    # ========================================================
    # STATE
    # ========================================================

    def get_state(self) -> PipelineState:

        with self._lock:

            return PipelineState(
                mode=self.state.mode,

                running=self.state.running,

                dino_running=self.state.dino_running,
                qwen_running=self.state.qwen_running,

                watcher_running=self.state.watcher_running,
                schedule_running=self.state.schedule_running,

                stop_requested=self.state.stop_requested,
            )

    # ========================================================
    # MODE
    # ========================================================

    def set_manual(self):

        with self._lock:

            self.state.mode = RunMode.MANUAL

            self.state.watcher_running = False
            self.state.schedule_running = False

            self.state.stop_requested = False

    def set_watcher(self):

        with self._lock:

            self.state.mode = RunMode.WATCHER

            self.state.watcher_running = True
            self.state.schedule_running = False

            self.state.stop_requested = False

    def set_schedule(self):

        with self._lock:

            self.state.mode = RunMode.SCHEDULE

            self.state.watcher_running = False
            self.state.schedule_running = True

            self.state.stop_requested = False

    # ========================================================
    # PERMISSIONS
    # ========================================================

    def manual_allowed(self) -> bool:

        with self._lock:

            return (
                self.state.mode
                == RunMode.MANUAL
            )

    def can_start(self, process: Process) -> bool:

        with self._lock:

            if self.state.mode != RunMode.MANUAL:
                return False

            if self.state.running:
                return False

            return True

    # ========================================================
    # START
    # ========================================================

    def start(
        self,
        process: Process,
    ) -> bool:

        with self._lock:

            if not self.can_start(process):
                return False

            self.state.running = True

            self.state.stop_requested = False

            if process in (
                Process.ALL,
                Process.DINO,
            ):
                self.state.dino_running = True

            if process in (
                Process.ALL,
                Process.QWEN,
            ):
                self.state.qwen_running = True

            return True

    # ========================================================
    # WORKER FINISHED
    # ========================================================

    def worker_finished(
        self,
        process: Process,
    ):

        with self._lock:

            if process in (
                Process.ALL,
                Process.DINO,
            ):
                self.state.dino_running = False

            if process in (
                Process.ALL,
                Process.QWEN,
            ):
                self.state.qwen_running = False

            if (
                not self.state.dino_running
                and not self.state.qwen_running
            ):
                self.state.running = False

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        with self._lock:

            self.state.stop_requested = True

            self.state.running = False

            self.state.dino_running = False
            self.state.qwen_running = False

            self.state.watcher_running = False
            self.state.schedule_running = False

            # ВАЖНО:
            # после STOP всегда возвращаемся
            # в ручной режим.

            self.state.mode = RunMode.MANUAL

            self.state.stop_requested = False

    # ========================================================
    # RESET
    # ========================================================

    def reset(self):

        with self._lock:

            self.state = PipelineState()

    # ========================================================
    # UI HELPERS
    # ========================================================

    def mode_label(self) -> str:

        with self._lock:

            if self.state.mode == RunMode.MANUAL:
                return "Ручной запуск"

            if self.state.mode == RunMode.WATCHER:
                return "Watcher"

            if self.state.mode == RunMode.SCHEDULE:
                return "Автоматический запуск"

            return "Неизвестно"

    def mode_description(self) -> str:

        with self._lock:

            if self.state.mode == RunMode.MANUAL:

                return (
                    "Ручной режим. "
                    "Процессы запускаются кнопками "
                    "в интерфейсе."
                )

            if self.state.mode == RunMode.WATCHER:

                return (
                    "Watcher. "
                    "Система постоянно наблюдает "
                    "за входной папкой и автоматически "
                    "обрабатывает новые фотографии. "
                    "Ручные кнопки запуска недоступны."
                )

            if self.state.mode == RunMode.SCHEDULE:

                return (
                    "Автоматический режим. "
                    "Процесс запускается автоматически "
                    "в заданное время. "
                    "Ручные кнопки запуска недоступны."
                )

            return ""

# ============================================================
# SINGLETON
# ============================================================

_controller = PipelineController()

def get_controller() -> PipelineController:
    return _controller
PY
```

Проверка:

```bash
uv run python -m py_compile \
    app/pipeline/controller.py
```

---

### 4. Важное изменение логики

Теперь **не надо запускать DINO/Qwen напрямую из UI**.

UI должен делать:

```python
controller.start(Process.DINO)
```

или:

```python
controller.start(Process.QWEN)
```

или:

```python
controller.start(Process.ALL)
```

А остановка:

```python
controller.stop()
```

Переключение режима:

```python
controller.set_manual()
controller.set_watcher()
controller.set_schedule()
```

---

### 5. Но есть один важный нюанс

Сейчас `start(Process.ALL)` только **фиксирует состояние**. Он ещё не запускает subprocess/worker.

И это специально.

Следующим шагом сделаем:

```text
PipelineController
       │
       ├── DINO worker
       │
       ├── Qwen worker
       │
       └── Watcher
```

и тогда уже получится настоящий процесс:

```text
MANUAL
  │
  ├─ [Запустить всё]
  │       ├─ DINO
  │       └─ Qwen
  │
  ├─ [Запустить DINO]
  │
  └─ [Запустить Qwen]

WATCHER
  │
  └─ watcher
       │
       └─ новые файлы
             │
             └─ photo_id
                  ├─ DINO
                  └─ Qwen

SCHEDULE
  │
  └─ время наступило
        │
        ├─ DINO
        └─ Qwen
```

И **при этом очереди PostgreSQL уже обеспечивают продолжение после прерывания**:

```text
pending
   ↓
processing
   ↓
done
```

Если процесс умер на `processing`, следующим слоем мы обязательно добавим recovery:

```text
processing
   │
   ├── worker жив → продолжаем
   │
   └── worker умер → вернуть в pending
```

Это важно сделать **до watcher**, иначе после перезапуска можно получить зависшие фотографии.

Следующим я бы сделал именно **recovery + единый запуск DINO/Qwen**, а уже потом подключил watcher и расписание.

---

### 👤 **User** — 2026-08-18 23:46:11

да

---

### 🤖 **Assistant** — 2026-08-18 23:46:13

Да. Сейчас делаем **recovery + реальный запуск DINO/Qwen через контроллер**. Это фундамент перед watcher.

### 1. Добавляем recovery в контроллер

Идея:

- `PENDING` — ждёт;
- `PROCESSING` — сейчас работает;
- если процесс аварийно умер, запись остаётся `PROCESSING`;
- при следующем запуске контроллер возвращает зависшие записи в `PENDING`;
- `DONE` никогда автоматически не трогаем.

Сначала сделаем отдельный модуль:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/pipeline/recovery.py <<'PY'
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
    Возвращает зависшие DINO/Qwen jobs из PROCESSING -> PENDING.

    DONE не затрагивается.
    ERROR не затрагивается.

    timeout нужен, чтобы не вернуть в очередь
    реально работающий долгий процесс.
    """

    cutoff = datetime.now(timezone.utc) - timedelta(
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
                    updated_at = CURRENT_TIMESTAMP
                WHERE
                    dino_status = 'processing'
                    AND updated_at < %s
                """,
                (cutoff,),
            )

            recovered_dino = cur.rowcount

            cur.execute(
                """
                UPDATE photos
                SET
                    qwen_status = 'pending',
                    updated_at = CURRENT_TIMESTAMP
                WHERE
                    qwen_status = 'processing'
                    AND updated_at < %s
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
PY

uv run python -m py_compile \
    app/pipeline/recovery.py
```

---

## 2. Но здесь есть одна поправка

Для recovery лучше использовать не просто `updated_at`, а отдельные:

```text
dino_started_at
qwen_started_at
```

Потому что `updated_at` может изменяться другими действиями.

Поэтому добавляем их сейчас:

```bash
psql -h localhost -U lora -d photobase <<'SQL'

ALTER TABLE photos
ADD COLUMN IF NOT EXISTS dino_started_at TIMESTAMP;

ALTER TABLE photos
ADD COLUMN IF NOT EXISTS qwen_started_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_photos_dino_processing
ON photos(dino_status, dino_started_at);

CREATE INDEX IF NOT EXISTS idx_photos_qwen_processing
ON photos(qwen_status, qwen_started_at);

SQL
```

Теперь меняем recovery:

```bash
cat > app/pipeline/recovery.py <<'PY'
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
PY
```

---

# 3. Теперь меняем DINO worker

В `claim_photo()` фиксируем время старта.

Сделаем аккуратно через Python-замену:

```bash
python - <<'PY'
from pathlib import Path

p = Path("app/workers/dino_worker.py")

s = p.read_text()

old = """            UPDATE photos
            SET
                dino_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
"""

new = """            UPDATE photos
            SET
                dino_status = 'processing',
                dino_started_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
"""

if old not in s:
    raise SystemExit("DINO claim block not found")

s = s.replace(old, new)

old = """                dino_time_sec = %s,
                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP
"""

new = """                dino_time_sec = %s,
                dino_started_at = NULL,
                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP
"""

if old not in s:
    raise SystemExit("DINO done block not found")

s = s.replace(old, new)

p.write_text(s)
PY
```

Проверяем:

```bash
grep -n -A8 -B2 "dino_started_at" \
    app/workers/dino_worker.py
```

---

# 4. То же для Qwen

```bash
python - <<'PY'
from pathlib import Path

p = Path("app/workers/qwen_worker.py")

s = p.read_text()

old = """            UPDATE photos
            SET
                qwen_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND qwen_status = 'pending'
"""

new = """            UPDATE photos
            SET
                qwen_status = 'processing',
                qwen_started_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND qwen_status = 'pending'
"""

if old not in s:
    raise SystemExit("QWEN claim block not found")

s = s.replace(old, new)

old = """                qwen_time_sec = %s,

                text_json =
"""

new = """                qwen_time_sec = %s,
                qwen_started_at = NULL,

                text_json =
"""

if old not in s:
    raise SystemExit("QWEN done block not found")

s = s.replace(old, new)

old = """                qwen_status = 'error',
                error_message = %s,
"""

new = """                qwen_status = 'error',
                qwen_started_at = NULL,
                error_message = %s,
"""

if old not in s:
    raise SystemExit("QWEN error block not found")

s = s.replace(old, new)

p.write_text(s)
PY
```

Проверяем синтаксис обоих:

```bash
uv run python -m py_compile \
    app/workers/dino_worker.py \
    app/workers/qwen_worker.py \
    app/pipeline/recovery.py \
    app/pipeline/controller.py
```

Должно быть:

```text
```

и код возврата:

```bash
echo $?
```

```text
0
```

---

# 5. Теперь реальный запуск из Controller

Создаём `runner.py`.

Он будет запускать **два независимых процесса**.

Это важно: DINO и Qwen не должны блокировать друг друга.

```bash
cat > app/pipeline/runner.py <<'PY'
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

PROJECT = Path(
    __file__
).resolve().parents[2]

class PipelineRunner:

    def __init__(self):

        self._lock = threading.RLock()

        self.dino_process = None
        self.qwen_process = None

    # ========================================================
    # DINO
    # ========================================================

    def start_dino(self):

        with self._lock:

            if self.is_dino_running():
                return False

            self.dino_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "app.workers.dino_worker",
                ],
                cwd=PROJECT,
                env=os.environ.copy(),
            )

            return True

    # ========================================================
    # QWEN
    # ========================================================

    def start_qwen(self):

        with self._lock:

            if self.is_qwen_running():
                return False

            self.qwen_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "app.workers.qwen_worker",
                ],
                cwd=PROJECT,
                env=os.environ.copy(),
            )

            return True

    # ========================================================
    # ALL
    # ========================================================

    def start_all(self):

        dino = self.start_dino()
        qwen = self.start_qwen()

        return dino or qwen

    # ========================================================
    # STATUS
    # ========================================================

    def is_dino_running(self):

        with self._lock:

            if self.dino_process is None:
                return False

            if self.dino_process.poll() is None:
                return True

            self.dino_process = None

            return False

    def is_qwen_running(self):

        with self._lock:

            if self.qwen_process is None:
                return False

            if self.qwen_process.poll() is None:
                return True

            self.qwen_process = None

            return False

    def status(self):

        return {
            "dino": self.is_dino_running(),
            "qwen": self.is_qwen_running(),
        }

    # ========================================================
    # STOP
    # ========================================================

    def stop_dino(self):

        with self._lock:

            if not self.is_dino_running():
                return

            self.dino_process.terminate()

    def stop_qwen(self):

        with self._lock:

            if not self.is_qwen_running():
                return

            self.qwen_process.terminate()

    def stop_all(self):

        self.stop_dino()
        self.stop_qwen()

    # ========================================================
    # CLEANUP
    # ========================================================

    def cleanup(self):

        with self._lock:

            if (
                self.dino_process is not None
                and self.dino_process.poll()
                is not None
            ):
                self.dino_process = None

            if (
                self.qwen_process is not None
                and self.qwen_process.poll()
                is not None
            ):
                self.qwen_process = None

_runner = PipelineRunner()

def get_runner():
    return _runner
PY
```

Проверка:

```bash
uv run python -m py_compile \
    app/pipeline/runner.py
```

---

# 6. Теперь Controller связываем с Runner

В `controller.py` добавим импорт:

```python
from app.pipeline.runner import get_runner
```

и в `__init__`:

```python
self.runner = get_runner()
```

А `start()` заменяем на реальный запуск:

```python
def start(
    self,
    process: Process,
) -> bool:

    with self._lock:

        if not self.can_start(process):
            return False

        started = False

        if process == Process.DINO:
            started = self.runner.start_dino()

        elif process == Process.QWEN:
            started = self.runner.start_qwen()

        elif process == Process.ALL:
            started = self.runner.start_all()

        if not started:
            return False

        self.state.running = True
        self.state.stop_requested = False

        self.state.dino_running = (
            self.runner.is_dino_running()
        )

        self.state.qwen_running = (
            self.runner.is_qwen_running()
        )

        return True
```

А `stop()`:

```python
def stop(self):

    with self._lock:

        self.state.stop_requested = True

        self.runner.stop_all()

        self.state.running = False

        self.state.dino_running = False
        self.state.qwen_running = False

        self.state.watcher_running = False
        self.state.schedule_running = False

        self.state.mode = RunMode.MANUAL

        self.state.stop_requested = False
```

---

## 7. Получаем уже правильную архитектуру

Теперь запуск:

```text
                         CONTROLLER
                             │
                 ┌───────────┴───────────┐
                 │                       │
              DINO                    QWEN
                 │                       │
        subprocess               subprocess
                 │                       │
                 ▼                       ▼
          dino_worker.py          qwen_worker.py
                 │                       │
                 └───────────┬───────────┘
                             │
                         PostgreSQL
                             │
                         photos
```

И самое главное:

```text
photo_id
   │
   ├────────── DINO
   │             │
   │             └── address_id
   │
   └────────── QWEN
                 │
                 └── description / brand / ...
```

**Никакой физической сортировки между ними нет.**

---

### 8. Что теперь уже обеспечено

| Ситуация | Результат |
|---|---|
| Новый файл | получает `photo_id` |
| DINO запущен | берёт свой `pending` |
| Qwen запущен | берёт свой `pending` |
| DINO закончил | пишет `address_id` |
| Qwen закончил | пишет описание |
| DINO ждёт Qwen | **нет** |
| Qwen ждёт DINO | **нет** |
| DINO упал | recovery вернёт его в `pending` |
| Qwen упал | recovery вернёт его в `pending` |
| `done` | повторно не берётся |
| Grid | показывает только записи с `address_id` |

И остаётся важный следующий слой: **ingest должен после создания `photo_id` фактически инициировать обе независимые очереди**, а затем мы подключаем **watcher**.

После этого уже можно переходить к UI с тремя режимами:

**🟢 Ручной / 🟡 Watcher / 🔵 Автоматический**, tooltip для каждого и неактивными кнопками запуска в двух автоматических режимах.

---

### 👤 **User** — 2026-08-18 23:46:47

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python - <<'PY'
from pathlib import Path

p = Path("app/workers/dino_worker.py")

s = p.read_text()

old = """            UPDATE photos
            SET
                dino_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
"""

new = """            UPDATE photos
            SET
                dino_status = 'processing',
                dino_started_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
"""

if old not in s:
PYwrite_text(s)ld, new)INO done block not found"))
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:46:48

Да, здесь просто команда вызвана через `python`, а в системе доступен `python3`.

Но **пока ничего не меняем**. У нас сейчас важный момент: нужно сначала привести DINO/Qwen к единой схеме состояний и `photo_id`, чтобы не начать частично переделывать worker.

Следующий шаг — проверить, есть ли уже временные поля:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -h localhost -U lora -d photobase -c '\d+ photos' | grep -E \
'photo_id|initial_id|address_id|dino_status|dino_started|dino_finished|qwen_status|qwen_started|qwen_finished|sort_status|preview_status'
```

И отдельно посмотрим текущий `dino_worker.py` на наличие уже добавленных изменений:

```bash
grep -nE \
'dino_status|dino_started|dino_finished|address_id|initial_id|photo_id' \
app/workers/dino_worker.py
```

**После этого я дам тебе готовый файл `dino_worker.py` целиком**, а не будем дальше править его кусками через `sed`/`python`.

И принцип фиксируем такой:

```text
                    INGEST
                       │
                       ▼
                  photo_id
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
            DINO               QWEN
              │                 │
              ▼                 ▼
          address_id       описание/JSON
              │                 │
              └────────┬────────┘
                       │
                    photo_id
                       │
                       ▼
                     GRID
```

То есть **Qwen никогда не ждёт DINO**, а DINO никогда не является условием запуска Qwen. `photo_id` — общий ключ связи с самого начала. Адрес появляется только в результате DINO, и **только после `address_id` фотография становится видимой в Grid**.

---

### 👤 **User** — 2026-08-18 23:47:10

int_mvp_v02

psql -h localhost -U lora -d photobase -c '\d+ photos' | grep -E \
'photo_id|initial_id|address_id|dino_status|dino_started|dino_finished|qwen_status|qwen_started|qwen_finished|sort_status|preview_status'
 photo_id              | text                        |           | not null |                                    | extended |             |              | 
 dino_status           | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 qwen_status           | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 sort_status           | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 preview_status        | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 address_id            | text                        |           |          |                                    | extended |             |              | 
 initial_id            | text                        |           |          |                                    | extended |             |              | 
 dino_started_at       | timestamp without time zone |           |          |                                    | plain    |             |              | 
 qwen_started_at       | timestamp without time zone |           |          |                                    | plain    |             |              | 
    "photos_pkey" PRIMARY KEY, btree (photo_id)
    "idx_photos_address_id" btree (address_id)
    "idx_photos_dino_processing" btree (dino_status, dino_started_at)
    "idx_photos_dino_queue" btree (dino_status, id)
    "idx_photos_initial_id" btree (initial_id)
    "idx_photos_preview_queue" btree (preview_status, id)
    "idx_photos_qwen_processing" btree (qwen_status, qwen_started_at)
    "idx_photos_qwen_queue" btree (qwen_status, id)
    "idx_photos_sort_queue" btree (sort_status, id)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -nE \
'dino_status|dino_started|dino_finished|address_id|initial_id|photo_id' \
app/workers/dino_worker.py
49:                dino_status = 'pending',
51:            WHERE dino_status = 'processing'
74:    что у неё уже существует photo_id и
75:    dino_status = pending.
86:                photo_id,
87:                initial_id,
92:                dino_status = 'pending'
111:                dino_status = 'processing',
115:                AND dino_status = 'pending'
140:        address_id = адрес, определённый DINO.
142:    photo_id остаётся независимым идентификатором фотографии.
145:    address_id = result.get("best_id")
153:                dino_status = 'done',
155:                address_id = %s,
169:                address_id,
173:                address_id,
207:                dino_status = 'error',
314:            photo_id = row["photo_id"]
315:            initial_id = row["initial_id"]
325:                photo_id,
326:                "| initial_id:",
327:                initial_id,
372:                address_id = result.get(
378:                    f"{photo_id}"
379:                    f" -> address_id={address_id}"
402:                    f"{photo_id}: {exc}"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:47:12

Отлично. Сейчас структура уже соответствует нашей новой модели: `photo_id` создаётся до разделения, `initial_id` отдельно, DINO пишет `address_id`, а Qwen может работать независимо.

Причём вижу, что `dino_worker.py` **уже частично переделан** — поэтому старый вариант целиком подменять нельзя.

Следующим шагом давай проверим его целиком, чтобы я дал точную финальную версию без потери уже сделанных изменений:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat app/workers/dino_worker.py
```

И сразу Qwen:

```bash
cat scripts/qwen4b_output_v01.py
```

После этого я соберу **два готовых файла целиком** с одинаковой логикой:

- `photo_id` — общий постоянный ключ;
- `initial_id` — псевдоним/идентификатор исходной группы;
- DINO → `address_id`;
- Qwen → описание по `photo_id`;
- Qwen не ждёт DINO;
- Grid показывает только `address_id IS NOT NULL`;
- `pending → processing → done/error`;
- зависшие `processing` можно возвращать в `pending`;
- уже `done` пропускаются;
- будет режим **перезапустить / пропустить / для всех**;
- прерывание не теряет прогресс.

После worker-ов перейдём к **общему управляющему процессу: manual / watcher / automatic**, который мы обсуждали.

---

### 👤 **User** — 2026-08-18 23:48:12

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat app/workers/dino_worker.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cat scripts/qwen4b_output_v01.py
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import json
import os
import time
from pathlib import Path

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

# ============================================================
# CONFIG
# ============================================================

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

MODEL = "qwen3-vl:4b-instruct"

OLLAMA_URL = (
    "http://localhost:11434/api/chat"
)

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
    return psycopg2.connect(
        **DB_CONFIG
    )

def reset_processing(conn):
    """
    Восстановление после прерывания.

    Если Qwen был processing во время:
        - Ctrl+C
        - падения процесса
        - перезагрузки
        - отключения машины

    фотография снова становится pending.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'pending',
                updated_at = CURRENT_TIMESTAMP
            WHERE qwen_status = 'processing'
            """
        )

        count = cur.rowcount

    conn.commit()

    if count:
        print(
            "[QWEN] Reset stale processing:",
            count,
        )

def claim_photo(conn):
    """
    Берёт следующую фотографию Qwen.

    ВАЖНО:

    Qwen не зависит от DINO.

    Условия только:

        qwen_status = pending
        source_path существует в БД
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
                qwen_status = 'pending'
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
            WHERE
                id = %s
                AND qwen_status = 'pending'
            """,
            (
                row["id"],
            ),
        )

        conn.commit()

        return row

# ============================================================
# SAVE RESULT
# ============================================================

def mark_done(
    conn,
    db_id,
    result,
    elapsed,
):
    """
    Записывает результат Qwen в ту же запись photos.

    Связь:
        PostgreSQL id
            ↓
        photo_id
            ↓
        Grid

    Qwen никогда не создаёт новый объект фотографии.
    """

    text_json = result.get(
        "text",
        [],
    )

    colors_json = result.get(
        "colors",
        [],
    )

    objects_json = result.get(
        "objects",
        [],
    )

    environment_json = result.get(
        "environment",
        {},
    )

    image_quality_json = result.get(
        "image_quality",
        {},
    )

    camera_view_json = result.get(
        "camera_view",
        {},
    )

    scene_objects_json = result.get(
        "objects",
        [],
    )

    analysis_quality_json = result.get(
        "analysis_quality",
        {},
    )

    raw_json = dict(
        result
    )

    raw_json.pop(
        "_time_sec",
        None,
    )

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
                scene_objects_json = %s::jsonb,
                analysis_quality_json = %s::jsonb,
                raw_json = %s::jsonb,

                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP

            WHERE
                id = %s
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
                    scene_objects_json,
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
    """
    Ошибка Qwen меняет только qwen_status.
    """

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

def image64(path):
    with open(
        path,
        "rb",
    ) as f:

        return base64.b64encode(
            f.read()
        ).decode()

# ============================================================
# QWEN
# ============================================================

def ask(path):

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

        elapsed = (
            time.time()
            - started
        )

        if response.status_code != 200:

            raise RuntimeError(
                response.text
            )

        data = response.json()

        stats = {
            "total_duration_sec": round(
                data.get(
                    "total_duration",
                    0,
                ) / 1e9,
                2,
            ),

            "load_duration_sec": round(
                data.get(
                    "load_duration",
                    0,
                ) / 1e9,
                2,
            ),

            "prompt_eval_duration_sec": round(
                data.get(
                    "prompt_eval_duration",
                    0,
                ) / 1e9,
                2,
            ),

            "eval_duration_sec": round(
                data.get(
                    "eval_duration",
                    0,
                ) / 1e9,
                2,
            ),

            "prompt_eval_count": data.get(
                "prompt_eval_count"
            ),

            "eval_count": data.get(
                "eval_count"
            ),
        }

        print(
            "[OLLAMA]",
            stats,
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
                    "description",
                    "",
                )
                or ""
            ).strip()

            if description:

                result["_time_sec"] = round(
                    elapsed,
                    2,
                )

                return result

            if attempt < max_attempts:

                print(
                    "[QWEN RETRY]"
                    " description empty"
                    " | attempt:",
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

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Process only N pending photos"
        ),
    )

    args = parser.parse_args()

    print("=" * 80)
    print(
        "QWEN3-VL 4B — DATABASE WORKER"
    )
    print("=" * 80)

    print(
        "MODEL:",
        MODEL,
    )

    print(
        "DATABASE:",
        DB_CONFIG["dbname"],
    )

    print()

    conn = get_connection()

    reset_processing(
        conn
    )

    processed = 0
    errors = 0

    try:

        # ----------------------------------------------------
        # QUEUE INFO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # LOOP
        # ----------------------------------------------------

        while True:

            if (
                args.limit is not None
                and processed >= args.limit
            ):

                print(
                    "LIMIT REACHED:",
                    args.limit,
                )

                break

            row = claim_photo(
                conn
            )

            if row is None:

                print(
                    "QWEN QUEUE EMPTY"
                )

                break

            db_id = row["id"]

            photo_id = row[
                "photo_id"
            ]

            initial_id = row[
                "initial_id"
            ]

            source_path = row[
                "source_path"
            ]

            print(
                "=" * 80
            )

            print(
                f"[{processed + 1}]",
                photo_id,
            )

            print(
                "INITIAL:",
                initial_id,
            )

            print(
                "SOURCE:",
                source_path,
            )

            started = time.time()

            try:

                path = Path(
                    source_path
                )

                if not path.exists():

                    raise FileNotFoundError(
                        f"Photo not found: {path}"
                    )

                if not path.is_file():

                    raise FileNotFoundError(
                        f"Not a file: {path}"
                    )

                result = ask(
                    path
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
                    "OK",
                    "| photo_id:",
                    photo_id,
                    "| time:",
                    round(
                        elapsed,
                        2,
                    ),
                    "sec",
                )

                print(
                    "CLIENT:",
                    result.get(
                        "client",
                        "",
                    ),
                )

                print(
                    "BRAND:",
                    result.get(
                        "brand",
                        "",
                    ),
                )

                print(
                    "CONFIDENCE:",
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
                    "ERROR:",
                    exc,
                    "| time:",
                    round(
                        elapsed,
                        2,
                    ),
                    "sec",
                )

                try:

                    mark_error(
                        conn,
                        db_id,
                        exc,
                    )

                except Exception as db_error:

                    print(
                        "DB ERROR:",
                        db_error,
                    )

    finally:

        conn.close()

        print()
        print("=" * 80)
        print(
            "QWEN WORKER STOPPED"
        )
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

---

### 🤖 **Assistant** — 2026-08-18 23:48:14

Да. Сейчас у нас уже правильная основа:

**`photo_id` создаётся в ingest ДО DINO и Qwen**, а дальше оба worker работают с одной строкой `photos`.

Следующий слой — **режим запуска процесса**. Его лучше делать отдельно от DINO/Qwen worker, чтобы worker'ы не знали, кто их запустил.

### Фиксируем три режима

| Режим | Что происходит | Кнопка «Запустить» |
|---|---|---|
| **Ручной** | процесс запускается кнопкой в UI | **активна** |
| **Автоматический** | запуск в заданное время | **неактивна** |
| **Watcher** | постоянно ждёт новые файлы | **неактивна** |

При **«Остановить»**:

```text
любой режим
     ↓
STOP
     ↓
остановить ingest / DINO / Qwen
     ↓
режим = manual
     ↓
кнопка Запустить = active
```

И ещё важное правило:

```text
Watcher = эксклюзивный режим
```

То есть при выборе Watcher нельзя одновременно иметь расписание или ручной запуск.

---

## Сейчас не трогаем `photos`

В таблице `photos` уже достаточно состояния отдельных этапов:

```text
photo_id
initial_id
address_id

dino_status
qwen_status
sort_status
preview_status
```

А **режим запуска** должен жить отдельно.

Я предлагаю таблицу:

```text
pipeline_control
```

с одной строкой состояния.

### Структура

```sql
CREATE TABLE IF NOT EXISTS pipeline_control (
    id INTEGER PRIMARY KEY DEFAULT 1,

    mode TEXT NOT NULL DEFAULT 'manual',

    auto_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    auto_time TIME,

    watcher_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    watcher_path TEXT,

    running BOOLEAN NOT NULL DEFAULT FALSE,

    started_at TIMESTAMP,
    stopped_at TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pipeline_control_singleton
        CHECK (id = 1),

    CONSTRAINT pipeline_control_mode
        CHECK (mode IN (
            'manual',
            'automatic',
            'watcher'
        ))
);
```

И сразу создать единственную строку:

```sql
INSERT INTO pipeline_control (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;
```

---

## Но я бы добавил ещё одно поле

Чтобы UI и launcher не гадали, почему процесс остановился:

```sql
ALTER TABLE pipeline_control
ADD COLUMN IF NOT EXISTS stop_requested BOOLEAN NOT NULL DEFAULT FALSE;
```

Получаем:

```text
mode
running
stop_requested
```

Это уже нормальная машина состояний.

Например:

### Ручной

```text
mode = manual
running = false
stop_requested = false
```

Нажали **Запустить**:

```text
mode = manual
running = true
stop_requested = false
```

### Автомат

```text
mode = automatic
running = false
stop_requested = false
auto_time = 23:00
```

В 23:00 launcher делает:

```text
running = true
```

### Watcher

```text
mode = watcher
running = true
watcher_enabled = true
```

Watcher живёт постоянно.

---

# Следующий шаг

Я предлагаю сейчас **не переписывать worker'ы ещё раз**.

Сначала создаём центральный контроллер:

```text
app/pipeline/
    controller.py       ← новое
    modes.py            ← новое
    queue.py            ← уже есть
    worker.py           ← уже есть
```

Он будет единственным местом, которое знает:

```text
manual
automatic
watcher
```

и запускает:

```text
photo_ingest
       ↓
DINO
       ↓
Qwen
       ↓
sort
       ↓
preview
```

При этом `photo_id` уже существует до попадания фотографии в DINO/Qwen:

```text
                    ┌── DINO ──→ address_id
PHOTO
  │
  └→ ingest
       │
       └→ photo_id
             │
             ├──→ DINO
             │
             └──→ QWEN
                    │
                    └→ описание
                         │
                         └──────┐
                                ↓
                              GRID
```

**То есть архитектуру `photos` сейчас не ломаем.**

---

### Сначала выполни только это

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -h localhost -U lora -d photobase <<'SQL'

CREATE TABLE IF NOT EXISTS pipeline_control (
    id INTEGER PRIMARY KEY DEFAULT 1,

    mode TEXT NOT NULL DEFAULT 'manual',

    auto_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    auto_time TIME,

    watcher_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    watcher_path TEXT,

    running BOOLEAN NOT NULL DEFAULT FALSE,
    stop_requested BOOLEAN NOT NULL DEFAULT FALSE,

    started_at TIMESTAMP,
    stopped_at TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pipeline_control_singleton
        CHECK (id = 1),

    CONSTRAINT pipeline_control_mode
        CHECK (
            mode IN (
                'manual',
                'automatic',
                'watcher'
            )
        )
);

INSERT INTO pipeline_control (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

SQL
```

Потом:

```bash
psql -h localhost -U lora -d photobase -c '\d+ pipeline_control'
```

**Пришли вывод.** После этого дам следующий файл — `app/pipeline/modes.py`, затем `controller.py`, и уже после этого подключим три режима к UI с tooltip'ами и правильным поведением кнопок.

---

### 👤 **User** — 2026-08-18 23:48:44

ontrol"
     Column      |            Type             | Collation | Nullable |      Default      | Storage  | Compression | Stats target | Description 
-----------------+-----------------------------+-----------+----------+-------------------+----------+-------------+--------------+-------------
 id              | integer                     |           | not null | 1                 | plain    |             |              | 
 mode            | text                        |           | not null | 'manual'::text    | extended |             |              | 
 auto_enabled    | boolean                     |           | not null | false             | plain    |             |              | 
 auto_time       | time without time zone      |           |          |                   | plain    |             |              | 
 watcher_enabled | boolean                     |           | not null | false             | plain    |             |              | 
 watcher_path    | text                        |           |          |                   | extended |             |              | 
 running         | boolean                     |           | not null | false             | plain    |             |              | 
 stop_requested  | boolean                     |           | not null | false             | plain    |             |              | 
 started_at      | timestamp without time zone |           |          |         :

---

### 🤖 **Assistant** — 2026-08-18 23:48:45

Отлично. Таблица создана правильно. Дальше делаем **файлы слоя режимов**, не трогая пока UI.

### 1. Создаём `modes.py`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/pipeline/modes.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Optional

MODE_MANUAL = "manual"
MODE_AUTOMATIC = "automatic"
MODE_WATCHER = "watcher"

VALID_MODES = {
    MODE_MANUAL,
    MODE_AUTOMATIC,
    MODE_WATCHER,
}

@dataclass
class PipelineMode:
    mode: str = MODE_MANUAL

    auto_enabled: bool = False
    auto_time: Optional[time] = None

    watcher_enabled: bool = False
    watcher_path: Optional[str] = None

    running: bool = False
    stop_requested: bool = False

def validate_mode(mode: str) -> str:
    if mode not in VALID_MODES:
        raise ValueError(
            f"Unknown pipeline mode: {mode}"
        )

    return mode

def build_manual_mode() -> PipelineMode:
    return PipelineMode(
        mode=MODE_MANUAL,
        auto_enabled=False,
        auto_time=None,
        watcher_enabled=False,
        watcher_path=None,
        running=False,
        stop_requested=False,
    )

def build_automatic_mode(
    auto_time: time,
) -> PipelineMode:

    return PipelineMode(
        mode=MODE_AUTOMATIC,
        auto_enabled=True,
        auto_time=auto_time,
        watcher_enabled=False,
        watcher_path=None,
        running=False,
        stop_requested=False,
    )

def build_watcher_mode(
    watcher_path: str,
) -> PipelineMode:

    if not watcher_path:
        raise ValueError(
            "Watcher path is required"
        )

    return PipelineMode(
        mode=MODE_WATCHER,
        auto_enabled=False,
        auto_time=None,
        watcher_enabled=True,
        watcher_path=watcher_path,
        running=False,
        stop_requested=False,
    )

def can_manual_start(state: PipelineMode) -> bool:
    """
    Кнопка «Запустить» доступна только
    в ручном режиме.
    """

    return (
        state.mode == MODE_MANUAL
        and not state.running
    )

def can_stop(state: PipelineMode) -> bool:
    return state.running

def reset_to_manual() -> PipelineMode:
    """
    Полный возврат в ручной режим.

    Используется после нажатия «Остановить».
    """

    return build_manual_mode()
PY
```

---

### 2. Проверяем файл

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python -m py_compile app/pipeline/modes.py
```

Если команда ничего не вывела — всё хорошо.

---

## Что этот слой уже гарантирует

### Ручной

```text
mode = manual
```

→ кнопка **Запустить** активна.

### Автоматический

```text
mode = automatic
auto_enabled = true
auto_time = 23:00
```

→ кнопка **Запустить** неактивна.

### Watcher

```text
mode = watcher
watcher_enabled = true
watcher_path = ...
```

→ кнопка **Запустить** неактивна.

И главное:

```text
Watcher
   X
Automatic
   X
Manual
```

То есть одновременно существует **только один режим**.

---

## Следующий файл — `controller.py`

Он будет уже работать с `pipeline_control`:

```text
UI
 │
 ├── выбрать режим
 │
 ▼
controller.py
 │
 ├── set_manual()
 ├── set_automatic()
 ├── set_watcher()
 ├── start_manual()
 ├── request_stop()
 └── reset_to_manual()
```

А дальше уже подключим к нему реальные:

```text
photo_ingest
DINO
Qwen
sort
preview
watcher
scheduler
```

**Сейчас выполни `py_compile`. Если без ошибки — следующим сообщением дам точный `controller.py`.**

---

### 👤 **User** — 2026-08-18 23:49:12

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

cat > app/pipeline/modes.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Optional

MODE_MANUAL = "manual"
MODE_AUTOMATIC = "automatic"
MODE_WATCHER = "watcher"

VALID_MODES = {
    MODE_MANUAL,
    MODE_AUTOMATIC,
    MODE_WATCHER,
}

@dataclass
class PipelineMode:
PY  return build_manual_mode() «Остановить». bool:
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python -m py_compile app/pipeline/modes.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:49:13

Отлично. `modes.py` скомпилировался без ошибки.

Но по выводу терминала вижу важный момент: команда `cat` в сообщении отображается обрезанной в середине файла. Раз `py_compile` прошёл, синтаксически файл сейчас валидный, но **перед следующим слоем лучше убедиться, что содержимое полное**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat app/pipeline/modes.py
```

Пришли вывод целиком.

После этого делаем **`app/pipeline/controller.py`** — он будет единственной точкой управления `manual / automatic / watcher`, включая `stop → manual`.

---

### 👤 **User** — 2026-08-18 23:49:28

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat app/pipeline/modes.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Optional

MODE_MANUAL = "manual"
MODE_AUTOMATIC = "automatic"
MODE_WATCHER = "watcher"

VALID_MODES = {
    MODE_MANUAL,
    MODE_AUTOMATIC,
    MODE_WATCHER,
}

@dataclass
class PipelineMode:
    mode: str = MODE_MANUAL

    auto_enabled: bool = False
    auto_time: Optional[time] = None

    watcher_enabled: bool = False
    watcher_path: Optional[str] = None

    running: bool = False
    stop_requested: bool = False

def validate_mode(mode: str) -> str:
    if mode not in VALID_MODES:
        raise ValueError(
            f"Unknown pipeline mode: {mode}"
        )

    return mode

def build_manual_mode() -> PipelineMode:
    return PipelineMode(
        mode=MODE_MANUAL,
        auto_enabled=False,
        auto_time=None,
        watcher_enabled=False,
        watcher_path=None,
        running=False,
        stop_requested=False,
    )

def build_automatic_mode(
    auto_time: time,
) -> PipelineMode:

    return PipelineMode(
        mode=MODE_AUTOMATIC,
        auto_enabled=True,
        auto_time=auto_time,
        watcher_enabled=False,
        watcher_path=None,
        running=False,
        stop_requested=False,
    )

def build_watcher_mode(
    watcher_path: str,
) -> PipelineMode:

    if not watcher_path:
        raise ValueError(
            "Watcher path is required"
        )

    return PipelineMode(
        mode=MODE_WATCHER,
        auto_enabled=False,
        auto_time=None,
        watcher_enabled=True,
        watcher_path=watcher_path,
        running=False,
        stop_requested=False,
    )

def can_manual_start(state: PipelineMode) -> bool:
    """
    Кнопка «Запустить» доступна только
    в ручном режиме.
    """

    return (
        state.mode == MODE_MANUAL
        and not state.running
    )

def can_stop(state: PipelineMode) -> bool:
    return state.running

def reset_to_manual() -> PipelineMode:
    """
    Полный возврат в ручной режим.

    Используется после нажатия «Остановить».
    """

    return build_manual_mode()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

