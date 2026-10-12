## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 🤖 **Assistant** — 2026-08-15 14:51:42

Да. И этот лог очень хорошо показывает, **почему V36 сейчас практически ничего не меняет**.

Главное: **сама идея с соседями правильная**, но текущая реализация применяет её не к тому типу ситуации.

### Что видно по `img_000...img_255`

У тебя фотографии идут последовательными сериями адресов:

- `img_000–017` → 85
- `018–033` → 95
- `034–042` → 82
- `043–58` → 92
- `60–75` → 81
- `76–95` → 78
- `96–103` → 80
- `104–111` → 79
- `112–122` → 84/87 — **здесь как раз есть проблема**
- `123–137` → 88
- `138–153` → 89
- `154–158` → 90/89
- `159–172` → 86
- `173–189` → 83
- `190–212` → 94
- `213–214` → пограничные
- `215–226` → 91
- `227–238` → 93
- `239–255` → 87

То есть данные для соседнего контекста **идеальные**: фотографии одного адреса идут пачками.

---

## Но сейчас V36 делает слишком жесткое условие

Вот например:

```text
img_113   87 → 84   margin 0.00585
img_114   84 → 87   margin 0.00484
img_115   87 → 84   margin 0.00081
img_116   84 → 87
img_117   84 → 87
img_118   84 → 87
img_119   87 → 84
img_120   84 → 87
img_121   84 → 87
img_122   84 → 87
```

Здесь алгоритм должен понять:

**мы находимся внутри перехода 79 → 84 → 87 → 88.**

И смотреть не просто `TOP-2` соседей, а **какая группа фотографий формируется вокруг текущего кадра**.

---

# Я бы сделал V37 именно по твоей логике

Для каждого сомнительного кадра:

### 1. V33 уверенно решил

Например:

```text
V33 = 84
margin = большое
```

→ ничего не делаем.

---

### 2. V33 сомневается

Например:

```text
TOP1 = 84
TOP2 = 87
margin < 0.005
```

Тогда:

**Сначала смотрим вперёд:**

```text
+1
+2
```

Но не просто проверяем `TOP-2`.

Для каждого соседнего изображения смотрим его **TOP-1**.

Например:

```text
текущий: 84 / 87

+1: 87
+2: 87
```

→ два соседа подтверждают 87.

**Меняем на 87.**

---

### Другой вариант

```text
текущий: 84 / 87

+1: 87
+2: 84
```

Ты именно это и сказал:

> если они похожи на кандидата 2 — значит это то, что надо, если второе фото не похоже, но похоже первое — значит тоже оно

То есть:

```text
+1 = 87
+2 = 84
```

→ **87 тоже достаточно.**

---

### Если вперёд ничего не подтвердилось

Тогда:

```text
-1
-2
```

И аналогичная логика.

---

# Но есть ещё важный момент

Я бы добавил **границы серии**.

Например:

```text
img_112 = 84
img_113 = 87
img_114 = 84
img_115 = 87
```

Если тупо смотреть соседей, можно получить хаос.

Поэтому V37 должен учитывать:

**сосед считается подтверждением только если он поддерживает одного из двух кандидатов текущего кадра.**

Иными словами:

```text
current:
TOP1 = 84
TOP2 = 87
```

Нам совершенно неинтересно, что сосед определился как `92`.

---

# И ещё лучше: учитывать направление

Алгоритм должен быть таким:

```text
ЕСЛИ margin >= 0.005:
    оставить V33

ИНАЧЕ:

    candidate1 = TOP1
    candidate2 = TOP2

    проверить +1
    проверить +2

    ЕСЛИ +1 или +2 подтверждают candidate2:
        candidate2 становится результатом

    ИНАЧЕ:
        проверить -1
        проверить -2

        ЕСЛИ -1 или -2 подтверждают candidate2:
            candidate2 становится результатом

        ИНАЧЕ:
            оставить candidate1
```

Но я бы сделал ещё одно улучшение:

### Если впереди и сзади разные результаты

Например:

```text
-2 = 84
-1 = 84

current = 87 / 84

+1 = 87
+2 = 87
```

Это **граница между сериями**.

Тогда нельзя просто сказать `87` или `84`.

Нужно смотреть направление относительно кадра.

Для `img_115`:

```text
img_113 = 87
img_114 = 84
img_115 = 87
img_116 = 84
img_117 = 84
```

Это уже показывает, что **сама последовательность может содержать кадры, которые DINO путает**, а не обязательно реальные смены адресов.

И здесь очень полезно будет использовать **не только соседние TOP-1, но и score кандидатов соседей**.

---

## Самое важное сейчас

По твоему benchmark мы уже знаем:

**V33:**

- TOP-1 = **95.31%**
- TOP-2 = **99.22%**
- TOP-5 = **100%**

То есть нам не надо ломать V33.

Наша задача V37:

> **трогать только примерно 5 сомнительных кадров и пытаться исправить их, не ухудшая остальные 251.**

И особенно проверить реальные проблемные зоны:

```text
85 → 89
92 → 89
92 → 95
84 → 87
90 → 89
94 → 86
94 → 89
89 → 94
```

Причём сейчас на `img_000...` мы видим очень важную вещь: **соседний контекст действительно соответствует физическому порядку съёмки**, поэтому этот механизм имеет смысл.

### Следующий шаг

Я бы **не переписывал сейчас весь pipeline**. Сделаем `v37` поверх существующего `benchmark_img/benchmark.json`:

1. берём V33 TOP-1/TOP-2;
2. сомнение `< 0.005`;
3. смотрим `+1`, `+2`;
4. если кандидат №2 встречается хотя бы в одном из них → кандидат №2;
5. если нет → смотрим `-1`, `-2`;
6. если и там нет → V33;
7. **не используем имена файлов вообще** — только физический порядок `img_000, img_001...`;
8. отдельно пишем в CSV каждое решение, чтобы можно было проверить глазами.

И после этого прогоняем **сначала на `data/input/new`**, а не на старом `test`, поскольку именно `new` у нас теперь содержит реальные `img_xxx`-имена.

Если хочешь, следующим сообщением дам **готовую команду для создания `sort_neighbor_v37.py`**, без ручного редактирования файла.

---

### 👤 **User** — 2026-08-15 14:53:20

да

---

### 🤖 **Assistant** — 2026-08-15 14:53:21

Да. Делаем V37 именно под реальные `img_000...img_999`: порядок файлов — единственный источник соседнего контекста.

Сначала создай скрипт:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/sort_neighbor_v37.py <<'PY'
#!/usr/bin/env python3

import csv
import json
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/new"
SOURCE_JSON = PROJECT / "data/output/benchmark_img/benchmark.json"

OUTPUT_DIR = PROJECT / "output/neighbor_v37"
SORTED_DIR = OUTPUT_DIR / "sorted"
REPORT_CSV = OUTPUT_DIR / "neighbor_decision.csv"

MARGIN_LIMIT = 0.005

def normalize_id(x):
    try:
        return int(str(x).replace("_v33", ""))
    except Exception:
        return None

def get_results(item):
    """
    Поддерживаем возможные варианты структуры benchmark.json.
    """
    results = (
        item.get("results")
        or item.get("predictions")
        or item.get("candidates")
        or item.get("top_k")
    )

    if isinstance(results, dict):
        results = list(results.items())

    if not isinstance(results, list):
        return []

    out = []

    for r in results:
        if isinstance(r, dict):
            fp = (
                r.get("fingerprint")
                or r.get("id")
                or r.get("label")
                or r.get("name")
            )
            score = (
                r.get("score")
                if r.get("score") is not None
                else r.get("similarity")
            )

            if fp is not None:
                try:
                    score = float(score)
                except Exception:
                    score = 0.0
                out.append((normalize_id(fp), score))

        elif isinstance(r, (list, tuple)) and len(r) >= 2:
            out.append((normalize_id(r[0]), float(r[1])))

    return [(fp, score) for fp, score in out if fp is not None]

def get_image(item):
    for key in ("image", "filename", "file", "path", "name"):
        value = item.get(key)
        if value:
            return Path(str(value)).name
    return None

