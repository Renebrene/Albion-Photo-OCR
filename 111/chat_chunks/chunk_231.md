## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 🤖 **Assistant** — 2026-08-21 01:24:39

После `dino_worker.py` сейчас **Hybrid v12 автоматически не запускается**.

По показанному коду цепочка такая:

```text
DINO worker
   ↓
SceneRecognizer.recognize_one()
   ↓
получает result
   ├── best_id
   ├── score
   ├── second_score
   └── margin
   ↓
mark_done()
   ↓
PostgreSQL photos
```

В `mark_done()` записывается:

```text
address_id        = result["best_id"]
dino_fingerprint  = result["best_id"]
dino_score        = result["score"]
dino_second_score = result["second_score"]
dino_margin       = result["margin"]
dino_time_sec     = elapsed
dino_status       = 'done'
```

То есть после DINO результат **просто сохраняется в PostgreSQL**.

### Что НЕ происходит

После этого `dino_worker.py` не делает:

```text
DINO
 ↓
Hybrid v12
 ↓
hybrid_final_id
```

В самом worker после `recognize_one()` вызывается только:

```text
mark_done(...)
```

и затем следующая фотография из очереди.

Поэтому сейчас:

```text
┌──────────────────────────┐
│      DINO WORKER         │
│                          │
│ SceneRecognizer          │
│      ↓                   │
│ best_id                  │
│      ↓                   │
│ PostgreSQL               │
└──────────────────────────┘
```

А Hybrid — **отдельный pipeline**:

```text
run_hybrid_v12.py
       ↓
run_recognition()
       ↓
DINO
       ↓
Hybrid v12
       ↓
hybrid_final_id
```

И вот это как раз надо сейчас проверить: **есть ли вообще какой-либо код, который после записи `dino_status='done'` берет эту запись и запускает Hybrid**. По уже показанным `grep` — похоже, что **нет**.

Следующим шагом логично проверить `supervisor.py` и все места, где отслеживается `dino_status='done'`: именно там может находиться скрытая связка DINO → следующий этап.

---

### 👤 **User** — 2026-08-21 01:25:21

давай

---

### 🤖 **Assistant** — 2026-08-21 01:25:23

Да. Проверяем **не предположением, а по коду**, есть ли связка:

`dino_status = done → Hybrid`.

Выполни сначала этот блок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DINO DONE / NEXT STAGE REFERENCES ================" && \
grep -RniE \
'dino_status.*done|dino_status.*processing|dino_status.*pending|hybrid_v12|run_hybrid|hybrid_final_id|hybrid_original_id|sort_status' \
app scripts \
--include="*.py" \
--include="*.sh" \
| head -600
```

Потом отдельно посмотрим supervisor:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SUPERVISOR ================" && \
nl -ba app/pipeline/supervisor.py | sed -n '1,280p'
```

И особенно важно — recovery:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ RECOVERY ================" && \
nl -ba app/pipeline/recovery.py | sed -n '1,180p'
```

**Пока ничего не меняем.**

Нам нужно установить фактическую цепочку:

```text
DINO worker
   ↓
dino_status = done
   ↓
??? кто забирает результат ???
   ↓
Hybrid?
   ↓
hybrid_final_id
   ↓
sort?
```

Если после `dino_status='done'` **никто не запускает Hybrid**, тогда становится ясно, что текущий технический модуль действительно работает по старой схеме, а `run_hybrid_v12.py` — отдельный pipeline.

---

### 👤 **User** — 2026-08-21 01:25:59

echo "================ DINO DONE / NEXT STAGE REFERENCES ================" && \
grep -RniE \
'dino_status.*done|dino_status.*processing|dino_status.*pending|hybrid_v12|run_hybrid|hybrid_final_id|hybrid_original_id|sort_status' \
app scripts \
--include="*.py" \
--include="*.sh" \
| head -600
================ DINO DONE / NEXT STAGE REFERENCES ================
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/web/photo_db.py:57:            sort_status
app/web/photo_db.py:90:                WHERE dino_status = 'done'
app/web/photo_db.py:94:                WHERE dino_status = 'processing'
app/web/photo_db.py:98:                WHERE dino_status = 'pending'
app/pipeline/recovery.py:54:                    dino_status = 'pending',
app/pipeline/recovery.py:58:                    dino_status = 'processing'
app/workers/dino_worker.py:49:                dino_status = 'pending',
app/workers/dino_worker.py:51:            WHERE dino_status = 'processing'
app/workers/dino_worker.py:75:    dino_status = pending.
app/workers/dino_worker.py:92:                dino_status = 'pending'
app/workers/dino_worker.py:111:                dino_status = 'processing',
app/workers/dino_worker.py:115:                AND dino_status = 'pending'
app/workers/dino_worker.py:153:                dino_status = 'done',
scripts/photo_ingest.py:249:                sort_status,
scripts/photo_ingest.py:462:        "  DINO : dino_status = pending"
scripts/benchmark_hybrid_v12_full.py:27:    "data/output/full_recognize_hybrid_v12_test.json"
scripts/run_daily_hybrid_v12.sh:42:/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
scripts/run_hybrid_v12.py:207:def hybrid_v12(rows, embedder, subs):
scripts/run_hybrid_v12.py:603:    hybrid_rows, changed, sub_count = hybrid_v12(
scripts/run_hybrid_v12.py:656:        output_dir / "hybrid_v12.json"
scripts/export_visual_compare.py:44:            "data/output/full_recognize_hybrid_v12_test.json",
scripts/export_visual_compare.py:58:            "hybrid_v12" /
scripts/diagnose_dino_hybrid_db.py:34:                    hybrid_original_id,
scripts/diagnose_dino_hybrid_db.py:35:                    hybrid_final_id,
scripts/diagnose_dino_hybrid_db.py:42:                WHERE dino_status = 'done'
scripts/diagnose_dino_hybrid_db.py:88:                if dino_status == "done":
scripts/diagnose_dino_hybrid_db.py:110:                print(f"hybrid_original_id  : {hybrid_original}")
scripts/diagnose_dino_hybrid_db.py:111:                print(f"hybrid_final_id     : {hybrid_final}")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SUPERVISOR ================" && \
nl -ba app/pipeline/supervisor.py | sed -n '1,280p'
================ SUPERVISOR ================
     1	from __future__ import annotations
     2	
     3	import asyncio
     4	import os
     5	import signal
     6	from datetime import datetime, timedelta
     7	from pathlib import Path
     8	
     9	from app.pipeline.controller import (
    10	    finish_stop,
    11	    get_state,
    12	    is_stop_requested,
    13	    start_automatic,
    14	    start_manual,
    15	    start_watcher,
    16	)
    17	
    18	
    19	PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"
    20	UV = Path.home() / ".local" / "bin" / "uv"
    21	
    22	DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
    23	QWEN_WORKER = PROJECT / "app" / "workers" / "qwen_worker.py"
    24	
    25	POLL_INTERVAL = 1.0
    26	
    27	
    28	# ============================================================
    29	# ENVIRONMENT
    30	# ============================================================
    31	
    32	def build_env():
    33	    env = os.environ.copy()
    34	
    35	    env.update(
    36	        {
    37	            "PATH": (
    38	                f"{Path.home() / '.local/bin'}:"
    39	                "/usr/local/sbin:"
    40	                "/usr/local/bin:"
    41	                "/usr/sbin:"
    42	                "/usr/bin:"
    43	                "/sbin:"
    44	                "/bin"
    45	            ),
    46	            "HOME": str(Path.home()),
    47	            "PYTHONUNBUFFERED": "1",
    48	        }
    49	    )
    50	
    51	    return env
    52	
    53	
    54	# ============================================================
    55	# PROCESS
    56	# ============================================================
    57	
    58	def process_running(process):
    59	    return (
    60	        process is not None
    61	        and process.returncode is None
    62	    )
    63	
    64	
    65	async def consume_output(
    66	    process,
    67	    prefix,
    68	):
    69	    if process.stdout is None:
    70	        return
    71	
    72	    try:
    73	        while True:
    74	            line = await process.stdout.readline()
    75	
    76	            if not line:
    77	                break
    78	
    79	            text = (
    80	                line
    81	                .decode(
    82	                    "utf-8",
    83	                    errors="replace",
    84	                )
    85	                .strip()
    86	            )
    87	
    88	            if text:
    89	                print(
    90	                    f"[{prefix}] {text}",
    91	                    flush=True,
    92	                )
    93	
    94	    except asyncio.CancelledError:
    95	        raise
    96	
    97	    except Exception as exc:
    98	        print(
    99	            f"[{prefix}] OUTPUT ERROR: {exc}",
   100	            flush=True,
   101	        )
   102	
   103	
   104	async def start_worker(
   105	    worker: Path,
   106	    prefix: str,
   107	):
   108	    if not worker.exists():
   109	        raise FileNotFoundError(
   110	            f"{prefix} worker not found: {worker}"
   111	        )
   112	
   113	    process = await asyncio.create_subprocess_exec(
   114	        str(UV),
   115	        "run",
   116	        "python",
   117	        str(worker),
   118	        cwd=str(PROJECT),
   119	        env=build_env(),
   120	        stdout=asyncio.subprocess.PIPE,
   121	        stderr=asyncio.subprocess.STDOUT,
   122	    )
   123	
   124	    print(
   125	        f"[SUPERVISOR] {prefix} START "
   126	        f"PID={process.pid}",
   127	        flush=True,
   128	    )
   129	
   130	    output_task = asyncio.create_task(
   131	        consume_output(
   132	            process,
   133	            prefix,
   134	        )
   135	    )
   136	
   137	    return process, output_task
   138	
   139	
   140	async def stop_process(
   141	    process,
   142	    prefix,
   143	):
   144	    if not process_running(process):
   145	        return
   146	
   147	    print(
   148	        f"[SUPERVISOR] stopping {prefix} "
   149	        f"PID={process.pid}",
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
   280	        # EXIT CODES
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ RECOVERY ================" && \
nl -ba app/pipeline/recovery.py | sed -n '1,180p'
================ RECOVERY ================
     1	from __future__ import annotations
     2	
     3	import os
     4	from datetime import datetime, timezone, timedelta
     5	
     6	import psycopg2
     7	
     8	
     9	DB_CONFIG = {
    10	    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    11	    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    12	    "user": os.getenv("PHOTOBASE_USER", "lora"),
    13	    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    14	    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
    15	}
    16	
    17	
    18	def get_connection():
    19	    return psycopg2.connect(**DB_CONFIG)
    20	
    21	
    22	def recover_stale_jobs(
    23	    timeout_minutes: int = 30,
    24	):
    25	    """
    26	    Возвращает зависшие worker jobs:
    27	
    28	        PROCESSING -> PENDING
    29	
    30	    Только если worker находился в PROCESSING
    31	    дольше timeout_minutes.
    32	
    33	    DONE не затрагивается.
    34	    ERROR не затрагивается.
    35	    """
    36	
    37	    cutoff = datetime.now(timezone.utc).replace(
    38	        tzinfo=None
    39	    ) - timedelta(
    40	        minutes=timeout_minutes
    41	    )
    42	
    43	    recovered_dino = 0
    44	    recovered_qwen = 0
    45	
    46	    with get_connection() as conn:
    47	
    48	        with conn.cursor() as cur:
    49	
    50	            cur.execute(
    51	                """
    52	                UPDATE photos
    53	                SET
    54	                    dino_status = 'pending',
    55	                    dino_started_at = NULL,
    56	                    updated_at = CURRENT_TIMESTAMP
    57	                WHERE
    58	                    dino_status = 'processing'
    59	                    AND dino_started_at < %s
    60	                """,
    61	                (cutoff,),
    62	            )
    63	
    64	            recovered_dino = cur.rowcount
    65	
    66	            cur.execute(
    67	                """
    68	                UPDATE photos
    69	                SET
    70	                    qwen_status = 'pending',
    71	                    qwen_started_at = NULL,
    72	                    updated_at = CURRENT_TIMESTAMP
    73	                WHERE
    74	                    qwen_status = 'processing'
    75	                    AND qwen_started_at < %s
    76	                """,
    77	                (cutoff,),
    78	            )
    79	
    80	            recovered_qwen = cur.rowcount
    81	
    82	        conn.commit()
    83	
    84	    return {
    85	        "dino": recovered_dino,
    86	        "qwen": recovered_qwen,
    87	    }
    88	
    89	
    90	if __name__ == "__main__":
    91	
    92	    result = recover_stale_jobs()
    93	
    94	    print(
    95	        "RECOVERY:",
    96	        result,
    97	    )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:26:00

Да. Теперь картина **однозначная**.

### Что происходит после DINO worker

Ничего следующего по цепочке распознавания **не запускается**.

`supervisor.py` прямо говорит:

```text
DINO → PostgreSQL dino_status
Qwen → PostgreSQL qwen_status
```

И его задача только:

```text
запустить DINO
запустить Qwen
следить за процессами
остановить при необходимости
```

Он **не читает результат DINO и не передаёт его в Hybrid**.

### Фактическая текущая схема

```text
ОБРАБОТАТЬ
    │
    ├───────────────┐
    ↓               ↓
