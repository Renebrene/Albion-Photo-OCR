## СЕССИЯ: ЛОРА ФИНАЛ 17 авг

**Создано:** 2026-08-16 21:41:46
**Обновлено:** 2026-08-19 17:07:59
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a820465-6788-83ea-b30d-7b8dfc43468a](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a820465-6788-83ea-b30d-7b8dfc43468a)

---

### 🤖 **Assistant** — 2026-08-16 22:11:07

> **Searching the web**
>
>
> **Searching the web**
>
> 
>
> Worked for a couple of seconds

Да. Только здесь веб не нужен - всё уже есть в проекте.

Сначала посмотрим **реальный формат входа Hybrid и реальный JSON обычного recognize**. Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ BENCHMARK JSON ================" && \
python - <<'PY'
import json
from pathlib import Path

p = Path("data/output/benchmark_sub_exp/benchmark.json")
data = json.loads(p.read_text(encoding="utf-8"))

print("keys:", list(data.keys()))
print("results:", len(data.get("results", [])))

if data.get("results"):
    print("\nFIRST RESULT:")
    print(json.dumps(data["results"][0], ensure_ascii=False, indent=2))
PY
echo "================ RECOGNIZER OUTPUT FORMAT ================" && \
sed -n '360,465p' app/core/recognizer.py
```

Это даст нам две вещи:

1. **точную структуру `benchmark.json`**, которую использует Hybrid v12;
2. точную структуру `best_id / candidates / scores / margin`, которую выдаёт текущий recognizer.

После этого уже сделаем **production runner Hybrid v12**, не меняя его веса и правила.

И главное - старый:

```text
scripts/sort_test_and_report_v2.py
```

пока **не трогаем**. Он остаётся контрольным тестовым sorter'ом.

---

### 👤 **User** — 2026-08-16 22:11:23

================ BENCHMARK JSON ================
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
================ RECOGNIZER OUTPUT FORMAT ================
                        ),

                        "best_image_score": float(
                            score.get(
                                "best_image_score",
                                0.0,
                            )
                        ),
                    }
                )

            ranked.sort(
                key=lambda item: item[
                    "score"
                ],
                reverse=True,
            )

            ranked = ranked[
                :max(
                    1,
                    int(top_k),
                )
            ]

            if not ranked:
                results.append(
                    {
                        "file": str(path),
                        "best_id": None,
                        "score": 0.0,
                        "second_score": 0.0,
                        "margin": 0.0,
                        "confidence": "NO_MATCH",
                        "status": "NO_MATCH",
                        "candidates": [],
                    }
                )

                continue

            best = ranked[0]

            best_score = float(
                best["score"]
            )

            if len(ranked) >= 2:
                second_score = float(
                    ranked[1]["score"]
                )
            else:
                second_score = 0.0

            margin = (
                best_score
                - second_score
            )

            confidence = (
                self._confidence(
                    best_score,
                    margin,
                )
            )

            status = (
                self._status_from_confidence(
                    confidence
                )
            )

            # Always use the best available candidate.
            #
            # The threshold is NO LONGER a rejection gate.
            # Even a weak candidate is accepted as the best
            # available address. The score/confidence are kept
            # for diagnostics.
            if best_score < threshold:
                best_id = None
                status = "NO_MATCH"
            else:
                best_id = best["id"]
                status = self._status_from_confidence(
                    confidence
                )

            results.append(
                {
                    "file": str(path),

                    "best_id": best_id,

                    "score": best_score,

                    "second_score": (
                        second_score
                    ),

                    "margin": float(
                        margin
                    ),

                    "confidence": confidence,

                    "status": status,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:11:24

Да, всё нормально — просто у тебя нет команды `python`, есть `python3`/`uv run python`.

Но главное: **формат recognizer уже подтвердился**. Он выдаёт именно то, что нам нужно:

```json
{
  "file": "...",
  "best_id": "...",
  "score": ...,
  "second_score": ...,
  "margin": ...,
  "confidence": "...",
  "status": "...",
  "candidates": [...]
}
```

И это хорошо стыкуется с Hybrid.

Нам теперь нужно получить **сам `benchmark.json`**. Запусти исправленный вариант:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ BENCHMARK JSON ================" && \
uv run python - <<'PY'
import json
from pathlib import Path

p = Path("data/output/benchmark_sub_exp/benchmark.json")

data = json.loads(p.read_text(encoding="utf-8"))

print("keys:", list(data.keys()))
print("results:", len(data.get("results", [])))

if data.get("results"):
    print("\nFIRST RESULT:")
    print(json.dumps(
        data["results"][0],
        ensure_ascii=False,
        indent=2
    ))
PY
```

### Что мы сейчас проверяем

Hybrid v12 ожидает:

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
margin
file
```

А recognizer уже подтверждённо выдаёт:

```text
best_id
score
second_score
margin
candidates[]
```

Поэтому, скорее всего, нам понадобится **не переписывать Hybrid**, а сделать адаптер:

```text
recognizer result
       ↓
adapter
       ↓
формат benchmark v12
       ↓
Hybrid v12
       ↓
final best_id
       ↓
sorter
```

Причём **формулу Hybrid v12 не трогаем вообще**.

После вывода `FIRST RESULT` я смогу точно сказать, где лучше поставить этот адаптер и дать следующий конкретный шаг.

---

### 👤 **User** — 2026-08-16 22:11:39

{
  "file": "/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG",
  "real": null,
  "top1": "85_v33",
  "top1_score": 0.9000321114063263,
  "top2": "93_v33",
  "top2_score": 0.8361609816551209,
  "top3": "78_v33",
  "top3_score": 0.8323249459266663,
  "top4": "86_v33",
  "top4_score": 0.828234815597534,
  "top5": "92_v33",
  "top5_score": 0.8217292141914367,
  "score": 0.9000321114063263,
  "margin": 0.06387112975120546,
  "confidence": "HIGH",
  "status": "CONFIDENT",
  "best_image": "85_014.JPG"
}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:11:40

Отлично. Теперь у нас есть **точное сопряжение двух форматов**.

### Что имеем

Обычный recognizer уже выдаёт практически весь необходимый вход для Hybrid v12:

```text
file
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
margin
```

Например:

```text
Ашхабадский_01.JPG

top1 = 85_v33       0.9000
top2 = 93_v33       0.8362
top3 = 78_v33       0.8323
top4 = 86_v33       0.8282
top5 = 92_v33       0.8217

margin = 0.06387
```

А Hybrid v12 делает именно то, что нам нужно: **DINO TOP1 остаётся основным решением, а Hybrid вмешивается только при сильных дополнительных признаках.**

---

## Но есть один важный нюанс

Hybrid v12 сейчас при каждом пограничном случае заново делает:

```python
query = embedder.embed_paths([image])[0]
```

То есть повторно считает DINO embedding.

Для benchmark это нормально.

Для рабочего pipeline — **лишняя работа**.

Но поскольку мы зафиксировали v12, **сейчас это не оптимизируем**.

Сначала сделаем production-версию **с абсолютно той же логикой**.

---

# Я предлагаю следующую схему

Не трогать:

```text
app/core/recognizer.py
scripts/benchmark_hybrid_v12_full.py
scripts/sort_test_and_report_v2.py
fingerprints *_v33
```

Создать новый файл:

```text
scripts/run_hybrid_v12.py
```

Он будет принимать:

```bash
uv run python scripts/run_hybrid_v12.py \
    --input data/input/test \
    --output data/output/test_sorted_hybrid_v12
```

и внутри:

```text
1. recognize
       ↓
2. получить top1..top5
       ↓
3. применить Hybrid v12
       ↓
4. получить FINAL best_id
       ↓
5. скопировать фото
       ↓
6. создать report.json
       ↓
7. создать statistics.json
```

### Ключевой момент

Внутри нового runner'а будет буквально сохранена логика:

```python
GLOBAL_WEIGHT = 10.0
SUB_WEIGHT = 2.5
NEIGHBOR_WEIGHT = 6.0

MARGIN_LIMIT = 0.02
```

и:

```python
if margin < MARGIN_LIMIT:
```

и:

```python
if sim > 0.88:
```

и:

```python
if sim > 0.92:
    bonus = 2.5
else:
    bonus = 1.0
```

и:

```python
if candidate != old and gain > 1.5:
    best = candidate
