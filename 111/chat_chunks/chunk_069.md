## СЕССИЯ: ФОТОБАЗА ОФИС

**Создано:** 2026-08-16 00:03:58
**Обновлено:** 2026-08-19 21:49:51
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df)

---

### 🤖 **Assistant** — 2026-08-16 00:33:46

Отлично, первый эксперимент дал очень полезную информацию. Самое главное: **пайплайн работает**, но мы проверили не совсем тот объект, который хотели.

Сейчас результат показывает:

```
макет (Screenshot)
        ↓
DINOv2
        ↓
сравнение со всей фотографией сцены
```

А DINOv2 видит в первую очередь **общую сцену**, а не сам баннер.

Поэтому получаем:

```
Screenshot 00-13-31

01 Радиаторный_25  0.1419
02 Зорге_15        0.1410
03 Зорге_17        0.1402
```

То есть он говорит:

> "Этот макет визуально немного похож на такие сцены"

а не:

> "На этом фото установлен именно этот баннер".

---

## Вывод по тесту №1

### Хорошая новость

Архитектура:

```
макет
 |
DINO
 |
поиск
 |
результаты
```

запускается.

---

### Плохая новость

Для задачи:

> оригинальный макет → фото с установленным баннером

нужен другой подход.

---

# Почему так произошло

Ваш основной recognizer работает отлично, потому что задача:

```
фото места
↓
найти похожее место
```

Это как раз DINOv2.

А здесь:

```
плоская картинка баннера
↓
найти эту картинку на фото под углом
```

Это задача **поиска объекта внутри изображения**.

---

# Следующий тест я бы сделал №2

Не весь кадр.

Нужно вырезать баннер с фотографии.

Например:

```
Фото:

+----------------------+
|                      |
|       дом            |
|                      |
|  +-------------+     |
|  |   БАННЕР    |     |
|  +-------------+     |
|                      |
+----------------------+
```

Сейчас DINO сравнивает:

```
макет
+
дом
+
деревья
+
дорога
+
небо
```

против:

```
всё фото
```

---

# Следующий эксперимент без сложного AI

Сделаем:

## Banner Search v02

Добавляем:

```
оригинал макета
        |
        |
        v

поиск похожей области на фото
        |
        |
        v

crop баннера
        |
        |
        v

DINO сравнение
```

---

Для этого лучше подходит:

### вариант 1 (быстрый)

OpenCV template matching:

```
макет
 |
изменение масштаба
 |
поиск области
 |
score
```

Плюсы:
- быстро;
- идеально для одинаковых макетов.

Минусы:
- плохо при сильной перспективе.

---

### вариант 2 (правильнее)

Feature matching:

```
SIFT / ORB

макет
 |
ключевые точки
 |
фото
 |
совпадения
```

Плюсы:
- работает с углом;
- работает с расстоянием.

---

### вариант 3 (самый мощный)

CLIP + crop + DINO rerank:

```
макет
 |
CLIP embedding
 |
поиск кандидатов

↓

DINO patch
 |
точное ранжирование
```

---

# Что я бы сделал сейчас

Не трогая recognizer:

## Banner Search v02

1. Берём один макет.
2. Берём 10-20 фото test.
3. Автоматически режем фото на плитки:

например:

```
фото 4000x3000

разбиваем:

4x3 = 12 областей
```

Получаем:

```
IMG001_tile01
IMG001_tile02
...
```

4. Каждую плитку прогоняем через DINO.
5. Сравниваем с макетом.

Схема:

```
                 фото
                  |
        -------------------
        | | | | | | | | |
        tiles
                  |
                  v
              DINO
                  |
                  v
            similarity
```

---

Это очень близко к вашей идее с OCR "табличка может быть где угодно" — только здесь ищем не текст, а графику.

---

Но прежде чем усложнять, я бы сделал один контрольный тест:

Возьмите из `data/input/test` **фото, где точно есть один из этих баннеров**, и сделайте вручную crop только баннера.

Например:

```
data/input/banners/banner1.jpg

data/input/test/crop_banner1.jpg
```

Запускаем тот же скрипт.

Если:

```
banner1 → crop_banner1

score > 0.8
```

значит DINO подходит, и нам надо только решить поиск области.

Если нет — идём в CLIP/SIFT.

Сейчас главный вывод: **DINO не плохой — просто мы дали ему неправильный вход (весь кадр вместо баннера).**

---

### 👤 **User** — 2026-08-16 00:39:32

01. Screenshot from 2026-08-16 00-38-11.png score=0.3523

---

### 🤖 **Assistant** — 2026-08-16 00:39:34

Вот это уже **очень важный результат**.

Сравниваем с предыдущими:

Было:

```
макет → вся фотография

score:
0.14 максимум
```

Стало:

```
макет → crop/область с баннером

score:
0.3523
```

То есть гипотеза подтверждается:

**DINOv2 начинает видеть баннер, когда убираем лишний фон.**

Но 0.35 — это ещё не "идеальное совпадение". Для DINOv2 это ожидаемо, потому что:

- макет — чистая графика;
- фото — реальный объект;
- угол съёмки;
- перспектива;
- освещение;
- часть баннера может быть закрыта;
- разные пропорции.

---

## Что это значит для архитектуры Banner Search

Теперь схема становится такой:

```
                Оригинал баннера
                       |
                       |
                    DINOv2
                       |
                       |
                embedding 768

Фото объекта
      |
      |
  поиск области
      |
      |
   crop баннера
      |
      |
   DINOv2
      |
      |
 similarity
```

---

## Следующий эксперимент №3

Нужно проверить не DINO, а **поиск области**.

Берём одно фото объекта:

```
Радиаторный_25.JPG
```

и делаем автоматическую нарезку:

например:

```
+----------------+
|                |
|    tile 1      |
|----------------|
|    tile 2      |
|----------------|
|    tile 3      |
|----------------|
|    tile 4      |
+----------------+
```

Каждый tile → DINO → сравнение.

---

## Но я бы добавил ещё одну вещь

Вместо простого crop:

```
crop 512x512
```

делаем несколько масштабов:

```
фото

scale 0.5
scale 0.7
scale 1.0

windows:
256
512
768
1024
```

Получаем:

```
одно фото
 |
 +-- 50 областей
 |
 DINO
 |
 top score
```

---

## Для промышленной версии это будет:

### Этап 1 — быстрый фильтр

Цвет:

```
banner
 |
dominant colors
 |
отбор 10%
```

### Этап 2 — поиск областей

```
sliding window
```

### Этап 3 — точная проверка

```
DINO patch embedding
```

---

Сейчас я бы сделал следующий маленький скрипт:

```
scripts/banner_crop_search_v01.py
```

который:

- берёт `data/input/banners`;
- берёт `data/input/test`;
- режет фото на окна;
- ищет лучший crop;
- сохраняет:

```
data/output/found_banners/

banner_name/

    original_photo.JPG
    best_crop.jpg
    result.json
```

Это будет уже первый настоящий **поисковик баннеров**.

И главное — он будет полностью отдельно от текущего recognizer.

---

### 👤 **User** — 2026-08-16 00:40:24

давай на примере Ашхабадский_01

---

### 🤖 **Assistant** — 2026-08-16 00:40:26

Отлично. Берём конкретный кейс:

**Фото объекта:**

```text
data/input/test/Ашхабадский_01.JPG
```

И один макет из:

```text
data/input/banners/
```

Цель:

проверить:

```text
оригинал баннера
        ↓
поиск внутри
Ашхабадский_01.JPG
        ↓
найти область баннера
        ↓
score
```

Сделаем сначала **визуальный диагностический тест**, без сложной оптимизации.

---

## Шаг 1. Создаём папку эксперимента

```bash
mkdir -p data/output/banner_debug/Ashhabadskiy_01
```

---

## Шаг 2. Режем фото на части

Сделаем сетку:

- 4 колонки
- 4 ряда

И получим 16 областей.

Создаём:

```bash
nano scripts/crop_test_banner.py
```

Код:

```python
from pathlib import Path
from PIL import Image

INPUT = Path(
    "data/input/test/Ашхабадский_01.JPG"
)

OUTPUT = Path(
    "data/output/banner_debug/Ashhabadskiy_01"
)

ROWS = 4
COLS = 4

def main():

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True
    )

    img = Image.open(INPUT)

    w, h = img.size

    print(
        "IMAGE:",
        w,
        h
    )

tile_w = w // COLS
    tile_h = h // ROWS

counter = 1

for r in range(ROWS):

        for c in range(COLS):

            x1 = c * tile_w
            y1 = r * tile_h

            x2 = (
                x1 + tile_w
                if c < COLS - 1
                else w
            )

            y2 = (
                y1 + tile_h
                if r < ROWS - 1
                else h
            )

crop = img.crop(
                (
                    x1,
                    y1,
                    x2,
                    y2
                )
            )

name = (
                OUTPUT /
                f"tile_{counter:02d}_r{r}_c{c}.jpg"
            )

crop.save(
                name,
                quality=95
            )

counter += 1

if __name__ == "__main__":
    main()
```

---

Запуск:

```bash
uv run python scripts/crop_test_banner.py
```

Получим:

```text
data/output/banner_debug/Ashhabadskiy_01/

tile_01.jpg
tile_02.jpg
...
tile_16.jpg
```

---

## Шаг 3. Проверяем глазами

Открой папку:

```bash
xdg-open data/output/banner_debug/Ashhabadskiy_01
```

Нам нужно увидеть:

- где находится баннер;
- попал ли он полностью в один tile.

---

После этого следующий шаг:

сделаем скрипт:

```text
banner_search_crop_v01.py
```

который будет:

```
banner.jpg
    |
    |
tile_01
tile_02
...
tile_16
    |
    |
DINO similarity
    |
    |
лучший tile
```

Для Ашхабадский_01 это даст первую реальную проверку поиска баннера внутри фото.

---

### 👤 **User** — 2026-08-16 00:42:46

баннер разрезан на части

---

### 🤖 **Assistant** — 2026-08-16 00:42:46

Отлично, это как раз ожидаемый результат для первого простого варианта. Значит сетка **4×4 слишком грубая** — баннер попал на границу между тайлами.

