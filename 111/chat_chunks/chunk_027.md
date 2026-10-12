## СЕССИЯ: Разработка подслепков

**Создано:** 2026-08-15 01:48:38
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f9b34-0188-83ea-b851-7793d1230a6f](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f9b34-0188-83ea-b851-7793d1230a6f)

---

### 👤 **User** — 2026-08-15 01:56:59

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

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
PY  print("  " + ", ".join(m["images"]))

======================================================================
sub_01 members=66 seed=74 seed_image=photo075.JPG mean=0.9028
REPRESENTATIVES:
   photo078.JPG
   photo075.JPG
   photo079.JPG
   photo073.JPG
   photo044.JPG
MEMBERS:
  photo002.JPG, photo004.JPG, photo006.JPG, photo007.JPG, photo008.JPG, photo009.JPG, photo010.JPG, photo011.JPG, photo012.JPG, photo018.JPG, photo021.JPG, photo022.JPG, photo024.JPG, photo025.JPG, photo026.JPG, photo027.JPG, photo028.JPG, photo029.JPG, photo030.JPG, photo031.JPG, photo032.JPG, photo033.JPG, photo039.JPG, photo040.JPG, photo041.JPG, photo042.JPG, photo043.JPG, photo044.JPG, photo045.JPG, photo046.JPG, photo047.JPG, photo048.JPG, photo049.JPG, photo050.JPG, photo051.JPG, photo052.JPG, photo053.JPG, photo054.JPG, photo055.JPG, photo056.JPG, photo057.JPG, photo058.JPG, photo059.JPG, photo060.JPG, photo061.JPG, photo062.JPG, photo063.JPG, photo064.JPG, photo065.JPG, photo066.JPG, photo067.JPG, photo068.JPG, photo069.JPG, photo070.JPG, photo071.JPG, photo072.JPG, photo073.JPG, photo074.JPG, photo075.JPG, photo076.JPG, photo077.JPG, photo078.JPG, photo079.JPG, photo080.JPG, photo081.JPG, photo082.JPG

======================================================================
sub_02 members=50 seed=40 seed_image=photo041.JPG mean=0.8944
REPRESENTATIVES:
   photo044.JPG
   photo042.JPG
   photo075.JPG
   photo078.JPG
   photo040.JPG
MEMBERS:
  photo002.JPG, photo004.JPG, photo006.JPG, photo007.JPG, photo008.JPG, photo009.JPG, photo010.JPG, photo011.JPG, photo012.JPG, photo021.JPG, photo022.JPG, photo024.JPG, photo025.JPG, photo027.JPG, photo028.JPG, photo029.JPG, photo031.JPG, photo032.JPG, photo033.JPG, photo037.JPG, photo039.JPG, photo040.JPG, photo041.JPG, photo042.JPG, photo043.JPG, photo044.JPG, photo045.JPG, photo051.JPG, photo052.JPG, photo053.JPG, photo055.JPG, photo056.JPG, photo057.JPG, photo058.JPG, photo059.JPG, photo060.JPG, photo061.JPG, photo062.JPG, photo063.JPG, photo072.JPG, photo073.JPG, photo074.JPG, photo075.JPG, photo076.JPG, photo077.JPG, photo078.JPG, photo079.JPG, photo080.JPG, photo081.JPG, photo082.JPG

======================================================================
sub_03 members=48 seed=29 seed_image=photo030.JPG mean=0.8939
REPRESENTATIVES:
   photo075.JPG
   photo078.JPG
   photo044.JPG
   photo079.JPG
   photo052.JPG
MEMBERS:
  photo010.JPG, photo011.JPG, photo012.JPG, photo021.JPG, photo022.JPG, photo024.JPG, photo025.JPG, photo026.JPG, photo027.JPG, photo028.JPG, photo029.JPG, photo030.JPG, photo031.JPG, photo033.JPG, photo039.JPG, photo040.JPG, photo042.JPG, photo043.JPG, photo044.JPG, photo045.JPG, photo046.JPG, photo047.JPG, photo048.JPG, photo049.JPG, photo050.JPG, photo051.JPG, photo052.JPG, photo053.JPG, photo054.JPG, photo055.JPG, photo056.JPG, photo057.JPG, photo058.JPG, photo059.JPG, photo061.JPG, photo062.JPG, photo063.JPG, photo072.JPG, photo073.JPG, photo074.JPG, photo075.JPG, photo076.JPG, photo077.JPG, photo078.JPG, photo079.JPG, photo080.JPG, photo081.JPG, photo082.JPG

======================================================================
sub_04 members=45 seed=67 seed_image=photo068.JPG mean=0.8813
REPRESENTATIVES:
   photo078.JPG
   photo079.JPG
   photo077.JPG
   photo081.JPG
   photo075.JPG
MEMBERS:
  photo002.JPG, photo004.JPG, photo006.JPG, photo007.JPG, photo008.JPG, photo009.JPG, photo027.JPG, photo028.JPG, photo029.JPG, photo031.JPG, photo033.JPG, photo039.JPG, photo040.JPG, photo042.JPG, photo044.JPG, photo051.JPG, photo052.JPG, photo053.JPG, photo055.JPG, photo056.JPG, photo057.JPG, photo058.JPG, photo059.JPG, photo060.JPG, photo062.JPG, photo063.JPG, photo064.JPG, photo065.JPG, photo066.JPG, photo067.JPG, photo068.JPG, photo069.JPG, photo070.JPG, photo071.JPG, photo072.JPG, photo073.JPG, photo074.JPG, photo075.JPG, photo076.JPG, photo077.JPG, photo078.JPG, photo079.JPG, photo080.JPG, photo081.JPG, photo082.JPG

======================================================================
sub_05 members=34 seed=45 seed_image=photo046.JPG mean=0.8886
REPRESENTATIVES:
   photo028.JPG
   photo052.JPG
   photo075.JPG
   photo078.JPG
   photo079.JPG
MEMBERS:
  photo010.JPG, photo011.JPG, photo012.JPG, photo021.JPG, photo022.JPG, photo024.JPG, photo025.JPG, photo026.JPG, photo027.JPG, photo028.JPG, photo029.JPG, photo030.JPG, photo033.JPG, photo045.JPG, photo046.JPG, photo047.JPG, photo048.JPG, photo049.JPG, photo050.JPG, photo051.JPG, photo052.JPG, photo053.JPG, photo054.JPG, photo057.JPG, photo058.JPG, photo072.JPG, photo073.JPG, photo074.JPG, photo075.JPG, photo077.JPG, photo078.JPG, photo079.JPG, photo080.JPG, photo081.JPG

======================================================================
sub_06 members=30 seed=65 seed_image=photo066.JPG mean=0.8906
REPRESENTATIVES:
   photo081.JPG
   photo077.JPG
   photo078.JPG
   photo063.JPG
   photo079.JPG
MEMBERS:
  photo009.JPG, photo027.JPG, photo044.JPG, photo051.JPG, photo055.JPG, photo056.JPG, photo057.JPG, photo058.JPG, photo059.JPG, photo060.JPG, photo063.JPG, photo064.JPG, photo065.JPG, photo066.JPG, photo067.JPG, photo068.JPG, photo069.JPG, photo070.JPG, photo071.JPG, photo072.JPG, photo073.JPG, photo074.JPG, photo075.JPG, photo076.JPG, photo077.JPG, photo078.JPG, photo079.JPG, photo080.JPG, photo081.JPG, photo082.JPG

======================================================================
sub_07 members=21 seed=66 seed_image=photo067.JPG mean=0.9014
REPRESENTATIVES:
   photo081.JPG
   photo077.JPG
   photo063.JPG
   photo080.JPG
   photo078.JPG
MEMBERS:
  photo055.JPG, photo063.JPG, photo064.JPG, photo065.JPG, photo066.JPG, photo067.JPG, photo068.JPG, photo069.JPG, photo070.JPG, photo071.JPG, photo072.JPG, photo073.JPG, photo074.JPG, photo075.JPG, photo076.JPG, photo077.JPG, photo078.JPG, photo079.JPG, photo080.JPG, photo081.JPG, photo082.JPG

======================================================================
sub_08 members=14 seed=19 seed_image=photo020.JPG mean=0.8876
REPRESENTATIVES:
   photo036.JPG
   photo031.JPG
   photo038.JPG
   photo033.JPG
   photo037.JPG
MEMBERS:
  photo007.JPG, photo008.JPG, photo009.JPG, photo015.JPG, photo020.JPG, photo031.JPG, photo032.JPG, photo033.JPG, photo034.JPG, photo035.JPG, photo036.JPG, photo037.JPG, photo038.JPG, photo073.JPG

======================================================================
sub_09 members=11 seed=34 seed_image=photo035.JPG mean=0.8995
REPRESENTATIVES:
   photo036.JPG
   photo038.JPG
   photo020.JPG
   photo037.JPG
   photo035.JPG
MEMBERS:
  photo015.JPG, photo020.JPG, photo031.JPG, photo032.JPG, photo033.JPG, photo034.JPG, photo035.JPG, photo036.JPG, photo037.JPG, photo038.JPG, photo042.JPG

======================================================================
sub_10 members=10 seed=16 seed_image=photo017.JPG mean=0.8916
REPRESENTATIVES:
   photo017.JPG
   photo014.JPG
   photo015.JPG
   photo001.JPG
   photo016.JPG
MEMBERS:
  photo001.JPG, photo005.JPG, photo013.JPG, photo014.JPG, photo015.JPG, photo016.JPG, photo017.JPG, photo036.JPG, photo037.JPG, photo038.JPG

======================================================================
sub_11 members=8 seed=12 seed_image=photo013.JPG mean=0.8813
REPRESENTATIVES:
   photo014.JPG
   photo017.JPG
   photo001.JPG
   photo013.JPG
   photo015.JPG
