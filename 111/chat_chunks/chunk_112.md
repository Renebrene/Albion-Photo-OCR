## СЕССИЯ: Продолжение разговора 1

**Создано:** 2026-08-18 12:11:53
**Обновлено:** 2026-08-19 17:07:58
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8421d7-3160-83ea-be54-4a2ad097babc](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8421d7-3160-83ea-be54-4a2ad097babc)

---

### 👤 **User** — 2026-08-18 12:21:40

"flat dense"
            )

        ui.separator().classes("my-2")

        ui.label(
            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
        ).classes(
            "text-sm"
        )

        run_button = ui.button(
            "▶  ЗАПУСТИТЬ ОБРАБОТКУ",
            on_click=run_pipeline,
        ).props(
            "unelevated"
        ).classes(
            "w-full text-lg font-bold"
        )

        status_label

        ui.label(
            "Главная рабочая операция"
        ).classes(
            "text-xs text-grey-6"
        )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== PREVIEW RELATED FILES ====="
find . -type f \
    $ -iname "*.py" -o -iname "*.sh" $ \
    -not -path "./.venv/*" \
    -not -path "./.git/*" \
    | while read f; do
        grep -qiE "preview|thumbnail|resize|Image\.thumbnail|Image\.resize" "$f" \
        && echo "$f"
    done
===== PREVIEW RELATED FILES =====
./app/web/components/photos.py
./app/web/components/technical.py
./app/core/scene_analyzer.py
./app/ocr/plate_detector.py
./fix_v31_final.sh
./upgrade_v31.sh
./scripts/banner_model_compare_v04.py
./scripts/create_previews_v01.py
./scripts/banner_qwen25vl_test_v01.py
./scripts/banner_model_compare_v05.py
./scripts/banner_llm_full_v02.py
./scripts/banner_qwen4b_test_v01.py
./scripts/banner_llm_folder_search_v01.py
./scripts/banner_database_v02.py
./scripts/make_subcluster_contact.py
./scripts/banner_database_v01.py
./scripts/qwen_prompt_ablation.py
./scripts/banner_model_compare_v03.py
./upgrade_patch_tokens.sh
./upgrade_v3.sh
./upgrade_v31_final.sh
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo "===== COPY / RESIZE LOGIC ====="