DINO worker       Qwen worker
    │               │
    ↓               ↓
PostgreSQL        PostgreSQL
dino_*            qwen_*
```

DINO:

```text
photo
  ↓
SceneRecognizer
  ↓
best_id
  ↓
address_id
  ↓
dino_fingerprint
dino_score
dino_second_score
dino_margin
dino_status = done
```

И **стоп**.

---

## Hybrid v12 сейчас вообще отдельная система

Единственное найденное место, где реально запускается Hybrid:

```text
scripts/run_daily_hybrid_v12.sh
        ↓
scripts/run_hybrid_v12.py
```

А внутри:

```text
run_recognition()
      ↓
DINO v33
      ↓
top-5
      ↓
Hybrid v12
      ↓
best_id
      ↓
virtual sort
```

То есть Hybrid **не является следующим этапом после `dino_worker.py`**.

---

## И это объясняет твой вопрос про `dino_fingerprint`

Сейчас поле:

```text
dino_fingerprint
```

заполняется вот этим:

```python
dino_fingerprint = address_id
```

а `address_id` = `result["best_id"]`.

То есть название `dino_fingerprint` здесь немного обманчивое.

Это **не DINO embedding/fingerprint**, сохранённый для последующего пересчёта.

Это просто:

```text
DINO best_id
```

Например:

```text
dino_fingerprint = "85_v33"
```

Это идентификатор найденного адресного fingerprint.

---

### А вот production Hybrid делает совсем другое

В твоём `run_hybrid_v12.py`:

```text
DINO v33
   ↓
получает исходные результаты
   ↓
Hybrid использует их
   ↓
проверяет пограничные случаи
   ↓
учитывает subfingerprints
   ↓
учитывает neighbors
   ↓
может изменить best_id
```

Поэтому именно **Hybrid должен быть конечным результатом распознавания**, если мы приняли новую архитектуру.

---

## Значит, сейчас есть архитектурная проблема

У нас одновременно существуют:

**Старая DB-ветка:**

```text
DINO worker → PostgreSQL
```

и

**Новая production-ветка:**

```text
run_hybrid_v12 → DINO + Hybrid → JSON
```

Но они **не соединены**.

И это очень важно, потому что UI уже содержит поля:

```text
hybrid_original_id
hybrid_final_id
hybrid_changed
hybrid_old_score
hybrid_score
hybrid_margin
hybrid_neighbors
```

но найденный код **не показывает процесса, который эти поля заполняет**.

Следовательно, следующий шаг — **найти, существует ли вообще запись `hybrid_*` в PostgreSQL где-нибудь ещё**, потому что наш `grep` показал только чтение этих полей и диагностику, но не `UPDATE photos SET hybrid_...`.

Я бы сейчас проверил именно это одной командой:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID DB WRITES ================" && \
grep -RniE \
'UPDATE[[:space:]]+photos|INSERT INTO photos|hybrid_original_id|hybrid_final_id|hybrid_changed|hybrid_old_score|hybrid_score|hybrid_margin|hybrid_neighbors' \
app scripts \
--include="*.py" \
| grep -vE 'photo_db.py|diagnose_dino_hybrid_db.py' \
| head -500
```

**Если там не будет ни одного `UPDATE` для `hybrid_*`, то Hybrid v12 сейчас вообще не записывает свой результат в PostgreSQL.** Это будет уже точное подтверждение, а не предположение.

---

### 👤 **User** — 2026-08-21 01:26:55

дино воркер является частью ub,hblf&

---

### 🤖 **Assistant** — 2026-08-21 01:26:56

