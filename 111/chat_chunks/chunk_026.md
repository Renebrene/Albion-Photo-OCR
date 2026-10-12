## СЕССИЯ: Разработка подслепков

**Создано:** 2026-08-15 01:48:38
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f9b34-0188-83ea-b851-7793d1230a6f](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f9b34-0188-83ea-b851-7793d1230a6f)

---

### 👤 **User** — 2026-08-15 01:48:38

OCR не развиваем, продолжаем подслепки

---

### 🤖 **Assistant** — 2026-08-15 01:48:38

Да. OCR пока **замораживаем** и продолжаем именно **подслепки / subfingerprints**.

Следующий логичный этап для нашего пайплайна:

**DINOv2 → fingerprint адреса → subfingerprints → первый кандидат → присвоение адреса**

Причём я бы сейчас не трогал основной fingerprint `v33`, а работал поверх него.

### Что делаем сейчас

Для каждого адреса создаём набор подслепков из его фотографий:

- общий scene embedding;
- patch embeddings;
- несколько кластеров похожих кадров;
- для каждого кластера — свой subfingerprint;
- сохраняем представителей кластера.

Например:

```text
78_v33/
├── embeddings.npy
├── patch_embeddings.npy
├── centroid.npy
├── ...
└── subfingerprints/
    ├── sub_01/
    │   ├── centroid.npy
    │   ├── embeddings.npy
    │   └── representatives.npy
    ├── sub_02/
    ├── sub_03/
    └── ...
```

Это особенно важно для твоего случая, потому что **один адрес может быть снят с совершенно разных точек**: подъезд, фасад, дорога, двор, дальний план и т.д. Один средний fingerprint это смешивает.

### Я предлагаю сейчас сделать именно это

Не классификатор и не OCR, а отдельный этап:

```text
data/fingerprints/
    78_v33
    79_v33
    80_v33
    ...

        ↓

subfingerprints

        ↓

recognize

новое фото
   ↓
DINOv2
   ↓
поиск ближайших subfingerprints
   ↓
ТОП кандидатов
   ↓
сравнение с полным fingerprint адреса
   ↓
итоговый адрес
```

И ключевой момент: **первый кандидат должен использоваться как подсказка, а не как окончательное решение**. Это как раз позволит нам потом добавить повторное распознавание новых фотографий относительно наиболее похожих кадров.

Если продолжаем с текущего состояния, я бы следующим шагом посмотрел **реальную структуру `78_v33` и текущий код создания subfingerprints**, а затем внес минимальные изменения, не ломая уже работающий `v33`.

---

### 👤 **User** — 2026-08-15 01:49:01

да

---

### 🤖 **Assistant** — 2026-08-15 01:49:01

Отлично. Тогда идём **от текущего `v33` и не ломаем существующий пайплайн**.

Следующий шаг — сначала посмотреть фактическую структуру проекта и текущую реализацию fingerprint/subfingerprint. После этого я дам точечные изменения.

Выполни в каталоге проекта:

```bash
cd ~/scene_fingerprint_mvp_v02

echo "=== PROJECT ==="
pwd

echo
echo "=== FINGERPRINTS ==="
find data/fingerprints -maxdepth 2 -type f | sort | head -200

echo
echo "=== CORE ==="
find app -maxdepth 3 -type f | sort

echo
echo "=== V33 ==="
find data/fingerprints/78_v33 -maxdepth 2 -type f -printf '%p %s bytes\n' | sort

echo
echo "=== SUBFINGERPRINT REFERENCES ==="
grep -RniE "subfinger|sub_finger|representative|cluster" app scripts pyproject.toml 2>/dev/null | head -200
```

И отдельно:

```bash
echo "=== CLI HELP ==="
uv run scene-fingerprint --help

echo
echo "=== RECOGNIZE HELP ==="
uv run scene-fingerprint recognize --help

echo
echo "=== CREATE HELP ==="
uv run scene-fingerprint create --help
```

**Ничего пока не изменяй и не запускай создание новых fingerprint.**

Пришли вывод целиком. По нему определим, что у нас уже есть для `subfingerprints`, и следующим сообщением сделаем первый рабочий генератор подслепков для `v33`.

---

### 👤 **User** — 2026-08-15 01:49:40

alexice@NEURO:~$ cd ~/scene_fingerprint_mvp_v02

echo "=== PROJECT ==="
pwd

echo
echo "=== FINGERPRINTS ==="
find data/fingerprints -maxdepth 2 -type f | sort | head -200

echo
echo "=== CORE ==="
find app -maxdepth 3 -type f | sort

echo
echo "=== V33 ==="
find data/fingerprints/78_v33 -maxdepth 2 -type f -printf '%p %s bytes\n' | sort 

echo
echo "=== SUBFINGERPRINT REFERENCES ==="
grep -RniE "subfinger|sub_finger|representative|cluster" app scripts pyproject.toml 2>/dev/null | head -200
bash: cd: /home/alexice/scene_fingerprint_mvp_v02: No such file or directory
=== PROJECT ===
/home/alexice

=== FINGERPRINTS ===
find: ‘data/fingerprints’: No such file or directory

=== CORE ===
find: ‘app’: No such file or directory

=== V33 ===
find: ‘data/fingerprints/78_v33’: No such file or directory

=== SUBFINGERPRINT REFERENCES ===
alexice@NEURO:~$ echo "=== CLI HELP ==="
uv run scene-fingerprint --help

echo
echo "=== RECOGNIZE HELP ==="
uv run scene-fingerprint recognize --help

echo
echo "=== CREATE HELP ==="
uv run scene-fingerprint create --help
=== CLI HELP ===
error: Failed to spawn: `scene-fingerprint`
  Caused by: No such file or directory (os error 2)

=== RECOGNIZE HELP ===
error: Failed to spawn: `scene-fingerprint`
  Caused by: No such file or directory (os error 2)

=== CREATE HELP ===
error: Failed to spawn: `scene-fingerprint`
  Caused by: No such file or d

---

### 🤖 **Assistant** — 2026-08-15 01:49:40

Да, здесь проблема простая: **мы сейчас не в каталоге проекта**. Судя по предыдущей работе, проект мог находиться не в `~/scene_fingerprint_mvp_v02`, а в другом месте.

Не будем угадывать путь. Сначала найдём его.

Выполни **только этот блок**:

```bash
echo "=== HOME ==="
echo "$HOME"

echo
echo "=== DIRECTORIES IN HOME ==="
find "$HOME" -maxdepth 2 -type d \( \
    -name "scene_fingerprint*" -o \
    -name ".venv" -o \
    -name "data" \
\) -print 2>/dev/null

echo
echo "=== scene-fingerprint FILES ==="
find "$HOME" -maxdepth 4 -type f \( \
    -name "pyproject.toml" -o \
    -name "scene_fingerprint.py" -o \
    -name "fingerprint.py" \
\) -print 2>/dev/null | head -100

echo
echo "=== KNOWN FINGERPRINT DIRECTORIES ==="
find "$HOME" -type d \( \
    -name "78_v33" -o \
    -name "79_v33" -o \
    -name "80_v33" \
\) -print 2>/dev/null
```

### Почему так

`uv run scene-fingerprint` тоже не работает, потому что `uv` сейчас запускается из `/home/alexice`, где нет `pyproject.toml` проекта и, соответственно, нет установленной CLI-команды.

Нам сейчас **не нужно ничего переустанавливать** и тем более пересоздавать fingerprint.

Найдём настоящий каталог проекта → перейдём туда → проверим `78_v33` → продолжим с подслепками.

Пришли вывод этого блока.

---

### 👤 **User** — 2026-08-15 01:50:47

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/scene_fingerprint_mvp_v02

echo "=== PROJECT ==="
pwd

echo
echo "=== FINGERPRINTS ==="
find data/fingerprints -maxdepth 2 -type f | sort | head -200

echo
echo "=== CORE ==="
find app -maxdepth 3 -type f | sort

echo
echo "=== V33 ==="
find data/fingerprints/78_v33 -maxdepth 2 -type f -printf '%p %s bytes\n' | sort 

echo
echo "=== SUBFINGERPRINT REFERENCES ==="
grep -RniE "subfinger|sub_finger|representative|cluster" app scripts pyproject.toml 2>/dev/null | head -200
bash: cd: /home/alexice/scene_fingerprint_mvp_v02: No such file or directory
=== PROJECT ===
/home/alexice/projects/scene_fingerprint_mvp_v02

