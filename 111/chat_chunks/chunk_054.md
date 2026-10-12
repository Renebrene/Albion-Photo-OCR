## СЕССИЯ: готовая

**Создано:** 2026-08-15 15:28:03
**Обновлено:** 2026-08-22 01:02:53
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a805b4f-ffdc-83ea-99c8-406054298239](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a805b4f-ffdc-83ea-99c8-406054298239)

---

### 🤖 **Assistant** — 2026-08-15 20:14:41

Отлично. Структура подходит.

Теперь делаем настоящий `sub rerank v02`.

Что используем:

- вход: `benchmark_sub_exp/benchmark.json`
- кандидаты: только `top1-top5`
- sub база: `data/fingerprints_sub_exp`
- embedding: тот же DINOv2 768
- сравнение: cosine с `centroid.npy`

Почему сначала centroid:
- быстро;
- соответствует текущему fingerprint v3.3;
- 256 фото × 5 адресов × ~2 sub = примерно 2500 сравнений — мгновенно.

Создаём:

```bash
nano scripts/benchmark_sub_rerank_v02.py
```

Вставь:

```python
#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder

PROJECT = Path(__file__).resolve().parent.parent

BENCHMARK = (
    PROJECT
    / "data/output/benchmark_sub_exp/benchmark.json"
)

SUB_DIR = (
    PROJECT
    / "data/fingerprints_sub_exp"
)

OUT = (
    PROJECT
    / "data/output/benchmark_sub_rerank_v02.json"
)

def normalize(v):

    v = np.asarray(
        v,
        dtype=np.float32
    )

    n = np.linalg.norm(v)

    if n == 0:
        return v

    return v / n

def load_sub():

    result = {}

    for d in SUB_DIR.iterdir():

        if not d.is_dir():
            continue

        centroid = d / "centroid.npy"

        if not centroid.exists():
            continue

        result[d.name] = normalize(
            np.load(centroid)
        )

    return result

def cosine(a,b):

    return float(
        np.dot(a,b)
    )

def main():

    print("="*80)
    print("SUB RERANK V02")
    print("="*80)

with open(
        BENCHMARK,
        encoding="utf-8"
    ) as f:
        bench=json.load(f)

settings=Settings()

    embedder=SceneEmbedder(
        settings
    )

sub_db=load_sub()

print(
        "Images:",
        len(bench["results"])
    )

    print(
        "Sub fingerprints:",
        len(sub_db)
    )

changed=[]

for idx,row in enumerate(
        bench["results"],
        1
    ):

        path=Path(
            row["file"]
        )

emb=embedder.embed_paths(
            [path]
        )[0]

emb=normalize(emb)

candidates=[]

for k in range(1,6):

            fp=row.get(
                f"top{k}"
            )

            if fp:
                candidates.append(
                    fp.replace(
                        "_v33",
                        ""
                    )
                )

best=row["top1"]
        best_score=row["top1_score"]

sub_best=None

for addr in candidates:

for sub_id,centroid in sub_db.items():

if not sub_id.startswith(
                    addr
                ):
                    continue

score=cosine(
                    emb,
                    centroid
                )

if (
                    sub_best is None
                    or score > sub_best["score"]
                ):

                    sub_best={
                        "sub":sub_id,
                        "address":addr,
                        "score":score
                    }

if sub_best:

            if (
                sub_best["address"]+"_v33"
                != best
            ):

                changed.append(
                    {
                        "file":path.name,
                        "old":best,
                        "old_score":best_score,
                        "new":sub_best["sub"],
                        "new_score":sub_best["score"],
                    }
                )

OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

OUT.write_text(
        json.dumps(
            {
                "changed":len(changed),
                "results":changed
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

print()
    print(
        "CHANGED:",
        len(changed)
    )

    for x in changed[:30]:

        print()
        print(
            x["file"]
        )

        print(
            x["old"],
            "->",
            x["new"]
        )

        print(
            x["old_score"],
            "->",
            x["new_score"]
        )

print()
    print(
        "saved:",
        OUT
    )

if __name__=="__main__":
    main()
```

Запуск:

```bash
uv run python scripts/benchmark_sub_rerank_v02.py
```

---

Ожидаем два варианта:

### Вариант 1 (хороший)
Будет что-то вроде:

```
CHANGED: 5

Ленина125_04.JPG
87_v33 -> 84_v33_sub_2
0.8958 -> 0.9124
```

Тогда subfingerprint реально помогает.

---

### Вариант 2
```
CHANGED: 0
```

Тогда centroid sub не даёт прироста и будем пробовать следующий уровень:

```
centroid
 +
environment 640
 +
color 48
 +
spatial 32
```

То есть полноценный compact descriptor rerank, как у V33.

Сейчас важный тест — **может ли сам факт разделения ракурсов решить спорные пары 84/87, 89/92**.

---

### 👤 **User** — 2026-08-15 20:16:07

CHANGED: 130

Вавилова52_08.JPG
95_v33 -> 94_v33_sub_3
0.7992325067520142 -> 0.8696886301040649

Добровольского17_01.JPG
82_v33 -> 92_v33_sub_1
0.8984161710739135 -> 0.7482138872146606

Добровольского17_06.JPG
82_v33 -> 92_v33_sub_2
0.9470346766710281 -> 0.7253468036651611

Зорге_17.jpg
95_v33 -> 92_v33_sub_2
0.8691043245792388 -> 0.8441705107688904

КА_01.JPG
81_v33 -> 84_v33_sub_2
0.9252433615922928 -> 0.8805630207061768

КА_02.JPG
81_v33 -> 84_v33_sub_2
0.9385261201858519 -> 0.8677136898040771

КА_03.JPG
81_v33 -> 84_v33_sub_2
0.9356184577941895 -> 0.8516137003898621

КА_04.JPG
81_v33 -> 84_v33_sub_2
0.9303612405061722 -> 0.8733957409858704

КА_05.JPG
81_v33 -> 84_v33_sub_2
0.9350122618675232 -> 0.8553653359413147

КА_06.JPG
81_v33 -> 84_v33_sub_2
0.9355985921621323 -> 0.8472755551338196

КА_07.JPG
81_v33 -> 84_v33_sub_2
0.9318429297208787 -> 0.8549286127090454

КА_08.JPG
81_v33 -> 84_v33_sub_2
0.9312276268005371 -> 0.8483825325965881

КА_09.JPG
81_v33 -> 84_v33_sub_2
0.9201316529512404 -> 0.861821711063385

КА_10.JPG
81_v33 -> 84_v33_sub_2
0.9223347353935243 -> 0.886755108833313

КА_11.JPG
81_v33 -> 84_v33_sub_2
0.8812718081474304 -> 0.8315843939781189

КА_12.JPG
81_v33 -> 85_v33_sub_1
0.8875578993558884 -> 0.8327827453613281

КА_13.JPG
81_v33 -> 84_v33_sub_2
0.9328902482986451 -> 0.9038782119750977

КА_14.JPG
81_v33 -> 84_v33_sub_2
0.9001390314102172 -> 0.8031208515167236

КА_15.JPG
81_v33 -> 84_v33_sub_2
0.8990001916885375 -> 0.8094092607498169

КА_16.JPG
81_v33 -> 84_v33_sub_2
0.8884866142272949 -> 0.7829555869102478

Комарова13_01.JPG
78_v33 -> 95_v33_sub_2
0.9469282221794127 -> 0.889930009841919

Комарова13_02.JPG
78_v33 -> 92_v33_sub_2
0.9507890856266022 -> 0.8797671794891357

Комарова13_03.JPG
78_v33 -> 95_v33_sub_2
0.9404607355594634 -> 0.8812100887298584

Комарова13_04.JPG
78_v33 -> 92_v33_sub_2
0.9459992891550063 -> 0.8538080453872681

Комарова13_05.JPG
78_v33 -> 95_v33_sub_2
0.9468323802947998 -> 0.9045283198356628

Комарова13_06.JPG
78_v33 -> 95_v33_sub_2
0.937333036661148 -> 0.8772381544113159

Комарова13_07.JPG
78_v33 -> 95_v33_sub_2
0.906127427816391 -> 0.819566011428833

Комарова13_08.JPG
78_v33 -> 92_v33_sub_2
0.9509821295738221 -> 0.8577523827552795

Комарова13_09.JPG
78_v33 -> 92_v33_sub_2
0.9293549776077271 -> 0.8646209239959717

Комарова13_10.JPG
78_v33 -> 92_v33_sub_2
0.9458954721689223 -> 0.8810544013977051

saved: /home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_sub_rerank_v02.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:16:08

Результат очень показательный. **Sub-rerank в текущем виде нельзя включать.** Но эксперимент удался — мы нашли важную особенность.

Сейчас проблема не в subfingerprints, а в логике выбора.

Что произошло:

Текущий V33:

```
query
 |
 +-- global fingerprint
       |
       +-- правильный адрес
```

А наш тест:

```
query
 |
 +-- TOP-5 адресов V33
 |
 +-- все sub всех этих адресов
 |
 +-- максимум cosine
```

Но мы сравниваем **DINO global embedding изображения** с **centroid subfingerprint**, который был построен на другой выборке.

Получилась ситуация:

```
старый:
81_v33
score 0.93

sub:
84_v33_sub_2
score 0.85
```

И всё равно он победил, потому что код не учитывает:

- насколько хуже score относительно исходного кандидата;
- насколько близок адрес был в TOP-5;
- насколько sub подтверждает именно свой родительский fingerprint.

---

Самый важный вывод:

### Subfingerprints работают как уточнение, но НЕ как самостоятельный классификатор.

Нужно сделать не так:

```
выбрать максимальный sub score
```

а так:

```
итоговый score =
старый V33 score
+
коэффициент * улучшение sub
```

Например:

```
81_v33

global:
0.935

sub:
81_sub_1
0.910

итог:
0.935 + 0.2*(0.910-0.935)

= хуже
```

