## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 👤 **User** — 2026-08-15 13:06:12

\) | sort | grep -Ei 'sort|classif|recogn|test|benchmark'
=== SORT / RECOGNIZE SCRIPTS ===
./app_backup_before_patch/core/recognizer.py
./app/core/recognizer.py
./backup_patch_tokens_20260808_131532/recognizer.py
./backup_v31_fix_20260808_230926/recognizer.py
./classify_final_test.py
./classify_test.py
./classify_test_results.py
./classify_test.sh
./classify_test_top1.sh
./scripts/benchmark_test_v1.py
./scripts/sort_baseline.py
./scripts/sort_test_and_report.py
./scripts/sort_test_and_report_v2.py
./sort_recognition_output.py
./tools/create_v34_test.py
./tools/create_v35_test.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=== OUTPUT DIRECTORIES ==="
find output -maxdepth 2 -type d | sort

=== OUTPUT DIRECTORIES ===
output
output/78
output/79
output/80
output/81
output/82
output/83
output/84
output/85
output/86
output/87
output/88
output/89
output/90
output/91
output/92
output/93
output/94
output/95
output/benchmark_best_delta
output/benchmark_components
output/benchmark_components/correct_analysis
output/benchmark_components/full_analysis
output/benchmark_components/full_analysis_262
output/benchmark_components/margin_best
output/NONE
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=== CURRENT RECOGNITION COMMANDS IN PROJECT ==="
grep -RniE 'recognize|copy|shutil.copy|shutil.copy2|mkdir|makedirs' \
    --include="*.py" \
    --include="*.sh" \
    . 2>/dev/null | head -100

=== CURRENT RECOGNITION COMMANDS IN PROJECT ===
./.venv/lib64/python3.12/site-packages/opt_einsum/blas.py:114:    # Einsum is faster than vectordot if we have to copy
./.venv/lib64/python3.12/site-packages/opt_einsum/blas.py:155:    first copy the data, perform the DGEMM, and then copy the data to the required
./.venv/lib64/python3.12/site-packages/opt_einsum/blas.py:192:    # Tensordot guarantees a copy for ndim > 2, should avoid skip if possible
./.venv/lib64/python3.12/site-packages/opt_einsum/_version.py:4:# unpacked source archive. Distribution tarballs contain a pre-generated copy
./.venv/lib64/python3.12/site-packages/opt_einsum/tests/test_blas.py:37:    # Tensor Dot (requires copy), lets not deal with this for now
./.venv/lib64/python3.12/site-packages/opt_einsum/tests/test_blas.py:47:    # Tensor Dot (requires copy), lets not deal with this for now with transpose
./.venv/lib64/python3.12/site-packages/opt_einsum/sharing.py:4:Copyright (c) 2018 Uber Technologies
./.venv/lib64/python3.12/site-packages/paddle/_pir_ops.py:1:# Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved
./.venv/lib64/python3.12/site-packages/paddle/_pir_ops.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/_legacy_C_ops.py:1:# Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved
./.venv/lib64/python3.12/site-packages/paddle/_legacy_C_ops.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/pir_utils.py:1:# Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved
./.venv/lib64/python3.12/site-packages/paddle/pir_utils.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/functional.py:1:# Copyright (c) 2025 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/functional.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/linalg.py:1:# Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved
./.venv/lib64/python3.12/site-packages/paddle/linalg.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/geometric/sampling/neighbors.py:1:#   Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/geometric/sampling/neighbors.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/geometric/sampling/__init__.py:1:# Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/geometric/sampling/__init__.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/geometric/reindex.py:1:#   Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/geometric/reindex.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/geometric/__init__.py:1:# Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/geometric/__init__.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/geometric/message_passing/utils.py:1:#   Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/geometric/message_passing/utils.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/geometric/message_passing/send_recv.py:1:#   Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/geometric/message_passing/send_recv.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/geometric/message_passing/__init__.py:1:# Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/geometric/message_passing/__init__.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/geometric/math.py:1:# Copyright (c) 2022 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/geometric/math.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/utils/install_check.py:1:# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/utils/install_check.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/utils/environments.py:1:# Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/utils/environments.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/utils/op_version.py:1:# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/utils/op_version.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/utils/layers_utils.py:1:#   Copyright (c) 2018 PaddlePaddle Authors. All Rights Reserved.
./.venv/lib64/python3.12/site-packages/paddle/utils/layers_utils.py:5:# You may obtain a copy of the License at
./.venv/lib64/python3.12/site-packages/paddle/utils/layers_utils.py:17:import copy
./.venv/lib64/python3.12/site-packages/paddle/utils/layers_utils.py:275:def copy_mutable_vars(structure):
./.venv/lib64/python3.12/site-packages/paddle/utils/layers_utils.py:279:    flat_structure = copy.copy(flatten(structure))
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:1:# Copyright (c) 2016, Serge Guelton
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:7:# 	Redistributions of source code must retain the above copyright notice, this
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:10:# 	Redistributions in binary form must reproduce the above copyright notice,
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:18:# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:21:# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:54:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:66:            gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:81:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:88:            gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:97:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:104:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:115:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:127:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:139:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:149:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:159:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:167:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:175:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:181:                    gast.copy_location(star, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:188:                    gast.copy_location(kw, node.kwargs)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:200:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:209:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:221:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:230:        return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:244:        return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:253:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:266:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:279:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:291:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:303:            return gast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:331:                    ast.copy_location(value, node.slice)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:335:            ast.copy_location(new_slice, node.slice)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:342:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:350:        return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:371:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:385:        return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:392:        return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:399:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:427:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:440:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:452:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:462:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:471:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:481:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:488:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:495:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:503:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:515:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:528:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/ast3.py:539:            return ast.copy_location(new_node, node)
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/gast.py:1:# Copyright (c) 2016, Serge Guelton
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/gast.py:7:# 	Redistributions of source code must retain the above copyright notice, this
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/gast.py:10:# 	Redistributions in binary form must reproduce the above copyright notice,
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/gast.py:18:# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/gast.py:21:# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
./.venv/lib64/python3.12/site-packages/paddle/utils/gast/gast.py:1262:def copy_location(new_node, old_node):
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:06:14

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed scene recognition workflow, script, sorting command, and margin logic**
>
> 
>
> Worked for 9s

Да. Здесь **не надо трогать `app/core/recognizer.py` и основной алгоритм**. Нам нужен отдельный тестовый прогон:

- все **262 фото**;
- только `78_v33 ... 95_v33`;
- обычный результат - `A_CURRENT`;
- для **margin < 0.005** - всего **7 фото** - выбирать `BEST`;
- затем разложить копии по папкам `78`, `79`, … `95`;
- исходные фото не менять.

У тебя сейчас уже есть правильный анализ, поэтому сначала нужно точно найти существующий скрипт сортировки и формат его входного JSON. Выполни **одну команду**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== classify_final_test.py ==="
sed -n '1,260p' classify_final_test.py

