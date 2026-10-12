## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-20 23:18:08

echo "================ WATCHER FILES ================" && \
find app scripts -type f $ -name "*.py" -o -name "*.sh" $ -print0 | \
xargs -0 grep -lniE \
'watchdog|Observer|FileSystemEventHandler|watcher|watch.*input|input/daily|on_created|on_modified' | \
sort -u && \
echo "================ SYSTEMD LORA ================" && \
systemctl cat lora | sed -n '1,180p'
================ WATCHER FILES ================
app/pipeline/controller.py
app/pipeline/modes.py
app/pipeline/supervisor.py
app/web/components/technical_modules/automation.py
app/web/components/technical.py
scripts/run_daily_hybrid_v12.sh
================ SYSTEMD LORA ================
# /etc/systemd/system/lora.service
[Unit]
Description=LORA Photo Database
After=network-online.target zerotier-one.service
Wants=network-online.target

[Service]
Type=simple
User=alexice
WorkingDirectory=/home/alexice/projects/scene_fingerprint_mvp_v02

ExecStart=/home/alexice/.local/bin/uv run python -m app.web.main --host 0.0.0.0 --port 8081

Restart=always
RestartSec=5

Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ WATCH / PIPELINE REFERENCES ================" && \
grep -RniE \
'input/daily|output/daily|preview/daily|photo_id|create.*preview|preview.*create|dino|hybrid|process.*photo|process.*file|watcher' \
app scripts \
--include="*.py" \
--include="*.sh" | \
head -n 500
================ WATCH / PIPELINE REFERENCES ================
app/web/components/search.py:24:    DINO / fingerprint здесь НЕ используется.
app/web/components/technical_modules/photo_processing.py:21:DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
app/web/components/technical_modules/photo_processing.py:45:    dino_process = None
app/web/components/technical_modules/photo_processing.py:48:    dino_stopping = False
app/web/components/technical_modules/photo_processing.py:144:        dino = data.get("dino", {})
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
app/web/components/technical_modules/photo_processing.py:263:        dino_running = process_running(
app/web/components/technical_modules/photo_processing.py:264:            dino_process
app/web/components/technical_modules/photo_processing.py:279:            and not dino_running
app/web/components/technical_modules/photo_processing.py:294:            dino_status_label,
app/web/components/technical_modules/photo_processing.py:295:            dino_running,
app/web/components/technical_modules/photo_processing.py:296:            dino_error > 0,
app/web/components/technical_modules/photo_processing.py:309:        if dino_running or qwen_running:
app/web/components/technical_modules/photo_processing.py:316:        elif dino_error or qwen_error:
app/web/components/technical_modules/photo_processing.py:335:            dino_running
app/web/components/technical_modules/photo_processing.py:340:            dino_running
app/web/components/technical_modules/photo_processing.py:344:        dino_run_button.enabled = not (
app/web/components/technical_modules/photo_processing.py:345:            dino_running
app/web/components/technical_modules/photo_processing.py:348:        dino_stop_button.enabled = (
app/web/components/technical_modules/photo_processing.py:349:            dino_running
app/web/components/technical_modules/photo_processing.py:404:    # START DINO
app/web/components/technical_modules/photo_processing.py:407:    async def start_dino():
app/web/components/technical_modules/photo_processing.py:409:        nonlocal dino_process
app/web/components/technical_modules/photo_processing.py:410:        nonlocal dino_stopping
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
app/web/components/technical_modules/photo_processing.py:693:        await start_dino()
app/web/components/technical_modules/photo_processing.py:706:            process_running(dino_process)
app/web/components/technical_modules/photo_processing.py:716:            await stop_dino()
app/web/components/technical_modules/photo_processing.py:720:                "Остановка DINO и Qwen запрошена",
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
app/web/components/technical_modules/photo_processing.py:1060:            "DINO и Qwen работают независимо. "
app/web/components/technical_modules/photo_processing.py:1071:    dino_stop_button.disable()
app/web/components/technical_modules/fingerprints.py:17:            "Рабочая версия: DINO / v33"
app/web/components/technical_modules/data.py:298:        # DINO
app/web/components/technical_modules/data.py:308:                    "DINO v33"
app/web/components/technical_modules/data.py:327:        # HYBRID
app/web/components/technical_modules/data.py:337:                    "Hybrid v12"
app/web/components/technical_modules/automation.py:12:    set_watcher,
app/web/components/technical_modules/automation.py:17:    MODE_WATCHER,
app/web/components/technical_modules/automation.py:62:                    MODE_WATCHER: "Watcher",
app/web/components/technical_modules/automation.py:79:                    MODE_WATCHER,
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
app/web/components/technical_modules/automation.py:393:            elif current.mode == MODE_WATCHER:
app/web/components/technical_modules/automation.py:394:                path = current.watcher_path or "—"
app/web/components/technical_modules/automation.py:397:                    "● Режим: Watcher"
app/web/components/technical_modules/automation.py:418:            watcher_enabled = (
app/web/components/technical_modules/automation.py:419:                current.mode == MODE_WATCHER
app/web/components/technical_modules/automation.py:426:            watcher_path_input.enabled = True
app/web/components/technical_modules/automation.py:450:                elif mode == MODE_WATCHER:
app/web/components/technical_modules/automation.py:452:                    watcher_path = (
app/web/components/technical_modules/automation.py:453:                        watcher_path_input.value or ""
app/web/components/technical_modules/automation.py:456:                    if not watcher_path:
app/web/components/technical_modules/automation.py:458:                            "Укажите папку для Watcher",
app/web/components/technical_modules/automation.py:464:                    set_watcher(
app/web/components/technical_modules/automation.py:465:                        watcher_path
app/web/components/technical_modules/automation.py:496:        # WATCHER PATH CHANGE
app/web/components/technical_modules/automation.py:499:        def watcher_path_changed(event):
app/web/components/technical_modules/automation.py:503:            if current.mode != MODE_WATCHER:
app/web/components/technical_modules/automation.py:513:                    "Путь Watcher не может быть пустым",
app/web/components/technical_modules/automation.py:522:                set_watcher(path)
app/web/components/technical_modules/automation.py:529:                    "[AUTOMATION] WATCHER PATH ERROR:",
app/web/components/technical_modules/automation.py:535:                    f"Ошибка пути Watcher: {exc}",
app/web/components/technical_modules/automation.py:541:        watcher_path_input.on(
app/web/components/technical_modules/automation.py:543:            watcher_path_changed,
app/web/components/technical_modules/qwen.py:180:def _find_latest_hybrid():
app/web/components/technical_modules/qwen.py:350:            result_dir = _find_latest_hybrid()
app/web/components/technical_modules/qwen.py:355:                    "[QWEN MANUAL] HYBRID RUN NOT FOUND",
app/web/components/technical_modules/qwen.py:360:                    "Не найден ни один запуск Hybrid.",
app/web/components/technical_modules/qwen.py:387:                    f"В последнем Hybrid нет фотографий: {result_dir}",
app/web/components/addresses.py:28:    # а не физические папки output/daily.
app/web/components/photos.py:293:    # Никакого output/daily.
app/web/components/photos.py:305:        if not str(record.get("photo_id") or "").strip():
app/web/components/photos.py:345:        # dino_fingerprint.
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/components/photos.py:350:        # Если DINO fingerprint отсутствует —
app/web/components/photos.py:355:            record.get("dino_fingerprint") or ""
app/web/components/photos.py:364:        # На данном этапе dino_fingerprint сам является
app/web/components/photos.py:459:        "only photos with DINO fingerprint + address_directory",
app/web/photo_db.py:20:            photo_id,
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
app/web/photo_db.py:132:        "dino": {
app/core/scene_analyzer.py:388:        # GLOBAL DINO
app/core/recognizer.py:26:        DINO patch tokens
app/core/recognizer.py:204:        # One DINO pass for all query images.
app/core/recognizer.py:571:        # DINO
app/core/config.py:14:        "facebook/dinov2-base"
app/core/embedder.py:10:    """DINOv2 ViT-B/14 global embedding service.
app/core/embedder.py:37:            f"[SceneEmbedder] Loading DINOv2: "
app/core/embedder.py:101:            # DINOv2 CLS token.
app/core/fingerprint.py:229:                "Invalid DINO embedding "
app/core/fingerprint.py:386:            "model": "dinov2_vitb14",
app/pipeline/modes.py:10:MODE_WATCHER = "watcher"
app/pipeline/modes.py:16:    MODE_WATCHER,
app/pipeline/modes.py:27:    watcher_enabled: bool = False
app/pipeline/modes.py:28:    watcher_path: Optional[str] = None
app/pipeline/modes.py:48:        watcher_enabled=False,
app/pipeline/modes.py:49:        watcher_path=None,
app/pipeline/modes.py:63:        watcher_enabled=False,
app/pipeline/modes.py:64:        watcher_path=None,
app/pipeline/modes.py:70:def build_watcher_mode(
app/pipeline/modes.py:71:    watcher_path: str,
app/pipeline/modes.py:74:    if not watcher_path:
app/pipeline/modes.py:76:            "Watcher path is required"
app/pipeline/modes.py:80:        mode=MODE_WATCHER,
app/pipeline/modes.py:83:        watcher_enabled=True,
app/pipeline/modes.py:84:        watcher_path=watcher_path,
app/pipeline/controller.py:12:    MODE_WATCHER,
app/pipeline/controller.py:16:    build_watcher_mode,
app/pipeline/controller.py:60:                    watcher_enabled,
app/pipeline/controller.py:61:                    watcher_path,
app/pipeline/controller.py:80:        watcher_enabled=bool(row["watcher_enabled"]),
app/pipeline/controller.py:81:        watcher_path=row["watcher_path"],
app/pipeline/controller.py:99:                    watcher_enabled = %s,
app/pipeline/controller.py:100:                    watcher_path = %s,
app/pipeline/controller.py:110:                    state.watcher_enabled,
app/pipeline/controller.py:111:                    state.watcher_path,
app/pipeline/controller.py:144:def set_watcher(watcher_path: str):
app/pipeline/controller.py:145:    state = build_watcher_mode(watcher_path)
app/pipeline/controller.py:225:def start_watcher():
app/pipeline/controller.py:228:    if state.mode != MODE_WATCHER:
app/pipeline/controller.py:230:            "Watcher start requested while mode is not watcher"
app/pipeline/controller.py:286:        watcher   -> watcher
app/pipeline/controller.py:289:    Это позволяет automatic/watcher продолжить работу
app/pipeline/controller.py:324:                    watcher_enabled = FALSE,
app/pipeline/controller.py:325:                    watcher_path = NULL,
app/pipeline/recovery.py:43:    recovered_dino = 0
app/pipeline/recovery.py:54:                    dino_status = 'pending',
app/pipeline/recovery.py:55:                    dino_started_at = NULL,
app/pipeline/recovery.py:58:                    dino_status = 'processing'
app/pipeline/recovery.py:59:                    AND dino_started_at < %s
app/pipeline/recovery.py:64:            recovered_dino = cur.rowcount
app/pipeline/recovery.py:85:        "dino": recovered_dino,
app/pipeline/supervisor.py:15:    start_watcher,
app/pipeline/supervisor.py:22:DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
app/pipeline/supervisor.py:187:    Один полный запуск DINO + Qwen.
app/pipeline/supervisor.py:190:        DINO -> PostgreSQL dino_status
app/pipeline/supervisor.py:196:    dino_process = None
app/pipeline/supervisor.py:199:    dino_output = None
app/pipeline/supervisor.py:223:        dino_process, dino_output = (
app/pipeline/supervisor.py:225:                DINO_WORKER,
app/pipeline/supervisor.py:226:                "DINO",
app/pipeline/supervisor.py:245:            dino_running = process_running(
app/pipeline/supervisor.py:246:                dino_process
app/pipeline/supervisor.py:253:            if not dino_running and not qwen_running:
app/pipeline/supervisor.py:264:                    dino_process,
app/pipeline/supervisor.py:265:                    "DINO",
app/pipeline/supervisor.py:283:        dino_code = (
app/pipeline/supervisor.py:284:            dino_process.returncode
app/pipeline/supervisor.py:285:            if dino_process is not None
app/pipeline/supervisor.py:296:            "[SUPERVISOR] DINO exit:",
app/pipeline/supervisor.py:297:            dino_code,
app/pipeline/supervisor.py:308:            dino_code,
app/pipeline/supervisor.py:319:            dino_process,
app/pipeline/supervisor.py:320:            "DINO",
app/pipeline/supervisor.py:329:            dino_output,
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
app/pipeline/supervisor.py:740:    if not DINO_WORKER.exists():
app/pipeline/supervisor.py:742:            f"DINO worker not found: {DINO_WORKER}"
app/pipeline/supervisor.py:787:        # WATCHER
app/pipeline/supervisor.py:790:        elif state.mode == "watcher":
app/pipeline/supervisor.py:792:            started = await wait_watcher_event()
app/workers/qwen_worker.py:159:        Qwen работает независимо от DINO.
app/workers/qwen_worker.py:162:        photo_id -> результат Qwen
app/workers/qwen_worker.py:173:                photo_id,
app/workers/qwen_worker.py:220:    photo_id остаётся постоянным идентификатором
app/workers/qwen_worker.py:552:        "[QWEN] Works independently from DINO."
app/workers/qwen_worker.py:558:        "[QWEN] Identity: photos.photo_id"
app/workers/qwen_worker.py:621:            photo_id = row["photo_id"]
app/workers/qwen_worker.py:628:                f"[QWEN] {photo_id}"
app/workers/qwen_worker.py:669:                    photo_id,
app/workers/qwen_worker.py:714:                    photo_id,
app/workers/dino_worker.py:35:    Возвращает зависшие DINO-задачи обратно в очередь.
app/workers/dino_worker.py:49:                dino_status = 'pending',
app/workers/dino_worker.py:51:            WHERE dino_status = 'processing'
app/workers/dino_worker.py:61:            f"[DINO] Reset stale processing jobs: {count}"
app/workers/dino_worker.py:67:    Забирает следующую фотографию из DINO-очереди.
app/workers/dino_worker.py:73:    DINO получает фотографию только потому,
app/workers/dino_worker.py:74:    что у неё уже существует photo_id и
app/workers/dino_worker.py:75:    dino_status = pending.
app/workers/dino_worker.py:86:                photo_id,
app/workers/dino_worker.py:92:                dino_status = 'pending'
app/workers/dino_worker.py:111:                dino_status = 'processing',
app/workers/dino_worker.py:115:                AND dino_status = 'pending'
app/workers/dino_worker.py:136:    Сохраняет результат DINO.
app/workers/dino_worker.py:140:        address_id = адрес, определённый DINO.
app/workers/dino_worker.py:142:    photo_id остаётся независимым идентификатором фотографии.
app/workers/dino_worker.py:153:                dino_status = 'done',
app/workers/dino_worker.py:157:                dino_fingerprint = %s,
app/workers/dino_worker.py:158:                dino_score = %s,
app/workers/dino_worker.py:159:                dino_second_score = %s,
app/workers/dino_worker.py:160:                dino_margin = %s,
app/workers/dino_worker.py:161:                dino_time_sec = %s,
app/workers/dino_worker.py:207:                dino_status = 'error',
app/workers/dino_worker.py:230:    print("DINO WORKER")
app/workers/dino_worker.py:240:    print("[DINO] Loading SceneEmbedder...")
app/workers/dino_worker.py:261:    print("[DINO] Database connected.")
app/workers/dino_worker.py:269:    print("[DINO] Worker ready.")
app/workers/dino_worker.py:273:            "DINO_MAX_ITEMS",
app/workers/dino_worker.py:294:                    f"[DINO] "
app/workers/dino_worker.py:308:                    "[DINO] Queue empty."
app/workers/dino_worker.py:314:            photo_id = row["photo_id"]
app/workers/dino_worker.py:324:                "[DINO]",
app/workers/dino_worker.py:325:                photo_id,
app/workers/dino_worker.py:377:                    f"[DINO] DONE "
app/workers/dino_worker.py:378:                    f"{photo_id}"
app/workers/dino_worker.py:401:                    f"[DINO] ERROR "
app/workers/dino_worker.py:402:                    f"{photo_id}: {exc}"
app/workers/dino_worker.py:417:                        "[DINO] "
app/workers/dino_worker.py:428:        print("DINO WORKER STOPPED")
scripts/banner_search_v03.py:238:def process_photo(
scripts/banner_search_v03.py:475:                process_photo,
scripts/create_previews_v01.py:19:def create_preview(source: Path, destination: Path):
scripts/create_previews_v01.py:48:        description="Create web previews for processed photos"
scripts/create_previews_v01.py:54:        help="Hybrid output directory",
scripts/create_previews_v01.py:109:            result = create_preview(
scripts/banner_model_compare_v05.py:151:def process_model(model, files, summary):
scripts/benchmark_hybrid_v08.py:27:    "data/output/benchmark_hybrid_v08.json"
scripts/benchmark_hybrid_v08.py:118:    print("HYBRID V03")
scripts/photo_ingest.py:38:    Следующий постоянный PHOTO_ID.
scripts/photo_ingest.py:49:            SELECT photo_id
scripts/photo_ingest.py:51:            WHERE photo_id LIKE 'PH_%'
scripts/photo_ingest.py:59:    for (photo_id,) in rows:
scripts/photo_ingest.py:61:        if not photo_id:
scripts/photo_ingest.py:64:        value = str(photo_id)
scripts/photo_ingest.py:93:    DINO и Qwen.
scripts/photo_ingest.py:135:def make_photo_id(number):
scripts/photo_ingest.py:209:    photo_id,
scripts/photo_ingest.py:218:        - DINO
scripts/photo_ingest.py:236:                photo_id,
scripts/photo_ingest.py:247:                dino_status,
scripts/photo_ingest.py:271:                photo_id,
scripts/photo_ingest.py:393:            photo_id = make_photo_id(
scripts/photo_ingest.py:407:                photo_id,
scripts/photo_ingest.py:418:                f"{photo_id}"
scripts/photo_ingest.py:462:        "  DINO : dino_status = pending"
scripts/photo_ingest.py:485:            "assign photo_id and initial_id, "
scripts/photo_ingest.py:487:            "DINO/Qwen queues."
scripts/benchmark_hybrid_v03.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v03.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v12_full.py:27:    "data/output/full_recognize_hybrid_v12_test.json"
scripts/benchmark_hybrid_v12_full.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v12_full.py:287:        # DINO TOP1 is default.
scripts/benchmark_hybrid_v12_full.py:288:        # Change only if hybrid has strong evidence.
scripts/run_daily_hybrid_v12.sh:7:INPUT="$PROJECT/data/input/daily"
scripts/run_daily_hybrid_v12.sh:11:OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"
scripts/run_daily_hybrid_v12.sh:15:echo "SCENE FINGERPRINT — DAILY HYBRID V12"
scripts/run_daily_hybrid_v12.sh:42:/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
scripts/benchmark_hybrid_v10_debug.py:27:    "data/output/benchmark_hybrid_v09.json"
scripts/benchmark_hybrid_v10_debug.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v10_debug.py:286:        # DINO TOP1 is default.
scripts/benchmark_hybrid_v10_debug.py:287:        # Change only if hybrid has strong evidence.
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
scripts/qwen4b_output_v01_before_compact_prompt.py:439:def process(files):
scripts/qwen4b_output_v01_before_compact_prompt.py:669:    process(files)
scripts/qwen4b_output_v01.py:199:    Qwen не зависит от DINO.
scripts/qwen4b_output_v01.py:215:                photo_id,
scripts/qwen4b_output_v01.py:274:        photo_id
scripts/qwen4b_output_v01.py:675:            "Process only N pending photos"
scripts/qwen4b_output_v01.py:765:            photo_id = row[
scripts/qwen4b_output_v01.py:766:                "photo_id"
scripts/qwen4b_output_v01.py:783:                photo_id,
scripts/qwen4b_output_v01.py:834:                    "| photo_id:",
scripts/qwen4b_output_v01.py:835:                    photo_id,
scripts/benchmark_hybrid_v05.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v05.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v04.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v04.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v01.py:27:    "data/output/benchmark_hybrid_v01.json"
scripts/benchmark_hybrid_v01.py:144:    print("HYBRID V01")
scripts/dry_run_best_sequence.py:365:            f"  DINO:   "
scripts/benchmark_hybrid_v07.py:27:    "data/output/benchmark_hybrid_v07.json"
scripts/benchmark_hybrid_v07.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v06.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v06.py:118:    print("HYBRID V03")
scripts/export_visual_compare.py:40:def export_hybrid():
scripts/export_visual_compare.py:44:            "data/output/full_recognize_hybrid_v12_test.json",
scripts/export_visual_compare.py:58:            "hybrid_v12" /
scripts/export_visual_compare.py:73:export_hybrid()
scripts/benchmark_hybrid_v09.py:27:    "data/output/benchmark_hybrid_v09.json"
scripts/benchmark_hybrid_v09.py:118:    print("HYBRID V03")
scripts/benchmark_hybrid_v09.py:286:        # DINO TOP1 is default.
scripts/benchmark_hybrid_v09.py:287:        # Change only if hybrid has strong evidence.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:18:09

Да. По этому выводу уже видно важную вещь: **Watcher сам не создаёт `photo_id` и превью**. Он только обнаруживает новые файлы и запускает общий pipeline.

Цепочка сейчас выглядит так:

```text
Watcher
   ↓
обнаружил новый JPG
   ↓
start_watcher()
   ↓
полный pipeline
   ↓
photo_ingest.py
   ├── создаёт PH_000000XX
   ├── создаёт запись в PostgreSQL
   ├── ставит dino_status = pending
   └── ставит qwen_status = pending
          ↓
       DINO worker
          ↓
       Hybrid
```

При этом у нас есть отдельный `scripts/create_previews_v01.py`, но по текущему grep **не видно, что именно Watcher вызывает его на этапе ingest**.

И это как раз надо проверить, потому что твоя логика должна быть:

```text
НОВОЕ ФОТО
   │
   ├── photo_id = PH_xxxxxxxx
   │
   ├── original/source_path → data/input/daily/...
   │
   ├── preview → data/preview/daily/...   ← сразу
   │
   └── PostgreSQL
         │
         ├── photo_id
         ├── source_path
         ├── preview_path
         ├── filename
         ├── ...
         ├── dino_status = pending
         └── qwen_status = pending
                 │
                 ↓
             DINO / Hybrid
                 │
                 ↓
          появляется address / fingerprint
                 │
                 ↓
              GRID
```

А **грид вообще не должен физически искать оригиналы**. Он получает список `photo_id`/записей из PostgreSQL после фильтрации, а затем:

```text
photo_id
   ↓
preview_path
   ↓
data/preview/...
```

При открытии карточки:

```text
photo_id
   ↓
source_path
   ↓
data/input/daily/оригинал.JPG
```

И Qwen/DINO/Hybrid всё это время привязаны к **тому же `photo_id`**, а не к имени файла или пути.

### Следующий шаг

Нам сейчас надо не менять код, а **точно найти место создания записи `photos` и место создания preview** и посмотреть, вызываются ли они одной операцией.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \

echo "================ PHOTO INGEST =================" && \
nl -ba scripts/photo_ingest.py | sed -n '1,520p' && \

echo "================ SUPERVISOR WATCHER =================" && \
nl -ba app/pipeline/supervisor.py | sed -n '480,735p' && \

echo "================ PREVIEW SCRIPT =================" && \
nl -ba scripts/create_previews_v01.py | sed -n '1,180p' && \

echo "================ PREVIEW CALLS =================" && \
grep -RniE \
'create_previews|create_preview|preview_path|scripts/create_previews' \
app scripts \
--include="*.py" \
--include="*.sh" | \
grep -vE 'benchmark|before_cache|__pycache__'
```

**Особенно интересуют последние 4 блока.**

После этого мы сможем точно установить:

1. где рождается `PH_000000XX`;
2. где создаётся preview;
3. записывается ли `preview_path` в PostgreSQL;
4. кто первым запускается — preview или DINO;
5. почему сейчас `preview_path` в БД пустой;
6. где лучше исправить архитектуру, чтобы **preview + `photo_id` создавались сразу при поступлении фотографии, независимо от DINO/Hybrid**.

И я бы пока **не трогал `photos.py`**. Судя по найденному коду, проблема гораздо ниже — на этапе ingest/pipeline.

---

### 👤 **User** — 2026-08-20 23:19:17

echo "================ PHOTO INGEST =================" && \
nl -ba scripts/photo_ingest.py | sed -n '1,520p' && \

echo "================ SUPERVISOR WATCHER =================" && \
nl -ba app/pipeline/supervisor.py | sed -n '480,735p' && \

echo "================ PREVIEW SCRIPT =================" && \
nl -ba scripts/create_previews_v01.py | sed -n '1,180p' && \

echo "================ PREVIEW CALLS =================" && \
grep -RniE \
'create_previews|create_preview|preview_path|scripts/create_previews' \
app scripts \
--include="*.py" \
--include="*.sh" | \
grep -vE 'benchmark|before_cache|__pycache__'
================ PHOTO INGEST =================
     1	#!/usr/bin/env python3
     2	
     3	from __future__ import annotations
     4	
     5	import argparse
     6	import os
     7	from pathlib import Path
     8	
     9	import psycopg2
    10	
    11	
    12	PROJECT = Path(__file__).resolve().parent.parent
    13	
    14	
    15	DB_CONFIG = {
    16	    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    17	    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    18	    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
    19	    "user": os.getenv("PHOTOBASE_USER", "lora"),
    20	    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    21	}
    22	
    23	
    24	IMAGE_EXTENSIONS = {
    25	    ".jpg",
    26	    ".jpeg",
    27	    ".png",
    28	    ".webp",
    29	}
    30	
    31	
    32	# ============================================================
    33	# ID
    34	# ============================================================
    35	
    36	def get_next_photo_number(conn):
    37	    """
    38	    Следующий постоянный PHOTO_ID.
    39	
    40	    PH_00000001
    41	    PH_00000002
    42	    ...
    43	    """
    44	
    45	    with conn.cursor() as cur:
    46	
    47	        cur.execute(
    48	            """
    49	            SELECT photo_id
    50	            FROM photos
    51	            WHERE photo_id LIKE 'PH_%'
    52	            """
    53	        )
    54	
    55	        rows = cur.fetchall()
    56	
    57	    max_number = 0
    58	
    59	    for (photo_id,) in rows:
    60	
    61	        if not photo_id:
    62	            continue
    63	
    64	        value = str(photo_id)
    65	
    66	        if not value.startswith("PH_"):
    67	            continue
    68	
    69	        try:
    70	            number = int(
    71	                value[3:]
    72	            )
    73	        except ValueError:
    74	            continue
    75	
    76	        max_number = max(
    77	            max_number,
    78	            number,
    79	        )
    80	
    81	    return max_number + 1
    82	
    83	
    84	def get_next_initial_number(conn):
    85	    """
    86	    Следующий внутренний INITIAL_ID.
    87	
    88	    IN_00000001
    89	    IN_00000002
    90	    ...
    91	
    92	    INITIAL_ID не зависит от адреса,
    93	    DINO и Qwen.
    94	    """
    95	
    96	    with conn.cursor() as cur:
    97	
    98	        cur.execute(
    99	            """
   100	            SELECT initial_id
   101	            FROM photos
   102	            WHERE initial_id LIKE 'IN_%'
   103	            """
   104	        )
   105	
   106	        rows = cur.fetchall()
   107	
   108	    max_number = 0
   109	
   110	    for (initial_id,) in rows:
   111	
   112	        if not initial_id:
   113	            continue
   114	
   115	        value = str(initial_id)
   116	
   117	        if not value.startswith("IN_"):
   118	            continue
   119	
   120	        try:
   121	            number = int(
   122	                value[3:]
   123	            )
   124	        except ValueError:
   125	            continue
   126	
   127	        max_number = max(
   128	            max_number,
   129	            number,
   130	        )
   131	
   132	    return max_number + 1
   133	
   134	
   135	def make_photo_id(number):
   136	    return f"PH_{number:08d}"
   137	
   138	
   139	def make_initial_id(number):
   140	    return f"IN_{number:08d}"
   141	
   142	
   143	# ============================================================
   144	# PATHS
   145	# ============================================================
   146	
   147	def normalize_path(path):
   148	    return str(
   149	        Path(path)
   150	        .expanduser()
   151	        .resolve()
   152	    )
   153	
   154	
   155	def get_existing_source_paths(conn):
   156	    """
   157	    Уже зарегистрированные source_path.
   158	
   159	    Используется для безопасного продолжения
   160	    после прерывания ingest.
   161	    """
   162	
   163	    with conn.cursor() as cur:
   164	
   165	        cur.execute(
   166	            """
   167	            SELECT source_path
   168	            FROM photos
   169	            WHERE source_path IS NOT NULL
   170	              AND source_path <> ''
   171	            """
   172	        )
   173	
   174	        return {
   175	            normalize_path(row[0])
   176	            for row in cur.fetchall()
   177	            if row[0]
   178	        }
   179	
   180	
   181	def find_images(input_dir):
   182	    """
   183	    Сканирует только файлы непосредственно
   184	    во входной папке.
   185	
   186	    Подкаталоги пока не трогаем.
   187	    """
   188	
   189	    return sorted(
   190	        (
   191	            p
   192	            for p in input_dir.iterdir()
   193	            if (
   194	                p.is_file()
   195	                and p.suffix.lower()
   196	                in IMAGE_EXTENSIONS
   197	            )
   198	        ),
   199	        key=lambda p: p.name.casefold(),
   200	    )
   201	
   202	
   203	# ============================================================
   204	# REGISTER
   205	# ============================================================
   206	
   207	def register_photo(
   208	    conn,
   209	    photo_id,
   210	    initial_id,
   211	    source_path,
   212	):
   213	    """
   214	    Создаёт единую первичную запись фотографии.
   215	
   216	    На этом этапе НЕ происходит:
   217	
   218	        - DINO
   219	        - Qwen
   220	        - сортировка
   221	        - определение адреса
   222	        - создание превью
   223	
   224	    Здесь только создаётся объект PHOTО.
   225	    """
   226	
   227	    source = Path(source_path)
   228	
   229	    filename = source.name
   230	
   231	    with conn.cursor() as cur:
   232	
   233	        cur.execute(
   234	            """
   235	            INSERT INTO photos (
   236	                photo_id,
   237	                initial_id,
   238	
   239	                source_path,
   240	                path,
   241	
   242	                filename,
   243	                original_filename,
   244	
   245	                status,
   246	
   247	                dino_status,
   248	                qwen_status,
   249	                sort_status,
   250	                preview_status
   251	            )
   252	            VALUES (
   253	                %s,
   254	                %s,
   255	
   256	                %s,
   257	                %s,
   258	
   259	                %s,
   260	                %s,
   261	
   262	                'pending',
   263	
   264	                'pending',
   265	                'pending',
   266	                'pending',
   267	                'pending'
   268	            )
   269	            """,
   270	            (
   271	                photo_id,
   272	                initial_id,
   273	
   274	                source_path,
   275	                source_path,
   276	
   277	                filename,
   278	                filename,
   279	            ),
   280	        )
   281	
   282	
   283	# ============================================================
   284	# INGEST
   285	# ============================================================
   286	
   287	def ingest(input_dir):
   288	
   289	    input_dir = (
   290	        input_dir
   291	        .expanduser()
   292	        .resolve()
   293	    )
   294	
   295	    if not input_dir.exists():
   296	
   297	        raise RuntimeError(
   298	            "Input directory does not exist:\n"
   299	            f"{input_dir}"
   300	        )
   301	
   302	    if not input_dir.is_dir():
   303	
   304	        raise RuntimeError(
   305	            "Input path is not a directory:\n"
   306	            f"{input_dir}"
   307	        )
   308	
   309	    images = find_images(
   310	        input_dir
   311	    )
   312	
   313	    print("=" * 80)
   314	    print("PHOTO INGEST")
   315	    print("=" * 80)
   316	    print()
   317	    print("INPUT :", input_dir)
   318	    print("FILES :", len(images))
   319	    print()
   320	
   321	    if not images:
   322	
   323	        print(
   324	            "No images found."
   325	        )
   326	
   327	        return
   328	
   329	    with psycopg2.connect(
   330	        **DB_CONFIG
   331	    ) as conn:
   332	
   333	        # ----------------------------------------------------
   334	        # Existing
   335	        # ----------------------------------------------------
   336	
   337	        existing_paths = (
   338	            get_existing_source_paths(
   339	                conn
   340	            )
   341	        )
   342	
   343	        # ----------------------------------------------------
   344	        # Next IDs
   345	        # ----------------------------------------------------
   346	
   347	        next_photo_number = (
   348	            get_next_photo_number(
   349	                conn
   350	            )
   351	        )
   352	
   353	        next_initial_number = (
   354	            get_next_initial_number(
   355	                conn
   356	            )
   357	        )
   358	
   359	        registered = 0
   360	        skipped = 0
   361	
   362	        # ----------------------------------------------------
   363	        # REGISTER
   364	        # ----------------------------------------------------
   365	
   366	        for image in images:
   367	
   368	            source_path = (
   369	                normalize_path(
   370	                    image
   371	                )
   372	            )
   373	
   374	            # -----------------------------------------------
   375	            # Already registered
   376	            # -----------------------------------------------
   377	
   378	            if source_path in existing_paths:
   379	
   380	                print(
   381	                    f"[SKIP]      {image.name}"
   382	                    " — already registered"
   383	                )
   384	
   385	                skipped += 1
   386	
   387	                continue
   388	
   389	            # -----------------------------------------------
   390	            # Create IDs
   391	            # -----------------------------------------------
   392	
   393	            photo_id = make_photo_id(
   394	                next_photo_number
   395	            )
   396	
   397	            initial_id = make_initial_id(
   398	                next_initial_number
   399	            )
   400	
   401	            # -----------------------------------------------
   402	            # DB record
   403	            # -----------------------------------------------
   404	
   405	            register_photo(
   406	                conn,
   407	                photo_id,
   408	                initial_id,
   409	                source_path,
   410	            )
   411	
   412	            existing_paths.add(
   413	                source_path
   414	            )
   415	
   416	            print(
   417	                f"[REGISTER] "
   418	                f"{photo_id}"
   419	                f" | initial={initial_id}"
   420	                f" | {image.name}"
   421	            )
   422	
   423	            registered += 1
   424	
   425	            next_photo_number += 1
   426	            next_initial_number += 1
   427	
   428	        conn.commit()
   429	
   430	    # ========================================================
   431	    # REPORT
   432	    # ========================================================
   433	
   434	    print()
   435	    print("=" * 80)
   436	    print("INGEST FINISHED")
   437	    print("=" * 80)
   438	    print()
   439	
   440	    print(
   441	        "Found      :",
   442	        len(images),
   443	    )
   444	
   445	    print(
   446	        "Registered :",
   447	        registered,
   448	    )
   449	
   450	    print(
   451	        "Skipped    :",
   452	        skipped,
   453	    )
   454	
   455	    print()
   456	
   457	    print(
   458	        "New photos are now available to:"
   459	    )
   460	
   461	    print(
   462	        "  DINO : dino_status = pending"
   463	    )
   464	
   465	    print(
   466	        "  QWEN : qwen_status = pending"
   467	    )
   468	
   469	    print()
   470	
   471	    print(
   472	        "No address has been assigned yet."
   473	    )
   474	
   475	
   476	# ============================================================
   477	# CLI
   478	# ============================================================
   479	
   480	def main():
   481	
   482	    parser = argparse.ArgumentParser(
   483	        description=(
   484	            "Register new photos, "
   485	            "assign photo_id and initial_id, "
   486	            "and put them into independent "
   487	            "DINO/Qwen queues."
   488	        )
   489	    )
   490	
   491	    parser.add_argument(
   492	        "--input",
   493	        type=Path,
   494	        required=True,
   495	        help=(
   496	            "Directory with incoming photos"
   497	        ),
   498	    )
   499	
   500	    args = parser.parse_args()
   501	
   502	    ingest(
   503	        args.input
   504	    )
   505	
   506	
   507	if __name__ == "__main__":
   508	    main()
================ SUPERVISOR WATCHER =================
   480	        if state.running:
   481	            return True
   482	
   483	        await asyncio.sleep(
   484	            POLL_INTERVAL
   485	        )
   486	
   487	
   488	# ============================================================
   489	# WATCHER
   490	# ============================================================
   491	
   492	WATCHER_EXTENSIONS = {
   493	    ".jpg",
   494	    ".jpeg",
   495	    ".png",
   496	    ".webp",
   497	}
   498	
   499	
   500	def watcher_snapshot(folder: Path):
   501	    """
   502	    Возвращает текущее состояние фотографий в папке.
   503	
   504	    Ключ:
   505	        абсолютный путь
   506	
   507	    Значение:
   508	        (size, mtime_ns)
   509	
   510	    Поэтому изменение существующего файла тоже
   511	    может быть замечено, но только как новое событие
   512	    после изменения baseline.
   513	    """
   514	
   515	    if not folder.exists():
   516	        return {}
   517	
   518	    if not folder.is_dir():
   519	        return {}
   520	
   521	    result = {}
   522	
   523	    try:
   524	        for item in folder.iterdir():
   525	
   526	            if not item.is_file():
   527	                continue
   528	
   529	            if item.suffix.lower() not in WATCHER_EXTENSIONS:
   530	                continue
   531	
   532	            try:
   533	                stat = item.stat()
   534	
   535	            except OSError:
   536	                continue
   537	
   538	            result[str(item.resolve())] = (
   539	                stat.st_size,
   540	                stat.st_mtime_ns,
   541	            )
   542	
   543	    except OSError as exc:
   544	
   545	        print(
   546	            "[SUPERVISOR] WATCHER SCAN ERROR:",
   547	            repr(exc),
   548	            flush=True,
   549	        )
   550	
   551	    return result
   552	
   553	
   554	async def wait_watcher_event():
   555	    """
   556	    Ждёт появления нового/изменённого фото.
   557	
   558	    Уже существующие фотографии при входе в Watcher
   559	    не считаются событием.
   560	
   561	    Перед запуском pipeline новый файл должен оставаться
   562	    неизменным минимум два последовательных опроса.
   563	    """
   564	
   565	    while True:
   566	
   567	        state = get_state()
   568	
   569	        if state.mode != "watcher":
   570	            return False
   571	
   572	        if state.stop_requested:
   573	            finish_stop()
   574	            return False
   575	
   576	        watcher_path = (
   577	            state.watcher_path
   578	            or ""
   579	        ).strip()
   580	
   581	        if not watcher_path:
   582	
   583	            print(
   584	                "[SUPERVISOR] Watcher has no path.",
   585	                flush=True,
   586	            )
   587	
   588	            await asyncio.sleep(
   589	                POLL_INTERVAL
   590	            )
   591	
   592	            continue
   593	
   594	        folder = Path(
   595	            watcher_path
   596	        ).expanduser()
   597	
   598	        baseline = watcher_snapshot(
   599	            folder
   600	        )
   601	
   602	        print(
   603	            "[SUPERVISOR] Watcher active:",
   604	            folder,
   605	            "| existing photos:",
   606	            len(baseline),
   607	            flush=True,
   608	        )
   609	
   610	        # ----------------------------------------------------
   611	        # WAIT FOR EVENT
   612	        # ----------------------------------------------------
   613	
   614	        previous = baseline
   615	
   616	        while True:
   617	
   618	            current_state = get_state()
   619	
   620	            if current_state.mode != "watcher":
   621	                return False
   622	
   623	            if current_state.stop_requested:
   624	                finish_stop()
   625	                return False
   626	
   627	            current = watcher_snapshot(
   628	                folder
   629	            )
   630	
   631	            changed = []
   632	
   633	            for filename, stat in current.items():
   634	
   635	                if filename not in previous:
   636	                    changed.append(
   637	                        (
   638	                            filename,
   639	                            stat,
   640	                        )
   641	                    )
   642	
   643	                elif previous[filename] != stat:
   644	                    changed.append(
   645	                        (
   646	                            filename,
   647	                            stat,
   648	                        )
   649	                    )
   650	
   651	            if changed:
   652	
   653	                # --------------------------------------------
   654	                # FILE STABILITY CHECK
   655	                # --------------------------------------------
   656	
   657	                print(
   658	                    "[SUPERVISOR] Watcher detected:",
   659	                    len(changed),
   660	                    "photo(s)",
   661	                    flush=True,
   662	                )
   663	
   664	                await asyncio.sleep(
   665	                    POLL_INTERVAL * 2
   666	                )
   667	
   668	                stable_state = get_state()
   669	
   670	                if stable_state.mode != "watcher":
   671	                    return False
   672	
   673	                if stable_state.stop_requested:
   674	                    finish_stop()
   675	                    return False
   676	
   677	                stable = watcher_snapshot(
   678	                    folder
   679	                )
   680	
   681	                stable_changed = []
   682	
   683	                for filename, stat in changed:
   684	
   685	                    if stable.get(filename) == stat:
   686	                        stable_changed.append(
   687	                            filename
   688	                        )
   689	
   690	                if stable_changed:
   691	
   692	                    print(
   693	                        "[SUPERVISOR] Watcher event confirmed:",
   694	                        len(stable_changed),
   695	                        "stable photo(s)",
   696	                        flush=True,
   697	                    )
   698	
   699	                    try:
   700	                        start_watcher()
   701	
   702	                    except Exception as exc:
   703	
   704	                        print(
   705	                            "[SUPERVISOR] WATCHER START ERROR:",
   706	                            repr(exc),
   707	                            flush=True,
   708	                        )
   709	
   710	                        await asyncio.sleep(
   711	                            POLL_INTERVAL
   712	                        )
   713	
   714	                        continue
   715	
   716	                    return True
   717	
   718	            previous = current
   719	
   720	            await asyncio.sleep(
   721	                POLL_INTERVAL
   722	            )
   723	
   724	
   725	# ============================================================
   726	# MAIN LOOP
   727	# ============================================================
   728	
   729	async def supervisor_loop():
   730	
   731	    print("=" * 70)
   732	    print("ALBION PIPELINE SUPERVISOR")
   733	    print("=" * 70)
   734	
   735	    if not UV.exists():
================ PREVIEW SCRIPT =================
     1	#!/usr/bin/env python3
     2	
     3	import argparse
     4	from pathlib import Path
     5	from PIL import Image
     6	
     7	
     8	IMAGE_EXTENSIONS = {
     9	    ".jpg",
    10	    ".jpeg",
    11	    ".png",
    12	    ".webp",
    13	}
    14	
    15	MAX_SIZE = 1200
    16	QUALITY = 82
    17	
    18	
    19	def create_preview(source: Path, destination: Path):
    20	    destination.parent.mkdir(
    21	        parents=True,
    22	        exist_ok=True,
    23	    )
    24	
    25	    if destination.exists():
    26	        return "skip"
    27	
    28	    with Image.open(source) as image:
    29	        image = image.convert("RGB")
    30	        image.thumbnail(
    31	            (MAX_SIZE, MAX_SIZE),
    32	            Image.Resampling.LANCZOS,
    33	        )
    34	
    35	        image.save(
    36	            destination,
    37	            "JPEG",
    38	            quality=QUALITY,
    39	            optimize=True,
    40	        )
    41	
    42	    return "created"
    43	
    44	
    45	def main():
    46	
    47	    parser = argparse.ArgumentParser(
    48	        description="Create web previews for processed photos"
    49	    )
    50	
    51	    parser.add_argument(
    52	        "--input",
    53	        required=True,
    54	        help="Hybrid output directory",
    55	    )
    56	
    57	    parser.add_argument(
    58	        "--output",
    59	        required=True,
    60	        help="Preview output directory",
    61	    )
    62	
    63	    args = parser.parse_args()
    64	
    65	    input_dir = Path(args.input).expanduser().resolve()
    66	    output_dir = Path(args.output).expanduser().resolve()
    67	
    68	    if not input_dir.exists():
    69	        raise SystemExit(
    70	            f"ERROR: input directory does not exist: {input_dir}"
    71	        )
    72	
    73	    files = sorted(
    74	        [
    75	            p
    76	            for p in input_dir.rglob("*")
    77	            if p.is_file()
    78	            and p.suffix.lower() in IMAGE_EXTENSIONS
    79	        ],
    80	        key=lambda p: str(p).lower(),
    81	    )
    82	
    83	    print("=" * 80)
    84	    print("PHOTO PREVIEW WORKER V01")
    85	    print("=" * 80)
    86	    print("INPUT :", input_dir)
    87	    print("OUTPUT:", output_dir)
    88	    print("FILES :", len(files))
    89	    print("MAX   :", MAX_SIZE)
    90	    print("QUALITY:", QUALITY)
    91	    print()
    92	
    93	    created = 0
    94	    skipped = 0
    95	    errors = 0
    96	
    97	    for index, source in enumerate(files, 1):
    98	
    99	        relative = source.relative_to(input_dir)
   100	
   101	        destination = (
   102	            output_dir
   103	            / relative.parent
   104	            / f"{source.stem}.jpg"
   105	        )
   106	
   107	        try:
   108	
   109	            result = create_preview(
   110	                source,
   111	                destination,
   112	            )
   113	
   114	            if result == "created":
   115	                created += 1
   116	            else:
   117	                skipped += 1
   118	
   119	            if index % 25 == 0 or index == len(files):
   120	                print(
   121	                    f"[{index}/{len(files)}] "
   122	                    f"created={created} "
   123	                    f"skipped={skipped} "
   124	                    f"errors={errors}",
   125	                    flush=True,
   126	                )
   127	
   128	        except Exception as error:
   129	
   130	            errors += 1
   131	
   132	            print(
   133	                f"ERROR: {source}: {error}",
   134	                flush=True,
   135	            )
   136	
   137	    print()
   138	    print("=" * 80)
   139	    print("PREVIEW FINISHED")
   140	    print("=" * 80)
   141	    print("Created:", created)
   142	    print("Skipped:", skipped)
   143	    print("Errors :", errors)
   144	    print("Output :", output_dir)
   145	    print()
   146	
   147	
   148	if __name__ == "__main__":
   149	    main()
================ PREVIEW CALLS =================
app/web/components/photos.py:72:def get_preview_path(photo_path):
app/web/components/photos.py:85:    preview_path = preview_root / relative
app/web/components/photos.py:87:    if preview_path.exists():
app/web/components/photos.py:88:        return preview_path
app/web/components/photos.py:1594:                                    preview_path = (
app/web/components/photos.py:1595:                                        get_preview_path(
app/web/components/photos.py:1601:                                        preview_path
app/web/components/photos.py:1602:                                        if preview_path
app/web/photo_db.py:26:            preview_path,
scripts/create_previews_v01.py:19:def create_preview(source: Path, destination: Path):
scripts/create_previews_v01.py:109:            result = create_preview(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:19:20

Да. Теперь картина уже достаточно чёткая - и **сейчас pipeline работает не так, как ты описал**.

### Что мы нашли

Сейчас фактически есть такая цепочка:

```text
Watcher
   ↓
start_watcher()
   ↓
PHOTO INGEST
   ↓
создаёт photo_id + initial_id
   ↓
dino_status = pending
qwen_status = pending
preview_status = pending
   ↓
DINO
   ↓
dino_fingerprint
   ↓
Hybrid
   ↓
address / hybrid_final_id
   ↓
фото становится видимым в grid
```

Причём `photo_ingest.py` прямо говорит:

> `На этом этапе ... создание превью` - НЕТ.

То есть **preview сейчас вообще не создаётся при ingest**.

А `scripts/create_previews_v01.py` - это отдельный старый batch-скрипт, который берёт уже обработанные фото из Hybrid output:

```text
--input = Hybrid output directory
--output = Preview output directory
```

И мы видим главное:

```text
PREVIEW CALLS
app/web/components/photos.py
scripts/create_previews_v01.py
```

То есть **watcher этот preview worker вообще не запускает**.

---

### При этом твоя новая логика правильная

Я бы зафиксировал архитектуру именно так:

```text
             НОВОЕ ФОТО
                  │
                  ▼
             WATCHER
                  │
                  ▼
             PHOTO INGEST
                  │
          ┌───────┴────────┐
          ▼                ▼
     photo_id          PREVIEW
          │                │
          │                ▼
          │          preview_path
          │          preview_status
          │
          ▼
       DINO QUEUE
          │
          ▼
     DINO fingerprint
          │
          ▼
        HYBRID
          │
          ▼
    address / client
          │
          ▼
       GRID FILTER
          │
          ▼
      ПОКАЗ ФОТО
```

То есть:

**photo_id и preview должны появляться практически одновременно с регистрацией фотографии.**

Но это **не означает, что фото сразу показывается в гриде**.

Grid должен использовать примерно такую логику:

```text
photo существует?
       ↓
есть preview?
       ↓
есть DINO fingerprint?
       ↓
есть определённый адрес?
       ↓
адрес проходит текущий фильтр?
       ↓
ПОКАЗАТЬ
```

Таким образом, preview можно подготовить заранее, а DINO/Hybrid остаются **гейтами видимости**.

---

### И ещё важный момент

Watcher сам по себе **не является обработчиком фотографии**.

Мы нашли его реальную функцию:

```text
supervisor.py
    watcher_snapshot()
    ↓
    обнаружение нового/изменённого файла
    ↓
    проверка стабильности файла
    ↓
    start_watcher()
```

То есть сейчас нам надо посмотреть **что именно делает `start_watcher()`**, а затем куда он передаёт управление.

Это ключевое место.

Потому что, судя по найденному коду, наиболее логичная точка изменения - **не трогать сам Watcher**, а встроить создание preview в уже существующий ingest/pipeline после обнаружения стабильного файла.

---

### Что я предлагаю сейчас

**Пока ничего не менять.**

Надо сначала посмотреть ровно две вещи:

1. `start_watcher()` в `app/pipeline/controller.py`
2. участок `supervisor.py`, где запускается полный pipeline после `start_watcher()`

Особенно нам нужны строки примерно:

```text
controller.py 210-270
supervisor.py 180-340
supervisor.py 729-820
```

После этого мы точно увидим:

```text
WATCHER → ??? → INGEST → DINO → QWEN/Hybrid
```

и определим **одно конкретное место**, куда поставить:

```text
create preview
```

Причём я бы не стал сейчас использовать старый `create_previews_v01.py` как отдельный этап после Hybrid. Его логика явно рассчитана на **Hybrid output**, а нам нужен новый ранний этап: **source photo → preview**.

То есть архитектурно правильнее будет сделать preview частью **первичного ingest**, а не частью Hybrid.

---

### 👤 **User** — 2026-08-20 23:20:37

хотя есть ли смысл переделывать время возникновения превью?

---

### 🤖 **Assistant** — 2026-08-20 23:20:38

Да — **смысл есть, но не обязательно прямо сейчас переделывать**. В твоей архитектуре я бы разделил два вопроса: **когда создаётся preview** и **когда фото становится видимым в grid**.

Сейчас у тебя:

```text
фото попало в Watcher
        ↓
photo_id
        ↓
DINO
        ↓
Hybrid / адрес
        ↓
grid
        ↓
preview уже нужен для отображения
```

А концептуально можно сделать:

```text
фото попало в Watcher
        ↓
photo_id + preview
        ↓
DINO
        ↓
Hybrid / адрес
        ↓
grid
```

### Что это даст

**Плюсы раннего preview:**

- preview готово заранее;
- когда DINO закончил работу, grid может показать фото практически мгновенно;
- preview не зависит от Hybrid output;
- не нужно потом отдельно генерировать превью для уже отсортированных фотографий;
- архитектура становится логичнее: preview относится к **самой фотографии**, а не к результату распознавания.

Особенно это хорошо соответствует твоей идее:

> `photo_id` — постоянная сущность фотографии, независимо от DINO/Qwen/адреса.

Preview логически относится к той же сущности.

### Но есть важный нюанс

**Раннее создание preview не ускорит появление фото в grid**, если grid сейчас специально требует:

```text
dino_fingerprint
+
address_directory
```

И это, на мой взгляд, правильно.

То есть я бы **не менял условие отображения**.

Получится:

```text
             PHOTO
               │
       ┌───────┴────────┐
       ▼                ▼
   photo_id           preview
       │
       ▼
      DINO
       │
       ▼
 dino_fingerprint
       │
       ▼
    HYBRID
       │
       ▼
    ADDRESS
       │
       ▼
  FILTER ADDRESS
       │
       ▼
      GRID
```

### Поэтому мой вывод

**Да, перенос preview на ранний этап архитектурно правильнее.**

Но это **не срочная оптимизация**. Если нынешний preview уже нормально создаётся и производительность устраивает, я бы сначала не ломал рабочую часть.

Я бы сделал это следующим небольшим изменением:

**при `PHOTO INGEST` одновременно с `photo_id` создавать preview из `source_path`, записывать его `preview_path` и переводить `preview_status` в `done`.**

При этом:

- DINO не ждёт preview;
- Qwen не ждёт preview;
- Hybrid не ждёт preview;
- grid всё равно ждёт DINO + адрес;
- старый `create_previews_v01.py` после Hybrid постепенно становится ненужным.

И это, на мой взгляд, **самая чистая модель для Альбиона**.

Но прежде чем менять — я бы посмотрел `start_watcher()` и реальную цепочку после него. Возможно, у нас уже есть подходящее место для ingest, и тогда изменение будет буквально небольшим.

---

### 👤 **User** — 2026-08-20 23:21:53

давай

---

### 🤖 **Assistant** — 2026-08-20 23:21:54

Да. Тогда следующий шаг — **не менять код**, а точно посмотреть, что делает `start_watcher()` после события Watcher и где именно запускается `photo_ingest.py`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ START_WATCHER =================" && \
nl -ba app/pipeline/controller.py | sed -n '210,315p' && \
echo && \
echo "================ SUPERVISOR PIPELINE =================" && \
nl -ba app/pipeline/supervisor.py | sed -n '150,380p' && \
echo && \
echo "================ ALL PHOTO_INGEST CALLS =================" && \
grep -RniE \
'photo_ingest|PHOTO INGEST|ingest\(|scripts/photo_ingest' \
app scripts \
--include="*.py" \
--include="*.sh" | \
grep -vE 'benchmark|__pycache__'
```

**Особенно интересуют три вещи:**

1. кто запускает `photo_ingest.py`;
2. что происходит сразу после ingest;
3. где сейчас запускается DINO и Hybrid.

После этого уже сможем точно поставить:

```text
Watcher
  ↓
photo_ingest
  ↓
photo_id + preview
  ↓
DINO queue
  ↓
Hybrid
  ↓
address
  ↓
GRID
```

и сделать это **без изменения самой логики распознавания**.

---