А:

```
87_v33

global:
0.895

84_sub_1:
0.913

но 84 не был первым

итог:
0.895 + bonus
```

---

Нужно изменить алгоритм.

## Версия V03

Логика:

### 1. Берём только top1 + top2

Не весь TOP-5.

Почему:

TOP-5 содержит шум.

---

### 2. Для каждого кандидата считаем:

```
parent_score = обычный V33

sub_best_score =
лучший sub этого адреса

delta =
sub_best - parent
```

---

### 3. Решение:

Меняем адрес только если:

```
delta > 0.015
```

и

```
parent был top1/top2
```

---

Пример:

Было:

```
Ленина125_04

87:
0.8958

84:
0.8950
```

Sub:

```
87_sub:
0.902

84_sub:
0.921
```

Получаем:

```
84 выигрывает
```

---

А вот:

```
Добровольского17

82:
0.947

92_sub:
0.725
```

будет отброшено.

---

Ещё один момент: у нас есть очень важная информация из твоего вывода:

### Большие группы ошибочных переходов:

```
КА_*
81 -> 84
```

```
Комарова13
78 -> 92/95
```

```
Добровольского
82 -> 92
```

Это как раз кандидаты для проверки.

---

Следующий шаг я бы сделал такой:

Создаём:

```bash
nano scripts/benchmark_sub_rerank_v03.py
```

и считаем:

```
CHANGED_STRICT
```

только где:

- новый sub улучшает score;
- родитель был TOP1 или TOP2;
- margin после изменения становится лучше.

Тогда мы увидим реальную пользу sub.

Сейчас предварительный вывод:

✅ кластеризация sub правильная  
✅ создание subfingerprint работает  
✅ 17 sub создано корректно  
❌ простое "максимальное сходство sub" неправильное  
➡️ нужен rerank, а не замена классификатора

Это как раз соответствует будущей архитектуре: **DINO глобальный поиск → subfingerprint уточнение → адрес.**

---

### 👤 **User** — 2026-08-15 20:17:10

DINO глобальный поиск → subfingerprint уточнение → адрес.

---

### 🤖 **Assistant** — 2026-08-15 20:17:12

Да, именно эта схема выглядит наиболее правильной для нашего проекта.

Сейчас эксперимент показал, что **subfingerprint не должен заменять DINO-глобальный поиск**. Он должен работать как второй этап уточнения.

Итоговая архитектура:

```
                 ФОТО
                  |
                  v
        +----------------+
        |  DINOv2 global |
        |   embedding   |
        +----------------+
                  |
                  |
          TOP-N кандидатов
          (например TOP-5)
                  |
                  v
        +----------------+
        | Subfingerprint |
        |    rerank      |
        +----------------+
                  |
                  |
       лучший ракурс / группа
                  |
                  v
              АДРЕС
```

---

### Этап 1. DINO global search

Это текущий V33.

Он отвечает на вопрос:

> "На какой объект это больше всего похоже?"

Например:

```
Фото:
Ленина125_04.JPG

TOP:

87_v33    0.8958
84_v33    0.8950
79_v33    0.812
95_v33    0.790
```

То есть:

```
кандидаты:
87
84
```

---

### Этап 2. Subfingerprint уточнение

Теперь смотрим только:

```
87_v33
 ├── sub_1
 └── sub_2

84_v33
 ├── sub_1
 └── sub_2
```

Получаем:

```
87_sub_1    0.901
87_sub_2    0.888

84_sub_1    0.913
84_sub_2    0.905
```

Теперь можно сказать:

```
84 лучше
```

---

### Почему это работает

Потому что адрес часто имеет несколько "состояний":

Например:

```
84
 |
 +-- фасад слева летом
 |
 +-- фасад справа зимой
 |
 +-- дальний план
 |
 +-- подъезд
```

Глобальный fingerprint усредняет:

```
84 = всё вместе
```

А subfingerprint сохраняет:

```
84_sub_1 = конкретный ракурс
84_sub_2 = другой ракурс
```

---

### В будущем добавляем третий уровень

Я бы сделал так:

```
Уровень 1
=========
DINO global

Цель:
быстро найти 5-10 адресов

|
        v

Уровень 2
=========
Subfingerprint

Цель:
отделить ракурсы

|
        v

Уровень 3
=========
Compact descriptor

(environment + color + spatial)

Цель:
разрешить спорные случаи

|
        v

Уровень 4
=========
OCR / номер / ручная проверка

Только сложные случаи
```

---

Для промышленного режима:

200-300 фото в день:

```
300 фото
 |
 |
DINO global
≈ несколько секунд
 |
 |
TOP-5
 |
 |
sub rerank
≈ доли секунды
 |
 |
готовая сортировка
```

---

Ещё важный момент по нашим экспериментам:

Вот эти случаи:

```
Ленина125:
87 <-> 84

Зорге:
89 <-> 92

Радиаторный:
94 <-> 89
```

— это **идеальные кандидаты для subfingerprint**.

То есть нам не нужно гонять sub по всем адресам.

Можно сделать:

```
если margin > 0.05
    сразу принять

если margin < 0.05
    включить sub-rerank
```

Это даст:

- скорость V33 на простых фото;
- точность sub на сложных.

И это уже очень похоже на промышленный pipeline распознавания.

---

### 👤 **User** — 2026-08-15 20:17:55

даваай

---

### 🤖 **Assistant** — 2026-08-15 20:17:57

Делаем **SUB RERANK V03** по правильной схеме:

```
DINO global
    |
    | если уверенно -> сразу результат
    |
    | если спорно -> subfingerprint уточнение
    |
адрес
```

Сейчас не трогаем recognizer.py. Делаем отдельный экспериментальный скрипт.

Логика V03:

1. Берём исходный `benchmark_sub_exp/benchmark.json`

2. Для каждого фото:

- смотрим:
  - `top1`
  - `top2`

Только эти два адреса.

3. Ищем среди:

```
data/fingerprints_sub_exp/

85_v33_sub_1
85_v33_sub_2
...
```

только соответствующие родители.

4. Считаем:

```
global_score = исходный V33 score

sub_score = лучший sub данного адреса
```

5. Меняем адрес только если:

```
sub_score > global_score + 0.015
```

и:

```
кандидат был TOP1 или TOP2
```

---

Создаём:

```bash
nano scripts/benchmark_sub_rerank_v03.py
```

Основная идея будет такая:

```python
if candidate_parent in [top1, top2]:

    improvement = (
        best_sub_score
        -
        parent_score
    )

    if improvement > 0.015:
        change_result()
```

---

После запуска получим три статистики:

```
ORIGINAL V33
----------------
correct candidates

SUB V02
----------------
changed: 130

SUB V03
----------------
changed:
improved:
rejected:
```

Особенно посмотрим:

```
Ленина125
87 <-> 84

Зорге
89 <-> 92

Радиаторный
94 <-> 89

КА
81
```

---

Ещё добавим в отчёт:

```
PHOTO
OLD
NEW
OLD SCORE
SUB SCORE
DELTA
REASON
```

Например:

```
Ленина125_04.JPG

OLD:
87_v33
0.8958

CANDIDATE:
84_v33

sub:
84_v33_sub_2
0.9214

DELTA:
+0.0256

ACTION:
CHANGED
```

После этого будет понятно, действительно ли sub помогает.

Следующим этапом после V03 уже можно будет встроить это внутрь `recognizer.py` как режим:

```
--rerank-sub
```

чтобы старый V33 оставался как базовый.

---

### 👤 **User** — 2026-08-15 20:18:09

продолжаем

---

### 🤖 **Assistant** — 2026-08-15 20:18:11

Продолжаем. Сейчас делаем **V03**, но сначала проверим один момент: у нас уже есть правильная база sub:

```
data/fingerprints_sub_exp/
    84_v33_sub_1
    84_v33_sub_2
    ...
```

и исходный benchmark:

```
data/output/benchmark_sub_exp/benchmark.json
```

Создаём новый скрипт:

```bash
nano scripts/benchmark_sub_rerank_v03.py
```

Вставляем:

```python
#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder

PROJECT = Path(__file__).resolve().parent.parent

BENCHMARK = (
    PROJECT /
    "data/output/benchmark_sub_exp/benchmark.json"
)

SUB_DIR = (
    PROJECT /
    "data/fingerprints_sub_exp"
)

OUT = (
    PROJECT /
    "data/output/benchmark_sub_rerank_v03.json"
)

MIN_DELTA = 0.015

def normalize(x):

    x = np.asarray(
        x,
        dtype=np.float32
    )

    n = np.linalg.norm(x)

    if n:
        x = x / n

    return x

def load_sub():

    db = {}

    for d in SUB_DIR.iterdir():

        if not d.is_dir():
            continue

        c = d / "centroid.npy"

        if not c.exists():
            continue

        db[d.name] = normalize(
            np.load(c)
        )

    return db

def main():

    print("=" * 80)
    print("SUB RERANK V03")
    print("=" * 80)

with open(
        BENCHMARK,
        encoding="utf-8"
    ) as f:
        data = json.load(f)

settings = Settings()

    embedder = SceneEmbedder(
        settings
    )

    sub_db = load_sub()

changed = []
    checked = 0

for row in data["results"]:

        top1 = row["top1"]
        top2 = row["top2"]

        candidates = [
            top1,
            top2,
        ]

image = Path(
            row["file"]
        )

emb = embedder.embed_paths(
            [image]
        )[0]

        emb = normalize(
            emb
        )

best_parent = top1
        best_score = row["top1_score"]
        best_sub = None

for parent in candidates:

            parent_id = parent.replace(
                "_v33",
                ""
            )

for sub_id, centroid in sub_db.items():

                if not sub_id.startswith(
                    parent_id + "_"
                ):
                    continue

score = float(
                    np.dot(
                        emb,
                        centroid
                    )
                )

if score > best_score:

                    delta = (
                        score -
                        row["top1_score"]
                    )

                    if delta >= MIN_DELTA:

                        best_score = score
                        best_parent = (
                            parent_id +
                            "_v33"
                        )
                        best_sub = sub_id

if best_parent != top1:

            changed.append(
                {
                    "file": image.name,
                    "old": top1,
                    "new": best_parent,
                    "sub": best_sub,
                    "old_score": row["top1_score"],
                    "new_score": best_score,
                    "delta": best_score-row["top1_score"],
                }
            )

checked += 1

OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT.write_text(
        json.dumps(
            {
                "checked": checked,
                "changed": len(changed),
                "results": changed,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

print()
    print("checked:", checked)
    print("changed:", len(changed))

    for x in changed[:30]:

        print()
        print(x["file"])
        print(
            x["old"],
            "->",
            x["new"]
        )
        print(
            "sub:",
            x["sub"]
        )
        print(
            "delta:",
            round(x["delta"],4)
        )

print()
    print("saved:")
    print(OUT)

if __name__ == "__main__":
    main()
```

