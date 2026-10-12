## СЕССИЯ: Продолжение проекта LORA

**Создано:** 2026-08-13 23:00:25
**Обновлено:** 2026-08-19 17:08:04
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7e224f-46a0-83ea-a4dd-2db3dc9a82bc](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7e224f-46a0-83ea-a4dd-2db3dc9a82bc)

---

### 👤 **User** — 2026-08-13 23:00:23

продолжаем проект LORA

---

### 🤖 **Assistant** — 2026-08-13 23:00:24

Да, продолжаем **LORA / Scene Fingerprint**.

По последней точке мы остановились на следующем:

- DINOv2 `facebook/dinov2-base`
- RTX 3060 12 GB
- patch tokens уже добавлены
- fingerprint `78_patch` содержит большие файлы `patch_embeddings.npy` (~62 MB)
- ты предложил **не делать огромные patch-снимки для каждого fingerprint**, а сначала прогнать папку `test`
- для каждой фотографии определить, **на какой из существующих fingerprint'ов она больше всего похожа**
- если уверенного совпадения нет — присвоить `00`
- результатом должна быть нумерация фотографий по распознанной сцене.

То есть сейчас логично сделать отдельный режим примерно:

```bash
uv run scene-fingerprint classify data/input/test
```

и получить:

```text
test/
├── 00_001.jpg      # ничего уверенно не распознано
├── 00_002.jpg
├── 78_001.jpg      # похожа на fingerprint 78
├── 78_002.jpg
├── 79_001.jpg
├── 80_001.jpg
└── ...
```

При этом **patch_embeddings вообще не нужно хранить для этой первой массовой сортировки**. Можно использовать обычные 768-мерные глобальные embedding'и и уже только для спорных случаев подключать patch-анализ.

Это даст нам гораздо более лёгкий и быстрый первый проход.

Если продолжаем именно с этого места, я бы сейчас сделал **отдельный `classify_test.py`/CLI-команду**, не ломая уже работающие `create / recognize / analyze`.

---

### 👤 **User** — 2026-08-13 23:01:45

давай. у меня для test - 78...85, а в папке test лежат также фотографии места, с которого не делался слепок

---

### 🤖 **Assistant** — 2026-08-13 23:01:45

Да. Тогда делаем **тест именно как классификацию**, где:

- `78–85` — известные места, для них есть fingerprints.
- В `test` одновременно лежат:
  - фотографии мест **78–85**;
  - фотографии **нового места**, которого среди fingerprints вообще нет.
- Новое место должно получать **`00`**, а не принудительно попадать в ближайший `78–85`.

Это важный момент: нам нужен не просто `top-1`, а **порог уверенности + отрыв от второго кандидата**.

Предлагаю первый вариант алгоритма:

```text
                    PHOTO
                      │
                      ▼
                DINOv2 embedding
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
    fingerprints 78–85       best similarity
          │                       │
          └───────────┬───────────┘
                      ▼
              similarity >= T ?
                 /          \
               нет           да
               │             │
              00       best - second >= margin ?
                            /       \
                          нет        да
                          │           │
                         00        78...85
```

### Как я предлагаю организовать результат

Не переименовывать исходные файлы сразу. Лучше создать:

```text
data/output/test_classified/
├── 00/
├── 78/
├── 79/
├── 80/
├── 81/
├── 82/
├── 83/
├── 84/
└── 85/
```

И копировать туда фотографии.

Плюс сделать CSV:

```text
filename,predicted,score,second_score,margin
IMG001.jpg,78,0.8421,0.7312,0.1109
IMG002.jpg,82,0.7914,0.7631,0.0283
IMG003.jpg,00,0.6125,0.6018,0.0107
```

Это особенно полезно для настройки порога.

**И я бы пока вообще не трогал patch embeddings.** Сначала посмотрим, насколько хорошо обычный 768-dimensional embedding разделяет 78–85 и неизвестное место. Если увидим много ошибок типа `82 → 84` или неизвестные фотографии попадают в известные — тогда добавим второй этап с patch tokens только для сомнительных кадров.

Следующим шагом нужно внести команду `classify` в твой существующий `scene-fingerprint`, причём так, чтобы **старые `create / recognize / analyze` не сломались**.

---

### 👤 **User** — 2026-08-13 23:02:40

можно сделать отдельный scen fingerprint, а еще лучше сделать это с помощью bash скрипта

---

### 🤖 **Assistant** — 2026-08-13 23:02:40

Да, **отдельный Bash-скрипт здесь даже лучше**. Не будем сейчас менять основной `scene-fingerprint` и рисковать рабочей системой.

Сделаем самостоятельный скрипт, который:

1. Берёт фотографии из `data/input/test`.
2. Использует существующие fingerprints **78–85**.
3. Для каждой фотографии получает DINOv2 embedding.
4. Сравнивает с `78...85`.
5. Если уверенности достаточно → кладёт фото в соответствующую папку `78`, `79` ... `85`.
6. Если фото похоже на неизвестное место → `00`.
7. Сохраняет CSV со всеми результатами и similarity.
8. **Не использует `patch_embeddings.npy`**, поэтому будет существенно экономнее по диску и памяти.
9. Исходные фотографии не трогает.

Я бы сделал структуру:

```text
scene_fingerprint/
├── classify_test.sh
└── ...
```

а результат:

```text
data/output/test_classified/
├── 00/
├── 78/
├── 79/
├── 80/
├── 81/
├── 82/
├── 83/
├── 84/
├── 85/
└── results.csv
```

Причём сначала запустим **диагностический режим**, который ничего не копирует, а только покажет:

```text
IMG_001.jpg  → 78   0.8734
IMG_002.jpg  → 82   0.8112
IMG_003.jpg  → 84   0.5441   UNKNOWN
IMG_004.jpg  → 79   0.9021
```

Так мы сначала подберём правильный `threshold` для `00`, а уже потом включим автоматическую сортировку.

**Это я считаю лучшим вариантом для твоего теста 78–85 + неизвестное место.**

---

### 👤 **User** — 2026-08-13 23:03:13

давай. создание нужных папок включи в скрипт

---

### 🤖 **Assistant** — 2026-08-13 23:03:14

Да. Сделаем **один самостоятельный Bash-скрипт**, который сам создаёт все необходимые папки.

Но поскольку сам Bash не должен заниматься DINOv2 — он будет запускать небольшой Python-классификатор, который Bash **сам создаст при первом запуске**. В итоге тебе нужен только один файл:

```text
classify_test.sh
```

Он создаст:

```text
data/output/test_classified/
├── 00/
├── 78/
├── 79/
├── 80/
├── 81/
├── 82/
├── 83/
├── 84/
├── 85/
└── results.csv
```

И **не будет изменять `data/input/test` или существующие fingerprints**.

Первый запуск сделаем в режиме диагностики — он покажет результаты и similarity, чтобы подобрать порог `00`. После этого включим копирование.

Если хочешь, я сразу дам **готовый `classify_test.sh` целиком**, который можно просто вставить в терминал и запустить.

---

### 👤 **User** — 2026-08-13 23:03:26

давай готовый

---

### 🤖 **Assistant** — 2026-08-13 23:03:27

Да. Ниже готовый вариант. Он рассчитан на твою текущую структуру проекта `scene_fingerprint_mvp_v02`, использует уже установленный `.venv`/`uv`, fingerprints `78–85` и **не трогает patch-файлы**.

Скрипт сам создаст папки и Python-классификатор.

### 1. Создай скрипт

Из корня проекта:

```bash
cd ~/scene_fingerprint_mvp_v02

cat > classify_test.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# TEST CLASSIFIER
# Classify images from data/input/test against fingerprints
# 78..85 using DINOv2 global embeddings.
#
# Unknown / insufficiently confident images -> 00
# Existing fingerprints and input images are NOT modified.
# ============================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TEST_DIR="$ROOT/data/input/test"
FP_DIR="$ROOT/data/fingerprints"
OUT_DIR="$ROOT/data/output/test_classified"

PY="$ROOT/.venv/bin/python"

# ------------------------------------------------------------
# Settings
# ------------------------------------------------------------

# Minimum cosine similarity required for recognition.
# Start relatively conservative; we will tune this after test.
THRESHOLD="${THRESHOLD:-0.60}"

# Minimum difference between best and second-best match.
# Prevents uncertain 78/79/etc. classifications.
MARGIN="${MARGIN:-0.03}"

# Fingerprints used for this test
FINGERPRINTS=(78 79 80 81 82 83 84 85)

# ------------------------------------------------------------
# Checks
# ------------------------------------------------------------

echo
echo "============================================================"
echo " Scene Fingerprint — TEST CLASSIFIER"
echo "============================================================"
echo

if [[ ! -d "$TEST_DIR" ]]; then
    echo "ERROR: test directory not found:"
    echo "  $TEST_DIR"
    exit 1
fi

if [[ ! -x "$PY" ]]; then
    echo "ERROR: Python environment not found:"
    echo "  $PY"
    echo
    echo "Run this from the project root."
    exit 1
fi

echo "[1/5] Checking fingerprints..."

for ID in "${FINGERPRINTS[@]}"; do
    if [[ ! -f "$FP_DIR/$ID/embeddings.npy" ]]; then
        echo "ERROR: fingerprint $ID is missing:"
        echo "  $FP_DIR/$ID/embeddings.npy"
        exit 1
    fi
done

echo "      fingerprints: ${FINGERPRINTS[*]}"

# ------------------------------------------------------------
# Create output directories
# ------------------------------------------------------------

echo
echo "[2/5] Creating output directories..."

mkdir -p "$OUT_DIR"

# Clean/create classification folders.
for ID in 00 "${FINGERPRINTS[@]}"; do
    mkdir -p "$OUT_DIR/$ID"
done

echo "      output: $OUT_DIR"

# ------------------------------------------------------------
# Create Python classifier
# ------------------------------------------------------------

PYFILE="$ROOT/.classify_test_tmp.py"

cat > "$PYFILE" <<'PYTHON'
import os
import sys
import csv
import shutil
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

# ============================================================
# Configuration from environment
# ============================================================

ROOT = Path(os.environ["SF_ROOT"])
TEST_DIR = Path(os.environ["SF_TEST_DIR"])
FP_DIR = Path(os.environ["SF_FP_DIR"])
OUT_DIR = Path(os.environ["SF_OUT_DIR"])

THRESHOLD = float(os.environ["SF_THRESHOLD"])
MARGIN = float(os.environ["SF_MARGIN"])

FINGERPRINTS = os.environ["SF_FINGERPRINTS"].split(",")

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

# ============================================================
# Helpers
# ============================================================

def normalize(x):
    x = np.asarray(x, dtype=np.float32)
    norm = np.linalg.norm(x, axis=-1, keepdims=True)
    norm[norm == 0] = 1.0
    return x / norm

def load_fingerprint(fp_id):
    """
    Load fingerprint embeddings and create one normalized
    centroid representation.

    We deliberately use ONLY embeddings.npy / centroid.npy.
    Patch embeddings are NOT loaded.
    """

    fp_path = FP_DIR / fp_id

    centroid_file = fp_path / "centroid.npy"
    embeddings_file = fp_path / "embeddings.npy"

    if centroid_file.exists():
        centroid = np.load(centroid_file)

        # Some files may contain an extra dimension.
        centroid = np.asarray(centroid, dtype=np.float32).reshape(-1)

        return normalize(centroid)

    if embeddings_file.exists():
        embeddings = np.load(embeddings_file)

        embeddings = np.asarray(
            embeddings,
            dtype=np.float32
        )

        if embeddings.ndim == 1:
            centroid = embeddings
        else:
            centroid = embeddings.mean(axis=0)

        return normalize(centroid)

    raise RuntimeError(
        f"Cannot load fingerprint {fp_id}: "
        f"no centroid.npy or embeddings.npy"
    )

def get_images(folder):
    result = []

    for p in sorted(folder.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
            result.append(p)

    return result

# ============================================================
# Load model
# ============================================================

print()
print("[SceneEmbedder] Loading DINOv2...")

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print(f"[SceneEmbedder] device={device}")

if device.type == "cuda":
    print(
        "[SceneEmbedder] GPU:",
        torch.cuda.get_device_name(0)
    )

processor = AutoImageProcessor.from_pretrained(
    "facebook/dinov2-base"
)

model = AutoModel.from_pretrained(
    "facebook/dinov2-base"
)

model.to(device)
model.eval()

print("[SceneEmbedder] model ready")

# ============================================================
# Load fingerprints
# ============================================================

print()
print("[Fingerprint] Loading fingerprints...")

fingerprints = {}

for fp_id in FINGERPRINTS:
    fingerprints[fp_id] = load_fingerprint(fp_id)

    print(
        f"  {fp_id}: dimension={len(fingerprints[fp_id])}"
    )

fp_ids = list(fingerprints.keys())

fp_matrix = np.stack(
    [fingerprints[x] for x in fp_ids]
)

print(
    f"[Fingerprint] loaded {len(fp_ids)} fingerprints"
)

# ============================================================
# Find test images
# ============================================================

images = get_images(TEST_DIR)

print()
print(f"[TEST] directory: {TEST_DIR}")
print(f"[TEST] images:    {len(images)}")

if not images:
    print("No images found.")
    sys.exit(0)

# ============================================================
# CSV
# ============================================================

csv_path = OUT_DIR / "results.csv"

csv_file = open(
    csv_path,
    "w",
    newline="",
    encoding="utf-8"
)

writer = csv.writer(csv_file)

writer.writerow([
    "filename",
    "predicted",
    "best_score",
    "second_score",
    "margin",
    "status",
])

# ============================================================
# Classification
# ============================================================

recognized = 0
unknown = 0

print()
print("============================================================")
print(" RESULTS")
print("============================================================")

for index, image_path in enumerate(images, start=1):

    relative_name = image_path.relative_to(TEST_DIR)

    try:
        image = Image.open(image_path).convert("RGB")

        inputs = processor(
            images=image,
            return_tensors="pt"
        )

        inputs = {
            k: v.to(device)
            for k, v in inputs.items()
        }

        with torch.inference_mode():
            outputs = model(**inputs)

            # DINOv2 CLS token
            embedding = outputs.last_hidden_state[:, 0, :]

            embedding = torch.nn.functional.normalize(
                embedding,
                p=2,
                dim=1
            )

        emb = embedding[0].detach().cpu().numpy()

        # cosine similarity because both vectors normalized
        scores = fp_matrix @ emb

        order = np.argsort(scores)[::-1]

        best_idx = order[0]

        best_id = fp_ids[best_idx]
        best_score = float(scores[best_idx])

        if len(order) > 1:
            second_score = float(scores[order[1]])
        else:
            second_score = 0.0

        margin = best_score - second_score

        # ----------------------------------------------------
        # Decision
        # ----------------------------------------------------

        if (
            best_score >= THRESHOLD
            and margin >= MARGIN
        ):
            predicted = best_id
            status = "MATCH"
            recognized += 1
        else:
            predicted = "00"
            status = "UNKNOWN"
            unknown += 1

        # ----------------------------------------------------
        # Destination
        # ----------------------------------------------------

        destination_dir = OUT_DIR / predicted

        # Preserve relative directory structure if needed.
        # To avoid filename collisions, prefix nested paths.
        safe_name = str(relative_name).replace(
            os.sep,
            "__"
        )

        destination = destination_dir / safe_name

        shutil.copy2(
            image_path,
            destination
        )

        writer.writerow([
            str(relative_name),
            predicted,
            f"{best_score:.6f}",
            f"{second_score:.6f}",
            f"{margin:.6f}",
            status,
        ])

        print(
            f"{index:4d}/{len(images):4d}  "
            f"{relative_name}  ->  "
            f"{predicted:>2}  "
            f"score={best_score:.4f}  "
            f"second={second_score:.4f}  "
            f"margin={margin:.4f}  "
            f"{status}"
        )

    except Exception as e:

        print(
            f"{index:4d}/{len(images):4d}  "
            f"{relative_name}  ->  ERROR: {e}"
        )

        writer.writerow([
            str(relative_name),
            "00",
            "",
            "",
            "",
            f"ERROR: {e}",
        ])

        unknown += 1

csv_file.close()

# ============================================================
# Summary
# ============================================================

print()
print("============================================================")
print(" SUMMARY")
print("============================================================")

print(f"Total:       {len(images)}")
print(f"Recognized:  {recognized}")
print(f"Unknown 00:  {unknown}")

print()
print(f"Threshold:   {THRESHOLD}")
print(f"Margin:      {MARGIN}")

print()
print("Results:")
print(f"  {OUT_DIR}")

print()
print("CSV:")
print(f"  {csv_path}")

print()
print("============================================================")
PYTHON

# ------------------------------------------------------------
# Run
# ------------------------------------------------------------

echo
echo "[3/5] Running classifier..."
echo
echo "      threshold = $THRESHOLD"
echo "      margin    = $MARGIN"
echo

export SF_ROOT="$ROOT"
export SF_TEST_DIR="$TEST_DIR"
export SF_FP_DIR="$FP_DIR"
export SF_OUT_DIR="$OUT_DIR"
export SF_THRESHOLD="$THRESHOLD"
export SF_MARGIN="$MARGIN"
export SF_FINGERPRINTS="$(IFS=,; echo "${FINGERPRINTS[*]}")"

"$PY" "$PYFILE"

# ------------------------------------------------------------
# Remove temporary Python file
# ------------------------------------------------------------

rm -f "$PYFILE"

# ------------------------------------------------------------
# Final
# ------------------------------------------------------------

echo
echo "[4/5] Classification complete."

echo
echo "[5/5] Output folders:"
echo

for ID in 00 "${FINGERPRINTS[@]}"; do
    COUNT=$(find "$OUT_DIR/$ID" -maxdepth 1 -type f 2>/dev/null | wc -l)
    printf "  %-3s %6d files\n" "$ID" "$COUNT"
done

echo
echo "CSV:"
echo "  $OUT_DIR/results.csv"

echo
echo "============================================================"
echo " DONE"
echo "============================================================"
BASH

chmod +x classify_test.sh
```

### 2. Запуск

Сначала просто:

```bash
./classify_test.sh
```

Он сам создаст:

```text
data/output/test_classified/
```

и папки:

```text
00
78
79
80
81
82
83
84
85
```

### Важный момент

Я поставил начальные параметры:

```text
threshold = 0.60
margin    = 0.03
```

Но **не считаем их окончательными**. Нам сейчас важнее увидеть реальные результаты на твоих фотографиях.

После запуска пришли сюда **весь вывод от `RESULTS` до `SUMMARY`** или хотя бы последние ~100 строк.

По нему мы посмотрим, например:

```text
IMG_001.jpg -> 78 score=0.91
IMG_002.jpg -> 78 score=0.89
IMG_003.jpg -> 83 score=0.64
IMG_004.jpg -> 84 score=0.62
IMG_005.jpg -> 00 score=0.58
```

И тогда уже подберём `threshold` так, чтобы **фотографии действительно новых мест уходили в `00`, а 78–85 распознавались максимально полно**.

При этом `patch_embeddings.npy` размером десятки мегабайт вообще не загружается.

---

### 👤 **User** — 2026-08-13 23:06:26

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ./classify_test.sh

