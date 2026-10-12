## СЕССИЯ: вторник

**Создано:** 2026-08-18 18:12:03
**Обновлено:** 2026-08-22 20:16:20
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1)

---

### 🤖 **Assistant** — 2026-08-18 21:03:00

Продолжаем. Следующий шаг — **безопасно добавить `photo_id` в PostgreSQL**, не трогая пока Grid, DINO и Qwen.

Но я бы немного изменил первоначальный вариант: **ID лучше делать не зависящим от даты**, чтобы он был постоянным идентификатором сущности фотографии. Например:

```text
PH_00000001
PH_00000002
...
```

или UUID. Для нашего проекта `PH_00000001` удобнее для отладки.

### 1. Сначала делаем резервную копию PostgreSQL

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
pg_dump -h localhost -p 5432 -U lora -d photobase \
  > /tmp/photobase_before_photo_id.sql
```

Проверяем:

```bash
ls -lh /tmp/photobase_before_photo_id.sql
```

### 2. Добавляем колонку

Пока **не ставим `NOT NULL`**, чтобы миграция была безопасной:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"ALTER TABLE photos ADD COLUMN IF NOT EXISTS photo_id TEXT;"
```

### 3. Заполняем существующие 100 записей

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"UPDATE photos SET photo_id = 'PH_' || LPAD(id::text, 8, '0') WHERE photo_id IS NULL;"
```

Получим:

```text
id   photo_id
1    PH_00000001
2    PH_00000002
...
100  PH_00000100
```

### 4. Проверяем

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT id, photo_id, address, filename FROM photos ORDER BY id LIMIT 10;"
```

И:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT COUNT(*), COUNT(photo_id), COUNT(DISTINCT photo_id) FROM photos;"
```

Должно быть примерно:

```text
 count | count | count
-------+-------+------
   100 |   100 |   100
```

### 5. Только после проверки ставим ограничения

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"ALTER TABLE photos ALTER COLUMN photo_id SET NOT NULL;"
```

и:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"CREATE UNIQUE INDEX IF NOT EXISTS idx_photos_photo_id ON photos(photo_id);"
```

---

**После этого остановимся.**

Следующий этап будет уже интереснее: переделаем начало pipeline так, чтобы при поступлении каждой новой фотографии **сначала создавалась PostgreSQL-запись с `photo_id`**, а DINO, сортировка, preview и Qwen дальше работали с этим ID.

То есть наконец получим именно ту схему, которую ты описал:

**фото → ID → DINO → адрес/сортировка → preview → PostgreSQL → Qwen → дополнение той же записи.**

---

### 👤 **User** — 2026-08-18 21:04:18

давай.

---

### 🤖 **Assistant** — 2026-08-18 21:04:20

Да. Делаем поэтапно, чтобы **не сломать рабочую базу и текущий Grid**.

### Шаг 1 — добавляем `photo_id`

Выполни целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
pg_dump -h localhost -p 5432 -U lora -d photobase \
  > /tmp/photobase_before_photo_id.sql && \
psql -h localhost -p 5432 -U lora -d photobase -c \
"ALTER TABLE photos ADD COLUMN IF NOT EXISTS photo_id TEXT;" && \
psql -h localhost -p 5432 -U lora -d photobase -c \
"UPDATE photos SET photo_id = 'PH_' || LPAD(id::text, 8, '0') WHERE photo_id IS NULL;" && \
psql -h localhost -p 5432 -U lora -d photobase -c \
"ALTER TABLE photos ALTER COLUMN photo_id SET NOT NULL;" && \
psql -h localhost -p 5432 -U lora -d photobase -c \
"CREATE UNIQUE INDEX IF NOT EXISTS idx_photos_photo_id ON photos(photo_id);"
```

### Шаг 2 — проверяем

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT id, photo_id, address, filename FROM photos ORDER BY id LIMIT 15;"
```

И:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT COUNT(*) AS total, COUNT(photo_id) AS with_photo_id, COUNT(DISTINCT photo_id) AS unique_photo_ids FROM photos;"
```

Ожидаем:

```text
total | with_photo_id | unique_photo_ids
------+---------------+----------------
100   | 100           | 100
```

---

### Что будет дальше

После этого **не будем сразу переписывать весь pipeline**.

Сначала изменим `app/web/photo_db.py`, чтобы Grid уже видел новый идентификатор:

```text
id
photo_id
address
filename
path
...
```

А затем найдём **реальную точку входа нового daily pipeline**, где фотография впервые появляется, и именно туда поставим создание `photo_id`.

Получится:

```text
                    НОВОЕ ФОТО
                        │
                        ▼
                 ┌─────────────┐
                 │  photo_id   │ ← создаётся ОДИН раз
                 └──────┬──────┘
                        │
              ┌─────────┼─────────┐
              ▼         ▼         ▼
            DINO      сортировка  другие
              │         │
              └────┬────┘
                   ▼
              address + path
                   │
                   ▼
              PostgreSQL
                   │
                   ▼
                 Qwen
                   │
                   ▼
            та же запись
```

**Сначала выполни два блока выше и пришли вывод.** После проверки переходим к коду — уже без теории.

---

### 👤 **User** — 2026-08-18 21:04:42

CREATE INDEX
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT id, photo_id, address, filename FROM photos ORDER BY id LIMIT 15;"
 id |  photo_id   | address |   filename    
----+-------------+---------+---------------
  1 | PH_00000001 | 78_v33  | Комарова13_01
  2 | PH_00000002 | 78_v33  | Комарова13_02
  3 | PH_00000003 | 78_v33  | Комарова13_03
  4 | PH_00000004 | 78_v33  | Комарова13_04
  5 | PH_00000005 | 78_v33  | Комарова13_05
  6 | PH_00000006 | 78_v33  | Комарова13_06
  7 | PH_00000007 | 78_v33  | Комарова13_07
  8 | PH_00000008 | 78_v33  | Комарова13_08
  9 | PH_00000009 | 78_v33  | Комарова13_09
 10 | PH_00000010 | 78_v33  | Комарова13_10
 11 | PH_00000011 | 78_v33  | Комарова13_11
 12 | PH_00000012 | 78_v33  | Комарова13_12
 13 | PH_00000013 | 78_v33  | Комарова13_13
 14 | PH_00000014 | 78_v33  | Комарова13_14
 15 | PH_00000015 | 78_v33  | Комарова13_15
(15 rows)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:04:43

Отлично. **`photo_id` успешно добавлен и заполнен.** Старые 100 записей не затронуты.

Теперь переходим к главному: **новые фото должны получать `photo_id` до DINO**.

Но сначала нужно найти точное место, где `run_daily_hybrid_v12.sh` получает фотографии и запускает обработку. Мы уже знаем, что сам `run_hybrid_v12.py` получает папку `data/input/daily`, но ID должен создаваться **до запуска DINO**, а не внутри сортировки.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
"data/input/daily|run_hybrid_v12|copy2|move|shutil|input_dir|INPUT|daily" \
scripts app \
--include="*.py" \
--include="*.sh" 2>/dev/null | head -300
```

И отдельно найдём всё, что сейчас пишет в PostgreSQL:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
"INSERT INTO photos|UPDATE photos|psycopg2.connect|photo_id" \
scripts app \
--include="*.py" 2>/dev/null
```

### Почему именно сейчас это важно

Мы не будем делать что-то вроде:

```text
фото
 ↓
DINO
 ↓
сортировка
 ↓
создание записи
```

Нам нужна схема:

```text
фото
 ↓
создали PH_xxxxxxxx
 ↓
записали в PostgreSQL
 ↓
DINO
 ↓
получили address
 ↓
сортировка
 ↓
обновили ту же запись
 ↓
создали preview
 ↓
Qwen
 ↓
обновили ту же запись
```

При этом **Grid до сортировки эти фото не показывает**, потому что `address IS NULL`. После сортировки запись получает адрес — и только тогда фотография становится частью обычного адресного представления Grid.

Это как раз устранит ту путаницу, о которой ты говорил с чекбоксами адресов.

---

### 👤 **User** — 2026-08-18 21:04:55

lora -d photobase -c \
"SELECT COUNT(*) AS total, COUNT(photo_id) AS with_photo_id, COUNT(DISTINCT photo_id) AS unique_photo_ids FROM photos;"
 total | with_photo_id | unique_photo_ids 
-------+---------------+------------------
   100 |           100 |              100
(1 row)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:04:56

Отлично. База в порядке:

```text
100 записей
100 photo_id
100 уникальных photo_id
```

Теперь **переходим к созданию ID в начале pipeline**.

Но перед изменением кода надо найти точную точку входа. Выполни эти **два поиска**.