Запуск:

```bash
uv run python scripts/benchmark_sub_rerank_v03.py
```

---

Что ожидаем:

Если всё правильно, количество изменений должно быть **не 130**, а примерно единицы/десятки.

Особенно смотрим:

- `Ленина125_*`
- `Зорге_*`
- `Радиаторный_*`
- `Малиновского_*`

Если V03 даст хорошие изменения — следующий шаг будет уже не benchmark, а перенос в `recognizer.py`:

```
recognize
 |
 +-- global DINO
 |
 +-- margin check
 |
 +-- sub rerank only if needed
 |
 +-- final address
```

То есть сохраним скорость V33 и добавим точность там, где сейчас есть спор.

---

### 👤 **User** — 2026-08-15 20:19:31

checked: 256
changed: 1

Вавилова52_08.JPG
95_v33 -> 94_v33
sub: 94_v33_sub_3
delta: 0.0705

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_sub_rerank_v03.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:19:32

Отличный результат. Это как раз подтверждает правильность архитектуры.

Сейчас V03 сделал **только одно изменение**, и оно выглядит очень здоровым:

```
Вавилова52_08.JPG

V33:
95_v33
score 0.7992

SUB:
94_v33_sub_3

новый:
94_v33
score 0.8697

delta:
+0.0705
```

То есть subfingerprint не "перетягивает" все подряд, а вмешивается только там, где действительно есть сильный сигнал.

---

Почему получилось всего 1 изменение:

В V02 была проблема:

```
changed: 130
```

Потому что мы сравнивали:

```
фото
   |
   +-- все 17 subfingerprint
```

и маленькие субкластеры начали конкурировать с большими адресами.

Например:

```
КА
81_v33
 |
 +--84_v33_sub_2
```

они могли случайно получить высокий cosine.

---

V03 уже ограничивает:

```
TOP1
TOP2
 |
 только их sub
```

То есть:

```
global говорит:

вероятно:
87 или 84

sub проверяет только:

87_sub_*
84_sub_*
```

Это правильная логика.

---

Но есть один момент. Сейчас V03 использует:

```
sub centroid
```

То есть:

```
sub_1
   |
   средний вектор
```

А у нас в fingerprint есть:

```
embeddings.npy
representatives.npy
environment_embeddings.npy
color_embeddings.npy
spatial_embeddings.npy
```

То есть можно сделать V04:

### Sub rerank по ближайшему кадру

Не:

```
photo -> centroid
```

а:

```
photo
 |
 |
сравнить с каждым изображением sub
 |
 |
лучший кадр
```

Например:

```
Вавилова52_08

95_v33
лучший кадр:
95_013.JPG
score 0.799

94_sub_3

кадр:
94_021.JPG
score 0.882
```

Это будет намного ближе к реальному распознаванию.

---

Я бы сделал следующий тест:

## V04

Алгоритм:

```
1. DINO global TOP5

2. Берём только TOP2

3. Для каждого адреса:

   открыть:
   embeddings.npy

4. cosine:

   photo embedding
          |
          v
   все изображения sub

5. max score

6. если delta > 0.02
   меняем
```

Ожидаю, что тогда мы поймаем как раз:

```
Ленина125
87 <-> 84

Зорге
89 <-> 92

Радиаторный
94 <-> 89
```

которые сейчас sequence исправлял через соседей.

---

Следующий шаг я бы сделал так:

```bash
nano scripts/benchmark_sub_rerank_v04.py
```

и меняем только механизм оценки:

было:

```
embedding -> centroid.npy
```

становится:

```
embedding -> embeddings.npy -> max()
```

Это будет уже почти финальная схема:

```
DINO global
     |
     TOP-5
     |
     subfingerprint nearest image
     |
     адрес
     |
     sequence smoothing
```

То есть четыре уровня защиты:
1. модельное сходство
2. ракурс
3. соседние кадры
4. временная последовательность съёмки

Именно это нам нужно для 200-300 фото в день.

---

### 👤 **User** — 2026-08-15 20:20:23

давай

---

### 🤖 **Assistant** — 2026-08-15 20:20:25

Делаем V04. Он будет использовать **реальные изображения внутри subfingerprint**, а не только centroid.

Создаём:

```bash
nano scripts/benchmark_sub_rerank_v04.py
```

Вставляем:

```python
#!/usr/bin/env python3

import json
from pathlib import Path

import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder

PROJECT = Path(__file__).resolve().parent.parent

BENCHMARK = (
    PROJECT /
    "data/output/benchmark_sub_exp/benchmark.json"
)

SUB_DIR = (
    PROJECT /
    "data/fingerprints_sub_exp"
)

OUT = (
    PROJECT /
    "data/output/benchmark_sub_rerank_v04.json"
)

MIN_DELTA = 0.02

def normalize(x):

    x = np.asarray(
        x,
        dtype=np.float32
    )

    n = np.linalg.norm(x)

    if n:
        x = x / n

    return x

def load_sub_database():

    db = {}

    for d in sorted(SUB_DIR.iterdir()):

        if not d.is_dir():
            continue

        emb_file = (
            d /
            "embeddings.npy"
        )

        meta_file = (
            d /
            "metadata.json"
        )

        if not emb_file.exists():
            continue

        embeddings = np.load(
            emb_file
        )

        embeddings = np.asarray(
            embeddings,
            dtype=np.float32
        )

        embeddings = np.array(
            [
                normalize(x)
                for x in embeddings
            ]
        )

names = []

        if meta_file.exists():

            with open(
                meta_file,
                encoding="utf-8"
            ) as f:
                meta=json.load(f)

            names = meta.get(
                "image_names",
                []
            )

db[d.name] = {
            "embeddings": embeddings,
            "names": names,
        }

return db

def parent_name(sub_id):

    # 84_v33_sub_2 -> 84_v33

    parts = sub_id.split("_sub_")

    return parts[0]

def main():

    print("="*80)
    print("SUB RERANK V04")
    print("="*80)

with open(
        BENCHMARK,
        encoding="utf-8"
    ) as f:

        data=json.load(f)

settings=Settings()

    embedder=SceneEmbedder(
        settings
    )

sub_db = load_sub_database()

changed=[]

    checked=0

for row in data["results"]:

        top_candidates = [
            row["top1"],
            row["top2"],
        ]

image = Path(
            row["file"]
        )

emb = embedder.embed_paths(
            [image]
        )[0]

        emb = normalize(
            emb
        )

best_parent = row["top1"]
        best_score = row["top1_score"]
        best_sub = None
        best_image = None

for parent in top_candidates:

for sub_id, sub in sub_db.items():

if parent_name(sub_id) != parent:
                    continue

scores = (
                    sub["embeddings"]
                    @ emb
                )

idx = int(
                    np.argmax(scores)
                )

                score = float(
                    scores[idx]
                )

if score > best_score:

                    delta = (
                        score -
                        row["top1_score"]
                    )

if delta >= MIN_DELTA:

                        best_score = score
                        best_parent = parent
                        best_sub = sub_id

if idx < len(sub["names"]):
                            best_image = (
                                sub["names"][idx]
                            )

if best_parent != row["top1"]:

            changed.append(
                {
                    "file": image.name,
                    "old": row["top1"],
                    "new": best_parent,
                    "sub": best_sub,
                    "best_image": best_image,
                    "old_score": row["top1_score"],
                    "new_score": best_score,
                    "delta": (
                        best_score -
                        row["top1_score"]
                    )
                }
            )

checked += 1

OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

OUT.write_text(
        json.dumps(
            {
                "checked": checked,
                "changed": len(changed),
                "results": changed
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

print()
    print("checked:", checked)
    print("changed:", len(changed))

for x in changed[:50]:

        print()
        print(x["file"])
        print(
            x["old"],
            "->",
            x["new"]
        )
        print(
            "sub:",
            x["sub"]
        )
        print(
            "image:",
            x["best_image"]
        )
        print(
            "delta:",
            round(
                x["delta"],
                4
            )
        )

print()
    print("saved:")
    print(OUT)

if __name__=="__main__":
    main()
```

Запуск:

```bash
uv run python scripts/benchmark_sub_rerank_v04.py
```

После результата смотрим главное:

1. Сколько изменений:

```text
changed:
```

2. Попались ли наши спорные группы:

```text
Ленина125
Зорге
Радиаторный
Малиновского
```

3. В отчёте появится:

```text
best_image:
```

Это важно — мы увидим, какой именно кадр из subfingerprint победил.

Если V04 даст хорошие изменения, следующим шагом объединяем:

```
recognizer.py

DINO TOP5
   |
   +-- margin < 0.03 ?
          |
          sub rerank
          |
          sequence smoothing
```

и получаем рабочий поток для отдела.

---

### 👤 **User** — 2026-08-15 20:22:06

hecked: 256
changed: 4

Ленина125_02.JPG
87_v33 -> 84_v33
sub: 84_v33_sub_2
image: 84_010.JPG
delta: 0.0633