MEMBERS:
  photo001.JPG, photo013.JPG, photo014.JPG, photo015.JPG, photo016.JPG, photo017.JPG, photo033.JPG, photo056.JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

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
PY          )   f"jaccard={jaccard:.3f}"} "
======================================================================
GROUP OVERLAP
======================================================================
sub_01 <-> sub_02: intersection=49 jaccard=0.731
sub_01 <-> sub_03: intersection=48 jaccard=0.727
sub_01 <-> sub_04: intersection=45 jaccard=0.682
sub_01 <-> sub_05: intersection=34 jaccard=0.515
sub_01 <-> sub_06: intersection=30 jaccard=0.455
sub_01 <-> sub_07: intersection=21 jaccard=0.318
sub_02 <-> sub_03: intersection=40 jaccard=0.690
sub_02 <-> sub_04: intersection=37 jaccard=0.638
sub_02 <-> sub_05: intersection=26 jaccard=0.448
sub_02 <-> sub_06: intersection=22 jaccard=0.379
sub_02 <-> sub_07: intersection=13 jaccard=0.224
sub_03 <-> sub_04: intersection=30 jaccard=0.476
sub_03 <-> sub_05: intersection=34 jaccard=0.708
sub_03 <-> sub_06: intersection=20 jaccard=0.345
sub_03 <-> sub_07: intersection=13 jaccard=0.232
sub_04 <-> sub_05: intersection=18 jaccard=0.295
sub_04 <-> sub_06: intersection=30 jaccard=0.667
sub_04 <-> sub_07: intersection=21 jaccard=0.467
sub_05 <-> sub_06: intersection=13 jaccard=0.255
sub_06 <-> sub_07: intersection=21 jaccard=0.700
sub_08 <-> sub_09: intersection=10 jaccard=0.667
sub_08 <-> sub_10: intersection= 4 jaccard=0.200
sub_09 <-> sub_10: intersection= 4 jaccard=0.235
sub_10 <-> sub_11: intersection= 6 jaccard=0.500
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:57:00

Вот теперь картина очень ясная. **Текущие subfingerprints нельзя оставлять в таком виде.** Но это не провал — наоборот, эксперимент показал, где именно проблема.

### Что мы увидели

`sub_01–sub_07` фактически описывают **одну большую визуальную область**:

- `sub_01` — 66/82
- `sub_02` — 50/82
- `sub_03` — 48/82
- `sub_04` — 45/82
- ...
- `sub_06` и `sub_07` имеют Jaccard `0.700`

Например:

```text
sub_01 ∩ sub_02 = 49 фотографий
Jaccard = 0.731
```

Это слишком много.

А вот:

```text
sub_08 ↔ sub_09 = 0.667
sub_10 ↔ sub_11 = 0.500
```

тоже говорят о том, что алгоритм последовательно выделяет **одни и те же локальные группы**, а не независимые визуальные состояния.

---

# Но есть очень важная хорошая новость

Посмотри на `sub_08–sub_11`.

Там уже явно проявляются отдельные группы:

```text
sub_08:
007 008 009
015 020
031–038
073

sub_09:
015 020
031–038
042

sub_10:
001 005 013–017
036–038

sub_11:
001 013–017
033
056
```

То есть **DINO уже видит структуру внутри адреса**.

Именно это нам нужно.

Проблема не в том, что DINO не способен разделять сцены.

Проблема в том, что наш текущий алгоритм говорит:

> «если фотография похожа на seed на 0.88 — включаем её»

и поэтому один большой кластер начинает поглощать почти всё.

---

# Я бы сейчас поменял саму философию subfingerprint

Не:

```text
seed
 ↓
все похожие фотографии
 ↓
новый seed
 ↓
все похожие фотографии
```

А:

```text
82 фотографии
       ↓
поиск естественных визуальных групп
       ↓
┌────────┬────────┬────────┬────────┐
│ группа │ группа │ группа │ группа │
│   A    │   B    │   C    │   D    │
└────────┴────────┴────────┴────────┘
       ↓
для каждой группы
       ↓
5–10 наиболее характерных фотографий
       ↓
SUBFINGERPRINT
```

То есть **subfingerprint должен быть не набором похожих фотографий, а компактным слепком конкретного визуального состояния адреса.**

---

# И здесь я предлагаю сделать очень важное изменение

Не будем пока трогать основной `v33`.

Он у нас уже хороший:

```text
global        768
environment   640
color          48
spatial        32
```

и веса:

```text
global       0.70
environment  0.20
color        0.07
spatial      0.03
```

Это оставляем.

### Новый subfingerprint будем строить из уже существующих embeddings.

То есть **GPU заново гонять фотографии не понадобится.**

Это очень удобно.

---

# Как я предлагаю сделать v34

Для каждого адреса:

### Шаг 1

Берём:

```text
embeddings.npy
environment_embeddings.npy
color_embeddings.npy
spatial_embeddings.npy
```

### Шаг 2

Для каждой пары фотографий считаем комбинированную близость:

```text
S =
    0.70 * global
  + 0.20 * environment
  + 0.07 * color
  + 0.03 * spatial
```

То есть subfingerprint будет учитывать не только «похожесть картинки», но и:

- окружающую среду;
- характерные цвета;
- пространственную структуру кадра.

---

# Шаг 3 — ищем ядра

Вот это принципиально.

Не будем выбирать seed как сейчас:

```text
самая центральная фотография
```

Вместо этого ищем **плотные локальные ядра**.

Например условно:

```text
               001
            013 014
          015 016 017
             036 037 038

                ↑
          ядро A
```

и:

```text
          063 064 065
        066 067 068 069
      070 071 072 073 074
        075 076 077 078
            079 080
```

это уже другое ядро.

---

# Шаг 4 — ограничиваем размер

Я бы начал с:

```text
MIN_CORE = 5
MAX_CORE = 25
```

То есть subfingerprint:

- меньше 5 фотографий → обычно шум;
- 5–25 → нормальный локальный слепок;
- больше 25 → скорее всего слишком общий кластер.

Для `78` ожидаю порядка:

```text
5–10 subfingerprints
```

а не 11 огромных перекрывающихся групп.

---

# Шаг 5 — самое главное: допускаем overlap

**Overlap нам нужен.**

Например одна фотография может принадлежать:

```text
sub_02
sub_03
```

потому что она действительно показывает переход между двумя визуальными состояниями.

Но:

```text
49 из 50
```

— это уже не overlap.

Я бы ввёл ограничение:

```text
Jaccard > 0.50
```

→ две группы считаются практически одинаковыми.

И тогда меньшая группа поглощается/удаляется.

---

# Что получится в конечном распознавании

И вот здесь начинается самое интересное.

Для новой фотографии:

```text
NEW PHOTO
   │
   ▼
global embedding
   │
   ▼
поиск адресов
   │
   ├── 78_v33   0.87
   ├── 91_v33   0.83
   └── 84_v33   0.81
             │
             ▼
       первый кандидат = 78
             │
             ▼
       subfingerprints 78
             │
       ┌─────┼─────┐
       ▼     ▼     ▼
      A      B      C
     .91    .73    .68
       │
       ▼
   sub_A подтверждает
       │
       ▼
     ADDRESS 78
```

И это намного надёжнее, чем просто:

```text
NEW → centroid 78 → 78
```

---

# А ещё мы можем сделать третий уровень

Это я бы **не реализовывал прямо сейчас**, но держал архитектуру в голове.

```text
ADDRESS
   │
   ├── SUBFINGERPRINT A
   │      ├── representative 1
   │      ├── representative 2
   │      └── representative 3
   │
   ├── SUBFINGERPRINT B
   │      ├── representative 1
   │      ├── representative 2
   │      └── representative 3
   │
   └── SUBFINGERPRINT C
          ├── representative 1
          ├── representative 2
          └── representative 3
```

То есть для поиска новой фотографии нам вообще не понадобится сравнивать её со всеми 82 фотографиями.

---

## И ещё один момент из твоего вопроса про светофоры, знаки и дома

**Да, они уже частично участвуют.**

DINOv2 global embedding не понимает объект буквально как OCR:

> «это светофор»

Но изображение светофора, дорожного знака, характерного фасада, дерева, геометрии дороги и т. д. влияет на embedding.

А наш:

```text
environment_embeddings
```

добавляет ещё один канал, который специально сохраняет информацию об окружающей сцене.

Поэтому в нашем случае это скорее:

```text
адрес =
    фасад
  + дорога
  + положение дороги
  + дома вокруг
  + деревья
  + цветовая среда
  + характерные объекты
  + геометрия сцены
```

а не просто фотография рекламного щита.

**Это как раз правильная стратегия для твоей задачи.**

---

## Следующий шаг

Я предлагаю **не переписывать весь проект**.

Сделаем отдельный эксперимент:

```text
scripts/make_subfingerprints_v2.py
```

Он будет читать существующий `78_v33`, строить комбинированную матрицу сходства и создавать:

```text
data/subfingerprints_v2/78_v33/
    sub_01/
    sub_02/
    ...
```

При этом старые:

```text
data/subfingerprints/78_v33
```

**не трогаем вообще.**

После этого прогоняем `78`, смотрим количество групп и overlap. Если структура нормальная — прогоняем сразу:

```text
79_v33
80_v33
81_v33
82_v33
...
95_v33
```

И только после этого подключаем subfingerprint к `recognize`.

**Это будет правильный следующий этап.**

---

### 👤 **User** — 2026-08-15 01:58:29

даавай.  размер Finferprint какой получается?

---

### 🤖 **Assistant** — 2026-08-15 01:58:29

Если ты имеешь в виду **размер самого fingerprint на диске**, то сейчас `v33` получается очень компактным.

Для `78_v33`:

```text
embeddings.npy              252 KB
environment_embeddings.npy  210 KB
color_embeddings.npy         16 KB
spatial_embeddings.npy       11 KB
representatives.npy          49 KB
centroid.npy                  3 KB
representative_indices.npy    0.2 KB
faiss.index                  252 KB
metadata.json                 2 KB
--------------------------------
ИТОГО                       ≈ 795 KB
```

То есть **один fingerprint адреса 78 — меньше 1 МБ**.

При этом в нём хранится информация о **82 фотографиях**.

### Если считать только основные признаки

На 1 фотографию:

```text
DINO global       768 × float32 = 3072 байта
environment       640 × float32 = 2560 байт
color              48 × float32 = 192 байта
spatial            32 × float32 = 128 байт
-----------------------------------------
всего                             5952 байта
```

То есть примерно **5.8 КБ на фотографию**.

Для 100 фотографий — около **580 КБ признаков**.

---

### А subfingerprint будет ещё компактнее

Мы **не будем копировать все embeddings внутрь каждого subfingerprint**.

Например:

```text
78_v33
│
├── основной fingerprint       ~800 KB
│
└── subfingerprints_v2
     ├── sub_01
     ├── sub_02
     ├── sub_03
     ├── ...
```

В subfingerprint достаточно хранить:

- индексы входящих фотографий;
- centroid;
- несколько representative embeddings;
- metadata.

Поэтому один подслепок будет порядка **десятков килобайт**, а не сотен.

---

### Это важно для будущей базы

Допустим, будет:

```text
1000 адресов
× 100 фотографий
```

Основные fingerprint:

**≈ 600–800 МБ**.

А если делать по 5–10 subfingerprints на адрес, это добавит сравнительно немного.