=== FINGERPRINTS ===
data/fingerprints/78_v33/centroid.npy
data/fingerprints/78_v33/color_embeddings.npy
data/fingerprints/78_v33/embeddings.npy
data/fingerprints/78_v33/environment_embeddings.npy
data/fingerprints/78_v33/faiss.index
data/fingerprints/78_v33/metadata.json
data/fingerprints/78_v33/representative_indices.npy
data/fingerprints/78_v33/representatives.npy
data/fingerprints/78_v33/spatial_embeddings.npy
data/fingerprints/79_v33/centroid.npy
data/fingerprints/79_v33/color_embeddings.npy
data/fingerprints/79_v33/embeddings.npy
data/fingerprints/79_v33/environment_embeddings.npy
data/fingerprints/79_v33/faiss.index
data/fingerprints/79_v33/metadata.json
data/fingerprints/79_v33/representative_indices.npy
data/fingerprints/79_v33/representatives.npy
data/fingerprints/79_v33/spatial_embeddings.npy
data/fingerprints/80_v33/centroid.npy
data/fingerprints/80_v33/color_embeddings.npy
data/fingerprints/80_v33/embeddings.npy
data/fingerprints/80_v33/environment_embeddings.npy
data/fingerprints/80_v33/faiss.index
data/fingerprints/80_v33/metadata.json
data/fingerprints/80_v33/representative_indices.npy
data/fingerprints/80_v33/representatives.npy
data/fingerprints/80_v33/spatial_embeddings.npy
data/fingerprints/81_v33/centroid.npy
data/fingerprints/81_v33/color_embeddings.npy
data/fingerprints/81_v33/embeddings.npy
data/fingerprints/81_v33/environment_embeddings.npy
data/fingerprints/81_v33/faiss.index
data/fingerprints/81_v33/metadata.json
data/fingerprints/81_v33/representative_indices.npy
data/fingerprints/81_v33/representatives.npy
data/fingerprints/81_v33/spatial_embeddings.npy
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
data/fingerprints/84_v34_test/embeddings.npy
data/fingerprints/84_v34_test/metadata.json
data/fingerprints/84_v35_test/embeddings.npy
data/fingerprints/84_v35_test/metadata.json
data/fingerprints/85_v33/centroid.npy
data/fingerprints/85_v33/color_embeddings.npy
data/fingerprints/85_v33/embeddings.npy
data/fingerprints/85_v33/environment_embeddings.npy
data/fingerprints/85_v33/faiss.index
data/fingerprints/85_v33/metadata.json
data/fingerprints/85_v33/representative_indices.npy
data/fingerprints/85_v33/representatives.npy
data/fingerprints/85_v33/spatial_embeddings.npy
data/fingerprints/86_v33/centroid.npy
data/fingerprints/86_v33/color_embeddings.npy
data/fingerprints/86_v33/embeddings.npy
data/fingerprints/86_v33/environment_embeddings.npy
data/fingerprints/86_v33/faiss.index
data/fingerprints/86_v33/metadata.json
data/fingerprints/86_v33/representative_indices.npy
data/fingerprints/86_v33/representatives.npy
data/fingerprints/86_v33/spatial_embeddings.npy
data/fingerprints/87_v33/centroid.npy
data/fingerprints/87_v33/color_embeddings.npy
data/fingerprints/87_v33/embeddings.npy
data/fingerprints/87_v33/environment_embeddings.npy
data/fingerprints/87_v33/faiss.index
data/fingerprints/87_v33/metadata.json
data/fingerprints/87_v33/representative_indices.npy
data/fingerprints/87_v33/representatives.npy
data/fingerprints/87_v33/spatial_embeddings.npy
data/fingerprints/88_v33/centroid.npy
data/fingerprints/88_v33/color_embeddings.npy
data/fingerprints/88_v33/embeddings.npy
data/fingerprints/88_v33/environment_embeddings.npy
data/fingerprints/88_v33/faiss.index
data/fingerprints/88_v33/metadata.json
data/fingerprints/88_v33/representative_indices.npy
data/fingerprints/88_v33/representatives.npy
data/fingerprints/88_v33/spatial_embeddings.npy
data/fingerprints/89_v33/centroid.npy
data/fingerprints/89_v33/color_embeddings.npy
data/fingerprints/89_v33/embeddings.npy
data/fingerprints/89_v33/environment_embeddings.npy
data/fingerprints/89_v33/faiss.index
data/fingerprints/89_v33/metadata.json
data/fingerprints/89_v33/representative_indices.npy
data/fingerprints/89_v33/representatives.npy
data/fingerprints/89_v33/spatial_embeddings.npy
data/fingerprints/90_v33/centroid.npy
data/fingerprints/90_v33/color_embeddings.npy
data/fingerprints/90_v33/embeddings.npy
data/fingerprints/90_v33/environment_embeddings.npy
data/fingerprints/90_v33/faiss.index
data/fingerprints/90_v33/metadata.json
data/fingerprints/90_v33/representative_indices.npy
data/fingerprints/90_v33/representatives.npy
data/fingerprints/90_v33/spatial_embeddings.npy
data/fingerprints/91_v33/centroid.npy
data/fingerprints/91_v33/color_embeddings.npy
data/fingerprints/91_v33/embeddings.npy
data/fingerprints/91_v33/environment_embeddings.npy
data/fingerprints/91_v33/faiss.index
data/fingerprints/91_v33/metadata.json
data/fingerprints/91_v33/representative_indices.npy
data/fingerprints/91_v33/representatives.npy
data/fingerprints/91_v33/spatial_embeddings.npy
data/fingerprints/92_v33/centroid.npy
data/fingerprints/92_v33/color_embeddings.npy
data/fingerprints/92_v33/embeddings.npy
data/fingerprints/92_v33/environment_embeddings.npy
data/fingerprints/92_v33/faiss.index
data/fingerprints/92_v33/metadata.json
data/fingerprints/92_v33/representative_indices.npy
data/fingerprints/92_v33/representatives.npy
data/fingerprints/92_v33/spatial_embeddings.npy
data/fingerprints/93_v33/centroid.npy
data/fingerprints/93_v33/color_embeddings.npy
data/fingerprints/93_v33/embeddings.npy
data/fingerprints/93_v33/environment_embeddings.npy
data/fingerprints/93_v33/faiss.index
data/fingerprints/93_v33/metadata.json
data/fingerprints/93_v33/representative_indices.npy
data/fingerprints/93_v33/representatives.npy
data/fingerprints/93_v33/spatial_embeddings.npy
data/fingerprints/94_v33/centroid.npy
data/fingerprints/94_v33/color_embeddings.npy
data/fingerprints/94_v33/embeddings.npy
data/fingerprints/94_v33/environment_embeddings.npy
data/fingerprints/94_v33/faiss.index
data/fingerprints/94_v33/metadata.json
data/fingerprints/94_v33/representative_indices.npy
data/fingerprints/94_v33/representatives.npy
data/fingerprints/94_v33/spatial_embeddings.npy
data/fingerprints/95_v33/centroid.npy
data/fingerprints/95_v33/color_embeddings.npy
data/fingerprints/95_v33/embeddings.npy
data/fingerprints/95_v33/environment_embeddings.npy
data/fingerprints/95_v33/faiss.index
data/fingerprints/95_v33/metadata.json
data/fingerprints/95_v33/representative_indices.npy
data/fingerprints/95_v33/representatives.npy
data/fingerprints/95_v33/spatial_embeddings.npy

=== CORE ===
app/cli.py
app/core/config.py
app/core/embedder.py
app/core/embedder.py.before_transformers
app/core/fingerprint.py
app/core/fingerprint.py.bak_before_create_opt
app/core/fingerprint.py.before_patchfix
app/core/image.py
app/core/__init__.py
app/core/__pycache__/config.cpython-312.pyc
app/core/__pycache__/embedder.cpython-312.pyc
app/core/__pycache__/fingerprint.cpython-312.pyc
app/core/__pycache__/image.cpython-312.pyc
app/core/__pycache__/__init__.cpython-312.pyc
app/core/__pycache__/recognizer.cpython-312.pyc
app/core/__pycache__/scene_analyzer.cpython-312.pyc
app/core/recognizer.py
app/core/recognizer.py.backup_before_force_match
app/core/recognizer.py.backup_before_optimization
app/core/recognizer.py.before_patchfix
app/core/scene_analyzer.py
app/core/scene_analyzer.py.backup_before_optimization
app/core/scene_analyzer.py.bak_before_create_opt
app/__init__.py
app/main.py
app/ocr/grid_ocr.py
app/ocr/__init__.py
app/ocr/ocr_pipeline.py
app/ocr/plate_detector.py
app/ocr/__pycache__/grid_ocr.cpython-312.pyc
app/ocr/__pycache__/__init__.cpython-312.pyc
app/ocr/__pycache__/ocr_pipeline.cpython-312.pyc
app/ocr/__pycache__/plate_detector.cpython-312.pyc
app/pipeline/__init__.py
app/pipeline/__pycache__/__init__.cpython-312.pyc
app/pipeline/__pycache__/queue.cpython-312.pyc
app/pipeline/__pycache__/worker.cpython-312.pyc
app/pipeline/queue.py
app/pipeline/worker.py
app/__pycache__/cli.cpython-312.pyc
app/__pycache__/__init__.cpython-312.pyc
app/__pycache__/main.cpython-312.pyc

=== V33 ===
data/fingerprints/78_v33/centroid.npy 3200 bytes
data/fingerprints/78_v33/color_embeddings.npy 15872 bytes
data/fingerprints/78_v33/embeddings.npy 252032 bytes
data/fingerprints/78_v33/environment_embeddings.npy 210048 bytes
data/fingerprints/78_v33/faiss.index 251949 bytes
data/fingerprints/78_v33/metadata.json 2149 bytes
data/fingerprints/78_v33/representative_indices.npy 192 bytes
data/fingerprints/78_v33/representatives.npy 49280 bytes
data/fingerprints/78_v33/spatial_embeddings.npy 10624 bytes