echo
echo "=== sort_test_and_report_v2.py ==="
sed -n '1,300p' scripts/sort_test_and_report_v2.py

echo
echo "=== sort_baseline.py ==="
sed -n '1,260p' scripts/sort_baseline.py
```

**Пришли вывод целиком.**

После этого я дам готовую команду/скрипт именно под текущий `v33`, чтобы мы не повторили ситуацию с `test_margin_best.py`, где структура `first/second` оказалась другой.

И важный момент: **7 файлов с margin < 0.005 будем не просто помечать, а реально пересортируем по `BEST`**, а остальные 255 - по обычному `A_CURRENT`. Затем посмотрим распределение и сделаем папку для визуального контроля.

---

### 👤 **User** — 2026-08-15 13:07:04

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== classify_final_test.py ==="
sed -n '1,260p' classify_final_test.py

echo
echo "=== sort_test_and_report_v2.py ==="
sed -n '1,300p' scripts/sort_test_and_report_v2.py

echo
echo "=== sort_baseline.py ==="
sed -n '1,260p' scripts/sort_baseline.py
=== classify_final_test.py ===
from pathlib import Path
import json
import shutil

RESULTS = Path("final_test_78_95.json")
SOURCE = Path("data/input/test")
OUTPUT = Path("data/output/test_classified")

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)

# --------------------------------------------------
# LOAD JSON
# --------------------------------------------------

lines = RESULTS.read_text(
    encoding="utf-8"
).splitlines()

start = None

for i, line in enumerate(lines):
    if line.strip() == "[":
        start = i
        break

if start is None:
    raise RuntimeError(
        "JSON array not found"
    )

data = json.loads(
    "\n".join(lines[start:])
)

print(
    f"Results loaded: {len(data)}"
)

# --------------------------------------------------
# COPY BY TOP-1
# --------------------------------------------------

counts = {}

for r in data:

    file_path = Path(
        r["file"]
    )

    filename = file_path.name

    # TOP-1 ALWAYS WINS
    best_id = r.get(
        "best_id"
    )

    # Если best_id отсутствует,
    # берём первого кандидата.
    if not best_id:

        candidates = r.get(
            "candidates",
            []
        )

        if candidates:
            best_id = candidates[0].get(
                "id"
            )

    # Только если вообще нет кандидата
    if not best_id:
        folder_name = "NO_CANDIDATE"
    else:
        folder_name = str(
            best_id
        )

    destination_dir = (
        OUTPUT / folder_name
    )

    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_file = (
        SOURCE / filename
    )

    if not source_file.exists():

        if file_path.exists():
            source_file = file_path

        else:
            print(
                f"[WARNING] "
                f"Source not found: "
                f"{filename}"
            )
            continue

    destination_file = (
        destination_dir
        / filename
    )

    # Защита от одинаковых имён
    if destination_file.exists():

        stem = destination_file.stem
        suffix = destination_file.suffix

        n = 2

        while True:

            candidate = (
                destination_dir
                / f"{stem}__{n}{suffix}"
            )

            if not candidate.exists():
                destination_file = candidate
                break

            n += 1

    shutil.copy2(
        source_file,
        destination_file,
    )

    counts[folder_name] = (
        counts.get(
            folder_name,
            0,
        ) + 1
    )

# --------------------------------------------------
# REPORT
# --------------------------------------------------

print()
print("=" * 70)
print("FINAL TOP-1 CLASSIFICATION")
print("=" * 70)

total = 0

for name in sorted(
    counts,
    key=lambda x: (
        int(
            "".join(
                c
                for c in x
                if c.isdigit()
            )
        )
        if any(
            c.isdigit()
            for c in x
        )
        else 9999
    ),
):

    count = counts[name]
    total += count

    print(
        f"{name:20} {count:4}"
    )

print()
print(
    f"TOTAL COPIED: {total}"
)

print(
    f"OUTPUT: {OUTPUT}"
)

=== sort_test_and_report_v2.py ===
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

=== sort_baseline.py ===
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:07:05

Да. Здесь лучше **не трогать `recognizer.py` и основной алгоритм**. Сделаем отдельный тестовый сортировщик поверх уже рассчитанного `components.csv`/результатов A_CURRENT:

- обычный случай → **первый кандидат**;
- только если `margin < 0.005` → рассматриваем `BEST`;
- если `BEST` отличается от первого кандидата → отдаём папку `BEST`;
- всего таких случаев должно быть **7 из 262**;
- остальные 255 остаются на первом кандидате;
- результат складываем в отдельную папку, чтобы не затронуть текущую сортировку;
- после этого получим CSV с тем, **что именно было изменено**, и папку для визуального контроля.

Судя по твоему `analysis.txt`, эти 7 случаев должны быть:

```text
Ленина 125-127 А (14).JPG
Ленина 125-127 А (10).JPG
Ленина 125-127 А (17).JPG
Вавилова ул. - Радиаторный пер.  A (70).JPG
Ленина 125-127 А (9).JPG
Ленина 125-127 А (11).JPG
Ленина 125-127 А (16).JPG
```

Причём среди них только три — положительные BEST-конфликты, а остальные четыре имеют отрицательный `BEST_DIFF`, то есть **BEST оставляет первый кандидат**, если применять правило «отдаём предпочтение best» буквально только там, где best лучше. Поэтому фактически измениться должны **3 фотографии**.

Но сначала лучше не писать код вслепую: нам нужно посмотреть точную структуру `components.csv` и `margin_best.csv`, потому что именно там уже есть все необходимые значения.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== components.csv HEADER ==="
head -1 output/benchmark_components/components.csv

echo
echo "=== margin_best.csv HEADER ==="
head -1 output/benchmark_components/full_analysis/margin_best.csv

echo
echo "=== 7 CASES ==="
grep -E 'Ленина 125-127|Вавилова ул. - Радиаторный' \
    output/benchmark_components/full_analysis/margin_best.csv
```

И ещё сразу покажи первые строки CSV:

```bash
echo
echo "=== SAMPLE ==="
head -5 output/benchmark_components/full_analysis/margin_best.csv
```

После этого я дам **готовый отдельный скрипт**, который создаст примерно такую структуру:

```text
output/
└── visual_check_margin005/
    ├── 78/
    ├── 79/
    ├── ...
    ├── 95/
    └── _CHANGED/
```

При этом в `_CHANGED` будут лежать копии именно тех фотографий, которым правило `margin < 0.005 + BEST` поменяло назначение. Это будет удобно для визуальной проверки.

---

### 👤 **User** — 2026-08-15 13:07:52

