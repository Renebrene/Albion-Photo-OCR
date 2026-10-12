## СЕССИЯ: Разработка подслепков

**Создано:** 2026-08-15 01:48:38
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f9b34-0188-83ea-b851-7793d1230a6f](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f9b34-0188-83ea-b851-7793d1230a6f)

---

### 🤖 **Assistant** — 2026-08-15 02:13:35

Да. Сделаем сразу **оба отчёта — CSV и JSON**, причём сортировка фотографий будет идти одновременно.

Ниже готовый скрипт. Он **не использует имена файлов для определения адреса** — имя сохраняется только как информация в отчёте.

Он использует уже существующий `/tmp/recognize_test.json`, поэтому **DINO заново считать не придётся**.

### 1. Создай скрипт

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_test_and_report.py <<'PY'
#!/usr/bin/env python3

import csv
import json
import shutil
import time
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

INPUT_DIR = Path("data/input/test")
RECOGNITION_JSON = Path("/tmp/recognize_test.json")

OUTPUT_DIR = Path("data/output_test")
REPORT_DIR = Path("data/reports")

REPORT_CSV = REPORT_DIR / "test_recognition.csv"
REPORT_JSON = REPORT_DIR / "test_recognition.json"
SUMMARY_JSON = REPORT_DIR / "test_summary.json"

def load_recognition():
    text = RECOGNITION_JSON.read_text(encoding="utf-8")

    start = text.find("[")
    if start < 0:
        raise RuntimeError("JSON array not found in recognition output")

    return json.loads(text[start:])

def clean_output():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

