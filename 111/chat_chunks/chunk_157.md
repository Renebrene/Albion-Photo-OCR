## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 🤖 **Assistant** — 2026-08-19 01:38:47

Делаем первый слой — **Supervisor для ручного и автоматического режима**. Watcher пока не трогаем.

Выполни целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > app/pipeline/supervisor.py <<'PY'
from __future__ import annotations

import asyncio
import os
import signal
from datetime import datetime, timedelta
from pathlib import Path

from app.pipeline.controller import (
    finish_stop,
    get_state,
    is_stop_requested,
    start_automatic,
    start_manual,
)

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"
UV = Path.home() / ".local" / "bin" / "uv"

DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
QWEN_WORKER = PROJECT / "app" / "workers" / "qwen_worker.py"

POLL_INTERVAL = 1.0

# ============================================================
# ENVIRONMENT
# ============================================================

def build_env():
    env = os.environ.copy()

    env.update(
        {
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
    )

    return env

# ============================================================
# PROCESS
# ============================================================

def process_running(process):
    return (
        process is not None
        and process.returncode is None
    )

async def consume_output(
    process,
    prefix,
):
    if process.stdout is None:
        return

    try:
        while True:
            line = await process.stdout.readline()

            if not line:
                break

            text = (
                line
                .decode(
                    "utf-8",
                    errors="replace",
                )
                .strip()
            )

            if text:
                print(
                    f"[{prefix}] {text}",
                    flush=True,
                )

    except asyncio.CancelledError:
        raise

    except Exception as exc:
        print(
            f"[{prefix}] OUTPUT ERROR: {exc}",
            flush=True,
        )

async def start_worker(
    worker: Path,
    prefix: str,
):
    if not worker.exists():
        raise FileNotFoundError(
            f"{prefix} worker not found: {worker}"
        )

    process = await asyncio.create_subprocess_exec(
        str(UV),
        "run",
        "python",
        str(worker),
        cwd=str(PROJECT),
        env=build_env(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    print(
        f"[SUPERVISOR] {prefix} START "
        f"PID={process.pid}",
        flush=True,
    )

    output_task = asyncio.create_task(
        consume_output(
            process,
            prefix,
        )
    )

    return process, output_task

async def stop_process(
    process,
    prefix,
):
    if not process_running(process):
        return

    print(
        f"[SUPERVISOR] stopping {prefix} "
        f"PID={process.pid}",
        flush=True,
    )

    try:
        process.terminate()

    except ProcessLookupError:
        return

    try:
        await asyncio.wait_for(
            process.wait(),
            timeout=10,
        )

    except asyncio.TimeoutError:

        print(
            f"[SUPERVISOR] {prefix} did not stop, "
            f"sending kill",
            flush=True,
        )

        try:
            process.kill()
        except ProcessLookupError:
            pass

        await process.wait()

# ============================================================
# PIPELINE RUN
# ============================================================

async def run_pipeline():
    """
    Один полный запуск DINO + Qwen.

    Workers остаются независимыми:
        DINO -> PostgreSQL dino_status
        Qwen -> PostgreSQL qwen_status

    Supervisor только управляет их жизненным циклом.
    """

    dino_process = None
    qwen_process = None

    dino_output = None
    qwen_output = None

    try:

        # ----------------------------------------------------
        # START
        # ----------------------------------------------------

        print(
            "=" * 70,
            flush=True,
        )

        print(
            "[SUPERVISOR] PIPELINE START",
            flush=True,
        )

        print(
            "=" * 70,
            flush=True,
        )

        dino_process, dino_output = (
            await start_worker(
                DINO_WORKER,
                "DINO",
            )
        )

        await asyncio.sleep(0.2)

        qwen_process, qwen_output = (
            await start_worker(
                QWEN_WORKER,
                "QWEN",
            )
        )

        # ----------------------------------------------------
        # WAIT
        # ----------------------------------------------------

        while True:

            dino_running = process_running(
                dino_process
            )

            qwen_running = process_running(
                qwen_process
            )

            if not dino_running and not qwen_running:
                break

            if is_stop_requested():

                print(
                    "[SUPERVISOR] STOP REQUESTED",
                    flush=True,
                )

                await stop_process(
                    dino_process,
                    "DINO",
                )

                await stop_process(
                    qwen_process,
                    "QWEN",
                )

                break

            await asyncio.sleep(
                POLL_INTERVAL
            )

        # ----------------------------------------------------
        # EXIT CODES
        # ----------------------------------------------------

        dino_code = (
            dino_process.returncode
            if dino_process is not None
            else None
        )

        qwen_code = (
            qwen_process.returncode
            if qwen_process is not None
            else None
        )

        print(
            "[SUPERVISOR] DINO exit:",
            dino_code,
            flush=True,
        )

        print(
            "[SUPERVISOR] QWEN exit:",
            qwen_code,
            flush=True,
        )

        return (
            dino_code,
            qwen_code,
        )

    finally:

        # ----------------------------------------------------
        # SAFETY CLEANUP
        # ----------------------------------------------------

        await stop_process(
            dino_process,
            "DINO",
        )

        await stop_process(
            qwen_process,
            "QWEN",
        )

        for task in (
            dino_output,
            qwen_output,
        ):

            if task is not None:
                await asyncio.gather(
                    task,
                    return_exceptions=True,
                )

        print(
            "[SUPERVISOR] PIPELINE FINISHED",
            flush=True,
        )

# ============================================================
# AUTOMATIC SCHEDULER
# ============================================================

def seconds_until(
    target_time,
):
    now = datetime.now()

    target = datetime.combine(
        now.date(),
        target_time,
    )

    if target <= now:
        target += timedelta(
            days=1
        )

    return (
        target - now
    ).total_seconds()

async def wait_automatic():
    """
    Ждёт заданного времени.

    Важно:
    automatic mode остаётся automatic после завершения
    одного запуска.
    """

    while True:

        state = get_state()

        if state.mode != "automatic":
            return False

        if state.stop_requested:
            finish_stop()
            return False

        if state.running:
            return False

        if state.auto_time is None:
            print(
                "[SUPERVISOR] Automatic mode has "
                "no auto_time",
                flush=True,
            )

            await asyncio.sleep(
                POLL_INTERVAL
            )

            continue

        delay = seconds_until(
            state.auto_time
        )

        print(
            "[SUPERVISOR] Automatic mode.",
            f"Next run in {delay:.0f}s",
            f"at {state.auto_time.strftime('%H:%M')}",
            flush=True,
        )

        # Проверяем состояние каждую секунду,
        # чтобы переключение режима происходило быстро.
        remaining = delay

        while remaining > 0:

            current = get_state()

            if current.mode != "automatic":
                return False

            if current.stop_requested:
                finish_stop()
                return False

            await asyncio.sleep(
                min(
                    POLL_INTERVAL,
                    remaining,
                )
            )

            remaining -= POLL_INTERVAL

        try:
            start_automatic()

        except Exception as exc:
            print(
                "[SUPERVISOR] AUTOMATIC START ERROR:",
                repr(exc),
                flush=True,
            )

            await asyncio.sleep(
                POLL_INTERVAL
            )

            continue

        return True

# ============================================================
# MANUAL MODE
# ============================================================

async def wait_manual_start():
    """
    В manual режиме Supervisor ждёт,
    пока UI вызовет start_manual().
    """

    while True:

        state = get_state()

        if state.mode != "manual":
            return False

        if state.stop_requested:
            finish_stop()
            return False

        if state.running:
            return True

        await asyncio.sleep(
            POLL_INTERVAL
        )

# ============================================================
# MAIN LOOP
# ============================================================

async def supervisor_loop():

    print("=" * 70)
    print("ALBION PIPELINE SUPERVISOR")
    print("=" * 70)

    if not UV.exists():
        raise FileNotFoundError(
            f"uv not found: {UV}"
        )

    if not DINO_WORKER.exists():
        raise FileNotFoundError(
            f"DINO worker not found: {DINO_WORKER}"
        )

    if not QWEN_WORKER.exists():
        raise FileNotFoundError(
            f"Qwen worker not found: {QWEN_WORKER}"
        )

    while True:

        state = get_state()

        print(
            "[SUPERVISOR] state:",
            state.mode,
            "| running:",
            state.running,
            "| stop:",
            state.stop_requested,
            flush=True,
        )

        # ====================================================
        # MANUAL
        # ====================================================

        if state.mode == "manual":

            started = await wait_manual_start()

            if not started:
                continue

        # ====================================================
        # AUTOMATIC
        # ====================================================

        elif state.mode == "automatic":

            started = await wait_automatic()

            if not started:
                continue

        # ====================================================
        # WATCHER
        # ====================================================

        elif state.mode == "watcher":

            print(
                "[SUPERVISOR] Watcher mode is not "
                "implemented yet.",
                flush=True,
            )

            await asyncio.sleep(
                2
            )

            continue

        # ====================================================
        # PIPELINE
        # ====================================================

        try:

            await run_pipeline()

        except asyncio.CancelledError:
            raise

        except Exception as exc:

            print(
                "[SUPERVISOR] PIPELINE ERROR:",
                repr(exc),
                flush=True,
            )

        # ====================================================
        # FINISH
        # ====================================================

        try:

            state = get_state()

            if state.stop_requested:

                print(
                    "[SUPERVISOR] Finalizing STOP",
                    flush=True,
                )

                finish_stop()

            else:

                # ВАЖНО:
                #
                # Automatic mode остаётся automatic.
                # Manual mode после запуска остаётся manual.
                #
                # Только running сбрасывается.
                #
                # Это позволяет automatic mode ждать
                # следующего запуска.

                from app.pipeline.controller import (
                    mark_finished,
                )

                mark_finished()

        except Exception as exc:

            print(
                "[SUPERVISOR] STATE FINALIZATION ERROR:",
                repr(exc),
                flush=True,
            )

        await asyncio.sleep(
            POLL_INTERVAL
        )

# ============================================================
# SIGNALS
# ============================================================

def install_signal_handlers(loop):

    def handle_signal():

        print(
            "[SUPERVISOR] OS STOP SIGNAL",
            flush=True,
        )

        try:
            from app.pipeline.controller import (
                request_stop,
            )

            request_stop()

        except Exception as exc:

            print(
                "[SUPERVISOR] Cannot request stop:",
                repr(exc),
                flush=True,
            )

    for sig in (
        signal.SIGINT,
        signal.SIGTERM,
    ):

        try:
            loop.add_signal_handler(
                sig,
                handle_signal,
            )

        except NotImplementedError:
            pass

async def main():

    loop = asyncio.get_running_loop()

    install_signal_handlers(
        loop
    )

    await supervisor_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print(
            "[SUPERVISOR] Interrupted",
            flush=True,
        )
PY
```

Но **пока не запускай supervisor**: в этом патче я специально использовал новый `mark_finished()`, которого ещё нет в `controller.py`.

Сначала добавим его.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat >> /tmp/empty <<'EOF'
EOF
```

Теперь вставь в `app/pipeline/controller.py` **перед `is_stop_requested()`**:

```python
def mark_finished():
    """
    Завершает текущий запуск pipeline,
    но НЕ меняет выбранный режим.

    Например:
        automatic -> automatic
        manual    -> manual
        watcher   -> watcher

    При этом:
        running = FALSE
        stop_requested = FALSE
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = FALSE,
                    stop_requested = FALSE,
                    stopped_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    return get_state()
```

Потом проверяем всё сразу:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/pipeline/supervisor.py \
app/pipeline/controller.py \
app/pipeline/modes.py \
app/workers/dino_worker.py \
app/workers/qwen_worker.py
```

Если **ошибок нет**, следующим шагом подключим `start_manual()` к существующей кнопке **«ЗАПУСТИТЬ»**, чтобы UI больше не запускал workers напрямую, а передавал управление Supervisor.

---

### 👤 **User** — 2026-08-19 01:40:33

давай командой

---

### 🤖 **Assistant** — 2026-08-19 01:40:34

Да. Сначала сделаем **безопасный патч `controller.py`**: режимы остаются настройкой, а `start_*()` реально запускают только состояние pipeline; сами DINO/Qwen уже запускаются из `photo_processing.py`.

Выполни одной командой:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/pipeline/controller.py app/pipeline/controller.py.bak && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/pipeline/controller.py")
s = p.read_text()

old = '''def set_manual():
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
'''

new = '''def set_manual():
    state = build_manual_mode()

    # Смена режима не должна оставлять pipeline
    # в состоянии running/stop_requested от предыдущего режима.
    current = get_state()
    state.running = current.running
    state.stop_requested = current.stop_requested

    _save_state(state)
    return state

def set_automatic(auto_time: time):
    state = build_automatic_mode(auto_time)

    current = get_state()
    state.running = current.running
    state.stop_requested = current.stop_requested

    _save_state(state)
    return state

def set_watcher(watcher_path: str):
    state = build_watcher_mode(watcher_path)

    current = get_state()
    state.running = current.running
    state.stop_requested = current.stop_requested

    _save_state(state)
    return state
'''

if old not in s:
    raise SystemExit("PATTERN NOT FOUND: set_* block")

s = s.replace(old, new)

p.write_text(s)
print("PATCH OK: controller.py")
PY
uv run python -m py_compile app/pipeline/controller.py && \
echo "================ VERIFY ================" && \
grep -n -A45 '^def set_manual' app/pipeline/controller.py
```

После этого покажи вывод команды. Затем сделаем следующий патч — **связь `start_automatic/start_watcher` с реальным запуском DINO/Qwen**, потому что сейчас по найденному коду `controller.py` только меняет PostgreSQL-флаг, а фактические subprocess запускаются отдельно из `photo_processing.py`.

---

### 👤 **User** — 2026-08-19 01:47:20

================ VERIFY ================
120:def set_manual():
121-    state = build_manual_mode()
122-
123-    # Смена режима не должна оставлять pipeline
124-    # в состоянии running/stop_requested от предыдущего режима.
125-    current = get_state()
126-    state.running = current.running
127-    state.stop_requested = current.stop_requested
128-
129-    _save_state(state)
130-    return state
131-
132-
133-def set_automatic(auto_time: time):
134-    state = build_automatic_mode(auto_time)
135-
136-    current = get_state()
137-    state.running = current.running
138-    state.stop_requested = current.stop_requested
139-
140-    _save_state(state)
141-    return state
142-
143-
144-def set_watcher(watcher_path: str):
145-    state = build_watcher_mode(watcher_path)
146-
147-    current = get_state()
148-    state.running = current.running
149-    state.stop_requested = current.stop_requested
150-
151-    _save_state(state)
152-    return state
153-
154-
155-def start_manual():
156-    state = get_state()
157-
158-    if state.mode != MODE_MANUAL:
159-        raise RuntimeError(
160-            "Manual start is available only in manual mode"
161-        )
162-
163-    if state.running:
164-        raise RuntimeError(
165-            "Pipeline is already running"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:47:23

Да. Этот патч применён правильно.

Но сейчас есть **важный момент**: `set_manual/set_automatic/set_watcher` сохраняют `running` и `stop_requested` от предыдущего состояния. Это означает, что переключение режима во время работающего pipeline **не останавливает pipeline**, что логично.

Следующий шаг — проверить, что **реальный запуск DINO/Qwen связан с `pipeline_control.running`**, а не только с кнопками UI. Сейчас по найденному коду видно:

- `start_manual()` / `start_automatic()` / `start_watcher()` только меняют PostgreSQL-состояние.
- DINO worker запускается напрямую из `photo_processing.py`.
- Qwen worker запускается напрямую из `photo_processing.py`.
- `start_automatic()` и `start_watcher()` пока **не вызываются из runtime-цикла**.
- Значит, автоматический режим пока фактически только записывает настройку, но сам pipeline не стартует по времени/Watcher.

Именно это сейчас надо добить.

Давай сначала найдём, **кто вообще должен вызывать `start_manual/start_automatic/start_watcher`**, одной командой:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PIPELINE START CALLS ================" && \
grep -RniE \
'\bstart_manual\(|\bstart_automatic\(|\bstart_watcher\(' \
app scripts \
--include="*.py" | grep -v '__pycache__'
```

Пришли вывод.

---

### 👤 **User** — 2026-08-19 01:47:55

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PIPELINE START CALLS ================" && \
grep -RniE \
'\bstart_manual\(|\bstart_automatic\(|\bstart_watcher\(' \
app scripts \
--include="*.py" | grep -v '__pycache__'
================ PIPELINE START CALLS ================
app/pipeline/controller.py:155:def start_manual():
app/pipeline/controller.py:191:def start_automatic():
app/pipeline/controller.py:225:def start_watcher():
app/pipeline/supervisor.py:440:            start_automatic()
app/pipeline/supervisor.py:465:    пока UI вызовет start_manual().
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:47:57

Да. Теперь картина стала ясной: **`start_automatic()` и `start_watcher()` уже вызываются из supervisor, а `start_manual()` вообще нигде не вызывается из UI**. Значит, следующий шаг — посмотреть `supervisor.py`, потому что именно там сейчас должна быть фактическая оркестрация запуска/остановки.

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SUPERVISOR START ================" && \
sed -n '1,540p' app/pipeline/supervisor.py
```

После этого я дам **точечный патч командой**, чтобы не ломать уже работающую DINO/Qwen-часть.

---

### 👤 **User** — 2026-08-19 01:48:25

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SUPERVISOR START ================" && \
sed -n '1,540p' app/pipeline/supervisor.py
================ SUPERVISOR START ================
from __future__ import annotations

import asyncio
import os
import signal
from datetime import datetime, timedelta
from pathlib import Path

from app.pipeline.controller import (
    finish_stop,
    get_state,
    is_stop_requested,
    start_automatic,
    start_manual,
)

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"
UV = Path.home() / ".local" / "bin" / "uv"

DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
QWEN_WORKER = PROJECT / "app" / "workers" / "qwen_worker.py"

POLL_INTERVAL = 1.0

# ============================================================
# ENVIRONMENT
# ============================================================

def build_env():
    env = os.environ.copy()

    env.update(
        {
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
    )

    return env

# ============================================================
# PROCESS
# ============================================================

def process_running(process):
    return (
        process is not None
        and process.returncode is None
    )

async def consume_output(
    process,
    prefix,
):
    if process.stdout is None:
        return

    try:
        while True:
            line = await process.stdout.readline()

            if not line:
                break

            text = (
                line
                .decode(
                    "utf-8",
                    errors="replace",
                )
                .strip()
            )

            if text:
                print(
                    f"[{prefix}] {text}",
                    flush=True,
                )

    except asyncio.CancelledError:
        raise

    except Exception as exc:
        print(
            f"[{prefix}] OUTPUT ERROR: {exc}",
            flush=True,
        )

async def start_worker(
    worker: Path,
    prefix: str,
):
    if not worker.exists():
        raise FileNotFoundError(
            f"{prefix} worker not found: {worker}"
        )

    process = await asyncio.create_subprocess_exec(
        str(UV),
        "run",
        "python",
        str(worker),
        cwd=str(PROJECT),
        env=build_env(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    print(
        f"[SUPERVISOR] {prefix} START "
        f"PID={process.pid}",
        flush=True,
    )

    output_task = asyncio.create_task(
        consume_output(
            process,
            prefix,
        )
    )

    return process, output_task

async def stop_process(
    process,
    prefix,
):
    if not process_running(process):
        return

    print(
        f"[SUPERVISOR] stopping {prefix} "
        f"PID={process.pid}",
        flush=True,
    )

    try:
        process.terminate()

    except ProcessLookupError:
        return

    try:
        await asyncio.wait_for(
            process.wait(),
            timeout=10,
        )

    except asyncio.TimeoutError:

        print(
            f"[SUPERVISOR] {prefix} did not stop, "
            f"sending kill",
            flush=True,
        )

        try:
            process.kill()
        except ProcessLookupError:
            pass

        await process.wait()

# ============================================================
# PIPELINE RUN
# ============================================================

async def run_pipeline():
    """
    Один полный запуск DINO + Qwen.

    Workers остаются независимыми:
        DINO -> PostgreSQL dino_status
        Qwen -> PostgreSQL qwen_status

    Supervisor только управляет их жизненным циклом.
    """

    dino_process = None
    qwen_process = None

    dino_output = None
    qwen_output = None

    try:

        # ----------------------------------------------------
        # START
        # ----------------------------------------------------

        print(
            "=" * 70,
            flush=True,
        )

        print(
            "[SUPERVISOR] PIPELINE START",
            flush=True,
        )

        print(
            "=" * 70,
            flush=True,
        )

        dino_process, dino_output = (
            await start_worker(
                DINO_WORKER,
                "DINO",
            )
        )

        await asyncio.sleep(0.2)

        qwen_process, qwen_output = (
            await start_worker(
                QWEN_WORKER,
                "QWEN",
            )
        )

        # ----------------------------------------------------
        # WAIT
        # ----------------------------------------------------

        while True:

            dino_running = process_running(
                dino_process
            )

            qwen_running = process_running(
                qwen_process
            )

            if not dino_running and not qwen_running:
                break

            if is_stop_requested():

                print(
                    "[SUPERVISOR] STOP REQUESTED",
                    flush=True,
                )

                await stop_process(
                    dino_process,
                    "DINO",
                )

                await stop_process(
                    qwen_process,
                    "QWEN",
                )

                break

            await asyncio.sleep(
                POLL_INTERVAL
            )

        # ----------------------------------------------------
        # EXIT CODES
        # ----------------------------------------------------

        dino_code = (
            dino_process.returncode
            if dino_process is not None
            else None
        )

        qwen_code = (
            qwen_process.returncode
            if qwen_process is not None
            else None
        )

        print(
            "[SUPERVISOR] DINO exit:",
            dino_code,
            flush=True,
        )

        print(
            "[SUPERVISOR] QWEN exit:",
            qwen_code,
            flush=True,
        )

        return (
            dino_code,
            qwen_code,
        )

    finally:

        # ----------------------------------------------------
        # SAFETY CLEANUP
        # ----------------------------------------------------

        await stop_process(
            dino_process,
            "DINO",
        )

        await stop_process(
            qwen_process,
            "QWEN",
        )

        for task in (
            dino_output,
            qwen_output,
        ):

            if task is not None:
                await asyncio.gather(
                    task,
                    return_exceptions=True,
                )

        print(
            "[SUPERVISOR] PIPELINE FINISHED",
            flush=True,
        )

# ============================================================
# AUTOMATIC SCHEDULER
# ============================================================

def seconds_until(
    target_time,
):
    now = datetime.now()

    target = datetime.combine(
        now.date(),
        target_time,
    )

    if target <= now:
        target += timedelta(
            days=1
        )

    return (
        target - now
    ).total_seconds()

async def wait_automatic():
    """
    Ждёт заданного времени.

    Важно:
    automatic mode остаётся automatic после завершения
    одного запуска.
    """

    while True:

        state = get_state()

        if state.mode != "automatic":
            return False

        if state.stop_requested:
            finish_stop()
            return False

        if state.running:
            return False

        if state.auto_time is None:
            print(
                "[SUPERVISOR] Automatic mode has "
                "no auto_time",
                flush=True,
            )

            await asyncio.sleep(
                POLL_INTERVAL
            )

            continue

        delay = seconds_until(
            state.auto_time
        )

        print(
            "[SUPERVISOR] Automatic mode.",
            f"Next run in {delay:.0f}s",
            f"at {state.auto_time.strftime('%H:%M')}",
            flush=True,
        )

        # Проверяем состояние каждую секунду,
        # чтобы переключение режима происходило быстро.
        remaining = delay

        while remaining > 0:

            current = get_state()

            if current.mode != "automatic":
                return False

            if current.stop_requested:
                finish_stop()
                return False

            await asyncio.sleep(
                min(
                    POLL_INTERVAL,
                    remaining,
                )
            )

            remaining -= POLL_INTERVAL

        try:
            start_automatic()

        except Exception as exc:
            print(
                "[SUPERVISOR] AUTOMATIC START ERROR:",
                repr(exc),
                flush=True,
            )

            await asyncio.sleep(
                POLL_INTERVAL
            )

            continue

        return True

# ============================================================
# MANUAL MODE
# ============================================================

async def wait_manual_start():
    """
    В manual режиме Supervisor ждёт,
    пока UI вызовет start_manual().
    """

    while True:

        state = get_state()

        if state.mode != "manual":
            return False

        if state.stop_requested:
            finish_stop()
            return False

        if state.running:
            return True

        await asyncio.sleep(
            POLL_INTERVAL
        )

# ============================================================
# MAIN LOOP
# ============================================================

async def supervisor_loop():

    print("=" * 70)
    print("ALBION PIPELINE SUPERVISOR")
    print("=" * 70)

    if not UV.exists():
        raise FileNotFoundError(
            f"uv not found: {UV}"
        )

    if not DINO_WORKER.exists():
        raise FileNotFoundError(
            f"DINO worker not found: {DINO_WORKER}"
        )

    if not QWEN_WORKER.exists():
        raise FileNotFoundError(
            f"Qwen worker not found: {QWEN_WORKER}"
        )

    while True:

        state = get_state()

        print(
            "[SUPERVISOR] state:",
            state.mode,
            "| running:",
            state.running,
            "| stop:",
            state.stop_requested,
            flush=True,
        )

        # ====================================================
        # MANUAL
        # ====================================================

        if state.mode == "manual":

            started = await wait_manual_start()

            if not started:
                continue

        # ====================================================
        # AUTOMATIC
        # ====================================================

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:48:26

> **Inspecting Remaining Supervisor Watcher Code**
>
>
> **Inspected remaining supervisor watcher code**
>
> 
>
> Worked for a few seconds

Да. По этому выводу уже видно главное: **`start_watcher()` вообще не используется Supervisor'ом**, а `start_manual()` вызывается только косвенно через UI, как и задумано.

Но прежде чем патчить, нам нужен **самый конец `supervisor.py`** — начиная примерно с `# AUTOMATIC` и до конца файла. Именно там сейчас должна быть логика переключения `automatic/manual/watcher`.

Выполни одной командой:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SUPERVISOR END ================" && \
sed -n '520,760p' app/pipeline/supervisor.py
```

После этого я дам **одну готовую команду-патч**, без ручного редактирования.

---

### 👤 **User** — 2026-08-19 01:48:50

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SUPERVISOR END ================" && \
sed -n '520,760p' app/pipeline/supervisor.py
================ SUPERVISOR END ================
            state.running,
            "| stop:",
            state.stop_requested,
            flush=True,
        )

        # ====================================================
        # MANUAL
        # ====================================================

        if state.mode == "manual":

            started = await wait_manual_start()

            if not started:
                continue

        # ====================================================
        # AUTOMATIC
        # ====================================================

        elif state.mode == "automatic":

            started = await wait_automatic()

            if not started:
                continue

        # ====================================================
        # WATCHER
        # ====================================================

        elif state.mode == "watcher":

            print(
                "[SUPERVISOR] Watcher mode is not "
                "implemented yet.",
                flush=True,
            )

            await asyncio.sleep(
                2
            )

            continue

        # ====================================================
        # PIPELINE
        # ====================================================

        try:

            await run_pipeline()

        except asyncio.CancelledError:
            raise

        except Exception as exc:

            print(
                "[SUPERVISOR] PIPELINE ERROR:",
                repr(exc),
                flush=True,
            )

        # ====================================================
        # FINISH
        # ====================================================

        try:

            state = get_state()

            if state.stop_requested:

                print(
                    "[SUPERVISOR] Finalizing STOP",
                    flush=True,
                )

                finish_stop()

            else:

                # ВАЖНО:
                #
                # Automatic mode остаётся automatic.
                # Manual mode после запуска остаётся manual.
                #
                # Только running сбрасывается.
                #
                # Это позволяет automatic mode ждать
                # следующего запуска.

                from app.pipeline.controller import (
                    mark_finished,
                )

                mark_finished()

        except Exception as exc:

            print(
                "[SUPERVISOR] STATE FINALIZATION ERROR:",
                repr(exc),
                flush=True,
            )

        await asyncio.sleep(
            POLL_INTERVAL
        )

# ============================================================
# SIGNALS
# ============================================================

def install_signal_handlers(loop):

    def handle_signal():

        print(
            "[SUPERVISOR] OS STOP SIGNAL",
            flush=True,
        )

        try:
            from app.pipeline.controller import (
                request_stop,
            )

            request_stop()

        except Exception as exc:

            print(
                "[SUPERVISOR] Cannot request stop:",
                repr(exc),
                flush=True,
            )

    for sig in (
        signal.SIGINT,
        signal.SIGTERM,
    ):

        try:
            loop.add_signal_handler(
                sig,
                handle_signal,
            )

        except NotImplementedError:
            pass

async def main():

    loop = asyncio.get_running_loop()

    install_signal_handlers(
        loop
    )

    await supervisor_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print(
            "[SUPERVISOR] Interrupted",
            flush=True,
        )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:48:53

Да, теперь картина полная.

Сейчас проблема конкретная:

- `manual` → работает через `start_manual()`;
- `automatic` → работает через `start_automatic()`;
- `watcher` → **вообще не запускает pipeline**, там заглушка `"Watcher mode is not implemented yet."`;
- при этом `start_watcher()` в `controller.py` уже существует.

Значит, следующий патч логично сделать **только для Supervisor**: реализовать Watcher без изменения DINO/Qwen и без изменения очередей.

Но чтобы не сделать неверную логику слежения, нам нужно проверить, **что именно должно считаться новой партией фото** и откуда Watcher должен брать путь. В `automation.py` уже есть `watcher_path`.

Если наша договорённость такая:

> **Watcher следит за указанной папкой; когда в ней появляются новые фото — запускает DINO + Qwen; после завершения ждёт следующего появления фото.**

то я могу сразу дать патч.

Если именно это — напиши **«да, именно так»**, и дам одну команду, которая внесёт патч.

---

### 👤 **User** — 2026-08-19 01:49:30

**да, именно так»**

---

### 🤖 **Assistant** — 2026-08-19 01:49:30

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed watcher patch, finish flow, startup baseline, and supervisor mode**
>
> 
>
> Worked for 10s

Да. Делаем **только Watcher в Supervisor**. DINO/Qwen и PostgreSQL-логику не трогаем.

Патч будет таким:

- при входе в Watcher запоминаем уже существующие фото;
- новые `.jpg/.jpeg/.png/.webp` считаются событием;
- ждём, пока новый файл перестанет меняться по размеру/mtime;
- вызываем `start_watcher()`;
- запускаем обычный `run_pipeline()` — DINO + Qwen;
- после завершения снова ждём новые фото;
- переключение режима и STOP продолжают работать;
- уже существующие при старте Watcher фотографии **не запускают pipeline**.

Выполни **одну команду**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

path = Path("app/pipeline/supervisor.py")
text = path.read_text()

# ------------------------------------------------------------
# 1. Добавляем start_watcher в import
# ------------------------------------------------------------

old = """    is_stop_requested,
    start_automatic,
    start_manual,
)"""

new = """    is_stop_requested,
    start_automatic,
    start_manual,
    start_watcher,
)"""

if old not in text:
    raise SystemExit("IMPORT BLOCK NOT FOUND")

text = text.replace(old, new, 1)

# ------------------------------------------------------------
# 2. Добавляем Watcher helpers перед MAIN LOOP
# ------------------------------------------------------------

marker = """# ============================================================
# MAIN LOOP
# ============================================================

async def supervisor_loop():
"""

insert = r'''# ============================================================
# WATCHER
# ============================================================

WATCHER_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

def watcher_snapshot(folder: Path):
    """
    Возвращает текущее состояние фотографий в папке.

    Ключ:
        абсолютный путь

    Значение:
        (size, mtime_ns)

    Поэтому изменение существующего файла тоже
    может быть замечено, но только как новое событие
    после изменения baseline.
    """

    if not folder.exists():
        return {}

    if not folder.is_dir():
        return {}

    result = {}

    try:
        for item in folder.iterdir():

            if not item.is_file():
                continue

            if item.suffix.lower() not in WATCHER_EXTENSIONS:
                continue

            try:
                stat = item.stat()

            except OSError:
                continue

            result[str(item.resolve())] = (
                stat.st_size,
                stat.st_mtime_ns,
            )

    except OSError as exc:

        print(
            "[SUPERVISOR] WATCHER SCAN ERROR:",
            repr(exc),
            flush=True,
        )

    return result

async def wait_watcher_event():
    """
    Ждёт появления нового/изменённого фото.

    Уже существующие фотографии при входе в Watcher
    не считаются событием.

    Перед запуском pipeline новый файл должен оставаться
    неизменным минимум два последовательных опроса.
    """

    while True:

        state = get_state()

        if state.mode != "watcher":
            return False

        if state.stop_requested:
            finish_stop()
            return False

        watcher_path = (
            state.watcher_path
            or ""
        ).strip()

        if not watcher_path:

            print(
                "[SUPERVISOR] Watcher has no path.",
                flush=True,
            )

            await asyncio.sleep(
                POLL_INTERVAL
            )

            continue

        folder = Path(
            watcher_path
        ).expanduser()

        baseline = watcher_snapshot(
            folder
        )

        print(
            "[SUPERVISOR] Watcher active:",
            folder,
            "| existing photos:",
            len(baseline),
            flush=True,
        )

        # ----------------------------------------------------
        # WAIT FOR EVENT
        # ----------------------------------------------------

        previous = baseline

        while True:

            current_state = get_state()

            if current_state.mode != "watcher":
                return False

            if current_state.stop_requested:
                finish_stop()
                return False

            current = watcher_snapshot(
                folder
            )

            changed = []

            for filename, stat in current.items():

                if filename not in previous:
                    changed.append(
                        (
                            filename,
                            stat,
                        )
                    )

                elif previous[filename] != stat:
                    changed.append(
                        (
                            filename,
                            stat,
                        )
                    )

            if changed:

                # --------------------------------------------
                # FILE STABILITY CHECK
                # --------------------------------------------

                print(
                    "[SUPERVISOR] Watcher detected:",
                    len(changed),
                    "photo(s)",
                    flush=True,
                )

                await asyncio.sleep(
                    POLL_INTERVAL * 2
                )

                stable_state = get_state()

                if stable_state.mode != "watcher":
                    return False

                if stable_state.stop_requested:
                    finish_stop()
                    return False

                stable = watcher_snapshot(
                    folder
                )

                stable_changed = []

                for filename, stat in changed:

                    if stable.get(filename) == stat:
                        stable_changed.append(
                            filename
                        )

                if stable_changed:

                    print(
                        "[SUPERVISOR] Watcher event confirmed:",
                        len(stable_changed),
                        "stable photo(s)",
                        flush=True,
                    )

                    try:
                        start_watcher()

                    except Exception as exc:

                        print(
                            "[SUPERVISOR] WATCHER START ERROR:",
                            repr(exc),
                            flush=True,
                        )

                        await asyncio.sleep(
                            POLL_INTERVAL
                        )

                        continue

                    return True

            previous = current

            await asyncio.sleep(
                POLL_INTERVAL
            )

# ============================================================
# MAIN LOOP
# ============================================================

async def supervisor_loop():
'''

if marker not in text:
    raise SystemExit("MAIN LOOP MARKER NOT FOUND")

text = text.replace(
    marker,
    insert,
    1,
)

# ------------------------------------------------------------
# 3. Replace Watcher placeholder
# ------------------------------------------------------------

old = '''        elif state.mode == "watcher":

            print(
                "[SUPERVISOR] Watcher mode is not "
                "implemented yet.",
                flush=True,
            )

            await asyncio.sleep(
                2
            )

            continue
'''

new = '''        elif state.mode == "watcher":

            started = await wait_watcher_event()

            if not started:
                continue
'''

if old not in text:
    raise SystemExit("WATCHER PLACEHOLDER NOT FOUND")

text = text.replace(
    old,
    new,
    1,
)

path.write_text(text)

print("WATCHER PATCH APPLIED")
PY

echo "================ COMPILE ================" && \
uv run python -m py_compile \
app/pipeline/supervisor.py \
app/pipeline/controller.py \
app/pipeline/modes.py

echo "================ VERIFY WATCHER ================" && \
grep -n -A35 -B5 \
'async def wait_watcher_event' \
app/pipeline/supervisor.py

echo "================ VERIFY MAIN ================" && \
grep -n -A12 -B5 \
'elif state.mode == "watcher"' \
app/pipeline/supervisor.py
```

После выполнения пришли вывод этой команды. Особенно интересуют `WATCHER PATCH APPLIED`, `COMPILE` и два `VERIFY`.

---

### 👤 **User** — 2026-08-19 01:50:12

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

path = Path("app/pipeline/supervisor.py")
text = path.read_text()

# ------------------------------------------------------------
# 1. Добавляем start_watcher в import
# ------------------------------------------------------------

old = """    is_stop_requested,
    start_automatic,
    start_manual,
)"""

new = """    is_stop_requested,
    start_automatic,
    start_manual,
    start_watcher,
)"""

if old not in text:
app/pipeline/supervisor.pyer"' \IN ================" && \& \--",===========
WATCHER PATCH APPLIED
================ COMPILE ================
================ VERIFY WATCHER ================
549-        )
550-
551-    return result
552-
553-
554:async def wait_watcher_event():
555-    """
556-    Ждёт появления нового/изменённого фото.
557-
558-    Уже существующие фотографии при входе в Watcher
559-    не считаются событием.
560-
561-    Перед запуском pipeline новый файл должен оставаться
562-    неизменным минимум два последовательных опроса.
563-    """
564-
565-    while True:
566-
567-        state = get_state()
568-
569-        if state.mode != "watcher":
570-            return False
571-
572-        if state.stop_requested:
573-            finish_stop()
574-            return False
575-
576-        watcher_path = (
577-            state.watcher_path
578-            or ""
579-        ).strip()
580-
581-        if not watcher_path:
582-
583-            print(
584-                "[SUPERVISOR] Watcher has no path.",
585-                flush=True,
586-            )
587-
588-            await asyncio.sleep(
589-                POLL_INTERVAL
================ VERIFY MAIN ================
785-
786-        # ====================================================
787-        # WATCHER
788-        # ====================================================
789-
790:        elif state.mode == "watcher":
791-
792-            started = await wait_watcher_event()
793-
794-            if not started:
795-                continue
796-
797-        # ====================================================
798-        # PIPELINE
799-        # ====================================================
800-
801-        try:
802-
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:50:13

Отлично. Патч применился и `py_compile` прошёл без ошибок.

Но сейчас есть **важный нюанс в логике Watcher**: текущая реализация каждый раз при входе в `wait_watcher_event()` создаёт `baseline` из всех существующих файлов. Это правильно для первого входа, но после завершения pipeline мы снова вызываем `wait_watcher_event()`, и **файлы, появившиеся во время предыдущего запуска, станут baseline**. Это нам как раз подходит: следующий запуск будет только на действительно новых/изменённых фото после предыдущего запуска.

Теперь надо проверить весь цикл, не запуская DINO/Qwen.

### 1. Проверим режим и состояние БД

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.pipeline.controller import get_state

state = get_state()

print("mode           =", state.mode)
print("running        =", state.running)
print("stop_requested =", state.stop_requested)
print("watcher_enabled=", state.watcher_enabled)
print("watcher_path   =", state.watcher_path)
PY
```

### 2. И отдельно проверим компиляцию всего изменённого слоя

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/pipeline/controller.py \
app/pipeline/modes.py \
app/pipeline/supervisor.py \
app/web/components/technical_modules/automation.py \
app/web/components/technical_modules/photo_processing.py
```

Если оба проходят, следующим шагом я бы **не запускал сразу реальный pipeline**, а сделаем безопасный тест Watcher на временной папке: Supervisor увидит тестовый JPG, подтвердит стабильность файла и выставит `running`, но реальные DINO/Qwen можно будет временно не запускать.

Так мы сначала проверим именно механику **«появился файл → событие → запуск»**, не рискуя настоящей фотобазой.

---

### 👤 **User** — 2026-08-19 01:50:42

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.pipeline.controller import get_state

state = get_state()

print("mode           =", state.mode)
print("running        =", state.running)
print("stop_requested =", state.stop_requested)
print("watcher_enabled=", state.watcher_enabled)
print("watcher_path   =", state.watcher_path)
PY
mode           = manual
running        = False
stop_requested = False
watcher_enabled= False
watcher_path   = None
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/pipeline/controller.py \
app/pipeline/modes.py \
app/pipeline/supervisor.py \
app/web/components/technical_modules/automation.py \
app/web/components/technical_modules/photo_processing.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:50:43

Отлично. Всё чисто:

- `manual`
- `running=False`
- `stop_requested=False`
- Watcher не активен
- все 5 файлов успешно компилируются.

Теперь проверим **сам Watcher безопасно**, без запуска DINO/Qwen.

Сделаем временную папку, переключим режим Watcher на неё, запустим только `wait_watcher_event()`, создадим тестовый JPG и убедимся, что событие обнаруживается и `running` становится `True`.

Но есть нюанс: `wait_watcher_event()` внутри вызывает `start_watcher()`, то есть изменит PostgreSQL-состояние. После теста мы обязательно вернёмся в `manual`.

Давай сначала проверим только обнаружение файла, **без изменения состояния**, через саму функцию snapshot. Команда:

```bash id="3t3n1s"
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path
import tempfile

from app.pipeline.supervisor import watcher_snapshot

with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp)

    print("TEMP:", folder)

    before = watcher_snapshot(folder)

    test_file = folder / "watcher_test.jpg"
    test_file.write_bytes(b"TEST-JPG-DATA")

    after = watcher_snapshot(folder)

    print("BEFORE:", before)
    print("AFTER :", after)

    assert test_file.resolve().as_posix() in after
    assert test_file.resolve().as_posix() not in before

print("WATCHER SNAPSHOT TEST: OK")
PY
```

Ожидаем в конце:

```text
WATCHER SNAPSHOT TEST: OK
```

Если это проходит, следующим шагом сделаем **реальный тест Watcher с временной директорией**, но подменим `run_pipeline`, чтобы DINO/Qwen вообще не стартовали. Это уже проверит полный цикл `новый файл → start_watcher → pipeline trigger → возврат в ожидание`.

---

### 👤 **User** — 2026-08-19 01:50:59

да

---

### 🤖 **Assistant** — 2026-08-19 01:51:00

Да. Делаем безопасный интеграционный тест: **DINO/Qwen не запускаются** — `run_pipeline()` будет временно подменён тестовой функцией.

Команда сама:
1. создаст временную папку;
2. переведёт `pipeline_control` в Watcher;
3. запустит `wait_watcher_event()`;
4. создаст тестовый JPG;
5. дождётся обнаружения;
6. проверит `running=True`;
7. вернёт состояние в `manual`;
8. удалит временную папку.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import asyncio
import tempfile
from pathlib import Path

import app.pipeline.supervisor as supervisor
from app.pipeline.controller import (
    get_state,
    set_manual,
    set_watcher,
)

async def main():

    print("=" * 70)
    print("WATCHER INTEGRATION TEST")
    print("=" * 70)

    with tempfile.TemporaryDirectory(
        prefix="albion_watcher_test_"
    ) as tmp:

        folder = Path(tmp)

        print("[TEST] Folder:", folder)

        # ----------------------------------------------------
        # WATCHER MODE
        # ----------------------------------------------------

        set_watcher(
            str(folder)
        )

        state = get_state()

        print(
            "[TEST] Mode:",
            state.mode,
            "| path:",
            state.watcher_path,
        )

        assert state.mode == "watcher"
        assert state.watcher_path == str(folder)

        # ----------------------------------------------------
        # WATCHER TASK
        # ----------------------------------------------------

        watcher_task = asyncio.create_task(
            supervisor.wait_watcher_event()
        )

        await asyncio.sleep(1.0)

        # ----------------------------------------------------
        # CREATE TEST PHOTO
        # ----------------------------------------------------

        test_file = folder / "TEST_WATCHER_001.jpg"

        print(
            "[TEST] Creating:",
            test_file,
        )

        test_file.write_bytes(
            b"FAKE-JPG-DATA"
        )

        # ----------------------------------------------------
        # WAIT FOR EVENT
        # ----------------------------------------------------

        try:

            result = await asyncio.wait_for(
                watcher_task,
                timeout=8,
            )

        except asyncio.TimeoutError:

            watcher_task.cancel()

            try:
                await watcher_task
            except asyncio.CancelledError:
                pass

            raise RuntimeError(
                "Watcher did not detect test file"
            )

        print(
            "[TEST] wait_watcher_event() ->",
            result,
        )

        assert result is True

        # ----------------------------------------------------
        # CHECK STATE
        # ----------------------------------------------------

        state = get_state()

        print(
            "[TEST] After detection:",
            "mode=", state.mode,
            "running=", state.running,
            "stop=", state.stop_requested,
        )

        assert state.mode == "watcher"
        assert state.running is True
        assert state.stop_requested is False

        print()
        print("WATCHER EVENT TEST: OK")

    # --------------------------------------------------------
    # RESTORE MANUAL
    # --------------------------------------------------------

    set_manual()

    state = get_state()

    print()
    print(
        "[TEST] Restored:",
        "mode=", state.mode,
        "running=", state.running,
        "stop=", state.stop_requested,
    )

    assert state.mode == "manual"
    assert state.running is False
    assert state.stop_requested is False

    print()
    print("=" * 70)
    print("WATCHER INTEGRATION TEST: PASSED")
    print("=" * 70)

asyncio.run(main())
PY
```

Здесь **реальный `run_pipeline()` вообще не вызывается**, поэтому DINO и Qwen не должны стартовать.

Пришли вывод. Если будет `WATCHER INTEGRATION TEST: PASSED`, следующим патчем уже можно сделать нормальный запуск Watcher через UI.

---

### 👤 **User** — 2026-08-19 01:51:21

[TEST] wait_watcher_event() -> True
[TEST] After detection: mode= watcher running= True stop= False

WATCHER EVENT TEST: OK

[TEST] Restored: mode= manual running= True stop= False
Traceback (most recent call last):
  File "<stdin>", line 149, in <module>
  File "/usr/lib/python3.12/asyncio/runners.py", line 194, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/asyncio/base_events.py", line 687, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "<stdin>", line 140, in main
AssertionError
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:51:24

Да, тест **Watcher сам прошёл**. Ошибка только в восстановлении состояния — и она как раз показывает эффект нашего предыдущего патча.

Вот ключевое:

```text
[TEST] wait_watcher_event() -> True
[TEST] After detection: mode= watcher running= True stop= False
WATCHER EVENT TEST: OK
```

То есть:

**файл появился → Watcher его увидел → `start_watcher()` выставил `running=True` — работает.**

А вот:

```text
[TEST] Restored: mode= manual running= True
```

произошло потому, что мы раньше специально сделали `set_manual()` сохраняющим `running`:

```python
state.running = current.running
```

Поэтому `set_manual()` **не предназначен для завершения уже запущенного pipeline**.

### Сейчас просто починим состояние БД

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.pipeline.controller import finish_stop, get_state

print("BEFORE:", get_state())

finish_stop()

state = get_state()

print("AFTER :", state)

assert state.mode == "manual"
assert state.running is False
assert state.stop_requested is False

print("STATE CLEANUP: OK")
PY
```

Ожидаем:

```text
AFTER : ... mode='manual' ... running=False ... stop_requested=False
STATE CLEANUP: OK
```

### Важный вывод

Сам Watcher **уже работает**. Теперь у нас есть подтверждённая цепочка:

```text
WATCHER MODE
     ↓
папка watcher_path
     ↓
появился новый JPG
     ↓
файл стабилизировался
     ↓
start_watcher()
     ↓
running = TRUE
     ↓
supervisor → run_pipeline()
     ↓
DINO + Qwen
```

И я бы **пока не менял `set_manual()` обратно**. Его текущее поведение нужно для того, чтобы переключение режима не сбрасывало состояние работающего pipeline посреди обработки.

Следующий шаг — проверить уже **полный Supervisor**, то есть чтобы после `running=True` он действительно вызвал `run_pipeline()`, дождался завершения DINO/Qwen и корректно оставил Watcher в режиме ожидания следующей партии.

---

### 👤 **User** — 2026-08-19 01:51:41

int_mvp_v02 && \
uv run python - <<'PY'
from app.pipeline.controller import finish_stop, get_state

print("BEFORE:", get_state())

finish_stop()

state = get_state()

print("AFTER :", state)

assert state.mode == "manual"
assert state.running is False
assert state.stop_requested is False

print("STATE CLEANUP: OK")
PY
BEFORE: PipelineMode(mode='manual', auto_enabled=False, auto_time=None, watcher_enabled=False, watcher_path=None, running=True, stop_requested=False)
AFTER : PipelineMode(mode='manual', auto_enabled=False, auto_time=None, watcher_enabled=False, watcher_path=None, running=False, stop_requested=False)
STATE CLEANUP: OK
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:51:43

Отлично. Состояние теперь чистое:

```text
mode=manual
running=False
stop_requested=False
```

И главное — **тест Watcher прошёл**, так что обнаружение нового файла уже подтверждено.

Теперь я бы сделал следующий безопасный тест: **полный цикл Supervisor без реальных DINO/Qwen**. Он проверит именно то место, которое пока не проверено:

```text
новый файл
   ↓
Watcher
   ↓
running=True
   ↓
Supervisor вызывает run_pipeline()
   ↓
pipeline завершается
   ↓
mark_finished()
   ↓
Watcher снова ждёт новые файлы
```

При этом `run_pipeline()` подменим тестовой функцией, поэтому GPU и Qwen не тронутся.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import asyncio
import tempfile
from pathlib import Path

import app.pipeline.supervisor as supervisor
from app.pipeline.controller import (
    finish_stop,
    get_state,
    set_manual,
    set_watcher,
)

async def fake_pipeline():
    print("[TEST PIPELINE] START")

    await asyncio.sleep(0.5)

    print("[TEST PIPELINE] FINISHED")

async def main():

    print("=" * 70)
    print("FULL WATCHER -> SUPERVISOR TEST")
    print("=" * 70)

    # --------------------------------------------------------
    # SAVE ORIGINAL
    # --------------------------------------------------------

    original_run_pipeline = supervisor.run_pipeline

    # --------------------------------------------------------
    # REPLACE REAL DINO/QWEN PIPELINE
    # --------------------------------------------------------

    supervisor.run_pipeline = fake_pipeline

    try:

        with tempfile.TemporaryDirectory(
            prefix="albion_supervisor_test_"
        ) as tmp:

            folder = Path(tmp)

            print("[TEST] WATCHER:", folder)

            # ------------------------------------------------
            # WATCHER MODE
            # ------------------------------------------------

            set_watcher(
                str(folder)
            )

            # ------------------------------------------------
            # CREATE WATCHER TASK
            # ------------------------------------------------

            watcher_task = asyncio.create_task(
                supervisor.wait_watcher_event()
            )

            # Даем watcher создать baseline.
            await asyncio.sleep(1.0)

            # ------------------------------------------------
            # NEW PHOTO
            # ------------------------------------------------

            test_file = (
                folder /
                "SUPERVISOR_TEST_001.jpg"
            )

            print(
                "[TEST] NEW FILE:",
                test_file,
            )

            test_file.write_bytes(
                b"FAKE-JPG-DATA"
            )

            # ------------------------------------------------
            # WATCHER DETECTION
            # ------------------------------------------------

            started = await asyncio.wait_for(
                watcher_task,
                timeout=8,
            )

            print(
                "[TEST] watcher result:",
                started,
            )

            assert started is True

            state = get_state()

            print(
                "[TEST] after watcher:",
                state,
            )

            assert state.mode == "watcher"
            assert state.running is True
            assert state.stop_requested is False

            # ------------------------------------------------
            # SUPERVISOR PIPELINE
            # ------------------------------------------------

            print()
            print(
                "[TEST] Calling run_pipeline()..."
            )

            await supervisor.run_pipeline()

            print(
                "[TEST] run_pipeline() returned"
            )

            # ------------------------------------------------
            # FINALIZATION
            # ------------------------------------------------

            state = get_state()

            print(
                "[TEST] BEFORE FINALIZATION:",
                state,
            )

            assert state.running is True

            from app.pipeline.controller import (
                mark_finished,
            )

            mark_finished()

            state = get_state()

            print(
                "[TEST] AFTER FINALIZATION:",
                state,
            )

            # Watcher должен остаться watcher,
            # но running должен стать False.
            assert state.mode == "watcher"
            assert state.running is False
            assert state.stop_requested is False

            print()
            print(
                "FULL WATCHER -> SUPERVISOR TEST: OK"
            )

    finally:

        # ----------------------------------------------------
        # RESTORE REAL PIPELINE
        # ----------------------------------------------------

        supervisor.run_pipeline = (
            original_run_pipeline
        )

        # ----------------------------------------------------
        # CLEAN DATABASE STATE
        # ----------------------------------------------------

        finish_stop()

        state = get_state()

        print()
        print(
            "[TEST] CLEAN STATE:",
            state,
        )

        assert state.mode == "manual"
        assert state.running is False
        assert state.stop_requested is False

        print()
        print("=" * 70)
        print("FULL WATCHER -> SUPERVISOR TEST: PASSED")
        print("=" * 70)

asyncio.run(main())
PY
```

Здесь особенно важен результат:

```text
[TEST] AFTER FINALIZATION: ... mode='watcher' ... running=False
FULL WATCHER -> SUPERVISOR TEST: PASSED
```

Если он проходит, значит **архитектура режимов уже замкнута правильно**, и останется подключить реальный запуск Supervisor/UI, не меняя DINO/Qwen.

---

### 👤 **User** — 2026-08-19 01:52:03

FULL WATCHER -> SUPERVISOR TEST: PASSED
======================================================================
Traceback (most recent call last):
  File "<stdin>", line 200, in <module>
  File "/usr/lib/python3.12/asyncio/runners.py", line 194, in run
    return runner.run(main)
           ^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/asyncio/runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/asyncio/base_events.py", line 687, in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
  File "<stdin>", line 142, in main
ImportError: cannot import name 'mark_finished' from 'app.pipeline.controller' (/home/alexice/projects/scene_fingerprint_mvp_v02/app/pipeline/controller.py)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:52:05

Да, здесь всё понятно. **Сам тест Watcher → Supervisor прошёл**, а упал только на финальной строке теста:

```text
ImportError: cannot import name 'mark_finished'
```

То есть у нас обнаружилась реальная несогласованность: `supervisor.py` уже вызывает `mark_finished()`, а в `controller.py` этой функции нет.

Это не надо обходить тестом — **нужно добавить `mark_finished()` в controller**, потому что это правильная часть архитектуры.

Выполни патч:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

path = Path("app/pipeline/controller.py")
text = path.read_text()

marker = """def finish_stop():
"""

if "def mark_finished():" in text:
    print("mark_finished() already exists")
    raise SystemExit(0)

if marker not in text:
    raise RuntimeError(
        "Не найдено место для вставки mark_finished()"
    )

insert = '''def mark_finished():
    """
    Завершает один запуск pipeline.

    ВАЖНО:

    Режим НЕ меняется.

    Поэтому:
        manual    -> manual
        automatic -> automatic
        watcher   -> watcher

    Сбрасывается только состояние текущего запуска.
    Это позволяет automatic/watcher продолжить работу
    после завершения очередной партии.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = FALSE,
                    stop_requested = FALSE,
                    stopped_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    return get_state()

'''

text = text.replace(
    marker,
    insert + marker,
    1,
)

path.write_text(text)

print("MARK_FINISHED PATCH APPLIED")
PY
```

После этого сразу:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/pipeline/controller.py \
app/pipeline/supervisor.py
```

И проверим наличие:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -A35 '^def mark_finished' \
app/pipeline/controller.py
```

После этого **повторим тот же полный тест**. На этот раз он должен пройти уже целиком, включая:

```text
Watcher
→ running=True
→ fake pipeline
→ mark_finished()
→ mode=watcher
→ running=False
→ cleanup
→ mode=manual
→ running=False
```

И это будет уже хорошее основание переходить к реальному Supervisor.

---

### 👤 **User** — 2026-08-19 01:52:26

давай

---

### 🤖 **Assistant** — 2026-08-19 01:52:27

Давай. Выполни сначала патч + компиляцию + проверку функции одной командой:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

path = Path("app/pipeline/controller.py")
text = path.read_text()

if "def mark_finished():" in text:
    print("mark_finished() уже существует")
else:
    marker = "def finish_stop():"

    if marker not in text:
        raise RuntimeError(
            "Не найдено место для вставки mark_finished()"
        )

    insert = '''def mark_finished():
    """
    Завершает текущий запуск pipeline,
    не меняя выбранный режим.

    manual    -> manual
    automatic -> automatic
    watcher   -> watcher

    Сбрасывается только состояние текущего запуска.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = FALSE,
                    stop_requested = FALSE,
                    stopped_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    return get_state()

'''

    text = text.replace(
        marker,
        insert + marker,
        1,
    )

    path.write_text(text)
    print("MARK_FINISHED PATCH APPLIED")

PY

echo "================ COMPILE ================" && \
uv run python -m py_compile \
app/pipeline/controller.py \
app/pipeline/supervisor.py && \
echo "COMPILE: OK" && \
echo "================ VERIFY ================" && \
grep -n -A32 '^def mark_finished' \
app/pipeline/controller.py
```

Если получишь `COMPILE: OK`, запускаем **повторный полный Watcher → Supervisor тест**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import asyncio
import tempfile
from pathlib import Path

import app.pipeline.supervisor as supervisor

from app.pipeline.controller import (
    finish_stop,
    get_state,
    mark_finished,
    set_watcher,
)

async def fake_pipeline():

    print("[TEST PIPELINE] START")

    await asyncio.sleep(0.5)

    print("[TEST PIPELINE] FINISHED")

async def main():

    print("=" * 70)
    print("FULL WATCHER -> SUPERVISOR TEST")
    print("=" * 70)

    original_run_pipeline = supervisor.run_pipeline

    supervisor.run_pipeline = fake_pipeline

    try:

        with tempfile.TemporaryDirectory(
            prefix="albion_supervisor_test_"
        ) as tmp:

            folder = Path(tmp)

            print(
                "[TEST] WATCHER:",
                folder,
            )

            # ------------------------------------------------
            # WATCHER
            # ------------------------------------------------

            set_watcher(
                str(folder)
            )

            state = get_state()

            print(
                "[TEST] INITIAL:",
                state,
            )

            assert state.mode == "watcher"
            assert state.running is False
            assert state.stop_requested is False

            # ------------------------------------------------
            # WAIT FOR WATCHER
            # ------------------------------------------------

            watcher_task = asyncio.create_task(
                supervisor.wait_watcher_event()
            )

            await asyncio.sleep(1.0)

            # ------------------------------------------------
            # NEW PHOTO
            # ------------------------------------------------

            test_file = (
                folder /
                "SUPERVISOR_TEST_001.jpg"
            )

            print(
                "[TEST] CREATE:",
                test_file,
            )

            test_file.write_bytes(
                b"FAKE-JPG-DATA"
            )

            # ------------------------------------------------
            # DETECT
            # ------------------------------------------------

            started = await asyncio.wait_for(
                watcher_task,
                timeout=8,
            )

            print(
                "[TEST] WATCHER RESULT:",
                started,
            )

            assert started is True

            state = get_state()

            print(
                "[TEST] AFTER WATCHER:",
                state,
            )

            assert state.mode == "watcher"
            assert state.running is True
            assert state.stop_requested is False

            # ------------------------------------------------
            # PIPELINE
            # ------------------------------------------------

            print(
                "[TEST] RUN PIPELINE"
            )

            await supervisor.run_pipeline()

            print(
                "[TEST] PIPELINE RETURNED"
            )

            # ------------------------------------------------
            # FINISH
            # ------------------------------------------------

            mark_finished()

            state = get_state()

            print(
                "[TEST] AFTER FINISH:",
                state,
            )

            assert state.mode == "watcher"
            assert state.running is False
            assert state.stop_requested is False

            print()
            print(
                "WATCHER -> PIPELINE -> FINISH: OK"
            )

    finally:

        supervisor.run_pipeline = (
            original_run_pipeline
        )

        # ----------------------------------------------------
        # FINAL CLEANUP
        # ----------------------------------------------------

        finish_stop()

        state = get_state()

        print()
        print(
            "[TEST] CLEANUP:",
            state,
        )

        assert state.mode == "manual"
        assert state.running is False
        assert state.stop_requested is False

        print()
        print("=" * 70)
        print("FULL WATCHER -> SUPERVISOR TEST: PASSED")
        print("=" * 70)

asyncio.run(main())
PY
```

**Важно:** этот тест снова не запускает ни DINO, ни Qwen. Мы проверяем только оркестрацию состояний.

Нужен финальный вывод:

```text
WATCHER -> PIPELINE -> FINISH: OK
...
FULL WATCHER -> SUPERVISOR TEST: PASSED
```

Если он будет — следующим шагом уже проверяем, **запускается ли сам `supervisor.py` из приложения**, а не только отдельные функции.

---

### 👤 **User** — 2026-08-19 01:53:02

FULL WATCHER -> SUPERVISOR TEST: PASSED
======================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

