## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-20 23:30:06

420	
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,155p'
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:30:07

Отлично. Теперь уже видно, как старая связка была устроена.

### Что делает старый Hybrid

`run_hybrid_v12.py` **сам запускал DINO v33**:

```text
run_hybrid_v12.py
        ↓
uv run scene-fingerprint recognize
        ↓
JSON top-5
        ↓
adapt_recognizer_rows()
        ↓
Hybrid v12
```

То есть Hybrid не получал данные напрямую из `dino_worker.py`. Он **повторно запускал recognition на той же папке**.

А текущий `dino_worker.py` работает иначе:

```text
photo
 ↓
recognizer.recognize_one()
 ↓
результат
 ↓
PostgreSQL
```

Поэтому сейчас у нас есть два разных механизма:

**Старый production/test runner:**

```text
папка → DINO → Hybrid → Sort
```

**Новый DB pipeline:**

```text
photo → DINO → PostgreSQL
```

И это объясняет, почему мы нигде не нашли вызов Hybrid внутри worker.

### Важный вывод

Нам **не нужно переделывать Hybrid под DINO worker прямо сейчас**.

Есть гораздо более безопасный путь:

```text
INGEST
 ↓
DINO worker
 ↓
PostgreSQL
 ↓
когда партия DINO закончена
 ↓
Hybrid v12
 ↓
обновление hybrid_* в PostgreSQL
 ↓
Sort
 ↓
Preview
```

То есть Hybrid остаётся отдельным этапом pipeline, но запускается **после завершения DINO**, а не как отдельное независимое распознавание.

Это очень хорошо соответствует твоему замечанию:

> Hybrid — часть DINO.

Функционально — да. Технически — это **последующая стадия DINO recognition**.

---

### Но есть один нюанс

Старый Hybrid сейчас получает соседей из:

```python
rows[index - 1]
rows[index + 1]
```

То есть порядок фотографий **критически важен**.

В DB-варианте нельзя просто обработать фотографии в произвольном порядке и потом запускать Hybrid по отдельным строкам. Нужно сохранить порядок входной партии.

И именно поэтому я бы сейчас посмотрел, **как ingest формирует порядок и `photo_id`**, прежде чем писать интеграцию.

Следующая команда:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba scripts/photo_ingest.py | sed -n '200,330p'
```

Она покажет участок, где фотографии получают `photo_id`, `initial_id` и попадают в DB. После этого уже можно будет спроектировать точную цепочку:

**INGEST → DINO → Hybrid → Sort → Preview**, не ломая соседнюю логику Hybrid.

---

### 👤 **User** — 2026-08-20 23:31:17

что DINO  WORKER Пишет в ПСКЛ?

---

### 🤖 **Assistant** — 2026-08-20 23:31:17

Сейчас `DINO worker` пишет в PostgreSQL таблицу `photos`.

После успешного распознавания он обновляет **одну конкретную фотографию**:

```text
dino_status          = 'done'
address_id           = DINO best_id
dino_fingerprint     = DINO best_id
dino_score           = score
dino_second_score    = second_score
dino_margin          = margin
dino_time_sec        = время обработки
error_message        = NULL
updated_at           = CURRENT_TIMESTAMP
```

Это видно непосредственно из `mark_done()`.

### Что важно

Сейчас DINO **не пишет в PostgreSQL**:

- `hybrid_original_id`
- `hybrid_final_id`
- `hybrid_changed`
- `hybrid_old_score`
- `hybrid_score`
- `hybrid_margin`
- `hybrid_neighbors`
- `sort_status`

То есть PostgreSQL сейчас хранит **результат первичного DINO**, но не окончательный Hybrid.

При этом:

```text
address_id = DINO best_id
dino_fingerprint = DINO best_id
```

`dino_fingerprint` оставлен как старое поле совместимости.

### Поэтому текущая модель фактически такая

```text
                 PostgreSQL photos
                       │
                       ▼
                    DINO
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
     address_id              dino_score
     (DINO result)           dino_margin
                              dino_status=done
```

А **Hybrid-поля уже предусмотрены в БД**, но текущий DINO worker их не заполняет.

И это, скорее всего, следующий участок, который нам надо восстановить: **Hybrid должен взять сохранённые DINO результаты, принять окончательное решение и записать его в эти `hybrid_*` поля**, после чего уже делать сортировку и preview.

Если хочешь, следующим шагом можем посмотреть **структуру таблицы `photos` целиком** и точно определить, какие поля уже подготовлены под эту цепочку.

---

### 👤 **User** — 2026-08-20 23:31:59

гибриду фото не нужны - он рабюотает уже с полями в ПСКЛ

---

### 🤖 **Assistant** — 2026-08-20 23:31:59

Да. **И это принципиально меняет схему.** Ты прав: если текущий Hybrid должен работать с уже записанными результатами DINO в PostgreSQL, то ему **не нужно повторно получать фотографии для обычного Global/Neighbor этапа**.

Но есть одно исключение: в показанном `hybrid_v12()` есть этот участок:

```python
if margin < MARGIN_LIMIT:
    image = Path(row["file"])
    query = embedder.embed_paths([image])[0]
```

То есть **текущий frozen-код Hybrid для SUB border cases всё-таки обращается к файлу фотографии**, чтобы получить embedding.

Поэтому надо разделить:

### Основной Hybrid

```text
DINO worker
   ↓
PostgreSQL
   ↓
top1
top2
top3
top4
top5
scores
margin
   ↓
Hybrid
   ↓
final_id
```

Фото здесь **не нужны**.

### SUB для border cases

Только если:

```text
margin < 0.02
```

тогда frozen Hybrid v12 делает дополнительный embedding исходного изображения:

```text
PostgreSQL
   ↓
margin < 0.02
   ↓
source_path
   ↓
DINO embedding
   ↓
SUB comparison
```

И это тоже уже не «повторное распознавание». Это **дополнительная проверка только пограничных случаев**.

---

### И здесь я бы ничего пока не менял

Нам надо сначала выяснить, **что именно DINO worker сейчас сохраняет из `candidates`**.

Потому что в `mark_done()` он сохраняет только:

```text
best_id
score
second_score
margin
```

А Hybrid требует:

```text
top1
top1_score
top2
top2_score
top3
top3_score
top4
top4_score
top5
top5_score
```

Если эти данные **уже есть в PostgreSQL в других полях** — отлично, просто используем их.

Если их нет — вот тогда DINO worker надо дополнить сохранением top-5.

**Следующий шаг — посмотреть схему `photos`.** Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'CREATE TABLE.*photos|ALTER TABLE.*photos|dino_score|dino_second_score|dino_margin|hybrid_original_id|hybrid_final_id' \
app scripts \
--include="*.py" \
--include="*.sql" \
--include="*.sh" | \
grep -vE '__pycache__|benchmark'
```