Ленина125_04.JPG
87_v33 -> 84_v33
sub: 84_v33_sub_2
image: 84_010.JPG
delta: 0.0518

Ленина125_08.JPG
87_v33 -> 84_v33
sub: 84_v33_sub_2
image: 84_010.JPG
delta: 0.052

Шеболдаева8_06.JPG
87_v33 -> 92_v33
sub: 92_v33_sub_1
image: 92_047.JPG
delta: 0.2073

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_sub_rerank_v04.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:22:07

Отлично. V04 уже показывает именно то поведение, которое мы хотели получить.

Результат:

```text
checked: 256
changed: 4
```

Из них три очень важных:

```
Ленина125_02.JPG
87_v33 -> 84_v33
sub: 84_v33_sub_2
image: 84_010.JPG
delta: +0.0633

Ленина125_04.JPG
87_v33 -> 84_v33
sub: 84_v33_sub_2
image: 84_010.JPG
delta: +0.0518

Ленина125_08.JPG
87_v33 -> 84_v33
sub: 84_v33_sub_2
image: 84_010.JPG
delta: +0.052
```

Это подтверждает гипотезу:

- глобальный V33 увидел сцену как `87`;
- внутри похожих адресов `84/87` subfingerprint нашёл конкретный ракурс;
- один и тот же кадр `84_010.JPG` подтверждает, что это не случайный шум.

То есть схема:

```
DINO global
     |
     | 87_v33
     |
TOP2:
84_v33
     |
     |
subfingerprint
     |
84_010.JPG
     |
84_v33
```

работает.

---

Очень интересный случай:

```
Шеболдаева8_06.JPG

87_v33 -> 92_v33

sub:
92_v33_sub_1

image:
92_047.JPG

delta:
+0.2073
```

Это уже не пограничный случай. Разница огромная:

```
+0.207
```

Значит глобальный fingerprint ошибся из-за похожего окружения, а subfingerprint фактически нашёл нужный объект.

---

Сравнение версий:

| Версия | Метод | Изменения |
|-|-|-:|
| V02 | все sub против всех | 130 ❌ |
| V03 | TOP1/TOP2 + centroid | 1 |
| V04 | TOP1/TOP2 + реальные кадры | 4 ✅ |

V04 выглядит наиболее правильным.

---

Следующий эксперимент я бы сделал **V05**, где изменим только одно:

Сейчас:

```
TOP1 + TOP2
```

Проверяем sub только у двух кандидатов.

Сделаем:

```
TOP5
```

но с защитой:

```
если TOP1 margin > 0.05
   не трогаем

если margin <= 0.05
   запускаем sub rerank TOP5
```

Почему:

У тебя в benchmark были случаи:

```
Ленина125
margin 0.0008

Зорге
0.0155

Радиаторный
0.0065
```

Вот именно там нужен sub.

А уверенные:

```
Ашхабадский
margin 0.0639
```

трогать нельзя.

Получится:

```
обычные фото:
DINO → адрес

сложные:
DINO → TOP5 → sub → адрес
```

Это уже будет почти финальная архитектура.

Следующий файл:

```bash
nano scripts/benchmark_sub_rerank_v05.py
```

Я бы делал именно его.

---

### 👤 **User** — 2026-08-15 20:25:52

Шеболдаева8_06.JPG  тут первоначально все верно, просто плохое фото и справа автобус, который ошибочно принимается за тарнсформатор. Надо сделать поиск не по всем субслепкам, ато только в пограничных случаях, когда есть вариант или/или. Или как вариант сделать праллельный поиск разного типа и сравнить потом соседи 87 / сублепок 87 / что то еще 88 - значит 87

---

### 🤖 **Assistant** — 2026-08-15 20:25:53

Да, это важное уточнение. Случай с **Шеболдаева8_06.JPG** показывает не ошибку глобального распознавания, а **ложное усиление subfingerprint**.

Сейчас V04 делает:

```
DINO TOP1
   |
   +-- проверяем sub TOP1/TOP2
   |
   +-- если один sub дал сильный score → меняем адрес
```

Проблема:

```
Шеболдаева8_06.JPG

DINO:
87_v33  ✅ правильно

но:
92_v33_sub_1
нашёл похожий объект (автобус)
и получил +0.207
```

То есть subfingerprint хорошо ищет похожие элементы, но не всегда знает, что это **тот же адрес**.

---

Я бы поменял архитектуру.

Не делать:

```
global → sub исправляет
```

А делать:

```
                 ┌─────────────┐
                 │ DINO global │
                 └──────┬──────┘
                        |
                    TOP-5
                        |
        ┌───────────────┼───────────────┐
        │               │               │
      87_v33        88_v33          92_v33
        │               │               │
    sub 87          sub 88          sub 92
        │               │               │
        └───────────────┼───────────────┘
                        |
                объединённый рейтинг
                        |
                  + соседи кадров
```

---

То есть subfingerprint становится **не заменой**, а дополнительным признаком.

Например:

## Фото Шеболдаева:

DINO:

```
87_v33       0.88
92_v33       0.84
88_v33       0.82
```

Sub:

```
92_sub       0.91  <-- автобус
87_sub       0.87
```

Но соседние кадры:

```
Шеболдаева_05
87

Шеболдаева_07
87
```

дают:

```
87 +2
92 +0
```

И итог:

```
87
```

---

Я бы ввёл три независимых голоса:

### 1. Global DINO

вес:

```
+10 * score
```

### 2. Sub fingerprint

только если:

```
margin < 0.03
```

вес:

```
+5 * sub_score
```

### 3. Sequence neighbors

если рядом:

```
предыдущий кадр = X
следующий кадр = X
```

то:

```
+8
```

---

Главное изменение:

**не запускать sub всегда.**

Только:

```
if margin < 0.03:
    запускаем sub rerank
else:
    доверяем global
```

Тогда:

Ашхабадский:

```
margin 0.0639

→ sub НЕ запускаем
```

Ленина125:

```
margin 0.0008

→ запускаем sub
```

Зорге:

```
margin 0.015

→ запускаем sub
```

Шеболдаева:

```
margin 0.0148

→ запускаем sub
```

но sub не сможет один изменить результат, потому что будут соседи.

---

Я бы следующим сделал не V05, а:

```
benchmark_hybrid_v01.py
```

Алгоритм:

1. Берём текущий `benchmark.json`.
2. Для каждого кадра:
   - TOP5 global.
3. Если margin < 0.03:
   - считаем sub только для этих 20-30% фото.
4. Складываем:
   - global score
   - sub score
   - neighbor votes.
5. Выводим:
   - old
   - new
   - почему изменилось.

Это будет уже очень близко к промышленной логике:

```
быстрый поиск → локальное уточнение → временная стабилизация
```

И ещё плюс: скорость останется почти как сейчас, потому что sub будет работать не на 256 фото, а примерно на 40-60 проблемных.

---

### 👤 **User** — 2026-08-15 20:26:53

давай

---

### 🤖 **Assistant** — 2026-08-15 20:26:55

Делаем **hybrid_v01**.

Создадим новый тестовый скрипт, не трогая основной pipeline.

```bash
nano scripts/benchmark_hybrid_v01.py
```

Вставляем:

```python
#!/usr/bin/env python3

import json
from pathlib import Path
from collections import defaultdict, Counter

import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder

PROJECT = Path(__file__).resolve().parent.parent

BENCHMARK = (
    PROJECT /
    "data/output/benchmark_sub_exp/benchmark.json"
)

SUB_DIR = (
    PROJECT /
    "data/fingerprints_sub_exp"
)

OUT = (
    PROJECT /
    "data/output/benchmark_hybrid_v01.json"
)

MARGIN_LIMIT = 0.03

GLOBAL_WEIGHT = 10.0
SUB_WEIGHT = 5.0
NEIGHBOR_WEIGHT = 8.0

def normalize(x):

    x=np.asarray(
        x,
        dtype=np.float32
    )

    n=np.linalg.norm(x)

    if n:
        x=x/n

    return x

def parent_id(x):

    if "_v33" in x:
        return x

    return x

def load_subs():

    result={}

    for d in SUB_DIR.iterdir():

        if not d.is_dir():
            continue

        emb=d/"embeddings.npy"

        if not emb.exists():
            continue

data=np.load(
            emb
        )

        data=np.array(
            [
                normalize(x)
                for x in data
            ]
        )

        result[d.name]=data

return result

def load_neighbors(rows):

    result={}

    for i,r in enumerate(rows):

        name=Path(
            r["file"]
        ).name

        result[name]=i

    return result

def get_neighbor_votes(rows, index):

    votes=Counter()

    for pos in [
        index-1,
        index+1,
    ]:

        if pos < 0:
            continue

        if pos >= len(rows):
            continue

r=rows[pos]

        votes[
            r["top1"]
        ] += 1

return votes

def main():

    print("="*80)
    print("HYBRID V01")
    print("="*80)

with open(
        BENCHMARK,
        encoding="utf-8"
    ) as f:

        data=json.load(f)

rows=data["results"]

settings=Settings()

    embedder=SceneEmbedder(
        settings
    )

subs=load_subs()

changed=[]

    checked=0

    rerank_count=0

for i,row in enumerate(rows):

        checked+=1

old=row["top1"]

scores=defaultdict(float)

# -------------------------
        # GLOBAL
        # -------------------------

        for k in range(1,6):

            fp=row.get(
                f"top{k}"
            )

            sc=row.get(
                f"top{k}_score"
            )

            if fp:

                scores[fp]+=(
                    float(sc)
                    *
                    GLOBAL_WEIGHT
                )

margin=row.get(
            "margin",
            1
        )

# -------------------------
        # SUB ONLY BORDER CASES
        # -------------------------

        if margin < MARGIN_LIMIT:

            rerank_count+=1

image=Path(
                row["file"]
            )

emb=embedder.embed_paths(
                [image]
            )[0]

emb=normalize(
                emb
            )

for parent in [
                row["top1"],
                row["top2"],
                row["top3"],
                row["top4"],
                row["top5"],
            ]:

for sub_id,sub_emb in subs.items():

                    if not sub_id.startswith(
                        parent
                    ):
                        continue

sim=max(
                        sub_emb @ emb
                    )

scores[parent]+=(
                        float(sim)
                        *
                        SUB_WEIGHT
                    )

# -------------------------
        # NEIGHBORS
        # -------------------------

        nv=get_neighbor_votes(
            rows,
            i
        )

for fp,n in nv.items():

            scores[fp]+=(
                n
                *
                NEIGHBOR_WEIGHT
            )

best=max(
            scores,
            key=scores.get
        )

if best != old:

            changed.append(
                {
                    "file":Path(
                        row["file"]
                    ).name,

                    "old":old,

                    "new":best,

                    "margin":margin,

                    "neighbor_votes":dict(nv),

                    "old_score":scores[old],

                    "new_score":scores[best],
                }
            )

OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

OUT.write_text(
        json.dumps(
            {
                "checked":checked,
                "rerank":rerank_count,
                "changed":len(changed),
                "results":changed,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

print()
    print(
        "checked:",
        checked
    )

    print(
        "sub rerank:",
        rerank_count
    )

    print(
        "changed:",
        len(changed)
    )

for x in changed[:50]:

        print()
        print(
            x["file"]
        )

        print(
            x["old"],
            "->",
            x["new"]
        )

        print(
            "neighbors:",
            x["neighbor_votes"]
        )

print()
    print(
        "saved:"
    )
    print(
        OUT
    )

if __name__=="__main__":
    main()
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v01.py
```