```

То есть **это будет не "новый Hybrid"**, а production-обвязка вокруг контрольной логики v12.

---

### И ещё лучше

Сделаем результат не просто:

```json
"new": "85_v33"
```

а сразу:

```json
"best_id": "85_v33",
"original_best_id": "85_v33",
"hybrid_changed": false
```

Если Hybrid исправил:

```json
"best_id": "78_v33",
"original_best_id": "85_v33",
"hybrid_changed": true
```

Тогда sorter вообще не должен знать о Hybrid.

Он просто получает:

```text
best_id
```

и делает свою работу.

Это очень чистое разделение:

```text
RECOGNITION
     ↓
HYBRID
     ↓
FINAL RESULT
     ↓
SORT
```

**Следующий шаг — создаём `run_hybrid_v12.py`, не меняя ни одной строки эталонного Hybrid v12.**

---

### 👤 **User** — 2026-08-16 22:12:22

давай

---

### 🤖 **Assistant** — 2026-08-16 22:12:25

Да. Делаем **production runner**, но контрольную логику Hybrid v12 не исправляем и не оптимизируем.

Есть даже важный момент: в самом v12 сейчас `SUB_WEIGHT` и `NEIGHBOR_WEIGHT` объявлены, но фактически не используются, а для соседей используется `+3.0`. **Оставляем именно так**, потому что это контрольная версия.

Создай новый файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > scripts/run_hybrid_v12.py <<'PY'
#!/usr/bin/env python3

import argparse
import json
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder

PROJECT = Path(__file__).resolve().parent.parent

SUB_DIR = PROJECT / "data/fingerprints_sub_exp"

# ============================================================
# HYBRID V12 — FROZEN CONTROL LOGIC
# ============================================================

MARGIN_LIMIT = 0.02

GLOBAL_WEIGHT = 10.0
SUB_WEIGHT = 2.5
NEIGHBOR_WEIGHT = 6.0

def normalize(x):
    x = np.asarray(x, dtype=np.float32)

    n = np.linalg.norm(x)

    if n > 0:
        x = x / n

    return x

def load_subs():
    result = {}

    if not SUB_DIR.exists():
        print(f"[Hybrid] WARNING: sub directory not found: {SUB_DIR}")
        return result

    for d in sorted(SUB_DIR.iterdir()):

        if not d.is_dir():
            continue

        f = d / "embeddings.npy"

        if not f.exists():
            continue

        emb = np.load(f)

        emb = np.array(
            [
                normalize(x)
                for x in emb
            ],
            dtype=np.float32,
        )

        result[d.name] = emb

    return result

def get_neighbor_votes(rows, index):
    votes = Counter()

    if index <= 0:
        return votes

    if index >= len(rows) - 1:
        return votes

    left = rows[index - 1]["top1"]
    right = rows[index + 1]["top1"]

    # FROZEN V12 RULE:
    # only complete agreement
    if left == right:
        votes[left] = 1

    return votes

def run_recognition(input_dir, fingerprints):
    """
    Run the existing DINO v33 recognizer.

    The recognizer itself is NOT modified.
    """

    fp_arg = ",".join(fingerprints)

    cmd = [
        "uv",
        "run",
        "scene-fingerprint",
        "recognize",
        str(input_dir),
        "--top-k",
        "5",
        "--threshold",
        "0.0",
        "--fingerprints",
        fp_arg,
        "--json",
    ]

    print("=" * 80)
    print("DINO v33 RECOGNITION")
    print("=" * 80)
    print("Input:", input_dir)
    print("Fingerprints:", ", ".join(fingerprints))
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

    decoder = json.JSONDecoder()
    data = None

    for i, ch in enumerate(combined):

        if ch != "[":
            continue

        try:
            candidate, _ = decoder.raw_decode(
                combined[i:]
            )

            if isinstance(candidate, list):
                data = candidate
                break

        except json.JSONDecodeError:
            pass

    if data is None:
        raise RuntimeError(
            "Не удалось найти JSON-массив в выводе recognition"
        )

    print("Images:", len(data))
    print(f"Recognition time: {elapsed:.2f} sec")

    return data, elapsed

def hybrid_v12(rows, embedder, subs):
    """
    Exact production adaptation of the frozen Hybrid v12 logic.

    Input:
        recognizer rows containing top1..top5.

    Output:
        rows with final best_id.
    """

    changed = []
    results = []
    sub_count = 0

    for i, row in enumerate(rows):

        old = row.get("top1")

        scores = defaultdict(float)

        # ====================================================
        # GLOBAL TOP-5
        # ====================================================

        for k in range(1, 6):

            fp = row.get(f"top{k}")
            sc = row.get(f"top{k}_score")

            if fp:
                scores[fp] += (
                    float(sc)
                    * GLOBAL_WEIGHT
                )

        # ====================================================
        # SUB ONLY BORDER CASES
        # ====================================================

        margin = row.get(
            "margin",
            1,
        )

        if margin < MARGIN_LIMIT:

            sub_count += 1

            image = Path(
                row["file"]
            )

            query = embedder.embed_paths(
                [image]
            )[0]

            query = normalize(query)

            # FROZEN V12:
            # only TOP1 and TOP2
            candidates = [
                row.get("top1"),
                row.get("top2"),
            ]

            for parent in candidates:

                if not parent:
                    continue

                for sub_id, sub_emb in subs.items():

                    if not sub_id.startswith(parent):
                        continue

                    sim = max(
                        sub_emb @ query
                    )

                    if sim > 0.88:

                        if sim > 0.92:
                            bonus = 2.5
                        else:
                            bonus = 1.0

                        scores[parent] += (
                            float(sim)
                            * bonus
                        )

        # ====================================================
        # SEQUENCE CONSENSUS
        # ====================================================

        neighbors = get_neighbor_votes(
            rows,
            i,
        )

        left_fp = None
        right_fp = None

        if i > 0:
            left_fp = rows[i - 1].get("top1")

        if i < len(rows) - 1:
            right_fp = rows[i + 1].get("top1")

        if (
            left_fp
            and right_fp
            and left_fp == right_fp
        ):
            # FROZEN V12:
            # actual implementation uses +3.0
            scores[left_fp] += 3.0

        # ====================================================
        # FINAL DECISION V12
        # ====================================================

        best = old

        ranked = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        if ranked:

            candidate = ranked[0][0]

            gain = (
                scores[candidate]
                - scores.get(old, 0)
            )

            if (
                candidate != old
                and gain > 1.5
            ):
                best = candidate

        old_score = scores.get(
            old,
            0,
        )

        new_score = scores.get(
            best,
            0,
        )

        hybrid_changed = best != old

        result = dict(row)

        result["original_best_id"] = old
        result["best_id"] = best

        result["hybrid_changed"] = hybrid_changed

        result["hybrid_old_score"] = old_score
        result["hybrid_score"] = new_score

        result["hybrid_margin"] = margin
        result["hybrid_neighbors"] = dict(neighbors)

        results.append(result)

        if (
            best != old
            and new_score > old_score
        ):
            changed.append(
                {
                    "file": Path(
                        row["file"]
                    ).name,
                    "old": old,
                    "new": best,
                    "margin": margin,
                    "neighbors": dict(neighbors),
                    "old_score": scores[old],
                    "new_score": scores[best],
                }
            )

    return results, changed, sub_count

def sort_results(rows, output_dir):
    """
    Copy photos according to FINAL Hybrid best_id.
    """

    print()
    print("=" * 80)
    print("SORTING")
    print("=" * 80)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    counters = Counter()
    sorted_rows = []

    for item in rows:

        source = Path(
            item["file"]
        )

        assigned_id = item.get(
            "best_id"
        )

        if not assigned_id:
            continue

        destination_dir = (
            output_dir / assigned_id
        )

        destination_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            destination_dir / source.name
        )

        shutil.copy2(
            source,
            destination,
        )

        counters[assigned_id] += 1

        sorted_rows.append(
            {
                "file": str(source),
                "filename": source.name,
                "assigned_id": assigned_id,
                "original_best_id": item.get(
                    "original_best_id"
                ),
                "hybrid_changed": item.get(
                    "hybrid_changed"
                ),
                "score": item.get("score"),
                "second_score": item.get(
                    "second_score"
                ),
                "margin": item.get("margin"),
                "confidence": item.get(
                    "confidence"
                ),
                "status": item.get("status"),
                "best_image": item.get(
                    "best_image"
                ),
                "best_image_score": item.get(
                    "best_image_score"
                ),
                "hybrid_old_score": item.get(
                    "hybrid_old_score"
                ),
                "hybrid_score": item.get(
                    "hybrid_score"
                ),
            }
        )

    for k in sorted(
        counters,
        key=lambda x: int(
            x.split("_")[0]
        ),
    ):
        print(
            f"{k:10s} {counters[k]:4d}"
        )

    return sorted_rows, counters

def main():

    parser = argparse.ArgumentParser(
        description="Production runner for frozen Hybrid v12"
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--first-address",
        type=int,
        default=78,
    )

    parser.add_argument(
        "--last-address",
        type=int,
        default=95,
    )

    args = parser.parse_args()

    input_dir = args.input
    output_dir = args.output

    if not input_dir.exists():
        raise RuntimeError(
            f"Нет папки: {input_dir}"
        )

    fingerprints = [
        f"{i}_v33"
        for i in range(
            args.first_address,
            args.last_address + 1,
        )
    ]

    print()
    print("=" * 80)
    print("SCENE FINGERPRINT — HYBRID V12 RUNNER")
    print("=" * 80)
    print()
    print("INPUT :", input_dir)
    print("OUTPUT:", output_dir)
    print()
    print("CONTROL:")
    print("  DINO        : v33")
    print("  HYBRID      : v12")
    print("  ADDRESSES   :", f"{args.first_address}-{args.last_address}")
    print()

    total_start = time.perf_counter()

    # --------------------------------------------------------
    # 1. DINO
    # --------------------------------------------------------

    recognition, recognition_time = run_recognition(
        input_dir,
        fingerprints,
    )

    # --------------------------------------------------------
    # 2. Load Hybrid subfingerprints
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("LOADING HYBRID SUBFINGERPRINTS")
    print("=" * 80)

    subs = load_subs()

    print("Subfingerprints:", len(subs))

    # --------------------------------------------------------
    # 3. Hybrid v12
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("HYBRID V12")
    print("=" * 80)

    settings = Settings()

    embedder = SceneEmbedder(
        settings
    )

    hybrid_rows, changed, sub_count = hybrid_v12(
        recognition,
        embedder,
        subs,
    )

    print()
    print("Checked:", len(hybrid_rows))
    print("Border cases:", sub_count)
    print("Hybrid changes:", len(changed))

    for item in changed:
        print()
        print(
            item["file"]
        )
        print(
            item["old"],
            "->",
            item["new"],
        )
        print(
            "margin:",
            item["margin"],
        )
        print(
            "neighbors:",
            item["neighbors"],
        )

    # --------------------------------------------------------
    # 4. Sort
    # --------------------------------------------------------

    sorted_rows, counters = sort_results(
        hybrid_rows,
        output_dir,
    )

    # --------------------------------------------------------
    # 5. Reports
    # --------------------------------------------------------

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    recognition_json = (
        output_dir / "recognition.json"
    )

    hybrid_json = (
        output_dir / "hybrid_v12.json"
    )

    report_json = (
        output_dir / "report.json"
    )

    statistics_json = (
        output_dir / "statistics.json"
    )

    recognition_json.write_text(
        json.dumps(
            recognition,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    hybrid_json.write_text(
        json.dumps(
            hybrid_rows,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report_json.write_text(
        json.dumps(
            sorted_rows,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    total_time = (
        time.perf_counter()
        - total_start
    )

    statistics = {
        "total_images": len(hybrid_rows),
        "sorted_images": len(sorted_rows),
        "recognition_time_seconds": recognition_time,
        "total_wall_time_seconds": total_time,
        "hybrid_border_cases": sub_count,
        "hybrid_changed": len(changed),
        "assigned": dict(counters),
        "control": {
            "recognizer": "DINOv2 v33",
            "rerank": "Hybrid v12",
            "margin_limit": MARGIN_LIMIT,
            "global_weight": GLOBAL_WEIGHT,
            "sub_weight": SUB_WEIGHT,
            "neighbor_weight": NEIGHBOR_WEIGHT,
        },
    }

    statistics_json.write_text(
        json.dumps(
            statistics,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)
    print()
    print("Images:", len(hybrid_rows))
    print("Hybrid changes:", len(changed))
    print(f"Recognition: {recognition_time:.2f} sec")
    print(f"Total:       {total_time:.2f} sec")
    print()
    print("Output:")
    print(output_dir)

if __name__ == "__main__":
    main()
PY
chmod +x scripts/run_hybrid_v12.py
```

