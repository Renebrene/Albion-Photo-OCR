## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 🤖 **Assistant** — 2026-08-15 03:18:19

Да. Если я правильно понял, нужно в `data/input/78`, `79`, … `95` переименовать файлы так, чтобы **номер папки стал основой имени**, например:

```text
data/input/78/
    78_001.JPG
    78_002.JPG
    78_003.JPG
    ...

data/input/79/
    79_001.JPG
    79_002.JPG
    79_003.JPG
    ...
```

При этом **расширение сохраняем**, а порядок берём по текущему имени файла.

Сначала безопасно посмотрим, что получится, **ничего не переименовывая**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

for n in range(78, 96):
    folder = Path("data/input") / str(n)

    files = sorted(
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )

    print(f"\n=== {n} ({len(files)} files) ===")

    for i, p in enumerate(files[:5], 1):
        print(f"{p.name}  ->  {n}_{i:03d}{p.suffix}")

    if len(files) > 5:
        print("...")
        for i, p in list(enumerate(files, 1))[-2:]:
            print(f"{p.name}  ->  {n}_{i:03d}{p.suffix}")
PY
```

Если вывод правильный, переименование лучше делать через **временные имена**, чтобы исключить столкновения имён:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

for n in range(78, 96):
    folder = Path("data/input") / str(n)

    files = sorted(
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )

    print(f"{n}: {len(files)} files")

    # Шаг 1 — временные имена
    temp_files = []

    for i, p in enumerate(files, 1):
        temp = folder / f".__rename_{n}_{i:05d}{p.suffix}"
        p.rename(temp)
        temp_files.append((temp, i))

    # Шаг 2 — окончательные имена
    for temp, i in temp_files:
        target = folder / f"{n}_{i:03d}{temp.suffix}"
        temp.rename(target)

print()
print("DONE")
PY
```

После этого проверим:

```bash
for n in {78..95}; do
    echo -n "$n: "
    find "data/input/$n" -maxdepth 1 -type f \
      \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
      | wc -l
done
```

Это **не меняет содержимое фотографий**, только имена файлов. И это удобно для следующего чистого создания слепков: `78_v33` будет содержать изображения `78_001`, `78_002`, и т.д., а `best_image` потом станет гораздо понятнее.

---

### 👤 **User** — 2026-08-15 03:22:22

где Щutput

---

### 🤖 **Assistant** — 2026-08-15 03:22:22

Если ты имеешь в виду **`output`**, то сейчас он находится здесь:

```bash
~/projects/scene_fingerprint_mvp_v02/data/output/
```

А для нашего теста сортировки использовалась папка:

```bash
~/projects/scene_fingerprint_mvp_v02/data/output/test_classified/
```

Если её ещё нет:

```bash
mkdir -p ~/projects/scene_fingerprint_mvp_v02/data/output/test_classified
```

После распознавания туда будем раскладывать:

```text
data/output/test_classified/
├── 78_v33/
├── 79_v33/
├── 80_v33/
...
├── 95_v33/
└── NO_CANDIDATE/
```

Если ты спрашивал **где именно должен быть `output` для текущего полного прогона**, то да — будем использовать `data/output/test_classified`.

---

### 👤 **User** — 2026-08-15 03:25:51

ТАМ ПУСТО

---

### 🤖 **Assistant** — 2026-08-15 03:25:51

Да, всё нормально — **пока там пусто**, потому что мы ещё не запускали этап **раскладывания распознанных фотографий по папкам**.

Сейчас у нас есть:

```text
data/input/78 ... 95     ← исходные фотографии
data/input/test          ← 262 тестовых фото
data/fingerprints/       ← слепки
final_test_78_95.json    ← результаты распознавания
```

А вот:

```text
data/output/test_classified/
```

пока **не заполнен**.

Причём предлагаю сейчас не делать лишних движений. Сначала:

### 1. Переименовываем исходники 78–95

В формат:

```text
78_001.JPG
78_002.JPG
...
95_001.JPG
95_002.JPG
```

### 2. Пересоздаём слепки

```text
78_v33
79_v33
...
95_v33
```

### 3. Запускаем распознавание `test`

Получаем новый JSON.

### 4. Раскладываем 262 фотографии

И вот **тогда**:

```text
data/output/test_classified/
├── 78_v33/
├── 79_v33/
├── ...
└── 95_v33/
```

То есть **пустой `output` сейчас — ожидаемо**.

