## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-20 23:22:14

grep -RniE \
'photo_ingest|PHOTO INGEST|ingest\(|scripts/photo_ingest' \
app scripts \
--include="*.py" \
--include="*.sh" | \
grep -vE 'benchmark|__pycache__'
================ START_WATCHER =================
   210	                    started_at = CURRENT_TIMESTAMP,
   211	                    stopped_at = NULL,
   212	                    updated_at = CURRENT_TIMESTAMP
   213	                WHERE id = 1
   214	                """
   215	            )
   216	
   217	        conn.commit()
   218	
   219	    state.running = True
   220	    state.stop_requested = False
   221	
   222	    return state
   223	
   224	
   225	def start_watcher():
   226	    state = get_state()
   227	
   228	    if state.mode != MODE_WATCHER:
   229	        raise RuntimeError(
   230	            "Watcher start requested while mode is not watcher"
   231	        )
   232	
   233	    if state.running:
   234	        return state
   235	
   236	    with get_connection() as conn:
   237	        with conn.cursor() as cur:
   238	            cur.execute(
   239	                """
   240	                UPDATE pipeline_control
   241	                SET
   242	                    running = TRUE,
   243	                    stop_requested = FALSE,
   244	                    started_at = CURRENT_TIMESTAMP,
   245	                    stopped_at = NULL,
   246	                    updated_at = CURRENT_TIMESTAMP
   247	                WHERE id = 1
   248	                """
   249	            )
   250	
   251	        conn.commit()
   252	
   253	    state.running = True
   254	    state.stop_requested = False
   255	
   256	    return state
   257	
   258	
   259	def request_stop():
   260	    with get_connection() as conn:
   261	        with conn.cursor() as cur:
   262	            cur.execute(
   263	                """
   264	                UPDATE pipeline_control
   265	                SET
   266	                    stop_requested = TRUE,
   267	                    updated_at = CURRENT_TIMESTAMP
   268	                WHERE id = 1
   269	                """
   270	            )
   271	
   272	        conn.commit()
   273	
   274	
   275	def mark_finished():
   276	    """
   277	    Завершает один запуск pipeline.
   278	
   279	    ВАЖНО:
   280	
   281	    Режим НЕ меняется.
   282	
   283	    Поэтому:
   284	        manual    -> manual
   285	        automatic -> automatic
   286	        watcher   -> watcher
   287	
   288	    Сбрасывается только состояние текущего запуска.
   289	    Это позволяет automatic/watcher продолжить работу
   290	    после завершения очередной партии.
   291	    """
   292	
   293	    with get_connection() as conn:
   294	        with conn.cursor() as cur:
   295	            cur.execute(
   296	                """
   297	                UPDATE pipeline_control
   298	                SET
   299	                    running = FALSE,
   300	                    stop_requested = FALSE,
   301	                    stopped_at = CURRENT_TIMESTAMP,
   302	                    updated_at = CURRENT_TIMESTAMP
   303	                WHERE id = 1
   304	                """
   305	            )
   306	
   307	        conn.commit()
   308	
   309	    return get_state()
   310	
   311	
   312	def finish_stop():
   313	    state = build_manual_mode()
   314	
   315	    with get_connection() as conn:

================ SUPERVISOR PIPELINE =================
   150	        flush=True,
   151	    )
   152	
   153	    try:
   154	        process.terminate()
   155	
   156	    except ProcessLookupError:
   157	        return
   158	
   159	    try:
   160	        await asyncio.wait_for(
   161	            process.wait(),
   162	            timeout=10,
   163	        )
   164	
   165	    except asyncio.TimeoutError:
   166	
   167	        print(
   168	            f"[SUPERVISOR] {prefix} did not stop, "
   169	            f"sending kill",
   170	            flush=True,
   171	        )
   172	
   173	        try:
   174	            process.kill()
   175	        except ProcessLookupError:
   176	            pass
   177	
   178	        await process.wait()
   179	
   180	
   181	# ============================================================
   182	# PIPELINE RUN
   183	# ============================================================
   184	
   185	async def run_pipeline():
   186	    """
   187	    Один полный запуск DINO + Qwen.
   188	
   189	    Workers остаются независимыми:
   190	        DINO -> PostgreSQL dino_status
   191	        Qwen -> PostgreSQL qwen_status
   192	
   193	    Supervisor только управляет их жизненным циклом.
   194	    """
   195	
   196	    dino_process = None
   197	    qwen_process = None
   198	
   199	    dino_output = None
   200	    qwen_output = None
   201	
   202	    try:
   203	
   204	        # ----------------------------------------------------
   205	        # START
   206	        # ----------------------------------------------------
   207	
   208	        print(
   209	            "=" * 70,
   210	            flush=True,
   211	        )
   212	
   213	        print(
   214	            "[SUPERVISOR] PIPELINE START",
   215	            flush=True,
   216	        )
   217	
   218	        print(
   219	            "=" * 70,
   220	            flush=True,
   221	        )
   222	
   223	        dino_process, dino_output = (
   224	            await start_worker(
   225	                DINO_WORKER,
   226	                "DINO",
   227	            )
   228	        )
   229	
   230	        await asyncio.sleep(0.2)
   231	
   232	        qwen_process, qwen_output = (
   233	            await start_worker(
   234	                QWEN_WORKER,
   235	                "QWEN",
   236	            )
   237	        )
   238	
   239	        # ----------------------------------------------------
   240	        # WAIT
   241	        # ----------------------------------------------------
   242	
   243	        while True:
   244	
   245	            dino_running = process_running(
   246	                dino_process
   247	            )
   248	
   249	            qwen_running = process_running(
   250	                qwen_process
   251	            )
   252	
   253	            if not dino_running and not qwen_running:
   254	                break
   255	
   256	            if is_stop_requested():
   257	
   258	                print(
   259	                    "[SUPERVISOR] STOP REQUESTED",
   260	                    flush=True,
   261	                )
   262	
   263	                await stop_process(
   264	                    dino_process,
   265	                    "DINO",
   266	                )
   267	
   268	                await stop_process(
   269	                    qwen_process,
   270	                    "QWEN",
   271	                )
   272	
   273	                break
   274	
   275	            await asyncio.sleep(
   276	                POLL_INTERVAL
   277	            )
   278	
   279	        # ----------------------------------------------------
   280	        # EXIT CODES
   281	        # ----------------------------------------------------
   282	
   283	        dino_code = (
   284	            dino_process.returncode
   285	            if dino_process is not None
   286	            else None
   287	        )
   288	
   289	        qwen_code = (
   290	            qwen_process.returncode
   291	            if qwen_process is not None
   292	            else None
   293	        )
   294	
   295	        print(
   296	            "[SUPERVISOR] DINO exit:",
   297	            dino_code,
   298	            flush=True,
   299	        )
   300	
   301	        print(
   302	            "[SUPERVISOR] QWEN exit:",
   303	            qwen_code,
   304	            flush=True,
   305	        )
   306	
   307	        return (
   308	            dino_code,
   309	            qwen_code,
   310	        )
   311	
   312	    finally:
   313	
   314	        # ----------------------------------------------------
   315	        # SAFETY CLEANUP
   316	        # ----------------------------------------------------
   317	
   318	        await stop_process(
   319	            dino_process,
   320	            "DINO",
   321	        )
   322	
   323	        await stop_process(
   324	            qwen_process,
   325	            "QWEN",
   326	        )
   327	
   328	        for task in (
   329	            dino_output,
   330	            qwen_output,
   331	        ):
   332	
   333	            if task is not None:
   334	                await asyncio.gather(
   335	                    task,
   336	                    return_exceptions=True,
   337	                )
   338	
   339	        print(
   340	            "[SUPERVISOR] PIPELINE FINISHED",
   341	            flush=True,
   342	        )
   343	
   344	
   345	# ============================================================
   346	# AUTOMATIC SCHEDULER
   347	# ============================================================
   348	
   349	def seconds_until(
   350	    target_time,
   351	):
   352	    now = datetime.now()
   353	
   354	    target = datetime.combine(
   355	        now.date(),
   356	        target_time,
   357	    )
   358	
   359	    if target <= now:
   360	        target += timedelta(
   361	            days=1
   362	        )
   363	
   364	    return (
   365	        target - now
   366	    ).total_seconds()
   367	
   368	
   369	async def wait_automatic():
   370	    """
   371	    Ждёт заданного времени.
   372	
   373	    Важно:
   374	    automatic mode остаётся automatic после завершения
   375	    одного запуска.
   376	    """
   377	
   378	    while True:
   379	
   380	        state = get_state()

================ ALL PHOTO_INGEST CALLS =================
scripts/photo_ingest.py:287:def ingest(input_dir):
scripts/photo_ingest.py:314:    print("PHOTO INGEST")
scripts/photo_ingest.py:502:    ingest(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:22:17

Вот теперь видно важную вещь: **сейчас `photo_ingest.py` вообще не вызывается Watcher'ом.**

То есть текущая цепочка фактически разорвана.

### Что сейчас происходит

Watcher в `supervisor.py` делает только:

```text
папка Watcher
   ↓
обнаружил новое/изменённое фото
   ↓
проверил стабильность
   ↓
start_watcher()
   ↓
state.running = True
   ↓
run_pipeline()
   ↓
DINO + Qwen
```

А `start_watcher()` **не запускает ingest**. Он только меняет состояние `pipeline_control`:

```text
running = TRUE
stop_requested = FALSE
```

И поиск подтверждает это однозначно:

```text
photo_ingest.py
    └── ingest() вызывается только из собственного main()
```

Никакого:

```text
subprocess ... photo_ingest.py
```

или импорта `photo_ingest` в `app/` нет.

---

### И ещё важнее — твоя модель данных уже подготовлена

В `photo_ingest.py` при регистрации создаётся:

```text
photo_id
initial_id
source_path
path
filename
original_filename

status = pending
dino_status = pending
qwen_status = pending
sort_status = pending
preview_status = pending
```

То есть архитектурно **место для раннего preview уже предусмотрено**.

Но прямо сейчас ingest сам говорит:

> создание превью — НЕ происходит.

А `create_previews_v01.py` вообще рассчитан на **Hybrid output directory**:

```text
Hybrid output
    ↓
create_previews_v01.py
    ↓
preview output
```

То есть это старый пост-Hybrid механизм.

---

## Поэтому я бы сейчас не переделывал всё сразу

Я бы сделал именно то, о чём ты говорил:

```text
WATCHER
   ↓
PHOTO INGEST
   ↓
photo_id + preview
   ↓
DINO pending
   ↓
DINO
   ↓
Hybrid
   ↓
address_id / final address
   ↓
GRID
```

Причём **preview не должен зависеть ни от DINO, ни от Hybrid, ни от адреса**.

И тогда появляется очень правильное разделение:

### До DINO

Фото уже существует как объект базы:

```text
photo_id
preview
source_path
filename
initial_id
```

### После DINO

Появляется:

```text
dino_fingerprint
dino_score
dino_status
```

### После Hybrid

Появляется окончательная идентификация:

```text
hybrid_final_id
address_id
sort_status
```

### Grid

А вот здесь фильтр решает, показывать фото или нет.

То есть твоя исходная идея:

> **photo_id + preview создаются одновременно, но фото появляется в гриде только после DINO/Hybrid и только если проходит фильтр адресов**

— архитектурно выглядит гораздо правильнее нынешней.

---

Но перед изменением я хочу увидеть **самый главный кусок `supervisor_loop()`**, потому что именно там окончательно определяется последовательность `Watcher → run_pipeline`.

Дай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SUPERVISOR LOOP =================" && \
nl -ba app/pipeline/supervisor.py | sed -n '725,850p' && \
echo && \
echo "================ SUPERVISOR TOP =================" && \
nl -ba app/pipeline/supervisor.py | sed -n '1,150p'
```

После этого я смогу сказать **куда именно вставить ingest + preview**, не ломая существующий DINO/Hybrid.

---

### 👤 **User** — 2026-08-20 23:23:29

может оставим как естьЮ, раннее создание превью ничем не поможет - для превью все равно требуется завершенный процесс дино и гибрид, после которого и можно создавать превью

---

### 🤖 **Assistant** — 2026-08-20 23:23:30

Да. **Я бы оставил как есть.** В твоей текущей архитектуре раннее создание превью действительно не даёт существенного выигрыша.

Логика сейчас получается нормальная:

```text
Новое фото
   ↓
INGEST
   ↓
DINO
   ↓
Qwen / Hybrid
   ↓
определён адрес / итоговая папка
   ↓
создание preview
   ↓
GRID
```

И это даже имеет несколько плюсов:

- превью создаётся только для **обработанного результата**;
- сразу известно, **в какую структуру каталогов** положить preview;
- не создаются превью для фотографий, которые могут не пройти обработку;
- не возникает проблемы с последующим перемещением preview при сортировке;
- `create_previews_v01.py` уже умеет сохранять структуру `relative.parent`, то есть хорошо подходит к итоговой структуре Hybrid;
- `preview_status = pending` уже есть в БД — значит, эту часть можно спокойно довести до автоматической обработки позже.

И главное: **раннее preview не ускоряет DINO/Hybrid и не делает сам Grid доступным**, если по требованиям фото нельзя показывать до завершения обработки.

Так что сейчас **не трогаем время создания preview**.

Я бы зафиксировал архитектуру именно так:

> **Preview — завершающий этап обработки фотографии после DINO + Hybrid.**

А сейчас лучше заниматься тем, что действительно влияет на UX и архитектуру: **чтобы после завершения обработки preview автоматически создавался и `preview_status` корректно менялся в БД**, без отдельного ручного запуска `create_previews_v01.py`.

---

### 👤 **User** — 2026-08-20 23:24:01

далее

---

### 🤖 **Assistant** — 2026-08-20 23:24:02

Да, идём дальше.

Следующий логичный шаг — **не менять сам момент создания preview**, а проверить, **кто сейчас должен запускать `create_previews_v01.py` после DINO + Hybrid**.

Сейчас по твоему выводу видно:

```text
app/web/components/photos.py
    └── только поиск preview

app/web/photo_db.py
    └── preview_path

scripts/create_previews_v01.py
    └── самостоятельный CLI

supervisor.py
    └── DINO + Qwen
    └── preview пока не запускает
```

То есть потенциально проблема не во времени создания, а в **автоматическом вызове**.

Дай теперь поиск по Hybrid/сортировке и завершению pipeline:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID / SORT CALLS ================" && \
grep -RniE \
'hybrid_final|sort_status|sort_test|sort_|hybrid|address_id|final_id' \
app/pipeline app scripts \
--include="*.py" \
--include="*.sh" | \
grep -vE 'benchmark|__pycache__' | head -n 300 && \

echo "================ PIPELINE END ================" && \
nl -ba app/pipeline/supervisor.py | sed -n '725,900p'
```

По этому выводу определим **точку, где обработка фотографии считается полностью законченной**. Именно туда, скорее всего, и нужно будет поставить автоматический preview worker — если он вообще сейчас не подключён.

---

### 👤 **User** — 2026-08-20 23:24:25

nl -ba app/pipeline/supervisor.py | sed -n '725,900p'
================ HYBRID / SORT CALLS ================
app/web/components/technical_modules/photo_processing.py:884:                    "DINO v33 / Hybrid v12"
app/web/components/technical_modules/data.py:327:        # HYBRID
app/web/components/technical_modules/data.py:337:                    "Hybrid v12"
app/web/components/technical_modules/qwen.py:180:def _find_latest_hybrid():
app/web/components/technical_modules/qwen.py:350:            result_dir = _find_latest_hybrid()
app/web/components/technical_modules/qwen.py:355:                    "[QWEN MANUAL] HYBRID RUN NOT FOUND",
app/web/components/technical_modules/qwen.py:360:                    "Не найден ни один запуск Hybrid.",
app/web/components/technical_modules/qwen.py:387:                    f"В последнем Hybrid нет фотографий: {result_dir}",
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/web/photo_db.py:50:            hybrid_changed,
app/web/photo_db.py:51:            hybrid_old_score,
app/web/photo_db.py:52:            hybrid_score,
app/web/photo_db.py:53:            hybrid_margin,
app/web/photo_db.py:54:            hybrid_neighbors,
app/web/photo_db.py:57:            sort_status
app/web/directory_db.py:36:        ORDER BY sort_order, id
app/web/directory_db.py:54:    Возвращает address_id для fingerprint.
app/web/directory_db.py:62:        SELECT address_id
app/web/directory_db.py:85:    address_id = get_address_by_fingerprint(
app/web/directory_db.py:89:    if address_id is None:
app/web/directory_db.py:94:    data = directory.get(address_id)
app/web/directory_db.py:100:        "id": address_id,
app/web/directory_db.py:122:        ORDER BY sort_order, LOWER(name)
app/web_v01_backup_20260816_142053/state.py:8:        self.sort_mode = "date_desc"
app/workers/qwen_worker.py:164:    address_id здесь НЕ используется.
app/workers/dino_worker.py:140:        address_id = адрес, определённый DINO.
app/workers/dino_worker.py:145:    address_id = result.get("best_id")
app/workers/dino_worker.py:155:                address_id = %s,
app/workers/dino_worker.py:169:                address_id,
app/workers/dino_worker.py:173:                address_id,
app/workers/dino_worker.py:372:                address_id = result.get(
app/workers/dino_worker.py:379:                    f" -> address_id={address_id}"
scripts/smart_client_normalizer.py:39:        ORDER BY sort_order, name
scripts/create_previews_v01.py:54:        help="Hybrid output directory",
scripts/sort_neighbor_v34.py:133:        final_id = original
scripts/sort_neighbor_v34.py:223:                final_id = second
scripts/sort_neighbor_v34.py:254:            OUTPUT_DIR / final_id
scripts/sort_neighbor_v34.py:271:        counters[final_id] += 1
scripts/sort_neighbor_v34.py:283:            "final_decision": final_id,
scripts/photo_ingest.py:249:                sort_status,
scripts/run_daily_hybrid_v12.sh:15:echo "SCENE FINGERPRINT — DAILY HYBRID V12"
scripts/run_daily_hybrid_v12.sh:42:/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
scripts/run_hybrid_v12.py:23:# HYBRID V12 — FROZEN CONTROL LOGIC
scripts/run_hybrid_v12.py:48:        print(f"[Hybrid] WARNING: sub directory not found: {SUB_DIR}")
scripts/run_hybrid_v12.py:182:    top1..top5 format required by frozen Hybrid v12.
scripts/run_hybrid_v12.py:207:def hybrid_v12(rows, embedder, subs):
scripts/run_hybrid_v12.py:209:    Exact production adaptation of the frozen Hybrid v12 logic.
scripts/run_hybrid_v12.py:363:        hybrid_changed = best != old
scripts/run_hybrid_v12.py:370:        result["hybrid_changed"] = hybrid_changed
scripts/run_hybrid_v12.py:372:        result["hybrid_old_score"] = old_score
scripts/run_hybrid_v12.py:373:        result["hybrid_score"] = new_score
scripts/run_hybrid_v12.py:375:        result["hybrid_margin"] = margin
scripts/run_hybrid_v12.py:376:        result["hybrid_neighbors"] = dict(neighbors)
scripts/run_hybrid_v12.py:401:def sort_results(rows, output_dir):
scripts/run_hybrid_v12.py:403:    Copy photos according to FINAL Hybrid best_id.
scripts/run_hybrid_v12.py:460:                "hybrid_changed": item.get(
scripts/run_hybrid_v12.py:461:                    "hybrid_changed"
scripts/run_hybrid_v12.py:478:                "hybrid_old_score": item.get(
scripts/run_hybrid_v12.py:479:                    "hybrid_old_score"
scripts/run_hybrid_v12.py:481:                "hybrid_score": item.get(
scripts/run_hybrid_v12.py:482:                    "hybrid_score"
scripts/run_hybrid_v12.py:503:        description="Production runner for frozen Hybrid v12"
scripts/run_hybrid_v12.py:550:    print("SCENE FINGERPRINT — HYBRID V12 RUNNER")
scripts/run_hybrid_v12.py:558:    print("  HYBRID      : v12")
scripts/run_hybrid_v12.py:574:    # 2. Load Hybrid subfingerprints
scripts/run_hybrid_v12.py:579:    print("LOADING HYBRID SUBFINGERPRINTS")
scripts/run_hybrid_v12.py:587:    # 3. Hybrid v12
scripts/run_hybrid_v12.py:592:    print("HYBRID V12")
scripts/run_hybrid_v12.py:603:    hybrid_rows, changed, sub_count = hybrid_v12(
scripts/run_hybrid_v12.py:610:    print("Checked:", len(hybrid_rows))
scripts/run_hybrid_v12.py:612:    print("Hybrid changes:", len(changed))
scripts/run_hybrid_v12.py:637:    sorted_rows, counters = sort_results(
scripts/run_hybrid_v12.py:638:        hybrid_rows,
scripts/run_hybrid_v12.py:655:    hybrid_json = (
scripts/run_hybrid_v12.py:656:        output_dir / "hybrid_v12.json"
scripts/run_hybrid_v12.py:676:    hybrid_json.write_text(
scripts/run_hybrid_v12.py:678:            hybrid_rows,
scripts/run_hybrid_v12.py:700:        "total_images": len(hybrid_rows),
scripts/run_hybrid_v12.py:704:        "hybrid_border_cases": sub_count,
scripts/run_hybrid_v12.py:705:        "hybrid_changed": len(changed),
scripts/run_hybrid_v12.py:709:            "rerank": "Hybrid v12",
scripts/run_hybrid_v12.py:731:    print("Images:", len(hybrid_rows))
scripts/run_hybrid_v12.py:732:    print("Hybrid changes:", len(changed))
scripts/sort_baseline.py:128:        "elapsed_sort_seconds": elapsed,
scripts/export_visual_compare.py:40:def export_hybrid():
scripts/export_visual_compare.py:44:            "data/output/full_recognize_hybrid_v12_test.json",
scripts/export_visual_compare.py:58:            "hybrid_v12" /
scripts/export_visual_compare.py:73:export_hybrid()
scripts/sort_neighbor_v35.py:78:        final_id = current
scripts/sort_neighbor_v35.py:164:                final_id = second
scripts/sort_neighbor_v35.py:199:        counters[final_id] += 1
scripts/sort_neighbor_v35.py:205:        if final_id != current:
scripts/sort_neighbor_v35.py:210:                "to": final_id,
scripts/sort_neighbor_v35.py:225:            "final": final_id,
================ PIPELINE END ================
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
   736	        raise FileNotFoundError(
   737	            f"uv not found: {UV}"
   738	        )
   739	
   740	    if not DINO_WORKER.exists():
   741	        raise FileNotFoundError(
   742	            f"DINO worker not found: {DINO_WORKER}"
   743	        )
   744	
   745	    if not QWEN_WORKER.exists():
   746	        raise FileNotFoundError(
   747	            f"Qwen worker not found: {QWEN_WORKER}"
   748	        )
   749	
   750	    while True:
   751	
   752	        state = get_state()
   753	
   754	        print(
   755	            "[SUPERVISOR] state:",
   756	            state.mode,
   757	            "| running:",
   758	            state.running,
   759	            "| stop:",
   760	            state.stop_requested,
   761	            flush=True,
   762	        )
   763	
   764	        # ====================================================
   765	        # MANUAL
   766	        # ====================================================
   767	
   768	        if state.mode == "manual":
   769	
   770	            started = await wait_manual_start()
   771	
   772	            if not started:
   773	                continue
   774	
   775	        # ====================================================
   776	        # AUTOMATIC
   777	        # ====================================================
   778	
   779	        elif state.mode == "automatic":
   780	
   781	            started = await wait_automatic()
   782	
   783	            if not started:
   784	                continue
   785	
   786	        # ====================================================
   787	        # WATCHER
   788	        # ====================================================
   789	
   790	        elif state.mode == "watcher":
   791	
   792	            started = await wait_watcher_event()
   793	
   794	            if not started:
   795	                continue
   796	
   797	        # ====================================================
   798	        # PIPELINE
   799	        # ====================================================
   800	
   801	        try:
   802	
   803	            await run_pipeline()
   804	
   805	        except asyncio.CancelledError:
   806	            raise
   807	
   808	        except Exception as exc:
   809	
   810	            print(
   811	                "[SUPERVISOR] PIPELINE ERROR:",
   812	                repr(exc),
   813	                flush=True,
   814	            )
   815	
   816	        # ====================================================
   817	        # FINISH
   818	        # ====================================================
   819	
   820	        try:
   821	
   822	            state = get_state()
   823	
   824	            if state.stop_requested:
   825	
   826	                print(
   827	                    "[SUPERVISOR] Finalizing STOP",
   828	                    flush=True,
   829	                )
   830	
   831	                finish_stop()
   832	
   833	            else:
   834	
   835	                # ВАЖНО:
   836	                #
   837	                # Automatic mode остаётся automatic.
   838	                # Manual mode после запуска остаётся manual.
   839	                #
   840	                # Только running сбрасывается.
   841	                #
   842	                # Это позволяет automatic mode ждать
   843	                # следующего запуска.
   844	
   845	                from app.pipeline.controller import (
   846	                    mark_finished,
   847	                )
   848	
   849	                mark_finished()
   850	
   851	        except Exception as exc:
   852	
   853	            print(
   854	                "[SUPERVISOR] STATE FINALIZATION ERROR:",
   855	                repr(exc),
   856	                flush=True,
   857	            )
   858	
   859	        await asyncio.sleep(
   860	            POLL_INTERVAL
   861	        )
   862	
   863	
   864	# ============================================================
   865	# SIGNALS
   866	# ============================================================
   867	
   868	def install_signal_handlers(loop):
   869	
   870	    def handle_signal():
   871	
   872	        print(
   873	            "[SUPERVISOR] OS STOP SIGNAL",
   874	            flush=True,
   875	        )
   876	
   877	        try:
   878	            from app.pipeline.controller import (
   879	                request_stop,
   880	            )
   881	
   882	            request_stop()
   883	
   884	        except Exception as exc:
   885	
   886	            print(
   887	                "[SUPERVISOR] Cannot request stop:",
   888	                repr(exc),
   889	                flush=True,
   890	            )
   891	
   892	    for sig in (
   893	        signal.SIGINT,
   894	        signal.SIGTERM,
   895	    ):
   896	
   897	        try:
   898	            loop.add_signal_handler(
   899	                sig,
   900	                handle_signal,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:24:26

Вот теперь картина ясная.

**Preview сейчас действительно не надо встраивать в `supervisor.py` прямо после `run_pipeline()`.** И причина важная: `run_pipeline()` у нас заканчивается после DINO + Qwen, но сам Hybrid v12 в показанном `supervisor.py` вообще не запускается.

Получается:

```text
WATCHER / MANUAL / AUTOMATIC
            ↓
       run_pipeline()
            ↓
      ┌───────┴───────┐
      ↓               ↓
     DINO            QWEN
      ↓               ↓
      └───────┬───────┘
              ↓
        supervisor finish
```

А Hybrid v12 пока живёт отдельно:

```text
scripts/run_hybrid_v12.py
        ↓
    Hybrid v12
        ↓
   sort_results()
        ↓
   output/address/
```

Поэтому **ставить preview в конец `supervisor_loop()` сейчас преждевременно**: тогда preview может появиться раньше фактического Hybrid/sort.

### Что я предлагаю сделать дальше

Не менять пока никакой код.

Нужно найти **как именно сейчас запускается `run_daily_hybrid_v12.sh`** и кто является его вызывающей стороной. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID LAUNCHERS ================" && \
grep -RniE \
'run_daily_hybrid_v12|run_hybrid_v12|hybrid_v12.py' \
app scripts \
--include="*.py" \
--include="*.sh" \
--include="*.service" \
--include="*.timer" \
| grep -vE 'benchmark|__pycache__|export_visual_compare' && \

echo "================ DAILY HYBRID SCRIPT ================" && \
nl -ba scripts/run_daily_hybrid_v12.sh | sed -n '1,180p' && \

echo "================ HYBRID END ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '600,750p'
```

После этого будет видно **настоящую последнюю точку обработки**.

И уже там решим, как лучше сделать:

```text
DINO
 ↓
Qwen
 ↓
Hybrid v12
 ↓
sort
 ↓
preview
 ↓
preview_status = ready
 ↓
GRID
```

То есть **не переделываем архитектуру ради раннего preview**. Нам нужно просто правильно подключить его к уже существующему завершению Hybrid, если автоматического вызова сейчас нет.

---

### 👤 **User** — 2026-08-20 23:25:04

echo "================ HYBRID END ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '600,750p'
================ HYBRID LAUNCHERS ================
scripts/run_daily_hybrid_v12.sh:42:/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
================ DAILY HYBRID SCRIPT ================
     1	#!/usr/bin/env bash
     2	
     3	set -euo pipefail
     4	
     5	PROJECT="$HOME/projects/scene_fingerprint_mvp_v02"
     6	
     7	INPUT="$PROJECT/data/input/daily"
     8	
     9	TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
    10	
    11	OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"
    12	
    13	echo
    14	echo "================================================================================"
    15	echo "SCENE FINGERPRINT — DAILY HYBRID V12"
    16	echo "================================================================================"
    17	echo
    18	echo "INPUT : $INPUT"
    19	echo "OUTPUT: $OUTPUT"
    20	echo
    21	
    22	if [ ! -d "$INPUT" ]; then
    23	    echo "ERROR: input directory does not exist:"
    24	    echo "$INPUT"
    25	    exit 1
    26	fi
    27	
    28	COUNT=$(find "$INPUT" -maxdepth 1 -type f \
    29	    $ -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" $ \
    30	    | wc -l)
    31	
    32	echo "Images: $COUNT"
    33	echo
    34	
    35	if [ "$COUNT" -eq 0 ]; then
    36	    echo "ERROR: no images found in $INPUT"
    37	    exit 1
    38	fi
    39	
    40	mkdir -p "$OUTPUT"
    41	
    42	/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
    43	    --input "$INPUT" \
    44	    --output "$OUTPUT" \
    45	    --first-address 78 \
    46	    --last-address 95
    47	
    48	echo
    49	echo "================================================================================"
    50	echo "DAILY PIPELINE FINISHED"
    51	echo "================================================================================"
    52	echo
    53	echo "Images : $COUNT"
    54	echo "Output : $OUTPUT"
    55	echo
================ HYBRID END ================
   600	
   601	    recognition = adapt_recognizer_rows(recognition)
   602	
   603	    hybrid_rows, changed, sub_count = hybrid_v12(
   604	        recognition,
   605	        embedder,
   606	        subs,
   607	    )
   608	
   609	    print()
   610	    print("Checked:", len(hybrid_rows))
   611	    print("Border cases:", sub_count)
   612	    print("Hybrid changes:", len(changed))
   613	
   614	    for item in changed:
   615	        print()
   616	        print(
   617	            item["file"]
   618	        )
   619	        print(
   620	            item["old"],
   621	            "->",
   622	            item["new"],
   623	        )
   624	        print(
   625	            "margin:",
   626	            item["margin"],
   627	        )
   628	        print(
   629	            "neighbors:",
   630	            item["neighbors"],
   631	        )
   632	
   633	    # --------------------------------------------------------
   634	    # 4. Sort
   635	    # --------------------------------------------------------
   636	
   637	    sorted_rows, counters = sort_results(
   638	        hybrid_rows,
   639	        output_dir,
   640	    )
   641	
   642	    # --------------------------------------------------------
   643	    # 5. Reports
   644	    # --------------------------------------------------------
   645	
   646	    output_dir.mkdir(
   647	        parents=True,
   648	        exist_ok=True,
   649	    )
   650	
   651	    recognition_json = (
   652	        output_dir / "recognition.json"
   653	    )
   654	
   655	    hybrid_json = (
   656	        output_dir / "hybrid_v12.json"
   657	    )
   658	
   659	    report_json = (
   660	        output_dir / "report.json"
   661	    )
   662	
   663	    statistics_json = (
   664	        output_dir / "statistics.json"
   665	    )
   666	
   667	    recognition_json.write_text(
   668	        json.dumps(
   669	            recognition,
   670	            ensure_ascii=False,
   671	            indent=2,
   672	        ),
   673	        encoding="utf-8",
   674	    )
   675	
   676	    hybrid_json.write_text(
   677	        json.dumps(
   678	            hybrid_rows,
   679	            ensure_ascii=False,
   680	            indent=2,
   681	        ),
   682	        encoding="utf-8",
   683	    )
   684	
   685	    report_json.write_text(
   686	        json.dumps(
   687	            sorted_rows,
   688	            ensure_ascii=False,
   689	            indent=2,
   690	        ),
   691	        encoding="utf-8",
   692	    )
   693	
   694	    total_time = (
   695	        time.perf_counter()
   696	        - total_start
   697	    )
   698	
   699	    statistics = {
   700	        "total_images": len(hybrid_rows),
   701	        "sorted_images": len(sorted_rows),
   702	        "recognition_time_seconds": recognition_time,
   703	        "total_wall_time_seconds": total_time,
   704	        "hybrid_border_cases": sub_count,
   705	        "hybrid_changed": len(changed),
   706	        "assigned": dict(counters),
   707	        "control": {
   708	            "recognizer": "DINOv2 v33",
   709	            "rerank": "Hybrid v12",
   710	            "margin_limit": MARGIN_LIMIT,
   711	            "global_weight": GLOBAL_WEIGHT,
   712	            "sub_weight": SUB_WEIGHT,
   713	            "neighbor_weight": NEIGHBOR_WEIGHT,
   714	        },
   715	    }
   716	
   717	    statistics_json.write_text(
   718	        json.dumps(
   719	            statistics,
   720	            ensure_ascii=False,
   721	            indent=2,
   722	        ),
   723	        encoding="utf-8",
   724	    )
   725	
   726	    print()
   727	    print("=" * 80)
   728	    print("DONE")
   729	    print("=" * 80)
   730	    print()
   731	    print("Images:", len(hybrid_rows))
   732	    print("Hybrid changes:", len(changed))
   733	    print(f"Recognition: {recognition_time:.2f} sec")
   734	    print(f"Total:       {total_time:.2f} sec")
   735	    print()
   736	    print("Output:")
   737	    print(output_dir)
   738	
   739	
   740	if __name__ == "__main__":
   741	    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:25:06

Да. Теперь видно главное.

**Hybrid v12 уже сам делает весь финальный этап:** `hybrid_v12()` → `sort_results()` → пишет `report.json/statistics.json` и завершает работу. Но он запускается **отдельным `run_daily_hybrid_v12.sh`**, а `supervisor.py` его вообще не вызывает.

То есть сейчас автоматическая цепочка проекта фактически **разорвана**:

```text
Watcher
   ↓
supervisor
   ↓
DINO + Qwen
   ↓
supervisor FINISH
```

А отдельно:

```text
run_daily_hybrid_v12.sh
   ↓
run_hybrid_v12.py
   ↓
DINO recognition
   ↓
Hybrid v12
   ↓
sort
   ↓
data/output/daily/TIMESTAMP/
```

И здесь есть ещё более важный момент: `run_hybrid_v12.py` на вход получает:

```text
data/input/daily
```

а не результаты DINO/Qwen из PostgreSQL.

### Поэтому я бы сейчас НЕ трогал preview

Ты был прав: раннее создание preview смысла не имеет.

Но следующий вопрос сейчас не preview, а **как должна выглядеть окончательная производственная цепочка**.

У нас есть два разных механизма:

1. **Новый supervisor / DB pipeline**
   - ingest
   - DINO worker
   - Qwen worker
   - PostgreSQL

2. **Старый/отдельный Hybrid v12**
   - свой input
   - своё распознавание
   - Hybrid
   - sort
   - output

И прежде чем что-либо менять, надо понять: **мы сейчас хотим встроить frozen Hybrid v12 в новый supervisor или он пока должен оставаться отдельным?**

Судя по архитектуре, правильный вариант — **встроить Hybrid в общий pipeline после завершения DINO/Qwen**, а не запускать его вторым независимым распознаванием.

Но это уже архитектурное изменение, поэтому сначала посмотрим, **что именно сейчас делают DINO и Qwen workers с PostgreSQL** и есть ли уже заготовка для Hybrid после них.

Следующая команда:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DINO WORKER END ================" && \
nl -ba app/workers/dino_worker.py | sed -n '1,430p' && \

echo "================ QWEN WORKER END ================" && \
nl -ba app/workers/qwen_worker.py | sed -n '1,450p'
```

После этого уже можно будет точно определить, **куда поставить Hybrid и где должна появляться готовность фото для грида**.

---

### 👤 **User** — 2026-08-20 23:25:32

гибрид - часть дин

---

### 🤖 **Assistant** — 2026-08-20 23:25:33

Да. Именно. Тогда архитектуру надо понимать иначе.

**Hybrid — не отдельный этап после DINO/Qwen. Hybrid является частью DINO-пайплайна.**

То есть правильная логика:

```text id="7c4p9v"
PHOTO INGEST
     ↓
  PostgreSQL
     ↓
 DINO WORKER
     │
     ├─ DINO recognition
     │
     ├─ Hybrid v12
     │
     └─ final address / sort
     ↓
 PHOTO READY
     ↓
 PREVIEW
     ↓
 GRID
```

А **Qwen идёт независимо**, параллельной веткой:

```text id="3x8w2k"
             ┌──→ DINO → Hybrid → Sort → Preview
PHOTO ───────┤
             └──→ Qwen
```

И это полностью соответствует тому, что у нас было зафиксировано раньше: **распознавание адреса — DINO + Hybrid, без участия LLM**.

### Тогда текущая проблема

Показанный `supervisor.py` запускает:

```text id="5x5d2j"
DINO worker
Qwen worker
```

но надо посмотреть **внутри `dino_worker.py`**, потому что именно там должен находиться или вызываться Hybrid.

А отдельный:

```text id="8z5h2r"
scripts/run_hybrid_v12.py
```

скорее всего является **production-реализацией алгоритма Hybrid**, а не самостоятельной веткой архитектуры.

Поэтому **ничего пока не переносим и не переписываем**.

Нам надо посмотреть DINO worker — особенно место, где он заканчивает обработку фотографии и записывает:

- `address_id`
- `dino_status`
- `sort_status`
- `hybrid_final_id`
- и т. п.

Вот это сейчас самое важное:

```bash id="q3k8xa"
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DINO WORKER ================" && \
nl -ba app/workers/dino_worker.py | sed -n '1,430p'
```

После него уже станет понятно, **где именно сейчас живёт Hybrid в новой DB-архитектуре** и почему отдельный `run_hybrid_v12.py` вообще существует.

---

### 👤 **User** — 2026-08-20 23:26:08

1	from __future__ import annotations
     2	
     3	import os
     4	import time
     5	from pathlib import Path
     6	
     7	import psycopg2
     8	from psycopg2.extras import RealDictCursor
     9	
    10	from app.core.config import Settings
    11	from app.core.embedder import SceneEmbedder
    12	from app.core.fingerprint import FingerprintManager
    13	from app.core.recognizer import SceneRecognizer
    14	
    15	
    16	DB_CONFIG = {
    17	    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    18	    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    19	    "user": os.getenv("PHOTOBASE_USER", "lora"),
    20	    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    21	    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
    22	}
    23	
    24	
    25	# ============================================================
    26	# DATABASE
    27	# ============================================================
    28	
    29	def get_connection():
    30	    return psycopg2.connect(**DB_CONFIG)
    31	
    32	
    33	def reset_processing(conn):
    34	    """
    35	    Возвращает зависшие DINO-задачи обратно в очередь.
    36	
    37	    Это позволяет продолжить работу после:
    38	        - остановки процесса
    39	        - перезагрузки
    40	        - падения Python
    41	        - аварии машины
    42	    """
    43	
    44	    with conn.cursor() as cur:
    45	        cur.execute(
    46	            """
    47	            UPDATE photos
    48	            SET
    49	                dino_status = 'pending',
    50	                updated_at = CURRENT_TIMESTAMP
    51	            WHERE dino_status = 'processing'
    52	            """
    53	        )
    54	
    55	        count = cur.rowcount
    56	
    57	    conn.commit()
    58	
    59	    if count:
    60	        print(
    61	            f"[DINO] Reset stale processing jobs: {count}"
    62	        )
    63	
    64	
    65	def claim_photo(conn):
    66	    """
    67	    Забирает следующую фотографию из DINO-очереди.
    68	
    69	    ВАЖНО:
    70	
    71	    Qwen здесь вообще не учитывается.
    72	
    73	    DINO получает фотографию только потому,
    74	    что у неё уже существует photo_id и
    75	    dino_status = pending.
    76	    """
    77	
    78	    with conn.cursor(
    79	        cursor_factory=RealDictCursor
    80	    ) as cur:
    81	
    82	        cur.execute(
    83	            """
    84	            SELECT
    85	                id,
    86	                photo_id,
    87	                initial_id,
    88	                source_path,
    89	                filename
    90	            FROM photos
    91	            WHERE
    92	                dino_status = 'pending'
    93	                AND source_path IS NOT NULL
    94	                AND source_path <> ''
    95	            ORDER BY id
    96	            FOR UPDATE SKIP LOCKED
    97	            LIMIT 1
    98	            """
    99	        )
   100	
   101	        row = cur.fetchone()
   102	
   103	        if row is None:
   104	            conn.commit()
   105	            return None
   106	
   107	        cur.execute(
   108	            """
   109	            UPDATE photos
   110	            SET
   111	                dino_status = 'processing',
   112	                updated_at = CURRENT_TIMESTAMP
   113	            WHERE
   114	                id = %s
   115	                AND dino_status = 'pending'
   116	            """,
   117	            (row["id"],),
   118	        )
   119	
   120	        conn.commit()
   121	
   122	        return row
   123	
   124	
   125	# ============================================================
   126	# RESULT
   127	# ============================================================
   128	
   129	def mark_done(
   130	    conn,
   131	    db_id,
   132	    result,
   133	    elapsed,
   134	):
   135	    """
   136	    Сохраняет результат DINO.
   137	
   138	    Главный результат нового слоя:
   139	
   140	        address_id = адрес, определённый DINO.
   141	
   142	    photo_id остаётся независимым идентификатором фотографии.
   143	    """
   144	
   145	    address_id = result.get("best_id")
   146	
   147	    with conn.cursor() as cur:
   148	
   149	        cur.execute(
   150	            """
   151	            UPDATE photos
   152	            SET
   153	                dino_status = 'done',
   154	
   155	                address_id = %s,
   156	
   157	                dino_fingerprint = %s,
   158	                dino_score = %s,
   159	                dino_second_score = %s,
   160	                dino_margin = %s,
   161	                dino_time_sec = %s,
   162	
   163	                error_message = NULL,
   164	                updated_at = CURRENT_TIMESTAMP
   165	
   166	            WHERE id = %s
   167	            """,
   168	            (
   169	                address_id,
   170	
   171	                # Старое поле оставляем для совместимости
   172	                # со старым кодом и статистикой.
   173	                address_id,
   174	
   175	                result.get("score"),
   176	                result.get("second_score"),
   177	                result.get("margin"),
   178	
   179	                elapsed,
   180	
   181	                db_id,
   182	            ),
   183	        )
   184	
   185	    conn.commit()
   186	
   187	
   188	def mark_error(
   189	    conn,
   190	    db_id,
   191	    error,
   192	):
   193	    """
   194	    Фиксирует ошибку конкретной фотографии.
   195	
   196	    Qwen-status при этом НЕ меняется.
   197	    """
   198	
   199	    message = str(error)
   200	
   201	    with conn.cursor() as cur:
   202	
   203	        cur.execute(
   204	            """
   205	            UPDATE photos
   206	            SET
   207	                dino_status = 'error',
   208	                error_message = %s,
   209	                updated_at = CURRENT_TIMESTAMP
   210	            WHERE id = %s
   211	            """,
   212	            (
   213	                message[:4000],
   214	                db_id,
   215	            ),
   216	        )
   217	
   218	    conn.commit()
   219	
   220	
   221	# ============================================================
   222	# WORKER
   223	# ============================================================
   224	
   225	def main():
   226	
   227	    settings = Settings()
   228	
   229	    print("=" * 70)
   230	    print("DINO WORKER")
   231	    print("=" * 70)
   232	    print("device  :", settings.device)
   233	    print("database:", DB_CONFIG["dbname"])
   234	    print("=" * 70)
   235	
   236	    # --------------------------------------------------------
   237	    # MODEL
   238	    # --------------------------------------------------------
   239	
   240	    print("[DINO] Loading SceneEmbedder...")
   241	
   242	    embedder = SceneEmbedder(settings)
   243	
   244	    manager = FingerprintManager(
   245	        settings,
   246	        embedder,
   247	    )
   248	
   249	    recognizer = SceneRecognizer(
   250	        settings,
   251	        embedder,
   252	        manager,
   253	    )
   254	
   255	    # --------------------------------------------------------
   256	    # DATABASE
   257	    # --------------------------------------------------------
   258	
   259	    conn = get_connection()
   260	
   261	    print("[DINO] Database connected.")
   262	
   263	    # --------------------------------------------------------
   264	    # RECOVERY
   265	    # --------------------------------------------------------
   266	
   267	    reset_processing(conn)
   268	
   269	    print("[DINO] Worker ready.")
   270	
   271	    max_items = int(
   272	        os.getenv(
   273	            "DINO_MAX_ITEMS",
   274	            "0",
   275	        )
   276	    )
   277	
   278	    processed = 0
   279	    errors = 0
   280	
   281	    try:
   282	
   283	        while True:
   284	
   285	            # ------------------------------------------------
   286	            # LIMIT
   287	            # ------------------------------------------------
   288	
   289	            if (
   290	                max_items > 0
   291	                and processed >= max_items
   292	            ):
   293	                print(
   294	                    f"[DINO] "
   295	                    f"Reached max_items={max_items}."
   296	                )
   297	                break
   298	
   299	            # ------------------------------------------------
   300	            # CLAIM
   301	            # ------------------------------------------------
   302	
   303	            row = claim_photo(conn)
   304	
   305	            if row is None:
   306	
   307	                print(
   308	                    "[DINO] Queue empty."
   309	                )
   310	
   311	                break
   312	
   313	            db_id = row["id"]
   314	            photo_id = row["photo_id"]
   315	            initial_id = row["initial_id"]
   316	            source_path = Path(
   317	                row["source_path"]
   318	            )
   319	
   320	            print()
   321	            print("-" * 70)
   322	
   323	            print(
   324	                "[DINO]",
   325	                photo_id,
   326	                "| initial_id:",
   327	                initial_id,
   328	                "| file:",
   329	                source_path.name,
   330	            )
   331	
   332	            started = time.perf_counter()
   333	
   334	            # ------------------------------------------------
   335	            # PROCESS
   336	            # ------------------------------------------------
   337	
   338	            try:
   339	
   340	                if not source_path.exists():
   341	                    raise FileNotFoundError(
   342	                        f"Photo not found: {source_path}"
   343	                    )
   344	
   345	                if not source_path.is_file():
   346	                    raise FileNotFoundError(
   347	                        f"Not a file: {source_path}"
   348	                    )
   349	
   350	                result = recognizer.recognize_one(
   351	                    source_path,
   352	                    top_k=5,
   353	                    threshold=0.65,
   354	                )
   355	
   356	                elapsed = (
   357	                    time.perf_counter()
   358	                    - started
   359	                )
   360	
   361	                # ------------------------------------------------
   362	                # SAVE
   363	                # ------------------------------------------------
   364	
   365	                mark_done(
   366	                    conn,
   367	                    db_id,
   368	                    result,
   369	                    elapsed,
   370	                )
   371	
   372	                address_id = result.get(
   373	                    "best_id"
   374	                )
   375	
   376	                print(
   377	                    f"[DINO] DONE "
   378	                    f"{photo_id}"
   379	                    f" -> address_id={address_id}"
   380	                    f" score={result.get('score', 0):.6f}"
   381	                    f" margin={result.get('margin', 0):.6f}"
   382	                    f" time={elapsed:.2f}s"
   383	                )
   384	
   385	                processed += 1
   386	
   387	            # ------------------------------------------------
   388	            # ERROR
   389	            # ------------------------------------------------
   390	
   391	            except Exception as exc:
   392	
   393	                errors += 1
   394	
   395	                elapsed = (
   396	                    time.perf_counter()
   397	                    - started
   398	                )
   399	
   400	                print(
   401	                    f"[DINO] ERROR "
   402	                    f"{photo_id}: {exc}"
   403	                    f" time={elapsed:.2f}s"
   404	                )
   405	
   406	                try:
   407	
   408	                    mark_error(
   409	                        conn,
   410	                        db_id,
   411	                        exc,
   412	                    )
   413	
   414	                except Exception as db_error:
   415	
   416	                    print(
   417	                        "[DINO] "
   418	                        "DB ERROR while marking error:",
   419	                        db_error,
   420	                    )
   421	
   422	    finally:
   423	
   424	        conn.close()
   425	
   426	        print()
   427	        print("=" * 70)
   428	        print("DINO WORKER STOPPED")
   429	        print("=" * 70)
   430	
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:26:09

Да, теперь точно видно.

**В текущем `dino_worker.py` Hybrid вообще не вызывается.** DINO сейчас делает только:

```text
recognizer.recognize_one()
        ↓
best_id
        ↓
photos.address_id
        ↓
dino_status = done
```

То есть поле `address_id` сейчас содержит **первичный результат DINO**, а не окончательный Hybrid.

При этом отдельный `run_hybrid_v12.py` содержит именно тот алгоритм, который нам нужен для окончательного решения:

```text
DINO recognition
      ↓
Hybrid v12
      ↓
final_id
      ↓
sort_results()
```

### Значит архитектурно надо разделить два понятия

Сейчас:

```text
address_id
    ↑
DINO best_id
```

А должно быть:

```text
DINO
  ↓
dino_address_id / исходный результат
  ↓
Hybrid v12
  ↓
hybrid_final_id
  ↓
окончательный address_id
```

Причём **сам алгоритм Hybrid v12 мы не меняем** — он у нас frozen.

И вот здесь становится понятно, зачем в `photos` уже присутствуют поля:

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

То есть схема БД уже явно подготовлена под эту архитектуру.

### А preview тогда действительно должен быть самым последним

Получается окончательная цепочка:

```text
PHOTO INGEST
      ↓
photo_id + initial_id
      ↓
┌───────────────┬───────────────┐
│               │               │
↓               ↓               ↓
DINO            QWEN
│
├─ recognition
│
├─ Hybrid v12
│
├─ final address
│
└─ sort
      ↓
preview
      ↓
GRID
```

И Qwen при этом остаётся независимым.

**Я бы сейчас не трогал ни preview, ни supervisor.** Следующий шаг — посмотреть, насколько легко встроить уже существующий frozen Hybrid v12 в DINO worker без изменения самого алгоритма.

Нам нужны прежде всего функции `hybrid_v12()` и загрузка subfingerprints из `run_hybrid_v12.py`.

Дай:

```bash id="j2v6bd"
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID CORE ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,420p' && \
echo "================ HYBRID MAIN ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '500,640p'
```

После этого можно будет определить **минимальный способ встроить Hybrid именно внутрь DINO worker**, не ломая frozen v12.

---

### 👤 **User** — 2026-08-20 23:26:54

ранее гибрид работал после дино успешно

---

### 🤖 **Assistant** — 2026-08-20 23:26:55

Да. И это важное уточнение.

Тогда **не надо изобретать новую схему Hybrid**. У нас уже была рабочая последовательность:

```text
DINO
 ↓
результаты DINO
 ↓
Hybrid v12
 ↓
окончательный ID
 ↓
sort
```

Она успешно работала раньше. Сейчас при переходе на новую DB-архитектуру мы просто видим, что:

- `dino_worker.py` сейчас заканчивается на `recognize_one()`;
- `run_hybrid_v12.py` содержит рабочий Hybrid;
- поля `hybrid_*` в PostgreSQL уже существуют;
- `sort_status` тоже существует;
- preview пока отдельно и правильно оставлен после завершения обработки.

То есть задача сейчас не «разработать Hybrid», а **вернуть уже работавшую связку DINO → Hybrid в новый pipeline**.

И я бы здесь был очень осторожен: **не переносить логику кусками, пока не найдём тот старый участок, где DINO передавал результаты в Hybrid.**

Лучше сначала найдём историческую реализацию Hybrid-вызова в проекте/backup:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'hybrid_v12|hybrid_v[0-9]+|hybrid_final_id|hybrid_original_id|hybrid_changed|run_hybrid' \
app scripts \
--include="*.py" \
--include="*.sh" | \
grep -vE '__pycache__|benchmark|export_visual'
```

**Цель — найти именно старую рабочую точку вызова**, а не менять алгоритм.

После этого уже можно будет аккуратно восстановить:

**DINO → Hybrid → sort → готовое фото**, сохранив нынешние `photo_id`, `initial_id`, PostgreSQL и supervisor.

---

### 👤 **User** — 2026-08-20 23:27:15

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'hybrid_v12|hybrid_v[0-9]+|hybrid_final_id|hybrid_original_id|hybrid_changed|run_hybrid' \
app scripts \
--include="*.py" \
--include="*.sh" | \
grep -vE '__pycache__|benchmark|export_visual'
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/web/photo_db.py:50:            hybrid_changed,
scripts/run_daily_hybrid_v12.sh:42:/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
scripts/run_hybrid_v12.py:207:def hybrid_v12(rows, embedder, subs):
scripts/run_hybrid_v12.py:363:        hybrid_changed = best != old
scripts/run_hybrid_v12.py:370:        result["hybrid_changed"] = hybrid_changed
scripts/run_hybrid_v12.py:460:                "hybrid_changed": item.get(
scripts/run_hybrid_v12.py:461:                    "hybrid_changed"
scripts/run_hybrid_v12.py:603:    hybrid_rows, changed, sub_count = hybrid_v12(
scripts/run_hybrid_v12.py:656:        output_dir / "hybrid_v12.json"
scripts/run_hybrid_v12.py:705:        "hybrid_changed": len(changed),
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:27:17

Вот теперь картина стала окончательно ясной.

**В текущей версии проекта вызова Hybrid из DINO worker нет вообще.** Поиск это подтвердил.

Есть только:

- `scripts/run_hybrid_v12.py` — сам рабочий Hybrid;
- `scripts/run_daily_hybrid_v12.sh` — его отдельный запуск;
- поля `hybrid_*` в DB/UI;
- но **нет связки `dino_worker → hybrid_v12()`**.

То есть после перестройки pipeline старая рабочая связка была фактически вынесена из DINO-процесса.

### И это хорошо объясняет текущее состояние

Сейчас:

```text id="w3d4r7"
INGEST
   ↓
DINO worker
   ↓
address_id = DINO best_id
   ↓
dino_status = done

QWEN worker
   ↓
qwen_status = done
```

А Hybrid живёт отдельно:

```text id="0x4xj7"
run_daily_hybrid_v12.sh
   ↓
run_hybrid_v12.py
   ↓
снова своё DINO recognition
   ↓
Hybrid
   ↓
sort
```

То есть **Hybrid не продолжает текущий DINO worker**, а фактически запускает отдельный старый pipeline.

---

### Поэтому сейчас я бы ничего не переписывал

Нам нужно восстановить именно прежнюю рабочую связь.

Причём я вижу важную деталь: `run_hybrid_v12.py` уже умеет делать:

```text
recognition
→ adapt_recognizer_rows()
→ hybrid_v12()
→ sort_results()
```

Значит наиболее безопасный вариант — **не копировать Hybrid-алгоритм в `dino_worker.py`**, а вынести/использовать его существующие функции.

Но прежде чем делать это, надо посмотреть **структуру входных `rows`, которую получает `hybrid_v12()`**. Тогда мы поймём, сможет ли результат `recognizer.recognize_one()` напрямую стать входом Hybrid.

Следующая команда — только диагностика:

```bash id="5qv8n2"
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba scripts/run_hybrid_v12.py | sed -n '150,420p'
```

Особенно нас интересуют:

```text
adapt_recognizer_rows()
hybrid_v12()
```

После этого я смогу сказать, **как вернуть старую рабочую схему без изменения самого Hybrid v12**.

---

### 👤 **User** — 2026-08-20 23:28:10

ne_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'hybrid_v12|hybrid_v[0-9]+|hybrid_final_id|hybrid_original_id|hybrid_changed|run_hybrid' \
app scripts \
--include="*.py" \
--include="*.sh" | \
grep -vE '__pycache__|benchmark|export_visual'
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/web/photo_db.py:50:            hybrid_changed,
scripts/run_daily_hybrid_v12.sh:42:/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
scripts/run_hybrid_v12.py:207:def hybrid_v12(rows, embedder, subs):
scripts/run_hybrid_v12.py:363:        hybrid_changed = best != old
scripts/run_hybrid_v12.py:370:        result["hybrid_changed"] = hybrid_changed
scripts/run_hybrid_v12.py:460:                "hybrid_changed": item.get(
scripts/run_hybrid_v12.py:461:                    "hybrid_changed"
scripts/run_hybrid_v12.py:603:    hybrid_rows, changed, sub_count = hybrid_v12(
scripts/run_hybrid_v12.py:656:        output_dir / "hybrid_v12.json"
scripts/run_hybrid_v12.py:705:        "hybrid_changed": len(changed),
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
bash: alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$: No such file or directory
bash: app/web/components/photos.py:347:: No such file or directory
bash: app/web/photo_db.py:48:: No such file or directory
bash: app/web/photo_db.py:49:: No such file or directory
bash: app/web/photo_db.py:50:: No such file or directory
bash: syntax error near unexpected token `('
bash: scripts/run_hybrid_v12.py:363:: No such file or directory
bash: scripts/run_hybrid_v12.py:370:: No such file or directory
bash: syntax error near unexpected token `('
bash: scripts/run_hybrid_v12.py:461:: No such file or directory
bash: syntax error near unexpected token `('
bash: scripts/run_hybrid_v12.py:656:: No such file or directory
bash: syntax error near unexpected token `('
bash: alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$: No such file or directory
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:28:11

Да, здесь просто случайно **вставился сам вывод терминала вместе с командой**. Ничего в проекте не сломалось.

Вот это:

```text
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$
app/web/components/photos.py:347:
...
```

Bash попытался выполнить как команды, поэтому и получил `No such file or directory` и `syntax error`.

Сейчас ты уже снова находишься в правильной директории:

```text
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$
```

Давай продолжим **только диагностикой**, ничего не меняем.

Выполни именно эту команду:

```bash
nl -ba scripts/run_hybrid_v12.py | sed -n '150,420p'
```

Пришли весь вывод. После него разберём, **как именно раньше Hybrid получал результаты DINO**, и уже потом решим, что восстанавливать.

---

### 👤 **User** — 2026-08-20 23:28:31

lexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ nl -ba scripts/run_hybrid_v12.py | sed -n '150,420p'
   150	
   151	    for i, ch in enumerate(combined):
   152	
   153	        if ch != "[":
   154	            continue
   155	
   156	        try:
   157	            candidate, _ = decoder.raw_decode(
   158	                combined[i:]
   159	            )
   160	
   161	            if isinstance(candidate, list):
   162	                data = candidate
   163	                break
   164	
   165	        except json.JSONDecodeError:
   166	            pass
   167	
   168	    if data is None:
   169	        raise RuntimeError(
   170	            "Не удалось найти JSON-массив в выводе recognition"
   171	        )
   172	
   173	    print("Images:", len(data))
   174	    print(f"Recognition time: {elapsed:.2f} sec")
   175	
   176	    return data, elapsed
   177	
   178	
   179	def adapt_recognizer_rows(rows):
   180	    """
   181	    Convert current recognizer output into the legacy
   182	    top1..top5 format required by frozen Hybrid v12.
   183	    """
   184	
   185	    adapted = []
   186	
   187	    for row in rows:
   188	        item = dict(row)
   189	
   190	        candidates = row.get("candidates", [])
   191	
   192	        for n in range(1, 6):
   193	            item[f"top{n}"] = None
   194	            item[f"top{n}_score"] = 0.0
   195	
   196	        for n, candidate in enumerate(candidates[:5], start=1):
   197	            item[f"top{n}"] = candidate.get("id")
   198	            item[f"top{n}_score"] = float(
   199	                candidate.get("score", 0.0)
   200	            )
   201	
   202	        adapted.append(item)
   203	
   204	    return adapted
   205	
   206	
   207	def hybrid_v12(rows, embedder, subs):
   208	    """
   209	    Exact production adaptation of the frozen Hybrid v12 logic.
   210	
   211	    Input:
   212	        recognizer rows containing top1..top5.
   213	
   214	    Output:
   215	        rows with final best_id.
   216	    """
   217	
   218	    changed = []
   219	    results = []
   220	    sub_count = 0
   221	
   222	    for i, row in enumerate(rows):
   223	
   224	        old = row.get("top1")
   225	
   226	        scores = defaultdict(float)
   227	
   228	        # ====================================================
   229	        # GLOBAL TOP-5
   230	        # ====================================================
   231	
   232	        for k in range(1, 6):
   233	
   234	            fp = row.get(f"top{k}")
   235	            sc = row.get(f"top{k}_score")
   236	
   237	            if fp:
   238	                scores[fp] += (
   239	                    float(sc)
   240	                    * GLOBAL_WEIGHT
   241	                )
   242	
   243	        # ====================================================
   244	        # SUB ONLY BORDER CASES
   245	        # ====================================================
   246	
   247	        margin = row.get(
   248	            "margin",
   249	            1,
   250	        )
   251	
   252	        if margin < MARGIN_LIMIT:
   253	
   254	            sub_count += 1
   255	
   256	            image = Path(
   257	                row["file"]
   258	            )
   259	
   260	            query = embedder.embed_paths(
   261	                [image]
   262	            )[0]
   263	
   264	            query = normalize(query)
   265	
   266	            # FROZEN V12:
   267	            # only TOP1 and TOP2
   268	            candidates = [
   269	                row.get("top1"),
   270	                row.get("top2"),
   271	            ]
   272	
   273	            for parent in candidates:
   274	
   275	                if not parent:
   276	                    continue
   277	
   278	                for sub_id, sub_emb in subs.items():
   279	
   280	                    if not sub_id.startswith(parent):
   281	                        continue
   282	
   283	                    sim = max(
   284	                        sub_emb @ query
   285	                    )
   286	
   287	                    if sim > 0.88:
   288	
   289	                        if sim > 0.92:
   290	                            bonus = 2.5
   291	                        else:
   292	                            bonus = 1.0
   293	
   294	                        scores[parent] += (
   295	                            float(sim)
   296	                            * bonus
   297	                        )
   298	
   299	        # ====================================================
   300	        # SEQUENCE CONSENSUS
   301	        # ====================================================
   302	
   303	        neighbors = get_neighbor_votes(
   304	            rows,
   305	            i,
   306	        )
   307	
   308	        left_fp = None
   309	        right_fp = None
   310	
   311	        if i > 0:
   312	            left_fp = rows[i - 1].get("top1")
   313	
   314	        if i < len(rows) - 1:
   315	            right_fp = rows[i + 1].get("top1")
   316	
   317	        if (
   318	            left_fp
   319	            and right_fp
   320	            and left_fp == right_fp
   321	        ):
   322	            # FROZEN V12:
   323	            # actual implementation uses +3.0
   324	            scores[left_fp] += 3.0
   325	
   326	        # ====================================================
   327	        # FINAL DECISION V12
   328	        # ====================================================
   329	
   330	        best = old
   331	
   332	        ranked = sorted(
   333	            scores.items(),
   334	            key=lambda x: x[1],
   335	            reverse=True,
   336	        )
   337	
   338	        if ranked:
   339	
   340	            candidate = ranked[0][0]
   341	
   342	            gain = (
   343	                scores[candidate]
   344	                - scores.get(old, 0)
   345	            )
   346	
   347	            if (
   348	                candidate != old
   349	                and gain > 1.5
   350	            ):
   351	                best = candidate
   352	
   353	        old_score = scores.get(
   354	            old,
   355	            0,
   356	        )
   357	
   358	        new_score = scores.get(
   359	            best,
   360	            0,
   361	        )
   362	
   363	        hybrid_changed = best != old
   364	
   365	        result = dict(row)
   366	
   367	        result["original_best_id"] = old
   368	        result["best_id"] = best
   369	
   370	        result["hybrid_changed"] = hybrid_changed
   371	
   372	        result["hybrid_old_score"] = old_score
   373	        result["hybrid_score"] = new_score
   374	
   375	        result["hybrid_margin"] = margin
   376	        result["hybrid_neighbors"] = dict(neighbors)
   377	
   378	        results.append(result)
   379	
   380	        if (
   381	            best != old
   382	            and new_score > old_score
   383	        ):
   384	            changed.append(
   385	                {
   386	                    "file": Path(
   387	                        row["file"]
   388	                    ).name,
   389	                    "old": old,
   390	                    "new": best,
   391	                    "margin": margin,
   392	                    "neighbors": dict(neighbors),
   393	                    "old_score": scores[old],
   394	                    "new_score": scores[best],
   395	                }
   396	            )
   397	
   398	    return results, changed, sub_count
   399	
   400	
   401	def sort_results(rows, output_dir):
   402	    """
   403	    Copy photos according to FINAL Hybrid best_id.
   404	    """
   405	
   406	    print()
   407	    print("=" * 80)
   408	    print("SORTING")
   409	    print("=" * 80)
   410	
   411	    output_dir.mkdir(
   412	        parents=True,
   413	        exist_ok=True,
   414	    )
   415	
   416	    counters = Counter()
   417	    sorted_rows = []
   418	
   419	    for item in rows:
   420	
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:28:32

Да. Теперь видно главное: **Hybrid v12 не является отдельным самостоятельным распознаванием**. Он получает уже готовые результаты DINO и поверх них делает rerank.

Ключевой участок:

```text
DINO recognition
    ↓
candidates top1..top5
    ↓
adapt_recognizer_rows()
    ↓
Hybrid v12
    ├─ GLOBAL TOP-5
    ├─ SUB — только пограничные случаи
    ├─ SEQUENCE CONSENSUS — соседние фото
    └─ FINAL DECISION
    ↓
best_id
```

Особенно важно:

```python
old = row.get("top1")
```

То есть `old` — это **первичный DINO top-1**.

А затем:

```python
result["original_best_id"] = old
result["best_id"] = best
```

Получаем ровно ту модель, которую мы обсуждали:

- `original_best_id` → результат DINO;
- `best_id` → окончательный результат Hybrid;
- `hybrid_changed` → изменил ли Hybrid решение.

### И ещё один важный момент

Hybrid **сам повторно считает embedding только для пограничных случаев**:

```python
if margin < MARGIN_LIMIT:
    query = embedder.embed_paths([image])[0]
```

То есть твоя мысль про превью абсолютно правильная.

Для обычной фотографии:

```text
DINO
 ↓
результат
 ↓
Hybrid
 ↓
готовый final_id
```

Для пограничной:

```text
DINO
 ↓
margin < limit
 ↓
дополнительный embedding для SUB
 ↓
Hybrid
 ↓
final_id
```

Поэтому создавать preview **до Hybrid действительно практически бессмысленно**, если preview должен отражать окончательную обработанную фотографию/её итоговую принадлежность.

---

### Но теперь обнаружилась важная техническая проблема

`hybrid_v12()` ожидает:

```python
row["file"]
row["candidates"]
row["margin"]
```

а текущий `dino_worker.py` после:

```python
result = recognizer.recognize_one(...)
```

получает `result`, после чего сохраняет только нужные поля в PostgreSQL.

Значит нам нужно не переносить Hybrid целиком, а сделать мост:

```text
recognizer.recognize_one()
        ↓
результат DINO
        ↓
адаптация к формату Hybrid
        ↓
hybrid_v12()
        ↓
final best_id
        ↓
одна запись в PostgreSQL
```

И здесь я бы **не стал пока менять `dino_worker.py`**.

Нужно сначала посмотреть **полный формат `recognizer.recognize_one()`**, чтобы не угадать названия полей. В самом `run_hybrid_v12.py` это уже предусмотрено через `adapt_recognizer_rows()`.

Следующая команда:

```bash
nl -ba scripts/run_hybrid_v12.py | sed -n '1,155p'
```

Она покажет функцию, которая сейчас получает результаты recognition. После неё мы сможем точно сопоставить её с `recognizer.recognize_one()` и восстановить старую последовательность **без изменения frozen Hybrid v12**.

---

### 👤 **User** — 2026-08-20 23:29:00

можно ли както зафиксировать эту связку чтобы потом не искать

---

### 🤖 **Assistant** — 2026-08-20 23:29:00

Да, и я бы **обязательно зафиксировал**. У нас уже достаточно информации, чтобы записать архитектурное правило проекта и больше к этому не возвращаться.

Зафиксировать нужно именно как **неизменяемую производственную цепочку**, а не просто заметку про Hybrid:

```text
PHOTO INGEST
    ↓
DINO recognition
    ↓
DINO top-1..top-5
    ↓
HYBRID v12
    ├─ Global TOP-5
    ├─ SUB для border cases
    ├─ Neighbor / sequence consensus
    └─ Final decision
    ↓
FINAL address_id
    ↓
SORT
    ↓
PREVIEW
    ↓
GRID
```

И принцип:

> **Hybrid v12 — это второй этап DINO recognition, а не отдельное независимое распознавание. Frozen Hybrid v12 не изменяется. Preview создаётся только после завершения DINO + Hybrid + Sort.**

Также важно сохранить соответствие:

```text
original_best_id = DINO top-1
best_id          = Hybrid final result
hybrid_changed   = изменил ли Hybrid решение
```

Я бы это записал в память проекта, чтобы в следующих разговорах можно было сразу продолжать с этой архитектуры.

---

### 👤 **User** — 2026-08-20 23:29:13

да

---

### 🤖 **Assistant** — 2026-08-20 23:29:17

Зафиксировал. Дальше считаем эту связку **замороженной архитектурой проекта** и не будем каждый раз искать её заново.

---

### 👤 **User** — 2026-08-20 23:29:22

далее

---

### 🤖 **Assistant** — 2026-08-20 23:29:23

Дальше логичный шаг — **не трогать Hybrid**, а восстановить его вызов после DINO в текущем PostgreSQL pipeline.

Нужно сначала проверить точный формат результата `recognizer.recognize_one()`, чтобы сделать мост без догадок.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,155p'
```

После этого сравним его с `dino_worker.py` и определим **минимальный патч DINO → Hybrid**. Пока ничего не изменяем.

---