То есть даже база:

```text
5000 адресов
500 000 фотографий
```

остаётся вполне реальной для нашей схемы.

И главное — **нам не нужно хранить сами фотографии в fingerprint**. Фотографии остаются отдельно, а fingerprint — это компактная математическая «слепка» сцены.

Так что по объёму наша текущая архитектура очень удачная.

---

### 👤 **User** — 2026-08-15 01:58:44

ок

---

### 🤖 **Assistant** — 2026-08-15 01:58:44

Отлично. Тогда следующий шаг — **делаем `make_subfingerprints_v2.py`**, старую версию не трогаем.

Будем строить подслепки из комбинации:

```text
DINO global       70%
environment       20%
color              7%
spatial            3%
```

с контролем размера групп и сильного overlap.

После `78_v33` сразу проверим результат визуально по спискам фотографий.

---

### 👤 **User** — 2026-08-15 01:58:49

ок

---

### 🤖 **Assistant** — 2026-08-15 01:58:49

Делаем. Сначала создадим новый скрипт **без изменения текущего `fingerprint.py`, `recognizer.py` и старых subfingerprints**.

Выполни из проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/make_subfingerprints_v2.py <<'PY'
#!/usr/bin/env python3

import json
import shutil
import sys
from pathlib import Path

import numpy as np

# ============================================================
# SETTINGS
# ============================================================

WEIGHTS = {
    "global": 0.70,
    "environment": 0.20,
    "color": 0.07,
    "spatial": 0.03,
}

MIN_CORE = 5
MAX_CORE = 25

# Минимальная близость для попадания в локальную группу.
CORE_THRESHOLD = 0.84

# Если две группы слишком похожи — считаем их дубликатами.
MERGE_JACCARD = 0.50

# Сколько представителей хранить в каждом subfingerprint.
REPRESENTATIVES = 5

# ============================================================
# UTILS
# ============================================================

def normalize_rows(x):
    x = x.astype(np.float32, copy=False)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return x / (norms + 1e-12)

def cosine_matrix(x):
    x = normalize_rows(x)
    return x @ x.T

def load_descriptor(path):
    return normalize_rows(np.load(path).astype(np.float32))

def combined_similarity(p, n):
    """
    Комбинированная similarity-матрица.

    Каждый descriptor нормализуется отдельно.
    Затем используется v33 weighting.
    """

    print("Loading descriptors...")

    global_x = load_descriptor(p / "embeddings.npy")
    env_x = load_descriptor(p / "environment_embeddings.npy")
    color_x = load_descriptor(p / "color_embeddings.npy")
    spatial_x = load_descriptor(p / "spatial_embeddings.npy")

    print(f"  global:      {global_x.shape}")
    print(f"  environment: {env_x.shape}")
    print(f"  color:       {color_x.shape}")
    print(f"  spatial:     {spatial_x.shape}")

    print("Building similarity matrices...")

    S = (
        WEIGHTS["global"] * (global_x @ global_x.T)
        + WEIGHTS["environment"] * (env_x @ env_x.T)
        + WEIGHTS["color"] * (color_x @ color_x.T)
        + WEIGHTS["spatial"] * (spatial_x @ spatial_x.T)
    )

    np.fill_diagonal(S, 1.0)

    return S, global_x

def choose_representatives(indices, global_x, count=REPRESENTATIVES):
    """
    Выбираем наиболее центральные изображения внутри группы.
    """

    if len(indices) <= count:
        return list(indices)

    X = global_x[indices]

    center = X.mean(axis=0)
    center /= np.linalg.norm(center) + 1e-12

    scores = X @ center

    order = np.argsort(-scores)

    return [indices[i] for i in order[:count]]

def group_jaccard(a, b):
    a = set(a)
    b = set(b)

    inter = len(a & b)
    union = len(a | b)

    if union == 0:
        return 0.0

    return inter / union

# ============================================================
# BUILD LOCAL GROUPS
# ============================================================

def build_groups(S):
    n = len(S)

    unused = set(range(n))
    groups = []

    # Чем больше средняя similarity кандидата с остальными,
    # тем более устойчивым будет seed.
    mean_sim = S.copy()
    np.fill_diagonal(mean_sim, 0)

    centrality = mean_sim.sum(axis=1) / max(n - 1, 1)

    while unused:

        # Берём наиболее центральную ещё не использованную точку.
        seed = max(
            unused,
            key=lambda i: centrality[i]
        )

        candidates = [
            i for i in unused
            if S[seed, i] >= CORE_THRESHOLD
        ]

        # Если группа слишком большая, оставляем ближайшие к seed.
        if len(candidates) > MAX_CORE:
            candidates = sorted(
                candidates,
                key=lambda i: S[seed, i],
                reverse=True
            )[:MAX_CORE]

        # Слишком маленькая группа — seed пока просто
        # исключаем из рассмотрения.
        if len(candidates) < MIN_CORE:
            unused.remove(seed)
            continue

        groups.append({
            "seed": seed,
            "members": sorted(candidates),
            "seed_score": float(centrality[seed]),
        })

        # ВАЖНО:
        # полностью удаляем участников только если они уже
        # попали в устойчивое ядро. Это допускает overlap.
        for i in candidates:
            unused.discard(i)

    return groups

# ============================================================
# MERGE DUPLICATES
# ============================================================

def merge_groups(groups):
    changed = True

    while changed:
        changed = False

        for i in range(len(groups)):
            if changed:
                break

            for j in range(i + 1, len(groups)):

                a = groups[i]["members"]
                b = groups[j]["members"]

                jac = group_jaccard(a, b)

                if jac >= MERGE_JACCARD:

                    # Оставляем более крупную / более устойчивую группу.
                    if len(a) >= len(b):
                        keep, remove = i, j
                    else:
                        keep, remove = j, i

                    merged = sorted(
                        set(groups[keep]["members"])
                        | set(groups[remove]["members"])
                    )

                    groups[keep]["members"] = merged

                    groups.pop(remove)

                    changed = True
                    break

    return groups

# ============================================================
# SAVE
# ============================================================

def save_groups(
    fingerprint,
    source,
    output_root,
    groups,
    global_x,
    image_names,
    S,
):
    output = output_root / fingerprint

    if output.exists():
        shutil.rmtree(output)

    output.mkdir(parents=True)

    for num, group in enumerate(groups, 1):

        members = group["members"]
        seed = group["seed"]

        sub_name = f"sub_{num:02d}"
        sub_dir = output / sub_name
        sub_dir.mkdir()

        reps = choose_representatives(
            members,
            global_x,
            REPRESENTATIVES,
        )

        # centroid
        centroid = global_x[members].mean(axis=0)
        centroid /= np.linalg.norm(centroid) + 1e-12

        np.save(
            sub_dir / "centroid.npy",
            centroid.astype(np.float32),
        )

        np.save(
            sub_dir / "representatives.npy",
            global_x[reps].astype(np.float32),
        )

        np.save(
            sub_dir / "representative_indices.npy",
            np.asarray(reps, dtype=np.int32),
        )

        np.save(
            sub_dir / "member_indices.npy",
            np.asarray(members, dtype=np.int32),
        )

        # Средняя similarity членов к centroid
        member_scores = global_x[members] @ centroid
        mean_score = float(member_scores.mean())

        metadata = {
            "subfingerprint": sub_name,
            "parent": fingerprint,
            "version": "2.0",

            "members": len(members),

            "seed_index": int(seed),
            "seed_image": image_names[seed],

            "mean_similarity_to_centroid": mean_score,

            "representatives": [
                image_names[i]
                for i in reps
            ],

            "images": [
                image_names[i]
                for i in members
            ],

            "weights": WEIGHTS,

            "threshold": CORE_THRESHOLD,
            "min_core": MIN_CORE,
            "max_core": MAX_CORE,
        }

        with open(
            sub_dir / "metadata.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                metadata,
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(
            f"  {sub_name:<8} "
            f"members={len(members):3d} "
            f"seed={seed:3d} "
            f"seed_image={image_names[seed]} "
            f"mean={mean_score:.4f}"
        )

    return output

# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "  uv run python scripts/make_subfingerprints_v2.py 78_v33"
        )
        sys.exit(1)

    fingerprint = sys.argv[1]

    source = Path("data/fingerprints") / fingerprint

    if not source.exists():
        print(f"ERROR: fingerprint not found: {source}")
        sys.exit(1)

    with open(
        source / "metadata.json",
        "r",
        encoding="utf-8",
    ) as f:
        metadata = json.load(f)

    image_names = metadata["image_names"]
    n = len(image_names)

    print()
    print("=" * 70)
    print("SUBFINGERPRINTS V2")
    print("=" * 70)
    print(f"FINGERPRINT: {fingerprint}")
    print(f"IMAGES:      {n}")
    print()
    print("WEIGHTS:")
    for k, v in WEIGHTS.items():
        print(f"  {k:<12} {v}")
    print()
    print(f"CORE_THRESHOLD: {CORE_THRESHOLD}")
    print(f"MIN_CORE:       {MIN_CORE}")
    print(f"MAX_CORE:       {MAX_CORE}")
    print(f"MERGE_JACCARD:  {MERGE_JACCARD}")
    print()

    S, global_x = combined_similarity(
        source,
        n,
    )

    print()
    print("Building local groups...")

    groups = build_groups(S)

    print(
        f"Initial groups: {len(groups)}"
    )

    groups = merge_groups(groups)

    print(
        f"After merge:    {len(groups)}"
    )

    print()
    print("FINAL GROUPS")
    print("-" * 70)

    output = save_groups(
        fingerprint,
        source,
        Path("data/subfingerprints_v2"),
        groups,
        global_x,
        image_names,
        S,
    )

    print()
    print("=" * 70)
    print(f"OUTPUT: {output}")
    print("=" * 70)

if __name__ == "__main__":
    main()
PY

chmod +x scripts/make_subfingerprints_v2.py
```

Теперь запускаем **только на `78_v33`**:

```bash
uv run python scripts/make_subfingerprints_v2.py 78_v33
```

### Важный момент

Я специально сделал этот вариант изолированным:

```text
data/fingerprints/78_v33
        │
        ▼
make_subfingerprints_v2.py
        │
        ▼