Ожидаем:

- `sub rerank` будет не 256, а только пограничные случаи;
- Шеболдаева не должна уйти в 92;
- Ленина125 должны остаться кандидатом на исправление;
- соседние кадры должны стабилизировать серии.

После вывода смотрим три блока:

1.

```text
sub rerank:
```

сколько реально сложных кадров.

2.

```text
changed:
```

сколько адресов поменялось.

3.

Особенно:

```text
Шеболдаева
Ленина125
Зорге
Радиаторный
```

Это будет первая версия настоящего "голосования признаков".

---

### 👤 **User** — 2026-08-15 20:27:45

checked: 256
sub rerank: 43
changed: 16

Ашхабадский_08.JPG
89_v33 -> 85_v33
neighbors: {'85_v33': 2}

Зорге_06.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 2}

Зорге_15.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 2}

Зорге_16.JPG
92_v33 -> 89_v33
neighbors: {'89_v33': 1, '95_v33': 1}

Зорге_17.jpg
95_v33 -> 92_v33
neighbors: {'92_v33': 1, '81_v33': 1}

Ленина125_01.JPG
84_v33 -> 87_v33
neighbors: {'79_v33': 1, '87_v33': 1}

Ленина125_02.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 2}

Ленина125_03.JPG
84_v33 -> 87_v33
neighbors: {'87_v33': 2}

Ленина125_04.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 2}

Ленина125_08.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 2}

Малиновского_к_Доватора_10.JPG
94_v33 -> 89_v33
neighbors: {'89_v33': 2}

Малиновского_к_Стачки_02.JPG
90_v33 -> 89_v33
neighbors: {'90_v33': 1, '89_v33': 1}

Малиновского_к_Стачки_03.JPG
89_v33 -> 90_v33
neighbors: {'90_v33': 2}

Малиновского_к_Стачки_04.JPG
90_v33 -> 89_v33
neighbors: {'89_v33': 2}

Радиаторный_24.JPG
86_v33 -> 89_v33
neighbors: {'94_v33': 1, '89_v33': 1}

Рубиновый_12.JPG
91_v33 -> 94_v33
neighbors: {'91_v33': 1, '93_v33': 1}

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v01.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:27:47

Результат интересный. Самое главное — **архитектура уже начинает работать**, но текущие веса слишком сильно доверяют соседям.

Сейчас у нас:

```
GLOBAL DINO
    +
SUB (только margin < 0.03)
    +
NEIGHBOR
```

и получили:

```
checked: 256
sub rerank: 43
changed: 16
```

---

### Хорошие изменения

Вот эти выглядят правильно:

```
Ашхабадский_08
89 -> 85
neighbors: {'85_v33': 2}
```

Это ровно то, что хотели. Один кадр ошибся, последовательность исправила.

---

```
Зорге_06
89 -> 92

Зорге_15
89 -> 92
```

тоже хорошо. Серия подтянулась.

---

```
Ленина125_02
87 -> 84

Ленина125_04
87 -> 84

Ленина125_08
87 -> 84
```

Это подтверждает V04: subfingerprint реально видит правильный адрес.

---

### Но есть проблема

Вот:

```
Зорге_16
92 -> 89

neighbors:
{'89_v33':1,'95_v33':1}
```

и:

```
Зорге_17
95 -> 92

neighbors:
{'92_v33':1,'81_v33':1}
```

Здесь соседей недостаточно. Они голосуют только по 1 кадру и могут качать результат.

---

Ещё:

```
Ленина125_01
84 -> 87

neighbors:
{'79_v33':1,'87_v33':1}
```

Это опасно. Соседний кадр 79 вообще не должен участвовать как равный голос.

---

## Главное изменение V02

Сейчас:

```python
NEIGHBOR_WEIGHT = 8
```

слишком много.

Сделаем:

```python
NEIGHBOR_WEIGHT = 3
```

Но добавим правило:

**соседи работают только если оба соседа одинаковые.**

Сейчас:

```
слева 87
справа 84

→ всё равно голосуем
```

Нужно:

```
слева 84
справа 84

→ +6

иначе:
→ ничего
```

То есть:

```text
если два соседа совпали:
    сильный бонус

если только один:
    игнорируем
```

---

Получится:

```
Ашхабадский_08

left 85
right 85

+6
исправляем

Зорге_16

left 89
right 95

0
не трогаем
```

---

Ещё один момент.

Сейчас sub включается:

```
margin < 0.03
```

Я бы оставил.

43 кадра из 256:

```
17%
```

это нормально.

---

Следующий шаг:

делаем **hybrid_v02**:

Изменения только:

1. Neighbor:

```python
if left == right:
    +6
else:
    0
```

2. Убираем одиночные голоса.

3. Sub оставляем.

4. Global оставляем главным.

И ожидаем:

- 16 изменений уменьшится примерно до 8-10;
- Ленина125 останется исправляться;
- Шеболдаева не уйдёт;
- случайные качели исчезнут.

Команда:

```bash
cp scripts/benchmark_hybrid_v01.py scripts/benchmark_hybrid_v02.py
nano scripts/benchmark_hybrid_v02.py
```

Меняем только блок `NEIGHBOR`.

Это уже будет ближе к финальной логике сортировки 200-300 фото в день.

---

### 👤 **User** — 2026-08-15 20:29:08

продолжаем

---

### 🤖 **Assistant** — 2026-08-15 20:29:09

Продолжаем с **hybrid_v02**. Сейчас меняем только логику соседей.

Открываем копию:

```bash
cp scripts/benchmark_hybrid_v01.py scripts/benchmark_hybrid_v02.py

nano scripts/benchmark_hybrid_v02.py
```

Найди:

```python
NEIGHBOR_WEIGHT = 8.0
```

замени:

```python
NEIGHBOR_WEIGHT = 6.0
```

---

Теперь найди функцию:

```python
def get_neighbor_votes(rows, index):
```

и замени её полностью на:

```python
def get_neighbor_votes(rows, index):

    votes = Counter()

    left = None
    right = None

if index - 1 >= 0:
        left = rows[index - 1]["top1"]

if index + 1 < len(rows):
        right = rows[index + 1]["top1"]

# Сильный соседский голос только когда
    # оба соседних кадра согласны

    if left is not None and right is not None:

        if left == right:
            votes[left] = 1

return votes
```

---

Ещё немного усилим защиту от sub-ошибок.

Найди:

```python
scores[parent]+=(
    float(sim)
    *
    SUB_WEIGHT
)
```

замени на:

```python
if sim > 0.80:

    scores[parent]+=(
        float(sim)
        *
        SUB_WEIGHT
    )
```

То есть слабые совпадения sub больше не будут влиять.

---

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v02.py
```

Ожидаем:

```
checked: 256
sub rerank: ~43
changed: меньше 16
```

Особенно проверяем:

### Должно остаться:

```
Ленина125_02
87 -> 84

Ленина125_04
87 -> 84

Ленина125_08
87 -> 84
```

### Должно исчезнуть:

```
Шеболдаева8_06
87 -> 92
```

### Должны перестать качаться:

```
Зорге_16
Зорге_17
Ленина125_01
```

После запуска пришли блок:

```
checked:
sub rerank:
changed:
```

и список изменений. Следующим шагом уже будем делать **финальный decision score**, где будет храниться не только победитель, но и "почему выбран адрес" (global/sub/sequence).

---

### 👤 **User** — 2026-08-15 20:32:16

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/benchmark_hybrid_v02.py
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/benchmark_hybrid_v02.py", line 264
    if sim > 0.80:
                  ^
IndentationError: unindent does not match any outer indentation level
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:32:18

Ошибка только по отступам. Python увидел, что блок `if sim > 0.80:` вставлен с другим уровнем отступа.

Сначала покажи участок, чтобы не гадать:

```bash
nl -ba scripts/benchmark_hybrid_v02.py | sed -n '245,275p'
```

Скорее всего сейчас там что-то вроде:

```python
                    sim=max(
                        sub_emb @ emb
                    )

if sim > 0.80:

                    scores[parent]+=(
                        float(sim)
                        *
                        SUB_WEIGHT
                    )
```

А должно быть **ровно так**:

```python
                    sim=max(
                        sub_emb @ emb
                    )

                    if sim > 0.80:

                        scores[parent]+=(
                            float(sim)
                            *
                            SUB_WEIGHT
                        )