with open(SOURCE_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

if isinstance(data, dict):
    items = (
        data.get("results")
        or data.get("images")
        or data.get("items")
        or data.get("data")
    )
else:
    items = data

if not isinstance(items, list):
    raise RuntimeError("Не удалось найти список результатов в benchmark.json")

records = []

for item in items:
    image = get_image(item)
    results = get_results(item)

    if not image or not results:
        continue

    top1 = results[0][0]
    top1_score = results[0][1]

    top2 = results[1][0] if len(results) > 1 else None
    top2_score = results[1][1] if len(results) > 1 else None

    margin = (
        top1_score - top2_score
        if top2_score is not None
        else 999.0
    )

    records.append({
        "image": image,
        "top1": top1,
        "top1_score": top1_score,
        "top2": top2,
        "top2_score": top2_score,
        "margin": margin,
    })

# Очень важно:
# сортируем по реальному имени img_000, img_001...
# а не по порядку JSON.
def image_number(r):
    name = Path(r["image"]).stem
    digits = "".join(c for c in name if c.isdigit())
    return int(digits) if digits else 10**9

records.sort(key=image_number)

changed = []
rows = []

for i, rec in enumerate(records):

    v33 = rec["top1"]
    second = rec["top2"]
    margin = rec["margin"]

    final = v33
    reason = "V33"

    forward_support = []
    backward_support = []

    forward_neighbors = []
    backward_neighbors = []

    # Работаем только с сомнительными кадрами.
    if margin < MARGIN_LIMIT and second is not None:

        # ------------------------------------------------------------
        # 1. СНАЧАЛА СМОТРИМ ВПЕРЕД
        # ------------------------------------------------------------
        for offset in (1, 2):
            j = i + offset

            if j >= len(records):
                continue

            neighbor = records[j]
            nid = neighbor["top1"]

            forward_neighbors.append(
                f"+{offset}:{neighbor['image']}={nid}"
            )

            if nid == second:
                forward_support.append(offset)

        # Если хотя бы один из следующих двух кадров
        # подтверждает кандидата №2 — выбираем его.
        if forward_support:
            final = second
            reason = "FORWARD_SUPPORT_TOP2"

        else:

            # --------------------------------------------------------
            # 2. ЕСЛИ ВПЕРЕДИ НЕ ПОДТВЕРДИЛОСЬ — СМОТРИМ НАЗАД
            # --------------------------------------------------------
            for offset in (1, 2):
                j = i - offset

                if j < 0:
                    continue

                neighbor = records[j]
                nid = neighbor["top1"]

                backward_neighbors.append(
                    f"-{offset}:{neighbor['image']}={nid}"
                )

                if nid == second:
                    backward_support.append(offset)

            if backward_support:
                final = second
                reason = "BACKWARD_SUPPORT_TOP2"
            else:
                reason = "NO_NEIGHBOR_SUPPORT"

    if final != v33:
        changed.append({
            "image": rec["image"],
            "v33": v33,
            "second": second,
            "final": final,
            "margin": margin,
            "reason": reason,
            "forward_support": forward_support,
            "backward_support": backward_support,
        })

    rows.append({
        "index": i,
        "image": rec["image"],
        "v33": v33,
        "second": second,
        "final": final,
        "margin": margin,
        "reason": reason,
        "forward_support": ",".join(map(str, forward_support)),
        "backward_support": ",".join(map(str, backward_support)),
        "forward_neighbors": "; ".join(forward_neighbors),
        "backward_neighbors": "; ".join(backward_neighbors),
    })

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if SORTED_DIR.exists():
    shutil.rmtree(SORTED_DIR)

SORTED_DIR.mkdir(parents=True)

for row in rows:
    src = INPUT_DIR / row["image"]

    if not src.exists():
        continue

    destination = SORTED_DIR / str(row["final"])
    destination.mkdir(parents=True, exist_ok=True)

    shutil.copy2(src, destination / src.name)

with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "index",
            "image",
            "v33",
            "second",
            "final",
            "margin",
            "reason",
            "forward_support",
            "backward_support",
            "forward_neighbors",
            "backward_neighbors",
        ],
    )

    writer.writeheader()
    writer.writerows(rows)

print("=" * 80)
print("NEIGHBOR CONTEXT V37")
print("=" * 80)
print(f"Input images : {len(records)}")
print(f"Margin limit : {MARGIN_LIMIT}")
print("Neighbor logic : +1,+2 -> -1,-2")
print("Neighbor match : TOP-1 of neighbor == TOP-2 of current")
print()

print("=" * 80)
print("RESULT")
print("=" * 80)

ambiguous = sum(1 for r in rows if r["margin"] < MARGIN_LIMIT)

print(f"Total images:        {len(rows)}")
print(f"Margin < 0.005:      {ambiguous}")
print(f"Changed by neighbors:{len(changed):8d}")

if changed:
    print()
    print("CHANGED")
    print("-" * 80)

    for x in changed:
        print(
            f"{x['image']}: "
            f"{x['v33']} -> {x['final']} "
            f"(second={x['second']}, "
            f"margin={x['margin']:.6f}, "
            f"{x['reason']})"
        )

print()
print("DISTRIBUTION")
print("-" * 80)

distribution = {}

for row in rows:
    distribution[row["final"]] = distribution.get(row["final"], 0) + 1

for fp in sorted(distribution):
    print(f"{fp:<8} {distribution[fp]:>4}")

print("-" * 80)
print(f"TOTAL    {len(rows):>8}")

print()
print("OUTPUT:")
print(f"  sorted : {SORTED_DIR}")
print(f"  report : {REPORT_CSV}")
PY

python -m py_compile scripts/sort_neighbor_v37.py

echo "STATUS=$?"
```

Если получишь:

```text
STATUS=0
```

запускаем:

```bash
rm -rf output/neighbor_v37

uv run python -u scripts/sort_neighbor_v37.py
```

И **пока ничего не меняем в основном pipeline**.

Особенно интересуют строки `CHANGED`. Если V37 исправит хотя бы несколько пограничных кадров, следующим шагом проверим его на нашем эталоне и посчитаем, стал ли TOP-1 выше 95.31%.

---

### 👤 **User** — 2026-08-15 14:53:44

echo "STATUS=$?"pile scripts/sort_neighbor_v37.py(row["final"], 0) + 1k.json")
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
STATUS=127

---

### 🤖 **Assistant** — 2026-08-15 14:53:45

Да, это просто потому, что в системе нет команды `python`. Сам скрипт не проверился.

У тебя проект работает через `uv`, поэтому используй:

```bash id="j9f5k4"
cd ~/projects/scene_fingerprint_mvp_v02

uv run python -m py_compile scripts/sort_neighbor_v37.py

echo "STATUS=$?"
```

Если будет:

```text
STATUS=0
```

тогда запускаем:

```bash id="m2j7xq"
rm -rf output/neighbor_v37

uv run python -u scripts/sort_neighbor_v37.py
```

**Важно:** строка `Command 'python' not found` не означает ошибку в самом `sort_neighbor_v37.py`. Просто `python` вне виртуального окружения у тебя не зарегистрирован как команда.

Пришли вывод запуска V37 — особенно блок `CHANGED`.

---

### 👤 **User** — 2026-08-15 14:54:09

NEIGHBOR CONTEXT V37
================================================================================
Input images : 256
Margin limit : 0.005
Neighbor logic : +1,+2 -> -1,-2
Neighbor match : TOP-1 of neighbor == TOP-2 of current

================================================================================
RESULT
================================================================================
Total images:        256
Margin < 0.005:      5
Changed by neighbors:       3

CHANGED
--------------------------------------------------------------------------------
img_114.JPG: 84 -> 87 (second=87, margin=0.004842, FORWARD_SUPPORT_TOP2)
img_115.JPG: 87 -> 84 (second=84, margin=0.000813, FORWARD_SUPPORT_TOP2)
img_119.JPG: 87 -> 84 (second=84, margin=0.000904, FORWARD_SUPPORT_TOP2)

DISTRIBUTION
--------------------------------------------------------------------------------
78         20
79          8
80          8
81         16
82          9
83         17
84          9
85         17
86         15
87         19
88         15
89         21
90          3
91         12
92         14
93         12
94         24
95         17
--------------------------------------------------------------------------------
TOTAL         256

OUTPUT:
  sorted : /home/alexice/projects/scene_fingerprint_mvp_v02/output/neighbor_v37/sorted
  report : /home/alexice/projects/scene_fingerprint_mvp_v02/output/neighbor_v37/neighbor_decision.csv
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:54:10

Да. **V37 уже работает по той логике, которую мы хотели для реальных `img_000...`**.

Но по результату видно важный момент: из 5 сомнительных кадров алгоритм изменил только 3:

- `img_114`: **84 → 87**
- `img_115`: **87 → 84**
- `img_119`: **87 → 84**

И это выглядит логично для участка **84 ↔ 87**: алгоритм использовал соседние фотографии, где второй кандидат текущего кадра подтверждался как TOP-1 у следующих кадров.

При этом есть нюанс: **V37 пока смотрит только вперёд, если вперёд есть поддержка**. Наша исходная логика была чуть более строгая:

1. Есть сомнение → смотрим `+1`, `+2`.
2. Если оба/один из них подтверждают **кандидата №2** → меняем.
3. Если впереди конфликт → смотрим `-1`, `-2`.
4. Если впереди ничего убедительного → используем предыдущие.
5. Если и там ничего → оставляем V33.

То есть сейчас я бы **не стал сразу считать V37 финальным алгоритмом**. Надо сделать ещё одну проверку — посмотреть, **какие именно 5 кадров имеют margin < 0.005**, и что происходит у них с соседями.

Дай команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== V37 UNCERTAIN ==="

awk -F',' 'NR==1 || $6 < 0.005 {print}' \
  output/neighbor_v37/neighbor_decision.csv
```

А затем:

```bash
echo
echo "=== V37 CHANGED ==="

grep -v '^index' output/neighbor_v37/neighbor_decision.csv | \
awk -F',' '$7 != "V33" {print}'
```

**Особенно интересуют 2 оставшихся сомнительных кадра**, которые V37 не изменил. Если там соседняя последовательность действительно подтверждает второй кандидат, поправим V38.

И ещё: **результат 256 фотографий очень хороший для теста** — V37 не начал массово «перетаскивать» правильные результаты, а вмешался только в 3 действительно пограничных случая. Это именно то поведение, которое нам сейчас нужно.

---

### 👤 **User** — 2026-08-15 14:54:41

int_mvp_v02

echo "=== V37 UNCERTAIN ==="

awk -F',' 'NR==1 || $6 < 0.005 {print}' \
  output/neighbor_v37/neighbor_decision.csv
=== V37 UNCERTAIN ===
index,image,v33,second,final,margin,reason,forward_support,backward_support,forward_neighbors,backward_neighbors
114,img_114.JPG,84,87,87,0.004841757416725212,FORWARD_SUPPORT_TOP2,1,,+1:img_115.JPG=87; +2:img_116.JPG=84,
115,img_115.JPG,87,84,84,0.0008131492137909424,FORWARD_SUPPORT_TOP2,"1,2",,+1:img_116.JPG=84; +2:img_117.JPG=84,
119,img_119.JPG,87,84,84,0.0009040278196335017,FORWARD_SUPPORT_TOP2,"1,2",,+1:img_120.JPG=84; +2:img_121.JPG=84,
122,img_122.JPG,84,87,84,0.0029696345329284224,NO_NEIGHBOR_SUPPORT,,,+1:img_123.JPG=88; +2:img_124.JPG=88,-1:img_121.JPG=84; -2:img_120.JPG=84
214,img_214.JPG,89,88,89,0.004967231154441976,NO_NEIGHBOR_SUPPORT,,,+1:img_215.JPG=91; +2:img_216.JPG=91,-1:img_213.JPG=86; -2:img_212.JPG=94
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=== V37 CHANGED ==="

grep -v '^index' output/neighbor_v37/neighbor_decision.csv | \
awk -F',' '$7 != "V33" {print}'