### Пока ничего не запускаем

Сначала проверим, что файл синтаксически корректный:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile scripts/run_hybrid_v12.py && \
echo "HYBRID V12 RUNNER: OK"
```

Если получим:

```text
HYBRID V12 RUNNER: OK
```

следующим шагом запустим его **на тех же 256 фотографиях**, но в новый каталог, например:

```text
data/output/test_sorted_hybrid_v12/
```

и сравним результат с нашим эталоном **247 + 9 подтверждённых изменений**.

**До этого момента ничего из замороженного v33/v12 не изменяется.**

---

### 👤 **User** — 2026-08-16 22:13:01

далее

---

### 🤖 **Assistant** — 2026-08-16 22:13:01

Дальше логичный шаг — **не менять Hybrid v12**, а встроить его в рабочую сортировку как второй этап после базового DINOv2 v33.

Сейчас у нас уже подтверждено:

```text
DINOv2 v33
    ↓
TOP-5
    ↓
Hybrid v12
    ├── global
    ├── sub-fingerprint rerank
    └── sequence consensus
    ↓
final address
    ↓
копирование в папку адреса
```

Но в `sort_test_and_report_v2.py` сейчас есть важный момент:

```python
assigned_id = item.get("best_id")
```

То есть сортировщик **берёт только результат обычного recognizer** и пока вообще не использует результат Hybrid v12.

### Следующий шаг

Сделаем отдельный рабочий скрипт:

```text
scripts/sort_test_hybrid_v12.py
```

Он будет:

1. запускать обычный `recognize`;
2. получать TOP-5 для всех 256 фото;
3. передавать результат через **Hybrid v12**;
4. использовать `new` из Hybrid как `assigned_id`;
5. раскладывать фотографии по:

```text
data/output/test_sorted_hybrid_v12/
├── 78_v33/
├── 79_v33/
├── ...
└── 95_v33/
```

6. сохранять одновременно:
   - `recognition.json`
   - `hybrid.json`
   - `report.csv`
   - `report.json`
   - `statistics.json`

И главное — **сам `benchmark_hybrid_v12_full.py` не трогаем**.

Я бы именно сейчас сделал этот отдельный production-like sorter, чтобы контрольный Hybrid v12 оставался неизменным эталоном.

---

### 👤 **User** — 2026-08-16 22:13:11

далее

---

### 🤖 **Assistant** — 2026-08-16 22:13:13

Да. **Следующий этап — делаем рабочий сортировщик Hybrid v12, не меняя сам Hybrid v12.**

Важно: текущий `benchmark_hybrid_v12_full.py` работает от `benchmark.json`, поэтому для рабочего пайплайна нам нужен отдельный адаптер:

```text
recognizer v33
      ↓
TOP-5
      ↓
Hybrid v12 logic
      ↓
final ID
      ↓
sorting
```

При этом эталон остаётся нетронутым:

```text
scripts/benchmark_hybrid_v12_full.py
data/output/full_recognize_hybrid_v12_test.json
data/output/check_visual/hybrid_v12/
```

### Сейчас делаем только копию рабочего сортировщика

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp scripts/sort_test_and_report_v2.py scripts/sort_test_and_report_hybrid_v12.py && \
echo "CREATED:" && \
ls -lh scripts/sort_test_and_report_hybrid_v12.py
```

После этого **ничего пока не запускай**.

Пришли вывод. Следующим шагом я дам точечную замену внутри копии, чтобы:

- `v33` остался BASE;
- Hybrid v12 стал единственным rerank;
- сортировка использовала `new`;
- `sort_test_and_report_v2.py` остался старым контрольным вариантом;
- никаких изменений в весах Hybrid v12 не будет.

---

### 👤 **User** — 2026-08-16 22:13:29

chmod +x scripts/run_hybrid_v12.pyme:.2f} sec") sec")---------_address}")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile scripts/run_hybrid_v12.py && \
echo "HYBRID V12 RUNNER: OK"
HYBRID V12 RUNNER: OK
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
cp scripts/sort_test_and_report_v2.py scripts/sort_test_and_report_hybrid_v12.py && \
echo "CREATED:" && \
ls -lh scripts/sort_test_and_report_hybrid_v12.py
CREATED:
-rwxrwxr-x 1 alexice alexice 11K Aug 16 22:13 scripts/sort_test_and_report_hybrid_v12.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:13:30

Отлично. `run_hybrid_v12.py` компилируется, копия сортировщика создана.