=== 7 CASES ===
Вавилова ул. - Радиаторный пер.  A (34).JPG,94_v33,92_v33,0.872397,0.857297,0.015100,0.870948,0.835760,-0.035188
Вавилова ул. - Радиаторный пер.  A (38).JPG,94_v33,92_v33,0.873826,0.852985,0.020841,0.845869,0.832864,-0.013005
Вавилова ул. - Радиаторный пер.  A (5).JPG,94_v33,91_v33,0.902684,0.857061,0.045623,0.885537,0.828686,-0.056851
Вавилова ул. - Радиаторный пер.  A (63).JPG,86_v33,89_v33,0.800680,0.794199,0.006481,0.743823,0.755776,0.011953
Вавилова ул. - Радиаторный пер.  A (70).JPG,88_v33,89_v33,0.797554,0.794325,0.003229,0.731110,0.735259,0.004149
Ленина 125-127 А (1).JPG,84_v33,87_v33,0.881931,0.857721,0.024210,0.944307,0.860633,-0.083674
Ленина 125-127 А (10).JPG,87_v33,84_v33,0.896861,0.894985,0.001876,0.893826,0.947581,0.053755
Ленина 125-127 А (11).JPG,84_v33,87_v33,0.899442,0.893362,0.006080,0.948665,0.887667,-0.060998
Ленина 125-127 А (12).JPG,84_v33,87_v33,0.888220,0.875735,0.012485,0.946145,0.868831,-0.077314
Ленина 125-127 А (13).JPG,84_v33,87_v33,0.900230,0.886959,0.013271,0.948489,0.885128,-0.063361
Ленина 125-127 А (14).JPG,87_v33,84_v33,0.888650,0.887613,0.001037,0.883096,0.940534,0.057438
Ленина 125-127 А (15).JPG,84_v33,87_v33,0.884702,0.861524,0.023178,0.942905,0.859820,-0.083085
Ленина 125-127 А (16).JPG,84_v33,87_v33,0.891408,0.882699,0.008709,0.941929,0.873775,-0.068154
Ленина 125-127 А (17).JPG,84_v33,87_v33,0.895833,0.893246,0.002587,0.942105,0.883259,-0.058846
Ленина 125-127 А (8).JPG,87_v33,84_v33,0.887508,0.881740,0.005768,0.882709,0.950911,0.068202
Ленина 125-127 А (9).JPG,84_v33,87_v33,0.896161,0.891359,0.004802,0.943069,0.885435,-0.057634
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=== SAMPLE ==="
head -5 output/benchmark_components/full_analysis/margin_best.csv

=== SAMPLE ===
image,current_first,current_second,final_first,final_second,final_margin,best_first,best_second,best_diff
00 (1).JPG,78_v33,92_v33,0.946832,0.892311,0.054521,0.956302,0.886462,-0.069840
00 (10).JPG,78_v33,91_v33,0.937443,0.879288,0.058155,0.927204,0.853744,-0.073460
00 (11).JPG,78_v33,95_v33,0.932518,0.890300,0.042218,0.938092,0.881098,-0.056994
00 (12).JPG,78_v33,83_v33,0.929418,0.889445,0.039973,0.928726,0.869961,-0.058765
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:07:53

Да, теперь всё однозначно.

Важный момент: **`margin < 0.005` — это действительно 7 фотографий**, но из этих 7 только **3 имеют `best_diff > 0`**. Значит, если правило такое:

> при margin < 0.005 отдаём предпочтение `BEST`, **но только если BEST реально лучше**

то меняем только **3 назначения**:

| Фото | Было | BEST | BEST_DIFF |
|---|---|---|---:|
| Ленина 125-127 А (10).JPG | 87 | **84** | +0.053755 |
| Ленина 125-127 А (14).JPG | 87 | **84** | +0.057438 |
| Вавилова ул. - Радиаторный пер. A (70).JPG | 88 | **89** | +0.004149 |

Остальные 4 остаются как есть:

- (8) — `BEST_DIFF +0.068202`, **но margin = 0.005768**, поэтому не попадает под `< 0.005`.
- (9), (11), (17) — margin < 0.005, но `BEST_DIFF < 0`, поэтому оставляем текущий результат.

То есть получаем очень аккуратное правило:

```text
IF final_margin < 0.005
AND best_diff > 0
THEN assigned = current_second
ELSE assigned = current_first
```

Причём `current_second` здесь соответствует кандидату, который BEST выбрал как более сильный.

### Делаем отдельный визуальный прогон

Я предлагаю **не запускать повторно распознавание**. Все необходимые данные уже есть в `margin_best.csv`. Это важно: мы сейчас тестируем **только логику принятия решения**, а не сам DINOv2.

Создадим отдельный скрипт:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_margin005_best.py <<'PY'
#!/usr/bin/env python3

import csv
import shutil
from pathlib import Path
from collections import Counter

PROJECT = Path(__file__).resolve().parent.parent

INPUT_CSV = (
    PROJECT
    / "output/benchmark_components/full_analysis/margin_best.csv"
)

SOURCE_DIR = PROJECT / "data/input/test"

OUTPUT_DIR = PROJECT / "output/visual_check_margin005"

CHANGED_DIR = OUTPUT_DIR / "_CHANGED"

MARGIN_THRESHOLD = 0.005

def safe_copy(src, dst_dir):
    dst_dir.mkdir(parents=True, exist_ok=True)

    dst = dst_dir / src.name

    if not dst.exists():
        shutil.copy2(src, dst)
        return dst

    stem = src.stem
    suffix = src.suffix

    n = 2

    while True:
        candidate = dst_dir / f"{stem}__{n}{suffix}"

        if not candidate.exists():
            shutil.copy2(src, candidate)
            return candidate

        n += 1