=== V37 CHANGED ===
114,img_114.JPG,84,87,87,0.004841757416725212,FORWARD_SUPPORT_TOP2,1,,+1:img_115.JPG=87; +2:img_116.JPG=84,
115,img_115.JPG,87,84,84,0.0008131492137909424,FORWARD_SUPPORT_TOP2,"1,2",,+1:img_116.JPG=84; +2:img_117.JPG=84,
119,img_119.JPG,87,84,84,0.0009040278196335017,FORWARD_SUPPORT_TOP2,"1,2",,+1:img_120.JPG=84; +2:img_121.JPG=84,
122,img_122.JPG,84,87,84,0.0029696345329284224,NO_NEIGHBOR_SUPPORT,,,+1:img_123.JPG=88; +2:img_124.JPG=88,-1:img_121.JPG=84; -2:img_120.JPG=84
214,img_214.JPG,89,88,89,0.004967231154441976,NO_NEIGHBOR_SUPPORT,,,+1:img_215.JPG=91; +2:img_216.JPG=91,-1:img_213.JPG=86; -2:img_212.JPG=94
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 14:54:42

Да. Здесь уже видно важную вещь: **V37 работает по нужной логике, но его нельзя пока считать улучшением точности**.

Что получилось:

- Неуверенных кадров: **5 из 256**.
- Из них V37 изменил **3**:
  - `img_114`: `84 → 87`
  - `img_115`: `87 → 84`
  - `img_119`: `87 → 84`
- `img_122`: оставил `84` — и это логично, потому что соседей в пользу `87` нет.
- `img_214`: оставил `89` — тоже правильно по текущему правилу.

### Но есть проблема в `114–119`

Посмотрим последовательность:

```text
112  84
113  87
114  84 → 87
115  87 → 84
116  84
117  84
118  84
119  87 → 84
120  84
121  84
122  84
```

Здесь возникает интересный эффект: **один ошибочный/пограничный кадр может подтянуть соседний**, а потом уже сам изменённый результат начинает влиять на нашу интерпретацию последовательности.

То есть нам теперь лучше перейти от правила:

> «посмотри на TOP-1 двух соседей»

к правилу:

> **«определи локальную последовательность адреса»**.

И это как раз соответствует реальной съемке: камера едет вдоль маршрута, поэтому несколько последовательных `img_xxx` обычно относятся к одному адресу.

### Я бы сделал V38 так

Для каждого сомнительного кадра:

1. Берём `TOP-1` текущего кадра.
2. Берём `TOP-2` текущего кадра как альтернативу.
3. Смотрим `+1`, `+2`.
4. Если там устойчиво появляется `TOP-2` — считаем альтернативу подтверждённой.
5. Если впереди нет подтверждения — смотрим `-1`, `-2`.
6. **При этом соседи должны оцениваться по исходному V33, а не по уже изменённому V38 результату.**
7. Если впереди и сзади конфликт — **ничего не меняем**.
8. Если соседняя группа состоит из 2+ кадров одного адреса — это сильнее одиночного совпадения.

И главное: **не менять сразу несколько соседних кадров цепочкой**.

Сейчас V37 фактически начал обнаруживать переход между `84` и `87`, но нам надо научиться отличать:

```text
84 84 84 87 84 84 84
```

от

```text
84 84 84 87 87 87 84
```

Во втором случае `87` — почти наверняка реальная группа.

---

Следующий шаг я предлагаю сделать очень конкретным: **V38 не просто сортирует, а строит локальные группы последовательных TOP-1** и показывает нам все места, где происходит конфликт.

Запускаем анализ для `img_000...img_255` и получаем что-то вроде:

```text
112 84
113 87
114 84
115 87
116 84
117 84
...
```

с пометкой:

```text
CONFLICT ZONE 112-122
candidate: 84
candidate: 87
```

После этого уже решим правило именно для таких зон. Это будет намного надёжнее, чем бесконечно подкручивать `MARGIN_LIMIT`.

---

### 👤 **User** — 2026-08-15 14:55:37

да

---

### 🤖 **Assistant** — 2026-08-15 14:55:38

Да. Тогда сейчас **не меняем сортировку**. Сначала строим V38 как диагностический режим: он найдёт локальные зоны, где TOP-1 меняется между адресами, и покажет контекст ±2 кадра.

Создай:

```bash id="p6f4xk"
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/analyze_sequence_v38.py <<'PY'
#!/usr/bin/env python3

import csv
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPORT = PROJECT / "output/neighbor_v37/neighbor_decision.csv"

with open(REPORT, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

# Реальный порядок img_000, img_001...
rows.sort(key=lambda r: int(
    "".join(c for c in Path(r["image"]).stem if c.isdigit())
))

print("=" * 80)
print("SEQUENCE ANALYSIS V38")
print("=" * 80)
print(f"Images: {len(rows)}")
print()

# ------------------------------------------------------------
# Ищем места, где TOP-1 меняется между соседними кадрами
# ------------------------------------------------------------

changes = []

for i in range(1, len(rows)):
    prev = int(rows[i - 1]["v33"])
    cur = int(rows[i]["v33"])

    if prev != cur:
        changes.append(i)

print("=" * 80)
print("ADDRESS TRANSITIONS")
print("=" * 80)

if not changes:
    print("No transitions.")
else:
    for i in changes:
        print()
        print(
            f"TRANSITION BEFORE {rows[i]['image']}: "
            f"{rows[i-1]['v33']} -> {rows[i]['v33']}"
        )

        start = max(0, i - 3)
        end = min(len(rows), i + 4)

        for j in range(start, end):
            r = rows[j]

            marker = "   "

            if j == i:
                marker = ">>>"
            elif j == i - 1:
                marker = "---"

            print(
                f"{marker} "
                f"{j:3d} "
                f"{r['image']:15s} "
                f"TOP1={r['v33']:>2} "
                f"TOP2={r['second']:>2} "
                f"margin={float(r['margin']):.6f}"
            )

# ------------------------------------------------------------
# Сомнительные кадры
# ------------------------------------------------------------

print()
print("=" * 80)
print("UNCERTAIN ZONES")
print("=" * 80)

uncertain = [
    i for i, r in enumerate(rows)
    if float(r["margin"]) < 0.005
]

if not uncertain:
    print("No uncertain images.")
else:

    printed_zones = set()

    for i in uncertain:

        # Группируем близкие сомнительные кадры
        zone_start = max(0, i - 2)
        zone_end = min(len(rows) - 1, i + 2)

        key = (zone_start, zone_end)

        if key in printed_zones:
            continue

        printed_zones.add(key)

        print()
        print(
            f"ZONE around {rows[i]['image']} "
            f"(index {i})"
        )
        print("-" * 80)

        start = max(0, i - 4)
        end = min(len(rows), i + 5)

        for j in range(start, end):
            r = rows[j]

            mark = "   "

            if j == i:
                mark = ">>>"

            print(
                f"{mark} "
                f"{j:3d} "
                f"{r['image']:15s} "
                f"TOP1={r['v33']:>2} "
                f"TOP2={r['second']:>2} "
                f"margin={float(r['margin']):.6f}"
            )

# ------------------------------------------------------------
# Серии одинакового TOP-1
# ------------------------------------------------------------

print()
print("=" * 80)
print("SEQUENTIAL GROUPS")
print("=" * 80)

groups = []

start = 0
current = int(rows[0]["v33"])

for i in range(1, len(rows)):

    value = int(rows[i]["v33"])

    if value != current:

        groups.append((start, i - 1, current))
        start = i
        current = value

groups.append((start, len(rows) - 1, current))

for start, end, fp in groups:

    size = end - start + 1

    # Показываем короткие группы — именно они наиболее интересны
    if size <= 3:

        print(
            f"{start:3d}-{end:3d} "
            f"size={size} "
            f"FP={fp}"
        )

        for i in range(start, end + 1):
            r = rows[i]

            print(
                f"       {r['image']:15s} "
                f"TOP1={r['v33']} "
                f"TOP2={r['second']} "
                f"margin={float(r['margin']):.6f}"
            )

print()
print("=" * 80)
print("DONE")
print("=" * 80)
PY

uv run python -m py_compile scripts/analyze_sequence_v38.py

echo "STATUS=$?"
```

Должно быть:

```text
STATUS=0
```

После этого:

```bash id="d6j7r4"
uv run python -u scripts/analyze_sequence_v38.py
```

### Что нас сейчас особенно интересует

В выводе появятся переходы примерно такого вида:

```text
TRANSITION BEFORE img_114.JPG: 87 -> 84

112  TOP1=84
113  TOP1=87
114  TOP1=84
115  TOP1=87
116  TOP1=84
117  TOP1=84
118  TOP1=84
119  TOP1=87
120  TOP1=84
```

И мы уже увидим **реальную структуру последовательности**, а не только отдельные сомнительные фотографии.

После этого я предложу V38-логику, которая будет работать именно с **группами кадров**, а не просто с соседним `TOP-1`. Это должно быть заметно устойчивее для реальной съемки `img_000...img_999`.

---

### 👤 **User** — 2026-08-15 14:56:24

================================================================================
ADDRESS TRANSITIONS
================================================================================

TRANSITION BEFORE img_007.JPG: 85 -> 89
      4 img_004.JPG     TOP1=85 TOP2=91 margin=0.059694
      5 img_005.JPG     TOP1=85 TOP2=91 margin=0.062207
---   6 img_006.JPG     TOP1=85 TOP2=93 margin=0.078912
>>>   7 img_007.JPG     TOP1=89 TOP2=85 margin=0.010600
      8 img_008.JPG     TOP1=85 TOP2=94 margin=0.034371
      9 img_009.JPG     TOP1=85 TOP2=92 margin=0.088215
     10 img_010.JPG     TOP1=85 TOP2=91 margin=0.084300

TRANSITION BEFORE img_008.JPG: 89 -> 85
      5 img_005.JPG     TOP1=85 TOP2=91 margin=0.062207
      6 img_006.JPG     TOP1=85 TOP2=93 margin=0.078912