Если хочешь, можем прямо сейчас сделать **одним безопасным скриптом весь цикл: переименование → новые слепки → распознавание → раскладка в `output`**.

---

### 👤 **User** — 2026-08-15 03:26:12

ДАВАЙ

---

### 🤖 **Assistant** — 2026-08-15 03:26:12

Да. Сделаем **полный прогон с нуля**, но старые результаты и старые слепки не уничтожаем.

Скрипт сделает:

1. Переименует фото `78–95` в `78_001.JPG`, `78_002.JPG` и т.д.
2. Старые `*_v33` перенесёт в резервную папку.
3. Создаст новые `*_v33`.
4. Проверит все 18 слепков.
5. Распознает `data/input/test` — 262 фото.
6. Сохранит JSON.
7. **Реально разложит фотографии в `data/output/test_classified/` по TOP-1.**

### Запускай целиком

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/full_clean_pipeline.sh <<'BASH'
#!/usr/bin/env bash
set -e

ROOT="$HOME/projects/scene_fingerprint_mvp_v02"
cd "$ROOT"

echo
echo "============================================================"
echo "  FULL CLEAN PIPELINE"
echo "============================================================"

# ============================================================
# 1. RENAME INPUT FILES
# ============================================================

echo
echo "============================================================"
echo "1. RENAME INPUT FILES 78-95"
echo "============================================================"

python3 - <<'PY'
from pathlib import Path

extensions = {".jpg", ".jpeg", ".png", ".webp"}

for n in range(78, 96):
    folder = Path("data/input") / str(n)

    files = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in extensions
    )

    print(f"{n}: {len(files)} images")

    # Проверяем, не переименованы ли уже
    expected = [
        folder / f"{n}_{i:03d}{p.suffix}"
        for i, p in enumerate(files, 1)
    ]

    already = all(
        p.name.startswith(f"{n}_")
        for p in files
    )

    if already:
        print("  already numbered -> skip")
        continue

    # Временные имена
    temp = []

    for i, p in enumerate(files, 1):
        t = folder / f".__tmp_{n}_{i:05d}{p.suffix}"
        p.rename(t)
        temp.append((t, i))

    # Финальные имена
    for t, i in temp:
        target = folder / f"{n}_{i:03d}{t.suffix}"
        t.rename(target)

print()
print("INPUT RENAME DONE")
PY

# ============================================================
# 2. BACKUP OLD V33
# ============================================================

echo
echo "============================================================"
echo "2. BACKUP OLD V33 FINGERPRINTS"
echo "============================================================"

BACKUP="fingerprints_backup_before_clean_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP"

for n in {78..95}; do
    if [ -d "data/fingerprints/${n}_v33" ]; then
        echo "backup ${n}_v33"
        mv "data/fingerprints/${n}_v33" "$BACKUP/"
    fi
done

echo
echo "Backup created:"
echo "$BACKUP"

# ============================================================
# 3. CREATE NEW FINGERPRINTS
# ============================================================

echo
echo "============================================================"
echo "3. CREATE FRESH V33 FINGERPRINTS"
echo "============================================================"

for n in {78..95}; do

    echo
    echo "------------------------------------------------------------"
    echo "CREATING ${n}_v33"
    echo "------------------------------------------------------------"

    uv run scene-fingerprint create \
        "${n}_v33" \
        "data/input/${n}"

done

# ============================================================
# 4. VERIFY FINGERPRINTS
# ============================================================

echo
echo "============================================================"
echo "4. VERIFY FINGERPRINTS"
echo "============================================================"

for n in {78..95}; do

    DIR="data/fingerprints/${n}_v33"

    if [ ! -f "$DIR/embeddings.npy" ]; then
        echo "ERROR: ${n}_v33 embeddings.npy missing"
        exit 1
    fi

    if [ ! -f "$DIR/centroid.npy" ]; then
        echo "ERROR: ${n}_v33 centroid.npy missing"
        exit 1
    fi

    if [ ! -f "$DIR/metadata.json" ]; then
        echo "ERROR: ${n}_v33 metadata.json missing"
        exit 1
    fi

    echo "OK ${n}_v33"
done

# ============================================================
# 5. CLEAN OUTPUT
# ============================================================

echo
echo "============================================================"
echo "5. PREPARE OUTPUT"
echo "============================================================"

OUTPUT="data/output/test_classified"

rm -rf "$OUTPUT"
mkdir -p "$OUTPUT"