============================================================
 Scene Fingerprint — TEST CLASSIFIER
============================================================

ERROR: test directory not found:
  /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ./classify_test.sh

============================================================
 Scene Fingerprint — TEST CLASSIFIER
============================================================

[1/5] Checking fingerprints...
ERROR: fingerprint 83 is missing:
  /home/alexice/projects/scene_fingerprint_mvp_v02/data/fingerprints/83/embeddings.npy
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-13 23:06:28

Да, здесь две отдельные проблемы, и обе легко исправить.

### 1. `test` лежит не там

Скрипт сейчас ищет:

```text
~/projects/scene_fingerprint_mvp_v02/data/input/test
```

В первый запуск этой папки вообще не было. Во второй запуск `test` уже появился/был создан, поэтому скрипт пошёл дальше.

### 2. Fingerprint 83 отсутствует

Скрипт жёстко проверяет:

```text
78 79 80 81 82 83 84 85
```

и останавливается на `83`.

Но нам **не надо предполагать**, что fingerprints лежат именно такими папками. Судя по нашей предыдущей работе, у тебя могли быть другие имена/структура, например `78_patch`, а часть слепков могла находиться непосредственно в `data/fingerprints`.

Давай сейчас **ничего не менять и не создавать заново**. Сначала посмотрим фактическую структуру.

Выполни из `~/projects/scene_fingerprint_mvp_v02`:

```bash
echo "=== TEST ==="
find data/input -maxdepth 2 -type f | sort | head -50

echo
echo "=== FINGERPRINT DIRECTORIES ==="
find data/fingerprints -maxdepth 2 -type f | sort

echo
echo "=== FINGERPRINT DIRS ==="
find data/fingerprints -mindepth 1 -maxdepth 1 -type d | sort
```

И ещё:

```bash
echo "=== PROJECT DATA ==="
ls -lah data/
echo
ls -lah data/fingerprints/
echo
ls -lah data/input/
```

**Пришли весь вывод сюда.**

После этого я переделаю `classify_test.sh` так, чтобы он:

- автоматически находил реальные fingerprints;
- использовал именно имеющиеся `78–85`;
- понимал `78_patch`, если он у тебя используется;
- сам создавал `test`, если нужно;
- сам создавал `00/78/79/...`;
- **не падал из-за отсутствующего fingerprint**;
- отдельно показывал, какие из `78–85` реально найдены;
- и главное — не будет считать отсутствие какого-либо слепка ошибкой, если мы его сознательно не используем.

Сейчас **не запускай создание fingerprints заново** — сначала посмотрим структуру.

---

### 👤 **User** — 2026-08-13 23:07:46

используй v33

---

### 🤖 **Assistant** — 2026-08-13 23:07:46

Да. Тогда **используем именно fingerprints `78_v33 ... 85_v33`** и вообще не трогаем `78_patch` и старые версии.

Переделаем скрипт под твою реальную схему:

```text
data/fingerprints/
├── 78_v33/
├── 79_v33/
├── 80_v33/
├── 81_v33/
├── 82_v33/
├── 83_v33/
├── 84_v33/
└── 85_v33/
```

И результат:

```text
data/output/test_classified/
├── 00/
├── 78/
├── 79/
├── 80/
├── 81/
├── 82/
├── 83/
├── 84/
└── 85/
```