```

То есть `if sim` должен быть на одном уровне с `sim=max(...)` внутри цикла:

```text
for parent:
    for sub_id:
        if not startswith:
            continue

        sim=max()

        if sim:
            scores +=
```

После исправления проверить:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v02.py
```

Если ошибок нет:

```bash
uv run python scripts/benchmark_hybrid_v02.py
```

Пришли результат.

---

### 👤 **User** — 2026-08-15 20:32:27

давай готовый

---

### 🤖 **Assistant** — 2026-08-15 20:32:28

Замени файл целиком.

```bash
nano scripts/benchmark_hybrid_v02.py
```

Вставь:

```python
#!/usr/bin/env python3

import json
from pathlib import Path
from collections import defaultdict, Counter

import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder

PROJECT = Path(__file__).resolve().parent.parent

BENCHMARK = (
    PROJECT /
    "data/output/benchmark_sub_exp/benchmark.json"
)

SUB_DIR = (
    PROJECT /
    "data/fingerprints_sub_exp"
)

OUT = (
    PROJECT /
    "data/output/benchmark_hybrid_v02.json"
)

MARGIN_LIMIT = 0.03

GLOBAL_WEIGHT = 10.0
SUB_WEIGHT = 5.0
NEIGHBOR_WEIGHT = 6.0

def normalize(x):

    x = np.asarray(
        x,
        dtype=np.float32
    )

    n = np.linalg.norm(x)

    if n:
        x = x / n

    return x

def load_subs():

    result = {}

    for d in SUB_DIR.iterdir():

        if not d.is_dir():
            continue

        emb_file = d / "embeddings.npy"

        if not emb_file.exists():
            continue

        data = np.load(
            emb_file
        )

        data = np.array(
            [
                normalize(x)
                for x in data
            ]
        )

        result[d.name] = data

return result

def get_neighbor_votes(rows, index):

    votes = Counter()

    left = None
    right = None

if index - 1 >= 0:
        left = rows[index - 1]["top1"]

if index + 1 < len(rows):
        right = rows[index + 1]["top1"]

# Голосуем только если оба соседа совпадают

    if left is not None and right is not None:

        if left == right:
            votes[left] = 1

return votes

def main():

    print("=" * 80)
    print("HYBRID V02")
    print("=" * 80)

with open(
        BENCHMARK,
        encoding="utf-8"
    ) as f:

        data = json.load(f)

rows = data["results"]

settings = Settings()

    embedder = SceneEmbedder(
        settings
    )

subs = load_subs()

changed = []

    rerank_count = 0

for i, row in enumerate(rows):

old = row["top1"]

scores = defaultdict(float)

# -------------------------
        # GLOBAL DINO
        # -------------------------

        for k in range(1, 6):

            fp = row.get(
                f"top{k}"
            )

            sc = row.get(
                f"top{k}_score"
            )

            if fp:

                scores[fp] += (
                    float(sc)
                    *
                    GLOBAL_WEIGHT
                )

margin = row.get(
            "margin",
            1
        )

# -------------------------
        # SUB ONLY BORDER CASES
        # -------------------------

        if margin < MARGIN_LIMIT:

            rerank_count += 1

image = Path(
                row["file"]
            )

emb = embedder.embed_paths(
                [image]
            )[0]

emb = normalize(
                emb
            )

candidates = [
                row.get(f"top{k}")
                for k in range(1, 6)
            ]

for parent in candidates:

                if parent is None:
                    continue

for sub_id, sub_emb in subs.items():

                    if not sub_id.startswith(
                        parent
                    ):
                        continue

sim = max(
                        sub_emb @ emb
                    )

# защита от случайных совпадений

                    if sim > 0.80:

                        scores[parent] += (
                            float(sim)
                            *
                            SUB_WEIGHT
                        )

# -------------------------
        # SEQUENCE NEIGHBORS
        # -------------------------

        neighbor_votes = get_neighbor_votes(
            rows,
            i
        )

for fp, count in neighbor_votes.items():

            scores[fp] += (
                count
                *
                NEIGHBOR_WEIGHT
            )

best = max(
            scores,
            key=scores.get
        )

if best != old:

            changed.append(
                {
                    "file": Path(
                        row["file"]
                    ).name,

                    "old": old,

                    "new": best,

                    "margin": margin,

                    "neighbors": dict(
                        neighbor_votes
                    ),

                    "old_score": scores[old],

                    "new_score": scores[best],
                }
            )

OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

OUT.write_text(
        json.dumps(
            {
                "checked": len(rows),
                "sub_rerank": rerank_count,
                "changed": len(changed),
                "results": changed,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

print()
    print(
        "checked:",
        len(rows)
    )

    print(
        "sub rerank:",
        rerank_count
    )

    print(
        "changed:",
        len(changed)
    )

for x in changed:

        print()
        print(
            x["file"]
        )

        print(
            x["old"],
            "->",
            x["new"]
        )

        print(
            "neighbors:",
            x["neighbors"]
        )

print()
    print("saved:")
    print(OUT)

if __name__ == "__main__":
    main()
```

После вставки:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v02.py
```

Если без ошибок:

```bash
uv run python scripts/benchmark_hybrid_v02.py
```

Ждём в первую очередь:

- `Шеболдаева8_06.JPG` — не должен уйти с 87
- `Ленина125_02/04/08` — должны остаться 84
- количество `changed` должно быть меньше 16.

---

### 👤 **User** — 2026-08-15 20:33:40

[SceneEmbedder] Ready.

checked: 256
sub rerank: 43
changed: 19

Ашхабадский_08.JPG
89_v33 -> 85_v33
neighbors: {'85_v33': 1}

Зорге_06.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_15.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_16.JPG
92_v33 -> 94_v33
neighbors: {}

КА_12.JPG
81_v33 -> 85_v33
neighbors: {'81_v33': 1}

Ленина125_02.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_03.JPG
84_v33 -> 87_v33
neighbors: {'87_v33': 1}

Ленина125_04.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_08.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Малиновского_к_Доватора_10.JPG
94_v33 -> 89_v33
neighbors: {'89_v33': 1}

Малиновского_к_Стачки_03.JPG
89_v33 -> 90_v33
neighbors: {'90_v33': 1}

Малиновского_к_Стачки_04.JPG
90_v33 -> 89_v33
neighbors: {'89_v33': 1}

Нагибина24_10.JPG
83_v33 -> 85_v33
neighbors: {'83_v33': 1}

Нагибина24_11.JPG
83_v33 -> 94_v33
neighbors: {'83_v33': 1}

Рубиновый_04.JPG
91_v33 -> 85_v33
neighbors: {'91_v33': 1}

Рубиновый_07.JPG
91_v33 -> 94_v33
neighbors: {'91_v33': 1}

Рубиновый_08.JPG
91_v33 -> 85_v33
neighbors: {'91_v33': 1}

Рубиновый_12.JPG
91_v33 -> 94_v33
neighbors: {}

Стачки_41_10.JPG
93_v33 -> 95_v33
neighbors: {'93_v33': 1}

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v02.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:33:42

Результат показал важную вещь: **соседи теперь не главная проблема**. Мы убрали сильное влияние последовательности, но выяснилось, что сами sub-реранжеры иногда перетягивают.

Сравнение:

### V01
```
changed: 16
```

### V02
```
changed: 19
```

То есть стало хуже. Причина видна:

```
neighbors: {'xxx':1}
```

Даже один сосед всё ещё добавляет голос, потому что функция:

```python
if left == right:
    votes[left] = 1
```

не сработала, но потом старый `scores` уже получил влияние sub.

---

Самые подозрительные:

## 1. Рубиновый

```
Рубиновый_04
91 -> 85

Рубиновый_08
91 -> 85

Рубиновый_12
91 -> 94
```

Это классическая ситуация: **один адрес имеет похожую сцену**. Subfingerprint 85/94 ошибочно цепляет.

Здесь нужен не sub-only rerank, а:

```
GLOBAL TOP кандидаты
        |
        |
        +---- если top1/top2 рядом
                  |
                  +--- sub сравнение
                  |
                  +--- соседняя серия
```

То есть sub нельзя разрешать менять на любой адрес.

---

## 2. КА_12

```
КА_12
81 -> 85
```

Очень подозрительно.

До этого:

```
КА_01 ... КА_16
81
```

одна фотография должна остаться 81.

Это значит:

sub увидел похожий объект, но серия говорит 81.

---

## 3. Нагибина

```
Нагибина24_10
83 -> 85

Нагибина24_11
83 -> 94
```

тоже нельзя менять.

---

Получается правильная схема:

# Hybrid V03

Не:

```
global
 + 
sub может поменять
```

А:

```
global TOP1

если margin > 0.03:
    оставить

если margin < 0.03:

    смотрим TOP1 и TOP2

    sub сравнивает только их

    если sub выигрывает:
          заменить

    иначе:
          оставить
```

То есть ограничиваем пространство решения.

---

Ещё добавим коэффициент:

Сейчас:

```
SUB_WEIGHT = 5
```

слишком много.

Делаем:

```python
SUB_WEIGHT = 2.5
```

И условие:

```python
if sim > 0.85
```

вместо:

```python
0.80
```

---

Ожидаем:

- Шеболдаева останется 87
- КА останется 81
- Нагибина останется 83
- Ленина125 02/04/08 исправятся на 84
- Ашхабадский/Зорге/Малиновского будут исправляться соседями

Делаем следующий файл:

```bash
cp scripts/benchmark_hybrid_v02.py scripts/benchmark_hybrid_v03.py
nano scripts/benchmark_hybrid_v03.py
```

Меняем:

```python
SUB_WEIGHT = 2.5
```

и:

```python
if sim > 0.85:
```

Но главное изменение — блок кандидатов.

Сейчас у тебя:

```python
candidates = [
    row.get(f"top{k}")
    for k in range(1,6)
]
```

заменить на:

```python
candidates = [
    row.get("top1"),
    row.get("top2"),
]
```

Это будет уже ближе к рабочей схеме:

**DINO глобальный поиск → только пограничный TOP2 → subfingerprint → последовательность.**

После запуска сравним V01/V02/V03.

---

### 👤 **User** — 2026-08-15 20:34:17

давай готовый файл

---

### 🤖 **Assistant** — 2026-08-15 20:34:19

Делаем `benchmark_hybrid_v03.py`. Полностью заменяем файл.

Команда:

```bash
nano scripts/benchmark_hybrid_v03.py
```

Вставь:

```python
#!/usr/bin/env python3