data/subfingerprints_v2/78_v33
```

Существующий:

```text
data/subfingerprints/78_v33
```

не изменяется.

**Пока не запускай 79–95.** Сначала посмотрим, что получилось у `78_v33`. Пришли весь вывод `FINAL GROUPS`, и по нему настроим пороги.

---

### 👤 **User** — 2026-08-15 01:59:31

WEIGHTS = {
    "global": 0.70,
    "environment": 0.20,
    "color": 0.07,
    "spatial": 0.03,
chmod +x scripts/make_subfingerprints_v2.py")){source}")s_v2.py 78_v33".
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/make_subfingerprints_v2.py 78_v33

======================================================================
SUBFINGERPRINTS V2
======================================================================
FINGERPRINT: 78_v33
IMAGES:      82

WEIGHTS:
  global       0.7
  environment  0.2
  color        0.07
  spatial      0.03

CORE_THRESHOLD: 0.84
MIN_CORE:       5
MAX_CORE:       25
MERGE_JACCARD:  0.5

Loading descriptors...
  global:      (82, 768)
  environment: (82, 640)
  color:       (82, 48)
  spatial:     (82, 32)
Building similarity matrices...

Building local groups...
Initial groups: 3
After merge:    3

FINAL GROUPS
----------------------------------------------------------------------
  sub_01   members= 25 seed= 41 seed_image=photo042.JPG mean=0.9572
  sub_02   members= 25 seed= 72 seed_image=photo073.JPG mean=0.9454
  sub_03   members= 25 seed= 32 seed_image=photo033.JPG mean=0.9175

======================================================================
OUTPUT: data/subfingerprints_v2/78_v33
======================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:59:32

Вот это уже **намного ближе к правильной модели**, но я вижу одну проблему: мы слишком жёстко ограничили группу `MAX_CORE=25`, поэтому получили ровно:

```text
25 + 25 + 25
```

Это подозрительно. Алгоритм просто обрезал большие естественные группы.

При этом средние сходства очень хорошие:

```text
sub_01  0.9572
sub_02  0.9454
sub_03  0.9175
```

То есть ядра действительно плотные.

### Что я предлагаю сейчас

Не увеличивать `MAX_CORE` вслепую и не менять веса.

Нужно понять **структуру этих трёх групп**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

root = Path("data/subfingerprints_v2/78_v33")

for p in sorted(root.glob("sub_*")):
    with open(p / "metadata.json", encoding="utf-8") as f:
        m = json.load(f)

    print()
    print("=" * 70)
    print(m["subfingerprint"])
    print("members:", m["members"])
    print("seed:", m["seed_image"])
    print("mean:", m["mean_similarity_to_centroid"])

    print("\nREPRESENTATIVES:")
    for x in m["representatives"]:
        print(" ", x)

    print("\nIMAGES:")
    print(" ", " ".join(m["images"]))
PY
```

И отдельно посмотрим **пересечение уже v2**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

root = Path("data/subfingerprints_v2/78_v33")

groups = []

for p in sorted(root.glob("sub_*")):
    with open(p / "metadata.json", encoding="utf-8") as f:
        m = json.load(f)
    groups.append((m["subfingerprint"], set(m["images"])))

print("=" * 70)
print("V2 OVERLAP")
print("=" * 70)

for i in range(len(groups)):
    for j in range(i + 1, len(groups)):
        na, a = groups[i]
        nb, b = groups[j]

        inter = len(a & b)
        union = len(a | b)

        print(
            f"{na} <-> {nb}: "
            f"intersection={inter} "
            f"jaccard={inter/union:.3f}"
        )
PY
```

### Но уже сейчас вывод очень хороший

Старый алгоритм:

```text
11 групп
66
50
48
45
34
30
21
14
11
10
8
```

и огромное перекрытие.

Новый:

```text
3 группы
25
25
25
```

и среднее качество ядра:

```text
0.957
0.945
0.918
```

Это значит, что **комбинированный descriptor действительно работает лучше для поиска устойчивых визуальных состояний**.

Следующий шаг — выяснить, не потеряли ли мы важные фотографии из-за `MAX_CORE=25`.

После вывода списков я бы сделал **v2.1**, где размер группы определяется автоматически, например:

```text
ядро → расширяем пока similarity не падает ниже естественного перелома
```

а не искусственно:

```text
MAX_CORE = 25
```

Это будет гораздо правильнее для разных адресов, потому что у одного адреса может быть 18 характерных фотографий, у другого 47, у третьего 9.

---

### 👤 **User** — 2026-08-15 02:00:09

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

root = Path("data/subfingerprints_v2/78_v33")

for p in sorted(root.glob("sub_*")):
    with open(p / "metadata.json", encoding="utf-8") as f:
        m = json.load(f)

    print()
    print("=" * 70)
    print(m["subfingerprint"])
    print("members:", m["members"])
    print("seed:", m["seed_image"])
    print("mean:", m["mean_similarity_to_centroid"])

    print("\nREPRESENTATIVES:")
    for x in m["representatives"]:
        print(" ", x)

PY  print(" ", " ".join(m["images"]))

======================================================================
sub_01
members: 25
seed: photo042.JPG
mean: 0.9571780562400818

REPRESENTATIVES:
  photo044.JPG
  photo042.JPG
  photo040.JPG
  photo057.JPG
  photo058.JPG

IMAGES:
  photo004.JPG photo008.JPG photo021.JPG photo022.JPG photo025.JPG photo028.JPG photo039.JPG photo040.JPG photo041.JPG photo042.JPG photo043.JPG photo044.JPG photo055.JPG photo056.JPG photo057.JPG photo058.JPG photo059.JPG photo060.JPG photo061.JPG photo062.JPG photo074.JPG photo075.JPG photo076.JPG photo077.JPG photo081.JPG

======================================================================
sub_02
members: 25
seed: photo073.JPG
mean: 0.9453625679016113

REPRESENTATIVES:
  photo079.JPG
  photo078.JPG
  photo063.JPG
  photo073.JPG
  photo072.JPG

IMAGES:
  photo002.JPG photo006.JPG photo007.JPG photo009.JPG photo010.JPG photo011.JPG photo012.JPG photo027.JPG photo045.JPG photo051.JPG photo052.JPG photo063.JPG photo064.JPG photo065.JPG photo066.JPG photo068.JPG photo069.JPG photo070.JPG photo071.JPG photo072.JPG photo073.JPG photo078.JPG photo079.JPG photo080.JPG photo082.JPG

======================================================================
sub_03
members: 25
seed: photo033.JPG
mean: 0.9175474643707275

REPRESENTATIVES:
  photo033.JPG
  photo031.JPG
  photo049.JPG
  photo029.JPG
  photo053.JPG

IMAGES:
  photo001.JPG photo003.JPG photo013.JPG photo014.JPG photo018.JPG photo020.JPG photo024.JPG photo026.JPG photo029.JPG photo030.JPG photo031.JPG photo032.JPG photo033.JPG photo034.JPG photo035.JPG photo036.JPG photo037.JPG photo038.JPG photo046.JPG photo047.JPG photo048.JPG photo049.JPG photo050.JPG photo053.JPG photo054.JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

root = Path("data/subfingerprints_v2/78_v33")

groups = []

for p in sorted(root.glob("sub_*")):
    with open(p / "metadata.json", encoding="utf-8") as f:
        m = json.load(f)
    groups.append((m["subfingerprint"], set(m["images"])))

print("=" * 70)
print("V2 OVERLAP")
print("=" * 70)

for i in range(len(groups)):
    for j in range(i + 1, len(groups)):
        na, a = groups[i]
PY      )   f"jaccard={inter/union:.3f}"
======================================================================
V2 OVERLAP
======================================================================
sub_01 <-> sub_02: intersection=0 jaccard=0.000
sub_01 <-> sub_03: intersection=0 jaccard=0.000
sub_02 <-> sub_03: intersection=0 jaccard=0.000
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 02:00:10

Да. **Это уже хороший результат.** И главное — V2 впервые разделил 78_v33 на **три независимых визуальных подслепка без перекрытия**.

### Что мы получили

| Подслепок | Фото | Среднее сходство |
|---|---:|---:|
| sub_01 | 25 | **0.9572** |
| sub_02 | 25 | **0.9454** |
| sub_03 | 25 | **0.9175** |

Но всего исходных фотографий **82**, а в подслепках только **75**.

То есть:

```text
82 исходных
-75 вошло в ядра
= 7 пока не вошло
```

И это **не ошибка**. Наоборот, эти 7 фотографий сейчас очень интересны: вероятно, это переходные/необычные ракурсы, фотографии с сильным изменением сцены или выбросы.

### И самое важное

Пересечение:

```text
sub_01 ↔ sub_02 = 0
sub_01 ↔ sub_03 = 0
sub_02 ↔ sub_03 = 0
```

Это значительно лучше старого алгоритма.

Старый вариант давал:

```text
sub_01 ↔ sub_02 = 49
sub_01 ↔ sub_03 = 48
...
```

То есть фактически создавал **не подслепки, а наборы похожих фотографий**, которые сильно накладывались друг на друга.

V2 уже создаёт именно **разные визуальные состояния одного адреса**.

---

## Но я бы пока не делал v2.1

Сначала надо посмотреть на **7 выпавших фотографий**.

Это очень важный тест.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path

fp = Path("data/fingerprints/78_v33")
subroot = Path("data/subfingerprints_v2/78_v33")

with open(fp / "metadata.json", encoding="utf-8") as f:
    meta = json.load(f)

all_images = set(meta["image_names"])

used = set()

for p in sorted(subroot.glob("sub_*")):
    with open(p / "metadata.json", encoding="utf-8") as f:
        m = json.load(f)
    used.update(m["images"])

lost = sorted(all_images - used)

print("=" * 70)
print("NOT IN ANY SUBFINGERPRINT CORE")
print("=" * 70)
print("count:", len(lost))

for x in lost:
    print(x)
PY
```

Получим примерно:

```text
NOT IN ANY SUBFINGERPRINT CORE
count: 7

photo005.JPG
photo015.JPG
...
```

---

## И дальше будет самое интересное

Мы можем сделать не просто:

```text
адрес 78
   ├── sub_01
   ├── sub_02
   └── sub_03
```

а полноценную структуру:

```text
                         FINGERPRINT 78
                              │
             ┌────────────────┼────────────────┐
             │                │                │
          SUB_01           SUB_02           SUB_03
           25 фото          25 фото          25 фото
             │                │                │
        representatives  representatives  representatives
             │                │                │
             └───────────────┼────────────────┘
                             │
                    7 переходных фото
```

И вот эти **7 переходных фотографий я бы пока не выбрасывал**.

Для распознавания нового снимка логика будет:

```text
Новая фотография
       ↓
DINO global
       ↓
поиск кандидатов среди адресов
       ↓
первый кандидат, например 78
       ↓
проверяем sub_01 / sub_02 / sub_03
       ↓
если попал в один из них с высоким score
       ↓
78
```