Для поиска баннеров так делать нельзя. Нужно перейти от фиксированной сетки к **скользящему окну (sliding window)**.

Схема будет такая:

```
Ашхабадский_01.JPG

+--------------------------------+
|                                |
|       окно 1                   |
|                                |
|    +----------------+          |
|    |                |          |
|    |    баннер      |          |
|    |                |          |
|    +----------------+          |
|                                |
+--------------------------------+
```

Окно будет двигаться с перекрытием:

например:

- размеры окон:
  - 20% ширины фото
  - 30%
  - 40%
  - 50%

- шаг:
  - 10–15%

Тогда один из crop гарантированно захватит баннер целиком.

---

Для `Ашхабадский_01.JPG` предлагаю следующий тест:

### Banner Search v02 (локальный)

Вход:

```
data/input/banners/
    banner.jpg

data/input/test/
    Ашхабадский_01.JPG
```

Процесс:

```
Ашхабадский_01.JPG

  ↓

генерация ~100-200 crop

  ↓

каждый crop
  ↓
SceneEmbedder
  ↓
cosine similarity

  ↓

Top-10
```

Вывод:

```
data/output/found_banners_debug/

Ашхабадский_01/

best_01.jpg
best_02.jpg
result.json
```

В `result.json`:

```json
[
 {
   "crop":"x420_y680_w900_h500.jpg",
   "score":0.71
 },
 {
   "crop":"x300_y620_w900_h500.jpg",
   "score":0.65
 }
]
```

---

Ещё лучше: раз у вас уже есть **patch tokens в DINOv2** (мы их добавляли для v33), можно будет сравнивать не весь crop, а локальные области.

То есть:

```
баннер
 |
patch embedding

фото
 |
patch embeddings

поиск похожих patch
```

Это как раз ближе к задаче "найти объект на сцене".

Но сначала сделаем простой sliding window и посмотрим на реальные score.

Следующий файл:

```
scripts/banner_crop_search_v01.py
```

будет первым настоящим поиском баннера на `Ашхабадский_01.JPG`.

---

### 👤 **User** — 2026-08-16 00:43:11

давай

---

### 🤖 **Assistant** — 2026-08-16 00:43:12

Делаем **Banner Crop Search v01**.

Задача этого скрипта:

```text
data/input/banners/
        |
        |  оригинал баннера
        v

data/input/test/
        |
        |  Ашхабадский_01.JPG
        v

генерация окон (sliding window)
        |
        v

DINOv2 embedding
        |
        v

cosine similarity
        |
        v

лучшие найденные области
```

---

Создаём файл:

```bash
nano scripts/banner_crop_search_v01.py
```

Вставляем:

```python
#!/usr/bin/env python3

import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

from app.core.runtime import get_embedder

PROJECT = Path(__file__).resolve().parent.parent

BANNER_DIR = PROJECT / "data/input/banners"
PHOTO_DIR = PROJECT / "data/input/test"

OUTPUT_DIR = PROJECT / "data/output/found_banners_debug"

TOP_K = 10

# размеры окон относительно изображения
WINDOW_SIZES = [
    0.25,
    0.35,
    0.45,
    0.55,
]

STEP = 0.15

EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".JPG",
    ".JPEG",
}

def images(folder):

    return [
        x for x in folder.rglob("*")
        if x.suffix in EXT
    ]

def cosine(a, b):

    a = np.asarray(a)
    b = np.asarray(b)

    return float(
        np.dot(a, b)
        /
        (
            np.linalg.norm(a)
            *
            np.linalg.norm(b)
        )
    )

def make_windows(img):

    w, h = img.size

    crops = []

    for size in WINDOW_SIZES:

        ww = int(w * size)
        hh = int(h * size)

        x = 0

        while x + ww <= w:

            y = 0

            while y + hh <= h:

                crop = img.crop(
                    (
                        x,
                        y,
                        x + ww,
                        y + hh
                    )
                )

                crops.append(
                    {
                        "image": crop,
                        "x": x,
                        "y": y,
                        "w": ww,
                        "h": hh,
                    }
                )

                y += int(hh * STEP)

            x += int(ww * STEP)

    return crops

def embed(embedder, img):

    tmp = Path(
        "/tmp/banner_crop.jpg"
    )

    img.save(
        tmp,
        quality=95
    )

    return embedder.embed_paths(
        [str(tmp)]
    )[0]

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

embedder = get_embedder()

banners = images(
        BANNER_DIR
    )

    photos = images(
        PHOTO_DIR
    )

if not banners:
        print(
            "Нет баннеров"
        )
        return

if not photos:
        print(
            "Нет фотографий"
        )
        return

for banner in banners:

print("\nQUERY:", banner.name)

banner_img = Image.open(
            banner
        )

banner_emb = embed(
            embedder,
            banner_img
        )

result_dir = (
            OUTPUT_DIR /
            banner.stem
        )

        result_dir.mkdir(
            parents=True,
            exist_ok=True
        )

results = []

for photo in photos:

            print(
                "SEARCH:",
                photo.name
            )

img = Image.open(
                photo
            )

windows = make_windows(
                img
            )

print(
                "windows:",
                len(windows)
            )

for idx, item in enumerate(
                tqdm(windows)
            ):

                score = cosine(
                    banner_emb,
                    embed(
                        embedder,
                        item["image"]
                    )
                )

results.append(
                    {
                        "photo": str(photo),
                        "score": score,
                        "x": item["x"],
                        "y": item["y"],
                        "w": item["w"],
                        "h": item["h"],
                    }
                )

results.sort(
            key=lambda x:x["score"],
            reverse=True
        )

top = results[:TOP_K]

for i, r in enumerate(
            top,
            start=1
        ):

            print(
                i,
                r["photo"],
                r["score"]
            )

img = Image.open(
                r["photo"]
            )

crop = img.crop(
                (
                    r["x"],
                    r["y"],
                    r["x"] + r["w"],
                    r["y"] + r["h"]
                )
            )

crop.save(
                result_dir /
                f"best_{i}.jpg"
            )

with open(
            result_dir / "result.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                top,
                f,
                indent=2,
                ensure_ascii=False
            )

if __name__ == "__main__":
    main()
```

---

Запуск:

```bash
uv run python scripts/banner_crop_search_v01.py
```

---

Первый тест лучше сделать только с:

```text
data/input/test/
    Ашхабадский_01.JPG
```

и одним файлом в:

```text
data/input/banners/
```

Иначе первый запуск будет долгий.

Ожидаемый результат:

```text
QUERY: banner.jpg

SEARCH: Ашхабадский_01.JPG

windows: 100-200

1 Ашхабадский_01.JPG score=0.xxx
2 Ашхабадский_01.JPG score=0.xxx
...
```

В папке:

```text
data/output/found_banners_debug/banner/
```

будут:

```text
best_1.jpg
best_2.jpg
...
result.json
```

Сначала посмотрим **нашёл ли он сам баннер визуально**. Потом будем оптимизировать скорость (сейчас это исследовательская версия).

---

### 👤 **User** — 2026-08-16 00:43:45

QUERY: бетсити.png
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/PIL/JpegImagePlugin.py", line 665, in _save
    rawmode = RAWMODE[im.mode]
              ~~~~~~~^^^^^^^^^