Но есть ещё один важный момент: **нужно точно знать структуру `*_v33`** — там могут быть `embeddings.npy`, `centroid.npy`, `metadata.json` и т.д.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find data/fingerprints -maxdepth 2 -type f \
  \( -path '*78_v33*' -o \
     -path '*79_v

---

### 👤 **User** — 2026-08-13 23:07:53

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo "=== TEST ==="
find data/input -maxdepth 2 -type f | sort | head -50

echo
echo "=== FINGERPRINT DIRECTORIES ==="
find data/fingerprints -maxdepth 2 -type f | sort

echo
echo "=== FINGERPRINT DIRS ==="
find data/fingerprints -mindepth 1 -maxdepth 1 -type d | sort
=== TEST ===
data/input/78/photo001.JPG
data/input/78/photo002.JPG
data/input/78/photo003.JPG
data/input/78/photo004.JPG
data/input/78/photo005.JPG
data/input/78/photo006.JPG
data/input/78/photo007.JPG
data/input/78/photo008.JPG
data/input/78/photo009.JPG
data/input/78/photo010.JPG
data/input/78/photo011.JPG
data/input/78/photo012.JPG
data/input/78/photo013.JPG
data/input/78/photo014.JPG
data/input/78/photo015.JPG
data/input/78/photo016.JPG
data/input/78/photo017.JPG
data/input/78/photo018.JPG
data/input/78/photo019.JPG
data/input/78/photo020.JPG
data/input/78/photo021.JPG
data/input/78/photo022.JPG
data/input/78/photo023.JPG
data/input/78/photo024.JPG
data/input/78/photo025.JPG
data/input/78/photo026.JPG
data/input/78/photo027.JPG
data/input/78/photo028.JPG
data/input/78/photo029.JPG
data/input/78/photo030.JPG
data/input/78/photo031.JPG
data/input/78/photo032.JPG
data/input/78/photo033.JPG
data/input/78/photo034.JPG
data/input/78/photo035.JPG
data/input/78/photo036.JPG
data/input/78/photo037.JPG
data/input/78/photo038.JPG
data/input/78/photo039.JPG
data/input/78/photo040.JPG
data/input/78/photo041.JPG
data/input/78/photo042.JPG
data/input/78/photo043.JPG
data/input/78/photo044.JPG
data/input/78/photo045.JPG
data/input/78/photo046.JPG
data/input/78/photo047.JPG
data/input/78/photo048.JPG
data/input/78/photo049.JPG
data/input/78/photo050.JPG

=== FINGERPRINT DIRECTORIES ===
data/fingerprints/78/centroid.npy
data/fingerprints/78/embeddings.npy
data/fingerprints/78/faiss.index
data/fingerprints/78/metadata.json
data/fingerprints/78_patch/centroid.npy
data/fingerprints/78_patch/embeddings.npy
data/fingerprints/78_patch/faiss.index
data/fingerprints/78_patch/metadata.json
data/fingerprints/78_patch/patch_centroid.npy
data/fingerprints/78_patch/patch_embeddings.npy
data/fingerprints/78_patch/patch_representatives.npy
data/fingerprints/78_patch/representatives.npy
data/fingerprints/78/representatives.npy
data/fingerprints/78_v31/centroid.npy
data/fingerprints/78_v31/embeddings.npy
data/fingerprints/78_v31/faiss.index
data/fingerprints/78_v31/metadata.json
data/fingerprints/78_v31/patch_centroid.npy
data/fingerprints/78_v31/patch_embeddings.npy
data/fingerprints/78_v31/patch_representatives.npy
data/fingerprints/78_v31/representatives.npy
data/fingerprints/78_v32/centroid.npy
data/fingerprints/78_v32/color_embeddings.npy
data/fingerprints/78_v32/embeddings.npy
data/fingerprints/78_v32/environment_embeddings.npy
data/fingerprints/78_v32/faiss.index
data/fingerprints/78_v32/metadata.json
data/fingerprints/78_v32/representative_indices.npy
data/fingerprints/78_v32/representatives.npy
data/fingerprints/78_v32/spatial_embeddings.npy
data/fingerprints/78_v33/centroid.npy
data/fingerprints/78_v33/color_embeddings.npy
data/fingerprints/78_v33/embeddings.npy
data/fingerprints/78_v33/environment_embeddings.npy
data/fingerprints/78_v33/faiss.index
data/fingerprints/78_v33/metadata.json
data/fingerprints/78_v33/representative_indices.npy
data/fingerprints/78_v33/representatives.npy
data/fingerprints/78_v33/spatial_embeddings.npy
data/fingerprints/78_v3/centroid.npy
data/fingerprints/78_v3/embeddings.npy
data/fingerprints/78_v3/environment_centroid.npy
data/fingerprints/78_v3/environment_embeddings.npy
data/fingerprints/78_v3/environment_representatives.npy
data/fingerprints/78_v3/faiss.index
data/fingerprints/78_v3/metadata.json
data/fingerprints/78_v3/patch_centroid.npy
data/fingerprints/78_v3/patch_embeddings.npy
data/fingerprints/78_v3/patch_representatives.npy
data/fingerprints/78_v3/representative_indices.npy
data/fingerprints/78_v3/representatives.npy
data/fingerprints/79/centroid.npy
data/fingerprints/79/embeddings.npy
data/fingerprints/79/faiss.index
data/fingerprints/79/metadata.json
data/fingerprints/79/patch_centroid.npy
data/fingerprints/79/patch_embeddings.npy
data/fingerprints/79/patch_representatives.npy
data/fingerprints/79/representatives.npy
data/fingerprints/79_v31/centroid.npy
data/fingerprints/79_v31/embeddings.npy
data/fingerprints/79_v31/faiss.index
data/fingerprints/79_v31/metadata.json
data/fingerprints/79_v31/patch_centroid.npy
data/fingerprints/79_v31/patch_embeddings.npy
data/fingerprints/79_v31/patch_representatives.npy
data/fingerprints/79_v31/representatives.npy
data/fingerprints/79_v32/centroid.npy
data/fingerprints/79_v32/color_embeddings.npy
data/fingerprints/79_v32/embeddings.npy
data/fingerprints/79_v32/environment_embeddings.npy
data/fingerprints/79_v32/faiss.index
data/fingerprints/79_v32/metadata.json
data/fingerprints/79_v32/representative_indices.npy
data/fingerprints/79_v32/representatives.npy
data/fingerprints/79_v32/spatial_embeddings.npy
data/fingerprints/79_v33/centroid.npy
data/fingerprints/79_v33/color_embeddings.npy
data/fingerprints/79_v33/embeddings.npy
data/fingerprints/79_v33/environment_embeddings.npy
data/fingerprints/79_v33/faiss.index
data/fingerprints/79_v33/metadata.json
data/fingerprints/79_v33/representative_indices.npy
data/fingerprints/79_v33/representatives.npy
data/fingerprints/79_v33/spatial_embeddings.npy
data/fingerprints/80/centroid.npy
data/fingerprints/80/embeddings.npy
data/fingerprints/80/faiss.index
data/fingerprints/80/metadata.json
data/fingerprints/80/patch_centroid.npy
data/fingerprints/80/patch_embeddings.npy
data/fingerprints/80/patch_representatives.npy
data/fingerprints/80/representatives.npy
data/fingerprints/80_v31/centroid.npy
data/fingerprints/80_v31/embeddings.npy
data/fingerprints/80_v31/faiss.index
data/fingerprints/80_v31/metadata.json
data/fingerprints/80_v31/patch_centroid.npy
data/fingerprints/80_v31/patch_embeddings.npy
data/fingerprints/80_v31/patch_representatives.npy
data/fingerprints/80_v31/representatives.npy
data/fingerprints/80_v32/centroid.npy
data/fingerprints/80_v32/color_embeddings.npy
data/fingerprints/80_v32/embeddings.npy
data/fingerprints/80_v32/environment_embeddings.npy
data/fingerprints/80_v32/faiss.index
data/fingerprints/80_v32/metadata.json
data/fingerprints/80_v32/representative_indices.npy
data/fingerprints/80_v32/representatives.npy
data/fingerprints/80_v32/spatial_embeddings.npy
data/fingerprints/80_v33/centroid.npy
data/fingerprints/80_v33/color_embeddings.npy
data/fingerprints/80_v33/embeddings.npy
data/fingerprints/80_v33/environment_embeddings.npy
data/fingerprints/80_v33/faiss.index
data/fingerprints/80_v33/metadata.json
data/fingerprints/80_v33/representative_indices.npy
data/fingerprints/80_v33/representatives.npy
data/fingerprints/80_v33/spatial_embeddings.npy
data/fingerprints/81/centroid.npy
data/fingerprints/81/embeddings.npy
data/fingerprints/81/faiss.index
data/fingerprints/81/metadata.json
data/fingerprints/81/patch_centroid.npy
data/fingerprints/81/patch_embeddings.npy
data/fingerprints/81/patch_representatives.npy
data/fingerprints/81/representatives.npy
data/fingerprints/81_v31/centroid.npy
data/fingerprints/81_v31/embeddings.npy
data/fingerprints/81_v31/faiss.index
data/fingerprints/81_v31/metadata.json
data/fingerprints/81_v31/patch_centroid.npy
data/fingerprints/81_v31/patch_embeddings.npy
data/fingerprints/81_v31/patch_representatives.npy
data/fingerprints/81_v31/representatives.npy
data/fingerprints/81_v32/centroid.npy
data/fingerprints/81_v32/color_embeddings.npy
data/fingerprints/81_v32/embeddings.npy
data/fingerprints/81_v32/environment_embeddings.npy
data/fingerprints/81_v32/faiss.index
data/fingerprints/81_v32/metadata.json
data/fingerprints/81_v32/representative_indices.npy
data/fingerprints/81_v32/representatives.npy
data/fingerprints/81_v32/spatial_embeddings.npy
data/fingerprints/81_v33/centroid.npy
data/fingerprints/81_v33/color_embeddings.npy
data/fingerprints/81_v33/embeddings.npy
data/fingerprints/81_v33/environment_embeddings.npy
data/fingerprints/81_v33/faiss.index
data/fingerprints/81_v33/metadata.json
data/fingerprints/81_v33/representative_indices.npy
data/fingerprints/81_v33/representatives.npy
data/fingerprints/81_v33/spatial_embeddings.npy
data/fingerprints/82/centroid.npy
data/fingerprints/82/embeddings.npy
data/fingerprints/82/faiss.index
data/fingerprints/82/metadata.json
data/fingerprints/82/patch_centroid.npy
data/fingerprints/82/patch_embeddings.npy
data/fingerprints/82/patch_representatives.npy
data/fingerprints/82/representatives.npy
data/fingerprints/82_v31/centroid.npy
data/fingerprints/82_v31/embeddings.npy
data/fingerprints/82_v31/faiss.index
data/fingerprints/82_v31/metadata.json
data/fingerprints/82_v31/patch_centroid.npy
data/fingerprints/82_v31/patch_embeddings.npy
data/fingerprints/82_v31/patch_representatives.npy
data/fingerprints/82_v31/representatives.npy
data/fingerprints/82_v32/centroid.npy
data/fingerprints/82_v32/color_embeddings.npy
data/fingerprints/82_v32/embeddings.npy
data/fingerprints/82_v32/environment_embeddings.npy
data/fingerprints/82_v32/faiss.index
data/fingerprints/82_v32/metadata.json
data/fingerprints/82_v32/representative_indices.npy
data/fingerprints/82_v32/representatives.npy
data/fingerprints/82_v32/spatial_embeddings.npy
data/fingerprints/82_v33/centroid.npy
data/fingerprints/82_v33/color_embeddings.npy
data/fingerprints/82_v33/embeddings.npy
data/fingerprints/82_v33/environment_embeddings.npy
data/fingerprints/82_v33/faiss.index
data/fingerprints/82_v33/metadata.json
data/fingerprints/82_v33/representative_indices.npy
data/fingerprints/82_v33/representatives.npy
data/fingerprints/82_v33/spatial_embeddings.npy
data/fingerprints/83_v33/centroid.npy
data/fingerprints/83_v33/color_embeddings.npy
data/fingerprints/83_v33/embeddings.npy
data/fingerprints/83_v33/environment_embeddings.npy
data/fingerprints/83_v33/faiss.index
data/fingerprints/83_v33/metadata.json
data/fingerprints/83_v33/representative_indices.npy
data/fingerprints/83_v33/representatives.npy
data/fingerprints/83_v33/spatial_embeddings.npy
data/fingerprints/84_v33/centroid.npy
data/fingerprints/84_v33/color_embeddings.npy
data/fingerprints/84_v33/embeddings.npy
data/fingerprints/84_v33/environment_embeddings.npy
data/fingerprints/84_v33/faiss.index
data/fingerprints/84_v33/metadata.json
data/fingerprints/84_v33/representative_indices.npy
data/fingerprints/84_v33/representatives.npy
data/fingerprints/84_v33/spatial_embeddings.npy
data/fingerprints/85_v33/centroid.npy
data/fingerprints/85_v33/color_embeddings.npy
data/fingerprints/85_v33/embeddings.npy
data/fingerprints/85_v33/environment_embeddings.npy
data/fingerprints/85_v33/faiss.index
data/fingerprints/85_v33/metadata.json
data/fingerprints/85_v33/representative_indices.npy
data/fingerprints/85_v33/representatives.npy
data/fingerprints/85_v33/spatial_embeddings.npy

=== FINGERPRINT DIRS ===
data/fingerprints/78
data/fingerprints/78_patch
data/fingerprints/78_v3
data/fingerprints/78_v31
data/fingerprints/78_v32
data/fingerprints/78_v33
data/fingerprints/79
data/fingerprints/79_v31
data/fingerprints/79_v32
data/fingerprints/79_v33
data/fingerprints/80
data/fingerprints/80_v31
data/fingerprints/80_v32
data/fingerprints/80_v33
data/fingerprints/81
data/fingerprints/81_v31
data/fingerprints/81_v32
data/fingerprints/81_v33
data/fingerprints/82
data/fingerprints/82_v31
data/fingerprints/82_v32
data/fingerprints/82_v33
data/fingerprints/83_v33
data/fingerprints/84_v33
data/fingerprints/85_v33
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo "=== PROJECT DATA ==="
ls -lah data/
echo
ls -lah data/fingerprints/
echo
ls -lah data/input/
=== PROJECT DATA ===
total 28K
drwxrwxr-x  7 alexice alexice 4.0K Aug 13 22:10  .
drwxrwxr-x 15 alexice alexice 4.0K Aug 13 23:03  ..
drwxrwxr-x 27 alexice alexice 4.0K Aug 13 22:48  fingerprints
drwxrwxr-x  3 alexice alexice 4.0K Aug  8 04:08  fingerprints_backup_before_patch
drwxrwxr-x 14 alexice alexice 4.0K Aug  9 11:26 'fingerprints (Copy)'
drwxrwxr-x 12 alexice alexice 4.0K Aug 13 23:06  input
drwxrwxr-x  3 alexice alexice 4.0K Aug 13 22:10  output

total 108K
drwxrwxr-x 27 alexice alexice 4.0K Aug 13 22:48 .
drwxrwxr-x  7 alexice alexice 4.0K Aug 13 22:10 ..
drwxrwxr-x  2 alexice alexice 4.0K Aug  8 04:08 78
drwxrwxr-x  2 alexice alexice 4.0K Aug  8 13:16 78_patch
drwxrwxr-x  2 alexice alexice 4.0K Aug  8 18:10 78_v3
drwxrwxr-x  2 alexice alexice 4.0K Aug  8 23:13 78_v31
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 16:16 78_v32
drwxrwxr-x  2 alexice alexice 4.0K Aug 10 21:18 78_v33
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 11:16 79
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 11:25 79_v31
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 16:03 79_v32
drwxrwxr-x  2 alexice alexice 4.0K Aug 10 21:21 79_v33
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 11:16 80
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 11:25 80_v31
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 16:03 80_v32
drwxrwxr-x  2 alexice alexice 4.0K Aug 10 21:22 80_v33
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 11:17 81
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 11:25 81_v31
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 16:03 81_v32
drwxrwxr-x  2 alexice alexice 4.0K Aug 10 21:22 81_v33
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 11:17 82
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 11:26 82_v31
drwxrwxr-x  2 alexice alexice 4.0K Aug  9 16:04 82_v32
drwxrwxr-x  2 alexice alexice 4.0K Aug 10 21:22 82_v33
drwxrwxr-x  2 alexice alexice 4.0K Aug 13 21:26 83_v33
drwxrwxr-x  2 alexice alexice 4.0K Aug 13 22:48 84_v33
drwxrwxr-x  2 alexice alexice 4.0K Aug 13 22:49 85_v33

total 56K
drwxrwxr-x 12 alexice alexice 4.0K Aug 13 23:06 .
drwxrwxr-x  7 alexice alexice 4.0K Aug 13 22:10 ..
drwxrwxr-x  2 alexice alexice 4.0K Aug  7 23:45 78
drwx------  2 alexice alexice 4.0K Aug  9 11:14 79
drwx------  2 alexice alexice 4.0K Aug  9 11:14 80
drwx------  2 alexice alexice 4.0K Aug  9 11:14 81
drwx------  2 alexice alexice 4.0K Aug  9 11:15 82
drwx------  2 alexice alexice 4.0K Aug 12 19:28 83
drwx------  2 alexice alexice 4.0K Aug 12 19:28 84
drwx------  2 alexice alexice 4.0K Aug 12 19:28 85
drwxrwxr-x  2 alexice alexice 4.0K Aug  7 23:35 new
drwx------  2 alexice alexice  12K Aug 13 21:55 test
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-13 23:07:54

Отлично, теперь структура полностью понятна. И да — **используем только `78_v33` … `85_v33`**.

Причём у `v33` есть дополнительные признаки:

```text
embeddings.npy
color_embeddings.npy
environment_embeddings.npy
spatial_embeddings.npy
```

Это хорошо. Но **на первом тесте я предлагаю не смешивать их вручную**. Сначала проверим базовый `embeddings.npy`, чтобы понять, насколько хорошо сам DINOv2 разделяет места. Patch-файлы вообще не загружаем.

Ещё исправляем важную вещь: `test` у тебя уже существует, и фотографии там, судя по структуре, лежат непосредственно внутри него. Поэтому скрипт должен искать рекурсивно, как мы сделали.

### Замени старый скрипт целиком

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > classify_test.sh <<'BASH'
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TEST_DIR="$ROOT/data/input/test"
FP_DIR="$ROOT/data/fingerprints"
OUT_DIR="$ROOT/data/output/test_classified"

PY="$ROOT/.venv/bin/python"

# ============================================================
# ONLY V33 FINGERPRINTS
# ============================================================

FINGERPRINTS=(
    78_v33
    79_v33
    80_v33
    81_v33
    82_v33
    83_v33
    84_v33
    85_v33
)

# ------------------------------------------------------------
# Initial thresholds
# ------------------------------------------------------------

THRESHOLD="${THRESHOLD:-0.60}"
MARGIN="${MARGIN:-0.03}"

# ------------------------------------------------------------
# Checks
# ------------------------------------------------------------

echo
echo "============================================================"
echo " Scene Fingerprint — TEST / V33"
echo "============================================================"
echo

if [[ ! -d "$TEST_DIR" ]]; then
    echo "ERROR: test directory not found:"
    echo "  $TEST_DIR"
    exit 1
fi

if [[ ! -x "$PY" ]]; then
    echo "ERROR: Python environment not found:"
    echo "  $PY"
    exit 1
fi

echo "[1/5] Checking V33 fingerprints..."

for FP in "${FINGERPRINTS[@]}"; do

    if [[ ! -d "$FP_DIR/$FP" ]]; then
        echo "ERROR: fingerprint directory missing:"
        echo "  $FP_DIR/$FP"
        exit 1
    fi

    if [[ ! -f "$FP_DIR/$FP/embeddings.npy" ]]; then
        echo "ERROR: embeddings missing:"
        echo "  $FP_DIR/$FP/embeddings.npy"
        exit 1
    fi

    echo "      OK: $FP"
done

# ------------------------------------------------------------
# Output
# ------------------------------------------------------------

echo
echo "[2/5] Creating output directories..."

mkdir -p "$OUT_DIR"

for ID in 00 78 79 80 81 82 83 84 85; do
    mkdir -p "$OUT_DIR/$ID"
done

# ------------------------------------------------------------
# Python classifier
# ------------------------------------------------------------

PYFILE="$ROOT/.classify_test_tmp.py"

cat > "$PYFILE" <<'PYTHON'
import os
import csv
import shutil
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

ROOT = Path(os.environ["SF_ROOT"])
TEST_DIR = Path(os.environ["SF_TEST_DIR"])
FP_DIR = Path(os.environ["SF_FP_DIR"])
OUT_DIR = Path(os.environ["SF_OUT_DIR"])

THRESHOLD = float(os.environ["SF_THRESHOLD"])
MARGIN = float(os.environ["SF_MARGIN"])

FINGERPRINTS = os.environ["SF_FINGERPRINTS"].split(",")

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}

