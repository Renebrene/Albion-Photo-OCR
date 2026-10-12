## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 🤖 **Assistant** — 2026-08-15 03:01:43

Да, теперь понятно, что у нас есть **полный отчёт по каждому снимку**, включая всех 5 кандидатов. Это именно то, что нужно для диагностики.

Причём `sort_test_and_report_v2.py` уже сохраняет:

- `candidate_1`
- `candidate_2 ... candidate_5`
- score каждого
- `margin`
- `confidence`
- `status`
- `global`
- `environment`
- `color`
- `spatial`
- `best_image`

Поэтому **не надо повторно гонять распознавание**. Сначала разберём уже полученный прогон.

### 1. Найдём свежие отчёты

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "================ REPORT FILES ================"

find . -type f \( \
    -name '*.json' -o \
    -name '*.csv' \
\) \
-not -path './.venv/*' \
-not -path './.git/*' \
-printf '%TY-%Tm-%Td %TH:%TM:%TS  %p\n' \
| sort -r \
| head -30
```

### 2. Посмотрим, куда именно `sort_test_and_report_v2.py` пишет результаты

```bash
grep -nE \
'^(INPUT_DIR|OUTPUT_DIR|REPORT|STATISTICS)|Path\(' \
scripts/sort_test_and_report_v2.py | head -80
```

### 3. И самое главное — покажем статистику последнего запуска

Если увидим, например:

```text
data/output/...
statistics.json
report.json
```

сразу выполним для найденного JSON:

```bash
python3 - <<'PY'
from pathlib import Path
import json