echo "Output:"
echo "$OUTPUT"

# ============================================================
# 6. RECOGNITION
# ============================================================

echo
echo "============================================================"
echo "6. RECOGNIZE TEST"
echo "============================================================"

RESULT="final_test_78_95_clean.json"

rm -f "$RESULT"

uv run scene-fingerprint recognize \
    data/input/test \
    --top-k 5 \
    --threshold 0.65 \
    > "$RESULT"

echo
echo "Recognition result:"
ls -lh "$RESULT"

# ============================================================
# 7. SORT TEST IMAGES BY TOP-1
# ============================================================

echo
echo "============================================================"
echo "7. SORT TEST IMAGES BY TOP-1"
echo "============================================================"

python3 - <<'PY'
from pathlib import Path
import json
import shutil

RESULT = Path("final_test_78_95_clean.json")
SOURCE = Path("data/input/test")
OUTPUT = Path("data/output/test_classified")

lines = RESULT.read_text(encoding="utf-8").splitlines()

start = None

for i, line in enumerate(lines):
    if line.strip() == "[":
        start = i
        break

if start is None:
    raise RuntimeError("JSON array not found")

data = json.loads("\n".join(lines[start:]))

print(f"Results loaded: {len(data)}")

counts = {}
no_candidate = 0

for r in data:

    file_path = Path(r["file"])
    filename = file_path.name

    best_id = r.get("best_id")

    # TOP-1 fallback
    if not best_id:
        candidates = r.get("candidates", [])

        if candidates:
            best_id = candidates[0].get("id")

    if not best_id:
        folder_name = "NO_CANDIDATE"
        no_candidate += 1
    else:
        folder_name = str(best_id)

    destination_dir = OUTPUT / folder_name
    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_file = SOURCE / filename

    if not source_file.exists():
        if file_path.exists():
            source_file = file_path
        else:
            print(f"[WARNING] Source not found: {filename}")
            continue

    destination_file = destination_dir / filename

    if destination_file.exists():

        stem = destination_file.stem
        suffix = destination_file.suffix

        n = 2

        while True:

            candidate = destination_dir / (
                f"{stem}__{n}{suffix}"
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
        counts.get(folder_name, 0) + 1
    )

# ============================================================
# REPORT
# ============================================================

print()
print("=" * 70)
print("FINAL TOP-1 CLASSIFICATION")
print("=" * 70)

total = 0

def sort_key(x):
    digits = "".join(c for c in x if c.isdigit())
    return int(digits) if digits else 9999

for name in sorted(counts, key=sort_key):

    count = counts[name]
    total += count

    print(f"{name:20} {count:4}")

print("-" * 70)
print(f"{'TOTAL COPIED':20} {total:4}")
print(f"{'NO CANDIDATE':20} {no_candidate:4}")
print("=" * 70)

print()
print(f"OUTPUT: {OUTPUT}")
PY

# ============================================================
# 8. FINAL CHECK
# ============================================================

echo
echo "============================================================"
echo "8. FINAL OUTPUT CHECK"
echo "============================================================"

echo
echo "Folders:"
find data/output/test_classified \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    | sort

echo
echo "Files per folder:"