def main():

    print("=" * 80)
    print("MARGIN < 0.005 + BEST VISUAL TEST")
    print("=" * 80)

    print("CSV   :", INPUT_CSV)
    print("SOURCE:", SOURCE_DIR)
    print("OUTPUT:", OUTPUT_DIR)
    print()

    if not INPUT_CSV.exists():
        raise FileNotFoundError(INPUT_CSV)

    if not SOURCE_DIR.exists():
        raise FileNotFoundError(SOURCE_DIR)

    # Clean only our test output.
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True)

    rows = []

    with INPUT_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

    print(f"CSV rows: {len(rows)}")
    print()

    counters = Counter()
    changed = []
    low_margin = []

    for row in rows:

        image = row["image"]

        current_first = row["current_first"]
        current_second = row["current_second"]

        final_margin = float(row["final_margin"])
        best_diff = float(row["best_diff"])

        # --------------------------------------------------
        # DECISION
        # --------------------------------------------------

        assigned = current_first
        reason = "FIRST"

        if final_margin < MARGIN_THRESHOLD:

            low_margin.append(row)

            if best_diff > 0:

                assigned = current_second
                reason = "BEST"

            else:

                reason = "FIRST_BEST_LOSES"

        # --------------------------------------------------
        # SOURCE
        # --------------------------------------------------

        src = SOURCE_DIR / image

        if not src.exists():

            print(
                f"[WARNING] source not found: {src}"
            )

            continue

        # --------------------------------------------------
        # DESTINATION
        # --------------------------------------------------

        folder = assigned.replace("_v33", "")

        dst_dir = OUTPUT_DIR / folder

        safe_copy(src, dst_dir)

        counters[folder] += 1

        # --------------------------------------------------
        # CHANGED
        # --------------------------------------------------

        if assigned != current_first:

            changed.append({
                "image": image,
                "old": current_first,
                "new": assigned,
                "margin": final_margin,
                "best_diff": best_diff,
            })

            # Put an additional copy into _CHANGED.
            safe_copy(src, CHANGED_DIR)

    # ------------------------------------------------------
    # REPORT
    # ------------------------------------------------------

    report = OUTPUT_DIR / "decision_report.csv"

    with report.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        fields = [
            "image",
            "old",
            "new",
            "margin",
            "best_diff",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()

        writer.writerows(changed)

    print("=" * 80)
    print("RESULT")
    print("=" * 80)

    print(
        f"Total images:        {len(rows)}"
    )

    print(
        f"Margin < 0.005:      {len(low_margin)}"
    )

    print(
        f"Changed by BEST:     {len(changed)}"
    )

    print()

    print("CHANGED:")
    print("-" * 80)

    for x in changed:

        print(
            f'{x["image"]}'
        )

        print(
            f'    {x["old"]} -> {x["new"]}'
        )

        print(
            f'    margin={x["margin"]:.6f}'
            f'  best_diff={x["best_diff"]:+.6f}'
        )

    print()
    print("DISTRIBUTION")
    print("-" * 80)

    for folder in sorted(
        counters,
        key=lambda x: int(x)
    ):

        print(
            f"{folder:10s} {counters[folder]:4d}"
        )

    print("-" * 80)
    print(
        f"{'TOTAL':10s} {sum(counters.values()):4d}"
    )

    print()
    print("OUTPUT:")
    print(
        f"  sorted : {OUTPUT_DIR}"
    )

    print(
        f"  changed: {CHANGED_DIR}"
    )

    print(
        f"  report : {report}"
    )

if __name__ == "__main__":
    main()
PY

chmod +x scripts/sort_margin005_best.py

uv run python scripts/sort_margin005_best.py
```

### Что получим

Основная папка:

```text
output/visual_check_margin005/
```

в ней:

```text
78/
79/
80/
...
95/
```

Это **полная сортировка всех 262 фотографий**.

А отдельно:

```text
output/visual_check_margin005/_CHANGED/
```

будут лежать только фотографии, где решение действительно поменялось:

```text
Ленина 125-127 А (10).JPG
Ленина 125-127 А (14).JPG
Вавилова ул. - Радиаторный пер. A (70).JPG
```

И:

```text
output/visual_check_margin005/decision_report.csv
```

покажет:

```text
image,old,new,margin,best_diff
```

Это как раз тот прогон, который нам сейчас нужен: **не меняем v33, не меняем распознавание, не меняем fingerprint — проверяем только новую логику принятия решения на 262 фотографиях.**

Запусти и пришли вывод `RESULT` + `DISTRIBUTION`. Тогда уже посмотрим, **стоит ли визуально оставлять эти 3 переключения на BEST**.

---

### 👤 **User** — 2026-08-15 13:09:30

RESULT
================================================================================
Total images:        262
Margin < 0.005:      7
Changed by BEST:     3

CHANGED:
--------------------------------------------------------------------------------
008.JPG
    83_v33 -> 92_v33
    margin=0.001418  best_diff=+0.003729
Ленина 125-127 А (10).JPG
    87_v33 -> 84_v33
    margin=0.001876  best_diff=+0.053755
Ленина 125-127 А (14).JPG
    87_v33 -> 84_v33
    margin=0.001037  best_diff=+0.057438

DISTRIBUTION
--------------------------------------------------------------------------------
78           20
79            8
80            8
81           16
82            9
83           17
84           10
85           17
86           14
87           12
88           14
89           19
90            3
91           10
92           18
93           11
94           21
95           16
--------------------------------------------------------------------------------
TOTAL       243

OUTPUT:
  sorted : /home/alexice/projects/scene_fingerprint_mvp_v02/output/visual_check_margin005
  changed: /home/alexice/projects/scene_fingerprint_mvp_v02/output/visual_check_margin005/_CHANGED
  report : /home/alexice/projects/scene_fingerprint_mvp_v02/output/visual_check_margin005/decision_report.csv
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:09:32

Вот здесь обнаружилась **важная проблема не в алгоритме**, а в исходных файлах.

### Что получилось

Логика сработала правильно:

- **262** изображения в benchmark.
- **7** имеют `margin < 0.005`.
- **3** реально переключены на BEST:
  - `008.JPG`: `83 → 92`
  - `Ленина 125-127 А (10).JPG`: `87 → 84`
  - `Ленина 125-127 А (14).JPG`: `87 → 84`

Но:

```text
TOTAL 243
```

вместо 262.

То есть **19 фотографий не были скопированы**, потому что их нет непосредственно в `data/input/test` по именам из CSV.

И ещё интересный момент: `Вавилова ... (70).JPG`, которую мы ожидали увидеть среди трёх BEST-переключений, в `CHANGED` нет. Скорее всего, она как раз попала в эти отсутствующие 19.

### Сейчас ничего не меняем

Сначала выясним, какие именно 19 файлов отсутствуют:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python - <<'PY'
import csv
from pathlib import Path

csv_path = Path(
    "output/benchmark_components/full_analysis/margin_best.csv"
)

source = Path("data/input/test")

missing = []

with csv_path.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:
    for row in csv.DictReader(f):
        name = row["image"]
        if not (source / name).exists():
            missing.append(name)

print("=" * 80)
print("MISSING SOURCE FILES")
print("=" * 80)

for name in missing:
    print(name)

print("-" * 80)
print(f"MISSING: {len(missing)}")
PY
```

И отдельно полезно проверить, **куда реально смотрят пути `file` в исходном recognition JSON**, потому что вполне возможно, что эти 19 файлов существуют, но находятся не в `data/input/test`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== TEST FILES ==="
find data/input/test -maxdepth 1 -type f | wc -l

echo
echo "=== RECOGNITION FILES ==="
find data/output/test_sorted_v2 -maxdepth 1 -type f -printf '%f\n' | sort | head -20

echo
echo "=== EXAMPLE CSV IMAGE ==="
grep '008.JPG' \
    output/benchmark_components/full_analysis/margin_best.csv

echo
echo "=== SEARCH 008.JPG IN PROJECT ==="
find . -type f -name '008.JPG' \
    -not -path './.venv/*' \
    -print
```

**Пока визуальную оценку делать рано.** Нам нужно получить полные **262/262**, иначе распределение `243` и визуальная папка неполные.

После этого исправим источник, повторим этот же тест **без изменения логики**, и тогда получим полноценную папку для визуального контроля.

---

### 👤 **User** — 2026-08-15 13:13:44

меня еще интересуют 008.jpg (83), Вавилова ул. - Радиаторный пер., A (63).JPG (86), 3 лЕНИНА 125 D (87), Вавилова ул. - Радиаторный пер., A (70).JPG В (88),Шеболдаева 95 А (8).JPG в 91, Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (20)  в  95. и ситуация в сортитрованныых 92,89 и 90

---

### 🤖 **Assistant** — 2026-08-15 13:13:46

Да, именно эти случаи сейчас **намного интереснее**, чем просто смотреть все 262. Я бы сделал отдельную визуальную выборку по двум группам:

### 1. Пограничные / спорные фотографии

Проверяем обязательно:

```text
008.JPG
    83 → 92
    margin 0.001418
    BEST_DIFF +0.003729

Вавилова ул. - Радиаторный пер. A (63).JPG
    86 / 89
    margin 0.006481
    BEST_DIFF +0.011953

Ленина 125-127 А (?? / D) (3)
    87

Вавилова ул. - Радиаторный пер. A (70).JPG
    88 / 89
    margin 0.003229
    BEST_DIFF +0.004149

Шеболдаева 95 А (8).JPG
    91 / 94
    margin 0.014957

Стачки пр-кт - Зорге ул. - пл. Защитников Отечества A (20).jpg
    95 / 92
    margin 0.013838
    BEST_DIFF +0.022570
```

Причём последние два **специально интересны**, потому что они уже не проходят `margin < 0.005`, но находятся достаточно близко к границе.

### 2. Сами папки 92 / 89 / 90

Тут я бы посмотрел не отдельные фотографии, а **всю выборку этих трёх адресов**:

```text
92
89
90
```

Потому что по анализу видно, что между ними есть систематическое смешивание:

```text
89 ↔ 92
89 ↔ 90
90 ↔ 89
92 ↔ 89
92 ↔ 83
```

И это уже может показать, является ли проблема конкретными кадрами или сами сцены визуально очень близки.

---

## Но сначала надо восстановить 19 пропущенных файлов

Сейчас наша папка `visual_check_margin005` содержит только **243/262**, поэтому делать вывод по папкам 92/89/90 пока неправильно.

Давай сначала найдём эти 19 файлов. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python - <<'PY'
import csv
from pathlib import Path

csv_path = Path(
    "output/benchmark_components/full_analysis/margin_best.csv"
)

source = Path("data/input/test")

missing = []

with csv_path.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:
    for row in csv.DictReader(f):
        name = row["image"]

        if not (source / name).exists():
            missing.append(row)

print("=" * 100)
print("MISSING 19 FILES")
print("=" * 100)

for r in missing:
    print(
        f'{r["image"]} | '
        f'{r["current_first"]} / {r["current_second"]} | '
        f'margin={float(r["final_margin"]):.6f} | '
        f'best_diff={float(r["best_diff"]):+.6f}'
    )

print("-" * 100)
print("COUNT:", len(missing))
PY
```

И сразу отдельно найдём **все интересующие тебя фотографии по всему проекту**:

```bash
echo
echo "=== INTERESTING FILES ==="

find . \
    -type f \
    -not -path './.venv/*' \
    \( \
        -iname '008.JPG' \
        -o -iname '*Вавилова*63*' \
        -o -iname '*Ленина*125*127*3*' \
        -o -iname '*Вавилова*70*' \
        -o -iname '*Шеболдаева*95*8*' \
        -o -iname '*Стачки*Зорге*20*' \
    \) \
    -print
```

### После этого

Я предлагаю сделать **не просто ещё одну сортировку**, а специальную папку:

```text
output/
└── visual_control/
    ├── 008/
    ├── 063/
    ├── lenina_125/
    ├── 070/
    ├── sheboldaeva_95/
    ├── stachki_zorge_20/
    ├── folder_89/
    ├── folder_90/
    └── folder_92/
```

В первые шесть положим **саму спорную фотографию + её top-кандидатов**, а для `89/90/92` — **весь отсортированный материал**.

Тогда мы визуально ответим сразу на три вопроса:

1. **Нужно ли реально менять 008: `83 → 92`?**
2. **Стоит ли BEST вмешиваться в `86/89` и `88/89`?**
3. **Что происходит между 89, 90 и 92 — случайные ошибки или систематически похожие адреса?**

И особенно интересен `008`: у него `BEST_DIFF` всего **+0.003729**, то есть это как раз тот случай, где нельзя автоматически считать BEST правильным только потому, что он математически выиграл.

---

### 👤 **User** — 2026-08-15 13:14:29

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

python - <<'PY'
import csv
from pathlib import Path

csv_path = Path(
    "output/benchmark_components/full_analysis/margin_best.csv"
)

source = Path("data/input/test")

missing = []

with csv_path.open(
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:
    for row in csv.DictReader(f):
        name = row["image"]

        if not (source / name).exists():
PYint("COUNT:", len(missing))"best_diff"]):+.6f}' '"]} | '
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:14:30