---   7 img_007.JPG     TOP1=89 TOP2=85 margin=0.010600
>>>   8 img_008.JPG     TOP1=85 TOP2=94 margin=0.034371
      9 img_009.JPG     TOP1=85 TOP2=92 margin=0.088215
     10 img_010.JPG     TOP1=85 TOP2=91 margin=0.084300
     11 img_011.JPG     TOP1=85 TOP2=91 margin=0.087674

TRANSITION BEFORE img_018.JPG: 85 -> 95
     15 img_015.JPG     TOP1=85 TOP2=91 margin=0.083659
     16 img_016.JPG     TOP1=85 TOP2=91 margin=0.084794
---  17 img_017.JPG     TOP1=85 TOP2=93 margin=0.069079
>>>  18 img_018.JPG     TOP1=95 TOP2=78 margin=0.056516
     19 img_019.JPG     TOP1=95 TOP2=94 margin=0.056369
     20 img_020.JPG     TOP1=95 TOP2=94 margin=0.026987
     21 img_021.JPG     TOP1=95 TOP2=94 margin=0.054354

TRANSITION BEFORE img_034.JPG: 95 -> 82
     31 img_031.JPG     TOP1=95 TOP2=94 margin=0.032756
     32 img_032.JPG     TOP1=95 TOP2=94 margin=0.048405
---  33 img_033.JPG     TOP1=95 TOP2=94 margin=0.066634
>>>  34 img_034.JPG     TOP1=82 TOP2=86 margin=0.089365
     35 img_035.JPG     TOP1=82 TOP2=80 margin=0.124883
     36 img_036.JPG     TOP1=82 TOP2=86 margin=0.123170
     37 img_037.JPG     TOP1=82 TOP2=86 margin=0.121100

TRANSITION BEFORE img_043.JPG: 82 -> 92
     40 img_040.JPG     TOP1=82 TOP2=86 margin=0.124007
     41 img_041.JPG     TOP1=82 TOP2=80 margin=0.137992
---  42 img_042.JPG     TOP1=82 TOP2=86 margin=0.137090
>>>  43 img_043.JPG     TOP1=92 TOP2=93 margin=0.050515
     44 img_044.JPG     TOP1=92 TOP2=91 margin=0.047921
     45 img_045.JPG     TOP1=92 TOP2=83 margin=0.058778
     46 img_046.JPG     TOP1=92 TOP2=83 margin=0.037640

TRANSITION BEFORE img_048.JPG: 92 -> 89
     45 img_045.JPG     TOP1=92 TOP2=83 margin=0.058778
     46 img_046.JPG     TOP1=92 TOP2=83 margin=0.037640
---  47 img_047.JPG     TOP1=92 TOP2=83 margin=0.053973
>>>  48 img_048.JPG     TOP1=89 TOP2=92 margin=0.015479
     49 img_049.JPG     TOP1=92 TOP2=93 margin=0.058042
     50 img_050.JPG     TOP1=92 TOP2=86 margin=0.042846
     51 img_051.JPG     TOP1=92 TOP2=93 margin=0.054863

TRANSITION BEFORE img_049.JPG: 89 -> 92
     46 img_046.JPG     TOP1=92 TOP2=83 margin=0.037640
     47 img_047.JPG     TOP1=92 TOP2=83 margin=0.053973
---  48 img_048.JPG     TOP1=89 TOP2=92 margin=0.015479
>>>  49 img_049.JPG     TOP1=92 TOP2=93 margin=0.058042
     50 img_050.JPG     TOP1=92 TOP2=86 margin=0.042846
     51 img_051.JPG     TOP1=92 TOP2=93 margin=0.054863
     52 img_052.JPG     TOP1=92 TOP2=83 margin=0.044789

TRANSITION BEFORE img_057.JPG: 92 -> 89
     54 img_054.JPG     TOP1=92 TOP2=93 margin=0.045520
     55 img_055.JPG     TOP1=92 TOP2=83 margin=0.053832
---  56 img_056.JPG     TOP1=92 TOP2=93 margin=0.056275
>>>  57 img_057.JPG     TOP1=89 TOP2=92 margin=0.017843
     58 img_058.JPG     TOP1=92 TOP2=89 margin=0.026014
     59 img_059.jpg     TOP1=95 TOP2=92 margin=0.013838
     60 img_060.JPG     TOP1=81 TOP2=84 margin=0.051434

TRANSITION BEFORE img_058.JPG: 89 -> 92
     55 img_055.JPG     TOP1=92 TOP2=83 margin=0.053832
     56 img_056.JPG     TOP1=92 TOP2=93 margin=0.056275
---  57 img_057.JPG     TOP1=89 TOP2=92 margin=0.017843
>>>  58 img_058.JPG     TOP1=92 TOP2=89 margin=0.026014
     59 img_059.jpg     TOP1=95 TOP2=92 margin=0.013838
     60 img_060.JPG     TOP1=81 TOP2=84 margin=0.051434
     61 img_061.JPG     TOP1=81 TOP2=84 margin=0.066338

TRANSITION BEFORE img_059.jpg: 92 -> 95
     56 img_056.JPG     TOP1=92 TOP2=93 margin=0.056275
     57 img_057.JPG     TOP1=89 TOP2=92 margin=0.017843
---  58 img_058.JPG     TOP1=92 TOP2=89 margin=0.026014
>>>  59 img_059.jpg     TOP1=95 TOP2=92 margin=0.013838
     60 img_060.JPG     TOP1=81 TOP2=84 margin=0.051434
     61 img_061.JPG     TOP1=81 TOP2=84 margin=0.066338
     62 img_062.JPG     TOP1=81 TOP2=84 margin=0.066601

TRANSITION BEFORE img_060.JPG: 95 -> 81
     57 img_057.JPG     TOP1=89 TOP2=92 margin=0.017843
     58 img_058.JPG     TOP1=92 TOP2=89 margin=0.026014
---  59 img_059.jpg     TOP1=95 TOP2=92 margin=0.013838
>>>  60 img_060.JPG     TOP1=81 TOP2=84 margin=0.051434
     61 img_061.JPG     TOP1=81 TOP2=84 margin=0.066338
     62 img_062.JPG     TOP1=81 TOP2=84 margin=0.066601
     63 img_063.JPG     TOP1=81 TOP2=84 margin=0.061724

TRANSITION BEFORE img_076.JPG: 81 -> 78
     73 img_073.JPG     TOP1=81 TOP2=84 margin=0.067211
     74 img_074.JPG     TOP1=81 TOP2=84 margin=0.056680
---  75 img_075.JPG     TOP1=81 TOP2=84 margin=0.064310
>>>  76 img_076.JPG     TOP1=78 TOP2=91 margin=0.057279
     77 img_077.JPG     TOP1=78 TOP2=91 margin=0.049500
     78 img_078.JPG     TOP1=78 TOP2=91 margin=0.051671
     79 img_079.JPG     TOP1=78 TOP2=91 margin=0.065462

TRANSITION BEFORE img_096.jpg: 78 -> 80
     93 img_093.JPG     TOP1=78 TOP2=83 margin=0.055605
     94 img_094.JPG     TOP1=78 TOP2=95 margin=0.042113
---  95 img_095.JPG     TOP1=78 TOP2=92 margin=0.068437
>>>  96 img_096.jpg     TOP1=80 TOP2=82 margin=0.133340
     97 img_097.JPG     TOP1=80 TOP2=82 margin=0.144542
     98 img_098.JPG     TOP1=80 TOP2=79 margin=0.089391
     99 img_099.JPG     TOP1=80 TOP2=79 margin=0.068869

TRANSITION BEFORE img_104.JPG: 80 -> 79
    101 img_101.JPG     TOP1=80 TOP2=82 margin=0.090512
    102 img_102.JPG     TOP1=80 TOP2=91 margin=0.102333
--- 103 img_103.JPG     TOP1=80 TOP2=79 margin=0.060323
>>> 104 img_104.JPG     TOP1=79 TOP2=92 margin=0.055152
    105 img_105.JPG     TOP1=79 TOP2=92 margin=0.028497
    106 img_106.JPG     TOP1=79 TOP2=87 margin=0.075933
    107 img_107.JPG     TOP1=79 TOP2=87 margin=0.079427

TRANSITION BEFORE img_112.JPG: 79 -> 84
    109 img_109.JPG     TOP1=79 TOP2=92 margin=0.075887
    110 img_110.JPG     TOP1=79 TOP2=87 margin=0.099866
--- 111 img_111.JPG     TOP1=79 TOP2=87 margin=0.077723
>>> 112 img_112.JPG     TOP1=84 TOP2=87 margin=0.023270
    113 img_113.JPG     TOP1=87 TOP2=84 margin=0.005852
    114 img_114.JPG     TOP1=84 TOP2=87 margin=0.004842
    115 img_115.JPG     TOP1=87 TOP2=84 margin=0.000813

TRANSITION BEFORE img_113.JPG: 84 -> 87
    110 img_110.JPG     TOP1=79 TOP2=87 margin=0.099866
    111 img_111.JPG     TOP1=79 TOP2=87 margin=0.077723
--- 112 img_112.JPG     TOP1=84 TOP2=87 margin=0.023270
>>> 113 img_113.JPG     TOP1=87 TOP2=84 margin=0.005852
    114 img_114.JPG     TOP1=84 TOP2=87 margin=0.004842
    115 img_115.JPG     TOP1=87 TOP2=84 margin=0.000813
    116 img_116.JPG     TOP1=84 TOP2=87 margin=0.006821

TRANSITION BEFORE img_114.JPG: 87 -> 84
    111 img_111.JPG     TOP1=79 TOP2=87 margin=0.077723
    112 img_112.JPG     TOP1=84 TOP2=87 margin=0.023270
--- 113 img_113.JPG     TOP1=87 TOP2=84 margin=0.005852
>>> 114 img_114.JPG     TOP1=84 TOP2=87 margin=0.004842
    115 img_115.JPG     TOP1=87 TOP2=84 margin=0.000813
    116 img_116.JPG     TOP1=84 TOP2=87 margin=0.006821
    117 img_117.JPG     TOP1=84 TOP2=87 margin=0.012005