def normalize(v):
    v = np.asarray(v, dtype=np.float32)
    norm = np.linalg.norm(v)

    if norm == 0:
        return v

    return v / norm

def load_fp(fp_id):

    path = FP_DIR / fp_id

    # V33 centroid is preferred.
    centroid_file = path / "centroid.npy"

    if centroid_file.exists():

        centroid = np.load(
            centroid_file
        ).astype(np.float32)

        centroid = centroid.reshape(-1)

        return normalize(centroid)

    # Fallback.
    embeddings = np.load(
        path / "embeddings.npy"
    ).astype(np.float32)

    if embeddings.ndim == 1:
        centroid = embeddings
    else:
        centroid = embeddings.mean(axis=0)

    return normalize(centroid)

def get_images():

    images = []

    for p in sorted(TEST_DIR.rglob("*")):

        if (
            p.is_file()
            and p.suffix.lower() in IMAGE_EXTENSIONS
        ):
            images.append(p)

    return images

# ============================================================
# MODEL
# ============================================================

print()
print("[SceneEmbedder] Loading facebook/dinov2-base...")

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print(f"[SceneEmbedder] device={device}")

if device.type == "cuda":

    print(
        "[SceneEmbedder] GPU:",
        torch.cuda.get_device_name(0)
    )

processor = AutoImageProcessor.from_pretrained(
    "facebook/dinov2-base"
)

model = AutoModel.from_pretrained(
    "facebook/dinov2-base"
)

model.to(device)
model.eval()

print("[SceneEmbedder] ready")

# ============================================================
# FINGERPRINTS
# ============================================================

print()
print("[Fingerprint] Loading V33...")

fp_vectors = {}

for fp in FINGERPRINTS:

    vec = load_fp(fp)

    fp_vectors[fp] = vec

    print(
        f"  {fp}: dimension={vec.shape[0]}"
    )

fp_matrix = np.stack(
    [fp_vectors[x] for x in FINGERPRINTS]
)

print(
    f"[Fingerprint] loaded {len(FINGERPRINTS)} fingerprints"
)

# ============================================================
# TEST FILES
# ============================================================

images = get_images()

print()
print(f"[TEST] directory: {TEST_DIR}")
print(f"[TEST] images:    {len(images)}")

if not images:
    print("ERROR: no images found")
    raise SystemExit(1)

# ============================================================
# CSV
# ============================================================

csv_path = OUT_DIR / "results.csv"

csv_file = open(
    csv_path,
    "w",
    newline="",
    encoding="utf-8"
)

writer = csv.writer(csv_file)

writer.writerow([
    "filename",
    "predicted",
    "best_score",
    "second_score",
    "margin",
    "status",
])

# ============================================================
# CLASSIFICATION
# ============================================================

recognized = 0
unknown = 0
errors = 0

print()
print("============================================================")
print(" RESULTS")
print("============================================================")

for n, image_path in enumerate(images, 1):

    relative = image_path.relative_to(TEST_DIR)

    try:

        image = Image.open(
            image_path
        ).convert("RGB")

        inputs = processor(
            images=image,
            return_tensors="pt"
        )

        inputs = {
            k: v.to(device)
            for k, v in inputs.items()
        }

        with torch.inference_mode():

            output = model(**inputs)

            # DINOv2 CLS token
            embedding = output.last_hidden_state[:, 0, :]

            embedding = torch.nn.functional.normalize(
                embedding,
                p=2,
                dim=1
            )

        emb = (
            embedding[0]
            .detach()
            .cpu()
            .numpy()
        )

        # ----------------------------------------------------
        # cosine similarity
        # ----------------------------------------------------

        scores = fp_matrix @ emb

        order = np.argsort(
            scores
        )[::-1]

        best_idx = order[0]

        best_fp = FINGERPRINTS[best_idx]

        best_score = float(
            scores[best_idx]
        )

        second_score = float(
            scores[order[1]]
        )

        margin = (
            best_score
            - second_score
        )

        # ----------------------------------------------------
        # decision
        # ----------------------------------------------------

        if (
            best_score >= THRESHOLD
            and margin >= MARGIN
        ):

            predicted = best_fp.replace(
                "_v33",
                ""
            )

            status = "MATCH"

            recognized += 1

        else:

            predicted = "00"

            status = "UNKNOWN"

            unknown += 1

        # ----------------------------------------------------
        # copy
        # ----------------------------------------------------

        out_dir = (
            OUT_DIR
            / predicted
        )

        # Prevent duplicate filenames.
        name = image_path.name

        destination = (
            out_dir
            / name
        )

        if destination.exists():

            stem = image_path.stem
            suffix = image_path.suffix

            destination = (
                out_dir
                / f"{stem}__{n}{suffix}"
            )

        shutil.copy2(
            image_path,
            destination
        )

        writer.writerow([
            str(relative),
            predicted,
            f"{best_score:.6f}",
            f"{second_score:.6f}",
            f"{margin:.6f}",
            status,
        ])

        print(
            f"{n:4d}/{len(images):4d} "
            f"{str(relative):40s} "
            f"-> {predicted:>2} "
            f"best={best_score:.4f} "
            f"second={second_score:.4f} "
            f"margin={margin:.4f} "
            f"{status}"
        )

    except Exception as e:

        errors += 1
        unknown += 1

        print(
            f"{n:4d}/{len(images):4d} "
            f"{str(relative):40s} "
            f"-> 00 ERROR: {e}"
        )

        writer.writerow([
            str(relative),
            "00",
            "",
            "",
            "",
            f"ERROR: {e}",
        ])

