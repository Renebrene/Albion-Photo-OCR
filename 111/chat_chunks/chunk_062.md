## СЕССИЯ: Branch · готовая

**Создано:** 2026-08-16 00:03:27
**Обновлено:** 2026-08-19 17:08:07
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d41d-8908-83ea-b688-e34e85acfaa9](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d41d-8908-83ea-b688-e34e85acfaa9)

---

### 🤖 **Assistant** — 2026-08-15 19:21:07

Отлично. Подслепки пересозданы на чистой версии проекта. Теперь у нас есть корректная база для сравнения.

Текущая картина:

```
84_v33
 ├─ cluster_0: 38
 └─ cluster_1: 16

85_v33
 ├─ cluster_0: 31
 └─ cluster_1: 27

89_v33
 ├─ cluster_0: 11
 ├─ cluster_1: 30
 └─ cluster_2: 25

92_v33
 ├─ cluster_0: 12
 └─ cluster_1: 45

95_v33
 ├─ cluster_0: 33
 ├─ cluster_1: 44
 └─ cluster_2: 9
```

Малые группы пока правильно исключаем:

```
87_v33 cluster_1: 3 ❌
94_v33 cluster_2: 3 ❌
```

---

Следующий шаг — **не менять распознавание**, а сделать диагностический прогон.

Нужно получить ответ:

> Если вместо одного центра v33 проверить ближайший subcluster, меняется ли уверенность кандидата?

Для этого сначала сохраним текущий baseline:

```bash
mkdir -p output/subfinger_test

cp output/sequence_v38_1/sorted \
   /tmp/baseline_sorted -r
```

Проверим, что есть результаты:

```bash
find output/sequence_v38_1/sorted -type f | wc -l
```

Должно быть:

```
256
```

---

Теперь нужен скрипт сравнения.

Создай:

```bash
nano scripts/test_subfingerprint_matching.py
```

Но сначала надо посмотреть формат созданных данных.

Выполни:

```bash
find output/subclusters/89_v33 -type f | head
```

и:

```bash
ls data/fingerprints/89_v33
```

Мне нужно увидеть:
- где лежат embeddings кластеров;
- есть ли mapping `image -> cluster`.

Потому что сейчас `export_subclusters.py` сделал только визуальную раскладку:

```
output/subclusters/89_v33/cluster_0/*.JPG
```

а для сравнения нужен числовой fingerprint каждого cluster.

Возможны два варианта:

### Вариант 1 (лучший)
Сделать из каждого cluster мини-фингерпринт:

```
89_v33_cluster0
89_v33_cluster1
89_v33_cluster2
```

и гонять их как дополнительные представители.

### Вариант 2
На лету считать embedding всех фото в cluster.

Я бы выбрал вариант 1.

Тогда итоговая схема будет:

```
89_v33

  global
     |
     +-- cluster_0
     +-- cluster_1
     +-- cluster_2
```

А адрес остаётся один.

---

Следующая команда сейчас:

```bash
find output/subclusters/89_v33 -type f | wc -l
```

и:

```bash
ls data/fingerprints/89_v33
```

После этого сделаем генератор тестовых sub-fingerprint и сравнение с v38.1.

---

### 👤 **User** — 2026-08-15 19:22:21

давай сделваем так - если по итогам получается информация для двух субслепков - делаем два, если больше двух - третий и дргие исключаем. В исходных фото могут быть несколько кадров всего лишь с другого ракурса и они могут быть важны

---

### 🤖 **Assistant** — 2026-08-15 19:22:22

Да, это правильная стратегия. Не делать «математические кластеры ради кластеров», а делать **ограниченное количество рабочих подслепков**.

Я бы зафиксировал правило так:

# Правило формирования подслепков v1

Для каждого адресного слепка:

```
адрес_v33
    |
    +-- основной fingerprint (все фото)
    |
    +-- sub_1 (если есть значимая группа)
    |
    +-- sub_2 (если есть вторая значимая группа)
```

Максимум:

```
2 подслепка
```

Третий и последующие не используются.

---

## Критерии создания подслепка

Не просто наличие cluster.

Группа должна пройти фильтр:

### 1. Размер

Минимум:

```
>= 10% от общего количества фото
```

Пример:

89:

```
66 фото

cluster_0 = 11  ✅
cluster_1 = 30  ✅
cluster_2 = 25  ✅
```

Все три значимые.

Но берём только два.

Например:

```
89_v33

main
 |
 + sub_1 = cluster_1 (30)
 + sub_2 = cluster_2 (25)

cluster_0 (11) отбросить
```

---

### 2. Отделённость

Используем silhouette:

Пример:

```
89:
0.222
```

нормально.

Но если:

```
0.05
```

значит кластеризация сомнительная.

Не делать подслепки.

---

### 3. Малые группы

Автоматически исключаем:

```
<10 фото
```

Поэтому:

```
87 cluster_1 = 3
❌

94 cluster_2 = 3
❌
```

---

# Как выбрать два из трёх

Не брать просто первые.

Сортировка:

1. размер группы
2. отличие от основного центра

Например:

```
89

cluster_1
30 фото
distance 0.18

cluster_2
25 фото
distance 0.16

cluster_0
11 фото
distance 0.30
```

Несмотря на маленький cluster_0, он может быть самым отличным, но слишком маленький.

Берём:

```
30
25
```

---

# Почему это правильно для ваших фото

У вас типичная задача:

один объект:

```
адрес 89
```

может иметь:

```
лето
зима

дальний план
крупный план

слева
справа

разное освещение
```

Подслепки как раз нужны для этого.

Но если делать слишком много:

```
89_a
89_b
89_c
89_d
89_e
```

получится дробление и хуже будет распознавание.

---

# В распознавании

Не делаем:

```
фото → cluster → адрес
```

Это опасно.

Делаем:

```
фото

 |
 |
89_v33
89_sub1
89_sub2

↓

лучший score

↓

адрес 89
```

То есть подслепки только усиливают адрес.

---

# Для теста предлагаю сейчас сделать генератор:

```
scripts/build_subfingerprints_v1.py
```

Он:

1. берёт `output/subclusters`
2. анализирует кластеры
3. оставляет максимум 2
4. игнорирует маленькие
5. создаёт:

```
data/subfingerprints_v1/

89_v33/
    sub_1/
       embeddings.npy
       metadata.json

    sub_2/
       embeddings.npy
       metadata.json
```

И вывод:

```
SUBFINGERPRINTS V1

89_v33
images:66

created:
sub_1 30 images
sub_2 25 images

ignored:
cluster_0 11 images
reason: third cluster
```

---

После этого сравним:

```
recognizer v33
        vs
recognizer v33 + subfingerprints_v1
```

Это будет честный тест.

Я бы именно так и делал. Ваше условие «максимум два подслепка» хорошо подходит под реальные фотоотчёты.

---

### 👤 **User** — 2026-08-15 19:23:04

давай для эксперимента возбмем даже маленькие сублсепки

---

### 🤖 **Assistant** — 2026-08-15 19:23:05

Хорошо. Для **эксперимента** лучше не отбрасывать маленькие группы, чтобы понять, есть ли от них реальная польза.

Тогда делаем отдельный режим:

# SUBFINGERPRINT EXPERIMENT v0

Правила:

- берём **все кластеры**
- максимум **3 подслепка**
- ничего не удаляем
- даже маленькие группы сохраняем
- основной v33 остаётся как есть

Структура:

```
data/subfingerprints_exp/

84_v33/
 ├── sub_1/
 ├── sub_2/

85_v33/
 ├── sub_1/
 ├── sub_2/

87_v33/
 ├── sub_1/
 └── sub_2/

89_v33/
 ├── sub_1/
 ├── sub_2/
 └── sub_3/
```

Например:

```
89_v33

cluster_0  11 фото  → sub_1
cluster_1  30 фото  → sub_2
cluster_2  25 фото  → sub_3
```

---

Но важный момент: **не заменяем основной слепок**.

Проверяем только дополнительный маршрут:

Было:

```
фото
 |
DINO
 |
89_v33
 |
адрес 89
```

Эксперимент:

```
фото
 |
DINO
 |
----------------
|              |
89_v33     subfingerprints
                 |
              sub_1
              sub_2
              sub_3

↓
лучший score

↓
адрес 89
```

---

Сейчас надо сделать экспериментальный экспорт.

Создаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nano scripts/build_subfingerprints_exp.py
```

Логика:

1. Берём:

```
output/subclusters/*_v33/cluster_*
```

2. Для каждого cluster:
- читаем список JPG
- создаём отдельный fingerprint

3. Создаём:

```
data/subfingerprints_exp/
```

---

После создания проверим именно проблемные случаи:

### Радиаторный

Проверяем:

```
Радиаторный_24.JPG
Радиаторный_25.JPG
```

Ожидаем:

если они были в отдельной группе:

```
89_v33_subX
```

они должны поднять score.

---

### И те 7 изменений из v38.1:

Особенно:

```
Ашхабадский_08.JPG
89 -> 85

Зорге_06.JPG
89 -> 92

Малиновского_к_Доватора_10.JPG
94 -> 89
```

Смотрим:

- изменятся ли обратно;
- уменьшится ли margin;
- появятся ли новые уверенные кандидаты.

---

После эксперимента уже решим:

вариант А:
```
subfingerprints реально помогают
→ включаем в recognizer
```

вариант Б:
```
помогают только крупные группы
→ фильтр >=10%
```

вариант В:
```
не дают прироста
→ оставляем только v33
```

Я бы сейчас сделал именно «грязный эксперимент» с маленькими группами, потому что у нас есть подозрение, что редкие ракурсы (как Радиаторный 24/25) могут быть полезными.

---

### 👤 **User** — 2026-08-15 19:23:33

авай

---

### 🤖 **Assistant** — 2026-08-15 19:23:35

Делаем экспериментальный режим. Сейчас ничего не меняем в рабочем `v33`, создаём отдельные подслепки.

Сначала проверим, что у нас есть исходные кластеры:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find output/subclusters -maxdepth 2 -type d | sort
```

Если всё на месте — создаём экспериментальную папку:

```bash
mkdir -p data/subfingerprints_exp
```

Теперь делаем генератор.

Создай файл:

```bash
nano scripts/build_subfingerprints_exp.py
```

Вставь:

```python
#!/usr/bin/env python3

from pathlib import Path
import json
import shutil

PROJECT = Path(__file__).resolve().parent.parent

SRC = PROJECT / "output/subclusters"
DST = PROJECT / "data/subfingerprints_exp"

def main():

    print("=" * 80)
    print("BUILD SUBFINGERPRINTS EXP")
    print("=" * 80)

    DST.mkdir(parents=True, exist_ok=True)

    count = 0

    for addr in sorted(SRC.glob("*_v33")):

        clusters = sorted(
            addr.glob("cluster_*"),
            key=lambda x: x.name
        )

        if not clusters:
            continue

        out_addr = DST / addr.name
        out_addr.mkdir(exist_ok=True)

        print()
        print(addr.name)

        for idx, cluster in enumerate(clusters, start=1):

            images = sorted(
                cluster.glob("*.JPG")
            )

            if not images:
                continue

            sub = out_addr / f"sub_{idx}"
            sub.mkdir(exist_ok=True)

            for img in images:
                shutil.copy2(
                    img,
                    sub / img.name
                )

            meta = {
                "parent": addr.name,
                "sub_id": idx,
                "images": len(images),
                "source_cluster": cluster.name,
                "files": [
                    x.name for x in images
                ]
            }

            with open(
                sub / "metadata.json",
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    meta,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            print(
                f"  sub_{idx}: {len(images)} images"
            )

            count += 1

print()
    print("=" * 80)
    print("DONE")
    print("created:", count)
    print(DST)

if __name__ == "__main__":
    main()
```

Запуск:

```bash
uv run python scripts/build_subfingerprints_exp.py
```

Проверка:

```bash
find data/subfingerprints_exp -maxdepth 2 -type d | sort
```

---

Но это пока **только разложение групп**. Следующий шаг — самое важное:

создать из каждой группы настоящий fingerprint:

например:

```
89_v33
 ├── основной
 ├── sub_1
 ├── sub_2
 └── sub_3
```

через существующий:

```bash
scene-fingerprint create
```

Надо будет сделать пакетный генератор:

```
data/subfingerprints_exp
        |
        v
data/fingerprints_sub_exp
        |
        |
89_v33_sub1
89_v33_sub2
...
```

И потом прогнать тот же `sort_sequence_v38_1.py`, но с расширенной базой.

Сначала сделай этот шаг и покажи вывод `BUILD SUBFINGERPRINTS EXP`.

---

### 👤 **User** — 2026-08-15 19:24:32

продолжаем

---

### 🤖 **Assistant** — 2026-08-15 19:24:34

Продолжаем. Сейчас у нас есть только группировка файлов, теперь надо сделать **настоящие слепки подкластеров**.

Цель:

```
data/fingerprints_sub_exp/

78_v33_sub1
78_v33_sub2

84_v33_sub1
84_v33_sub2

89_v33_sub1
89_v33_sub2
89_v33_sub3
...
```

Они будут использоваться только для эксперимента.

---

Сначала проверим, что генерация групп прошла:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find data/subfingerprints_exp -maxdepth 2 -type d | sort | head -50
```

Если есть:

```
data/subfingerprints_exp/89_v33/sub_1
data/subfingerprints_exp/89_v33/sub_2
data/subfingerprints_exp/89_v33/sub_3
```

идём дальше.

---

Создаём пакетное создание слепков.

Файл:

```bash
nano scripts/create_subfingerprint_exp.py
```

Код:

```python
#!/usr/bin/env python3

from pathlib import Path
import subprocess

PROJECT = Path(__file__).resolve().parent.parent

SRC = PROJECT / "data/subfingerprints_exp"
DST = PROJECT / "data/fingerprints_sub_exp"

def main():

    DST.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 80)
    print("CREATE SUBFINGERPRINTS EXP")
    print("=" * 80)

for addr in sorted(SRC.glob("*_v33")):

        for sub in sorted(addr.glob("sub_*")):

            images = list(sub.glob("*.JPG"))

            if not images:
                continue

fp_name = (
                f"{addr.name}_{sub.name}"
            )

            print()
            print(
                "CREATE",
                fp_name,
                len(images),
                "images"
            )

cmd = [
                "uv",
                "run",
                "scene-fingerprint",
                "create",
                fp_name,
                str(sub)
            ]

            subprocess.run(
                cmd,
                cwd=PROJECT
            )

print()
    print("=" * 80)
    print("DONE")
    print(DST)

if __name__ == "__main__":
    main()
```

---

Запуск:

```bash
uv run python scripts/create_subfingerprint_exp.py
```

Будет примерно:

```
CREATE 84_v33_sub1 38 images
CREATE 84_v33_sub2 16 images

CREATE 89_v33_sub1 11 images
CREATE 89_v33_sub2 30 images
CREATE 89_v33_sub3 25 images
```

---

Потом проверяем:

```bash
find data/fingerprints -maxdepth 1 -type d | grep sub
```

---

Следующий этап после этого:

1. Сделаем копию текущего recognizer:

```
recognizer.py
        |
        +-- v33 baseline
        |
        +-- v33 + sub_exp
```

2. Прогоним:

- текущие 256 фото
- сравним `Changed`
- отдельно посмотрим:
  - Радиаторный_24
  - Радиаторный_25
  - 7 случаев из v38.1

3. Если подслепки улучшают — интегрируем уже аккуратно в основной алгоритм.

---

### 👤 **User** — 2026-08-15 19:24:43

subfingerprints_exp.py
================================================================================
BUILD SUBFINGERPRINTS EXP
================================================================================

84_v33
  sub_1: 38 images
  sub_2: 16 images

85_v33
  sub_1: 31 images
  sub_2: 27 images

87_v33
  sub_1: 43 images
  sub_2: 3 images

89_v33
  sub_1: 11 images
  sub_2: 30 images
  sub_3: 25 images

92_v33
  sub_1: 12 images
  sub_2: 45 images

94_v33
  sub_1: 28 images
  sub_2: 36 images
  sub_3: 3 images

95_v33
  sub_1: 33 images
  sub_2: 44 images
  sub_3: 9 images

================================================================================
DONE
created: 17
/home/alexice/projects/scene_fingerprint_mvp_v02/data/subfingerprints_exp
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ find data/subfingerprints_exp -maxdepth 2 -type d | sort
data/subfingerprints_exp
data/subfingerprints_exp/84_v33
data/subfingerprints_exp/84_v33/sub_1
data/subfingerprints_exp/84_v33/sub_2
data/subfingerprints_exp/85_v33
data/subfingerprints_exp/85_v33/sub_1
data/subfingerprints_exp/85_v33/sub_2
data/subfingerprints_exp/87_v33
data/subfingerprints_exp/87_v33/sub_1
data/subfingerprints_exp/87_v33/sub_2
data/subfingerprints_exp/89_v33
data/subfingerprints_exp/89_v33/sub_1
data/subfingerprints_exp/89_v33/sub_2
data/subfingerprints_exp/89_v33/sub_3
data/subfingerprints_exp/92_v33
data/subfingerprints_exp/92_v33/sub_1
data/subfingerprints_exp/92_v33/sub_2
data/subfingerprints_exp/94_v33
data/subfingerprints_exp/94_v33/sub_1
data/subfingerprints_exp/94_v33/sub_2
data/subfingerprints_exp/94_v33/sub_3
data/subfingerprints_exp/95_v33
data/subfingerprints_exp/95_v33/sub_1
data/subfingerprints_exp/95_v33/sub_2
data/subfingerprints_exp/95_v33/sub_3

---

### 🤖 **Assistant** — 2026-08-15 19:24:45

Отлично. Первый этап эксперимента готов. Получилось именно то, что хотели: **не отбрасываем маленькие группы**, чтобы проверить их влияние.

Сейчас имеем:

```
17 экспериментальных подслепков
```

Распределение:

```
84_v33
 ├─ sub_1 38
 └─ sub_2 16

85_v33
 ├─ sub_1 31
 └─ sub_2 27

87_v33
 ├─ sub_1 43
 └─ sub_2 3        ← экспериментальная маленькая группа

89_v33
 ├─ sub_1 11       ← возможно важный ракурс
 ├─ sub_2 30
 └─ sub_3 25

92_v33
 ├─ sub_1 12
 └─ sub_2 45

94_v33
 ├─ sub_1 28
 ├─ sub_2 36
 └─ sub_3 3

95_v33
 ├─ sub_1 33
 ├─ sub_2 44
 └─ sub_3 9
```

Это хороший набор для проверки.

---

Следующий шаг: создать реальные fingerprint из этих групп.

Но я немного изменю подход.

Не будем смешивать их с:

```
data/fingerprints/
```

Сделаем отдельную папку:

```
data/fingerprints_sub_exp/
```

чтобы потом можно было удалить одним движением.

---

Создаём:

```bash
mkdir -p data/fingerprints_sub_exp
```

Теперь нужен пакетный скрипт, но надо учесть одну особенность:

`scene-fingerprint create` сейчас пишет напрямую в:

```
data/fingerprints
```

Поэтому просто запускать его нельзя.

Сначала посмотрим, поддерживает ли `FingerprintManager` другой путь.

Проверка:

```bash
grep -R "fingerprints" -n app | head -30
```

и:

```bash
grep -R "data/fingerprints" -n app scripts
```

---

Если путь зашит, сделаем временный режим:

```
data/fingerprints/
      |
      + v33_original

data/fingerprints_sub_exp/
      |
      + 89_v33_sub_1
```

или добавим переменную:

```
FINGERPRINT_ROOT
```

Это даже полезно для будущего веб-интерфейса, потому что там будут разные базы:

```
/storage/fingerprints/legal/
/storage/fingerprints/test/
```

---

После создания подслепков будем делать сравнение:

### База 1 (текущая)

```
78_v33
79_v33
...
95_v33
```

### База 2 (эксперимент)

```
78_v33
79_v33
...
95_v33

+
84_v33_sub_1
84_v33_sub_2
...
95_v33_sub_3
```

Но важно: результат должен возвращать **родительский адрес**, а не:

```
89_v33_sub_2
```

То есть:

```
89_v33_sub_2
        |
        ↓
       89
```

---

Сейчас дай вывод:

```bash
grep -R "data/fingerprints" -n app scripts
```

Посмотрим самый чистый способ подключить экспериментальную базу без ломки v33.

---

### 👤 **User** — 2026-08-15 19:25:20

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ mkdir -p data/fingerprints_sub_exp
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -R "fingerprints" -n app | head -30
app/core/recognizer.py.before_restore_old_matching_20260815_025751:103:        fingerprints=None,
app/core/recognizer.py.before_restore_old_matching_20260815_025751:119:        loaded_fingerprints = []
app/core/recognizer.py.before_restore_old_matching_20260815_025751:121:        # Optional whitelist of fingerprints.
app/core/recognizer.py.before_restore_old_matching_20260815_025751:122:        # If provided, ONLY these fingerprints are used.
app/core/recognizer.py.before_restore_old_matching_20260815_025751:123:        if fingerprints is not None:
app/core/recognizer.py.before_restore_old_matching_20260815_025751:124:            allowed_fingerprints = {
app/core/recognizer.py.before_restore_old_matching_20260815_025751:126:                for item in fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025751:130:            allowed_fingerprints = None
app/core/recognizer.py.before_restore_old_matching_20260815_025751:133:            self.manager.list_fingerprints()
app/core/recognizer.py.before_restore_old_matching_20260815_025751:143:                allowed_fingerprints is not None
app/core/recognizer.py.before_restore_old_matching_20260815_025751:145:                not in allowed_fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025751:183:            loaded_fingerprints.append(
app/core/recognizer.py.before_restore_old_matching_20260815_025751:190:        if not loaded_fingerprints:
app/core/recognizer.py.before_restore_old_matching_20260815_025751:193:                "fingerprints found."
app/core/recognizer.py.before_restore_old_matching_20260815_025751:200:                for fp_id, _ in loaded_fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025751:283:            for fingerprint_id, data in loaded_fingerprints:
app/core/recognizer.py.before_restore_old_matching_20260815_025724:103:        fingerprints=None,
app/core/recognizer.py.before_restore_old_matching_20260815_025724:119:        loaded_fingerprints = []
app/core/recognizer.py.before_restore_old_matching_20260815_025724:121:        # Optional whitelist of fingerprints.
app/core/recognizer.py.before_restore_old_matching_20260815_025724:122:        # If provided, ONLY these fingerprints are used.
app/core/recognizer.py.before_restore_old_matching_20260815_025724:123:        if fingerprints is not None:
app/core/recognizer.py.before_restore_old_matching_20260815_025724:124:            allowed_fingerprints = {
app/core/recognizer.py.before_restore_old_matching_20260815_025724:126:                for item in fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025724:130:            allowed_fingerprints = None
app/core/recognizer.py.before_restore_old_matching_20260815_025724:133:            self.manager.list_fingerprints()
app/core/recognizer.py.before_restore_old_matching_20260815_025724:143:                allowed_fingerprints is not None
app/core/recognizer.py.before_restore_old_matching_20260815_025724:145:                not in allowed_fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025724:183:            loaded_fingerprints.append(
app/core/recognizer.py.before_restore_old_matching_20260815_025724:190:        if not loaded_fingerprints:
app/core/recognizer.py.before_restore_old_matching_20260815_025724:193:                "fingerprints found."
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:25:21

Вывод показывает важную вещь: `grep` поймал в основном старые backup-файлы. Нужно смотреть только рабочие файлы.

Сделаем точнее:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -R "data/fingerprints" -n app --exclude="*.bak*" --exclude="*.backup*" --exclude="*.before*"
```

и отдельно:

```bash
grep -R "FingerprintManager" -n app --exclude="*.bak*" --exclude="*.backup*" --exclude="*.before*"
```

---

Но уже видно по `recognizer.py.before_restore_old_matching...`, что у нас есть хороший вариант:

```python
recognize(..., fingerprints=None)
```

То есть распознавание умеет принимать список разрешённых fingerprint.

Это даже лучше.

Для эксперимента не надо делать отдельный движок.

Сделаем так:

## Экспериментальная база

Вместо:

```
78_v33
79_v33
...
95_v33
```

передаём:

```
78_v33
79_v33
...
95_v33

84_v33_sub_1
84_v33_sub_2

89_v33_sub_1
89_v33_sub_2
89_v33_sub_3
...
```

А потом в результате добавим группировку:

```
89_v33_sub_2
        |
        ↓
parent=89
```

---

Следующий шаг:

Надо создать сами fingerprint.

Проверим, куда пишет create:

```bash
grep -R "class FingerprintManager" -n app
```

и:

```bash
grep -R "create(" -n app/core | head -20
```

---

Скорее всего у нас есть два пути:

### Вариант А (предпочтительный)
Добавить временный параметр:

```bash
scene-fingerprint create \
    89_v33_sub_1 \
    data/subfingerprints_exp/89_v33/sub_1 \
    --root data/fingerprints_sub_exp
```

Это потом пригодится для веб-интерфейса.

### Вариант Б
Создать через текущий механизм:

```bash
scene-fingerprint create \
89_v33_sub_1 \
data/subfingerprints_exp/89_v33/sub_1
```

потом перенести:

```bash
mv data/fingerprints/89_v33_sub_1 \
   data/fingerprints_sub_exp/
```

---

Я бы сейчас не трогал CLI. Сначала быстро сделаем рабочий эксперимент через текущий `create`, потом уже вынесем путь в настройки для будущего GUI.

Следующая команда:

```bash
grep -R "FINGERPRINT" -n app/core app/cli.py
```

Посмотрим, где проще подключить отдельный каталог.

---

### 👤 **User** — 2026-08-15 19:25:41

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -R "data/fingerprints" -n app --exclude="*.bak*" --exclude="*.backup*" --exclude="*.before*"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -R "FingerprintManager" -n app --exclude="*.bak*" --exclude="*.backup*" --exclude="*.before*"
app/core/fingerprint.py:14:class FingerprintManager:
grep: app/core/__pycache__/fingerprint.cpython-312.pyc: binary file matches
app/pipeline/worker.py:7:from app.core.fingerprint import FingerprintManager
app/pipeline/worker.py:24:        self.manager = FingerprintManager(
app/main.py:5:from app.core.fingerprint import FingerprintManager
app/main.py:9:manager = FingerprintManager(settings, embedder)
app/cli.py:10:from app.core.fingerprint import FingerprintManager
app/cli.py:396:        manager = FingerprintManager(
app/cli.py:567:        manager = FingerprintManager(
app/cli.py:608:        manager = FingerprintManager(
grep: app/__pycache__/cli.cpython-312.pyc: binary file matches
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:25:43

Отлично. Значит путь не зашит строкой `data/fingerprints`, а идёт через `FingerprintManager` и настройки. Это хороший вариант — потом легко вынести в веб-интерфейс.

Теперь смотрим сам менеджер.

Выполни:

```bash
sed -n '1,120p' app/core/fingerprint.py
```

и:

```bash
sed -n '380,430p' app/cli.py
```

Нужно увидеть, как `create` получает путь.

---

Предварительно уже понятно, что архитектуру лучше сделать так:

```
data/
├── fingerprints/              # рабочие v33
│   ├── 78_v33
│   ├── 79_v33
│   └── ...
│
├── fingerprints_sub_exp/      # эксперимент
│   ├── 89_v33_sub_1
│   ├── 89_v33_sub_2
│   └── ...
```

А в будущем:

```
settings.json

{
 "fingerprint_root":
 "data/fingerprints"
}
```

и веб-интерфейс сможет переключать:

```
[ Основная база v33 ]
[ Экспериментальная ]
[ Архивная ]
```

---

После просмотра `fingerprint.py` сделаем маленький пакетный скрипт:

```
subfingerprints_exp
        |
        |
scene-fingerprint create
        |
        v
fingerprints_sub_exp
```

и сразу проверим один адрес:

```bash
89_v33_sub_1
```

Не будем сразу создавать все 17 — сначала один тестовый.

После создания проверим:

```bash
ls data/fingerprints_sub_exp/89_v33_sub_1
```

Должны появиться:

```
embeddings.npy
metadata.json
centroid.npy
faiss.index
...
```

После этого запускаем полный пакет.

---

### 👤 **User** — 2026-08-15 19:26:11

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '1,120p' app/core/fingerprint.py
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import faiss
import numpy as np

from .image import image_files
from .scene_analyzer import CompactDescriptor

class FingerprintManager:
    """
    Fingerprint storage for Scene Fingerprint v3.3 compact.

    Stored:

        embeddings.npy
        centroid.npy
        representatives.npy
        representative_indices.npy

        environment_embeddings.npy
        color_embeddings.npy
        spatial_embeddings.npy

        faiss.index
        metadata.json

    Patch storage:
        DISABLED
    """

    VERSION = "3.3"

    def __init__(
        self,
        settings,
        embedder,
    ):
        self.settings = settings
        self.embedder = embedder

        self.settings.fingerprints_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _path(
        self,
        fingerprint_id,
    ):
        return (
            self.settings.fingerprints_dir
            / str(fingerprint_id)
        )

    def list_fingerprints(self):
        result = []

        root = (
            self.settings.fingerprints_dir
        )

        if not root.exists():
            return result

        for directory in sorted(
            root.iterdir()
        ):
            if not directory.is_dir():
                continue

            metadata_file = (
                directory
                / "metadata.json"
            )

            if not metadata_file.exists():
                continue

            try:
                metadata = json.loads(
                    metadata_file.read_text(
                        encoding="utf-8"
                    )
                )
            except (
                OSError,
                ValueError,
                json.JSONDecodeError,
            ):
                continue

            result.append(
                {
                    "id": directory.name,
                    **metadata,
                }
            )

        return result

    @staticmethod
    def _normalize_rows(array):
        array = np.asarray(
            array,
            dtype=np.float32,
        )

        if array.ndim == 1:
            array = array.reshape(
                1,
                -1,
            )

        norms = np.linalg.norm(
            array,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '380,430p' app/cli.py
    if args.command == "create":

        folder = Path(
            args.folder
        )

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: "
                f"{folder}"
            )

        embedder = SceneEmbedder(
            settings
        )

        manager = FingerprintManager(
            settings,
            embedder,
        )

        metadata = manager.create(
            args.fingerprint,
            folder,
            embedder,
        )

        print()

        print(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    # --------------------------------------------------
    # QUEUE BATCH ADD
    # --------------------------------------------------

    if args.command == "queue-batch-add":

        from app.pipeline.queue import JobQueue

        queue = JobQueue(
            settings.data_dir / "jobs.db"
        )

---

### 🤖 **Assistant** — 2026-08-15 19:26:12

Отлично. Теперь видно архитектуру. У нас всё сделано правильно: **путь к хранилищу задаётся через `settings.fingerprints_dir`**, значит для эксперимента не надо ломать CLI.

Нужно посмотреть только настройки.

Выполни:

```bash
grep -R "fingerprints_dir" -n app
```

Скорее всего там будет что-то вроде:

```python
settings.fingerprints_dir = data_dir / "fingerprints"
```

---

Дальше есть два аккуратных варианта.

## Вариант 1 (лучший для эксперимента)

Сделать временную переменную окружения:

```bash
FINGERPRINTS_DIR=data/fingerprints_sub_exp
```

и запускать создание подслепков туда.

Плюс:
- ничего не меняем;
- потом это легко уйдёт в веб-интерфейс;
- разные базы можно переключать.

---

## Вариант 2 (быстрее)

Перед запуском пакетного создания временно заменить:

```python
fingerprints
```

на:

```python
fingerprints_sub_exp
```

Но это хуже — потом можно забыть вернуть.

---

Я бы сделал сейчас правильно: добавить поддержку отдельного каталога.

Например:

```python
settings.py

fingerprints_dir = (
    Path(os.getenv(
        "FINGERPRINTS_DIR",
        data_dir / "fingerprints"
    ))
)
```

Тогда:

обычный режим:

```bash
uv run scene-fingerprint recognize ...
```

использует:

```
data/fingerprints
```

а эксперимент:

```bash
FINGERPRINTS_DIR=data/fingerprints_sub_exp \
uv run python scripts/create_subfingerprint_exp.py
```

создаёт туда.

Это сразу приближает нас к будущему веб-интерфейсу, где будет выбор базы.

---

После этого сделаем пакетный create всех 17:

```text
84_v33_sub_1
84_v33_sub_2

85_v33_sub_1
85_v33_sub_2

...

95_v33_sub_3
```

Потом проверим:

```bash
find data/fingerprints_sub_exp -maxdepth 1 -type d | sort
```

и перейдём к самому интересному — сравнению распознавания.

Сейчас покажи:

```bash
grep -R "fingerprints_dir" -n app
```

чтобы точно встроить без риска.

---

### 👤 **User** — 2026-08-15 19:26:27

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -R "fingerprints_dir" -n app
app/core/config.py:16:    def fingerprints_dir(self):
app/core/fingerprint.py.before_patchfix:17:        self.root = Path(settings.fingerprints_dir)
app/core/fingerprint.py:46:        self.settings.fingerprints_dir.mkdir(
app/core/fingerprint.py:56:            self.settings.fingerprints_dir
app/core/fingerprint.py:64:            self.settings.fingerprints_dir
app/core/fingerprint.py.bak_before_create_opt:45:        self.settings.fingerprints_dir.mkdir(
app/core/fingerprint.py.bak_before_create_opt:55:            self.settings.fingerprints_dir
app/core/fingerprint.py.bak_before_create_opt:63:            self.settings.fingerprints_dir
grep: app/core/__pycache__/fingerprint.cpython-312.pyc: binary file matches
grep: app/core/__pycache__/config.cpython-312.pyc: binary file matches
app/cli.py:485:                settings.fingerprints_dir
grep: app/__pycache__/cli.cpython-312.pyc: binary file matches
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:26:30

Отлично. Сейчас видно, что **основной recognizer пока вообще не использует subfingerprints**. Мы их только создали:

```
data/subfingerprints_exp
```

но текущий путь:

```
recognize
  ↓
FingerprintManager
  ↓
data/fingerprints/*_v33
```

их не читает.

Для эксперимента лучше **не ломать v33**, а сделать второй слой проверки:

```
обычный поиск v33
        |
        |
        +-- если уверенность высокая → оставить
        |
        +-- если сомнение / близкие кандидаты
                 |
                 ↓
          проверка subfingerprints_exp
                 |
                 ↓
          уточнение адреса
```

То есть subfingerprint работает как "уточнитель", а не как отдельная база.

---

## Этап 1. Проверяем влияние subfingerprint

Сделаем копию текущего распознавания:

```
recognizer_v33
```

и добавим:

```
sub_match_score
```

Логика:

Например:

фото:

```
89
score 0.71
```

проверяем:

```
89_v33/sub_1
89_v33/sub_2
89_v33/sub_3
```

получаем:

```
sub_1 0.83
sub_2 0.61
sub_3 0.58
```

тогда:

```
итог = 89
подтип = sub_1
```

Но наружу имя остается:

```
89
```

---

## Важно

Твоё решение с маленькими sub пока оставляем для эксперимента:

```
87:
 sub_1 43
 sub_2 3

94:
 sub_1 28
 sub_2 36
 sub_3 3
```

После теста маленькие:

```
3 картинки
```

скорее всего уберем.

Правило потом:

```
subcluster < 5 фото
        ↓
не создаем
```

---

## Следующий шаг

Создаем отдельный каталог:

```
data/fingerprints_sub_exp
```

уже есть.

Теперь туда надо положить реальные fingerprint-структуры, а не просто папки с JPG.

Сделаем генератор:

```
scripts/build_subfingerprint_database.py
```

Он:

берет:

```
data/subfingerprints_exp
```

пример:

```
89_v33
 ├── sub_1
 │     11 jpg
 ├── sub_2
 │     30 jpg
 └── sub_3
       25 jpg
```

и создает:

```
data/fingerprints_sub_exp

89_v33_sub1
89_v33_sub2
89_v33_sub3
```

с обычным:

```
embeddings.npy
centroid.npy
faiss.index
metadata.json
```

То есть старый код сможет их читать.

---

После этого тест:

1. обычная база:

```
data/fingerprints
```

2. расширенная:

```
data/fingerprints
+
data/fingerprints_sub_exp
```

и сравниваем:

```
Changed:
7
```

было:

```
Changed: ?
```

стало:

```
Changed: ?
```

Особенно смотрим:

```
Радиаторный_24
Радиаторный_25
```

и подобные.

---

Следующий файл, который надо сделать:

```
scripts/build_subfingerprint_database.py
```

Он не трогает рабочий v33 и создаёт только экспериментальную базу.

После этого уже добавим переключатель:

```
--use-subfingerprints
```

в recognize.

---

### 👤 **User** — 2026-08-15 19:26:50

делаем

---

### 🤖 **Assistant** — 2026-08-15 19:26:51

Делаем. Первый шаг — создаём генератор экспериментальной базы subfingerprints.

Создай файл:

```bash
nano scripts/build_subfingerprint_database.py
```

вставь:

```python
#!/usr/bin/env python3

from pathlib import Path
import shutil
import json
import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager

PROJECT = Path(__file__).resolve().parent.parent

SOURCE = PROJECT / "data/subfingerprints_exp"

TARGET = PROJECT / "data/fingerprints_sub_exp"

def main():

    print("=" * 80)
    print("BUILD SUBFINGERPRINT DATABASE")
    print("=" * 80)

    TARGET.mkdir(
        parents=True,
        exist_ok=True
    )

    settings = Settings()

    embedder = SceneEmbedder(
        settings
    )

    manager = FingerprintManager(
        settings,
        embedder
    )

created = 0

for address_dir in sorted(SOURCE.iterdir()):

        if not address_dir.is_dir():
            continue

address = address_dir.name

for sub_dir in sorted(address_dir.iterdir()):

            if not sub_dir.is_dir():
                continue

images = list(
                sub_dir.glob("*.JPG")
            ) + list(
                sub_dir.glob("*.jpg")
            )

if not images:
                continue

fp_id = (
                address
                + "_"
                + sub_dir.name
            )

print()
            print(fp_id)
            print(
                " images:",
                len(images)
            )

# временная папка
            tmp = TARGET / "_tmp"

            if tmp.exists():
                shutil.rmtree(tmp)

            tmp.mkdir()

for img in images:
                shutil.copy2(
                    img,
                    tmp / img.name
                )

# переключаем каталог fingerprint
            old = settings.fingerprints_dir

            settings.fingerprints_dir = TARGET

manager.create(
                fp_id,
                tmp,
                embedder
            )

settings.fingerprints_dir = old

shutil.rmtree(tmp)

            created += 1

print()
    print("=" * 80)
    print("DONE")
    print("created:", created)
    print(TARGET)

if __name__ == "__main__":
    main()
```

---

Потом запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/build_subfingerprint_database.py
```

Ожидаемый результат:

```
BUILD SUBFINGERPRINT DATABASE
================================================================================

84_v33_sub_1
 images: 38

84_v33_sub_2
 images: 16

...

95_v33_sub_3
 images: 9

================================================================================
DONE
created: 17
data/fingerprints_sub_exp
```

---

Проверяем:

```bash
find data/fingerprints_sub_exp -maxdepth 2 -name metadata.json | sort
```

должно быть:

```
data/fingerprints_sub_exp/84_v33_sub_1/metadata.json
data/fingerprints_sub_exp/84_v33_sub_2/metadata.json
...
data/fingerprints_sub_exp/95_v33_sub_3/metadata.json
```

После этого сделаем второй этап — добавим в `recognize` необязательный режим:

```bash
--use-subfingerprints
```

чтобы старый v33 и экспериментальная база сравнивались параллельно.

---

### 👤 **User** — 2026-08-15 19:27:30

Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 7768.13it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.

84_v33_sub_1
 images: 38
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/build_subfingerprint_database.py", line 132, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/build_subfingerprint_database.py", line 106, in main
    settings.fingerprints_dir = TARGET
    ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<string>", line 4, in __setattr__
dataclasses.FrozenInstanceError: cannot assign to field 'fingerprints_dir'

---

### 🤖 **Assistant** — 2026-08-15 19:27:31

Отлично, ошибка понятная. `Settings` у нас сделан как **frozen dataclass**, поэтому нельзя менять:

```python
settings.fingerprints_dir = TARGET
```

Это даже хорошо — настройки защищены.

Сделаем правильно: создадим отдельный экземпляр `Settings` для экспериментальной базы.

Сначала посмотрим `config.py`:

```bash
sed -n '1,80p' app/core/config.py
```

Скорее всего там что-то вроде:

```python
@dataclass(frozen=True)
class Settings:
```

и есть `data_dir`.

---

Пока можно исправить без изменения архитектуры.

Открой:

```bash
nano scripts/build_subfingerprint_database.py
```

Замени блок:

```python
settings = Settings()

embedder = SceneEmbedder(
    settings
)

manager = FingerprintManager(
    settings,
    embedder
)
```

на:

```python
settings = Settings()

embedder = SceneEmbedder(
    settings
)
```

---

А внутри цикла замени:

```python
# переключаем каталог fingerprint
old = settings.fingerprints_dir

settings.fingerprints_dir = TARGET

manager.create(
    fp_id,
    tmp,
    embedder
)

settings.fingerprints_dir = old
```

на:

```python
exp_settings = Settings(
    fingerprints_dir=TARGET
)

manager = FingerprintManager(
    exp_settings,
    embedder
)

manager.create(
    fp_id,
    tmp,
    embedder
)
```

---

Но это зависит от того, какие поля принимает `Settings`.

Поэтому сначала покажи:

```bash
sed -n '1,100p' app/core/config.py
```

После этого дам точный патч под твой класс. Сейчас мы на правильном пути — сама идея с отдельной базой работает, надо только корректно создать настройки.

---

### 👤 **User** — 2026-08-15 19:27:45

from dataclasses import dataclass
from pathlib import Path
import os
import torch

@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("SCENE_HOST", "127.0.0.1")
    port: int = int(os.getenv("SCENE_PORT", "8080"))
    data_dir: Path = Path(os.getenv("SCENE_DATA", "data"))
    model_name: str = os.getenv("SCENE_MODEL", "facebook/dinov2-base")
    device: str = os.getenv("SCENE_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    batch_size: int = int(os.getenv("SCENE_BATCH", "16"))

    @property
    def fingerprints_dir(self):
        return self.data_dir / "fingerprints"

settings = Settings()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:27:47

Теперь всё ясно. `fingerprints_dir` — это **property**, а не поле dataclass. Поэтому:

```python
settings.fingerprints_dir = TARGET
```

невозможно в принципе.

Правильный путь — создать временный `Settings` с другим `data_dir`.

У тебя сейчас:

```python
@property
def fingerprints_dir(self):
    return self.data_dir / "fingerprints"
```

значит достаточно поменять:

```python
data_dir
```

на отдельную папку.

---

Исправляем скрипт.

Открой:

```bash
nano scripts/build_subfingerprint_database.py
```

Найди:

```python
settings = Settings()

embedder = SceneEmbedder(
    settings
)
```

оставляем как есть.

А внутри цикла удали весь блок:

```python
# переключаем каталог fingerprint
old = settings.fingerprints_dir

settings.fingerprints_dir = TARGET

manager.create(
    fp_id,
    tmp,
    embedder
)

settings.fingerprints_dir = old
```

и замени на:

```python
exp_settings = Settings(
    data_dir=TARGET.parent
)

exp_settings = Settings(
    data_dir=PROJECT / "data"
)

# временно меняем через окружение нельзя,
# поэтому создаём отдельный менеджер с заменой data_dir
class SubSettings:
    data_dir = TARGET.parent

    @property
    def fingerprints_dir(self):
        return TARGET

sub_manager = FingerprintManager(
    SubSettings(),
    embedder
)

sub_manager.create(
    fp_id,
    tmp,
    embedder
)
```

---

Но я бы сделал ещё чище.

Лучше сразу добавить в `FingerprintManager` поддержку каталога:

```python
def __init__(
    self,
    settings,
    embedder,
    root=None,
):
    self.settings = settings
    self.embedder = embedder

    self.root = (
        root
        if root
        else settings.fingerprints_dir
    )

    self.root.mkdir(
        parents=True,
        exist_ok=True
    )
```

и заменить:

```python
self.settings.fingerprints_dir
```

на:

```python
self.root
```

Тогда создание эксперимента будет просто:

```python
manager = FingerprintManager(
    settings,
    embedder,
    root=Path("data/fingerprints_sub_exp")
)
```

Это более правильная архитектура — потом веб-интерфейс сможет выбирать:

```
Основная база:
data/fingerprints

Эксперимент:
data/fingerprints_sub_exp

Архив:
data/archive
```

---

Я предлагаю сделать второй вариант. Он маленький патч, но сразу готовит проект под будущий Web UI.

Сначала сделаем изменение `fingerprint.py`, потом пересоберём subfingerprints.

---

### 👤 **User** — 2026-08-15 19:28:21

готовый файл

---

### 🤖 **Assistant** — 2026-08-15 19:28:23

Делаем аккуратно. Замени файл:

```bash
nano app/core/fingerprint.py
```

Но полностью файл большой, поэтому безопаснее не переписывать весь, а сделать минимальный патч.

В начале класса найди:

```python
def __init__(
    self,
    settings,
    embedder,
):
    self.settings = settings
    self.embedder = embedder

    self.settings.fingerprints_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
```

замени на:

```python
def __init__(
    self,
    settings,
    embedder,
    root=None,
):
    self.settings = settings
    self.embedder = embedder

    self.root = (
        Path(root)
        if root is not None
        else settings.fingerprints_dir
    )

    self.root.mkdir(
        parents=True,
        exist_ok=True,
    )
```

---

Теперь в этом же файле найди все:

```python
self.settings.fingerprints_dir
```

их должно быть 2 места:

например:

```python
self.settings.fingerprints_dir / str(fingerprint_id)
```

замени на:

```python
self.root / str(fingerprint_id)
```

и:

```python
root = self.settings.fingerprints_dir
```

замени на:

```python
root = self.root
```

---

После этого проверь:

```bash
grep -n "fingerprints_dir" app/core/fingerprint.py
```

Должно остаться только:

```text
(ничего)
```

или только комментарии.

---

Теперь исправляем генератор.

В:

```bash
nano scripts/build_subfingerprint_database.py
```

замени создание менеджера:

было:

```python
manager = FingerprintManager(
    settings,
    embedder
)
```

делаем:

```python
manager = FingerprintManager(
    settings,
    embedder,
    root=TARGET
)
```

и полностью удаляем блок:

```python
settings.fingerprints_dir = TARGET
...
settings.fingerprints_dir = old
```

---

Перед запуском очистим недосозданную базу:

```bash
rm -rf data/fingerprints_sub_exp/*
```

Запуск:

```bash
uv run python scripts/build_subfingerprint_database.py
```

Ожидаем:

```
84_v33_sub_1
 images: 38

84_v33_sub_2
 images: 16

...

DONE
created: 17
data/fingerprints_sub_exp
```

После этого проверяем:

```bash
find data/fingerprints_sub_exp -maxdepth 2 -name metadata.json | wc -l
```

должно быть:

```
17
```

Это изменение оставляем — оно нам всё равно понадобится для будущего веб-интерфейса выбора базы слепков.

---

### 👤 **User** — 2026-08-15 19:30:52

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n "fingerprints_dir" app/core/fingerprint.py
50:        else settings.fingerprints_dir
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:30:53

Отлично. Это правильный результат.

Осталась только одна ссылка:

```python
50:        else settings.fingerprints_dir
```

Она **должна остаться** — это fallback:

```python
self.root = (
    Path(root)
    if root is not None
    else settings.fingerprints_dir
)
```

Логика теперь такая:

обычная работа:

```
FingerprintManager(
    settings,
    embedder
)
```

использует:

```
data/fingerprints
```

эксперимент:

```
FingerprintManager(
    settings,
    embedder,
    root=data/fingerprints_sub_exp
)
```

использует:

```
data/fingerprints_sub_exp
```

---

Теперь проверим, что нет других проблем:

```bash
grep -n "self.root" app/core/fingerprint.py
```

Должно быть примерно:

```
50:self.root = ...
58:self.root.mkdir(...)
```

и:

```bash
grep -n "def _path" -A8 app/core/fingerprint.py
```

должно быть:

```python
def _path(self, fingerprint_id):
    return (
        self.root
        / str(fingerprint_id)
    )
```

---

Теперь запускаем сборку:

```bash
rm -rf data/fingerprints_sub_exp/*

uv run python scripts/build_subfingerprint_database.py
```

После окончания:

```bash
find data/fingerprints_sub_exp -maxdepth 2 -name metadata.json | wc -l
```

Ожидаем:

```
17
```

После этого подключим их к тестовому распознаванию через отдельный флаг, не затрагивая рабочий `v33`.

---

### 👤 **User** — 2026-08-15 19:31:13

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n "self.root" app/core/fingerprint.py
47:    self.root = (
53:    self.root.mkdir(
63:            self.root / str(fingerprint_id)
71:            root = self.root
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:31:14

Отлично. `FingerprintManager` теперь правильно подготовлен под несколько баз слепков.

Проверяем сам генератор перед запуском:

```bash
grep -n "FingerprintManager" -A5 scripts/build_subfingerprint_database.py
```

Должно быть:

```python
manager = FingerprintManager(
    settings,
    embedder,
    root=TARGET
)
```

Если так — запускаем.

Сначала очистим недоделанную базу:

```bash
rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp
```

Запуск:

```bash
uv run python scripts/build_subfingerprint_database.py
```

После завершения:

```bash
find data/fingerprints_sub_exp -maxdepth 2 -name metadata.json | sort
```

и:

```bash
find data/fingerprints_sub_exp -maxdepth 1 -type d | wc -l
```

Ожидаем:

```
17 metadata.json
```

Структура будет:

```
data/fingerprints_sub_exp/

84_v33_sub_1
84_v33_sub_2

85_v33_sub_1
85_v33_sub_2

87_v33_sub_1
87_v33_sub_2

89_v33_sub_1
89_v33_sub_2
89_v33_sub_3

92_v33_sub_1
92_v33_sub_2

94_v33_sub_1
94_v33_sub_2
94_v33_sub_3

95_v33_sub_1
95_v33_sub_2
95_v33_sub_3
```

Дальше уже будем делать эксперимент:

1. текущий распознаватель на `data/fingerprints`
2. распознаватель на `data/fingerprints_sub_exp`
3. сравним:
   - сколько изменилось адресов
   - уверенность первого кандидата
   - ошибочные переходы

Важно: рабочую `v33` пока вообще не трогаем. Это будет отдельный экспериментальный слой.

---

### 👤 **User** — 2026-08-15 19:31:27

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n "self.root" app/core/fingerprint.py
47:    self.root = (
53:    self.root.mkdir(
63:            self.root / str(fingerprint_id)
71:            root = self.root
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n "FingerprintManager" -A5 scripts/build_subfingerprint_database.py
10:from app.core.fingerprint import FingerprintManager
11-
12-
13-PROJECT = Path(__file__).resolve().parent.parent
14-
15-SOURCE = PROJECT / "data/subfingerprints_exp"
--
37:    manager = FingerprintManager(
38-        settings,
39-        embedder
40-    )
41-
42-
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:31:28

Вот здесь как раз остался старый вариант. Скрипт всё ещё создаёт менеджер без `root`, поэтому он будет писать в обычный:

```
data/fingerprints
```

а не в экспериментальный:

```
data/fingerprints_sub_exp
```

Исправляем.

Открой:

```bash
nano scripts/build_subfingerprint_database.py
```

Найди:

```python
manager = FingerprintManager(
    settings,
    embedder
)
```

замени на:

```python
manager = FingerprintManager(
    settings,
    embedder,
    root=TARGET
)
```

Сохрани.

Проверь:

```bash
grep -n "FingerprintManager" -A6 scripts/build_subfingerprint_database.py
```

Должно быть:

```
37:    manager = FingerprintManager(
38-        settings,
39-        embedder,
40-        root=TARGET
41-    )
```

---

Потом запускаем чистый эксперимент:

```bash
rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
```

После завершения:

```bash
find data/fingerprints_sub_exp -maxdepth 2 -name metadata.json | wc -l
```

Ожидаем:

```
17
```

И обязательно проверим, что рабочие v33 не изменились:

```bash
ls data/fingerprints | grep sub
```

там ничего быть не должно.

После этого подключим эти 17 субслепков к отдельному тестовому распознаванию.

---

### 👤 **User** — 2026-08-15 19:33:01

-A6 scripts/build_subfingerprint_database.py
10:from app.core.fingerprint import FingerprintManager
11-
12-
13-PROJECT = Path(__file__).resolve().parent.parent
14-
15-SOURCE = PROJECT / "data/subfingerprints_exp"
16-
--
38:    manager = FingerprintManager(
39-        settings,
40-        embedder,
41-        root=TARGET
42-    )
43-
44-    created = 0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:33:02

Отлично, теперь всё правильно. Скрипт будет писать именно в экспериментальную базу:

```text
data/fingerprints_sub_exp
```

Запускаем пересборку.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
```

После окончания проверяем:

```bash
find data/fingerprints_sub_exp -maxdepth 2 -name metadata.json | sort
```

и количество:

```bash
find data/fingerprints_sub_exp -maxdepth 2 -name metadata.json | wc -l
```

Должно быть:

```
17
```

Потом проверим размеры:

```bash
du -h --max-depth=1 data/fingerprints_sub_exp | sort -h
```

Ожидаем примерно 17 небольших слепков.

Следующий шаг после этого — не подключать их в основной `recognizer.py`, а сделать **тестовый режим**:

```
v33 обычные слепки
        |
        | сравнение
        |
v33 + subfingerprints_exp
```

и прогнать тот же:

```
data/input/test
```

сравним:
- сколько фото изменили адрес;
- какие были сомнительные случаи;
- поднялась ли уверенность;
- не появились ли ложные перекидывания между похожими домами.

Основную базу пока не трогаем.

---

### 👤 **User** — 2026-08-15 19:33:19

rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/build_subfingerprint_database.py", line 10, in <module>
    from app.core.fingerprint import FingerprintManager
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/fingerprint.py", line 44
    self.settings = settings
    ^
IndentationError: expected an indented block after function definition on line 38
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:33:21

Сейчас ошибка уже не в скрипте сборки, а в `app/core/fingerprint.py`.

Python говорит:

```
app/core/fingerprint.py", line 44
self.settings = settings
IndentationError: expected an indented block after function definition on line 38
```

Значит после добавления `root` сломался отступ в `__init__`.

Покажи этот участок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nl -ba app/core/fingerprint.py | sed -n '30,75p'
```

Скорее всего сейчас там что-то вроде:

```python
def __init__(
    self,
    settings,
    embedder,
    root=None,
):
self.settings = settings
```

а должно быть:

```python
def __init__(
    self,
    settings,
    embedder,
    root=None,
):
    self.settings = settings
    self.embedder = embedder

    self.root = (
        Path(root)
        if root is not None
        else settings.fingerprints_dir
    )

    self.root.mkdir(
        parents=True,
        exist_ok=True,
    )
```

Сначала посмотрим реальные строки, чтобы не менять лишнее.

---

### 👤 **User** — 2026-08-15 19:33:37

int_mvp_v02

nl -ba app/core/fingerprint.py | sed -n '30,75p'
    30	        metadata.json
    31	
    32	    Patch storage:
    33	        DISABLED
    34	    """
    35	
    36	    VERSION = "3.3"
    37	
    38	    def __init__(
    39	    self,
    40	    settings,
    41	    embedder,
    42	    root=None,
    43	    ):
    44	    self.settings = settings
    45	    self.embedder = embedder
    46	
    47	    self.root = (
    48	        Path(root)
    49	        if root is not None
    50	        else settings.fingerprints_dir
    51	    )
    52	
    53	    self.root.mkdir(
    54	        parents=True,
    55	        exist_ok=True,
    56	    )
    57	
    58	    def _path(
    59	        self,
    60	        fingerprint_id,
    61	    ):
    62	        return (
    63	            self.root / str(fingerprint_id)
    64	            / str(fingerprint_id)
    65	        )
    66	
    67	    def list_fingerprints(self):
    68	        result = []
    69	
    70	        root = (
    71	            root = self.root
    72	        )
    73	
    74	        if not root.exists():
    75	            return result
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:33:38

Вижу проблему. При правке сломались **все отступы в `__init__`**, плюс есть ещё одна ошибка ниже:

```python
root = (
    root = self.root
)
```

это тоже синтаксически неверно.

Нужно заменить блок с 38 по 72 строку.

Открой:

```bash
nano app/core/fingerprint.py
```

Замени этот участок:

```python
def __init__(
self,
settings,
embedder,
root=None,
):
self.settings = settings
self.embedder = embedder

self.root = (
    Path(root)
    if root is not None
    else settings.fingerprints_dir
)

self.root.mkdir(
    parents=True,
    exist_ok=True,
)

def _path(
    self,
    fingerprint_id,
):
    return (
        self.root / str(fingerprint_id)
        / str(fingerprint_id)
    )

def list_fingerprints(self):
    result = []

    root = (
        root = self.root
    )
```

на:

```python
    def __init__(
        self,
        settings,
        embedder,
        root=None,
    ):
        self.settings = settings
        self.embedder = embedder

        self.root = (
            Path(root)
            if root is not None
            else settings.fingerprints_dir
        )

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _path(
        self,
        fingerprint_id,
    ):
        return (
            self.root / str(fingerprint_id)
        )

    def list_fingerprints(self):
        result = []

        root = self.root
```

Сохрани.

Проверяем синтаксис:

```bash
python -m py_compile app/core/fingerprint.py
```

Если без вывода — всё исправлено.

Потом снова:

```bash
rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
```

---

Ещё момент: у тебя в `_path()` раньше было:

```python
self.root / str(fingerprint_id) / str(fingerprint_id)
```

это похоже на старый формат. В v33 у нас структура должна быть:

```
data/fingerprints_sub_exp/
 └── 84_v33_sub_1/
     ├── embeddings.npy
     ├── centroid.npy
     ├── metadata.json
     └── faiss.index
```

поэтому оставляем только:

```python
self.root / str(fingerprint_id)
```

Иначе получится лишняя вложенность:

```
84_v33_sub_1/
    84_v33_sub_1/
        metadata.json
```

После исправления можно строить экспериментальную базу.

---

### 👤 **User** — 2026-08-15 19:34:41

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python -m py_compile app/core/fingerprint.py
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:34:43

Это нормально, у тебя окружение через `uv`, поэтому системного `python` нет.

Проверку делаем так:

```bash
uv run python -m py_compile app/core/fingerprint.py
```

Если ошибок нет — продолжаем сборку:

```bash
rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
```

После создания проверим структуру:

```bash
find data/fingerprints_sub_exp -maxdepth 2 -type f | head -30
```

и:

```bash
find data/fingerprints_sub_exp -maxdepth 1 -type d | sort
```

Ожидаемый результат:

```
data/fingerprints_sub_exp/84_v33_sub_1
data/fingerprints_sub_exp/84_v33_sub_2
...
data/fingerprints_sub_exp/95_v33_sub_2
```

Дальше уже сделаем **тестовый recognizer с двумя базами одновременно**:

1. обычные:
```
data/fingerprints/*_v33
```

2. экспериментальные:
```
data/fingerprints_sub_exp/*
```

и сравним:
- первый кандидат совпал / нет
- изменились ли 7 спорных кадров из v38.1
- появились ли ложные срабатывания от маленьких подслепков

Маленькие `sub_2 = 3 фото` пока оставляем именно как эксперимент, потом по результатам введём фильтр.

---

### 👤 **User** — 2026-08-15 19:34:56

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m py_compile app/core/fingerprint.py
  File "app/core/fingerprint.py", line 71
    )
    ^
SyntaxError: unmatched ')'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:34:58

Осталась синтаксическая ошибка в районе строки 71. После предыдущего исправления там, скорее всего, осталась лишняя закрывающая скобка от старого блока.

Покажи точный участок:

```bash
nl -ba app/core/fingerprint.py | sed -n '60,85p'
```

Скорее всего сейчас там что-то вроде:

```python
    def list_fingerprints(self):
        result = []

        root = self.root
        )
```

или похожий остаток.

Нужно привести к виду:

```python
    def list_fingerprints(self):
        result = []

        root = self.root

        if not root.exists():
            return result
```

Пришли вывод 60–85 строк, поправим ровно этот участок.

---

### 👤 **User** — 2026-08-15 19:35:14

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ nl -ba app/core/fingerprint.py | sed -n '60,85p'
    60	        fingerprint_id,
    61	    ):
    62	        return (
    63	            self.root / str(fingerprint_id)
    64	        )
    65	
    66	    def list_fingerprints(self):
    67	        result = []
    68	
    69	        root = self.root
    70	
    71	        )
    72	
    73	        if not root.exists():
    74	            return result
    75	
    76	        for directory in sorted(
    77	            root.iterdir()
    78	        ):
    79	            if not directory.is_dir():
    80	                continue
    81	
    82	            metadata_file = (
    83	                directory
    84	                / "metadata.json"
    85	            )

---

### 🤖 **Assistant** — 2026-08-15 19:35:15

Да, нашли. Осталась одна лишняя строка:

```python
71         )
```

Её нужно удалить.

Командой:

```bash
sed -i '71d' app/core/fingerprint.py
```

Проверяем:

```bash
nl -ba app/core/fingerprint.py | sed -n '60,80p'
```

Должно стать:

```python
    def list_fingerprints(self):
        result = []

        root = self.root

        if not root.exists():
            return result
```

Теперь компиляция:

```bash
uv run python -m py_compile app/core/fingerprint.py
```

Если ошибок нет — запускаем сборку:

```bash
rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
```

После этого уже можно будет переходить к сравнению распознавания.

---

### 👤 **User** — 2026-08-15 19:35:51

84_v33_sub_1
 images: 38
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/build_subfingerprint_database.py", line 133, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/build_subfingerprint_database.py", line 107, in main
    settings.fingerprints_dir = TARGET
    ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<string>", line 4, in __setattr__
dataclasses.FrozenInstanceError: cannot assign to field 'fingerprints_dir'

---

### 🤖 **Assistant** — 2026-08-15 19:35:55

Отлично, `fingerprint.py` уже исправлен. Теперь ошибка вернулась в самом `build_subfingerprint_database.py`.

Причина:

```python
settings.fingerprints_dir = TARGET
```

Но `Settings` у нас:

```python
@dataclass(frozen=True)
```

то есть настройки **только для чтения**. Мы как раз добавили `root=TARGET`, поэтому менять `settings` больше не нужно.

Открой:

```bash
nano scripts/build_subfingerprint_database.py
```

Найди строку:

```python
settings.fingerprints_dir = TARGET
```

и удали её.

Должно быть примерно так:

```python
manager = FingerprintManager(
    settings,
    embedder,
    root=TARGET
)
```

После сохранения проверяем:

```bash
grep -n "fingerprints_dir\|FingerprintManager" scripts/build_subfingerprint_database.py
```

В идеале должно остаться только:

```text
FingerprintManager
```

без:

```text
settings.fingerprints_dir = TARGET
```

Запускаем:

```bash
rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
```

Теперь создание должно пойти:

```
84_v33_sub_1
 images: 38
...
95_v33_sub_2
 images: 44

DONE
created: 17
```

После этого проверим, что экспериментальная база реально создана:

```bash
find data/fingerprints_sub_exp -maxdepth 1 -type d | sort
```

Следующий этап — подключение **второго слоя поиска** (v33 + subfingerprints) без изменения основного распознавания.

---

### 👤 **User** — 2026-08-15 19:37:40

images: 38
[Fingerprint v3.3] Creating '84_v33_sub_1' from 38 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: /home/alexice/projects/scene_fingerprint_mvp_v02/data/fingerprints_sub_exp/84_v33_sub_1
[Fingerprint v3.3] global=(38, 768)
[Fingerprint v3.3] environment=(38, 640)
[Fingerprint v3.3] color=(38, 48)
[Fingerprint v3.3] spatial=(38, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/build_subfingerprint_database.py", line 130, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/build_subfingerprint_database.py", line 114, in main
    settings.fingerprints_dir = old
    ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<string>", line 4, in __setattr__
dataclasses.FrozenInstanceError: cannot assign to field 'fingerprints_dir'

---

### 🤖 **Assistant** — 2026-08-15 19:37:41

Отлично — сам подслепок **создался правильно**:

```text
Saved: .../data/fingerprints_sub_exp/84_v33_sub_1

global=(38, 768)
environment=(38, 640)
color=(38, 48)
spatial=(38, 32)
```

Теперь падает только в конце, потому что в скрипте остался старый механизм "вернуть старый путь":

```python
settings.fingerprints_dir = old
```

Он больше не нужен, так как мы уже передаём:

```python
root=TARGET
```

Нужно убрать весь блок восстановления.

Покажи последние строки:

```bash
nl -ba scripts/build_subfingerprint_database.py | sed -n '90,125p'
```

Скорее всего там:

```python
old = settings.fingerprints_dir
settings.fingerprints_dir = TARGET

...
settings.fingerprints_dir = old
```

Нужно удалить обе строки изменения `settings`.

Быстро можно:

```bash
sed -i '/settings\.fingerprints_dir =/d' scripts/build_subfingerprint_database.py
```

Потом проверить:

```bash
grep -n "fingerprints_dir" scripts/build_subfingerprint_database.py
```

должно быть пусто.

Запускаем заново:

```bash
rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
```

Теперь ожидаем:

```text
================================================================================
DONE
created: 17
data/fingerprints_sub_exp
```

После этого сделаем следующий шаг: добавим временный режим теста:

```
recognize:
    обычные v33
        ↓
    если уверенность низкая
        ↓
    поиск по sub_exp
        ↓
    сравнение результата
```

То есть базовый стабильный алгоритм v38.1 не трогаем. Подслепки будут работать как дополнительный слой проверки.

---

### 👤 **User** — 2026-08-15 19:38:00

104	            # переключаем каталог fingerprint
   105	            old = settings.fingerprints_dir
   106	
   107	            manager.create(
   108	                fp_id,
   109	                tmp,
   110	                embedder
   111	            )
   112	
   113	
   114	            settings.fingerprints_dir = old
   115	
   116	
   117	            shutil.rmtree(tmp)
   118	
   119	            created += 1
   120	
   121	
   122	    print()
   123	    print("=" * 80)
   124	    print("DONE")
   125	    print("created:", created)

---

### 🤖 **Assistant** — 2026-08-15 19:38:01

Да, тут остался старый код после перехода на `root=TARGET`.

Сейчас блок:

```python
old = settings.fingerprints_dir

manager.create(
    fp_id,
    tmp,
    embedder
)

settings.fingerprints_dir = old
```

уже неправильный. `settings` заморожен (`frozen=True`), и переключать путь через него нельзя.

Меняем на прямой вызов через текущий `manager`.

Открой:

```bash
nano scripts/build_subfingerprint_database.py
```

Замени строки 104–114 на:

```python
            manager.create(
                fp_id,
                tmp,
                embedder
            )
```

То есть должно стать:

```python
        if images:

            print()
            print(fp_id)
            print(" images:", len(images))

            manager.create(
                fp_id,
                tmp,
                embedder
            )

            shutil.rmtree(tmp)

            created += 1
```

Проверка:

```bash
uv run python -m py_compile scripts/build_subfingerprint_database.py
```

Потом пересоздаём:

```bash
rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
```

Сейчас уже должно пройти все 17 подслепков до конца.

После окончания проверим:

```bash
find data/fingerprints_sub_exp -maxdepth 1 -type d | sort
```

и можно будет запускать сравнительный тест v33 против v33+sub.

---

### 👤 **User** — 2026-08-15 19:39:56

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ find data/fingerprints_sub_exp -maxdepth 1 -type d | sort
data/fingerprints_sub_exp
data/fingerprints_sub_exp/84_v33_sub_2
data/fingerprints_sub_exp/85_v33_sub_2
data/fingerprints_sub_exp/87_v33_sub_2
data/fingerprints_sub_exp/89_v33_sub_3
data/fingerprints_sub_exp/92_v33_sub_2
data/fingerprints_sub_exp/94_v33_sub_3
data/fingerprints_sub_exp/95_v33_sub_3

---

### 🤖 **Assistant** — 2026-08-15 19:39:57

Отлично. Но здесь обнаружился важный момент.

Создались только:

```
84_v33_sub_2
85_v33_sub_2
87_v33_sub_2
89_v33_sub_3
92_v33_sub_2
94_v33_sub_3
95_v33_sub_3
```

То есть **не 17 отдельных подслепков**, а 7 папок. Причина почти наверняка в текущем `FingerprintManager.create()` — он не умеет создавать несколько fingerprint внутри одной папки `data/fingerprints_sub_exp`, а при одинаковых базовых ID перезаписывает предыдущий.

Например:

Было:

```
84_v33
 ├── sub_1
 └── sub_2
```

должно было стать:

```
data/fingerprints_sub_exp/

84_v33_sub_1
84_v33_sub_2

85_v33_sub_1
85_v33_sub_2

...
```

А сейчас:

```
84_v33_sub_2   ← sub_1 потерян
85_v33_sub_2   ← sub_1 потерян
...
```

Нужно проверить, не перезаписали ли мы данные.

Сначала:

```bash
find data/fingerprints_sub_exp -maxdepth 1 -type d | wc -l
```

должно быть 18 (корень + 17 слепков).

Сейчас будет 8.

---

Надо поправить `build_subfingerprint_database.py`.

Сейчас, скорее всего, формирование имени идёт неправильно.

Покажи участок:

```bash
nl -ba scripts/build_subfingerprint_database.py | sed -n '70,115p'
```

Нужно сделать так:

```python
fp_id = sub_path.name
```

где `sub_path.name` будет:

```
84_v33_sub_1
84_v33_sub_2
```

а не только:

```
84_v33_sub
```

---

Это важный тест, потому что сейчас мы проверяем саму идею подслепков. Лучше не запускать распознавание на неполной базе.

После исправления должно быть:

```
created: 17
```

и:

```bash
find data/fingerprints_sub_exp -maxdepth 1 -type d | sort
```

выдаст:

```
84_v33_sub_1
84_v33_sub_2
85_v33_sub_1
85_v33_sub_2
87_v33_sub_1
87_v33_sub_2
89_v33_sub_1
89_v33_sub_2
89_v33_sub_3
92_v33_sub_1
92_v33_sub_2
94_v33_sub_1
94_v33_sub_2
94_v33_sub_3
95_v33_sub_1
95_v33_sub_2
95_v33_sub_3
```

И только после этого сравним качество.

---

### 👤 **User** — 2026-08-15 19:40:25

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ find data/fingerprints_sub_exp -maxdepth 1 -type d | wc -l
8
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:40:26

Да, подтверждено — сейчас база неполная: **8 папок вместо 18**.

Причина: при создании подслепков они имеют одинаковые имена и второй вариант затирает первый.

Сейчас надо не трогать `FingerprintManager`, а исправить только экспериментальный скрипт.

Покажи участок формирования `fp_id`:

```bash
nl -ba scripts/build_subfingerprint_database.py | sed -n '45,100p'
```

Скорее всего там что-то вроде:

```python
fp_id = f"{base}_sub_{i}"
```

но нужно увидеть точный код.

После исправления будет пересоздание:

```bash
rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
```

Ожидаемый результат:

```
created: 17
```

и:

```bash
find data/fingerprints_sub_exp -maxdepth 1 -type d | sort
```

должен показать:

```
84_v33_sub_1
84_v33_sub_2
85_v33_sub_1
85_v33_sub_2
87_v33_sub_1
87_v33_sub_2
89_v33_sub_1
89_v33_sub_2
89_v33_sub_3
92_v33_sub_1
92_v33_sub_2
94_v33_sub_1
94_v33_sub_2
94_v33_sub_3
95_v33_sub_1
95_v33_sub_2
95_v33_sub_3
```

После этого уже будем делать тест:

**вариант А:** только `*_v33`  
**вариант Б:** `*_v33` + `*_sub_*`

и сравним, улучшились ли 7 ошибочных кадров из V38.1.

---

### 👤 **User** — 2026-08-15 19:40:45

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ nl -ba scripts/build_subfingerprint_database.py | sed -n '45,100p'
    45	
    46	
    47	    for address_dir in sorted(SOURCE.iterdir()):
    48	
    49	        if not address_dir.is_dir():
    50	            continue
    51	
    52	
    53	        address = address_dir.name
    54	
    55	
    56	        for sub_dir in sorted(address_dir.iterdir()):
    57	
    58	            if not sub_dir.is_dir():
    59	                continue
    60	
    61	
    62	            images = list(
    63	                sub_dir.glob("*.JPG")
    64	            ) + list(
    65	                sub_dir.glob("*.jpg")
    66	            )
    67	
    68	
    69	            if not images:
    70	                continue
    71	
    72	
    73	            fp_id = (
    74	                address
    75	                + "_"
    76	                + sub_dir.name
    77	            )
    78	
    79	
    80	            print()
    81	            print(fp_id)
    82	            print(
    83	                " images:",
    84	                len(images)
    85	            )
    86	
    87	
    88	            # временная папка
    89	            tmp = TARGET / "_tmp"
    90	
    91	            if tmp.exists():
    92	                shutil.rmtree(tmp)
    93	
    94	            tmp.mkdir()
    95	
    96	
    97	            for img in images:
    98	                shutil.copy2(
    99	                    img,
   100	                    tmp / img.name
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 19:40:51

Код формирования `fp_id` правильный:

```python
fp_id = (
    address
    + "_"
    + sub_dir.name
)
```

То есть он должен создавать:

```
84_v33_sub_1
84_v33_sub_2
```

Проблема не здесь.

Проблема в другом месте: `FingerprintManager.create()` при сохранении, скорее всего, **не использует весь `fingerprint_id` как имя папки**, а где-то обрезает до базового ID.

Мы видели раньше:

```python
def _path(
    self,
    fingerprint_id,
):
    return (
        self.root / str(fingerprint_id)
    )
```

Но сейчас нужно проверить сам `create()`.

Покажи:

```bash
grep -n "def create" -A120 app/core/fingerprint.py
```

Скорее всего внутри есть что-то вроде:

```python
fingerprint_dir = self._path(
    fingerprint_id.split("_")[0]
)
```

или старый механизм группировки.

---

После исправления логика должна быть:

```
data/fingerprints_sub_exp/

84_v33_sub_1/
    embeddings.npy
    metadata.json
    ...

84_v33_sub_2/
    embeddings.npy
    metadata.json

85_v33_sub_1/
...
```

Без объединения.

---

Ещё один момент: у нас сейчас остались 7 папок, потому что последние подслепки **перезаписали первые**:

например:

```
84_v33_sub_1  → создан
84_v33_sub_2  → записан поверх
```

После исправления надо будет просто:

```bash
rm -rf data/fingerprints_sub_exp
mkdir data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
```

и получить `created: 17`.

Покажи `def create`, поправим минимально.

---

### 👤 **User** — 2026-08-15 19:41:13

pp/core/fingerprint.py
156:    def create(
157-        self,
158-        fingerprint_id,
159-        folder,
160-        embedder=None,
161-    ):
162-        fingerprint_id = str(
163-            fingerprint_id
164-        )
165-
166-        folder = Path(folder)
167-
168-        paths = image_files(folder)
169-
170-        if not paths:
171-            raise ValueError(
172-                f"No images found in {folder}"
173-            )
174-
175-        output = self._path(
176-            fingerprint_id
177-        )
178-
179-        if output.exists():
180-            existing = list(
181-                output.iterdir()
182-            )
183-
184-            if existing:
185-                raise FileExistsError(
186-                    f"Fingerprint '{fingerprint_id}' "
187-                    f"already exists and is not empty: "
188-                    f"{output}"
189-                )
190-
191-        output.mkdir(
192-            parents=True,
193-            exist_ok=True,
194-        )
195-
196-        embedder = (
197-            embedder
198-            or self.embedder
199-        )
200-
201-        print(
202-            f"[Fingerprint v3.3] "
203-            f"Creating '{fingerprint_id}' "
204-            f"from {len(paths)} images"
205-        )
206-
207-        print(
208-            "[Fingerprint v3.3] "
209-            "Building compact descriptors..."
210-        )
211-
212-        embeddings = embedder.embed_paths(
213-            paths
214-        )
215-
216-        embeddings = np.asarray(
217-            embeddings,
218-            dtype=np.float32,
219-        )
220-
221-        if embeddings.ndim == 1:
222-            embeddings = embeddings.reshape(
223-                1,
224-                -1,
225-            )
226-
227-        if embeddings.shape[1] != 768:
228-            raise ValueError(
229-                "Invalid DINO embedding "
230-                f"dimension: {embeddings.shape}"
231-            )
232-
233-        embeddings = self._normalize_rows(
234-            embeddings
235-        )
236-
237-        centroid = embeddings.mean(
238-            axis=0
239-        )
240-
241-        centroid = self._normalize_vector(
242-            centroid
243-        )
244-
245-        similarities = (
246-            embeddings @ centroid
247-        )
248-
249-        representative_count = min(
250-            16,
251-            len(paths),
252-        )
253-
254-        representative_indices = (
255-            np.argsort(
256-                similarities
257-            )[
258-                -representative_count:
259-            ][::-1]
260-        ).astype(np.int32)
261-
262-        representatives = (
263-            embeddings[
264-                representative_indices
265-            ]
266-        )
267-
268-        # --------------------------------------------------
269-        # CPU compact descriptors
270-        #
271-        # One image load per worker + parallel processing.
272-        # --------------------------------------------------
273-
274-        workers = min(
275-            6,
276-            max(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