Да — **если под «Hybrid» мы понимаем новую production-цепочку**, то логически DINO worker должен быть её частью.

Но **в текущем коде он частью Hybrid v12 не является**.

Сейчас есть две разные реализации:

```text
DINO WORKER
PostgreSQL
   ↓
dino best_id
```

и отдельно:

```text
run_hybrid_v12.py
   ↓
run_recognition()
   ↓
DINO v33
   ↓
top-5
   ↓
Hybrid v12
   ↓
финальный best_id
```

То есть **DINO-алгоритм внутри Hybrid есть**, но это не `app/workers/dino_worker.py`.

Именно это мы сейчас обнаружили.

Если твоя задумка такая:

```text
ОБРАБОТАТЬ
    ↓
DINO WORKER
    ↓
DINO v33
    ↓
Hybrid v12
    ↓
финальный address_id
    ↓
PostgreSQL
```

то **это правильная целевая архитектура**. Тогда `dino_worker.py` надо не выбрасывать, а переделать так, чтобы его `recognize_one()` был первой частью полного Hybrid-процесса, а в БД сохранялся уже **результат Hybrid**, при этом исходный DINO результат можно хранить отдельно для диагностики/пересчёта.

И я бы **пока ничего не менял**, пока не посмотрим весь `dino_worker.py` и функцию `recognize_one()`. Там станет видно, насколько легко встроить Hybrid внутрь него.

---

### 👤 **User** — 2026-08-21 01:27:53

давайсделаем тест дино воркер и гибрид на 50 фото из инпута - чисто виртуально

---

### 🤖 **Assistant** — 2026-08-21 01:27:57

Да. И здесь как раз надо разделить две вещи:

**DINO worker сам по себе Hybrid v12 не запускает.** По текущему коду он делает:

`PostgreSQL pending → берёт фото → SceneRecognizer.recognize_one(top_k=5) → получает best_id/top5 → пишет результат в PostgreSQL`.

А `run_hybrid_v12.py` — отдельный механизм, который берёт результаты распознавания и применяет Hybrid v12.

Поэтому для теста я предлагаю сделать **полностью виртуальный прогон 50 фотографий**, без:

- записи в PostgreSQL;
- изменения `dino_status`;
- изменения `dino_fingerprint`;
- изменения `address_id`;
- копирования фотографий;
- создания `output/daily/...`;
- изменения реальных данных.

Схема теста:

```text
50 фото из data/input/test
        ↓
виртуальная очередь DINO worker
        ↓
SceneRecognizer
        ↓
DINO top-5
        ↓
Hybrid v12
        ↓
виртуальный результат
        ↓
JSON/CSV отчёт
```

При этом **реальный DINO worker не будем запускать напрямую**, потому что он специально написан как DB-worker и будет работать с PostgreSQL.

### Сначала проверим, как именно Hybrid получает DINO-результаты

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID V12 CORE ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,280p'
```

и отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID V12 MAIN ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '560,675p'
```

**Пока ничего не меняем.**

После этого я смогу сделать тестовый `virtual_dino_hybrid_50.py`, который использует **тот же `SceneRecognizer`, тот же DINO v33 и тот же Hybrid v12**, но вместо PostgreSQL будет виртуальная очередь из 50 файлов.

Это будет гораздо полезнее обычного benchmark: мы проверим именно цепочку

**DINO worker → результат DINO → Hybrid v12**, 

не затрагивая рабочую БД и физические файлы.

---

### 👤 **User** — 2026-08-21 01:29:09

отдельно посмотреть гибрид надо - может дино воркер и не нужен - он может быть частью экперимента или теста или создания слепков

---

### 🤖 **Assistant** — 2026-08-21 01:29:10

Да. **Именно это сейчас и надо выяснить, прежде чем что-либо переделывать.**

По тому, что мы уже увидели, есть серьёзный признак, что `dino_worker.py` — это **не обязательная часть основного Hybrid-пайплайна**, а отдельный DB-worker для фоновой обработки.

Сейчас логически имеются **три разных механизма**:

```text
1. ОСНОВНОЕ РАСПОЗНАВАНИЕ
run_recognition()
    ↓
scene-fingerprint recognize
    ↓
DINO v33
    ↓
top-1 ... top-5

2. ЭКСПЕРИМЕНТ / ТЕСТ HYBRID
DINO results
    ↓
Hybrid v12
    ↓
hybrid_final_id

3. ФОНОВЫЙ DB WORKER
PostgreSQL
    ↓
dino_worker.py
    ↓
SceneRecognizer
    ↓
PostgreSQL
```

И пока **не доказано**, что пункт 3 нужен пункту 1 или 2.

Более того, `dino_worker.py` сейчас **сам не содержит Hybrid v12**. Он вызывает:

```python
result = recognizer.recognize_one(
    source_path,
    top_k=5,
    threshold=0.65,
)
```

и затем сохраняет:

```text
address_id
dino_fingerprint
dino_score
dino_second_score
dino_margin
```

То есть он делает **обычный DINO recognition**, а не Hybrid.

### Поэтому сейчас я бы вообще не трогал DINO worker.

Сначала надо **отдельно разобрать `run_hybrid_v12.py`**:

1. Откуда он получает исходный DINO результат.
2. Сам ли он запускает DINO.
3. Нужен ли ему PostgreSQL.
4. Что именно является входом Hybrid.
5. Как формируется `hybrid_neighbors`.
6. Как формируется `best_id`.
7. Что именно Hybrid меняет относительно `original_best_id`.
8. Можно ли запустить его непосредственно на 50 фото.
9. Можно ли получить полностью виртуальный результат без БД и копирования файлов.

Особенно важен этот момент из твоего результата:

```text
original_best_id: 85_v33
best_id:          85_v33
hybrid_changed:   False
hybrid_neighbors: {'85_v33': 1}
```

То есть Hybrid явно знает про **исходный DINO результат** и поверх него выполняет дополнительную логику.

### Давай сейчас только изучим Hybrid

Выполни сначала:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID V12 STRUCTURE ================" && \
grep -nE \
'^def |^class |recognize|top_k|best_id|original_best_id|hybrid_neighbors|neighbors|subfinger|Fingerprint|SceneRecognizer|PostgreSQL|psycopg|json' \
scripts/run_hybrid_v12.py \
| head -300
```

Потом сам основной кусок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID V12 1-280 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,280p'
```

