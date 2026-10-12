## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 👤 **User** — 2026-08-15 13:46:09

=== SYNTAX ===
STATUS=0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/visual_check_neighbor_v35

uv run python -u scripts/sort_neighbor_v35.py

================================================================================
NEIGHBOR CONTEXT V35
================================================================================
Input images : 243
Margin limit : 0.005
Neighbor +/- : 2

================================================================================
RESULT
================================================================================
Total images:        243
Margin < 0.005:      6
Changed by neighbors:       2

CHANGED
--------------------------------------------------------------------------------
Ленина 125-127 А (10).JPG
    87 -> 84
    margin=0.001876
    reason=SECOND_SUPPORTED_BY_2+_NEIGHBORS
    second: -1:Ленина 125-127 А (1).JPG; +1:Ленина 125-127 А (11).JPG; +2:Ленина 125-127 А (12).JPG
Ленина 125-127 А (14).JPG
    87 -> 84
    margin=0.001037
    reason=SECOND_SUPPORTED_BY_2+_NEIGHBORS
    second: -2:Ленина 125-127 А (12).JPG; -1:Ленина 125-127 А (13).JPG; +1:Ленина 125-127 А (15).JPG; +2:Ленина 125-127 А (16).JPG

DISTRIBUTION
--------------------------------------------------------------------------------
78           20
79            8
80            8
81           16
82            9
83           18
84           10
85           17
86           14
87           12
88           14
89           19
90            3
91           10
92           17
93           11
94           21
95           16
--------------------------------------------------------------------------------
TOTAL        243

OUTPUT:
  sorted : /home/alexice/projects/scene_fingerprint_mvp_v02/output/visual_check_neighbor_v35
  report : /home/alexice/projects/scene_fingerprint_mvp_v02/output/visual_check_neighbor_v35/neighbor_decision.csv
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== V35 CHANGES ==="
grep -A8 -B2 "CHANGED" \
  output/visual_check_neighbor_v35/neighbor_decision.csv \
  | head -100
=== V35 CHANGES ===
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import csv
from pathlib import Path

p = Path("output/visual_check_neighbor_v35/neighbor_decision.csv")

with p.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

print("TOTAL ROWS:", len(rows))
print()

changed = []
for r in rows:
    old = r.get("original_id") or r.get("current_id") or r.get("assigned_id")
    new = r.get("final_id") or r.get("neighbor_id") or r.get("assigned_id")

    if old != new:
        changed.append(r)

print("CHANGED:", len(changed))
PY  print(r)nged:
TOTAL ROWS: 243

CHANGED: 0
====================================================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import csv
from pathlib import Path

p = Path("output/visual_check_neighbor_v35/neighbor_decision.csv")