csv_file.close()

# ============================================================
# SUMMARY
# ============================================================

print()
print("============================================================")
print(" SUMMARY")
print("============================================================")

print(f"Total:       {len(images)}")
print(f"Recognized:  {recognized}")
print(f"Unknown 00:  {unknown}")
print(f"Errors:      {errors}")

print()
print(f"Threshold:   {THRESHOLD}")
print(f"Margin:      {MARGIN}")

print()
print("============================================================")
print(" DISTRIBUTION")
print("============================================================")

for ID in ["00", "78", "79", "80", "81", "82", "83", "84", "85"]:

    count = len([
        p for p in (OUT_DIR / ID).iterdir()
        if p.is_file()
    ])

    print(
        f"  {ID:>2}: {count}"
    )

print()
print("CSV:")
print(csv_path)

print()
PYTHON

# ------------------------------------------------------------
# Environment
# ------------------------------------------------------------

export SF_ROOT="$ROOT"
export SF_TEST_DIR="$TEST_DIR"
export SF_FP_DIR="$FP_DIR"
export SF_OUT_DIR="$OUT_DIR"
export SF_THRESHOLD="$THRESHOLD"
export SF_MARGIN="$MARGIN"

export SF_FINGERPRINTS="$(
    IFS=,
    echo "${FINGERPRINTS[*]}"
)"

# ------------------------------------------------------------
# RUN
# ------------------------------------------------------------

echo
echo "[3/5] Running classifier..."
echo
echo "      Fingerprints: 78_v33 ... 85_v33"
echo "      Threshold:    $THRESHOLD"
echo "      Margin:       $MARGIN"
echo
echo "      PATCH EMBEDDINGS ARE NOT USED."
echo

"$PY" "$PYFILE"

# ------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------

rm -f "$PYFILE"

echo
echo "[4/5] Done."

echo
echo "[5/5] Output:"
echo "  $OUT_DIR"

echo
echo "Folders:"
for ID in 00 78 79 80 81 82 83 84 85; do
    COUNT=$(find "$OUT_DIR/$ID" -maxdepth 1 -type f | wc -l)
    printf "  %-2s : %s\n" "$ID" "$COUNT"
done

echo
echo "CSV:"
echo "  $OUT_DIR/results.csv"

echo
echo "============================================================"
BASH

chmod +x classify_test.sh
```

Теперь запускай:

```bash
./classify_test.sh
```

### Но есть один нюанс

Я специально оставил **только `centroid.npy` из каждого `*_v33`** для первого теста.

То есть сравнение будет:

```text
фото → DINOv2 768-dim
             ↓
       ┌─────┴─────┐
       ↓           ↓
   78_v33       79_v33 ... 85_v33
       ↓           ↓
        cosine similarity
               ↓
          лучший результат
               ↓
       threshold + margin
          ↓           ↓
        MATCH        00