И затем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID V12 280-680 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '280,680p'
```

После этого уже можно будет точно сказать:

**DINO worker — часть рабочего контура, экспериментальный инструмент, тестовый инструмент или вообще лишний слой.**

И только потом имеет смысл делать наш **виртуальный тест 50 фото**.

---

### 👤 **User** — 2026-08-21 01:30:56

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID V12 STRUCTURE ================" && \
grep -nE \
'^def |^class |recognize|top_k|best_id|original_best_id|hybrid_neighbors|neighbors|subfinger|Fingerprint|SceneRecognizer|PostgreSQL|psycopg|json' \
scripts/run_hybrid_v12.py \
| head -300
================ HYBRID V12 STRUCTURE ================
4:import json
33:def normalize(x):
44:def load_subs():
76:def get_neighbor_votes(rows, index):
96:def run_recognition(input_dir, fingerprints):
98:    Run the existing DINO v33 recognizer.
100:    The recognizer itself is NOT modified.
109:        "recognize",
117:        "--json",
124:    print("Fingerprints:", ", ".join(fingerprints))
143:            f"recognize завершился с кодом {process.returncode}"
148:    decoder = json.JSONDecoder()
165:        except json.JSONDecodeError:
179:def adapt_recognizer_rows(rows):
181:    Convert current recognizer output into the legacy
207:def hybrid_v12(rows, embedder, subs):
212:        recognizer rows containing top1..top5.
215:        rows with final best_id.
303:        neighbors = get_neighbor_votes(
367:        result["original_best_id"] = old
368:        result["best_id"] = best
376:        result["hybrid_neighbors"] = dict(neighbors)
392:                    "neighbors": dict(neighbors),
401:def sort_results(rows, output_dir):
403:    Copy photos according to FINAL Hybrid best_id.
426:            "best_id"
457:                "original_best_id": item.get(
458:                    "original_best_id"
500:def main():
574:    # 2. Load Hybrid subfingerprints
601:    recognition = adapt_recognizer_rows(recognition)
629:            "neighbors:",
630:            item["neighbors"],
651:    recognition_json = (
652:        output_dir / "recognition.json"
655:    hybrid_json = (
656:        output_dir / "hybrid_v12.json"
659:    report_json = (
660:        output_dir / "report.json"
663:    statistics_json = (
664:        output_dir / "statistics.json"
667:    recognition_json.write_text(
668:        json.dumps(
676:    hybrid_json.write_text(
677:        json.dumps(
685:    report_json.write_text(
686:        json.dumps(
708:            "recognizer": "DINOv2 v33",
717:    statistics_json.write_text(
718:        json.dumps(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID V12 1-280 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,280p'
================ HYBRID V12 1-280 ================
     1	#!/usr/bin/env python3
     2	
     3	import argparse
     4	import json
     5	import shutil
     6	import subprocess
     7	import time
     8	from collections import Counter, defaultdict
     9	from pathlib import Path
    10	
    11	import numpy as np
    12	
    13	from app.core.config import Settings
    14	from app.core.embedder import SceneEmbedder
    15	
    16	
    17	PROJECT = Path(__file__).resolve().parent.parent
    18	
    19	SUB_DIR = PROJECT / "data/fingerprints_sub_exp"
    20	
    21	
    22	# ============================================================
    23	# HYBRID V12 — FROZEN CONTROL LOGIC
    24	# ============================================================
    25	
    26	MARGIN_LIMIT = 0.02
    27	
    28	GLOBAL_WEIGHT = 10.0
    29	SUB_WEIGHT = 2.5
    30	NEIGHBOR_WEIGHT = 6.0
    31	
    32	
    33	def normalize(x):
    34	    x = np.asarray(x, dtype=np.float32)
    35	
    36	    n = np.linalg.norm(x)
    37	
    38	    if n > 0:
    39	        x = x / n
    40	
    41	    return x
    42	
    43	
    44	def load_subs():
    45	    result = {}
    46	
    47	    if not SUB_DIR.exists():
    48	        print(f"[Hybrid] WARNING: sub directory not found: {SUB_DIR}")
    49	        return result
    50	
    51	    for d in sorted(SUB_DIR.iterdir()):
    52	
    53	        if not d.is_dir():
    54	            continue
    55	
    56	        f = d / "embeddings.npy"
    57	
    58	        if not f.exists():
    59	            continue
    60	
    61	        emb = np.load(f)
    62	
    63	        emb = np.array(
    64	            [
    65	                normalize(x)
    66	                for x in emb
    67	            ],
    68	            dtype=np.float32,
    69	        )
    70	
    71	        result[d.name] = emb
    72	
    73	    return result
    74	
    75	
    76	def get_neighbor_votes(rows, index):
    77	    votes = Counter()
    78	
    79	    if index <= 0:
    80	        return votes
    81	
    82	    if index >= len(rows) - 1:
    83	        return votes
    84	
    85	    left = rows[index - 1]["top1"]
    86	    right = rows[index + 1]["top1"]
    87	
    88	    # FROZEN V12 RULE:
    89	    # only complete agreement
    90	    if left == right:
    91	        votes[left] = 1
    92	
    93	    return votes
    94	
    95	
    96	def run_recognition(input_dir, fingerprints):
    97	    """
    98	    Run the existing DINO v33 recognizer.
    99	
   100	    The recognizer itself is NOT modified.
   101	    """
   102	
   103	    fp_arg = ",".join(fingerprints)
   104	
   105	    cmd = [
   106	        "uv",
   107	        "run",
   108	        "scene-fingerprint",
   109	        "recognize",
   110	        str(input_dir),
   111	        "--top-k",
   112	        "5",
   113	        "--threshold",
   114	        "0.0",
   115	        "--fingerprints",
   116	        fp_arg,
   117	        "--json",
   118	    ]
   119	
   120	    print("=" * 80)
   121	    print("DINO v33 RECOGNITION")
   122	    print("=" * 80)
   123	    print("Input:", input_dir)
   124	    print("Fingerprints:", ", ".join(fingerprints))
   125	    print()
   126	
   127	    start = time.perf_counter()
   128	
   129	    process = subprocess.run(
   130	        cmd,
   131	        cwd=PROJECT,
   132	        capture_output=True,
   133	        text=True,
   134	    )
   135	
   136	    elapsed = time.perf_counter() - start
   137	
   138	    if process.returncode != 0:
   139	        print(process.stdout)
   140	        print(process.stderr)
   141	
   142	        raise RuntimeError(
   143	            f"recognize завершился с кодом {process.returncode}"
   144	        )
   145	
   146	    combined = process.stdout + "\n" + process.stderr
   147	
   148	    decoder = json.JSONDecoder()
   149	    data = None
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
nt_mvp_v02 && \
echo "================ HYBRID V12 280-680 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '280,680p'
================ HYBRID V12 280-680 ================
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
   421	        source = Path(
   422	            item["file"]
   423	        )
   424	
   425	        assigned_id = item.get(
   426	            "best_id"
   427	        )
   428	
   429	        if not assigned_id:
   430	            continue
   431	
   432	        destination_dir = (
   433	            output_dir / assigned_id
   434	        )
   435	
   436	        destination_dir.mkdir(
   437	            parents=True,
   438	            exist_ok=True,
   439	        )
   440	
   441	        destination = (
   442	            destination_dir / source.name
   443	        )
   444	
   445	        shutil.copy2(
   446	            source,
   447	            destination,
   448	        )
   449	
   450	        counters[assigned_id] += 1
   451	
   452	        sorted_rows.append(
   453	            {
   454	                "file": str(source),
   455	                "filename": source.name,
   456	                "assigned_id": assigned_id,
   457	                "original_best_id": item.get(
   458	                    "original_best_id"
   459	                ),
   460	                "hybrid_changed": item.get(
   461	                    "hybrid_changed"
   462	                ),
   463	                "score": item.get("score"),
   464	                "second_score": item.get(
   465	                    "second_score"
   466	                ),
   467	                "margin": item.get("margin"),
   468	                "confidence": item.get(
   469	                    "confidence"
   470	                ),
   471	                "status": item.get("status"),
   472	                "best_image": item.get(
   473	                    "best_image"
   474	                ),
   475	                "best_image_score": item.get(
   476	                    "best_image_score"
   477	                ),
   478	                "hybrid_old_score": item.get(
   479	                    "hybrid_old_score"
   480	                ),
   481	                "hybrid_score": item.get(
   482	                    "hybrid_score"
   483	                ),
   484	            }
   485	        )
   486	
   487	    for k in sorted(
   488	        counters,
   489	        key=lambda x: int(
   490	            x.split("_")[0]
   491	        ),
   492	    ):
   493	        print(
   494	            f"{k:10s} {counters[k]:4d}"
   495	        )
   496	
   497	    return sorted_rows, counters
   498	
   499	
   500	def main():
   501	
   502	    parser = argparse.ArgumentParser(
   503	        description="Production runner for frozen Hybrid v12"
   504	    )
   505	
   506	    parser.add_argument(
   507	        "--input",
   508	        required=True,
   509	        type=Path,
   510	    )
   511	
   512	    parser.add_argument(
   513	        "--output",
   514	        required=True,
   515	        type=Path,
   516	    )
   517	
   518	    parser.add_argument(
   519	        "--first-address",
   520	        type=int,
   521	        default=78,
   522	    )
   523	
   524	    parser.add_argument(
   525	        "--last-address",
   526	        type=int,
   527	        default=95,
   528	    )
   529	
   530	    args = parser.parse_args()
   531	
   532	    input_dir = args.input
   533	    output_dir = args.output
   534	
   535	    if not input_dir.exists():
   536	        raise RuntimeError(
   537	            f"Нет папки: {input_dir}"
   538	        )
   539	
   540	    fingerprints = [
   541	        f"{i}_v33"
   542	        for i in range(
   543	            args.first_address,
   544	            args.last_address + 1,
   545	        )
   546	    ]
   547	
   548	    print()
   549	    print("=" * 80)
   550	    print("SCENE FINGERPRINT — HYBRID V12 RUNNER")
   551	    print("=" * 80)
   552	    print()
   553	    print("INPUT :", input_dir)
   554	    print("OUTPUT:", output_dir)
   555	    print()
   556	    print("CONTROL:")
   557	    print("  DINO        : v33")
   558	    print("  HYBRID      : v12")
   559	    print("  ADDRESSES   :", f"{args.first_address}-{args.last_address}")
   560	    print()
   561	
   562	    total_start = time.perf_counter()
   563	
   564	    # --------------------------------------------------------
   565	    # 1. DINO
   566	    # --------------------------------------------------------
   567	
   568	    recognition, recognition_time = run_recognition(
   569	        input_dir,
   570	        fingerprints,
   571	    )
   572	
   573	    # --------------------------------------------------------
   574	    # 2. Load Hybrid subfingerprints
   575	    # --------------------------------------------------------
   576	
   577	    print()
   578	    print("=" * 80)
   579	    print("LOADING HYBRID SUBFINGERPRINTS")
   580	    print("=" * 80)
   581	
   582	    subs = load_subs()
   583	
   584	    print("Subfingerprints:", len(subs))
   585	
   586	    # --------------------------------------------------------
   587	    # 3. Hybrid v12
   588	    # --------------------------------------------------------
   589	
   590	    print()
   591	    print("=" * 80)
   592	    print("HYBRID V12")
   593	    print("=" * 80)
   594	
   595	    settings = Settings()
   596	
   597	    embedder = SceneEmbedder(
   598	        settings
   599	    )
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:30:57

Теперь картина стала однозначной.

### Главное

**`dino_worker.py` не является частью Hybrid v12.**

В `scripts/run_hybrid_v12.py` прямо зашит собственный запуск DINO:

```text
run_hybrid_v12.py
        │
        ├── run_recognition()
        │       │
        │       └── uv run scene-fingerprint recognize
        │                 │
        │                 └── DINO v33
        │
        ├── load_subs()
        │
        ├── hybrid_v12()
        │
        └── sort_results()