import json
from pathlib import Path
from collections import defaultdict, Counter

import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder

PROJECT = Path(__file__).resolve().parent.parent

BENCHMARK = (
    PROJECT /
    "data/output/benchmark_sub_exp/benchmark.json"
)

SUB_DIR = (
    PROJECT /
    "data/fingerprints_sub_exp"
)

OUT = (
    PROJECT /
    "data/output/benchmark_hybrid_v03.json"
)

MARGIN_LIMIT = 0.03

GLOBAL_WEIGHT = 10.0
SUB_WEIGHT = 2.5
NEIGHBOR_WEIGHT = 6.0

def normalize(x):

    x = np.asarray(
        x,
        dtype=np.float32
    )

    n = np.linalg.norm(x)

    if n > 0:
        x = x / n

    return x

def load_subs():

    result = {}

    for d in sorted(SUB_DIR.iterdir()):

        if not d.is_dir():
            continue

        f = d / "embeddings.npy"

        if not f.exists():
            continue

        emb = np.load(
            f
        )

        emb = np.array(
            [
                normalize(x)
                for x in emb
            ]
        )

        result[d.name] = emb

return result

def get_neighbor_votes(rows, index):

    votes = Counter()

if index <= 0:
        return votes

if index >= len(rows)-1:
        return votes

left = rows[index-1]["top1"]
    right = rows[index+1]["top1"]

# только полное согласие

    if left == right:

        votes[left] = 1

return votes

def main():

    print("=" * 80)
    print("HYBRID V03")
    print("=" * 80)

with open(
        BENCHMARK,
        encoding="utf-8"
    ) as f:

        data = json.load(f)

rows = data["results"]

settings = Settings()

    embedder = SceneEmbedder(
        settings
    )

subs = load_subs()

changed = []
    sub_count = 0

for i, row in enumerate(rows):

        old = row["top1"]

scores = defaultdict(float)

#
        # GLOBAL TOP-5
        #

        for k in range(1, 6):

            fp = row.get(
                f"top{k}"
            )

            sc = row.get(
                f"top{k}_score"
            )

            if fp:

                scores[fp] += (
                    float(sc)
                    *
                    GLOBAL_WEIGHT
                )

#
        # SUB ONLY BORDER CASES
        #

        margin = row.get(
            "margin",
            1
        )

if margin < MARGIN_LIMIT:

            sub_count += 1

image = Path(
                row["file"]
            )

query = embedder.embed_paths(
                [image]
            )[0]

            query = normalize(
                query
            )

#
            # ТОЛЬКО TOP1 и TOP2
            #

            candidates = [
                row.get("top1"),
                row.get("top2"),
            ]

for parent in candidates:

                if not parent:
                    continue

for sub_id, sub_emb in subs.items():

                    if not sub_id.startswith(
                        parent
                    ):
                        continue

sim = max(
                        sub_emb @ query
                    )

if sim > 0.85:

                        scores[parent] += (
                            float(sim)
                            *
                            SUB_WEIGHT
                        )

#
        # SEQUENCE
        #

        neighbors = get_neighbor_votes(
            rows,
            i
        )

for fp in neighbors:

            scores[fp] += (
                NEIGHBOR_WEIGHT
            )

best = max(
            scores,
            key=scores.get
        )

if best != old:

            changed.append(
                {
                    "file":
                        Path(
                            row["file"]
                        ).name,

                    "old":
                        old,

                    "new":
                        best,

                    "margin":
                        margin,

                    "neighbors":
                        dict(neighbors),

                    "old_score":
                        scores[old],

                    "new_score":
                        scores[best],
                }
            )

OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

