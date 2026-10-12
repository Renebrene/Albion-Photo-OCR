## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-21 22:47:02

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '180,360p' app/pipeline/supervisor.py

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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 22:47:03

Да. Здесь уже видно **конкретное место, которое надо менять**.

Сейчас цепочка `supervisor.py` такая:

`run_pipeline()` → запускает **DINO_WORKER** → запускает **QWEN_WORKER** → ждёт оба процесса.

А по новой архитектуре должно быть:

`run_pipeline()` → **Hybrid v12** + **Qwen** параллельно.

При этом **DINO worker из supervisor вообще убираем**. DINO 33 должен запускаться **внутри Hybrid v12**, а не отдельным worker'ом.

То есть:

```text
                    ┌── Hybrid v12 ──> внутренний DINO 33
                    │                 └─> TOP1-5 + соседи + best_id
daily ─> photo_id ──┤                 └─> hybrid_final_id ─> PostgreSQL
                    │
                    └── Qwen ────────> описание ─> PostgreSQL
```

И никаких физических перемещений фотографий.

### Что сейчас неправильно

Вот этот участок:

```python
dino_process, dino_output = (
    await start_worker(
        DINO_WORKER,
        "DINO",
    )
)
```

должен исчезнуть.

И вместо него должен запускаться `run_hybrid_v12.py`.

Но **пока не будем сразу править**. Нужно пройти цепочку с самого начала, как ты и сказал:

1. `manual / automatic / watcher`
2. кто фактически вызывает `run_pipeline()`
3. как определяется наличие новых файлов в `daily`
4. кто присваивает `photo_id`
5. что именно передаётся Hybrid
6. как Hybrid пишет `hybrid_*` в PostgreSQL
7. как Qwen независимо получает те же `photo_id`
8. кто создаёт превью
9. как грид видит новые записи.

Сейчас мы находимся примерно на пункте **2–3**.

Следующий вывод сделай **короткий**, чтобы не пришлось загружать километры:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "===== SUPERVISOR START =====" && \
grep -nE \
'run_pipeline|start_manual|start_automatic|start_watcher|photo_ingest|daily|DINO_WORKER|QWEN_WORKER' \
app/pipeline/supervisor.py | head -120
```

Пришли только этот вывод.

---

### 👤 **User** — 2026-08-21 22:48:14

да. и надо очистить основную базу пройдя всю цепочку по новой. для начала присовить photo_id файлам

---

### 🤖 **Assistant** — 2026-08-21 22:48:15

Да. Тогда **не начинаем с замены worker'а**. Сначала делаем чистый прогон базы.

Правильный порядок:

1. **Очистить основную PostgreSQL-базу** от результатов старой обработки.
2. Оставить/подготовить исходные фото в `daily`.
3. Запустить **только этап присвоения `photo_id`**.
4. Проверить, что каждому файлу соответствует запись:
   `photo_id ↔ filename ↔ source_path`.
5. Только после этого подключаем Hybrid 12 и Qwen параллельно.
6. Затем превью и отображение в гриде.

И главное: **не удаляем сами фотографии из `daily`** и пока не запускаем DINO/Qwen.

Сначала выясним, какой именно скрипт сейчас присваивает `photo_id`. Короткая команда:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'photo_id|PH_[0-9]|INSERT INTO photos' \
scripts app/pipeline \
--include="*.py" \
| grep -vE 'bak|broken|diagnose|__pycache__' \
| head -120
```

Пришли вывод. По нему определим **чистый первый этап**, а затем я дам отдельную команду для очистки БД и отдельную — для присвоения `photo_id`.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)

---