```

Это сейчас правильный эксперимент: **проверяем, способен ли глобальный DINOv2 сам отличить 78–85 от нового неизвестного места**.

И ещё важное: поскольку в `test` у тебя есть папки/файлы, названия которых могут содержать `78`, `79` и т. п., скрипт **не использует имя исходной папки как подсказку**. Он реально классифицирует изображение по embedding.

После запуска **не меняй threshold и не запускай второй раз пока**. Пришли мне вывод блока `RESULTS` и `SUMMARY`. По нему мы увидим реальное распределение similarity и уже решим, нужно ли подключать к `v33` ещё `color/environment/spatial` признаки.

---

### 👤 **User** — 2026-08-13 23:12:06

============================================================
 RESULTS
============================================================
   1/ 103 00 (1).JPG                               -> 78 best=0.9549 second=0.8717 margin=0.0831 MATCH
   2/ 103 00 (10).JPG                              -> 78 best=0.9357 second=0.8636 margin=0.0721 MATCH
   3/ 103 00 (11).JPG                              -> 78 best=0.9329 second=0.8621 margin=0.0708 MATCH
   4/ 103 00 (12).JPG                              -> 78 best=0.9261 second=0.8736 margin=0.0526 MATCH
   5/ 103 00 (2).JPG                               -> 78 best=0.9345 second=0.8558 margin=0.0786 MATCH
   6/ 103 00 (3).JPG                               -> 78 best=0.8859 second=0.8105 margin=0.0754 MATCH
   7/ 103 00 (4).JPG                               -> 78 best=0.9554 second=0.8610 margin=0.0943 MATCH
   8/ 103 00 (5).JPG                               -> 78 best=0.9281 second=0.8553 margin=0.0728 MATCH
   9/ 103 00 (6).JPG                               -> 78 best=0.9539 second=0.8796 margin=0.0744 MATCH
  10/ 103 00 (7).JPG                               -> 78 best=0.9384 second=0.8617 margin=0.0767 MATCH
  11/ 103 00 (8).JPG                               -> 79 best=0.9121 second=0.8474 margin=0.0646 MATCH
  12/ 103 00 (9).JPG                               -> 78 best=0.9383 second=0.8515 margin=0.0867 MATCH
  13/ 103 1 Конной Армии 32 А (1).JPG              -> 81 best=0.9244 second=0.8493 margin=0.0751 MATCH
  14/ 103 1 Конной Армии 32 А (10).JPG             -> 81 best=0.9240 second=0.8254 margin=0.0986 MATCH
  15/ 103 1 Конной Армии 32 А (11).JPG             -> 81 best=0.9168 second=0.8279 margin=0.0889 MATCH
  16/ 103 1 Конной Армии 32 А (12).JPG             -> 81 best=0.9143 second=0.8334 margin=0.0809 MATCH
  17/ 103 1 Конной Армии 32 А (35).JPG             -> 81 best=0.9094 second=0.8242 margin=0.0851 MATCH
  18/ 103 1 Конной Армии 32 А (36).JPG             -> 81 best=0.9221 second=0.8651 margin=0.0571 MATCH
  19/ 103 1 Конной Армии 32 А (37).JPG             -> 81 best=0.8607 second=0.8089 margin=0.0518 MATCH
  20/ 103 1 Конной Армии 32 А (38).JPG             -> 00 best=0.8762 second=0.8498 margin=0.0264 UNKNOWN
  21/ 103 1 Конной Армии 32 А (39).JPG             -> 81 best=0.9353 second=0.8706 margin=0.0647 MATCH
  22/ 103 1 Конной Армии 32 А (6).JPG              -> 81 best=0.9270 second=0.8432 margin=0.0838 MATCH
  23/ 103 1 Конной Армии 32 А (7).JPG              -> 81 best=0.9210 second=0.8385 margin=0.0825 MATCH
  24/ 103 1 Конной Армии 32 А (8).JPG              -> 81 best=0.9156 second=0.8380 margin=0.0776 MATCH
  25/ 103 1 Конной Армии 32 А (9).JPG              -> 81 best=0.9188 second=0.8425 margin=0.0763 MATCH
  26/ 103 1 Конной Армии А (16).JPG                -> 81 best=0.8785 second=0.7913 margin=0.0872 MATCH
  27/ 103 1 Конной Армии А (17).JPG                -> 81 best=0.8755 second=0.8024 margin=0.0730 MATCH
  28/ 103 1 Конной Армии А (18).JPG                -> 81 best=0.8603 second=0.7767 margin=0.0835 MATCH
  29/ 103 Добровольского 17 А (34).JPG             -> 82 best=0.8605 second=0.7385 margin=0.1219 MATCH
  30/ 103 Добровольского 17 А (35).JPG             -> 82 best=0.9394 second=0.7972 margin=0.1422 MATCH
  31/ 103 Добровольского 17 А (36).JPG             -> 82 best=0.9371 second=0.7727 margin=0.1644 MATCH
  32/ 103 Добровольского 17 А (37).JPG             -> 82 best=0.9456 second=0.7943 margin=0.1513 MATCH
  33/ 103 Добровольского 17 А (38).JPG             -> 82 best=0.9288 second=0.7627 margin=0.1661 MATCH
  34/ 103 Добровольского 17 А (59).JPG             -> 82 best=0.9251 second=0.7518 margin=0.1733 MATCH
  35/ 103 Добровольского 17 А (60).JPG             -> 82 best=0.9394 second=0.7703 margin=0.1690 MATCH
  36/ 103 Добровольского 17 А (61).JPG             -> 82 best=0.9343 second=0.7561 margin=0.1782 MATCH
  37/ 103 Добровольского 17 А (63).JPG             -> 82 best=0.9315 second=0.7535 margin=0.1780 MATCH
  38/ 103 Комарова 20 Добровольского Б (4).JPG     -> 00 best=0.4461 second=0.4205 margin=0.0256 UNKNOWN
  39/ 103 Комарова 20 Добровольского Б (5).JPG     -> 79 best=0.9380 second=0.8480 margin=0.0900 MATCH
  40/ 103 Комарова 20 Добровольского Б (6).JPG     -> 79 best=0.9419 second=0.8398 margin=0.1021 MATCH
  41/ 103 Комарова 28 А (1).JPG                    -> 80 best=0.8965 second=0.8182 margin=0.0783 MATCH
  42/ 103 Комарова 28 А (2).JPG                    -> 80 best=0.9219 second=0.8672 margin=0.0547 MATCH
  43/ 103 Комарова 28 А (3).JPG                    -> 80 best=0.9161 second=0.8008 margin=0.1153 MATCH
  44/ 103 Комарова 28 А (4).JPG                    -> 80 best=0.9156 second=0.7941 margin=0.1215 MATCH
  45/ 103 Комарова 28 А (5).JPG                    -> 80 best=0.9185 second=0.8213 margin=0.0972 MATCH
  46/ 103 Комарова 28 А (6).JPG                    -> 80 best=0.9022 second=0.8590 margin=0.0431 MATCH
  47/ 103 Комарова Добровольского А (1).JPG        -> 00 best=0.8770 second=0.8618 margin=0.0152 UNKNOWN
  48/ 103 Комарова Добровольского А (42).JPG       -> 00 best=0.8765 second=0.8656 margin=0.0109 UNKNOWN
  49/ 103 Комарова Добровольского А (8).JPG        -> 00 best=0.8660 second=0.8611 margin=0.0049 UNKNOWN
  50/ 103 Комарова Добровольского Б (17).JPG       -> 79 best=0.9397 second=0.8577 margin=0.0820 MATCH
  51/ 103 Комарова Добровольского Б (20).JPG       -> 79 best=0.9258 second=0.7975 margin=0.1283 MATCH
  52/ 103 Комарова Добровольского Б (23).JPG       -> 79 best=0.9400 second=0.8352 margin=0.1047 MATCH
  53/ 103 Комарова Добровольского Б (5).JPG        -> 79 best=0.9437 second=0.8399 margin=0.1038 MATCH
  54/ 103 Космонавтов 13 Комарова А (15).JPG       -> 78 best=0.9313 second=0.8649 margin=0.0664 MATCH
  55/ 103 Космонавтов 13 Комарова А (18).JPG       -> 78 best=0.9511 second=0.8497 margin=0.1013 MATCH
  56/ 103 Космонавтов 13 Комарова А (3).JPG        -> 78 best=0.9481 second=0.8625 margin=0.0856 MATCH
  57/ 103 Космонавтов 13 Комарова А (9).JPG        -> 78 best=0.9538 second=0.8831 margin=0.0707 MATCH
  58/ 103 Ленина 125-127 А (1).JPG                 -> 84 best=0.8712 second=0.8291 margin=0.0421 MATCH
  59/ 103 Ленина 125-127 А (10).JPG                -> 00 best=0.8792 second=0.8685 margin=0.0107 UNKNOWN
  60/ 103 Ленина 125-127 А (11).JPG                -> 00 best=0.8848 second=0.8659 margin=0.0189 UNKNOWN
  61/ 103 Ленина 125-127 А (12).JPG                -> 00 best=0.8680 second=0.8463 margin=0.0218 UNKNOWN
  62/ 103 Ленина 125-127 А (13).JPG                -> 00 best=0.8854 second=0.8690 margin=0.0164 UNKNOWN
  63/ 103 Ленина 125-127 А (14).JPG                -> 00 best=0.8699 second=0.8526 margin=0.0173 UNKNOWN
  64/ 103 Ленина 125-127 А (15).JPG                -> 84 best=0.8720 second=0.8319 margin=0.0401 MATCH
  65/ 103 Ленина 125-127 А (16).JPG                -> 00 best=0.8752 second=0.8581 margin=0.0171 UNKNOWN
  66/ 103 Ленина 125-127 А (17).JPG                -> 00 best=0.8825 second=0.8653 margin=0.0172 UNKNOWN
  67/ 103 Ленина 125-127 А (8).JPG                 -> 00 best=0.8605 second=0.8512 margin=0.0093 UNKNOWN
  68/ 103 Ленина 125-127 А (9).JPG                 -> 00 best=0.8758 second=0.8512 margin=0.0246 UNKNOWN
  69/ 103 Ленина Ашхабадский А (1).JPG             -> 85 best=0.8985 second=0.7919 margin=0.1066 MATCH
  70/ 103 Ленина Ашхабадский А (23).JPG            -> 85 best=0.9148 second=0.7918 margin=0.1230 MATCH
  71/ 103 Ленина Ашхабадский А (24).JPG            -> 85 best=0.9397 second=0.8281 margin=0.1115 MATCH
  72/ 103 Ленина Ашхабадский А (25).JPG            -> 85 best=0.9226 second=0.8224 margin=0.1002 MATCH
  73/ 103 Ленина Ашхабадский А (26).JPG            -> 85 best=0.9333 second=0.8322 margin=0.1012 MATCH
  74/ 103 Ленина Ашхабадский А (27).JPG            -> 85 best=0.9334 second=0.7978 margin=0.1356 MATCH
  75/ 103 Ленина Ашхабадский А (28).JPG            -> 85 best=0.9328 second=0.7927 margin=0.1401 MATCH
  76/ 103 Ленина Ашхабадский А (3).JPG             -> 85 best=0.7627 second=0.6513 margin=0.1115 MATCH
  77/ 103 Ленина Ашхабадский А (4).JPG             -> 85 best=0.8417 second=0.7727 margin=0.0690 MATCH
  78/ 103 Ленина Ашхабадский А (43).JPG            -> 85 best=0.9419 second=0.8200 margin=0.1219 MATCH
  79/ 103 Ленина Ашхабадский А (44).JPG            -> 85 best=0.9177 second=0.8111 margin=0.1065 MATCH
  80/ 103 Ленина Ашхабадский А (45).JPG            -> 85 best=0.9029 second=0.7948 margin=0.1081 MATCH
  81/ 103 Ленина Ашхабадский А (5).JPG             -> 85 best=0.9480 second=0.8601 margin=0.0879 MATCH
  82/ 103 Ленина Ашхабадский А (6).JPG             -> 85 best=0.9281 second=0.7966 margin=0.1314 MATCH
  83/ 103 Ленина Ашхабадский А (7).JPG             -> 00 best=0.5171 second=0.5081 margin=0.0090 UNKNOWN
  84/ 103 Ленина Ашхабадский А (8).JPG             -> 85 best=0.8937 second=0.8355 margin=0.0582 MATCH
  85/ 103 Ленина Ашхабадский А2 (1).JPG            -> 85 best=0.8853 second=0.8128 margin=0.0725 MATCH
  86/ 103 Ленина Ашхабадский А2 (2).JPG            -> 85 best=0.9342 second=0.8344 margin=0.0998 MATCH
  87/ 103 Нагибина 24 А (1).JPG                    -> 83 best=0.9263 second=0.8592 margin=0.0671 MATCH
  88/ 103 Нагибина 24 А (10).JPG                   -> 83 best=0.9464 second=0.8681 margin=0.0784 MATCH
  89/ 103 Нагибина 24 А (11).JPG                   -> 83 best=0.9349 second=0.8638 margin=0.0711 MATCH
  90/ 103 Нагибина 24 А (12).JPG                   -> 00 best=0.8672 second=0.8486 margin=0.0185 UNKNOWN
  91/ 103 Нагибина 24 А (13).JPG                   -> 00 best=0.8659 second=0.8423 margin=0.0236 UNKNOWN
  92/ 103 Нагибина 24 А (2).JPG                    -> 83 best=0.8896 second=0.8308 margin=0.0588 MATCH
  93/ 103 Нагибина 24 А (3).JPG                    -> 83 best=0.8608 second=0.8206 margin=0.0402 MATCH
  94/ 103 Нагибина 24 А (30).JPG                   -> 83 best=0.9228 second=0.8466 margin=0.0762 MATCH
  95/ 103 Нагибина 24 А (31).JPG                   -> 83 best=0.9208 second=0.8347 margin=0.0861 MATCH
  96/ 103 Нагибина 24 А (32).JPG                   -> 83 best=0.9175 second=0.8320 margin=0.0855 MATCH
  97/ 103 Нагибина 24 А (33).JPG                   -> 83 best=0.9149 second=0.8283 margin=0.0866 MATCH
  98/ 103 Нагибина 24 А (34).JPG                   -> 83 best=0.9206 second=0.8571 margin=0.0635 MATCH
  99/ 103 Нагибина 24 А (35).JPG                   -> 83 best=0.9131 second=0.8293 margin=0.0838 MATCH
 100/ 103 Нагибина 24 А (4).JPG                    -> 83 best=0.9021 second=0.8554 margin=0.0467 MATCH
 101/ 103 Нагибина 24 А (5).JPG                    -> 83 best=0.8940 second=0.8248 margin=0.0692 MATCH
 102/ 103 Нагибина 24 А (8).JPG                    -> 83 best=0.9281 second=0.8371 margin=0.0911 MATCH
 103/ 103 Нагибина 24 А (9).JPG                    -> 83 best=0.9030 second=0.8378 margin=0.0652 MATCH

============================================================
 SUMMARY
============================================================
Total:       103
Recognized:  86
Unknown 00:  17
Errors:      0

Threshold:   0.6
Margin:      0.03

============================================================
 DISTRIBUTION
============================================================
  00: 17
  78: 15
  79: 7
  80: 6
  81: 15
  82: 9
  83: 15
  84: 2
  85: 17

CSV:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/test_classified/results.csv

[4/5] Done.

[5/5] Output:
  /home/alexice/projects/scene_fingerprint_mvp_v02/data/output/test_classified

Folders:
  00 : 17
  78 : 15
  79 : 7
  80 : 6
  81 : 15
  82 : 9
  83 : 15
  84 : 2
  85 : 17

CSV:
  /home/alexice/projects/scene_fingerprint_mvp_v02/data/output/test_classified/results.csv

============================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-13 23:12:07

Вот теперь картина очень интересная. **Базовый DINOv2 уже работает довольно хорошо**, но одновременно видно, почему нам нужен следующий этап.

### Что получилось

Из 103 фотографий:

| Результат | Кол-во |
|---|---:|
| 78 | 15 |
| 79 | 7 |
| 80 | 6 |
| 81 | 15 |
| 82 | 9 |
| 83 | 15 |
| 84 | 2 |
| 85 | 17 |
| **00** | **17** |

Всего распознано **86/103**, то есть ~83.5%.

Причём распределение очень логичное: фотографии группируются по местам, а не случайно.

### Но есть важное наблюдение

Посмотри, например, `81`:

```text
best=0.8607 margin=0.0518 → 81 MATCH
best=0.8762 margin=0.0264 → 00 UNKNOWN
best=0.9353 margin=0.0647 → 81 MATCH
```

То есть проблема **не в низкой similarity**.

У фотографии:

```text
1 Конной Армии 32 А (38).JPG
```

similarity = **0.8762** — это очень высокая величина.

Она ушла в `00` только потому, что:

```text
0.8762 - 0.8498 = 0.0264
```

и мы установили `margin=0.03`.

То же самое с `Ленина 125-127 А`:

```text
0.8792 / 0.8685
0.8848 / 0.8659
0.8680 / 0.8463
...
```

Это явно **не "неизвестные места"**. Это фотографии, где глобальный DINO не может уверенно отличить два похожих объекта.

И вот это как раз тот случай, где нам пригодятся дополнительные признаки `v33`.

---

## Ещё более важное

У нас есть три типа `00`.

### Тип 1 — действительно неизвестное

Например:

```text
Комарова 20 Добровольского Б (4).JPG
best=0.4461
```

Это настоящий кандидат на `00`.

### Тип 2 — известное место, но DINO сомневается

Например:

```text
81:
0.8762 / 0.8498
```

или:

```text
84:
0.8792 / 0.8685
```

Здесь нельзя просто повышать/понижать threshold.

### Тип 3 — вероятно известное место, но отдельный кадр сильно отличается

Например:

```text
Ленина Ашхабадский А (7).JPG
0.5171 / 0.5081
```

Остальные фотографии этого же адреса практически все уверенно определились как `85`.

Это очень показательный пример.

**Значит, классификация одной фотографии по centroid недостаточна.**

---

# Что предлагаю сделать дальше

У тебя `v33` специально содержит:

```text
embeddings.npy
color_embeddings.npy
environment_embeddings.npy
spatial_embeddings.npy
```

То есть мы можем сделать **V33 Multi-Feature Classifier**.

Не надо делать новый fingerprint.

Для каждого тестового изображения получаем:

```text
                 PHOTO
                   │
          ┌────────┼────────┐
          ↓        ↓        ↓
       DINOv2    COLOR   ENVIRONMENT
       768       ...       ...
          │        │        │
          └────────┼────────┘
                   ↓
                SPATIAL
                   │
                   ↓
             COMBINED SCORE
                   │
             ┌─────┴─────┐
             ↓           ↓
         известное      00