files = sorted(
    Path(".").rglob("*.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True
)

for p in files[:10]:
    print(p)
PY
```

---

### Почему сейчас я не хочу просто смотреть на распределение 78–95

У нас уже есть очень важная информация: **262 снимка получили TOP-1**.

Но нам нужно разделить ошибки на три типа:

**Тип A — правильного адреса вообще нет в TOP-5**

```text
REAL 90

1. 94  0.71
2. 87  0.69
3. 91  0.67
4. 88  0.66
5. 93  0.64
```

→ проблема самого fingerprint/признаков.

**Тип B — правильный адрес есть, но не первый**

```text
REAL 90

1. 94  0.712
2. 90  0.708   ← правильный
3. 87  0.681
```

→ **это уже очень интересно**. Значит, система знает правильный адрес, но неправильно ранжирует кандидатов.

**Тип C — правильный адрес первый, но мы его считаем ошибкой из-за порога**

```text
REAL 90

1. 90  0.59
2. 94  0.56
```

→ fingerprint фактически угадал, но threshold отбрасывает результат.

И вот после того как мы вернули старую логику `NO_MATCH`, **особенно важно проверить Тип C**.

Поэтому сейчас **не запускай ещё один тест**. Пришли вывод первой команды с JSON/CSV. По нему мы достанем результаты последнего запуска и построим нормальный анализ ошибок 78–95.

---

### 👤 **User** — 2026-08-15 03:02:32

from pathlib import Path
import json

files = sorted(
    Path(".").rglob("*.json"),
    key=lambda p: p.stat().st_mtime,
    reverse=True
)

for p in files[:10]:
    print(p)
PY
data/fingerprints/95_v33/metadata.json
data/fingerprints/94_v33/metadata.json
data/fingerprints/93_v33/metadata.json
data/fingerprints/92_v33/metadata.json
data/fingerprints/91_v33/metadata.json
data/fingerprints/90_v33/metadata.json
data/fingerprints/89_v33/metadata.json
data/fingerprints/88_v33/metadata.json
data/fingerprints/87_v33/metadata.json
data/fingerprints/86_v33/metadata.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:02:33

Да. Здесь мы видим, что поиск по `*.json` забивается `metadata.json` от fingerprint'ов, поэтому отчёт оказался не в первых 10.

Давай найдём **именно файлы отчёта**, ориентируясь на имена, которые использует `sort_test_and_report_v2.py`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "================ REPORT PATHS ================"

grep -nE \
'REPORT_CSV|REPORT_JSON|STATISTICS_JSON|OUTPUT_DIR|INPUT_DIR' \
scripts/sort_test_and_report_v2.py

echo
echo "================ RECENT CSV/JSON ================"

find data /tmp . -type f \( \
    -name '*.csv' -o \
    -name '*.json' \
\) \
-not -path './.venv/*' \
-not -path './.git/*' \
-not -path './data/fingerprints/*' \
-printf '%TY-%Tm-%Td %TH:%TM:%TS  %p\n' \
2>/dev/null \
| sort -r \
| head -40
```

После этого мы сразу найдём свежий `REPORT_JSON`/`STATISTICS_JSON`.

**Повторно распознавать 262 фотографии пока не нужно.** Если отчёт сохранился, у нас уже есть всё необходимое для анализа:

- TOP-1;
- TOP-5;
- score;
- margin;
- global;
- environment;
- color;
- spatial;
- confidence;
- status.

И я предлагаю первым делом посчитать очень конкретную вещь:

> **из всех ошибочных TOP-1 сколько раз правильный адрес находился на 2–5 месте?**

Если таких случаев много — мы нашли причину ошибок и сможем улучшать **ранжирование**, не переделывая сами fingerprint'ы.

---

### 👤 **User** — 2026-08-15 03:02:48

379:    STATISTICS_JSON.write_text(
438:    print("Sorted:", OUTPUT_DIR)
439:    print("CSV:   ", REPORT_CSV)
440:    print("JSON:  ", REPORT_JSON)
441:    print("Stats: ", STATISTICS_JSON)

================ RECENT CSV/JSON ================
2026-08-15 02:37:32.3324771120  data/fingerprints/95_v33/metadata.json
2026-08-15 02:37:16.6201184100  data/fingerprints/94_v33/metadata.json
2026-08-15 02:37:01.0666442530  data/fingerprints/93_v33/metadata.json
2026-08-15 02:36:49.1436886900  data/fingerprints/92_v33/metadata.json
2026-08-15 02:36:36.9607424950  data/fingerprints/91_v33/metadata.json
2026-08-15 02:36:26.5735305950  data/fingerprints/90_v33/metadata.json
2026-08-15 02:36:18.6926514250  data/fingerprints/89_v33/metadata.json
2026-08-15 02:36:05.5970140740  data/fingerprints/88_v33/metadata.json
2026-08-15 02:35:53.7364866750  data/fingerprints/87_v33/metadata.json
2026-08-15 02:35:41.7867821410  data/fingerprints/86_v33/metadata.json
2026-08-15 02:35:28.0869849840  data/fingerprints/85_v33/metadata.json
2026-08-15 02:35:14.9101714310  data/fingerprints/84_v33/metadata.json
2026-08-15 02:35:02.1536321970  data/fingerprints/83_v33/metadata.json
2026-08-15 02:34:48.6499821840  data/fingerprints/82_v33/metadata.json
2026-08-15 02:34:35.6067974620  data/fingerprints/81_v33/metadata.json
2026-08-15 02:34:20.2216036860  data/fingerprints/80_v33/metadata.json
2026-08-15 02:34:10.5514038430  data/fingerprints/79_v33/metadata.json
2026-08-15 02:33:57.2073079450  data/fingerprints/78_v33/metadata.json
2026-08-15 02:14:31.3582558780  data/reports/test_summary.json
2026-08-15 02:14:31.3582558780  ./data/reports/test_summary.json
2026-08-15 02:14:31.3573896440  data/reports/test_recognition.json
2026-08-15 02:14:31.3573896440  ./data/reports/test_recognition.json
2026-08-15 02:14:31.3543895560  data/reports/test_recognition.csv
2026-08-15 02:14:31.3543895560  ./data/reports/test_recognition.csv
2026-08-15 02:08:11.8692745260  /tmp/recognize_test.json
2026-08-15 01:59:17.9900458500  data/subfingerprints_v2/78_v33/sub_03/metadata.json
2026-08-15 01:59:17.9900458500  ./data/subfingerprints_v2/78_v33/sub_03/metadata.json
2026-08-15 01:59:17.9892822970  data/subfingerprints_v2/78_v33/sub_02/metadata.json
2026-08-15 01:59:17.9892822970  ./data/subfingerprints_v2/78_v33/sub_02/metadata.json
2026-08-15 01:59:17.9878431850  data/subfingerprints_v2/78_v33/sub_01/metadata.json
2026-08-15 01:59:17.9878431850  ./data/subfingerprints_v2/78_v33/sub_01/metadata.json
2026-08-15 01:55:40.9005750230  data/subfingerprints/78_v33/metadata.json
2026-08-15 01:55:40.9005750230  ./data/subfingerprints/78_v33/metadata.json
2026-08-15 01:55:40.9004173180  data/subfingerprints/78_v33/sub_11/metadata.json
2026-08-15 01:55:40.9004173180  ./data/subfingerprints/78_v33/sub_11/metadata.json
2026-08-15 01:55:40.8995254620  data/subfingerprints/78_v33/sub_10/metadata.json
2026-08-15 01:55:40.8995254620  ./data/subfingerprints/78_v33/sub_10/metadata.json
2026-08-15 01:55:40.8987491190  data/subfingerprints/78_v33/sub_09/metadata.json
2026-08-15 01:55:40.8987491190  ./data/subfingerprints/78_v33/sub_09/metadata.json
2026-08-15 01:55:40.8978631740  data/subfingerprints/78_v33/sub_08/metadata.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:02:48

Да. По этим данным уже видно важное:

1. **Сами `78_v33 ... 95_v33` были пересозданы сегодня в 02:33–02:37.**
2. Тест сортировки был завершён в **02:14**, то есть он использовал **предыдущую версию слепков**, а не эти свежесозданные.
3. Поэтому результат `262` фотографий пока **нельзя использовать для оценки текущего v33**.
4. При этом diff показывает, что в `recognizer.py` после оптимизации **логика выбора кандидата не изменилась**, кроме `FORCED_MATCH`. Основное изменение — предварительный расчёт дескрипторов и многопоточность.
5. Значит, сейчас правильный следующий шаг — **чистый контрольный прогон на только что пересозданных `78_v33–95_v33`**, желательно с сохранением полного CSV/JSON.

Я бы сейчас **ничего в коде не менял**. Сначала получим чистый результат.

### 1. Проверим, какие fingerprint реально будут использоваться

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== V33 FINGERPRINTS ==="
find data/fingerprints -maxdepth 1 -type d -name '*_v33' | sort

echo
echo "=== COUNTS ==="
for d in data/fingerprints/*_v33; do
    [ -d "$d" ] || continue
    echo -n "$(basename "$d"): "
    find "$d" -maxdepth 1 -type f | wc -l
done
```

### 2. Затем запускаем тест заново

Но **не удаляй старый отчёт без копии**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

mkdir -p data/reports/backup_before_new_test

cp -f data/reports/test_recognition.csv \
      data/reports/backup_before_new_test/test_recognition_0214.csv 2>/dev/null || true

cp -f data/reports/test_recognition.json \
      data/reports/backup_before_new_test/test_recognition_0214.json 2>/dev/null || true

cp -f data/reports/test_summary.json \
      data/reports/backup_before_new_test/test_summary_0214.json 2>/dev/null || true
```

После этого запускаем **тот же самый тестовый скрипт**, которым получили:

```text
TOTAL COPIED: 262
OUTPUT: data/output/test_classified
```

Если команда у тебя потерялась, найдем её:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
'FINAL TOP-1 CLASSIFICATION|TOTAL COPIED|test_classified|SCENE FINGERPRINT TEST SORTER' \
--include='*.py' \
--include='*.sh' \
.
```

**Пришли вывод этой команды.**

Дальше я дам ровно одну команду на повторный прогон.

---

И ещё один очень важный момент: после нового прогона нам надо смотреть **не только распределение**:

```text
78 20
79 8
...
```

а именно пары:

```text
реальный адрес → выбранный адрес
score
margin
confidence
global
environment
color
spatial
candidate_2
candidate_3
```

Потому что сейчас у нас есть подозрение, что проблема может быть не в оптимизации вообще, а в **самом рейтинге v33** либо в том, что `FORCED_MATCH` превращает плохие распознавания в якобы успешные.

Особенно интересует:

```text
score
margin
global
environment
color
spatial
candidate_2
```

Если, например, неправильные фотографии имеют:

```text
best = 0.58
second = 0.57
margin = 0.01
```

то это совсем другая проблема, чем:

```text
best = 0.82
second = 0.54
margin = 0.28
```

Во втором случае **сам алгоритм уверенно ошибается**, и тогда будем разбирать веса/слепки. В первом — кандидаты просто неразличимы, и можно возвращать старую логику с порогом/первым кандидатом.

**Сейчас главное — прогнать именно на свежих `78_v33–95_v33`, не меняя код.**

---

### 👤 **User** — 2026-08-15 03:03:30

int_mvp_v02

grep -RniE \
'FINAL TOP-1 CLASSIFICATION|TOTAL COPIED|test_classified|SCENE FINGERPRINT TEST SORTER' \
--include='*.py' \
--include='*.sh' \
.
./classify_test.sh:8:OUT_DIR="$ROOT/data/output/test_classified"
./classify_test_results.py:7:OUTPUT = Path("output/test_classified")
./classify_final_test.py:7:OUTPUT = Path("data/output/test_classified")
./classify_final_test.py:153:print("FINAL TOP-1 CLASSIFICATION")
./classify_final_test.py:185:    f"TOTAL COPIED: {total}"
./scripts/sort_test_and_report_v2.py:355:    print("SCENE FINGERPRINT TEST SORTER V2")
./classify_test.py:22:OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "test_classified"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:03:31

Отлично. Судя по выводу, **последний результат `FINAL TOP-1 CLASSIFICATION` делал `classify_final_test.py`**.

Давай сначала посмотрим, **какие fingerprint он реально передаёт recognizer'у**, и только потом запускаем. Это важно, чтобы случайно опять не получить тест на старом наборе.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== classify_final_test.py ==="
nl -ba classify_final_test.py | sed -n '1,230p'
```

Пришли вывод.

После этого я проверю:

- откуда берётся список `78_v33 ... 95_v33`;
- какой `threshold`;
- какие параметры `recognize()` передаются;
- не используется ли где-то `*_fast`;
- куда пишется отчёт;
- не осталось ли старого `FORCED_MATCH`;
- и дам **одну точную команду для чистого контрольного прогона** на свежих слепках.

Пока **не запускай повторно** — сначала посмотрим этот файл.

---

### 👤 **User** — 2026-08-15 03:03:49

echo "=== classify_final_test.py ==="
nl -ba classify_final_test.py | sed -n '1,230p'
=== classify_final_test.py ===
     1	from pathlib import Path
     2	import json
     3	import shutil
     4	
     5	RESULTS = Path("final_test_78_95.json")
     6	SOURCE = Path("data/input/test")
     7	OUTPUT = Path("data/output/test_classified")
     8	
     9	OUTPUT.mkdir(
    10	    parents=True,
    11	    exist_ok=True,
    12	)
    13	
    14	# --------------------------------------------------
    15	# LOAD JSON
    16	# --------------------------------------------------
    17	
    18	lines = RESULTS.read_text(
    19	    encoding="utf-8"
    20	).splitlines()
    21	
    22	start = None
    23	
    24	for i, line in enumerate(lines):
    25	    if line.strip() == "[":
    26	        start = i
    27	        break
    28	
    29	if start is None:
    30	    raise RuntimeError(
    31	        "JSON array not found"
    32	    )
    33	
    34	data = json.loads(
    35	    "\n".join(lines[start:])
    36	)
    37	
    38	print(
    39	    f"Results loaded: {len(data)}"
    40	)
    41	
    42	# --------------------------------------------------
    43	# COPY BY TOP-1
    44	# --------------------------------------------------
    45	
    46	counts = {}
    47	
    48	for r in data:
    49	
    50	    file_path = Path(
    51	        r["file"]
    52	    )
    53	
    54	    filename = file_path.name
    55	
    56	    # TOP-1 ALWAYS WINS
    57	    best_id = r.get(
    58	        "best_id"
    59	    )
    60	
    61	    # Если best_id отсутствует,
    62	    # берём первого кандидата.
    63	    if not best_id:
    64	
    65	        candidates = r.get(
    66	            "candidates",
    67	            []
    68	        )
    69	
    70	        if candidates:
    71	            best_id = candidates[0].get(
    72	                "id"
    73	            )
    74	
    75	    # Только если вообще нет кандидата
    76	    if not best_id:
    77	        folder_name = "NO_CANDIDATE"
    78	    else:
    79	        folder_name = str(
    80	            best_id
    81	        )
    82	
    83	    destination_dir = (
    84	        OUTPUT / folder_name
    85	    )
    86	
    87	    destination_dir.mkdir(
    88	        parents=True,
    89	        exist_ok=True,
    90	    )
    91	
    92	    source_file = (
    93	        SOURCE / filename
    94	    )
    95	
    96	    if not source_file.exists():
    97	
    98	        if file_path.exists():
    99	            source_file = file_path
   100	
   101	        else:
   102	            print(
   103	                f"[WARNING] "
   104	                f"Source not found: "
   105	                f"{filename}"
   106	            )
   107	            continue
   108	
   109	    destination_file = (
   110	        destination_dir
   111	        / filename
   112	    )
   113	
   114	    # Защита от одинаковых имён
   115	    if destination_file.exists():
   116	
   117	        stem = destination_file.stem
   118	        suffix = destination_file.suffix
   119	
   120	        n = 2
   121	
   122	        while True:
   123	
   124	            candidate = (
   125	                destination_dir
   126	                / f"{stem}__{n}{suffix}"
   127	            )
   128	
   129	            if not candidate.exists():
   130	                destination_file = candidate
   131	                break
   132	
   133	            n += 1
   134	
   135	    shutil.copy2(
   136	        source_file,
   137	        destination_file,
   138	    )
   139	
   140	    counts[folder_name] = (
   141	        counts.get(
   142	            folder_name,
   143	            0,
   144	        ) + 1
   145	    )
   146	
   147	# --------------------------------------------------
   148	# REPORT
   149	# --------------------------------------------------
   150	
   151	print()
   152	print("=" * 70)
   153	print("FINAL TOP-1 CLASSIFICATION")
   154	print("=" * 70)
   155	
   156	total = 0
   157	
   158	for name in sorted(
   159	    counts,
   160	    key=lambda x: (
   161	        int(
   162	            "".join(
   163	                c
   164	                for c in x
   165	                if c.isdigit()
   166	            )
   167	        )
   168	        if any(
   169	            c.isdigit()
   170	            for c in x
   171	        )
   172	        else 9999
   173	    ),
   174	):
   175	
   176	    count = counts[name]
   177	    total += count
   178	
   179	    print(
   180	        f"{name:20} {count:4}"
   181	    )
   182	
   183	print()
   184	print(
   185	    f"TOTAL COPIED: {total}"
   186	)
   187	
   188	print(
   189	    f"OUTPUT: {OUTPUT}"
   190	)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:03:49

Да, теперь всё понятно.

`classify_final_test.py` **вообще не выполняет распознавание**. Он только берёт уже готовый:

```text
final_test_78_95.json
```

и раскладывает фотографии по `best_id`.

То есть результат:

```text
78_v33 20
79_v33 8
...
TOTAL COPIED: 262
```

— это результат **предыдущего запуска распознавания**, сохранённого в `final_test_78_95.json`.

А свежие fingerprints `78_v33–95_v33` были созданы **после** этого запуска. Поэтому сейчас нам нужно найти команду, которая создала `final_test_78_95.json`.

### Найдём источник JSON

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== WHO CREATES final_test_78_95.json ==="

grep -Rni \
"final_test_78_95.json" \
--include="*.py" \
--include="*.sh" \
.
```

И ещё сразу:

```bash
echo
echo "=== RECOGNIZE CALLS ==="

grep -RniE \
'recognize\(|scene-fingerprint recognize|final_test_78_95|top_k|threshold' \
--include="*.py" \
--include="*.sh" \
. | head -200
```

### Почему это сейчас принципиально

У нас есть три разных вещи:

**1. Распознавание**

```text
test images
     ↓
SceneRecognizer
     ↓
78_v33 ... 95_v33
     ↓
final_test_78_95.json
```

**2. Сортировка**

```text
final_test_78_95.json
     ↓
classify_final_test.py
     ↓
data/output/test_classified/
```

**3. Свежие слепки**

```text
78_v33 ... 95_v33
```

Они были пересозданы в 02:33–02:37, **но JSON в 02:14**, следовательно, сортировка 262 файлов использовала старое распознавание.

---

И ещё важное наблюдение из diff.

Ты показал:

```text
backup_before_optimization
             ↓
        recognizer.py
```

Там **нет изменения алгоритма ранжирования**.

А вот:

```text
backup_before_force_match
             ↓
        recognizer.py
```

есть конкретное изменение:

```python
if best_score < threshold:
    best_id = None
    status = "NO_MATCH"
```

заменено на:

```python
best_id = best["id"]

if best_score < threshold:
    status = "FORCED_MATCH"
```

То есть **ошибок в папках сейчас визуально может быть очень много именно потому, что `classify_final_test.py` безусловно раскладывает TOP-1**, а TOP-1 при `FORCED_MATCH` существует даже для слабого результата.

Но сначала нам надо получить **новый JSON на свежих v33**. Тогда мы сможем разделить:

- ошибка самого распознавания;
- ошибка `FORCED_MATCH`;
- ошибка оптимизации;
- проблема конкретных fingerprint;
- проблема первого кандидата.

Пришли вывод двух команд выше. После этого дам точную команду запуска нового контрольного теста.

---

### 👤 **User** — 2026-08-15 03:04:21

\x1c \x03(\t\x12\x15\n\rxpu_recv_list\x18\x1d \x03(\t\x12\x15\n\rxpu_start_idx\x18\x1e \x01(\x05\x12\x13\n\x0bxpu_end_idx\x18\x1f \x01(\x05\x12\x19\n\nuse_ps_gpu\x18  \x01(\x08:\x05\x66\x61lse\x12!\n\x19user_define_dump_filename\x18! \x01(\t\x12\x33\n%scale_sparse_gradient_with_batch_size\x18\" \x01(\x08:\x04true\x12\x10\n\x08trainers\x18# \x03(\x05\x12\x12\n\ntrainer_id\x18$ \x01(\x05\x12\x12\n\nfleet_desc\x18% \x01(\t\x12%\n\x16is_dump_in_simple_mode\x18& \x01(\x08:\x05\x66\x61lse\x12\x1b\n\x10\x64ump_fields_mode\x18\' \x01(\t:\x01w\x12\x1c\n\x11\x64ump_num_decimals\x18( \x01(\x05:\x01\x39\x12\x1c\n\ruse_gpu_graph\x18) \x01(\x08:\x05\x66\x61lse\x12?\n\rhogwild_param\x18\x65 \x01(\x0b\x32(.paddle.framework.HogwildWorkerParameter\x12\x41\n\x0e\x64ownpour_param\x18g \x01(\x0b\x32).paddle.framework.DownpourWorkerParameter\x12\x44\n\x10pull_dense_param\x18\x66 \x01(\x0b\x32*.paddle.framework.PullDenseWorkerParameter\x12?\n\rsection_param\x18h \x01(\x0b\x32(.paddle.framework.SectionWorkerParameter\x12J\n\x13heter_section_param\x18i \x01(\x0b\x32-.paddle.framework.HeterSectionWorkerParameter\x12\x32\n\tdata_desc\x18\xc9\x01 \x01(\x0b\x32\x1e.paddle.framework.DataFeedDesc\"B\n\x16HogwildWorkerParameter\x12\x10\n\x08skip_ops\x18\x01 \x03(\t\x12\x16\n\x0estat_var_names\x18\x02 \x03(\t\"\xa0\x02\n\x17\x44ownpourWorkerParameter\x12\x36\n\x0csparse_table\x18\x01 \x03(\x0b\x32 .paddle.framework.TableParameter\x12\x35\n\x0b\x64\x65nse_table\x18\x02 \x03(\x0b\x32 .paddle.framework.TableParameter\x12\x10\n\x08skip_ops\x18\x03 \x03(\t\x12\x37\n\x0eprogram_config\x18\x04 \x03(\x0b\x32\x1f.paddle.framework.ProgramConfig\x12\x19\n\x0bpush_sparse\x18\x05 \x01(\x08:\x04true\x12\x18\n\npush_dense\x18\x06 \x01(\x08:\x04true\x12\x16\n\x0estat_var_names\x18\x07 \x03(\t\"\xa5\x02\n\x16SectionWorkerParameter\x12\x37\n\x0esection_config\x18\x01 \x01(\x0b\x32\x1f.paddle.framework.SectionConfig\x12\x15\n\nqueue_size\x18\x02 \x01(\x05:\x01\x31\x12\x15\n\nsync_steps\x18\x03 \x01(\x03:\x01\x31\x12\x1c\n\x11start_cpu_core_id\x18\x04 \x01(\x05:\x01\x31\x12\x17\n\x0fparam_need_sync\x18\x05 \x03(\t\x12\x18\n\x10num_microbatches\x18\x06 \x01(\x05\x12\x1e\n\x13num_pipeline_stages\x18\x07 \x01(\x05:\x01\x31\x12\x19\n\x0epipeline_stage\x18\x08 \x01(\x05:\x01\x31\x12\x18\n\rschedule_mode\x18\t \x01(\x05:\x01\x30\"\x90\x02\n\x1bHeterSectionWorkerParameter\x12\x37\n\x0esection_config\x18\x01 \x01(\x0b\x32\x1f.paddle.framework.SectionConfig\x12\x15\n\nqueue_size\x18\x02 \x01(\x05:\x01\x31\x12\x15\n\nsync_steps\x18\x03 \x01(\x03:\x01\x31\x12\x1c\n\x11start_cpu_core_id\x18\x04 \x01(\x05:\x01\x31\x12\x17\n\x0fparam_need_sync\x18\x05 \x03(\t\x12\x18\n\x10num_microbatches\x18\x06 \x01(\x05\x12\x1e\n\x13num_pipeline_stages\x18\x07 \x01(\x05:\x01\x31\x12\x19\n\x0epipeline_stage\x18\x08 \x01(\x05:\x01\x31\"\xa6\x02\n\rSectionConfig\x12\x39\n\x0cprogram_desc\x18\x01 \x01(\x0b\x32#.paddle.framework.proto.ProgramDesc\x12\x34\n\x05place\x18\x02 \x01(\x0e\x32%.paddle.framework.SectionConfig.Place\x12\x16\n\x0b\x63oncurrency\x18\x03 \x01(\x05:\x01\x31\x12\x1c\n\x14section_in_var_names\x18\x04 \x03(\t\x12\x1d\n\x15section_out_var_names\x18\x05 \x03(\t\x12\x14\n\x08place_id\x18\x06 \x01(\x05:\x02-1\"9\n\x05Place\x12\x0c\n\x08\x43PUPlace\x10\x00\x12\r\n\tCUDAPlace\x10\x01\x12\x13\n\x0f\x43UDAPinnedPlace\x10\x02\"\xb1\x01\n\x0b\x46\x65tchConfig\x12\x17\n\x0f\x66\x65tch_var_names\x18\x01 \x03(\t\x12\x1c\n\x14\x66\x65tch_var_str_format\x18\x02 \x03(\t\x12\x19\n\x0cprint_period\x18\x03 \x01(\x05:\x03\x31\x30\x30\x12;\n\x06method\x18\x04 \x01(\x0e\x32$.paddle.framework.FetchConfig.Method:\x05PRINT\"\x13\n\x06Method\x12\t\n\x05PRINT\x10\x00\"\x9c\x01\n\x15\x41\x64justInsWeightConfig\x12\x1a\n\x0bneed_adjust\x18\x01 \x01(\x08:\x05\x66\x61lse\x12\x12\n\x08nid_slot\x18\x02 \x01(\t:\x00\x12\x1d\n\x12nid_adjw_threshold\x18\x03 \x01(\x02:\x01\x30\x12\x19\n\x0enid_adjw_ratio\x18\x04 \x01(\x02:\x01\x30\x12\x19\n\x0fins_weight_slot\x18\x05 \x01(\t:\x00\"1\n\x12TableDependencyMap\x12\x0b\n\x03key\x18\x01 \x02(\x05\x12\x0e\n\x06values\x18\x02 \x03(\x05\"\x8e\x03\n\x0f\x43opyTableConfig\x12\x18\n\tneed_copy\x18\x01 \x01(\x08:\x05\x66\x61lse\x12\x16\n\tbatch_num\x18\x02 \x01(\x05:\x03\x31\x30\x30\x12\x19\n\x11src_sparse_tables\x18\x03 \x03(\x05\x12\x1a\n\x12\x64\x65st_sparse_tables\x18\x04 \x03(\x05\x12\x18\n\x10src_dense_tables\x18\x05 \x03(\x05\x12\x19\n\x11\x64\x65st_dense_tables\x18\x06 \x03(\x05\x12\x14\n\x0csrc_var_list\x18\x07 \x03(\t\x12\x15\n\rdest_var_list\x18\x08 \x03(\t\x12$\n\x15\x64\x65nse_pull_after_copy\x18\t \x01(\x08:\x05\x66\x61lse\x12$\n\x16sparse_copy_by_feasign\x18\n \x01(\x08:\x04true\x12 \n\x11\x65nable_dependency\x18\x0b \x01(\x08:\x05\x66\x61lse\x12\x42\n\x14table_dependency_map\x18\x0c \x03(\x0b\x32$.paddle.framework.TableDependencyMap\"*\n\x0c\x43ondTableMap\x12\x0b\n\x03key\x18\x01 \x02(\x05\x12\r\n\x05value\x18\x02 \x02(\x05\"\xe2\x01\n\rProgramConfig\x12\x12\n\nprogram_id\x18\x01 \x02(\t\x12\x1c\n\x14push_sparse_table_id\x18\x02 \x03(\x05\x12\x1b\n\x13push_dense_table_id\x18\x03 \x03(\x05\x12\x1c\n\x14pull_sparse_table_id\x18\x04 \x03(\x05\x12\x1b\n\x13pull_dense_table_id\x18\x05 \x03(\x05\x12G\n\x1fpartial_pushdense_condtable_map\x18\n \x03(\x0b\x32\x1e.paddle.framework.CondTableMap\"\x95\x01\n\x18PullDenseWorkerParameter\x12\x14\n\tthreshold\x18\x01 \x01(\x05:\x01\x31\x12\x12\n\ndevice_num\x18\x02 \x01(\x05\x12\x18\n\rsleep_time_ms\x18\x03 \x01(\x05:\x01\x32\x12\x35\n\x0b\x64\x65nse_table\x18\x04 \x03(\x0b\x32 .paddle.framework.TableParameter\"\xea\x02\n\x0eTableParameter\x12\x10\n\x08table_id\x18\x01 \x01(\x04\x12\x18\n\x10\x64\x65nse_value_name\x18\x02 \x03(\t\x12\x17\n\x0f\x64\x65nse_grad_name\x18\x03 \x03(\t\x12\x1d\n\x15push_dense_wait_times\x18\x05 \x03(\x05\x12\x17\n\x0fsparse_key_name\x18\x06 \x03(\t\x12\x19\n\x11sparse_value_name\x18\x07 \x03(\t\x12\x18\n\x10sparse_grad_name\x18\x08 \x03(\t\x12\x1e\n\x16push_sparse_wait_times\x18\t \x03(\x05\x12\x0f\n\x07\x65mb_dim\x18\n \x01(\x05\x12\x0f\n\x07\x66\x65\x61_dim\x18\x0b \x01(\x05\x12\x16\n\x0elabel_var_name\x18\x0c \x01(\t\x12\x17\n\x08is_local\x18\r \x01(\x08:\x05\x66\x61lse\x12\x17\n\x08is_async\x18\x0e \x01(\x08:\x05\x66\x61lse\x12\x1a\n\x12\x61sync_wait_op_name\x18\x0f \x01(\tB\x02H\x03')
./.venv/lib64/python3.12/site-packages/paddle/base/framework.py:308:    "relu6": ["threshold"],
./.venv/lib64/python3.12/site-packages/paddle/base/framework.py:7011:                        if name.endswith("_threshold"):
./.venv/lib64/python3.12/site-packages/paddle/static/amp/fp16_lists.py:238:    'top_k',
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:90:        topk_out, topk_indices = _legacy_C_ops.top_k_v2(
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:115:        type="top_k_v2",
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:141:    num_thresholds=2**12 - 1,
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:171:        num_thresholds(int, optional): The number of thresholds to use when discretizing
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:261:        stat_pos = paddle.zeros(shape=[1, num_thresholds + 1], dtype="int64")
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:262:        stat_neg = paddle.zeros(shape=[1, num_thresholds + 1], dtype="int64")
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:270:            num_thresholds,
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:302:        shape=[(1 + slide_steps) * (num_thresholds + 1) + 1],
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:307:        shape=[(1 + slide_steps) * (num_thresholds + 1) + 1],
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:313:        persistable=True, dtype='int64', shape=[1, num_thresholds + 1]
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:316:        persistable=True, dtype='int64', shape=[1, num_thresholds + 1]
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:337:            "num_thresholds": num_thresholds,
./.venv/lib64/python3.12/site-packages/paddle/static/nn/metric.py:357:            "num_thresholds": num_thresholds,
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quant_config.py:103:    "top_k_v2": [["X"], ["Out", "Indices"]],
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quant2_int8_onednn_pass.py:88:        self._weight_thresholds = {}
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quant2_int8_onednn_pass.py:103:        graph = self._gather_weight_thresholds_from_fake(graph)
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quant2_int8_onednn_pass.py:215:    def _gather_weight_thresholds_from_fake(self, graph):
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quant2_int8_onednn_pass.py:223:                    self._weight_thresholds[input_name] = np.array(
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quant2_int8_onednn_pass.py:228:                    self._weight_thresholds[input_name] = np.array(
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quant2_int8_onednn_pass.py:236:            if op.op().has_attr("out_threshold"):
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quant2_int8_onednn_pass.py:237:                attr_scale = op.op().attr("out_threshold")
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quant2_int8_onednn_pass.py:394:        scales = self._weight_thresholds[output_var_name]
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quantization_pass.py:1799:                    # For compatibility, we save output threshold by two methods.
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quantization_pass.py:1800:                    op_node.op()._set_attr("out_threshold", float(scale_value))
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/quantization_pass.py:1809:                        argname_index[0] + str(argname_index[1]) + "_threshold",
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/cal_kl_threshold.py:81:def cal_kl_threshold(hist, bin_width, bits):
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/cal_kl_threshold.py:83:    Using the KL-divergence method to get the more precise threshold.
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/post_training_quantization.py:34:from .cal_kl_threshold import cal_kl_threshold
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/post_training_quantization.py:186:                get the KL threshold for quantized activations and get the abs_max
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/post_training_quantization.py:191:                algo= 'hist', get the value of 'hist_percent' quantile as the threshold.
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/post_training_quantization.py:194:            hist_percent(float, optional): The threshold of algo 'hist' for activations.
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/post_training_quantization.py:363:        self._quantized_var_threshold = {}
./.venv/lib64/python3.12/site-packages/paddle/static/quantization/post_training_quantization.py:372:        # The threshold for algo = abs_max, mse or avg
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:04:22

Да, это уже очень полезный результат. И похоже, мы нашли важную развилку.

То, что ты сейчас прислал, **не является выводом наших `grep` по проекту** — туда попал огромный бинарно/экранированный фрагмент из `.venv` (Paddle). Его можно полностью игнорировать.

Но главное по предыдущим diff уже ясно:

### Что произошло

`backup_before_optimization` → текущий `recognizer.py`:

- алгоритм ранжирования кандидатов **не изменён**;
- добавлена многопоточность `ThreadPoolExecutor`;
- дескрипторы `environment/color/spatial` теперь считаются один раз на фотографию;
- добавлен whitelist fingerprints;
- в `SceneAnalyzer.compare()` передаются заранее рассчитанные дескрипторы.

То есть **сама оптимизация не должна была изменить результат**, если `CompactDescriptor` и `SceneAnalyzer` остались прежними.

А вот:

`backup_before_force_match` → текущий `recognizer.py`

имеет реальное изменение поведения:

```python
if best_score < threshold:
    best_id = None
    status = "NO_MATCH"
```

было заменено на:

```python
best_id = best["id"]

if best_score < threshold:
    status = "FORCED_MATCH"
```

Это **может объяснить огромное количество визуально неправильных папок**.

---

## Сейчас предлагаю сделать контрольный тест правильно

Нам нужно не `classify_final_test.py`, а сначала заново получить `final_test_78_95.json`.

Но перед запуском найдём **только наши файлы**, исключив `.venv`, чтобы больше не ловить мусор Paddle.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== FINAL TEST REFERENCES ==="

grep -Rni \
"final_test_78_95.json" \
--exclude-dir=.venv \
--exclude-dir=.git \
--exclude-dir=__pycache__ \
--include="*.py" \
--include="*.sh" \
.
```

И отдельно:

```bash
echo
echo "=== RECOGNIZER CALLS ==="

grep -RniE \
'recognize\(|scene-fingerprint recognize|recognizer\.recognize' \
--exclude-dir=.venv \
--exclude-dir=.git \
--exclude-dir=__pycache__ \
--include="*.py" \
--include="*.sh" \
.
```

### Почему именно так

После этого мы должны получить примерно такую цепочку:

```text
test
 ↓
recognize
 ↓
SceneRecognizer
 ↓
78_v33 ... 95_v33
 ↓
final_test_78_95.json
 ↓
classify_final_test.py
 ↓
test_classified
```

И вот **на этапе `recognize`** мы сделаем свежий JSON на только что пересозданных `78_v33–95_v33`.

После этого уже можно будет сравнить:

```text
старый результат
        VS
новый результат
```

а затем отдельно сделать эксперимент:

```text
старый алгоритм + свежие v33
```

и

```text
текущий оптимизированный алгоритм + свежие v33
```

Это даст нам абсолютно чистый ответ, **оптимизация виновата или нет**.

И я бы пока **не трогал `recognizer.py`**. Сначала получим контрольные данные.

---

### 👤 **User** — 2026-08-15 03:04:44

=== FINAL TEST REFERENCES ===
./classify_final_test.py:5:RESULTS = Path("final_test_78_95.json")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:04:46

Да. Теперь картина становится намного яснее.

**`classify_final_test.py` не является источником ошибок распознавания.** Он только берет уже готовый `final_test_78_95.json` и раскладывает фотографии по `best_id`.

А по двум diff мы видим важное:

1. **До оптимизации алгоритм распознавания в `recognizer.py` практически не менялся.**
2. Оптимизация добавила:
   - `ThreadPoolExecutor`;
   - предварительный расчет `environment/color/spatial`;
   - передачу этих дескрипторов в `analyzer.compare()`.
3. **Но отдельно был изменен алгоритм принятия результата:**
   ```python
   if best_score < threshold:
       best_id = None
       status = "NO_MATCH"
   ```
   заменено на:
   ```python
   best_id = best["id"]

   if best_score < threshold:
       status = "FORCED_MATCH"
   ```
   
   То есть сейчас **даже плохое совпадение принудительно превращается в адрес**.

Именно поэтому статистика:

```text
TOTAL COPIED: 262
```

сама по себе **вообще не говорит о качестве распознавания**. Мы сейчас физически раскладываем все 262 фотографии, даже если алгоритм уверен, что это не тот адрес.

### Предлагаю сейчас не менять код

Сначала сделаем **чистый диагностический прогон текущего распознавания**, чтобы понять, где именно появились ошибки.

Нам нужны три вещи:

- score;
- margin между №1 и №2;
- `global/environment/color/spatial`;
- `candidate_2`;
- status/confidence.

И самое главное — сравнить это с распределением по адресам.

---

### 1. Сначала найдем, кто создает `final_test_78_95.json`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== WHO CREATES final_test_78_95.json ==="

grep -Rni \
"final_test_78_95.json" \
--exclude-dir=.venv \
--exclude-dir=.git \
.
```

И еще:

```bash
echo
echo "=== WHO RUNS recognize ==="

grep -RniE \
"recognize|SceneRecognizer|recognize_folder|recognize\(" \
--include="*.py" \
--include="*.sh" \
--exclude-dir=.venv \
--exclude-dir=.git \
. | head -200
```

---

### 2. Затем посмотрим сам JSON

После этого выполни:

```bash
echo
echo "=== final_test_78_95.json ==="

ls -lh final_test_78_95.json

echo
echo "=== FIRST RESULT ==="

python3 - <<'PY'
import json
from pathlib import Path

p = Path("final_test_78_95.json")

text = p.read_text(encoding="utf-8")
lines = text.splitlines()

start = next(
    i for i, line in enumerate(lines)
    if line.strip() == "["
)

data = json.loads("\n".join(lines[start:]))

print("TOTAL:", len(data))
print()

for x in data[:3]:
    print(json.dumps(x, ensure_ascii=False, indent=2))
    print("=" * 80)
PY
```

---

### 3. И сразу получим настоящую статистику качества

Вот этот кусок особенно важен:

```bash
python3 - <<'PY'
import json
from pathlib import Path
from collections import Counter

p = Path("final_test_78_95.json")

text = p.read_text(encoding="utf-8")
lines = text.splitlines()

start = next(
    i for i, line in enumerate(lines)
    if line.strip() == "["
)

data = json.loads("\n".join(lines[start:]))

print("=" * 80)
print("RECOGNITION DIAGNOSTICS")
print("=" * 80)

print("TOTAL:", len(data))

scores = [
    float(x["score"])
    for x in data
    if x.get("score") is not None
]

margins = [
    float(x["margin"])
    for x in data
    if x.get("margin") is not None
]

print()
print("SCORE:")
print("  min :", min(scores))
print("  mean:", sum(scores) / len(scores))
print("  max :", max(scores))

print()
print("MARGIN:")
print("  min :", min(margins))
print("  mean:", sum(margins) / len(margins))
print("  max :", max(margins))

print()
print("STATUS:")
print(Counter(
    x.get("status")
    for x in data
))

print()
print("CONFIDENCE:")
print(Counter(
    x.get("confidence")
    for x in data
))

print()
print("TOP-1:")
print(Counter(
    x.get("best_id")
    for x in data
))

print()
print("LOW SCORE < 0.65:")

low = [
    x for x in data
    if x.get("score") is not None
    and float(x["score"]) < 0.65
]

print("COUNT:", len(low))

for x in sorted(
    low,
    key=lambda x: float(x["score"])
)[:20]:

    print(
        f'{Path(x["file"]).name:35} '
        f'score={x["score"]} '
        f'margin={x.get("margin")} '
        f'best={x.get("best_id")} '
        f'candidate2={x.get("candidate_2")} '
        f'candidate2_score={x.get("candidate_2_score")}'
    )
PY
```

### Что это нам даст

Если окажется, например:

```text
SCORE:
  min : 0.31
  mean: 0.58
  max : 0.91

LOW SCORE < 0.65:
COUNT: 97
```

то мы сразу увидим, что **97 фотографий раньше должны были быть `NO_MATCH`, а теперь они насильно разложены по адресам**.

А если scores нормальные, например:

```text
mean: 0.82
```

но ошибки все равно массовые — тогда проблема **не в `FORCED_MATCH`**, а в самом сравнении `SceneAnalyzer`.

И вот тогда уже надо смотреть второй очень важный diff:

```text
backup_before_optimization
        VS
текущий scene_analyzer.py
```

Потому что твой первый diff показывает только `recognizer.py`. **Оптимизация могла изменить не сам порядок выбора кандидата, а формулу `compare()` в `scene_analyzer.py`.**

После этих команд пришли вывод. По нему уже можно будет точно определить: **у нас проблема в forced match, в измененной формуле score, в дескрипторах или в fingerprint v33.**

---

### 👤 **User** — 2026-08-15 03:05:45

echo
echo "=== final_test_78_95.json ==="

ls -lh final_test_78_95.json

echo
echo "=== FIRST RESULT ==="

python3 - <<'PY'
import json
from pathlib import Path

p = Path("final_test_78_95.json")

text = p.read_text(encoding="utf-8")
lines = text.splitlines()

start = next(
    i for i, line in enumerate(lines)
    if line.strip() == "["
)

data = json.loads("\n".join(lines[start:]))

print("TOTAL:", len(data))
print()

for x in data[:3]:
    print(json.dumps(x, ensure_ascii=False, indent=2))
    print("=" * 80)
PY

---

### 🤖 **Assistant** — 2026-08-15 03:05:46

Да, запускай именно эту команду. Она ничего не изменяет — только читает `final_test_78_95.json` и показывает первые 3 результата.

После выполнения пришли **весь вывод**, особенно поля:

```text
best_id
score
margin
confidence
status
global
environment
color
spatial
candidate_2
candidate_2_score
```

По ним сразу проверим, **ошибка появилась из-за forced match или уже внутри самого `SceneAnalyzer.compare()`**.

---

### 👤 **User** — 2026-08-15 03:05:54

=== WHO CREATES final_test_78_95.json ===
./classify_final_test.py:5:RESULTS = Path("final_test_78_95.json")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=== WHO RUNS recognize ==="

grep -RniE \
"recognize|SceneRecognizer|recognize_folder|recognize\(" \
--include="*.py" \
--include="*.sh" \
--exclude-dir=.venv \
--exclude-dir=.git \
. | head -200

=== WHO RUNS recognize ===
./classify_test.sh:288:recognized = 0
./classify_test.sh:380:            recognized += 1
./classify_test.sh:475:print(f"Recognized:  {recognized}")
./app/core/scene_analyzer.py:377:        supplied already calculated by the recognizer.
./app/core/recognizer.py:15:class SceneRecognizer:
./app/core/recognizer.py:17:    Scene Fingerprint v3.3 compact recognizer.
./app/core/recognizer.py:97:    def recognize_folder(
./app/core/recognizer.py:115:            f"[Recognizer] "
./app/core/recognizer.py:161:                    f"[Recognizer] SKIP "
./app/core/recognizer.py:176:                    f"[Recognizer] SKIP old "
./app/core/recognizer.py:197:            "[Recognizer] Fingerprints: "
./app/core/recognizer.py:256:            f"[Recognizer] CPU workers: "
./app/core/recognizer.py:310:                        f"[Recognizer] SKIP "
./app/core/recognizer.py:484:    def recognize(
./app/core/recognizer.py:490:        return self.recognize_folder(
./app/main.py:6:from app.core.recognizer import SceneRecognizer
./app/main.py:10:recognizer = SceneRecognizer(settings, embedder, manager)
./app/main.py:19:        recognize_tab = ui.tab("Распознавание")
./app/main.py:38:        with ui.tab_panel(recognize_tab):
./app/main.py:48:                    rows = recognizer.recognize_folder(
./app/cli.py:11:from app.core.recognizer import SceneRecognizer
./app/cli.py:124:    # RECOGNIZE
./app/cli.py:127:    recognize_parser = subparsers.add_parser(
./app/cli.py:128:        "recognize",
./app/cli.py:129:        help="Recognize images",
./app/cli.py:132:    recognize_parser.add_argument(
./app/cli.py:137:    recognize_parser.add_argument(
./app/cli.py:144:    recognize_parser.add_argument(
./app/cli.py:151:    recognize_parser.add_argument(
./app/cli.py:158:    recognize_parser.add_argument(
./app/cli.py:165:    recognize_parser.add_argument(
./app/cli.py:589:    # RECOGNIZE
./app/cli.py:592:    if args.command == "recognize":
./app/cli.py:613:        recognizer = SceneRecognizer(
./app/cli.py:629:            recognizer.recognize_folder(
./app/ocr/ocr_pipeline.py:40:    def recognize(self, image_path: str | Path) -> list[OCRResult]:
./app/ocr/ocr_pipeline.py:102:    results = ocr.recognize(
./upgrade_v31_fix.sh:13:cp -a app/core/recognizer.py "$BACKUP/" 2>/dev/null || true
./upgrade_v31_fix.sh:82:print("  uv run scene-fingerprint recognize data/input/new --top-k 5 --threshold 0.65")
./fix_v31_final.sh:19:    app/core/recognizer.py \
./fix_v31_final.sh:709:echo "[4/6] Writing recognizer.py"
./fix_v31_final.sh:711:cat > app/core/recognizer.py <<'PY'
./fix_v31_final.sh:719:class SceneRecognizer:
./fix_v31_final.sh:935:    def recognize_folder(
./fix_v31_final.sh:1174:    def __init__(self, recognizer):
./fix_v31_final.sh:1175:        self.recognizer = recognizer
./fix_v31_final.sh:1182:        yield from self.recognizer.analyze(
./fix_v31_final.sh:1193:    app/core/recognizer.py \
./fix_v31_final.sh:1277:echo "  uv run scene-fingerprint recognize data/input/new --top-k 5 --threshold 0.65"
./upgrade_v31.sh:21:    app/core/recognizer.py \
./upgrade_v31.sh:644:echo "[3/5] Writing recognizer.py"
./upgrade_v31.sh:646:cat > app/core/recognizer.py <<'PY'
./upgrade_v31.sh:657:class SceneRecognizer:
./upgrade_v31.sh:884:    def recognize_folder(
./upgrade_v31.sh:1047:from app.core.recognizer import SceneRecognizer
./upgrade_v31.sh:1053:        self.recognizer = SceneRecognizer(
./upgrade_v31.sh:1063:        yield from self.recognizer.analyze(
./upgrade_v31.sh:1081:from app.core.recognizer import SceneRecognizer
./upgrade_v31.sh:1112:        "recognize",
./upgrade_v31.sh:1113:        help="Recognize images against fingerprints",
./upgrade_v31.sh:1187:    # RECOGNIZE
./upgrade_v31.sh:1190:    if args.cmd == "recognize":
./upgrade_v31.sh:1201:        recognizer = SceneRecognizer(
./upgrade_v31.sh:1206:        for result in recognizer.recognize_folder(
./upgrade_v31.sh:1289:    app/core/recognizer.py \
./upgrade_v31.sh:1315:echo "  uv run scene-fingerprint recognize data/input/new --top-k 5 --threshold 0.65"
./backup_v31_fix_20260808_230926/scene_analyzer.py:3:from app.core.recognizer import SceneRecognizer
./backup_v31_fix_20260808_230926/scene_analyzer.py:9:        self.recognizer = SceneRecognizer(
./backup_v31_fix_20260808_230926/scene_analyzer.py:19:        yield from self.recognizer.analyze(
./backup_v31_fix_20260808_230926/recognizer.py:11:class SceneRecognizer:
./backup_v31_fix_20260808_230926/recognizer.py:238:    def recognize_folder(
./backup_v31_fix_20260808_230926/cli.py:10:from app.core.recognizer import SceneRecognizer
./backup_v31_fix_20260808_230926/cli.py:41:        "recognize",
./backup_v31_fix_20260808_230926/cli.py:42:        help="Recognize images against fingerprints",
./backup_v31_fix_20260808_230926/cli.py:116:    # RECOGNIZE
./backup_v31_fix_20260808_230926/cli.py:119:    if args.cmd == "recognize":
./backup_v31_fix_20260808_230926/cli.py:130:        recognizer = SceneRecognizer(
./backup_v31_fix_20260808_230926/cli.py:135:        for result in recognizer.recognize_folder(
./scripts/sort_test_and_report_v2.py:67:        [Recognizer]
./scripts/sort_test_and_report_v2.py:99:        "recognize",
./scripts/sort_test_and_report_v2.py:133:            f"recognize завершился с кодом {process.returncode}"
./scripts/benchmark_test_v1.py:93:        "recognize",
./scripts/benchmark_test_v1.py:126:            f"recognize failed: {proc.returncode}"
./scripts/sort_test_and_report.py:12:RECOGNITION_JSON = Path("/tmp/recognize_test.json")
./scripts/sort_test_and_report.py:27:    # [Recognizer] ...
./scripts/sort_test_and_report.py:144:        # если recognize уже начал их отдавать.
./backup_v31_dynamic_20260808_231245/app/core/scene_analyzer.py:6:    def __init__(self, recognizer):
./backup_v31_dynamic_20260808_231245/app/core/scene_analyzer.py:7:        self.recognizer = recognizer
./backup_v31_dynamic_20260808_231245/app/core/scene_analyzer.py:14:        yield from self.recognizer.analyze(
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py:8:class SceneRecognizer:
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py:140:    def recognize_folder(
./backup_v31_final_20260808_231056/app/core/scene_analyzer.py:3:from app.core.recognizer import SceneRecognizer
./backup_v31_final_20260808_231056/app/core/scene_analyzer.py:9:        self.recognizer = SceneRecognizer(
./backup_v31_final_20260808_231056/app/core/scene_analyzer.py:19:        yield from self.recognizer.analyze(
./backup_v31_final_20260808_231056/app/core/recognizer.py:11:class SceneRecognizer:
./backup_v31_final_20260808_231056/app/core/recognizer.py:238:    def recognize_folder(
./backup_v31_final_20260808_231056/cli.py:10:from app.core.recognizer import SceneRecognizer
./backup_v31_final_20260808_231056/cli.py:41:        "recognize",
./backup_v31_final_20260808_231056/cli.py:42:        help="Recognize images against fingerprints",
./backup_v31_final_20260808_231056/cli.py:116:    # RECOGNIZE
./backup_v31_final_20260808_231056/cli.py:119:    if args.cmd == "recognize":
./backup_v31_final_20260808_231056/cli.py:130:        recognizer = SceneRecognizer(
./backup_v31_final_20260808_231056/cli.py:135:        for result in recognizer.recognize_folder(
./classify_test.py:12:from app.core.recognizer import SceneRecognizer
./classify_test.py:33:# Existing recognizer settings.
./classify_test.py:288:    recognizer = SceneRecognizer(
./classify_test.py:303:    # Use the existing recognizer.
./classify_test.py:309:        "[Recognizer] Starting recognition..."
./classify_test.py:312:    results = recognizer.recognize_folder(
./classify_test.py:375:            # was skipped by recognizer.
./upgrade_patch_tokens.sh:9:cp -a app/core/embedder.py app/core/fingerprint.py app/core/recognizer.py app/core/scene_analyzer.py "backup_patch_tokens_${STAMP}/"
./upgrade_patch_tokens.sh:449:echo "[4/4] Writing recognizer.py and scene_analyzer.py..."
./upgrade_patch_tokens.sh:450:cat > app/core/recognizer.py <<'PY'
./upgrade_patch_tokens.sh:455:class SceneRecognizer:
./upgrade_patch_tokens.sh:461:    def recognize_folder(
./upgrade_patch_tokens.sh:782:    app/core/recognizer.py \
./upgrade_patch_tokens.sh:795:echo "  uv run scene-fingerprint recognize data/input/new --top-k 5 --threshold 0.50"
./backup_patch_tokens_20260808_131532/scene_analyzer.py:160:        recognizer/API/GUI code.
./backup_patch_tokens_20260808_131532/recognizer.py:4:class SceneRecognizer:
./backup_patch_tokens_20260808_131532/recognizer.py:10:    def recognize_folder(self, folder, top_k=5, threshold=0.65):
./app_backup_before_patch/core/scene_analyzer.py:160:        recognizer/API/GUI code.
./app_backup_before_patch/core/recognizer.py:4:class SceneRecognizer:
./app_backup_before_patch/core/recognizer.py:10:    def recognize_folder(self, folder, top_k=5, threshold=0.65):
./app_backup_before_patch/main.py:6:from app.core.recognizer import SceneRecognizer
./app_backup_before_patch/main.py:10:recognizer = SceneRecognizer(settings, embedder, manager)
./app_backup_before_patch/main.py:19:        recognize_tab = ui.tab("Распознавание")
./app_backup_before_patch/main.py:38:        with ui.tab_panel(recognize_tab):
./app_backup_before_patch/main.py:48:                    rows = recognizer.recognize_folder(
./app_backup_before_patch/cli.py:7:from app.core.recognizer import SceneRecognizer
./app_backup_before_patch/cli.py:35:    # RECOGNIZE
./app_backup_before_patch/cli.py:38:    recognize = sub.add_parser(
./app_backup_before_patch/cli.py:39:        "recognize",
./app_backup_before_patch/cli.py:40:        help="Recognize images against fingerprints",
./app_backup_before_patch/cli.py:43:    recognize.add_argument("folder")
./app_backup_before_patch/cli.py:45:    recognize.add_argument(
./app_backup_before_patch/cli.py:51:    recognize.add_argument(
./app_backup_before_patch/cli.py:96:    # RECOGNIZE
./app_backup_before_patch/cli.py:99:    if args.cmd == "recognize":
./app_backup_before_patch/cli.py:107:        recognizer = SceneRecognizer(
./app_backup_before_patch/cli.py:113:        results = recognizer.recognize_folder(
./upgrade_v3.sh:8:for f in app/core/fingerprint.py app/core/recognizer.py app/core/scene_analyzer.py app/cli.py; do
./upgrade_v3.sh:239:cat > app/core/recognizer.py <<'PY'
./upgrade_v3.sh:243:class SceneRecognizer:
./upgrade_v3.sh:248:    def recognize_folder(self, folder, top_k=5, threshold=0.65):
./upgrade_v3.sh:276:uv run python -m py_compile app/core/fingerprint.py app/core/scene_analyzer.py app/core/recognizer.py
./upgrade_v3.sh:284:echo "Recognize:"
./upgrade_v3.sh:285:echo "  uv run scene-fingerprint recognize data/input/new --top-k 5 --threshold 0.65"
./classify_test_top1.sh:591:recognized = (
./classify_test_top1.sh:597:    f"Recognized:  {recognized}"
./upgrade_v31_final.sh:19:cp -a app/core/recognizer.py "$BACKUP/app/core/" 2>/dev/null || true
./upgrade_v31_final.sh:552:echo "[4/7] Rebuilding recognizer.py"
./upgrade_v31_final.sh:554:cat > app/core/recognizer.py <<'PY'
./upgrade_v31_final.sh:562:class SceneRecognizer:
./upgrade_v31_final.sh:694:    def recognize_folder(
./upgrade_v31_final.sh:868:    def __init__(self, recognizer):
./upgrade_v31_final.sh:869:        self.recognizer = recognizer
./upgrade_v31_final.sh:876:        yield from self.recognizer.analyze(
./upgrade_v31_final.sh:887:    app/core/recognizer.py \
./upgrade_v31_final.sh:981:echo "Recognize:"
./upgrade_v31_final.sh:983:echo "  uv run scene-fingerprint recognize data/input/new --top-k 5 --threshold 0.65"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:05:55

Вот теперь мы нашли важную вещь.

`final_test_78_95.json` **вообще не создаётся `classify_final_test.py`** — этот файл только читает его.

А реальный запуск распознавания, судя по выводу, находится в:

```text
classify_test.sh
classify_test.py
scripts/sort_test_and_report_v2.py
```

Причём `classify_test.py` напрямую вызывает:

```python
recognizer.recognize_folder(...)
```

То есть именно его сейчас надо разобрать.

И ещё важнее: у нас уже есть очень сильная зацепка. Текущий `recognizer.py` отличается от `backup_before_force_match` **не только forced match**. Он изменил способ расчёта `SceneAnalyzer.compare()`:

```python
score = self.analyzer.compare(
    Path(path),
    fingerprint_id,
    query_global=query_embedding,
    query_environment=...,
    query_color=...,
    query_spatial=...,
)
```

Следовательно, **оптимизация действительно могла изменить результат**, даже если финальная логика выбора кандидата почти осталась прежней.

### Сейчас ничего не откатываем

Сначала надо установить, **какая именно версия `scene_analyzer.py` была до оптимизации** и сравнить её с текущей.

Выполни одним блоком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== BACKUPS OF scene_analyzer.py ==="
echo "=============================================="

find . \
  -path './.venv' -prune -o \
  -name 'scene_analyzer.py*' -print \
  | sort

echo
echo "=============================================="
echo "=== CURRENT scene_analyzer.py ==="
echo "=============================================="

ls -lh --time-style=long-iso app/core/scene_analyzer.py*

echo
echo "=============================================="
echo "=== CURRENT COMPARE() ==="
echo "=============================================="

grep -nE \
'def compare|query_global|query_environment|query_color|query_spatial|return score|score =' \
app/core/scene_analyzer.py

echo
echo "=============================================="
echo "=== classify_test.py RECOGNITION ==="
echo "=============================================="

nl -ba classify_test.py | sed -n '270,330p'

echo
echo "=============================================="
echo "=== classify_test.sh RECOGNITION COMMAND ==="
echo "=============================================="

grep -nE \
'python|uv run|recognize|final_test|json|recognition' \
classify_test.sh | head -120
```

### И ещё один очень важный тест

У нас есть backup:

```text
app_backup_before_patch/core/recognizer.py
```

и:

```text
backup_patch_tokens_20260808_131532/recognizer.py
```

Но нам нужен именно **непосредственно предшествующий оптимизации** `scene_analyzer.py`.

Поэтому после первого блока особенно интересует вывод:

```text
find . ... -name 'scene_analyzer.py*'
```

---

### Почему я сейчас не предлагаю просто восстановить `recognizer.py`

Потому что мы уже видим:

**оптимизация ≠ только ThreadPoolExecutor.**

Текущий код теперь заранее считает:

```text
environment
color
spatial
```

и передает их в:

```text
SceneAnalyzer.compare()
```

Если текущий `compare()` использует эти параметры иначе, чем старая версия, то мы получим ровно нашу ситуацию:

> раньше распознавание было хорошим → после оптимизации резко много ошибок.

А `FORCED_MATCH` лишь **маскирует эти ошибки**, превращая плохие результаты в конкретные адреса.

То есть сейчас надо разделить две проблемы:

```text
                 ТЕСТ
                   │
                   ▼
          SceneAnalyzer.compare()
                   │
          ┌────────┴────────┐
          │                 │
      правильный        неправильный
        score               score
          │                 │
          ▼                 ▼
     выбор TOP-1       много ошибок
          │
          ▼
   threshold / forced
      match
```

**Сначала восстановим старую формулу score, не трогая оптимизацию скорости.** Это как раз соответствует твоей первоначальной идее:

> оставить всю оптимизацию, но использовать старый алгоритм распознавания.

Пришли вывод блока выше — после него я дам **точную команду сравнения старого и нового `SceneAnalyzer`**, а не будем гадать.

---

### 👤 **User** — 2026-08-15 03:06:29

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== BACKUPS OF scene_analyzer.py ==="
echo "=============================================="

find . \
  -path './.venv' -prune -o \
  -name 'scene_analyzer.py*' -print \
  | sort

echo
echo "=============================================="
echo "=== CURRENT scene_analyzer.py ==="
echo "=============================================="

ls -lh --time-style=long-iso app/core/scene_analyzer.py*

echo
echo "=============================================="
echo "=== CURRENT COMPARE() ==="
echo "=============================================="

grep -nE \
'def compare|query_global|query_environment|query_color|query_spatial|return scoclassify_test.sh | head -120al_test|json|recognition' \
==============================================
=== BACKUPS OF scene_analyzer.py ===
==============================================
./app_backup_before_patch/core/scene_analyzer.py
./app/core/scene_analyzer.py
./app/core/scene_analyzer.py.backup_before_optimization
./app/core/scene_analyzer.py.bak_before_create_opt
./backup_patch_tokens_20260808_131532/scene_analyzer.py
./backup_v31_dynamic_20260808_231245/app/core/scene_analyzer.py
./backup_v31_final_20260808_231056/app/core/scene_analyzer.py
./backup_v31_fix_20260808_230926/scene_analyzer.py

==============================================
=== CURRENT scene_analyzer.py ===
==============================================
-rw-rw-r-- 1 alexice alexice 12K 2026-08-15 00:26 app/core/scene_analyzer.py
-rw-rw-r-- 1 alexice alexice 10K 2026-08-14 23:56 app/core/scene_analyzer.py.backup_before_optimization
-rw-rw-r-- 1 alexice alexice 11K 2026-08-15 00:13 app/core/scene_analyzer.py.bak_before_create_opt

==============================================
=== CURRENT COMPARE() ===
==============================================
364:    def compare(
368:        query_global=None,
369:        query_environment=None,
370:        query_color=None,
371:        query_spatial=None,
391:        if query_global is None:
392:            query_global = (
398:        query_global = np.asarray(
399:            query_global,
403:        global_score = self.cosine(
404:            query_global,
410:            @ query_global
417:        best_image_score = float(
443:            query_environment is None
444:            or query_color is None
445:            or query_spatial is None
452:                query_environment,
453:                query_color,
454:                query_spatial,
459:        environment_score = (
461:                query_environment,
468:        color_score = (
470:                query_color,
477:        spatial_score = (
479:                query_spatial,
490:        final_score = (

==============================================
=== classify_test.py RECOGNITION ===
==============================================
   270	    # --------------------------------------------------------
   271	    # Initialize model
   272	    # --------------------------------------------------------
   273	
   274	    print(
   275	        "[Model] Loading DINO..."
   276	    )
   277	
   278	    embedder = SceneEmbedder(
   279	        settings
   280	    )
   281	
   282	
   283	    manager = FingerprintManager(
   284	        settings,
   285	        embedder,
   286	    )
   287	
   288	    recognizer = SceneRecognizer(
   289	        settings,
   290	        embedder,
   291	        manager,
   292	    )
   293	
   294	    print(
   295	        "[Model] Ready."
   296	    )
   297	
   298	    print()
   299	
   300	    # --------------------------------------------------------
   301	    # IMPORTANT:
   302	    #
   303	    # Use the existing recognizer.
   304	    # It uses compact v3.3 fingerprints
   305	    # and DOES NOT use patch tokens.
   306	    # --------------------------------------------------------
   307	
   308	    print(
   309	        "[Recognizer] Starting recognition..."
   310	    )
   311	
   312	    results = recognizer.recognize_folder(
   313	        TEST_DIR,
   314	        top_k=TOP_K,
   315	        threshold=THRESHOLD,
   316	    )
   317	
   318	    print()
   319	
   320	    # --------------------------------------------------------
   321	    # Create lookup by filename
   322	    # --------------------------------------------------------
   323	
   324	    results_by_file = {}
   325	
   326	    for result in results:
   327	
   328	        file_path = Path(
   329	            result["file"]
   330	        )

==============================================
=== classify_test.sh RECOGNITION COMMAND ===
==============================================
10:PY="$ROOT/.venv/bin/python"
288:recognized = 0
380:            recognized += 1
475:print(f"Recognized:  {recognized}")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:06:31

Отлично. Теперь у нас есть **идеальная точка для проверки**.

Есть непосредственный backup:

```text
app/core/scene_analyzer.py.backup_before_optimization
```

и текущий:

```text
app/core/scene_analyzer.py
```

Причём размеры:

```text
до оптимизации: 10K
текущий:        12K
```

То есть теперь можем точно определить, **изменилась ли формула распознавания**, а не гадать.

Сделай следующий блок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

diff -u \
  app/core/scene_analyzer.py.backup_before_optimization \
  app/core/scene_analyzer.py \
  > /tmp/scene_analyzer_diff.txt

echo "=== DIFF SIZE ==="
wc -l /tmp/scene_analyzer_diff.txt

echo
echo "=== DIFF ==="
cat /tmp/scene_analyzer_diff.txt
```

И отдельно — чтобы сразу увидеть именно формулу:

```bash
echo
echo "=============================================="
echo "=== OLD compare() ==="
echo "=============================================="

nl -ba app/core/scene_analyzer.py.backup_before_optimization \
  | sed -n '350,530p'

echo
echo "=============================================="
echo "=== CURRENT compare() ==="
echo "=============================================="

nl -ba app/core/scene_analyzer.py \
  | sed -n '350,530p'
```

### Что мы ищем

Особенно интересуют строки вокруг:

```python
global_score
environment_score
color_score
spatial_score
final_score
```

Если окажется, что было, например:

```python
final_score = (
    global_score * A
    + environment_score * B
    + color_score * C
    + spatial_score * D
)
```

а стало:

```python
final_score = ...
```

с другими коэффициентами/нормализацией — **вот и причина деградации**.

Если же `final_score` полностью одинаковый, тогда проблема не в формуле, а в том, **как оптимизированный recognizer передает данные в `compare()`**.

И это особенно интересно, потому что текущий код имеет новый путь:

```text
DINO global
      │
      ├── query_global ──────────┐
      │                          │
CPU descriptors                 ▼
environment ───────────────► compare()
color
spatial
```

а старый код, судя по diff, позволял `SceneAnalyzer` самому получать эти данные.

То есть вполне может оказаться, что **мы ускорили не только вычисления, но и случайно поменяли семантику входных данных**.

Пока **ничего не восстанавливай и не меняй**. Пришли этот diff — по нему уже можно будет точно сказать, какую старую логику надо вернуть, оставив `ThreadPoolExecutor` и остальные оптимизации.

---