Теперь **не трогаем эталонный `sort_test_and_report_v2.py`**. В новой копии сначала посмотрим, что уже есть в runner, и не будем вслепую переписывать логику.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,260p' scripts/run_hybrid_v12.py
```

И сразу после этого:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -nE 'BENCHMARK|SUB_DIR|OUT|MARGIN|WEIGHT|Hybrid|hybrid|top1|top2|new|old' \
scripts/run_hybrid_v12.py
```

Пришли оба вывода.

**Цель сейчас:** проверить интерфейс `run_hybrid_v12.py`, чтобы новый сортировщик просто подключил его как готовый этап rerank, а **Hybrid v12 и его веса вообще не изменялись**.

---

### 👤 **User** — 2026-08-16 22:13:49

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -nE 'BENCHMARK|SUB_DIR|OUT|MARGIN|WEIGHT|Hybrid|hybrid|top1|top2|new|old' \ 
scripts/run_hybrid_v12.py
19:SUB_DIR = PROJECT / "data/fingerprints_sub_exp"
26:MARGIN_LIMIT = 0.02
28:GLOBAL_WEIGHT = 10.0
29:SUB_WEIGHT = 2.5
30:NEIGHBOR_WEIGHT = 6.0
47:    if not SUB_DIR.exists():
48:        print(f"[Hybrid] WARNING: sub directory not found: {SUB_DIR}")
51:    for d in sorted(SUB_DIR.iterdir()):
85:    left = rows[index - 1]["top1"]
86:    right = rows[index + 1]["top1"]
113:        "--threshold",
179:def hybrid_v12(rows, embedder, subs):
181:    Exact production adaptation of the frozen Hybrid v12 logic.
184:        recognizer rows containing top1..top5.
196:        old = row.get("top1")
212:                    * GLOBAL_WEIGHT
224:        if margin < MARGIN_LIMIT:
241:                row.get("top1"),
242:                row.get("top2"),
284:            left_fp = rows[i - 1].get("top1")
287:            right_fp = rows[i + 1].get("top1")
302:        best = old
316:                - scores.get(old, 0)
320:                candidate != old
325:        old_score = scores.get(
326:            old,
330:        new_score = scores.get(
335:        hybrid_changed = best != old
339:        result["original_best_id"] = old
342:        result["hybrid_changed"] = hybrid_changed
344:        result["hybrid_old_score"] = old_score
345:        result["hybrid_score"] = new_score
347:        result["hybrid_margin"] = margin
348:        result["hybrid_neighbors"] = dict(neighbors)
353:            best != old
354:            and new_score > old_score
361:                    "old": old,
362:                    "new": best,
365:                    "old_score": scores[old],
366:                    "new_score": scores[best],
375:    Copy photos according to FINAL Hybrid best_id.
432:                "hybrid_changed": item.get(
433:                    "hybrid_changed"
450:                "hybrid_old_score": item.get(
451:                    "hybrid_old_score"
453:                "hybrid_score": item.get(
454:                    "hybrid_score"
475:        description="Production runner for frozen Hybrid v12"
526:    print("OUTPUT:", output_dir)
546:    # 2. Load Hybrid subfingerprints
559:    # 3. Hybrid v12
573:    hybrid_rows, changed, sub_count = hybrid_v12(
580:    print("Checked:", len(hybrid_rows))
582:    print("Hybrid changes:", len(changed))
590:            item["old"],
592:            item["new"],
608:        hybrid_rows,
625:    hybrid_json = (
626:        output_dir / "hybrid_v12.json"
646:    hybrid_json.write_text(
648:            hybrid_rows,
670:        "total_images": len(hybrid_rows),
674:        "hybrid_border_cases": sub_count,
675:        "hybrid_changed": len(changed),
679:            "rerank": "Hybrid v12",
680:            "margin_limit": MARGIN_LIMIT,
681:            "global_weight": GLOBAL_WEIGHT,
682:            "sub_weight": SUB_WEIGHT,
683:            "neighbor_weight": NEIGHBOR_WEIGHT,
701:    print("Images:", len(hybrid_rows))
702:    print("Hybrid changes:", len(changed))
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:13:51

Отлично. По выводу видно главное: **`run_hybrid_v12.py` уже является готовым production runner для замороженного Hybrid v12.** Переписывать Hybrid не нужно.

Особенно важны строки:

```text
179: def hybrid_v12(...)
181: Exact production adaptation of the frozen Hybrid v12 logic.
```

и:

```text
679: "rerank": "Hybrid v12"
680: "margin_limit": MARGIN_LIMIT
681: "global_weight": GLOBAL_WEIGHT
682: "sub_weight": SUB_WEIGHT
683: "neighbor_weight": NEIGHBOR_WEIGHT
```

То есть сейчас архитектура уже правильная:

```text
                    ┌─────────────────────┐
                    │  DINOv2 v33         │
                    │  BASE recognizer     │
                    └──────────┬──────────┘
                               │
                              TOP-5
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Hybrid v12       │
                    │                     │
                    │ Global              │
                    │ Sub-fingerprint     │
                    │ Neighbor consensus  │
                    └──────────┬──────────┘
                               │
                          FINAL best_id
                               │
                               ▼
                    ┌─────────────────────┐
                    │      SORT           │
                    └─────────────────────┘
```

### Следующий шаг

Теперь **не меняем код вообще**. Сначала запускаем `run_hybrid_v12.py` на тех же 256 фотографиях и проверяем, что runner воспроизводит наш контрольный результат.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
rm -rf data/output/test_sorted_hybrid_v12 && \
uv run python scripts/run_hybrid_v12.py \
  --input data/input/test \
  --output data/output/test_sorted_hybrid_v12
```

Если у runner другие аргументы CLI и он скажет `unrecognized arguments`, **ничего не исправляй** — просто пришли ошибку.

Нас сейчас интересуют четыре числа:

```text
Images
Hybrid changes
Hybrid border cases
output directory
```

И особенно:

```text
Hybrid changes: 9
```

Если получаем те же **9 подтверждённых изменений**, значит мы успешно отделили:

**замороженный Hybrid v12 → рабочий runner → будущую сортировку.**

После этого подключим сортировку фотографий.

---

### 👤 **User** — 2026-08-16 22:15:11

_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9065.29it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 711, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 573, in main
    hybrid_rows, changed, sub_count = hybrid_v12(
                                      ^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 275, in hybrid_v12
    neighbors = get_neighbor_votes(
                ^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 85, in get_neighbor_votes
    left = rows[index - 1]["top1"]
           ~~~~~~~~~~~~~~~^^^^^^^^
KeyError: 'top1'

---

### 🤖 **Assistant** — 2026-08-16 22:15:13

Да — это **не проблема Hybrid v12**. Мы нашли несовпадение формата данных.

`run_hybrid_v12.py` ожидает:

```text
top1
top2
top3
...
```

а текущий `recognize --json` возвращает:

```text
best_id
score
second_score
margin
candidates
```

То есть Hybrid падает именно здесь:

```python
left = rows[index - 1]["top1"]
```

### Важный момент

**Hybrid v12 не трогаем.** Его логика уже заморожена.

Нужно сделать адаптацию формата:

```text
recognizer JSON
       ↓
adapter
       ↓
top1..top5
       ↓
frozen Hybrid v12
       ↓
final best_id
```

Причём это даже лучше, чем менять сам Hybrid.

### Сначала проверим точный формат `candidates`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run scene-fingerprint recognize \
  data/input/test \
  --top-k 5 \
  --threshold 0.0 \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33,87_v33,88_v33,89_v33,90_v33,91_v33,92_v33,93_v33,94_v33,95_v33 \
  --json > /tmp/recognition_v33.json && \
python3 - <<'PY'
import json

with open("/tmp/recognition_v33.json", encoding="utf-8") as f:
    data = json.load(f)

print("TYPE:", type(data).__name__)
print("COUNT:", len(data))
print(json.dumps(data[0], ensure_ascii=False, indent=2))
PY
```

**Именно этот вывод пришли мне.**

После этого я дам маленький адаптер, который преобразует:

```text
candidates[0..4]
```

в:

```text
top1
top1_score
top2
top2_score
...
top5
top5_score
```

и мы снова запустим **тот же самый Hybrid v12 без изменения его весов и правил**.

---

### 👤 **User** — 2026-08-16 22:16:53

Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8488.57it/s]
Traceback (most recent call last):
  File "<stdin>", line 4, in <module>
  File "/usr/lib/python3.12/json/__init__.py", line 293, in load
    return loads(fp.read(),
           ^^^^^^^^^^^^^^^^
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

### 🤖 **Assistant** — 2026-08-16 22:16:55

Да, здесь всё понятно. Ошибка **не в recognizer** и не в Hybrid.

Мы перенаправили весь stdout в файл:

```bash
> /tmp/recognition_v33.json
```

а `SceneEmbedder` печатает служебные сообщения туда же:

```text
[SceneEmbedder] ...
```

Поэтому файл оказался не чистым JSON.

Причём у нас уже есть `find_json()` в проекте, который как раз умеет отделять JSON от таких сообщений.

### Делаем проще

Не запускаем повторно распознавание. Нам нужно получить **чистый JSON из уже имеющегося вывода**.

Сначала посмотрим, что реально лежит в файле:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
head -20 /tmp/recognition_v33.json
```

И:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
tail -5 /tmp/recognition_v33.json
```

Пришли этот вывод.

После этого я дам команду, которая извлечёт настоящий JSON без повторного запуска DINOv2.

И ещё: предупреждение

```text
Warning: You are sending unauthenticated requests to the HF Hub
```

**сейчас можно игнорировать**. Модель загрузилась нормально:

```text
Loading weights: 100%
```

Никакой токен сейчас настраивать не надо.

---

### 👤 **User** — 2026-08-16 22:17:19

[Recognizer] Query images: 257
[Recognizer] Fingerprints: 78_v33, 79_v33, 80_v33, 81_v33, 82_v33, 83_v33, 84_v33, 85_v33, 86_v33, 87_v33, 88_v33, 89_v33, 90_v33, 91_v33, 92_v33, 93_v33, 94_v33, 95_v33
[Recognizer] CPU workers: 6
[
  {
    "file": "data/input/test/Screenshot from 2026-08-16 00-38-11.png",
    "best_id": "89_v33",
    "score": 0.4969404840469361,
    "second_score": 0.4236461102962494,
    "margin": 0.0732943737506867,
    "confidence": "NO_MATCH",
    "status": "NO_MATCH",
    "best_image": "89_35.JPG",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
tail -5 /tmp/recognition_v33.json
        "best_image_score": 0.8583124876022339
      }
    ]
  }
]
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:17:20

Отлично. Теперь причина полностью ясна.

В `/tmp/recognition_v33.json` есть служебные строки:

```text
[Recognizer] Query images: 257
[Recognizer] Fingerprints: ...
[Recognizer] CPU workers: 6
```

а дальше идёт **валидный JSON-массив**. Поэтому `json.load()` и падал.

И ещё важная деталь: сейчас распознано **257 изображений**, а контрольный benchmark был на **256**. В `test` появилась дополнительная картинка:

```text
Screenshot from 2026-08-16 00-38-11.png
```

Пока это не проблема — просто фиксируем.

### Теперь извлекаем чистый JSON

Не запускаем DINO повторно. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import json
from pathlib import Path

src = Path("/tmp/recognition_v33.json")
dst = Path("/tmp/recognition_v33_clean.json")

text = src.read_text(encoding="utf-8")

start = text.find("[")
if start < 0:
    raise RuntimeError("JSON array not found")

data, _ = json.JSONDecoder().raw_decode(text[start:])

dst.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("CLEAN JSON:", dst)
print("IMAGES:", len(data))
print()
print(json.dumps(data[0], ensure_ascii=False, indent=2))
PY
```

Ожидаем:

```text
CLEAN JSON: /tmp/recognition_v33_clean.json
IMAGES: 257
```

После этого **не запускай Hybrid ещё раз**.

Пришли вывод команды. Затем мы аккуратно адаптируем `candidates → top1..top5` и запустим **замороженный Hybrid v12 на этих же самых результатах**, без повторного вычисления DINO.

---

### 👤 **User** — 2026-08-16 22:17:58

dst = Path("/tmp/recognition_v33_clean.json")

text = src.read_text(encoding="utf-8")

start = text.find("[")
if start < 0:
    raise RuntimeError("JSON array not found")

data, _ = json.JSONDecoder().raw_decode(text[start:])

dst.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("CLEAN JSON:", dst)
print("IMAGES:", len(data))
PYint(json.dumps(data[0], ensure_ascii=False, indent=2))
Traceback (most recent call last):
  File "<stdin>", line 13, in <module>
  File "/usr/lib/python3.12/json/decoder.py", line 355, in raw_decode
    raise JSONDecodeError("Expecting value", s, err.value) from None
json.decoder.JSONDecodeError: Expecting value: line 1 column 2 (char 1)

---

### 🤖 **Assistant** — 2026-08-16 22:18:14

Да. Я вижу ошибку в моей предыдущей команде: `text.find("[")` находит **первую `[` в `[Recognizer]`**, а не начало JSON.

Исправляем. Ничего заново не запускаем.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import json
from pathlib import Path

src = Path("/tmp/recognition_v33.json")
dst = Path("/tmp/recognition_v33_clean.json")

text = src.read_text(encoding="utf-8")

# Ищем строку, которая действительно начинается с JSON-массива
start = None

for line_start in [0] + [i + 1 for i, c in enumerate(text) if c == "\n"]:
    if text[line_start:].lstrip().startswith("[\n"):
        start = line_start + len(text[line_start:]) - len(text[line_start:].lstrip())
        break

if start is None:
    raise RuntimeError("JSON array not found")

data, _ = json.JSONDecoder().raw_decode(text[start:])

dst.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("CLEAN JSON:", dst)
print("IMAGES:", len(data))
print()
print(json.dumps(data[0], ensure_ascii=False, indent=2))
PY
```

Должно получиться примерно:

```text
CLEAN JSON: /tmp/recognition_v33_clean.json
IMAGES: 257
```

После этого **не запускаем распознавание и не трогаем Hybrid v12**. Нам уже достаточно имеющегося результата.

---

### 👤 **User** — 2026-08-16 22:31:59

_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8161.41it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 711, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 573, in main
    hybrid_rows, changed, sub_count = hybrid_v12(
                                      ^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 275, in hybrid_v12
    neighbors = get_neighbor_votes(
                ^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 85, in get_neighbor_votes
    left = rows[index - 1]["top1"]
           ~~~~~~~~~~~~~~~^^^^^^^^
KeyError: 'top1'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:32:04

Да. Здесь проблема **не в Hybrid v12**, а в формате входных данных.

### Что произошло

`run_hybrid_v12.py` ожидает старый benchmark-формат:

```python
row["top1"]
row["top1_score"]
row["top2"]
row["top2_score"]
...
```

А текущий `recognizer` выдаёт новый production-формат:

```json
{
  "best_id": "89_v33",
  "score": 0.4969,
  "second_score": 0.4236,
  "candidates": [...]
}
```

Поэтому падает:

```text
KeyError: 'top1'
```

**Сам Hybrid v12 не трогаем.** Нужно сделать адаптер `recognizer → benchmark format` перед вызовом `hybrid_v12()`.

---

## 1. Сначала посмотрим реальную структуру `candidates`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import json

p = "/tmp/recognition_v33_clean.json"

with open(p, encoding="utf-8") as f:
    data = json.load(f)

print("IMAGES:", len(data))
print()
print(json.dumps(data[0], ensure_ascii=False, indent=2))
PY
```

Это важный шаг: нам нужно увидеть, как именно сейчас выглядят `candidates`.

---

## 2. Но саму причину уже можно исправить

В `scripts/run_hybrid_v12.py` перед:

```python
hybrid_rows, changed, sub_count = hybrid_v12(
```

нужно добавить преобразование.

Сделаем **отдельную функцию**, чтобы вообще не менять frozen Hybrid v12:

```python
def adapt_recognizer_rows(rows):
    """
    Convert current recognizer output into the legacy
    top1/top2/... format expected by frozen Hybrid v12.
    Hybrid logic itself remains untouched.
    """

    adapted = []

    for row in rows:
        new_row = dict(row)

        candidates = row.get("candidates", [])

        # Current recognizer format
        if candidates:
            for n, candidate in enumerate(candidates[:5], start=1):
                new_row[f"top{n}"] = candidate.get("id")
                new_row[f"top{n}_score"] = float(
                    candidate.get("score", 0.0)
                )

        else:
            # Fallback from flat recognizer fields
            best_id = row.get("best_id")
            best_score = row.get("score", 0.0)

            if best_id:
                new_row["top1"] = best_id
                new_row["top1_score"] = float(best_score)

            second_score = row.get("second_score", 0.0)

            if second_score:
                new_row["top2_score"] = float(second_score)

        # Ensure all expected fields exist
        for n in range(1, 6):
            new_row.setdefault(f"top{n}", None)
            new_row.setdefault(f"top{n}_score", 0.0)

        # Hybrid uses margin
        new_row.setdefault("margin", 0.0)

        adapted.append(new_row)

    return adapted
```

И непосредственно перед Hybrid:

```python
rows = adapt_recognizer_rows(rows)

hybrid_rows, changed, sub_count = hybrid_v12(
    rows,
    embedder,
    subs,
)
```

---

### Но есть один важный момент

Я **не хочу сейчас давать тебе слепую замену**, пока не увидим `candidates`.

Потому что для Hybrid v12 критично, чтобы было именно:

```text
candidate 1 → id + score
candidate 2 → id + score
candidate 3 → id + score
candidate 4 → id + score
candidate 5 → id + score
```

А не просто:

```text
best_id
second_score
```

Иначе мы потеряем информацию, на которой работает GLOBAL TOP-5.

---

## 3. И ещё одна вещь

Вот это:

```text
Warning: You are sending unauthenticated requests to the HF Hub...
```

**не имеет отношения к ошибке.**

И:

```text
[SceneEmbedder] patch extraction=DISABLED (compact)
```

тоже нормально.

Для нашего frozen Hybrid v12 это как раз ожидаемая конфигурация.

---

### Сейчас делаем только это

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import json

p = "/tmp/recognition_v33_clean.json"

with open(p, encoding="utf-8") as f:
    data = json.load(f)

print("IMAGES:", len(data))
print()
print(json.dumps(data[0], ensure_ascii=False, indent=2))
PY
```

**Пришли вывод первого объекта.**

После этого я дам точный патч для `run_hybrid_v12.py`, причем:

**DINO v33 → НЕ ТРОГАЕМ**  
**Recognizer → НЕ ТРОГАЕМ**  
**Hybrid v12 → НЕ ТРОГАЕМ**  
**только адаптер формата между ними.**

Это самый правильный вариант для сохранения нашего эталона.

---

### 👤 **User** — 2026-08-16 22:32:33

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import json

p = "/tmp/recognition_v33_clean.json"

with open(p, encoding="utf-8") as f:
    data = json.load(f)

print("IMAGES:", len(data))
print()
print(json.dumps(data[0], ensure_ascii=False, indent=2))
PY
IMAGES: 257

{
  "file": "data/input/test/Screenshot from 2026-08-16 00-38-11.png",
  "best_id": "89_v33",
  "score": 0.4969404840469361,
  "second_score": 0.4236461102962494,
  "margin": 0.0732943737506867,
  "confidence": "NO_MATCH",
  "status": "NO_MATCH",
  "best_image": "89_35.JPG",
  "best_image_score": 0.42484360933303833,
  "candidates": [
    {
      "id": "89_v33",
      "score": 0.4969404840469361,
      "global": 0.3631412982940674,
      "environment": 0.8440547585487366,
      "color": 0.6481564044952393,
      "spatial": 0.9519891738891602,
      "best_image": "89_35.JPG",
      "best_image_score": 0.42484360933303833
    },
    {
      "id": "95_v33",
      "score": 0.4236461102962494,
      "global": 0.24489960074424744,
      "environment": 0.8766330480575562,
      "color": 0.6784668564796448,
      "spatial": 0.9799033403396606,
      "best_image": "95_041.JPG",
      "best_image_score": 0.3332248628139496
    },
    {
      "id": "86_v33",
      "score": 0.41980840802192687,
      "global": 0.2576867341995239,
      "environment": 0.8361449241638184,
      "color": 0.6269475221633911,
      "spatial": 0.9437460899353027,
      "best_image": "86_057.JPG",
      "best_image_score": 0.2997652292251587
    },
    {
      "id": "85_v33",
      "score": 0.4130537739396095,
      "global": 0.24715556204319,
      "environment": 0.8369951248168945,
      "color": 0.6347363591194153,
      "spatial": 0.9404770135879517,
      "best_image": "85_049.JPG",
      "best_image_score": 0.3108336329460144
    },
    {
      "id": "90_v33",
      "score": 0.40980753064155584,
      "global": 0.28924837708473206,
      "environment": 0.7607811093330383,
      "color": 0.40204644203186035,
      "spatial": 0.9011397957801819,
      "best_image": "90_003.jpg",
      "best_image_score": 0.3395891785621643
    }
  ]
}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:32:34

Отлично. Теперь всё ясно. Формат `candidates` **полностью содержит TOP-5**, поэтому ничего из информации терять не нужно.

И главное: **Hybrid v12 оставляем абсолютно неизменным.** Исправляем только входной адаптер.

### 1. Добавляем адаптер

В `scripts/run_hybrid_v12.py` найди функцию:

```python
def hybrid_v12(rows, embedder, subs):
```

И **непосредственно перед ней** вставь:

```python
def adapt_recognizer_rows(rows):
    """
    Adapter:
    current recognizer format -> frozen Hybrid v12 format.

    Hybrid v12 itself is NOT modified.
    """

    adapted = []

    for row in rows:
        item = dict(row)

        candidates = row.get("candidates", [])

        for n in range(1, 6):
            item[f"top{n}"] = None
            item[f"top{n}_score"] = 0.0

        for n, candidate in enumerate(candidates[:5], start=1):
            item[f"top{n}"] = candidate.get("id")
            item[f"top{n}_score"] = float(
                candidate.get("score", 0.0)
            )

        adapted.append(item)

    return adapted
```

---

### 2. Передаём адаптированные строки в Hybrid

Найди примерно строку:

```python
hybrid_rows, changed, sub_count = hybrid_v12(
    rows,
    embedder,
    subs
)
```

Замени на:

```python
rows = adapt_recognizer_rows(rows)

hybrid_rows, changed, sub_count = hybrid_v12(
    rows,
    embedder,
    subs
)
```

---

### 3. Проверяем синтаксис

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile scripts/run_hybrid_v12.py && \
echo "RUNNER: OK"
```

Если получим:

```text
RUNNER: OK
```

тогда запускаем.

---

### Важный момент

Твой текущий первый объект:

```text
89_v33  0.4969
95_v33  0.4236
86_v33  0.4198
85_v33  0.4130
90_v33  0.4098
```

после адаптера станет для Hybrid ровно:

```text
top1 = 89_v33
top2 = 95_v33
top3 = 86_v33
top4 = 85_v33
top5 = 90_v33
```

То есть существующая логика:

```python
for k in range(1, 6):
```

будет работать **точно так, как она работала на benchmark**.

И `margin` останется исходным:

```text
0.07329
```

А значит border-case:

```python
if margin < 0.02:
```

тоже работает штатно.

### Получается правильная архитектура

```text
DINOv2 v33
     ↓
Recognizer
     ↓
current format
     ↓
[ADAPTER]
     ↓
legacy top1..top5 format
     ↓
FROZEN HYBRID v12
     ↓
final Hybrid best_id
```

**Никаких изменений весов `10 / 2.5 / 6`, порога `0.02` или правила `gain > 1.5`.**

Сначала сделай `py_compile`. Если `RUNNER: OK` — следующим шагом запускаем полный Hybrid на **257 фотографиях** и сравним количество изменений с контрольными **9 изменениями / 256**.

---

### 👤 **User** — 2026-08-16 22:32:57

сделай, хотя раньше это было не нужнол

---

### 🤖 **Assistant** — 2026-08-16 22:33:02

Да. И ты прав: **раньше адаптер был не нужен**, потому что `benchmark_hybrid_v12_full.py` напрямую получал benchmark с `top1..top5`. Сейчас мы подключаем Hybrid v12 к **новому production recognizer**, который отдаёт `best_id + candidates[]`.

Сделаем адаптер, **не меняя сам Hybrid v12**.

Выполни одной командой:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

p = Path("scripts/run_hybrid_v12.py")
text = p.read_text(encoding="utf-8")

marker = "def hybrid_v12(rows, embedder, subs):"

adapter = '''def adapt_recognizer_rows(rows):
    """
    Adapter:
    current recognizer format -> frozen Hybrid v12 format.

    Hybrid v12 logic itself is NOT modified.
    """

    adapted = []

    for row in rows:
        item = dict(row)

        candidates = row.get("candidates", [])

        for n in range(1, 6):
            item[f"top{n}"] = None
            item[f"top{n}_score"] = 0.0

        for n, candidate in enumerate(candidates[:5], start=1):
            item[f"top{n}"] = candidate.get("id")
            item[f"top{n}_score"] = float(
                candidate.get("score", 0.0)
            )

        adapted.append(item)

    return adapted

'''

if "def adapt_recognizer_rows(rows):" not in text:
    if marker not in text:
        raise SystemExit("ERROR: hybrid_v12() marker not found")

    text = text.replace(marker, adapter + marker, 1)

old = '''    hybrid_rows, changed, sub_count = hybrid_v12(
        rows,
        embedder,
        subs,
    )'''

new = '''    rows = adapt_recognizer_rows(rows)

    hybrid_rows, changed, sub_count = hybrid_v12(
        rows,
        embedder,
        subs,
    )'''

if old in text:
    text = text.replace(old, new, 1)
elif "rows = adapt_recognizer_rows(rows)" not in text:
    raise SystemExit("ERROR: hybrid_v12() call pattern not found")

p.write_text(text, encoding="utf-8")

print("PATCHED:", p)
PY
```

Потом сразу проверяем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile scripts/run_hybrid_v12.py && \
echo "HYBRID V12 ADAPTER: OK"
```

И **пока не запускаем полный прогон**. Сначала проверим, что адаптер действительно превратил текущий `candidates[]` в `top1..top5` и что Hybrid видит те же 5 кандидатов.

Это как раз правильное разделение:

```text
recognizer
    ↓
adapter              ← новое, техническое
    ↓
top1..top5
    ↓
Hybrid v12           ← ЭТАЛОН, не трогаем
```

После `HYBRID V12 ADAPTER: OK` дам короткую проверку перед полным запуском.

---

### 👤 **User** — 2026-08-16 22:33:27

ок

---

### 🤖 **Assistant** — 2026-08-16 22:33:27

Отлично. Тогда следующий шаг — **только проверка адаптера**, без изменения логики Hybrid v12.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile scripts/run_hybrid_v12.py && \
echo "HYBRID V12 ADAPTER: OK"
```

Если получим:

```text
HYBRID V12 ADAPTER: OK
```

— запускаем полный прогон на 257 изображениях и смотрим:

- сколько обработано;
- сколько Hybrid rerank cases;
- сколько изменений;
- какие именно адреса изменились;
- не отличается ли поведение от контрольных **9 изменений на 256**.

**Эталон Hybrid v12 не меняем.**

---

### 👤 **User** — 2026-08-16 22:33:39

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile scripts/run_hybrid_v12.py && \
echo "HYBRID V12 ADAPTER: OK"
HYBRID V12 ADAPTER: OK

---

### 🤖 **Assistant** — 2026-08-16 22:33:40

Отлично. Адаптер синтаксически чистый. Теперь **полный Hybrid v12 на текущих 257 снимках**.

Запускай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/run_hybrid_v12.py
```

После окончания **пришли весь вывод**, особенно блок:

```text
Images:
Hybrid changes:
Hybrid border cases:
```

и список:

```text
old -> new
```

Сейчас ничего больше не меняем. Проверяем, что новый production-путь воспроизводит поведение нашего **замороженного Hybrid v12**.

---

### 👤 **User** — 2026-08-16 22:34:01

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/run_hybrid_v12.py
usage: run_hybrid_v12.py [-h] --input INPUT --output OUTPUT
                         [--first-address FIRST_ADDRESS]
                         [--last-address LAST_ADDRESS]
run_hybrid_v12.py: error: the following arguments are required: --input, --output
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:34:02

Да, всё нормально — это не ошибка Hybrid. У `run_hybrid_v12.py` предусмотрены обязательные параметры `--input` и `--output`.

Запускаем на нашей текущей папке `test` и сохраняем результат отдельно, чтобы **не затронуть эталон**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/run_hybrid_v12.py \
  --input data/input/test \
  --output data/output/test_hybrid_v12
```

Это должно обработать текущие **257 изображений** и создать:

```text
data/output/test_hybrid_v12/
```

После завершения пришли вывод целиком. Особенно нужны:

```text
Images:
Hybrid changes:
Hybrid border cases:
```

и список изменений `old -> new`.

**Эталонные файлы Hybrid v12 при этом не затрагиваем.**

---

### 👤 **User** — 2026-08-16 22:35:16

[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 711, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 573, in main
    hybrid_rows, changed, sub_count = hybrid_v12(
                                      ^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 275, in hybrid_v12
    neighbors = get_neighbor_votes(
                ^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 85, in get_neighbor_votes
    left = rows[index - 1]["top1"]
           ~~~~~~~~~~~~~~~^^^^^^^^
KeyError: 'top1'

---

### 🤖 **Assistant** — 2026-08-16 22:35:18

Да — теперь видно, что **адаптер добавился, но в `main()` его результат не попал в `hybrid_v12()`**. Ошибка абсолютно та же, значит `hybrid_v12()` всё ещё получает исходные `rows`.

Ничего в Hybrid v12 не меняем. Сейчас проверим ровно место вызова.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba scripts/run_hybrid_v12.py | sed -n '555,585p'
```

Пришли вывод этих строк.

После этого дам **точечную замену 2–3 строк**. Не будем больше трогать остальной файл.

---

### 👤 **User** — 2026-08-16 22:35:36

KeyError: 'top1'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba scripts/run_hybrid_v12.py | sed -n '555,585p'
   555	
   556	    print("Subfingerprints:", len(subs))
   557	
   558	    # --------------------------------------------------------
   559	    # 3. Hybrid v12
   560	    # --------------------------------------------------------
   561	
   562	    print()
   563	    print("=" * 80)
   564	    print("HYBRID V12")
   565	    print("=" * 80)
   566	
   567	    settings = Settings()
   568	
   569	    embedder = SceneEmbedder(
   570	        settings
   571	    )
   572	
   573	    hybrid_rows, changed, sub_count = hybrid_v12(
   574	        recognition,
   575	        embedder,
   576	        subs,
   577	    )
   578	
   579	    print()
   580	    print("Checked:", len(hybrid_rows))
   581	    print("Border cases:", sub_count)
   582	    print("Hybrid changes:", len(changed))
   583	
   584	    for item in changed:
   585	        print()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:35:37

Да, нашли точно. На строке 574 передаётся `recognition`, а не адаптированный список.

Исправляем **только это место**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/run_hybrid_v12.py")
text = p.read_text(encoding="utf-8")

old = """    hybrid_rows, changed, sub_count = hybrid_v12(
        recognition,
        embedder,
        subs,
    )"""

new = """    recognition = adapt_recognizer_rows(recognition)

    hybrid_rows, changed, sub_count = hybrid_v12(
        recognition,
        embedder,
        subs,
    )"""

if old not in text:
    raise SystemExit("TARGET BLOCK NOT FOUND")

text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")

print("PATCHED: recognition -> adapt_recognizer_rows -> Hybrid v12")
PY
```

Проверяем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile scripts/run_hybrid_v12.py && \
echo "HYBRID V12 PIPELINE: OK"
```

И затем запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/run_hybrid_v12.py \
  --input data/input/test \
  --output data/output/test_hybrid_v12
```

Теперь цепочка будет именно такая:

```text
recognizer
    ↓
recognition
    ↓
adapt_recognizer_rows()
    ↓
top1 ... top5
    ↓
FROZEN HYBRID v12
```

**Сам алгоритм Hybrid v12 не меняем вообще.**

---

### 👤 **User** — 2026-08-16 22:36:59

[SceneEmbedder] Ready.
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 713, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/run_hybrid_v12.py", line 573, in main
    recognition = adapt_recognizer_rows(recognition)
                  ^^^^^^^^^^^^^^^^^^^^^
NameError: name 'adapt_recognizer_rows' is not defined

---

### 🤖 **Assistant** — 2026-08-16 22:37:06

Да, теперь причина окончательно ясна: **вызов адаптера есть, а самой функции Python не видит**. Значит предыдущая вставка функции фактически не попала в файл в доступной области.

Сейчас не будем гадать. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n "adapt_recognizer_rows\|def hybrid_v12" scripts/run_hybrid_v12.py
```

Пришли вывод.

После этого я дам **одну точную команду**, которая поставит функцию в правильное место — непосредственно перед `def hybrid_v12(...)`.

Сам Hybrid v12 пока **не трогаем**.

---

### 👤 **User** — 2026-08-16 22:37:19

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n "adapt_recognizer_rows\|def hybrid_v12" scripts/run_hybrid_v12.py
179:def hybrid_v12(rows, embedder, subs):
573:    recognition = adapt_recognizer_rows(recognition)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:37:21

Да, всё подтверждено: функции нет, остался только её вызов.

Сейчас вставим её **ровно перед строкой 179**, не затрагивая Hybrid v12.

Выполни:

```bash id="r9wq8j"
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/run_hybrid_v12.py")
text = p.read_text(encoding="utf-8")

marker = "def hybrid_v12(rows, embedder, subs):"

adapter = '''def adapt_recognizer_rows(rows):
    """
    Convert current recognizer output into the legacy
    top1..top5 format required by frozen Hybrid v12.
    """

    adapted = []

    for row in rows:
        item = dict(row)

        candidates = row.get("candidates", [])

        for n in range(1, 6):
            item[f"top{n}"] = None
            item[f"top{n}_score"] = 0.0

        for n, candidate in enumerate(candidates[:5], start=1):
            item[f"top{n}"] = candidate.get("id")
            item[f"top{n}_score"] = float(
                candidate.get("score", 0.0)
            )

        adapted.append(item)

    return adapted

'''

if "def adapt_recognizer_rows(rows):" in text:
    raise SystemExit("Adapter already exists")

if marker not in text:
    raise SystemExit("Hybrid v12 function not found")

text = text.replace(marker, adapter + marker, 1)

p.write_text(text, encoding="utf-8")

print("ADAPTER INSERTED")
PY
```

Теперь сразу проверяем:

```bash id="7n8r4m"
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n "adapt_recognizer_rows\|def hybrid_v12" scripts/run_hybrid_v12.py && \
uv run python -m py_compile scripts/run_hybrid_v12.py && \
echo "HYBRID V12 PIPELINE: OK"
```

Ожидаем:

```text
179:def adapt_recognizer_rows(rows):
...
207:def hybrid_v12(rows, embedder, subs):
573:    recognition = adapt_recognizer_rows(recognition)
HYBRID V12 PIPELINE: OK
```

После этого запускаем тот же полный прогон:

```bash id="i7ojfr"
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/run_hybrid_v12.py \
  --input data/input/test \
  --output data/output/test_hybrid_v12
```

Теперь `KeyError: top1` и `NameError` уже не должны возникнуть.

---

### 👤 **User** — 2026-08-16 22:38:52

SORTING
================================================================================
78_v33       20
79_v33        8
80_v33        8
81_v33       16
82_v33        9
83_v33       17
84_v33       11
85_v33       18
86_v33       15
87_v33       17
88_v33       15
89_v33       20
90_v33        3
91_v33       12
92_v33       16
93_v33       12
94_v33       23
95_v33       17

================================================================================
DONE
================================================================================

Images: 257
Hybrid changes: 9
Recognition: 48.33 sec
Total:       53.83 sec

Output:
data/output/test_hybrid_v12
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:38:53

Отлично. **Получили контрольный результат.** ✅

### Hybrid v12 production run

```text
Images:          257
Hybrid changes:    9
Recognition:    48.33 sec
Total:          53.83 sec
```

Распределение по адресам:

```text
78_v33    20
79_v33     8
80_v33     8
81_v33    16
82_v33     9
83_v33    17
84_v33    11
85_v33    18
86_v33    15
87_v33    17
88_v33    15
89_v33    20
90_v33     3
91_v33    12
92_v33    16
93_v33    12
94_v33    23
95_v33    17
```

**257 / 257 обработаны**, ошибок нет.

И самое важное:

> **Hybrid v12 сделал ровно 9 изменений.**

Это полностью соответствует нашему контрольному прогону на 256 изображениях: **9 подтверждённых изменений**.

### Значит, сейчас цепочка рабочая

```text
DINOv2 v33 fingerprints
          ↓
      Recognizer
          ↓
      TOP-5 candidates
          ↓
       Adapter
          ↓
      Hybrid v12
          ↓
       9 rerank
          ↓
    test_hybrid_v12
```

Производительность:

**48.33 сек / 257 ≈ 5.32 изображения/сек**, то есть примерно **188 мс на фото** на этом прогоне.

Выход сохранён здесь:

```text
data/output/test_hybrid_v12
```

Я бы сейчас **ничего больше в алгоритме не менял**. Это уже очень хороший момент, чтобы зафиксировать рабочую production-связку как:

**DINOv2 v33 + Recognizer + Adapter + Hybrid v12.**

---

### 👤 **User** — 2026-08-16 22:39:31

ок

---

### 🤖 **Assistant** — 2026-08-16 22:39:32

Зафиксировали. 👍

**Эталонная связка:**

```text
DINOv2 v33
   ↓
Recognizer
   ↓
TOP-5
   ↓
Adapter
   ↓
Hybrid v12
```

Контроль:

```text
257 изображений
9 Hybrid changes
48.33 сек recognition
53.83 сек total
```

**Логику и веса Hybrid v12 больше не трогаем.**

---

### 👤 **User** — 2026-08-16 22:39:40

дальше

---

### 🤖 **Assistant** — 2026-08-16 22:39:42

Дальше я бы **не улучшал распознавание**, а перевёл текущую связку в следующий контрольный этап: **проверяем 9 Hybrid-переклассификаций визуально и затем готовим production-сортировщик**.

### Шаг 1 — посмотреть ровно 9 изменений

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
import json
from pathlib import Path

p = Path("data/output/test_hybrid_v12/hybrid_v12.json")
data = json.loads(p.read_text(encoding="utf-8"))

changed = [x for x in data if x.get("hybrid_changed")]

print("=" * 80)
print("HYBRID V12 CHANGES")
print("=" * 80)
print("COUNT:", len(changed))

for x in changed:
    print()
    print(x.get("file"))
    print(
        x.get("original_best_id"),
        "->",
        x.get("best_id")
    )
    print(
        "old_score:",
        x.get("hybrid_old_score"),
        "new_score:",
        x.get("hybrid_score")
    )
    print("margin:", x.get("hybrid_margin"))
    print("neighbors:", x.get("hybrid_neighbors"))
PY
```

### Шаг 2 — визуальная проверка

Нам сейчас нужны именно эти 9:

```text
DINO TOP1 → Hybrid
```

Если они снова подтверждаются визуально, то у нас уже есть очень сильная фиксация:

```text
DINO v33                  базовое распознавание
Hybrid v12                исправляет пограничные случаи
9/9 изменений             подтверждены визуально
```

### Шаг 3 — после проверки

Тогда делаем следующий уровень:

```text
data/input/день
        ↓
Recognizer v33
        ↓
Hybrid v12
        ↓
78_v33/
79_v33/
...
95_v33/
        ↓
report.csv
statistics.json
```

То есть текущий `run_hybrid_v12.py` превращаем фактически в **боевой распознаватель/сортировщик дневной папки**.

**Сейчас выполняем только Шаг 1.** Пришли список 9 изменений — дальше решим, нужно ли визуально открывать все 9 или уже можно переходить к production-сценарию.

---

### 👤 **User** — 2026-08-16 22:39:56

все ок

---

### 🤖 **Assistant** — 2026-08-16 22:39:56

Отлично. Тогда **распознавание считаем замороженным**.

### Зафиксированная production-связка

```text
DINOv2 v33 fingerprints
        ↓
Recognizer
        ↓
TOP-5 candidates
        ↓
Adapter
        ↓
Hybrid v12
        ↓
Final address
        ↓
Sorting + report
```

Контрольный прогон:

```text
257 изображений
9 Hybrid changes
9/9 визуально подтверждены
48.33 сек recognition
53.83 сек total
```

Теперь логично перейти к **production-пайплайну рекламного отдела**: папка с фотографиями за день → автоматическое распознавание → сортировка по адресам → отчёт → список сомнительных кадров.

Следующий этап уже не должен менять распознавание.

---

### 👤 **User** — 2026-08-16 22:40:02

далее

---

### 🤖 **Assistant** — 2026-08-16 22:40:03

Да. Следующий этап — **сделать боевой дневной запуск**, не меняя ни DINO v33, ни Hybrid v12.

Сейчас у нас тестовый runner уже доказан. Нужно проверить его на реальной структуре входа и сделать удобную команду запуска.

### 1. Сначала посмотрим текущий runner

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba scripts/run_hybrid_v12.py | sed -n '390,720p'
```

Пришли вывод.

Я проверю только production-часть:

- принимает ли любую входную папку;
- правильно ли создаёт выходную;
- копирует ли **оригиналы**, а не меняет их;
- сортирует ли по `78_v33 ... 95_v33`;
- сохраняет ли `recognition.json`;
- сохраняет ли `hybrid_v12.json`;
- сохраняет ли CSV/статистику;
- что происходит с `NO_MATCH`;
- можно ли запускать следующий день без ручной чистки старого результата.

**Алгоритм распознавания при этом вообще не трогаем.**

---