=== SUBFINGERPRINT REFERENCES ===
app/core/fingerprint.py.before_patchfix:149:        # Select up to 16 representative global images.
app/core/fingerprint.py.before_patchfix:159:        representatives = embeddings[indices]
app/core/fingerprint.py.before_patchfix:182:        patch_representatives = patch_embeddings[indices]
app/core/fingerprint.py.before_patchfix:199:            out / "representatives.npy",
app/core/fingerprint.py.before_patchfix:200:            representatives.astype(np.float32),
app/core/fingerprint.py.before_patchfix:214:            out / "patch_representatives.npy",
app/core/fingerprint.py.before_patchfix:215:            patch_representatives.astype(np.float32),
app/core/fingerprint.py.before_patchfix:231:            "representatives": len(indices),
app/core/fingerprint.py.before_patchfix:271:            "representatives.npy",
app/core/fingerprint.py.before_patchfix:274:            "patch_representatives.npy",
app/core/fingerprint.py.before_patchfix:304:            "representatives": np.load(
app/core/fingerprint.py.before_patchfix:305:                out / "representatives.npy"
app/core/fingerprint.py.before_patchfix:313:            "patch_representatives": np.load(
app/core/fingerprint.py.before_patchfix:314:                out / "patch_representatives.npy"
app/core/recognizer.py.before_patchfix:26:            reference["representatives"],
app/core/recognizer.py.before_patchfix:41:            reference["patch_representatives"],
app/core/recognizer.py.before_patchfix:52:        # spatial patch positions in every representative.
app/core/fingerprint.py:22:        representatives.npy
app/core/fingerprint.py:23:        representative_indices.npy
app/core/fingerprint.py:244:        representative_count = min(
app/core/fingerprint.py:249:        representative_indices = (
app/core/fingerprint.py:253:                -representative_count:
app/core/fingerprint.py:257:        representatives = (
app/core/fingerprint.py:259:                representative_indices
app/core/fingerprint.py:345:            output / "representatives.npy",
app/core/fingerprint.py:346:            representatives.astype(
app/core/fingerprint.py:352:            output / "representative_indices.npy",
app/core/fingerprint.py:353:            representative_indices,
app/core/fingerprint.py:386:            "representatives": int(
app/core/fingerprint.py:387:                representative_count
app/core/fingerprint.py:477:            "representatives.npy",
app/core/fingerprint.py:478:            "representative_indices.npy",
app/core/fingerprint.py:541:            "representatives": np.load(
app/core/fingerprint.py:542:                output / "representatives.npy"
app/core/fingerprint.py:545:            "representative_indices": np.load(
app/core/fingerprint.py:547:                / "representative_indices.npy"
app/core/fingerprint.py.bak_before_create_opt:21:        representatives.npy
app/core/fingerprint.py.bak_before_create_opt:22:        representative_indices.npy
app/core/fingerprint.py.bak_before_create_opt:243:        representative_count = min(
app/core/fingerprint.py.bak_before_create_opt:248:        representative_indices = (
app/core/fingerprint.py.bak_before_create_opt:252:                -representative_count:
app/core/fingerprint.py.bak_before_create_opt:256:        representatives = (
app/core/fingerprint.py.bak_before_create_opt:258:                representative_indices
app/core/fingerprint.py.bak_before_create_opt:313:            output / "representatives.npy",
app/core/fingerprint.py.bak_before_create_opt:314:            representatives.astype(
app/core/fingerprint.py.bak_before_create_opt:320:            output / "representative_indices.npy",
app/core/fingerprint.py.bak_before_create_opt:321:            representative_indices,
app/core/fingerprint.py.bak_before_create_opt:354:            "representatives": int(
app/core/fingerprint.py.bak_before_create_opt:355:                representative_count
app/core/fingerprint.py.bak_before_create_opt:445:            "representatives.npy",
app/core/fingerprint.py.bak_before_create_opt:446:            "representative_indices.npy",
app/core/fingerprint.py.bak_before_create_opt:509:            "representatives": np.load(
app/core/fingerprint.py.bak_before_create_opt:510:                output / "representatives.npy"
app/core/fingerprint.py.bak_before_create_opt:513:            "representative_indices": np.load(
app/core/fingerprint.py.bak_before_create_opt:515:                / "representative_indices.npy"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo "=== CLI HELP ==="
uv run scene-fingerprint --help

echo
echo "=== RECOGNIZE HELP ==="
uv run scene-fingerprint recognize --help

echo
echo "=== CREATE HELP ==="
uv run scene-fingerprint create --help
=== CLI HELP ===
usage: scene-fingerprint [-h]
                         {create,queue-add,queue-batch-add,analyze,recognize}
                         ...

Scene fingerprinting and recognition v3.3 compact

positional arguments:
  {create,queue-add,queue-batch-add,analyze,recognize}
    create              Create v3.3 compact fingerprint
    queue-add           Add fingerprint creation job to queue
    queue-batch-add     Add a range of folders to fingerprint queue
    analyze             Analyze one fingerprint
    recognize           Recognize images

options:
  -h, --help            show this help message and exit

=== RECOGNIZE HELP ===
usage: scene-fingerprint recognize [-h] [--top-k TOP_K]
                                   [--threshold THRESHOLD] [--workers WORKERS]
                                   [--fingerprints FINGERPRINTS] [--json]
                                   folder

positional arguments:
  folder                Folder with query images

options:
  -h, --help            show this help message and exit
  --top-k TOP_K         Number of candidates
  --threshold THRESHOLD
                        Minimum absolute match score
  --workers WORKERS     Number of CPU workers for descriptor calculation
  --fingerprints FINGERPRINTS
                        Comma-separated fingerprint IDs to use
  --json                Output JSON

=== CREATE HELP ===
usage: scene-fingerprint create [-h] fingerprint folder

positional arguments:
  fingerprint  Fingerprint ID
  folder       Folder with reference images

options:
  -h, --help   show this help message and exit
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:50:49

Отлично. Теперь картина ясна.

У нас уже есть **v3.3 compact**, и самое важное — `embeddings.npy` в `78_v33` содержит не просто один средний вектор, а набор векторов фотографий. Поэтому **подслепки можно построить без повторного прогона DINOv2**. Это именно то, что сейчас нужно.

Я бы пока **не менял `fingerprint.py` и `recognizer.py`**. Сделаем отдельный инструмент `subfingerprint`, который читает существующие `*_v33`.

### Сначала проверим реальные размеры и metadata

Это безопасно и ничего не меняет. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python - <<'PY'
import json
import numpy as np
from pathlib import Path

for fp in ["78_v33", "79_v33", "80_v33", "81_v33", "82_v33"]:
    p = Path("data/fingerprints") / fp

    print("\n" + "=" * 70)
    print(fp)

    with open(p / "metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    print("metadata:")
    for k, v in meta.items():
        print(f"  {k}: {v}")

    for name in [
        "embeddings.npy",
        "color_embeddings.npy",
        "environment_embeddings.npy",
        "spatial_embeddings.npy",
        "representatives.npy",
        "representative_indices.npy",
    ]:
        a = np.load(p / name, mmap_mode="r")
        print(f"{name:30s} shape={a.shape} dtype={a.dtype}")
PY
```

### Зачем это нужно

Я хочу увидеть, например:

```text
embeddings.npy
    (N, 768)

environment_embeddings.npy
    (N, ...)

color_embeddings.npy
    (N, ...)

spatial_embeddings.npy
    (N, ...)
```

Если там действительно **N фотографий**, то подслепки мы можем сделать непосредственно кластеризацией этих уже существующих дескрипторов.

Причём я предлагаю **не делать просто KMeans на весь адрес**.

Для нашего случая лучше:

```text
78_v33
   │
   ├── все фотографии адреса
   │
   ├── sub_01  ← фасад / основной ракурс
   ├── sub_02  ← боковой ракурс
   ├── sub_03  ← дорога / окружение
   ├── sub_04  ← двор
   └── sub_05  ← другой характерный ракурс
```

А затем при распознавании:

```text
НОВОЕ ФОТО
     │
     ▼
DINOv2
     │
     ▼
поиск ближайших subfingerprints
     │
     ├── 78/sub_03   0.91
     ├── 78/sub_01   0.87
     ├── 83/sub_02   0.74
     └── 91/sub_04   0.71
              │
              ▼
        первый кандидат = 78
```

И уже **после получения первого кандидата** можно делать более дорогую проверку только внутри его фотографий.

Это намного ближе к той архитектуре, которую мы обсуждали: **первый кандидат → уточнение → адрес**, а не пытаться одним глобальным centroid определить всё.

Пришли вывод проверки размеров. После него уже напишем `make_subfingerprints.py` под фактический формат `v33`, а не будем гадать о структуре данных.

---

### 👤 **User** — 2026-08-15 01:51:26

int_mvp_v02

python - <<'PY'
import json
import numpy as np
from pathlib import Path

for fp in ["78_v33", "79_v33", "80_v33", "81_v33", "82_v33"]:
    p = Path("data/fingerprints") / fp

    print("\n" + "=" * 70)
    print(fp)

    with open(p / "metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    print("metadata:")
    for k, v in meta.items():
        print(f"  {k}: {v}")

    for name in [
        "embeddings.npy",
        "color_embeddings.npy",
PY      print(f"{name:30s} shape={a.shape} dtype={a.dtype}")
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:51:26

Да, всё нормально — просто в этой системе команда `python` не установлена как alias. У нас проект работает через **`uv`**, поэтому лучше вообще не использовать системный `python`.

Запусти тот же тест через `uv run python`:

```bash id="f0xq0a"
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
import numpy as np
from pathlib import Path

for fp in ["78_v33", "79_v33", "80_v33", "81_v33", "82_v33"]:
    p = Path("data/fingerprints") / fp

    print("\n" + "=" * 70)
    print(fp)

    with open(p / "metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    print("metadata:")
    for k, v in meta.items():
        print(f"  {k}: {v}")

    for name in [
        "embeddings.npy",
        "color_embeddings.npy",
        "environment_embeddings.npy",
        "spatial_embeddings.npy",
        "representatives.npy",
        "representative_indices.npy",
    ]:
        a = np.load(p / name, mmap_mode="r")
        print(f"{name:30s} shape={a.shape} dtype={a.dtype}")
PY
```

Это **только чтение**, ничего не создаёт и не меняет.

Особенно нужны мне строки вида:

```text
embeddings.npy                  shape=(...)
color_embeddings.npy            shape=(...)
environment_embeddings.npy      shape=(...)
spatial_embeddings.npy          shape=(...)
representatives.npy              shape=(...)
representative_indices.npy      shape=(...)
```

После этого уже определим точную схему подслепков.

---

### 👤 **User** — 2026-08-15 01:51:48

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
import numpy as np
from pathlib import Path

for fp in ["78_v33", "79_v33", "80_v33", "81_v33", "82_v33"]:
    p = Path("data/fingerprints") / fp

    print("\n" + "=" * 70)
    print(fp)

    with open(p / "metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    print("metadata:")
    for k, v in meta.items():
        print(f"  {k}: {v}")

    for name in [
        "embeddings.npy",
        "color_embeddings.npy",
PY      print(f"{name:30s} shape={a.shape} dtype={a.dtype}")

======================================================================
78_v33
metadata:
  id: 78_v33
  version: 3.3
  model: dinov2_vitb14
  images: 82
  dimension: 768
  representatives: 16
  patch_tokens: 0
  patch_storage: False
  environment_descriptor: compact_v1
  environment_dimension: 640
  color_descriptor: hsv_histogram_v1
  color_dimension: 48
  spatial_descriptor: gray_grid_v1
  spatial_dimension: 32
  weights: {'global': 0.7, 'environment': 0.2, 'color': 0.07, 'spatial': 0.03}
  image_names: ['photo001.JPG', 'photo002.JPG', 'photo003.JPG', 'photo004.JPG', 'photo005.JPG', 'photo006.JPG', 'photo007.JPG', 'photo008.JPG', 'photo009.JPG', 'photo010.JPG', 'photo011.JPG', 'photo012.JPG', 'photo013.JPG', 'photo014.JPG', 'photo015.JPG', 'photo016.JPG', 'photo017.JPG', 'photo018.JPG', 'photo019.JPG', 'photo020.JPG', 'photo021.JPG', 'photo022.JPG', 'photo023.JPG', 'photo024.JPG', 'photo025.JPG', 'photo026.JPG', 'photo027.JPG', 'photo028.JPG', 'photo029.JPG', 'photo030.JPG', 'photo031.JPG', 'photo032.JPG', 'photo033.JPG', 'photo034.JPG', 'photo035.JPG', 'photo036.JPG', 'photo037.JPG', 'photo038.JPG', 'photo039.JPG', 'photo040.JPG', 'photo041.JPG', 'photo042.JPG', 'photo043.JPG', 'photo044.JPG', 'photo045.JPG', 'photo046.JPG', 'photo047.JPG', 'photo048.JPG', 'photo049.JPG', 'photo050.JPG', 'photo051.JPG', 'photo052.JPG', 'photo053.JPG', 'photo054.JPG', 'photo055.JPG', 'photo056.JPG', 'photo057.JPG', 'photo058.JPG', 'photo059.JPG', 'photo060.JPG', 'photo061.JPG', 'photo062.JPG', 'photo063.JPG', 'photo064.JPG', 'photo065.JPG', 'photo066.JPG', 'photo067.JPG', 'photo068.JPG', 'photo069.JPG', 'photo070.JPG', 'photo071.JPG', 'photo072.JPG', 'photo073.JPG', 'photo074.JPG', 'photo075.JPG', 'photo076.JPG', 'photo077.JPG', 'photo078.JPG', 'photo079.JPG', 'photo080.JPG', 'photo081.JPG', 'photo082.JPG']
embeddings.npy                 shape=(82, 768) dtype=float32
color_embeddings.npy           shape=(82, 48) dtype=float32
environment_embeddings.npy     shape=(82, 640) dtype=float32
spatial_embeddings.npy         shape=(82, 32) dtype=float32
representatives.npy            shape=(16, 768) dtype=float32
representative_indices.npy     shape=(16,) dtype=int32

======================================================================
79_v33
metadata:
  id: 79_v33
  version: 3.3
  model: dinov2_vitb14
  images: 65
  dimension: 768
  representatives: 16
  patch_tokens: 0
  patch_storage: False
  environment_descriptor: compact_v1
  environment_dimension: 640
  color_descriptor: hsv_histogram_v1
  color_dimension: 48
  spatial_descriptor: gray_grid_v1
  spatial_dimension: 32
  weights: {'global': 0.7, 'environment': 0.2, 'color': 0.07, 'spatial': 0.03}
  image_names: ['00 (1).JPG', '00 (10).JPG', '00 (11).JPG', '00 (12).JPG', '00 (13).JPG', '00 (14).JPG', '00 (15).JPG', '00 (16).JPG', '00 (17).JPG', '00 (18).JPG', '00 (19).JPG', '00 (2).JPG', '00 (20).JPG', '00 (21).JPG', '00 (22).JPG', '00 (23).JPG', '00 (24).JPG', '00 (25).JPG', '00 (26).JPG', '00 (27).JPG', '00 (28).JPG', '00 (29).JPG', '00 (3).JPG', '00 (30).JPG', '00 (31).JPG', '00 (32).JPG', '00 (33).JPG', '00 (34).JPG', '00 (35).JPG', '00 (36).JPG', '00 (37).JPG', '00 (38).JPG', '00 (39).JPG', '00 (4).JPG', '00 (40).JPG', '00 (41).JPG', '00 (42).JPG', '00 (43).JPG', '00 (44).JPG', '00 (45).JPG', '00 (46).JPG', '00 (47).JPG', '00 (48).JPG', '00 (49).JPG', '00 (5).JPG', '00 (50).JPG', '00 (51).JPG', '00 (52).JPG', '00 (53).JPG', '00 (54).JPG', '00 (55).JPG', '00 (56).JPG', '00 (57).JPG', '00 (58).JPG', '00 (59).JPG', '00 (6).JPG', '00 (60).JPG', '00 (61).JPG', '00 (62).JPG', '00 (63).JPG', '00 (64).JPG', '00 (65).JPG', '00 (7).JPG', '00 (8).JPG', '00 (9).JPG']
embeddings.npy                 shape=(65, 768) dtype=float32
color_embeddings.npy           shape=(65, 48) dtype=float32
environment_embeddings.npy     shape=(65, 640) dtype=float32
spatial_embeddings.npy         shape=(65, 32) dtype=float32
representatives.npy            shape=(16, 768) dtype=float32
representative_indices.npy     shape=(16,) dtype=int32

======================================================================
80_v33
metadata:
  id: 80_v33
  version: 3.3
  model: dinov2_vitb14
  images: 37
  dimension: 768
  representatives: 16
  patch_tokens: 0
  patch_storage: False
  environment_descriptor: compact_v1
  environment_dimension: 640
  color_descriptor: hsv_histogram_v1
  color_dimension: 48
  spatial_descriptor: gray_grid_v1
  spatial_dimension: 32
  weights: {'global': 0.7, 'environment': 0.2, 'color': 0.07, 'spatial': 0.03}
  image_names: ['001.JPG', '002.JPG', '003.JPG', '004.JPG', '005.JPG', '006.JPG', '007.JPG', '008.JPG', '009.JPG', '010.JPG', '011.JPG', '012.JPG', '013.JPG', '014.JPG', '015.JPG', '016.JPG', '017.JPG', '018.JPG', '019.JPG', '020.JPG', '021.JPG', '022.JPG', '023.JPG', '024.JPG', '025.JPG', '026.JPG', '027.JPG', '028.JPG', '029.JPG', '030.JPG', '031.JPG', '032.JPG', '033.JPG', '034.JPG', '035.JPG', '036.JPG', '037.JPG']
embeddings.npy                 shape=(37, 768) dtype=float32
color_embeddings.npy           shape=(37, 48) dtype=float32
environment_embeddings.npy     shape=(37, 640) dtype=float32
spatial_embeddings.npy         shape=(37, 32) dtype=float32
representatives.npy            shape=(16, 768) dtype=float32
representative_indices.npy     shape=(16,) dtype=int32

======================================================================
81_v33
metadata:
  id: 81_v33
  version: 3.3
  model: dinov2_vitb14
  images: 65
  dimension: 768
  representatives: 16
  patch_tokens: 0
  patch_storage: False
  environment_descriptor: compact_v1
  environment_dimension: 640
  color_descriptor: hsv_histogram_v1
  color_dimension: 48
  spatial_descriptor: gray_grid_v1
  spatial_dimension: 32
  weights: {'global': 0.7, 'environment': 0.2, 'color': 0.07, 'spatial': 0.03}
  image_names: ['01.JPG', '02.JPG', '03.JPG', '04.JPG', '05.JPG', '06.JPG', '07.JPG', '08.JPG', '09.JPG', '10.JPG', '11.JPG', '12.JPG', '13.JPG', '14.JPG', '15.JPG', '16.JPG', '17.JPG', '18.JPG', '19.JPG', '20.JPG', '21.JPG', '22.JPG', '23.JPG', '24.JPG', '25.JPG', '26.JPG', '27.JPG', '28.JPG', '29.JPG', '30.JPG', '31.JPG', '32.JPG', '33.JPG', '34.JPG', '35.JPG', '36.JPG', '37.JPG', '38.JPG', '39.JPG', '40.JPG', '41.JPG', '42.JPG', '43.JPG', '44.JPG', '45.JPG', '46.JPG', '47.JPG', '48.JPG', '49.JPG', '50.JPG', '51.JPG', '52.JPG', '53.JPG', '54.JPG', '55.JPG', '56.JPG', '57.JPG', '58.JPG', '59.JPG', '60.JPG', '61.JPG', '62.JPG', '63.JPG', '64.JPG', '65.JPG']
embeddings.npy                 shape=(65, 768) dtype=float32
color_embeddings.npy           shape=(65, 48) dtype=float32
environment_embeddings.npy     shape=(65, 640) dtype=float32
spatial_embeddings.npy         shape=(65, 32) dtype=float32
representatives.npy            shape=(16, 768) dtype=float32
representative_indices.npy     shape=(16,) dtype=int32

======================================================================
82_v33
metadata:
  id: 82_v33
  version: 3.3
  model: dinov2_vitb14
  images: 67
  dimension: 768
  representatives: 16
  patch_tokens: 0
  patch_storage: False
  environment_descriptor: compact_v1
  environment_dimension: 640
  color_descriptor: hsv_histogram_v1
  color_dimension: 48
  spatial_descriptor: gray_grid_v1
  spatial_dimension: 32
  weights: {'global': 0.7, 'environment': 0.2, 'color': 0.07, 'spatial': 0.03}
  image_names: ['1.JPG', '10.JPG', '11.JPG', '12.JPG', '13.JPG', '14.JPG', '15.JPG', '16.JPG', '17.JPG', '18.JPG', '19.JPG', '2.JPG', '20.JPG', '21.JPG', '22.JPG', '23.JPG', '24.JPG', '25.JPG', '26.JPG', '27.JPG', '28.JPG', '29.JPG', '3.JPG', '30.JPG', '31.JPG', '32.JPG', '33.JPG', '34.JPG', '35.JPG', '36.JPG', '37.JPG', '38.JPG', '39.JPG', '4.JPG', '40.JPG', '41.JPG', '42.JPG', '43.JPG', '44.JPG', '45.JPG', '46.JPG', '47.JPG', '48.JPG', '49.JPG', '5.JPG', '50.JPG', '51.JPG', '52.JPG', '53.JPG', '54.JPG', '55.JPG', '56.JPG', '57.JPG', '58.JPG', '59.JPG', '6.JPG', '60.JPG', '61.JPG', '62.JPG', '63.JPG', '64.JPG', '65.JPG', '66.JPG', '67.JPG', '7.JPG', '8.JPG', '9.JPG']
embeddings.npy                 shape=(67, 768) dtype=float32
color_embeddings.npy           shape=(67, 48) dtype=float32
environment_embeddings.npy     shape=(67, 640) dtype=float32
spatial_embeddings.npy         shape=(67, 32) dtype=float32
representatives.npy            shape=(16, 768) dtype=float32
representative_indices.npy     shape=(16,) dtype=int32
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:51:50

Отлично. Теперь у нас есть **вся необходимая структура**.

И здесь есть важный момент: **пересчитывать DINOv2 для создания подслепков не надо**.

У каждого `v33` уже есть полный набор признаков **для каждой фотографии**:

- `embeddings` — 768 DINOv2
- `environment` — 640
- `color` — 48
- `spatial` — 32

Например, у `78_v33`:

```text
82 фотографии
82 × 768  DINOv2
82 × 640  environment
82 × 48   color
82 × 32   spatial
```

То есть мы можем построить подслепки **из уже существующих данных**.

### Но я предлагаю не делать пока кластеризацию вслепую

Сначала посмотрим, **насколько фотографии внутри каждого адреса вообще разбиваются на естественные группы**.

Это важно: например, если у `78` реально есть 4 разных ракурса, мы увидим 4 устойчивых группы. А если KMeans просто искусственно разобьёт один и тот же ракурс на 6 частей — это нам не нужно.

Поэтому следующий тест — **анализ попарных сходств и автоматический поиск естественных групп**. Ничего в fingerprint не изменяем.

Запусти:

```bash id="p9b4aa"
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

for fp in ["78_v33", "79_v33", "80_v33", "81_v33", "82_v33"]:
    p = Path("data/fingerprints") / fp

    X = np.load(p / "embeddings.npy").astype(np.float32)

    # На всякий случай нормализация
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-12

    S = cosine_similarity(X)
    n = len(X)

    # Убираем диагональ
    vals = S[np.triu_indices(n, k=1)]

    print("\n" + "=" * 70)
    print(fp, "images =", n)

    for q in [0, 10, 25, 50, 75, 90, 95, 99, 100]:
        print(f"similarity p{q:02d}: {np.percentile(vals, q):.4f}")

    # Для каждой фотографии — среднее сходство с остальными
    mean_sim = (S.sum(axis=1) - 1) / max(n - 1, 1)

    order = np.argsort(mean_sim)

    print("\nMOST ISOLATED:")
    for i in order[:5]:
        print(
            f"  {i:3d}  mean={mean_sim[i]:.4f}"
        )

    print("\nMOST CENTRAL:")
    for i in order[-5:][::-1]:
        print(
            f"  {i:3d}  mean={mean_sim[i]:.4f}"
        )
PY
```

Это даст нам, например:

```text
similarity p10: 0.52
similarity p50: 0.71
similarity p90: 0.86
similarity p99: 0.94
```

и покажет, насколько сильно внутри одного адреса фотографии отличаются.

### Почему это сейчас важнее KMeans

Мы хотим получить не просто:

```text
78 → sub_01
   → sub_02
   → sub_03
```

а **реальные визуальные подтипы адреса**.

Я бы в итоге сделал примерно такую структуру:

```text
78_v33
│
├── sub_01
│   ├── centroid
│   ├── images: 01, 07, 12, 18...
│   └── representative images
│
├── sub_02
│   ├── centroid
│   ├── images: 02, 03, 04...
│   └── representative images
│
├── sub_03
│   └── ...
│
└── ...
```

Причём **subfingerprint будет состоять не только из DINOv2**. Мы сохраним ту же идею `v33`:

```text
subfingerprint score =
    DINOv2       0.70
    environment  0.20
    color        0.07
    spatial      0.03
```

Это позволит потом искать новый снимок не против усреднённого `78`, а против **конкретного визуального состояния `78/sub_02`**.

И ещё один важный момент: `representatives.npy` сейчас содержит только **16 представителей всего адреса**. Это не подслепки. Мы их не будем путать с новой системой.

**Пришли вывод этого теста.** По распределениям сходства я определю, какой метод лучше использовать — фиксированный K, hierarchical/DBSCAN-подобную группировку или гибрид с минимальным размером подслепка.

---

### 👤 **User** — 2026-08-15 01:52:20

import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

for fp in ["78_v33", "79_v33", "80_v33", "81_v33", "82_v33"]:
    p = Path("data/fingerprints") / fp

    X = np.load(p / "embeddings.npy").astype(np.float32)

    # На всякий случай нормализация
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-12

    S = cosine_similarity(X)
    n = len(X)

    # Убираем диагональ
    vals = S[np.triu_indices(n, k=1)]

    print("\n" + "=" * 70)
PY      )   f"  {i:3d}  mean={mean_sim[i]:.4f}" 1)стальными):.4f}")
Traceback (most recent call last):
  File "<stdin>", line 3, in <module>
ModuleNotFoundError: No module named 'sklearn'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:52:21

Да, `sklearn` в окружении не установлен. **Устанавливать его сейчас не надо** — для этого теста он вообще не нужен. NumPy сам прекрасно посчитает cosine similarity.

И вижу, что при вставке команды терминал немного испортил конец heredoc (`PY ...`). Поэтому давай дадим **чистый вариант без sklearn**.

Запусти:

```bash id="2g4w8n"
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import numpy as np
from pathlib import Path

for fp in ["78_v33", "79_v33", "80_v33", "81_v33", "82_v33"]:
    p = Path("data/fingerprints") / fp

    X = np.load(p / "embeddings.npy").astype(np.float32)

    # L2 normalization
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-12

    # Cosine similarity = normalized dot product
    S = X @ X.T

    n = len(X)

    # Только верхний треугольник, без диагонали
    vals = S[np.triu_indices(n, k=1)]

    print()
    print("=" * 70)
    print(fp, "images =", n)

    print("\nSIMILARITY DISTRIBUTION")

    for q in [0, 10, 25, 50, 75, 90, 95, 99, 100]:
        print(
            f"p{q:02d}: {np.percentile(vals, q):.4f}"
        )

    # Среднее сходство каждой фотографии
    mean_sim = (S.sum(axis=1) - 1.0) / max(n - 1, 1)

    order = np.argsort(mean_sim)

    print("\nMOST ISOLATED:")
    for i in order[:5]:
        print(
            f"  image #{i:3d}  "
            f"mean={mean_sim[i]:.4f}"
        )

    print("\nMOST CENTRAL:")
    for i in order[-5:][::-1]:
        print(
            f"  image #{i:3d}  "
            f"mean={mean_sim[i]:.4f}"
        )
PY
```

Это полностью автономно: используются только `numpy` и стандартный Python.

И главное — **ничего не меняет в базе fingerprint**.

После вывода уже можно будет решить, как строить подслепки. Я ожидаю, что по этим данным станет видно, насколько внутри одного адреса есть несколько устойчивых визуальных групп.

---

### 👤 **User** — 2026-08-15 01:52:43

78_v33 images = 82

SIMILARITY DISTRIBUTION
p00: 0.5949
p10: 0.7563
p25: 0.8060
p50: 0.8526
p75: 0.8885
p90: 0.9220
p95: 0.9435
p99: 0.9693
p100: 1.0000

MOST ISOLATED:
  image # 22  mean=0.7294
  image # 15  mean=0.7405
  image #  4  mean=0.7436
  image # 18  mean=0.7578
  image # 14  mean=0.7713

MOST CENTRAL:
  image # 74  mean=0.8828
  image # 43  mean=0.8827
  image # 41  mean=0.8827
  image # 72  mean=0.8817
  image # 77  mean=0.8794

======================================================================
79_v33 images = 65

SIMILARITY DISTRIBUTION
p00: 0.5749
p10: 0.7329
p25: 0.8135
p50: 0.8583
p75: 0.8917
p90: 0.9153
p95: 0.9336
p99: 0.9591
p100: 0.9846

MOST ISOLATED:
  image #  4  mean=0.6796
  image # 62  mean=0.6888
  image # 22  mean=0.7271
  image # 16  mean=0.7391
  image # 61  mean=0.7519

MOST CENTRAL:
  image # 40  mean=0.8790
  image # 20  mean=0.8788
  image # 51  mean=0.8763
  image # 38  mean=0.8752
  image # 35  mean=0.8752

======================================================================
80_v33 images = 37

SIMILARITY DISTRIBUTION
p00: 0.7744
p10: 0.8395
p25: 0.8622
p50: 0.8894
p75: 0.9101
p90: 0.9297
p95: 0.9407
p99: 0.9714
p100: 1.0000

MOST ISOLATED:
  image # 32  mean=0.8378
  image # 13  mean=0.8486
  image #  8  mean=0.8583
  image # 18  mean=0.8592
  image #  6  mean=0.8606

MOST CENTRAL:
  image #  4  mean=0.9089
  image # 15  mean=0.9089
  image # 27  mean=0.9081
  image # 24  mean=0.9065
  image #  3  mean=0.9032

======================================================================
81_v33 images = 65

SIMILARITY DISTRIBUTION
p00: 0.2815
p10: 0.6433
p25: 0.7267
p50: 0.8077
p75: 0.8444
p90: 0.8843
p95: 0.9246
p99: 0.9565
p100: 0.9794

MOST ISOLATED:
  image # 34  mean=0.4250
  image # 56  mean=0.6270
  image # 55  mean=0.6280
  image # 11  mean=0.6350
  image # 12  mean=0.6830

MOST CENTRAL:
  image # 22  mean=0.8350
  image # 17  mean=0.8341
  image # 18  mean=0.8290
  image # 19  mean=0.8239
  image # 27  mean=0.8236

======================================================================
82_v33 images = 67

SIMILARITY DISTRIBUTION
p00: 0.7381
p10: 0.8098
p25: 0.8363
p50: 0.8669
p75: 0.8927
p90: 0.9159
p95: 0.9421
p99: 0.9698
p100: 0.9841

MOST ISOLATED:
  image #  0  mean=0.8080
  image # 64  mean=0.8366
  image # 29  mean=0.8375
  image # 54  mean=0.8391
  image # 33  mean=0.8402

MOST CENTRAL:
  image # 40  mean=0.8980
  image # 39  mean=0.8959
  image # 38  mean=0.8931
  image # 42  mean=0.8912
  image # 23  mean=0.8884

---

### 🤖 **Assistant** — 2026-08-15 01:52:46

Вот теперь картина действительно интересная. **Подслепки нам нужны**, и результаты хорошо показывают почему.

### Что видно

`78`, `79`, `82` имеют достаточно плотное внутреннее пространство:

| Адрес | median | min | вывод |
|---|---:|---:|---|
| 78 | 0.853 | 0.595 | несколько заметно отличающихся ракурсов |
| 79 | 0.858 | 0.575 | то же |
| 80 | 0.889 | 0.774 | очень однородный набор |
| 81 | 0.808 | **0.282** | явно есть сильно отличающийся материал |
| 82 | 0.867 | 0.738 | довольно однородный |

Особенно важен **81**:

```text
image #34   mean = 0.425
```

при том, что остальные в основном значительно ближе друг к другу.

Это практически идеальный пример того, почему один centroid адреса недостаточен.

---

## Но я бы изменил первоначальную идею кластеризации

Я **не стал бы сейчас делать обычный KMeans**.

Для нашего проекта гораздо интереснее сделать **локальные подслепки**.

То есть:

```text
78
│
├── sub_01 → центральная группа кадров
├── sub_02 → другой ракурс
├── sub_03 → ещё один ракурс
└── sub_04 → редкий/отдельный ракурс
```

Причём подслепки **могут пересекаться**.

Например:

```text
sub_01:
  01 03 07 09 12 15 18 22 ...

sub_02:
  03 07 09 12 19 24 28 ...

sub_03:
  41 43 45 48 51 ...
```

Это лучше жёсткого:

```text
sub_01 = фотографии 1-20
sub_02 = 21-40
```

потому что два соседних ракурса могут иметь много общего.

### А самое главное

При распознавании нового фото мы хотим узнать:

> **"На какой конкретный участок пространства этот снимок больше всего похож?"**

а не:

> "На какой средний адрес он похож?"

---

# Предлагаю следующий этап

Сделаем отдельный тестовый генератор:

```text
make_subfingerprints.py
```

Он пока **ничего не меняет в `v33`**.

Для каждого адреса он:

1. берёт `embeddings.npy`;
2. нормализует DINO-векторы;
3. строит матрицу cosine similarity;
4. находит наиболее характерные кадры;
5. вокруг каждого характерного кадра собирает локальную группу;
6. удаляет слишком похожие центры;
7. сохраняет несколько подслепков;
8. сохраняет **индексы исходных фотографий**, чтобы мы всегда знали, какие реальные кадры стоят за subfingerprint.

Причём я предлагаю сохранить **не только centroid**, а:

```text
subfingerprint/
    centroid.npy
    member_indices.npy
    representatives.npy
    metadata.json
```

Например:

```text
78_v33/
└── subfingerprints/
    ├── sub_01/
    │   ├── centroid.npy
    │   ├── member_indices.npy
    │   ├── representatives.npy
    │   └── metadata.json
    ├── sub_02/
    ├── sub_03/
    └── ...
```

И `metadata.json` будет содержать примерно:

```text
sub_01
members: 17
center_image: photo043.JPG
images:
    photo003.JPG
    photo007.JPG
    photo012.JPG
    ...
```

### И ещё важное решение

Для **81** мы не будем насильно загонять `image #34` в один из обычных кластеров.

Если фотография действительно сильно отличается, подслепок должен уметь сказать:

```text
sub_05
type = isolated
image = 35.JPG
```

Это потенциально очень полезно: **редкий ракурс может оказаться как раз самым информативным при распознавании нового снимка**.

---

## Следующий шаг я бы сделал на одном адресе — 78

Не надо сразу прогонять все 95+ fingerprint.

Сначала строим:

```text
78_v33 → subfingerprints
```

и смотрим, что получилось.

После визуальной проверки/статистики уже применяем алгоритм ко всем адресам.

**Это правильнее, чем сейчас сразу генерировать сотни подслепков и потом разбираться, хорошо ли они получились.**

Если согласен, следующим шагом дам готовую команду, которая создаст **только тестовые подслепки для `78_v33`**, не изменяя сам `78_v33`.

---

### 👤 **User** — 2026-08-15 01:53:39

используются ли при слепке внешние фиксированные объекты типа светофоров и знаков, цвет домов сзади

---

### 🤖 **Assistant** — 2026-08-15 01:53:41

> **Searching the web**
>
>
> **Searching arxiv.org**
>
> 
>
> Worked for a couple of seconds

Да. **Часть таких объектов уже учитывается нашим текущим слепком, но не так явно и надёжно, как нам нужно.**

Сейчас у `v33` есть четыре составляющих:

- **DINOv2 global - 70%**: общий визуальный образ сцены. Он способен учитывать устойчивые визуальные признаки окружения - фасад, деревья, дорогу, характерные объекты и т.п. DINOv2 как раз предназначен для универсальных визуальных признаков, в том числе на уровне изображения и отдельных областей. ([arXiv](https://arxiv.org/abs/2304.07193?utm_source=chatgpt.com))
- **environment - 20%**: отдельный дескриптор окружения. Для нашей задачи это особенно важная часть.
- **color - 7%**: цветовая статистика изображения. Поэтому общий цвет домов/деревьев/неба **частично попадает сюда**.
- **spatial - 3%**: грубая пространственная структура изображения.

То есть, например:

> светофор слева + красно-белый знак справа + жёлтый дом на заднем плане + деревья + дорога

**не теряются полностью**.

Но есть принципиальная проблема.

### Сейчас система не знает, что именно является «якорем»

Для DINOv2:

```text
светофор
знак
дерево
дом
машина
дорога
```

- всё это просто части визуального признакового пространства.

Он не говорит нам:

> «Вот этот светофор - очень устойчивый объект данного адреса».

И именно поэтому **подслепки нам нужны**.

---

# Я бы сделал подслепок именно таким

Не просто:

```text
SUB_01 = 20 похожих фотографий
```

а условно:

```text
SUB_01
│
├── DINOv2 global
├── environment
├── color
├── spatial
│
└── устойчивые визуальные якоря
       │
       ├── светофор
       ├── дорожный знак
       ├── угол дома
       ├── дерево
       ├── фонарный столб
       └── характерный цвет фасада
```

Причём **OCR для этого вообще не нужен**.

Нам не обязательно знать:

> «это знак 3.24».

Нам гораздо важнее:

> **«в этом месте изображения регулярно присутствует один и тот же визуальный объект».**

Это уже задача визуального сопоставления.

---

## Особенно интересен цвет домов сзади

Вот это я бы **обязательно сохранял**.

Например, фотография рекламного щита может меняться:

```text
Фото A:
[щит] [серый дом] [дерево] [дорога]

Фото B:
[щит] [серый дом] [дерево] [дорога]

Фото C:
[щит] [серый дом] [дерево] [дорога]
```

Даже если сам рекламный щит совершенно другой, **окружение остаётся якорем адреса**.

И наоборот:

```text
Адрес 78:
щит + жёлтый дом + светофор + дерево

Адрес 91:
щит + жёлтый дом + светофор + дерево
```

Тогда одного глобального embedding недостаточно - нужно смотреть **пространственное расположение этих признаков**.

Именно поэтому у нас уже есть `spatial_embeddings`, но сейчас его вес всего **3%**.

Я бы **не стал пока менять эти веса**. Сначала сделаем подслепки и проверим их на реальных фотографиях.

---

# Самое важное изменение

Я предлагаю сделать два уровня.

### Уровень 1 - адрес

```text
78_v33
```

Это общий отпечаток всего места.

### Уровень 2 - подслепок

```text
78_v33
 ├── sub_01
 ├── sub_02
 ├── sub_03
 └── sub_04
```

Каждый `sub` соответствует **конкретному визуальному ракурсу/части окружения**.

И тогда новый снимок:

```text
                 НОВОЕ ФОТО
                      │
                      ▼
                   DINOv2
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
     адресные слепки          подслепки
          │                       │
          │                 78/sub_03  0.91
          │                 91/sub_01  0.73
          │                 82/sub_02  0.69
          │
          └──────────────┬───────────┘
                         ▼
                   КАНДИДАТ 78
                         │
                         ▼
                 уточнение по фото
```

И вот это уже будет гораздо ближе к **visual place recognition**, где задача как раз состоит в поиске места по устойчивым визуальным признакам при изменении ракурса, освещения и т.д. ([arXiv](https://arxiv.org/abs/2502.20676?utm_source=chatgpt.com))

### Поэтому ответ коротко:

**Да - светофоры, знаки, деревья, дома и их цвета уже частично участвуют в нынешнем `v33`. Но пока они представлены не как отдельные устойчивые якоря.**

И я бы сейчас **не добавлял OCR и не добавлял object detection**.

Сначала используем то, что уже есть:

**DINOv2 + environment + color + spatial → подслепки.**

А уже после первого теста подслепков станет видно, действительно ли нам не хватает явных объектов. Если не хватает - тогда можно будет добавить **локальные признаки/patch-level matching**, что будет намного полезнее для светофоров и знаков, чем OCR.

---

**Sources:**

- [DINOv2: Learning Robust Visual Features without Supervision](https://arxiv.org/abs/2304.07193?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-15 01:54:49

продолжай, я думаю, что при текущем алгоритме можно добиться приемлемого результата пусть даже с небольшим процентом ошибок

---

### 🤖 **Assistant** — 2026-08-15 01:54:50

> **Searching the web**
>
>
> **Searching arxiv.org**
>
> 
>
> Worked for a couple of seconds

Да, я с тобой согласен. **Не надо сейчас усложнять систему объектными детекторами, OCR или обучением новой модели.** При нашем объёме данных и текущем `v33` вполне реально получить практически полезный результат за счёт правильного использования уже имеющихся признаков.

Причём результаты, которые мы получили, это подтверждают.

### Я бы сейчас зафиксировал архитектуру

```text
ФОТО
  │
  ▼
DINOv2
  │
  ├── global 768
  ├── environment 640
  ├── color 48
  └── spatial 32
          │
          ▼
     SUBFINGERPRINTS
          │
          ▼
    TOP кандидатов
          │
          ▼
  первый кандидат адреса
          │
          ▼
  уточнение по фотографиям
```

Это вполне нормальный подход для visual place recognition: современные работы как раз используют DINOv2 как основу для устойчивых глобальных признаков, а затем улучшают retrieval за счёт пространственной/многоуровневой информации и повторного ранжирования. ([arXiv](https://arxiv.org/abs/2502.20676?utm_source=chatgpt.com))

## Что я предлагаю сделать сейчас

Не трогать `v33`.

Создать рядом:

```text
data/subfingerprints/
```

и построить там подслепки:

```text
data/subfingerprints/
├── 78_v33/
│   ├── sub_01/
│   ├── sub_02/
│   ├── sub_03/
│   └── ...
├── 79_v33/
├── 80_v33/
...
```

Но **первую версию я бы сделал очень простой**.

### Подслепок = группа похожих фотографий

Например для `78`:

```text
82 фотографий
       ↓
анализ похожести
       ↓
┌─────────────────────┐
│ sub_01  23 фото     │
│ sub_02  18 фото     │
│ sub_03  14 фото     │
│ sub_04  11 фото     │
│ sub_05   9 фото     │
│ sub_06   7 фото     │
└─────────────────────┘
```

При этом не обязательно, чтобы сумма была ровно 82: **одна фотография может принадлежать нескольким подслепкам**, если она находится между двумя ракурсами.

---

## И я бы не выбрасывал одиночные фотографии

Вот `81` очень показателен:

```text
image #34 → mean similarity 0.425
```

Это не обязательно плохая фотография.

Она может быть:

- другим направлением съёмки;
- крупным планом;
- фотографией перекрёстка;
- видом с другой стороны;
- снимком, где основной объект почти не виден.

И именно такой кадр может оказаться **идеальным ключом для будущей фотографии с такого же ракурса**.

Поэтому:

```text
sub_01 ... sub_05
```

и отдельно:

```text
rare / isolated
```

- это разумнее, чем просто выкинуть выбросы.

---

# А веса пока оставляем v33

Это очень важно.

Сейчас:

```text
global       0.70
environment  0.20
color        0.07
spatial      0.03
```

**Не будем их менять.**

Сначала проверим, что даёт сама идея подслепков.

Потому что сейчас у нас есть отличная возможность сделать эксперимент:

```text
Старый алгоритм
       VS
Старый алгоритм + subfingerprints
```

на одном и том же наборе.

И тогда мы получим реальную цифру:

> было 82% правильных первых кандидатов → стало 91%

или:

> было 91% → стало 94%

И уже после этого будем решать, нужны ли нам дополнительные признаки.

---

## Следующий шаг

Теперь я предлагаю **не делать ещё один диагностический скрипт**.

Мы уже достаточно посмотрели статистику.

Следующим сообщением я дам тебе **готовый `make_subfingerprints.py`**, который:

- работает через `uv`;
- использует существующие `*_v33`;
- не требует `sklearn`;
- не требует DINOv2;
- не изменяет существующие fingerprint;
- создаёт отдельные `data/subfingerprints`;
- сохраняет индексы исходных фотографий;
- создаёт centroid каждого подслепка;
- сохраняет несколько представителей;
- умеет отдельно сохранять изолированные кадры.

И сначала запустим его **только на `78_v33`**.

Если результат по структуре нормальный - одной командой прогоняем уже все `*_v33`.

Это сейчас самый рациональный путь.

---

**Sources:**

- [SciceVPR: Stable Cross-Image Correlation Enhanced Model for Visual Place Recognition](https://arxiv.org/abs/2502.20676?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-15 01:55:09

продолжаем

---

### 🤖 **Assistant** — 2026-08-15 01:55:09

Продолжаем. Сейчас делаем **первую рабочую версию генератора подслепков**, но без изменения существующих `v33`.

Я предлагаю начать с алгоритма **графовых локальных групп**, а не KMeans. Он лучше подходит к нашей задаче: фотографии одного адреса могут иметь несколько ракурсов, а некоторые кадры могут быть переходными между группами.

Сначала создадим скрипт.

```bash id="7zqv3m"
cd ~/projects/scene_fingerprint_mvp_v02

mkdir -p scripts data/subfingerprints

cat > scripts/make_subfingerprints.py <<'PY'
#!/usr/bin/env python3

import argparse
import json
import shutil
from pathlib import Path

import numpy as np

def normalize(x):
    x = x.astype(np.float32, copy=False)
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.maximum(n, 1e-12)

def build_similarity(X):
    X = normalize(X)
    return X @ X.T

def make_groups(
    similarity,
    min_similarity=0.84,
    seed_similarity=0.88,
    min_group_size=5,
):
    """
    Строит перекрывающиеся локальные группы.

    seed:
        кадр должен иметь достаточно сильное локальное окружение.

    member:
        кадр попадает в группу, если достаточно похож
        на центральный кадр.

    Группы могут пересекаться.
    """

    n = len(similarity)

    # Среднее сходство каждой фотографии.
    mean_sim = (similarity.sum(axis=1) - 1.0) / max(n - 1, 1)

    # Чем выше среднее сходство, тем более центральный кадр.
    order = np.argsort(mean_sim)[::-1]

    groups = []
    used_as_seed = set()

    for seed in order:
        if seed in used_as_seed:
            continue

        # Кандидаты вокруг seed.
        members = np.where(similarity[seed] >= min_similarity)[0]

        # Сам seed обязательно входит.
        if seed not in members:
            members = np.append(members, seed)

        members = np.unique(members)

        if len(members) < min_group_size:
            continue

        # Для seed нужен достаточно плотный локальный кластер.
        local = members[members != seed]

        if len(local) > 0:
            local_mean = float(similarity[seed, local].mean())
        else:
            local_mean = 1.0

        if local_mean < seed_similarity:
            continue

        # Не создаём практически одинаковые группы.
        duplicate = False

        current = set(int(x) for x in members)

        for g in groups:
            old = set(g["members"])

            intersection = len(current & old)
            union = len(current | old)

            jaccard = intersection / max(union, 1)

            if jaccard >= 0.75:
                duplicate = True
                break

        if duplicate:
            continue

        groups.append(
            {
                "seed": int(seed),
                "members": sorted(int(x) for x in members),
                "mean_similarity": local_mean,
            }
        )

        used_as_seed.add(int(seed))

    return groups, mean_sim

def add_isolated_groups(
    groups,
    mean_sim,
    similarity,
    min_mean_similarity=0.60,
):
    """
    Сохраняет редкие кадры как отдельные subfingerprint.

    Это особенно важно для случаев вроде 81_v33,
    где один кадр сильно отличается от остальных.
    """

    assigned = set()

    for g in groups:
        assigned.update(g["members"])

    n = len(mean_sim)

    for i in range(n):
        if i in assigned:
            continue

        # Если кадр действительно не похож на основную массу,
        # сохраняем его как отдельный subfingerprint.
        if mean_sim[i] < min_mean_similarity:
            groups.append(
                {
                    "seed": int(i),
                    "members": [int(i)],
                    "mean_similarity": float(mean_sim[i]),
                    "isolated": True,
                }
            )

    return groups

def create_subfingerprint(
    source,
    output,
    group_id,
    group,
    embeddings,
    environment,
    color,
    spatial,
    image_names,
    representatives_per_group=5,
):
    members = np.asarray(group["members"], dtype=np.int32)

    # Глобальный centroid.
    global_vectors = embeddings[members]
    centroid = global_vectors.mean(axis=0)
    centroid /= max(np.linalg.norm(centroid), 1e-12)

    # Остальные descriptor'ы тоже усредняем.
    env = environment[members].mean(axis=0)
    col = color[members].mean(axis=0)
    spa = spatial[members].mean(axis=0)

    # Представители — реальные фотографии,
    # наиболее близкие к centroid.
    X = normalize(global_vectors)

    c = centroid.reshape(1, -1)
    scores = (X @ c.T).reshape(-1)

    order = np.argsort(scores)[::-1]

    rep_count = min(
        representatives_per_group,
        len(members),
    )

    rep_local = order[:rep_count]
    rep_indices = members[rep_local]

    out = output / group_id
    out.mkdir(parents=True, exist_ok=True)

    np.save(out / "centroid.npy", centroid.astype(np.float32))
    np.save(out / "environment.npy", env.astype(np.float32))
    np.save(out / "color.npy", col.astype(np.float32))
    np.save(out / "spatial.npy", spa.astype(np.float32))

    np.save(out / "member_indices.npy", members)

    np.save(
        out / "representative_indices.npy",
        rep_indices.astype(np.int32),
    )

    np.save(
        out / "representatives.npy",
        embeddings[rep_indices].astype(np.float32),
    )

    metadata = {
        "source_fingerprint": source.name,
        "subfingerprint": group_id,
        "members": int(len(members)),
        "isolated": bool(group.get("isolated", False)),
        "seed_index": int(group["seed"]),
        "seed_image": image_names[group["seed"]],
        "mean_similarity_to_seed": float(
            group["mean_similarity"]
        ),
        "images": [
            image_names[int(i)]
            for i in members
        ],
        "representatives": [
            image_names[int(i)]
            for i in rep_indices
        ],
    }

    with open(
        out / "metadata.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metadata,
            f,
            ensure_ascii=False,
            indent=2,
        )

def process_fingerprint(
    fingerprint,
    fingerprints_root,
    output_root,
    min_similarity,
    seed_similarity,
    min_group_size,
):
    source = fingerprints_root / fingerprint

    if not source.exists():
        raise FileNotFoundError(source)

    required = [
        "embeddings.npy",
        "environment_embeddings.npy",
        "color_embeddings.npy",
        "spatial_embeddings.npy",
        "metadata.json",
    ]

    for name in required:
        if not (source / name).exists():
            raise FileNotFoundError(
                f"{source / name} not found"
            )

    embeddings = np.load(
        source / "embeddings.npy"
    ).astype(np.float32)

    environment = np.load(
        source / "environment_embeddings.npy"
    ).astype(np.float32)

    color = np.load(
        source / "color_embeddings.npy"
    ).astype(np.float32)

    spatial = np.load(
        source / "spatial_embeddings.npy"
    ).astype(np.float32)

    with open(
        source / "metadata.json",
        "r",
        encoding="utf-8",
    ) as f:
        metadata = json.load(f)

    image_names = metadata["image_names"]

    if len(image_names) != len(embeddings):
        raise RuntimeError(
            f"{fingerprint}: image_names={len(image_names)} "
            f"but embeddings={len(embeddings)}"
        )

    print()
    print("=" * 70)
    print(f"FINGERPRINT: {fingerprint}")
    print(f"IMAGES:      {len(embeddings)}")

    similarity = build_similarity(embeddings)

    groups, mean_sim = make_groups(
        similarity,
        min_similarity=min_similarity,
        seed_similarity=seed_similarity,
        min_group_size=min_group_size,
    )

    groups = add_isolated_groups(
        groups,
        mean_sim,
        similarity,
    )

    # Сортировка:
    # сначала большие группы, затем одиночные.
    groups.sort(
        key=lambda g: (
            bool(g.get("isolated", False)),
            -len(g["members"]),
        )
    )

    output = output_root / fingerprint

    if output.exists():
        shutil.rmtree(output)

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary = {
        "fingerprint": fingerprint,
        "images": len(embeddings),
        "subfingerprints": len(groups),
        "parameters": {
            "min_similarity": min_similarity,
            "seed_similarity": seed_similarity,
            "min_group_size": min_group_size,
        },
        "groups": [],
    }

    for number, group in enumerate(groups, start=1):
        group_id = f"sub_{number:02d}"

        create_subfingerprint(
            source=source,
            output=output,
            group_id=group_id,
            group=group,
            embeddings=embeddings,
            environment=environment,
            color=color,
            spatial=spatial,
            image_names=image_names,
        )

        summary["groups"].append(
            {
                "id": group_id,
                "members": len(group["members"]),
                "isolated": bool(
                    group.get("isolated", False)
                ),
                "seed_index": group["seed"],
                "seed_image": image_names[group["seed"]],
                "mean_similarity": group["mean_similarity"],
            }
        )

    with open(
        output / "metadata.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(f"SUBFINGERPRINTS: {len(groups)}")

    for g in summary["groups"]:
        print(
            f"  {g['id']:8s}"
            f" members={g['members']:3d}"
            f" seed={g['seed_index']:3d}"
            f" mean={g['mean_similarity']:.4f}"
            f"{' ISOLATED' if g['isolated'] else ''}"
        )

    print()
    print(f"OUTPUT: {output}")

def main():
    parser = argparse.ArgumentParser(
        description="Create subfingerprints from existing v3.3 fingerprints"
    )

    parser.add_argument(
        "fingerprint",
        help="Fingerprint ID, e.g. 78_v33",
    )

    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.84,
    )

    parser.add_argument(
        "--seed-similarity",
        type=float,
        default=0.88,
    )

    parser.add_argument(
        "--min-group-size",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--fingerprints-root",
        default="data/fingerprints",
    )

    parser.add_argument(
        "--output-root",
        default="data/subfingerprints",
    )

    args = parser.parse_args()

    process_fingerprint(
        fingerprint=args.fingerprint,
        fingerprints_root=Path(
            args.fingerprints_root
        ),
        output_root=Path(
            args.output_root
        ),
        min_similarity=args.min_similarity,
        seed_similarity=args.seed_similarity,
        min_group_size=args.min_group_size,
    )

if __name__ == "__main__":
    main()
PY

chmod +x scripts/make_subfingerprints.py
```

Теперь **только для 78**:

```bash id="w5p0au"
cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/make_subfingerprints.py 78_v33
```

### Что должно появиться

Примерно:

```text
data/subfingerprints/78_v33/
├── metadata.json
├── sub_01/
│   ├── centroid.npy
│   ├── environment.npy
│   ├── color.npy
│   ├── spatial.npy
│   ├── member_indices.npy
│   ├── representative_indices.npy
│   ├── representatives.npy
│   └── metadata.json
├── sub_02/
...
```

**Пока не запускай на 79–95.** Сначала посмотрим, сколько групп алгоритм получил для `78` и какие размеры групп.

Пришли вывод команды `uv run python scripts/make_subfingerprints.py 78_v33`.

---

### 👤 **User** — 2026-08-15 01:55:50

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/make_subfingerprints.py 78_v33

======================================================================
FINGERPRINT: 78_v33
IMAGES:      82

SUBFINGERPRINTS: 11
  sub_01   members= 66 seed= 74 mean=0.9028
  sub_02   members= 50 seed= 40 mean=0.8944
  sub_03   members= 48 seed= 29 mean=0.8939
  sub_04   members= 45 seed= 67 mean=0.8813
  sub_05   members= 34 seed= 45 mean=0.8886
  sub_06   members= 30 seed= 65 mean=0.8906
  sub_07   members= 21 seed= 66 mean=0.9014
  sub_08   members= 14 seed= 19 mean=0.8876
  sub_09   members= 11 seed= 34 mean=0.8995
  sub_10   members= 10 seed= 16 mean=0.8916
  sub_11   members=  8 seed= 12 mean=0.8813

OUTPUT: data/subfingerprints/78_v33
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:55:54

Да. **Результат хороший как первый эксперимент, но алгоритм сейчас слишком щедрый.**

Для `78_v33`:

```text
82 исходных фото
11 subfingerprints
суммарно 337 попаданий
```

То есть подслепки сильно пересекаются. Это ожидаемо из-за нашей идеи перекрывающихся групп, но сейчас перекрытие **слишком большое**.

Например:

```text
sub_01 = 66 из 82
sub_02 = 50
sub_03 = 48
...
```

Это уже почти не «подслепки», а несколько разных способов представить один и тот же адрес.

### Что нам на самом деле нужно

Я бы стремился примерно к такому:

```text
78_v33 — 82 фото

sub_01 → 25–40 фото
sub_02 → 20–35 фото
sub_03 → 15–30 фото
sub_04 → 10–25 фото
...
```

с умеренным пересечением.

При этом:

**не нужно делать subfingerprint для каждой мелкой вариации.**

Наша задача — получить несколько **устойчивых визуальных состояний адреса**.

---

## И ещё один важный момент

Сейчас группы строятся только по:

```text
DINOv2 global
```

а мы уже договорились, что для конечного подслепка должны использоваться:

```text
global       70%
environment  20%
color         7%
spatial       3%
```

Поэтому текущий результат я рассматриваю именно как **тест структуры**, а не как финальный алгоритм.

---

# Давай сейчас не переделывать скрипт вслепую

У нас есть очень полезный следующий эксперимент.

Посмотрим, **какие фотографии попали в каждый подслепок** и насколько группы реально отличаются.

Выполни:

```bash id="m6t4jg"
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

root = Path("data/subfingerprints/78_v33")

for p in sorted(root.glob("sub_*")):
    if not p.is_dir():
        continue

    with open(p / "metadata.json", "r", encoding="utf-8") as f:
        m = json.load(f)

    print()
    print("=" * 70)
    print(
        f"{m['subfingerprint']} "
        f"members={m['members']} "
        f"seed={m['seed_index']} "
        f"seed_image={m['seed_image']} "
        f"mean={m['mean_similarity_to_seed']:.4f}"
    )

    print("REPRESENTATIVES:")
    for x in m["representatives"]:
        print("  ", x)

    print("MEMBERS:")
    print("  " + ", ".join(m["images"]))
PY
```

И ещё один короткий тест — **пересечение групп**:

```bash id="e6qz1q"
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

root = Path("data/subfingerprints/78_v33")

groups = []

for p in sorted(root.glob("sub_*")):
    if not p.is_dir():
        continue

    with open(p / "metadata.json", "r", encoding="utf-8") as f:
        m = json.load(f)

    groups.append(
        (
            m["subfingerprint"],
            set(m["images"])
        )
    )

print("=" * 70)
print("GROUP OVERLAP")
print("=" * 70)

for i in range(len(groups)):
    for j in range(i + 1, len(groups)):
        a_name, a = groups[i]
        b_name, b = groups[j]

        inter = len(a & b)
        union = len(a | b)
        jaccard = inter / union

        if jaccard >= 0.20:
            print(
                f"{a_name} <-> {b_name}: "
                f"intersection={inter:2d} "
                f"jaccard={jaccard:.3f}"
            )
PY
```

### Зачем нам это

Если увидим:

```text
sub_01:
photo043
photo044
photo045
...

sub_02:
photo043
photo044
photo045
...
```

то алгоритм действительно делает почти дубликаты.

А если:

```text
sub_01 → фасадный ракурс
sub_02 → дорога/перекрёсток
sub_03 → боковой фасад
sub_04 → дальний план
```

то **мы попали ровно туда, куда хотели**.

И вот здесь особенно интересно будет посмотреть на `78`, потому что у него `p50=0.8526`, то есть пространство фотографий достаточно разнообразное.

**Пока ничего не меняем.** Пришли оба вывода — по ним уже настроим размер и перекрытие подслепков, а затем подключим к ним `environment + color + spatial`.

---