TRANSITION BEFORE img_115.JPG: 84 -> 87
    112 img_112.JPG     TOP1=84 TOP2=87 margin=0.023270
    113 img_113.JPG     TOP1=87 TOP2=84 margin=0.005852
--- 114 img_114.JPG     TOP1=84 TOP2=87 margin=0.004842
>>> 115 img_115.JPG     TOP1=87 TOP2=84 margin=0.000813
    116 img_116.JPG     TOP1=84 TOP2=87 margin=0.006821
    117 img_117.JPG     TOP1=84 TOP2=87 margin=0.012005
    118 img_118.JPG     TOP1=84 TOP2=87 margin=0.013808

TRANSITION BEFORE img_116.JPG: 87 -> 84
    113 img_113.JPG     TOP1=87 TOP2=84 margin=0.005852
    114 img_114.JPG     TOP1=84 TOP2=87 margin=0.004842
--- 115 img_115.JPG     TOP1=87 TOP2=84 margin=0.000813
>>> 116 img_116.JPG     TOP1=84 TOP2=87 margin=0.006821
    117 img_117.JPG     TOP1=84 TOP2=87 margin=0.012005
    118 img_118.JPG     TOP1=84 TOP2=87 margin=0.013808
    119 img_119.JPG     TOP1=87 TOP2=84 margin=0.000904

TRANSITION BEFORE img_119.JPG: 84 -> 87
    116 img_116.JPG     TOP1=84 TOP2=87 margin=0.006821
    117 img_117.JPG     TOP1=84 TOP2=87 margin=0.012005
--- 118 img_118.JPG     TOP1=84 TOP2=87 margin=0.013808
>>> 119 img_119.JPG     TOP1=87 TOP2=84 margin=0.000904
    120 img_120.JPG     TOP1=84 TOP2=87 margin=0.022544
    121 img_121.JPG     TOP1=84 TOP2=87 margin=0.008946
    122 img_122.JPG     TOP1=84 TOP2=87 margin=0.002970

TRANSITION BEFORE img_120.JPG: 87 -> 84
    117 img_117.JPG     TOP1=84 TOP2=87 margin=0.012005
    118 img_118.JPG     TOP1=84 TOP2=87 margin=0.013808
--- 119 img_119.JPG     TOP1=87 TOP2=84 margin=0.000904
>>> 120 img_120.JPG     TOP1=84 TOP2=87 margin=0.022544
    121 img_121.JPG     TOP1=84 TOP2=87 margin=0.008946
    122 img_122.JPG     TOP1=84 TOP2=87 margin=0.002970
    123 img_123.JPG     TOP1=88 TOP2=92 margin=0.157716

TRANSITION BEFORE img_123.JPG: 84 -> 88
    120 img_120.JPG     TOP1=84 TOP2=87 margin=0.022544
    121 img_121.JPG     TOP1=84 TOP2=87 margin=0.008946
--- 122 img_122.JPG     TOP1=84 TOP2=87 margin=0.002970
>>> 123 img_123.JPG     TOP1=88 TOP2=92 margin=0.157716
    124 img_124.JPG     TOP1=88 TOP2=92 margin=0.118758
    125 img_125.JPG     TOP1=88 TOP2=87 margin=0.102999
    126 img_126.JPG     TOP1=88 TOP2=92 margin=0.167498

TRANSITION BEFORE img_138.JPG: 88 -> 89
    135 img_135.JPG     TOP1=88 TOP2=92 margin=0.185633
    136 img_136.JPG     TOP1=88 TOP2=89 margin=0.066637
--- 137 img_137.JPG     TOP1=88 TOP2=92 margin=0.110203
>>> 138 img_138.JPG     TOP1=89 TOP2=92 margin=0.076642
    139 img_139.JPG     TOP1=89 TOP2=80 margin=0.125486
    140 img_140.JPG     TOP1=89 TOP2=80 margin=0.100586
    141 img_141.JPG     TOP1=89 TOP2=94 margin=0.024926

TRANSITION BEFORE img_147.JPG: 89 -> 94
    144 img_144.JPG     TOP1=89 TOP2=93 margin=0.110560
    145 img_145.JPG     TOP1=89 TOP2=93 margin=0.103956
--- 146 img_146.JPG     TOP1=89 TOP2=92 margin=0.042704
>>> 147 img_147.JPG     TOP1=94 TOP2=89 margin=0.007643
    148 img_148.JPG     TOP1=89 TOP2=92 margin=0.067138
    149 img_149.JPG     TOP1=89 TOP2=92 margin=0.066388
    150 img_150.JPG     TOP1=89 TOP2=86 margin=0.081856

TRANSITION BEFORE img_148.JPG: 94 -> 89
    145 img_145.JPG     TOP1=89 TOP2=93 margin=0.103956
    146 img_146.JPG     TOP1=89 TOP2=92 margin=0.042704
--- 147 img_147.JPG     TOP1=94 TOP2=89 margin=0.007643
>>> 148 img_148.JPG     TOP1=89 TOP2=92 margin=0.067138
    149 img_149.JPG     TOP1=89 TOP2=92 margin=0.066388
    150 img_150.JPG     TOP1=89 TOP2=86 margin=0.081856
    151 img_151.JPG     TOP1=89 TOP2=94 margin=0.083818

TRANSITION BEFORE img_154.JPG: 89 -> 90
    151 img_151.JPG     TOP1=89 TOP2=94 margin=0.083818
    152 img_152.JPG     TOP1=89 TOP2=93 margin=0.102016
--- 153 img_153.JPG     TOP1=89 TOP2=92 margin=0.055820
>>> 154 img_154.JPG     TOP1=90 TOP2=89 margin=0.103489
    155 img_155.JPG     TOP1=90 TOP2=89 margin=0.026188
    156 img_156.JPG     TOP1=89 TOP2=90 margin=0.021352
    157 img_157.JPG     TOP1=90 TOP2=89 margin=0.022768

TRANSITION BEFORE img_156.JPG: 90 -> 89
    153 img_153.JPG     TOP1=89 TOP2=92 margin=0.055820
    154 img_154.JPG     TOP1=90 TOP2=89 margin=0.103489
--- 155 img_155.JPG     TOP1=90 TOP2=89 margin=0.026188
>>> 156 img_156.JPG     TOP1=89 TOP2=90 margin=0.021352
    157 img_157.JPG     TOP1=90 TOP2=89 margin=0.022768
    158 img_158.JPG     TOP1=89 TOP2=90 margin=0.026167
    159 img_159.JPG     TOP1=86 TOP2=82 margin=0.094095

TRANSITION BEFORE img_157.JPG: 89 -> 90
    154 img_154.JPG     TOP1=90 TOP2=89 margin=0.103489
    155 img_155.JPG     TOP1=90 TOP2=89 margin=0.026188
--- 156 img_156.JPG     TOP1=89 TOP2=90 margin=0.021352
>>> 157 img_157.JPG     TOP1=90 TOP2=89 margin=0.022768
    158 img_158.JPG     TOP1=89 TOP2=90 margin=0.026167
    159 img_159.JPG     TOP1=86 TOP2=82 margin=0.094095
    160 img_160.JPG     TOP1=86 TOP2=92 margin=0.086074

TRANSITION BEFORE img_158.JPG: 90 -> 89
    155 img_155.JPG     TOP1=90 TOP2=89 margin=0.026188
    156 img_156.JPG     TOP1=89 TOP2=90 margin=0.021352
--- 157 img_157.JPG     TOP1=90 TOP2=89 margin=0.022768
>>> 158 img_158.JPG     TOP1=89 TOP2=90 margin=0.026167
    159 img_159.JPG     TOP1=86 TOP2=82 margin=0.094095
    160 img_160.JPG     TOP1=86 TOP2=92 margin=0.086074
    161 img_161.JPG     TOP1=86 TOP2=94 margin=0.075611

TRANSITION BEFORE img_159.JPG: 89 -> 86
    156 img_156.JPG     TOP1=89 TOP2=90 margin=0.021352
    157 img_157.JPG     TOP1=90 TOP2=89 margin=0.022768
--- 158 img_158.JPG     TOP1=89 TOP2=90 margin=0.026167
>>> 159 img_159.JPG     TOP1=86 TOP2=82 margin=0.094095
    160 img_160.JPG     TOP1=86 TOP2=92 margin=0.086074
    161 img_161.JPG     TOP1=86 TOP2=94 margin=0.075611
    162 img_162.JPG     TOP1=86 TOP2=95 margin=0.079658

TRANSITION BEFORE img_173.JPG: 86 -> 83
    170 img_170.JPG     TOP1=86 TOP2=78 margin=0.095036
    171 img_171.JPG     TOP1=86 TOP2=92 margin=0.097614
--- 172 img_172.JPG     TOP1=86 TOP2=92 margin=0.079168
>>> 173 img_173.JPG     TOP1=83 TOP2=91 margin=0.040983
    174 img_174.JPG     TOP1=83 TOP2=91 margin=0.031771
    175 img_175.JPG     TOP1=83 TOP2=91 margin=0.033023
    176 img_176.JPG     TOP1=83 TOP2=91 margin=0.030709

TRANSITION BEFORE img_190.JPG: 83 -> 94
    187 img_187.JPG     TOP1=83 TOP2=93 margin=0.035307
    188 img_188.JPG     TOP1=83 TOP2=93 margin=0.038667
--- 189 img_189.JPG     TOP1=83 TOP2=91 margin=0.049504
>>> 190 img_190.JPG     TOP1=94 TOP2=93 margin=0.011105
    191 img_191.JPG     TOP1=94 TOP2=95 margin=0.061824
    192 img_192.JPG     TOP1=94 TOP2=91 margin=0.084103
    193 img_193.JPG     TOP1=94 TOP2=85 margin=0.065152

TRANSITION BEFORE img_213.JPG: 94 -> 86
    210 img_210.JPG     TOP1=94 TOP2=91 margin=0.045623
    211 img_211.JPG     TOP1=94 TOP2=92 margin=0.015100