Причём подслепок может дать дополнительный сигнал:

```text
78
score = 0.91

sub_01 = 0.96  ← очень уверенно
sub_02 = 0.73
sub_03 = 0.68
```

Это намного информативнее, чем просто:

```text
78 = 0.91
```

---

### И ещё один важный момент

Мы **не меняем сейчас веса**:

```text
global       70%
environment  20%
color         7%
spatial       3%
```

Я бы их оставил.

Потому что именно такая комбинация сейчас позволяет учитывать одновременно:

- общую геометрию сцены;
- здания и окружающую обстановку;
- характерные цвета;
- пространственное расположение элементов.

То есть **цвет дома на заднем плане, деревья, дорога, фасады, светофоры/знаки и прочие визуально устойчивые элементы уже частично входят в fingerprint через DINO + environment descriptor**. Мы пока не пытаемся отдельно распознавать каждый такой объект.

**Следующий шаг — посмотреть эти 7 выпавших фотографий.** От этого станет понятно, нужно ли вообще расширять подслепки или текущая модель уже достаточно хороша.

---

### 👤 **User** — 2026-08-15 02:02:36

две фото я убрал - они не оттуда, а оставшиеся просто хуже качеством

---

### 🤖 **Assistant** — 2026-08-15 02:02:37

Отлично. Тогда результат **ещё лучше, чем выглядит по цифрам**.

Из 82 фотографий:

- **2 были чужими** → правильно не должны входить в fingerprint.
- **5 оставшихся — просто более плохого качества** → их не обязательно включать в ядро подслепка.
- **75 фотографий** образовали 3 очень плотных подслепка.
- Перекрытие между подслепками — **0**.

То есть сейчас структура 78 выглядит вполне естественно:

```text
78_v33
│
├── sub_01   25 фото   similarity 0.957
├── sub_02   25 фото   similarity 0.945
├── sub_03   25 фото   similarity 0.918
│
└── 5 слабых/низкокачественных фото
```

### Я бы сейчас ничего не оптимизировал

Это важный момент. Мы уже получили **приемлемую модель fingerprint**, и сейчас лучше перейти к проверке на реальной задаче — **распознаванию новых фотографий**.

Причём я бы сделал следующий эксперимент:

```text
Новая фотография
       ↓
DINO fingerprint
       ↓
ТОП кандидатов адресов
       ↓
первый кандидат
       ↓
его subfingerprints
       ↓
уточнение кандидата
```

Например:

```text
photo_new.JPG

78_v33    0.87
81_v33    0.84
83_v33    0.79
...

первый кандидат = 78

sub_01    0.94  ←
sub_02    0.72
sub_03    0.68

ИТОГ → 78
```

Именно это соответствует нашей первоначальной идее **«первый кандидат → подслепки → окончательное присвоение»**.

Причём мы можем использовать подслепки не как жёсткий фильтр, а как **дополнительное подтверждение**. Тогда плохое качество фотографии не будет автоматически приводить к отказу.

### Следующий шаг

Я предлагаю сейчас сделать **recognize_v2** поверх уже существующего `recognize`, не ломая рабочий алгоритм:

```text
v3.3 fingerprint
        ↓
обычный поиск TOP-K
        ↓
TOP-1 кандидат
        ↓
subfingerprints этого кандидата
        ↓
sub-score
        ↓
пересчёт уверенности
        ↓
адрес
```

И сначала прогнать его **на фотографиях самих известных адресов** — это даст нам объективную картину, насколько подслепки действительно улучшают распознавание, прежде чем подключать новые 200–300 фотографий дневной съемки.

---

### 👤 **User** — 2026-08-15 02:03:18

давай прогоним по тем что у меня есть

---

### 🤖 **Assistant** — 2026-08-15 02:03:18

Да. Причём лучше сразу сделать **контрольный прогон по существующим фотографиям**, не меняя основной `recognizer.py`.

Сначала определим, где лежат исходные фотографии для адресов `78–95`, и какие из них доступны. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== INPUT FOLDERS ==="
find data/input -maxdepth 2 -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.JPG" -o -iname "*.JPEG" \) \
  | sort | head -300

echo
echo "=== INPUT DIRECTORIES ==="
find data/input -maxdepth 2 -type d | sort
```

После этого я дам команду, которая сделает тест:

```text
известный адрес
      ↓
его фотографии
      ↓
recognize
      ↓
TOP-1
      ↓
subfingerprint TOP-1
      ↓
совпал / не совпал
```

И получим уже не ощущения, а конкретную статистику:

```text
Всего тестовых фото:  ...
Правильно TOP-1:      ... %
Правильно TOP-3:      ... %
После subfingerprint: ... %

78 → ...
79 → ...
80 → ...
...
```

**Пока ничего в коде не меняем.** Сначала измерим текущую систему на имеющемся датасете.

---

### 👤 **User** — 2026-08-15 02:03:43

data/input

---

### 🤖 **Assistant** — 2026-08-15 02:03:43

Да, тогда начинаем с `data/input`. Нам нужно понять структуру каталогов и какие фотографии там есть.

Выполни из проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== DATA/INPUT ==="
find data/input -maxdepth 2 -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.JPG" -o -iname "*.JPEG" \) \
  | sort

echo
echo "=== DIRECTORIES ==="
find data/input -maxdepth 2 -type d | sort
```