Да, здесь просто `python` в системе не является командой. У тебя проект работает через `uv`, поэтому лучше использовать **`uv run python`**.

И похоже, heredoc при вставке в терминал у тебя ещё и исказился. Давай одной командой, аккуратно.

### 1. Найдём отсутствующие 19 файлов

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import csv
from pathlib import Path

csv_path = Path("output/benchmark_components/full_analysis/margin_best.csv")
source = Path("data/input/test")

missing = []

with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        name = row["image"]

        if not (source / name).exists():
            missing.append(row)

print("=" * 100)
print("MISSING SOURCE FILES")
print("=" * 100)

for r in missing:
    print(
        f'{r["image"]} | '
        f'{r["current_first"]} / {r["current_second"]} | '
        f'margin={float(r["final_margin"]):.6f} | '
        f'best_diff={float(r["best_diff"]):+.6f}'
    )

print("-" * 100)
print(f"MISSING: {len(missing)}")
PY
```

### 2. И сразу найдём интересующие нас фотографии

```bash
echo
echo "=== INTERESTING FILES ==="

find . \
    -type f \
    -not -path './.venv/*' \
    \( \
        -iname '008.JPG' \
        -o -iname '*Вавилова*63*' \
        -o -iname '*Ленина*125*127*3*' \
        -o -iname '*Вавилова*70*' \
        -o -iname '*Шеболдаева*95*8*' \
        -o -iname '*Стачки*Зорге*20*' \
    \) \
    -print