--- 212 img_212.JPG     TOP1=94 TOP2=92 margin=0.020842
>>> 213 img_213.JPG     TOP1=86 TOP2=89 margin=0.006465
    214 img_214.JPG     TOP1=89 TOP2=88 margin=0.004967
    215 img_215.JPG     TOP1=91 TOP2=92 margin=0.046349
    216 img_216.JPG     TOP1=91 TOP2=92 margin=0.051920

TRANSITION BEFORE img_214.JPG: 86 -> 89
    211 img_211.JPG     TOP1=94 TOP2=92 margin=0.015100
    212 img_212.JPG     TOP1=94 TOP2=92 margin=0.020842
--- 213 img_213.JPG     TOP1=86 TOP2=89 margin=0.006465
>>> 214 img_214.JPG     TOP1=89 TOP2=88 margin=0.004967
    215 img_215.JPG     TOP1=91 TOP2=92 margin=0.046349
    216 img_216.JPG     TOP1=91 TOP2=92 margin=0.051920
    217 img_217.JPG     TOP1=91 TOP2=94 margin=0.047678

TRANSITION BEFORE img_215.JPG: 89 -> 91
    212 img_212.JPG     TOP1=94 TOP2=92 margin=0.020842
    213 img_213.JPG     TOP1=86 TOP2=89 margin=0.006465
--- 214 img_214.JPG     TOP1=89 TOP2=88 margin=0.004967
>>> 215 img_215.JPG     TOP1=91 TOP2=92 margin=0.046349
    216 img_216.JPG     TOP1=91 TOP2=92 margin=0.051920
    217 img_217.JPG     TOP1=91 TOP2=94 margin=0.047678
    218 img_218.JPG     TOP1=91 TOP2=93 margin=0.009692

TRANSITION BEFORE img_227.JPG: 91 -> 93
    224 img_224.JPG     TOP1=91 TOP2=85 margin=0.035989
    225 img_225.JPG     TOP1=91 TOP2=93 margin=0.040446
--- 226 img_226.JPG     TOP1=91 TOP2=93 margin=0.017470
>>> 227 img_227.JPG     TOP1=93 TOP2=91 margin=0.051985
    228 img_228.JPG     TOP1=93 TOP2=91 margin=0.046309
    229 img_229.JPG     TOP1=93 TOP2=92 margin=0.036054
    230 img_230.JPG     TOP1=93 TOP2=91 margin=0.049084

TRANSITION BEFORE img_239.JPG: 93 -> 87
    236 img_236.JPG     TOP1=93 TOP2=95 margin=0.019226
    237 img_237.JPG     TOP1=93 TOP2=92 margin=0.036748
--- 238 img_238.JPG     TOP1=93 TOP2=92 margin=0.030524
>>> 239 img_239.JPG     TOP1=87 TOP2=85 margin=0.077950
    240 img_240.JPG     TOP1=87 TOP2=85 margin=0.066717
    241 img_241.JPG     TOP1=87 TOP2=85 margin=0.068609
    242 img_242.JPG     TOP1=87 TOP2=79 margin=0.072898

================================================================================
UNCERTAIN ZONES
================================================================================

ZONE around img_114.JPG (index 114)
--------------------------------------------------------------------------------
    110 img_110.JPG     TOP1=79 TOP2=87 margin=0.099866
    111 img_111.JPG     TOP1=79 TOP2=87 margin=0.077723
    112 img_112.JPG     TOP1=84 TOP2=87 margin=0.023270
    113 img_113.JPG     TOP1=87 TOP2=84 margin=0.005852
>>> 114 img_114.JPG     TOP1=84 TOP2=87 margin=0.004842
    115 img_115.JPG     TOP1=87 TOP2=84 margin=0.000813
    116 img_116.JPG     TOP1=84 TOP2=87 margin=0.006821
    117 img_117.JPG     TOP1=84 TOP2=87 margin=0.012005
    118 img_118.JPG     TOP1=84 TOP2=87 margin=0.013808

ZONE around img_115.JPG (index 115)
--------------------------------------------------------------------------------
    111 img_111.JPG     TOP1=79 TOP2=87 margin=0.077723
    112 img_112.JPG     TOP1=84 TOP2=87 margin=0.023270
    113 img_113.JPG     TOP1=87 TOP2=84 margin=0.005852
    114 img_114.JPG     TOP1=84 TOP2=87 margin=0.004842
>>> 115 img_115.JPG     TOP1=87 TOP2=84 margin=0.000813
    116 img_116.JPG     TOP1=84 TOP2=87 margin=0.006821
    117 img_117.JPG     TOP1=84 TOP2=87 margin=0.012005
    118 img_118.JPG     TOP1=84 TOP2=87 margin=0.013808
    119 img_119.JPG     TOP1=87 TOP2=84 margin=0.000904

ZONE around img_119.JPG (index 119)
--------------------------------------------------------------------------------
    115 img_115.JPG     TOP1=87 TOP2=84 margin=0.000813
    116 img_116.JPG     TOP1=84 TOP2=87 margin=0.006821
    117 img_117.JPG     TOP1=84 TOP2=87 margin=0.012005
    118 img_118.JPG     TOP1=84 TOP2=87 margin=0.013808
>>> 119 img_119.JPG     TOP1=87 TOP2=84 margin=0.000904
    120 img_120.JPG     TOP1=84 TOP2=87 margin=0.022544
    121 img_121.JPG     TOP1=84 TOP2=87 margin=0.008946
    122 img_122.JPG     TOP1=84 TOP2=87 margin=0.002970
    123 img_123.JPG     TOP1=88 TOP2=92 margin=0.157716

ZONE around img_122.JPG (index 122)
--------------------------------------------------------------------------------
    118 img_118.JPG     TOP1=84 TOP2=87 margin=0.013808
    119 img_119.JPG     TOP1=87 TOP2=84 margin=0.000904
    120 img_120.JPG     TOP1=84 TOP2=87 margin=0.022544
    121 img_121.JPG     TOP1=84 TOP2=87 margin=0.008946
>>> 122 img_122.JPG     TOP1=84 TOP2=87 margin=0.002970
    123 img_123.JPG     TOP1=88 TOP2=92 margin=0.157716
    124 img_124.JPG     TOP1=88 TOP2=92 margin=0.118758
    125 img_125.JPG     TOP1=88 TOP2=87 margin=0.102999
    126 img_126.JPG     TOP1=88 TOP2=92 margin=0.167498

ZONE around img_214.JPG (index 214)
--------------------------------------------------------------------------------
    210 img_210.JPG     TOP1=94 TOP2=91 margin=0.045623
    211 img_211.JPG     TOP1=94 TOP2=92 margin=0.015100
    212 img_212.JPG     TOP1=94 TOP2=92 margin=0.020842
    213 img_213.JPG     TOP1=86 TOP2=89 margin=0.006465
>>> 214 img_214.JPG     TOP1=89 TOP2=88 margin=0.004967
    215 img_215.JPG     TOP1=91 TOP2=92 margin=0.046349
    216 img_216.JPG     TOP1=91 TOP2=92 margin=0.051920
    217 img_217.JPG     TOP1=91 TOP2=94 margin=0.047678
    218 img_218.JPG     TOP1=91 TOP2=93 margin=0.009692

================================================================================
SEQUENTIAL GROUPS
================================================================================
  7-  7 size=1 FP=89
       img_007.JPG     TOP1=89 TOP2=85 margin=0.010600
 48- 48 size=1 FP=89
       img_048.JPG     TOP1=89 TOP2=92 margin=0.015479
 57- 57 size=1 FP=89
       img_057.JPG     TOP1=89 TOP2=92 margin=0.017843
 58- 58 size=1 FP=92
       img_058.JPG     TOP1=92 TOP2=89 margin=0.026014
 59- 59 size=1 FP=95
       img_059.jpg     TOP1=95 TOP2=92 margin=0.013838
112-112 size=1 FP=84
       img_112.JPG     TOP1=84 TOP2=87 margin=0.023270
113-113 size=1 FP=87
       img_113.JPG     TOP1=87 TOP2=84 margin=0.005852
114-114 size=1 FP=84
       img_114.JPG     TOP1=84 TOP2=87 margin=0.004842
115-115 size=1 FP=87
       img_115.JPG     TOP1=87 TOP2=84 margin=0.000813
116-118 size=3 FP=84
       img_116.JPG     TOP1=84 TOP2=87 margin=0.006821
       img_117.JPG     TOP1=84 TOP2=87 margin=0.012005
       img_118.JPG     TOP1=84 TOP2=87 margin=0.013808
119-119 size=1 FP=87
       img_119.JPG     TOP1=87 TOP2=84 margin=0.000904
120-122 size=3 FP=84
       img_120.JPG     TOP1=84 TOP2=87 margin=0.022544
       img_121.JPG     TOP1=84 TOP2=87 margin=0.008946
       img_122.JPG     TOP1=84 TOP2=87 margin=0.002970
147-147 size=1 FP=94
       img_147.JPG     TOP1=94 TOP2=89 margin=0.007643
154-155 size=2 FP=90
       img_154.JPG     TOP1=90 TOP2=89 margin=0.103489
       img_155.JPG     TOP1=90 TOP2=89 margin=0.026188
156-156 size=1 FP=89
       img_156.JPG     TOP1=89 TOP2=90 margin=0.021352
157-157 size=1 FP=90
       img_157.JPG     TOP1=90 TOP2=89 margin=0.022768
158-158 size=1 FP=89
       img_158.JPG     TOP1=89 TOP2=90 margin=0.026167
213-213 size=1 FP=86
       img_213.JPG     TOP1=86 TOP2=89 margin=0.006465
214-214 size=1 FP=89
       img_214.JPG     TOP1=89 TOP2=88 margin=0.004967

================================================================================
DONE

---

### 🤖 **Assistant** — 2026-08-15 14:56:26

Да. По этому анализу уже видно, что **V37 работает правильно как корректор локальных выбросов**, но есть важный момент: участок **112–122** нельзя решать простым правилом `TOP-1 соседа`.

### Что видно

Самый проблемный участок:

`112–122`

```text
112 → 84
113 → 87
114 → 84
115 → 87
116 → 84
117 → 84
118 → 84
119 → 87
120 → 84
121 → 84
122 → 84
```