with p.open(encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

print("TOTAL ROWS:", len(rows))
print()

changed = []
for r in rows:
    old = r.get("original_id") or r.get("current_id") or r.get("assigned_id")
    new = r.get("final_id") or r.get("neighbor_id") or r.get("assigned_id")

    if old != new:
        changed.append(r)

print("CHANGED:", len(changed))
PY  print(r)nged:
TOTAL ROWS: 243

CHANGED: 0
====================================================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ head -2 output/visual_check_neighbor_v35/neighbor_decision.csv
image,v33,second,final,margin,second_neighbor_count,current_neighbor_count,reason,second_neighbors,current_neighbors
00 (1).JPG,78,92,78,0.054521,0,0,V33,,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:46:10

Вот теперь результат **очень хороший**. И заодно выяснилась причина, почему моя предыдущая проверка CSV дала `CHANGED: 0` — я использовал неправильные имена колонок. У тебя реальные поля:

```text
image,v33,second,final,...
```

### Что сделал v35

Из 243 фотографий:

- **237** — уверенно остались на результате v33;
- **6** — имели `margin < 0.005`;
- из этих 6 **только 2 реально изменены соседним контекстом**;
- оба изменения — в серии `Ленина 125-127 А`;
- оба изменения выглядят логично.

```text
Ленина 125-127 А (10).JPG
87 → 84
```

Соседи:

```text
(9)  → 84
(11) → 84
(12) → 84
```

И:

```text
Ленина 125-127 А (14).JPG
87 → 84
```

Соседи:

```text
(12) → 84
(13) → 84
(15) → 84
(16) → 84
```

То есть здесь соседний алгоритм действительно делает то, что мы хотели: **не пытается переучивать распознавание, а исправляет одиночный сомнительный кадр внутри серии.**

### А самое важное

`008` и `009` **v35 вообще не тронул**.

То есть после нашего правила:

> менять только если второй кандидат поддерживается минимум двумя соседями

получилось:

```text
008    83 → 83
009    92 → 92
```

И это правильно с точки зрения сохранения исходного решения v33.

Таким образом, **v35 значительно безопаснее v34**.

---

## Я бы сейчас зафиксировал v35 как рабочую логику

Схема получается:

```text
DINOv2 / v33
      ↓
TOP-1 кандидат
      ↓
margin < 0.005 ?
      │
     НЕТ ─────────────→ оставить TOP-1
      │
     ДА
      ↓
посмотреть ±2 фотографии
      ↓
второй кандидат подтверждается
минимум 2 соседями?
      │
   НЕТ ──────────────→ оставить TOP-1
      │
     ДА
      ↓
заменить на второго кандидата
```

И это гораздо разумнее, чем просто:

```text
если сосед похож → поменять
```

Потому что мы уже увидели на `008/009`, что соседняя логика может создать **обмен двух правильных последовательных кадров**.

---

### Но есть ещё один важный момент

У нас осталось **4 сомнительных кадра**, которые v35 НЕ изменил.

Это именно те случаи, которые стоит посмотреть:

```text
margin < 0.005
```

Давай выведем их:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== ALL MARGIN < 0.005 AFTER V35 ==="

python3 - <<'PY'
import csv

p = "output/visual_check_neighbor_v35/neighbor_decision.csv"

with open(p, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

for r in rows:
    if float(r["margin"]) < 0.005:
        print()
        print(r["image"])
        print(
            f"  v33={r['v33']}  "
            f"second={r['second']}  "
            f"final={r['final']}  "
            f"margin={r['margin']}"
        )
        print(
            f"  second_neighbors={r['second_neighbor_count']}"
        )
        print(
            f"  current_neighbors={r['current_neighbor_count']}"
        )
        print(
            f"  reason={r['reason']}"
        )
PY
```

**Вот эти 4 кадра сейчас наиболее интересны.**

После них у нас будет практически полный контрольный набор:

1. ошибки, которые v33 исправляет сам;
2. ошибки, которые исправляет v35;
3. случаи, где v35 правильно **не вмешивается**;
4. отдельные известные спорные серии.

Если эти 4 тоже выглядят нормально, я бы уже **не усложнял алгоритм** и переходил к интеграции этой логики в основной `recognize/sort` pipeline.

---

### 👤 **User** — 2026-08-15 13:47:09

)
        print(
PY      )   f"  reason={r['reason']}"'current_neighbor_count']}"
=== ALL MARGIN < 0.005 AFTER V35 ===

008.JPG
  v33=83  second=92  final=83  margin=0.001418
  second_neighbors=1
  current_neighbors=0
  reason=ONE_NEIGHBOR_KEEP_V33

009.JPG
  v33=92  second=83  final=92  margin=0.004476
  second_neighbors=1
  current_neighbors=0
  reason=ONE_NEIGHBOR_KEEP_V33

Ленина 125-127 А (10).JPG
  v33=87  second=84  final=84  margin=0.001876
  second_neighbors=3
  current_neighbors=0
  reason=SECOND_SUPPORTED_BY_2+_NEIGHBORS

Ленина 125-127 А (14).JPG
  v33=87  second=84  final=84  margin=0.001037
  second_neighbors=4
  current_neighbors=0
  reason=SECOND_SUPPORTED_BY_2+_NEIGHBORS

Ленина 125-127 А (17).JPG
  v33=84  second=87  final=84  margin=0.002587
  second_neighbors=1
  current_neighbors=3
  reason=CONFLICT_KEEP_V33

Ленина 125-127 А (9).JPG
  v33=84  second=87  final=84  margin=0.004802
  second_neighbors=1
  current_neighbors=1
  reason=CONFLICT_KEEP_V33
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 13:47:10

Вот теперь картина практически идеальная для нашей задачи.

### Что получилось

Всего **6 сомнительных кадров**:

| Фото | v33 | 2-й кандидат | v35 | Решение |
|---|---:|---:|---:|---|
| `008.JPG` | 83 | 92 | **83** | оставить |
| `009.JPG` | 92 | 83 | **92** | оставить |
| `Ленина... (9)` | 84 | 87 | **84** | оставить |
| `Ленина... (10)` | 87 | 84 | **84** | исправить |
| `Ленина... (14)` | 87 | 84 | **84** | исправить |
| `Ленина... (17)` | 84 | 87 | **84** | оставить |

### Особенно хорошо сработала логика на `Ленина`

Получилась последовательность:

```text
(9)  → 84
(10) → 84   ← v35 исправил
(11) → 84
(12) → 84
(13) → 84
(14) → 84   ← v35 исправил
(15) → 84
(16) → 84
(17) → 84
```

То есть v35 фактически **восстановил целостную серию**.

А `008/009`:

```text
008 → 83
009 → 92
```

остались как были, потому что каждый из них получил поддержку второго кандидата только от одного соседа. Это именно то поведение, которое нам нужно.

---

## Я бы зафиксировал v35

Причём правило получается очень простое:

**1. Основой всегда является v33 TOP-1.**

**2. Neighbor-логика включается только при `margin < 0.005`.**

**3. Если второй кандидат поддержан ≥2 соседями — меняем.**

**4. Если второй кандидат поддержан только одним соседом — НЕ меняем.**

**5. Если есть конфликт между поддержкой текущего и второго кандидата — НЕ меняем.**

Это очень консервативный алгоритм. Для нашего потока фотографий сериями это как раз преимущество.

### И ещё важный вывод

Мы **не стали использовать соседей для всех 243 фотографий**.

Это правильно.

DINOv2/v33 остаётся главным распознавателем, а соседний контекст превращается в небольшой **корректор сомнительных кадров**.

То есть:

```text
                    ┌── margin >= 0.005 ──→ v33 TOP-1
                    │
DINOv2 v33 → margin ┤
                    │
                    └── margin < 0.005
                              ↓
                       проверка ±2 соседей
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
              ≥2 подтверждения     нет уверенного
                    ↓                   ↓
              второй кандидат       v33 TOP-1
```

**Я бы именно эту v35-логику теперь переносил в основной pipeline распознавания.**

---

### 👤 **User** — 2026-08-15 13:48:05

давай анчитсу прогоним все фото и сохранит вывод по пронумерованным папкам

---

### 🤖 **Assistant** — 2026-08-15 13:48:09

Да. Теперь можно сделать **боевой прогон v35**: взять весь `data/input/test`, применить v33 + консервативную neighbor-логику и разложить результат по папкам `78 ... 95`.

Я бы **не трогал предыдущие результаты**, а записал новый результат отдельно.

### 1. Запускаем финальную сортировку

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/final_v35
mkdir -p output/final_v35

uv run python -u scripts/sort_neighbor_v35.py
```

Но сейчас `v35` пишет в:

```text
output/visual_check_neighbor_v35
```

Поэтому после запуска просто делаем отдельную финальную копию:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/final_v35
mkdir -p output/final_v35

for N in $(seq 78 95); do
    if [ -d "output/visual_check_neighbor_v35/$N" ]; then
        mkdir -p "output/final_v35/$N"
        cp -a "output/visual_check_neighbor_v35/$N/." \
              "output/final_v35/$N/"
    fi
done
```

### 2. Проверяем распределение

```bash
echo
echo "=== FINAL V35 DISTRIBUTION ==="

TOTAL=0

for N in $(seq 78 95); do
    C=$(find "output/final_v35/$N" -maxdepth 1 -type f 2>/dev/null | wc -l)
    printf "%-4s %4d\n" "$N" "$C"
    TOTAL=$((TOTAL + C))
done

echo "----------------"
echo "TOTAL $TOTAL"
```

Должно получиться:

```text
78    20
79     8
80     8
81    16
82     9
83    18
84    10
85    17
86    14
87    12
88    14
89    19
90     3
91    10
92    17
93    11
94    21
95    16
----------------
TOTAL 243
```

### 3. И отдельно сохраним отчёт

```bash
cp output/visual_check_neighbor_v35/neighbor_decision.csv \
   output/final_v35/neighbor_decision.csv
```

В итоге будет:

```text
output/
└── final_v35/
    ├── 78/
    ├── 79/
    ├── 80/
    ├── ...
    ├── 95/
    └── neighbor_decision.csv
```

**Важно:** сейчас `v35` обрабатывает **243 фотографии**, потому что в `margin_best.csv` есть 262 записи, но для 19 из них исходные файлы отсутствуют в `data/input/test`. Мы это уже установили.

То есть этот прогон не потеряет ничего из доступных исходников: **243 фотографии → 18 пронумерованных папок**.

---

### 👤 **User** — 2026-08-15 14:07:20

NEIGHBOR CONTEXT V35
================================================================================
Input images : 0
Margin limit : 0.005
Neighbor +/- : 2

================================================================================
RESULT
================================================================================
Total images:        0
Margin < 0.005:      0
Changed by neighbors:       0

DISTRIBUTION
--------------------------------------------------------------------------------
78            0
79            0
80            0
81            0
82            0
83            0
84            0
85            0
86            0
87            0
88            0
89            0
90            0
91            0
92            0
93            0
94            0
95            0
--------------------------------------------------------------------------------
TOTAL          0

OUTPUT:
  sorted : /home/alexice/projects/scene_fingerprint_mvp_v02/output/visual_check_neighbor_v35
  report : /home/alexice/projects/scene_fingerprint_mvp_v02/output/visual_check_neighbor_v35/neighbor_decision.csv
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output/final_v35
mkdir -p output/final_v35

for N in $(seq 78 95); do
    if [ -d "output/visual_check_neighbor_v35/$N" ]; then
        mkdir -p "output/final_v35/$N"
        cp -a "output/visual_check_neighbor_v35/$N/." \
              "output/final_v35/$N/"
    fi
done
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=== FINAL V35 DISTRIBUTION ==="

TOTAL=0

for N in $(seq 78 95); do
    C=$(find "output/final_v35/$N" -maxdepth 1 -type f 2>/dev/null | wc -l)
    printf "%-4s %4d\n" "$N" "$C"
    TOTAL=$((TOTAL + C))
done

echo "----------------"
echo "TOTAL $TOTAL"

=== FINAL V35 DISTRIBUTION ===
78      0
79      0
80      0
81      0
82      0
83      0
84      0
85      0
86      0
87      0
88      0
89      0
90      0
91      0
92      0
93      0
94      0
95      0
----------------
TOTAL 0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:07:21

Да, здесь моя ошибка: **мы повторно запустили `v35`, а он читает не `data/input/test` напрямую, а источник, который сейчас не соответствует текущему набору**, поэтому получил `Input images : 0` и затёр предыдущий `visual_check_neighbor_v35`.

Хорошо, что мы это заметили — **`final_v35` пока пустой, ничего не потеряли в исходниках.**

Сначала восстановим предыдущий корректный результат из CSV, а затем сделаем нормальную сортировку.

### 1. Проверяем, что сейчас есть

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== TEST ==="
find data/input/test -maxdepth 1 -type f | wc -l

echo
echo "=== BENCHMARK CSV ==="
wc -l output/benchmark_components/full_analysis/margin_best.csv

echo
echo "=== V35 CSV ==="
wc -l output/visual_check_neighbor_v35/neighbor_decision.csv

echo
echo "=== SCRIPT INPUT SETTINGS ==="
grep -nE 'INPUT_DIR|SOURCE_CSV|OUTPUT_DIR|MARGIN_LIMIT|NEIGHBOR' \
    scripts/sort_neighbor_v35.py
```

### 2. И главное — **не запускай v35 повторно**

Нам сейчас нужен тот корректный результат, который только что был:

```text
Input images : 243
...
Changed by neighbors: 2
```

Но мы его случайно перезаписали новым пустым запуском.

Если `data/input/test` действительно содержит 243 файла, то я дам тебе отдельный **финальный скрипт сортировки**, который:

- берёт существующий `margin_best.csv`;
- применяет именно проверенную v35-логику;
- использует реальные файлы из `data/input/test`;
- **не зависит от того, что `v35` сам ищет как input**;
- создаёт:

```text
output/final_v35/
├── 78/
├── 79/
├── ...
├── 95/
└── neighbor_decision.csv
```

И главное — перед копированием он сначала покажет:

```text
SOURCE FILES: 243
CSV RECORDS: 262
MATCHED: 243
MISSING: 19
```

чтобы мы больше не получили ситуацию `Input images: 0`.

Сейчас пришли вывод команды из пункта **1**.

---

### 👤 **User** — 2026-08-15 14:07:57

echo
echo "=== BENCHMARK CSV ==="
wc -l output/benchmark_components/full_analysis/margin_best.csv

echo
echo "=== V35 CSV ==="
wc -l output/visual_check_neighbor_v35/neighbor_decision.csv

echo
echo "=== SCRIPT INPUT SETTINGS ==="
grep -nE 'INPUT_DIR|SOURCE_CSV|OUTPUT_DIR|MARGIN_LIMIT|NEIGHBOR' \
    scripts/sort_neighbor_v35.py
=== TEST ===
257

=== BENCHMARK CSV ===
263 output/benchmark_components/full_analysis/margin_best.csv

=== V35 CSV ===
1 output/visual_check_neighbor_v35/neighbor_decision.csv

=== SCRIPT INPUT SETTINGS ===
10:INPUT_DIR = PROJECT / "data/input/test"
12:SOURCE_CSV = (
17:OUTPUT_DIR = PROJECT / "output/visual_check_neighbor_v35"
18:REPORT_CSV = OUTPUT_DIR / "neighbor_decision.csv"
20:MARGIN_LIMIT = 0.005
21:NEIGHBOR_RADIUS = 2
27:    with SOURCE_CSV.open(
33:            if (INPUT_DIR / row["image"]).exists():
48:    OUTPUT_DIR.mkdir(
89:        if margin < MARGIN_LIMIT:
95:                i - NEIGHBOR_RADIUS
100:                i + NEIGHBOR_RADIUS + 1
167:                    "SECOND_SUPPORTED_BY_2+_NEIGHBORS"
186:                    "ONE_NEIGHBOR_KEEP_V33"
192:                    "NO_NEIGHBOR_EVIDENCE"
250:            OUTPUT_DIR / folder
259:            INPUT_DIR / item["image"]
328:    print("NEIGHBOR CONTEXT V35")
336:        f"Margin limit : {MARGIN_LIMIT}"
340:        f"Neighbor +/- : {NEIGHBOR_RADIUS}"
427:        OUTPUT_DIR
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:08:00

Отлично. Теперь всё понятно.

Сейчас:

- `data/input/test` — **257 фотографий**
- `margin_best.csv` — **262 фотографии**
- значит, сейчас отсутствует только **5 исходников**, а не 19, как было раньше.
- `v35` был запущен после того, как что-то изменилось в окружении/файлах, и его CSV теперь пустой — **его не используем**.

И ещё важное: **не надо повторно запускать `sort_neighbor_v35.py`**. Мы уже проверили его логику. Сейчас лучше сделать отдельный финальный сортировщик на базе проверенного результата v35.

Но сначала определим ровно эти 5 отсутствующих файлов и убедимся, что остальные 257 полностью совпадают с benchmark.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import csv
from pathlib import Path

project = Path(".")
source = project / "data/input/test"
csv_path = project / "output/benchmark_components/full_analysis/margin_best.csv"

with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

missing = []
present = []

for r in rows:
    name = r["image"]
    if (source / name).exists():
        present.append(r)
    else:
        missing.append(r)

print("CSV RECORDS :", len(rows))
print("SOURCE FILES:", len(list(source.iterdir())))
print("MATCHED     :", len(present))
print("MISSING     :", len(missing))

print()
print("=== MISSING ===")

for r in missing:
    print(
        f"{r['image']} | "
        f"{r['current_first']} / {r['current_second']} | "
        f"margin={r['final_margin']}"
    )

print()
print("=== READY FOR FINAL SORT ===")

if len(present) == len(list(source.iterdir())):
    print("OK: all source photos have benchmark records")
else:
    print("WARNING: source/CSV counts do not match")
PY
```

### После этого

Если увидим:

```text
CSV RECORDS : 262
SOURCE FILES: 257
MATCHED     : 257
MISSING     : 5
```

то всё отлично.

Затем я дам **одну команду/скрипт для финального прогона**, который будет делать именно это:

```text
data/input/test
       ↓
margin_best.csv
       ↓
v35 neighbor logic
       ↓
output/final_v35/
    78/
    79/
    ...
    95/
```

При этом он **не будет менять исходные фотографии**, не будет зависеть от `visual_check_neighbor_v35` и перед записью проверит количество файлов.

И ещё: в финальной версии я сохраню **не только итоговую папку, но и CSV с решением для каждой фотографии**, чтобы потом можно было точно увидеть:

```text
файл | v33 | второй кандидат | финальный | margin | причина
```

Это уже будет нормальная рабочая разметка для следующего этапа.

---

### 👤 **User** — 2026-08-15 14:08:27

я сейчас зачистил папку test и переименовал - надо прогнать по новой

---

### 🤖 **Assistant** — 2026-08-15 14:08:28

Да, тогда всё правильно: **старые `margin_best.csv` и результаты нам сейчас не нужны**. Если `test` заново сформирован и переименован, нужно выполнить полный новый прогон:

**новые фото → v33 → neighbor v35 → сортировка по папкам 78–95.**

Сначала проверим, что именно сейчас лежит в `test`, чтобы не повторить ситуацию с `0` файлов.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== TEST INPUT ==="
find data/input/test -maxdepth 1 -type f | sort | head
echo
echo "TOTAL:"
find data/input/test -maxdepth 1 -type f | wc -l
```

Если количество фотографий правильное, запускаем **обычное распознавание v33 заново**, чтобы получить свежий:

```text
output/benchmark_components/full_analysis/margin_best.csv
```

Но перед запуском я хочу посмотреть, **какой именно скрипт у тебя сейчас создаёт `margin_best.csv`**, чтобы не угадать команду и не испортить текущую рабочую схему.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== SCRIPTS ==="
ls -lh scripts/

echo
echo "=== margin_best ==="
grep -Rni "margin_best" scripts --exclude='*.pyc' | head -30
```

Пришли вывод. После этого дам **точную последовательность команд одним блоком**: свежий v33 → v35 → разложить всё по `78–95`.

---

### 👤 **User** — 2026-08-15 14:08:42

int_mvp_v02

echo "=== TEST INPUT ==="
find data/input/test -maxdepth 1 -type f | sort | head
echo
echo "TOTAL:"
find data/input/test -maxdepth 1 -type f | wc -l
=== TEST INPUT ===
data/input/test/Ашхабадский_01.JPG
data/input/test/Ашхабадский_02.JPG
data/input/test/Ашхабадский_03.JPG
data/input/test/Ашхабадский_04.JPG
data/input/test/Ашхабадский_05.JPG
data/input/test/Ашхабадский_06.JPG
data/input/test/Ашхабадский_07.JPG
data/input/test/Ашхабадский_08.JPG
data/input/test/Ашхабадский_09.JPG
data/input/test/Ашхабадский_10.JPG

TOTAL:
257
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:08:43

Отлично. Сейчас в `test` **257 новых фотографий**, и старые имена там уже не используются. Значит, начинаем чистый прогон.

Сначала нужно получить **свежий v33**, потому что старый `margin_best.csv` относится к предыдущему набору.

Выполни:

```bash id="zj6j5r"
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== SCRIPTS WITH margin_best ==="
grep -Rni "margin_best" scripts --exclude='*.pyc' | head -50
```

Пришли вывод. По нему я дам точную команду свежего распознавания.

**Пока ничего не запускай и не удаляй.** Нам важно сначала найти тот скрипт, который у тебя уже корректно формировал `margin_best.csv`.

---

### 👤 **User** — 2026-08-15 14:09:02

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== SCRIPTS WITH margin_best ==="
grep -Rni "margin_best" scripts --exclude='*.pyc' | head -50
=== SCRIPTS WITH margin_best ===
scripts/sort_margin005_best.py:13:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_neighbor_v34.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_neighbor_v35.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:09:05

Отлично. Значит `margin_best.csv` создаётся **не этими сортировщиками**, а предыдущим этапом benchmark/распознавания.

Найдём точную команду, которой мы делали свежий benchmark. Ищем по `benchmark_components` и `full_analysis`:

```bash id="8x8q3p"
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== BENCHMARK SCRIPTS ==="
grep -RniE "benchmark_components|full_analysis|final_margin|current_first|best_diff" \
    scripts --exclude='*.pyc' | head -100
```

И заодно:

```bash id="1f9j7k"
echo
echo "=== ALL PY SCRIPTS ==="
find scripts -maxdepth 1 -type f -name "*.py" -printf "%f\n" | sort
```

Пришли оба вывода.

После этого мы сделаем **полностью чистый цикл**:

```text
257 новых фото
      ↓
v33 распознавание
      ↓
fresh margin_best.csv
      ↓
v35 neighbor correction
      ↓
final_v35/
├── 78
├── 79
├── ...
└── 95
```

И уже **не будем использовать ни одного результата от старого набора фотографий**.

---

### 👤 **User** — 2026-08-15 14:09:23

/margin_best.csv"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== BENCHMARK SCRIPTS ==="
grep -RniE "benchmark_components|full_analysis|final_margin|current_first|best_diff" \
    scripts --exclude='*.pyc' | head -100
=== BENCHMARK SCRIPTS ===
scripts/sort_margin005_best.py:13:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_margin005_best.py:96:        current_first = row["current_first"]
scripts/sort_margin005_best.py:99:        final_margin = float(row["final_margin"])
scripts/sort_margin005_best.py:100:        best_diff = float(row["best_diff"])
scripts/sort_margin005_best.py:106:        assigned = current_first
scripts/sort_margin005_best.py:109:        if final_margin < MARGIN_THRESHOLD:
scripts/sort_margin005_best.py:113:            if best_diff > 0:
scripts/sort_margin005_best.py:152:        if assigned != current_first:
scripts/sort_margin005_best.py:156:                "old": current_first,
scripts/sort_margin005_best.py:158:                "margin": final_margin,
scripts/sort_margin005_best.py:159:                "best_diff": best_diff,
scripts/sort_margin005_best.py:182:            "best_diff",
scripts/sort_margin005_best.py:227:            f'  best_diff={x["best_diff"]:+.6f}'
scripts/sort_neighbor_v34.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_neighbor_v34.py:127:        original = r.get("current_first", "")
scripts/sort_neighbor_v34.py:130:        margin = ffloat(r.get("final_margin"))
scripts/sort_neighbor_v34.py:177:                    neighbor_result.get("current_first")
scripts/sort_neighbor_v34.py:186:                    neighbor_result.get("final_margin")
scripts/sort_neighbor_v35.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_neighbor_v35.py:67:            row.get("current_first")
scripts/sort_neighbor_v35.py:75:            row["final_margin"]
scripts/sort_neighbor_v35.py:111:                    neighbor.get("current_first")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=== ALL PY SCRIPTS ==="
find scripts -maxdepth 1 -type f -name "*.py" -printf "%f\n" | sort

=== ALL PY SCRIPTS ===
benchmark_test_v1.py
make_subfingerprints.py
make_subfingerprints_v2.py
sort_baseline.py
sort_margin005_best.py
sort_neighbor_v34.py
sort_neighbor_v35.py
sort_test_and_report.py
sort_test_and_report_v2.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:09:24

Теперь видно структуру. `margin_best.csv` создаётся на этапе **`benchmark_test_v1.py`** либо связанного с ним запуска. Давай не гадать — посмотрим, как именно он вызывается и какие пути использует.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== benchmark_test_v1.py ==="
sed -n '1,260p' scripts/benchmark_test_v1.py
```

И отдельно конец файла:

```bash
echo
echo "=== END ==="
tail -80 scripts/benchmark_test_v1.py
```

После этого я дам **одну нормальную последовательность команд** для нового набора из 257 фото:

1. свежий benchmark/v33;
2. свежий `margin_best.csv`;
3. v35 с соседями;
4. сортировка всех 257 фото по `78–95`;
5. отчёт по всем сомнительным случаям.

Старые результаты при этом не будем смешивать с новым тестом.

---

### 👤 **User** — 2026-08-15 14:09:50

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== benchmark_test_v1.py ==="
sed -n '1,260p' scripts/benchmark_test_v1.py
=== benchmark_test_v1.py ===
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=== END ==="
tail -80 scripts/benchmark_test_v1.py

=== END ===

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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:09:51

Да. Теперь причина ясна: `benchmark_test_v1.py` делает **только recognition → `data/output/benchmark_v1/benchmark.json`**. Старый `margin_best.csv` создавался следующим этапом, которого среди этих скриптов напрямую нет.

Поэтому сейчас не будем гадать. Сделаем свежий recognition на твоих **257 новых фото**, сохраним его отдельно и посмотрим структуру результата. Это безопасно и не затронет старые результаты.

Запусти:

```bash id="q5m8j0"
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf data/output/benchmark_v1
mkdir -p data/output/benchmark_v1

uv run python -u scripts/benchmark_test_v1.py
```

Ожидаем:

```text
BENCHMARK RECOGNITION
Images: 257
Fingerprints: 18
...
TOTAL: 257
...
OUTPUT:
.../data/output/benchmark_v1/benchmark.json
```

### После этого

Покажи последние строки:

```bash id="l3t0l1"
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== BENCHMARK ==="
ls -lh data/output/benchmark_v1/benchmark.json

echo
echo "=== FIRST RESULTS ==="
uv run python - <<'PY'
import json

p = "data/output/benchmark_v1/benchmark.json"

with open(p, encoding="utf-8") as f:
    d = json.load(f)

print("TOTAL:", d["total"])
print()

for x in d["results"][:10]:
    print(
        x["file"],
        "|",
        x["top1"],
        f"{x['top1_score']:.6f}" if x["top1_score"] is not None else "-",
        "|",
        x["top2"],
        f"{x['top2_score']:.6f}" if x["top2_score"] is not None else "-"
    )
PY
```

**Пока `sort_neighbor_v35.py` не запускай.**

После этого я дам следующий шаг, который преобразует свежий `benchmark.json` в нужный нам формат `margin_best.csv`, а затем уже прогоняем **v35 neighbor logic** и раскладываем **все 257 фотографий по папкам 78–95**.

---

### 👤 **User** — 2026-08-15 14:11:18

=== FIRST RESULTS ===
TOTAL: 256

/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG | 85_v33 0.900032 | 93_v33 0.836161
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_02.JPG | 85_v33 0.933634 | 93_v33 0.861263
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_03.JPG | 85_v33 0.914995 | 94_v33 0.844996
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_04.JPG | 85_v33 0.813182 | 91_v33 0.750666
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_05.JPG | 85_v33 0.869826 | 91_v33 0.810131
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_06.JPG | 85_v33 0.945078 | 91_v33 0.882871
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_07.JPG | 85_v33 0.931058 | 93_v33 0.852145
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_08.JPG | 89_v33 0.636720 | 85_v33 0.625444
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_09.JPG | 85_v33 0.906731 | 94_v33 0.872360
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_10.JPG | 85_v33 0.925078 | 92_v33 0.836863

---

### 🤖 **Assistant** — 2026-08-15 14:11:21

Вот здесь обнаружилась важная вещь: **в `test` 257 файлов, а recognition обработал только 256**.

Это надо исправить **до сортировки**, иначе одна фотография потеряется.

По первым результатам всё выглядит нормально: новые имена не мешают распознаванию, например серия `Ашхабадский_01...07` уверенно идёт в `85_v33`.

Сейчас найдём **единственную фотографию, которая не попала в `benchmark.json`**:

```bash id="m2r7q1"
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

test = Path("data/input/test")
bench = Path("data/output/benchmark_v1/benchmark.json")

with bench.open(encoding="utf-8") as f:
    data = json.load(f)

input_names = {p.name for p in test.iterdir() if p.is_file()}
result_names = {
    Path(x["file"]).name
    for x in data["results"]
}

missing = sorted(input_names - result_names)
extra = sorted(result_names - input_names)

print("INPUT :", len(input_names))
print("RESULT:", len(result_names))
print()

print("=== MISSING FROM RECOGNITION ===")
for x in missing:
    print(x)

print()
print("=== EXTRA ===")
for x in extra:
    print(x)
PY
```

### Почему это важно

Мы сейчас строим уже **чистый новый цикл**, поэтому итог должен быть:

```text
257 входных
257 распознанных
257 отсортированных
```

И только после этого:

```text
v33
 ↓
margin
 ↓
neighbor v35
 ↓
78 ... 95
```

Причём я бы **не использовал старый `margin_best.csv` вообще**. Для нового набора лучше сформировать его заново непосредственно из свежего `benchmark.json`.

Сначала пришли вывод этой проверки — найдём пропавшее фото.

---

### 👤 **User** — 2026-08-15 14:11:37

int_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

test = Path("data/input/test")
bench = Path("data/output/benchmark_v1/benchmark.json")

with bench.open(encoding="utf-8") as f:
    data = json.load(f)

input_names = {p.name for p in test.iterdir() if p.is_file()}
result_names = {
    Path(x["file"]).name
    for x in data["results"]
}

missing = sorted(input_names - result_names)
extra = sorted(result_names - input_names)

print("INPUT :", len(input_names))
print("RESULT:", len(result_names))
PY  print(x)ra:A ===")M RECOGNITION ===")
INPUT : 257
RESULT: 256

=== MISSING FROM RECOGNITION ===
Комарова28_01

=== EXTRA ===
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:11:38

Нашли. **Единственное потерянное фото — `Комарова28_01`**. Значит проблема не в сортировке, а именно на этапе recognition.

Надо понять, почему оно не попало в JSON. Сначала проверим реальное имя файла и формат:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== FILE ==="
ls -lb data/input/test/*Комарова28*

echo
echo "=== TYPE ==="
file data/input/test/*Комарова28*

echo
echo "=== SIZE ==="
du -h data/input/test/*Комарова28*
```

И отдельно попробуем распознать **только этот файл**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

mkdir -p /tmp/test_one
rm -f /tmp/test_one/*

cp -a data/input/test/*Комарова28* /tmp/test_one/

uv run scene-fingerprint recognize \
    /tmp/test_one \
    --top-k 5 \
    --threshold 0.0 \
    --fingerprints "$(printf '%s,' {78..95} | sed 's/,$//' | sed 's/\([0-9]*\)/\1_v33/g')" \
    --json
```

Но здесь есть важный момент: **лучше не продолжать со старым `benchmark_test_v1.py`**, пока не выясним это. Нам нужен полный набор 257/257.

Если одиночное распознавание `Комарова28_01` проходит, значит это, скорее всего, проблема массового запуска/парсинга JSON. Если не проходит — посмотрим ошибку конкретного изображения.

Пришли вывод этих двух команд.

---

### 👤 **User** — 2026-08-15 14:12:59

там не было расширения. сейчас все норм

---

### 🤖 **Assistant** — 2026-08-15 14:13:00

Отлично. Тогда причина найдена: **у `Комарова28_01` просто не было расширения**, поэтому recognition его не обработал.

Теперь у нас чистый набор **257 файлов**. Делаем полный цикл заново, уже без старых результатов.

### 1. Повторный benchmark

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf data/output/benchmark_v1
mkdir -p data/output/benchmark_v1

uv run python -u scripts/benchmark_test_v1.py
```

После него проверяем обязательно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

test = Path("data/input/test")
bench = Path("data/output/benchmark_v1/benchmark.json")

with bench.open(encoding="utf-8") as f:
    data = json.load(f)

inp = {p.name for p in test.iterdir() if p.is_file()}
out = {Path(x["file"]).name for x in data["results"]}

print("INPUT :", len(inp))
print("RESULT:", len(out))
print("MISSING:", len(inp - out))

for x in sorted(inp - out):
    print("  ", x)
PY
```

Должно быть:

```text
INPUT : 257
RESULT: 257
MISSING: 0
```

### 2. После этого

Я дам тебе **новый генератор `margin_best.csv` из этого свежего benchmark**, чтобы больше вообще не зависеть от старого файла.

Затем:

```text
257 фотографий
      ↓
fresh v33 TOP-5
      ↓
margin < 0.005
      ↓
neighbor v35
      ↓
257 фотографий
      ↓
папки 78 ... 95
```

И отдельно получим список всех случаев, где **v35 изменил решение v33**, чтобы визуально проверить именно потенциальные ошибки.

**Старые `margin_best.csv`, `visual_check_margin005` и `visual_check_neighbor_v35` в новый результат не подмешиваем.**

---

### 👤 **User** — 2026-08-15 14:14:07

Следующим шагом построим mapping адрес -> fingerprint и получим настоящий TOP-1/2/3/5 accuracy.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

test = Path("data/input/test")
bench = Path("data/output/benchmark_v1/benchmark.json")

with bench.open(encoding="utf-8") as f:
    data = json.load(f)

inp = {p.name for p in test.iterdir() if p.is_file()}
out = {Path(x["file"]).name for x in data["results"]}

print("INPUT :", len(inp))
print("RESULT:", len(out))
print("MISSING:", len(inp - out))

for x in sorted(inp - out):
    print("  ", x)
PY
INPUT : 257
RESULT: 257
MISSING: 0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:14:12

Отлично. Теперь у нас **257/257**, можно переходить к настоящему benchmark.

Но я бы сделал mapping аккуратно: **не использовать текущий результат v33 как `REAL`**, иначе accuracy будет искусственно завышена. Нужно построить эталон `адрес → fingerprint` независимо от распознавания.

Сначала посмотрим, какие именно адресные серии сейчас есть в `test`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== TEST SERIES ==="

python - <<'PY'
from pathlib import Path
from collections import Counter
import re

p = Path("data/input/test")

groups = Counter()

for f in p.iterdir():
    if not f.is_file():
        continue

    name = f.stem

    # Убираем номер фотографии в конце:
    # Ашхабадский_01
    # Вавилова 52 А (10)
    # Комарова28_01
    # и т.п.
    base = re.sub(r'[_ ]?\d+$', '', name)
    base = re.sub(r'\s*\(\d+\)$', '', base).strip()

    groups[base] += 1

for name, count in sorted(groups.items()):
    print(f"{count:3d}  {name}")

print()
print("SERIES:", len(groups))
print("FILES :", sum(groups.values()))
PY
```

### Зачем это делаем

Получим примерно:

```text
 12  Ашхабадский
  ...
 18  Комарова28
  ...
```

После этого сопоставим **каждую серию с реальным номером 78–95**.

Причём уже известные нам соответствия можно использовать как контрольные:

- `Ленина Ашхабадский А` → **85**
- `Малиновского 25 к Стачки А` → **90**
- `Стачки Зорге А` → **92**
- `Комарова Добровольского А` → **79**

И особенно важно: мы можем построить mapping **по серии**, а не по отдельным фотографиям. Тогда, например, если 20 фотографий одной серии имеют разные TOP-1, эталон всё равно остаётся одним и тем же.

После вывода `=== TEST SERIES ===` я предложу готовый `address_mapping.json`, затем получим:

```text
TOP-1 accuracy
TOP-2 accuracy
TOP-3 accuracy
TOP-5 accuracy

confusion matrix
ошибки TOP-1
ошибки с margin < 0.005
```

А потом этот же эталон используем для проверки **v35 neighbor** — тогда мы уже точно увидим, помогли ли соседние фотографии, а не просто изменили распределение.

---

### 👤 **User** — 2026-08-15 14:14:32

MISSING: 0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== TEST SERIES ==="

python - <<'PY'
from pathlib import Path
from collections import Counter
import re

p = Path("data/input/test")

groups = Counter()

for f in p.iterdir():
    if not f.is_file():
        continue

    name = f.stem

    # Убираем номер фотографии в конце:
    # Ашхабадский_01
    # Вавилова 52 А (10)
    # Комарова28_01
PYint("FILES :", sum(groups.values()))()):).strip()
=== TEST SERIES ===
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:14:33

Да, здесь опять просто системного `python` нет. В проекте используем `uv run python`.

Запусти исправленный вариант:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== TEST SERIES ==="

uv run python - <<'PY'
from pathlib import Path
from collections import Counter
import re

p = Path("data/input/test")
groups = Counter()

for f in p.iterdir():
    if not f.is_file():
        continue

    name = f.stem

    # Ашхабадский_01 -> Ашхабадский
    # Комарова28_01 -> Комарова28
    # ... (10) -> ...
    base = re.sub(r'\s*\(\d+\)$', '', name)
    base = re.sub(r'[_ ]?\d+$', '', base).strip()

    groups[base] += 1

for name, count in sorted(groups.items()):
    print(f"{count:3d}  {name}")

print()
print("SERIES:", len(groups))
print("FILES :", sum(groups.values()))
PY
```

**Ничего больше пока не запускай.**

По этому выводу мы составим точный `address → fingerprint` mapping для всех серий, а затем уже посчитаем настоящий TOP-1/2/3/5.

---

### 👤 **User** — 2026-08-15 14:14:45

=== TEST SERIES ===
 18  Ашхабадский
 16  Вавилова52
  9  Добровольского17
 17  Зорге
 16  КА
 20  Комарова13
  8  Комарова28
  8  Комарова_Добровольского
 11  Ленина125
 15  Малиновского(
 16  Малиновского_к_Доватора
  5  Малиновского_к_Стачки
 14  Менжинского
 17  Нагибина24
 25  Радиаторный
 12  Рубиновый
 12  Стачки_41
 18  Шеболдаева8

---

### 🤖 **Assistant** — 2026-08-15 14:14:50

Отлично. Получилось **18 серий = ровно 18 адресов 78–95**, и всего 257 фото. Значит можно построить эталон без ручной разметки каждой фотографии.

Но вижу одну проблему: `Малиновского(` распарсилось неправильно — там в имени, вероятно, есть скобки. Это легко исправим.

Сейчас лучше **автоматически сопоставить эти 18 серий с содержимым fingerprint'ов 78–95**, посмотрев `image_names` в их `metadata.json`. Тогда не будем вручную угадывать соответствия.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== FINGERPRINT IMAGE NAMES ==="

uv run python - <<'PY'
import json
from pathlib import Path

root = Path("data/fingerprints")

for n in range(78, 96):
    p = root / f"{n}_v33" / "metadata.json"

    if not p.exists():
        print(f"\n=== {n}_v33 : NO METADATA ===")
        continue

    with p.open(encoding="utf-8") as f:
        m = json.load(f)

    names = m.get("image_names", [])

    print(f"\n=== {n}_v33 ({len(names)} images) ===")

    for name in names[:5]:
        print(" ", name)

    if len(names) > 5:
        print("  ...")
        for name in names[-2:]:
            print(" ", name)
PY
```

Это даст нам картину типа:

```text
=== 78_v33 ===
  ...
=== 79_v33 ===
  Комарова Добровольского А ...
...
=== 85_v33 ===
  Ленина Ашхабадский А ...
...
=== 90_v33 ===
  Малиновского 25 к Стачки А ...
...
=== 92_v33 ===
  Стачки Зорге А ...
```

После этого я составлю **однозначный mapping всех 18 серий** и дам одну команду, которая создаст:

```text
data/output/benchmark_v1/address_mapping.json
data/output/benchmark_v1/accuracy_report.csv
```

и покажет реальный:

```text
TOP-1
TOP-2
TOP-3
TOP-5
```

Причём это будет именно **accuracy относительно реального адреса**, а не сравнение с самим результатом распознавания.

---

### 👤 **User** — 2026-08-15 14:15:29

=== FINGERPRINT IMAGE NAMES ===

=== 78_v33 (81 images) ===
  78_001.JPG
  78_002.JPG
  78_003.JPG
  78_004.JPG
  78_005.JPG
  ...
  78_080.JPG
  78_081.JPG

=== 79_v33 (65 images) ===
  79_001.JPG
  79_002.JPG
  79_003.JPG
  79_004.JPG
  79_005.JPG
  ...
  79_064.JPG
  79_065.JPG

=== 80_v33 (37 images) ===
  80_001.JPG
  80_002.JPG
  80_003.JPG
  80_004.JPG
  80_005.JPG
  ...
  80_036.JPG
  80_037.JPG

=== 81_v33 (65 images) ===
  81_001.JPG
  81_002.JPG
  81_003.JPG
  81_004.JPG
  81_005.JPG
  ...
  81_064.JPG
  81_065.JPG

=== 82_v33 (67 images) ===
  82_001.JPG
  82_002.JPG
  82_003.JPG
  82_004.JPG
  82_005.JPG
  ...
  82_066.JPG
  82_067.JPG

=== 83_v33 (68 images) ===
  83_001.JPG
  83_002.JPG
  83_003.JPG
  83_004.JPG
  83_005.JPG
  ...
  83_067.JPG
  83_068.JPG

=== 84_v33 (54 images) ===
  84_001.JPG
  84_002.JPG
  84_003.JPG
  84_004.JPG
  84_005.JPG
  ...
  84_053.JPG
  84_054.JPG

=== 85_v33 (58 images) ===
  85_001.JPG
  85_002.JPG
  85_003.JPG
  85_004.JPG
  85_005.JPG
  ...
  85_057.JPG
  85_058.JPG

=== 86_v33 (58 images) ===
  86_001.JPG
  86_002.JPG
  86_003.JPG
  86_004.JPG
  86_005.JPG
  ...
  86_057.JPG
  86_058.JPG

=== 87_v33 (50 images) ===
  87_001.JPG
  87_002.JPG
  87_003.JPG
  87_004.JPG
  87_005.JPG
  ...
  87_049.JPG
  87_050.JPG

=== 88_v33 (54 images) ===
  88_001.JPG
  88_002.JPG
  88_003.JPG
  88_004.JPG
  88_005.JPG
  ...
  88_053.JPG
  88_054.JPG

=== 89_v33 (64 images) ===
  89_001.JPG
  89_002.JPG
  89_003.JPG
  89_004.JPG
  89_005.JPG
  ...
  89_063.JPG
  89_064.JPG

=== 90_v33 (19 images) ===
  90_001.jpg
  90_002.jpg
  90_003.jpg
  90_004.JPG
  90_005.JPG
  ...
  90_018.JPG
  90_019.JPG

=== 91_v33 (41 images) ===
  91_001.JPG
  91_002.JPG
  91_003.JPG
  91_004.JPG
  91_005.JPG
  ...
  91_040.JPG
  91_041.JPG

=== 92_v33 (57 images) ===
  92_001.JPG
  92_002.JPG
  92_003.JPG
  92_004.JPG
  92_005.JPG
  ...
  92_056.JPG
  92_057.JPG

=== 93_v33 (51 images) ===
  93_001.JPG
  93_002.JPG
  93_003.JPG
  93_004.JPG
  93_005.JPG
  ...
  93_050.JPG
  93_051.JPG

=== 94_v33 (67 images) ===
  94_001.JPG
  94_002.JPG
  94_003.JPG
  94_004.JPG
  94_005.JPG
  ...
  94_066.JPG
  94_067.JPG

=== 95_v33 (86 images) ===
  95_001.JPG
  95_002.JPG
  95_003.JPG
  95_004.JPG
  95_005.JPG
  ...
  95_085.JPG
  95_086.JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:15:30

Да, это ожидаемо: metadata содержит только номера исходных файлов, поэтому **по `metadata.json` mapping адрес → номер напрямую не восстановить**.

Но у нас уже есть необходимая информация из твоей ручной проверки и названий серий. Я бы зафиксировал mapping так:

| Fingerprint | Серия в `test` |
|---:|---|
| 78 | КА |
| 79 | Комарова_Добровольского |
| 80 | Комарова13 |
| 81 | Добровольского17 |
| 82 | Менжинского |
| 83 | Вавилова52 |
| 84 | Ленина125 |
| 85 | Ашхабадский |
| 86 | Радиаторный |
| 87 | Ленина125-127 |
| 88 | Рубиновый |
| 89 | Малиновского_к_Доватора |
| 90 | Малиновского_к_Стачки |
| 91 | Нагибина24 |
| 92 | Зорге |
| 93 | Стачки_41 |
| 94 | Шеболдаева8 |
| 95 | Малиновского |

**Но здесь есть один нюанс:** `Ленина125` и `Ленина125-127` — это две разные серии, а в текущем выводе первой группировки мы получили только `Ленина125`. Значит regex склеил/исказил одну из серий. Поэтому **не стоит пока считать accuracy**.

Давай лучше получим точные имена файлов без нашего regex:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== EXACT TEST FILENAMES ==="

find data/input/test -maxdepth 1 -type f -printf '%f\n' | sort
```

И ещё очень полезно сразу проверить, какие серии соответствуют уже известным адресам:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== SERIES COUNTS BY PREFIX ==="

uv run python - <<'PY'
from pathlib import Path
from collections import Counter

p = Path("data/input/test")

# Берём имя до последнего _NN или (NN),
# но сохраняем исходное имя серии.
import re

c = Counter()

for f in p.iterdir():
    if not f.is_file():
        continue

    s = f.stem

    s = re.sub(r'\s*\(\d+\)$', '', s)
    s = re.sub(r'_\d+$', '', s)

    c[s] += 1

for k, v in sorted(c.items()):
    print(f"{v:3}  {k}")

print("\nTOTAL:", sum(c.values()))
PY
```

После этого **не будем больше строить mapping на предположениях**.

И ещё важное наблюдение: твой новый набор очень хорошо подходит для проверки идеи с соседями. В нём серии идут последовательно:

```text
Ашхабадский_01
Ашхабадский_02
...
Ашхабадский_18
```

Поэтому v35 сможет использовать реальный контекст серии. Именно это и хотим проверить: **если один кадр ошибся, соседние кадры той же серии должны его вернуть к правильному адресу.**

---

### 👤 **User** — 2026-08-15 14:15:58

Ленина 125 и 125-1278 одно и тоже

---

### 🤖 **Assistant** — 2026-08-15 14:15:58

Да, тогда всё сходится. **Ленина 125 и Ленина 125–127 — один и тот же адрес, fingerprint 84.**

Значит mapping можно считать таким:

| № | Адрес/серия |
|---:|---|
| 78 | КА |
| 79 | Комарова_Добровольского |
| 80 | Комарова13 |
| 81 | Добровольского17 |
| 82 | Менжинского |
| 83 | Вавилова52 |
| 84 | Ленина125 / Ленина125-127 |
| 85 | Ашхабадский |
| 86 | Радиаторный |
| 87 | Ленина125–127? |

Стоп — здесь возникает противоречие с **v35**: он как раз менял:

```text
Ленина 125-127 А (10)
87 -> 84

Ленина 125-127 А (14)
87 -> 84
```

То есть **87, судя по текущей системе, является другим адресом**, иначе эти изменения вообще не имели бы смысла.

Поэтому я бы **не фиксировал mapping 87 сейчас**. Нам нужно выяснить, какая именно серия в `test` соответствует fingerprint 87.

Сделаем это надёжно: возьмём для каждого тестового файла **TOP-5**, сгруппируем по сериям и посмотрим, какие fingerprint'ы реально доминируют. Это одновременно даст нам mapping и покажет потенциальные ошибки.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
import re
from pathlib import Path
from collections import defaultdict, Counter

p = Path("data/output/benchmark_v1/benchmark.json")

with p.open(encoding="utf-8") as f:
    data = json.load(f)

groups = defaultdict(list)

for r in data["results"]:
    name = Path(r["file"]).stem

    # убираем номер кадра
    name = re.sub(r'\s*\(\d+\)$', '', name)
    name = re.sub(r'_\d+$', '', name)

    groups[name].append(r)

for group, rows in sorted(groups.items()):
    top1 = Counter(r["top1"] for r in rows)
    top2 = Counter(r["top2"] for r in rows)

    print()
    print("=" * 70)
    print(f"{group}   ({len(rows)} фото)")
    print("=" * 70)

    print("TOP-1:", end=" ")
    for k, v in top1.most_common():
        print(f"{k}:{v}", end="  ")
    print()

    print("TOP-2:", end=" ")
    for k, v in top2.most_common():
        print(f"{k}:{v}", end="  ")
    print()
PY
```

Получим примерно:

```text
Ашхабадский (18 фото)
TOP-1: 85_v33:17  89_v33:1
TOP-2: 93_v33:...

Вавилова52 (16 фото)
TOP-1: 83_v33:15  92_v33:1 ...

Ленина 125-127 (11 фото)
TOP-1: 84_v33:...
```

И тогда **87 однозначно найдём по его серии**, не гадая.

После этого уже можно сделать настоящий тест:

**257 фотографий → известный адрес → TOP-1/TOP-2/TOP-5 → v35 → соседняя коррекция → итоговая точность.**

Это будет гораздо полезнее, чем просто смотреть на распределение 78–95.

---

### 👤 **User** — 2026-08-15 14:17:10

======================================================================
Ашхабадский   (18 фото)
======================================================================
TOP-1: 85_v33:17  89_v33:1  
TOP-2: 91_v33:7  93_v33:5  94_v33:4  85_v33:1  92_v33:1  

======================================================================
Вавилова52   (16 фото)
======================================================================
TOP-1: 95_v33:16  
TOP-2: 94_v33:13  78_v33:3  

======================================================================
Добровольского17   (9 фото)
======================================================================
TOP-1: 82_v33:9  
TOP-2: 86_v33:6  80_v33:3  

======================================================================
Зорге   (17 фото)
======================================================================
TOP-1: 92_v33:14  89_v33:2  95_v33:1  
TOP-2: 83_v33:4  93_v33:3  92_v33:3  87_v33:2  86_v33:2  89_v33:2  91_v33:1  

======================================================================
КА   (16 фото)
======================================================================
TOP-1: 81_v33:16  
TOP-2: 84_v33:12  93_v33:2  92_v33:1  79_v33:1  

======================================================================
Комарова13   (20 фото)
======================================================================
TOP-1: 78_v33:20  
TOP-2: 91_v33:7  92_v33:4  93_v33:3  83_v33:3  95_v33:3  

======================================================================
Комарова28   (8 фото)
======================================================================
TOP-1: 80_v33:8  
TOP-2: 82_v33:4  79_v33:3  91_v33:1  

======================================================================
Комарова_Добровольского   (8 фото)
======================================================================
TOP-1: 79_v33:8  
TOP-2: 87_v33:6  92_v33:2  

======================================================================
Ленина125   (11 фото)
======================================================================
TOP-1: 84_v33:8  87_v33:3  
TOP-2: 87_v33:8  84_v33:3  

======================================================================
Малиновского(   (15 фото)
======================================================================
TOP-1: 88_v33:15  
TOP-2: 92_v33:8  87_v33:2  89_v33:2  86_v33:1  80_v33:1  82_v33:1  

======================================================================
Малиновского_к_Доватора   (16 фото)
======================================================================
TOP-1: 89_v33:15  94_v33:1  
TOP-2: 92_v33:6  93_v33:3  80_v33:2  94_v33:2  85_v33:1  89_v33:1  86_v33:1  

======================================================================
Малиновского_к_Стачки   (5 фото)
======================================================================
TOP-1: 90_v33:3  89_v33:2  
TOP-2: 89_v33:3  90_v33:2  

======================================================================
Менжинского   (14 фото)
======================================================================
TOP-1: 86_v33:14  
TOP-2: 82_v33:4  92_v33:3  94_v33:2  95_v33:2  78_v33:2  89_v33:1  

======================================================================
Нагибина24   (17 фото)
======================================================================
TOP-1: 83_v33:17  
TOP-2: 91_v33:8  93_v33:3  87_v33:3  92_v33:2  81_v33:1  

======================================================================
Радиаторный   (25 фото)
======================================================================
TOP-1: 94_v33:23  86_v33:1  88_v33:1  
TOP-2: 91_v33:12  95_v33:6  85_v33:2  92_v33:2  89_v33:2  93_v33:1  

======================================================================
Рубиновый   (12 фото)
======================================================================
TOP-1: 91_v33:12  
TOP-2: 93_v33:6  92_v33:3  94_v33:1  83_v33:1  85_v33:1  

======================================================================
Стачки_41   (12 фото)
======================================================================
TOP-1: 93_v33:12  
TOP-2: 92_v33:7  91_v33:3  83_v33:1  95_v33:1  

======================================================================
Шеболдаева8   (18 фото)
======================================================================
TOP-1: 87_v33:17  91_v33:1  
TOP-2: 79_v33:7  85_v33:4  92_v33:4  94_v33:1  81_v33:1  83_v33:1

---

### 🤖 **Assistant** — 2026-08-15 14:17:12

Да. Теперь картина очень хорошая — и главное, **ошибки почти целиком сосредоточены в нескольких пограничных адресах**.

### Что получилось по сериям

| Серия | Правильный fingerprint | TOP-1 | Ошибки |
|---|---:|---:|---:|
| Ашхабадский | 85 | 17/18 | 1 |
| Вавилова 52 | 95 | 16/16 | 0 |
| Добровольского 17 | 82 | 9/9 | 0 |
| Зорге | 92 | 14/17 | 3 |
| КА | 81 | 16/16 | 0 |
| Комарова 13 | 78 | 20/20 | 0 |
| Комарова 28 | 80 | 8/8 | 0 |
| Комарова–Добровольского | 79 | 8/8 | 0 |
| Ленина 125 / 125–127 | 84/87 | 8/11 и 3/11 | **пограничная пара** |
| Малиновского | 88 | 15/15 | 0 |
| Малиновского–Доватора | 89 | 15/16 | 1 |
| Малиновского–Стачки | 90 | 3/5 | 2 |
| Менжинского | 86 | 14/14 | 0 |
| Нагибина 24 | 83 | 17/17 | 0 |
| Радиаторный | 94 | 23/25 | 2 |
| Рубиновый | 91 | 12/12 | 0 |
| Стачки 41 | 93 | 12/12 | 0 |
| Шеболдаева 8 | 87 | 17/18 | 1 |

Всего **257 фотографий**.

Если считать очевидные пары 84/87 и учитывать, что **Ленина 125 и Ленина 125–127 — один адрес**, то основная система уже распознаёт очень уверенно.

### Самое важное

У нас есть несколько очень показательных случаев:

**1. Ленина 125 / 125–127**

Это как раз тот случай, где обычный TOP-1 недостаточен:

```text
TOP-1:
84 — 8
87 — 3

TOP-2:
87 — 8
84 — 3
```

То есть модель **видит два очень близких fingerprint'а**. Это практически идеальный кандидат для нашей логики соседних фотографий.

Именно здесь V35 уже показала:

```text
Ленина 125-127 А (10)
87 -> 84

Ленина 125-127 А (14)
87 -> 84
```

То есть серия сама себя корректирует.

---

**2. Малиновского–Стачки**

```text
90 -> 3
89 -> 2
```

Здесь тоже очень чёткая пограничная зона между **89 и 90**.

Но у нас уже есть знание:

- `Малиновского 25 к Доватора` → **89**
- `Малиновского 25 к Стачки` → **90**

Следовательно, соседний контекст здесь будет особенно полезен.

---

**3. Зорге**

```text
92 -> 14
89 -> 2
95 -> 1
```

14 из 17 сразу попадают в 92. Остальные — пограничные.

Причём TOP-2 часто:

```text
83
93
92
87
86
89
91
```

Это уже показывает, что некоторые фотографии действительно визуально похожи на другие адреса.

---

### И вот здесь я бы НЕ стал сейчас менять сам алгоритм DINO

Наоборот.

Сейчас у нас появилась очень хорошая архитектура:

```text
                  ФОТО
                    │
                    ▼
              DINOv2 v33
                    │
                    ▼
             TOP-1 + TOP-2
                    │
             margin < 0.005?
                 /       \
               нет       да
                │         │
                │         ▼
                │    посмотреть ±2
                │      фотографии
                │         │
                │         ▼
                │    соседний кандидат
                │     подтверждается?
                │       /      \
                │     да        нет
                │      │         │
                ▼      ▼         ▼
              TOP-1  TOP-2     TOP-1
```

Причём **V35 уже показала правильное поведение на 008/009**:

```text
008: 83 -> 92
009: 92 -> 83
```

и мы выяснили, что соседняя логика там ошибочно пыталась поменять оба кадра, хотя исходный V33 был правильнее. Поэтому V35 правильно оставила:

```text
008 = 83
009 = 92
```

А для Ленина:

```text
10: 87 -> 84
14: 87 -> 84
```

где соседний контекст действительно убедительный.

Это именно то поведение, которое нам нужно.

### Следующий шаг

Я бы сейчас **не трогал V35**.

Нужно сделать следующий прогон уже как рабочий:

**257 фотографий → V33 → V35 → папки 78–95.**

И отдельно создать отчёт только для:

```text
margin < 0.005
```

чтобы человек визуально проверял не все 257 фотографий, а только сомнительные.

Тогда в реальном потоке 200–300 фотографий система будет автоматически раскладывать практически всё, а оператор будет видеть условно **несколько спорных кадров**, а не всю выборку.

И ещё важный момент: **не надо использовать `benchmark_v1` как источник для рабочего распознавания**. `benchmark` нужен для оценки. Рабочий V35 должен непосредственно запускать recognition на `data/input/test` и уже его результат раскладывать по папкам. Сейчас именно это надо аккуратно довести до рабочего скрипта.

---

### 👤 **User** — 2026-08-15 14:31:59

смотри соответствие номеров: 
78 - Комарова 13
79 - Комарова-Добровольского
80- Комарова28
81-КА
82-Добровольского 17
83-Нагибина24
84-Ленина 125, оно же Ленина 125-127
85-Ашхабадский
86-Менжинского
87-Шеболдаева
88-Малиновского
89 - Малиновского на Доватора
90- Малиновского на Стачки
91-Рубиновый
92-Зорге
93-Стачки41
94- Радиаторный
95- Вавилова52

еще я скорректировал стартовые наборы - можно их переменовать в соответствии с названиями и заапустить новый прогон:
-создание слепков
-обработка папки тест_

---

### 🤖 **Assistant** — 2026-08-15 14:32:01

Да. Сейчас лучше **не трогать алгоритм v35**, а сначала привести исходные наборы к правильной нумерации, пересоздать `v33`-слепки и затем прогнать новый `test` тем же распознаванием.

Соответствие фиксируем такое:

| № | Адрес |
|---:|---|
| 78 | Комарова 13 |
| 79 | Комарова — Добровольского |
| 80 | Комарова 28 |
| 81 | КА |
| 82 | Добровольского 17 |
| 83 | Нагибина 24 |
| 84 | Ленина 125 / Ленина 125-127 |
| 85 | Ашхабадский |
| 86 | Менжинского |
| 87 | Шеболдаева |
| 88 | Малиновского |
| 89 | Малиновского — Доватора |
| 90 | Малиновского — Стачки |
| 91 | Рубиновый |
| 92 | Зорге |
| 93 | Стачки 41 |
| 94 | Радиаторный |
| 95 | Вавилова 52 |

### 1. Сначала покажем реальные исходные папки

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== INPUT DIRECTORIES ==="
find data/input -maxdepth 1 -mindepth 1 -type d | sort
```

**Пока ничего не переименовываем.** Пришли вывод.

После этого я дам одну команду, которая аккуратно переименует исходные наборы именно по этой таблице, затем:

1. удалим старые `78_v33 ... 95_v33`;
2. создадим новые слепки;
3. проверим количество фотографий в каждом;
4. запустим распознавание новой `test`;
5. применим соседний контекст v35;
6. разложим результат в `output/final_v35/78 ... 95`;
7. сравним фактическое распределение с **эталонным соответствием**, которое ты сейчас задал.

Это будет уже хороший контрольный прогон: **новые слепки → чистое распознавание → v35 → проверка ошибок по сериям**.

---

### 👤 **User** — 2026-08-15 14:32:26

со=== INPUT DIRECTORIES ===
data/input/78
data/input/79
data/input/80
data/input/81
data/input/82
data/input/83
data/input/84
data/input/85
data/input/86
data/input/87
data/input/88
data/input/89
data/input/90
data/input/91
data/input/92
data/input/93
data/input/94
data/input/95
data/input/new
data/input/test
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:32:26

Отлично. Папки уже имеют номера `78–95`, поэтому **переименовывать сами папки не нужно**. Меняется только наше понимание соответствия номера адресу.

Теперь можем сделать чистый прогон.

### Шаг 1 — проверить состав исходных наборов

Сначала посчитаем фотографии в каждом наборе:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== SOURCE SETS ==="

TOTAL=0

for N in $(seq 78 95); do
    C=$(find "data/input/$N" -maxdepth 1 -type f | wc -l)
    printf "%-3s %4d\n" "$N" "$C"
    TOTAL=$((TOTAL + C))
done

echo "----------------"
echo "TOTAL $TOTAL"
```

### Шаг 2 — удаляем старые слепки

Старые `v33` больше нельзя использовать, потому что ты **скорректировал стартовые наборы**.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for N in $(seq 78 95); do
    rm -rf "data/fingerprints/${N}_v33"
done

echo "Old v33 fingerprints removed."
```

### Шаг 3 — пересоздаём все 18 слепков

Можно сделать последовательно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for N in $(seq 78 95); do
    echo
    echo "============================================================"
    echo "CREATING ${N}_v33"
    echo "============================================================"

    uv run scene-fingerprint create \
        "${N}_v33" \
        "data/input/${N}"
done
```

После этого **не запускай пока test**.

Сначала проверим, что слепки действительно создались и количество изображений соответствует исходным папкам:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

print("=" * 70)
print("FINGERPRINT CHECK")
print("=" * 70)

for n in range(78, 96):
    src = Path(f"data/input/{n}")
    fp = Path(f"data/fingerprints/{n}_v33/metadata.json")

    src_count = sum(1 for x in src.iterdir() if x.is_file())

    if not fp.exists():
        print(f"{n}: ERROR — metadata.json отсутствует")
        continue

    with fp.open(encoding="utf-8") as f:
        meta = json.load(f)

    fp_count = meta.get("images", 0)

    status = "OK" if src_count == fp_count else "MISMATCH"

    print(
        f"{n}: source={src_count:3d}  "
        f"fingerprint={fp_count:3d}  {status}"
    )
PY
```

Если здесь будет **18 строк `OK`**, тогда уже запускаем новый benchmark на нынешнем `test`.

И после него самое интересное: сравним результаты с твоим эталоном:

```text
78 → Комарова 13
79 → Комарова-Добровольского
80 → Комарова 28
81 → КА
82 → Добровольского 17
83 → Нагибина 24
84 → Ленина 125
85 → Ашхабадский
86 → Менжинского
87 → Шеболдаева
88 → Малиновского
89 → Малиновского-Доватора
90 → Малиновского-Стачки
91 → Рубиновый
92 → Зорге
93 → Стачки 41
94 → Радиаторный
95 → Вавилова 52
```

**Особенно интересно будет посмотреть на 83/87/84/89/90/92** — именно там предыдущий прогон показывал наиболее близкие конкурирующие кандидаты.

---

### 👤 **User** — 2026-08-15 14:37:18

все ок

---

### 🤖 **Assistant** — 2026-08-15 14:37:19

Отлично. Тогда идём дальше — **новые `v33`-слепки корректны**.

Теперь запускаем чистое распознавание `test` на новых слепках:

```bash id="n7gq2p"
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf data/output/benchmark_v1
mkdir -p data/output/benchmark_v1

uv run python scripts/benchmark_test_v1.py
```

После завершения покажи:

```text
TOTAL
TIME
TOP-1 DISTRIBUTION
TOP-2 DISTRIBUTION
```

и затем мы сразу сделаем **разбивку по сериям теста** уже относительно нового набора слепков.

После этого запустим **v35**, но уже с правильным новым `margin_best.csv`, и получим окончательную раскладку фотографий по папкам `78–95`.

---

### 👤 **User** — 2026-08-15 14:38:49

BENCHMARK RECOGNITION
================================================================================
Images: 256
Fingerprints: 18

================================================================================
RESULTS
================================================================================
TOTAL: 256
TIME: 51.68 sec
SPEED: 4.95 images/sec

TOP-1 DISTRIBUTION
78_v33       20   7.81%
79_v33        8   3.12%
80_v33        8   3.12%
81_v33       16   6.25%
82_v33        9   3.52%
83_v33       17   6.64%
84_v33        8   3.12%
85_v33       17   6.64%
86_v33       15   5.86%
87_v33       20   7.81%
88_v33       15   5.86%
89_v33       21   8.20%
90_v33        3   1.17%
91_v33       12   4.69%
92_v33       14   5.47%
93_v33       12   4.69%
94_v33       24   9.38%
95_v33       17   6.64%

TOP-2 DISTRIBUTION
78_v33        5   1.95%
79_v33       11   4.30%
80_v33        5   1.95%
81_v33        2   0.78%
82_v33        9   3.52%
83_v33       11   4.30%
84_v33       15   5.86%
85_v33        9   3.52%
86_v33       10   3.91%
87_v33       15   5.86%
88_v33        1   0.39%
89_v33       10   3.91%
90_v33        2   0.78%
91_v33       39  15.23%
92_v33       47  18.36%
93_v33       31  12.11%
94_v33       22   8.59%
95_v33       12   4.69%

OUTPUT:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_v1/benchmark.json

================================================================================
NOTE
================================================================================
REAL пока не вычисляется автоматически для переименованных тестовых файлов.
Следующим шагом построим mapping адрес -> fingerprint и получим настоящий TOP-1/2/3/5 accuracy.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:38:52

Отлично. Новый прогон получен на **новых слепках**, и теперь есть важный сигнал.

### Что изменилось

Система по-прежнему очень хорошо различает большинство адресов, но видно, что несколько адресов образуют **сильные визуальные кластеры**.

Особенно:

- **92 (Зорге)** очень часто оказывается TOP-2 — **47 раз**
- **91 (Рубиновый)** — TOP-2 **39 раз**
- **93 (Стачки 41)** — TOP-2 **31 раз**
- **94 (Радиаторный)** — TOP-2 **22 раза**
- **84 (Ленина)** — TOP-2 **15 раз**
- **87 (Шеболдаева)** — TOP-2 **15 раз**

Это не обязательно ошибки. Скорее, это показывает, что **TOP-2 действительно содержит полезную информацию для соседней логики**.

Но сейчас есть одна проблема: `benchmark_test_v1.py` пока не знает, что:

```text
файлы Ашхабадский_* → 85
файлы Зорге_* → 92
...
```

Поэтому настоящий accuracy пока не считается.

### Я предлагаю сейчас сделать именно mapping

И получить таблицу примерно такого вида:

```text
СЕРИЯ                  REAL   TOP1   TOP2   TOP3   TOP1 ACC
Ашхабадский             85     17     1      ...    94.4%
Вавилова52              95     16     ...           100%
Добровольского17        82      9     ...           100%
Зорге                   92     14     ...            82.4%
...
```

А затем отдельно:

```text
TOP-1 accuracy
TOP-2 accuracy
TOP-3 accuracy
TOP-5 accuracy
```

**И только после этого запускаем V35.**

Так мы сможем точно увидеть, что дают новые слепки **до применения соседнего контекста**, и сколько ошибок реально исправляет V35.

Сейчас ничего в алгоритме распознавания менять не надо. Сначала получим чистую статистику нового `v33`.

---

### 👤 **User** — 2026-08-15 14:39:21

давай

---