```

**Пока ничего не пересортировываем.** Пришли вывод этих двух команд.

После этого я сделаю нам специальный `visual_control` именно для:

- `008` — **83 vs 92**
- Вавилова (63) — **86 vs 89**
- Ленина (3) — **87 и кандидаты**
- Вавилова (70) — **88 vs 89**
- Шеболдаева 95 (8) — **91 vs 94**
- Стачки/Зорге (20) — **95 vs 92**
- и **полных папок 89 / 90 / 92**.

Тогда уже визуально решим, где v33 ошибается системно.

---

### 👤 **User** — 2026-08-15 13:15:03

====================
MISSING SOURCE FILES
====================================================================================================
Вавилова ул. - Радиаторный пер.  A (34).JPG | 94_v33 / 92_v33 | margin=0.015100 | best_diff=-0.035188
Вавилова ул. - Радиаторный пер.  A (38).JPG | 94_v33 / 92_v33 | margin=0.020841 | best_diff=-0.013005
Вавилова ул. - Радиаторный пер.  A (5).JPG | 94_v33 / 91_v33 | margin=0.045623 | best_diff=-0.056851
Вавилова ул. - Радиаторный пер.  A (63).JPG | 86_v33 / 89_v33 | margin=0.006481 | best_diff=+0.011953
Вавилова ул. - Радиаторный пер.  A (70).JPG | 88_v33 / 89_v33 | margin=0.003229 | best_diff=+0.004149
Малиновского ул.  915  A (14).JPG | 88_v33 / 92_v33 | margin=0.111513 | best_diff=-0.137119
Нагибина пр. - Рубиновый - пл. Сов. Конституции  A (19).JPG | 91_v33 / 92_v33 | margin=0.051920 | best_diff=-0.083583
Нагибина пр. - Рубиновый - пл. Сов. Конституции  A (6).JPG | 91_v33 / 92_v33 | margin=0.046350 | best_diff=-0.049232
Нагибина пр. Рубиновый - пл. Сов. Конституции  A(30).JPG | 91_v33 / 94_v33 | margin=0.047677 | best_diff=-0.050810
Стачки пр-кт - Зорге ул. - пл. Защитников Отечества  A (10).JPG | 89_v33 / 92_v33 | margin=0.017624 | best_diff=+0.051273
Стачки пр-кт - Зорге ул. - пл. Защитников Отечества  A (18).JPG | 92_v33 / 89_v33 | margin=0.024985 | best_diff=-0.080618
Стачки пр-кт - Зорге ул. - пл. Защитников Отечества  A (20).jpg | 95_v33 / 92_v33 | margin=0.013838 | best_diff=+0.022570
Стачки пр-кт 41 - ст-н Локомотив  A (1).JPG | 93_v33 / 92_v33 | margin=0.030525 | best_diff=-0.014250
Шеболдаева ул. 8-81 - пл. Народного Ополчения (РГУПС)  B (36).JPG | 87_v33 / 79_v33 | margin=0.053129 | best_diff=-0.084990
Шеболдаева ул. 8-81 - пл. Народного Ополчения (РГУПС)  B (74).JPG | 87_v33 / 79_v33 | margin=0.033310 | best_diff=-0.040865
Шеболдаева ул. 8-81 - пл. Народного Ополчения (РГУПС)  B (81).JPG | 87_v33 / 79_v33 | margin=0.038758 | best_diff=-0.065503
Шеболдаева ул. 881 - пл. Народного Ополчения (РГУПС)  A (33).JPG | 87_v33 / 81_v33 | margin=0.039552 | best_diff=-0.092949
Шеболдаева ул. 881 - пл. Народного Ополчения (РГУПС)  B (22).JPG | 87_v33 / 92_v33 | margin=0.084914 | best_diff=-0.110933
Шеболдаева ул. 881 - пл. Народного Ополчения (РГУПС)  B (69).JPG | 87_v33 / 83_v33 | margin=0.080333 | best_diff=-0.099885
----------------------------------------------------------------------------------------------------
MISSING: 19
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=== INTERESTING FILES ==="

find . \
    -type f \
    -not -path './.venv/*' \
    $ \
        -iname '008.JPG' \
        -o -iname '*Вавилова*63*' \
        -o -iname '*Ленина*125*127*3*' \
        -o -iname '*Вавилова*70*' \
        -o -iname '*Шеболдаева*95*8*' \
        -o -iname '*Стачки*Зорге*20*' \
    $ \
    -print

=== INTERESTING FILES ===
./output/86/Вавилова ул. - Радиаторный пер., A (63).JPG
./output/84/Ленина 125-127 А (13).JPG
./output/visual_check_margin005/92/008.JPG
./output/visual_check_margin005/84/Ленина 125-127 А (13).JPG
./output/visual_check_margin005/_CHANGED/008.JPG
./output/visual_check_margin005/91/Шеболдаева 95 А (8).JPG
./output/83/008.JPG
./output/91/Шеболдаева 95 А (8).JPG
./output/95/Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (20).jpg
./output/88/Вавилова ул. - Радиаторный пер., A (70).JPG
./data/input/test/Ленина 125-127 А (13).JPG
./data/input/test/Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (20).jpg
./data/input/test/008.JPG
./data/input/test/Вавилова ул. - Радиаторный пер., A (70).JPG
./data/input/test/Шеболдаева 95 А (8).JPG
./data/input/test/Вавилова ул. - Радиаторный пер., A (63).JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:15:04

Отлично. Теперь понятно, что произошло: **19 файлов в `margin_best.csv` действительно отсутствуют в `data/input/test`**, поэтому из них нельзя напрямую сделать визуальный контроль. Но наши ключевые интересующие файлы **есть**, и уже рассортированы.

Причём есть важный момент: для `008.JPG` папка `92` появилась только благодаря нашему правилу BEST, а исходная классификация была `83`.

### Сейчас предлагаю не трогать основной результат

Сделаем отдельную папку `output/visual_control_interest`, куда скопируем **только интересующие фотографии**, но разложим их по вариантам:

- `008`: **83 / 92**
- Вавилова (63): **86 / 89**
- Вавилова (70): **88 / 89**
- Шеболдаева 95 (8): **91 / 94**
- Стачки/Зорге (20): **95 / 92**
- Ленина 125-127 — здесь надо найти именно `(3)`, а его сейчас нет в `data/input/test`, поэтому пока пропускаем.

А для **89 / 90 / 92** сделаем отдельные полные папки из текущего результата, чтобы посмотреть распределение целиком.

Сначала выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/visual_control_interest
mkdir -p output/visual_control_interest

# ============================================================
# INTERESTING CASES — копируем в отдельные папки по вариантам
# ============================================================

mkdir -p output/visual_control_interest/008/{83,92}
mkdir -p output/visual_control_interest/vavilova_63/{86,89}
mkdir -p output/visual_control_interest/vavilova_70/{88,89}
mkdir -p output/visual_control_interest/sheboldaeva_95_8/{91,94}
mkdir -p output/visual_control_interest/stachki_zorge_20/{95,92}

# 008
cp "data/input/test/008.JPG" \
   output/visual_control_interest/008/83/

cp "data/input/test/008.JPG" \
   output/visual_control_interest/008/92/

# Вавилова 63
cp "data/input/test/Вавилова ул. - Радиаторный пер., A (63).JPG" \
   output/visual_control_interest/vavilova_63/86/

cp "data/input/test/Вавилова ул. - Радиаторный пер., A (63).JPG" \
   output/visual_control_interest/vavilova_63/89/

# Вавилова 70
cp "data/input/test/Вавилова ул. - Радиаторный пер., A (70).JPG" \
   output/visual_control_interest/vavilova_70/88/

cp "data/input/test/Вавилова ул. - Радиаторный пер., A (70).JPG" \
   output/visual_control_interest/vavilova_70/89/

# Шеболдаева 95 (8)
cp "data/input/test/Шеболдаева 95 А (8).JPG" \
   output/visual_control_interest/sheboldaeva_95_8/91/

cp "data/input/test/Шеболдаева 95 А (8).JPG" \
   output/visual_control_interest/sheboldaeva_95_8/94/

# Стачки / Зорге (20)
cp "data/input/test/Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (20).jpg" \
   output/visual_control_interest/stachki_zorge_20/95/

cp "data/input/test/Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (20).jpg" \
   output/visual_control_interest/stachki_zorge_20/92/

echo
echo "=== INTERESTING CASES ==="
find output/visual_control_interest -type f | sort
```