OUT.write_text(
        json.dumps(
            {
                "checked":
                    len(rows),

                "sub_rerank":
                    sub_count,

                "changed":
                    len(changed),

                "results":
                    changed,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

print()
    print(
        "checked:",
        len(rows)
    )

    print(
        "sub rerank:",
        sub_count
    )

    print(
        "changed:",
        len(changed)
    )

for x in changed:

        print()
        print(
            x["file"]
        )

        print(
            x["old"],
            "->",
            x["new"]
        )

        print(
            "neighbors:",
            x["neighbors"]
        )

print()
    print("saved:")
    print(OUT)

if __name__ == "__main__":
    main()
```

Проверка:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v03.py
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v03.py
```

Критические проверки после результата:

1. `Шеболдаева8_06.JPG` должна остаться:
```
87_v33
```

2. должны исправиться:
```
Ленина125_02
Ленина125_04
Ленина125_08
```

3. не должны появиться:
```
КА_*
81 -> 84/85
```

4. `changed` ожидаем примерно:
```
5-10
```

Это уже схема, которую можно дальше превращать в рабочий recognizer:
**DINO TOP-5 → margin gate → TOP2 sub → sequence consensus → адрес**.

---

### 👤 **User** — 2026-08-15 20:35:23

checked: 256
sub rerank: 43
changed: 10

Ашхабадский_08.JPG
89_v33 -> 85_v33
neighbors: {'85_v33': 1}

Зорге_06.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_15.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Ленина125_02.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_03.JPG
84_v33 -> 87_v33
neighbors: {'87_v33': 1}

Ленина125_04.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_08.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Малиновского_к_Доватора_10.JPG
94_v33 -> 89_v33
neighbors: {'89_v33': 1}

Малиновского_к_Стачки_03.JPG
89_v33 -> 90_v33
neighbors: {'90_v33': 1}

Малиновского_к_Стачки_04.JPG
90_v33 -> 89_v33
neighbors: {'89_v33': 1}

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v03.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:35:24

Отлично. Это уже намного ближе к рабочей схеме.

Сравнение:

| Версия | changed | Комментарий |
|-|-:|-|
| hybrid_v01 | 16 | слишком сильный sub/neighbor |
| hybrid_v02 | 19 | хуже, много ложных перестановок |
| **hybrid_v03** | **10** | уже стабильная логика |

Сейчас изменения выглядят логично:

### Исправленные правильно

```
Ашхабадский_08
89 -> 85
```

```
Зорге_06
89 -> 92
```

```
Зорге_15
89 -> 92
```

```
Ленина125_02
87 -> 84

Ленина125_04
87 -> 84

Ленина125_08
87 -> 84
```

Это именно те случаи, ради которых мы делали subfingerprint.

---

### Остался один спорный:

```
Ленина125_03
84 -> 87
neighbors: {'87_v33':1}
```

Вот здесь интересно.

Ранее у нас было:

```
Ленина125_02 87 -> 84
Ленина125_04 87 -> 84
Ленина125_08 87 -> 84
```

То есть серия выглядит:

```
02 84
03 ?
04 84
08 84
```

Сейчас алгоритм поменял 03 обратно на 87.

Я бы **не трогал пока**. Это может быть реальная другая сторона дома/баннера.

---

### Малиновского:

```
94 -> 89
89 -> 90
90 -> 89
```

Это ожидаемый классический случай "соседние адреса похожи".

Тут можно улучшить следующим этапом.

---

## Следующий шаг — hybrid_v04

Я бы не усиливал sub. Сейчас баланс хороший.

Добавляем только одно правило:

### Серийный консенсус

Если в окне ±3 кадра:

```
89
?
89
```

то середину можно подтянуть.

Например:

```
89
90
89
```

→ 89

Но только если:

- глобальный margin низкий
- соседние два кадра совпадают

То есть:

```
A ? A
```

исправляем.

Но:

```
A ? B
```

не трогаем.

---

Это даст:

```
Малиновского_к_Стачки_03
89 -> 90
```

скорее всего вернётся.

И:

```
Ленина125_03
84 -> 87
```

останется, потому что:

```
84 ? 84
```

будет сильнее.

Я бы сделал сейчас `hybrid_v04` именно с этим одним изменением.

Команда:

```bash
cp scripts/benchmark_hybrid_v03.py scripts/benchmark_hybrid_v04.py
nano scripts/benchmark_hybrid_v04.py
```

Добавляем после блока:

```python
# SEQUENCE
neighbors = get_neighbor_votes(
    rows,
    i
)
```

логику окна:

```python
window_votes = Counter()

for j in range(
    max(0, i-3),
    min(len(rows), i+4)
):
    if j == i:
        continue

    fp = rows[j]["top1"]
    window_votes[fp] += 1

for fp, count in window_votes.items():

    if count >= 2:
        scores[fp] += 3
```

То есть не один сосед, а **два подтверждения в окне**.

После этого ожидаю:

```
changed: 6-8
```

И это уже будет практически финальный пайплайн:

```
DINO global
      ↓
margin gate
      ↓
TOP2 subfingerprint
      ↓
sequence consensus
      ↓
address
```

Следующий тест уже можно будет гонять на папке из реальных 200-300 фотографий дня.

---

### 👤 **User** — 2026-08-15 20:37:26

давай готовый файл или исправь с sed

---

### 🤖 **Assistant** — 2026-08-15 20:37:28

Лучше не переписывать весь файл. Сделаем точечное исправление через `python`-замену (надёжнее, чем `sed` для больших блоков).

Сначала сделай копию:

```bash
cp scripts/benchmark_hybrid_v03.py scripts/benchmark_hybrid_v04.py
```

Теперь вставляем окно консенсуса.

Выполни:

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v04.py")

s = p.read_text(encoding="utf-8")

old = '''        for fp in neighbors:

            scores[fp] += (
                NEIGHBOR_WEIGHT
            )

best = max(
'''

new = '''        for fp in neighbors:

            scores[fp] += (
                NEIGHBOR_WEIGHT
            )

# --------------------------------------------------
        # SEQUENCE WINDOW CONSENSUS
        #
        # Используем только повторяющиеся адреса
        # в небольшом окне вокруг кадра.
        # Один сосед не считается доказательством.
        # --------------------------------------------------

        window_votes = Counter()

        for j in range(
            max(0, i - 3),
            min(len(rows), i + 4)
        ):

            if j == i:
                continue

            fp = rows[j]["top1"]

            if fp:
                window_votes[fp] += 1

for fp, count in window_votes.items():

            if count >= 2:

                scores[fp] += 3.0

best = max(
'''

if old not in s:
    raise SystemExit(
        "BLOCK NOT FOUND"
    )

s = s.replace(
    old,
    new
)

p.write_text(
    s,
    encoding="utf-8"
)

print("patched:", p)
PY
```

Проверка:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v04.py
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v04.py
```

Ожидаем:

- `Ленина125_02/04/08` остаются 84
- `Шеболдаева8_06` отсутствует в изменениях
- `Малиновского_к_Стачки_03/04` должны стать стабильнее
- `changed` желательно ≤ 8

После запуска пришли только:

```text
checked:
sub rerank:
changed:
```

и список `CHANGED`.

---

### 👤 **User** — 2026-08-15 20:37:49

hybrid_v03.py scripts/benchmark_hybrid_v04.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v04.py")

s = p.read_text(encoding="utf-8")

old = '''        for fp in neighbors:

            scores[fp] += (
                NEIGHBOR_WEIGHT
            )

best = max(
'''

new = '''        for fp in neighbors:

            scores[fp] += (
                NEIGHBOR_WEIGHT
PYint("patched:", p)OUND"] += 3.0otes.items():--------------
BLOCK NOT FOUND

---

### 🤖 **Assistant** — 2026-08-15 20:37:50

Похоже, вставка в терминал оборвалась: часть `PY` попала внутрь текста, поэтому блок не заменился. Файл `hybrid_v04.py` скорее всего остался без изменений.

Сделаем проще — через `grep` найдём точное место.

Выполни:

```bash
grep -n "for fp in neighbors" -A12 scripts/benchmark_hybrid_v04.py
```

Скорее всего там отличается от моего шаблона.

Но можно сразу сделать более надёжный патч по строке `best = max(`.

Запусти:

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v04.py")

s = p.read_text(encoding="utf-8")

marker = "        best = max(\n"

insert = r'''
        # --------------------------------------------------
        # SEQUENCE WINDOW CONSENSUS
        #
        # Учитываем только повторение адреса
        # в окне ±3 кадров.
        # Один сосед не является доказательством.
        # --------------------------------------------------

        window_votes = Counter()

        for j in range(
            max(0, i - 3),
            min(len(rows), i + 4)
        ):

            if j == i:
                continue

            fp = rows[j]["top1"]

            if fp:
                window_votes[fp] += 1

for fp, count in window_votes.items():

            if count >= 2:
                scores[fp] += 3.0

'''

if marker not in s:
    raise SystemExit("marker not found")

s = s.replace(
    marker,
    insert + marker,
    1
)

p.write_text(
    s,
    encoding="utf-8"
)

print("patched", p)
PY
```

Проверка:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v04.py
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v04.py
```

Если снова будет ошибка — пришли:

```bash
nl -ba scripts/benchmark_hybrid_v04.py | sed -n '180,260p'
```

Сейчас у нас уже хорошая база: `hybrid_v03` — это рабочий вариант, поэтому даже если v04 не зайдёт, ничего не потеряно.

---

### 👤 **User** — 2026-08-15 20:38:15

max(0, i - 3),
PYint("patched", p)"("marker not found")ems():
patched scripts/benchmark_hybrid_v04.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:38:17

Отлично, патч применился:

```text
patched scripts/benchmark_hybrid_v04.py
```

Теперь сначала проверяем синтаксис:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v04.py
```

Если ошибок нет — запускаем:

```bash
uv run python scripts/benchmark_hybrid_v04.py
```

После результата сравним с v03. Особенно смотрим:

1. `changed`
2. исчезли ли:
```
Малиновского_к_Стачки_03
Малиновского_к_Стачки_04
```

3. не появились ли ложные:
```
КА_*
Шеболдаева8_06
Нагибина24_*
```

Если v04 даст хуже — оставляем v03 как базовую и будем менять только веса консенсуса. Сейчас у нас уже есть контрольная точка.

---

### 👤 **User** — 2026-08-15 20:38:56

checked: 256
sub rerank: 43
changed: 15

Ашхабадский_08.JPG
89_v33 -> 85_v33
neighbors: {'85_v33': 1}

Зорге_06.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_15.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_17.jpg
95_v33 -> 92_v33
neighbors: {}

Ленина125_01.JPG
84_v33 -> 87_v33
neighbors: {}

Ленина125_02.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_03.JPG
84_v33 -> 87_v33
neighbors: {'87_v33': 1}

Ленина125_04.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_08.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Малиновского_к_Доватора_10.JPG
94_v33 -> 89_v33
neighbors: {'89_v33': 1}

Малиновского_к_Стачки_03.JPG
89_v33 -> 90_v33
neighbors: {'90_v33': 1}

Малиновского_к_Стачки_04.JPG
90_v33 -> 89_v33
neighbors: {'89_v33': 1}

Малиновского_к_Стачки_05.JPG
89_v33 -> 90_v33
neighbors: {}

Радиаторный_24.JPG
86_v33 -> 94_v33
neighbors: {}

Радиаторный_25.JPG
89_v33 -> 94_v33
neighbors: {}

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v03.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:38:57

Результат показал важный момент: **hybrid_v04 хуже v03**.

Сравнение:

| Версия | changed |
|-|-:|
| hybrid_v03 | **10** |
| hybrid_v04 | 15 |

Причина — окно ±3 оказалось слишком агрессивным. Оно начало тянуть соседние адреса там, где глобальный DINO был уже правильный.

Особенно плохие новые изменения:

```text
Зорге_17.jpg
95 -> 92
neighbors: {}

Ленина125_01.JPG
84 -> 87
neighbors: {}

Малиновского_к_Стачки_05.JPG
89 -> 90
neighbors: {}

Радиаторный_24.JPG
86 -> 94
Радиаторный_25.JPG
89 -> 94
```

Там нет подтверждения соседей, а изменение произошло из-за общего score.

---

Возвращаемся к v03 как базе.

Но я бы сделал **hybrid_v05 не с окном, а с более строгим правилом**:

### Новая логика:

Соседи разрешают изменение только если:

```
left == right
```

и:

```
margin < 0.03
```

То есть только:

```
89
?
89
```

может исправиться.

Но:

```
89
90
89
```

не трогаем.

И дополнительно:

если subfingerprint дал прирост:

```
sub_score - global_score > 0.05
```

тогда разрешаем.

Получается:

```
DINO TOP5
    |
    +-- высокий margin
    |       оставить
    |
    +-- низкий margin
            |
            +-- subfingerprint
            |
            +-- строгий соседний консенсус
```

Это ближе к промышленной логике.

---

Сейчас сделаем v05:

```bash
cp scripts/benchmark_hybrid_v03.py scripts/benchmark_hybrid_v05.py
```

И уберём из v04 окно.

Фактически v05 будет:

- база v03
- добавить только:
  - строгий `left == right`
  - без окна
  - без усиления всех повторов

Ожидаемый результат:

```
changed: 6-8
```

и исчезнут ложные:

```
Радиаторный
Зорге_17
Ленина125_01
```

Сейчас направление правильное: **subfingerprint должен быть не вторым классификатором, а арбитром спорных случаев**. Именно это мы и проверяем.

---

### 👤 **User** — 2026-08-15 20:39:51

продолжаем

---

### 🤖 **Assistant** — 2026-08-15 20:39:53

Продолжаем. Делаем **hybrid_v05** от стабильного `v03`, не от v04.

Цель:
- глобальный DINO остаётся главным;
- subfingerprint вмешивается только в спорных случаях;
- соседей используем только как подтверждение, а не как самостоятельный голос.

Сначала копия:

```bash
cp scripts/benchmark_hybrid_v03.py scripts/benchmark_hybrid_v05.py
```

Посмотрим место принятия решения:

```bash
grep -n "changed\|neighbors\|best" scripts/benchmark_hybrid_v05.py
```

и:

```bash
nl -ba scripts/benchmark_hybrid_v05.py | sed -n '180,280p'
```

Нам нужно найти блок примерно вида:

```python
if best != original:
    changed += 1
```

Там заменим логику на:

```python
allow_change = False

# 1. Сильный subfingerprint
if sub_delta > 0.05:
    allow_change = True

# 2. Или строгий соседний консенсус
if (
    left_fp
    and right_fp
    and left_fp == right_fp
):
    allow_change = True

if allow_change and best != original:
    changed += 1
```

Важно: **никаких `window_votes` и голосов ±3 кадров**.

После правки:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v05.py
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v05.py | tee output/hybrid_v05.log
```

Смотрим только итог:

```text
checked:
sub rerank:
changed:
```

и список изменённых.

Ожидаем, что:
- `Ленина125_02/04/08` останутся исправляться 87→84;
- `Шеболдаева8_06` не тронется;
- `Радиаторный_24/25` не будут прыгать;
- `changed` вернётся примерно к 7–10.

После этого уже можно будет переходить к следующему уровню: **двухступенчатый recognizer**:

```
DINO global TOP-5
        |
        v
только кандидаты 2-3 близких адресов
        |
        v
subfingerprint
        |
        v
sequence consensus
        |
        v
final address
```

Это будет уже почти рабочий промышленный пайплайн.

---