```

То есть **Hybrid v12 сам запускает DINO recognition**.

Причём это видно непосредственно в строках 96–117:

```text
uv run scene-fingerprint recognize
--top-k 5
--threshold 0.0
--fingerprints 78_v33,...,95_v33
--json
```

А затем результаты этого DINO передаются прямо в:

```text
hybrid_v12(
    recognition,
    embedder,
    subs,
)
```

### Что тогда делает `dino_worker.py`

Он представляет собой **другой контур**:

```text
PostgreSQL
   ↓
dino_status = pending
   ↓
dino_worker.py
   ↓
SceneRecognizer.recognize_one()
   ↓
PostgreSQL
   ↓
dino_status = done
```

То есть это DB-worker для асинхронной обработки фотографий.

Он **не вызывает**:

```text
hybrid_v12()
load_subs()
run_hybrid_v12.py
```

и вообще не знает о Hybrid v12.

---

### Более того, Hybrid уже является полноценным пайплайном

Вот реальная последовательность из твоего файла:

```text
1. INPUT
   data/input/...

        ↓

2. DINO v33
   run_recognition()

        ↓

3. top1 ... top5

        ↓

4. адаптация результата
   adapt_recognizer_rows()

        ↓

5. загрузка subfingerprints

        ↓

6. Hybrid v12
   ├── GLOBAL TOP-5
   ├── SUB для border cases
   ├── SEQUENCE CONSENSUS
   └── FINAL DECISION

        ↓

7. best_id

        ↓

8. sort_results()

        ↓

9. физическое копирование
   output/.../<best_id>/<photo>
```

И это очень важно для нашего дальнейшего решения.

### Что делает Hybrid

У него три источника информации.

**1. Обычный DINO top-5**

Вес:

```text
GLOBAL_WEIGHT = 10.0
```

То есть каждый кандидат из top-5 получает:

```text
score × 10
```

**2. Subfingerprint**

Только если:

```text
margin < 0.02
```

То есть Hybrid **не прогоняет subfingerprint по всем фотографиям**.

Он рассматривает только пограничные случаи.

Причём только:

```text
top1
top2
```

и только subfingerprints соответствующих адресов.

**3. Соседи**

Если:

```text
предыдущее top1 == следующее top1
```

то этому адресу добавляется:

```text
+3.0
```

Это как раз та функция, про которую ты раньше говорил: **смотреть на соседние фотографии и их результаты**.

---

### И самое важное

Финальное решение:

```text
candidate != old
AND
gain > 1.5
```

Только тогда:

```text
best_id = candidate
```

Иначе:

```text
best_id = original top1
```

Поэтому:

```text
original_best_id
```

— это первоначальный DINO top-1,

а:

```text
best_id
```

— окончательное решение Hybrid.

Это абсолютно логично.

---

## Следовательно, архитектурно я бы сейчас разделил

```text
                    ОСНОВНОЙ КОНТУР
                           │
                           ▼
                    run_hybrid_v12.py
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
        DINO v33                  Hybrid v12
     scene-fingerprint             sub + neighbors
             │                           │
             └─────────────┬─────────────┘
                           ▼
                       best_id
                           │
                           ▼
                    виртуальная сортировка
                    ИЛИ физическая сортировка
```

А отдельно:

```text
              DB / BACKGROUND КОНТУР
                       │
                       ▼
                 dino_worker.py
                       │
                       ▼
                  PostgreSQL
```

`dino_worker.py` может быть полезен для **DB-автоматизации**, экспериментов, фоновой обработки или другого режима, но **для нашего Hybrid-пайплайна он не нужен**.

### Поэтому следующий тест лучше делать именно так

Не трогать `dino_worker.py`.

Берём **50 реальных фотографий из `data/input/test`**, запускаем **существующий `run_hybrid_v12.py`**, но убираем/обходим только его физический `sort_results()`.

Получим:

```text
50 фото
 ↓
DINO v33
 ↓
top1..top5
 ↓
Hybrid v12
 ↓
original_best_id
best_id
hybrid_changed
hybrid_margin
hybrid_neighbors
 ↓
JSON/CSV
```

**Никакой PostgreSQL и никакого копирования фотографий.**

Это будет чистый эксперимент над уже существующим настоящим Hybrid v12, а не имитация.

---

### 👤 **User** — 2026-08-21 01:31:59

да

---

### 🤖 **Assistant** — 2026-08-21 01:32:04

Да. Теперь картина уже достаточно ясная, и **DINO worker действительно выглядит отдельной веткой**, а не обязательной частью Hybrid v12.

### Что реально делает Hybrid v12

По `run_hybrid_v12.py` цепочка такая:

```text
50 фото
   │
   ▼
scene-fingerprint recognize
   │
   ▼
DINO v33
   │
   ├── top1
   ├── top2
   ├── top3
   ├── top4
   └── top5
   │
   ▼
Hybrid v12
   │
   ├── Global TOP-5
   ├── Subfingerprints — только margin < 0.02
   └── соседние фото — если left top1 == right top1
   │
   ▼
финальный best_id
   │
   ▼
сортировка
```

Это прямо видно из кода: Hybrid **сам запускает** `scene-fingerprint recognize` на строках 96–176, а затем получает `top1..top5` и обрабатывает их на строках 207–398.

То есть:

> **DINO worker `app/workers/dino_worker.py` для Hybrid v12 вообще не нужен.**

---

### А что делает DINO worker

Он работает по совершенно другой схеме:

```text
PostgreSQL photos
      │
      ▼
dino_status = pending
      │
      ▼
DINO worker
      │
      ▼
recognizer.recognize_one()
      │
      ▼
top-5 / best_id
      │
      ▼
PostgreSQL
dino_status = done
```

Ключевое место:

```python
result = recognizer.recognize_one(
    source_path,
    top_k=5,
    threshold=0.65,
)
```

и потом:

```python
mark_done(
    conn,
    db_id,
    result,
    elapsed,
)
```

То есть worker нужен для **асинхронной обработки очереди фотографий в PostgreSQL**.

А Hybrid — это отдельный экспериментальный/production runner, который работает **файлово**, без PostgreSQL.

---

## Поэтому предлагаю сейчас ничего не менять

Сделаем чистый эксперимент на **50 фотографиях**:

### Тест №1 — DINO worker

Посмотрим:

- сколько фото берет из PostgreSQL;
- какой `best_id` получает;
- какие `top1..top5`;
- сколько времени;
- что именно записывает в БД;
- не делает ли он что-то сверх обычного DINO recognition.

### Тест №2 — Hybrid v12

На **тех же 50 фотографиях**:

```text
DINO v33
   ↓
top1..top5
   ↓
Hybrid v12
   ↓