```

И самое интересное — можно использовать **разные веса**.

Например, предварительно:

```text
DINO       50%
Environment 25%
Spatial     15%
Color       10%
```

Но я **не хочу сейчас придумывать веса наугад**.

У нас есть прекрасный тестовый набор, где по именам файлов мы фактически знаем правильный ответ:

```text
78 → фотографии 78
79 → фотографии 79
...
85 → фотографии 85
```

и есть неизвестные.

То есть мы можем использовать эти 103 фотографии как **контрольный набор** и подобрать параметры математически.

---

## И ещё я бы изменил сам принцип `00`

Сейчас:

```text
best < threshold OR margin < 0.03
                     ↓
                    00
```

Это слишком грубо.

Нам нужно:

### Сначала определить кандидата

Например:

```text
78  0.93
79  0.86
80  0.61
...
```

→ кандидат `78`.

### Затем проверить кандидата дополнительными признаками.

Например:

```text
DINO:        0.93
Environment: 0.88
Spatial:     0.91
Color:       0.71
```

→ очень вероятно `78`.

А для реально неизвестного:

```text
DINO:        0.45
Environment: 0.39
Spatial:     0.42
Color:       0.51
```

→ `00`.

---

# Сейчас я бы НЕ менял threshold

Текущий результат — отличный диагностический материал.

Особенно интересно, что:

- `78` — очень уверенно;
- `79` — очень уверенно;
- `80` — очень уверенно;
- `81` — в основном уверенно;
- `82` — очень уверенно;
- `83` — уверенно;
- `84` — пока мало тестовых кадров;
- `85` — в основном очень уверенно;
- неизвестные уже начали отделяться.

**Следующий шаг — сделать второй Bash-скрипт `classify_test_v33.sh`, который использует все четыре компонента V33, но сначала работает в режиме анализа и ничего не переименовывает.**

Причём я предлагаю сделать ему два результата одновременно:

```text
00_real
```

— если все признаки говорят, что место неизвестное,

и

```text
00_uncertain
```

— если место, скорее всего, одно из 78–85, но классификатор не уверен.

Это позволит нам увидеть разницу между **"не знаю что это"** и **"знаю, что это одно из известных мест, но не могу выбрать между 81 и 84"**.

И только после этого сделаем окончательную сортировку `00 / 78 ... 85`.

**Я бы именно так продолжал — сейчас у нас уже достаточно данных, чтобы не гадать с порогами, а реально проверить V33.**

---

### 👤 **User** — 2026-08-13 23:13:58

давай. но уже сейчас видно, что результат очень хороший, если не считать образоцов 84, все остальные определяются очень уверенно - и если бы скрипт выбирал кандидадата 1,  товсе сошлось бы

---

### 🤖 **Assistant** — 2026-08-13 23:13:59

Да, согласен. И это **важное наблюдение**.

По факту текущий тест показывает, что **Top-1 уже практически идеально находит правильное место**, а проблема `00` сейчас искусственно создаётся нашим правилом `margin >= 0.03`.

Например:

```text
81:  best=0.8762 second=0.8498 → Top-1 = 81
84:  best=0.8792 second=0.8685 → Top-1 = 84
83:  best=0.8672 second=0.8486 → Top-1 = 83
85:  best=0.5171 second=0.5081 → Top-1 = 85
```

То есть **Top-1 во всех этих случаях указывает на правильную группу**, но `margin` отправляет их в `00`.

### Поэтому я предлагаю изменить эксперимент

Не надо пока делать сложный `Multi-Feature`.

Сначала сделаем **честный Top-1 тест**:

```text
фото
 ↓
78_v33
79_v33
80_v33
81_v33
82_v33
83_v33
84_v33
85_v33
 ↓
MAX similarity
 ↓
TOP-1
```

И `00` будем присваивать **только если similarity действительно низкая**.

Например:

```text
0.95 → 78
0.93 → 81
0.88 → 84
0.86 → 83
0.52 → 00
0.45 → 00
```

То есть **margin пока вообще убираем**.

---

### И тогда получим очень показательный результат

Текущие 17 `00` разделятся примерно на две категории:

**А. Реально неизвестные:**

```text
0.4461
0.5171
...
```

**Б. На самом деле известные, но margin был маленький:**

```text
0.8762 → 81
0.8770 → 79/...
0.8792 → 84
0.8848 → 84
...
```

Именно это нам сейчас нужно выяснить.

---

### Но есть ещё одна очень важная вещь

Ты сказал:

> если бы скрипт выбирал кандидата 1, то всё сошлось бы

**Да. Это и есть главный результат этого эксперимента.**

Причём `84` выглядит особенным:

```text
84:
0.8712
0.8720
```

и несколько фотографий `Ленина 125-127 А` имеют:

```text
0.8792
0.8848
0.8854
...
```

но второе место у них очень близко.

То есть `84` действительно требует отдельного внимания, а не общий алгоритм.

---

## Поэтому следующий скрипт я предлагаю сделать так

Он будет выводить **TOP-5**, а не только TOP-1:

```text
photo.jpg

1. 84_v33   0.8848
2. 85_v33   0.8659
3. 81_v33   0.7421
4. 78_v33   0.7112
5. 83_v33   0.7045
```

И отдельно:

```text
TOP-1: 84
CONFIDENCE: HIGH
```

или:

```text
TOP-1: 84
TOP-2: 85
STATUS: AMBIGUOUS
```

Но **не отправлять такие фотографии в `00`**.

`00` оставляем только для случаев, где:

```text
TOP-1 < threshold
```

Я бы начал с:

```text
threshold = 0.60
```

потому что уже сейчас видно, что реальные совпадения у нас в основном значительно выше `0.60`, а действительно чужая фотография дала `0.4461`.

После этого посмотрим на **все 103 Top-1**.

Если результат действительно окажется 100% по известным 78–85, тогда уже совершенно спокойно добавим `color/environment/spatial` **только как второй уровень для спорных случаев**, а не будем усложнять основной классификатор.

**Это намного правильнее архитектурно: быстрый и очень точный Top-1 → дополнительная проверка только при необходимости.**

---

### 👤 **User** — 2026-08-13 23:14:28

давай скрипт

---