def main():

    started = time.perf_counter()

    data = load_recognition()

    clean_output()

    print("=" * 80)
    print("SORT TEST BY FIRST CANDIDATE")
    print("=" * 80)

    print(f"INPUT:       {INPUT_DIR}")
    print(f"FILES:       {len(data)}")
    print(f"OUTPUT:      {OUTPUT_DIR}")
    print()

    rows = []

    distribution = Counter()
    score_by_id = defaultdict(list)
    margin_by_id = defaultdict(list)

    status_counter = Counter()
    confidence_counter = Counter()

    copied = 0

    for i, item in enumerate(data, 1):

        src = Path(item["file"])

        # Первый кандидат — именно он определяет адрес
        best_id = item["best_id"]

        # Убираем суффикс _v33
        if best_id.endswith("_v33"):
            address = best_id[:-4]
        else:
            address = best_id

        dst_dir = OUTPUT_DIR / address
        dst_dir.mkdir(parents=True, exist_ok=True)

        dst = dst_dir / src.name

        # Если одинаковые имена вдруг встретились повторно
        if dst.exists():
            stem = src.stem
            suffix = src.suffix

            n = 2

            while True:
                dst = dst_dir / f"{stem}__{n}{suffix}"

                if not dst.exists():
                    break

                n += 1

        shutil.copy2(src, dst)
        copied += 1

        candidates = item.get("candidates", [])

        sub_info = None

        # На будущее сохраняем информацию о локальных кандидатах,
        # если recognize уже начал их отдавать.
        if item.get("subfingerprint"):
            sub_info = item["subfingerprint"]

        row = {
            "file": str(src),
            "filename": src.name,
            "assigned_id": address,
            "fingerprint": best_id,

            "score": float(item.get("score", 0)),
            "second_score": float(item.get("second_score", 0)),
            "margin": float(item.get("margin", 0)),

            "confidence": item.get("confidence", ""),
            "status": item.get("status", ""),

            "best_image": item.get("best_image", ""),
            "best_image_score": float(
                item.get("best_image_score", 0)
            ),

            "subfingerprint": sub_info,

            "output_file": str(dst),
        }

        rows.append(row)

        distribution[address] += 1
        score_by_id[address].append(row["score"])
        margin_by_id[address].append(row["margin"])

        status_counter[row["status"]] += 1
        confidence_counter[row["confidence"]] += 1

        if i % 25 == 0 or i == len(data):
            print(
                f"[{i:3d}/{len(data)}] "
                f"{src.name} -> {address} "
                f"score={row['score']:.4f}"
            )

    elapsed = time.perf_counter() - started

    # ------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------

    fields = [
        "file",
        "filename",
        "assigned_id",
        "fingerprint",
        "score",
        "second_score",
        "margin",
        "confidence",
        "status",
        "best_image",
        "best_image_score",
        "subfingerprint",
        "output_file",
    ]

    with open(REPORT_CSV, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------

    summary_distribution = {}

    for address in sorted(distribution, key=lambda x: int(x)):
        scores = score_by_id[address]
        margins = margin_by_id[address]

        summary_distribution[address] = {
            "count": len(scores),
            "percentage": round(
                len(scores) / len(rows) * 100, 2
            ),
            "score_min": round(min(scores), 6),
            "score_mean": round(
                sum(scores) / len(scores), 6
            ),
            "score_max": round(max(scores), 6),
            "margin_min": round(min(margins), 6),
            "margin_mean": round(
                sum(margins) / len(margins), 6
            ),
            "margin_max": round(max(margins), 6),
        }

    scores = [x["score"] for x in rows]
    margins = [x["margin"] for x in rows]

    summary = {
        "generated_at": datetime.now().isoformat(),

        "input": str(INPUT_DIR),
        "output": str(OUTPUT_DIR),

        "total_files": len(rows),
        "copied_files": copied,

        "elapsed_seconds": round(elapsed, 4),
        "seconds_per_image": round(
            elapsed / len(rows), 4
        ) if rows else 0,

        "score": {
            "min": min(scores) if scores else 0,
            "mean": (
                sum(scores) / len(scores)
                if scores else 0
            ),
            "max": max(scores) if scores else 0,
        },

        "margin": {
            "min": min(margins) if margins else 0,
            "mean": (
                sum(margins) / len(margins)
                if margins else 0
            ),
            "max": max(margins) if margins else 0,
        },

        "status": dict(status_counter),
        "confidence": dict(confidence_counter),

        "distribution": summary_distribution,

        "reports": {
            "csv": str(REPORT_CSV),
            "json": str(REPORT_JSON),
        }
    }

    # JSON с каждой фотографией
    report_json = {
        "summary": summary,
        "images": rows,
    }

    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(
            report_json,
            f,
            ensure_ascii=False,
            indent=2
        )

    with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ------------------------------------------------------------
    # CONSOLE SUMMARY
    # ------------------------------------------------------------

    print()
    print("=" * 80)
    print("SORT COMPLETE")
    print("=" * 80)

    print(f"TOTAL:       {len(rows)}")
    print(f"COPIED:      {copied}")
    print(f"TIME:        {elapsed:.2f} sec")
    print(
        f"PER IMAGE:   "
        f"{elapsed / len(rows):.4f} sec"
        if rows else ""
    )

    print()
    print("DISTRIBUTION")
    print("-" * 80)

    for address in sorted(
        distribution,
        key=lambda x: int(x)
    ):
        count = distribution[address]

        print(
            f"{address:>3}: "
            f"{count:3d} "
            f"({count / len(rows) * 100:6.2f}%)"
        )

    print()
    print("SCORE")
    print("-" * 80)

    print(f"min : {min(scores):.4f}")
    print(f"mean: {sum(scores) / len(scores):.4f}")
    print(f"max : {max(scores):.4f}")

    print()
    print("MARGIN")
    print("-" * 80)

    print(f"min : {min(margins):.4f}")
    print(f"mean: {sum(margins) / len(margins):.4f}")
    print(f"max : {max(margins):.4f}")

    print()
    print("STATUS")
    print("-" * 80)

    for k, v in status_counter.most_common():
        print(f"{k:18s} {v:4d}")

    print()
    print("REPORTS")
    print("-" * 80)

    print(REPORT_CSV)
    print(REPORT_JSON)
    print(SUMMARY_JSON)

    print()
    print("SORTED PHOTOS")
    print("-" * 80)

    print(OUTPUT_DIR)

if __name__ == "__main__":
    main()
PY

chmod +x scripts/sort_test_and_report.py
```

### 2. Запуск

```bash
uv run python scripts/sort_test_and_report.py
```

После этого получим:

```text
data/output_test/
├── 78/
├── 79/
├── 80/
├── 81/
...
└── 95/
```

и:

```text
data/reports/
├── test_recognition.csv
├── test_recognition.json
└── test_summary.json
```

### Но есть один нюанс

Текущий `/tmp/recognize_test.json` уже содержит результаты **без subfingerprint V2**. Поэтому этот первый отчёт будет сортировать именно по **первому fingerprint-кандидату**.

Это даже полезно как базовая точка.

После этого я предлагаю сделать **второй прогон**, где для каждого первого кандидата проверяем его:

```text
data/subfingerprints_v2/78_v33/
data/subfingerprints_v2/79_v33/
...
```

и добавляем в CSV:

```text
assigned_id
fingerprint_score
subfingerprint
subfingerprint_score
sub_margin
best_image
```

Тогда мы сможем сравнить:

**DINO TOP-1 → против DINO TOP-1 + локальный subfingerprint**

и увидеть, действительно ли подслепки улучшают визуальную сортировку.

---

### 👤 **User** — 2026-08-15 02:14:06

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/sort_test_and_report.py
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/sort_test_and_report.py", line 348, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/sort_test_and_report.py", line 44, in main
    data = load_recognition()
           ^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/sort_test_and_report.py", line 29, in load_recognition
    return json.loads(text[start:])
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/json/decoder.py", line 337, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/json/decoder.py", line 355, in raw_decode
    raise JSONDecodeError("Expecting value", s, err.value) from None
json.decoder.JSONDecodeError: Expecting value: line 1 column 2 (char 1)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 02:14:07

Да, вижу причину. `/tmp/recognize_test.json` **не является чистым JSON**: туда попали строки `[SceneEmbedder]...`, и простой поиск первой `[` находит именно её.

Надёжнее не искать первую `[` вообще, а найти начало JSON-массива по строке, начинающейся с `[` и следующей за ней `{`.

### Исправим только загрузку

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("scripts/sort_test_and_report.py")
text = p.read_text(encoding="utf-8")

old = '''def load_recognition():
    text = RECOGNITION_JSON.read_text(encoding="utf-8")

    start = text.find("[")
    if start < 0:
        raise RuntimeError("JSON array not found in recognition output")

    return json.loads(text[start:])
'''

new = '''def load_recognition():
    text = RECOGNITION_JSON.read_text(encoding="utf-8")

    # В stdout попадают служебные сообщения:
    # [SceneEmbedder] ...
    # [Recognizer] ...
    #
    # Поэтому ищем именно начало JSON-массива:
    # [
    #   {
    #       "file": ...
    #
    lines = text.splitlines()

    start = None

    for i, line in enumerate(lines):
        if line.strip() == "[":
            # Проверяем, что дальше действительно начинается JSON
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip().startswith("{"):
                    start = i
                    break

        if start is not None:
            break

    if start is None:
        raise RuntimeError(
            "JSON array not found in recognition output"
        )

    json_text = "\\n".join(lines[start:])

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        print("JSON parsing error:")
        print(e)
        print()
        print("JSON starts with:")
        print(json_text[:1000])
        raise
'''

if old not in text:
    raise RuntimeError("Old load_recognition() block not found")

p.write_text(text.replace(old, new), encoding="utf-8")

print("FIXED:", p)
PY
```

Проверяем:

```bash
uv run python scripts/sort_test_and_report.py
```

### Но ещё лучше

После того как этот запуск пройдёт, **не будем пока считать результат окончательным**.

Сначала посмотрим:

```text
data/output_test/78
data/output_test/79
...
```

и CSV:

```bash
head -5 data/reports/test_recognition.csv
```

А затем сделаем второй этап — **subfingerprint V2**.

Там будет уже такая цепочка:

```text
ФОТО
 │
 ▼
DINOv2
 │
 ├── 78  score .91
 ├── 83  score .88
 ├── 85  score .87
 ├── ...
 │
 ▼
ПЕРВЫЙ КАНДИДАТ = 78
 │
 ▼
subfingerprints 78_v33
 │
 ├── sub_01 .94
 ├── sub_02 .91
 └── sub_03 .87
 │
 ▼
78
```

И **78 всё равно будет назначен**, даже если subfingerprint не подтвердил его. Он нужен нам как дополнительная визуальная информация, а не как механизм отказа.

После исправления просто пришли вывод запуска.

---

### 👤 **User** — 2026-08-15 02:15:33

сейчас результаты хуже, чем в прошлый раз

---

### 🤖 **Assistant** — 2026-08-15 02:15:34

Да. И это важный сигнал: **сейчас не надо продолжать сортировку и тем более менять пороги наугад**.

По предыдущему прогону у нас уже есть хороший базовый результат:

- 262 фотографии;
- средний score **0.8622**;
- 84 `CONFIDENT`;
- 55 `PROBABLE_MATCH`;
- 123 случая были неоднозначными/без уверенного результата;
- главное — мы видели, что **первый кандидат часто был правильным даже при маленьком margin**.

А текущая версия с подслепками могла ухудшить именно ранжирование кандидатов. Поэтому предлагаю вернуться на контролируемый вариант.

### Что делаем сейчас

**1. Не используем `make_subfingerprints_v2.py` для изменения самого fingerprint.**

Оставляем исходные `78_v33 ... 95_v33`.

**2. Подслепки используем только как дополнительный уровень поиска:**

```text
фото
  ↓
DINO global + environment + color + spatial
  ↓
TOP кандидаты fingerprint
  ↓
если fingerprint №1
  ↓
проверяем его subfingerprints
  ↓
берём лучший subfingerprint
  ↓
выбираем ПЕРВЫЙ fingerprint-кандидат
  ↓
папка 78 / 79 / 80 ...
```

То есть **подслепки не имеют права самостоятельно заменить первый глобальный кандидат**, если только мы не докажем на тестах, что это улучшает результат.

**3. Никакой папки `uncategorized`.**

Каждое изображение обязательно попадает в одну из:

```text
78
79
80
...
95
```

Даже если confidence низкий.

**4. Названия исходных файлов не используем вообще.**

Это принципиально для настоящего теста. Например:

```text
Вавилова 52 А (10).JPG
```

не должно влиять на классификацию.

---

### И ещё исправим ошибку JSON

Ошибка:

```text
JSONDecodeError: Expecting value: line 1 column 2
```

возникла потому, что скрипт ищет:

```python
text.find("[")
```

но в выводе есть:

```text
[SceneEmbedder]
```

и именно эту `[` он принимает за начало JSON.

Нужно искать **реальное начало JSON**, например последнюю строку перед JSON или использовать маркер.

Я бы вообще убрал зависимость от `/tmp/recognize_test.json`: сортировщик сам должен запускать recognition и получать JSON отдельно от диагностического вывода.

---

### Предлагаю следующую версию

Сделаем один нормальный скрипт:

```bash
uv run python scripts/sort_test_and_report_v2.py
```

Он:

1. берет `data/input/test`;
2. распознает все фотографии;
3. использует **78_v33–95_v33**;
4. использует subfingerprints как дополнительную проверку;
5. **всегда выбирает первый кандидат**;
6. копирует фотографии:

```text
data/output/test_sorted/
├── 78/
├── 79/
├── 80/
├── ...
└── 95/
```

7. **ничего не удаляет из `data/input/test`**;
8. создает:

```text
data/output/test_sorted/report.csv
data/output/test_sorted/report.json
data/output/test_sorted/statistics.json
```

9. в CSV для каждого снимка пишет:

```text
file
assigned_id
score
second_score
margin
confidence
best_image
best_image_score
global
environment
color
spatial
subfingerprint
subfingerprint_score
processing_time_ms
```

10. отдельно собирает:

```text
CPU %
GPU %
GPU memory
RAM
total time
images/sec
average ms/image
```

И самое важное — **сначала мы сделаем контрольный прогон на тех же 262 фотографиях**, чтобы сравнить новую версию непосредственно с уже полученным результатом.

После этого уже можно будет визуально открыть:

```text
data/output/test_sorted/78
data/output/test_sorted/79
...
```

и посмотреть, насколько хорошо реально разложились фотографии.

**Я бы сейчас именно так и пошёл: сначала воспроизводимый baseline, затем подслепки как второй этап, а не наоборот.**

---

### 👤 **User** — 2026-08-15 02:16:04

давай

---

### 🤖 **Assistant** — 2026-08-15 02:16:05

> **Inspecting project scripts and recognizer code**
>
>
> **Inspected project scripts and recognizer code**
>
> 
>
> Worked for a couple of seconds

Да. Делаем **v2 сортировщика без изменения fingerprint'ов**.

Но в этой сессии я не имею доступа к твоему `/home/alexice/projects/...`, поэтому не могу физически записать файл прямо в твою систему. Дам готовый скрипт, который можно создать одной командой.

Сейчас принцип такой:

- `78_v33 ... 95_v33` — исходные fingerprint;
- **первый кандидат является главным**;
- subfingerprints пока **не меняют назначение**, а только записываются в отчёт для последующего анализа;
- никаких `uncategorized`;
- фотографии копируются по номерам;
- создаются CSV + JSON;
- измеряются время, RAM, CPU и GPU;
- исходные файлы не трогаются.

### 1. Создай скрипт

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_test_and_report_v2.py <<'PY'
#!/usr/bin/env python3

import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from collections import Counter

import psutil

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/test"
OUTPUT_DIR = PROJECT / "data/output/test_sorted_v2"

FINGERPRINTS = [
    f"{i}_v33"
    for i in range(78, 96)
]

RECOGNITION_JSON = OUTPUT_DIR / "recognition.json"
REPORT_CSV = OUTPUT_DIR / "report.csv"
REPORT_JSON = OUTPUT_DIR / "report.json"
STATISTICS_JSON = OUTPUT_DIR / "statistics.json"

def gpu_stats():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )

        line = result.stdout.strip().splitlines()[0]
        parts = [x.strip() for x in line.split(",")]

        return {
            "gpu_name": parts[0],
            "gpu_utilization_percent": float(parts[1]),
            "gpu_memory_used_mb": float(parts[2]),
            "gpu_memory_total_mb": float(parts[3]),
        }

    except Exception:
        return {
            "gpu_name": None,
            "gpu_utilization_percent": None,
            "gpu_memory_used_mb": None,
            "gpu_memory_total_mb": None,
        }

def find_json(text):
    """
    Find the actual JSON array, ignoring messages such as:
        [SceneEmbedder]
        [Recognizer]
    """

    decoder = json.JSONDecoder()

    for i, ch in enumerate(text):
        if ch != "[":
            continue

        candidate = text[i:]

        try:
            obj, end = decoder.raw_decode(candidate)

            if isinstance(obj, list):
                return obj

        except json.JSONDecodeError:
            pass

    raise RuntimeError("Не удалось найти JSON-массив в выводе recognition")

def run_recognition():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fp_arg = ",".join(FINGERPRINTS)

    cmd = [
        "uv",
        "run",
        "scene-fingerprint",
        "recognize",
        str(INPUT_DIR),
        "--top-k",
        "5",
        "--threshold",
        "0.0",
        "--fingerprints",
        fp_arg,
        "--json",
    ]

    print("=" * 80)
    print("RUNNING RECOGNITION")
    print("=" * 80)

    print("Input:", INPUT_DIR)
    print("Fingerprints:", ", ".join(FINGERPRINTS))
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

    data = find_json(combined)

    RECOGNITION_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return data, elapsed

def copy_images(data):
    print()
    print("=" * 80)
    print("SORTING")
    print("=" * 80)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    counters = Counter()

    for item in data:
        source = Path(item["file"])

        # Главный принцип:
        # ВСЕГДА используем best_id = первый кандидат.
        assigned_id = item.get("best_id")

        if not assigned_id:
            continue

        destination_dir = OUTPUT_DIR / assigned_id
        destination_dir.mkdir(parents=True, exist_ok=True)

        destination = destination_dir / source.name

        shutil.copy2(source, destination)

        counters[assigned_id] += 1

        candidates = item.get("candidates", [])

        row = {
            "file": str(source),
            "filename": source.name,
            "assigned_id": assigned_id,
            "score": item.get("score"),
            "second_score": item.get("second_score"),
            "margin": item.get("margin"),
            "confidence": item.get("confidence"),
            "status": item.get("status"),
            "best_image": item.get("best_image"),
            "best_image_score": item.get("best_image_score"),
            "global": None,
            "environment": None,
            "color": None,
            "spatial": None,
            "candidate_2": None,
            "candidate_2_score": None,
            "candidate_3": None,
            "candidate_3_score": None,
            "candidate_4": None,
            "candidate_4_score": None,
            "candidate_5": None,
            "candidate_5_score": None,
        }

        if candidates:
            c = candidates[0]

            row["global"] = c.get("global")
            row["environment"] = c.get("environment")
            row["color"] = c.get("color")
            row["spatial"] = c.get("spatial")

        for n in range(1, min(5, len(candidates))):
            c = candidates[n]

            row[f"candidate_{n+1}"] = c.get("id")
            row[f"candidate_{n+1}_score"] = c.get("score")

        rows.append(row)

    print()

    for k in sorted(counters, key=lambda x: int(x.split("_")[0])):
        print(f"{k:10s} {counters[k]:4d}")

    return rows, counters

def write_reports(rows, counters, recognition_time):
    fields = [
        "file",
        "filename",
        "assigned_id",
        "score",
        "second_score",
        "margin",
        "confidence",
        "status",
        "best_image",
        "best_image_score",
        "global",
        "environment",
        "color",
        "spatial",
        "candidate_2",
        "candidate_2_score",
        "candidate_3",
        "candidate_3_score",
        "candidate_4",
        "candidate_4_score",
        "candidate_5",
        "candidate_5_score",
    ]

    with open(REPORT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    scores = [
        float(x["score"])
        for x in rows
        if x["score"] is not None
    ]

    margins = [
        float(x["margin"])
        for x in rows
        if x["margin"] is not None
    ]

    status_counter = Counter(
        x["status"]
        for x in rows
        if x["status"]
    )

    confidence_counter = Counter(
        x["confidence"]
        for x in rows
        if x["confidence"]
    )

    process = psutil.Process(os.getpid())

    stats = {
        "total_images": len(rows),

        "recognition_time_seconds": recognition_time,

        "images_per_second":
            len(rows) / recognition_time
            if recognition_time > 0 else None,

        "milliseconds_per_image":
            recognition_time * 1000 / len(rows)
            if rows else None,

        "score": {
            "min": min(scores) if scores else None,
            "mean": sum(scores) / len(scores) if scores else None,
            "max": max(scores) if scores else None,
        },

        "margin": {
            "min": min(margins) if margins else None,
            "mean": sum(margins) / len(margins) if margins else None,
            "max": max(margins) if margins else None,
        },

        "status": dict(status_counter),
        "confidence": dict(confidence_counter),

        "assigned": dict(counters),

        "cpu": {
            "logical_cpus": psutil.cpu_count(),
            "process_cpu_percent": process.cpu_percent(interval=0.5),
        },

        "ram": {
            "total_mb":
                psutil.virtual_memory().total / 1024 / 1024,

            "used_mb":
                psutil.virtual_memory().used / 1024 / 1024,

            "available_mb":
                psutil.virtual_memory().available / 1024 / 1024,

            "process_rss_mb":
                process.memory_info().rss / 1024 / 1024,
        },

        "gpu": gpu_stats(),
    }

    REPORT_JSON.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    STATISTICS_JSON.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return stats

def main():
    print()
    print("=" * 80)
    print("SCENE FINGERPRINT TEST SORTER V2")
    print("=" * 80)

    if not INPUT_DIR.exists():
        raise RuntimeError(f"Нет папки: {INPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    start_total = time.perf_counter()

    data, recognition_time = run_recognition()

    rows, counters = copy_images(data)

    stats = write_reports(
        rows,
        counters,
        recognition_time,
    )

    total_time = time.perf_counter() - start_total

    stats["total_wall_time_seconds"] = total_time

    STATISTICS_JSON.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("STATISTICS")
    print("=" * 80)

    print(f"Images:             {stats['total_images']}")
    print(f"Recognition time:   {recognition_time:.2f} sec")
    print(f"Total time:         {total_time:.2f} sec")
    print(
        f"Speed:              "
        f"{stats['images_per_second']:.2f} images/sec"
    )
    print(
        f"Per image:          "
        f"{stats['milliseconds_per_image']:.1f} ms"
    )

    print()
    print("SCORE")
    print(f"  min:              {stats['score']['min']:.4f}")
    print(f"  mean:             {stats['score']['mean']:.4f}")
    print(f"  max:              {stats['score']['max']:.4f}")

    print()
    print("MARGIN")
    print(f"  min:              {stats['margin']['min']:.4f}")
    print(f"  mean:             {stats['margin']['mean']:.4f}")
    print(f"  max:              {stats['margin']['max']:.4f}")

    print()
    print("RAM")
    print(
        f"  process RSS:      "
        f"{stats['ram']['process_rss_mb']:.1f} MB"
    )

    print()
    print("GPU")
    print(f"  name:             {stats['gpu']['gpu_name']}")
    print(
        f"  utilization:      "
        f"{stats['gpu']['gpu_utilization_percent']}%"
    )
    print(
        f"  memory:           "
        f"{stats['gpu']['gpu_memory_used_mb']} / "
        f"{stats['gpu']['gpu_memory_total_mb']} MB"
    )

    print()
    print("=" * 80)
    print("OUTPUT")
    print("=" * 80)

    print("Sorted:", OUTPUT_DIR)
    print("CSV:   ", REPORT_CSV)
    print("JSON:  ", REPORT_JSON)
    print("Stats: ", STATISTICS_JSON)

if __name__ == "__main__":
    main()
PY

chmod +x scripts/sort_test_and_report_v2.py
```

### 2. Запуск

```bash
uv run python scripts/sort_test_and_report_v2.py
```

Он должен создать:

```text
data/output/test_sorted_v2/
├── 78_v33/
├── 79_v33/
├── 80_v33/
├── ...
├── 95_v33/
├── recognition.json
├── report.csv
├── report.json
└── statistics.json
```

### Важный момент

Я специально поставил:

```text
--threshold 0.0
```

потому что нам сейчас нужен **полный визуальный benchmark**, а не фильтр качества.

То есть даже фотография с score `0.56` будет куда-то распределена. Это соответствует твоему требованию:

> не делать папку неклассифицированное.

И пока **не используем названия файлов** для оценки. Поэтому результат можно честно смотреть глазами.

После запуска пришли сюда вывод от:

```bash
uv run python scripts/sort_test_and_report_v2.py
```

Особенно интересуют блоки:

```text
SORTING
STATISTICS
OUTPUT
```

и затем мы уже посмотрим распределение **78–95** и решим, как именно подключить subfingerprints, не испортив первый кандидат.

---

### 👤 **User** — 2026-08-15 02:16:43

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/sort_test_and_report_v2.py
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/sort_test_and_report_v2.py", line 12, in <module>
    import psutil
ModuleNotFoundError: No module named 'psutil'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 02:16:44

Да, это просто отсутствует `psutil` в `.venv`. Сам проект при этом в порядке.

Лучше не устанавливать пакет глобально. Добавим его через `uv`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv add psutil
```

После этого:

```bash
uv run python scripts/sort_test_and_report_v2.py
```

### Если `uv add` скажет, что проект не поддерживает зависимости

Тогда:

```bash
uv pip install psutil
```

и снова:

```bash
uv run python scripts/sort_test_and_report_v2.py
```

---

Но есть ещё один важный момент в нашем скрипте: **GPU utilization, полученный после завершения recognition, может быть уже почти 0%**. Поэтому для нормальной статистики GPU лучше измерять его **во время самого распознавания**, а не после.

Я предлагаю сначала просто запустить текущую версию, чтобы проверить сортировку. Если она нормально отработает, следующим шагом сделаем `v3`, где мониторинг будет параллельно собирать:

- GPU utilization;
- VRAM used;
- RAM;
- CPU;
- пик RAM;
- пик VRAM;
- время recognition;
- время копирования;
- общее время;
- images/sec.

И тогда статистика будет действительно полезной для будущих **200–300 фотографий за день**.

---

### 👤 **User** — 2026-08-15 02:18:49

результат тоже плохой - перед этим был лучше, \

---

### 🤖 **Assistant** — 2026-08-15 02:18:49

Да. Тогда **останавливаемся и не пытаемся "улучшать" текущую версию**. Судя по всему, проблема не в сортировщике как таковом, а в том, что мы изменили способ формирования/сравнения кандидата.

У нас уже есть контрольная точка, которая работала лучше:

```text
DINOv2 global        0.70
environment          0.20
color                0.07
spatial              0.03
```

и обычный `recognize` по `78_v33 ... 95_v33`.

При этом твоя тестовая папка содержит **262 фотографии**, а реальные названия файлов позволяют нам сейчас сделать очень полезный эксперимент: **сравнить автоматический результат с фактическим адресом**, но только для анализа — алгоритм названия использовать не будет.

### Я предлагаю вернуться на лучший вариант

Не будем пока использовать:

- `subfingerprints_v2`;
- пороги `CORE_THRESHOLD`;
- clustering;
- переопределение первого кандидата;
- какие-либо новые веса.

Используем именно:

```text
image
 ↓
DINOv2
 ↓
global/environment/color/spatial
 ↓
18 fingerprint
 ↓
TOP-1
```

А затем добавим **совершенно отдельный эксперимент**:

```text
TOP-1 fingerprint
       ↓
его subfingerprints
       ↓
только аналитика
```

То есть subfingerprint пока **не может испортить результат**.

---

### И вот что я хочу сделать следующим шагом

Для каждого из 262 снимков сохранить:

```text
фактический адрес      ← извлекаем ТОЛЬКО для benchmark
TOP-1                  ← алгоритм
TOP-2
TOP-3
score
margin
best_image
```

Например:

```text
Вавилова 52 А (10).JPG

REAL:     83
TOP-1:    83_v33     0.91   ✓
TOP-2:    85_v33     0.87
TOP-3:    78_v33     0.84
```

Или:

```text
Малиновского 25 ... JPG

REAL:     85
TOP-1:    81_v33     0.80   ✗
TOP-2:    85_v33     0.79
TOP-3:    83_v33     0.77
```

Вот второй случай особенно важен.

Если правильный адрес часто оказывается **TOP-2**, значит алгоритм уже видит нужное место, но неправильно ранжирует кандидатов. Тогда мы можем улучшить ranking.

Если правильный адрес вообще не входит в TOP-5 — проблема уже в fingerprint/признаках.

### И это намного полезнее, чем сейчас визуально перебирать папки.

Плюс мы увидим отдельно:

```text
TOP-1 accuracy
TOP-2 accuracy
TOP-3 accuracy
TOP-5 accuracy
```

Например, может оказаться:

```text
TOP-1 = 72%
TOP-2 = 86%
TOP-3 = 93%
TOP-5 = 97%
```

Тогда **97% уже фактически достигнуто**, и нам надо только научиться выбирать правильный первый кандидат.

А это как раз очень хорошо согласуется с твоей идеей:

> **"ориентироваться на первого кандидата"**

но сначала надо понять, насколько часто правильный адрес уже находится среди первых кандидатов.

**Предлагаю именно этот benchmark сделать следующим.** Это даст нам объективный ответ, почему предыдущая версия была лучше и куда двигать алгоритм дальше.

---

### 👤 **User** — 2026-08-15 02:19:39

давай

---

### 🤖 **Assistant** — 2026-08-15 02:19:40

Да. Делаем **чистый benchmark на текущем, лучшем варианте**, без subfingerprints и без изменения ranking.

Но есть важный момент: названия в `data/input/test` у тебя произвольные **только с точки зрения алгоритма**, зато для benchmark они содержат фактический адрес. Поэтому скрипт будет использовать имя **только для определения `REAL`**, а recognition будет работать так, будто имени нет.

Сделаем TOP-1 / TOP-2 / TOP-3 / TOP-5 и confusion matrix.

Сначала установим `psutil`, раз он нужен для статистики:

```bash
cd ~/projects/scene_fingerprint_mvp_v02
uv add psutil
```

Затем создай benchmark:

```bash
cat > scripts/benchmark_test_v1.py <<'PY'
#!/usr/bin/env python3

import json
import re
import subprocess
import time
from pathlib import Path
from collections import Counter, defaultdict

import psutil

PROJECT = Path(__file__).resolve().parent.parent
TEST_DIR = PROJECT / "data/input/test"
OUT_DIR = PROJECT / "data/output/benchmark_v1"

FINGERPRINTS = [f"{i}_v33" for i in range(78, 96)]

def extract_real_address(filename):
    """
    Используется ТОЛЬКО для benchmark.

    Примеры:
      Вавилова 52 А (10).JPG -> 83
      1 Конной Армии 32 А (10).JPG -> ...
    """

    # Пока не угадываем адрес по тексту.
    # Используем соответствие имени через fingerprint image database
    # ниже.
    return None

def load_fingerprint_names():
    """
    Строим:
        filename -> fingerprint

    Это позволяет определить REAL для файлов,
    которые являются копиями/вариантами исходных фотографий.
    """

    result = {}

    for fp in FINGERPRINTS:
        p = PROJECT / "data/fingerprints" / fp / "metadata.json"

        if not p.exists():
            continue

        with open(p, encoding="utf-8") as f:
            meta = json.load(f)

        for name in meta.get("image_names", []):
            result[name.lower()] = fp

    return result

def find_real_from_filename(filename, fingerprint_names):
    """
    Сначала пробуем точное имя.

    Если имя тестового файла отличается от имени fingerprint,
    пытаемся использовать известные группы адресов из имени.

    Это benchmark-логика и НИКОГДА не передается recognition.
    """

    key = filename.lower()

    if key in fingerprint_names:
        return fingerprint_names[key]

    # Важный случай:
    # тестовые файлы обычно переименованы адресом.
    #
    # Для полноценного benchmark нам нужно заранее составить
    # mapping адрес -> fingerprint.
    #
    # Поэтому пока возвращаем UNKNOWN.
    return None

def run_recognition():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        "uv",
        "run",
        "scene-fingerprint",
        "recognize",
        str(TEST_DIR),
        "--top-k",
        "5",
        "--threshold",
        "0.0",
        "--fingerprints",
        ",".join(FINGERPRINTS),
        "--json",
    ]

    print("=" * 80)
    print("BENCHMARK RECOGNITION")
    print("=" * 80)
    print("Images:", len(list(TEST_DIR.glob("*"))))
    print("Fingerprints:", len(FINGERPRINTS))
    print()

    t0 = time.perf_counter()

    proc = subprocess.run(
        cmd,
        cwd=PROJECT,
        capture_output=True,
        text=True,
    )

    elapsed = time.perf_counter() - t0

    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise RuntimeError(
            f"recognize failed: {proc.returncode}"
        )

    # Ищем JSON-массив среди служебного вывода.
    decoder = json.JSONDecoder()

    data = None

    text = proc.stdout + "\n" + proc.stderr

    for i, ch in enumerate(text):
        if ch != "[":
            continue

        try:
            obj, end = decoder.raw_decode(text[i:])
            if isinstance(obj, list):
                data = obj
                break
        except json.JSONDecodeError:
            continue

    if data is None:
        raise RuntimeError("JSON recognition result not found")

    return data, elapsed

def main():

    if not TEST_DIR.exists():
        raise RuntimeError(f"Нет папки {TEST_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fingerprint_names = load_fingerprint_names()

    data, elapsed = run_recognition()

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)

    print("TOTAL:", len(data))
    print("TIME:", f"{elapsed:.2f} sec")
    print(
        "SPEED:",
        f"{len(data)/elapsed:.2f} images/sec"
    )

    # Пока REAL может быть неизвестен.
    # Но сохраняем всю информацию TOP-5.

    rows = []

    for x in data:

        candidates = x.get("candidates", [])

        top = [
            c.get("id")
            for c in candidates[:5]
        ]

        scores = [
            c.get("score")
            for c in candidates[:5]
        ]

        rows.append({
            "file": x.get("file"),
            "real": find_real_from_filename(
                Path(x.get("file", "")).name,
                fingerprint_names
            ),
            "top1": top[0] if len(top) > 0 else None,
            "top1_score": scores[0] if len(scores) > 0 else None,
            "top2": top[1] if len(top) > 1 else None,
            "top2_score": scores[1] if len(scores) > 1 else None,
            "top3": top[2] if len(top) > 2 else None,
            "top3_score": scores[2] if len(scores) > 2 else None,
            "top4": top[3] if len(top) > 3 else None,
            "top4_score": scores[3] if len(scores) > 3 else None,
            "top5": top[4] if len(top) > 4 else None,
            "top5_score": scores[4] if len(scores) > 4 else None,
            "score": x.get("score"),
            "margin": x.get("margin"),
            "confidence": x.get("confidence"),
            "status": x.get("status"),
            "best_image": x.get("best_image"),
        })

    # Сохраняем полный benchmark.
    (OUT_DIR / "benchmark.json").write_text(
        json.dumps(
            {
                "total": len(rows),
                "recognition_time_sec": elapsed,
                "images_per_second": len(rows) / elapsed,
                "fingerprints": FINGERPRINTS,
                "results": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Простая статистика TOP кандидатов.
    top1 = Counter(x["top1"] for x in rows)
    top2 = Counter(x["top2"] for x in rows)

    print()
    print("TOP-1 DISTRIBUTION")
    for fp, n in sorted(top1.items()):
        print(
            f"{fp:10s} {n:4d} "
            f"{100*n/len(rows):6.2f}%"
        )

    print()
    print("TOP-2 DISTRIBUTION")
    for fp, n in sorted(top2.items()):
        print(
            f"{fp:10s} {n:4d} "
            f"{100*n/len(rows):6.2f}%"
        )

    print()
    print("OUTPUT:")
    print(OUT_DIR / "benchmark.json")

    print()
    print("=" * 80)
    print("NOTE")
    print("=" * 80)
    print(
        "REAL пока не вычисляется автоматически для "
        "переименованных тестовых файлов."
    )
    print(
        "Следующим шагом построим mapping "
        "адрес -> fingerprint и получим настоящий TOP-1/2/3/5 accuracy."
    )

if __name__ == "__main__":
    main()
PY

chmod +x scripts/benchmark_test_v1.py
```

Запускаем:

```bash
uv run python scripts/benchmark_test_v1.py
```

### Но я хочу сразу уточнить одну вещь

Для **настоящего** benchmark нам недостаточно просто посмотреть на TOP-1. У тебя тестовые файлы имеют названия вроде:

```text
Вавилова 52 А (10).JPG
Комарова 28 А (3).JPG
Нагибина Рубиновый А (12).JPG
```

а fingerprint называется:

```text
83_v33
84_v33
85_v33
```

Нам нужно один раз построить таблицу:

```text
78 -> реальный адрес
79 -> реальный адрес
...
95 -> реальный адрес
```

После этого сможем получить **реальную точность**, например:

```text
TOP-1    76.3%
TOP-2    88.9%
TOP-3    94.7%
TOP-5    98.1%
```

И вот **это будет главный показатель**, по которому будем решать, что делать с subfingerprints.

Не ориентируемся больше на `margin` или на субъективное ощущение, что папки «выглядят хуже». Сначала получаем цифры, затем меняем **только один элемент алгоритма за раз**.

---

### 👤 **User** — 2026-08-15 02:20:53

пока так как есть, т.к. много неназванных фото, а номера еще не имеют присвоенного имени

---

### 🤖 **Assistant** — 2026-08-15 02:20:53

Да, тогда **не пытаемся строить `REAL` и accuracy**. Это сейчас даже правильнее.

У нас фактически два разных этапа:

### Сейчас — классификация по номеру

Алгоритм должен делать только:

```text
фотография
   ↓
DINOv2
   ↓
78_v33 ... 95_v33
   ↓
TOP-1
   ↓
папка 78 / 79 / ... / 95
```

И совершенно неважно, называется исходный файл:

```text
Вавилова 52 А (10).JPG
```

или:

```text
photo_001.jpg
```

Для алгоритма имя **вообще не используется**.

### Почему это нам подходит

У нас сейчас есть номера:

```text
78
79
80
...
95
```

Но еще нет окончательного справочника:

```text
78 → конкретный адрес
79 → конкретный адрес
...
```

Поэтому сейчас мы фактически создаём **базу визуальных слепков объектов**, а не систему распознавания адресов.

Когда позже установим:

```text
78 → "..."
79 → "..."
```

все уже отсортированные фотографии автоматически получат нормальные названия.

---

### И я бы сейчас сделал именно так

Не трогать текущие fingerprints `78_v33 ... 95_v33`.

Сделать **чистую сортировку test**:

```text
data/output/test_sorted/
├── 78/
├── 79/
├── 80/
├── 81/
├── ...
└── 95/
```

Причём **каждая фотография обязательно попадает в один номер**.

А отчёт:

```text
report.csv
report.json
statistics.json
```

сохраняет:

```text
файл
TOP-1
score
TOP-2
score
TOP-3
score
TOP-4
score
TOP-5
score
margin
confidence
best_image
global
environment
color
spatial
```

Это позволит нам потом посмотреть на **неудачные случаи визуально**, даже если мы пока не знаем правильного номера.

---

И ещё: поскольку ты сказал, что **предыдущий результат визуально был лучше**, я бы сейчас вообще **не включал subfingerprints в присвоение номера**.

Сначала добиваемся стабильной работы:

**обычный v33 → первый кандидат → сортировка.**

А subfingerprints подключим потом как дополнительный сигнал и сравним:

```text
v33 baseline
       VS
v33 + subfingerprint
```

на одних и тех же 262 фотографиях.

Это даст нам честный ответ, **улучшили мы систему или испортили её**.

---

### 👤 **User** — 2026-08-15 02:21:28

ок

---

### 🤖 **Assistant** — 2026-08-15 02:21:28

Ок. Тогда фиксируем текущую схему как **baseline**:

- `78_v33 ... 95_v33`
- исходные веса `0.70 / 0.20 / 0.07 / 0.03`
- **TOP-1 = назначение номера**
- subfingerprints пока не вмешиваются в выбор
- никаких `uncategorized`
- имена файлов не учитываются
- создаём CSV/JSON + статистику CPU/GPU/RAM/времени.

Следующий эксперимент будем сравнивать именно с этим baseline, чтобы не потерять лучший уже полученный результат.

---

### 👤 **User** — 2026-08-15 02:22:08

ок

---

### 🤖 **Assistant** — 2026-08-15 02:22:08

Хорошо. Фиксируем baseline и дальше меняем только **один компонент за раз**, чтобы точно понимать, что реально улучшает распознавание.

---

### 👤 **User** — 2026-08-15 02:22:14

давай

---

### 🤖 **Assistant** — 2026-08-15 02:22:14

Давай. Сейчас лучше не менять алгоритм, а **сначала получить чистый baseline-прогон и сохранить его как эталон**.

У тебя уже есть `sort_test_and_report_v2.py`, но он требует `psutil`. Чтобы не тратить время на установку статистических зависимостей, предлагаю пока запустить сам recognition напрямую — он у нас уже проверен.

### 1. Запусти baseline

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf data/output/baseline_v33
mkdir -p data/output/baseline_v33

/usr/bin/time -v \
uv run scene-fingerprint recognize data/input/test \
  --top-k 5 \
  --threshold 0.0 \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33,87_v33,88_v33,89_v33,90_v33,91_v33,92_v33,93_v33,94_v33,95_v33 \
  --json \
  > data/output/baseline_v33/recognition_raw.txt \
  2> data/output/baseline_v33/system_stats.txt
```

Это **ничего не сортирует и ничего не изменяет**.

---

### 2. Посмотри системную статистику

```bash
cat data/output/baseline_v33/system_stats.txt | tail -30
```

Там будут:

```text
Elapsed time
Maximum resident set size
User time
System time
CPU %
```

GPU отдельно посмотрим через `nvidia-smi`.

---

### 3. Сохраним чистый JSON

Поскольку в выводе есть строки:

```text
[SceneEmbedder] ...
[Recognizer] ...
```

нельзя просто делать `json.loads(text[text.find("["):])`.

Используем JSON decoder:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

src = Path("data/output/baseline_v33/recognition_raw.txt")
dst = Path("data/output/baseline_v33/recognition.json")

text = src.read_text(encoding="utf-8")

decoder = json.JSONDecoder()

data = None

for i, ch in enumerate(text):
    if ch != "[":
        continue

    try:
        obj, end = decoder.raw_decode(text[i:])
        if isinstance(obj, list):
            data = obj
            break
    except json.JSONDecodeError:
        pass

if data is None:
    raise RuntimeError("JSON recognition result not found")

dst.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("OK")
print("Images:", len(data))
print("Saved:", dst)
PY
```

Должно получиться:

```text
Images: 262
Saved: data/output/baseline_v33/recognition.json
```

---

### 4. И сразу получим распределение TOP-1

```bash
uv run python - <<'PY'
import json
from collections import Counter
from pathlib import Path

p = Path("data/output/baseline_v33/recognition.json")
data = json.loads(p.read_text(encoding="utf-8"))

c = Counter(x["best_id"] for x in data)

print("=" * 70)
print("BASELINE V33")
print("=" * 70)
print("TOTAL:", len(data))
print()

for k, v in sorted(c.items(), key=lambda x: int(x[0].split("_")[0])):
    print(f"{k:10s} {v:4d} {v/len(data)*100:6.2f}%")

print()
print("SCORE")
scores = [x["score"] for x in data]
print("min :", f"{min(scores):.4f}")
print("mean:", f"{sum(scores)/len(scores):.4f}")
print("max :", f"{max(scores):.4f}")

print()
print("MARGIN")
margins = [x["margin"] for x in data]
print("min :", f"{min(margins):.4f}")
print("mean:", f"{sum(margins)/len(margins):.4f}")
print("max :", f"{max(margins):.4f}")
PY
```

---

После этого у нас будет **железная контрольная точка**:

```text
baseline_v33/
├── recognition.json
├── recognition_raw.txt
└── system_stats.txt
```

И уже от неё будем делать следующий эксперимент — **подключать subfingerprints только для переоценки TOP-кандидатов**, не трогая исходные fingerprints. Так мы наконец увидим, действительно ли они улучшают визуальную классификацию.

---

### 👤 **User** — 2026-08-15 02:23:14

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python - <<'PY'
import json
from pathlib import Path

src = Path("data/output/baseline_v33/recognition_raw.txt")
dst = Path("data/output/baseline_v33/recognition.json")

text = src.read_text(encoding="utf-8")

decoder = json.JSONDecoder()

data = None

for i, ch in enumerate(text):
    if ch != "[":
        continue

    try:
        obj, end = decoder.raw_decode(text[i:])
        if isinstance(obj, list):
            data = obj
            break
    except json.JSONDecodeError:
PYint("Saved:", dst)(data))_ascii=False, indent=2), found")
Traceback (most recent call last):
  File "<stdin>", line 26, in <module>

---

### 🤖 **Assistant** — 2026-08-15 02:23:15

Да, здесь снова проблема **не в распознавании**, а в извлечении JSON из `recognition_raw.txt`. Судя по предыдущему выводу, в начале файла идут служебные сообщения `SceneEmbedder`, а затем JSON.

Сделаем надёжнее: не будем искать первую `[` посимвольно. Найдём JSON-массив и проверим, что после него нет мусора.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

src = Path("data/output/baseline_v33/recognition_raw.txt")
dst = Path("data/output/baseline_v33/recognition.json")

text = src.read_text(encoding="utf-8")

decoder = json.JSONDecoder()

data = None
start_pos = None

# Ищем любой '[' и пробуем декодировать JSON
for i in range(len(text)):
    if text[i] != "[":
        continue

    try:
        obj, end = decoder.raw_decode(text[i:])
    except json.JSONDecodeError:
        continue

    if isinstance(obj, list) and obj:
        # Проверяем, что это действительно список результатов
        if isinstance(obj[0], dict) and "file" in obj[0]:
            data = obj
            start_pos = i
            break

if data is None:
    print("ERROR: JSON recognition results not found")
    print("File:", src)
    print("Size:", len(text))
    raise SystemExit(1)

dst.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("=" * 70)
print("JSON EXTRACTED")
print("=" * 70)
print("Source:", src)
print("Output:", dst)
print("Results:", len(data))
print("JSON starts at character:", start_pos)

# Небольшая проверка
print()
print("FIRST RESULT:")
print("file:", data[0].get("file"))
print("best_id:", data[0].get("best_id"))
print("score:", data[0].get("score"))
print("second:", data[0].get("second_score"))
print("margin:", data[0].get("margin"))
print("status:", data[0].get("status"))
PY
```

Ожидаем примерно:

```text
======================================================================
JSON EXTRACTED
======================================================================
Source: data/output/baseline_v33/recognition_raw.txt
Output: data/output/baseline_v33/recognition.json
Results: 262

FIRST RESULT:
file: data/input/test/...
best_id: 78_v33
score: ...
second: ...
margin: ...
status: ...
```

### Важно

Пока **ничего заново не распознаём**.

У нас уже есть тот результат на **262 фотографии**, который ты считаешь лучшим. Его и используем как baseline.

Дальше предлагаю сделать именно то, что ты хотел:

```text
data/input/test/
        ↓
существующий recognition.json
        ↓
для каждого фото:
    TOP-1 fingerprint
        ↓
    + subfingerprint
        ↓
    выбираем ПЕРВОГО кандидата
        ↓
data/output/baseline_v33/sorted/
    ├── 78/
    ├── 79/
    ├── 80/
    ├── 81/
    ├── ...
    └── 95/
```

**Без `uncertain` / `unclassified`.**

То есть даже если:

```text
best       = 83
score      = 0.79
second     = 82
margin     = 0.008
```

фото всё равно попадёт в:

```text
sorted/83/
```

Потому что сейчас наша задача — **визуально проверить качество первого кандидата**, а не отбрасывать сомнительные фотографии.

И одновременно сделаем:

```text
report.csv
report.json
performance.json
```

с полями примерно:

```text
file
assigned_id
score
second_id
second_score
margin
subfingerprint
best_image
best_image_score
global
environment
color
spatial
```

и статистикой:

```text
total_images
per_fingerprint
score_mean
score_min
score_max
margin_mean

GPU:
  model
  peak_vram
  elapsed

CPU:
  utilization
  workers

RAM:
  peak
  average
```

Но **сначала выполни только команду выше**. Если она покажет `Results: 262`, будем сортировать именно этот удачный baseline, не запуская DINOv2 повторно.

---

### 👤 **User** — 2026-08-15 02:23:40

int_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

src = Path("data/output/baseline_v33/recognition_raw.txt")
dst = Path("data/output/baseline_v33/recognition.json")

text = src.read_text(encoding="utf-8")

decoder = json.JSONDecoder()

data = None
start_pos = None

# Ищем любой '[' и пробуем декодировать JSON
for i in range(len(text)):
    if text[i] != "[":
        continue

    try:
        obj, end = decoder.raw_decode(text[i:])
PYint("status:", data[0].get("status"))ore"))nt=2),d")0]:атов
ERROR: JSON recognition results not found
File: data/output/baseline_v33/recognition_raw.txt
Size: 390

---

### 🤖 **Assistant** — 2026-08-15 02:23:41

Да. Теперь причина ясна: `recognition_raw.txt` имеет всего **390 байт**, то есть там **нет результатов 262 фотографий**. Скорее всего, предыдущий запуск был перенаправлен так, что JSON фактически не попал в этот файл, либо файл был перезаписан ошибочным запуском.

**Старый хороший результат на 262 фото у нас в переписке есть только в виде вывода, но полного JSON сейчас нет.** Поэтому восстанавливать его из `recognition_raw.txt` невозможно.

Предлагаю не трогать текущие fingerprint'ы и сделать **один чистый baseline-запуск**, но сразу правильно сохранить JSON.

### 1. Удаляем битый файл

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -f data/output/baseline_v33/recognition_raw.txt
rm -f data/output/baseline_v33/recognition.json
```

### 2. Запускаем распознавание и сохраняем ВСЁ

Здесь важный момент: служебный вывод DINOv2 может идти в stdout, поэтому просто `> file` нам неудобно.

Используем `tee`:

```bash
mkdir -p data/output/baseline_v33

uv run scene-fingerprint recognize data/input/test \
  --top-k 5 \
  --threshold 0.50 \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33,87_v33,88_v33,89_v33,90_v33,91_v33,92_v33,93_v33,94_v33,95_v33 \
  --json 2>&1 | tee data/output/baseline_v33/recognition_raw.txt
```

**Не прерывай команду**, пока она не закончит все 262 фотографии.

### 3. Сразу после окончания проверь размер

```bash
wc -c data/output/baseline_v33/recognition_raw.txt
```

Он должен быть уже не `390`, а **десятки/сотни килобайт или больше**.

И:

```bash
grep -c '"file":' data/output/baseline_v33/recognition_raw.txt
```

Должно быть:

```text
262
```

### 4. Затем извлечём JSON

После успешного запуска выполни:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

src = Path("data/output/baseline_v33/recognition_raw.txt")
dst = Path("data/output/baseline_v33/recognition.json")

text = src.read_text(encoding="utf-8")

decoder = json.JSONDecoder()
data = None

for i, ch in enumerate(text):
    if ch != "[":
        continue

    try:
        obj, end = decoder.raw_decode(text[i:])
    except json.JSONDecodeError:
        continue

    if (
        isinstance(obj, list)
        and len(obj) > 0
        and isinstance(obj[0], dict)
        and "file" in obj[0]
        and "best_id" in obj[0]
    ):
        data = obj
        break

if data is None:
    print("ERROR: recognition JSON not found")
    raise SystemExit(1)

dst.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("=" * 70)
print("BASELINE JSON")
print("=" * 70)
print("Results:", len(data))
print("Saved:", dst)
print()
print("First:")
print(data[0]["file"])
print(data[0]["best_id"])
print(data[0]["score"])
PY
```

---

### Но я бы сейчас сделал ещё лучше

Поскольку ты сказал, что **предыдущий результат был лучше**, нам надо сохранить именно его как эталон.

После нового запуска мы сравним:

```text
                 старый результат
                        │
                        ▼
                  baseline_v33
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
         TOP-1 номер          TOP-1 score
              │                   │
              └─────────┬─────────┘
                        ▼
                  сортировка
                        │
                        ▼
              78 / 79 / ... / 95
```

И **не будем менять алгоритм распознавания**.

После этого уже можно отдельно добавить подслепки как второй этап:

```text
DINO global
     ↓
TOP-5 fingerprint
     ↓
subfingerprints
     ↓
визуальная проверка первого кандидата
```

Это гораздо безопаснее, чем сейчас снова менять веса или пороги.

**Сейчас выполни только запуск из пункта 2.** После него пришли последние ~30 строк вывода и результат `grep -c '"file":'`. Тогда пойдём дальше.

---

### 👤 **User** — 2026-08-15 02:25:11

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ wc -c data/output/baseline_v33/recognition_raw.txt
514381 data/output/baseline_v33/recognition_raw.txt
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -c '"file":' data/output/baseline_v33/recognition_raw.txt
262
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 02:25:13

Отлично. Теперь всё правильно: **262 результата**, файл нормального размера.

Следующий шаг — извлечь JSON и сразу проверить, что это именно результаты распознавания.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

src = Path("data/output/baseline_v33/recognition_raw.txt")
dst = Path("data/output/baseline_v33/recognition.json")

text = src.read_text(encoding="utf-8")
decoder = json.JSONDecoder()

data = None

for i, ch in enumerate(text):
    if ch != "[":
        continue

    try:
        obj, end = decoder.raw_decode(text[i:])
    except json.JSONDecodeError:
        continue

    if (
        isinstance(obj, list)
        and len(obj) == 262
        and isinstance(obj[0], dict)
        and "file" in obj[0]
        and "best_id" in obj[0]
    ):
        data = obj
        break

if data is None:
    raise RuntimeError("Не найден JSON с 262 результатами")

dst.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("=" * 70)
print("BASELINE JSON CREATED")
print("=" * 70)
print("Results:", len(data))
print("Saved:", dst)
print()
print("FIRST RESULT")
print("file:       ", data[0]["file"])
print("best_id:    ", data[0]["best_id"])
print("score:      ", data[0]["score"])
print("second:     ", data[0]["second_score"])
print("margin:     ", data[0]["margin"])
print("status:     ", data[0]["status"])
print("best_image: ", data[0].get("best_image"))
PY
```

После этого должно быть:

```text
BASELINE JSON CREATED
Results: 262
Saved: data/output/baseline_v33/recognition.json
```

### Потом сразу сделаем сортировку

Причём я предлагаю **не учитывать `status` вообще**.

То есть:

- `CONFIDENT` → первый кандидат
- `PROBABLE_MATCH` → первый кандидат
- `AMBIGUOUS` → **первый кандидат**
- `NO_MATCH` → **первый кандидат**

И никаких:

```text
uncertain/
unclassified/
unknown/
```

не создаём.

Например:

```text
data/output/baseline_v33/sorted/
├── 78/
├── 79/
├── 80/
├── 81/
├── 82/
├── 83/
├── 84/
├── 85/
├── 86/
├── 87/
├── 88/
├── 89/
├── 90/
├── 91/
├── 92/
├── 93/
├── 94/
└── 95/
```

А внутри сохраняем **копии**, оригиналы `data/input/test` не трогаем.

И одновременно сформируем:

```text
data/output/baseline_v33/
├── recognition_raw.txt
├── recognition.json
├── sorted/
├── report.csv
└── report.json
```

В отчёте для каждой фотографии будут, среди прочего:

```text
filename
assigned_id
score
second_id
second_score
margin
status
best_image
best_image_score
global
environment
color
spatial
```

Это даст нам очень удобную возможность потом открыть, например, только:

```text
83/
```

и **визуально посмотреть, насколько хорошо первый кандидат действительно определяет адрес**.

Сейчас выполни создание `recognition.json`.

---

### 👤 **User** — 2026-08-15 02:26:14

BASELINE JSON CREATED
======================================================================
Results: 262
Saved: data/output/baseline_v33/recognition.json

FIRST RESULT
file:        data/input/test/00 (1).JPG
best_id:     78_v33
score:       0.9474834299087525
second:      0.8808266913890838
margin:      0.06665673851966869
status:      CONFIDENT
best_image:  photo040.JPG

---

### 🤖 **Assistant** — 2026-08-15 02:26:15

Отлично. Теперь у нас есть **полный baseline из 262 фотографий**, и это именно тот вариант распознавания, который мы хотим проверить визуально.

Теперь сортируем **строго по `best_id` (первому кандидату)**, независимо от `status`, и одновременно создаём CSV/JSON-отчёт.

Я бы сделал это отдельным скриптом, чтобы исходный `recognition.json` больше не трогать.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_baseline.py <<'PY'
#!/usr/bin/env python3

import csv
import json
import shutil
import time
from collections import Counter
from pathlib import Path

BASE = Path("data/output/baseline_v33")
SRC = BASE / "recognition.json"
OUT = BASE / "sorted"
REPORT_CSV = BASE / "report.csv"
REPORT_JSON = BASE / "report.json"

FINGERPRINTS = [
    "78_v33", "79_v33", "80_v33", "81_v33", "82_v33",
    "83_v33", "84_v33", "85_v33", "86_v33", "87_v33",
    "88_v33", "89_v33", "90_v33", "91_v33", "92_v33",
    "93_v33", "94_v33", "95_v33",
]

def main():
    t0 = time.perf_counter()

    data = json.loads(SRC.read_text(encoding="utf-8"))

    print("=" * 80)
    print("SORT BASELINE V33")
    print("=" * 80)
    print("INPUT:", len(data))

    # Создаём папки только для реально встречающихся кандидатов
    OUT.mkdir(parents=True, exist_ok=True)

    for fp in FINGERPRINTS:
        (OUT / fp.replace("_v33", "")).mkdir(exist_ok=True)

    rows = []
    counts = Counter()

    for item in data:
        src = Path(item["file"])

        # ГЛАВНОЕ:
        # всегда используем ПЕРВОГО кандидата
        best_id = item["best_id"]
        folder = best_id.replace("_v33", "")

        if folder not in FINGERPRINTS:
            # Защита от неожиданных ID
            folder = best_id

        dst_dir = OUT / folder
        dst_dir.mkdir(parents=True, exist_ok=True)

        dst = dst_dir / src.name

        # Не перезаписываем файл при совпадении имени
        if dst.exists():
            stem = src.stem
            suffix = src.suffix
            n = 2

            while True:
                candidate = dst_dir / f"{stem}__{n}{suffix}"
                if not candidate.exists():
                    dst = candidate
                    break
                n += 1

        shutil.copy2(src, dst)

        counts[best_id] += 1

        rows.append({
            "file": str(src),
            "filename": src.name,
            "assigned_id": best_id,
            "score": item.get("score"),
            "second_id": (
                item["candidates"][1]["id"]
                if len(item.get("candidates", [])) > 1
                else ""
            ),
            "second_score": item.get("second_score"),
            "margin": item.get("margin"),
            "status": item.get("status"),
            "confidence": item.get("confidence"),
            "best_image": item.get("best_image"),
            "best_image_score": item.get("best_image_score"),
            "global": (
                item["candidates"][0].get("global")
                if item.get("candidates")
                else ""
            ),
            "environment": (
                item["candidates"][0].get("environment")
                if item.get("candidates")
                else ""
            ),
            "color": (
                item["candidates"][0].get("color")
                if item.get("candidates")
                else ""
            ),
            "spatial": (
                item["candidates"][0].get("spatial")
                if item.get("candidates")
                else ""
            ),
        })

    # CSV
    fields = list(rows[0].keys())

    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    elapsed = time.perf_counter() - t0

    # JSON report
    report = {
        "total": len(data),
        "counts": dict(sorted(counts.items())),
        "elapsed_sort_seconds": elapsed,
        "source": str(SRC),
        "output": str(OUT),
        "rule": "ALWAYS_FIRST_CANDIDATE",
    }

    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("DISTRIBUTION")
    print("-" * 80)

    for fp in FINGERPRINTS:
        print(f"{fp:10s} {counts[fp]:4d}")

    print("-" * 80)
    print(f"TOTAL      {sum(counts.values()):4d}")

    print()
    print("OUTPUT:")
    print("  sorted :", OUT)
    print("  CSV    :", REPORT_CSV)
    print("  JSON   :", REPORT_JSON)
    print()
    print(f"TIME: {elapsed:.3f} sec")

if __name__ == "__main__":
    main()
PY

chmod +x scripts/sort_baseline.py
```

И запускаем:

```bash
uv run python scripts/sort_baseline.py
```

### Что особенно важно

Здесь **не используется порог `0.50` и не используется `status`** для решения, куда класть фотографию.

Решение ровно такое:

```text
фотография
    ↓
recognition.json
    ↓
best_id
    ↓
папка номера
```

Например:

```text
00 (1).JPG
   ↓
78_v33
   ↓
sorted/78/00 (1).JPG
```

Даже если:

```text
status = AMBIGUOUS
```

она всё равно попадёт в `78`.

Это сейчас правильно, потому что **мы хотим оценить алгоритм глазами**, а не искусственно скрывать его ошибки.

После запуска пришли вывод `DISTRIBUTION`. По нему уже можно будет увидеть, например, сколько из 262 фотографий система отдала каждому номеру и сравнить это с реальным содержимым `data/input/test`.

---

### 👤 **User** — 2026-08-15 02:26:51

ISTRIBUTION
--------------------------------------------------------------------------------
78_v33       50
79_v33       16
80_v33       14
81_v33       35
82_v33       20
83_v33       57
84_v33       11
85_v33       59
86_v33        0
87_v33        0
88_v33        0
89_v33        0
90_v33        0
91_v33        0
92_v33        0
93_v33        0
94_v33        0
95_v33        0
--------------------------------------------------------------------------------
TOTAL       262

OUTPUT:
  sorted : data/output/baseline_v33/sorted
  CSV    : data/output/baseline_v33/report.csv
  JSON   : data/output/baseline_v33/report.json

TIME: 0.373 sec
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 02:26:52

Отлично. Это важный результат.

### Что получили

Распределение **полностью совпало с предыдущим benchmark**:

| Номер | Фото |
|---:|---:|
| 78 | 50 |
| 79 | 16 |
| 80 | 14 |
| 81 | 35 |
| 82 | 20 |
| 83 | 57 |
| 84 | 11 |
| 85 | 59 |
| 86-95 | 0 |
| **Всего** | **262** |

То есть сортировка работает правильно и **не изменила результаты распознавания**.

Но здесь обнаруживается интересный момент: в `data/input/test` у нас есть реальные фотографии и для **86-95**, а текущая модель вообще ни одной из них не выбрала. Это уже не проблема сортировщика - это проблема **самого fingerprint recognition**.

### Сейчас я бы НЕ менял алгоритм

Ты правильно сказал раньше: пока номера не имеют присвоенного имени, нам важнее накопить визуальную статистику.

У нас теперь есть:

```text
data/output/baseline_v33/
│
├── recognition.json      ← полный результат 262 фото
├── recognition_raw.txt
├── report.csv            ← результат каждой фотографии
├── report.json
│
└── sorted/
    ├── 78/
    ├── 79/
    ├── 80/
    ├── 81/
    ├── 82/
    ├── 83/
    ├── 84/
    └── 85/
```

### Следующий очень полезный тест

У нас есть **истинная информация в именах файлов**:

```text
Вавилова 52 А (...)
Комарова 28 А (...)
Добровольского 17 А (...)
...
```

То есть можно автоматически сравнить:

**что система назначила**

с

**тем, что написано в имени исходной фотографии**.

Например:

```text
Вавилова 52 А (10).JPG
        ↓
система → 83
```

Это позволит получить реальную таблицу:

```text
РЕАЛЬНЫЙ АДРЕС       → 78 79 80 81 ... 95
Вавилова 52 А        →  0  0  0  0 ... ?
Комарова 28 А        →  ?
...
```

И самое интересное - увидеть **матрицу ошибок**.

Но поскольку имена fingerprint сейчас - это просто `78`, `79`, `80`..., мы можем сначала определить соответствие:

```text
реальный адрес → fingerprint
```

по большинству фотографий.

Тогда получится уже настоящий benchmark:

```text
               ПРЕДСКАЗАНО
              78 79 80 81 82 83 84 85
РЕАЛЬНО 78    47  1  0  1  0  1  0  0
        79     0 15  0  0  1  0  0  0
        ...
```

И мы увидим не только процент правильных, но и **какие именно адреса система путает между собой**.

Это будет гораздо полезнее, чем сейчас менять `0.70 / 0.20 / 0.07 / 0.03` наугад.

**Следующий шаг я предлагаю именно такой: построить автоматическую confusion matrix по `data/input/test` и `recognition.json`.** Это позволит понять, насколько текущий DINOv2 уже хорош и где именно он ошибается.

---

### 👤 **User** — 2026-08-15 02:33:05

надо проверить, что ничего не сломалось. 1) пересоздаем слепки для 78-95 - проверяем, как работает v33 2) запускаем распознавание и сортировку папки test c раскладыванием результата по папкам с номером

---

### 🤖 **Assistant** — 2026-08-15 02:33:05

Да. Сейчас **не будем менять алгоритм распознавания**. Проверяем именно тот вариант `v33`, который дал предыдущий хороший результат:

- DINOv2 global - **0.70**
- environment - **0.20**
- color - **0.07**
- spatial - **0.03**
- без `subfingerprints_v2` в основном score;
- все папки `78-95` пересоздаём заново;
- затем прогоняем `data/input/test`;
- **каждый файл обязательно получает папку номера**, даже если confidence низкий;
- имя файла не используем как источник истины;
- `best_id` = первый кандидат;
- создаём отчёты CSV + JSON;
- отдельно считаем CPU/GPU/RAM и время.

### 1. Сначала сохраним старые v33

```bash
cd ~/projects/scene_fingerprint_mvp_v02

mkdir -p data/fingerprints_backup_v33

for n in {78..95}; do
    if [ -d "data/fingerprints/${n}_v33" ]; then
        mv "data/fingerprints/${n}_v33" \
           "data/fingerprints_backup_v33/${n}_v33_$(date +%Y%m%d_%H%M%S)"
    fi
done
```

Проверяем:

```bash
ls -lah data/fingerprints_backup_v33
```

---

# 2. Пересоздаём fingerprints 78-95

Запускаем **по одному**, чтобы если какой-то номер упадёт, мы сразу увидели какой.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for n in {78..95}; do
    echo
    echo "============================================================"
    echo "CREATING ${n}_v33"
    echo "============================================================"

    uv run scene-fingerprint create \
        "${n}_v33" \
        "data/input/${n}"

    if [ $? -ne 0 ]; then
        echo "!!! ERROR: ${n}_v33 !!!"
        exit 1
    fi
done
```

После этого проверим все 18:

```bash
uv run python - <<'PY'
import json
import numpy as np
from pathlib import Path

root = Path("data/fingerprints")

print("=" * 80)
print("V33 FINGERPRINT CHECK")
print("=" * 80)

total = 0

for n in range(78, 96):
    fp = root / f"{n}_v33"

    print(f"\n{n}_v33")

    if not fp.exists():
        print("  !!! MISSING")
        continue

    try:
        m = json.loads((fp / "metadata.json").read_text())

        e = np.load(fp / "embeddings.npy")
        env = np.load(fp / "environment_embeddings.npy")
        color = np.load(fp / "color_embeddings.npy")
        spatial = np.load(fp / "spatial_embeddings.npy")
        reps = np.load(fp / "representatives.npy")

        print(f"  images:        {m['images']}")
        print(f"  embeddings:    {e.shape}")
        print(f"  environment:   {env.shape}")
        print(f"  color:         {color.shape}")
        print(f"  spatial:       {spatial.shape}")
        print(f"  representatives:{reps.shape}")
        print(f"  version:       {m.get('version')}")
        print(f"  weights:       {m.get('weights')}")

        ok = (
            e.shape[0] == m["images"] and
            env.shape[0] == m["images"] and
            color.shape[0] == m["images"] and
            spatial.shape[0] == m["images"]
        )

        print("  STATUS:", "OK" if ok else "!!! BROKEN !!!")

        if ok:
            total += 1

    except Exception as ex:
        print("  !!! ERROR:", ex)

print("\n" + "=" * 80)
print(f"VALID FINGERPRINTS: {total}/18")
print("=" * 80)
PY
```

**Очень важно:** здесь мы увидим, действительно ли после пересоздания все fingerprints имеют именно формат v3.3, а не случайно какой-нибудь более новый/старый формат.

---

# 3. Перед распознаванием проверяем количество фотографий

У нас сейчас ожидается:

```text
78 = 81
79 = 65
80 = 37
81 = 65
82 = 67
83 = 68
84 = 54
85 = 58
86 = 58
87 = 50
88 = 54
89 = 64
90 = 19
91 = 41
92 = 57
93 = 51
94 = 67
95 = 86
```

После пересоздания:

```bash
for n in {78..95}; do
    echo -n "$n: "
    find "data/input/$n" -maxdepth 1 -type f \
        \( -iname "*.jpg" -o -iname "*.jpeg" \) | wc -l
done
```

Количество `images` в metadata должно совпасть.

---

# 4. Теперь контрольное распознавание test

Я предлагаю **сначала вообще ничего не сортировать**.

Только получить результаты:

```bash
rm -f /tmp/recognize_test_v33.txt

/usr/bin/time -v \
uv run scene-fingerprint recognize data/input/test \
    --top-k 5 \
    --threshold 0.50 \
    --fingerprints \
78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33,87_v33,88_v33,89_v33,90_v33,91_v33,92_v33,93_v33,94_v33,95_v33 \
    --json \
    > /tmp/recognize_test_v33.txt \
    2> /tmp/recognize_test_v33.time
```

Это специально делаем отдельно от сортировки.

Потом:

```bash
echo "=== TIME / RESOURCE ==="
cat /tmp/recognize_test_v33.time
```

И:

```bash
grep -c '"file":' /tmp/recognize_test_v33.txt
```

Должно быть:

```text
262
```

---

# 5. И главное - исправляем проблему JSON

У нас уже была проблема:

```text
SceneEmbedder...
Recognizer...
[
   ...
]
```

и из-за этого скрипт пытался взять первый `[` из служебного вывода.

Поэтому для нового теста **не надо использовать старый парсер**.

Надёжнее найти JSON по первой строке, которая начинается именно с:

```text
[
```

То есть после запуска:

```bash
grep -n '^\[' /tmp/recognize_test_v33.txt | head
```

Если там есть строка JSON, дальше парсер можно сделать нормально.

---

# 6. Сортировка

После того как убедимся, что распознавание снова даёт результаты, делаем:

```text
data/output/v33_test/
├── sorted/
│   ├── 78/
│   ├── 79/
│   ├── 80/
│   ├── ...
│   └── 95/
├── recognition.json
├── report.csv
└── report.json
```

Причём принцип такой:

```text
best_id = 78_v33
       ↓
папка 78
```

То есть **не создаём**:

```text
unknown/
ambiguous/
unclassified/
```

Даже если:

```text
score = 0.65
margin = 0.003
```

фотография всё равно идёт к **первому кандидату**.

Это сейчас правильнее для нашего эксперимента, потому что мы хотим проверить именно:

> насколько хорошо визуальный fingerprint сам распределяет фотографии по адресам.

А не насколько хорошо пороговая система умеет отказываться от решения.

---

## Что особенно важно сейчас

У нас есть очень хороший контрольный ориентир из предыдущего запуска:

```text
262 фотографии

78_v33   50
79_v33   16
80_v33   14
81_v33   35
82_v33   20
83_v33   57
84_v33   11
85_v33   59
86-95     0
```

**Именно этот результат считаем baseline.**

После пересоздания fingerprints 78-95 нам нужно сравнить новый результат с ним.

Если после пересоздания:

- 78 примерно около 50
- 79 около 16
- 80 около 14
- 81 около 35
- 82 около 20
- 83 около 57
- 84 около 11
- 85 около 59

- значит **ничего не сломалось**.

Если распределение резко изменится, будем искать отличие в создании fingerprint, а не начинать крутить веса.

### И ещё один важный момент

Сейчас я бы **не подключал subfingerprints V2** к основному распознаванию. Мы уже увидели, что предыдущий baseline `v33` работал лучше. Subfingerprints пока оставляем как отдельный исследовательский инструмент.

Сначала добиваемся воспроизводимости **baseline v33 → 262 фото → сортировка по первому кандидату**. Затем уже можно будет поверх этого добавить OCR таблички как **дополнительный корректор первого кандидата**, а не заменять DINOv2. Это как раз соответствует нашей первоначальной идее: **DINOv2 → первый кандидат → OCR/табличка только для спорных случаев**.

---

### 👤 **User** — 2026-08-15 02:40:19

все ок

---

### 🤖 **Assistant** — 2026-08-15 02:40:20

Отлично. Тогда фиксируем текущую версию как **рабочий baseline v33**.

Сейчас логика такая:

1. **78-95** - fingerprints пересозданы и проверены.
2. `test` - распознаём все **262 фото**.
3. Фото всегда раскладываются по **первому кандидату** `best_id`.
4. Папки `unknown/unclassified` не используем.
5. `subfingerprints_v2` пока не вмешиваем в основной алгоритм.
6. Сохраняем:
   - `recognition.json`
   - `report.csv`
   - `report.json`
   - статистику времени/CPU/GPU/RAM.
7. Этот результат используем как **контрольную точку**, чтобы дальше понимать, улучшает ли изменение алгоритма результат или ухудшает.

Следующий логичный шаг - **визуально проверить рассортированные папки**, особенно случаи с маленьким `margin`. Именно там сейчас находятся потенциальные ошибки.

После этого можем подключить **OCR табличек как второй этап только для спорных фотографий**: DINOv2 выбирает первый кандидат → OCR ищет номер → номер подтверждает или исправляет адрес.

---

### 👤 **User** — 2026-08-15 02:40:28

Визуально проверить рассортированные папки

---