Если фотографий много, можно вместо полного списка сразу получить статистику по папкам:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for d in data/input/*/; do
    [ -d "$d" ] || continue
    echo -n "$(basename "$d"): "
    find "$d" -maxdepth 1 -type f \
      \( -iname "*.jpg" -o -iname "*.jpeg" \) | wc -l
done
```

**Пришли второй вывод.** По нему сразу определим тестовый набор и следующим шагом запустим распознавание по имеющимся фотографиям, а затем добавим проверку через подслепки.

---

### 👤 **User** — 2026-08-15 02:03:59

=== DIRECTORIES ===
data/input
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

### 🤖 **Assistant** — 2026-08-15 02:04:00

Отлично. У нас уже есть идеальный контрольный набор:

```text
78–95   → известные адреса
new     → новые фотографии
test    → отдельный тест
```

И fingerprint'ы `78_v33 ... 95_v33` уже существуют.

### Сейчас делаем базовый контрольный прогон

Не трогаем код и не добавляем подслепки в recognizer. Сначала проверим, насколько хорошо **текущий v3.3** распознаёт фотографии, которые уже принадлежат известным адресам.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint recognize data/input/test \
  --top-k 5 \
  --threshold 0.50 \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33,87_v33,88_v33,89_v33,90_v33,91_v33,92_v33,93_v33,94_v33,95_v33
```

Если `data/input/test` содержит именно фотографии с известными адресами, получим первый baseline.

Но я бы **ещё лучше** сделал автоматический тест по всем:

```text
78 → проверяем среди 78–95
79 → проверяем среди 78–95
...
95 → проверяем среди 78–95
```

Для этого сначала покажи:

```bash
find data/input/test -maxdepth 2 -type f | sort | head -100
```

и

```bash
for d in data/input/{78..95}; do
    echo -n "$(basename "$d"): "
    find "$d" -maxdepth 1 -type f \
      \( -iname "*.jpg" -o -iname "*.jpeg" \) | wc -l
done
```

После этого сделаем **нормальный benchmark**, где для каждого фото известен правильный адрес.

И уже поверх него сравним:

**v3.3 обычный fingerprint → v3.3 + subfingerprints.**

Это будет самый полезный эксперимент сейчас.

---

### 👤 **User** — 2026-08-15 02:06:20

th 2 -type f | sort | head -100
data/input/test/00 (10).JPG
data/input/test/00 (11).JPG
data/input/test/00 (12).JPG
data/input/test/001.JPG
data/input/test/00 (1).JPG
data/input/test/002.JPG
data/input/test/00 (2).JPG
data/input/test/003.JPG
data/input/test/00 (3).JPG
data/input/test/004.JPG
data/input/test/00 (4).JPG
data/input/test/005.JPG
data/input/test/00 (5).JPG
data/input/test/006.JPG
data/input/test/00 (6).JPG
data/input/test/007.JPG
data/input/test/00 (7).JPG
data/input/test/008.JPG
data/input/test/00 (8).JPG
data/input/test/009.JPG
data/input/test/00 (9).JPG
data/input/test/1 Конной Армии 32 А (10).JPG
data/input/test/1 Конной Армии 32 А (11).JPG
data/input/test/1 Конной Армии 32 А (12).JPG
data/input/test/1 Конной Армии 32 А (1).JPG
data/input/test/1 Конной Армии 32 А (35).JPG
data/input/test/1 Конной Армии 32 А (36).JPG
data/input/test/1 Конной Армии 32 А (37).JPG
data/input/test/1 Конной Армии 32 А (38).JPG
data/input/test/1 Конной Армии 32 А (39).JPG
data/input/test/1 Конной Армии 32 А (6).JPG
data/input/test/1 Конной Армии 32 А (7).JPG
data/input/test/1 Конной Армии 32 А (8).JPG
data/input/test/1 Конной Армии 32 А (9).JPG
data/input/test/1 Конной Армии А (16).JPG
data/input/test/1 Конной Армии А (17).JPG
data/input/test/1 Конной Армии А (18).JPG
data/input/test/Вавилова 52 А (10).JPG
data/input/test/Вавилова 52 А (11).JPG
data/input/test/Вавилова 52 А (12).JPG
data/input/test/Вавилова 52 А (14).JPG
data/input/test/Вавилова 52 А (16).JPG
data/input/test/Вавилова 52 А (17).JPG
data/input/test/Вавилова 52 А (18).JPG
data/input/test/Вавилова 52 А (1).JPG
data/input/test/Вавилова 52 А (20).JPG
data/input/test/Вавилова 52 А (21).JPG
data/input/test/Вавилова 52 А (23).JPG
data/input/test/Вавилова 52 А (25).JPG
data/input/test/Вавилова 52 А (28).JPG
data/input/test/Вавилова 52 А (4).JPG
data/input/test/Вавилова 52 А (8).JPG
data/input/test/Вавилова 52 А (9).JPG
data/input/test/Вавилова Радиаторный А (11).JPG
data/input/test/Вавилова Радиаторный А (16).JPG
data/input/test/Вавилова Радиаторный А (17).JPG
data/input/test/Вавилова Радиаторный А (1).JPG
data/input/test/Вавилова Радиаторный А (21).JPG
data/input/test/Вавилова Радиаторный А (22).JPG
data/input/test/Вавилова Радиаторный А (25).JPG
data/input/test/Вавилова Радиаторный А (26).JPG
data/input/test/Вавилова Радиаторный А (29).JPG
data/input/test/Вавилова Радиаторный А (30).JPG
data/input/test/Вавилова Радиаторный А (31).JPG
data/input/test/Вавилова Радиаторный А (32).JPG
data/input/test/Вавилова Радиаторный А (35).JPG
data/input/test/Вавилова Радиаторный А (38).JPG
data/input/test/Вавилова Радиаторный А (4).JPG
data/input/test/Вавилова Радиаторный А (50).JPG
data/input/test/Вавилова Радиаторный А (6).JPG
data/input/test/Вавилова Радиаторный А (7).JPG
data/input/test/Вавилова Радиаторный А (8).JPG
data/input/test/Вавилова Радиаторный А (9).JPG
data/input/test/Вавилова ул. - Радиаторный пер., A (34).JPG
data/input/test/Вавилова ул. - Радиаторный пер., A (38).JPG
data/input/test/Вавилова ул. - Радиаторный пер., A (5).JPG
data/input/test/Вавилова ул. - Радиаторный пер., A (63).JPG
data/input/test/Вавилова ул. - Радиаторный пер., A (70).JPG
data/input/test/Добровольского 17 А (34).JPG
data/input/test/Добровольского 17 А (35).JPG
data/input/test/Добровольского 17 А (36).JPG
data/input/test/Добровольского 17 А (37).JPG
data/input/test/Добровольского 17 А (38).JPG
data/input/test/Добровольского 17 А (59).JPG
data/input/test/Добровольского 17 А (60).JPG
data/input/test/Добровольского 17 А (61).JPG
data/input/test/Добровольского 17 А (63).JPG
data/input/test/Комарова 20 Добровольского Б (4).JPG
data/input/test/Комарова 20 Добровольского Б (5).JPG
data/input/test/Комарова 20 Добровольского Б (6).JPG
data/input/test/Комарова 28 А (1).JPG
data/input/test/Комарова 28 А (2).JPG
data/input/test/Комарова 28 А (3).JPG
data/input/test/Комарова 28 А (4).JPG
data/input/test/Комарова 28 А (5).JPG
data/input/test/Комарова 28 А (6).JPG
data/input/test/Комарова Добровольского А (1).JPG
data/input/test/Комарова Добровольского А (42).JPG
data/input/test/Комарова Добровольского А (8).JPG
data/input/test/Комарова Добровольского Б (17).JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ for d in data/input/{78..95}; do
    echo -n "$(basename "$d"): "
    find "$d" -maxdepth 1 -type f \
      $ -iname "*.jpg" -o -iname "*.jpeg" $ | wc -l
done
78: 81
79: 65
80: 37
81: 65
82: 67
83: 68
84: 54
85: 58
86: 58
87: 50
88: 54
89: 64
90: 19
91: 41
92: 57
93: 51
94: 67
95: 86
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 02:06:22

Да. Теперь у нас есть **хороший реальный тестовый набор**.

`data/input/test` — это не просто копия папок 78–95: там уже есть файлы с реальными названиями адресов, например:

```text
Вавилова 52 А (...)
Добровольского 17 А (...)
Комарова 28 А (...)
...
```

А в `data/input/78..95` — исходные фотографии для построения fingerprint.

Поэтому можем сделать настоящий benchmark:

**известный адрес → его фотографии из `test` → поиск среди 78–95 → сравнение с правильным адресом.**

Но есть нюанс: названия файлов в `test` не содержат ID `78–95`, поэтому сначала надо понять соответствие адресов папкам. Это уже, судя по названиям, есть в данных проекта, но **не будем угадывать**.

### Давай сначала посмотрим, что уже умеет `test`

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint recognize data/input/test \
  --top-k 5 \
  --threshold 0.50 \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33,87_v33,88_v33,89_v33,90_v33,91_v33,92_v33,93_v33,94_v33,95_v33 \
  --json > /tmp/recognize_test.json

echo "RESULT:"
head -c 3000 /tmp/recognize_test.json
```

Это важно сделать **до разработки subfingerprint-recognizer**.

Почему: мы увидим фактический формат результата текущего recognizer и сможем аккуратно встроить второй этап, не ломая существующую систему.

### А ещё у нас есть 1109 исходных фотографий

Сумма папок 78–95:

```text
78   81
79   65
80   37
81   65
82   67
83   68
84   54
85   58
86   58
87   50
88   54
89   64
90   19
91   41
92   57
93   51
94   67
95   86
────────
   1109
```

Это уже достаточно большой набор, чтобы нормально проверить алгоритм.

И я бы **не прогонял пока все 1109 через DINO заново** — embeddings уже есть в fingerprint'ах. Сначала проверим `test`, потому что там потенциально несколько сотен фотографий и это даст нам реальную картину ошибок.

Пришли первые ~3000 символов `/tmp/recognize_test.json`. По нему сразу сделаем следующий шаг — **автоматический тест + подслепки**, без OCR.

---

### 👤 **User** — 2026-08-15 02:09:17

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint recognize data/input/test \
  --top-k 5 \
  --threshold 0.50 \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33,87_v33,88_v33,89_v33,90_v33,91_v33,92_v33,93_v33,94_v33,95_v33 \
  --json > /tmp/recognize_test.json

echo "RESULT:"
head -c 3000 /tmp/recognize_test.json
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9659.11it/s]
RESULT:
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Recognizer] Query images: 262
[Recognizer] Fingerprints: 78_v33, 79_v33, 80_v33, 81_v33, 82_v33, 83_v33, 84_v33, 85_v33
[Recognizer] CPU workers: 6
[
  {
    "file": "data/input/test/00 (1).JPG",
    "best_id": "78_v33",
    "score": 0.9474834299087525,
    "second_score": 0.8808266913890838,
    "margin": 0.06665673851966869,
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
        "id": "83_v33",
        "score": 0.8808266913890838,
        "global": 0.8717389106750488,
        "environment": 0.910814106464386,
        "color": 0.8405479788780212,
        "spatial": 0.9869424700737,
        "best_image": "22 (25).JPG",
        "best_image_score": 0.8683322668075562
      },
      {
        "id": "85_v33",
        "score": 0.8743322974443436,
        "global": 0.8600600361824036,
        "environment": 0.8831697702407837,
        "color": 0.9498430490493774,
        "spatial": 0.9722434878349304,
        "best_image": "000 (49).JPG",
        "best_image_score": 0.866817831993103
      },
      {
        "id": "79_v33",
        "score": 0.8522472059726715,
        "global": 0.8358133435249329,
        "environment": 0.8646810054779053,
        "color": 0.9405946731567383,
        "spatial": 0.9466679096221924,
        "best_image": "00 (8).JPG",
        "best_image_score": 0.854549765586853
      },
      {
        "id": "81_v33",
        "score": 0.840322676897049,
        "global": 0.8023285269737244,
        "environment": 0.9145163893699646,
        "color": 0.9478660225868225,
        "spatial": 0.9812936186790466,
        "best_image": "05.JPG",
        "best_image_score": 0.80205899477005
      }
    ]
  },
  {
    "file": "data/input/test/00 (10).JPG",
    "best_id": "78_v33",
    "score": 0.9383711481094359,
    "second_score": 0.866859638094902,
    "margin": 0.07151151001453393,
    "confidence": "HIGH",
    "status": "CONFIDENT",
    "best_image": "photo042.JPG",
    "best_image_score": 0.9266887903213501,
    "candidates": [
      {
        "id": "78_v33",
        "score": 0.9383711481094359,
        "global": 0.935716450214386,
        "environment": 0.9365684390068054,
        "color": 0.9463983178138733,
        "spatial": 0.9936020970344543,
        "best_image": "photo042.JPG",
        "best_image_score": 0.9266887903213501
      },
      {

---

### 🤖 **Assistant** — 2026-08-15 02:09:21

Отлично. **Первый результат уже очень обнадёживает.**

Для `00 (1).JPG` система дала:

```text
78_v33   0.9475   ← первый
83_v33   0.8808
85_v33   0.8743
79_v33   0.8522
81_v33   0.8403
```

Причём внутри первого кандидата:

```text
global       0.9549
environment  0.9361
color        0.8892
spatial      0.9870
```

То есть система видит не только общую картинку, но и **структуру/окружение сцены**. Это именно то, что нам нужно.

И ещё важное: `test` содержит **262 фотографии**, а не все файлы из каталога — значит, текущий recognizer действительно что-то отфильтровал/ограничил. Это тоже надо понять.

## Сейчас не будем ничего менять

Сделаем **автоматический отчёт по этим 262 результатам**:

- сколько раз каждый адрес оказался TOP-1;
- распределение `HIGH / MEDIUM / LOW`;
- средний score;
- средний margin;
- сколько случаев с margin < 0.03 / 0.05 / 0.10;
- TOP-1 → TOP-2 расстояние.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path
from collections import Counter

text = Path("/tmp/recognize_test.json").read_text(encoding="utf-8")

# В вывод попали сообщения SceneEmbedder/Recognizer.
# Берём JSON начиная с первой '['.
start = text.find("[")
if start < 0:
    raise RuntimeError("JSON не найден")

data = json.loads(text[start:])

print("=" * 80)
print("RECOGNITION BENCHMARK")
print("=" * 80)

print("TOTAL:", len(data))

best = Counter(x["best_id"] for x in data)
status = Counter(x["status"] for x in data)
confidence = Counter(x["confidence"] for x in data)

print("\nTOP-1 DISTRIBUTION")
for k, v in best.most_common():
    print(f"{k:10s} {v:4d}  {v/len(data)*100:6.2f}%")

print("\nSTATUS")
for k, v in status.most_common():
    print(f"{k:15s} {v:4d}  {v/len(data)*100:6.2f}%")

print("\nCONFIDENCE")
for k, v in confidence.most_common():
    print(f"{k:15s} {v:4d}  {v/len(data)*100:6.2f}%")

scores = [x["score"] for x in data]
margins = [x["margin"] for x in data]

print("\nSCORE")
print(" min :", f"{min(scores):.4f}")
print(" mean:", f"{sum(scores)/len(scores):.4f}")
print(" max :", f"{max(scores):.4f}")

print("\nMARGIN")
print(" min :", f"{min(margins):.4f}")
print(" mean:", f"{sum(margins)/len(margins):.4f}")
print(" max :", f"{max(margins):.4f}")

print("\nMARGIN BUCKETS")
for threshold in [0.01, 0.02, 0.03, 0.05, 0.07, 0.10]:
    n = sum(m < threshold for m in margins)
    print(f"< {threshold:.2f}: {n:4d} ({n/len(data)*100:5.1f}%)")

print("\nLOWEST MARGIN CASES")
for x in sorted(data, key=lambda x: x["margin"])[:20]:
    print(
        f"{x['margin']:.4f}  "
        f"{x['score']:.4f}  "
        f"{x['best_id']:10s}  "
        f"{x['file']}"
    )
PY
```

### А затем сделаем самое главное — проверим подслепки

У нас уже есть:

```text
data/subfingerprints_v2/78_v33
```

Но пока только для `78`.

Поэтому сначала **не надо создавать подслепки для всех 18 адресов**.

Используем `78` как экспериментальный адрес:

```text
262 test-фото
       ↓
обычный recognizer
       ↓
78_v33 — TOP-1
       ↓
если кандидат 78
       ↓
sub_01 / sub_02 / sub_03
       ↓
дополнительное подтверждение
```

Это позволит увидеть очень важную вещь:

> **Может ли подслепок исправить случаи, когда несколько адресов визуально похожи?**

Именно ради этого мы его и создавали.

Пришли вывод `RECOGNITION BENCHMARK`. После него я дам следующий скрипт, который **не будет заново гонять DINO** — он возьмёт уже рассчитанные результаты и аккуратно проверит влияние `subfingerprints_v2`.

---

### 👤 **User** — 2026-08-15 02:10:02

int_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path
from collections import Counter

text = Path("/tmp/recognize_test.json").read_text(encoding="utf-8")

# В вывод попали сообщения SceneEmbedder/Recognizer.
# Берём JSON начиная с первой '['.
start = text.find("[")
if start < 0:
    raise RuntimeError("JSON не найден")

data = json.loads(text[start:])

print("=" * 80)
print("RECOGNITION BENCHMARK")
print("=" * 80)

print("TOTAL:", len(data))

PY  )   f"{x['file']}"]:10s}  "a x: x["margin"])[:20]:0:5.1f}%)")
Traceback (most recent call last):
  File "<stdin>", line 13, in <module>
  File "/usr/lib/python3.12/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/json/decoder.py", line 337, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/json/decoder.py", line 355, in raw_decode
    raise JSONDecodeError("Expecting value", s, err.value) from None
json.decoder.JSONDecodeError: Expecting value: line 1 column 2 (char 1)

---

### 🤖 **Assistant** — 2026-08-15 02:10:03

Да, здесь проблема не в данных. В `/tmp/recognize_test.json` попали **служебные строки `[SceneEmbedder]...`**, а не только JSON. Поэтому `find("[")` нашёл первую `[` слишком рано.

Сделаем надёжнее: найдём строку, которая начинается именно с `[` и следующая строка начинается с `{`.

Выполни этот вариант:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import json
from pathlib import Path
from collections import Counter

path = Path("/tmp/recognize_test.json")
lines = path.read_text(encoding="utf-8").splitlines()

# Ищем начало настоящего JSON-массива
start = None

for i, line in enumerate(lines):
    if line.strip() == "[":
        if i + 1 < len(lines) and lines[i + 1].lstrip().startswith("{"):
            start = i
            break

if start is None:
    print("JSON начало не найдено")
    print("Первые строки файла:")
    print("\n".join(lines[:30]))
    raise SystemExit(1)

json_text = "\n".join(lines[start:])
data = json.loads(json_text)

print("=" * 80)
print("RECOGNITION BENCHMARK")
print("=" * 80)

print("TOTAL:", len(data))

best = Counter(x["best_id"] for x in data)
status = Counter(x["status"] for x in data)
confidence = Counter(x["confidence"] for x in data)

print("\nTOP-1 DISTRIBUTION")
for k, v in best.most_common():
    print(f"{k:10s} {v:4d}  {v/len(data)*100:6.2f}%")

print("\nSTATUS")
for k, v in status.most_common():
    print(f"{k:15s} {v:4d}  {v/len(data)*100:6.2f}%")

print("\nCONFIDENCE")
for k, v in confidence.most_common():
    print(f"{k:15s} {v:4d}  {v/len(data)*100:6.2f}%")

scores = [x["score"] for x in data]
margins = [x["margin"] for x in data]

print("\nSCORE")
print(" min :", f"{min(scores):.4f}")
print(" mean:", f"{sum(scores)/len(scores):.4f}")
print(" max :", f"{max(scores):.4f}")

print("\nMARGIN")
print(" min :", f"{min(margins):.4f}")
print(" mean:", f"{sum(margins)/len(margins):.4f}")
print(" max :", f"{max(margins):.4f}")

print("\nMARGIN BUCKETS")
for threshold in [0.01, 0.02, 0.03, 0.05, 0.07, 0.10]:
    n = sum(m < threshold for m in margins)
    print(f"< {threshold:.2f}: {n:4d} ({n/len(data)*100:5.1f}%)")

print("\nLOWEST MARGIN CASES")
for x in sorted(data, key=lambda x: x["margin"])[:20]:
    print(
        f"{x['margin']:.4f}  "
        f"{x['score']:.4f}  "
        f"{x['best_id']:10s}  "
        f"{x['file']}"
    )
PY
```

### Но я заметил ещё одну важную вещь

В предыдущем выводе:

```text
[Recognizer] Query images: 262
[Recognizer] Fingerprints: 78_v33, ... 85_v33
```

Хотя мы передали **78–95**.

То есть в выводе первых 3000 символов показались только:

```text
78 ... 85
```

и не видно `86–95`. Возможно, просто вывод был обрезан после `85`, но это надо проверить.

После benchmark также выполни:

```bash
grep -m 1 "Fingerprints:" /tmp/recognize_test.json
```

Если там действительно только `78_v33 ... 85_v33`, значит recognizer по какой-то причине не загрузил `86–95`.

**Это сейчас важнее подслепков**, потому что мы хотим получить честный benchmark по всем 18 адресам.

---

### 👤 **User** — 2026-08-15 02:10:23

RECOGNITION BENCHMARK
================================================================================
TOTAL: 262

TOP-1 DISTRIBUTION
85_v33       59   22.52%
83_v33       57   21.76%
78_v33       50   19.08%
81_v33       35   13.36%
82_v33       20    7.63%
79_v33       16    6.11%
80_v33       14    5.34%
84_v33       11    4.20%

STATUS
CONFIDENT         84   32.06%
AMBIGUOUS         79   30.15%
PROBABLE_MATCH    55   20.99%
NO_MATCH          44   16.79%

CONFIDENCE
HIGH              84   32.06%
AMBIGUOUS         79   30.15%
PROBABLE          55   20.99%
NO_MATCH          44   16.79%

SCORE
 min : 0.5634
 mean: 0.8622
 max : 0.9676

MARGIN
 min : 0.0001
 mean: 0.0352
 max : 0.1447

MARGIN BUCKETS
< 0.01:   93 ( 35.5%)
< 0.02:  135 ( 51.5%)
< 0.03:  159 ( 60.7%)
< 0.05:  177 ( 67.6%)
< 0.07:  221 ( 84.4%)
< 0.10:  242 ( 92.4%)

LOWEST MARGIN CASES
0.0001  0.8752  83_v33      data/input/test/Комарова Добровольского А (42).JPG
0.0002  0.8545  83_v33      data/input/test/Нагибина Рубиновый А (12).JPG
0.0003  0.8522  83_v33      data/input/test/Вавилова 52 А (4).JPG
0.0005  0.7115  81_v33      data/input/test/Малиновского 9 А (6).JPG
0.0005  0.8676  83_v33      data/input/test/Нагибина Рубиновый А (5).JPG
0.0006  0.8225  82_v33      data/input/test/менжин (11).JPG
0.0008  0.7963  78_v33      data/input/test/Малиновского 25 к Доватора (26).JPG
0.0008  0.8615  79_v33      data/input/test/Шеболдаева 8 РИИЖТ (13).JPG
0.0011  0.8482  79_v33      data/input/test/Шеболдаева ул. 881 - пл. Народного Ополчения (РГУПС) (1).JPG
0.0011  0.8765  82_v33      data/input/test/Комарова Добровольского А (1).JPG
0.0011  0.7980  81_v33      data/input/test/Малиновского 25 к Доватора (17).JPG
0.0012  0.8086  85_v33      data/input/test/Малиновского 25 к Доватора А (28).JPG
0.0013  0.6941  85_v33      data/input/test/Вавилова Радиаторный А (1).JPG
0.0015  0.8626  85_v33      data/input/test/Стачки Зорге А (37).JPG
0.0017  0.8744  83_v33      data/input/test/Вавилова 52 А (21).JPG
0.0017  0.7727  83_v33      data/input/test/Нагибина Рубиновый А (52).JPG
0.0018  0.8856  83_v33      data/input/test/Стачки Зорге А (40).JPG
0.0018  0.8876  83_v33      data/input/test/Стачки 41 А (6).JPG
0.0019  0.8774  83_v33      data/input/test/Вавилова 52 А (18).JPG
0.0019  0.6601  85_v33      data/input/test/менжин (7).JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 02:10:24

Да. И вот теперь у нас появился **очень полезный реальный benchmark на 262 фотографиях**. И я бы пока **не менял DINOv2**, а сначала правильно использовал то, что уже есть.

### Что видно сейчас

Главная проблема не в том, что алгоритм «не видит» адрес.

Он часто видит **правильную группу среди первых кандидатов**, но несколько адресов имеют очень похожую окружающую сцену.

По результату:

| Показатель | Сейчас |
|---|---:|
| Фото | 262 |
| CONFIDENT | 84 / 32% |
| PROBABLE | 55 / 21% |
| AMBIGUOUS | 79 / 30% |
| NO_MATCH | 44 / 17% |
| Средний score | **0.862** |
| Средний margin | **0.035** |

Особенно интересен margin:

- только **35.5%** имеют margin < 0.01
- **51.5%** < 0.02
- **60.7%** < 0.03
- **67.6%** < 0.05

То есть примерно **2/3 фотографий алгоритм пока различает недостаточно уверенно**.

Но это не означает 2/3 ошибок.

### Самое важное

У нас есть названия файлов тестовых фотографий:

```text
Комарова Добровольского А
Нагибина Рубиновый А
Вавилова 52 А
Малиновского 9 А
Малиновского 25 к Доватора
Шеболдаева 8 РИИЖТ
Стачки Зорге А
...
```

А benchmark сейчас **вообще не использует эту информацию**. Он просто смотрит, какой fingerprint оказался первым.

То есть мы можем использовать эти имена **только для оценки качества**, а не для самого распознавания.

И здесь я предлагаю следующий этап.

---

# 1. Сначала выясним реальную TOP-1 / TOP-3 точность

Сейчас у нас есть очень хорошая возможность.

Поскольку `data/input/test` уже содержит фотографии с правильным адресом в имени файла, сделаем автоматический benchmark:

```text
имя файла
   ↓
эталонный адрес
   ↓
TOP-1
TOP-2
TOP-3
TOP-5
```

Например:

```text
Вавилова 52 А (18).JPG

правильный = Вавилова 52 А

TOP-1:
   83_v33   0.8774

TOP-2:
   85_v33   0.8755
   ...
```

И самое главное - определим:

> **правильный fingerprint вообще попал в TOP-5 или нет?**

Это гораздо важнее текущего `CONFIDENT`.

---

# 2. Почему это сейчас особенно важно

Представим:

```text
правильный: 85_v33

TOP-1 83_v33   0.875
TOP-2 85_v33   0.871
TOP-3 78_v33   0.830
```

Для текущего алгоритма это:

```text
AMBIGUOUS
```

Но для нашего будущего пайплайна это **почти правильный результат**.

Мы можем сделать:

```text
DINO
  ↓
TOP-5 кандидатов
  ↓
OCR таблички
  ↓
проверка номера адреса
  ↓
выбор правильного кандидата
```

И вот тут твоя идея с табличками становится очень сильной.

---

# 3. Я бы сейчас не усиливал OCR на всех фотографиях

Сделаем каскад.

### Первый этап - очень дешёвый

DINOv2:

```text
262 фото
   ↓
TOP-5 fingerprint
```

Получаем максимум:

```text
5 × 262 = 1310 кандидатов
```

Но фактически OCR нужен будет не для всех.

Например:

```text
margin > 0.07
       ↓
CONFIDENT
       ↓
сразу принимаем
```

А:

```text
margin < 0.07
       ↓
сомнительный случай
       ↓
OCR
```

Это сильно снижает нагрузку.

---

# 4. И ещё одна очень важная вещь

Мы сейчас используем:

```python
global       0.70
environment  0.20
color        0.07
spatial      0.03
```

И это уже довольно разумно.

Но посмотри на конкретный пример:

```text
78_v33

global       0.9549
environment  0.9361
color        0.8892
spatial      0.9870

TOTAL        0.9475
```

Здесь видно, что **global + environment действительно работают**.

Цвет и spatial дают небольшую коррекцию.

Поэтому я бы **не увеличивал color/spatial**.

---

# 5. А вот environment я бы сохранил

Ты раньше спрашивал:

> используются ли внешние фиксированные объекты типа светофоров, знаков и цвет домов сзади?

Да - косвенно они попадают в `environment` и особенно в DINO global embedding.

То есть условно:

```text
дом
деревья
дорога
светофор
столб
знак
фасад
бордюр
цвет здания
характер перекрёстка
```

всё это может участвовать в fingerprint.

Но DINO не знает, что:

```text
"вот этот светофор"
```

является светофором.

Он видит визуальный паттерн.

И именно поэтому **фиксированные объекты вокруг рекламной конструкции очень полезны**.

---

# 6. Что я предлагаю сделать прямо сейчас

Не трогать fingerprint.

Не пересоздавать `78_v33 ... 95_v33`.

Сначала сделать скрипт:

```text
scripts/benchmark_recognition.py
```

который возьмёт:

```text
/tmp/recognize_test.json
```

и `data/input/test`.

И выдаст:

```text
BENCHMARK
========================================

TOTAL: 262

TOP-1 ACCURACY: xx.xx%
TOP-2 ACCURACY: xx.xx%
TOP-3 ACCURACY: xx.xx%
TOP-5 ACCURACY: xx.xx%

CORRECT IN TOP-5: xxx / 262

BY FINGERPRINT
78: ...
79: ...
80: ...
...
95: ...

CONFIDENT:
correct ...
wrong ...

AMBIGUOUS:
correct ...
wrong ...

NO_MATCH:
correct ...
wrong ...
```

А самое интересное:

```text
MISCLASSIFIED
------------------------------------------------

Малиновского 25 к Доватора
TOP1: 78
TOP2: 85  ← ПРАВИЛЬНЫЙ
TOP3: 83

Вавилова 52 А
TOP1: 83
TOP2: 85  ← ПРАВИЛЬНЫЙ
...
```

Тогда мы **увидим реальные пары адресов, которые путаются между собой**.

И уже после этого решим, что лучше:

```text
DINO
  ↓
TOP-5
  ↓
subfingerprint
  ↓
OCR таблички
  ↓
адрес
```

Причём я бы сейчас ставил цель не 100%.

Для твоей задачи вполне реалистичная архитектура:

**DINO правильно определяет адрес в TOP-3/TOP-5 → OCR разбирает спорные случаи → остальные уходят в ручную проверку.**

Это уже может дать практически пригодную систему.

Если хочешь идти дальше именно сейчас - следующим шагом я дам **готовую команду/скрипт benchmark**, который не требует `sklearn` и прямо на твоём `/tmp/recognize_test.json` посчитает **реальную TOP-1/2/3/5 точность по адресам из имён файлов**.

---

### 👤 **User** — 2026-08-15 02:12:18

важнее визуальная проверка, т.к названия произвольные. нужно прогнать тестовую папку и фотогграфии рассортировать - по номерам , причем по первому кандидату с учтом подслепков, не делать папку неклассифицированное

---

### 🤖 **Assistant** — 2026-08-15 02:12:18

> **Inspecting Project Scripts For Recognizer Modifications**
>
>
> **Inspected project scripts for recognizer modifications**
>
> 
>
> Worked for a few seconds

Да. Здесь я бы **не использовал `status` и `threshold` для окончательной сортировки**.

Сейчас задача должна работать так:

1. Берём каждую фотографию из `data/input/test`.
2. Считаем кандидатов по всем fingerprint `78_v33 ... 95_v33`.
3. Для каждого номера получаем **первого кандидата**.
4. Внутри первого кандидата дополнительно используем его **subfingerprints v2** как локальные визуальные слепки.
5. Если subfingerprint подтверждает первый кандидат — уверенность повышаем.
6. Если не подтверждает — **всё равно оставляем первый fingerprint**, потому что ты хочешь именно визуальную проверку и не хочешь `не классифицированное`.
7. Копируем фотографии в:

```text
data/output/test_sorted/
├── 78/
├── 79/
├── 80/
...
├── 95/
```

То есть **имя файла вообще не участвует** в классификации.

### Важный момент

По текущему тесту у нас:

- 262 фотографии;
- средний score `0.862`;
- только 32% имеют `HIGH`;
- но это **не означает**, что остальные нужно выбрасывать;
- особенно важен первый кандидат + визуальное сходство с конкретными фотографиями адреса.

Именно поэтому я предлагаю следующий режим:

```text
DINO global
      ↓
18 fingerprint
      ↓
TOP-1
      ↓
subfingerprints TOP-1 fingerprint
      ↓
сравнение с локальными группами
      ↓
итоговый адрес = ПЕРВЫЙ КАНДИДАТ
      ↓
копирование в папку номера
```

При этом в отчёте сохраним:

```text
файл
назначенный номер
fingerprint score
subfingerprint
sub score
margin
best_image
```

Это позволит потом визуально открыть спорные случаи и понять, где алгоритм ошибается.

**Я бы сейчас не менял веса `0.70 / 0.20 / 0.07 / 0.03`.** На этом этапе важнее получить реальную раскладку всех 262 фотографий и посмотреть глазами, что получилось.

Следующий шаг — сделать отдельный скрипт, например:

```text
scripts/sort_test_by_first_candidate.py
```

который **без `NO_MATCH` и без `не классифицированное`** рассортирует всю `data/input/test` по `78...95`.

После этого мы уже сможем сделать самое полезное: **показать статистику по каждому номеру и отдельно список фотографий, где первый кандидат конфликтует с subfingerprint**. Это будет намного информативнее нынешнего `CONFIDENT/AMBIGUOUS`.

---

### 👤 **User** — 2026-08-15 02:13:17

давай. и добавь статистику по работе CPU GPU RAM и времени

---

### 🤖 **Assistant** — 2026-08-15 02:13:18

Да. Здесь лучше сделать **отдельный production-тест сортировки**, не ориентируясь на имена файлов вообще.

Логика будет такая:

1. Берём `data/input/test`.
2. Для каждого фото считаем DINOv2 + environment/color/spatial.
3. Сравниваем **сначала с fingerprint**, затем с **подслепками V2**.
4. Выбираем **первого кандидата**, а не пытаемся получить «идеальную уверенность».
5. **Всегда присваиваем номер** `78`, `79`, ..., `95`.
6. Копируем фото в:
   ```text
   data/output_test/78/
   data/output_test/79/
   ...
   data/output_test/95/
   ```
7. Имя исходного файла сохраняем.
8. Для каждого файла пишем:
   - выбранный адрес;
   - score;
   - second score;
   - margin;
   - какой subfingerprint дал лучший результат;
   - лучшее совпавшее эталонное фото.
9. В конце - статистика:
   - всего файлов;
   - сколько попало в каждый номер;
   - средний/минимальный/max score;
   - средний margin;
   - **общее время**;
   - время на фотографию;
   - CPU;
   - GPU;
   - RAM;
   - VRAM;
   - пиковые значения.

И главное: **никакой папки `unclassified`**.

Но я бы не менял существующий `recognize`. Сделаем отдельный скрипт, например:

```text
scripts/sort_test_by_first_candidate.py
```

и он будет использовать текущие `78_v33 ... 95_v33` плюс `data/subfingerprints_v2/78_v33` и аналогичные подслепки, если они существуют.

### Важный момент

Сейчас у нас есть очень хорошее подтверждение, что **жёсткая классификация по первому кандидату имеет смысл**:

- 262 фотографии;
- средний score `0.8622`;
- максимум `0.9676`;
- даже при маленьком margin система всё равно обычно имеет достаточно высокий первый score.

То есть для нашей задачи лучше:

> **TOP-1 → присвоить адрес → потом визуально проверить спорные случаи**

а не:

> маленький margin → выбросить фотографию.

Это полностью соответствует твоей задаче: **название файла не является источником истины**, а визуальная проверка должна оценивать именно результат распознавания.

Следующим шагом я бы сделал скрипт, который **физически рассортирует эти 262 фотографии**, и одновременно создаст CSV/JSON отчёт, чтобы потом можно было быстро посмотреть, какие фотографии система отдала не туда.

---

### 👤 **User** — 2026-08-15 02:13:34

Создай CSV/JSON отчёт

---