for d in data/output/test_classified/*; do
    [ -d "$d" ] || continue

    printf "%-30s " "$(basename "$d")"

    find "$d" -maxdepth 1 -type f \
        \( -iname "*.jpg" -o -iname "*.jpeg" \
           -o -iname "*.png" -o -iname "*.webp" \) \
        | wc -l
done

echo
echo "============================================================"
echo "PIPELINE COMPLETE"
echo "============================================================"

echo
echo "RESULT JSON:"
echo "  $ROOT/final_test_78_95_clean.json"

echo
echo "CLASSIFIED OUTPUT:"
echo "  $ROOT/data/output/test_classified"

echo
echo "OLD FINGERPRINT BACKUP:"
echo "  $ROOT/$BACKUP"
BASH

chmod +x /tmp/full_clean_pipeline.sh

/tmp/full_clean_pipeline.sh
```

### Что должно получиться

В конце ожидаем примерно такую структуру:

```text
data/output/test_classified/

78_v33/
79_v33/
80_v33/
81_v33/
82_v33/
83_v33/
84_v33/
85_v33/
86_v33/
87_v33/
88_v33/
89_v33/
90_v33/
91_v33/
92_v33/
93_v33/
94_v33/
95_v33/
```

И суммарно должно быть **262 файла**.

При этом экспериментальные:

```text
84_v34_test
84_v35_test
```

**не участвуют и не удаляются**.

А старые `78_v33 ... 95_v33` будут лежать в каталоге вида:

```text
fingerprints_backup_before_clean_20260815_...
```

После завершения **пришли последние ~100 строк вывода**, особенно блок `FINAL TOP-1 CLASSIFICATION`. Тогда сравним новый чистый прогон с предыдущими `262` и убедимся, что пересоздание слепков дало тот же результат.

---

### 👤 **User** — 2026-08-15 03:27:43

повышение embediing dimension на что нибудь повлияет

---

### 🤖 **Assistant** — 2026-08-15 03:27:43

Да, **может повлиять очень сильно**, но зависит от того, что именно мы называем повышением embedding dimension.

В нашем текущем проекте DINOv2 даёт:

```text
embedding dimension = 768
```

### Если просто увеличить 768 → например 1024

Нельзя просто «растянуть» существующий вектор 768 → 1024 и ожидать улучшения. Это не даст новой информации.

Чтобы получить реально более размерный embedding, нужно использовать другую модель/архитектуру или извлекать дополнительные признаки.

### Что даст большее embedding dimension

Потенциально:

- больше информации о мелких различиях между сценами;
- лучше разделение **очень похожих адресов**;
- меньше вероятность, что два похожих пейзажа получат почти одинаковый вектор;
- потенциально лучше TOP-1 для сложных случаев вроде твоих `89/90`.

Но есть цена:

| | 768 | больше |
|---|---:|---:|
| Информация | хорошая | потенциально больше |
| Различение похожих сцен | хорошее | может улучшиться |
| RAM/VRAM | ниже | выше |
| Размер слепков | меньше | больше |
| Скорость | выше | ниже |
| Требования к базе | ниже | выше |
| Гарантированное улучшение | — | **нет** |

### Важнее другое

В нашем случае я бы **пока не трогал 768**.

У нас уже есть очень хороший результат:

```text
262 фото
18 кандидатов
высокие score ~0.93–0.95
```

И главное — мы видим, что DINO уже достаточно хорошо различает адреса.

Например:

```text
78:
global 0.9549
environment 0.9361
color 0.8892
spatial 0.9870
FINAL 0.9475
```

То есть проблема сейчас не выглядит как **«embedding слишком маленький»**.

---

### Есть более интересный путь

У нас DINOv2 `base`:

```text
ViT-B/14
768 dimensions
```

Можно перейти, например, на более крупный DINOv2:

```text
ViT-L/14
1024 dimensions
```

или другой более мощный вариант.

Но это уже **другая модель**, поэтому придётся:

```text
новая модель
    ↓
новые embeddings
    ↓
новые fingerprints
    ↓
новое распознавание
```

И сравнить:

```text
DINO-B/14 768
        VS
DINO-L/14 1024
```

Причём на **одних и тех же 262 тестовых фотографиях**.

Тогда мы реально увидим, стало ли лучше.

**Но я бы сначала закончил текущий чистый прогон.** У нас сейчас есть очень хорошая контрольная точка v3.3/768. После неё можно сделать эксперимент с 1024, не ломая рабочую систему.

---

### 👤 **User** — 2026-08-15 03:30:37

ViT-B/14  ViT-L/14 разница в ресурсоемкости

---

### 🤖 **Assistant** — 2026-08-15 03:30:38

Да. Для твоей **RTX 3060 12 GB** разница между DINOv2 **ViT-B/14** и **ViT-L/14** будет заметной.

| | ViT-B/14 | ViT-L/14 |
|---|---:|---:|
| Embedding | **768** | **1024** |
| Параметры | ~86M | ~304M |
| Размер модели | ~350 MB | ~1.2 GB |
| Вычисления | 1× | примерно **3–4×** |
| VRAM | комфортно | заметно выше |
| Скорость | высокая | существенно медленнее |
| Качество признаков | очень хорошее | выше |
| RTX 3060 12 GB | ✅ | ⚠️ возможно, но с ограничениями |

### Для нашего пайплайна

Здесь есть важный нюанс: фотографии у тебя примерно **3500×2500**, но DINO не обрабатывает весь оригинал как огромный тензор. Поэтому основная нагрузка определяется размером входа модели и количеством изображений в batch.

У нас сейчас:

```text
RTX 3060
11.6 GB VRAM

DINOv2 ViT-B/14
768
```

работает нормально.

`ViT-L/14` имеет примерно **в 3.5 раза больше параметров**:

```text
B:  ~86 млн
L: ~304 млн
```

Поэтому:

**VRAM:** существенно больше  
**скорость:** существенно ниже  
**диск:** больше  
**batch size:** скорее всего придётся уменьшить.

---

### Но я бы не переходил на L сразу

Для нашего конкретного проекта есть более интересный эксперимент.

Сейчас мы используем:

```text
ViT-B/14
768-d global embedding
```

и уже получили очень хорошие результаты.

Если проблема:

```text
89 ≈ 90
```

то переход на L может помочь, **но совсем не обязательно**.

Причина в том, что у нас сейчас итог:

```text
GLOBAL       70%
ENVIRONMENT  20%
COLOR         7%
SPATIAL       3%
```

То есть даже если L даст более качественный global embedding, он не обязательно изменит TOP-1.

---

### Что я бы сделал

Не менять рабочую систему.

Сначала сохранить текущий результат как **baseline**:

```text
B/14
768
v3.3
262 тестовых
```

Потом сделать экспериментальную ветку:

```text
L/14
1024
те же 1022 исходных фото
те же 262 test
```

и сравнить:

```text
B/14 → сколько правильных
L/14 → сколько правильных
```

Причём **89/90 будет одним из самых интересных тестов**.

Если L даст, например:

```text
B/14    90 → 89
L/14    90 → 90
```

при этом время распознавания выросло в 3 раза — тогда уже решаем, стоит ли это того.

А если:

```text
B/14    90 → 89
L/14    90 → 89
```

то смысла переходить на L для нашего проекта практически нет.

**С RTX 3060 я бы пока оставил B/14 как рабочую модель. L/14 имеет смысл именно как экспериментальная контрольная модель, а не как замена рабочей.**

---

### 👤 **User** — 2026-08-15 03:33:42

7. SORT TEST IMAGES BY TOP-1
============================================================
Traceback (most recent call last):
  File "<stdin>", line 19, in <module>
RuntimeError: JSON array not found

---

### 🤖 **Assistant** — 2026-08-15 03:33:43

Да, это уже **не ошибка распознавания**. Скрипт сортировки просто не нашёл JSON-массив в `final_test_78_95.json`.

Сначала проверим, что реально записалось в файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== JSON FILE ==="
ls -lh final_test_78_95.json

echo
echo "=== FIRST 40 LINES ==="
head -40 final_test_78_95.json

echo
echo "=== LAST 20 LINES ==="
tail -20 final_test_78_95.json
```

И отдельно:

```bash
echo
echo "=== JSON STRUCTURE ==="
python3 - <<'PY'
from pathlib import Path

p = Path("final_test_78_95.json")

text = p.read_text(encoding="utf-8")

print("SIZE:", len(text))
print("FIRST CHARACTERS:")
print(repr(text[:500]))

print()
print("Contains '[':", "[" in text)
print("Contains '{':", "{" in text)
print("Contains 'Query images':", "Query images" in text)
PY
```

### Скорее всего

После полного прогона у нас файл мог содержать не сам JSON, а **текстовый вывод программы**, например:

```text
[Model] Loading DINO...
[Recognizer] Starting recognition...
...
```

а сортировщик ожидает:

```json
[
  {
    "file": "...",
    "best_id": "78_v33",
    ...
  }
]
```

То есть надо сначала понять **что именно сейчас записывает `final_test_78_95.json`**.

Пришли вывод этих команд. **Пока ничего не удаляем и не пересоздаём** — если распознавание уже успешно прошло, результаты можно восстановить без повторного прогона.

---

### 👤 **User** — 2026-08-15 03:34:13

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== JSON FILE ==="
ls -lh final_test_78_95.json

echo
echo "=== FIRST 40 LINES ==="
head -40 final_test_78_95.json

echo
echo "=== LAST 20 LINES ==="
tail -20 final_test_78_95.json
=== JSON FILE ===
-rw-rw-r-- 1 alexice alexice 536K Aug 15 00:35 final_test_78_95.json

=== FIRST 40 LINES ===
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Recognizer] Query images: 262
[Recognizer] Fingerprints: 78_v33, 79_v33, 80_v33, 81_v33, 82_v33, 83_v33, 84_v33, 85_v33, 86_v33_fast, 87_v33_fast, 88_v33_fast, 89_v33_fast, 90_v33_fast, 91_v33_fast, 92_v33_fast, 93_v33_fast, 94_v33_fast, 95_v33_fast
[Recognizer] CPU workers: 6
[
  {
    "file": "data/input/test/00 (1).JPG",
    "best_id": "78_v33",
    "score": 0.9474834299087525,
    "second_score": 0.8923110395669936,
    "margin": 0.055172390341758804,
    "confidence": "HIGH",
    "status": "CONFIDENT",
    "best_image": "photo040.JPG",
    "best_image_score": 0.9566447734832764,
    "candidates": [
      {
        "id": "78_v33",
        "score": 0.9474834299087525,
        "global": 0.9548540711402893,
        "environment": 0.9361472129821777,
        "color": 0.8892236948013306,
        "spatial": 0.987015962600708,
        "best_image": "photo040.JPG",
        "best_image_score": 0.9566447734832764
      },
      {
        "id": "92_v33_fast",
        "score": 0.8923110395669936,
        "global": 0.8786738514900208,
        "environment": 0.906001091003418,
        "color": 0.9520142674446106,
        "spatial": 0.9799375534057617,
        "best_image": "Стачки Зорге А (45).JPG",

=== LAST 20 LINES ===
        "global": 0.7942922115325928,
        "environment": 0.9406343698501587,
        "color": 0.8165338039398193,
        "spatial": 0.9923828840255737,
        "best_image": "Вавилова 52 А (15).JPG",
        "best_image_score": 0.8088638782501221
      },
      {
        "id": "94_v33_fast",
        "score": 0.8246417653560639,
        "global": 0.7760992646217346,
        "environment": 0.9471738338470459,
        "color": 0.8885720372200012,
        "spatial": 0.9912490248680115,
        "best_image": "Вавилова Радиаторный А (13).JPG",
        "best_image_score": 0.7822959423065186
      }
    ]
  }
]
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=== JSON STRUCTURE ==="
python3 - <<'PY'
from pathlib import Path

p = Path("final_test_78_95.json")

text = p.read_text(encoding="utf-8")

print("SIZE:", len(text))
print("FIRST CHARACTERS:")
print(repr(text[:500]))

print()
print("Contains '[':", "[" in text)
print("Contains '{':", "{" in text)
print("Contains 'Query images':", "Query images" in text)
PY

=== JSON STRUCTURE ===
SIZE: 530659
FIRST CHARACTERS:
'[SceneEmbedder] device=cuda\n[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060\n[SceneEmbedder] VRAM=11.6 GB\n[SceneEmbedder] Loading DINOv2: facebook/dinov2-base\n[SceneEmbedder] embedding dimension=768\n[SceneEmbedder] patch extraction=DISABLED (compact)\n[SceneEmbedder] Ready.\n[Recognizer] Query images: 262\n[Recognizer] Fingerprints: 78_v33, 79_v33, 80_v33, 81_v33, 82_v33, 83_v33, 84_v33, 85_v33, 86_v33_fast, 87_v33_fast, 88_v33_fast, 89_v33_fast, 90_v33_fast, 91_v33_fast, 92_v33_fast, 93_v33_fast, 94_v3'

Contains '[': True
Contains '{': True
Contains 'Query images': True
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:34:15

Да, причина найдена. **`final_test_78_95.json` не является чистым JSON** — в начале туда попадает лог запуска:

```text
[SceneEmbedder] device=cuda
...
[Recognizer] CPU workers: 6
[
  {
    ...
```

Поэтому скрипт сортировки, который ожидает JSON, лучше сделать устойчивым: брать всё начиная с **первой строки, которая после `.strip()` равна `[`**.

Но есть ещё более важный момент: этот файл **старый**. В нём присутствуют:

```text
86_v33_fast
87_v33_fast
...
95_v33_fast
```

а сейчас у нас каталоги:

```text
86_v33
87_v33
...
95_v33
```

То есть **этот результат нельзя использовать для финального теста после пересоздания слепков**.

### Сейчас предлагаю сделать правильно

Сначала удаляем старый результат и старый output:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -f final_test_78_95.json

rm -rf data/output/test_classified

mkdir -p data/output/test_classified

echo "=== CLEAN ==="
echo "Old JSON removed"
echo "Old classification removed"
```

Затем **полностью пересоздаём 18 слепков 78–95**:

```bash
for n in $(seq 78 95); do
    echo
    echo "============================================================"
    echo "CREATING FINGERPRINT $n"
    echo "============================================================"

    rm -rf "data/fingerprints/${n}_v33"

    uv run scene-fingerprint create \
        "${n}_v33" \
        "data/input/${n}" || exit 1
done
```

После этого проверяем, что действительно созданы именно новые `v33`:

```bash
echo
echo "============================================================"
echo "=== FINGERPRINTS ==="
echo "============================================================"

find data/fingerprints \
    -maxdepth 1 \
    -mindepth 1 \
    -type d \
    -name '*_v33' \
    | sort
```

И проверяем количество исходных фотографий:

```bash
echo
echo "============================================================"
echo "=== FINGERPRINT CONTENT ==="
echo "============================================================"

for n in $(seq 78 95); do
    printf "%-10s " "${n}_v33"

    python3 - "$n" <<'PY'
import sys
from pathlib import Path
import json

n = sys.argv[1]
p = Path(f"data/fingerprints/{n}_v33/metadata.json")

if not p.exists():
    print("NO METADATA")
    raise SystemExit

d = json.loads(p.read_text())

print(
    "images=",
    len(d.get("image_names", [])),
    "version=",
    d.get("version")
)
PY
done
```

### А затем запускаем чистое распознавание

Очень важно сохранить **stdout отдельно от JSON**, чтобы больше не получить такую проблему.

Если текущий запуск у тебя идёт через `classify_final_test.py`, сначала покажи:

```bash
sed -n '1,120p' classify_final_test.py
```

Я по нему дам **одну правильную команду**, которая создаст:

```text
final_test_78_95.json
```

как настоящий JSON без `[SceneEmbedder]`, `[Recognizer]` и прочих логов.

После этого уже:

1. 18 новых слепков `78_v33 ... 95_v33`
2. распознавание всех **262 test**
3. TOP-1
4. распределение по 18 адресам
5. копирование фотографий в `data/output/test_classified/78 ... 95`
6. визуальная проверка.

И тогда результат будет действительно **чистым тестом текущего v3.3 с нуля**, без примеси старых `_fast`.

---

### 👤 **User** — 2026-08-15 03:39:49

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '1,120p' classify_final_test.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:39:51

Да. `classify_final_test.py` — это **только сортировщик уже готового JSON**, он не запускает распознавание. И сам сортировщик написан нормально: он как раз умеет пропускать лог в начале файла.

Проблема была не в нём, а в том, **как был создан `final_test_78_95.json`**.

Сейчас предлагаю не менять `classify_final_test.py`. Сначала пересоздадим слепки, затем отдельно создадим чистый JSON распознавания.

### 1. Пересоздаём `78_v33 ... 95_v33`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for n in $(seq 78 95); do
    echo
    echo "============================================================"
    echo "CREATING ${n}_v33"
    echo "============================================================"

    rm -rf "data/fingerprints/${n}_v33"

    uv run scene-fingerprint create \
        "${n}_v33" \
        "data/input/${n}" || exit 1
done
```

### 2. Проверяем, что все 18 слепков создались

```bash
echo
echo "============================================================"
echo "=== FINGERPRINT CHECK ==="
echo "============================================================"

for n in $(seq 78 95); do
    p="data/fingerprints/${n}_v33"

    if [ -f "$p/metadata.json" ]; then
        printf "%-12s OK\n" "${n}_v33"
    else
        printf "%-12s ERROR\n" "${n}_v33"
    fi
done
```

### 3. Проверяем версии и количество фотографий

```bash
python3 - <<'PY'
from pathlib import Path
import json

print("=" * 70)
print("FINGERPRINTS")
print("=" * 70)

for n in range(78, 96):
    p = Path(f"data/fingerprints/{n}_v33/metadata.json")

    if not p.exists():
        print(f"{n}_v33 ERROR: metadata missing")
        continue

    d = json.loads(p.read_text(encoding="utf-8"))

    print(
        f"{n}_v33: "
        f"images={len(d.get('image_names', []))} "
        f"version={d.get('version')}"
    )
PY
```

**После этого остановимся.** Покажи вывод этих трёх команд.

Если все 18 `OK`, следующим шагом дам команду на распознавание **262 фотографий `test` только по этим свежим `78_v33–95_v33`**, причём сделаем JSON чистым, без мусора `[SceneEmbedder]` в начале.

---

