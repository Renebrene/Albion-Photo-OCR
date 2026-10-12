## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 🤖 **Assistant** — 2026-08-21 01:37:18

Да. Тогда это уже не эксперимент — **делаем Hybrid основным worker-пайплайном**, а отдельный `dino_worker.py` убираем из цепочки запуска.

Но важный момент: **DINO v33 внутри Hybrid не меняем**, меняем только orchestration.

Целевая архитектура:

```text
                 ФОТО
                   │
        ┌──────────┴──────────┐
        │                     │
   ручной запуск          автоматизация
        │                     │
        └──────────┬──────────┘
                   ▼
             HYBRID WORKER
                   │
          ┌────────┴────────┐
          │                 │
       DINO v33          Hybrid v12
          │                 │
          └────────┬────────┘
                   ▼
             final best_id
                   │
                   ▼
              PostgreSQL
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
       статистика  watcher  UI
```

И **CPU принудительно**:

```text
SCENE_DEVICE=cpu
```

При этом:

- `DINO v33` не меняем;
- `Hybrid v12` не меняем;
- fingerprints `*_v33` не меняем;
- логику subfingerprints не меняем;
- neighbor logic не меняем;
- `run_hybrid_v12.py` пока не переписываем.

### Сначала сделаем карту интеграции

Нам надо найти **все места, где сейчас подразумевается именно DINO worker**, а не только `dino_worker.py`.

Выполни из корня проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ ALL DINO WORKER REFERENCES ================" && \
grep -RniE \
'dino_worker|DINO_WORKER|start_dino|stop_dino|dino_process|dino_status|dino_started_at|dino_finished_at|dino_error|hybrid_original_id|hybrid_final_id|sort_status' \
app scripts \
--include="*.py" \
--include="*.sh" \
| tee /tmp/dino_hybrid_refs.txt
```

Потом отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PIPELINE / AUTOMATION / WATCHER ================" && \
grep -RniE \
'supervisor|watcher|automatic|manual|start_all|start_dino|start_qwen|run_pipeline|DINO|QWEN|HYBRID' \
app/pipeline app/web scripts \
--include="*.py" \
--include="*.sh" \
| head -1000
```