### 1. Где запускается daily pipeline и куда попадают фотографии

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
"data/input/daily|run_hybrid_v12|copy2|move|shutil|input_dir|INPUT|daily" \
scripts app \
--include="*.py" \
--include="*.sh" 2>/dev/null | head -300
```

### 2. Где сейчас PostgreSQL получает/изменяет фотографии

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
"INSERT INTO photos|UPDATE photos|psycopg2.connect|photo_id" \
scripts app \
--include="*.py" 2>/dev/null
```

**Пришли оба вывода.**

После этого я покажу конкретно, **в какой файл и в какое место вставляем генератор `photo_id`**, причём существующие 100 записей и текущий Grid оставляем нетронутыми.

---

### 👤 **User** — 2026-08-18 21:05:44

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
"data/input/daily|run_hybrid_v12|copy2|move|shutil|input_dir|INPUT|daily" \
scripts app \
--include="*.py" \
--include="*.sh" 2>/dev/null | head -300
scripts/sort_neighbor_v35_benchmark.py:5:import shutil
scripts/sort_neighbor_v35_benchmark.py:11:INPUT_DIR = PROJECT / "data/input/test"
scripts/sort_neighbor_v35_benchmark.py:75:        if (INPUT_DIR / Path(r["file"]).name).exists()
scripts/sort_neighbor_v35_benchmark.py:81:    print(f"Input images : {len(results)}")
scripts/sort_neighbor_v35_benchmark.py:229:        src = INPUT_DIR / image
scripts/sort_neighbor_v35_benchmark.py:232:        shutil.copy2(src, dst)
scripts/sort_test_and_report_v2.py:6:import shutil
scripts/sort_test_and_report_v2.py:17:INPUT_DIR = PROJECT / "data/input/test"
scripts/sort_test_and_report_v2.py:100:        str(INPUT_DIR),
scripts/sort_test_and_report_v2.py:114:    print("Input:", INPUT_DIR)
scripts/sort_test_and_report_v2.py:175:        shutil.copy2(source, destination)
scripts/sort_test_and_report_v2.py:358:    if not INPUT_DIR.exists():
scripts/sort_test_and_report_v2.py:359:        raise RuntimeError(f"Нет папки: {INPUT_DIR}")
scripts/make_subfingerprints_v2.py:4:import shutil
scripts/make_subfingerprints_v2.py:162:            unused.remove(seed)
scripts/make_subfingerprints_v2.py:205:                        keep, remove = i, j
scripts/make_subfingerprints_v2.py:207:                        keep, remove = j, i
scripts/make_subfingerprints_v2.py:211:                        | set(groups[remove]["members"])
scripts/make_subfingerprints_v2.py:216:                    groups.pop(remove)
scripts/make_subfingerprints_v2.py:240:        shutil.rmtree(output)
scripts/benchmark_test_v1.py:14:TEST_DIR = PROJECT / "data/input/test"
scripts/banner_search_v03.py:18:BANNER_DIR = PROJECT / "data/input/banners"
scripts/banner_search_v03.py:19:PHOTO_DIR = PROJECT / "data/input/test"
scripts/benchmark_test_sub_exp.py:14:TEST_DIR = PROJECT / "data/input/test"
scripts/banner_search_v03_2.py:19:BANNER_DIR = PROJECT / "data/input/banners"
scripts/banner_search_v03_2.py:20:PHOTO_DIR = PROJECT / "data/input/test"
scripts/sort_test_and_report.py:5:import shutil
scripts/sort_test_and_report.py:11:INPUT_DIR = Path("data/input/test")
scripts/sort_test_and_report.py:69:        shutil.rmtree(OUTPUT_DIR)
scripts/sort_test_and_report.py:87:    print(f"INPUT:       {INPUT_DIR}")
scripts/sort_test_and_report.py:136:        shutil.copy2(src, dst)
scripts/sort_test_and_report.py:248:        "input": str(INPUT_DIR),
scripts/banner_model_compare_v04.py:12:INPUT_DIR = Path("data/input/test")
scripts/banner_model_compare_v04.py:221:        list(INPUT_DIR.glob("*.JPG"))
scripts/banner_model_compare_v04.py:223:        list(INPUT_DIR.glob("*.jpg"))
scripts/banner_model_compare_v04.py:225:        list(INPUT_DIR.glob("*.PNG"))
scripts/banner_model_compare_v04.py:227:        list(INPUT_DIR.glob("*.png"))
scripts/sort_margin005_best.py:4:import shutil
scripts/sort_margin005_best.py:11:INPUT_CSV = (
scripts/sort_margin005_best.py:16:SOURCE_DIR = PROJECT / "data/input/test"
scripts/sort_margin005_best.py:31:        shutil.copy2(src, dst)
scripts/sort_margin005_best.py:43:            shutil.copy2(src, candidate)
scripts/sort_margin005_best.py:55:    print("CSV   :", INPUT_CSV)
scripts/sort_margin005_best.py:60:    if not INPUT_CSV.exists():
scripts/sort_margin005_best.py:61:        raise FileNotFoundError(INPUT_CSV)
scripts/sort_margin005_best.py:68:        shutil.rmtree(OUTPUT_DIR)
scripts/sort_margin005_best.py:74:    with INPUT_CSV.open(
scripts/create_previews_v01.py:52:        "--input",
scripts/create_previews_v01.py:65:    input_dir = Path(args.input).expanduser().resolve()
scripts/create_previews_v01.py:68:    if not input_dir.exists():
scripts/create_previews_v01.py:70:            f"ERROR: input directory does not exist: {input_dir}"
scripts/create_previews_v01.py:76:            for p in input_dir.rglob("*")
scripts/create_previews_v01.py:86:    print("INPUT :", input_dir)
scripts/create_previews_v01.py:99:        relative = source.relative_to(input_dir)
scripts/banner_crop_search_v02.py:5:import shutil
scripts/banner_crop_search_v02.py:18:BANNER_DIR = PROJECT / "data/input/banners"
scripts/banner_crop_search_v02.py:19:PHOTO_DIR = PROJECT / "data/input/test"
scripts/banner_qwen25vl_test_v01.py:11:INPUT_DIR = Path("data/input/test")
scripts/banner_qwen25vl_test_v01.py:152:        list(INPUT_DIR.glob("*.JPG"))
scripts/banner_qwen25vl_test_v01.py:153:        + list(INPUT_DIR.glob("*.jpg"))
scripts/banner_qwen25vl_test_v01.py:154:        + list(INPUT_DIR.glob("*.PNG"))
scripts/banner_qwen25vl_test_v01.py:155:        + list(INPUT_DIR.glob("*.png"))
scripts/banner_model_compare_v05.py:12:INPUT_DIR = Path("data/input/test")
scripts/banner_model_compare_v05.py:289:        list(INPUT_DIR.glob("*.JPG"))
scripts/banner_model_compare_v05.py:290:        + list(INPUT_DIR.glob("*.jpg"))
scripts/banner_model_compare_v05.py:291:        + list(INPUT_DIR.glob("*.PNG"))
scripts/banner_model_compare_v05.py:292:        + list(INPUT_DIR.glob("*.png"))
scripts/banner_llm_full_v02.py:15:    "data/input/banners/видео_сизякин.jpg"
scripts/banner_llm_full_v02.py:19:    "data/input/test/Ашхабадский_01.JPG"
scripts/sort_neighbor_v34.py:4:import shutil
scripts/sort_neighbor_v34.py:10:INPUT_DIR = PROJECT / "data/input/test"
scripts/sort_neighbor_v34.py:45:        for p in INPUT_DIR.iterdir()
scripts/sort_neighbor_v34.py:104:    print(f"Input images : {len(files)}")
scripts/sort_neighbor_v34.py:266:        shutil.copy2(
scripts/sort_test_and_report_hybrid_v12.py:6:import shutil
scripts/sort_test_and_report_hybrid_v12.py:17:INPUT_DIR = PROJECT / "data/input/test"
scripts/sort_test_and_report_hybrid_v12.py:100:        str(INPUT_DIR),
scripts/sort_test_and_report_hybrid_v12.py:114:    print("Input:", INPUT_DIR)
scripts/sort_test_and_report_hybrid_v12.py:175:        shutil.copy2(source, destination)
scripts/sort_test_and_report_hybrid_v12.py:358:    if not INPUT_DIR.exists():
scripts/sort_test_and_report_hybrid_v12.py:359:        raise RuntimeError(f"Нет папки: {INPUT_DIR}")
scripts/sort_sequence_v38_1_subtest.py:4:import shutil
scripts/sort_sequence_v38_1_subtest.py:11:INPUT_DIR = PROJECT / "data/input/test"
scripts/sort_sequence_v38_1_subtest.py:91:            INPUT_DIR /
scripts/sort_sequence_v38_1_subtest.py:258:        shutil.copy2(
scripts/sort_sequence_v38_1_subtest.py:259:            INPUT_DIR/d["image"],
scripts/search_banners_v01.py:4:import shutil
scripts/search_banners_v01.py:15:BANNER_DIR = PROJECT / "data/input/banners"
scripts/search_banners_v01.py:16:SEARCH_DIR = PROJECT / "data/input/test"
scripts/search_banners_v01.py:226:            shutil.copy2(
scripts/run_daily_hybrid_v12.sh:7:INPUT="$PROJECT/data/input/daily"
scripts/run_daily_hybrid_v12.sh:11:OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"
scripts/run_daily_hybrid_v12.sh:15:echo "SCENE FINGERPRINT — DAILY HYBRID V12"
scripts/run_daily_hybrid_v12.sh:18:echo "INPUT : $INPUT"
scripts/run_daily_hybrid_v12.sh:22:if [ ! -d "$INPUT" ]; then
scripts/run_daily_hybrid_v12.sh:23:    echo "ERROR: input directory does not exist:"
scripts/run_daily_hybrid_v12.sh:24:    echo "$INPUT"
scripts/run_daily_hybrid_v12.sh:28:COUNT=$(find "$INPUT" -maxdepth 1 -type f \
scripts/run_daily_hybrid_v12.sh:36:    echo "ERROR: no images found in $INPUT"
scripts/run_daily_hybrid_v12.sh:42:/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
scripts/run_daily_hybrid_v12.sh:43:    --input "$INPUT" \
scripts/run_daily_hybrid_v12.sh:50:echo "DAILY PIPELINE FINISHED"
scripts/sort_sequence_v39.py:4:import shutil
scripts/sort_sequence_v39.py:11:INPUT_DIR = PROJECT / "data/input/test"
scripts/sort_sequence_v39.py:91:            INPUT_DIR /
scripts/sort_sequence_v39.py:258:        shutil.copy2(
scripts/sort_sequence_v39.py:259:            INPUT_DIR/d["image"],
scripts/banner_qwen4b_test_v01.py:11:INPUT_DIR = Path("data/input/test")
scripts/banner_qwen4b_test_v01.py:152:        list(INPUT_DIR.glob("*.JPG"))
scripts/banner_qwen4b_test_v01.py:153:        + list(INPUT_DIR.glob("*.jpg"))
scripts/banner_qwen4b_test_v01.py:154:        + list(INPUT_DIR.glob("*.PNG"))
scripts/banner_qwen4b_test_v01.py:155:        + list(INPUT_DIR.glob("*.png"))
scripts/run_hybrid_v12.py:5:import shutil
scripts/run_hybrid_v12.py:96:def run_recognition(input_dir, fingerprints):
scripts/run_hybrid_v12.py:110:        str(input_dir),
scripts/run_hybrid_v12.py:123:    print("Input:", input_dir)
scripts/run_hybrid_v12.py:211:    Input:
scripts/run_hybrid_v12.py:445:        shutil.copy2(
scripts/run_hybrid_v12.py:507:        "--input",
scripts/run_hybrid_v12.py:532:    input_dir = args.input
scripts/run_hybrid_v12.py:535:    if not input_dir.exists():
scripts/run_hybrid_v12.py:537:            f"Нет папки: {input_dir}"
scripts/run_hybrid_v12.py:553:    print("INPUT :", input_dir)
scripts/run_hybrid_v12.py:569:        input_dir,
scripts/banner_llm_folder_search_v01.py:6:import shutil
scripts/banner_llm_folder_search_v01.py:18:    "data/input/banners"
scripts/banner_llm_folder_search_v01.py:22:    "data/input/test"
scripts/banner_llm_folder_search_v01.py:234:                shutil.copy2(
scripts/build_subfingerprints_exp.py:5:import shutil
scripts/build_subfingerprints_exp.py:53:                shutil.copy2(
scripts/make_subfingerprints.py:5:import shutil
scripts/make_subfingerprints.py:335:        shutil.rmtree(output)
scripts/sort_neighbor_v37.py:5:import shutil
scripts/sort_neighbor_v37.py:10:INPUT_DIR = PROJECT / "data/input/new"
scripts/sort_neighbor_v37.py:247:    shutil.rmtree(SORTED_DIR)
scripts/sort_neighbor_v37.py:252:    src = INPUT_DIR / row["image"]
scripts/sort_neighbor_v37.py:260:    shutil.copy2(src, destination / src.name)
scripts/sort_neighbor_v37.py:288:print(f"Input images : {len(records)}")
scripts/sort_baseline.py:5:import shutil
scripts/sort_baseline.py:31:    print("INPUT:", len(data))
scripts/sort_baseline.py:72:        shutil.copy2(src, dst)
scripts/banner_crop_search_v01.py:4:import shutil
scripts/banner_crop_search_v01.py:16:BANNER_DIR = PROJECT / "data/input/banners"
scripts/banner_crop_search_v01.py:17:PHOTO_DIR = PROJECT / "data/input/test"
scripts/qwen4b_output_v01_before_compact_prompt.py:14:INPUT_DIR = PROJECT / "data" / "output" / "test_sorted_v2"
scripts/qwen4b_output_v01_before_compact_prompt.py:415:    for path in INPUT_DIR.rglob("*"):
scripts/qwen4b_output_v01_before_compact_prompt.py:428:    relative = source.relative_to(INPUT_DIR)
scripts/qwen4b_output_v01_before_compact_prompt.py:578:        "input": str(INPUT_DIR),
scripts/qwen4b_output_v01_before_compact_prompt.py:653:    print("INPUT:", INPUT_DIR)
scripts/qwen4b_output_v01.py:14:INPUT_DIR = PROJECT / "data" / "output" / "test_sorted_v2"
scripts/qwen4b_output_v01.py:264:    for path in INPUT_DIR.rglob("*"):
scripts/qwen4b_output_v01.py:277:    relative = source.relative_to(INPUT_DIR)
scripts/qwen4b_output_v01.py:446:        "input": str(INPUT_DIR),
scripts/qwen4b_output_v01.py:503:    global INPUT_DIR, OUTPUT_DIR
scripts/qwen4b_output_v01.py:515:        "--input",
scripts/qwen4b_output_v01.py:517:        default=INPUT_DIR,
scripts/qwen4b_output_v01.py:518:        help="Input directory with sorted photos"
scripts/qwen4b_output_v01.py:530:    INPUT_DIR = args.input.expanduser().resolve()
scripts/qwen4b_output_v01.py:540:    print("INPUT:", INPUT_DIR)
scripts/banner_candidates_v01.py:16:BANNER_DIR = PROJECT / "data/input/banners"
scripts/banner_candidates_v01.py:17:PHOTO_DIR = PROJECT / "data/input/test"
scripts/banner_search_v02.py:4:import shutil
scripts/banner_search_v02.py:15:    "data/input/test"
scripts/banner_search_v02.py:119:            shutil.copy2(
scripts/banner_search_v03_3.py:16:BANNER_DIR = PROJECT / "data/input/banners"
scripts/banner_search_v03_3.py:17:PHOTO_DIR = PROJECT / "data/input/test"
scripts/crop_test_banner.py:5:INPUT = Path(
scripts/crop_test_banner.py:6:    "data/input/test/Ашхабадский_01.JPG"
scripts/crop_test_banner.py:25:    img = Image.open(INPUT)
scripts/banner_llm_full_v01.py:13:    "data/input/banners/видео_сизякин.jpg"
scripts/banner_llm_full_v01.py:17:    "data/input/test/Ашхабадский_01.JPG"
scripts/banner_model_compare_v02.py:15:INPUT_DIR = Path("data/input/test")
scripts/banner_model_compare_v02.py:153:        list(INPUT_DIR.glob("*.JPG"))
scripts/banner_model_compare_v02.py:155:        list(INPUT_DIR.glob("*.jpg"))
scripts/banner_model_compare_v02.py:157:        list(INPUT_DIR.glob("*.png"))
scripts/banner_model_compare_v01.py:15:INPUT_DIR = Path("data/input/test")
scripts/banner_model_compare_v01.py:142:        list(INPUT_DIR.glob("*.JPG")) +
scripts/banner_model_compare_v01.py:143:        list(INPUT_DIR.glob("*.jpg")) +
scripts/banner_model_compare_v01.py:144:        list(INPUT_DIR.glob("*.png"))
scripts/banner_database_v02.py:17:INPUT_DIR = Path(
scripts/banner_database_v02.py:18:    "data/input/test"
scripts/banner_database_v02.py:273:        x for x in INPUT_DIR.iterdir()
scripts/banner_search_v01.py:4:import shutil
scripts/banner_search_v01.py:15:    "data/input/test"
scripts/banner_search_v01.py:95:            shutil.copy2(
scripts/dry_run_best_sequence.py:15:INPUT_DIR = PROJECT / "data/input/test"
scripts/dry_run_best_sequence.py:59:        for p in INPUT_DIR.iterdir()
scripts/dry_run_best_sequence.py:140:    print("INPUT:", INPUT_DIR)
scripts/dry_run_best_sequence.py:149:    if not INPUT_DIR.exists():
scripts/dry_run_best_sequence.py:150:        raise FileNotFoundError(INPUT_DIR)
scripts/build_subfingerprint_database.py:4:import shutil
scripts/build_subfingerprint_database.py:80:                shutil.rmtree(tmp)
scripts/build_subfingerprint_database.py:85:                shutil.copy2(
scripts/build_subfingerprint_database.py:96:            shutil.rmtree(tmp)
scripts/sort_neighbor_v36_img.py:5:import shutil
scripts/sort_neighbor_v36_img.py:10:INPUT_DIR = PROJECT / "data/input/test_img"
scripts/sort_neighbor_v36_img.py:258:        src = INPUT_DIR / filename
scripts/sort_neighbor_v36_img.py:266:        shutil.copy2(
scripts/sort_neighbor_v36_img.py:311:    print(f"Input images : {len(rows)}")
scripts/sort_neighbor_v36.py:5:import shutil
scripts/sort_neighbor_v36.py:10:INPUT_DIR = PROJECT / "data/input/test"
scripts/sort_neighbor_v36.py:258:        src = INPUT_DIR / filename
scripts/sort_neighbor_v36.py:266:        shutil.copy2(
scripts/sort_neighbor_v36.py:311:    print(f"Input images : {len(rows)}")
scripts/sort_sequence_v38.py:4:import shutil
scripts/sort_sequence_v38.py:11:INPUT_DIR = PROJECT / "data/input/test"
scripts/sort_sequence_v38.py:78:        if (INPUT_DIR / Path(r["file"]).name).exists()
scripts/sort_sequence_v38.py:215:        src=INPUT_DIR/d["image"]
scripts/sort_sequence_v38.py:228:        shutil.copy2(
scripts/banner_database_v01.py:17:INPUT_DIR = Path(
scripts/banner_database_v01.py:18:    "data/input/test"
scripts/banner_database_v01.py:208:        x for x in INPUT_DIR.iterdir()
scripts/llm_resolver_v01.py:190:    print(f"Input: {REPORT}")
scripts/sort_sequence_sub_v01.py:4:import shutil
scripts/sort_sequence_sub_v01.py:11:INPUT_DIR = PROJECT / "data/input/test"
scripts/sort_sequence_sub_v01.py:90:            INPUT_DIR /
scripts/sort_sequence_sub_v01.py:257:        shutil.copy2(
scripts/sort_sequence_sub_v01.py:258:            INPUT_DIR/d["image"],
scripts/export_subclusters.py:4:import shutil
scripts/export_subclusters.py:14:INPUT_DIR = PROJECT / "data/input"
scripts/export_subclusters.py:36:    # data/input/89/89_01.JPG
scripts/export_subclusters.py:38:        INPUT_DIR / fp_name.split("_")[0] / img_name,
scripts/export_subclusters.py:39:        INPUT_DIR / fp_name / img_name,
scripts/export_subclusters.py:133:            shutil.rmtree(out_dir)
scripts/export_subclusters.py:183:                    shutil.copy2(
scripts/sort_sequence_v38_1.py:4:import shutil
scripts/sort_sequence_v38_1.py:11:INPUT_DIR = PROJECT / "data/input/test"
scripts/sort_sequence_v38_1.py:91:            INPUT_DIR /
scripts/sort_sequence_v38_1.py:258:        shutil.copy2(
scripts/sort_sequence_v38_1.py:259:            INPUT_DIR/d["image"],
scripts/export_visual_compare.py:2:import shutil
scripts/export_visual_compare.py:6:SRC_ROOT = Path("data/input/test")
scripts/export_visual_compare.py:36:        shutil.copy2(src,dst)
scripts/export_visual_compare.py:68:        shutil.copy2(src,dst)
scripts/banner_model_compare_v03.py:12:INPUT_DIR = Path("data/input/test")
scripts/banner_model_compare_v03.py:168:        list(INPUT_DIR.glob("*.JPG"))
scripts/banner_model_compare_v03.py:169:        + list(INPUT_DIR.glob("*.jpg"))
scripts/banner_model_compare_v03.py:170:        + list(INPUT_DIR.glob("*.PNG"))
scripts/banner_model_compare_v03.py:171:        + list(INPUT_DIR.glob("*.png"))
scripts/sort_neighbor_v35.py:4:import shutil
scripts/sort_neighbor_v35.py:10:INPUT_DIR = PROJECT / "data/input/test"
scripts/sort_neighbor_v35.py:33:            if (INPUT_DIR / row["image"]).exists():
scripts/sort_neighbor_v35.py:259:            INPUT_DIR / item["image"]
scripts/sort_neighbor_v35.py:286:        shutil.copy2(
scripts/sort_neighbor_v35.py:332:        f"Input images : {len(rows)}"
app/web/components/search.py:174:        search = ui.input(
app/web/components/filters.py:40:                icon="remove",
app/web/components/technical_modules/photo_processing.py:9:DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
app/web/components/technical_modules/photo_processing.py:14:    source_input = ui.input(
app/web/components/technical_modules/photo_processing.py:16:        value=str(PROJECT / "data/input/daily"),
app/web/components/technical_modules/photo_processing.py:21:    output_input = ui.input(
app/web/components/technical_modules/photo_processing.py:23:        value=str(PROJECT / "data/output/daily"),
app/web/components/technical_modules/photo_processing.py:38:        input_dir = Path(
app/web/components/technical_modules/photo_processing.py:39:            source_input.value
app/web/components/technical_modules/photo_processing.py:42:        if not input_dir.is_absolute():
app/web/components/technical_modules/photo_processing.py:43:            input_dir = PROJECT / input_dir
app/web/components/technical_modules/photo_processing.py:45:        if not input_dir.exists():
app/web/components/technical_modules/photo_processing.py:47:                f"Папка не найдена: {input_dir}",
app/web/components/technical_modules/photo_processing.py:53:            p for p in input_dir.iterdir()
app/web/components/technical_modules/photo_processing.py:69:        if not DAILY_SCRIPT.exists():
app/web/components/technical_modules/photo_processing.py:71:                f"Не найден скрипт: {DAILY_SCRIPT}",
app/web/components/technical_modules/photo_processing.py:101:                str(DAILY_SCRIPT),
app/web/components/technical_modules/photo_processing.py:176:            output_input.value = str(
app/web/components/technical_modules/photo_processing.py:243:                    "--input",
app/web/components/technical_modules/photo_processing.py:293:                output_input.value = str(
app/web/components/technical_modules/photo_processing.py:355:            source_input
app/web/components/technical_modules/photo_processing.py:372:            output_input
app/web/components/technical_modules/data.py:12:DAILY_ROOT = PROJECT / "data" / "output" / "daily"
app/web/components/technical_modules/data.py:24:def latest_daily_root():
app/web/components/technical_modules/data.py:25:    if not DAILY_ROOT.exists():
app/web/components/technical_modules/data.py:29:        p for p in DAILY_ROOT.iterdir()
app/web/components/technical_modules/data.py:56:def daily_stats():
app/web/components/technical_modules/data.py:57:    root = latest_daily_root()
app/web/components/technical_modules/data.py:242:    daily = daily_stats()
app/web/components/technical_modules/data.py:343:                    f"Последний запуск: {daily['run']}"
app/web/components/technical_modules/data.py:349:                "ГОТОВ" if daily["photos"] else "НЕТ ДАННЫХ",
app/web/components/technical_modules/data.py:350:                color="positive" if daily["photos"] else "warning",
app/web/components/technical_modules/data.py:358:                f"Фото: {daily['photos']}"
app/web/components/technical_modules/data.py:362:                f"Адресов: {daily['addresses']}"
app/web/components/technical_modules/users.py:146:                    name_input = ui.input(
app/web/components/technical_modules/users.py:187:                    custom_color = ui.color_input(
app/web/components/technical_modules/users.py:201:                            name_input.value or ""
app/web/components/technical_modules/users.py:275:                    name_input = ui.input(
app/web/components/technical_modules/users.py:285:                            name_input.value or ""
app/web/components/technical_modules/users.py:579:                                custom_color = ui.color_input(
app/web/components/technical_modules/qwen.py:17:DAILY_ROOT = (
app/web/components/technical_modules/qwen.py:21:    / "daily"
app/web/components/technical_modules/qwen.py:182:    if not DAILY_ROOT.exists():
app/web/components/technical_modules/qwen.py:187:        for p in DAILY_ROOT.iterdir()
app/web/components/technical_modules/qwen.py:403:                f"[QWEN MANUAL] INPUT: {result_dir}",
app/web/components/technical_modules/qwen.py:448:                "--input",
app/web/components/addresses.py:3:from app.web.components.photos import get_latest_daily_root
app/web/components/addresses.py:16:    daily_root = get_latest_daily_root()
app/web/components/addresses.py:18:    if daily_root is None:
app/web/components/addresses.py:21:    return daily_root / f"{address}_v33"
app/web/components/collections.py:16:        name = ui.input(
app/web/components/photos.py:20:    / "daily"
app/web/components/photos.py:23:DAILY_ROOT = (
app/web/components/photos.py:27:    / "daily"
app/web/components/photos.py:31:def get_latest_daily_root():
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
"INSERT INTO photos|UPDATE photos|psycopg2.connect|photo_id" \
scripts app \
--include="*.py" 2>/dev/null
scripts/import_qwen_to_db.py:166:        INSERT INTO photos (
scripts/migrate_sqlite_to_postgres.py:52:    pg_conn = psycopg2.connect(
scripts/migrate_sqlite_to_postgres.py:155:                INSERT INTO photos (
app/web/components/search.py:90:    with psycopg2.connect(**PG_CONFIG) as conn:
app/web/photo_db.py:44:    with psycopg2.connect(**PG_CONFIG) as conn:
app/web/client_db.py:46:    with psycopg2.connect(**PG_CONFIG) as conn:
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:05:45

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed Albion Fotobase architecture, photo IDs, scripts, and grid visibility rules**
>
> 
>
> Worked for 9s

Да. Мы уже подошли к правильной точке.

Сейчас у нас:

- PostgreSQL `photobase` - основная БД.
- `photos.photo_id` уже существует и заполнен: `PH_00000001 ... PH_00000100`.
- `photo_id` должен быть **создан в самом начале обработки**, ещё до DINO/Qwen/сортировки.
- Грид **не должен показывать исходные нераспределённые фото**.
- Фото попадает в грид только когда оно уже отсортировано и есть соответствующая запись в PostgreSQL.
- Превью можно создавать **в конце сортировки**, после появления записи.
- Qwen потом дополняет существующую запись по `photo_id`, а не создаёт новую фотографию.
- DINO также должен работать с тем же `photo_id`.

То есть логика должна стать такой:

```text
data/input/daily
        │
        ▼
┌──────────────────────┐
│ 1. REGISTRATION      │
│ создать photo_id     │
│ PH_00000101          │
└──────────┬───────────┘
           │
           ├── исходный файл
           ├── photo_id
           └── технические метаданные
                    │
                    ▼
             DINO / HYBRID
                    │
                    ▼
              СОРТИРОВКА
                    │
                    ▼
        data/output/daily/.../85_v33/
                    │
                    ▼
        PostgreSQL UPDATE photos
        ├── photo_id
        ├── address
        ├── path
        └── filename
                    │
                    ▼
             создать preview
                    │
                    ▼
                 ГРИД
```

И самое важное: **грид вообще не должен самостоятельно искать новые файлы в `data/input/daily`**. Его источник истины - PostgreSQL + уже отсортированный файл.

### Следующий шаг

Нам сейчас надо найти **точку входа `run_daily_hybrid_v12.sh → run_hybrid_v12.py`**, где можно поставить регистрацию фотографий.

Покажи сначала начало и конец `run_hybrid_v12.py`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,180p' scripts/run_hybrid_v12.py && \
echo "==================== MAIN ====================" && \
sed -n '420,620p' scripts/run_hybrid_v12.py
```

После этого я предложу конкретное изменение: **одна регистрация `photo_id` до распознавания**, затем передача этого ID через весь pipeline до PostgreSQL.

Пока **ничего в коде не меняем** - сначала точно найдём точку входа, чтобы не сломать замороженный Hybrid v12.

---

### 👤 **User** — 2026-08-18 21:06:45

int_mvp_v02 && \
sed -n '1,180p' scripts/run_hybrid_v12.py && \
echo "==================== MAIN ====================" && \
sed -n '420,620p' scripts/run_hybrid_v12.py
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

def adapt_recognizer_rows(rows):
    """
==================== MAIN ====================

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

    recognition = adapt_recognizer_rows(recognition)

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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
 не надо жестко привязывать инпут папк

---

### 🤖 **Assistant** — 2026-08-18 21:06:46

Да, **жёстко привязывать `input` к конкретной папке не надо**. И сейчас у нас уже правильная основа:

```bash
run_daily_hybrid_v12.sh
    --input "$INPUT"
    --output "$OUTPUT"
```

а `run_hybrid_v12.py` принимает:

```python
parser.add_argument(
    "--input",
    required=True,
    type=Path,
)
```

То есть `run_hybrid_v12.py` уже универсальный — он не знает, что это обязательно `data/input/daily`.

### Что предлагаю сделать

Разделить понятия:

```text
INPUT
  ↓
регистрация фото → photo_id
  ↓
DINO
  ↓
Hybrid v12
  ↓
OUTPUT
  ↓
создание записи PostgreSQL
  ↓
превью
  ↓
грид
```

При этом `input` может быть любым:

```bash
--input data/input/daily
```

или

```bash
--input /mnt/photos/incoming
```

или

```bash
--input /какая/угодно/папка
```

### И ещё важный момент

Я бы **не вносил регистрацию `photo_id` прямо внутрь `run_recognition()`**.

Лучше перед DINO добавить отдельный этап:

```python
photo_registry = register_input_photos(input_dir)
```

Он получает реальные файлы из переданного `input_dir` и для каждого:

```text
photo_id = PH_00000101
filename = ...
source_path = ...
```

После этого DINO работает как сейчас, а мы **привязываем результат распознавания к уже существующему `photo_id`**.

Тогда замороженный:

```text
DINO v33
Hybrid v12
```

вообще не трогаем.

И после сортировки уже делаем:

```text
photo_id
    ↓
address
path
filename
```

в PostgreSQL.

### А грид

Тут полностью согласен с твоей логикой:

**до сортировки фото в гриде нет.**

Потому что иначе появляются фотографии без адреса, а чекбоксы адресов теряют смысл.

Грид делает:

```sql
SELECT ...
FROM photos
WHERE address IS NOT NULL
```

и дальше применяет выбранные адреса/клиентов.

То есть:

```text
input
 └─ фото ещё НЕ в гриде

DINO
 └─ определил кандидата

Hybrid
 └─ определил final address

sort
 └─ физически положил фото

PostgreSQL
 └─ появилась/обновилась запись с address + path

preview
 └─ создан

GRID
 └─ теперь фото появляется
```

Это как раз убирает путаницу.

**Следующий шаг:** нам надо посмотреть оставшуюся часть `run_hybrid_v12.py`, особенно функцию сортировки целиком и место, где формируется `sorted_rows`. Тогда аккуратно вставим `photo_id`, не меняя сам Hybrid v12.

---

### 👤 **User** — 2026-08-18 21:07:24

давайц смотреть

---

### 🤖 **Assistant** — 2026-08-18 21:07:26

Да. Смотрим именно в эту сторону.

Сейчас у нас уже есть важная база:

- `photos.photo_id` создан;
- 100 записей имеют уникальные `PH_00000001 ... PH_00000100`;
- `photo_id` будет **постоянным идентификатором фотографии**;
- `address` — это уже **результат сортировки DINO**, а не идентификатор фото;
- грид должен брать фотографии **только из БД**, поэтому несортированные файлы в `data/input/...` сами по себе в гриде не появляются;
- превью можно создавать **после сортировки**, когда уже есть `photo_id`, `address`, `path`;
- `Qwen` и будущий DINO-этап могут привязываться к `photo_id`, а не к имени файла/пути.

И да — **`run_hybrid_v12.py` не надо жестко привязывать к `data/input/daily`**. У него уже сейчас это правильно сделано через:

```python
parser.add_argument(
    "--input",
    required=True,
    type=Path,
)
```

То есть проблема не в самом `run_hybrid_v12.py`, а в обвязке и следующем этапе.

### Я бы зафиксировал поток так

```text
INPUT
  │
  │ фотографии
  ▼
[создание photo_id]
  │
  │ PH_00000123
  ▼
[ DINO / Hybrid ]
  │
  │ assigned_id = 85_v33
  ▼
[ SORT ]
  │
  ├── data/output/daily/<run>/85_v33/photo.JPG
  │
  ├── запись в PostgreSQL
  │      photo_id = PH_00000123
  │      address  = 85_v33
  │      path     = ...
  │
  └── создание preview
  │
  ▼
[ Qwen ]
  │
  │ photo_id = PH_00000123
  ▼
[ DB ]
  │
  ▼
[ GRID ]
```

И самое важное: **до сортировки фото может существовать физически, но не обязано отображаться в гриде**.

---

### Сейчас я бы не трогал `get_filtered_photos()`

Он уже соответствует нужной логике:

```python
if not selected_addresses:
    files = get_all_indexed_photos()
else:
    ...
```

То есть `PHOTO_INDEX` является источником того, что считается отображаемой фотографией.

Нужно только сделать так, чтобы `PHOTO_INDEX` строился **из БД**, а не из физического просмотра папок.

Тогда чекбоксы адресов работают естественно:

```text
☑ 78_v33
☐ 79_v33
☑ 85_v33
```

→ грид показывает только DB-записи с этими `address`.

---

### А `photo_id` должен пройти через весь pipeline

Вот это сейчас главный следующий шаг.

Сейчас `run_hybrid_v12.py` получает:

```python
item["file"]
item["best_id"]
```

и при сортировке делает:

```python
source = Path(item["file"])

assigned_id = item.get("best_id")

destination_dir = output_dir / assigned_id
destination_dir.mkdir(...)
destination = destination_dir / source.name

shutil.copy2(source, destination)
```

Здесь нужно добавить **регистрацию фотографии**, но не делать так:

```text
filename → id
```

а:

```text
каждая новая фотография → новый photo_id
```

Например:

```text
PH_00000101
```

и уже затем:

```text
photo_id     PH_00000101
filename     Ашхабадский_12.JPG
address      85_v33
path         data/output/daily/20260818_201500/85_v33/Ашхабадский_12.JPG
```

---

### И ещё один принцип я бы сейчас зафиксировал

**`photo_id` не должен меняться при перемещении/копировании фотографии.**

Например:

```text
PH_00000101
```

сегодня:

```text
input/Ашхабадский_12.JPG
```

после сортировки:

```text
output/daily/.../85_v33/Ашхабадский_12.JPG
```

после обработки:

```text
archive/.../85_v33/Ашхабадский_12.JPG
```

ID остаётся:

```text
PH_00000101
```

Меняется только `path`.

Это как раз позволит Qwen, DINO, превью, поиску и истории обработки ссылаться на **один объект**, независимо от того, где физически лежит файл.

---

И ещё: **`id INTEGER` в таблице пока можно оставить как внутренний технический PostgreSQL ID**, а `photo_id TEXT` использовать как наш бизнес-идентификатор.

То есть:

```text
id       = 123              ← внутренний БД
photo_id = PH_00000123      ← идентификатор фотографии проекта
```

Это лучше, чем полностью переделывать существующий `id`.

### Следующий шаг

Я бы сейчас посмотрел **полностью `run_hybrid_v12.py` от функции сортировки до конца**, потому что именно туда нужно аккуратно встроить:

1. генерацию `photo_id`;
2. запись фотографии в PostgreSQL;
3. `address`;
4. `path`;
5. затем создание preview;
6. и только после этого обновление грида.

Дай вывод:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '180,520p' scripts/run_hybrid_v12.py
```

И будем менять уже **конкретно этот pipeline**, не ломая замороженную логику Hybrid v12.

---

### 👤 **User** — 2026-08-18 21:09:10

имя потом можно менять у файла - если он напримернеправильно отсортирован - по похожести, надо иметь возможность изменить имя и адресную папку

---

### 🤖 **Assistant** — 2026-08-18 21:09:11

Да. И это как раз ещё один аргумент в пользу отдельного `photo_id`.

Нужно разделить **идентичность фотографии** и её **текущее расположение/имя**.

### Модель

```text
photo_id = PH_00000123     ← никогда не меняется
```

А вот это можно менять:

```text
address = 85_v33
filename = Ашхабадский_12.JPG
path = data/output/.../85_v33/Ашхабадский_12.JPG
```

Например, DINO сначала ошибся:

```text
PH_00000123
85_v33/
Ашхабадский_12.JPG
```

Пользователь определил, что фото на самом деле относится к `78_v33`.

Мы делаем:

```text
PH_00000123
78_v33/
Комарова13_27.JPG
```

**`photo_id` остаётся тем же.**

---

### Причём я бы позволил менять отдельно

1. **Адрес**
   ```text
   85_v33 → 78_v33
   ```

2. **Имя файла**
   ```text
   Ашхабадский_12.JPG
   → Комарова13_27.JPG
   ```

3. **Оба одновременно**

А физически при этом:

```text
старый путь
    ↓
перемещение/переименование
    ↓
новый путь
```

и в БД обновляется:

```text
address
filename
path
```

но:

```text
photo_id
```

не трогается.

---

### Более того, это даст нам историю

Я бы даже заложил возможность хранить:

```text
photo_id: PH_00000123

DINO:
    predicted_address = 85_v33
    score = 0.81

USER:
    final_address = 78_v33
    final_filename = Комарова13_27.JPG
```

Тогда мы **не теряем результат DINO**, даже если человек его исправил.

И в будущем можно анализировать:

> DINO постоянно путает 85_v33 и 78_v33.

Это уже полезная информация для улучшения распознавания.

---

### И главное для грида

Грид вообще не должен определять адрес по имени файла или по физической папке.

Он должен видеть:

```text
photo_id       PH_00000123
address        78_v33
filename       Комарова13_27.JPG
path           ...
```

Поэтому если мы переносим фото:

```text
85_v33/Ашхабадский_12.JPG
        ↓
78_v33/Комарова13_27.JPG
```

грид после обновления БД автоматически покажет его в `78_v33`.

Чекбоксы адресов при этом продолжают работать абсолютно нормально.

**То есть архитектурно у нас получается:**

```text
                    ┌───────────────┐
                    │   photo_id    │
                    │ PH_00000123   │
                    │   неизменный  │
                    └───────┬───────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
         DINO/Qwen       address        filename
                            │              │
                            └──────┬───────┘
                                   ▼
                              path / preview
                                   │
                                   ▼
                                  GRID
```

Это я бы **зафиксировал как основную архитектуру** перед тем, как дальше переделывать сортировку.

---

### 👤 **User** — 2026-08-18 21:10:00

да

---

### 🤖 **Assistant** — 2026-08-18 21:10:01

Да, тогда **фиксируем эту архитектуру**.

### Основное правило проекта

`photo_id` — постоянная идентичность фотографии:

```text
PH_00000001
PH_00000002
PH_00000003
...
```

Он создаётся **в самом начале обработки** и больше никогда не меняется.

### Всё остальное — изменяемые свойства

```text
photo_id       PH_00000123   ← НЕ меняется

address        85_v33        ← можно изменить
filename       Ашхабадский_12.JPG ← можно изменить
path           ...           ← меняется при переносе
```

### Полный процесс

```text
Фото поступило
      │
      ▼
создать photo_id
      │
      ▼
DINO / Hybrid
      │
      ▼
предварительный address
      │
      ▼
сортировка
      │
      ▼
запись в PostgreSQL
      │
      ├── photo_id
      ├── address
      ├── filename
      ├── path
      └── результаты обработки
      │
      ▼
создание preview
      │
      ▼
GRID
```

Если позже выяснилось, что фото ошибочно определено:

```text
85_v33/Ашхабадский_12.JPG
          │
          ▼
      исправление
          │
          ▼
78_v33/Комарова13_27.JPG
```

то:

```text
photo_id = PH_00000123
```

остаётся прежним.

---

И ещё важный момент: **я бы не использовал `id` PostgreSQL как идентификатор проекта**.

Оставляем:

```text
id       INTEGER   ← технический ID PostgreSQL
photo_id TEXT      ← наш постоянный ID фотографии
```

Сейчас это уже практически так и сделано:

```text
id | photo_id    | address
1  | PH_00000001 | 78_v33
2  | PH_00000002 | 78_v33
...
```

Это хорошая схема.

**Следующим шагом логично переделать `run_hybrid_v12.py`: сначала выдавать `photo_id`, затем сортировать, затем создавать/обновлять запись БД и preview.** При этом сам алгоритм Hybrid v12 вообще не трогаем.

---

### 👤 **User** — 2026-08-18 21:10:52

photo id выдавать до дино - чтобы и квен и дино работали уже с эим id

---

### 🤖 **Assistant** — 2026-08-18 21:10:53

Да. **Именно так лучше.** Тогда `photo_id` становится идентификатором объекта на всём протяжении pipeline, а не появляется после DINO.

### Фиксируем окончательно

```text
                    ФОТО ПОСТУПИЛО
                           │
                           ▼
                 ┌──────────────────┐
                 │ создать photo_id │
                 │  PH_00000123     │
                 └────────┬─────────┘
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
           DINO                       QWEN
      работает с ID              работает с ID
             │                         │
             └────────────┬────────────┘
                          ▼
                     СОРТИРОВКА
                          │
                          ▼
                    ADDRESS / NAME
                          │
                          ▼
                    PostgreSQL
                          │
                          ▼
                      PREVIEW
                          │
                          ▼
                        GRID
```

То есть **ID выдаётся один раз, до любого AI-анализа**.

---

### Например

При поступлении:

```text
input/
├── IMG_001.JPG
├── IMG_002.JPG
└── IMG_003.JPG
```

сразу создаём:

```text
IMG_001.JPG → PH_00000101
IMG_002.JPG → PH_00000102
IMG_003.JPG → PH_00000103
```

И дальше DINO получает не просто:

```text
IMG_001.JPG
```

а логически:

```text
PH_00000101 → IMG_001.JPG
```

Qwen аналогично:

```text
PH_00000101 → результат Qwen
```

---

### И физическое имя вообще перестаёт быть идентификатором

Это очень важно.

Фото может пройти:

```text
PH_00000101
    │
    ├── исходное имя: IMG_001.JPG
    │
    ├── DINO → 85_v33
    │
    ├── Qwen → анализ
    │
    ├── пользователь исправил
    │
    └── итог:
          78_v33/Комарова13_27.JPG
```

При этом всё время:

```text
PH_00000101
```

---

### Я бы даже сделал промежуточный manifest

Сразу после поступления фотографий:

```text
photo_manifest.json
```

например:

```json
{
  "PH_00000101": {
    "source_path": "data/input/daily/IMG_001.JPG",
    "original_filename": "IMG_001.JPG"
  },
  "PH_00000102": {
    "source_path": "data/input/daily/IMG_002.JPG",
    "original_filename": "IMG_002.JPG"
  }
}
```

Но **главным источником истины всё равно будет PostgreSQL**.

Тогда DINO/Qwen могут использовать:

```text
photo_id → физический файл
```

а после сортировки физический путь может поменяться — `photo_id` нет.

---

### Для Qwen это особенно удобно

Сейчас у нас Qwen фактически строится вокруг:

```text
address / filename / path
```

Нужно постепенно перейти к:

```text
photo_id
```

Например результат:

```text
data/metadata/qwen4b/PH_00000101.json
```

или ещё лучше — Qwen пишет результат непосредственно в PostgreSQL по:

```text
photo_id = PH_00000101
```

Тогда переименование файла **вообще никак не ломает связь с результатом Qwen**.

---

### Для DINO аналогично

DINO может использовать временный mapping:

```text
PH_00000101 → /path/to/current/file.JPG
```

и возвращать:

```text
photo_id       = PH_00000101
predicted      = 85_v33
score           = 0.87
```

А не считать имя файла главным ключом.

---

**Итого: `photo_id` создаём первым действием после обнаружения фотографии. DINO, Qwen, сортировка, preview, PostgreSQL и GRID работают вокруг него. Имя файла, адресная папка и физический путь — изменяемые атрибуты.**

Это я бы уже считал **замороженным архитектурным решением**.

---

### 👤 **User** — 2026-08-18 21:11:47

lf

---

### 🤖 **Assistant** — 2026-08-18 21:11:48

Да. Тогда идём дальше.

Следующий шаг — **не менять пока Hybrid v12**, а сначала встроить слой `photo_id` перед DINO.

Нам нужно посмотреть, **как сейчас `run_daily_hybrid_v12.sh` запускает `run_hybrid_v12.py` и где именно начинается обработка файлов**. После этого вставим туда:

```text
INPUT
 ↓
создание photo_id
 ↓
manifest / БД
 ↓
DINO
 ↓
Hybrid
 ↓
сортировка
 ↓
обновление address + filename + path
 ↓
preview
```

Дай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat scripts/run_daily_hybrid_v12.sh && \
echo "==================== HYBRID MAIN ====================" && \
sed -n '180,430p' scripts/run_hybrid_v12.py
```

После этого уже можно будет точно определить место вставки `photo_id`, **не ломая рабочий Hybrid v12**.

---

### 👤 **User** — 2026-08-18 21:12:18

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
cat scripts/run_daily_hybrid_v12.sh && \
echo "==================== HYBRID MAIN ====================" && \
sed -n '180,430p' scripts/run_hybrid_v12.py
#!/usr/bin/env bash

set -euo pipefail

PROJECT="$HOME/projects/scene_fingerprint_mvp_v02"

INPUT="$PROJECT/data/input/daily"

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"

OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"

echo
echo "================================================================================"
echo "SCENE FINGERPRINT — DAILY HYBRID V12"
echo "================================================================================"
echo
echo "INPUT : $INPUT"
echo "OUTPUT: $OUTPUT"
echo

if [ ! -d "$INPUT" ]; then
    echo "ERROR: input directory does not exist:"
    echo "$INPUT"
    exit 1
fi

COUNT=$(find "$INPUT" -maxdepth 1 -type f \
    $ -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" $ \
    | wc -l)

echo "Images: $COUNT"
echo

if [ "$COUNT" -eq 0 ]; then
    echo "ERROR: no images found in $INPUT"
    exit 1
fi

mkdir -p "$OUTPUT"

/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
    --input "$INPUT" \
    --output "$OUTPUT" \
    --first-address 78 \
    --last-address 95

echo
echo "================================================================================"
echo "DAILY PIPELINE FINISHED"
echo "================================================================================"
echo
echo "Images : $COUNT"
echo "Output : $OUTPUT"
echo
==================== HYBRID MAIN ====================
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:12:19

Да, теперь картина ясная. И здесь видно **правильное место для `photo_id`**.

Сейчас pipeline такой:

```text
run_daily_hybrid_v12.sh
        │
        ▼
data/input/daily
        │
        ▼
run_hybrid_v12.py
        │
        ├── DINO
        ├── Hybrid v12
        │
        ▼
sort_results()
        │
        ▼
data/output/daily/<timestamp>/<address>/
```

### Что меняем

`run_daily_hybrid_v12.sh` пока можно оставить просто оболочкой. **Не надо привязывать сам Hybrid к конкретной папке.** У него уже есть `--input`.

А вот в `run_hybrid_v12.py` перед:

```python
recognition, recognition_time = run_recognition(
    input_dir,
    fingerprints,
)
```

нужно добавить этап:

```text
INPUT
  ↓
регистрация фотографий
  ↓
photo_id
  ↓
DINO
```

При этом **в сам алгоритм `hybrid_v12()` вообще не лезем**.

---

## Но есть важный нюанс

Сейчас DINO получает:

```python
str(input_dir)
```

и возвращает строки примерно с:

```python
row["file"]
```

Поэтому нам не нужно заставлять DINO физически переименовывать файлы в `PH_00000001.JPG`.

Это было бы плохо.

Лучше сделать mapping:

```text
PH_00000101 → /data/input/daily/IMG_001.JPG
PH_00000102 → /data/input/daily/IMG_002.JPG
```

DINO продолжает работать с реальным файлом:

```text
IMG_001.JPG
```

а после получения результата мы добавляем к его строке:

```python
row["photo_id"] = "PH_00000101"
```

Таким образом Hybrid остаётся абсолютно прежним.

---

## База должна создаваться ДО DINO

Например, пришли 3 фотографии:

```text
data/input/daily/
├── DSC_001.JPG
├── DSC_002.JPG
└── DSC_003.JPG
```

До запуска DINO:

```text
PH_00000101 → DSC_001.JPG
PH_00000102 → DSC_002.JPG
PH_00000103 → DSC_003.JPG
```

В PostgreSQL сразу появляется:

```text
photo_id       address   filename     path
PH_00000101    NULL      DSC_001.JPG  data/input/daily/DSC_001.JPG
PH_00000102    NULL      DSC_002.JPG  data/input/daily/DSC_002.JPG
PH_00000103    NULL      DSC_003.JPG  data/input/daily/DSC_003.JPG
```

`address` пока `NULL`.

---

## Потом DINO

Получаем:

```text
PH_00000101 → 85_v33
PH_00000102 → 78_v33
PH_00000103 → 85_v33
```

Hybrid может изменить решение:

```text
PH_00000102 → 78_v33
```

или:

```text
PH_00000102 → 79_v33
```

---

## Потом сортировка

И вот здесь нынешний `sort_results()` должен стать ответственным за физическое размещение.

Сейчас:

```python
destination_dir = output_dir / assigned_id
destination = destination_dir / source.name

shutil.copy2(
    source,
    destination,
)
```

Нужно будет получить:

```text
photo_id = PH_00000102
assigned_id = 78_v33
filename = DSC_002.JPG
```

и создать:

```text
data/output/daily/20260818_.../
└── 78_v33/
    └── DSC_002.JPG
```

После успешного копирования обновить БД:

```text
photo_id = PH_00000102
address  = 78_v33
path     = data/output/daily/.../78_v33/DSC_002.JPG
```

---

# А имя файла можно менять позже

Например пользователь в гриде увидел:

```text
PH_00000102
DSC_002.JPG
78_v33
```

и понял:

> это вообще-то Комарова13.

Тогда операция:

```text
78_v33/DSC_002.JPG
        ↓
78_v33/Комарова13_27.JPG
```

БД:

```text
photo_id = PH_00000102
address  = 78_v33
filename = Комарова13_27.JPG
path     = .../78_v33/Комарова13_27.JPG
```

Если одновременно исправили адрес:

```text
78_v33/DSC_002.JPG
        ↓
85_v33/Комарова13_27.JPG
```

`photo_id` всё равно:

```text
PH_00000102
```

---

## И Qwen

Вот здесь появляется большой плюс.

Qwen больше не должен ориентироваться на:

```text
85_v33/Комарова13_27.JPG
```

как на идентичность.

Он получает:

```text
PH_00000102
```

и результат относится именно к нему.

Например:

```text
photo_id = PH_00000102
qwen_status = ok
description = ...
objects_json = ...
colors_json = ...
```

Потом хоть десять раз меняй имя и папку — результат Qwen остаётся связанным с фотографией.

---

# И preview

Тоже **после сортировки**:

```text
DINO
 ↓
Hybrid
 ↓
copy/sort
 ↓
DB update
 ↓
preview
 ↓
GRID
```

То есть грид не увидит промежуточные фотографии из `input`.

Это полностью соответствует твоей мысли про чекбоксы адресов:

```text
☑ 78_v33
☐ 79_v33
☑ 85_v33
```

Грид показывает только те записи БД, у которых:

```text
address IN ('78_v33', '85_v33')
```

и только уже отсортированные фотографии.

---

### Поэтому сейчас я бы сделал только первый этап

**Не трогаем `hybrid_v12()`, не трогаем алгоритм DINO, не трогаем фильтры грида.**

Добавляем отдельную функцию примерно:

```python
register_input_photos(input_dir)
```

которая:

1. находит фотографии в переданном `--input`;
2. получает следующий `photo_id`;
3. создаёт записи в PostgreSQL;
4. сохраняет исходный `path` и `filename`;
5. возвращает mapping `path → photo_id`.

А затем `run_recognition()`/результаты DINO получают этот `photo_id`.

Но перед написанием кода надо посмотреть **оставшуюся часть `main()` и особенно конец `sort_results()`**, потому что там сейчас формируется итоговый JSON/отчёт и именно туда нужно аккуратно протянуть `photo_id`.

Дай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '400,620p' scripts/run_hybrid_v12.py
```

Тогда сделаем первый минимальный патч без изменения распознавания.

---

### 👤 **User** — 2026-08-18 21:13:46

запускать процесс присвоения id можно: - кнопкой, вручную, - автоматически в поределенное время, - постепенно прозванивая папку на наличие новых файлов

---

### 🤖 **Assistant** — 2026-08-18 21:13:47

Да. И это даже лучше: **присвоение `photo_id` сделать отдельным независимым этапом**, а не частью DINO/Hybrid.

### Получается 3 режима запуска

```text id="4o1fqs"
                INPUT / ВХОДНАЯ ПАПКА
                         │
                         ▼
                СКАНИРОВАНИЕ НОВЫХ ФАЙЛОВ
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
          КНОПКА       ТАЙМЕР      WATCHER
          вручную      по времени  постоянно
              │          │          │
              └──────────┼──────────┘
                         ▼
                  СОЗДАНИЕ photo_id
                         │
                         ▼
                    PostgreSQL
```

При этом **сам факт присвоения ID ещё не означает, что фото должно появиться в гриде**.

---

### Состояния фотографии

Я бы заложил примерно такую логику:

```text id="b0c49p"
photo_id       PH_00000123
source_path    data/input/daily/IMG_123.JPG

processing_status = NEW
address            = NULL
sorted_path        = NULL
```

После DINO:

```text id="z7w4h5"
processing_status = RECOGNIZED
address = 85_v33
```

После сортировки:

```text id="x6nd8a"
processing_status = SORTED
address = 85_v33
sorted_path = data/output/daily/.../85_v33/IMG_123.JPG
```

После preview:

```text id="r3c9fk"
processing_status = READY
```

И **только `READY` участвует в GRID**.

Это очень хорошо решает твою проблему с путаницей.

---

## 1. Кнопка

В техническом модуле:

```text id="u8yq9m"
[ СКАНИРОВАТЬ НОВЫЕ ФОТО ]
```

Нажал → программа смотрит входную папку → находит новые файлы → выдаёт им `photo_id`.

Например:

```text id="8m7c0d"
Найдено: 17 новых фото
Назначено ID: 17
Пропущено: 0
```

---

## 2. Автоматически по времени

Например:

```text id="2ofj9t"
каждые 5 минут
```

или:

```text id="c2w5j4"
08:00
12:00
16:00
20:00
```

Сканер работает независимо от DINO.

---

## 3. Постоянный watcher

Это ещё интереснее.

```text id="i6t4k8"
data/input/daily/
```

постоянно наблюдается:

```text
новый JPG
   ↓
обнаружен
   ↓
подождать окончания копирования
   ↓
photo_id
   ↓
DB
```

Например камера/другая программа копирует большой файл:

```text
IMG_123.JPG
```

watcher не должен сразу хватать его.

Можно проверять:

```text id="v4y6v0"
размер сейчас = 18.2 MB
через 2 сек = 18.2 MB
```

→ файл стабилен → регистрируем.

---

# И это позволяет сделать очередь

Вот здесь архитектура становится очень удобной:

```text id="t1n4o2"
NEW
 │
 ▼
ID_ASSIGNED
 │
 ▼
DINO_QUEUE
 │
 ▼
DINO_DONE
 │
 ▼
QWEN_QUEUE
 │
 ▼
SORTED
 │
 ▼
PREVIEW
 │
 ▼
READY
```

При этом DINO и Qwen могут работать **не синхронно**.

Например:

```text
PH_00000101 → DINO готов → сортировка
PH_00000102 → DINO работает
PH_00000103 → ждёт DINO
PH_00000104 → Qwen работает
PH_00000105 → готов
```

---

## И главное — грид

Грид смотрит не на входную папку.

Он смотрит БД:

```text id="x8r5p6"
WHERE processing_status = 'READY'
```

и применяет чекбоксы:

```text
AND address IN (...)
```

Поэтому новая фотография может уже иметь:

```text
PH_00000150
```

но пока она:

```text
NEW
```

**в гриде её нет.**

Она появится только когда полностью прошла нужный pipeline.

---

### Я бы ещё немного изменил название статуса

Не делать один огромный `processing_status`, а иметь понятные этапы:

```text id="2j1jzq"
photo_id
source_path
address
filename
sorted_path

dino_status
qwen_status
sort_status
preview_status
```

Тогда можно видеть:

```text id="w8lq5s"
PH_00000150
DINO:    done
QWEN:    running
SORT:    waiting
PREVIEW: waiting
```

Это потом идеально ляжет на **мониторинг технических процессов**, который у нас уже есть в интерфейсе.

И ещё важное: **ID-сканер должен быть идемпотентным** — хоть каждую секунду проверяй папку, уже зарегистрированной фотографии второй `photo_id` не получит. Для этого нужен уникальный ключ на исходный файл/его fingerprint.

Я бы следующим шагом спроектировал именно этот **Photo Ingestor** — маленький независимый модуль, который можно запускать кнопкой, по расписанию или как watcher.

---

### 👤 **User** — 2026-08-18 21:14:51

давай интегратор

---