final best_id
```

И сравним:

```text
PHOTO
DINO best_id
HYBRID best_id
CHANGED?
DINO score
HYBRID score
margin
neighbors
```

Тогда станет абсолютно понятно, нужен ли вообще `dino_worker.py` в основной цепочке.

---

### И особенно важный момент

В Hybrid уже есть **повторный DINO embedding** только для пограничных случаев:

```python
if margin < MARGIN_LIMIT:
```

после чего он смотрит subfingerprints.

То есть Hybrid — это не:

```text
DINO worker → Hybrid
```

а:

```text
Hybrid
 └── внутри себя запускает DINO recognition
       └── потом применяет Hybrid
```

Это принципиально разные архитектуры.

**Следующий шаг я бы сделал именно сравнительный тест 50 фото, ничего в коде не меняя.** Сначала отдельно запускаем Hybrid на 50, затем отдельно проверяем DINO worker на тех же 50 и сравниваем результаты.

---

### 👤 **User** — 2026-08-21 01:32:22

и пробуем запустить dino в гибриде на цпу

---

### 🤖 **Assistant** — 2026-08-21 01:32:23

> **Inspecting Device Configuration and CLI Arguments**
>
>
> **Inspected device configuration and CLI arguments**
>
> 
>
> Worked for 5s

Да. Здесь как раз стоит сделать **чистый эксперимент**, не меняя production-код.

По уже показанному `run_hybrid_v12.py` схема такая:

```text
50 фото
   ↓
scene-fingerprint recognize
   ↓
DINO v33
   ↓
top1..top5
   ↓
Hybrid v12
   ├─ global TOP-5
   ├─ subfingerprints для border cases
   └─ соседние фото
   ↓
final best_id
```

И важный момент: **`dino_worker.py` в этот эксперимент вообще не нужен**. Hybrid v12 сам запускает `scene-fingerprint recognize` через `run_recognition()`.

Чтобы проверить именно **DINO внутри Hybrid на CPU**, сначала надо увидеть, как в проекте задаётся `device`. Выполни на своей машине:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DEVICE CONFIG ================" && \
grep -RniE \
'device.*cuda|device.*cpu|DEVICE|CUDA_VISIBLE_DEVICES|settings.device' \
app/core app \
--include="*.py" \
| head -120
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID SETTINGS ================" && \
nl -ba app/core/config.py | sed -n '1,220p'
```

После этого я дам **точную команду на 50 фотографий**, которая:

- не трогает БД;
- не запускает `dino_worker`;
- не запускает Qwen;
- запускает именно `Hybrid v12`;
- заставляет DINO работать на CPU;
- сохраняет результат в отдельную тестовую папку;
- позволит отдельно сравнить **DINO top1** и **Hybrid final best_id**.

Это будет как раз хороший тест, чтобы понять, **нужен ли вообще `dino_worker.py` для рабочего Hybrid-пайплайна**, или он действительно является отдельным техническим/экспериментальным механизмом.

---