grep -R -n -E \
"Image\.thumbnail|Image\.resize|shutil\.copy|copy2|copyfile|thumbnail|preview" \
scripts app \
--include="*.py" \
--include="*.sh" \
| grep -v "__pycache__" \
| grep -v "\.bak" \
| grep -v "\.before" \
| head -200
===== COPY / RESIZE LOGIC =====
scripts/sort_neighbor_v35_benchmark.py:232:        shutil.copy2(src, dst)
scripts/sort_test_and_report_v2.py:175:        shutil.copy2(source, destination)
scripts/sort_test_and_report.py:136:        shutil.copy2(src, dst)
scripts/sort_margin005_best.py:31:        shutil.copy2(src, dst)
scripts/sort_margin005_best.py:43:            shutil.copy2(src, candidate)
scripts/create_previews_v01.py:19:def create_preview(source: Path, destination: Path):
scripts/create_previews_v01.py:30:        image.thumbnail(
scripts/create_previews_v01.py:48:        description="Create web previews for processed photos"
scripts/create_previews_v01.py:109:            result = create_preview(
scripts/banner_llm_full_v02.py:30:    img.thumbnail(
scripts/sort_neighbor_v34.py:266:        shutil.copy2(
scripts/sort_test_and_report_hybrid_v12.py:175:        shutil.copy2(source, destination)
scripts/sort_sequence_v38_1_subtest.py:258:        shutil.copy2(
scripts/search_banners_v01.py:226:            shutil.copy2(
scripts/sort_sequence_v39.py:258:        shutil.copy2(
scripts/run_hybrid_v12.py:445:        shutil.copy2(
scripts/banner_llm_folder_search_v01.py:45:    img.thumbnail(
scripts/banner_llm_folder_search_v01.py:234:                shutil.copy2(
scripts/build_subfingerprints_exp.py:53:                shutil.copy2(
scripts/sort_neighbor_v37.py:260:    shutil.copy2(src, destination / src.name)
scripts/sort_baseline.py:72:        shutil.copy2(src, dst)
scripts/banner_search_v02.py:119:            shutil.copy2(
scripts/banner_database_v02.py:135:    img.thumbnail(
scripts/make_subcluster_contact.py:38:        im.thumbnail(THUMB)
scripts/banner_search_v01.py:95:            shutil.copy2(
scripts/build_subfingerprint_database.py:85:                shutil.copy2(
scripts/sort_neighbor_v36_img.py:266:        shutil.copy2(
scripts/sort_neighbor_v36.py:266:        shutil.copy2(
scripts/sort_sequence_v38.py:228:        shutil.copy2(
scripts/banner_database_v01.py:83:    img.thumbnail(
scripts/sort_sequence_sub_v01.py:257:        shutil.copy2(
scripts/export_subclusters.py:183:                    shutil.copy2(
scripts/sort_sequence_v38_1.py:258:        shutil.copy2(
scripts/export_visual_compare.py:36:        shutil.copy2(src,dst)
scripts/export_visual_compare.py:68:        shutil.copy2(src,dst)
scripts/sort_neighbor_v35.py:286:        shutil.copy2(
app/web/components/photos.py:19:    / "preview"
app/web/components/photos.py:51:def get_latest_preview_root():
app/web/components/photos.py:52:    """Return the newest daily preview directory."""
app/web/components/photos.py:71:def get_preview_path(photo_path):
app/web/components/photos.py:72:    """Map daily output photo to its preview image."""
app/web/components/photos.py:73:    preview_root = get_latest_preview_root()
app/web/components/photos.py:76:    if preview_root is None or daily_root is None:
app/web/components/photos.py:84:    preview_path = preview_root / relative
app/web/components/photos.py:86:    if preview_path.exists():
app/web/components/photos.py:87:        return preview_path
app/web/components/photos.py:1111:                                    preview_path = (
app/web/components/photos.py:1112:                                        get_preview_path(
app/web/components/photos.py:1118:                                        preview_path
app/web/components/photos.py:1119:                                        if preview_path
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:21:42

Отлично. Теперь уже точно знаем: **генератор preview существует**, и это `scripts/create_previews_v01.py`.

Причём текущий `photos.py` уже полностью подготовлен для него:

```text
output/daily/<run>/
        ↓
preview/daily/<run>/
        ↓
get_preview_path()
        ↓
GRID
```

Осталось понять только **какие аргументы принимает `create_previews_v01.py`** и был ли он раньше частью запуска.

Выполни две команды:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== CREATE PREVIEWS SCRIPT ====="
cat scripts/create_previews_v01.py

echo
echo "===== WHO CALLS IT ====="
grep -R -n "create_previews_v01" . \
    --exclude-dir=.venv \
    --exclude-dir=.git \
    --exclude="*.pyc"
```

После этого я дам **одну конкретную правку** в pipeline, чтобы после сегодняшнего `20260818_115048` автоматически создавался:

```text
data/preview/daily/20260818_115048/
```

и grid сразу видел новые фото.

Пока ничего вручную не создаём и старый preview от 16-го не удаляем.

---

### 👤 **User** — 2026-08-18 12:22:57

scripts/build_subfingerprints_exp.py:53:                shutil.copy2(
scripts/sort_neighbor_v37.py:260:    shutil.copy2(src, destination / src.name)
scripts/sort_baseline.py:72:        shutil.copy2(src, dst)
scripts/banner_search_v02.py:119:            shutil.copy2(
scripts/banner_database_v02.py:135:    img.thumbnail(
scripts/make_subcluster_contact.py:38:        im.thumbnail(THUMB)
scripts/banner_search_v01.py:95:            shutil.copy2(
scripts/build_subfingerprint_database.py:85:                shutil.copy2(
scripts/sort_neighbor_v36_img.py:266:        shutil.copy2(
scripts/sort_neighbor_v36.py:266:        shutil.copy2(
scripts/sort_sequence_v38.py:228:        shutil.copy2(
scripts/banner_database_v01.py:83:    img.thumbnail(
scripts/sort_sequence_sub_v01.py:257:        shutil.copy2(
scripts/export_subclusters.py:183:                    shutil.copy2(
scripts/sort_sequence_v38_1.py:258:        shutil.copy2(
scripts/export_visual_compare.py:36:        shutil.copy2(src,dst)
scripts/export_visual_compare.py:68:        shutil.copy2(src,dst)
scripts/sort_neighbor_v35.py:286:        shutil.copy2(
app/web/components/photos.py:19:    / "preview"
app/web/components/photos.py:51:def get_latest_preview_root():
app/web/components/photos.py:52:    """Return the newest daily preview directory."""
app/web/components/photos.py:71:def get_preview_path(photo_path):
app/web/components/photos.py:72:    """Map daily output photo to its preview image."""
app/web/components/photos.py:73:    preview_root = get_latest_preview_root()
app/web/components/photos.py:76:    if preview_root is None or daily_root is None:
app/web/components/photos.py:84:    preview_path = preview_root / relative
app/web/components/photos.py:86:    if preview_path.exists():
app/web/components/photos.py:87:        return preview_path
app/web/components/photos.py:1111:                                    preview_path = (
app/web/components/photos.py:1112:                                        get_preview_path(
app/web/components/photos.py:1118:                                        preview_path
app/web/components/photos.py:1119:                                        if preview_path
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== CREATE PREVIEWS SCRIPT ====="
cat scripts/create_previews_v01.py

echo
echo "===== WHO CALLS IT ====="
grep -R -n "create_previews_v01" . \
    --exclude-dir=.venv \
    --exclude-dir=.git \
    --exclude="*.pyc"
===== CREATE PREVIEWS SCRIPT =====
#!/usr/bin/env python3

import argparse
from pathlib import Path
from PIL import Image

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

MAX_SIZE = 1200
QUALITY = 82

def create_preview(source: Path, destination: Path):
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if destination.exists():
        return "skip"

    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail(
            (MAX_SIZE, MAX_SIZE),
            Image.Resampling.LANCZOS,
        )

        image.save(
            destination,
            "JPEG",
            quality=QUALITY,
            optimize=True,
        )

    return "created"

def main():

    parser = argparse.ArgumentParser(
        description="Create web previews for processed photos"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Hybrid output directory",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Preview output directory",
    )

    args = parser.parse_args()

    input_dir = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()

    if not input_dir.exists():
        raise SystemExit(
            f"ERROR: input directory does not exist: {input_dir}"
        )

    files = sorted(
        [
            p
            for p in input_dir.rglob("*")
            if p.is_file()
            and p.suffix.lower() in IMAGE_EXTENSIONS
        ],
        key=lambda p: str(p).lower(),
    )

    print("=" * 80)
    print("PHOTO PREVIEW WORKER V01")
    print("=" * 80)
    print("INPUT :", input_dir)
    print("OUTPUT:", output_dir)
    print("FILES :", len(files))
    print("MAX   :", MAX_SIZE)
    print("QUALITY:", QUALITY)
    print()

    created = 0
    skipped = 0
    errors = 0

    for index, source in enumerate(files, 1):

        relative = source.relative_to(input_dir)

        destination = (
            output_dir
            / relative.parent
            / f"{source.stem}.jpg"
        )

        try:

            result = create_preview(
                source,
                destination,
            )

            if result == "created":
                created += 1
            else:
                skipped += 1

            if index % 25 == 0 or index == len(files):
                print(
                    f"[{index}/{len(files)}] "
                    f"created={created} "
                    f"skipped={skipped} "
                    f"errors={errors}",
                    flush=True,
                )

        except Exception as error:

            errors += 1

            print(
                f"ERROR: {source}: {error}",
                flush=True,
            )

    print()
    print("=" * 80)
    print("PREVIEW FINISHED")
    print("=" * 80)
    print("Created:", created)
    print("Skipped:", skipped)
    print("Errors :", errors)
    print("Output :", output_dir)
    print()

if __name__ == "__main__":
    main()

===== WHO CALLS IT =====

^C
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== CREATE PREVIEWS SCRIPT ====="
cat scripts/create_previews_v01.py

echo
echo "===== WHO CALLS IT ====="
grep -R -n "create_previews_v01" . \
    --exclude-dir=.venv \
    --exclude-dir=.git \
    --exclude="*.pyc"
===== CREATE PREVIEWS SCRIPT =====
#!/usr/bin/env python3

import argparse
from pathlib import Path
from PIL import Image

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

MAX_SIZE = 1200
QUALITY = 82

def create_preview(source: Path, destination: Path):
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if destination.exists():
        return "skip"

    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail(
            (MAX_SIZE, MAX_SIZE),
            Image.Resampling.LANCZOS,
        )

        image.save(
            destination,
            "JPEG",
            quality=QUALITY,
            optimize=True,
        )

    return "created"

def main():

    parser = argparse.ArgumentParser(
        description="Create web previews for processed photos"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Hybrid output directory",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Preview output directory",
    )

    args = parser.parse_args()

    input_dir = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()

    if not input_dir.exists():
        raise SystemExit(
            f"ERROR: input directory does not exist: {input_dir}"
        )

    files = sorted(
        [
            p
            for p in input_dir.rglob("*")
            if p.is_file()
            and p.suffix.lower() in IMAGE_EXTENSIONS
        ],
        key=lambda p: str(p).lower(),
    )

    print("=" * 80)
    print("PHOTO PREVIEW WORKER V01")
    print("=" * 80)
    print("INPUT :", input_dir)
    print("OUTPUT:", output_dir)
    print("FILES :", len(files))
    print("MAX   :", MAX_SIZE)
    print("QUALITY:", QUALITY)
    print()

    created = 0
    skipped = 0
    errors = 0

    for index, source in enumerate(files, 1):

        relative = source.relative_to(input_dir)

        destination = (
            output_dir
            / relative.parent
            / f"{source.stem}.jpg"
        )

        try:

            result = create_preview(
                source,
                destination,
            )

            if result == "created":
                created += 1
            else:
                skipped += 1

            if index % 25 == 0 or index == len(files):
                print(
                    f"[{index}/{len(files)}] "
                    f"created={created} "
                    f"skipped={skipped} "
                    f"errors={errors}",
                    flush=True,
                )

        except Exception as error:

            errors += 1

            print(
                f"ERROR: {source}: {error}",
                flush=True,
            )

    print()
    print("=" * 80)
    print("PREVIEW FINISHED")
    print("=" * 80)
    print("Created:", created)
    print("Skipped:", skipped)
    print("Errors :", errors)
    print("Output :", output_dir)
    print()

if __name__ == "__main__":
    main()

===== WHO CALLS IT =====
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:22:57

Да. Причина теперь ясна.

**Сортировка сегодня создала 530 фото:**

```text
data/output/daily/20260818_115048/
```

но **preview для этого запуска вообще не создавался**. Поэтому grid пытается найти:

```text
data/preview/daily/20260818_115048/...
```

не находит его и фактически остаётся без превью.

При этом `create_previews_v01.py` уже готов и корректно умеет делать именно то, что нужно. Просто **нигде не вызывается**.

### Сейчас лучше не трогать `photos.py`

Он уже правильно настроен:

```text
последний output/daily
        ↓
фото
        ↓
соответствующий preview/daily
        ↓
grid
```

Нужно подключить генератор preview **после Hybrid-сортировки и до Qwen**.

Но сначала я бы сделал безопасный тест на уже существующем запуске `20260818_115048`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

/home/alexice/.local/bin/uv run python scripts/create_previews_v01.py \
    --input data/output/daily/20260818_115048 \
    --output data/preview/daily/20260818_115048
```

После завершения:

```bash
echo "===== OUTPUT ====="
find data/output/daily/20260818_115048 -type f | wc -l

echo "===== PREVIEWS ====="
find data/preview/daily/20260818_115048 -type f | wc -l

echo "===== SAMPLE ====="
find data/preview/daily/20260818_115048 -type f | head -10
```

Ожидаем примерно:

```text
OUTPUT
530

PREVIEWS
530
```

После этого **перезапусти web-интерфейс и обнови страницу** — новые 530 фотографий должны появиться в grid.

---

### А затем сделаем постоянное исправление

В `scripts/run_daily_hybrid_v12.sh` после:

```bash
/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
    --input "$INPUT" \
    --output "$OUTPUT" \
    --first-address 78 \
    --last-address 95
```

добавим:

```bash
PREVIEW="$PROJECT/data/preview/daily/$TIMESTAMP"

echo
echo "================================================================================"
echo "CREATING WEB PREVIEWS"
echo "================================================================================"
echo
echo "INPUT : $OUTPUT"
echo "OUTPUT: $PREVIEW"
echo

/home/alexice/.local/bin/uv run python scripts/create_previews_v01.py \
    --input "$OUTPUT" \
    --output "$PREVIEW"
```

Тогда каждый новый запуск будет автоматически создавать пару:

```text
data/output/daily/20260818_115048/     ← оригиналы
data/preview/daily/20260818_115048/    ← thumbnails
```

И **Qwen при этом вообще не затрагиваем**.

Сначала сделаем тест на сегодняшних 530 — это самый безопасный вариант.

---

### 👤 **User** — 2026-08-18 12:26:04

потом квеновское описание будет добавлено в епрвью автоматически?

---

### 🤖 **Assistant** — 2026-08-18 12:26:04

Да, **но не самим `create_previews_v01.py`**.

Сейчас цепочка у нас такая:

```text
DINO v33
   ↓
Hybrid v12
   ↓
data/output/daily/20260818_115048/
   ↓
создание preview
   ↓
data/preview/daily/20260818_115048/
   ↓
Qwen3-VL 4B
   ↓
PostgreSQL / metadata
   ↓
grid
```

А главное: **Qwen не должен физически переписывать JPG-preview**. Он создаёт описание/метаданные, а grid берёт их по соответствующему пути фотографии.

У нас уже есть связка через PostgreSQL:

```python
PHOTO_RECORD_INDEX
```

и поля:

```text
description
client
brand
category
text_json
colors_json
objects_json
environment_json
...
```

То есть правильная архитектура:

**фото → preview + Qwen-анализ → одна карточка в grid.**

При этом для сегодняшних 530 фото сначала нужно проверить, **куда именно Qwen сейчас записал описания для запуска `20260818_115048` и совпадают ли пути с `data/output/daily/20260818_115048/...`**.

Это важно проверить до изменения pipeline, чтобы не сломать уже работающую часть.

Можем следующим шагом проверить **одну конкретную фотографию: JPG → Qwen JSON → PostgreSQL → запись, которую видит grid**. Тогда будет понятно, что вся цепочка уже связывается автоматически.

---

### 👤 **User** — 2026-08-18 12:27:19

нужно будет еще добавить отображение прогесса в Квен и обработку, который будет виден даже после перезахода в настройки и возможность прерватьт процессы

---

### 🤖 **Assistant** — 2026-08-18 12:27:19

Да. И я бы сейчас это заложил **как отдельный механизм состояния фоновых задач**, а не просто текст в `status_label`.

Сейчас у нас слабое место: прогресс Qwen живёт внутри текущего UI-процесса. При перезаходе в настройки/обновлении страницы его можно потерять.

Нам нужно сделать так:

```text
                 ┌──────────────────────────┐
                 │      DAILY PROCESS        │
                 │                          │
                 │ DINO → Hybrid → Preview  │
                 │        → Qwen → DB       │
                 └────────────┬─────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ PROCESS STATE  │
                    │   PostgreSQL   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
          Web UI #1       Web UI #2      после reload
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                     ОДИН прогресс
```

### Что будет отображаться

Например:

**Обработка фотографий**

```text
● DINO / Hybrid
████████████████████░░░░  82%

530 / 647 фото
```

Затем:

```text
✓ Hybrid v12 завершён

● Создание preview
████████████████████████  100%

530 / 530
```

И:

```text
● Qwen3-VL 4B
██████████░░░░░░░░░░░░░░  43%

228 / 530 фотографий

Текущее:
Вавилова52_12.JPG
```

А после завершения:

```text
✓ Обработка завершена

530 / 530
Время: 18 мин 42 сек
```

### И обязательно кнопка

```text
[ ⏹ ОСТАНОВИТЬ ]
```

Причём остановка должна быть **настоящей**, а не просто скрывать UI.

То есть:

```text
RUNNING
   ↓
STOP REQUEST
   ↓
Qwen subprocess.terminate()
   ↓
процесс завершён
   ↓
STATE = STOPPED
```

При этом уже обработанные фотографии **не теряются**.

---

### После перезахода

Это особенно важно.

Ты заходишь снова в настройки через 10 минут и видишь:

```text
ФОТООБРАБОТКА

Qwen3-VL 4B
██████████████░░░░░░░░  61%

323 / 530

Статус: выполняется

[ ОСТАНОВИТЬ ]
```

Потому что UI не является источником состояния.

Источник:

```text
PostgreSQL
```

или отдельный persistent state-файл, но я бы в нашем случае использовал **PostgreSQL**, поскольку он у нас уже есть для фотографий.

---

### Ещё лучше — сделать журнал запусков

Например:

```text
ОБРАБОТКИ

2026-08-18 11:50
Hybrid + Qwen
530 фото
████████████████████ 100%
✓ Завершено

2026-08-18 14:20
Hybrid + Qwen
812 фото
████████░░░░░░░░░░░░ 42%
● Выполняется
[Остановить]
```

И можно будет открыть конкретный запуск.

---

### Я бы сделал это в 3 этапа

**1. Сейчас**

Не меняем алгоритмы DINO/Hybrid/Qwen.

Добавляем:

- `job_id`
- статус
- текущий этап
- `total`
- `processed`
- процент
- текущий файл
- время начала
- время окончания
- PID/идентификатор процесса
- cancel flag

**2. Qwen**

Переделываем его запуск так, чтобы он регулярно сообщал:

```text
processed=228
total=530
current="Вавилова52_12.JPG"
```

и UI получает это состояние.

**3. UI**

Добавляем:

```text
┌──────────────────────────────────────┐
│ ОБРАБОТКА ФОТО                       │
│                                      │
│ Hybrid v12       ✓ завершён          │
│ Preview          ✓ завершён          │
│ Qwen3-VL 4B      ● работает          │
│                                      │
│ ████████████░░░░░░░░ 43%             │
│                                      │
│ 228 / 530                            │
│ Вавилова52_12.JPG                    │
│                                      │
│ [ ⏹ ОСТАНОВИТЬ ]                     │
└──────────────────────────────────────┘
```

И **этот блок будет восстанавливаться после перезагрузки страницы/повторного входа**.

---

И ещё один важный момент: **не будем сейчас переделывать всё сразу**. Сначала я бы зафиксировал сегодняшнюю рабочую цепочку:

**Hybrid → Preview → Qwen → PostgreSQL → Grid**

а затем поверх неё добавил менеджер задач. Это позволит не рисковать уже работающим распознаванием.

---

### 👤 **User** — 2026-08-18 12:27:47

да

---

### 🤖 **Assistant** — 2026-08-18 12:27:47

Да. Тогда идём **поэтапно и без изменения рабочего алгоритма распознавания**.

### Этап 1 — сначала исправляем текущую цепочку

Сейчас для сегодняшнего запуска:

```text
20260818_115048
```

у нас есть:

- 530 фото в `output/daily`
- preview ещё не создан
- Qwen должен описать эти фото

Сначала создаём preview для этих 530 фото и проверяем, что **grid начинает их видеть**.

Команда:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

/home/alexice/.local/bin/uv run python scripts/create_previews_v01.py \
    --input data/output/daily/20260818_115048 \
    --output data/preview/daily/20260818_115048
```

После окончания:

```bash
find data/preview/daily/20260818_115048 -type f | wc -l
```

Должно быть:

```text
530
```

### Этап 2 — автоматизируем Preview

После проверки добавим в:

```text
scripts/run_daily_hybrid_v12.sh
```

автоматический вызов:

```text
Hybrid
   ↓
output/daily/<RUN>
   ↓
create_previews_v01
   ↓
preview/daily/<RUN>
   ↓
Qwen
```

### Этап 3 — менеджер процессов

После этого займёмся тем, о чём ты сказал:

**состояние обработки будет постоянным.**

Сделаем отдельную сущность `job`:

```text
job_id
run_id
stage
status
total
processed
percent
current_file
started_at
finished_at
pid
cancel_requested
error
```

Например:

```text
RUN 20260818_115048

Hybrid      ✓ 100%
Preview     ✓ 100%
Qwen        ● 43%
             228 / 530

             [ ОСТАНОВИТЬ ]
```

И это будет храниться независимо от страницы браузера.

### Этап 4 — восстановление после входа

При открытии страницы UI спрашивает:

```text
Есть активная job?
```

Если да — показывает её текущее состояние.

Поэтому можно:

- закрыть настройки;
- перезагрузить браузер;
- зайти через час;

и увидеть тот же процесс:

```text
Qwen3-VL 4B
██████████████░░░░░░ 61%

323 / 530

[ ОСТАНОВИТЬ ]
```

### Этап 5 — корректная остановка

Кнопка будет останавливать **реальный subprocess Qwen**, а не только менять надпись.

При этом уже обработанные записи сохраняются, а задача получает:

```text
STOPPED
```

и потом её можно будет либо продолжить, либо запустить заново только необработанные фотографии.

---

**Сейчас делаем только этап 1.** Запусти создание 530 preview и пришли последние строки вывода. После этого проверим grid и только затем начнём подключать постоянный прогресс.

---

### 👤 **User** — 2026-08-18 12:31:16

PREVIEW FINISHED
================================================================================
Created: 526
Skipped: 0
Errors : 0
Output : /home/alexice/projects/scene_fingerprint_mvp_v02/data/preview/daily/20260818_115048

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ find data/preview/daily/20260818_115048 -type f | wc -l
526
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:31:18

Отлично. Значит генератор preview работает корректно:

```text
Output: 530 фото в daily
Preview: 526
Ошибок: 0
```

Но здесь есть **небольшое расхождение 530 → 526**, которое лучше выяснить сейчас, прежде чем замораживать pipeline.

Сначала выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== OUTPUT BY EXTENSION ====="
find data/output/daily/20260818_115048 -type f \
    | sed 's/.*\.//' \
    | tr '[:upper:]' '[:lower:]' \
    | sort | uniq -c

echo
echo "===== PREVIEW BY EXTENSION ====="
find data/preview/daily/20260818_115048 -type f \
    | sed 's/.*\.//' \
    | tr '[:upper:]' '[:lower:]' \
    | sort | uniq -c

echo
echo "===== OUTPUT IMAGE FILES ====="
find data/output/daily/20260818_115048 -type f \
    \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
    | wc -l

echo
echo "===== PREVIEW FILES ====="
find data/preview/daily/20260818_115048 -type f | wc -l
```

Почему это важно: `create_previews_v01.py` обрабатывает только:

```text
.jpg
.jpeg
.png
.webp
```

Поэтому вполне возможно, что те 4 файла из `530` — например, не изображения или имеют другой формат.

**Если там окажется 526 изображений — всё нормально.** Тогда preview полностью соответствует всем фотографиям, которые может показать grid.

После этого уже проверяем сам grid. А затем переходим к постоянному прогрессу **Hybrid → Preview → Qwen → PostgreSQL**, не ломая текущую рабочую схему.

---

### 👤 **User** — 2026-08-18 12:31:40

echo "===== OUTPUT BY EXTENSION ====="
find data/output/daily/20260818_115048 -type f \
    | sed 's/.*\.//' \
    | tr '[:upper:]' '[:lower:]' \
    | sort | uniq -c

echo
echo "===== PREVIEW BY EXTENSION ====="
find data/preview/daily/20260818_115048 -type f \
    | sed 's/.*\.//' \
    | tr '[:upper:]' '[:lower:]' \
    | sort | uniq -c

echo
echo "===== OUTPUT IMAGE FILES ====="
find data/output/daily/20260818_115048 -type f \
    $ -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" $ \
    | wc -l

echo
echo "===== PREVIEW FILES ====="
find data/preview/daily/20260818_115048 -type f | wc -l
===== OUTPUT BY EXTENSION =====
    525 jpg
      4 json
      1 png

===== PREVIEW BY EXTENSION =====
    526 jpg

===== OUTPUT IMAGE FILES =====
526

===== PREVIEW FILES =====
526
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:31:40

Да, всё нормально. Причина найдена:

```text
OUTPUT:
526 изображений
+ 4 JSON
= 530 файлов

PREVIEW:
526 JPG
```

То есть **ничего не потерялось**. Все 526 фотографий получили preview, ошибок нет.

Теперь можем проверить главное — **видит ли их grid**.

### 1. Проверяем соответствие output ↔ preview

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== MISSING PREVIEWS ====="

python3 - <<'PY'
from pathlib import Path

out = Path("data/output/daily/20260818_115048")
prev = Path("data/preview/daily/20260818_115048")

images = [
    p for p in out.rglob("*")
    if p.is_file()
    and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
]

missing = []

for p in images:
    rel = p.relative_to(out)
    preview = prev / rel.parent / f"{p.stem}.jpg"

    if not preview.exists():
        missing.append(str(rel))

print("OUTPUT IMAGES :", len(images))
print("MISSING       :", len(missing))

for item in missing[:20]:
    print(item)
PY
```

Ожидаем:

```text
OUTPUT IMAGES : 526
MISSING       : 0
```

### 2. После этого

**Перезапусти web-приложение** и обнови страницу с фотографиями.

Теперь grid должен брать:

```text
data/output/daily/20260818_115048/...
                 ↓
data/preview/daily/20260818_115048/...
```

а не старый:

```text
data/output/test_sorted_v2
```

И вот здесь мы уже проверим, что наша новая логика `DAILY_ROOT` действительно работает в реальном UI.

Если **526 фото появились в grid**, тогда первый этап закрываем и переходим к автоматизации:

> **Hybrid → Preview → Qwen → PostgreSQL → Grid**

с постоянным прогрессом и кнопкой **«Остановить»**, который сохраняется даже после выхода из настроек.

---

### 👤 **User** — 2026-08-18 12:32:21

**Фотографии**

0 фотографий в тестовой базе

---

### 🤖 **Assistant** — 2026-08-18 12:32:22

Да. Сейчас причина уже очевидна: **daily-пайплайн отработал правильно**, но страница «Фотографии» всё ещё считает фотобазой `data/output/test_sorted_v2`.

У нас сейчас:

- `data/output/daily/20260818_115048` → **526 фото**
- `data/preview/daily/20260818_115048` → **526 preview**
- `photos.py` уже умеет брать последний `daily`
- но `app/web/config.py` всё ещё содержит:

```python
PHOTO_ROOT = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "test_sorted_v2"
)
```

Поэтому UI и показывает **«0 фотографий в тестовой базе»**.

### Что делаем

Нужно перевести `PHOTO_ROOT` на daily, но **не ломать PostgreSQL, Qwen и preview**.

Я бы сейчас сделал так:

```python
# ============================================================
# PHOTO DATABASE
# ============================================================

PHOTO_ROOT = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "daily"
)
```

Но есть важный момент: `photos.py` уже содержит правильную логику:

```python
daily_root = get_latest_daily_root()
```

и дальше:

```python
for address in STATE.addresses:
    folder = daily_root / f"{address}_v33"
```

То есть после изменения `PHOTO_ROOT` нам надо **не допустить двойного добавления `daily`** в `build_photo_index()`.

Сейчас там:

```python
if not PHOTO_ROOT.exists():
    return
```

и затем уже используется `daily_root`.

Это нормально, если `PHOTO_ROOT` будет корнем:

```text
data/output/daily
```

### Следующий шаг

Сначала покажи текущий верх `photos.py`, чтобы мы сделали изменение аккуратно и не тронули уже работающую систему:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,165p' app/web/components/photos.py
```

После этого я дам **точечную замену**, а затем проверим:

```text
Фотографии
└── 526 фото
    ├── 78_v33
    ├── 79_v33
    ...
    └── 95_v33
```

И preview должны автоматически соответствовать именно запуску:

```text
20260818_115048
```

А следующим этапом уже сделаем то, о чём ты сказал: **единый persistent-процесс обработки с прогрессом Hybrid + Qwen, сохранением состояния после перезахода и кнопкой «Прервать»**.

---

### 👤 **User** — 2026-08-18 12:33:06

================================================================================
PREVIEW FINISHED
================================================================================
Created: 526
Skipped: 0
Errors : 0
Output : /home/alexice/projects/scene_fingerprint_mvp_v02/data/preview/daily/20260818_115048

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ find data/preview/daily/20260818_115048 -type f | wc -l
526
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== OUTPUT BY EXTENSION ====="
find data/output/daily/20260818_115048 -type f \
    | sed 's/.*\.//' \
    | tr '[:upper:]' '[:lower:]' \
    | sort | uniq -c

echo
echo "===== PREVIEW BY EXTENSION ====="
find data/preview/daily/20260818_115048 -type f \
    | sed 's/.*\.//' \
    | tr '[:upper:]' '[:lower:]' \
    | sort | uniq -c

echo
echo "===== OUTPUT IMAGE FILES ====="
find data/output/daily/20260818_115048 -type f \
    $ -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" $ \
    | wc -l

echo
echo "===== PREVIEW FILES ====="
find data/preview/daily/20260818_115048 -type f | wc -l
===== OUTPUT BY EXTENSION =====
    525 jpg
      4 json
      1 png

===== PREVIEW BY EXTENSION =====
    526 jpg

===== OUTPUT IMAGE FILES =====
526

===== PREVIEW FILES =====
526
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== MISSING PREVIEWS ====="

python3 - <<'PY'
from pathlib import Path

out = Path("data/output/daily/20260818_115048")
prev = Path("data/preview/daily/20260818_115048")

images = [
    p for p in out.rglob("*")
    if p.is_file()
    and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
]

missing = []

for p in images:
    rel = p.relative_to(out)
    preview = prev / rel.parent / f"{p.stem}.jpg"

    if not preview.exists():
        missing.append(str(rel))

print("OUTPUT IMAGES :", len(images))
print("MISSING       :", len(missing))

for item in missing[:20]:
    print(item)
PY
===== MISSING PREVIEWS =====
OUTPUT IMAGES : 526
MISSING       : 0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,165p' app/web/components/photos.py
from pathlib import Path
import json
import sqlite3
import zipfile
import tempfile

from nicegui import ui

from app.web.config import PHOTO_ROOT, DB_PATH, PROJECT_ROOT

# ============================================================
# PHOTO PREVIEWS
# ============================================================

PREVIEW_ROOT = (
    PROJECT_ROOT
    / "data"
    / "preview"
    / "daily"
)

DAILY_ROOT = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "daily"
)

def get_latest_daily_root():
    """Return the newest daily output directory."""
    if not DAILY_ROOT.exists():
        return None

    runs = [
        path
        for path in DAILY_ROOT.iterdir()
        if path.is_dir()
    ]

    if not runs:
        return None

    return max(
        runs,
        key=lambda path: path.name,
    )

def get_latest_preview_root():
    """Return the newest daily preview directory."""
    if not PREVIEW_ROOT.exists():
        return None

    runs = [
        path
        for path in PREVIEW_ROOT.iterdir()
        if path.is_dir()
    ]

    if not runs:
        return None

    return max(
        runs,
        key=lambda path: path.name,
    )

def get_preview_path(photo_path):
    """Map daily output photo to its preview image."""
    preview_root = get_latest_preview_root()
    daily_root = get_latest_daily_root()

    if preview_root is None or daily_root is None:
        return None

    try:
        relative = photo_path.relative_to(daily_root)
    except ValueError:
        return None

    preview_path = preview_root / relative

    if preview_path.exists():
        return preview_path

    return None
from app.web.state import STATE, Photo
from app.web.photo_db import build_photo_record_index

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

# ============================================================
# PHOTO INDEX
# ============================================================

PHOTO_INDEX: dict[str, list[Path]] = {}

PHOTO_RECORD_INDEX: dict[str, dict] = {}

def build_photo_index():

    PHOTO_INDEX.clear()
    PHOTO_RECORD_INDEX.clear()

    try:
        PHOTO_RECORD_INDEX.update(
            build_photo_record_index(PROJECT_ROOT)
        )

        print(
            "[PHOTO RECORD INDEX]",
            "records=",
            len(PHOTO_RECORD_INDEX),
            flush=True,
        )

    except Exception as exc:

        print(
            "[PHOTO RECORD INDEX ERROR]",
            repr(exc),
            flush=True,
        )

    daily_root = get_latest_daily_root()

    if daily_root is None:
        print(
            "[DAILY PHOTO ROOT] not found",
            flush=True,
        )
        return

    print(
        "[DAILY PHOTO ROOT]",
        daily_root,
        flush=True,
    )

    for address in STATE.addresses:

        folder = daily_root / f"{address}_v33"

        if not folder.exists():
            PHOTO_INDEX[address] = []
            continue

        files = [
            path
            for path in folder.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                in IMAGE_EXTENSIONS
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:33:06

Вот теперь всё подтверждено: **`photos.py` уже правильно переключён на `daily`**. Менять его не надо.

Проблема в другом: в начале `photos.py` всё ещё импортируется `PHOTO_ROOT`:

```python
from app.web.config import PHOTO_ROOT, DB_PATH, PROJECT_ROOT
```

но в показанном `build_photo_index()` он **уже не используется** для поиска фотографий. Значит `0 фотографий в тестовой базе` приходит, скорее всего, **из UI/состояния или другого места**, где ещё используется старое понятие `test_sorted_v2`.

Нужно найти все места, которые формируют именно эту надпись и счётчик.

Выполни **только эти команды**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== TEST DATABASE TEXT ====="

grep -R -n \
    -E "тестовой базе|test_sorted_v2|Фотографии|фотографий" \
    app/web \
    --include="*.py" \
    --exclude="*.bak*" \
    --exclude="*.before*" \
    --exclude="*.pyc"
```

И отдельно:

```bash
echo "===== PHOTO INDEX COUNTERS ====="

grep -n -E \
    "len\(PHOTO_INDEX|sum\(len|PHOTO_INDEX|PHOTO_LIMIT|get_address_count|get_all_indexed_photos" \
    app/web/components/photos.py
```

### Что я ожидаю найти

Где-то осталось что-то вроде:

```python
PHOTO_ROOT = ...test_sorted_v2
```

или UI всё ещё показывает:

```python
"0 фотографий в тестовой базе"
```

на основании старого счётчика.

При этом **сам источник фотографий уже исправлен**:

```text
DAILY_ROOT
   ↓
20260818_115048
   ↓
526 изображений
```

И preview тоже полностью готовы:

```text
526 output images
526 previews
0 missing
```

Поэтому **ничего пересоздавать и ничего в DINO/Hybrid/Qwen сейчас не меняем**.

Следующий шаг — найти именно старый счётчик/текст в UI и заменить его на текущий `daily`.

---

### 👤 **User** — 2026-08-18 12:33:36

and path.suffix.lower()
                in IMAGE_EXTENSIONS
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== TEST DATABASE TEXT ====="

grep -R -n \
    -E "тестовой базе|test_sorted_v2|Фотографии|фотографий" \
    app/web \
    --include="*.py" \
    --exclude="*.bak*" \
    --exclude="*.before*" \
    --exclude="*.pyc"
===== TEST DATABASE TEXT =====
app/web/components/photos_before_cache_20260816_145128.py:191:                    "Фотографии"
app/web/components/photos_before_cache_20260816_145128.py:263:                    f"фотографий в тестовой базе"
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:162:        "Загрузка фотографий будет подключена "
app/web/components/technical_modules/photo_processing.py:15:        label="Источник фотографий",
app/web/components/technical_modules/photo_processing.py:64:                "В папке нет фотографий",
app/web/components/technical_modules/photo_processing.py:348:            "Источник фотографий"
app/web/components/photos.py:661:                    "Фотографии"
app/web/components/photos.py:766:                    "Нет выбранных фотографий",
app/web/components/photos.py:835:                    "Нет выбранных фотографий",
app/web/components/photos.py:957:                "Фотографии пока не загружены"
app/web/components/photos.py:1041:                    f"фотографий в тестовой базе"
app/web/components/photos.py:1210:                            f"Показаны все {len(files)} фотографий"
app/web/components/photos.py:1276:                    "Фотографии загружаются..."
app/web/photo_db.py:14:    Загружает все записи фотографий из PostgreSQL.
app/web/frontend_v02.py:374:                    "Фотографии"
app/web/frontend_v02.py:380:                    "946 фотографий"
app/web/config.py:16:    / "test_sorted_v2"
app/web/frontend_v01_backup_before_modular.py:353:                    "Фотографии"
app/web/frontend_v01_backup_before_modular.py:359:                    "946 фотографий"
app/web/frontend_v01.py:353:                    "Фотографии"
app/web/frontend_v01.py:359:                    "946 фотографий"
app/web/client_db.py:17:    а не количество фотографий.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo "===== PHOTO INDEX COUNTERS ====="

grep -n -E \
    "len\(PHOTO_INDEX|sum\(len|PHOTO_INDEX|PHOTO_LIMIT|get_address_count|get_all_indexed_photos" \
    app/web/components/photos.py
===== PHOTO INDEX COUNTERS =====
106:PHOTO_INDEX: dict[str, list[Path]] = {}
113:    PHOTO_INDEX.clear()
156:            PHOTO_INDEX[address] = []
173:        PHOTO_INDEX[address] = files
176:def get_all_indexed_photos():
182:            PHOTO_INDEX.get(
243:            files = get_all_indexed_photos()
254:                    PHOTO_INDEX.get(
300:def get_address_count(address):
303:        PHOTO_INDEX.get(
633:        get_all_indexed_photos()
638:        f"addresses={len(PHOTO_INDEX)}",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

                and path.suffix.lower()
                in IMAGE_EXTENSIONS
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== TEST DATABASE TEXT ====="

grep -R -n \
    -E "тестовой базе|test_sorted_v2|Фотографии|фотографий" \
    app/web \
    --include="*.py" \
    --exclude="*.bak*" \
    --exclude="*.before*" \
    --exclude="*.pyc"
===== TEST DATABASE TEXT =====
app/web/components/photos_before_cache_20260816_145128.py:191:                    "Фотографии"
app/web/components/photos_before_cache_20260816_145128.py:263:                    f"фотографий в тестовой базе"
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:162:        "Загрузка фотографий будет подключена "
app/web/components/technical_modules/photo_processing.py:15:        label="Источник фотографий",
app/web/components/technical_modules/photo_processing.py:64:                "В папке нет фотографий",
app/web/components/technical_modules/photo_processing.py:348:            "Источник фотографий"
app/web/components/photos.py:661:                    "Фотографии"
app/web/components/photos.py:766:                    "Нет выбранных фотографий",
app/web/components/photos.py:835:                    "Нет выбранных фотографий",
app/web/components/photos.py:957:                "Фотографии пока не загружены"
app/web/components/photos.py:1041:                    f"фотографий в тестовой базе"
app/web/components/photos.py:1210:                            f"Показаны все {len(files)} фотографий"
app/web/components/photos.py:1276:                    "Фотографии загружаются..."
app/web/photo_db.py:14:    Загружает все записи фотографий из PostgreSQL.
app/web/frontend_v02.py:374:                    "Фотографии"
app/web/frontend_v02.py:380:                    "946 фотографий"
app/web/config.py:16:    / "test_sorted_v2"
app/web/frontend_v01_backup_before_modular.py:353:                    "Фотографии"
app/web/frontend_v01_backup_before_modular.py:359:                    "946 фотографий"
app/web/frontend_v01.py:353:                    "Фотографии"
app/web/frontend_v01.py:359:                    "946 фотографий"
app/web/client_db.py:17:    а не количество фотографий.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo "===== PHOTO INDEX COUNTERS ====="

grep -n -E \
    "len\(PHOTO_INDEX|sum\(len|PHOTO_INDEX|PHOTO_LIMIT|get_address_count|get_all_indexed_photos" \
    app/web/components/photos.py
===== PHOTO INDEX COUNTERS =====
106:PHOTO_INDEX: dict[str, list[Path]] = {}
113:    PHOTO_INDEX.clear()
156:            PHOTO_INDEX[address] = []
173:        PHOTO_INDEX[address] = files
176:def get_all_indexed_photos():
182:            PHOTO_INDEX.get(
243:            files = get_all_indexed_photos()
254:                    PHOTO_INDEX.get(
300:def get_address_count(address):
303:        PHOTO_INDEX.get(
633:        get_all_indexed_photos()
638:        f"addresses={len(PHOTO_INDEX)}",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:33:36

Да, теперь причина практически ясна.

**Фото в daily есть: 526. Превью есть: 526. Но интерфейс всё ещё показывает «0 фотографий в тестовой базе», потому что часть UI-текста/логики осталась от старой `test_sorted_v2`.**

Причём текущий `photos.py` уже правильно перешёл на:

```text
data/output/daily/<последний запуск>/<address>_v33
```

и `get_latest_daily_root()` действительно возвращает:

```text
data/output/daily/20260818_115048
```

### Что я предлагаю сейчас

Не трогать рабочую индексацию и не ломать просмотр. Сначала найдём **конкретный участок, который рисует "0 фотографий в тестовой базе"**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1000,1070p' app/web/components/photos.py

echo "===================="

sed -n '600,660p' app/web/components/photos.py

echo "===================="

sed -n '940,970p' app/web/components/photos.py
```

Особенно интересует строка около **1041**:

```text
f"фотографий в тестовой базе"
```

Скорее всего там просто старый текст/счётчик, который больше не соответствует новой архитектуре.

---

### И важный момент

Мы уже подтвердили:

```text
OUTPUT images = 526
PREVIEW files = 526
MISSING previews = 0
```

То есть **пайплайн фотографий сейчас не проблема**.

Следующая задача:

```text
daily output
      ↓
PHOTO_INDEX
      ↓
get_all_indexed_photos()
      ↓
UI счётчик
      ↓
photo_grid
```

Нужно проверить именно последний участок.

И после этого я бы сразу сделал правильную схему:

```text
Текущий daily run
        │
        ├── 526 оригиналов
        ├── 526 preview
        └── Qwen metadata
                │
                ▼
        PostgreSQL / статус обработки
                │
                ▼
        UI
        ├── количество фото
        ├── прогресс Hybrid
        ├── прогресс Qwen
        ├── текущая операция
        ├── сохранение состояния после перезахода
        └── STOP / CANCEL
```

То есть **не будем возвращать `test_sorted_v2`**. Он уже должен остаться только старым тестовым источником.

Сначала исправим отображение текущего daily набора, потом подключим к нему постоянный статус Hybrid/Qwen и кнопку прерывания.

---

### 👤 **User** — 2026-08-18 12:37:11

"len\(PHOTO_INDEX|sum\(len|PHOTO_INDEX|PHOTO_LIMIT|get_address_count|get_all_indexed_photos" \
    app/web/components/photos.py
===== PHOTO INDEX COUNTERS =====
106:PHOTO_INDEX: dict[str, list[Path]] = {}
113:    PHOTO_INDEX.clear()
156:            PHOTO_INDEX[address] = []
173:        PHOTO_INDEX[address] = files
176:def get_all_indexed_photos():
182:            PHOTO_INDEX.get(
243:            files = get_all_indexed_photos()
254:                    PHOTO_INDEX.get(
300:def get_address_count(address):
303:        PHOTO_INDEX.get(
633:        get_all_indexed_photos()
638:        f"addresses={len(PHOTO_INDEX)}",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1000,1070p' app/web/components/photos.py

echo "===================="

sed -n '600,660p' app/web/components/photos.py

echo "===================="

sed -n '940,970p' app/web/components/photos.py
                    flush=True,
                )

                # ------------------------------------------------
                # CLEAR PREVIOUS GRID
                # ------------------------------------------------

                photo_grid_container.clear()

                record_by_path = PHOTO_RECORD_INDEX

                STATE.photos = []

                for path in files:

                    record = record_by_path.get(
                        str(path.resolve())
                    )

                    STATE.photos.append(
                        Photo(
                            path=path,
                            db_record=record,
                        )
                    )

                print(
                    "[PHOTO RECORD LINK]",
                    "linked=",
                    sum(
                        1
                        for photo in STATE.photos
                        if photo.db_record is not None
                    ),
                    "total=",
                    len(STATE.photos),
                    flush=True,
                )

                count_label.text = (
                    f"{len(files)} "
                    f"фотографий в тестовой базе"
                )

                if not files:

                    with photo_grid_container:

                        with ui.column().classes(
                            "w-full "
                            "items-center "
                            "justify-center "
                            "p-12"
                        ):

                            ui.icon(
                                "photo_library",
                                size="64px",
                            ).classes(
                                "text-grey-5"
                            )

                            ui.label(
                                "Фотографий нет"
                            ).classes(
                                "text-grey-6"
                            )

                    return

                # ------------------------------------------------
====================
                on_click=lambda: (
                    dialog.close(),
                    ui.notify(
                        "Подборки будут подключены позже"
                    ),
                ),
            ).props(
                "flat align-left w-full"
            )

    dialog.open()

# ============================================================
# BUILD PHOTOS
# ============================================================

def build_photos():

    # --------------------------------------------------------
    # Сканируем базу ОДИН РАЗ
    # --------------------------------------------------------

    build_photo_index()

    # ========================================================
    # LAZY GRID
    # ========================================================

    GRID_PAGE_SIZE = 40
    grid_loaded = 0

    total_photos = len(
        get_all_indexed_photos()
    )

    print(
        "[PHOTO INDEX]",
        f"addresses={len(PHOTO_INDEX)}",
        f"photos={total_photos}",
        flush=True,
    )

    with ui.column().classes(
        "w-full h-full min-w-0"
    ):

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        with ui.row().classes(
            "w-full items-center "
            "justify-between px-3 py-2"
        ):

            with ui.column().classes(
                "gap-0"
            ):

                ui.label(
====================
        # LAZY GRID
        # ----------------------------------------------------

        grid_requested = False

        with ui.row().classes(
            "w-full items-center px-3 py-2"
        ):

            show_grid_button = ui.button(
                "Показать фотографии",
                icon="photo_library",
            ).props(
                "unelevated"
            )

            grid_status_label = ui.label(
                "Фотографии пока не загружены"
            ).classes(
                "text-sm text-grey-6"
            )

        # ----------------------------------------------------
        # SCROLL AREA
        # ----------------------------------------------------

        with ui.scroll_area().classes(
            "w-full flex-grow"
        ) as photo_scroll_area:

            # Контейнер грида.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:37:11

Вот оно. **Причина найдена.**

Индекс уже считает текущий daily набор:

```python
total_photos = len(get_all_indexed_photos())
```

и выше мы фактически подтвердили, что там должно быть **526**.

Но при отображении результата осталось старое название:

```python
count_label.text = (
    f"{len(files)} "
    f"фотографий в тестовой базе"
)
```

То есть это **не причина нулевого количества**, а старый текст. А вот сообщение **«0 фотографий в тестовой базе»** скорее всего формируется до загрузки грида — в lazy-load части.

### Сейчас найдём точное место

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '660,760p' app/web/components/photos.py

echo "===================="

sed -n '1180,1300p' app/web/components/photos.py
```

Нас интересуют участки, где создаются:

```python
count_label
grid_status_label
show_grid_button
```

и где им присваивается `.text`.

---

### Но уже видно, что архитектура правильная

Сейчас цепочка:

```text
data/output/daily/20260818_115048
              ↓
get_latest_daily_root()
              ↓
build_photo_index()
              ↓
PHOTO_INDEX
              ↓
get_all_indexed_photos()
              ↓
total_photos = 526
```

То есть **не надо сейчас переделывать `PHOTO_INDEX`, `PHOTO_ROOT` или PostgreSQL**.

И ещё важный момент: PostgreSQL сейчас содержит только импортированные/проанализированные записи. Поэтому мы не должны использовать количество записей PostgreSQL как количество фотографий в daily-папке.

Правильнее разделить:

- **Фотографии:** физически найдено в текущем daily run → **526**
- **Qwen:** сколько из этих 526 обработано
- **Hybrid:** сколько обработано/распознано
- **PostgreSQL:** сколько записей уже импортировано

И именно это потом позволит сделать нормальный постоянный статус:

```text
Текущий запуск: 20260818_115048

Обработка
██████████████░░░░░░  72%  380 / 526

Qwen3-VL 4B
████████░░░░░░░░░░░░  41%  156 / 380

Статус: выполняется
[ ОСТАНОВИТЬ ]
```

Причём статус будем хранить **на диске/в PostgreSQL**, а не только в памяти NiceGUI. Поэтому после перезахода в «Настройки» или обновления страницы он восстановится.

Сейчас пришли вывод этих двух `sed` — **следующим шагом поправим именно счётчик 0 → 526, не затрагивая остальное.**

---

### 👤 **User** — 2026-08-18 12:37:33

selected_count_label.text = (
                f"Выбрано: {len(STATE.selected_photos)}"
            )

            print(
                "[PHOTO SELECT ALL]",
                "count=",
                len(STATE.selected_photos),
                flush=True,
            )

def clear_selected_photos():

            STATE.selected_photos.clear()

            for checkbox in photo_checkboxes.values():
                checkbox.value = False

            selected_count_label.text = "Выбрано: 0"

            print(
                "[PHOTO SELECT CLEAR]",
                flush=True,
            )

def download_selected_zip():

            files = [
                Path(path)
                for path in STATE.selected_photos
====================
                                # ADDRESS
                                # ----------------------------

                                ui.label(
                                    photo.path.parent.name.replace(
                                        "_v33",
                                        "",
                                    )
                                ).classes(
                                    "px-2 pb-2 "
                                    "text-xs text-grey-6"
                                )

                    # ----------------------------
                    # LOADING STATUS
                    # ----------------------------

                    if len(files) < len(all_files):

                        ui.label(
                            f"Показано {len(files)} из "
                            f"{len(all_files)}"
                        ).classes(
                            "w-full text-center "
                            "text-sm text-grey-6 p-4"
                        )

                    else:

                        ui.label(
                            f"Показаны все {len(files)} фотографий"
                        ).classes(
                            "w-full text-center "
                            "text-sm text-grey-6 p-4"
                        )

                grid_status_label.text = (
                    f"Показано {len(files)} из "
                    f"{len(all_files)}"
                )

            # ------------------------------------------------
            # LOAD MORE
            # ------------------------------------------------

            def load_more_photos():

                nonlocal grid_loaded

                if not grid_requested:
                    return

                all_files = get_filtered_photos()

                if grid_loaded >= len(all_files):
                    return

                old_loaded = grid_loaded

                grid_loaded = min(
                    grid_loaded + GRID_PAGE_SIZE,
                    len(all_files),
                )

                print(
                    "[PHOTO GRID LOAD MORE]",
                    "from=", old_loaded,
                    "to=", grid_loaded,
                    "total=", len(all_files),
                    flush=True,
                )

                render_photo_grid()

            # ------------------------------------------------
            # FIRST REQUEST
            # ------------------------------------------------

            def request_photo_grid():

                nonlocal grid_requested
                nonlocal grid_loaded

                print(
                    "[PHOTO GRID BUTTON CLICK]",
                    flush=True,
                )

                grid_requested = True

                grid_loaded = min(
                    GRID_PAGE_SIZE,
                    len(get_filtered_photos()),
                )

                grid_status_label.text = (
                    "Фотографии загружаются..."
                )

                render_photo_grid()

                print(
                    "[PHOTO GRID RENDERED]",
                    "loaded=",
                    grid_loaded,
                    flush=True,
                )

            show_grid_button.on_click(
                request_photo_grid,
            )

            # ------------------------------------------------
            # AUTO LOAD ON SCROLL
            # ------------------------------------------------

            def handle_grid_scroll(e):

                if not grid_requested:
                    return

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:37:34

Да. Этот участок подтверждает: **счётчик 0 возникает не здесь**.

Здесь всё завязано на:

```python
get_filtered_photos()
```

и если `get_filtered_photos()` возвращает 0, кнопка загрузки получает:

```python
grid_loaded = min(
    GRID_PAGE_SIZE,
    len(get_filtered_photos()),
)
```

то есть `0`.

Но мы уже знаем, что `PHOTO_INDEX` должен содержать 526. Значит, проблема, скорее всего, **в фильтрах `STATE`**, а не в daily-папке.

Особенно подозрительны:

```python
STATE.selected_addresses
STATE.selected_clients
STATE.search_query
STATE.search_results
```

### Проверяем без изменения кода

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
from app.web.components.photos import (
    build_photo_index,
    PHOTO_INDEX,
    get_all_indexed_photos,
    get_filtered_photos,
)
from app.web.state import STATE

build_photo_index()

print("========================================")
print("STATE")
print("addresses        =", len(STATE.addresses))
print("selected_addresses=", STATE.selected_addresses)
print("selected_clients =", STATE.selected_clients)
print("search_query     =", repr(STATE.search_query))
print("search_results   =", len(STATE.search_results))

print("========================================")
print("INDEX")
print("addresses indexed =", len(PHOTO_INDEX))
print("all indexed       =", len(get_all_indexed_photos()))

print("========================================")
print("FILTERED")
print("filtered photos   =", len(get_filtered_photos()))

print("========================================")
print("NON EMPTY ADDRESSES")

for address, files in PHOTO_INDEX.items():
    if files:
        print(address, len(files))
PY
```

### Что ожидаем

Я ожидаю примерно:

```text
addresses indexed = 18
all indexed       = 526
filtered photos   = 526
```

Если будет:

```text
all indexed       = 526
filtered photos   = 0
```

— **нашли проблему: состояние фильтров.**

Если же:

```text
all indexed = 0
```

— тогда проблема между `STATE.addresses` и папками `78_v33 ... 95_v33`.

---

И ещё: старую надпись

```python
f"{len(files)} фотографий в тестовой базе"
```

после диагностики обязательно поменяем на нейтральную:

```python
f"{len(files)} фотографий"
```

или лучше:

```python
f"{len(files)} фотографий в текущем запуске"
```

**Но пока не меняем.** Сначала посмотрим этот тест — он даст нам точное место поломки.

---

### 👤 **User** — 2026-08-18 12:37:52

print("========================================")
print("FILTERED")
print("filtered photos   =", len(get_filtered_photos()))

print("========================================")
print("NON EMPTY ADDRESSES")

for address, files in PHOTO_INDEX.items():
    if files:
        print(address, len(files))
PY
[PHOTO RECORD INDEX] records= 100
[DAILY PHOTO ROOT] /home/alexice/projects/scene_fingerprint_mvp_v02/data/output/daily/20260818_115048
========================================
STATE
addresses        = 18
selected_addresses= set()
selected_clients = None
search_query     = ''
search_results   = 0
========================================
INDEX
addresses indexed = 18
all indexed       = 526
========================================
FILTERED
filtered photos   = 526
========================================
NON EMPTY ADDRESSES
78 89
79 33
80 9
81 16
82 9
83 17
84 19
85 24
86 22
87 17
88 15
89 33
90 3
91 14
92 39
93 29
94 120
95 18
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:37:52

Отлично. **Backend индексации полностью исправен.**

Сейчас имеем:

```text
DAILY ROOT        = 20260818_115048
INDEX             = 526
FILTERED          = 526
ADDRESSES         = 18
PREVIEWS          = 526
MISSING PREVIEWS  = 0
```

То есть **фотографии в UI должны быть 526**. Проблема исключительно в отображении/моменте загрузки UI.

### Что происходит

`build_photos()` уже получает:

```python
total_photos = len(get_all_indexed_photos())
```

то есть:

```text
526
```

Но дальше используется lazy grid: фотографии реально загружаются только после:

> **Показать фотографии**

И старый интерфейс всё ещё содержит формулировку:

```python
f"{len(files)} фотографий в тестовой базе"
```

Кроме того, есть первоначальный статус:

```python
"Фотографии пока не загружены"
```

Это нормально до нажатия кнопки, но **«0 фотографий в тестовой базе» — явно старый UI-код**.

---

## Предлагаю сейчас сделать маленькое исправление

Без изменения логики.

### 1. Меняем текст

В `photos.py`:

```python
count_label.text = (
    f"{len(files)} "
    f"фотографий в текущем запуске"
)
```

вместо:

```python
count_label.text = (
    f"{len(files)} "
    f"фотографий в тестовой базе"
)
```

### 2. В заголовке сразу показываем количество

В `build_photos()` у нас уже есть:

```python
total_photos = len(
    get_all_indexed_photos()
)
```

Поэтому интерфейс может сразу показывать:

```text
Фотографии
526 фотографий в текущем запуске
```

а кнопка:

```text
▶ Показать фотографии
```

и после нажатия:

```text
Показано 40 из 526
```

---

### Но есть ещё один важный момент

Сейчас:

```text
PostgreSQL records = 100
```

а фотографий:

```text
526
```

Это **не ошибка**. PostgreSQL пока содержит только 100 записей, а физический daily output уже содержит 526 фотографий.

И это как раз связано с тем, что мы обсуждали про Qwen.

В итоге я бы сделал три независимых показателя:

```text
ФОТОГРАФИИ
526

QWEN
156 / 526

БАЗА ДАННЫХ
100 / 526
```

И отдельный постоянный статус:

```text
Обработка: Qwen3-VL 4B
██████████░░░░░░░░░░ 48%
251 / 526

[ ОСТАНОВИТЬ ]
```

Этот статус будем хранить вне состояния страницы, чтобы **после перезахода он не сбрасывался**.

---

### Сейчас предлагаю не делать большой переделки

Сначала исправим **только счётчик/надпись**, перезапустим web и убедимся, что UI видит 526.

Дай команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -i 's/фотографий в тестовой базе/фотографий в текущем запуске/' \
    app/web/components/photos.py

uv run python -m py_compile app/web/components/photos.py

grep -n "фотографий в" app/web/components/photos.py
```

После этого **перезапускаем web**, проверяем экран «Фотографии».

Если там появится 526 — эту часть **замораживаем** и переходим к главной следующей задаче: **единый persistent Job Manager для Hybrid + Qwen с прогрессом, восстановлением после перезахода и STOP.**

---

### 👤 **User** — 2026-08-18 12:39:37

пусто фото нет и список адресов не обновился

---

### 🤖 **Assistant** — 2026-08-18 12:39:38

Да. Тогда проблема уже **не в `PHOTO_INDEX`**. Мы доказали, что backend при прямом вызове видит:

```text
18 адресов
526 фото
filtered = 526
```

Но браузер показывает старый список адресов и пустой grid. Значит, **страница/STATE не пересобирается после смены источника на `daily`**.

Особенно важно: `build_photo_index()` вызывается, но список `STATE.addresses` может формироваться из старого источника (`test_sorted_v2`). Поэтому сейчас не будем ничего менять вслепую.

Давай найдём, **откуда формируется `STATE.addresses`**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== STATE ADDRESSES ====="
grep -R -n \
    "STATE.addresses\|addresses =" \
    app/web \
    --include="*.py" \
    --exclude="*.bak*" \
    --exclude="*.before*" \
    --exclude="*.pyc"

echo
echo "===== STATE DEFINITION ====="
sed -n '1,260p' app/web/state.py

echo
echo "===== CONFIG ====="
cat app/web/config.py
```

И ещё сразу:

```bash
echo
echo "===== TEST_SORTED_V2 REFERENCES ====="
grep -R -n "test_sorted_v2" app/web \
    --include="*.py" \
    --exclude="*.bak*" \
    --exclude="*.before*" \
    --exclude="*.pyc"
```

### Почему это сейчас самое важное

У нас уже есть:

```text
daily/
└── 20260818_115048/
    ├── 78_v33
    ├── 79_v33
    ...
    └── 95_v33
```

и `PHOTO_INDEX` содержит:

```text
78 89
79 33
...
94 120
95 18
```

То есть **новый источник работает**.

Но UI может делать примерно такое:

```text
STATE.addresses ← старый test_sorted_v2
                         ↓
build_photo_index()
                         ↓
ищет daily/<старый список адресов>
                         ↓
часть/всё не совпадает
                         ↓
пустой UI
```

А ещё список адресов может создаваться **один раз при старте приложения**, поэтому после нового daily запуска он физически не обновляется.

Нам нужно сделать правильную архитектуру:

```text
Новый daily run
       ↓
data/output/daily/20260818_115048
       ↓
автоматически определить адреса
       ↓
STATE.addresses
       ↓
PHOTO_INDEX
       ↓
UI
```

То есть **список адресов больше не должен зависеть от `test_sorted_v2` вообще**.

Пришли вывод этих четырёх блоков. После этого я дам точечную правку, без очередного перелопачивания `photos.py`.

---

### 👤 **User** — 2026-08-18 12:40:18

1041:                    f"фотографий в текущем запуске"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== STATE ADDRESSES ====="
grep -R -n \
    "STATE.addresses\|addresses =" \
    app/web \
    --include="*.py" \
    --exclude="*.bak*" \
    --exclude="*.before*" \
    --exclude="*.pyc"

echo
echo "===== STATE DEFINITION ====="
sed -n '1,260p' app/web/state.py

echo
echo "===== CONFIG ====="
cat app/web/config.py
===== STATE ADDRESSES =====
app/web/components/photos_before_cache_20260816_145128.py:22:    for address in STATE.addresses:
app/web/components/addresses.py:63:                STATE.selected_addresses = set(
app/web/components/addresses.py:64:                    STATE.addresses
app/web/components/addresses.py:103:        for address in STATE.addresses:
app/web/components/photos.py:151:    for address in STATE.addresses:
app/web/components/photos.py:180:    for address in STATE.addresses:
app/web/components/photos.py:240:        selected_addresses = STATE.selected_addresses
app/web/components/photos.py:248:            for address in STATE.addresses:

===== STATE DEFINITION =====
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Photo:
    path: Path
    selected: bool = False
    db_record: dict | None = None

@dataclass
class Collection:
    name: str
    kind: str = "Моя"
    client: str = ""

@dataclass
class AppState:
    manager: str = "Вихляева Алена"
    user_id: int | None = None

    manager_colors: dict[str, str] = field(default_factory=lambda: {
        "Вихляева Алена": "#1976D2",
        "Пятницына Диана": "#2E7D32",
        "Аннин Илья": "#7B1FA2",
        "Иванова Елена": "#C62828",
        "Марышева Елена": "#00838F",
        "Бутовченко Ольга": "#6A1B9A",
        "Кривошлыкова Ангелина": "#1565C0",
        "Теплинская Наталья": "#2E7D32",
        "Папикян Эля": "#AD1457",
        "Путилина Татьяна": "#4E342E",
    })

    dark_mode: bool = False

    clients: list[str] = field(default_factory=lambda: [
        "Все клиенты",
        "Единая Россия",
        "Яндекс",
        "Самокат",
        "Сбер",
        "Ozon",
        "Бетсити",
        "Альбион-Тур",
    ])

    addresses: list[str] = field(default_factory=lambda: [
        "78",
        "79",
        "80",
        "81",
        "82",
        "83",
        "84",
        "85",
        "86",
        "87",
        "88",
        "89",
        "90",
        "91",
        "92",
        "93",
        "94",
        "95",
    ])

    collections: list[Collection] = field(default_factory=lambda: [
        Collection("Важное"),
        Collection("На согласование"),
        Collection("Для клиента"),
        Collection("Самокат — август", "Клиентская", "Самокат"),
        Collection("Яндекс — Москва", "Клиентская", "Яндекс"),
    ])

    # None = все клиенты, set() = ничего не выбрано
    selected_clients: set[str] | None = None
    selected_addresses: set[str] = field(default_factory=set)

    # SQLite / поиск
    search_query: str = ""
    search_results: list[dict] = field(default_factory=list)

    photos: list[Photo] = field(default_factory=list)
    selected_photos: set[str] = field(default_factory=set)

    refresh_photos: object = None

STATE = AppState()

===== CONFIG =====
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ============================================================
# PHOTO DATABASE
# ============================================================

# Результат тестового распознавания v33.
# Исходный data/input/test НЕ трогаем.
PHOTO_ROOT = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "test_sorted_v2"
)

# 0 = без ограничения
PHOTO_LIMIT = 0

# ============================================================
# UI
# ============================================================

LOGO_PATH = (
    PROJECT_ROOT
    / "app"
    / "web"
    / "assets"
    / "logo.png"
)

HOST = "0.0.0.0"
PORT = 8081

# ============================================================
# SQLITE METADATA DATABASE
# ============================================================

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "metadata"
    / "photos.db"
)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:40:19

Вот теперь нашли **ещё одну конкретную причину**.

`STATE.addresses` уже правильный — там 78–95. Но `config.py` всё ещё содержит старый источник:

```python
PHOTO_ROOT = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "test_sorted_v2"
)
```

А `photos.py` мы уже перевели на:

```text
data/output/daily/<последний запуск>
```

Получается, сейчас приложение использует **два разных источника одновременно**:

```text
PHOTO_ROOT → test_sorted_v2          ← старый
DAILY_ROOT → output/daily/...        ← новый
```

И это очень хорошо объясняет, почему часть UI показывает старые данные.

Но есть ещё один важный момент: **адреса в `state.py` статически зашиты 78–95**, поэтому список адресов сам по себе действительно никогда не «обновится» после нового запуска.

### Делаем правильно

Не будем просто менять `PHOTO_ROOT` на `DAILY_ROOT`, потому что `photos.py` уже содержит новую логику выбора последнего daily run.

Нужно убрать зависимость UI от `PHOTO_ROOT` там, где она относится к фотографиям.

Сначала посмотрим `addresses.py`, потому что именно он, вероятно, формирует тот самый список адресов, который ты видишь.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== ADDRESSES COMPONENT ====="
sed -n '1,180p' app/web/components/addresses.py

echo
echo "===== PHOTO_ROOT CURRENT USAGE ====="
grep -R -n "PHOTO_ROOT" app/web \
    --include="*.py" \
    --exclude="*.bak*" \
    --exclude="*.before*" \
    --exclude="*.pyc"
```

**Пока ничего не меняем.**

После этого я дам одну согласованную правку, чтобы:

```text
data/output/daily/20260818_115048
        ↓
автоматически определяются 78–95
        ↓
список адресов
        ↓
526 фотографий
        ↓
526 preview
```

И одновременно уберём `test_sorted_v2` из рабочего пути.

А уже после этого подключим к этому же механизму **persistent progress Hybrid/Qwen + STOP**, чтобы не делать второй раз архитектурную переделку.

---