Но есть ещё более полезная вещь.

Для **89, 90 и 92** я бы не просто смотрел отдельные спорные фотографии. Нужно посмотреть **всю группу**, потому что мы хотим понять, не происходит ли систематического смешивания этих адресов.

Сделай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/visual_control_groups
mkdir -p output/visual_control_groups

for N in 89 90 92; do
    mkdir -p "output/visual_control_groups/$N"

    if [ -d "output/$N" ]; then
        cp -a "output/$N/." "output/visual_control_groups/$N/"
    fi

    if [ -d "output/visual_check_margin005/$N" ]; then
        mkdir -p "output/visual_control_groups/${N}_margin005"
        cp -a "output/visual_check_margin005/$N/." \
              "output/visual_control_groups/${N}_margin005/"
    fi
done

echo
echo "=== GROUPS ==="
find output/visual_control_groups -maxdepth 2 -type f | sort | sed -n '1,100p'

echo
echo "=== COUNTS ==="
for N in 89 90 92; do
    echo "----- $N -----"
    find "output/visual_control_groups/$N" -type f | wc -l
done
```

### И ещё один важный момент

В твоём предыдущем результате:

```text
Margin < 0.005: 7
Changed by BEST: 3
```

это **не означает**, что только 3 из 7 сомнительные.

Из семи:

- `008` → BEST слегка меняет `83 → 92`, `best_diff +0.003729` — **очень слабый сигнал**;
- `Вавилова 63` → `86 → 89`, `best_diff +0.011953` — уже интереснее;
- `Вавилова 70` → `88 → 89`, `best_diff +0.004149` — слабый сигнал;
- `Ленина (10)` → `87 → 84`, `+0.053755` — **очень сильный сигнал BEST**;
- `Ленина (14)` → `87 → 84`, `+0.057438` — **очень сильный сигнал BEST**;
- `Ленина (8)` → `87 → 84`, `+0.068202` — **самый сильный конфликт**, но margin `0.005768`, поэтому формально он не входит в `<0.005`;
- `Ленина (17)` → `84`, BEST подтверждает `84` (`-0.058846`);
- `Ленина (9)` → `84`, BEST подтверждает `84` (`-0.057634`);
- `Ленина (11)` → `84`, BEST подтверждает `84` (`-0.060998`).

То есть **серия Ленина очень показательная**: из 11 кадров этого адреса система почти всегда понимает `84`, а три кадра выбиваются в `87`, причём BEST для них очень сильно тянет обратно в `84`.

Это как раз тот случай, ради которого мы вводили BEST.

После выполнения команд у нас будет материал для визуальной проверки **без изменения рабочего результата**.

---

### 👤 **User** — 2026-08-15 13:23:59

=== GROUPS ===
output/visual_control_groups/89_margin005/Ленина Ашхабадский А (7).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (17).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (1).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (26).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (6).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (7).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (11).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (25).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (28).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (2).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (32).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (47).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (4).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (5).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (6).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (8).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Стачки А (3).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Стачки А (5).JPG
output/visual_control_groups/89_margin005/Стачки Зорге А (25).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (17).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (1).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (26).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (6).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (7).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (11).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (25).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (28).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (2).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (32).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (47).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (4).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (5).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (6).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (8).JPG
output/visual_control_groups/89/Малиновского 25 к Стачки А (3).JPG
output/visual_control_groups/89/Малиновского 25 к Стачки А (5).JPG
output/visual_control_groups/89/Стачки Зорге А (25).JPG
output/visual_control_groups/89/Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (10).JPG
output/visual_control_groups/90_margin005/Малиновского 25 к Стачки А (1).JPG
output/visual_control_groups/90_margin005/Малиновского 25 к Стачки А (2).JPG
output/visual_control_groups/90_margin005/Малиновского 25 к Стачки А (4).JPG
output/visual_control_groups/90/Малиновского 25 к Стачки А (1).JPG
output/visual_control_groups/90/Малиновского 25 к Стачки А (2).JPG
output/visual_control_groups/90/Малиновского 25 к Стачки А (4).JPG
output/visual_control_groups/92/009.JPG
output/visual_control_groups/92_margin005/008.JPG
output/visual_control_groups/92_margin005/009.JPG
output/visual_control_groups/92_margin005/Комарова Добровольского А (1).JPG
output/visual_control_groups/92_margin005/Комарова Добровольского А (42).JPG
output/visual_control_groups/92_margin005/Комарова Добровольского А (8).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (13).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (16).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (21).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (2).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (34).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (37).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (40).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (43).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (48).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (49).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (59).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (6).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (84).JPG
output/visual_control_groups/92/Комарова Добровольского А (1).JPG
output/visual_control_groups/92/Комарова Добровольского А (42).JPG
output/visual_control_groups/92/Комарова Добровольского А (8).JPG
output/visual_control_groups/92/Стачки Зорге А (13).JPG
output/visual_control_groups/92/Стачки Зорге А (16).JPG
output/visual_control_groups/92/Стачки Зорге А (21).JPG
output/visual_control_groups/92/Стачки Зорге А (2).JPG
output/visual_control_groups/92/Стачки Зорге А (34).JPG
output/visual_control_groups/92/Стачки Зорге А (37).JPG
output/visual_control_groups/92/Стачки Зорге А (40).JPG
output/visual_control_groups/92/Стачки Зорге А (43).JPG
output/visual_control_groups/92/Стачки Зорге А (48).JPG
output/visual_control_groups/92/Стачки Зорге А (49).JPG
output/visual_control_groups/92/Стачки Зорге А (59).JPG
output/visual_control_groups/92/Стачки Зорге А (6).JPG
output/visual_control_groups/92/Стачки Зорге А (84).JPG
output/visual_control_groups/92/Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (18).JPG

=== COUNTS ===
----- 89 -----
19
----- 90 -----
3
----- 92 -----
18
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/visual_control_groups
mkdir -p output/visual_control_groups

for N in 89 90 92; do
    mkdir -p "output/visual_control_groups/$N"

    if [ -d "output/$N" ]; then
        cp -a "output/$N/." "output/visual_control_groups/$N/"
    fi

    if [ -d "output/visual_check_margin005/$N" ]; then
        mkdir -p "output/visual_control_groups/${N}_margin005"
        cp -a "output/visual_check_margin005/$N/." \
              "output/visual_control_groups/${N}_margin005/"
    fi
done

echo
echo "=== GROUPS ==="
find output/visual_control_groups -maxdepth 2 -type f | sort | sed -n '1,100p'

donefind "output/visual_control_groups/$N" -type f | wc -l

=== GROUPS ===
output/visual_control_groups/89_margin005/Ленина Ашхабадский А (7).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (17).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (1).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (26).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (6).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора (7).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (11).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (25).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (28).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (2).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (32).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (47).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (4).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (5).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (6).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Доватора А (8).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Стачки А (3).JPG
output/visual_control_groups/89_margin005/Малиновского 25 к Стачки А (5).JPG
output/visual_control_groups/89_margin005/Стачки Зорге А (25).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (17).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (1).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (26).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (6).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора (7).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (11).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (25).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (28).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (2).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (32).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (47).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (4).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (5).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (6).JPG
output/visual_control_groups/89/Малиновского 25 к Доватора А (8).JPG
output/visual_control_groups/89/Малиновского 25 к Стачки А (3).JPG
output/visual_control_groups/89/Малиновского 25 к Стачки А (5).JPG
output/visual_control_groups/89/Стачки Зорге А (25).JPG
output/visual_control_groups/89/Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (10).JPG
output/visual_control_groups/90_margin005/Малиновского 25 к Стачки А (1).JPG
output/visual_control_groups/90_margin005/Малиновского 25 к Стачки А (2).JPG
output/visual_control_groups/90_margin005/Малиновского 25 к Стачки А (4).JPG
output/visual_control_groups/90/Малиновского 25 к Стачки А (1).JPG
output/visual_control_groups/90/Малиновского 25 к Стачки А (2).JPG
output/visual_control_groups/90/Малиновского 25 к Стачки А (4).JPG
output/visual_control_groups/92/009.JPG
output/visual_control_groups/92_margin005/008.JPG
output/visual_control_groups/92_margin005/009.JPG
output/visual_control_groups/92_margin005/Комарова Добровольского А (1).JPG
output/visual_control_groups/92_margin005/Комарова Добровольского А (42).JPG
output/visual_control_groups/92_margin005/Комарова Добровольского А (8).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (13).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (16).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (21).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (2).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (34).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (37).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (40).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (43).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (48).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (49).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (59).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (6).JPG
output/visual_control_groups/92_margin005/Стачки Зорге А (84).JPG
output/visual_control_groups/92/Комарова Добровольского А (1).JPG
output/visual_control_groups/92/Комарова Добровольского А (42).JPG
output/visual_control_groups/92/Комарова Добровольского А (8).JPG
output/visual_control_groups/92/Стачки Зорге А (13).JPG
output/visual_control_groups/92/Стачки Зорге А (16).JPG
output/visual_control_groups/92/Стачки Зорге А (21).JPG
output/visual_control_groups/92/Стачки Зорге А (2).JPG
output/visual_control_groups/92/Стачки Зорге А (34).JPG
output/visual_control_groups/92/Стачки Зорге А (37).JPG
output/visual_control_groups/92/Стачки Зорге А (40).JPG
output/visual_control_groups/92/Стачки Зорге А (43).JPG
output/visual_control_groups/92/Стачки Зорге А (48).JPG
output/visual_control_groups/92/Стачки Зорге А (49).JPG
output/visual_control_groups/92/Стачки Зорге А (59).JPG
output/visual_control_groups/92/Стачки Зорге А (6).JPG
output/visual_control_groups/92/Стачки Зорге А (84).JPG
output/visual_control_groups/92/Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (18).JPG

=== COUNTS ===
----- 89 -----
19
----- 90 -----

---

### 🤖 **Assistant** — 2026-08-15 13:24:01

Да, сейчас картина уже достаточно понятная.

### Что мы фактически проверяем

Есть три уровня:

- **89** — обычная сортировка: 19 фото.
- **89_margin005** — те же 19 фото, но выделены случаи с `margin < 0.005`.
- Аналогично **90** — 3 фото.
- **92** — 18 фото + отдельно `92_margin005`.

То есть сейчас у нас есть хорошие группы для визуального сравнения **обычной сортировки против пограничных случаев**.

Особенно интересны:

| Группа | Что смотреть |
|---|---|
| **89** | вся группа из 19 фото — не смешался ли другой адрес |
| **89_margin005** | 19 фото — какие из них реально спорные |
| **90** | все 3 фото — маленькая группа, очень показательная |
| **90_margin005** | те же 3 — сравнение |
| **92** | вся группа из 18 фото |
| **92_margin005** | спорные внутри 92 |
| **92 → 008/009** | особенно важные переходы |

### Важный момент по 008

У нас уже есть:

- `output/83/008.JPG` — исходный TOP-1
- `output/visual_check_margin005/92/008.JPG` — решение BEST
- `output/visual_check_margin005/_CHANGED/008.JPG` — само изменение

То есть **008 — идеальный контрольный пример**, потому что алгоритмы разошлись:

`83 → 92`

при `margin = 0.001418`.

Причём `best_diff = +0.003729`, то есть BEST действительно перевешивает первоначальный вариант, но совсем немного. Это как раз тот случай, который нам надо оценить глазами.

### По остальным интересующим

У нас подтверждены реальные исходники:

- Вавилова / Радиаторный, **A (63)** → `86`
- Вавилова / Радиаторный, **A (70)** → `88`
- Ленина 125–127 → интересующие кадры находятся
- Шеболдаева 95 A (8) → `91`
- Стачки–Зорге–пл. Защитников, A (20) → `95`

А вот часть названий из `margin_best.csv` отсутствует непосредственно в `data/input/test`, поэтому их сейчас нельзя честно пересортировать/сравнить по исходнику. Это те 19 `MISSING SOURCE FILES`, которые мы нашли.

### Я бы сейчас ничего в алгоритме не менял

Сначала **визуальный контроль этих групп**.

Причём особенно важно посмотреть не только на отдельные спорные фотографии, а на **целостность кластеров**:

**89 → 90 → 92**

Потому что если, например, окажется, что фотографии из 89 визуально действительно являются одним объектом, а 90 и 92 имеют характерные общие элементы, это даст нам гораздо больше информации, чем просто проверка 7 пограничных кадров.

После визуального контроля можно будет принять решение:

1. оставить `TOP-1`;
2. использовать `BEST` только при `margin < 0.005`;
3. либо изменить правило для пограничных случаев.

И пока я бы **не трогал v33 и не менял сам recognizer** — текущий эксперимент как раз хорошо изолирует вопрос: помогает ли BEST на малом margin.

---

### 👤 **User** — 2026-08-15 13:32:58

89:  Стачки Зорге А (25).JPG это 92 , Малиновского 25 к Стачки А это 90, Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (10)  это 92
89 margin005: Ленина Ашхабадский А (7) это 85, Малиновского 25 к Стачки А (3) это 90, Стачки Зорге А (25) - это 92
92: 009, Комарова Добровольского А (1) - это  79, 
92margin005: 008 и 009 это 79, Комарова Добровольского А (1) это 79

---