### 👤 **User** — 2026-08-21 01:32:55

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DEVICE CONFIG ================" && \
grep -RniE \
'device.*cuda|device.*cpu|DEVICE|CUDA_VISIBLE_DEVICES|settings.device' \
app/core app \
--include="*.py" \
| head -120
================ DEVICE CONFIG ================
app/core/config.py:16:    device: str = os.getenv(
app/core/config.py:17:        "SCENE_DEVICE",
app/core/embedder.py:20:        self.device = torch.device(settings.device)
app/core/embedder.py:22:        print(f"[SceneEmbedder] device={self.device}")
app/core/embedder.py:24:        if self.device.type == "cuda":
app/core/embedder.py:27:                f"{torch.cuda.get_device_name(0)}"
app/core/embedder.py:31:                f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
app/core/embedder.py:49:        self.model = self.model.to(self.device)
app/core/embedder.py:93:                    self.device,
app/core/config.py:16:    device: str = os.getenv(
app/core/config.py:17:        "SCENE_DEVICE",
app/core/embedder.py:20:        self.device = torch.device(settings.device)
app/core/embedder.py:22:        print(f"[SceneEmbedder] device={self.device}")
app/core/embedder.py:24:        if self.device.type == "cuda":
app/core/embedder.py:27:                f"{torch.cuda.get_device_name(0)}"
app/core/embedder.py:31:                f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
app/core/embedder.py:49:        self.model = self.model.to(self.device)
app/core/embedder.py:93:                    self.device,
app/workers/dino_worker.py:232:    print("device  :", settings.device)
app/ocr/ocr_pipeline.py:38:        print("[OCR] Ready. Device=CPU")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID SETTINGS ================" && \
nl -ba app/core/config.py | sed -n '1,220p'
================ HYBRID SETTINGS ================
     1	from dataclasses import dataclass
     2	from pathlib import Path
     3	import os
     4	import torch
     5	
     6	
     7	@dataclass(frozen=True)
     8	class Settings:
     9	    host: str = os.getenv("SCENE_HOST", "127.0.0.1")
    10	    port: int = int(os.getenv("SCENE_PORT", "8080"))
    11	    data_dir: Path = Path(os.getenv("SCENE_DATA", "data"))
    12	    model_name: str = os.getenv(
    13	        "SCENE_MODEL",
    14	        "facebook/dinov2-base"
    15	    )
    16	    device: str = os.getenv(
    17	        "SCENE_DEVICE",
    18	        "cuda" if torch.cuda.is_available() else "cpu"
    19	    )
    20	    batch_size: int = int(
    21	        os.getenv(
    22	            "SCENE_BATCH",
    23	            "16"
    24	        )
    25	    )
    26	
    27	    @property
    28	    def fingerprints_dir(self):
    29	        return Path(
    30	            os.getenv(
    31	                "SCENE_FINGERPRINTS",
    32	                str(self.data_dir / "fingerprints")
    33	            )
    34	        )
    35	
    36	
    37	settings = Settings()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:32:56

Да. Теперь всё ясно: **CPU можно включить без изменения кода** через `SCENE_DEVICE=cpu`.

И для нашего теста я предлагаю **не запускать `dino_worker.py` вообще**. Проверяем именно самостоятельный Hybrid v12.

### Тест 50 фото: DINO внутри Hybrid → CPU

Сначала создадим отдельную папку с 50 фото из `data/input/daily`, не трогая оригинал:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
rm -rf data/test_hybrid_cpu_50 data/output/test_hybrid_cpu_50 && \
mkdir -p data/test_hybrid_cpu_50 data/output/test_hybrid_cpu_50 && \
find data/input/daily -maxdepth 1 -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  | sort | head -50 \
  | while read f; do cp "$f" data/test_hybrid_cpu_50/; done && \
echo "TEST PHOTOS:" && \
find data/test_hybrid_cpu_50 -type f | wc -l
```

Потом запускаем **только Hybrid v12**, принудительно на CPU:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
SCENE_DEVICE=cpu \
SCENE_BATCH=4 \
uv run python scripts/run_hybrid_v12.py \
  --input data/test_hybrid_cpu_50 \
  --output data/output/test_hybrid_cpu_50 \
  --first-address 78 \
  --last-address 95
```

### Что реально произойдёт

Первая стадия:

```text
DINO v33 RECOGNITION
        ↓
scene-fingerprint recognize
        ↓
50 фотографий
        ↓
top1
top2
top3
top4
top5
```

Причём здесь DINO работает **на CPU**, потому что:

```text
SCENE_DEVICE=cpu
```

Затем Hybrid:

```text
top1..top5
     ↓
GLOBAL TOP-5
     ↓
margin < 0.02 ?
     ↓ да
subfingerprints
     ↓
соседи слева/справа
     ↓
FINAL best_id
```

И самое главное — этот запуск **не использует PostgreSQL** и **не использует `dino_worker.py`**.

---

### Что нам даст эксперимент

В конце у нас будут отдельно:

```text
data/output/test_hybrid_cpu_50/
├── recognition.json
├── hybrid_v12.json
├── report.json
└── statistics.json
```

То есть можно будет проверить:

```text
DINO top1
      ↓
      └── изменился Hybrid?
              ↓
        final best_id
```

Особенно интересны строки:

```text
original_best_id
best_id
hybrid_changed
margin
hybrid_old_score
hybrid_score
hybrid_neighbors
```

Если, например:

```text
DINO:
top1 = 83_v33

Hybrid:
original_best_id = 83_v33
best_id          = 85_v33
hybrid_changed   = true
```

значит **Hybrid действительно выполняет дополнительную работу после DINO**.

А если почти все:

```text
original_best_id == best_id
```

то Hybrid в основном подтверждает исходный DINO результат.

И тогда уже можно отдельно сравнить:

**`DINO worker` → PostgreSQL → DB**

против

**`Hybrid v12` → DINO recognition → Hybrid → final best_id**

и решить, нужен ли `dino_worker.py` вообще в основном рабочем процессе.

**Пока код не меняем.** Сначала этот CPU-тест — это наиболее чистый способ разобраться в архитектуре.

---

### 👤 **User** — 2026-08-21 01:33:17

можно просто взять перые 150 фото

---

### 🤖 **Assistant** — 2026-08-21 01:33:17

Да. Даже лучше — **первые 150**, без дополнительной выборки.

Создаём тестовую копию:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
rm -rf data/test_hybrid_cpu_150 data/output/test_hybrid_cpu_150 && \
mkdir -p data/test_hybrid_cpu_150 data/output/test_hybrid_cpu_150 && \
find data/input/daily -maxdepth 1 -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  | sort | head -150 \
  | while read f; do cp "$f" data/test_hybrid_cpu_150/; done && \
echo "TEST PHOTOS:" && \
find data/test_hybrid_cpu_150 -type f | wc -l
```

Должно показать:

```text
TEST PHOTOS:
150
```

Затем запускаем **Hybrid v12, где DINO внутри Hybrid работает на CPU**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
SCENE_DEVICE=cpu \
SCENE_BATCH=4 \
uv run python scripts/run_hybrid_v12.py \
  --input data/test_hybrid_cpu_150 \
  --output data/output/test_hybrid_cpu_150 \
  --first-address 78 \
  --last-address 95
```

Это важный тест именно для нашего вопроса:

> **нужен ли отдельный `dino_worker.py`, или DINO является просто вычислительным этапом Hybrid/эксперимента?**

После запуска **не надо пока ничего менять**. Пришли весь вывод от:

```text
DINO v33 RECOGNITION
```

до конца.

По нему отдельно разберём:

1. сколько времени занял DINO на CPU;
2. сколько было `Border cases`;
3. сколько `Hybrid changes`;
4. какие именно

---

### 👤 **User** — 2026-08-21 01:33:24

первые 50

---

### 🤖 **Assistant** — 2026-08-21 01:33:24

Да, делаем **первые 50 фото**.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
rm -rf data/test_hybrid_cpu_50 data/output/test_hybrid_cpu_50 && \
mkdir -p data/test_hybrid_cpu_50 data/output/test_hybrid_cpu_50 && \
find data/input/daily -maxdepth 1 -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  | sort | head -50 \
  | while read f; do cp "$f" data/test_hybrid_cpu_50/; done && \
echo "TEST PHOTOS:" && \
find data/test_hybrid_cpu_50 -type f | wc -l
```

Потом:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
SCENE_DEVICE=cpu \
SCENE_BATCH=4 \
uv run python scripts/run_hybrid_v12.py \
  --input data/test_hybrid_cpu_50 \
  --output data/output/test_hybrid_cpu_50 \
  --first-address 78 \
  --last-address 95
```

Это **не запускает `dino_worker.py`**. Запускается `run_hybrid_v12.py`, а внутри него DINO v33 работает на CPU.

После выполнения пришли вывод целиком — посмотрим, что именно делает DINO внутри Hybrid и насколько вообще нужен отдельный DINO worker.

---

### 👤 **User** — 2026-08-21 01:34:20

Checked: 50
Border cases: 4
Hybrid changes: 1

Ашхабадский_08.JPG
89_v33 -> 85_v33
margin: 0.010599818229675262
neighbors: {'85_v33': 1}

================================================================================
SORTING
================================================================================
82_v33        9
85_v33       18
89_v33        2
92_v33        5
95_v33       16

================================================================================
DONE
================================================================================

Images: 50
Hybrid changes: 1
Recognition: 18.54 sec
Total:       21.08 sec

Output:
data/output/test_hybrid_cpu_50
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:34:22

Да - тест очень показательный.

### Что получилось

На **50 фото**:

| Этап | Результат |
|---|---:|
| DINO v33 recognition | 18.54 сек |
| Hybrid v12 | ~2.54 сек |
| Всего | 21.08 сек |
| Border cases | 4 |
| Изменений Hybrid | **1** |

Главное:

```text
Ашхабадский_08.JPG
DINO:    89_v33
Hybrid:  85_v33
```

Причём Hybrid поменял решение **не произвольно**:

```text
margin = 0.0106 < 0.02
```

то есть фотография попала в пограничный случай.

И соседний консенсус:

```text
neighbors: {'85_v33': 1}
```

поддержал `85_v33`.

### Что это доказывает

Получается очень чистая цепочка:

```text
DINO v33
   │
   │ 50 фото
   ▼
top1..top5
   │
   ├── 46 обычных случаев
   │
   └── 4 border cases
          │
          ▼
      Hybrid v12
          │
          └── 1 изменение
                │
                ▼
          89_v33 → 85_v33
```

То есть **Hybrid действительно является следующим этапом после DINO**, а не отдельным параллельным распознавателем.

И ещё важнее: из 50 фотографий Hybrid изменил только **1 результат (2%)**.

### А `dino_worker.py` здесь не участвовал вообще

И результат получен:

```text
run_hybrid_v12.py
    ↓
scene-fingerprint recognize
    ↓
DINO v33
    ↓
Hybrid v12
```

Причём весь DINO recognition на CPU занял всего:

**18.54 секунды на 50 фото ≈ 0.37 сек/фото.**

Это очень полезный результат.

---

### Теперь я бы сделал следующий тест

Не надо пока трогать код.

Нужно посмотреть **одну конкретную фотографию `Ашхабадский_08.JPG` подробно**:

```text
DINO top1
DINO top2
DINO top3
DINO top4
DINO top5
scores
margin
subfingerprint contribution
neighbor contribution
global contribution
финальный score
```

Тогда мы точно увидим, **почему Hybrid перекинул 89 → 85**.

И после этого уже можно будет сказать, какую реальную функцию выполняет Hybrid и нужен ли где-нибудь `dino_worker.py`.

Если хочешь, следующим шагом достанем из `hybrid_v12.json` **полный расчёт именно для `Ашхабадский_08.JPG`**.

---

### 👤 **User** — 2026-08-21 01:34:53

### `dino_worker.py` здесь не участвовал вообще

И результат получен:  не трогаем Дино33

---

### 🤖 **Assistant** — 2026-08-21 01:34:54

Да, **DINO v33 не трогаем вообще**.

Фиксируем текущий вариант как контрольный:

```text
DINO v33
   ↓
top1..top5
   ↓
Hybrid v12
   ↓
best_id
```

`scene-fingerprint recognize` остаётся **как есть**.

Не меняем:

- DINO v33;
- `SceneRecognizer`;
- fingerprints `*_v33`;
- `top1..top5`;
- порог/логику текущего recognition;
- Hybrid v12.

А `dino_worker.py` пока просто рассматриваем как **отдельный механизм**, который не участвует в этом пайплайне.

Следующий анализ лучше делать уже **поверх этого неизменяемого DINO v33** — разобрать, что именно Hybrid добавляет к его результату.

---

### 👤 **User** — 2026-08-21 01:35:23

гибрид - вполне раборчий пайплайн не стоит его трогать

---

### 🤖 **Assistant** — 2026-08-21 01:35:24

Согласен. **Hybrid v12 тоже не трогаем.**

Фиксируем как рабочий, проверенный пайплайн:

```text
INPUT
  ↓
DINO v33
  ↓
TOP-5
  ↓
HYBRID v12
  ├─ Global TOP-5
  ├─ Subfingerprints для border cases
  └─ соседний консенсус
  ↓
FINAL best_id
  ↓
SORT
```

Тест на 50 фото это подтвердил:

- **50** обработано;
- **4** пограничных случая;
- **1** изменение DINO → Hybrid;
- Hybrid отработал без ошибок;
- весь CPU-тест — **21.08 сек**.

Поэтому сейчас правильная стратегия — **не оптимизировать и не переписывать рабочую часть**, а разобраться с отдельным `dino_worker.py`.

То есть дальше вопрос только такой:

> **Зачем в проекте существует `dino_worker.py` и нужен ли он вообще для текущей системы?**

Его можно исследовать отдельно, не касаясь **DINO v33 + Hybrid v12**.

---

### 👤 **User** — 2026-08-21 01:35:39

Зачем в проекте существует `dino_worker.py` и нужен ли он вообще для текущей системы?

---

### 🤖 **Assistant** — 2026-08-21 01:35:41

Да. По тому коду, который мы уже посмотрели, ответ довольно чёткий.

## Зачем существует `dino_worker.py`

`dino_worker.py` — это **фоновый DB-worker для PostgreSQL**, а не часть Hybrid v12.

Его задача:

```text id="y3b1du"
PostgreSQL
   ↓
photos.dino_status = pending
   ↓
dino_worker.py
   ↓
SceneRecognizer.recognize_one()
   ↓
DINO v33
   ↓
результат
   ↓
PostgreSQL
   ↓
dino_status = done
```

Он нужен, если система хочет работать в режиме:

> «В БД появилась фотография → фоновый процесс сам её распознал → результат записал обратно в БД».

То есть это **очередь фоновой обработки**.

---

## А текущий рабочий Hybrid работает иначе

У нас уже проверено:

```text id="q1j2w5"
фотографии
    ↓
run_hybrid_v12.py
    ↓
scene-fingerprint recognize
    ↓
DINO v33
    ↓
top1..top5
    ↓
Hybrid v12
    ↓
best_id
    ↓
сортировка
```

И здесь **PostgreSQL не нужен для самого распознавания**.

Мы только что реально прогнали 50 фотографий:

```text
Images: 50
Recognition: 18.54 sec
Hybrid changes: 1
Total: 21.08 sec
```

`dino_worker.py` в этом процессе вообще не участвовал.

---

# Поэтому нужен ли он?

### Для текущего Hybrid-пайплайна — **нет**.

Если основной процесс системы теперь:

```text
фото → DINO v33 → Hybrid v12 → best_id → сортировка
```

то `dino_worker.py` становится **лишним промежуточным механизмом**.

Он не добавляет ничего к Hybrid:

- не делает Hybrid;
- не загружает subfingerprints;
- не делает соседний анализ;
- не улучшает `best_id` после DINO;
- не нужен для запуска `run_hybrid_v12.py`.

---

## Но удалять его пока не надо

Я бы пока оставил его в проекте.

Потому что у него есть потенциальное назначение для **другого режима работы**:

```text
WEB / PostgreSQL
       ↓
новые фотографии
       ↓
очередь
       ↓
dino_worker
       ↓
DB результат
```

То есть это не «плохой» код. Просто он решает **другую задачу**.

И у тебя в проекте действительно есть DB-поля:

```text id="4o7w8p"
dino_status
dino_started_at
dino_error
...
```

и recovery-механизм:

```text id="0j3b9q"
PROCESSING → PENDING
```

Это явно показывает, что `dino_worker.py` создавался как самостоятельный **асинхронный DB pipeline**.

---

# А вот здесь есть интересный архитектурный вопрос

Сейчас получается два разных DINO-контура:

### Контур A — рабочий

```text id="8h1hpo"
DINO v33
   ↓
Hybrid v12
   ↓
best_id
```

### Контур B — старый/альтернативный

```text id="09c1n7"
DINO worker
   ↓
PostgreSQL
   ↓
dino_status
   ↓
результат DINO
```

И **контур B не продолжает обработку до Hybrid**.

Это означает, что если текущая задача системы — **получить окончательный адрес `best_id`**, то DB DINO-worker действительно выглядит как незавершённая/параллельная ветка.

---

## Мой вывод

**Не трогаем DINO v33.**

**Не трогаем Hybrid v12.**

А `dino_worker.py` пока классифицируем так:

> **отдельный DB/фоновой worker, исторически или экспериментально созданный для асинхронного DINO-распознавания фотографий через PostgreSQL.**

Для нынешнего рабочего конвейера:

> **DINO worker не нужен.**

Но перед удалением я бы сделал ещё одну проверку: **кто вообще запускает `dino_worker.py` и кто читает записанные им `dino_*` поля**.

Если окажется, что текущая Web-система нигде реально не использует этот результат — тогда уже можно будет спокойно признать его **мёртвой/старой веткой**, а не частью основной архитектуры.

---

### 👤 **User** — 2026-08-21 01:35:54

наверно это часть эксперименнта

---

### 🤖 **Assistant** — 2026-08-21 01:35:55

Да, **по всему, что мы сейчас увидели, это очень похоже на экспериментальную/промежуточную ветку**.

Особенно показательно:

- `dino_worker.py` работает через PostgreSQL-очередь `pending → processing → done`;
- `supervisor.py` запускает DINO и Qwen как независимые workers;
- при этом рабочий `Hybrid v12` вообще построен иначе;
- Hybrid сам запускает **DINO v33 recognition**, получает TOP-5 и затем применяет свою логику;
- наш реальный тест 50 фото подтвердил, что **DINO v33 + Hybrid v12 уже является самостоятельным рабочим конвейером**.

Поэтому я бы сейчас обозначил архитектуру так:

```text
                         ОСНОВНОЙ РАБОЧИЙ ПАЙПЛАЙН
                                      │
                                      ▼
                              DINO v33 recognize
                                      │
                                      ▼
                                  Hybrid v12
                                      │
                                      ▼
                              FINAL best_id
                                      │
                                      ▼
                                  SORTING

ЭКСПЕРИМЕНТАЛЬНАЯ ВЕТКА
                                      │
                                      ▼
                               dino_worker.py
                                      │
                                      ▼
                                PostgreSQL
                           pending → processing → done
```

И **ничего из экспериментальной ветки пока не удаляем**.

Следующий правильный шаг — не менять код, а просто выяснить **историю и назначение `dino_worker.py` по проекту**: кто его запускает, какие поля БД он заполняет и кто эти поля потом читает.

Тогда мы окончательно разделим:

**рабочее → эксперимент → старый код**,  
не рискуя сломать текущий DINO v33 + Hybrid v12.

---

### 👤 **User** — 2026-08-21 01:36:33

возможно дино воркер не законченное встраивание гибрида в систему

---

### 🤖 **Assistant** — 2026-08-21 01:36:33

Да, **это вполне возможно**, и по текущему коду эта гипотеза даже выглядит правдоподобнее, чем просто «мёртвый код».

Сейчас видно промежуточное состояние:

```text id="k6j7pz"
DINO worker
    ↓
PostgreSQL
    ↓
dino_status = done
    ↓
результат DINO
```

Но дальше **нет шага**:

```text
DINO result
    ↓
Hybrid v12
    ↓
final best_id
```

При этом отдельный `run_hybrid_v12.py` уже полностью умеет делать:

```text id="8s7f4c"
DINO v33
   ↓
TOP-5
   ↓
Hybrid v12
   ├── global
   ├── subfingerprints
   └── neighbors
   ↓
final best_id
```

Поэтому действительно может быть, что `dino_worker.py` — это **заготовка для интеграции Hybrid в серверный/БД-пайплайн**, которая осталась недоделанной.

### Тогда архитектура могла планироваться примерно так

```text id="q5m8rz"
                     WEB / PostgreSQL
                           │
                           ▼
                    очередь фотографий
                           │
                           ▼
                     DINO WORKER
                           │
                           ▼
                     DINO v33 TOP-5
                           │
                           ▼
                      HYBRID v12
                           │
                           ▼
                    FINAL best_id
                           │
                           ▼
                      PostgreSQL
```

А сейчас реально закончена только первая часть:

```text id="v3j6sc"
PostgreSQL → DINO worker → PostgreSQL
```

и отдельно закончена экспериментальная:

```text id="n2k8qa"
файлы → DINO v33 → Hybrid v12 → сортировка
```

### Поэтому пока я бы не называл `dino_worker.py` ненужным

Лучше считать его:

> **кандидатом на серверную интеграцию DINO + Hybrid, возможно оставшимся от незавершённого этапа разработки.**

И это легко проверить без изменений.

Нужно найти **все места, где результат `dino_worker` должен переходить дальше** — особенно `mark_done()`, поля `hybrid_original_id`, `hybrid_final_id`, `sort_status` и запуск workers.

Вот это уже даст нам ответ: **был ли Hybrid задуман как следующий этап после DINO worker** или worker действительно создавался для отдельного эксперимента.

---

### 👤 **User** — 2026-08-21 01:37:16

надо заменить дино воркер на гибрид везде где он есть - от автоматизации и вотчера, в ручном азпуске, в стаитстике и т.п. И сделать его запуск на Цпу

---