И ещё:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID DB FIELDS ================" && \
grep -RniE \
'hybrid_original_id|hybrid_final_id|hybrid_score|hybrid_changed|sort_status' \
app scripts \
--include="*.py" \
--include="*.sh" \
| head -500
```

**Пока ничего не изменяй.**

По этим трём выводам я составлю точную карту:

1. где заменить запуск DINO worker на Hybrid;
2. где заменить остановку;
3. где изменить supervisor;
4. где изменить watcher;
5. где изменить ручной запуск;
6. какие статусы оставить/переименовать;
7. куда записывать `hybrid_original_id` / `hybrid_final_id`;
8. что делать со статистикой;
9. как встроить `SCENE_DEVICE=cpu`;
10. и главное — **как сделать это без изменения самого проверенного DINO v33 + Hybrid v12**.

---

### 👤 **User** — 2026-08-21 01:38:11

echo "================ ALL DINO WORKER REFERENCES ================" && \
grep -RniE \
'dino_worker|DINO_WORKER|start_dino|stop_dino|dino_process|dino_status|dino_started_at|dino_finished_at|dino_error|hybrid_original_id|hybrid_final_id|sort_status' \
app scripts \
--include="*.py" \
--include="*.sh" \
| tee /tmp/dino_hybrid_refs.txt
================ ALL DINO WORKER REFERENCES ================
app/web/components/technical_modules/photo_processing.py:21:DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
app/web/components/technical_modules/photo_processing.py:45:    dino_process = None
app/web/components/technical_modules/photo_processing.py:152:        dino_processing = int(
app/web/components/technical_modules/photo_processing.py:158:        dino_error = int(
app/web/components/technical_modules/photo_processing.py:163:            dino_done + dino_error
app/web/components/technical_modules/photo_processing.py:191:        dino_processing_label.text = str(
app/web/components/technical_modules/photo_processing.py:192:            dino_processing
app/web/components/technical_modules/photo_processing.py:199:        dino_error_label.text = str(
app/web/components/technical_modules/photo_processing.py:200:            dino_error
app/web/components/technical_modules/photo_processing.py:264:            dino_process
app/web/components/technical_modules/photo_processing.py:294:            dino_status_label,
app/web/components/technical_modules/photo_processing.py:296:            dino_error > 0,
app/web/components/technical_modules/photo_processing.py:316:        elif dino_error or qwen_error:
app/web/components/technical_modules/photo_processing.py:407:    async def start_dino():
app/web/components/technical_modules/photo_processing.py:409:        nonlocal dino_process
app/web/components/technical_modules/photo_processing.py:423:        if process_running(dino_process):
app/web/components/technical_modules/photo_processing.py:436:        if not DINO_WORKER.exists():
app/web/components/technical_modules/photo_processing.py:439:                f"Не найден DINO worker: {DINO_WORKER}",
app/web/components/technical_modules/photo_processing.py:464:            dino_process = (
app/web/components/technical_modules/photo_processing.py:469:                    str(DINO_WORKER),
app/web/components/technical_modules/photo_processing.py:478:                f"[WEB] DINO START PID={dino_process.pid}",
app/web/components/technical_modules/photo_processing.py:484:                    dino_process,
app/web/components/technical_modules/photo_processing.py:497:            dino_process = None
app/web/components/technical_modules/photo_processing.py:515:    async def stop_dino():
app/web/components/technical_modules/photo_processing.py:519:        if not process_running(dino_process):
app/web/components/technical_modules/photo_processing.py:526:            dino_process.terminate()
app/web/components/technical_modules/photo_processing.py:693:        await start_dino()
app/web/components/technical_modules/photo_processing.py:706:            process_running(dino_process)
app/web/components/technical_modules/photo_processing.py:716:            await stop_dino()
app/web/components/technical_modules/photo_processing.py:889:                dino_status_label = ui.label(
app/web/components/technical_modules/photo_processing.py:901:                    on_click=start_dino,
app/web/components/technical_modules/photo_processing.py:908:                    on_click=stop_dino,
app/web/components/technical_modules/photo_processing.py:943:                dino_processing_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:955:                dino_error_label = ui.label("0").classes(
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/web/photo_db.py:56:            dino_status,
app/web/photo_db.py:57:            sort_status
app/web/photo_db.py:90:                WHERE dino_status = 'done'
app/web/photo_db.py:94:                WHERE dino_status = 'processing'
app/web/photo_db.py:95:            ) AS dino_processing,
app/web/photo_db.py:98:                WHERE dino_status = 'pending'
app/web/photo_db.py:102:                WHERE dino_status = 'error'
app/web/photo_db.py:103:            ) AS dino_error,
app/pipeline/recovery.py:54:                    dino_status = 'pending',
app/pipeline/recovery.py:55:                    dino_started_at = NULL,
app/pipeline/recovery.py:58:                    dino_status = 'processing'
app/pipeline/recovery.py:59:                    AND dino_started_at < %s
app/pipeline/supervisor.py:22:DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
app/pipeline/supervisor.py:190:        DINO -> PostgreSQL dino_status
app/pipeline/supervisor.py:196:    dino_process = None
app/pipeline/supervisor.py:223:        dino_process, dino_output = (
app/pipeline/supervisor.py:225:                DINO_WORKER,
app/pipeline/supervisor.py:246:                dino_process
app/pipeline/supervisor.py:264:                    dino_process,
app/pipeline/supervisor.py:284:            dino_process.returncode
app/pipeline/supervisor.py:285:            if dino_process is not None
app/pipeline/supervisor.py:319:            dino_process,
app/pipeline/supervisor.py:740:    if not DINO_WORKER.exists():
app/pipeline/supervisor.py:742:            f"DINO worker not found: {DINO_WORKER}"
app/workers/dino_worker.py:49:                dino_status = 'pending',
app/workers/dino_worker.py:51:            WHERE dino_status = 'processing'
app/workers/dino_worker.py:75:    dino_status = pending.
app/workers/dino_worker.py:92:                dino_status = 'pending'
app/workers/dino_worker.py:111:                dino_status = 'processing',
app/workers/dino_worker.py:115:                AND dino_status = 'pending'
app/workers/dino_worker.py:153:                dino_status = 'done',
app/workers/dino_worker.py:207:                dino_status = 'error',
scripts/photo_ingest.py:247:                dino_status,
scripts/photo_ingest.py:249:                sort_status,
scripts/photo_ingest.py:462:        "  DINO : dino_status = pending"
scripts/diagnose_dino_hybrid_db.py:29:                    dino_status,
scripts/diagnose_dino_hybrid_db.py:34:                    hybrid_original_id,
scripts/diagnose_dino_hybrid_db.py:35:                    hybrid_final_id,
scripts/diagnose_dino_hybrid_db.py:42:                WHERE dino_status = 'done'
scripts/diagnose_dino_hybrid_db.py:74:                    dino_status,
scripts/diagnose_dino_hybrid_db.py:88:                if dino_status == "done":
scripts/diagnose_dino_hybrid_db.py:105:                print(f"dino_status         : {dino_status}")
scripts/diagnose_dino_hybrid_db.py:110:                print(f"hybrid_original_id  : {hybrid_original}")
scripts/diagnose_dino_hybrid_db.py:111:                print(f"hybrid_final_id     : {hybrid_final}")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PIPELINE / AUTOMATION / WATCHER ================" && \
grep -RniE \
'supervisor|watcher|automatic|manual|start_all|start_dino|start_qwen|run_pipeline|DINO|QWEN|HYBRID' \
app/pipeline app/web scripts \
--include="*.py" \
--include="*.sh" \
| head -1000
================ PIPELINE / AUTOMATION / WATCHER ================
app/pipeline/modes.py:8:MODE_MANUAL = "manual"
app/pipeline/modes.py:9:MODE_AUTOMATIC = "automatic"
app/pipeline/modes.py:10:MODE_WATCHER = "watcher"
app/pipeline/modes.py:14:    MODE_MANUAL,
app/pipeline/modes.py:15:    MODE_AUTOMATIC,
app/pipeline/modes.py:16:    MODE_WATCHER,
app/pipeline/modes.py:22:    mode: str = MODE_MANUAL
app/pipeline/modes.py:27:    watcher_enabled: bool = False
app/pipeline/modes.py:28:    watcher_path: Optional[str] = None
app/pipeline/modes.py:43:def build_manual_mode() -> PipelineMode:
app/pipeline/modes.py:45:        mode=MODE_MANUAL,
app/pipeline/modes.py:48:        watcher_enabled=False,
app/pipeline/modes.py:49:        watcher_path=None,
app/pipeline/modes.py:55:def build_automatic_mode(
app/pipeline/modes.py:60:        mode=MODE_AUTOMATIC,
app/pipeline/modes.py:63:        watcher_enabled=False,
app/pipeline/modes.py:64:        watcher_path=None,
app/pipeline/modes.py:70:def build_watcher_mode(
app/pipeline/modes.py:71:    watcher_path: str,
app/pipeline/modes.py:74:    if not watcher_path:
app/pipeline/modes.py:76:            "Watcher path is required"
app/pipeline/modes.py:80:        mode=MODE_WATCHER,
app/pipeline/modes.py:83:        watcher_enabled=True,
app/pipeline/modes.py:84:        watcher_path=watcher_path,
app/pipeline/modes.py:90:def can_manual_start(state: PipelineMode) -> bool:
app/pipeline/modes.py:97:        state.mode == MODE_MANUAL
app/pipeline/modes.py:106:def reset_to_manual() -> PipelineMode:
app/pipeline/modes.py:113:    return build_manual_mode()
app/pipeline/controller.py:10:    MODE_AUTOMATIC,
app/pipeline/controller.py:11:    MODE_MANUAL,
app/pipeline/controller.py:12:    MODE_WATCHER,
app/pipeline/controller.py:14:    build_automatic_mode,
app/pipeline/controller.py:15:    build_manual_mode,
app/pipeline/controller.py:16:    build_watcher_mode,
app/pipeline/controller.py:60:                    watcher_enabled,
app/pipeline/controller.py:61:                    watcher_path,
app/pipeline/controller.py:72:        return build_manual_mode()
app/pipeline/controller.py:80:        watcher_enabled=bool(row["watcher_enabled"]),
app/pipeline/controller.py:81:        watcher_path=row["watcher_path"],
app/pipeline/controller.py:99:                    watcher_enabled = %s,
app/pipeline/controller.py:100:                    watcher_path = %s,
app/pipeline/controller.py:110:                    state.watcher_enabled,
app/pipeline/controller.py:111:                    state.watcher_path,
app/pipeline/controller.py:120:def set_manual():
app/pipeline/controller.py:121:    state = build_manual_mode()
app/pipeline/controller.py:133:def set_automatic(auto_time: time):
app/pipeline/controller.py:134:    state = build_automatic_mode(auto_time)
app/pipeline/controller.py:144:def set_watcher(watcher_path: str):
app/pipeline/controller.py:145:    state = build_watcher_mode(watcher_path)
app/pipeline/controller.py:155:def start_manual():
app/pipeline/controller.py:158:    if state.mode != MODE_MANUAL:
app/pipeline/controller.py:160:            "Manual start is available only in manual mode"
app/pipeline/controller.py:191:def start_automatic():
app/pipeline/controller.py:194:    if state.mode != MODE_AUTOMATIC:
app/pipeline/controller.py:196:            "Automatic start requested while mode is not automatic"
app/pipeline/controller.py:225:def start_watcher():
app/pipeline/controller.py:228:    if state.mode != MODE_WATCHER:
app/pipeline/controller.py:230:            "Watcher start requested while mode is not watcher"
app/pipeline/controller.py:284:        manual    -> manual
app/pipeline/controller.py:285:        automatic -> automatic
app/pipeline/controller.py:286:        watcher   -> watcher
app/pipeline/controller.py:289:    Это позволяет automatic/watcher продолжить работу
app/pipeline/controller.py:313:    state = build_manual_mode()
app/pipeline/controller.py:321:                    mode = 'manual',
app/pipeline/controller.py:324:                    watcher_enabled = FALSE,
app/pipeline/controller.py:325:                    watcher_path = NULL,
app/pipeline/controller.py:359:def manual_start_allowed() -> bool:
app/pipeline/controller.py:363:        state.mode == MODE_MANUAL
app/pipeline/recovery.py:43:    recovered_dino = 0
app/pipeline/recovery.py:44:    recovered_qwen = 0
app/pipeline/recovery.py:54:                    dino_status = 'pending',
app/pipeline/recovery.py:55:                    dino_started_at = NULL,
app/pipeline/recovery.py:58:                    dino_status = 'processing'
app/pipeline/recovery.py:59:                    AND dino_started_at < %s
app/pipeline/recovery.py:64:            recovered_dino = cur.rowcount
app/pipeline/recovery.py:70:                    qwen_status = 'pending',
app/pipeline/recovery.py:71:                    qwen_started_at = NULL,
app/pipeline/recovery.py:74:                    qwen_status = 'processing'
app/pipeline/recovery.py:75:                    AND qwen_started_at < %s
app/pipeline/recovery.py:80:            recovered_qwen = cur.rowcount
app/pipeline/recovery.py:85:        "dino": recovered_dino,
app/pipeline/recovery.py:86:        "qwen": recovered_qwen,
app/pipeline/supervisor.py:13:    start_automatic,
app/pipeline/supervisor.py:14:    start_manual,
app/pipeline/supervisor.py:15:    start_watcher,
app/pipeline/supervisor.py:22:DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
app/pipeline/supervisor.py:23:QWEN_WORKER = PROJECT / "app" / "workers" / "qwen_worker.py"
app/pipeline/supervisor.py:125:        f"[SUPERVISOR] {prefix} START "
app/pipeline/supervisor.py:148:        f"[SUPERVISOR] stopping {prefix} "
app/pipeline/supervisor.py:168:            f"[SUPERVISOR] {prefix} did not stop, "
app/pipeline/supervisor.py:185:async def run_pipeline():
app/pipeline/supervisor.py:187:    Один полный запуск DINO + Qwen.
app/pipeline/supervisor.py:190:        DINO -> PostgreSQL dino_status
app/pipeline/supervisor.py:191:        Qwen -> PostgreSQL qwen_status
app/pipeline/supervisor.py:193:    Supervisor только управляет их жизненным циклом.
app/pipeline/supervisor.py:196:    dino_process = None
app/pipeline/supervisor.py:197:    qwen_process = None
app/pipeline/supervisor.py:199:    dino_output = None
app/pipeline/supervisor.py:200:    qwen_output = None
app/pipeline/supervisor.py:214:            "[SUPERVISOR] PIPELINE START",
app/pipeline/supervisor.py:223:        dino_process, dino_output = (
app/pipeline/supervisor.py:225:                DINO_WORKER,
app/pipeline/supervisor.py:226:                "DINO",
app/pipeline/supervisor.py:232:        qwen_process, qwen_output = (
app/pipeline/supervisor.py:234:                QWEN_WORKER,
app/pipeline/supervisor.py:235:                "QWEN",
app/pipeline/supervisor.py:245:            dino_running = process_running(
app/pipeline/supervisor.py:246:                dino_process
app/pipeline/supervisor.py:249:            qwen_running = process_running(
app/pipeline/supervisor.py:250:                qwen_process
app/pipeline/supervisor.py:253:            if not dino_running and not qwen_running:
app/pipeline/supervisor.py:259:                    "[SUPERVISOR] STOP REQUESTED",
app/pipeline/supervisor.py:264:                    dino_process,
app/pipeline/supervisor.py:265:                    "DINO",
app/pipeline/supervisor.py:269:                    qwen_process,
app/pipeline/supervisor.py:270:                    "QWEN",
app/pipeline/supervisor.py:283:        dino_code = (
app/pipeline/supervisor.py:284:            dino_process.returncode
app/pipeline/supervisor.py:285:            if dino_process is not None
app/pipeline/supervisor.py:289:        qwen_code = (
app/pipeline/supervisor.py:290:            qwen_process.returncode
app/pipeline/supervisor.py:291:            if qwen_process is not None
app/pipeline/supervisor.py:296:            "[SUPERVISOR] DINO exit:",
app/pipeline/supervisor.py:297:            dino_code,
app/pipeline/supervisor.py:302:            "[SUPERVISOR] QWEN exit:",
app/pipeline/supervisor.py:303:            qwen_code,
app/pipeline/supervisor.py:308:            dino_code,
app/pipeline/supervisor.py:309:            qwen_code,
app/pipeline/supervisor.py:319:            dino_process,
app/pipeline/supervisor.py:320:            "DINO",
app/pipeline/supervisor.py:324:            qwen_process,
app/pipeline/supervisor.py:325:            "QWEN",
app/pipeline/supervisor.py:329:            dino_output,
app/pipeline/supervisor.py:330:            qwen_output,
app/pipeline/supervisor.py:340:            "[SUPERVISOR] PIPELINE FINISHED",
app/pipeline/supervisor.py:346:# AUTOMATIC SCHEDULER
app/pipeline/supervisor.py:369:async def wait_automatic():
app/pipeline/supervisor.py:374:    automatic mode остаётся automatic после завершения
app/pipeline/supervisor.py:382:        if state.mode != "automatic":
app/pipeline/supervisor.py:394:                "[SUPERVISOR] Automatic mode has "
app/pipeline/supervisor.py:410:            "[SUPERVISOR] Automatic mode.",
app/pipeline/supervisor.py:424:            if current.mode != "automatic":
app/pipeline/supervisor.py:441:            start_automatic()
app/pipeline/supervisor.py:445:                "[SUPERVISOR] AUTOMATIC START ERROR:",
app/pipeline/supervisor.py:460:# MANUAL MODE
app/pipeline/supervisor.py:463:async def wait_manual_start():
app/pipeline/supervisor.py:465:    В manual режиме Supervisor ждёт,
app/pipeline/supervisor.py:466:    пока UI вызовет start_manual().
app/pipeline/supervisor.py:473:        if state.mode != "manual":
app/pipeline/supervisor.py:489:# WATCHER
app/pipeline/supervisor.py:492:WATCHER_EXTENSIONS = {
app/pipeline/supervisor.py:500:def watcher_snapshot(folder: Path):
app/pipeline/supervisor.py:529:            if item.suffix.lower() not in WATCHER_EXTENSIONS:
app/pipeline/supervisor.py:546:            "[SUPERVISOR] WATCHER SCAN ERROR:",
app/pipeline/supervisor.py:554:async def wait_watcher_event():
app/pipeline/supervisor.py:558:    Уже существующие фотографии при входе в Watcher
app/pipeline/supervisor.py:569:        if state.mode != "watcher":
app/pipeline/supervisor.py:576:        watcher_path = (
app/pipeline/supervisor.py:577:            state.watcher_path
app/pipeline/supervisor.py:581:        if not watcher_path:
app/pipeline/supervisor.py:584:                "[SUPERVISOR] Watcher has no path.",
app/pipeline/supervisor.py:595:            watcher_path
app/pipeline/supervisor.py:598:        baseline = watcher_snapshot(
app/pipeline/supervisor.py:603:            "[SUPERVISOR] Watcher active:",
app/pipeline/supervisor.py:620:            if current_state.mode != "watcher":
app/pipeline/supervisor.py:627:            current = watcher_snapshot(
app/pipeline/supervisor.py:658:                    "[SUPERVISOR] Watcher detected:",
app/pipeline/supervisor.py:670:                if stable_state.mode != "watcher":
app/pipeline/supervisor.py:677:                stable = watcher_snapshot(
app/pipeline/supervisor.py:693:                        "[SUPERVISOR] Watcher event confirmed:",
app/pipeline/supervisor.py:700:                        start_watcher()
app/pipeline/supervisor.py:705:                            "[SUPERVISOR] WATCHER START ERROR:",
app/pipeline/supervisor.py:729:async def supervisor_loop():
app/pipeline/supervisor.py:732:    print("ALBION PIPELINE SUPERVISOR")
app/pipeline/supervisor.py:740:    if not DINO_WORKER.exists():
app/pipeline/supervisor.py:742:            f"DINO worker not found: {DINO_WORKER}"
app/pipeline/supervisor.py:745:    if not QWEN_WORKER.exists():
app/pipeline/supervisor.py:747:            f"Qwen worker not found: {QWEN_WORKER}"
app/pipeline/supervisor.py:755:            "[SUPERVISOR] state:",
app/pipeline/supervisor.py:765:        # MANUAL
app/pipeline/supervisor.py:768:        if state.mode == "manual":
app/pipeline/supervisor.py:770:            started = await wait_manual_start()
app/pipeline/supervisor.py:776:        # AUTOMATIC
app/pipeline/supervisor.py:779:        elif state.mode == "automatic":
app/pipeline/supervisor.py:781:            started = await wait_automatic()
app/pipeline/supervisor.py:787:        # WATCHER
app/pipeline/supervisor.py:790:        elif state.mode == "watcher":
app/pipeline/supervisor.py:792:            started = await wait_watcher_event()
app/pipeline/supervisor.py:803:            await run_pipeline()
app/pipeline/supervisor.py:811:                "[SUPERVISOR] PIPELINE ERROR:",
app/pipeline/supervisor.py:827:                    "[SUPERVISOR] Finalizing STOP",
app/pipeline/supervisor.py:837:                # Automatic mode остаётся automatic.
app/pipeline/supervisor.py:838:                # Manual mode после запуска остаётся manual.
app/pipeline/supervisor.py:842:                # Это позволяет automatic mode ждать
app/pipeline/supervisor.py:854:                "[SUPERVISOR] STATE FINALIZATION ERROR:",
app/pipeline/supervisor.py:873:            "[SUPERVISOR] OS STOP SIGNAL",
app/pipeline/supervisor.py:887:                "[SUPERVISOR] Cannot request stop:",
app/pipeline/supervisor.py:915:    await supervisor_loop()
app/pipeline/supervisor.py:924:            "[SUPERVISOR] Interrupted",
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:24:    DINO / fingerprint здесь НЕ используется.
app/web/components/search.py:59:            qwen_status,
app/web/components/search.py:60:            qwen_time_sec,
app/web/components/technical_modules/photo_processing.py:21:DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
app/web/components/technical_modules/photo_processing.py:22:QWEN_WORKER = PROJECT / "app" / "workers" / "qwen_worker.py"
app/web/components/technical_modules/photo_processing.py:45:    dino_process = None
app/web/components/technical_modules/photo_processing.py:46:    qwen_process = None
app/web/components/technical_modules/photo_processing.py:48:    dino_stopping = False
app/web/components/technical_modules/photo_processing.py:49:    qwen_stopping = False
app/web/components/technical_modules/photo_processing.py:144:        dino = data.get("dino", {})
app/web/components/technical_modules/photo_processing.py:145:        qwen = data.get("qwen", {})
app/web/components/technical_modules/photo_processing.py:148:        # DINO
app/web/components/technical_modules/photo_processing.py:151:        dino_done = int(dino.get("done", 0))
app/web/components/technical_modules/photo_processing.py:152:        dino_processing = int(
app/web/components/technical_modules/photo_processing.py:153:            dino.get("processing", 0)
app/web/components/technical_modules/photo_processing.py:155:        dino_pending = int(
app/web/components/technical_modules/photo_processing.py:156:            dino.get("pending", 0)
app/web/components/technical_modules/photo_processing.py:158:        dino_error = int(
app/web/components/technical_modules/photo_processing.py:159:            dino.get("error", 0)
app/web/components/technical_modules/photo_processing.py:162:        dino_finished = (
app/web/components/technical_modules/photo_processing.py:163:            dino_done + dino_error
app/web/components/technical_modules/photo_processing.py:166:        dino_progress = (
app/web/components/technical_modules/photo_processing.py:170:                    dino_finished
app/web/components/technical_modules/photo_processing.py:179:        dino_progress_bar.value = (
app/web/components/technical_modules/photo_processing.py:180:            dino_progress / 100
app/web/components/technical_modules/photo_processing.py:183:        dino_progress_label.text = (
app/web/components/technical_modules/photo_processing.py:184:            f"{dino_finished} / {total}"
app/web/components/technical_modules/photo_processing.py:187:        dino_done_label.text = str(
app/web/components/technical_modules/photo_processing.py:188:            dino_done
app/web/components/technical_modules/photo_processing.py:191:        dino_processing_label.text = str(
app/web/components/technical_modules/photo_processing.py:192:            dino_processing
app/web/components/technical_modules/photo_processing.py:195:        dino_pending_label.text = str(
app/web/components/technical_modules/photo_processing.py:196:            dino_pending
app/web/components/technical_modules/photo_processing.py:199:        dino_error_label.text = str(
app/web/components/technical_modules/photo_processing.py:200:            dino_error
app/web/components/technical_modules/photo_processing.py:204:        # QWEN
app/web/components/technical_modules/photo_processing.py:207:        qwen_done = int(qwen.get("done", 0))
app/web/components/technical_modules/photo_processing.py:208:        qwen_processing = int(
app/web/components/technical_modules/photo_processing.py:209:            qwen.get("processing", 0)
app/web/components/technical_modules/photo_processing.py:211:        qwen_pending = int(
app/web/components/technical_modules/photo_processing.py:212:            qwen.get("pending", 0)
app/web/components/technical_modules/photo_processing.py:214:        qwen_error = int(
app/web/components/technical_modules/photo_processing.py:215:            qwen.get("error", 0)
app/web/components/technical_modules/photo_processing.py:218:        qwen_finished = (
app/web/components/technical_modules/photo_processing.py:219:            qwen_done + qwen_error
app/web/components/technical_modules/photo_processing.py:222:        qwen_progress = (
app/web/components/technical_modules/photo_processing.py:226:                    qwen_finished
app/web/components/technical_modules/photo_processing.py:235:        qwen_progress_bar.value = (
app/web/components/technical_modules/photo_processing.py:236:            qwen_progress / 100
app/web/components/technical_modules/photo_processing.py:239:        qwen_progress_label.text = (
app/web/components/technical_modules/photo_processing.py:240:            f"{qwen_finished} / {total}"
app/web/components/technical_modules/photo_processing.py:243:        qwen_done_label.text = str(
app/web/components/technical_modules/photo_processing.py:244:            qwen_done
app/web/components/technical_modules/photo_processing.py:247:        qwen_processing_label.text = str(
app/web/components/technical_modules/photo_processing.py:248:            qwen_processing
app/web/components/technical_modules/photo_processing.py:251:        qwen_pending_label.text = str(
app/web/components/technical_modules/photo_processing.py:252:            qwen_pending
app/web/components/technical_modules/photo_processing.py:255:        qwen_error_label.text = str(
app/web/components/technical_modules/photo_processing.py:256:            qwen_error
app/web/components/technical_modules/photo_processing.py:263:        dino_running = process_running(
app/web/components/technical_modules/photo_processing.py:264:            dino_process
app/web/components/technical_modules/photo_processing.py:267:        qwen_running = process_running(
app/web/components/technical_modules/photo_processing.py:268:            qwen_process
app/web/components/technical_modules/photo_processing.py:279:            and not dino_running
app/web/components/technical_modules/photo_processing.py:280:            and not qwen_running
app/web/components/technical_modules/photo_processing.py:294:            dino_status_label,
app/web/components/technical_modules/photo_processing.py:295:            dino_running,
app/web/components/technical_modules/photo_processing.py:296:            dino_error > 0,
app/web/components/technical_modules/photo_processing.py:300:            qwen_status_label,
app/web/components/technical_modules/photo_processing.py:301:            qwen_running,
app/web/components/technical_modules/photo_processing.py:302:            qwen_error > 0,
app/web/components/technical_modules/photo_processing.py:309:        if dino_running or qwen_running:
app/web/components/technical_modules/photo_processing.py:316:        elif dino_error or qwen_error:
app/web/components/technical_modules/photo_processing.py:335:            dino_running
app/web/components/technical_modules/photo_processing.py:336:            or qwen_running
app/web/components/technical_modules/photo_processing.py:340:            dino_running
app/web/components/technical_modules/photo_processing.py:341:            or qwen_running
app/web/components/technical_modules/photo_processing.py:344:        dino_run_button.enabled = not (
app/web/components/technical_modules/photo_processing.py:345:            dino_running
app/web/components/technical_modules/photo_processing.py:348:        dino_stop_button.enabled = (
app/web/components/technical_modules/photo_processing.py:349:            dino_running
app/web/components/technical_modules/photo_processing.py:352:        qwen_run_button.enabled = not (
app/web/components/technical_modules/photo_processing.py:353:            qwen_running
app/web/components/technical_modules/photo_processing.py:356:        qwen_stop_button.enabled = (
app/web/components/technical_modules/photo_processing.py:357:            qwen_running
app/web/components/technical_modules/photo_processing.py:404:    # START DINO
app/web/components/technical_modules/photo_processing.py:407:    async def start_dino():
app/web/components/technical_modules/photo_processing.py:409:        nonlocal dino_process
app/web/components/technical_modules/photo_processing.py:410:        nonlocal dino_stopping
app/web/components/technical_modules/photo_processing.py:415:        if state.mode != "manual":
app/web/components/technical_modules/photo_processing.py:417:                "DINO нельзя запускать вручную в текущем режиме.",
app/web/components/technical_modules/photo_processing.py:423:        if process_running(dino_process):
app/web/components/technical_modules/photo_processing.py:436:        if not DINO_WORKER.exists():
app/web/components/technical_modules/photo_processing.py:439:                f"Не найден DINO worker: {DINO_WORKER}",
app/web/components/technical_modules/photo_processing.py:446:        dino_stopping = False
app/web/components/technical_modules/photo_processing.py:464:            dino_process = (
app/web/components/technical_modules/photo_processing.py:469:                    str(DINO_WORKER),
app/web/components/technical_modules/photo_processing.py:478:                f"[WEB] DINO START PID={dino_process.pid}",
app/web/components/technical_modules/photo_processing.py:484:                    dino_process,
app/web/components/technical_modules/photo_processing.py:485:                    "DINO",
app/web/components/technical_modules/photo_processing.py:490:                "DINO запущен",
app/web/components/technical_modules/photo_processing.py:497:            dino_process = None
app/web/components/technical_modules/photo_processing.py:500:                "[WEB] DINO START ERROR:",
app/web/components/technical_modules/photo_processing.py:506:                f"Ошибка запуска DINO: {exc}",
app/web/components/technical_modules/photo_processing.py:512:    # STOP DINO
app/web/components/technical_modules/photo_processing.py:515:    async def stop_dino():
app/web/components/technical_modules/photo_processing.py:517:        nonlocal dino_stopping
app/web/components/technical_modules/photo_processing.py:519:        if not process_running(dino_process):
app/web/components/technical_modules/photo_processing.py:522:        dino_stopping = True
app/web/components/technical_modules/photo_processing.py:526:            dino_process.terminate()
app/web/components/technical_modules/photo_processing.py:529:                "DINO останавливается",
app/web/components/technical_modules/photo_processing.py:540:                f"Ошибка остановки DINO: {exc}",
app/web/components/technical_modules/photo_processing.py:546:    # START QWEN
app/web/components/technical_modules/photo_processing.py:549:    async def start_qwen():
app/web/components/technical_modules/photo_processing.py:551:        nonlocal qwen_process
app/web/components/technical_modules/photo_processing.py:552:        nonlocal qwen_stopping
app/web/components/technical_modules/photo_processing.py:557:        if state.mode != "manual":
app/web/components/technical_modules/photo_processing.py:559:                "Qwen нельзя запускать вручную в текущем режиме.",
app/web/components/technical_modules/photo_processing.py:565:        if process_running(qwen_process):
app/web/components/technical_modules/photo_processing.py:578:        if not QWEN_WORKER.exists():
app/web/components/technical_modules/photo_processing.py:581:                f"Не найден Qwen worker: {QWEN_WORKER}",
app/web/components/technical_modules/photo_processing.py:588:        qwen_stopping = False
app/web/components/technical_modules/photo_processing.py:606:            qwen_process = (
app/web/components/technical_modules/photo_processing.py:611:                    str(QWEN_WORKER),
app/web/components/technical_modules/photo_processing.py:620:                f"[WEB] QWEN START PID={qwen_process.pid}",
app/web/components/technical_modules/photo_processing.py:626:                    qwen_process,
app/web/components/technical_modules/photo_processing.py:627:                    "QWEN",
app/web/components/technical_modules/photo_processing.py:632:                "Qwen запущен",
app/web/components/technical_modules/photo_processing.py:639:            qwen_process = None
app/web/components/technical_modules/photo_processing.py:642:                "[WEB] QWEN START ERROR:",
app/web/components/technical_modules/photo_processing.py:648:                f"Ошибка запуска Qwen: {exc}",
app/web/components/technical_modules/photo_processing.py:654:    # STOP QWEN
app/web/components/technical_modules/photo_processing.py:657:    async def stop_qwen():
app/web/components/technical_modules/photo_processing.py:659:        nonlocal qwen_stopping
app/web/components/technical_modules/photo_processing.py:661:        if not process_running(qwen_process):
app/web/components/technical_modules/photo_processing.py:664:        qwen_stopping = True
app/web/components/technical_modules/photo_processing.py:668:            qwen_process.terminate()
app/web/components/technical_modules/photo_processing.py:671:                "Qwen останавливается",
app/web/components/technical_modules/photo_processing.py:682:                f"Ошибка остановки Qwen: {exc}",
app/web/components/technical_modules/photo_processing.py:691:    async def start_all():
app/web/components/technical_modules/photo_processing.py:693:        await start_dino()
app/web/components/technical_modules/photo_processing.py:697:        await start_qwen()
app/web/components/technical_modules/photo_processing.py:706:            process_running(dino_process)
app/web/components/technical_modules/photo_processing.py:707:            or process_running(qwen_process)
app/web/components/technical_modules/photo_processing.py:716:            await stop_dino()
app/web/components/technical_modules/photo_processing.py:717:            await stop_qwen()
app/web/components/technical_modules/photo_processing.py:720:                "Остановка DINO и Qwen запрошена",
app/web/components/technical_modules/photo_processing.py:833:                on_click=start_all,
app/web/components/technical_modules/photo_processing.py:868:        # DINO
app/web/components/technical_modules/photo_processing.py:884:                    "DINO v33 / Hybrid v12"
app/web/components/technical_modules/photo_processing.py:889:                dino_status_label = ui.label(
app/web/components/technical_modules/photo_processing.py:899:                dino_run_button = ui.button(
app/web/components/technical_modules/photo_processing.py:901:                    on_click=start_dino,
app/web/components/technical_modules/photo_processing.py:906:                dino_stop_button = ui.button(
app/web/components/technical_modules/photo_processing.py:908:                    on_click=stop_dino,
app/web/components/technical_modules/photo_processing.py:917:            dino_progress_bar = ui.linear_progress(
app/web/components/technical_modules/photo_processing.py:925:            dino_progress_label = ui.label(
app/web/components/technical_modules/photo_processing.py:937:                dino_done_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:943:                dino_processing_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:949:                dino_pending_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:955:                dino_error_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:960:        # QWEN
app/web/components/technical_modules/photo_processing.py:976:                    "Qwen3-VL 4B"
app/web/components/technical_modules/photo_processing.py:981:                qwen_status_label = ui.label(
app/web/components/technical_modules/photo_processing.py:991:                qwen_run_button = ui.button(
app/web/components/technical_modules/photo_processing.py:993:                    on_click=start_qwen,
app/web/components/technical_modules/photo_processing.py:998:                qwen_stop_button = ui.button(
app/web/components/technical_modules/photo_processing.py:1000:                    on_click=stop_qwen,
app/web/components/technical_modules/photo_processing.py:1009:            qwen_progress_bar = ui.linear_progress(
app/web/components/technical_modules/photo_processing.py:1017:            qwen_progress_label = ui.label(
app/web/components/technical_modules/photo_processing.py:1029:                qwen_done_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:1035:                qwen_processing_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:1041:                qwen_pending_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:1047:                qwen_error_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:1060:            "DINO и Qwen работают независимо. "
app/web/components/technical_modules/photo_processing.py:1071:    dino_stop_button.disable()
app/web/components/technical_modules/photo_processing.py:1072:    qwen_stop_button.disable()
app/web/components/technical_modules/fingerprints.py:17:            "Рабочая версия: DINO / v33"
app/web/components/technical_modules/data.py:13:QWEN_ROOT = PROJECT / "data" / "metadata" / "qwen4b"
app/web/components/technical_modules/data.py:78:def qwen_stats():
app/web/components/technical_modules/data.py:80:    Статистика Qwen3-VL 4B.
app/web/components/technical_modules/data.py:90:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/data.py:95:    if QWEN_ROOT.exists():
app/web/components/technical_modules/data.py:98:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/data.py:243:    qwen = qwen_stats()
app/web/components/technical_modules/data.py:298:        # DINO
app/web/components/technical_modules/data.py:308:                    "DINO v33"
app/web/components/technical_modules/data.py:327:        # HYBRID
app/web/components/technical_modules/data.py:337:                    "Hybrid v12"
app/web/components/technical_modules/data.py:368:        # QWEN
app/web/components/technical_modules/data.py:378:                    "Qwen3-VL 4B"
app/web/components/technical_modules/data.py:389:            qwen_color = (
app/web/components/technical_modules/data.py:391:                if qwen["status"] == "ГОТОВ"
app/web/components/technical_modules/data.py:396:                qwen["status"],
app/web/components/technical_modules/data.py:397:                color=qwen_color,
app/web/components/technical_modules/data.py:405:                f"Обработано: {qwen['photos']}"
app/web/components/technical_modules/data.py:409:                f"OK: {qwen['ok']}"
app/web/components/technical_modules/data.py:413:                f"Ошибок: {qwen['errors']}"
app/web/components/technical_modules/data.py:417:                f"Адресов: {qwen['addresses']}"
app/web/components/technical_modules/data.py:421:                f"Среднее время: {qwen['avg_time']:.2f} сек"
app/web/components/technical_modules/data.py:425:                f"Средняя уверенность: {qwen['avg_confidence']:.1f}%"
app/web/components/technical_modules/automation.py:10:    set_automatic,
app/web/components/technical_modules/automation.py:11:    set_manual,
app/web/components/technical_modules/automation.py:12:    set_watcher,
app/web/components/technical_modules/automation.py:15:    MODE_AUTOMATIC,
app/web/components/technical_modules/automation.py:16:    MODE_MANUAL,
app/web/components/technical_modules/automation.py:17:    MODE_WATCHER,
app/web/components/technical_modules/automation.py:61:                    MODE_MANUAL: "Ручной",
app/web/components/technical_modules/automation.py:62:                    MODE_WATCHER: "Watcher",
app/web/components/technical_modules/automation.py:63:                    MODE_AUTOMATIC: "Автоматический",
app/web/components/technical_modules/automation.py:78:                    MODE_MANUAL,
app/web/components/technical_modules/automation.py:79:                    MODE_WATCHER,
app/web/components/technical_modules/automation.py:80:                    MODE_AUTOMATIC,
app/web/components/technical_modules/automation.py:94:            "Выберите режим запуска: ручной, Watcher "
app/web/components/technical_modules/automation.py:99:        # WATCHER PATH
app/web/components/technical_modules/automation.py:105:            watcher_path_input = ui.input(
app/web/components/technical_modules/automation.py:106:                "Папка для Watcher",
app/web/components/technical_modules/automation.py:107:                value=state.watcher_path or "",
app/web/components/technical_modules/automation.py:114:            watcher_path_input.tooltip(
app/web/components/technical_modules/automation.py:116:                "контролировать в режиме Watcher. "
app/web/components/technical_modules/automation.py:125:            with ui.dialog() as watcher_folder_dialog, ui.card().classes(
app/web/components/technical_modules/automation.py:129:                    "Выбор папки для Watcher"
app/web/components/technical_modules/automation.py:141:                    "path": state.watcher_path or str(Path.home())
app/web/components/technical_modules/automation.py:221:                def open_watcher_folder_dialog():
app/web/components/technical_modules/automation.py:223:                        watcher_path_input.value
app/web/components/technical_modules/automation.py:224:                        or state.watcher_path
app/web/components/technical_modules/automation.py:229:                    watcher_folder_dialog.open()
app/web/components/technical_modules/automation.py:231:                def select_watcher_folder():
app/web/components/technical_modules/automation.py:234:                    watcher_path_input.value = path
app/web/components/technical_modules/automation.py:238:                    if current.mode == MODE_WATCHER:
app/web/components/technical_modules/automation.py:240:                            set_watcher(path)
app/web/components/technical_modules/automation.py:243:                                "[AUTOMATION] WATCHER PATH ERROR:",
app/web/components/technical_modules/automation.py:249:                                f"Ошибка пути Watcher: {exc}",
app/web/components/technical_modules/automation.py:254:                    watcher_folder_dialog.close()
app/web/components/technical_modules/automation.py:258:                        f"Папка Watcher выбрана: {path}",
app/web/components/technical_modules/automation.py:267:                        on_click=watcher_folder_dialog.close,
app/web/components/technical_modules/automation.py:272:                        on_click=select_watcher_folder,
app/web/components/technical_modules/automation.py:277:                on_click=open_watcher_folder_dialog,
app/web/components/technical_modules/automation.py:283:        # AUTOMATIC TIME
app/web/components/technical_modules/automation.py:343:        # MISSED AUTOMATIC START
app/web/components/technical_modules/automation.py:388:            if current.mode == MODE_MANUAL:
app/web/components/technical_modules/automation.py:393:            elif current.mode == MODE_WATCHER:
app/web/components/technical_modules/automation.py:394:                path = current.watcher_path or "—"
app/web/components/technical_modules/automation.py:397:                    "● Режим: Watcher"
app/web/components/technical_modules/automation.py:401:            elif current.mode == MODE_AUTOMATIC:
app/web/components/technical_modules/automation.py:418:            watcher_enabled = (
app/web/components/technical_modules/automation.py:419:                current.mode == MODE_WATCHER
app/web/components/technical_modules/automation.py:422:            automatic_enabled = (
app/web/components/technical_modules/automation.py:423:                current.mode == MODE_AUTOMATIC
app/web/components/technical_modules/automation.py:426:            watcher_path_input.enabled = True
app/web/components/technical_modules/automation.py:429:                automatic_enabled
app/web/components/technical_modules/automation.py:446:                if mode == MODE_MANUAL:
app/web/components/technical_modules/automation.py:448:                    set_manual()
app/web/components/technical_modules/automation.py:450:                elif mode == MODE_WATCHER:
app/web/components/technical_modules/automation.py:452:                    watcher_path = (
app/web/components/technical_modules/automation.py:453:                        watcher_path_input.value or ""
app/web/components/technical_modules/automation.py:456:                    if not watcher_path:
app/web/components/technical_modules/automation.py:458:                            "Укажите папку для Watcher",
app/web/components/technical_modules/automation.py:464:                    set_watcher(
app/web/components/technical_modules/automation.py:465:                        watcher_path
app/web/components/technical_modules/automation.py:468:                elif mode == MODE_AUTOMATIC:
app/web/components/technical_modules/automation.py:474:                    set_automatic(
app/web/components/technical_modules/automation.py:496:        # WATCHER PATH CHANGE
app/web/components/technical_modules/automation.py:499:        def watcher_path_changed(event):
app/web/components/technical_modules/automation.py:503:            if current.mode != MODE_WATCHER:
app/web/components/technical_modules/automation.py:513:                    "Путь Watcher не может быть пустым",
app/web/components/technical_modules/automation.py:522:                set_watcher(path)
app/web/components/technical_modules/automation.py:529:                    "[AUTOMATION] WATCHER PATH ERROR:",
app/web/components/technical_modules/automation.py:535:                    f"Ошибка пути Watcher: {exc}",
app/web/components/technical_modules/automation.py:541:        watcher_path_input.on(
app/web/components/technical_modules/automation.py:543:            watcher_path_changed,
app/web/components/technical_modules/automation.py:547:        # AUTOMATIC TIME CHANGE
app/web/components/technical_modules/automation.py:554:            if current.mode != MODE_AUTOMATIC:
app/web/components/technical_modules/automation.py:563:                set_automatic(
app/web/components/technical_modules/qwen.py:10:QWEN_ROOT = (
app/web/components/technical_modules/qwen.py:14:    / "qwen4b"
app/web/components/technical_modules/qwen.py:24:QWEN_SCRIPT = (
app/web/components/technical_modules/qwen.py:27:    / "qwen4b_output_v01.py"
app/web/components/technical_modules/qwen.py:35:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/qwen.py:40:    if QWEN_ROOT.exists():
app/web/components/technical_modules/qwen.py:44:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/qwen.py:57:def _load_qwen_status():
app/web/components/technical_modules/qwen.py:72:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:156:                "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:173:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:180:def _find_latest_hybrid():
app/web/components/technical_modules/qwen.py:200:def build_qwen():
app/web/components/technical_modules/qwen.py:205:            "QWEN3-VL 4B"
app/web/components/technical_modules/qwen.py:269:                "▶ Запустить Qwen",
app/web/components/technical_modules/qwen.py:275:                "■ Остановить Qwen",
app/web/components/technical_modules/qwen.py:294:    qwen_process = None
app/web/components/technical_modules/qwen.py:295:    qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:297:    async def stop_qwen():
app/web/components/technical_modules/qwen.py:298:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:299:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:301:        if qwen_process is None:
app/web/components/technical_modules/qwen.py:304:        qwen_stop_requested = True
app/web/components/technical_modules/qwen.py:307:            f"[QWEN MANUAL] STOP REQUESTED PID={qwen_process.pid}",
app/web/components/technical_modules/qwen.py:312:            qwen_process.terminate()
app/web/components/technical_modules/qwen.py:317:                f"[QWEN MANUAL] STOP FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:321:    async def run_qwen():
app/web/components/technical_modules/qwen.py:323:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:324:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:326:        print("[QWEN MANUAL] START", flush=True)
app/web/components/technical_modules/qwen.py:328:        qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:335:            if not QWEN_SCRIPT.exists():
app/web/components/technical_modules/qwen.py:338:                    f"[QWEN MANUAL] SCRIPT NOT FOUND: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:343:                    f"Не найден Qwen script: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:350:            result_dir = _find_latest_hybrid()
app/web/components/technical_modules/qwen.py:355:                    "[QWEN MANUAL] HYBRID RUN NOT FOUND",
app/web/components/technical_modules/qwen.py:360:                    "Не найден ни один запуск Hybrid.",
app/web/components/technical_modules/qwen.py:382:                    f"[QWEN MANUAL] NO IMAGES: {result_dir}",
app/web/components/technical_modules/qwen.py:387:                    f"В последнем Hybrid нет фотографий: {result_dir}",
app/web/components/technical_modules/qwen.py:396:            qwen_output = QWEN_ROOT / run_name
app/web/components/technical_modules/qwen.py:397:            qwen_output.mkdir(
app/web/components/technical_modules/qwen.py:403:                f"[QWEN MANUAL] INPUT: {result_dir}",
app/web/components/technical_modules/qwen.py:408:                f"[QWEN MANUAL] OUTPUT: {qwen_output}",
app/web/components/technical_modules/qwen.py:413:                f"[QWEN MANUAL] IMAGES: {total_images}",
app/web/components/technical_modules/qwen.py:420:            model_label.text = "qwen3-vl:4b-instruct"
app/web/components/technical_modules/qwen.py:435:                f"Запуск Qwen3-VL 4B: {total_images} фото",
app/web/components/technical_modules/qwen.py:447:                str(QWEN_SCRIPT),
app/web/components/technical_modules/qwen.py:451:                str(qwen_output),
app/web/components/technical_modules/qwen.py:457:            qwen_process = process
app/web/components/technical_modules/qwen.py:460:                f"[QWEN MANUAL] PID: {process.pid}",
app/web/components/technical_modules/qwen.py:488:                    f"[QWEN] {text}",
app/web/components/technical_modules/qwen.py:530:                if "[QWEN] OK |" in text:
app/web/components/technical_modules/qwen.py:580:                    "[QWEN] ERROR" in text
app/web/components/technical_modules/qwen.py:581:                    or "[QWEN] FAILED" in text
app/web/components/technical_modules/qwen.py:617:                if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:627:                f"[QWEN MANUAL] FINISHED "
app/web/components/technical_modules/qwen.py:632:            if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:638:                    f"Qwen остановлен: "
app/web/components/technical_modules/qwen.py:650:                    "✓ Qwen3-VL 4B завершён",
app/web/components/technical_modules/qwen.py:660:                status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:663:                    f"Qwen завершился с ошибкой: {returncode}",
app/web/components/technical_modules/qwen.py:671:                f"[QWEN MANUAL] EXCEPTION: {exc!r}",
app/web/components/technical_modules/qwen.py:676:            status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:680:                    f"Ошибка запуска Qwen: {exc}",
app/web/components/technical_modules/qwen.py:689:            qwen_process = None
app/web/components/technical_modules/qwen.py:690:            qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:706:                    f"[QWEN MANUAL] UI REFRESH FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:712:        data = _load_qwen_status()
app/web/components/technical_modules/qwen.py:772:    run_button.on_click(run_qwen)
app/web/components/technical_modules/qwen.py:773:    stop_button.on_click(stop_qwen)
app/web/components/photos.py:345:        # dino_fingerprint.
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/components/photos.py:350:        # Если DINO fingerprint отсутствует —
app/web/components/photos.py:355:            record.get("dino_fingerprint") or ""
app/web/components/photos.py:364:        # На данном этапе dino_fingerprint сам является
app/web/components/photos.py:459:        "only photos with DINO fingerprint + address_directory",
app/web/components/photos.py:920:                        if value("qwen_status") != "—":
app/web/components/photos.py:923:                                f"Qwen: {value('qwen_status')}"
app/web/components/photos.py:1618:                                    # AI / QWEN STATUS
app/web/components/photos.py:1621:                                    qwen_status = (
app/web/components/photos.py:1623:                                            "qwen_status"
app/web/components/photos.py:1643:                                        qwen_status,
app/web/components/photos.py:1719:                                # QWEN DESCRIPTION
app/web/client_aliases.py:4:Qwen может распознавать одно и то же название с ошибками,
app/web/photo_db.py:32:            qwen_status,
app/web/photo_db.py:33:            qwen_time_sec,
app/web/photo_db.py:44:            dino_fingerprint,
app/web/photo_db.py:45:            dino_score,
app/web/photo_db.py:46:            dino_second_score,
app/web/photo_db.py:47:            dino_margin,
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/web/photo_db.py:50:            hybrid_changed,
app/web/photo_db.py:51:            hybrid_old_score,
app/web/photo_db.py:52:            hybrid_score,
app/web/photo_db.py:53:            hybrid_margin,
app/web/photo_db.py:54:            hybrid_neighbors,
app/web/photo_db.py:56:            dino_status,
app/web/photo_db.py:81:    Быстрая статистика независимых веток DINO и Qwen.
app/web/photo_db.py:90:                WHERE dino_status = 'done'
app/web/photo_db.py:91:            ) AS dino_done,
app/web/photo_db.py:94:                WHERE dino_status = 'processing'
app/web/photo_db.py:95:            ) AS dino_processing,
app/web/photo_db.py:98:                WHERE dino_status = 'pending'
app/web/photo_db.py:99:            ) AS dino_pending,
app/web/photo_db.py:102:                WHERE dino_status = 'error'
app/web/photo_db.py:103:            ) AS dino_error,
app/web/photo_db.py:106:                WHERE qwen_status = 'done'
app/web/photo_db.py:107:            ) AS qwen_done,
app/web/photo_db.py:110:                WHERE qwen_status = 'processing'
app/web/photo_db.py:111:            ) AS qwen_processing,
app/web/photo_db.py:114:                WHERE qwen_status = 'pending'
app/web/photo_db.py:115:            ) AS qwen_pending,
app/web/photo_db.py:118:                WHERE qwen_status = 'error'
app/web/photo_db.py:119:            ) AS qwen_error
app/web/photo_db.py:132:        "dino": {
app/web/photo_db.py:139:        "qwen": {
app/web/main.py:13:from app.pipeline.supervisor import supervisor_loop
app/web/main.py:37:# =================================# PIPELINE SUPERVISOR
app/web/main.py:40:_supervisor_task = None
app/web/main.py:43:async def start_pipeline_supervisor():
app/web/main.py:44:    global _supervisor_task
app/web/main.py:47:        _supervisor_task is not None
app/web/main.py:48:        and not _supervisor_task.done()
app/web/main.py:51:            "[WEB] Pipeline Supervisor already running",
app/web/main.py:57:        "[WEB] Starting Pipeline Supervisor",
app/web/main.py:61:    _supervisor_task = asyncio.create_task(
app/web/main.py:62:        supervisor_loop()
app/web/main.py:68:    start_pipeline_supervisor,
app/web/client_db.py:14:    Возвращает клиентов из результатов Qwen.
app/web/client_db.py:17:    для которых Qwen определил клиента.
scripts/smart_client_normalizer.py:21:DEFAULT_MODEL = "qwen3:4b-instruct"
scripts/smart_client_normalizer.py:134:def ask_qwen(raw_name, clients, model):
scripts/smart_client_normalizer.py:232:    # Защита: Qwen не имеет права придумать клиента.
scripts/smart_client_normalizer.py:255:        description="Smart normalization of unknown clients using local Qwen."
scripts/smart_client_normalizer.py:372:                result = ask_qwen(
scripts/banner_model_compare_v04.py:19:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v04.py:20:    "qwen2.5vl:3b",
scripts/create_previews_v01.py:54:        help="Hybrid output directory",
scripts/banner_qwen25vl_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen25vl_test_v01")
scripts/banner_qwen25vl_test_v01.py:14:MODEL = "qwen2.5vl:3b"
scripts/banner_qwen25vl_test_v01.py:159:    print("QWEN2.5-VL 3B TEST")
scripts/banner_model_compare_v05.py:16:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v05.py:17:    "qwen2.5vl:3b",
scripts/benchmark_hybrid_v08.py:27:    "data/output/benchmark_hybrid_v08.json"
scripts/benchmark_hybrid_v08.py:118:    print("HYBRID V03")
scripts/banner_llm_full_v02.py:11:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_llm_full_v02.py:141:    print("QWEN3-VL BANNER TEST")
scripts/photo_ingest.py:93:    DINO и Qwen.
scripts/photo_ingest.py:218:        - DINO
scripts/photo_ingest.py:219:        - Qwen
scripts/photo_ingest.py:247:                dino_status,
scripts/photo_ingest.py:248:                qwen_status,
scripts/photo_ingest.py:462:        "  DINO : dino_status = pending"
scripts/photo_ingest.py:466:        "  QWEN : qwen_status = pending"
scripts/photo_ingest.py:487:            "DINO/Qwen queues."
scripts/benchmark_hybrid_v03.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v03.py:118:    print("HYBRID V03")
scripts/import_qwen_to_db.py:10:QWEN_DIR = PROJECT / "data/metadata/qwen4b"
scripts/import_qwen_to_db.py:53:            qwen_status TEXT,
scripts/import_qwen_to_db.py:54:            qwen_time_sec REAL,
scripts/import_qwen_to_db.py:90:        ON photos(qwen_status)
scripts/import_qwen_to_db.py:114:    relative = json_path.relative_to(QWEN_DIR)
scripts/import_qwen_to_db.py:178:            qwen_status,
scripts/import_qwen_to_db.py:179:            qwen_time_sec,
scripts/import_qwen_to_db.py:216:            qwen_status = excluded.qwen_status,
scripts/import_qwen_to_db.py:217:            qwen_time_sec = excluded.qwen_time_sec,
scripts/import_qwen_to_db.py:264:    QWEN_DIR.mkdir(
scripts/import_qwen_to_db.py:275:        QWEN_DIR.rglob("*.json")
scripts/import_qwen_to_db.py:279:    print("QWEN → SQLITE")
scripts/import_qwen_to_db.py:283:    print("QWEN DIR:", QWEN_DIR)
scripts/benchmark_hybrid_v12_full.py:27:    "data/output/full_recognize_hybrid_v12_test.json"
scripts/benchmark_hybrid_v12_full.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v12_full.py:287:        # DINO TOP1 is default.
scripts/benchmark_hybrid_v12_full.py:288:        # Change only if hybrid has strong evidence.
scripts/run_daily_hybrid_v12.sh:15:echo "SCENE FINGERPRINT — DAILY HYBRID V12"
scripts/run_daily_hybrid_v12.sh:42:/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
scripts/benchmark_hybrid_v10_debug.py:27:    "data/output/benchmark_hybrid_v09.json"
scripts/benchmark_hybrid_v10_debug.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v10_debug.py:286:        # DINO TOP1 is default.
scripts/benchmark_hybrid_v10_debug.py:287:        # Change only if hybrid has strong evidence.
scripts/banner_qwen4b_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen4b_test_v01")
scripts/banner_qwen4b_test_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_qwen4b_test_v01.py:159:    print("QWEN3-VL 4B TEST")
scripts/run_hybrid_v12.py:23:# HYBRID V12 — FROZEN CONTROL LOGIC
scripts/run_hybrid_v12.py:48:        print(f"[Hybrid] WARNING: sub directory not found: {SUB_DIR}")
scripts/run_hybrid_v12.py:98:    Run the existing DINO v33 recognizer.
scripts/run_hybrid_v12.py:121:    print("DINO v33 RECOGNITION")
scripts/run_hybrid_v12.py:182:    top1..top5 format required by frozen Hybrid v12.
scripts/run_hybrid_v12.py:207:def hybrid_v12(rows, embedder, subs):
scripts/run_hybrid_v12.py:209:    Exact production adaptation of the frozen Hybrid v12 logic.
scripts/run_hybrid_v12.py:363:        hybrid_changed = best != old
scripts/run_hybrid_v12.py:370:        result["hybrid_changed"] = hybrid_changed
scripts/run_hybrid_v12.py:372:        result["hybrid_old_score"] = old_score
scripts/run_hybrid_v12.py:373:        result["hybrid_score"] = new_score
scripts/run_hybrid_v12.py:375:        result["hybrid_margin"] = margin
scripts/run_hybrid_v12.py:376:        result["hybrid_neighbors"] = dict(neighbors)
scripts/run_hybrid_v12.py:403:    Copy photos according to FINAL Hybrid best_id.
scripts/run_hybrid_v12.py:460:                "hybrid_changed": item.get(
scripts/run_hybrid_v12.py:461:                    "hybrid_changed"
scripts/run_hybrid_v12.py:478:                "hybrid_old_score": item.get(
scripts/run_hybrid_v12.py:479:                    "hybrid_old_score"
scripts/run_hybrid_v12.py:481:                "hybrid_score": item.get(
scripts/run_hybrid_v12.py:482:                    "hybrid_score"
scripts/run_hybrid_v12.py:503:        description="Production runner for frozen Hybrid v12"
scripts/run_hybrid_v12.py:550:    print("SCENE FINGERPRINT — HYBRID V12 RUNNER")
scripts/run_hybrid_v12.py:557:    print("  DINO        : v33")
scripts/run_hybrid_v12.py:558:    print("  HYBRID      : v12")
scripts/run_hybrid_v12.py:565:    # 1. DINO
scripts/run_hybrid_v12.py:574:    # 2. Load Hybrid subfingerprints
scripts/run_hybrid_v12.py:579:    print("LOADING HYBRID SUBFINGERPRINTS")
scripts/run_hybrid_v12.py:587:    # 3. Hybrid v12
scripts/run_hybrid_v12.py:592:    print("HYBRID V12")
scripts/run_hybrid_v12.py:603:    hybrid_rows, changed, sub_count = hybrid_v12(
scripts/run_hybrid_v12.py:610:    print("Checked:", len(hybrid_rows))
scripts/run_hybrid_v12.py:612:    print("Hybrid changes:", len(changed))
scripts/run_hybrid_v12.py:638:        hybrid_rows,
scripts/run_hybrid_v12.py:655:    hybrid_json = (
scripts/run_hybrid_v12.py:656:        output_dir / "hybrid_v12.json"
scripts/run_hybrid_v12.py:676:    hybrid_json.write_text(
scripts/run_hybrid_v12.py:678:            hybrid_rows,
scripts/run_hybrid_v12.py:700:        "total_images": len(hybrid_rows),
scripts/run_hybrid_v12.py:704:        "hybrid_border_cases": sub_count,
scripts/run_hybrid_v12.py:705:        "hybrid_changed": len(changed),
scripts/run_hybrid_v12.py:708:            "recognizer": "DINOv2 v33",
scripts/run_hybrid_v12.py:709:            "rerank": "Hybrid v12",
scripts/run_hybrid_v12.py:731:    print("Images:", len(hybrid_rows))
scripts/run_hybrid_v12.py:732:    print("Hybrid changes:", len(changed))
scripts/benchmark_hybrid_v11.py:27:    "data/output/benchmark_hybrid_v11.json"
scripts/benchmark_hybrid_v11.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v11.py:286:        # DINO TOP1 is default.
scripts/benchmark_hybrid_v11.py:287:        # Change only if hybrid has strong evidence.
scripts/benchmark_hybrid_v02.py:27:    "data/output/benchmark_hybrid_v02.json"
scripts/benchmark_hybrid_v02.py:118:    print("HYBRID V02")
scripts/benchmark_hybrid_v02.py:158:        # GLOBAL DINO
scripts/banner_llm_folder_search_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/benchmark_qwen_vl.py:122:        description="Benchmark Qwen-VL models through Ollama"
scripts/benchmark_qwen_vl.py:134:            "qwen2.5-vl:7b",
scripts/benchmark_qwen_vl.py:135:            "qwen3-vl:4b",
scripts/benchmark_qwen_vl.py:166:    print("QWEN VL BENCHMARK")
scripts/benchmark_qwen_vl.py:341:        "benchmark_qwen_vl.json"
scripts/qwen4b_output_v01_before_compact_prompt.py:15:OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"
scripts/qwen4b_output_v01_before_compact_prompt.py:17:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01_before_compact_prompt.py:649:    print("QWEN3-VL 4B — OUTPUT ANALYSIS")
scripts/qwen4b_output_v01.py:29:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01.py:161:    Если Qwen был processing во время:
scripts/qwen4b_output_v01.py:176:                qwen_status = 'pending',
scripts/qwen4b_output_v01.py:178:            WHERE qwen_status = 'processing'
scripts/qwen4b_output_v01.py:188:            "[QWEN] Reset stale processing:",
scripts/qwen4b_output_v01.py:195:    Берёт следующую фотографию Qwen.
scripts/qwen4b_output_v01.py:199:    Qwen не зависит от DINO.
scripts/qwen4b_output_v01.py:203:        qwen_status = pending
scripts/qwen4b_output_v01.py:221:                qwen_status = 'pending'
scripts/qwen4b_output_v01.py:242:                qwen_status = 'processing',
scripts/qwen4b_output_v01.py:246:                AND qwen_status = 'pending'
scripts/qwen4b_output_v01.py:269:    Записывает результат Qwen в ту же запись photos.
scripts/qwen4b_output_v01.py:278:    Qwen никогда не создаёт новый объект фотографии.
scripts/qwen4b_output_v01.py:336:                qwen_status = 'done',
scripts/qwen4b_output_v01.py:344:                qwen_time_sec = %s,
scripts/qwen4b_output_v01.py:429:    Ошибка Qwen меняет только qwen_status.
scripts/qwen4b_output_v01.py:440:                qwen_status = 'error',
scripts/qwen4b_output_v01.py:470:# QWEN
scripts/qwen4b_output_v01.py:620:                    "[QWEN RETRY]"
scripts/qwen4b_output_v01.py:639:                "[QWEN JSON ERROR]",
scripts/qwen4b_output_v01.py:683:        "QWEN3-VL 4B — DATABASE WORKER"
scripts/qwen4b_output_v01.py:720:                WHERE qwen_status = 'pending'
scripts/qwen4b_output_v01.py:758:                    "QWEN QUEUE EMPTY"
scripts/qwen4b_output_v01.py:920:            "QWEN WORKER STOPPED"
scripts/benchmark_hybrid_v05.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v05.py:118:    print("HYBRID V03")
scripts/banner_llm_full_v01.py:9:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_model_compare_v02.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v02.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v01.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v01.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_database_v02.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/benchmark_hybrid_v04.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v04.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v01.py:27:    "data/output/benchmark_hybrid_v01.json"
scripts/benchmark_hybrid_v01.py:144:    print("HYBRID V01")
scripts/migrate_sqlite_to_postgres.py:75:                qwen_status,
scripts/migrate_sqlite_to_postgres.py:76:                qwen_time_sec,
scripts/migrate_sqlite_to_postgres.py:111:                row["qwen_status"],
scripts/migrate_sqlite_to_postgres.py:112:                row["qwen_time_sec"],
scripts/migrate_sqlite_to_postgres.py:165:                    qwen_status,
scripts/migrate_sqlite_to_postgres.py:166:                    qwen_time_sec,
scripts/dry_run_best_sequence.py:365:            f"  DINO:   "
scripts/benchmark_client_normalizer.py:111:def ask_qwen(raw_name, clients, model):
scripts/benchmark_client_normalizer.py:316:                result, elapsed = ask_qwen(
scripts/benchmark_client_models_25.py:24:    "qwen3:4b",
scripts/benchmark_client_models_25.py:25:    "qwen3:8b",
scripts/benchmark_client_models_25.py:26:    "qwen2.5:7b",
scripts/benchmark_client_models_25.py:164:def ask_qwen(raw_name, directory_names, model):
scripts/benchmark_client_models_25.py:351:                result = ask_qwen(
scripts/benchmark_hybrid_v07.py:27:    "data/output/benchmark_hybrid_v07.json"
scripts/benchmark_hybrid_v07.py:118:    print("HYBRID V03")
scripts/banner_database_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/llm_resolver_v01.py:11:MODEL = "qwen3:4b"
scripts/llm_resolver_v01.py:224:        print("--- QWEN3:4B ---")
scripts/benchmark_hybrid_v06.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v06.py:118:    print("HYBRID V03")
scripts/export_visual_compare.py:40:def export_hybrid():
scripts/export_visual_compare.py:44:            "data/output/full_recognize_hybrid_v12_test.json",
scripts/export_visual_compare.py:58:            "hybrid_v12" /
scripts/export_visual_compare.py:73:export_hybrid()
scripts/diagnose_dino_hybrid_db.py:29:                    dino_status,
scripts/diagnose_dino_hybrid_db.py:30:                    dino_fingerprint,
scripts/diagnose_dino_hybrid_db.py:31:                    dino_score,
scripts/diagnose_dino_hybrid_db.py:32:                    dino_second_score,
scripts/diagnose_dino_hybrid_db.py:33:                    dino_margin,
scripts/diagnose_dino_hybrid_db.py:34:                    hybrid_original_id,
scripts/diagnose_dino_hybrid_db.py:35:                    hybrid_final_id,
scripts/diagnose_dino_hybrid_db.py:36:                    hybrid_changed,
scripts/diagnose_dino_hybrid_db.py:37:                    hybrid_old_score,
scripts/diagnose_dino_hybrid_db.py:38:                    hybrid_score,
scripts/diagnose_dino_hybrid_db.py:39:                    hybrid_margin,
scripts/diagnose_dino_hybrid_db.py:40:                    hybrid_neighbors
scripts/diagnose_dino_hybrid_db.py:42:                WHERE dino_status = 'done'
scripts/diagnose_dino_hybrid_db.py:51:            print("DINO -> POSTGRES -> HYBRID DIAGNOSTIC")
scripts/diagnose_dino_hybrid_db.py:58:                print("NO DINO DONE ROWS")
scripts/diagnose_dino_hybrid_db.py:61:            dino_done = 0
scripts/diagnose_dino_hybrid_db.py:62:            dino_with_fp = 0
scripts/diagnose_dino_hybrid_db.py:63:            hybrid_done = 0
scripts/diagnose_dino_hybrid_db.py:64:            hybrid_changed = 0
scripts/diagnose_dino_hybrid_db.py:74:                    dino_status,
scripts/diagnose_dino_hybrid_db.py:75:                    dino_fp,
scripts/diagnose_dino_hybrid_db.py:76:                    dino_score,
scripts/diagnose_dino_hybrid_db.py:77:                    dino_second,
scripts/diagnose_dino_hybrid_db.py:78:                    dino_margin,
scripts/diagnose_dino_hybrid_db.py:79:                    hybrid_original,
scripts/diagnose_dino_hybrid_db.py:80:                    hybrid_final,
scripts/diagnose_dino_hybrid_db.py:81:                    hybrid_changed_value,
scripts/diagnose_dino_hybrid_db.py:82:                    hybrid_old_score,
scripts/diagnose_dino_hybrid_db.py:83:                    hybrid_score,
scripts/diagnose_dino_hybrid_db.py:84:                    hybrid_margin,
scripts/diagnose_dino_hybrid_db.py:85:                    hybrid_neighbors,
scripts/diagnose_dino_hybrid_db.py:88:                if dino_status == "done":
scripts/diagnose_dino_hybrid_db.py:89:                    dino_done += 1
scripts/diagnose_dino_hybrid_db.py:91:                if dino_fp:
scripts/diagnose_dino_hybrid_db.py:92:                    dino_with_fp += 1
scripts/diagnose_dino_hybrid_db.py:93:                    fingerprints[dino_fp] = fingerprints.get(dino_fp, 0) + 1
scripts/diagnose_dino_hybrid_db.py:95:                if hybrid_final is not None:
scripts/diagnose_dino_hybrid_db.py:96:                    hybrid_done += 1
scripts/diagnose_dino_hybrid_db.py:98:                if hybrid_changed_value:
scripts/diagnose_dino_hybrid_db.py:99:                    hybrid_changed += 1
scripts/diagnose_dino_hybrid_db.py:105:                print(f"dino_status         : {dino_status}")
scripts/diagnose_dino_hybrid_db.py:106:                print(f"dino_fingerprint    : {dino_fp}")
scripts/diagnose_dino_hybrid_db.py:107:                print(f"dino_score          : {dino_score}")
scripts/diagnose_dino_hybrid_db.py:108:                print(f"dino_second_score   : {dino_second}")
scripts/diagnose_dino_hybrid_db.py:109:                print(f"dino_margin         : {dino_margin}")
scripts/diagnose_dino_hybrid_db.py:110:                print(f"hybrid_original_id  : {hybrid_original}")
scripts/diagnose_dino_hybrid_db.py:111:                print(f"hybrid_final_id     : {hybrid_final}")
scripts/diagnose_dino_hybrid_db.py:112:                print(f"hybrid_changed      : {hybrid_changed_value}")
scripts/diagnose_dino_hybrid_db.py:113:                print(f"hybrid_old_score    : {hybrid_old_score}")
scripts/diagnose_dino_hybrid_db.py:114:                print(f"hybrid_score        : {hybrid_score}")
scripts/diagnose_dino_hybrid_db.py:115:                print(f"hybrid_margin       : {hybrid_margin}")
scripts/diagnose_dino_hybrid_db.py:116:                print(f"hybrid_neighbors    : {json.dumps(hybrid_neighbors, ensure_ascii=False)}")
scripts/diagnose_dino_hybrid_db.py:123:            print("DINO done           :", dino_done)
scripts/diagnose_dino_hybrid_db.py:124:            print("DINO with fingerprint:", dino_with_fp)
scripts/diagnose_dino_hybrid_db.py:125:            print("Hybrid final present:", hybrid_done)
scripts/diagnose_dino_hybrid_db.py:126:            print("Hybrid changed      :", hybrid_changed)
scripts/diagnose_dino_hybrid_db.py:129:            print("DINO fingerprints:")
scripts/diagnose_dino_hybrid_db.py:142:            print("  dino_fingerprint")
scripts/diagnose_dino_hybrid_db.py:143:            print("  dino_score")
scripts/diagnose_dino_hybrid_db.py:144:            print("  dino_second_score")
scripts/diagnose_dino_hybrid_db.py:145:            print("  dino_margin")
scripts/diagnose_dino_hybrid_db.py:147:            print("But old Hybrid v12 requires:")
scripts/benchmark_hybrid_v09.py:27:    "data/output/benchmark_hybrid_v09.json"
scripts/benchmark_hybrid_v09.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v09.py:286:        # DINO TOP1 is default.
scripts/benchmark_hybrid_v09.py:287:        # Change only if hybrid has strong evidence.
scripts/qwen_prompt_ablation.py:15:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen_prompt_ablation.py:218:    print("QWEN3-VL 4B — PROMPT ABLATION TEST")
scripts/banner_model_compare_v03.py:19:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v03.py:20:    "qwen3-vl:2b-instruct",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 👤 **User** — 2026-08-21 01:38:31

слишком длинны вывод

---

### 🤖 **Assistant** — 2026-08-21 01:38:33

Понял. Буду отвечать **коротко и по делу**, без длинных объяснений.

---

### 👤 **User** — 2026-08-21 01:38:47

я не могу загрузить слишком длинный вывод

---

### 🤖 **Assistant** — 2026-08-21 01:38:48

Да. Если вывод терминала слишком длинный, **не загружай весь**.

Лучше так:

```bash
команда 2>&1 | tail -100
```

или, если нужна ошибка:

```bash
команда 2>&1 | grep -iE 'error|fail|exception|traceback' -C 5
```

Если вывод нужен для диагностики целиком — сохрани в файл:

```bash
команда 2>&1 | tee /tmp/output.txt
```

и загрузи `/tmp/output.txt`.

**Для нашего проекта лучше присылай последние 100–200 строк + участок с ошибкой.**

---