Тогда мы точно увидим, **какие DINO-поля уже есть в PostgreSQL и куда Hybrid должен писать результат**.

---

### 👤 **User** — 2026-08-20 23:32:55

по идее связка дино гибрид была рабочая alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'CREATE TABLE.*photos|ALTER TABLE.*photos|dino_score|dino_second_score|dino_margin|hybrid_original_id|hybrid_final_id' \
app scripts \
--include="*.py" \
--include="*.sql" \
--include="*.sh" | \
grep -vE '__pycache__|benchmark'
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/photo_db.py:45:            dino_score,
app/web/photo_db.py:46:            dino_second_score,
app/web/photo_db.py:47:            dino_margin,
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/workers/dino_worker.py:158:                dino_score = %s,
app/workers/dino_worker.py:159:                dino_second_score = %s,
app/workers/dino_worker.py:160:                dino_margin = %s,
scripts/import_qwen_to_db.py:39:        CREATE TABLE IF NOT EXISTS photos (
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:32:56

Да. И по тому, что мы сейчас нашли, **логика действительно выглядит так, что связку DINO → Hybrid можно и нужно было строить через PostgreSQL**, без повторного чтения фотографий Hybrid'ом.

Сейчас картина такая:

**DINO Worker** пишет в `photos`:

- `dino_status = 'done'`
- `address_id`
- `dino_fingerprint`
- `dino_score`
- `dino_second_score`
- `dino_margin`
- `dino_time_sec`

То есть после завершения DINO в PostgreSQL уже есть результат распознавания и данные для дальнейшего решения.

А вот найденный `scripts/run_hybrid_v12.py` — это **старый/отдельный файловый Hybrid**, который:

1. сам запускает `scene-fingerprint recognize`;
2. получает `top1..top5`;
3. **снова читает фотографии** для border cases через:
   `embedder.embed_paths([image])`;
4. применяет Hybrid v12;
5. сортирует файлы.

То есть это **не тот вариант связки, который нам сейчас нужен**.

### Что логично сделать

Зафиксировать архитектуру:

```text
PHOTO
  ↓
DINO WORKER
  ↓
PostgreSQL.photos
  ├── dino_status
  ├── address_id
  ├── dino_fingerprint
  ├── dino_score
  ├── dino_second_score
  └── dino_margin
        ↓
     HYBRID
        ↓
PostgreSQL.photos
  ├── hybrid_original_id
  ├── hybrid_final_id
  ├── hybrid_changed
  ├── hybrid_old_score
  ├── hybrid_score
  └── hybrid_margin / neighbors
```

И тогда **Hybrid вообще не должен получать `input_dir` и не должен повторно вычислять DINO**.

Причём это хорошо согласуется с тем, что у тебя уже есть в `photo_db.py`:

```text
hybrid_original_id
hybrid_final_id
hybrid_changed
```

То есть поля под такую архитектуру **уже предусмотрены**.

Но прежде чем что-либо менять, я бы сейчас **не трогал рабочий DINO**. Следующий шаг — найти старую реализацию Hybrid, которая раньше действительно брала результаты DINO из PostgreSQL, и восстановить именно эту связку, а не переделывать `run_hybrid_v12.py` вслепую.

Нужно найти, **кто сейчас/раньше писал `hybrid_original_id` и `hybrid_final_id`**. Это даст нам точку восстановления старой рабочей цепочки.

---

### 👤 **User** — 2026-08-20 23:33:34

давай

---

### 🤖 **Assistant** — 2026-08-20 23:33:35

Да. Идём от существующего кода, ничего пока не меняем.

Нужно найти **любую старую запись `hybrid_*` в PostgreSQL** и код, который её обновлял.

Выполни:

```bash id="z2z7j7"
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'UPDATE photos|INSERT INTO photos|hybrid_original_id|hybrid_final_id|hybrid_changed|hybrid_old_score|hybrid_score|hybrid_margin|hybrid_neighbors' \
app scripts \
--include="*.py" \
--include="*.sql" \
--include="*.sh" | \
grep -vE '__pycache__|benchmark|export_visual'
```

Особенно нас интересует, появится ли что-нибудь вроде:

```text
UPDATE photos
SET hybrid_original_id = ...
```

или функция типа:

```text
run_hybrid(...)
process_hybrid(...)
mark_hybrid_done(...)
```

**Не запускаем Hybrid и ничего не редактируем.** Просто пришли вывод.

---

### 👤 **User** — 2026-08-20 23:33:53

app scripts \
--include="*.py" \
--include="*.sql" \
--include="*.sh" | \
grep -vE '__pycache__|benchmark|export_visual'
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/web/photo_db.py:50:            hybrid_changed,
app/web/photo_db.py:51:            hybrid_old_score,
app/web/photo_db.py:52:            hybrid_score,
app/web/photo_db.py:53:            hybrid_margin,
app/web/photo_db.py:54:            hybrid_neighbors,
app/pipeline/recovery.py:52:                UPDATE photos
app/pipeline/recovery.py:68:                UPDATE photos
app/workers/qwen_worker.py:194:            UPDATE photos
app/workers/qwen_worker.py:242:            UPDATE photos
app/workers/qwen_worker.py:328:            UPDATE photos
app/workers/dino_worker.py:47:            UPDATE photos
app/workers/dino_worker.py:109:            UPDATE photos
app/workers/dino_worker.py:151:            UPDATE photos
app/workers/dino_worker.py:205:            UPDATE photos
scripts/photo_ingest.py:235:            INSERT INTO photos (
scripts/import_qwen_to_db.py:166:        INSERT INTO photos (
scripts/run_hybrid_v12.py:363:        hybrid_changed = best != old
scripts/run_hybrid_v12.py:370:        result["hybrid_changed"] = hybrid_changed
scripts/run_hybrid_v12.py:372:        result["hybrid_old_score"] = old_score
scripts/run_hybrid_v12.py:373:        result["hybrid_score"] = new_score
scripts/run_hybrid_v12.py:375:        result["hybrid_margin"] = margin
scripts/run_hybrid_v12.py:376:        result["hybrid_neighbors"] = dict(neighbors)
scripts/run_hybrid_v12.py:460:                "hybrid_changed": item.get(
scripts/run_hybrid_v12.py:461:                    "hybrid_changed"
scripts/run_hybrid_v12.py:478:                "hybrid_old_score": item.get(
scripts/run_hybrid_v12.py:479:                    "hybrid_old_score"
scripts/run_hybrid_v12.py:481:                "hybrid_score": item.get(
scripts/run_hybrid_v12.py:482:                    "hybrid_score"
scripts/run_hybrid_v12.py:705:        "hybrid_changed": len(changed),
scripts/qwen4b_output_v01.py:174:            UPDATE photos
scripts/qwen4b_output_v01.py:240:            UPDATE photos
scripts/qwen4b_output_v01.py:334:            UPDATE photos
scripts/qwen4b_output_v01.py:438:            UPDATE photos
scripts/migrate_sqlite_to_postgres.py:155:                INSERT INTO photos (
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:33:54

Вот теперь картина стала очень показательной.

**В текущем коде вообще нет PostgreSQL-записи результата Hybrid.**

Единственное место, где реально вычисляются:

```text
hybrid_changed
hybrid_old_score
hybrid_score
hybrid_margin
hybrid_neighbors
```

— это `scripts/run_hybrid_v12.py`.

Но там они существуют только внутри JSON-результата. `UPDATE photos` для Hybrid отсутствует.

При этом `app/web/photo_db.py` уже читает:

```text
hybrid_original_id
hybrid_final_id
hybrid_changed
hybrid_old_score
hybrid_score
hybrid_margin
hybrid_neighbors
```

То есть UI **ожидает Hybrid-результаты в PostgreSQL**, а текущий pipeline их туда не записывает.

### Следовательно

Похоже, мы нашли именно разрыв, который возник при переходе на новый pipeline:

```text
                 СЕЙЧАС

INGEST
  ↓
DINO WORKER
  ↓
PostgreSQL
  ↓
   ❌ Hybrid DB stage отсутствует
  ↓
UI ожидает hybrid_*

СТАРЫЙ / ОТДЕЛЬНЫЙ

input folder
  ↓
run_hybrid_v12.py
  ↓
DINO recognition
  ↓
Hybrid
  ↓
files + JSON
```

Именно поэтому я бы **не стал сейчас переписывать Hybrid v12**.

Нам нужно восстановить отсутствующий слой:

```text id="5trz5a"
DINO Worker
       ↓
PostgreSQL
       ↓
HYBRID DB WORKER
       ↓
PostgreSQL hybrid_*
       ↓
SORT
       ↓
PREVIEW
```

### Но есть ещё один очень важный вопрос

Чтобы Hybrid действительно мог работать **только с PostgreSQL**, надо выяснить, **есть ли там top-5 DINO-кандидаты**.

Сейчас `dino_worker.py` сохраняет только:

```text
best_id
score
second_score
margin
```

а Frozen Hybrid v12 требует:

```text
top1
top1_score
top2
top2_score
top3
top3_score
top4
top4_score
top5
top5_score
```

Поэтому следующий шаг — посмотреть **реальный `result`, который возвращает `recognize_one()`**, и структуру таблицы.

Самый безопасный вариант — сначала посмотреть определение `SceneRecognizer.recognize_one()`:

```bash id="6xj7p8"
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -Rni \
'def recognize_one' \
app \
--include="*.py"
```

Пришли вывод. От этого уже станет понятно, **есть ли top-5 внутри DINO сейчас и просто не сохраняется в PostgreSQL, или текущий worker вообще получает только top-1/top-2**.

---

### 👤 **User** — 2026-08-20 23:34:37

именно после гибрида образуются точные значения fingerprint id

---

### 🤖 **Assistant** — 2026-08-20 23:34:37

Да. Тогда это принципиально важно: **Hybrid не просто дополнительная сортировка — он формирует окончательный `fingerprint_id` фотографии.**

Получается правильная логика:

```text
ФОТО
  ↓
DINO
  ↓
первичный fingerprint / top-5
  ↓
HYBRID
  ├─ учитывает DINO
  ├─ учитывает subfingerprint для пограничных случаев
  └─ учитывает соседние фотографии
  ↓
FINAL fingerprint_id
  ↓
запись в PostgreSQL
  ↓
сортировка по FINAL fingerprint_id
  ↓
превью
```

И поэтому **создавать превью раньше Hybrid действительно бессмысленно** — окончательный адрес фотографии ещё не определён.

Более того, из показанного `run_hybrid_v12.py` видно точное место формирования финального ID:

```python
old = row.get("top1")
...
best = old
...
result["original_best_id"] = old
result["best_id"] = best
```

То есть:

- `original_best_id` — что решил DINO;
- `best_id` — **окончательное решение Hybrid**.

И вот это `best_id` должно стать тем самым `hybrid_final_id` в PostgreSQL.

### Поэтому я предлагаю дальше не трогать сам Hybrid v12

Нужно восстановить/зафиксировать **связку DINO → Hybrid → PostgreSQL**.

Сначала выясним, какие именно поля сейчас есть в `photos` и какие из них реально заполняются DINO.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'CREATE TABLE|ALTER TABLE|dino_fingerprint|dino_score|dino_second_score|dino_margin|hybrid_original_id|hybrid_final_id|hybrid_changed|hybrid_old_score|hybrid_score|hybrid_margin|hybrid_neighbors' \
app scripts \
--include="*.py" \
--include="*.sql" \
--include="*.sh" | \
grep -vE '__pycache__|benchmark|export_visual'
```

И **после этого отдельно посмотрим `photo_ingest.py`**, потому что нам надо точно зафиксировать весь контракт:

**что создаёт ingest → что пишет DINO → что читает Hybrid → что пишет Hybrid → что использует сортировка.**

Тогда больше не придётся каждый раз заново искать эту связку.

---

### 👤 **User** — 2026-08-20 23:35:30

int_mvp_v02 && \
grep -RniE \
'CREATE TABLE|ALTER TABLE|dino_fingerprint|dino_score|dino_second_score|dino_margin|hybrid_original_id|hybrid_final_id|hybrid_changed|hybrid_old_score|hybrid_score|hybrid_margin|hybrid_neighbors' \
app scripts \
--include="*.py" \
--include="*.sql" \
--include="*.sh" | \
grep -vE '__pycache__|benchmark|export_visual'
app/web/components/photos.py:345:        # dino_fingerprint.
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/components/photos.py:355:            record.get("dino_fingerprint") or ""
app/web/components/photos.py:364:        # На данном этапе dino_fingerprint сам является
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
app/web/users_db.py:54:                CREATE TABLE IF NOT EXISTS users (
app/web/users_db.py:68:                CREATE TABLE IF NOT EXISTS user_settings (
app/pipeline/queue.py:49:                CREATE TABLE IF NOT EXISTS jobs (
app/workers/dino_worker.py:157:                dino_fingerprint = %s,
app/workers/dino_worker.py:158:                dino_score = %s,
app/workers/dino_worker.py:159:                dino_second_score = %s,
app/workers/dino_worker.py:160:                dino_margin = %s,
scripts/import_qwen_to_db.py:39:        CREATE TABLE IF NOT EXISTS photos (
scripts/run_hybrid_v12.py:363:        hybrid_changed = best != old
scripts/run_hybrid_v12.py:370:        result["hybrid_changed"] = hybrid_changed
scripts/run_hybrid_v12.py:372:        result["hybrid_old_score"] = old_score
scripts/run_hybrid_v12.py:373:        result["hybrid_score"] = new_score
scripts/run_hybrid_v12.py:375:        result["hybrid_margin"] = margin
scripts/run_hybrid_v12.py:376:        result["hybrid_neighbors"] = dict(neighbors)
scripts/run_hybrid_v12.py:460:                "hybrid_changed": item.get(
scripts/run_hybrid_v12.py:461:                    "hybrid_changed"
scripts/run_hybrid_v12.py:478:                "hybrid_old_score": item.get(
scripts/run_hybrid_v12.py:479:                    "hybrid_old_score"
scripts/run_hybrid_v12.py:481:                "hybrid_score": item.get(
scripts/run_hybrid_v12.py:482:                    "hybrid_score"
scripts/run_hybrid_v12.py:705:        "hybrid_changed": len(changed),
scripts/banner_database_v02.py:93:    CREATE TABLE IF NOT EXISTS banners
scripts/banner_database_v01.py:50:    CREATE TABLE IF NOT EXISTS banners
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'CREATE TABLE|ALTER TABLE|dino_fingerprint|dino_score|dino_second_score|dino_margin|hybrid_original_id|hybrid_final_id|hybrid_changed|hybrid_old_score|hybrid_score|hybrid_margin|hybrid_neighbors' \
app scripts \
--include="*.py" \
--include="*.sql" \
--include="*.sh" | \
grep -vE '__pycache__|benchmark|export_visual'
app/web/components/photos.py:345:        # dino_fingerprint.
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/components/photos.py:355:            record.get("dino_fingerprint") or ""
app/web/components/photos.py:364:        # На данном этапе dino_fingerprint сам является
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
app/web/users_db.py:54:                CREATE TABLE IF NOT EXISTS users (
app/web/users_db.py:68:                CREATE TABLE IF NOT EXISTS user_settings (
app/pipeline/queue.py:49:                CREATE TABLE IF NOT EXISTS jobs (
app/workers/dino_worker.py:157:                dino_fingerprint = %s,
app/workers/dino_worker.py:158:                dino_score = %s,
app/workers/dino_worker.py:159:                dino_second_score = %s,
app/workers/dino_worker.py:160:                dino_margin = %s,
scripts/import_qwen_to_db.py:39:        CREATE TABLE IF NOT EXISTS photos (
scripts/run_hybrid_v12.py:363:        hybrid_changed = best != old
scripts/run_hybrid_v12.py:370:        result["hybrid_changed"] = hybrid_changed
scripts/run_hybrid_v12.py:372:        result["hybrid_old_score"] = old_score
scripts/run_hybrid_v12.py:373:        result["hybrid_score"] = new_score
scripts/run_hybrid_v12.py:375:        result["hybrid_margin"] = margin
scripts/run_hybrid_v12.py:376:        result["hybrid_neighbors"] = dict(neighbors)
scripts/run_hybrid_v12.py:460:                "hybrid_changed": item.get(
scripts/run_hybrid_v12.py:461:                    "hybrid_changed"
scripts/run_hybrid_v12.py:478:                "hybrid_old_score": item.get(
scripts/run_hybrid_v12.py:479:                    "hybrid_old_score"
scripts/run_hybrid_v12.py:481:                "hybrid_score": item.get(
scripts/run_hybrid_v12.py:482:                    "hybrid_score"
scripts/run_hybrid_v12.py:705:        "hybrid_changed": len(changed),
scripts/banner_database_v02.py:93:    CREATE TABLE IF NOT EXISTS banners
scripts/banner_database_v01.py:50:    CREATE TABLE IF NOT EXISTS banners
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:35:30

Да. Теперь картина достаточно ясная.

**Именно здесь у нас важное разделение:**

1. **DINO Worker** распознаёт фото и пишет в PostgreSQL:
   - `address_id`
   - `dino_fingerprint`
   - `dino_score`
   - `dino_second_score`
   - `dino_margin`
   - `dino_status`

2. **Hybrid v12** должен брать уже готовый результат DINO и **уточнять конечный fingerprint/address ID**, используя:
   - top1/top2 DINO;
   - subfingerprints;
   - соседние фотографии;
   - margin.

3. После Hybrid именно **финальный ID должен стать точным результатом**, который дальше используется фотобазой.

И вот тут обнаружилась существенная проблема текущей архитектуры:

**текущий `scripts/run_hybrid_v12.py` вообще не пишет результат Hybrid обратно в PostgreSQL.**

Он делает:

```text
DINO recognition
      ↓
adapt_recognizer_rows()
      ↓
Hybrid v12
      ↓
sort_results()
      ↓
JSON / папки output
```

А не:

```text
DINO Worker
      ↓
PostgreSQL
      ↓
Hybrid v12
      ↓
PostgreSQL
      ↓
точный final fingerprint ID
```

То есть нынешний Hybrid — это фактически **отдельный старый batch-процесс**, который получает фотографии повторно через `run_recognition()`. Это видно прямо из строк 96–118: он снова запускает `scene-fingerprint recognize`.

А твоя исходная рабочая связка, судя по описанию, должна быть другой:

```text
                ┌─────────────────┐
PHOTO ─────────►│   DINO WORKER   │
                └────────┬────────┘
                         │
                         ▼
                  PostgreSQL
              dino_* + address_id
                         │
                         ▼
                ┌─────────────────┐
                │   HYBRID v12    │
                │                 │
                │ top1/top2       │
                │ subfingerprints │
                │ neighbors       │
                │ margin          │
                └────────┬────────┘
                         │
                         ▼
                  PostgreSQL
              hybrid_final_id
                         │
                         ▼
                   ФОТОБАЗА
```

И это **намного правильнее**, чем делать превью раньше.

### Поэтому я бы сейчас ничего не переделывал в превью

Ты был прав: раннее создание превью нам ничего принципиально не даёт.

Сначала надо восстановить именно **рабочую цепочку DINO → Hybrid → PostgreSQL**.

Причём не надо переписывать саму логику Hybrid v12. У нас уже есть её зафиксированная часть:

- `MARGIN_LIMIT = 0.02`
- GLOBAL TOP-5
- SUB только для border cases
- SUB только TOP1/TOP2
- `sim > 0.88`
- bonus `2.5` при `sim > 0.92`
- соседний consensus только при полном совпадении
- `+3.0`
- смена результата только если `gain > 1.5`

Это как раз и нужно сохранить.

**Следующий шаг я предлагаю сделать диагностическим, без изменений кода:** найти старую/текущую схему `photos` и проверить, **есть ли в PostgreSQL уже колонки `hybrid_*` и какие из них реально заполнены**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python - <<'PY'
import psycopg2
import os

conn = psycopg2.connect(
    host=os.getenv("PHOTOBASE_HOST", "localhost"),
    port=int(os.getenv("PHOTOBASE_PORT", "5432")),
    user=os.getenv("PHOTOBASE_USER", "lora"),
    password=os.getenv("PHOTOBASE_PASSWORD", ""),
    dbname=os.getenv("PHOTOBASE_DB", "photobase"),
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_name = 'photos'
        ORDER BY ordinal_position
    """)

    for name, dtype in cur.fetchall():
        print(f"{name:30} {dtype}")

conn.close()
PY
```

И сразу после него:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python - <<'PY'
import psycopg2
import os

conn = psycopg2.connect(
    host=os.getenv("PHOTOBASE_HOST", "localhost"),
    port=int(os.getenv("PHOTOBASE_PORT", "5432")),
    user=os.getenv("PHOTOBASE_USER", "lora"),
    password=os.getenv("PHOTOBASE_PASSWORD", ""),
    dbname=os.getenv("PHOTOBASE_DB", "photobase"),
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT
            COUNT(*) AS total,
            COUNT(dino_fingerprint) AS dino,
            COUNT(hybrid_original_id) AS hybrid_original,
            COUNT(hybrid_final_id) AS hybrid_final,
            COUNT(hybrid_changed) AS hybrid_changed
        FROM photos
    """)

    print(cur.fetchone())

conn.close()
PY
```

**Пока ничего не меняем.** По этим двум выводам будет видно, насколько далеко нынешняя БД уже соответствует старой рабочей связке и что именно нужно вернуть в Hybrid.

---

### 👤 **User** — 2026-08-20 23:36:27

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
python - <<'PY'
import psycopg2
import os

conn = psycopg2.connect(
    host=os.getenv("PHOTOBASE_HOST", "localhost"),
    port=int(os.getenv("PHOTOBASE_PORT", "5432")),
    user=os.getenv("PHOTOBASE_USER", "lora"),
    password=os.getenv("PHOTOBASE_PASSWORD", ""),
    dbname=os.getenv("PHOTOBASE_DB", "photobase"),
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_name = 'photos'
        ORDER BY ordinal_position
    """)

PYnn.close()t(f"{name:30} {dtype}")():
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:36:29

Да, здесь просто ошибка в команде: у тебя в системе нет команды `python`, есть `python3`.

Но **сейчас лучше ничего не менять в БД**. Мы сначала точно посмотрим структуру `photos`, чтобы восстановить связку:

**DINO → запись результатов в PostgreSQL → Hybrid → уточнение `fingerprint_id` → сохранение финального результата.**

Выполни именно это:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
import psycopg2
import os

conn = psycopg2.connect(
    host=os.getenv("PHOTOBASE_HOST", "localhost"),
    port=int(os.getenv("PHOTOBASE_PORT", "5432")),
    user=os.getenv("PHOTOBASE_USER", "lora"),
    password=os.getenv("PHOTOBASE_PASSWORD", ""),
    dbname=os.getenv("PHOTOBASE_DB", "photobase"),
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT
            ordinal_position,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_name = 'photos'
        ORDER BY ordinal_position
    """)

    for pos, name, dtype in cur.fetchall():
        print(f"{pos:3}  {name:30} {dtype}")

conn.close()
PY
```

**Пришли весь вывод.**

После этого отдельно проверим **реальные значения нескольких строк `photos`** — особенно:

- `photo_id`
- `initial_id`
- `address_id`
- `dino_fingerprint`
- `dino_score`
- `dino_second_score`
- `dino_margin`
- `hybrid_original_id`
- `hybrid_final_id`
- `hybrid_changed`
- `hybrid_old_score`
- `hybrid_score`
- `hybrid_margin`
- `hybrid_neighbors`

И тогда уже станет видно, **куда именно раньше записывался результат Hybrid и почему текущий `run_hybrid_v12.py` пока работает отдельно от PostgreSQL**.

И да — твоя логика сейчас выглядит правильной: **Hybrid не должен повторно искать фотографию**. Если DINO уже записал необходимые результаты в PostgreSQL, Hybrid должен брать их оттуда, выполнять свою корректировку по соседям/подфингерпринтам и записывать **финальный fingerprint ID обратно в PostgreSQL**.

---

### 👤 **User** — 2026-08-20 23:37:05

uv python

---

### 🤖 **Assistant** — 2026-08-20 23:37:05

Да, верно — у тебя проект работает через `uv`, поэтому используем **`uv run python`**, а не системный `python3`.

Запусти:

```bash id="f6x8qa"
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import psycopg2
import os

conn = psycopg2.connect(
    host=os.getenv("PHOTOBASE_HOST", "localhost"),
    port=int(os.getenv("PHOTOBASE_PORT", "5432")),
    user=os.getenv("PHOTOBASE_USER", "lora"),
    password=os.getenv("PHOTOBASE_PASSWORD", ""),
    dbname=os.getenv("PHOTOBASE_DB", "photobase"),
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT
            ordinal_position,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_name = 'photos'
        ORDER BY ordinal_position
    """)

    for pos, name, dtype in cur.fetchall():
        print(f"{pos:3}  {name:30} {dtype}")

conn.close()
PY
```

Это будет использовать **тот же Python/окружение проекта**, что и DINO Worker.

Пришли вывод целиком.

---

### 👤 **User** — 2026-08-20 23:37:18

PYnn.close()t(f"{pos:3}  {name:30} {dtype}")
  1  id                             bigint
  2  photo_id                       text
  3  source_path                    text
  4  path                           text
  5  filename                       text
  6  original_filename              text
  7  address                        text
  8  client                         text
  9  brand                          text
 10  category                       text
 11  description                    text
 12  status                         text
 13  dino_status                    text
 14  qwen_status                    text
 15  sort_status                    text
 16  preview_status                 text
 17  error_message                  text
 18  dino_fingerprint               text
 19  dino_score                     double precision
 20  dino_second_score              double precision
 21  dino_margin                    double precision
 22  dino_time_sec                  double precision
 23  hybrid_original_id             text
 24  hybrid_final_id                text
 25  hybrid_changed                 boolean
 26  hybrid_old_score               double precision
 27  hybrid_score                   double precision
 28  hybrid_margin                  double precision
 29  hybrid_neighbors               jsonb
 30  confidence                     integer
 31  qwen_time_sec                  double precision
 32  text_json                      jsonb
 33  colors_json                    jsonb
 34  objects_json                   jsonb
 35  environment_json               jsonb
 36  image_quality_json             jsonb
 37  camera_view_json               jsonb
 38  scene_objects_json             jsonb
 39  analysis_quality_json          jsonb
 40  raw_json                       jsonb
 41  preview_path                   text
 42  created_at                     timestamp without time zone
 43  updated_at                     timestamp without time zone
 44  source_id                      text
 45  address_id                     text
 46  initial_id                     text
 47  dino_started_at                timestamp without time zone
 48  qwen_started_at                timestamp without time zone
 49  legal_address                  text
 50  simple_address                 text
 51  client_normalized              text

---

### 🤖 **Assistant** — 2026-08-20 23:37:20

Отлично. **База уже полностью подготовлена под правильную связку.** Ничего добавлять в схему не нужно.

Ключевой момент:

```text
DINO:
18  dino_fingerprint
19  dino_score
20  dino_second_score
21  dino_margin
22  dino_time_sec

HYBRID:
23  hybrid_original_id
24  hybrid_final_id
25  hybrid_changed
26  hybrid_old_score
27  hybrid_score
28  hybrid_margin
29  hybrid_neighbors
```

То есть архитектура фактически уже заложена в `photos`.

### И я теперь вижу, что нам надо проверить

Нужно понять **что реально лежит в этих полях сейчас**. Особенно интересно:

- есть ли старые `hybrid_final_id`;
- совпадает ли он с `dino_fingerprint` или отличается;
- есть ли `hybrid_neighbors`;
- какие значения были у реально обработанных фотографий.

Запускаем только чтение:

```bash id="w4w0xy"
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import os
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    host=os.getenv("PHOTOBASE_HOST", "localhost"),
    port=int(os.getenv("PHOTOBASE_PORT", "5432")),
    user=os.getenv("PHOTOBASE_USER", "lora"),
    password=os.getenv("PHOTOBASE_PASSWORD", ""),
    dbname=os.getenv("PHOTOBASE_DB", "photobase"),
)

with conn.cursor(cursor_factory=RealDictCursor) as cur:
    cur.execute("""
        SELECT
            id,
            photo_id,
            filename,
            dino_status,
            dino_fingerprint,
            dino_score,
            dino_second_score,
            dino_margin,
            hybrid_original_id,
            hybrid_final_id,
            hybrid_changed,
            hybrid_old_score,
            hybrid_score,
            hybrid_margin,
            hybrid_neighbors
        FROM photos
        WHERE dino_fingerprint IS NOT NULL
        ORDER BY id DESC
        LIMIT 20
    """)

    rows = cur.fetchall()

for row in rows:
    print("=" * 100)
    for key, value in row.items():
        print(f"{key:24}: {value}")

conn.close()
PY
```

### Почему именно это

Если увидим, например:

```text
dino_fingerprint     : 83
hybrid_original_id   : 83
hybrid_final_id      : 78
hybrid_changed       : true
```

то это будет **прямое доказательство**, что Hybrid действительно превращал первоначальный результат DINO в окончательный fingerprint.

А если там старые реальные данные — вообще идеально: мы сможем восстановить **не предполагаемую архитектуру, а фактически работавшую раньше**.

Пока никаких изменений. Только читаем 20 последних записей.

---

### 👤 **User** — 2026-08-20 23:37:49

====================================================================================================
id                      : 526
photo_id                : PH_00000526
filename                : Шолохова 127 А (9).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8843672466278076
dino_second_score       : 0.8525879204273223
dino_margin             : 0.03177932620048529
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 525
photo_id                : PH_00000525
filename                : Шолохова 127 А (8).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8970452749729155
dino_second_score       : 0.8808208197355271
dino_margin             : 0.01622445523738847
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 524
photo_id                : PH_00000524
filename                : Шолохова 127 А (7).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8904132449626921
dino_second_score       : 0.8756258612871168
dino_margin             : 0.014787383675575305
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 523
photo_id                : PH_00000523
filename                : Шолохова 127 А (6).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8736575585603713
dino_second_score       : 0.8586697649955749
dino_margin             : 0.014987793564796403
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 522
photo_id                : PH_00000522
filename                : Шолохова 127 А (5).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8984276247024536
dino_second_score       : 0.8798490905761719
dino_margin             : 0.018578534126281743
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 521
photo_id                : PH_00000521
filename                : Шолохова 127 А (4).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8974342620372772
dino_second_score       : 0.8775184828042984
dino_margin             : 0.019915779232978714
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 520
photo_id                : PH_00000520
filename                : Шолохова 127 А (3).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.9046348762512207
dino_second_score       : 0.8852626359462736
dino_margin             : 0.019372240304947108
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 519
photo_id                : PH_00000519
filename                : Шолохова 127 А (2).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8618447566032409
dino_second_score       : 0.8615931856632232
dino_margin             : 0.0002515709400177091
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 518
photo_id                : PH_00000518
filename                : Шолохова 127 А (19).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8940805959701538
dino_second_score       : 0.8718812644481658
dino_margin             : 0.02219933152198794
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 517
photo_id                : PH_00000517
filename                : Шолохова 127 А (18).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8924807512760162
dino_second_score       : 0.8799367851018907
dino_margin             : 0.012543966174125565
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 516
photo_id                : PH_00000516
filename                : Шолохова 127 А (17).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8944720298051834
dino_second_score       : 0.8666357392072677
dino_margin             : 0.027836290597915703
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 515
photo_id                : PH_00000515
filename                : Шолохова 127 А (16).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.851322934627533
dino_second_score       : 0.8352598595619203
dino_margin             : 0.016063075065612664
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 514
photo_id                : PH_00000514
filename                : Шолохова 127 А (15).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.7879115408658982
dino_second_score       : 0.7679122918844222
dino_margin             : 0.01999924898147598
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 513
photo_id                : PH_00000513
filename                : Шолохова 127 А (14).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8080845338106155
dino_second_score       : 0.7955688482522965
dino_margin             : 0.012515685558319056
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 512
photo_id                : PH_00000512
filename                : Шолохова 127 А (13).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.7006912517547607
dino_second_score       : 0.6869233208894729
dino_margin             : 0.013767930865287714
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 511
photo_id                : PH_00000511
filename                : Шолохова 127 А (12).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.9007747375965118
dino_second_score       : 0.8843768554925919
dino_margin             : 0.016397882103919903
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 510
photo_id                : PH_00000510
filename                : Шолохова 127 А (11).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8698311281204224
dino_second_score       : 0.8615509045124052
dino_margin             : 0.008280223608017168
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 509
photo_id                : PH_00000509
filename                : Шолохова 127 А (10).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8889733201265334
dino_second_score       : 0.8715850049257278
dino_margin             : 0.017388315200805637
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 508
photo_id                : PH_00000508
filename                : Шолохова 127 А (1).JPG
dino_status             : done
dino_fingerprint        : 94_v33
dino_score              : 0.8989868396520614
dino_second_score       : 0.876552192568779
dino_margin             : 0.022434647083282355
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
====================================================================================================
id                      : 507
photo_id                : PH_00000507
filename                : Шеболдаева8_18.JPG
dino_status             : done
dino_fingerprint        : 87_v33
dino_score              : 0.9412475711107254
dino_second_score       : 0.8578296142816544
dino_margin             : 0.08341795682907105
hybrid_original_id      : None
hybrid_final_id         : None
hybrid_changed          : False
hybrid_old_score        : None
hybrid_score            : None
hybrid_margin           : None
hybrid_neighbors        : None
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:37:52

Да. Теперь причина уже видна довольно чётко.

**Связка DINO → Hybrid действительно должна быть такой:**

`DINO Worker → записывает результат в PostgreSQL → Hybrid читает эти поля из PostgreSQL → Hybrid уточняет ID → записывает финальный ID обратно в PostgreSQL`.

А сейчас у нас **DINO работает отдельно и Hybrid фактически оторван от PostgreSQL**.

### Что сейчас делает DINO Worker

Он уже правильно пишет в `photos`:

- `dino_fingerprint`
- `dino_score`
- `dino_second_score`
- `dino_margin`
- `dino_status = done`

И это подтверждается твоими данными:

```text
dino_fingerprint = 94_v33
dino_score        = 0.884367...
dino_second_score = 0.852587...
dino_margin       = 0.031779...
```

То есть DINO свою часть выполняет.

### Что сейчас делает Hybrid v12

В показанном `run_hybrid_v12.py` есть принципиальная проблема.

Он получает данные через:

```python
run_recognition(input_dir, fingerprints)
```

то есть **заново запускает `scene-fingerprint recognize` по фотографиям**.

А затем:

```python
hybrid_rows, changed, sub_count = hybrid_v12(
    recognition,
    embedder,
    subs,
)
```

И результат сохраняет только сюда:

```text
recognition.json
hybrid_v12.json
report.json
statistics.json
```

**В PostgreSQL этот скрипт ничего не записывает.**

Поэтому твоя текущая картина:

```text
dino_status             = done
dino_fingerprint        = 94_v33

hybrid_original_id      = None
hybrid_final_id         = None
hybrid_changed          = False
hybrid_old_score        = None
hybrid_score            = None
hybrid_margin           = None
hybrid_neighbors        = None
```

абсолютно логична.

---

## И самое важное

Ты прав: **фотографии Hybrid вообще не нужны** в новой архитектуре.

У нас уже есть всё необходимое в PostgreSQL:

```text
dino_fingerprint
dino_score
dino_second_score
dino_margin
```

А для последовательного анализа есть сами строки `photos`, где можно получить соседей.

То есть правильная архитектура сейчас должна быть:

```text
                    ┌──────────────────────┐
                    │     PostgreSQL       │
                    │       photos         │
                    └──────────┬───────────┘
                               │
                         DINO Worker
                               │
                               ▼
                    dino_fingerprint
                    dino_score
                    dino_second_score
                    dino_margin
                               │
                               ▼
                       ┌─────────────┐
                       │ HYBRID V12  │
                       └──────┬──────┘
                              │
                  ┌───────────┼───────────┐
                  │           │           │
               TOP-5       SUB-FP      NEIGHBORS
                  │           │           │
                  └───────────┼───────────┘
                              ▼
                       FINAL ADDRESS ID
                              │
                              ▼
                    PostgreSQL photos
                              │
                              ▼
                    hybrid_final_id
```

Именно это нам и надо восстановить.

### Причём старый Hybrid v12 уже содержит саму логику

Вот эти правила у нас зафиксированы:

```text
MARGIN_LIMIT = 0.02
GLOBAL_WEIGHT = 10.0
SUB_WEIGHT = 2.5
NEIGHBOR_WEIGHT = 6.0
```

и:

- Global TOP-5
- Sub только для border cases
- только TOP1 + TOP2 для sub
- `sim > 0.88`
- `sim > 0.92 → bonus 2.5`
- иначе bonus `1.0`
- соседи только при полном согласии
- соседний бонус `+3.0`
- смена результата только если `gain > 1.5`

То есть **сам алгоритм терять не надо**.

---

### Но есть ещё один важный момент

В текущем `run_hybrid_v12.py` Hybrid всё-таки использует `embedder` для sub-фингерпринтов:

```python
query = embedder.embed_paths([image])[0]
```

Это означает: старый Hybrid действительно требовал файл фотографии **только для повторного получения embedding query**.

Но если мы хотим окончательно сделать:

> **DINO один раз посчитал embedding → сохранил результат → Hybrid работает только по БД**

то надо посмотреть, **сохраняется ли сам embedding DINO** где-нибудь для каждой фотографии.

Если нет — есть два варианта:

1. сохранить DINO embedding в PostgreSQL/отдельное хранилище;
2. либо оставить повторный `embed_paths()` только для border cases.

Но это уже отдельный вопрос.

---

### Сейчас главное

**Не надо переделывать DINO Worker.**

Он уже правильно пишет свою часть.

Надо восстановить именно второй этап:

```text
DINO DB results
       ↓
Hybrid V12 DB
       ↓
hybrid_original_id
hybrid_final_id
hybrid_changed
hybrid_old_score
hybrid_score
hybrid_margin
hybrid_neighbors
```

И тогда твои `None` после DINO исчезнут.

**Следующим шагом я бы не трогал рабочий `run_hybrid_v12.py`, а сначала сделал отдельный диагностический DB-Hybrid, который прочитает 20–30 уже обработанных строк из PostgreSQL и покажет, может ли он воспроизвести старый Hybrid результат без повторного запуска DINO.** Это безопаснее всего: сначала докажем связку на существующих данных, потом подключим её к pipeline.

---

### 👤 **User** — 2026-08-20 23:39:00

давай

---

### 🤖 **Assistant** — 2026-08-20 23:39:04

Да. Делаем **сначала только диагностику, без изменения БД и без изменения рабочего кода**.

И сразу важное: по текущей схеме PostgreSQL у нас есть `dino_fingerprint`, `dino_score`, `dino_second_score`, `dino_margin`, но **нет TOP-3/TOP-4/TOP-5 кандидатов DINO**. Поэтому старый Hybrid v12 нельзя пока побайтно воспроизвести только из этих полей: его Global-часть использует TOP-5.

Но сначала проверим, что **DINO → PostgreSQL → Hybrid** вообще можно связать на существующих данных.

### 1. Создаём диагностический скрипт

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/diagnose_dino_hybrid_db.py <<'PY'
#!/usr/bin/env python3

import os
import json
import psycopg2

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

def main():

    conn = psycopg2.connect(**DB_CONFIG)

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    id,
                    photo_id,
                    filename,
                    dino_status,
                    dino_fingerprint,
                    dino_score,
                    dino_second_score,
                    dino_margin,
                    hybrid_original_id,
                    hybrid_final_id,
                    hybrid_changed,
                    hybrid_old_score,
                    hybrid_score,
                    hybrid_margin,
                    hybrid_neighbors
                FROM photos
                WHERE dino_status = 'done'
                ORDER BY id DESC
                LIMIT 30
            """)

            rows = cur.fetchall()

            print()
            print("=" * 100)
            print("DINO -> POSTGRES -> HYBRID DIAGNOSTIC")
            print("=" * 100)
            print()
            print("Rows:", len(rows))
            print()

            if not rows:
                print("NO DINO DONE ROWS")
                return

            dino_done = 0
            dino_with_fp = 0
            hybrid_done = 0
            hybrid_changed = 0

            fingerprints = {}

            for row in rows:

                (
                    db_id,
                    photo_id,
                    filename,
                    dino_status,
                    dino_fp,
                    dino_score,
                    dino_second,
                    dino_margin,
                    hybrid_original,
                    hybrid_final,
                    hybrid_changed_value,
                    hybrid_old_score,
                    hybrid_score,
                    hybrid_margin,
                    hybrid_neighbors,
                ) = row

                if dino_status == "done":
                    dino_done += 1

                if dino_fp:
                    dino_with_fp += 1
                    fingerprints[dino_fp] = fingerprints.get(dino_fp, 0) + 1

                if hybrid_final is not None:
                    hybrid_done += 1

                if hybrid_changed_value:
                    hybrid_changed += 1

                print("-" * 100)
                print(f"id                  : {db_id}")
                print(f"photo_id            : {photo_id}")
                print(f"filename            : {filename}")
                print(f"dino_status         : {dino_status}")
                print(f"dino_fingerprint    : {dino_fp}")
                print(f"dino_score          : {dino_score}")
                print(f"dino_second_score   : {dino_second}")
                print(f"dino_margin         : {dino_margin}")
                print(f"hybrid_original_id  : {hybrid_original}")
                print(f"hybrid_final_id     : {hybrid_final}")
                print(f"hybrid_changed      : {hybrid_changed_value}")
                print(f"hybrid_old_score    : {hybrid_old_score}")
                print(f"hybrid_score        : {hybrid_score}")
                print(f"hybrid_margin       : {hybrid_margin}")
                print(f"hybrid_neighbors    : {json.dumps(hybrid_neighbors, ensure_ascii=False)}")

            print()
            print("=" * 100)
            print("SUMMARY")
            print("=" * 100)
            print()
            print("DINO done           :", dino_done)
            print("DINO with fingerprint:", dino_with_fp)
            print("Hybrid final present:", hybrid_done)
            print("Hybrid changed      :", hybrid_changed)
            print()

            print("DINO fingerprints:")
            for fp, count in sorted(
                fingerprints.items(),
                key=lambda x: (-x[1], x[0]),
            ):
                print(f"  {fp:20} {count}")

            print()
            print("=" * 100)
            print("IMPORTANT")
            print("=" * 100)
            print()
            print("PostgreSQL currently contains:")
            print("  dino_fingerprint")
            print("  dino_score")
            print("  dino_second_score")
            print("  dino_margin")
            print()
            print("But old Hybrid v12 requires:")
            print("  TOP1")
            print("  TOP2")
            print("  TOP3")
            print("  TOP4")
            print("  TOP5")
            print()
            print("Therefore exact old V12 Global TOP-5 cannot yet be")
            print("reconstructed from the current DB fields alone.")
            print()

    finally:
        conn.close()

if __name__ == "__main__":
    main()
PY
```

### 2. Запускаем именно через `uv`

У тебя `python` не установлен как команда, поэтому:

```bash
uv run python scripts/diagnose_dino_hybrid_db.py
```

### Что нас сейчас интересует

Особенно важны три вещи.

**Первое:** действительно ли все DINO результаты уже лежат в PostgreSQL.

**Второе:** есть ли где-нибудь в БД информация TOP-3…TOP-5, которую мы пока не нашли.

**Третье:** подтверждение текущего разрыва:

```text
dino_fingerprint = 94_v33
        ↓
dino_score
dino_second_score
dino_margin
        ↓
        X
hybrid_final_id = NULL
```

После этого уже будем решать архитектуру.

И **ничего пока не меняй в `dino_worker.py` и `run_hybrid_v12.py`**. Нам сейчас нужно увидеть результат этой диагностики.

---