KeyError: 'RGBA'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/banner_crop_search_v01.py", line 300, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/banner_crop_search_v01.py", line 174, in main
    banner_emb = embed(
                 ^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/banner_crop_search_v01.py", line 119, in embed
    img.save(
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/PIL/Image.py", line 2711, in save
    save_handler(self, fp, filename)
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/PIL/JpegImagePlugin.py", line 668, in _save
    raise OSError(msg) from e
OSError: cannot write mode RGBA as JPEG

---

### 🤖 **Assistant** — 2026-08-16 00:43:48

Отлично, это обычная проблема с PNG. `бетсити.png` имеет альфа-канал:

```text
RGBA
```

а временный файл мы сохраняем как JPEG:

```python
tmp = Path("/tmp/banner_crop.jpg")
img.save(tmp, quality=95)
```

JPEG не умеет хранить прозрачность.

Исправляем функцию `embed()`.

Открой:

```bash
nano scripts/banner_crop_search_v01.py
```

Найди:

```python
def embed(embedder, img):

    tmp = Path(
        "/tmp/banner_crop.jpg"
    )

    img.save(
        tmp,
        quality=95
    )

    return embedder.embed_paths(
        [str(tmp)]
    )[0]
```

Замени полностью на:

```python
def embed(embedder, img):

    tmp = Path(
        "/tmp/banner_crop.jpg"
    )

    # PNG с прозрачностью -> RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    img.save(
        tmp,
        format="JPEG",
        quality=95
    )

    return embedder.embed_paths(
        [str(tmp)]
    )[0]
```

---

После этого снова:

```bash
uv run python scripts/banner_crop_search_v01.py
```

---

Кстати, это полезный момент для будущей архитектуры:

в веб-интерфейсе надо сразу принимать:

```text
JPG
PNG
WEBP
```

и перед DINO делать единый preprocessing:

```text
RGBA
CMYK
P
   |
   v
RGB
   |
   v
SceneEmbedder
```

То есть проблема сейчас не в Banner Search, а в подготовке входного изображения.

---

### 👤 **User** — 2026-08-16 00:44:03

давац готовый

---

### 🤖 **Assistant** — 2026-08-16 00:44:04

Замените функцию `embed()` в `scripts/banner_crop_search_v01.py` на эту. Это готовый исправленный вариант с поддержкой PNG/RGBA:

```python
def embed(embedder, img):

    tmp = Path(
        "/tmp/banner_crop.jpg"
    )

    # Нормализация изображений:
    # PNG с прозрачностью, WEBP, RGBA и т.п.
    # приводим к RGB перед JPEG
    if img.mode != "RGB":
        img = img.convert("RGB")

    img.save(
        tmp,
        format="JPEG",
        quality=95
    )

    return embedder.embed_paths(
        [str(tmp)]
    )[0]
```

Больше в файле ничего менять не нужно.

После сохранения:

```bash
uv run python scripts/banner_crop_search_v01.py
```

Теперь:

```text
QUERY: бетсити.png
```

должен пройти дальше и начать:

```text
SEARCH: Ашхабадский_01.JPG
windows: ...
```

Если после этого будет долго — это нормально: текущая версия делает полный перебор всех окон через DINOv2. Следующий этап будет оптимизация (batch embedding, workers, GPU batching), как мы планировали в дорожной карте.

---

### 👤 **User** — 2026-08-16 00:46:19

этот одноядерный процесс надо распраллелить, или перенести на Gpu

---

### 🤖 **Assistant** — 2026-08-16 00:46:20

Да, сейчас это узкое место. Текущая версия делает самое дорогое действие:

```text
каждое окно
    |
    v
DINOv2 inference
    |
    v
GPU
```

Но мы вызываем модель **по одному crop за раз**:

```python
embed_paths([одна картинка])
```

Из-за этого RTX 3060 почти простаивает, а CPU занят подготовкой.

Для Banner Search v01 это неправильный режим.

---

## Что нужно сделать правильно

Не распараллеливать DINOv2 через много процессов.

Почему:

- каждый worker загрузит свою копию модели;
- VRAM 11.6 GB быстро закончится;
- будет хуже, чем один GPU batch.

Правильная архитектура:

```
CPU
 |
 | генерация crop
 |
 batch 32-64 изображений
 |
 v
RTX 3060
 |
 DINOv2
 |
 embeddings
 |
 cosine similarity
```

---

## Изменение №1 — batch embedding

Сейчас:

```python
for window in windows:
    embed(window)
```

Плохо.

Нужно:

```python
windows
   |
   v
[
 crop1,
 crop2,
 crop3,
 ...
 crop64
]
   |
   v
embed_paths()
   |
   v
матрица Nx768
```

Ваш `SceneEmbedder` уже это умеет:

```python
embed_images()
```

и:

```python
embed_paths(paths)
```

---

## Изменение №2 — размер batch

Для RTX 3060 12GB:

начать:

```python
BATCH_SIZE = 32
```

если нормально:

```python
BATCH_SIZE = 64
```

---

## Изменение №3 — CPU workers

Ваше правило из дорожной карты сохраняем:

> workers = 1/2 от числа рабочих ядер CPU

Например:

```python
import os

WORKERS = max(
    1,
    os.cpu_count() // 2
)
```

Но workers использовать только для:

- загрузки изображений;
- подготовки crop.

Не для DINO.

---

## Новая схема Banner Search v02

```
                Фото
                 |
        sliding window generator
                 |
        -----------------
        |               |
     worker 1        worker N
        |
        |
     crop queue
        |
        v
    GPU batch
        |
        v
    DINOv2
        |
        v
  similarity search
```

---

## Что это даст

Сейчас:

```
1 crop = 0.3-0.8 сек
```

100 окон:

```
30-80 секунд
```

После batch:

```
100 окон:
примерно 2-5 секунд
```

на вашей RTX 3060.

---

Следующий правильный шаг — не чинить текущий скрипт кусками, а сделать:

```
scripts/banner_crop_search_v02.py
```

с:

✅ batch GPU  
✅ workers = CPU/2  
✅ RAM limit 75%  
✅ сохранение лучших crop  
✅ лог скорости  

Это уже будет соответствовать той оптимизированной архитектуре, которую мы закладывали.

---

### 👤 **User** — 2026-08-16 00:46:53

давай

---

### 🤖 **Assistant** — 2026-08-16 00:46:54

Делаем **Banner Crop Search v02**.  
Основные изменения:

✅ DINOv2 работает батчами на GPU  
✅ CPU используется только для подготовки crop  
✅ workers = половина ядер CPU  
✅ без загрузки нескольких копий модели  
✅ RAM контролируем через размер очереди  
✅ сохраняем лучшие найденные области

Создаём новый файл:

```bash
nano scripts/banner_crop_search_v02.py
```

Вставляем:

```python
#!/usr/bin/env python3

import json
import os
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image
from tqdm import tqdm

from app.core.runtime import get_embedder

PROJECT = Path(__file__).resolve().parent.parent

BANNER_DIR = PROJECT / "data/input/banners"
PHOTO_DIR = PROJECT / "data/input/test"

OUTPUT_DIR = PROJECT / "data/output/found_banners_debug"

TOP_K = 10

BATCH_SIZE = 32

WORKERS = max(
    1,
    os.cpu_count() // 2
)

WINDOW_SIZES = [
    0.25,
    0.35,
    0.45,
    0.55,
]

STEP = 0.15

EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".JPG",
    ".JPEG",
    ".PNG",
}

def get_images(folder):

    return [
        x
        for x in folder.rglob("*")
        if x.suffix in EXT
    ]

def cosine_matrix(query, vectors):

    query = query / np.linalg.norm(query)

    vectors = vectors / np.linalg.norm(
        vectors,
        axis=1,
        keepdims=True
    )

    return np.dot(
        vectors,
        query
    )

def make_windows(img):

    w, h = img.size

    crops = []

    for size in WINDOW_SIZES:

        ww = int(w * size)
        hh = int(h * size)

        step_x = max(
            1,
            int(ww * STEP)
        )

        step_y = max(
            1,
            int(hh * STEP)
        )

        for x in range(
            0,
            w - ww,
            step_x
        ):

            for y in range(
                0,
                h - hh,
                step_y
            ):

                crops.append(
                    {
                        "image": img.crop(
                            (
                                x,
                                y,
                                x + ww,
                                y + hh
                            )
                        ),
                        "x": x,
                        "y": y,
                        "w": ww,
                        "h": hh,
                    }
                )

    return crops

def save_temp_images(items, prefix):

    paths = []

    tmp_dir = Path(
        "/tmp/banner_batch"
    )

    tmp_dir.mkdir(
        exist_ok=True
    )

    for i, item in enumerate(items):

        path = (
            tmp_dir /
            f"{prefix}_{i}.jpg"
        )

        img = item["image"]

        if img.mode != "RGB":
            img = img.convert(
                "RGB"
            )

        img.save(
            path,
            quality=95
        )

        paths.append(
            str(path)
        )

    return paths

def embed_batch(embedder, items, prefix):

    paths = save_temp_images(
        items,
        prefix
    )

    return embedder.embed_paths(
        paths
    )

def main():

    print("=" * 70)
    print("BANNER SEARCH v02")
    print("=" * 70)

    print(
        "CPU workers:",
        WORKERS
    )

    print(
        "Batch:",
        BATCH_SIZE
    )

OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

embedder = get_embedder()

banners = get_images(
        BANNER_DIR
    )

    photos = get_images(
        PHOTO_DIR
    )

if not banners:
        print("No banners")
        return

if not photos:
        print("No photos")
        return

for banner in banners:

        print("\nQUERY:",
              banner.name)

banner_img = Image.open(
            banner
        )

        banner_item = {
            "image": banner_img
        }

banner_emb = embed_batch(
            embedder,
            [banner_item],
            "banner"
        )[0]

results = []

for photo in photos:

            print(
                "SEARCH:",
                photo.name
            )

img = Image.open(
                photo
            )

windows = make_windows(
                img
            )

print(
                "windows:",
                len(windows)
            )

embeddings = []

for start in tqdm(
                range(
                    0,
                    len(windows),
                    BATCH_SIZE
                )
            ):

                batch = windows[
                    start:
                    start + BATCH_SIZE
                ]

                emb = embed_batch(
                    embedder,
                    batch,
                    f"crop_{start}"
                )

                embeddings.append(
                    emb
                )

embeddings = np.concatenate(
                embeddings,
                axis=0
            )

scores = cosine_matrix(
                banner_emb,
                embeddings
            )

best_indexes = np.argsort(
                scores
            )[::-1][:TOP_K]

for idx in best_indexes:

                item = windows[idx]

                results.append(
                    {
                        "photo": str(photo),
                        "score": float(
                            scores[idx]
                        ),
                        "x": item["x"],
                        "y": item["y"],
                        "w": item["w"],
                        "h": item["h"],
                    }
                )

results.sort(
            key=lambda x:x["score"],
            reverse=True
        )

out = (
            OUTPUT_DIR /
            banner.stem
        )

        out.mkdir(
            parents=True,
            exist_ok=True
        )

final = results[:TOP_K]

for i,r in enumerate(
            final,
            start=1
        ):

            print(
                i,
                r["score"],
                r["photo"]
            )

img = Image.open(
                r["photo"]
            )

crop = img.crop(
                (
                    r["x"],
                    r["y"],
                    r["x"] + r["w"],
                    r["y"] + r["h"]
                )
            )

crop.save(
                out /
                f"best_{i}.jpg"
            )

with open(
            out/"result.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                final,
                f,
                indent=2,
                ensure_ascii=False
            )

print("\nDONE")

if __name__ == "__main__":
    main()
```

---

Запуск для теста:

Сначала оставьте только:

```text
data/input/test/
    Ашхабадский_01.JPG
```

и один баннер:

```text
data/input/banners/
    бетсити.png
```

Запуск:

```bash
uv run python scripts/banner_crop_search_v02.py
```

---

После запуска пришлите:

1. время выполнения;
2. строку:

```text
windows: xxxx
```

3. Top-10:

```text
1 0.xxx ...
```

4. желательно посмотреть:

```text
data/output/found_banners_debug/бетсити/
best_1.jpg
```

Это уже будет первый настоящий тест поиска баннера внутри фотографии.

---

### 👤 **User** — 2026-08-16 00:47:44

на ашхабадский надо использовать сизякин

---

### 🤖 **Assistant** — 2026-08-16 00:47:45

Да, правильно. Для **Ашхабадский_01** нужно использовать именно тот макет, который реально установлен на этом объекте.

То есть тест должен быть:

```text
Запрос:
data/input/banners/
    видео_сизякин.jpg   (или точное имя файла)

Поиск:
data/input/test/
    Ашхабадский_01.JPG
```

А не:

```text
бетсити.png
```

Потому что сейчас мы проверяем не просто "похожесть", а реальную задачу:

```text
оригинальный макет
        ↓
найти этот же баннер
        ↓
на фотографии объекта
```

---

Перед запуском лучше очистить папку результатов:

```bash
rm -rf data/output/found_banners_debug/*
```

Оставить только один запрос:

```bash
ls data/input/banners
```

должно быть примерно:

```text
видео_сизякин.jpg
```

И в тесте:

```bash
ls data/input/test | grep Ашхабадский
```

должно быть:

```text
Ашхабадский_01.JPG
```

Запуск:

```bash
uv run python scripts/banner_crop_search_v02.py
```

---

Что будем смотреть:

Если всё правильно:

```
QUERY: видео_сизякин.jpg

SEARCH: Ашхабадский_01.JPG

windows: xxxx

1  score=0.7-0.9
```

и `best_1.jpg` должен визуально показать область баннера.

Если score останется около:

```
0.3-0.4
```

— значит DINO видит общий стиль, но не сам баннер. Тогда следующим шагом будет подключение **patch tokens из вашего v33**, потому что они как раз предназначены для локальных деталей.

---

### 👤 **User** — 2026-08-16 00:51:28

QUERY: видео_сизякин.jpg
SEARCH: Ашхабадский_01.JPG
windows: 727
100%|██████████████████████████████████████████| 23/23 [00:13<00:00,  1.71it/s]
1 0.34176695346832275 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
2 0.3330652415752411 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
3 0.33275219798088074 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
4 0.3305279612541199 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
5 0.3264985680580139 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
6 0.3232753872871399 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
7 0.3207782506942749 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
8 0.3142091631889343 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
9 0.3095817565917969 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
10 0.30588358640670776 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG

QUERY: Screenshot from 2026-08-16 00-38-11.png
SEARCH: Ашхабадский_01.JPG
windows: 727
100%|██████████████████████████████████████████| 23/23 [00:12<00:00,  1.84it/s]
1 0.9213459491729736 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
2 0.9206516146659851 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
3 0.9017031192779541 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
4 0.8960278630256653 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
5 0.8685312271118164 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
6 0.8625114560127258 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
7 0.8588914275169373 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
8 0.8327857255935669 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
9 0.828622579574585 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
10 0.8276575207710266 /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG

DONE
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 00:51:29

Вот это уже очень показательный тест. Теперь мы видим реальную картину.

Результаты:

### 1. Правильный макет

```
видео_сизякин.jpg
        ↓
Ашхабадский_01.JPG
```

получили:

```
0.341
0.333
0.332
...
```

### 2. Скриншот (очевидно тот же баннер/фрагмент)

```
Screenshot from 2026-08-16 00-38-11.png
        ↓
Ашхабадский_01.JPG
```

получили:

```
0.921
0.920
0.901
0.896
...
```

---

## Главный вывод

Алгоритм поиска области **работает**.

DINOv2 прекрасно находит:

```
картинка → такая же картинка
```

с score ~0.92.

Но:

```
оригинальный макет → фотография реального баннера
```

не срабатывает.

Это не проблема поиска. Это проблема **типа признаков**.

---

Сейчас DINO видит:

```
Screenshot:
████████████
████████████
████████████
```

и в фото ищет практически такие же пиксели.

А оригинальный макет:

```
[чистый дизайн]

текст
логотип
цвет
графика
```

против:

```
фото:
- перспектива
- искажение
- блики
- низкое разрешение
- фон
```

---

## Что нужно добавить

Для баннеров нужен двухэтапный поиск.

### Этап 1. Поиск области

Уже есть:

```
sliding window
        ↓
727 crop
```

---

### Этап 2. Специализированное сравнение

Не DINO scene embedding.

Нужно добавить:

```
макет
 |
 feature extractor
 |
+
 crop фото
 |
 feature extractor
 |
 similarity
```

Но модель должна понимать графику.

---

## Я бы не трогал ваш recognizer

Он закрыт и работает.

Для баннеров сделать отдельный модуль:

```
app/banner_search/
```

---

Архитектура:

```
                БАННЕР

                 |
        -------------------
        |                 |
      CLIP              ORB/SIFT
        |                 |
        |                 |
        --------+----------
                |
             rerank
                |
                v

             найденные фото
```

---

Почему CLIP:

Он лучше понимает:

```
логотип
текст
цветовую композицию
дизайн
```

То есть:

```
"Бетсити красно-синий баннер"
```

для него ближе, чем для DINO.

---

## Следующий тест я бы сделал очень маленький:

Не менять архитектуру.

Берём:

```
видео_сизякин.jpg
```

и тот же:

```
Ашхабадский_01.JPG
```

Но вместо DINO whole embedding используем ваши уже имеющиеся:

```
patch tokens
```

из v33.

Потому что patch tokens работают локально:

```
DINO image:

[ ][ ][ ][ ]
[ ][БАННЕР][ ]
[ ][ ][ ][ ]

```

а сейчас у нас:

```
вся картинка = один вектор
```

---

То есть следующий файл:

```
scripts/banner_crop_search_v03_patch.py
```

будет использовать:

```
patch_embeddings
```

из вашего SceneEmbedder.

Это очень логичный следующий шаг, потому что у вас эта часть уже была сделана для v33. Мы не изобретаем новый pipeline. Используем то, что уже дало хороший результат в распознавании адресов.

---

### 👤 **User** — 2026-08-16 00:52:37

маленькие LLM с vision?

---

### 🤖 **Assistant** — 2026-08-16 00:52:38

Да, маленькие Vision-LLM здесь **могут быть полезны**, но важно правильно поставить им задачу.

Сейчас у нас проблема:

```text
оригинальный макет
        ↓
фото реального баннера
```

DINOv2 говорит:

> "визуально похоже/не похоже"

Но не понимает смысл:

- это тот же логотип;
- это тот же текст;
- это тот же рекламный блок;
- это тот же дизайн, но сфотографированный под углом.

Vision-LLM как раз сильнее в этом.

---

## Как я бы использовал Vision-LLM в вашей архитектуре

Не вместо DINO, а как **финальный эксперт**.

Схема:

```
                 Фотоотчёт
                     |
              быстрый поиск
                     |
          DINO / CLIP / color
                     |
              Top-20 кандидатов
                     |
                     v
             Vision LLM
                     |
        "это тот же баннер: да/нет"
```

То есть LLM не смотрит 3000 фотографий. Она проверяет только 10-20 кандидатов.

---

## Подходящие маленькие модели

### 1. Qwen2.5-VL / Qwen3-VL

Очень интересный вариант.

Плюсы:

- хорошо работает с текстом на изображениях;
- понимает рекламные макеты;
- можно запускать локально.

Для вашей RTX 3060 12GB:

реально:

- 3B версия — комфортно;
- 7B — возможно с квантованием.

---

### 2. MiniCPM-V

Очень хорошая маленькая vision-модель.

Плюсы:

- маленькая;
- быстрая;
- хорошо понимает изображения.

Для вашего железа подходит лучше больших моделей.

---

### 3. LLaVA

Популярная, но я бы сейчас не выбирал первой.

Она больше для:

- описаний;
- вопросов по картинке.

Для точного сравнения баннеров есть варианты лучше.

---

## Как это встроить в ваш проект

Я бы сделал отдельный модуль:

```
app/
 └── banner_search/
      |
      ├── cropper.py
      ├── dino_ranker.py
      ├── color_filter.py
      └── vision_verify.py
```

---

Алгоритм:

### Шаг 1

Быстро:

```
300 фото
       |
       |
DINO/CLIP
       |
       |
50 кандидатов
```

---

### Шаг 2

Vision LLM:

Подаём:

```
image 1:
оригинальный макет

image 2:
найденный crop
```

Запрос:

```
Это один и тот же рекламный баннер?
Учитывай:
- логотип
- текст
- расположение элементов
- цветовую схему

Ответ:
MATCH / NO MATCH
confidence 0-100
```

---

Получаем:

```
Ашхабадский_01

DINO:
0.34

Vision:
MATCH 94%

Итог:
найден
```

---

## Ещё один важный момент

У вас уже есть огромный плюс:

ваши фотоотчёты подписаны:

```
Ашхабадский
Радиаторный
Зорге
...
```

То есть в будущем можно сделать обучение на своих данных:

```
правильные пары:

макет
 +
фото установленного баннера
```

И тогда можно дообучить маленький reranker.

---

Моё мнение по архитектуре для вашего проекта:

**не заменять DINO.**

Сделать:

```
DINOv2
    |
    | быстрый поиск
    ↓
Top-20

Vision LLM
    |
    | проверка
    ↓

результат
```

Это будет и быстро, и надёжно.

Для вашей RTX 3060 я бы первым попробовал **Qwen2.5-VL-3B или MiniCPM-V**, а не большие модели.

---

### 👤 **User** — 2026-08-16 00:53:15

Шаг 1

---

### 🤖 **Assistant** — 2026-08-16 00:53:16

Делаем **Шаг 1 — быстрый поиск кандидатов**.  
Vision-LLM пока не подключаем. Сначала строим правильный фильтр.

Цель:

```text
оригинал баннера
        |
        |
        v
быстрый поиск по фотоотчётам
        |
        |
        v
TOP-20 областей, где МОЖЕТ быть этот баннер
```

Для этого используем:

- текущий `SceneEmbedder` (DINOv2);
- sliding window;
- GPU batch (уже сделали);
- сохраняем лучшие crop.

Но меняем логику:

Сейчас:

```text
DINO whole image embedding
```

Дальше:

```text
DINO patch-level / crop-level ranking
```

---

## Шаг 1. Подготавливаем данные

Оставляем тест:

```
data/input/banners/
    видео_сизякин.jpg

data/input/test/
    Ашхабадский_01.JPG
```

Проверка:

```bash
ls data/input/banners
ls data/input/test | grep Ашхабадский
```

---

## Шаг 1.1 — добавляем сохранение координат и превью

Создаём:

```bash
nano scripts/banner_candidates_v01.py
```

Логика:

```text
Ашхабадский_01.JPG

        sliding windows

        727 crop

        DINO batch

        сортировка

        TOP-20
```

Результат:

```
data/output/banner_candidates/

видео_сизякин/

    01_score_0.XXX.jpg
    02_score_0.XXX.jpg
    ...
    candidates.json
```

---

Но перед написанием файла я хочу сделать одно изменение относительно v02.

Сейчас размер окон:

```python
WINDOW_SIZES=[
0.25,
0.35,
0.45,
0.55
]
```

Для баннеров это мало.

На ваших фото наружной рекламы чаще:

- баннер занимает 30-70% ширины;
- может быть длинный горизонтальный формат.

Добавим:

```python
WINDOW_SIZES=[
0.20,
0.30,
0.40,
0.50,
0.60,
0.70
]
```

и отдельно горизонтальные окна:

```python
RATIOS=[
(1.0,1.0),
(2.0,1.0),
(3.0,1.0),
(1.5,1.0)
]
```

То есть искать не только квадрат:

```text
[  ]
```

а:

```text
[------------]
```

что для баннеров намного правильнее.

---

После этого Шаг 1 даст нам:

пример:

```
TOP candidates:

01 score=0.48
   x=1230 y=850 w=1200 h=400

02 score=0.44
   x=1100 y=820 w=1300 h=450
```

и мы глазами смотрим:

**попал ли он в область баннера.**

---

После подтверждения:

**Шаг 2 будет подключение Vision LLM как проверяющего.**

То есть:

```
TOP-20 DINO
       |
       v
Vision LLM
       |
       v
"тот же баннер / не тот"
```

Начинаем с Шага 1. Я подготовлю `banner_candidates_v01.py` под вашу текущую структуру проекта.

---

### 👤 **User** — 2026-08-16 00:53:52

давай макет

---

### 🤖 **Assistant** — 2026-08-16 00:53:55

Берём **макет `видео_сизякин.jpg`** как эталон.

Для первого полноценного теста схема такая:

```text
ЭТАЛОН:

data/input/banners/
└── видео_сизякин.jpg

ПОИСК:

data/input/test/
└── Ашхабадский_01.JPG

РЕЗУЛЬТАТ:

data/output/banner_candidates/
└── видео_сизякин/
    ├── 01_score_xxx.jpg
    ├── 02_score_xxx.jpg
    ├── ...
    └── candidates.json
```

Алгоритм:

```text
видео_сизякин.jpg
        |
        v
DINO embedding

Ашхабадский_01.JPG
        |
        v
генерация окон разных размеров
        |
        v
DINO batch на GPU
        |
        v
TOP-20 crop
```

Для этого теста оставляем только:

```bash
rm data/input/banners/*
cp "путь_к_макету/видео_сизякин.jpg" data/input/banners/
```

и:

```bash
rm data/input/test/*
cp "путь_к_фото/Ашхабадский_01.JPG" data/input/test/
```

После этого запускаем уже **Шаг 1 — поиск кандидатов**.

Следующим сообщением дам готовый `banner_candidates_v01.py` (не экспериментальный, а под вашу структуру `scene_fingerprint_mvp_v02`).

---

### 👤 **User** — 2026-08-16 00:54:00

давай файл

---

### 🤖 **Assistant** — 2026-08-16 00:54:01

Создаём файл:

```bash
nano scripts/banner_candidates_v01.py
```

Вставьте полностью:

```python
#!/usr/bin/env python3

import json
import os
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

from app.core.runtime import get_embedder

PROJECT = Path(__file__).resolve().parent.parent

BANNER_DIR = PROJECT / "data/input/banners"
PHOTO_DIR = PROJECT / "data/input/test"

OUTPUT_DIR = PROJECT / "data/output/banner_candidates"

TOP_K = 20

BATCH_SIZE = 32

WORKERS = max(
    1,
    os.cpu_count() // 2
)

# Для наружной рекламы
# разные размеры и соотношения сторон

WINDOWS = [
    (0.20, 1.0),
    (0.30, 1.0),
    (0.40, 1.0),
    (0.50, 1.0),
    (0.60, 1.0),
    (0.70, 1.0),

    # горизонтальные баннеры
    (0.25, 2.0),
    (0.30, 2.5),
    (0.35, 3.0),
]

STEP = 0.20

EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".JPG",
    ".JPEG",
    ".PNG",
}

def get_images(folder):

    return [
        x
        for x in folder.rglob("*")
        if x.suffix in EXT
    ]

def normalize(img):

    if img.mode != "RGB":
        img = img.convert("RGB")

    return img

def make_windows(img):

    w, h = img.size

    result = []

for scale, ratio in WINDOWS:

        win_w = int(
            w * scale
        )

        win_h = int(
            win_w / ratio
        )

if win_h >= h:
            continue

step_x = max(
            50,
            int(win_w * STEP)
        )

        step_y = max(
            50,
            int(win_h * STEP)
        )

for y in range(
            0,
            h - win_h,
            step_y
        ):

            for x in range(
                0,
                w - win_w,
                step_x
            ):

                crop = img.crop(
                    (
                        x,
                        y,
                        x + win_w,
                        y + win_h
                    )
                )

                result.append(
                    {
                        "image": crop,
                        "x": x,
                        "y": y,
                        "w": win_w,
                        "h": win_h,
                    }
                )

return result

def save_batch(items, prefix):

    tmp = Path(
        "/tmp/banner_candidates"
    )

    tmp.mkdir(
        exist_ok=True
    )

paths = []

for i,item in enumerate(items):

        path = (
            tmp /
            f"{prefix}_{i}.jpg"
        )

normalize(
            item["image"]
        ).save(
            path,
            quality=95
        )

paths.append(
            str(path)
        )

return paths

def embed_batch(embedder, items, prefix):

    paths = save_batch(
        items,
        prefix
    )

    return embedder.embed_paths(
        paths
    )

def cosine_scores(query, vectors):

    query = (
        query /
        np.linalg.norm(query)
    )

vectors = (
        vectors /
        np.linalg.norm(
            vectors,
            axis=1,
            keepdims=True
        )
    )

return np.dot(
        vectors,
        query
    )

def main():

    print("="*70)
    print("BANNER CANDIDATES v01")
    print("="*70)

print(
        "CPU workers:",
        WORKERS
    )

    print(
        "GPU batch:",
        BATCH_SIZE
    )

OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

embedder = get_embedder()

banners = get_images(
        BANNER_DIR
    )

    photos = get_images(
        PHOTO_DIR
    )

if len(banners) != 1:

        print(
            "Для теста нужен один макет"
        )
        print(
            banners
        )
        return

banner = banners[0]
    photo = photos[0]

print(
        "\nQUERY:",
        banner.name
    )

    print(
        "PHOTO:",
        photo.name
    )

banner_img = Image.open(
        banner
    )

banner_emb = embed_batch(
        embedder,
        [
            {
                "image":banner_img
            }
        ],
        "banner"
    )[0]

img = Image.open(
        photo
    )

windows = make_windows(
        img
    )

print(
        "Generated windows:",
        len(windows)
    )

all_scores = []
    all_embeddings = []

for start in tqdm(
        range(
            0,
            len(windows),
            BATCH_SIZE
        )
    ):

        batch = windows[
            start:
            start+BATCH_SIZE
        ]

emb = embed_batch(
            embedder,
            batch,
            f"crop_{start}"
        )

all_embeddings.append(
            emb
        )

embeddings = np.concatenate(
        all_embeddings,
        axis=0
    )

scores = cosine_scores(
        banner_emb,
        embeddings
    )

indexes = np.argsort(
        scores
    )[::-1][:TOP_K]

out = (
        OUTPUT_DIR /
        banner.stem
    )

    out.mkdir(
        parents=True,
        exist_ok=True
    )

result = []

for rank,idx in enumerate(
        indexes,
        start=1
    ):

        item = windows[idx]

        score = float(
            scores[idx]
        )

print(
            f"{rank:02d}",
            score,
            item["x"],
            item["y"],
            item["w"],
            item["h"]
        )

crop = item["image"]

        crop.save(
            out /
            f"{rank:02d}_{score:.3f}.jpg",
            quality=95
        )

result.append(
            {
                "rank":rank,
                "score":score,
                "x":item["x"],
                "y":item["y"],
                "w":item["w"],
                "h":item["h"],
            }
        )

with open(
        out/"candidates.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False
        )

print("\nDONE")

if __name__ == "__main__":
    main()
```

Запуск:

```bash
uv run python scripts/banner_candidates_v01.py
```

Перед тестом:

```bash
ls data/input/banners
ls data/input/test
```

Должно быть:

```text
data/input/banners/
    видео_сизякин.jpg

data/input/test/
    Ашхабадский_01.JPG
```

После запуска пришлите:

1. строку:

```text
Generated windows: xxxx
```

2. первые 10 результатов:

```text
01 0.xxx x y w h
```

3. что лежит в:

```bash
ls data/output/banner_candidates/видео_сизякин
```

Особенно интересно будет открыть:

```text
01_xxx.jpg
```

Если туда попал баннер — первый этап готов.

---

### 👤 **User** — 2026-08-16 00:55:38

QUERY: видео_сизякин.jpg
PHOTO: Ашхабадский_01.JPG
Generated windows: 1479
100%|██████████████████████████████████████████| 47/47 [00:21<00:00,  2.18it/s]
01 0.45938539505004883 1770 1144 888 444
02 0.4094139635562897 1704 1190 1065 426
03 0.3807388246059418 1770 1232 888 444
04 0.37694495916366577 1736 1148 1243 414
05 0.37650054693222046 1488 1148 1243 414
06 0.3726878762245178 1770 1320 888 444
07 0.37255623936653137 1704 1275 1065 426
08 0.3677558898925781 1593 1144 888 444
09 0.3409005105495453 1416 1144 888 444
10 0.34015607833862305 1278 1105 1065 426
11 0.33944639563560486 1488 1066 1243 414
12 0.33432334661483765 1491 1190 1065 426
13 0.3336030840873718 1947 1144 888 444
14 0.3299944996833801 1488 1230 1243 414
15 0.32850897312164307 1704 852 710 710
16 0.32314494252204895 1846 994 710 710
17 0.32116788625717163 1240 1148 1243 414
18 0.3135135769844055 1770 1408 888 444
19 0.31081676483154297 1704 1105 1065 426
20 0.3095574378967285 1278 1190 1065 426

DONE
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 00:55:39

Отлично. Это уже **реальный результат поиска**, и он гораздо информативнее предыдущего.

Главное:

```text
QUERY: видео_сизякин.jpg
PHOTO: Ашхабадский_01.JPG
```

Лучший кандидат:

```text
01 score=0.459385

x=1770
y=1144
w=888
h=444
```

То есть DINO + sliding window нашёл **конкретную область**, а не весь кадр.

---

## Что изменилось относительно первого теста

Было:

```text
всё фото → макет

score ~0.34
```

Сейчас:

```text
область фото → макет

score 0.459
```

Прирост:

```text
+35%
```

Это подтверждает, что направление правильное.

---

## Очень интересный момент

Все топовые кандидаты находятся примерно здесь:

```
x: 1400-1900
y: 1100-1400
```

То есть:

```text
01
02
03
04
05
...
```

это одна и та же зона с разными размерами окна.

Например:

```
01:
1770 1144 888 444

02:
1704 1190 1065 426

04:
1736 1148 1243 414
```

DINO стабильно нашёл один объект.

Это хороший признак.

---

## Следующий шаг — визуальная проверка

Открой:

```bash
xdg-open data/output/banner_candidates/видео_сизякин
```

Посмотри:

```text
01_0.459.jpg
02_0.409.jpg
03_0.380.jpg
```

Главный вопрос:

**внутри первого crop действительно находится баннер "Сизякин"?**

---

## Если да

Тогда следующий шаг:

### Banner Search v02.1

Добавляем:

### 1. Удаление дублей

Сейчас:

```
01
02
03
04
05
```

это один и тот же баннер.

Нужно делать NMS (non-max suppression):

```text
найден один объект

оставить:
лучший crop

удалить похожие окна
```

Тогда будет:

```
1. Баннер найден
2. координаты
3. score
```

---

### 2. Второй ранг — Vision LLM

После NMS:

```
DINO:

candidate #1
candidate #2
candidate #3

↓

Vision LLM

"это тот же баннер?"

↓

MATCH
```

---

Но сейчас я бы сделал ещё один очень важный тест.

Взять **эти координаты**:

```
x=1770
y=1144
w=888
h=444
```

и сравнить:

```
видео_сизякин.jpg

vs

01_0.459.jpg
```

Если глазами это один баннер — первый этап готов.

---

Ещё замечание: скорость тоже хорошая:

```
1479 windows
21 сек
```

На RTX 3060.

После оптимизации можно будет:

- уменьшить окна;
- добавить предварительный color filter;
- сделать batch 64.

Реально выйти на:

```
1 фото ≈ 3-5 секунд
```

---

Сейчас пришлите, что находится в `01_0.459.jpg` (можно просто скрин/описание). Это определит следующий шаг.

---

### 👤 **User** — 2026-08-16 00:56:21

внутри все верно

---

### 🤖 **Assistant** — 2026-08-16 00:56:22

Отлично. Это ключевой момент — **первый этап поиска баннеров доказан**.

Получилась рабочая цепочка:

```text
оригинальный макет
        |
        v
DINOv2 embedding
        |
        v
поиск по sliding window
        |
        v
найдена область на реальном фото
        |
        v
score 0.459
```

И самое важное: найденный crop действительно содержит нужный баннер.

---

## Что мы сейчас имеем

Текущая версия:

```
banner_candidates_v01
```

уже умеет:

✅ взять макет  
✅ найти область на фотографии  
✅ работать с реальным фото (перспектива, фон)  
✅ работать на GPU batch  
✅ выдавать координаты найденного объекта  

---

## Следующий логичный этап — улучшение качества

Сейчас проблема не в поиске, а в ранжировании.

У нас:

```
01 0.459  правильный баннер
02 0.409  тот же баннер (другое окно)
03 0.380  тот же баннер
...
```

Нужно убрать дубли.

Добавляем **NMS (Non-Max Suppression)**.

Было:

```
TOP-20

01
02
03
04
05
...
```

станет:

```
Найденные объекты:

1. Ашхабадский_01
   score 0.459
   bbox 1770,1144,888,444

2. следующий объект
   score 0.xxx
```

---

## Потом второй уровень

После NMS:

```
DINO
 |
 | быстро
 |
TOP-5
 |
 v
Vision LLM
 |
 | проверка смысла
 |
MATCH / NO MATCH
```

Например:

Vision получает:

```
Изображение A:
оригинальный макет Сизякин

Изображение B:
crop с Ашхабадский_01
```

И отвечает:

```
MATCH
confidence: 96%
```

---

## Ещё один важный вывод

Ваша первоначальная идея:

> "загрузить оригинал макета и найти его среди подписанных фото"

— абсолютно реализуема.

Причём структура получается очень хорошая:

```
                    WEB UI

                      |
        +-------------+-------------+
        |                           |
  Распознавание адресов        Поиск баннеров
        |                           |
   DINO fingerprints          Banner Search
        |                           |
  alias адреса                макет → фото
```

Они используют одну инфраструктуру:

- GPU
- SceneEmbedder
- логи
- историю
- web интерфейс

---

Я предлагаю следующий шаг:

**Banner Search v02 — добавить NMS + красивый отчёт**

Вывод:

```
data/output/banner_search/

видео_сизякин/

result.html
result.json

01_found.jpg
02_found.jpg
```

В HTML сразу:

```
[оригинал]

↓

[найденный фрагмент]

score: 0.459
координаты:
x=1770 y=1144
```

Это уже будет почти готовый модуль для будущего веб-интерфейса.

---

### 👤 **User** — 2026-08-16 00:56:46

параллельно можно обрабатывать несколько фото?

---

### 🤖 **Assistant** — 2026-08-16 00:56:48

Да, можно. Более того, для вашего сценария (200–300 фото в дневном фотоотчёте) **это обязательно нужно сделать**.

Но важно разделить два уровня параллельности.

Сейчас у нас:

```text
1 фото
 |
1479 crop
 |
DINO batch
 |
результат
```

То есть GPU занят **одним фото за раз**.

---

## Правильная архитектура для пакетного поиска

Нужно сделать очередь:

```text
                 PHOTO QUEUE

Ашхабадский_01 ─┐
Радиаторный_25 ──┤
Зорге_15 ────────┤
Менжинского_10 ──┘
                  |
                  v

          CPU workers

       генерация crop
       подготовка batch

|
                  v

              GPU QUEUE

        DINOv2 batch=32/64

|
                  v

             результаты
```

---

## Сколько фото одновременно?

С вашей конфигурацией:

- RTX 3060 12 GB
- DINOv2 ViT-B/14
- CPU неизвестно, но правило у нас уже есть:

```python
workers = CPU cores / 2
```

Я бы начал:

```text
CPU workers: 4-8
GPU batch: 64
одновременно фото в памяти: 4-8
```

---

## Вариант для ваших 300 фото

Например:

```text
300 фотографий

worker 1:
создаёт окна фото №1

worker 2:
создаёт окна фото №2

worker 3:
создаёт окна фото №3

worker 4:
создаёт окна фото №4

GPU:

batch 64 crop

↓

результаты
```

---

## Важный момент по RAM

Вы правильно заложили ограничение:

> RAM 75%

Нельзя просто открыть 300 фото 4000×3000.

Одно такое фото:

```text
4000 × 3000 × 3 byte ≈ 36 MB
```

Но после PIL/тензоров:

может быть 100-200 MB.

Поэтому нужен:

```text
producer-consumer queue
```

Например:

```python
QUEUE_SIZE = 8
```

То есть максимум 8 фотографий готовятся одновременно.

---

## По времени

Сейчас:

```text
1 фото
1479 окон
21 сек
```

Если 300 фото:

```text
≈ 6300 секунд
≈ 10,5 часов
```

Но это без оптимизации.

После:

### batch GPU

примерно:

```text
1 фото:
3-5 сек
```

300 фото:

```text
15-25 минут
```

---

## Для вашей будущей веб-системы я бы сделал так:

```text
Banner Search Job

id
|
├── source_folder
├── banner
├── status
├── processed
├── total
├── best_results
└── log
```

И интерфейс:

```
[Макет баннера]

[Папка фотоотчёта]

Количество фото: 286

        СТАРТ

████████░░░ 78%

Найдено:
Ашхабадский_01  score 0.459
Радиаторный_25   score 0.421
```

---

Следующий технический шаг я бы сделал не NMS, а именно:

**Banner Search v03 — пакетная обработка папки**

Потому что у вас конечная задача — не один Ашхабадский, а:

> загрузить макет → найти его среди сотен фотоотчётов.

И архитектуру уже лучше строить под это.

---

### 👤 **User** — 2026-08-16 00:57:45

Banner Search v03 — пакетная обработка папки

---

### 🤖 **Assistant** — 2026-08-16 00:57:46

Делаем **Banner Search v03 — пакетная обработка папки**.

Цель версии v03:

```text
макет баннера
        |
        v
папка с фотоотчётами (200-300 фото)
        |
        v
параллельная подготовка crop
        |
        v
GPU batch DINO
        |
        v
TOP найденных мест
```

Отличия от v01/v02:

✅ обрабатывает **всю папку**  
✅ несколько фото в очереди  
✅ GPU batch сохраняется  
✅ ограничение памяти через очередь  
✅ результат по каждому фото  
✅ общий рейтинг по всей папке  

Архитектура:

```text
                 data/input/test

        +------------+------------+
        |            |            |
     фото 1       фото 2       фото 3
        |            |            |
        +------------+------------+
                     |
                     v

             crop workers

          CPU workers = cores/2

                     |
                     v

              GPU batch queue

              DINOv2 RTX 3060

                     |
                     v

              similarity

                     |
                     v

data/output/banner_search/

    видео_сизякин/

        Ашхабадский_01/
             best_01.jpg
             result.json

        Радиаторный_25/
             best_01.jpg
             result.json

        summary.json
```

---

Перед кодом сделаем важное изменение.

В v02 у нас:

```python
фото
 |
все окна
 |
DINO
```

В v03:

```python
фото №1
    |
 crop generation
    |
 queue

фото №2
    |
 crop generation
    |
 queue

GPU:
batch 64 crop
```

---

Настройки для вашей RTX 3060:

```python
BATCH_SIZE = 64
MAX_QUEUE = 8
WORKERS = CPU/2
```

Если будет нехватка VRAM:

```python
BATCH_SIZE = 32
```

---

Создаём файл:

```bash
nano scripts/banner_search_v03.py
```

Я дам его следующим сообщением, потому что он уже получается достаточно большой (около 350 строк), и лучше вставить цельным файлом без обрезки.

Он будет использовать вашу текущую структуру:

```python
from app.core.runtime import get_embedder
```

и не затронет:

- recognizer
- fingerprints
- v33
- основной пайплайн

То есть это будет отдельный экспериментальный модуль `Banner Search`.

---

### 👤 **User** — 2026-08-16 00:58:18

давай файл

---

### 🤖 **Assistant** — 2026-08-16 00:58:19

Создаём:

```bash
nano scripts/banner_search_v03.py
```

Вставьте файл целиком:

```python
#!/usr/bin/env python3

import os
import json
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from PIL import Image
from tqdm import tqdm

from app.core.runtime import get_embedder

PROJECT = Path(__file__).resolve().parent.parent

BANNER_DIR = PROJECT / "data/input/banners"
PHOTO_DIR = PROJECT / "data/input/test"

OUTPUT_DIR = PROJECT / "data/output/banner_search"

TOP_K = 5

BATCH_SIZE = 64

WORKERS = max(
    1,
    os.cpu_count() // 2
)

STEP = 0.20

WINDOWS = [
    (0.20, 1.0),
    (0.30, 1.0),
    (0.40, 1.0),
    (0.50, 1.0),
    (0.60, 1.0),

    (0.25, 2.0),
    (0.30, 2.5),
    (0.35, 3.0),
]

EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".JPG",
    ".JPEG",
    ".PNG",
}

def images(folder):

    return [
        p
        for p in folder.rglob("*")
        if p.suffix in EXT
    ]

def prepare(img):

    if img.mode != "RGB":
        img = img.convert("RGB")

    return img

def create_windows(img):

    w, h = img.size

    result = []

for scale, ratio in WINDOWS:

        ww = int(w * scale)

        hh = int(
            ww / ratio
        )

if hh >= h:
            continue

sx = max(
            50,
            int(ww * STEP)
        )

        sy = max(
            50,
            int(hh * STEP)
        )

for y in range(
            0,
            h-hh,
            sy
        ):

            for x in range(
                0,
                w-ww,
                sx
            ):

                result.append(
                    {
                        "image":
                            img.crop(
                                (
                                    x,
                                    y,
                                    x+ww,
                                    y+hh
                                )
                            ),

                        "bbox":
                            [
                                x,
                                y,
                                ww,
                                hh
                            ]
                    }
                )

return result

def cosine(query, vectors):

    query = (
        query /
        np.linalg.norm(query)
    )

    vectors = (
        vectors /
        np.linalg.norm(
            vectors,
            axis=1,
            keepdims=True
        )
    )

return vectors @ query

def embed_items(
        embedder,
        items,
        prefix
):

    tmp = Path(
        "/tmp/banner_v03"
    )

    tmp.mkdir(
        exist_ok=True
    )

paths=[]

for i,item in enumerate(items):

        p = (
            tmp /
            f"{prefix}_{i}.jpg"
        )

        prepare(
            item["image"]
        ).save(
            p,
            quality=90
        )

        paths.append(
            str(p)
        )

return embedder.embed_paths(
        paths
    )

def process_photo(
        embedder,
        banner_emb,
        photo
):

    img = Image.open(
        photo
    )

img = prepare(
        img
    )

windows = create_windows(
        img
    )

embeddings=[]

for i in range(
        0,
        len(windows),
        BATCH_SIZE
    ):

        batch = windows[
            i:
            i+BATCH_SIZE
        ]

emb = embed_items(
            embedder,
            batch,
            photo.stem
        )

embeddings.append(
            emb
        )

embeddings = np.concatenate(
        embeddings,
        axis=0
    )

scores = cosine(
        banner_emb,
        embeddings
    )

best = np.argsort(
        scores
    )[::-1][:TOP_K]

result_dir = (
        OUTPUT_DIR /
        photo.stem
    )

    result_dir.mkdir(
        parents=True,
        exist_ok=True
    )

rows=[]

for rank,index in enumerate(
        best,
        1
    ):

        item = windows[index]

        score=float(
            scores[index]
        )

filename = (
            result_dir /
            f"{rank:02d}_{score:.3f}.jpg"
        )

item["image"].save(
            filename,
            quality=95
        )

rows.append(
            {
                "rank":rank,
                "score":score,
                "bbox":
                    item["bbox"],
                "file":
                    str(filename)
            }
        )

with open(
        result_dir/"result.json",
        "w",
        encoding="utf8"
    ) as f:

        json.dump(
            rows,
            f,
            indent=2,
            ensure_ascii=False
        )

return {
        "photo":
            photo.name,

        "best":
            rows[0]
    }

def main():

    print("="*70)
    print("BANNER SEARCH v03")
    print("="*70)

print(
        "Workers:",
        WORKERS
    )

    print(
        "GPU batch:",
        BATCH_SIZE
    )

OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

embedder = get_embedder()

banners = images(
        BANNER_DIR
    )

photos = images(
        PHOTO_DIR
    )

if len(banners)==0:

        print(
            "Нет макета"
        )

        return

if len(banners)>1:

        print(
            "Положите один макет"
        )

        return

banner=banners[0]

print(
        "\nQUERY:",
        banner.name
    )

    print(
        "PHOTOS:",
        len(photos)
    )

banner_item = [
        {
            "image":
                Image.open(
                    banner
                )
        }
    ]

banner_emb = embed_items(
        embedder,
        banner_item,
        "banner"
    )[0]

results=[]

with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as pool:

tasks = [

            pool.submit(
                process_photo,
                embedder,
                banner_emb,
                p
            )

            for p in photos
        ]

for task in tqdm(
            as_completed(tasks),
            total=len(tasks)
        ):

            results.append(
                task.result()
            )

results.sort(
        key=lambda x:
            x["best"]["score"],
        reverse=True
    )

with open(
        OUTPUT_DIR/"summary.json",
        "w",
        encoding="utf8"
    ) as f:

        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False
        )

print("\nTOP RESULTS")

    for r in results[:20]:

        print(
            r["best"]["score"],
            r["photo"]
        )

print("\nDONE")

if __name__ == "__main__":

    main()
```

Запуск:

```bash
uv run python scripts/banner_search_v03.py
```

---

Для первого теста оставляем:

```text
data/input/banners/
└── видео_сизякин.jpg

data/input/test/
├── Ашхабадский_01.JPG
├── Радиаторный_25.JPG
├── Зорге_15.JPG
...
```

После запуска пришлите:

1. блок:

```text
Workers:
GPU batch:
PHOTOS:
```

2. `TOP RESULTS`

3. размер папки:

```bash
du -sh data/output/banner_search
```

Следующий шаг после проверки — добавим **NMS + HTML отчёт + сохранение только реально найденных баннеров**.

---

### 👤 **User** — 2026-08-16 01:02:14

cpu отдыхает - как можно переложить часть работы на него, может быть воркеров 8 сделать или 10

---

### 🤖 **Assistant** — 2026-08-16 01:02:15

Да, сейчас это ожидаемое поведение. В текущем `v03` узкое место — **GPU**, а CPU почти не загружен, потому что мы сделали простую схему:

```text
CPU:
создал окно
сохранил jpg
отдал

GPU:
DINO embedding
DINO embedding
DINO embedding
...
```

То есть CPU делает слишком мало.

Увеличение:

```python
WORKERS = 8
```

или:

```python
WORKERS = 10
```

может помочь, но не сильно, потому что у нас сейчас проблема не только в количестве потоков.

---

## Что лучше сделать

Разделить pipeline на 3 этапа:

```text
                CPU
                 |
                 |
        генерация crop окон
        подготовка изображений
        resize
        normalize
                 |
                 v

              очередь

                 |
                 v

                GPU
          DINO batch 64/128

                 |
                 v

                CPU
        сортировка score
        NMS
        сохранение
```

Сейчас у нас нет настоящего буфера между CPU и GPU.

---

## Быстрый тест №1

Сначала просто увеличим:

```python
WORKERS = 8
```

или лучше:

```python
WORKERS = min(
    10,
    os.cpu_count()
)
```

Проверяем загрузку:

```bash
htop
```

и:

```bash
watch -n 1 nvidia-smi
```

---

## Но есть более важный параметр

Сейчас:

```python
BATCH_SIZE = 64
```

Для RTX 3060 12GB можно попробовать:

```python
BATCH_SIZE = 96
```

или:

```python
BATCH_SIZE = 128
```

Потому что DINOv2 ViT-B/14 обычно любит большие batch.

---

## Ещё тормозит вот это место

Сейчас каждый crop:

```python
crop.save(
    jpg
)

embed_paths(
    jpg
)
```

То есть идёт:

```text
RAM
 ↓
JPEG encode
 ↓
диск /tmp
 ↓
JPEG decode
 ↓
GPU
```

Это очень дорого.

Правильнее:

```text
RAM
 ↓
PIL Image
 ↓
transform
 ↓
GPU
```

Без сохранения 1479 jpg на каждый кадр.

Это даст больше, чем увеличение workers.

---

## Мой порядок оптимизации:

### 1. Сейчас:

изменить:

```python
WORKERS = 8
BATCH_SIZE = 96
```

и проверить.

### 2. Потом:

убрать:

```python
save jpg → load jpg
```

перевести на:

```python
embed_images()
```

У вас эта функция уже есть:

```python
app/core/embedder.py

def embed_images(...)
```

Это самый большой резерв.

### 3. Потом:

добавить multiprocessing:

```text
CPU process 1
CPU process 2
CPU process 3
CPU process 4

готовят batches

GPU постоянно занят
```

---

Для вашего железа я бы целился примерно в:

сейчас:

```text
GPU utilization: 40-60%
CPU: 10%
```

цель:

```text
GPU utilization: 90-95%
CPU: 40-60%
```

---

Давайте сначала сделаем минимальное изменение:

в `banner_search_v03.py`:

заменить:

```python
WORKERS = max(
    1,
    os.cpu_count() // 2
)
```

на:

```python
WORKERS = min(
    10,
    os.cpu_count()
)
```

и:

```python
BATCH_SIZE = 96
```

Запустить повторно и посмотреть `nvidia-smi` + время. Если GPU всё равно будет простаивать — тогда убираем JPEG через `embed_images()`. Это даст самый большой прирост.

---

### 👤 **User** — 2026-08-16 01:03:13

авай готовый файл

---

### 🤖 **Assistant** — 2026-08-16 01:03:14

Да, делаем промежуточную оптимизированную версию **v03.1**.

Изменения относительно v03:

1. `WORKERS = min(10, os.cpu_count())`
2. `BATCH_SIZE = 96`
3. Убираем лишнее ограничение по CPU/2
4. Добавляем вывод загрузочного режима
5. Оставляем архитектуру без изменения, чтобы сравнить скорость

Откройте:

```bash
nano scripts/banner_search_v03.py
```

Замените начало файла до `WINDOWS` на это:

```python
#!/usr/bin/env python3

import os
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from PIL import Image
from tqdm import tqdm

from app.core.runtime import get_embedder

PROJECT = Path(__file__).resolve().parent.parent

BANNER_DIR = PROJECT / "data/input/banners"
PHOTO_DIR = PROJECT / "data/input/test"

OUTPUT_DIR = PROJECT / "data/output/banner_search"

TOP_K = 5

# ===== OPTIMIZATION =====

CPU_CORES = os.cpu_count() or 1

WORKERS = min(
    10,
    CPU_CORES
)

# RTX 3060 12GB
BATCH_SIZE = 96

print("=" * 70)
print("BANNER SEARCH v03.1")
print("=" * 70)
print("CPU cores:", CPU_CORES)
print("Workers:", WORKERS)
print("GPU batch:", BATCH_SIZE)
print("=" * 70)

STEP = 0.20

WINDOWS = [
    (0.20, 1.0),
    (0.30, 1.0),
    (0.40, 1.0),
    (0.50, 1.0),
    (0.60, 1.0),

    (0.25, 2.0),
    (0.30, 2.5),
    (0.35, 3.0),
]

EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".JPG",
    ".JPEG",
    ".PNG",
}
```

Остальную часть файла оставляем без изменений.

---

Запуск:

```bash
uv run python scripts/banner_search_v03.py
```

Параллельно в другом терминале:

GPU:

```bash
watch -n 1 nvidia-smi
```

CPU:

```bash
htop
```

---

Что ожидаем:

Было:

```
1479 windows
21 сек
GPU ~40-60%
CPU ~10%
```

После:

```
GPU batch 96
workers 10
```

ожидаем:

```
GPU ~70-90%
время меньше
```

---

Если GPU всё равно будет простаивать — следующий шаг уже не `workers`, а самый большой резерв:

**убрать сохранение каждого crop в JPEG и передавать PIL → tensor напрямую через `embed_images()`**.

Там может быть ускорение в 2-3 раза.

---

### 👤 **User** — 2026-08-16 01:10:01

запустил - ничего не присходило

---

### 🤖 **Assistant** — 2026-08-16 01:10:02

Похоже, я дал не совсем удачное изменение: мы вынесли `print()` в начало файла, но если запуск идёт через импорт или завис на инициализации `get_embedder()`, вывода может не быть сразу.

Сначала проверим, **что именно происходит**.

В другом терминале выполните:

```bash
ps aux | grep banner_search
```

и отдельно:

```bash
nvidia-smi
```

---

Ещё важный момент: в `v03` у нас:

```python
from app.core.runtime import get_embedder
```

А `get_embedder()` может загрузить:

- PyTorch
- DINOv2
- CUDA
- веса модели

Это может занимать время и без вывода.

---

Давайте сделаем правильный вариант: добавим контрольные точки.

Откройте:

```bash
nano scripts/banner_search_v03.py
```

Найдите:

```python
embedder = get_embedder()
```

замените на:

```python
print("Loading embedder...", flush=True)

embedder = get_embedder()

print("Embedder ready", flush=True)
```

---

Дальше найдите:

```python
banners = images(
    BANNER_DIR
)
```

замените:

```python
print("Scanning folders...", flush=True)

banners = images(
    BANNER_DIR
)

photos = images(
    PHOTO_DIR
)

print(
    "Banner files:",
    len(banners),
    "Photo files:",
    len(photos),
    flush=True
)
```

---

И перед обработкой:

найдите:

```python
with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as pool:
```

замените:

```python
print(
    "Starting workers:",
    WORKERS,
    flush=True
)

with ThreadPoolExecutor(
        max_workers=WORKERS
    ) as pool:
```

---

Запускаем:

```bash
uv run python scripts/banner_search_v03.py
```

Должно появиться:

```text
======================================================================
BANNER SEARCH v03.1
======================================================================
CPU cores: xx
Workers: 10
GPU batch: 96

Loading embedder...
[SceneEmbedder] device=cuda
[SceneEmbedder] Ready.

Embedder ready

Scanning folders...
Banner files: 1 Photo files: xxx

Starting workers: 10
```

---

Если после `Loading embedder...` стоит больше 1-2 минут — проблема не в workers, а в загрузке модели.

Если после `Starting workers: 10` зависает — тогда будем менять схему потоков, потому что PyTorch + CUDA не любит несколько потоков, одновременно вызывающих один и тот же `embedder`.

И это как раз может быть наша следующая оптимизация: **CPU workers → очередь → один GPU worker**. Для PyTorch это обычно быстрее и стабильнее.

---

### 👤 **User** — 2026-08-16 01:11:19

alexice@NEURO:~/Desktop$ ps aux | grep banner_search
alexice   141793  0.1  0.0 221508 31152 pts/3    Sl+  01:10   0:00 uv run python scripts/banner_search_v03.py
alexice   141804  150 31.4 21166696 10298800 pts/3 Sl+ 01:10   0:17 /home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/python3 scripts/banner_search_v03.py
alexice   141997  0.0  0.0   9296  2316 pts/0    S+   01:10   0:00 grep --color=auto banner_search
alexice@NEURO:~/Desktop$ ps aux | grep banner_search
alexice   141793  0.0  0.0 221508  2212 pts/3    Sl+  01:10   0:00 uv run python scripts/banner_search_v03.py
alexice   141804  181 87.3 40090788 28628804 pts/3 Sl+ 01:10   0:38 /home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/python3 scripts/banner_search_v03.py
alexice   142063  0.0  0.0   9296  2296 pts/0    S+   01:10   0:00 grep --color=auto banner_search
alexice@NEURO:~/Desktop$

---

### 🤖 **Assistant** — 2026-08-16 01:11:20

Отлично, теперь видно, что **процесс не завис**. Он работает, но мы нашли проблему.

Смотрите:

Первый замер:

```
CPU: 150%
RAM: 31.4% (10 GB)
```

Через 28 секунд:

```
CPU: 181%
RAM: 87.3% (28 GB)
```

То есть:

- процесс активно считает;
- CPU загружен;
- память улетает вверх.

Проблема не в workers — проблема в архитектуре v03.

---

## Что произошло

Мы сделали:

```python
ThreadPoolExecutor(
    max_workers=10
)
```

и каждый worker запускает:

```python
process_photo()
        |
        |
        create_windows()
        |
        |
        DINO embedding
```

То есть одновременно:

```
worker 1 → PyTorch → GPU
worker 2 → PyTorch → GPU
worker 3 → PyTorch → GPU
...
worker 10 → PyTorch → GPU
```

А PyTorch начинает копировать данные в CUDA и держать их в памяти.

Получилось:

```
10 потоков
×
1479 crop
×
тензоры
```

отсюда:

```
RAM 28 GB
```

---

## Правильная схема для вашей задачи

Нужно НЕ так:

```
10 CPU workers
      |
      |
  10 GPU запросов
```

А так:

```
CPU workers (8-10)

готовят crop

        |
        |
     QUEUE

        |
        |
  ОДИН GPU worker

  DINO batch=96
```

То есть GPU всегда один.

Это стандартный pipeline для нейросетей.

---

## Сейчас остановите процесс

В терминале:

```bash
Ctrl+C
```

---

## Временное решение для теста

Поставьте обратно:

```python
WORKERS = 2
```

и:

```python
BATCH_SIZE = 96
```

Проверим скорость.

Но правильная версия будет v03.2:

```
CPU producer
      |
 multiprocessing.Queue
      |
GPU consumer
```

---

## Ещё один момент

RAM 75% у нас нарушилась.

Сейчас:

```
28 GB
```

Если у вас 32 GB RAM — это почти предел.

Нужно добавить ограничение:

```python
MAX_IN_MEMORY_PHOTOS = 4
```

То есть:

не держать одновременно:

```
10 фото
×
1479 crop
```

а:

```
4 фото
×
crop
×
batch
```

---

Предлагаю сделать **v03.2 правильно**:

- `workers = CPU/2` для генерации окон;
- очередь максимум 4;
- один GPU поток;
- batch 96;
- RAM ограничена;
- GPU загрузка будет выше.

Это уже будет архитектура под ваши 200-300 фотоотчётов.

---

### 👤 **User** — 2026-08-16 01:11:59

ltkfq

---

### 🤖 **Assistant** — 2026-08-16 01:12:00

Похоже, набралось в неправильной раскладке: `ltkfq` = **"давай"**.

Делаем **Banner Search v03.2 — правильная архитектура**:

```text
CPU workers
    |
    |  готовят crop
    |
    v
Queue (ограниченная память)
    |
    |
    v
Один GPU worker
    |
    | batch 96
    |
    v
DINOv2
    |
    v
результаты
```

Что исправляем:

- убираем одновременный вызов CUDA из 10 потоков;
- CPU занимается подготовкой окон;
- GPU получает большие стабильные batch;
- RAM ограничиваем;
- сохраняем правило:

```python
workers = CPU / 2
```

Настройки:

```python
CPU_WORKERS = max(1, os.cpu_count() // 2)

GPU_BATCH = 96

QUEUE_SIZE = 4
```

Ожидаемый результат:

сейчас:

```text
RAM: 28 GB
GPU нестабильно
```

после:

```text
RAM: 8-12 GB
GPU: 80-95%
```

и обработка 200-300 фото станет предсказуемой.

Сейчас подготовлю готовый файл:

```text
scripts/banner_search_v03_2.py
```

под вашу текущую структуру:

```python
from app.core.runtime import get_embedder
```

и без изменения основного `recognizer`.

---

### 👤 **User** — 2026-08-16 01:12:11

давай файл

---