При этом:

- 112: `84`, margin `0.023`
- 113: `87`, margin `0.00585`
- 114: `84`, margin `0.00484`
- 115: `87`, margin `0.00081`
- 116–118: уверенно `84`
- 119: `87`, margin `0.00090`
- 120–122: `84`

То есть **84 образует устойчивую группу**, а `87` появляется как одиночные выбросы.

Особенно показательно:

```text
113 = 87
114 = 84
115 = 87
116 = 84
117 = 84
118 = 84
119 = 87
120 = 84
121 = 84
122 = 84
```

Поэтому изменения V37:

```text
114: 84 → 87
115: 87 → 84
119: 87 → 84
```

я бы **не считал окончательным решением**.

### Главный вывод

Здесь гораздо лучше работает не только соседняя логика:

> «если сосед TOP-1 совпал с TOP-2 текущего — поменять»

а **анализ последовательного сегмента**.

Для этого участка система должна увидеть:

```text
112 84
113 87   ← сомнительно
114 84   ← сомнительно
115 87   ← сомнительно
116 84
117 84
118 84
119 87   ← сомнительно
120 84
121 84
122 84
```

и понять:

**доминирующий адрес = 84.**

Причём это очень хороший случай для автоматической коррекции: вокруг каждого спорного кадра есть сильная поддержка `84`.

---

### А вот остальные переходы выглядят нормально

Например:

```text
17 → 18
85 → 95
```

и после этого:

```text
18 95
19 95
20 95
21 95
```

Это настоящий переход.

То же самое:

```text
33 → 34
95 → 82
```

после него четыре кадра `82`.

И:

```text
42 → 43
82 → 92
```

после него стабильно `92`.

И:

```text
75 → 76
81 → 78
```

после него стабильно `78`.

То есть **не надо пытаться сглаживать все переходы**. Настоящие смены адреса у нас тоже присутствуют.

---

## Что я предлагаю сделать следующим шагом

Не менять сам V33.

Оставляем:

```text
V33
 ↓
TOP-1 / TOP-2
 ↓
V37 neighbor correction
```

и добавляем **V38 — segment consistency**.

Логика примерно такая:

```text
если TOP-1 текущего отличается
от доминирующего адреса в окне ±N,

и текущий имеет маленький margin,

и после него/до него есть устойчивый сегмент
доминирующего адреса,

→ считать текущий TOP-1 выбросом.
```

Для `114` получится:

```text
113 = 87
114 = 84
115 = 87
116 = 84
117 = 84
118 = 84
119 = 87
120 = 84
121 = 84
122 = 84
```

V38 должен определить:

```text
segment = 84
```

и дать:

```text
114 → 84
115 → 84
119 → 84
```

То есть **в данном случае V37 фактически оставит 114 ошибочным, а V38 его вернёт обратно**.

---

### Ещё один интересный участок — 213–218

```text
212 = 94
213 = 86  margin 0.00646
214 = 89  margin 0.00497
215 = 91
216 = 91
217 = 91
218 = 91
```

Здесь уже нельзя просто сказать, что `213` и `214` — выбросы.

Похоже на реальный переход:

```text
94
94
94
↓
86
89
↓
91
91
91
91
```

Но `213` и `214` очень сомнительные. **Их лучше оставить в uncertain, а не автоматически исправлять.**

И это очень важно для архитектуры LORA:

> **автоматически исправляем только очевидные выбросы; пограничные переходы отправляем в uncertain.**

---

### Я бы сейчас не трогал алгоритм распознавания V33

Он уже показывает достаточно хорошую картину.

Следующий эксперимент лучше сделать именно на логике постобработки:

```text
V33
  ↓
V37 neighbor
  ↓
V38 segment consistency
  ↓
final
  ├── sorted/
  └── uncertain/
```

Причём `uncertain` должен содержать не только маленький margin, но и **конфликт последовательности**.

Это даст нам гораздо более правильную систему:

**DINOv2 → V33 → локальная коррекция → анализ последовательности → адрес / uncertain.**

И главное — мы не будем портить реальные переходы между адресами.

---

### 👤 **User** — 2026-08-15 15:00:18

да. в принципе на постобработке можно определять граиницы серии  ивсе что между ними определять одним адреом

---

### 🤖 **Assistant** — 2026-08-15 15:00:19

Да. **Это, скорее всего, будет намного надёжнее V37.** Мы можем перейти от исправления отдельных фотографий к определению **серий фотографий**.

Идея:

```text
V33 TOP-1
   ↓
поиск границ серий
   ↓
каждая серия = один адрес
   ↓
внутри серии выбираем доминирующий адрес
   ↓
все фото серии получают этот адрес
```

Например, текущий участок:

```text
112  84
113  87
114  84
115  87
116  84
117  84
118  84
119  87
120  84
121  84
122  84
123  88
124  88
125  88
126  88
```

Алгоритм может увидеть:

```text
112 ───────────────── 122 | 123 ─────────
          ADDRESS 84      |      ADDRESS 88
```

и получить:

```text
112 → 84
113 → 84
114 → 84
115 → 84
116 → 84
117 → 84
118 → 84
119 → 84
120 → 84
121 → 84
122 → 84

123 → 88
124 → 88
125 → 88
126 → 88
```

### Причём границу надо искать не по одному кадру

Например:

```text
... 84 84 84 84 84
            87
              88 88 88 88
```

`87` не должен автоматически создавать новую серию.

А вот:

```text
84 84 84 84
87 87
88 88 88 88 88
```

уже может быть граница:

```text
84 | 87 | 88
```

Но если `87` имеет слабый confidence/margin, можем получить:

```text
84 | 88
```

То есть **граница определяется устойчивым изменением адреса**, а не единичным TOP-1.

### Я бы сделал V38 именно так

Вместо:

> «исправить сомнительную фотографию по соседу»

делаем:

> **«разбить последовательность фотографий на устойчивые серии»**.

Для каждой серии считаем:

- TOP-1 каждого кадра;
- TOP-2;
- margin;
- количество голосов каждого адреса;
- средний margin;
- длину серии;
- подтверждение адреса до границы;
- подтверждение адреса после границы.

И затем:

**1. Находим кандидатов на границы.**

**2. Проверяем границу с обеих сторон.**

**3. Определяем адрес всей серии.**

**4. Только после этого раскладываем фотографии.**

Это гораздо ближе к реальной природе данных: фотограф обычно снимает **один адрес серией**, потом переезжает к следующему.

Я бы сейчас **не писал сразу V38 вслепую**. Сначала сделаем диагностический скрипт, который покажет:

```text
SERIES 01: img_001–006 → 85
SERIES 02: img_007–007 → 89 ? 
SERIES 03: img_008–017 → 85
SERIES 04: img_018–033 → 95
...
```

и отдельно отметит:

```text
BOUNDARY 17 → 18
confidence: HIGH
```

или

```text
BOUNDARY 112 → 123
confidence: HIGH
```

Тогда мы **визуально проверим, правильно ли алгоритм видит границы**, и только после этого подключим автоматическое присвоение адреса всей серии. Это будет намного безопаснее.

---

### 👤 **User** — 2026-08-15 15:00:51

давай

---

### 🤖 **Assistant** — 2026-08-15 15:00:52

Да. Сделаем сначала **диагностический V38**, который ничего не меняет и не сортирует. Он только определяет серии по уже готовому `v33` и показывает предполагаемые границы.

Запусти из:

```bash
cd ~/projects/scene_fingerprint_mvp_v02
```

Сначала посмотрим, какие скрипты сейчас есть:

```bash
echo "=== SCRIPTS ==="
ls -lah scripts/

echo
echo "=== NEIGHBOR V37 ==="
sed -n '1,260p' scripts/sort_neighbor_v37.py
```

А затем я дам `v38`, который будет работать примерно так:

```text
V33
 ↓
последовательность TOP-1
 ↓
сглаживание одиночных выбросов
 ↓
поиск устойчивых границ
 ↓
SERIES
 ↓
доминирующий адрес серии
```

На первом этапе **никаких изменений файлов и сортировки не будет**.

Особенно хочу проверить на твоих данных следующие места:

```text
1–110
112–123      ← проблемная серия 84
123–147      ← переход 84 → 88 → 89
154–159      ← 89 ↔ 90
189–193      ← 83 → 94
210–218      ← 94 → 86 → 89 → 91
```

Если V38 правильно выделит эти серии, тогда уже сделаем второй этап:

```text
V38
 ↓
series_id
 ↓
series_address
 ↓
все фотографии серии → один адрес
 ↓
uncertain только для действительно неоднозначных границ
```

**Пришли вывод `sed` выше**, и я подстрою V38 точно под текущий формат твоего `v37`, чтобы не ломать существующий пайплайн.

---

### 👤 **User** — 2026-08-15 15:01:19

=== SCRIPTS ===
total 160K
drwxrwxr-x  3 alexice alexice 4.0K Aug 15 14:55 .
drwxrwxr-x 16 alexice alexice 4.0K Aug 15 03:54 ..
-rw-rw-r--  1 alexice alexice 4.1K Aug 15 14:55 analyze_sequence_v38.py
-rwxrwxr-x  1 alexice alexice 7.0K Aug 15 02:20 benchmark_test_v1.py
-rwxrwxr-x  1 alexice alexice  12K Aug 15 01:55 make_subfingerprints.py
-rwxrwxr-x  1 alexice alexice  11K Aug 15 01:59 make_subfingerprints_v2.py
drwxrwxr-x  2 alexice alexice 4.0K Aug 15 14:55 __pycache__
-rwxrwxr-x  1 alexice alexice 4.3K Aug 15 02:26 sort_baseline.py
-rwxrwxr-x  1 alexice alexice 5.1K Aug 15 13:08 sort_margin005_best.py
-rwxrwxr-x  1 alexice alexice  11K Aug 15 13:36 sort_neighbor_v34.py
-rwxrwxr-x  1 alexice alexice 7.7K Aug 15 14:41 sort_neighbor_v35_benchmark.py
-rwxrwxr-x  1 alexice alexice 9.1K Aug 15 13:41 sort_neighbor_v35.py
-rw-rw-r--  1 alexice alexice 9.5K Aug 15 14:50 sort_neighbor_v36_img.py
-rw-rw-r--  1 alexice alexice 9.5K Aug 15 14:46 sort_neighbor_v36.py
-rw-rw-r--  1 alexice alexice 8.2K Aug 15 14:53 sort_neighbor_v37.py
-rwxrwxr-x  1 alexice alexice 9.3K Aug 15 02:14 sort_test_and_report.py
-rwxrwxr-x  1 alexice alexice  11K Aug 15 02:16 sort_test_and_report_v2.py

=== NEIGHBOR V37 ===
#!/usr/bin/env python3

import csv
import json
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/new"
SOURCE_JSON = PROJECT / "data/output/benchmark_img/benchmark.json"

OUTPUT_DIR = PROJECT / "output/neighbor_v37"
SORTED_DIR = OUTPUT_DIR / "sorted"
REPORT_CSV = OUTPUT_DIR / "neighbor_decision.csv"

MARGIN_LIMIT = 0.005

def normalize_id(x):
    try:
        return int(str(x).replace("_v33", ""))
    except Exception:
        return None

def get_results(item):
    """
    Поддерживаем возможные варианты структуры benchmark.json.
    """
    results = (
        item.get("results")
        or item.get("predictions")
        or item.get("candidates")
        or item.get("top_k")
    )

    if isinstance(results, dict):
        results = list(results.items())

    if not isinstance(results, list):
        return []

    out = []

    for r in results:
        if isinstance(r, dict):
            fp = (
                r.get("fingerprint")
                or r.get("id")
                or r.get("label")
                or r.get("name")
            )
            score = (
                r.get("score")
                if r.get("score") is not None
                else r.get("similarity")
            )

            if fp is not None:
                try:
                    score = float(score)
                except Exception:
                    score = 0.0
                out.append((normalize_id(fp), score))

        elif isinstance(r, (list, tuple)) and len(r) >= 2:
            out.append((normalize_id(r[0]), float(r[1])))

    return [(fp, score) for fp, score in out if fp is not None]

def get_image(item):
    for key in ("image", "filename", "file", "path", "name"):
        value = item.get(key)
        if value:
            return Path(str(value)).name
    return None

with open(SOURCE_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

if isinstance(data, dict):
    items = (
        data.get("results")
        or data.get("images")
        or data.get("items")
        or data.get("data")
    )
else:
    items = data

if not isinstance(items, list):
    raise RuntimeError("Не удалось найти список результатов в benchmark.json")

records = []

for item in items:
    image = get_image(item)
    results = get_results(item)

    if not image or not results:
        continue

    top1 = results[0][0]
    top1_score = results[0][1]

    top2 = results[1][0] if len(results) > 1 else None
    top2_score = results[1][1] if len(results) > 1 else None

    margin = (
        top1_score - top2_score
        if top2_score is not None
        else 999.0
    )

    records.append({
        "image": image,
        "top1": top1,
        "top1_score": top1_score,
        "top2": top2,
        "top2_score": top2_score,
        "margin": margin,
    })

# Очень важно:
# сортируем по реальному имени img_000, img_001...
# а не по порядку JSON.
def image_number(r):
    name = Path(r["image"]).stem
    digits = "".join(c for c in name if c.isdigit())
    return int(digits) if digits else 10**9

records.sort(key=image_number)

changed = []
rows = []

for i, rec in enumerate(records):

    v33 = rec["top1"]
    second = rec["top2"]
    margin = rec["margin"]

    final = v33
    reason = "V33"

    forward_support = []
    backward_support = []

    forward_neighbors = []
    backward_neighbors = []

    # Работаем только с сомнительными кадрами.
    if margin < MARGIN_LIMIT and second is not None:

        # ------------------------------------------------------------
        # 1. СНАЧАЛА СМОТРИМ ВПЕРЕД
        # ------------------------------------------------------------
        for offset in (1, 2):
            j = i + offset

            if j >= len(records):
                continue

            neighbor = records[j]
            nid = neighbor["top1"]

            forward_neighbors.append(
                f"+{offset}:{neighbor['image']}={nid}"
            )

            if nid == second:
                forward_support.append(offset)

        # Если хотя бы один из следующих двух кадров
        # подтверждает кандидата №2 — выбираем его.
        if forward_support:
            final = second
            reason = "FORWARD_SUPPORT_TOP2"

        else:

            # --------------------------------------------------------
            # 2. ЕСЛИ ВПЕРЕДИ НЕ ПОДТВЕРДИЛОСЬ — СМОТРИМ НАЗАД
            # --------------------------------------------------------
            for offset in (1, 2):
                j = i - offset

                if j < 0:
                    continue

                neighbor = records[j]
                nid = neighbor["top1"]

                backward_neighbors.append(
                    f"-{offset}:{neighbor['image']}={nid}"
                )

                if nid == second:
                    backward_support.append(offset)

            if backward_support:
                final = second
                reason = "BACKWARD_SUPPORT_TOP2"
            else:
                reason = "NO_NEIGHBOR_SUPPORT"

    if final != v33:
        changed.append({
            "image": rec["image"],
            "v33": v33,
            "second": second,
            "final": final,
            "margin": margin,
            "reason": reason,
            "forward_support": forward_support,
            "backward_support": backward_support,
        })

    rows.append({
        "index": i,
        "image": rec["image"],
        "v33": v33,
        "second": second,
        "final": final,
        "margin": margin,
        "reason": reason,
        "forward_support": ",".join(map(str, forward_support)),
        "backward_support": ",".join(map(str, backward_support)),
        "forward_neighbors": "; ".join(forward_neighbors),
        "backward_neighbors": "; ".join(backward_neighbors),
    })

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if SORTED_DIR.exists():
    shutil.rmtree(SORTED_DIR)

SORTED_DIR.mkdir(parents=True)

for row in rows:
    src = INPUT_DIR / row["image"]

    if not src.exists():
        continue

    destination = SORTED_DIR / str(row["final"])
    destination.mkdir(parents=True, exist_ok=True)

    shutil.copy2(src, destination / src.name)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:01:25

Да. Здесь уже видно, что **V37 — это не тот уровень постобработки, который нам нужен**.

В частности, зона `112–122` показывает типичную проблему:

- 112 = 84
- 113 = 87
- 114 = 84
- 115 = 87
- 116–118 = 84
- 119 = 87
- 120–122 = 84

При этом до неё идёт `79`, а после неё — стабильный `88`.

То есть логически это почти наверняка **одна серия 84**, а отдельные `87` внутри неё — шум распознавания.

### Предлагаю V38 сделать именно как последовательностную постобработку

Не менять сам DINO/V33 вообще.

Схема:

```text
V33 TOP1
   ↓
строим последовательность адресов
   ↓
находим устойчивые серии / границы
   ↓
одиночные выбросы внутри серии удаляем
   ↓
границы определяем по устойчивому новому адресу
   ↓
весь участок между границами получает один адрес
   ↓
копируем фотографии по адресам
```

Например:

```text
111  79
112  84
113  87  ← шум
114  84
115  87  ← шум
116  84
117  84
118  84
119  87  ← шум
120  84
121  84
122  84
123  88
124  88
125  88
```

V38 должен получить:

```text
111  79
112  84
113  84
114  84
115  84
116  84
117  84
118  84
119  84
120  84
121  84
122  84
123  88
124  88
125  88
```

То есть **не исправляем отдельную фотографию — определяем серию**.

---

## Но сначала я бы не трогал V37

Сделаем V38 отдельным экспериментом, чтобы можно было сравнить:

```text
V33
 ↓
V37
 ↓
V38
```

И обязательно сохраним CSV с решением.

### Предлагаю параметры V38

```text
MIN_STABLE_RUN = 2
MIN_MARGIN = 0.02
MAX_NOISE_GAP = 3
```

Смысл:

- серия из 2+ последовательных уверенных кадров считается якорем;
- короткие вкрапления другого адреса внутри серии считаются шумом;
- граница появляется только когда новый адрес получает устойчивое подтверждение;
- между двумя границами весь диапазон получает один адрес.

Это особенно хорошо должно решить `84/87`.

### И ещё важный момент

В V37 сейчас есть довольно опасная логика:

```python
if nid == second:
    final = second
```

То есть **одного соседнего кадра достаточно, чтобы изменить адрес**.

Для серии это наоборот нужно делать:

```text
один кадр → почти никогда не меняем адрес
два последовательных кадра → кандидат на новую серию
три кадра → практически подтверждённая граница
```

---

### Следующим шагом давай сделаем V38 поверх текущего V37

Но **не будем пока автоматически сортировать**.

Первый запуск V38 должен только создать:

```text
output/sequence_v38/
    sequence_decision.csv
    sequence_report.txt
```

и показать:

```text
BOUNDARY
79 → 84
frames 112-122 = 84

BOUNDARY
84 → 88
frames 123-...
```

А уже после просмотра границ включим реальную сортировку.

**Это безопаснее:** сначала проверим, правильно ли алгоритм понимает серии на этих 256 фотографиях.

---

### 👤 **User** — 2026-08-15 15:01:56

да

---

### 🤖 **Assistant** — 2026-08-15 15:01:57

> **Inspecting Sequence Analysis Script**
>
>
> **Inspected sequence analysis script**
>
> 
>
> Worked for 4s

Отлично. У тебя `analyze_sequence_v38.py` уже существует, поэтому **не будем создавать новый файл поверх него**.

Сейчас нужно посмотреть, что именно в нём уже реализовано. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== V38 CURRENT ==="
sed -n '1,320p' scripts/analyze_sequence_v38.py
```

И сразу после этого:

```bash
echo
echo "=== V38 HELP ==="
python3 scripts/analyze_sequence_v38.py --help
```

Обрати внимание: у тебя команда `python` не существует, поэтому дальше используем **`python3`** или `uv run python`.

Пришли оба вывода. После этого я либо сразу запущу существующий V38, либо точечно поправлю его под логику **«границы серий → один адрес на всю серию»**.

---

