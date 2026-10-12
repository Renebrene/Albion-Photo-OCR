## СЕССИЯ: ФОТОБАЗА ОФИС

**Создано:** 2026-08-16 00:03:58
**Обновлено:** 2026-08-19 21:49:51
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df)

---

### 🤖 **Assistant** — 2026-08-16 01:12:15

Делаем `v03.2`.  
Главное изменение: **GPU больше не вызывается из нескольких потоков**. CPU только готовит задания, один поток работает с DINO.

Создайте:

```bash
nano scripts/banner_search_v03_2.py
```

Вставьте:

```python
#!/usr/bin/env python3

import os
import json
import queue
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image
from tqdm import tqdm

from app.core.runtime import get_embedder

PROJECT = Path(__file__).resolve().parent.parent

BANNER_DIR = PROJECT / "data/input/banners"
PHOTO_DIR = PROJECT / "data/input/test"

OUTPUT_DIR = PROJECT / "data/output/banner_search_v03_2"

TOP_K = 5

CPU_WORKERS = max(
    1,
    (os.cpu_count() or 2) // 2
)

GPU_BATCH = 96

QUEUE_SIZE = 4

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

def get_images(folder):

    return [
        p
        for p in folder.rglob("*")
        if p.suffix in EXT
    ]

def prepare(img):

    if img.mode != "RGB":
        img = img.convert("RGB")

    return img

def make_windows(path):

    img = prepare(
        Image.open(path)
    )

    w, h = img.size

    result = []

    for scale, ratio in WINDOWS:

        ww = int(w * scale)
        hh = int(ww / ratio)

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

def embed_images(embedder, items):

    images = [
        x["image"]
        for x in items
    ]

    return embedder.embed_images(
        images
    )

def gpu_worker(
        embedder,
        banner_emb,
        tasks,
        results
):

    while True:

        item = tasks.get()

        if item is None:
            break

photo, windows = item

all_embeddings = []

for i in range(
            0,
            len(windows),
            GPU_BATCH
        ):

            batch = windows[
                i:i+GPU_BATCH
            ]

            emb = embed_images(
                embedder,
                batch
            )

            all_embeddings.append(
                emb
            )

embeddings = np.concatenate(
            all_embeddings,
            axis=0
        )

scores = cosine(
            banner_emb,
            embeddings
        )

best = np.argsort(
            scores
        )[::-1][:TOP_K]

out_dir = (
            OUTPUT_DIR /
            photo.stem
        )

        out_dir.mkdir(
            parents=True,
            exist_ok=True
        )

rows=[]

for rank,idx in enumerate(
            best,
            1
        ):

            w = windows[idx]

            score=float(
                scores[idx]
            )

filename = (
                out_dir /
                f"{rank:02d}_{score:.3f}.jpg"
            )

w["image"].save(
                filename,
                quality=95
            )

rows.append(
                {
                    "rank": rank,
                    "score": score,
                    "bbox": w["bbox"],
                    "file": str(filename)
                }
            )

with open(
            out_dir/"result.json",
            "w",
            encoding="utf8"
        ) as f:

            json.dump(
                rows,
                f,
                indent=2,
                ensure_ascii=False
            )

results.append(
            {
                "photo": photo.name,
                "score": rows[0]["score"],
                "best": rows[0]
            }
        )

tasks.task_done()

def main():

    print("="*70)
    print("BANNER SEARCH v03.2")
    print("="*70)

    print(
        "CPU workers:",
        CPU_WORKERS
    )

    print(
        "GPU batch:",
        GPU_BATCH
    )

    print(
        "Queue:",
        QUEUE_SIZE
    )

OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

print("Loading model...")

    embedder = get_embedder()

    print("Model ready")

banners = get_images(
        BANNER_DIR
    )

    photos = get_images(
        PHOTO_DIR
    )

if len(banners) != 1:

        print(
            "Нужен один файл в banners"
        )
        return

banner = banners[0]

banner_emb = embedder.embed_images(
        [
            prepare(
                Image.open(
                    banner
                )
            )
        ]
    )[0]

print(
        "Photos:",
        len(photos)
    )

tasks = queue.Queue(
        maxsize=QUEUE_SIZE
    )

results=[]

gpu = threading.Thread(
        target=gpu_worker,
        args=(
            embedder,
            banner_emb,
            tasks,
            results
        )
    )

    gpu.start()

print("Preparing crops...")

def producer(photo):

        windows = make_windows(
            photo
        )

        tasks.put(
            (
                photo,
                windows
            )
        )

with ThreadPoolExecutor(
        max_workers=CPU_WORKERS
    ) as pool:

        list(
            tqdm(
                pool.map(
                    producer,
                    photos
                ),
                total=len(photos)
            )
        )

tasks.join()

tasks.put(None)

    gpu.join()

results.sort(
        key=lambda x:
            x["score"],
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

print("\nTOP")

    for r in results[:20]:

        print(
            r["score"],
            r["photo"]
        )

print("DONE")

if __name__ == "__main__":
    main()
```

Запуск:

```bash
uv run python scripts/banner_search_v03_2.py
```

Параллельно:

```bash
watch -n 1 nvidia-smi
```

и:

```bash
htop
```

Что ожидаем увидеть:

- RAM не должна уходить к 28 GB;
- GPU должен быть занят ровнее;
- CPU будет занят генерацией окон.

После запуска пришлите:

```
CPU workers:
GPU batch:
Photos:
```

и первые строки `TOP`.

---

### 👤 **User** — 2026-08-16 01:13:55

опять все зависло

---

### 🤖 **Assistant** — 2026-08-16 01:13:58

Хорошо, это полезный тест. Судя по симптомам, проблема уже понятна: **зависание происходит не из-за GPU**, а из-за архитектуры подготовки данных.

В `v03.2` я сделал ошибку: мы сделали очередь, но **producer сначала полностью готовит все окна для всех фотографий**, а только потом передаёт их в GPU.

То есть при 200–300 фото получается:

```text
CPU workers
    |
    |
создают тысячи crop
    |
    |
держат их в RAM
    |
    |
queue забита
```

И если один worker зависает на PIL/памяти — кажется, что всё "стоит".

---

Сейчас надо остановить:

```bash
Ctrl+C
```

Проверить, что процесс ушёл:

```bash
ps aux | grep banner_search
```

---

Я бы сделал следующий вариант **v03.3**, более правильный:

```text
Фото №1
 |
CPU worker
 |
генерирует crop
 |
сразу в GPU batch
 |
результат
 |
следующее фото

```

То есть **не копим окна вообще**.

Память будет:

```
1 фото → crop → GPU → удалить
```

а не:

```
300 фото → 400000 crop → RAM
```

---

Ещё добавим обязательный контроль:

```python
print(
 "processing:",
 photo.name,
 flush=True
)
```

чтобы всегда было видно, где процесс.

---

Настройки оставляем:

```python
CPU_WORKERS = 4
GPU_BATCH = 96
```

Не 10. Для PyTorch + CUDA лучше меньше.

---

И ещё одно важное изменение:

Мы больше не будем использовать:

```python
ThreadPoolExecutor
```

для GPU pipeline.

Сделаем:

```text
CPU multiprocessing
        |
        |
один основной процесс
        |
        |
GPU
```

Это стабильнее для PyTorch.

---

То есть следующий файл:

```
scripts/banner_search_v03_3.py
```

будет:

✅ потоковая обработка  
✅ RAM максимум несколько GB  
✅ один CUDA контекст  
✅ прогресс по каждому фото  
✅ подходит для 300 фотоотчётов  

Сейчас мы уже нашли, где была ошибка. Дальше не будем наращивать workers — сначала сделаем стабильный pipeline.

---

### 👤 **User** — 2026-08-16 01:14:33

давай

---

### 🤖 **Assistant** — 2026-08-16 01:14:34

Делаем **v03.3**. Эта версия проще и стабильнее:

- ❌ нет многопоточности вокруг CUDA;
- ❌ нет накопления тысяч crop в RAM;
- ✅ одно фото → crop → GPU batch → результат → освобождение памяти;
- ✅ RAM остаётся стабильной;
- ✅ GPU работает последовательно и предсказуемо.

Создайте:

```bash
nano scripts/banner_search_v03_3.py
```

Вставьте:

```python
#!/usr/bin/env python3

import os
import json
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

from app.core.runtime import get_embedder

PROJECT = Path(__file__).resolve().parent.parent

BANNER_DIR = PROJECT / "data/input/banners"
PHOTO_DIR = PROJECT / "data/input/test"

OUTPUT_DIR = PROJECT / "data/output/banner_search_v03_3"

TOP_K = 5

GPU_BATCH = 96

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

def get_images(folder):

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

def embed_batch(embedder, batch):

    images = [
        x["image"]
        for x in batch
    ]

    return embedder.embed_images(
        images
    )

def search_photo(
        embedder,
        banner_emb,
        photo
):

    print(
        "\nPROCESS:",
        photo.name,
        flush=True
    )

img = prepare(
        Image.open(photo)
    )

windows = create_windows(
        img
    )

print(
        "windows:",
        len(windows),
        flush=True
    )

best_scores = []

    embeddings_all = []

for start in tqdm(
        range(
            0,
            len(windows),
            GPU_BATCH
        ),
        desc="GPU batches"
    ):

        batch = windows[
            start:
            start+GPU_BATCH
        ]

emb = embed_batch(
            embedder,
            batch
        )

scores = cosine(
            banner_emb,
            emb
        )

for i,s in enumerate(scores):

            best_scores.append(
                (
                    float(s),
                    windows[start+i]
                )
            )

best_scores.sort(
        key=lambda x:x[0],
        reverse=True
    )

best_scores = best_scores[:TOP_K]

out = (
        OUTPUT_DIR /
        photo.stem
    )

    out.mkdir(
        parents=True,
        exist_ok=True
    )

rows=[]

for rank,(score,item) in enumerate(
        best_scores,
        1
    ):

        file = (
            out /
            f"{rank:02d}_{score:.3f}.jpg"
        )

item["image"].save(
            file,
            quality=95
        )

rows.append(
            {
                "rank":rank,
                "score":score,
                "bbox":item["bbox"],
                "file":str(file)
            }
        )

with open(
        out/"result.json",
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
        "photo":photo.name,
        "score":rows[0]["score"]
    }

def main():

    print("="*70)
    print("BANNER SEARCH v03.3")
    print("="*70)

    print(
        "CPU cores:",
        os.cpu_count()
    )

    print(
        "GPU batch:",
        GPU_BATCH
    )

OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

print(
        "Loading model..."
    )

    embedder = get_embedder()

    print(
        "Model ready"
    )

banners = get_images(
        BANNER_DIR
    )

    photos = get_images(
        PHOTO_DIR
    )

if len(banners)!=1:

        print(
            "В banners должен быть один макет"
        )

        return

banner = banners[0]

banner_img = prepare(
        Image.open(
            banner
        )
    )

banner_emb = embedder.embed_images(
        [
            banner_img
        ]
    )[0]

print(
        "QUERY:",
        banner.name
    )

    print(
        "PHOTOS:",
        len(photos)
    )

results=[]

for photo in photos:

        r = search_photo(
            embedder,
            banner_emb,
            photo
        )

        results.append(
            r
        )

results.sort(
        key=lambda x:x["score"],
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
            r["score"],
            r["photo"]
        )

print("\nDONE")

if __name__ == "__main__":
    main()
```

Запуск:

```bash
uv run python scripts/banner_search_v03_3.py
```

Контроль:

```bash
watch -n 1 nvidia-smi
```

и:

```bash
htop
```

Ожидаем:

- RAM не должна расти бесконечно;
- появится:

```
PROCESS: Ашхабадский_01.JPG
windows: 1479
GPU batches: 16/16
```

После первого фото сразу будет понятно, работает ли поток.

Если эта версия стабильна — дальше оптимизируем скорость (без риска зависаний): уберём промежуточные преобразования PIL и поднимем загрузку GPU.

---

### 👤 **User** — 2026-08-16 01:16:08

пошло быстрее, но можно нагрузить cpu побольше

---

### 🤖 **Assistant** — 2026-08-16 01:16:09

Отлично. Значит мы попали в правильную архитектуру: **GPU теперь работает стабильно**, RAM не улетает. Сейчас узкое место уже видно — подготовка окон на CPU.

В `v03.3` сейчас:

```text
CPU:
создать crop
    |
GPU:
DINO batch
```

Но CPU делает всё в одном основном потоке:

```python
for photo in photos:
    search_photo(...)
```

Поэтому часть процессора простаивает.

Теперь можно аккуратно добавить **CPU prefetch**, но не трогать CUDA.

Правильная схема:

```
CPU worker 1 ┐
CPU worker 2 ├──> очередь окон
CPU worker 3 ┘
              |
              v
        один GPU worker
              |
              v
          DINO batch 96
```

То есть:

- CPU будет загружен;
- GPU останется один;
- RAM ограничим.

---

Для вашей машины (RTX 3060 + предположительно многоядерный CPU) я бы поставил:

```python
CPU_WORKERS = 4
QUEUE_SIZE = 3
GPU_BATCH = 128
```

Не 10 потоков — это мы уже проверили, что плохо для CUDA.

---

В текущем файле меняем только подготовку.

В начало добавляем:

```python
from concurrent.futures import ThreadPoolExecutor
import queue
import threading
```

Добавляем настройки:

```python
CPU_WORKERS = 4
QUEUE_SIZE = 3
```

---

Но я бы сделал ещё лучше: не распараллеливать crop внутри одного фото, а параллелить **фотографии**.

То есть:

сейчас:

```
фото1
  crop
  GPU
фото2
  crop
  GPU
```

будет:

```
CPU:
фото1 → подготовка
фото2 → подготовка
фото3 → подготовка

        очередь

GPU:
batch
batch
batch
```

---

Следующая версия будет:

`banner_search_v03_4.py`

Изменения:

✅ CPU workers = 4  
✅ очередь ограничена (RAM ≤ 75%)  
✅ GPU один  
✅ batch 128  
✅ прогресс по фото сохраняется  
✅ без зависаний v03.1/v03.2  

По скорости ожидаю:

сейчас у вас примерно:

```
47 batches
21 сек
```

может стать:

```
47 batches
10-15 сек
```

при условии, что GPU не станет ограничением.

Сделаю готовый `v03_4`.

---

### 👤 **User** — 2026-08-16 01:16:33

у меня ryzen 5600

---

### 🤖 **Assistant** — 2026-08-16 01:16:34

Отлично, тогда картина яснее.

У вас:

- **AMD Ryzen 5 5600**
- 6 ядер / 12 потоков
- **RTX 3060 12 GB**
- RAM (судя по прошлому выводу) около 32 GB

Для такого железа оптимальные настройки будут другие.

Не надо ставить 10 workers. Для Ryzen 5600 лучше:

```python
CPU_WORKERS = 3
```

или максимум:

```python
CPU_WORKERS = 4
```

Почему:

- 6 физических ядер;
- 2-3 ядра оставить системе и PyTorch;
- остальные использовать для подготовки crop.

Схема:

```
Ryzen 5600

ядро 1-3:
  подготовка окон
  PIL resize
  crop

ядро 4-6:
  система + Python + CUDA driver

RTX 3060:
  DINOv2 batch
```

---

Ещё можно увеличить batch:

Сейчас:

```python
GPU_BATCH = 96
```

Для RTX 3060 12GB я бы попробовал:

```python
GPU_BATCH = 128
```

Если без ошибки CUDA:

```python
GPU_BATCH = 160
```

DINOv2 ViT-B/14 обычно хорошо масштабируется.

---

Я бы сделал следующую конфигурацию v03.4:

```python
CPU_WORKERS = 3
QUEUE_SIZE = 3
GPU_BATCH = 128
```

и включил:

```python
torch.backends.cudnn.benchmark = True
```

Это даст небольшой прирост.

---

Ещё важный момент: у вас поиск идёт по разрезанному баннеру.

Сейчас:

```
1 фото:
1479 окон
```

При 300 фото:

```
443 700 окон
```

Поэтому следующий большой прирост будет не только CPU, а:

1. предварительный поиск по цвету/размеру;
2. отсеивание 70-80% окон;
3. DINO только для кандидатов.

Например:

```
443 000 окон

↓ color histogram

80 000 окон

↓ DINO

лучшие 100
```

Это уже будет реально промышленный режим.

Но сначала я бы сделал v03.4 под ваш Ryzen 5600:

```
3 CPU workers
batch 128
prefetch queue
```

Это будет правильный баланс для вашей системы.

---

### 👤 **User** — 2026-08-16 01:19:23

пока что гоняю существующий тест. 15 с на фото - надо посомтреть результат - найдет или нет

---

### 🤖 **Assistant** — 2026-08-16 01:19:24

Отлично. Сейчас **не трогаем оптимизацию** — это правильный момент.

15 секунд на фото для текущего алгоритма (1479 окон + DINOv2 ViT-B/14) уже выглядит нормально. Главное сейчас — **качество поиска**, а не скорость.

Проверяем по факту:

1. В конце должен появиться блок:

```text
TOP RESULTS

0.xxx  Ашхабадский_01.JPG
0.xxx  ...
```

2. Смотрим папку:

```bash
ls -lah data/output/banner_search_v03_3
```

Должны быть каталоги:

```text
Ашхабадский_01/
```

внутри:

```text
01_0.xxx.jpg
02_0.xxx.jpg
03_0.xxx.jpg
result.json
```

Самое важное — открыть первый crop:

```bash
xdg-open data/output/banner_search_v03_3/Ашхабадский_01/01_*.jpg
```

---

Для теста с **"видео_сизякин.jpg" → "Ашхабадский_01.JPG"** я бы ожидал примерно такую картину:

### хороший результат:

```text
score > 0.7
```

и crop реально содержит кусок баннера.

### средний:

```text
0.4 - 0.7
```

Это уже интересно — значит DINO нашёл визуальное соответствие, но надо улучшать поиск.

### плохо:

```text
< 0.3
```

Тогда надо менять стратегию:

- не весь crop через DINO;
- добавить multi-scale;
- добавить цветовой фильтр;
- возможно добавить CLIP для макета.

---

Сейчас ключевой тест:

**нашёл ли v03.3 именно кусок Ашхабадского баннера, а не просто похожую сцену?**

Пришлите:

1. последние 20 строк консоли (`TOP RESULTS`);
2. первый найденный crop (можно скрин).

Если попадание есть — дальше будем уже ускорять. Если нет — будем менять саму метрику поиска.

---

### 👤 **User** — 2026-08-16 01:25:43

очень ресурсоемкая задача, давай попробуем LLM

---

### 🤖 **Assistant** — 2026-08-16 01:25:44

Да, можно попробовать LLM с Vision, но важно правильно определить место в пайплайне. Для вашей задачи **LLM не должна заменять DINO-поиск**, иначе будет медленно и дорого. Лучше использовать её как **второй этап проверки кандидатов**.

Сейчас у нас:

```text
макет баннера
        |
        v
DINOv2 crop search
        |
        v
топ-N найденных окон
```

Добавляем:

```text
топ-10 / топ-20 окон
        |
        v
Vision LLM
        |
        v
"это тот же баннер или нет?"
```

---

Почему так:

DINO хорошо отвечает на вопрос:

> "похоже ли это визуально?"

Но плохо понимает:

> "это именно тот рекламный макет, только снятый с другого ракурса?"

А Vision LLM может оценивать:

- логотип;
- текст;
- расположение элементов;
- цвета;
- персонажей;
- структуру баннера.

---

Для локальной работы на вашей машине:

Ryzen 5600 + RTX 3060 12GB:

### Реальные варианты:

#### 1. Qwen2.5-VL
Очень интересный вариант.

Например:

- Qwen2.5-VL-3B
- Qwen2.5-VL-7B

На RTX 3060:

- 3B — нормально;
- 7B — скорее с квантованием.

#### 2. LLaVA
Старый вариант:

- LLaVA 1.5 7B
- LLaVA-NeXT

Работать будет, но хуже для мелких деталей.

#### 3. MiniCPM-V
Тоже хороший вариант для слабых GPU.

---

Я бы сделал архитектуру так:

```
                 БАННЕР
                    |
                    |
             DINO crop search
                    |
          ---------------------
          |        |          |
        crop1    crop2      crop3
          |
          |
       Vision LLM
          |
          |
   вероятность совпадения
```

Например запрос:

```
Ты эксперт по наружной рекламе.

Сравни два изображения.

Изображение А — оригинальный макет.
Изображение Б — фотография с улицы.

Определи:
1. это один и тот же баннер?
2. процент совпадения.
3. какие признаки совпадают.
```

Ответ:

```json
{
"match": true,
"confidence": 92,
"reason":
"Совпадает логотип, расположение текста,
цветовая схема и изображение человека"
}
```

---

Но я бы не запускал LLM по всем 1479 окнам.

Правильный режим:

Сначала DINO:

```
1479 окон
 ↓
20 лучших
 ↓
Vision LLM
 ↓
1-3 финальных
```

Тогда время:

сейчас:

```
15 сек / фото
```

будет:

```
15 сек DINO
+
5-10 сек LLM
```

а не минуты.

---

Предлагаю сделать отдельный эксперимент:

**Banner Search v04 — DINO + Vision verifier**

Пока без изменения текущего поиска:

1. Оставляем `v03.3`.
2. Берём top-5 crop.
3. Отправляем их в локальную Vision модель.
4. Получаем ранжирование.

Для вашей RTX 3060 я бы начал с:

- **Qwen2.5-VL-3B-Instruct**
или
- **MiniCPM-V 2.6**

Через `ollama` будет проще всего.

Сначала проверим, есть ли у вас уже Ollama:

```bash
ollama list
```

Если нет — поднимем отдельный модуль и подключим к `banner_search`.

---

### 👤 **User** — 2026-08-16 01:26:52

NAME                    ID              SIZE      MODIFIED     
qwen3:1.7b              8f68893c685c    1.4 GB    28 hours ago    
qwen3:0.6b              7df6b6e09427    522 MB    28 hours ago    
qwen3-coder:latest      06c1097efce0    18 GB     6 days ago      
qwen3-vl:4b-instruct    ee4b975b58c1    3.3 GB    6 days ago      
qwq:32b                 009cb3f08d74    19 GB     6 days ago      
qwen3-32k:latest        b3e2287c81ab    5.2 GB    6 days ago      
bge-m3:latest           790764642607    1.2 GB    6 days ago      
qwen3:4b                359d7dd4bcda    2.5 GB    6 days ago      
qwen3:8b                500a1f067a9f    5.2 GB    6 days ago      
deepseek-r1:14b         c333b7232bdb    9.0 GB    4 weeks ago     
llama3.2-vision:11b     6f2f9757ae97    7.8 GB    4 weeks ago     
qwen2.5-coder:7b        dae161e27b0e    4.7 GB    4 weeks ago     
alexice@NEURO:~/Desktop$ 
  давай попробуем чисто на llm

---

### 🤖 **Assistant** — 2026-08-16 01:26:54

Отлично, у вас уже есть подходящая модель:

```text
qwen3-vl:4b-instruct    3.3 GB
```

Для чистого эксперимента **LLM-only** это как раз лучший кандидат из имеющихся.

Но надо понимать ограничения:

- DINOv2 ищет по тысячам окон быстро;
- Vision LLM делает "понимание", но медленно;
- поэтому чистый LLM по всей папке `test` будет очень тяжёлым.

Сделаем **тест №1**:

**Задача:**

```text
QUERY:
data/input/banners/видео_сизякин.jpg

SEARCH:
data/input/test/Ашхабадский_01.JPG
```

Отправляем:

1. оригинальный макет;
2. фото с улицы;

и спрашиваем:

> "Есть ли этот баннер на фотографии?"

---

Создадим скрипт:

```bash
nano scripts/banner_llm_test_v01.py
```

Файл:

```python
#!/usr/bin/env python3

import base64
import json
import requests
from pathlib import Path

QUERY = Path(
    "data/input/banners/видео_сизякин.jpg"
)

PHOTO = Path(
    "data/input/test/Ашхабадский_01.JPG"
)

MODEL = "qwen3-vl:4b-instruct"

def encode_image(path):

    with open(path, "rb") as f:
        return base64.b64encode(
            f.read()
        ).decode()

def ask_llm():

    prompt = """
Ты эксперт по наружной рекламе.

У тебя есть два изображения.

Изображение 1:
оригинальный макет баннера.

Изображение 2:
фотография с улицы.

Определи:

1. Есть ли этот же баннер на фотографии?
2. Процент уверенности 0-100.
3. Какие признаки совпадают:
- логотип
- текст
- цвета
- композиция
- изображения людей/предметов

Ответь строго JSON:

{
"match": true/false,
"confidence": число,
"reason": "описание"
}
"""

payload = {

        "model": MODEL,

        "messages":[
            {
                "role":"user",
                "content":[

                    {
                    "type":"text",
                    "text":prompt
                    },

                    {
                    "type":"image",
                    "image":
                    encode_image(QUERY)
                    },

                    {
                    "type":"image",
                    "image":
                    encode_image(PHOTO)
                    }

                ]
            }
        ],

        "stream":False
    }

r=requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=600
    )

print(
        r.json()["message"]["content"]
    )

if __name__=="__main__":

    print(
        "QUERY:",
        QUERY
    )

    print(
        "PHOTO:",
        PHOTO
    )

    ask_llm()
```

Запуск:

```bash
uv run python scripts/banner_llm_test_v01.py
```

---

Ожидаем что-то типа:

```json
{
"match": true,
"confidence": 92,
"reason":
"Совпадает логотип BetCity,
расположение текста и цветовая схема"
}
```

---

Очень интересно будет сравнить:

DINO дал:

```text
0.459
```

LLM может дать совсем другую оценку.

Если Qwen3-VL сможет уверенно сказать "да" — это будет сильный аргумент в пользу гибридной схемы:

```text
DINO → 20 кандидатов → Qwen3-VL → финальный ответ
```

А не просто DINO.

---

### 👤 **User** — 2026-08-16 01:27:12

z ,ele bcrfnm gj ythfpltkyysv wtksv ajnj

---

### 🤖 **Assistant** — 2026-08-16 01:27:15

Понял: **будем искать по неразделённым целым фотографиям**, без нарезки на окна.

Это как раз хороший тест для LLM, потому что она будет работать в своей сильной зоне:

```text
макет баннера
        +
полное фото улицы
        ↓
Qwen3-VL
        ↓
есть ли этот баннер на фото
```

Но надо учитывать ограничение: если баннер занимает небольшую часть большого фото, Vision-модель может его "не заметить".

Поэтому сделаем два режима:

### Тест №1 — полный кадр

```text
QUERY:
видео_сизякин.jpg

PHOTO:
Ашхабадский_01.JPG
```

LLM получает оригинал + всё фото.

---

### Тест №2 — полный кадр + автоматический zoom

Если полный кадр не увидит:

```text
фото
 |
 +-- верх
 +-- центр
 +-- низ
 +-- левая часть
 +-- правая часть
```

и уже эти части отдаём Qwen3-VL.

Это будет намного дешевле, чем DINO:

Сейчас DINO:

```text
1 фото
≈1500 окон
≈15 секунд
```

LLM:

```text
1 фото
1-5 запросов
```

---

Для первого теста я бы изменил скрипт:

- убрать DINO полностью;
- использовать `qwen3-vl:4b-instruct`;
- вывести:
  - match;
  - confidence;
  - описание совпадений.

После этого сравним:

```
DINO v03.3:
score 0.459

Qwen3-VL:
???
```

Если Qwen3-VL уверенно найдёт Ашхабадский — тогда можно сделать отдельный быстрый режим:
**LLM-first поиск по фотоотчётам**, а DINO оставить как массовый ускоритель.

---

### 👤 **User** — 2026-08-16 01:27:51

давай

---

### 🤖 **Assistant** — 2026-08-16 01:27:52

Делаем **чистый LLM тест по целым фотографиям**.

Используем вашу:

```text
qwen3-vl:4b-instruct
```

Задача:

```text
data/input/banners/видео_сизякин.jpg
            +
data/input/test/Ашхабадский_01.JPG

            ↓

        Qwen3-VL

            ↓

есть баннер или нет
```

Создаём файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nano scripts/banner_llm_full_v01.py
```

Вставьте:

```python
#!/usr/bin/env python3

import base64
import json
import requests
from pathlib import Path

MODEL = "qwen3-vl:4b-instruct"

QUERY = Path(
    "data/input/banners/видео_сизякин.jpg"
)

PHOTO = Path(
    "data/input/test/Ашхабадский_01.JPG"
)

def image64(path):

    with open(path, "rb") as f:
        return base64.b64encode(
            f.read()
        ).decode("utf-8")

def ask():

    prompt = """
Ты специалист по наружной рекламе.

Сравни два изображения.

Первое изображение:
это оригинальный макет рекламного баннера.

Второе изображение:
это фотография улицы.

Определи, присутствует ли этот баннер
на фотографии.

Учитывай:
- логотипы
- текст
- цвета
- расположение элементов
- изображения людей
- общую композицию

Ответ строго JSON:

{
 "match": true или false,
 "confidence": число 0-100,
 "reason": "краткое объяснение"
}

Не придумывай совпадения.
Если баннер маленький или плохо виден,
укажи низкую уверенность.
"""

payload = {

        "model": MODEL,

        "stream": False,

        "messages": [
            {
                "role": "user",

                "content": [

                    {
                        "type": "text",
                        "text": prompt
                    },

                    {
                        "type": "image",
                        "image": image64(QUERY)
                    },

                    {
                        "type": "image",
                        "image": image64(PHOTO)
                    }

                ]
            }
        ]
    }

print("Sending to:", MODEL)

    r = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=600
    )

    r.raise_for_status()

    answer = r.json()["message"]["content"]

    print("\nRESULT:")
    print(answer)

if __name__ == "__main__":

    print("="*60)
    print("BANNER LLM TEST")
    print("="*60)

    print("QUERY :", QUERY)
    print("PHOTO :", PHOTO)

    ask()
```

Запуск:

```bash
uv run python scripts/banner_llm_full_v01.py
```

Параллельно можно смотреть GPU:

```bash
watch -n 1 nvidia-smi
```

---

Ожидаемый результат будет примерно:

```json
{
 "match": true,
 "confidence": 85,
 "reason": "Совпадает логотип BetCity, цветовая схема и расположение текста"
}
```

или:

```json
{
 "match": false,
 "confidence": 20,
 "reason": "Не удалось обнаружить похожий баннер"
}
```

После этого сравним:

- DINO: `0.459`
- Qwen3-VL: результат

И решим, какой путь лучше:
1. LLM-only;
2. DINO → LLM (скорее всего лучший вариант);
3. DINO + OCR + LLM как эксперт.

---

### 👤 **User** — 2026-08-16 01:28:35

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/banner_llm_full_v01.py
============================================================
BANNER LLM TEST
============================================================
QUERY : data/input/banners/видео_сизякин.jpg
PHOTO : data/input/test/Ашхабадский_01.JPG
Sending to: qwen3-vl:4b-instruct
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/banner_llm_full_v01.py", line 126, in <module>
    ask()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/banner_llm_full_v01.py", line 108, in ask
    r.raise_for_status()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/requests/models.py", line 1167, in raise_for_status
    raise HTTPError(http_error_msg, response=self)
requests.exceptions.HTTPError: 400 Client Error: Bad Request for url: http://localhost:11434/api/chat
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 01:28:36

Хорошо, ошибка понятная. Ollama отвечает, но **формат запроса для vision неправильный**.

У Ollama API для vision-моделей (`qwen3-vl`) изображения передаются не как:

```json
{
"type":"image",
"image":"base64..."
}
```

а через поле `images` у сообщения.

Исправляем.

Замените функцию `ask()` в файле на эту:

```python
def ask():

    prompt = """
Ты специалист по наружной рекламе.

Сравни два изображения.

Первое изображение:
оригинальный макет рекламного баннера.

Второе изображение:
фотография улицы.

Определи, есть ли этот же баннер
на фотографии.

Учитывай:
- логотип
- текст
- цвета
- расположение элементов
- композицию

Ответ строго JSON:

{
 "match": true,
 "confidence": 0-100,
 "reason": "описание"
}

Если не уверен — снижай confidence.
"""

payload = {

        "model": MODEL,

        "stream": False,

        "messages": [
            {
                "role": "user",

                "content": prompt,

                "images": [
                    image64(QUERY),
                    image64(PHOTO)
                ]
            }
        ]
    }

print("Sending images...")

    r = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=600
    )

print("HTTP:", r.status_code)

    if r.status_code != 200:
        print(r.text)
        return

answer = r.json()["message"]["content"]

    print("\nRESULT:")
    print(answer)
```

---

Перед повтором проверим, что Ollama действительно видит vision:

```bash
ollama show qwen3-vl:4b-instruct
```

Должно быть что-то вроде:

```text
Capabilities:
  vision
```

---

Потом:

```bash
uv run python scripts/banner_llm_full_v01.py
```

---

Ещё момент: если фото 3500×2500, Qwen3-VL может долго переваривать полный размер. Если будет:

- 2-3 минуты без ответа;
- VRAM забита;

тогда добавим перед отправкой:

```python
img.thumbnail((1280,1280))
```

Это для LLM почти не ухудшит качество, а скорость увеличит в несколько раз.

Сначала попробуем исправленный API.

---

### 👤 **User** — 2026-08-16 01:29:49

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ollama show qwen3-vl:4b-instruct
  Model
    architecture        qwen3vl    
    parameters          4.4B       
    context length      262144     
    embedding length    2560       
    quantization        Q4_K_M     

  Capabilities
    completion    
    vision        
    tools         

  Parameters
    temperature    1       
    top_k          20      
    top_p          0.95    

  License
    Apache License               
    Version 2.0, January 2004    
    ...                          

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 01:29:50

Отлично. Модель подходит:

```text
architecture        qwen3vl
parameters          4.4B
quantization        Q4_K_M
Capabilities:
    vision ✅
```

Значит проблема была только в формате запроса.

Теперь меняем скрипт под настоящий Ollama Vision API.

Заодно я бы сразу добавил уменьшение изображения, потому что ваши фото 3500×2500 для Qwen3-VL избыточны. Для первого теста достаточно 1280 px.

Замените весь файл:

```bash
nano scripts/banner_llm_full_v02.py
```

на:

```python
#!/usr/bin/env python3

import base64
import io
import requests

from pathlib import Path
from PIL import Image

MODEL = "qwen3-vl:4b-instruct"

QUERY = Path(
    "data/input/banners/видео_сизякин.jpg"
)

PHOTO = Path(
    "data/input/test/Ашхабадский_01.JPG"
)

def image64(path, max_size=1280):

    img = Image.open(path)

    if img.mode != "RGB":
        img = img.convert("RGB")

    img.thumbnail(
        (max_size, max_size)
    )

    buf = io.BytesIO()

    img.save(
        buf,
        format="JPEG",
        quality=90
    )

    return base64.b64encode(
        buf.getvalue()
    ).decode()

def ask():

    prompt = """
Ты эксперт по наружной рекламе.

Сравни два изображения.

IMAGE 1:
оригинальный макет баннера.

IMAGE 2:
фотография улицы.

Нужно определить:
есть ли этот же баннер на фотографии.

Проверяй:
- логотип
- текст
- цветовую схему
- расположение элементов
- изображения
- композицию

Ответ строго JSON:

{
 "match": true или false,
 "confidence": число 0-100,
 "reason": "краткое объяснение"
}
"""

payload = {

        "model": MODEL,

        "stream": False,

        "messages": [

            {
                "role": "user",

                "content": prompt,

                "images": [

                    image64(QUERY),

                    image64(PHOTO)

                ]

            }

        ]
    }

print("Sending to Ollama...")

r = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=600
    )

print(
        "HTTP:",
        r.status_code
    )

if r.status_code != 200:

        print(r.text)
        return

print("\nRESULT:")
    print(
        r.json()["message"]["content"]
    )

if __name__ == "__main__":

    print("="*60)
    print("QWEN3-VL BANNER TEST")
    print("="*60)

    print(
        "QUERY:",
        QUERY
    )

    print(
        "PHOTO:",
        PHOTO
    )

    ask()
```

Запуск:

```bash
uv run python scripts/banner_llm_full_v02.py
```

Параллельно:

```bash
watch -n 1 nvidia-smi
```

Что интересно посмотреть:

1. Время ответа.
2. Использование VRAM.
3. Ответ Qwen.

Особенно важен случай:

- DINO дал `0.459`
- Qwen сможет сказать "это тот же баннер" или нет.

Если Qwen3-VL увидит Ашхабадский — это будет хороший кандидат на второй этап:
**DINO ищет быстро → Qwen подтверждает**.

---

### 👤 **User** — 2026-08-16 01:30:49

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/banner_llm_full_v02.py
============================================================
QWEN3-VL BANNER TEST
============================================================
QUERY: data/input/banners/видео_сизякин.jpg
PHOTO: data/input/test/Ашхабадский_01.JPG
Sending to Ollama...
HTTP: 200

RESULT:
{
  "match": true,
  "confidence": 98,
  "reason": "Оба изображения показывают идентичный баннер. Логотип партии, текст (имя, должность, дата выборов, слоган), цветовая схема (голубой фон, белый и красный текст/элементы) и расположение всех графических элементов совпадают. Фотография демонстрирует баннер в контексте улицы, что подтверждает его наличие."
}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 01:30:51

Отличный результат. Это очень важный эксперимент.

Получили:

```text
Qwen3-VL 4B:
match = true
confidence = 98%
```

при этом:

```text
DINOv2 crop search:
score ≈ 0.459
```

То есть вывод такой:

**LLM Vision действительно решает задачу "это тот же баннер?" намного лучше, чем чистый embedding.**

Но есть важный нюанс: это был **один известный кадр**. Теперь надо проверить реальную задачу поиска.

---

## Что мы узнали

Текущие методы:

### DINOv2

Сильная сторона:

✅ быстрый поиск по тысячам изображений  
✅ устойчивость к ракурсу  
✅ не нужен текст  

Слабая сторона:

❌ не понимает смысл баннера  
❌ может путать похожие композиции  

---

### Qwen3-VL

Сильная сторона:

✅ понимает:
- логотипы;
- текст;
- композицию;
- смысл;
- элементы дизайна.

Слабая сторона:

❌ медленный;
❌ нельзя гонять по 300 фото × 1500 окон.

---

Получается идеальная архитектура:

```
                МАКЕТ
                  |
                  |
        -------------------
        |                 |
     быстрый поиск     LLM
       DINO             |
        |               |
        |               |
   топ-20 кандидатов    |
        |               |
        ----------------
                  |
                  |
            финальный ответ
```

---

## Следующий тест (самый важный)

Нужно проверить не один crop, а **папку test**.

Например:

```
data/input/test
    Ашхабадский_01.JPG
    Радиаторный_01.JPG
    Зорге_15.JPG
    ...
```

Делаем:

1. Берём один макет:

```
data/input/banners/видео_сизякин.jpg
```

2. Отправляем Qwen по очереди:

```
макет + фото №1
макет + фото №2
...
```

3. Получаем:

```
Ашхабадский_01.JPG       98%
Радиаторный_25.JPG       12%
Зорге_15.JPG             8%
...
```

Это уже настоящий тест поиска.

---

Но ещё лучше:

Перед LLM добавить дешёвый фильтр:

```
300 фото

 ↓

цветовой fingerprint

 ↓

50 кандидатов

 ↓

Qwen3-VL

 ↓

5 найденных
```

Тогда можно обрабатывать дневной фотоотчёт.

---

Следующий файл я бы сделал:

```
scripts/banner_llm_folder_search_v01.py
```

Функции:

- берет один макет из `data/input/banners`;
- перебирает `data/input/test`;
- сохраняет:

```
data/output/found_banners/
       видео_сизякин/
          Ашхабадский_01.json
          Ашхабадский_01.jpg
```

- сортирует по confidence.

Это уже будет первый рабочий прототип **поиска баннеров через Vision LLM**.

---

### 👤 **User** — 2026-08-16 01:31:21

давай

---

### 🤖 **Assistant** — 2026-08-16 01:31:22

Делаем первый рабочий прототип:

**Banner LLM Search v01**

Логика:

```text
data/input/banners/
        |
        |  (макет)
        v

Qwen3-VL

        ^
        |
data/input/test/
        |
        |-- фото1
        |-- фото2
        |-- фото3

        ↓

data/output/found_banners/
        |
        |-- имя_макета/
              |
              |-- результаты.json
              |-- найденные фото
```

Создаём файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nano scripts/banner_llm_folder_search_v01.py
```

Вставляем:

```python
#!/usr/bin/env python3

import base64
import io
import json
import shutil
import requests

from pathlib import Path
from PIL import Image
from tqdm import tqdm

MODEL = "qwen3-vl:4b-instruct"

BANNER_DIR = Path(
    "data/input/banners"
)

TEST_DIR = Path(
    "data/input/test"
)

OUTPUT_DIR = Path(
    "data/output/found_banners"
)

IMAGE_EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".JPG"
}

def encode_image(path, size=1280):

    img = Image.open(path)

    if img.mode != "RGB":
        img = img.convert("RGB")

    img.thumbnail(
        (size, size)
    )

    buf = io.BytesIO()

    img.save(
        buf,
        format="JPEG",
        quality=90
    )

    return base64.b64encode(
        buf.getvalue()
    ).decode()

def ask_llm(
    banner,
    photo
):

    prompt = """

Ты эксперт по наружной рекламе.

Сравни два изображения.

IMAGE 1:
оригинальный макет баннера.

IMAGE 2:
фотография улицы.

Определи:
есть ли этот же баннер
на фотографии.

Проверяй:
- логотип
- текст
- цвета
- расположение элементов
- композицию

Ответ строго JSON:

{
"match": true или false,
"confidence": число 0-100,
"reason": "описание"
}

"""

payload = {

        "model": MODEL,

        "stream": False,

        "messages": [

            {
                "role":"user",

                "content":prompt,

                "images":[

                    encode_image(banner),

                    encode_image(photo)

                ]

            }

        ]

    }

r = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=600
    )

r.raise_for_status()

text = r.json()["message"]["content"]

try:
        return json.loads(text)

    except:

        return {
            "match":False,
            "confidence":0,
            "reason":text
        }

def main():

OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

banner = next(
        BANNER_DIR.iterdir()
    )

out = OUTPUT_DIR / banner.stem

    out.mkdir(
        exist_ok=True
    )

photos = [

        x for x in TEST_DIR.iterdir()

        if x.suffix in IMAGE_EXT

    ]

results=[]

print()
    print("="*60)
    print("BANNER:")
    print(banner)
    print("PHOTOS:",len(photos))
    print("="*60)

for photo in tqdm(photos):

        try:

            result = ask_llm(
                banner,
                photo
            )

row={

                "photo":photo.name,

                **result

            }

results.append(row)

print(
                photo.name,
                result.get(
                    "confidence",
                    0
                )
            )

if (
                result.get("match")
                and
                result.get("confidence",0)>70
            ):

                shutil.copy2(
                    photo,
                    out / photo.name
                )

except Exception as e:

            print(
                "ERROR",
                photo,
                e
            )

results.sort(
        key=lambda x:
        x.get(
            "confidence",
            0
        ),
        reverse=True
    )

with open(
        out/"results.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

print()
    print("DONE")
    print(
        out
    )

if __name__=="__main__":

    main()
```

Запуск:

```bash
uv run python scripts/banner_llm_folder_search_v01.py
```

Мониторинг:

```bash
watch -n 1 nvidia-smi
```

---

Первый прогон лучше сделать на маленькой папке:

```bash
ls data/input/test | head
```

Потому что сейчас будет:

```
1 фото ≈ несколько секунд
100 фото ≈ несколько минут
```

После проверки добавим:

1. многопоточность по фото;
2. очередь GPU;
3. сохранение истории поиска;
4. интеграцию с DINO (гибридный режим).

Сейчас цель — проверить **находит ли Qwen3-VL реальные баннеры среди разных фото**, а не только прямое сравнение.

---

### 👤 **User** — 2026-08-16 01:51:01

DONE
data/output/found_banners/видео_сизякин

---

### 🤖 **Assistant** — 2026-08-16 01:51:04

Отлично. Первый полный прогон **LLM-only поиска** завершился.

Теперь надо посмотреть качество, а не скорость.

Проверяем результаты:

```bash
cat data/output/found_banners/видео_сизякин/results.json
```

или удобнее:

```bash
python -m json.tool data/output/found_banners/видео_сизякин/results.json | less
```

И список реально найденных фото:

```bash
ls -lah data/output/found_banners/видео_сизякин
```

Ожидаем структуру:

```text
видео_сизякин/
├── results.json
├── Ашхабадский_01.JPG
├── ...
```

Самое важное сейчас:

1. **Есть ли среди скопированных файлов:**

```text
Ашхабадский_01.JPG
```

2. Какие confidence у первых результатов.

Нужно увидеть примерно:

```json
[
  {
    "photo": "Ашхабадский_01.JPG",
    "match": true,
    "confidence": 98,
    "reason": "..."
  }
]
```

---

Если это подтвердится, то у нас уже есть два рабочих режима:

### Режим A — массовое распознавание адресов

```text
DINO fingerprint
↓
быстро
↓
юридический адрес
```

### Режим B — поиск конкретного баннера

```text
макет
↓
Qwen3-VL
↓
фото с этим баннером
```

---

Следующий шаг после просмотра JSON я бы сделал **v02**:

- сохранять не только найденные фото, но и `confidence`;
- создавать HTML-отчёт с превью;
- сортировать:

```
99-90%
80-90%
70-80%
```

Потому что для отдела рекламы это будет намного удобнее, чем смотреть JSON.

Сейчас пришлите первые ~30 строк `results.json` и список файлов в папке результата.

---

### 👤 **User** — 2026-08-16 01:56:31

баннера он опознал только в нескольких случаях - остальное - шум. Может быть делать прогон нейросетки сразу после алгоритма распознавния слепков и переименования фотоотчета за день. Неросеть сделает описание поподробнее и сохранит в базу, например будет действовать по алгоитму - описать баннер (клиент, даты, цвет, что изображено, любой текст, который можно получить). При поступлении задания (если это просто текст - найди макеты Сбера , то ищет макеты по базе с текстом Сбер), если это изображениме - по такому же алгоритму описывает баннер и ищет схождения в базе. Если находит - берет фото и копирует его в результат

---

### 🤖 **Assistant** — 2026-08-16 01:56:32

Да, вот это уже гораздо более правильная архитектура. Фактически мы пришли к тому, что **Vision LLM не должна искать по всему архиву напрямую**. Она должна работать как **индексатор и эксперт**, а поиск делать по подготовленной базе.

То, что получилось сейчас:

```text
макет → Qwen3-VL → 300 фото
```

неэффективно.

Qwen видит хорошо, но не знает, где искать. Поэтому получает много шума.

Лучше:

```text
                ФОТООТЧЕТ ДНЯ
                     |
                     |
              DINO распознавание
              (адрес / слепок)
                     |
                     |
              переименование фото
                     |
                     |
          +----------+----------+
          |
          v
    Vision LLM анализ
          |
          |
    база описаний баннеров
```

---

## Новая дорожная карта №2 (поиск баннеров)

### Этап 1. Построение базы баннеров

После твоего текущего процесса:

```text
200-300 фото в день

↓

распознаны адреса:

Ашхабадский_01.JPG
Радиаторный_25.JPG
...
```

запускается отдельный индексатор.

Для каждого фото:

### Vision LLM делает описание:

Например:

```json
{
"id":"Ашхабадский_01",

"client":"BetCity",

"type":"наружный баннер",

"colors":[
"синий",
"белый",
"красный"
],

"text":[
"BetCity",
"Ставки на спорт",
"2026"
],

"objects":[
"мужчина",
"футбольный мяч",
"логотип"
],

"layout":
"логотип справа, человек слева",

"date_visible":
"2026",

"embedding":
"..."
}
```

---

Эта информация сохраняется:

например:

```
data/banner_database/

    banners.json

    images/

        Ашхабадский_01.JPG

    embeddings/

        qwen_embedding.npy
```

---

## Этап 2. Поиск по тексту

Запрос:

> "найди Сбер"

Не нужен Vision.

Ищем:

```text
SQLite / JSON

WHERE text LIKE '%Сбер%'
```

Результат:

```
Сбербанк
Сбер
СберKids
```

---

## Этап 3. Поиск по изображению

Пользователь кидает макет:

```
new_banner.jpg
```

Дальше:

Vision LLM:

создаёт описание:

```json
{
"text":"Сбер",
"colors":"зеленый",
"objects":"человек",
"layout":"логотип сверху"
}
```

Дальше:

поиск:

1. текстовый индекс;
2. цвет;
3. embedding;
4. финальная проверка Qwen.

---

То есть:

```text
новый макет

      |
      v

Qwen описание

      |
      +---- текстовый поиск
      |
      +---- цветовой поиск
      |
      +---- embedding поиск

              |
              v

          топ 10

              |
              v

          Qwen verifier

              |
              v

          результат
```

---

## Почему это лучше

Сейчас:

```
1 макет
×
10000 фотографий
×
Vision LLM
```

= тяжело.

Новая схема:

Один раз:

```
10000 фото
×
Vision LLM
```

Создали базу.

Потом:

```
любой запрос
=
миллисекунды поиска
+
несколько проверок
```

---

## И самое интересное

У тебя уже есть половина системы:

Готово:

✅ DINOv2 распознавание адресов  
✅ автоматическая сортировка  
✅ структура фотоархива  

Остаётся добавить:

1. `banner_analyzer.py`

который после сортировки делает описания.

2. `banner_db.py`

SQLite база:

```
id
photo
address
client
text
colors
objects
embedding
date
```

3. `banner_search.py`

поиск.

---

Я бы сейчас **не продолжал развивать LLM-only поиск**. Этот эксперимент был полезен: он показал, что Qwen3-VL хорошо понимает баннер, но плохо подходит как массовый поисковик.

Следующий правильный шаг:

**Banner Database v01**

Сделать скрипт, который берет уже распознанную папку `test`, прогоняет через `qwen3-vl:4b-instruct` и создаёт первый JSON/SQLite каталог баннеров.

Это будет фундамент для настоящего поиска.

---

### 👤 **User** — 2026-08-16 01:57:57

давай

---

### 🤖 **Assistant** — 2026-08-16 01:57:58

Отлично. Тогда делаем **Banner Database v01**.

Цель первой версии:

После твоего текущего распознавания:

```text
data/input/test

Ашхабадский_01.JPG
Радиаторный_25.JPG
Зорге_15.JPG
...
```

запускаем индексатор:

```text
Фото
 |
 v
Qwen3-VL
 |
 v
описание баннера
 |
 v
SQLite база
```

На выходе:

```text
data/banner_database/

banner.db
images/
descriptions/
```

---

## Что будет храниться

Таблица `banners`:

| поле | пример |
|-|-|
| file | Ашхабадский_01.JPG |
| address | Ашхабадский |
| client | BetCity |
| text | Ставки на спорт |
| colors | синий белый красный |
| objects | человек, мяч |
| description | полный текст |
| created | дата |

---

Создаём файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nano scripts/banner_database_v01.py
```

Вставляем:

```python
#!/usr/bin/env python3

import base64
import io
import json
import sqlite3
import requests

from pathlib import Path
from PIL import Image
from tqdm import tqdm

MODEL = "qwen3-vl:4b-instruct"

INPUT_DIR = Path(
    "data/input/test"
)

DB_PATH = Path(
    "data/banner_database/banner.db"
)

EXT = {
    ".jpg",
    ".jpeg",
    ".JPG",
    ".png"
}

def init_db():

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    con = sqlite3.connect(
        DB_PATH
    )

    cur = con.cursor()

    cur.execute(
    """
    CREATE TABLE IF NOT EXISTS banners
    (
        id INTEGER PRIMARY KEY,

        file TEXT UNIQUE,

        client TEXT,

        text TEXT,

        colors TEXT,

        objects TEXT,

        description TEXT
    )
    """
    )

    con.commit()

    return con

def encode_image(path):

    img = Image.open(path)

    if img.mode!="RGB":
        img=img.convert("RGB")

img.thumbnail(
        (1280,1280)
    )

buf=io.BytesIO()

    img.save(
        buf,
        format="JPEG",
        quality=90
    )

return base64.b64encode(
        buf.getvalue()
    ).decode()

def analyze(path):

prompt="""

Ты анализируешь фотографию наружной рекламы.

Создай описание баннера.

Извлеки:

- клиент / бренд
- весь читаемый текст
- цвета
- объекты
- людей
- логотипы
- подробное описание композиции

Если информации нет,
пиши unknown.

Ответ строго JSON:

{
"client":"",
"text":"",
"colors":"",
"objects":"",
"description":""
}

"""

payload={

        "model":MODEL,

        "stream":False,

        "messages":[

            {

            "role":"user",

            "content":prompt,

            "images":[
                encode_image(path)
            ]

            }

        ]

    }

r=requests.post(

        "http://localhost:11434/api/chat",

        json=payload,

        timeout=600

    )

r.raise_for_status()

answer=r.json()["message"]["content"]

try:
        return json.loads(answer)

    except:

        return {

        "client":"",
        "text":"",
        "colors":"",
        "objects":"",
        "description":answer

        }

def main():

con=init_db()

    cur=con.cursor()

photos=[

        x for x in INPUT_DIR.iterdir()

        if x.suffix in EXT

    ]

print(
        "FILES:",
        len(photos)
    )

for photo in tqdm(photos):

cur.execute(
            "SELECT id FROM banners WHERE file=?",
            (photo.name,)
        )

if cur.fetchone():

            continue

try:

            data=analyze(photo)

cur.execute(
            """
            INSERT INTO banners
            (
            file,
            client,
            text,
            colors,
            objects,
            description
            )

            VALUES (?,?,?,?,?,?)

            """,

            (

            photo.name,

            data.get("client",""),

            data.get("text",""),

            data.get("colors",""),

            data.get("objects",""),

            data.get("description","")

            )

            )

con.commit()

print(
                "\n",
                photo.name
            )

            print(
                data
            )

except Exception as e:

            print(
                "ERROR",
                photo,
                e
            )

con.close()

print(
        "\nDONE"
    )

    print(
        DB_PATH
    )

if __name__=="__main__":

    main()
```

---

Запуск:

```bash
uv run python scripts/banner_database_v01.py
```

Проверка базы:

```bash
sqlite3 data/banner_database/banner.db
```

Внутри:

```sql
.tables

select file,client,text from banners;
```

---

Первый тест я бы сделал не на всех фото, а на 10:

```bash
mkdir data/input/test10

cp data/input/test/*.JPG data/input/test10/
```

и поменять:

```python
INPUT_DIR = Path(
    "data/input/test10"
)
```

Потому что сейчас каждая фотография = запрос к Qwen.

---

После создания базы следующий шаг будет **Banner Search v02**:

Запрос:

```
Сбер зеленый баннер
```

или:

```
загружаю макет.jpg
```

и он ищет уже по базе, а не гоняет нейросеть по всему архиву.

---

### 👤 **User** — 2026-08-16 01:59:20

0%|                                                  | 0/257 [00:00<?, ?it/s]ERROR data/input/test/Стачки_41_01.JPG Error binding parameter 4: type 'list' is not supported
  0%|▏                                         | 1/257 [00:09<38:47,  9.09s/it]ERROR data/input/test/Малиновского_к_Стачки_05.JPG Error binding parameter 4: type 'list' is not supported
  1%|▎                                         | 2/257 [00:14<28:47,  6.77s/it]

---

### 🤖 **Assistant** — 2026-08-16 01:59:21

Отлично, это хороший знак — сама связка **Qwen3-VL → JSON → SQLite** работает. Ошибка уже не в модели, а в формате данных.

Причина:

Qwen иногда возвращает поля не строками, а списками.

Например:

```json
{
 "colors": [
   "зеленый",
   "белый",
   "черный"
 ]
}
```

А SQLite ожидает:

```text
"зеленый, белый, черный"
```

Поэтому:

```
Error binding parameter 4: type 'list' is not supported
```

Параметр 4 как раз `colors`.

---

Исправляем универсально: все поля перед записью приводим к строке.

В файле:

```bash
nano scripts/banner_database_v01.py
```

найдите место:

```python
cur.execute(
"""
INSERT INTO banners
(
file,
client,
text,
colors,
objects,
description
)

VALUES (?,?,?,?,?,?)

""",

(
photo.name,

data.get("client",""),

data.get("text",""),

data.get("colors",""),

data.get("objects",""),

data.get("description","")

)

)
```

замените на:

```python
def to_text(value):

    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(
            str(x) for x in value
        )

    if isinstance(value, dict):
        return json.dumps(
            value,
            ensure_ascii=False
        )

    return str(value)
```

и ниже:

```python
cur.execute(
"""
INSERT INTO banners
(
file,
client,
text,
colors,
objects,
description
)

VALUES (?,?,?,?,?,?)

""",

(
photo.name,

to_text(data.get("client")),

to_text(data.get("text")),

to_text(data.get("colors")),

to_text(data.get("objects")),

to_text(data.get("description"))

)

)
```

---

Ещё я бы добавил защиту от следующей типичной проблемы: Qwen может вернуть JSON в markdown:

```text
```json
{
...
}
```
```

Тогда `json.loads()` упадёт.

Замените:

```python
try:
    return json.loads(answer)
```

на:

```python
try:

    answer = answer.replace(
        "```json",
        ""
    ).replace(
        "```",
        ""
    ).strip()

    return json.loads(answer)

```

---

После исправления базу лучше удалить и пересоздать:

```bash
rm -f data/banner_database/banner.db
```

и снова:

```bash
uv run python scripts/banner_database_v01.py
```

---

Кстати, скорость у вас получилась:

```
9 секунд / фото
```

Это нормально для Qwen3-VL 4B на RTX 3060.

257 фото:

примерно:

```
35-40 минут
```

Но это одноразовое создание индекса.

Дальше поиск будет занимать секунды.

Следующий этап после успешного заполнения базы — сделаем:

```
banner_search_v01.py

"найди Сбер"
        ↓
SQLite full text search

"найди этот макет"
        ↓
Qwen описание
        ↓
поиск по базе
        ↓
копирование найденных фото
```

То есть уже получится полноценный архивный поиск баннеров.

---

### 👤 **User** — 2026-08-16 01:59:52

давай готовый

---

### 🤖 **Assistant** — 2026-08-16 01:59:53

Делаем готовую замену: **`banner_database_v02.py`**.

Изменения относительно v01:

✅ исправлены списки (`colors`, `objects`, `text`)  
✅ защита от markdown JSON от Qwen  
✅ пропуск уже обработанных фото  
✅ нормальная запись в SQLite  
✅ сохранение полного ответа LLM  
✅ устойчивость к разным форматам ответа  

Создайте файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nano scripts/banner_database_v02.py
```

Вставьте полностью:

```python
#!/usr/bin/env python3

import base64
import io
import json
import sqlite3
import requests

from pathlib import Path
from PIL import Image
from tqdm import tqdm

MODEL = "qwen3-vl:4b-instruct"

INPUT_DIR = Path(
    "data/input/test"
)

DB_PATH = Path(
    "data/banner_database/banner.db"
)

EXT = {
    ".jpg",
    ".jpeg",
    ".JPG",
    ".png"
}

def to_text(value):

    if value is None:
        return ""

    if isinstance(value, list):

        return ", ".join(
            str(x)
            for x in value
        )

    if isinstance(value, dict):

        return json.dumps(
            value,
            ensure_ascii=False
        )

    return str(value)

def clean_json(text):

    text = text.strip()

    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    return text.strip()

def init_db():

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

con = sqlite3.connect(
        DB_PATH
    )

cur = con.cursor()

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS banners
    (
        id INTEGER PRIMARY KEY,

        file TEXT UNIQUE,

        client TEXT,

        text TEXT,

        colors TEXT,

        objects TEXT,

        description TEXT,

        raw_json TEXT

    )
    """
    )

con.commit()

return con

def encode_image(path):

    img = Image.open(path)

if img.mode != "RGB":

        img = img.convert(
            "RGB"
        )

img.thumbnail(
        (1280,1280)
    )

buf = io.BytesIO()

img.save(
        buf,
        format="JPEG",
        quality=90
    )

return base64.b64encode(
        buf.getvalue()
    ).decode()

def analyze(path):

prompt = """

Ты анализируешь фотографию наружной рекламы.

Определи:

1. бренд или клиента
2. весь читаемый текст
3. цвета
4. объекты на баннере
5. людей
6. логотипы
7. подробное описание композиции

Если данных нет, напиши unknown.

Ответ строго JSON:

{
"client":"",
"text":"",
"colors":[],
"objects":[],
"description":""
}

"""

payload = {

        "model": MODEL,

        "stream": False,

        "messages":
        [

            {

            "role":"user",

            "content":prompt,

            "images":
            [
                encode_image(path)
            ]

            }

        ]

    }

r = requests.post(

        "http://localhost:11434/api/chat",

        json=payload,

        timeout=600

    )

r.raise_for_status()

answer = r.json()[
        "message"
    ][
        "content"
    ]

answer = clean_json(
        answer
    )

try:

        return json.loads(
            answer
        )

except Exception:

return {

            "client":"",
            "text":"",
            "colors":[],
            "objects":[],
            "description":answer

        }

def main():

    con = init_db()

    cur = con.cursor()

photos = [

        x for x in INPUT_DIR.iterdir()

        if x.suffix in EXT

    ]

print(
        "FILES:",
        len(photos)
    )

for photo in tqdm(
        photos
    ):

cur.execute(

            "SELECT id FROM banners WHERE file=?",

            (
                photo.name,
            )

        )

if cur.fetchone():

            continue

try:

            data = analyze(
                photo
            )

cur.execute(
            """
            INSERT INTO banners
            (
            file,
            client,
            text,
            colors,
            objects,
            description,
            raw_json
            )

            VALUES (?,?,?,?,?,?,?)

            """,

            (

            photo.name,

            to_text(
                data.get("client")
            ),

            to_text(
                data.get("text")
            ),

            to_text(
                data.get("colors")
            ),

            to_text(
                data.get("objects")
            ),

            to_text(
                data.get("description")
            ),

            json.dumps(
                data,
                ensure_ascii=False
            )

            )

            )

con.commit()

except Exception as e:

            print()

            print(
                "ERROR:",
                photo
            )

            print(
                e
            )

con.close()

print()
    print(
        "DONE"
    )

    print(
        DB_PATH
    )

if __name__=="__main__":

    main()
```

---

Перед повторным запуском удалить битую базу:

```bash
rm -f data/banner_database/banner.db
```

Запуск:

```bash
uv run python scripts/banner_database_v02.py
```

Проверка:

```bash
sqlite3 data/banner_database/banner.db
```

Внутри:

```sql
.tables

select file,client,text,colors from banners limit 10;
```

---

После того как база заполнится, следующий шаг будет уже **Banner Search v01**:

- запрос текстом:
  ```
  Сбер зеленый баннер
  ```

- запрос картинкой:
  ```
  макет.jpg
  ```

и выдача:

```
Ашхабадский_01.JPG
score 96%
→ копировать в found_banners/
```

То есть уже не перебор 257 фото через LLM, а поиск по индексу.

---

### 👤 **User** — 2026-08-16 02:21:52

DONE
data/banner_database/banner.db
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sqlite3 data/banner_database/banner.db
SQLite version 3.45.1 2024-01-30 16:01:20
Enter ".help" for usage hints.
sqlite> .tables

select file,client,text,colors from banners limit 10;
sqlite>

---

### 🤖 **Assistant** — 2026-08-16 02:21:54

Отлично, база создалась:

```text
DONE
data/banner_database/banner.db
```

Но вот этот момент:

```sql
sqlite> .tables

select file,client,text,colors from banners limit 10;
sqlite>
```

показывает, что **таблиц нет или они пустые**.

Скорее всего причина одна из двух:

1. SQLite база создана, но `CREATE TABLE` не выполнился (маловероятно).
2. Скрипт не добавил ни одной записи (скорее всего).

Проверяем.

В sqlite выполните:

```sql
.tables
```

Должно быть:

```text
banners
```

Если пусто — проверяем структуру:

```sql
.schema
```

---

Проверим количество записей:

```sql
select count(*) from banners;
```

Ожидаю:

```text
257
```

Если:

```text
0
```

значит цикл прошёл, но вставка не произошла.

---

Ещё полезно посмотреть последние сообщения запуска. Повторите:

```bash
uv run python scripts/banner_database_v02.py
```

В начале должно быть:

```text
FILES: 257
```

и дальше индикатор:

```text
100%|████████████████████| 257/257
```

Но в норме он должен создавать записи.

---

Есть ещё один момент: в v02 я добавил пропуск уже обработанных:

```python
SELECT id FROM banners WHERE file=?
```

Если база создавалась во время первого неудачного запуска, она могла остаться пустой, но это легко проверить.

Сейчас в sqlite выполните:

```sql
.schema banners;
```

и:

```sql
select count(*) from banners;
```

Пришлите вывод.

Если таблица пустая — сделаем маленький фикс с выводом каждого результата Qwen:

```text
Ашхабадский_01.JPG
client: BetCity
text: ...
```

и сразу увидим, где остановилось.

---

### 👤 **User** — 2026-08-16 02:22:37

/banner.db
SQLite version 3.45.1 2024-01-30 16:01:20
Enter ".help" for usage hints.
sqlite> .tables

select file,client,text,colors from banners limit 10;
sqlite> сизякин
   ...> .tables
   ...> .schema
   ...> select count(*) from banners;
Parse error: near "сизякин": syntax error
  сизякин .tables .schema select count(*) from banners;
  ^--- error here
sqlite>

---

### 🤖 **Assistant** — 2026-08-16 02:22:38

Вы просто случайно ввели текст `сизякин` прямо в консоль SQLite 🙂. SQLite воспринял это как часть SQL-команды и поэтому выдал:

```text
Parse error: near "сизякин"
```

Сейчас вы всё ещё внутри sqlite.

Введите по очереди **только команды**:

```sql
.tables
```

потом:

```sql
.schema banners
```

потом:

```sql
select count(*) from banners;
```

---

Если таблица есть и всё хорошо, должно быть примерно:

```text
sqlite> .tables
banners

sqlite> select count(*) from banners;
257
```

Потом проверим данные:

```sql
select file,client,text,colors from banners limit 10;
```

---

Если `.tables` ничего не покажет — значит база создана, но таблица не появилась.

Если покажет `banners`, но `count(*)` даст `0` — значит Qwen не записал результаты.

Пришлите вывод этих трёх команд.

---

### 👤 **User** — 2026-08-16 02:23:45

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sqlite3 data/banner_database/banner.db
SQLite version 3.45.1 2024-01-30 16:01:20
Enter ".help" for usage hints.
sqlite> .tables

select file,client,text,colors from banners limit 10;
sqlite> сизякин
   ...> .tables
   ...> .schema
   ...> select count(*) from banners;
Parse error: near "сизякин": syntax error
  сизякин .tables .schema select count(*) from banners;
  ^--- error here
sqlite> .tables
banners
sqlite> .schema banners
CREATE TABLE banners
    (
        id INTEGER PRIMARY KEY,

        file TEXT UNIQUE,

        client TEXT,

        text TEXT,

        colors TEXT,

        objects TEXT,

        description TEXT,

        raw_json TEXT

    );
sqlite> select count(*) from banners;
257
sqlite> select file,client,text,colors from banners limit 10;
Стачки_41_01.JPG|EMBARGO|КОНЦЕРТ САМЫХ ВАЖНЫХ ШАНСОН ГОДА ИРИНА КРУГ- ЖЕКА, БОРТИНЬ ЗИНОВИЧ, АНАТОЛИЙ ПОЛОТОНОВ И БЕДА МАРМАКОВ. 28 АВГУСТА ВОРОВАНИКИ. БИЛЕТЫ: EMBARGOVILLA.RU|black, white, red
Малиновского_к_Стачки_05.JPG|unknown|НАДЕЖНЫЕ АККУМУЛЯТОРЫ
НА ЛЮБУЮ ТЕХНИКУ
БЕСПЛАТНАЯ ДОСТАВКА И УСТАНОВКА
8 800 550 15 88

НАРОДНАЯ ПРОГРАММА
СКАЗАНО —
СДЕЛАНО!
|red, blue, white
Малиновского_к_Доватора_15.JPG|бобренок|СКИДКИ ДО 25% 
Высокое Маркет
greenworks
ЛЕНЕМ ТАК, ЧТО ПОТОМ ХОЧЕТСЯ УПЫВАТЬСЯ|red, white, brown
Радиаторный_05.JPG|Resurs|ЧОКЕП RESURS
1350₽
3-5 МАРТЯ
Маркет|red, white, black
Добровольского17_07.JPG|Бетсити|БЕТСИТИ
СУПЕРЛГА ПО ФУТЗАЛУ|blue, white, black
Зорге_02.JPG|ВРЕМЯ|Единоразовая выплата
3.700.000
ВРЕМЯ
новых
побед
контракт61.pdf
8 (838) 1-555-599

2026
БАЙКО
АНДРЭ
МАТВ|blue, white, black, red, gray
Вавилова52_12.JPG|Ozon Fresh|189₽
БЕДРО ПО-КАВКАЗУ
Озон fresh
ООО «Интернет-реклама»
всё с агрокомпанией, тракторами и молоком — от 3 до 10% в год.
Полюс побежден. Дары познания.
Сотрудникам, которые хотят поднимать уровень.|pink, cyan
Малиновского(_05.JPG|||
Стачки_41_03.JPG|Ozon fresh|269 Р
ФИЛЕ ГРУДКИ
1 кг
БлагоЯр
OZON
fresh
ПОЛУЧАЙТЕ ПРОМОКОДЫ:
— на любой товар,
— на оплату доставки.
ЗАПРЕЩЕННЫЕ ОТВЕТЫ —
по всем вопросам и
предложениям: 8-800-500-77-96.|pink, light blue, white, red, black
Малиновского_к_Доватора_06.JPG|||
sqlite>

---

### 🤖 **Assistant** — 2026-08-16 02:23:47

Отлично. Это уже **рабочая база**. 👍

Получили ровно то, что планировали:

```text
257 фото
↓
Qwen3-VL
↓
SQLite
↓
описания баннеров
```

И главное — качество извлечения уже видно:

Примеры:

```
Добровольского17_07.JPG
client: Бетсити
text:
БЕТСИТИ
СУПЕРЛИГА ПО ФУТЗАЛУ

colors:
blue, white, black
```

```
Вавилова52_12.JPG
client:
Ozon Fresh

text:
189₽
БЕДРО ПО-КАВКАЗУ
...
```

То есть база уже пригодна для поиска.

---

Теперь следующий шаг — **Banner Search v01**.

Логика:

## Вариант 1. Текстовый поиск

Например:

```
найти Бетсити
```

или:

```
найти баннеры Ozon
```

Идёт запрос:

```sql
WHERE client LIKE '%Ozon%'
OR text LIKE '%Ozon%'
```

Результат:

```
1. Добровольского17_07.JPG
2. ...
```

---

## Вариант 2. Поиск по макету

Загружаем:

```
data/input/banners/видео_сизякин.jpg
```

Дальше:

```
макет
 |
 |
 Qwen3-VL
 |
 описание:
 
client: Бетсити
colors:
blue white black

text:
БЕТСИТИ
СУПЕРЛИГА
 |
 |
 SQLite поиск
 |
 |
 top 10 кандидатов
 |
 |
 Qwen проверяет
 |
 |
 копирование результата
```

---

## Но я бы добавил ещё один слой

Сейчас база:

```json
текст
цвет
описание
```

Нужно добавить:

### embedding описания

Например:

```
"Бетсити синий спортивный баннер человек футбол"
```

превратить в вектор.

Тогда поиск:

```
"синий футбольный баннер"
```

найдёт:

```
БЕТСИТИ
```

даже если слово Бетсити не написано.

Для этого идеально подходит твой уже установленный:

```
bge-m3
```

или можно использовать DINO.

---

Я предлагаю следующий порядок:

### Banner Search v01

Сделать сейчас:

✅ поиск по тексту  
✅ поиск по клиенту  
✅ поиск по цветам  
✅ вывод найденных фото  
✅ копирование в:

```
data/output/found_banners/<название поиска>/
```

---

### Banner Search v02

Добавить:

✅ описание макета через Qwen  
✅ сравнение описаний  
✅ поиск похожих баннеров

---

### Banner Search v03

Интеграция:

```
DINO распознал адрес
        |
        |
257 фото дня
        |
        |
Qwen индексатор
        |
        |
banner.db
        |
        |
поиск отдела рекламы
```

---

Сейчас база уже готова. Следующий файл предлагаю сделать:

```
scripts/banner_search_v01.py
```

с интерфейсом:

```bash
python banner_search_v01.py "Бетсити"
```

и выводом:

```
FOUND:

1.
Добровольского17_07.JPG
client: Бетсити
score: 100%

copy:
data/output/found_banners/Бетсити/
```

Это будет первый настоящий поисковик по архиву.

---

### 👤 **User** — 2026-08-16 02:24:34

sqlite> WHERE client LIKE '%Ozon%'
OR text LIKE '%Ozon%'
   ...>

---

### 🤖 **Assistant** — 2026-08-16 02:24:35

Вы сейчас снова в SQLite, но ввели только условие `WHERE`. Само по себе оно не является SQL-запросом — ему нужен `SELECT`.

Введите так:

```sql
SELECT file, client, text
FROM banners
WHERE client LIKE '%Ozon%'
   OR text LIKE '%Ozon%';
```

Должны появиться найденные фото, например:

```text
Вавилова52_12.JPG|Ozon Fresh|189₽ БЕДРО ПО-КАВКАЗУ...
Стачки_41_03.JPG|Ozon fresh|269 Р ФИЛЕ ГРУДКИ...
```

---

Ещё полезные проверки базы:

### Найти Бетсити:

```sql
SELECT file, client, text
FROM banners
WHERE client LIKE '%Бет%'
   OR text LIKE '%БЕТ%';
```

### Найти все уникальные клиенты:

```sql
SELECT DISTINCT client
FROM banners
ORDER BY client;
```

### Найти всё, где есть слово "баннер" в описании:

```sql
SELECT file, description
FROM banners
WHERE description LIKE '%баннер%';
```

---

Сейчас мы фактически вручную проверяем, что индекс работает. Следующий шаг — вынести это в `banner_search_v01.py`, чтобы менеджер не заходил в SQLite, а просто писал:

```bash
./banner_search.py "Ozon"
```

или через веб-интерфейс.

---

### 👤 **User** — 2026-08-16 02:24:58

sqlite> WHERE client LIKE '%Ozon%'
OR text LIKE '%Ozon%'
   ...> SELECT file, client, text
FROM banners
WHERE client LIKE '%Ozon%'
   OR text LIKE '%Ozon%';
Parse error: near "WHERE": syntax error
  WHERE client LIKE '%Ozon%' OR text LIKE '%Ozon%' SELECT file, client, text FRO
  ^--- error here
sqlite>

---

### 🤖 **Assistant** — 2026-08-16 02:25:00

Ошибка из-за того, что предыдущая команда `WHERE ...` осталась незавершённой. SQLite уже был в режиме продолжения:

```text
...>
```

и потом вы добавили новый `SELECT`, получилось:

```sql
WHERE ...
SELECT ...
```

Это невалидно.

Сначала сбросьте незаконченный ввод:

Нажмите:

```
Ctrl+C
```

Должно появиться снова:

```text
sqlite>
```

Теперь вводите **целиком одним блоком**:

```sql
SELECT file, client, text
FROM banners
WHERE client LIKE '%Ozon%'
   OR text LIKE '%Ozon%';
```

Или в одну строку:

```sql
SELECT file,client,text FROM banners WHERE client LIKE '%Ozon%' OR text LIKE '%Ozon%';
```

---

На будущее в SQLite:

- `sqlite>` — ждёт новую команду
- `...>` — ждёт продолжение текущей команды

Если случайно попали в `...>` — почти всегда проще нажать:

```
Ctrl+C
```

и начать заново.

---

### 👤 **User** — 2026-08-16 02:26:56

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sqlite3 data/banner_database/banner.db
SQLite version 3.45.1 2024-01-30 16:01:20
Enter ".help" for usage hints.
sqlite> SELECT file, client, text
FROM banners
WHERE client LIKE '%Ozon%'
   OR text LIKE '%Ozon%';
Вавилова52_12.JPG|Ozon Fresh|189₽
БЕДРО ПО-КАВКАЗУ
Озон fresh
ООО «Интернет-реклама»
всё с агрокомпанией, тракторами и молоком — от 3 до 10% в год.
Полюс побежден. Дары познания.
Сотрудникам, которые хотят поднимать уровень.
Стачки_41_03.JPG|Ozon fresh|269 Р
ФИЛЕ ГРУДКИ
1 кг
БлагоЯр
OZON
fresh
ПОЛУЧАЙТЕ ПРОМОКОДЫ:
— на любой товар,
— на оплату доставки.
ЗАПРЕЩЕННЫЕ ОТВЕТЫ —
по всем вопросам и
предложениям: 8-800-500-77-96.
Малиновского(_08.JPG|Ozon fresh|249Р
ВЕТКИНА ДЛЯ ЗАВТРАКА
OZON fresh
6+
Комарова13_16.JPG|Ozon|199₽ СЫР ГАУДА ПРЕМИУМ
Сыр Антон, 2017
OZON fresh
Рубиновый_05.JPG|OZON fresh|ООО «Интернет-Решения» (г. Зеленый, Россия), ГУДЗЕНСКИЙ ПЛ. Д. 10
37 АТ ПОМ. СВОБ. ЛУГА, В ТОРГОВЫХ ОТЕЛОНАХ
Комарова13_09.JPG|Самокат|199 ₽ -40% 337
Особенности кормления Двигательный топт

OZON fresh 6+
Предназначен для детей старше 6 лет.
Карточные батончики с чистым вкусом и привлекательным внешним видом.
Зорге_08.JPG|hot&fresh by ozon fresh|2026 ГОД АМ. БАЙКОВА в Ростове-на-Дону
БАЙКОВ
АНДЕРЁЙ
МАТВЕЕВИЧ
Рубиновый_02.JPG|Ozon|259 ₽
СОФРЕЛЬ СЛАДОСТОПЕНАЯ
Напиток, 500 г.
OZON fresh

Шеболдаева8_16.JPG|Ozon Fresh|399Р
ПЕЛЬМЕНИ
НАМИ!
Онлайн-магазин
Свежие пельмени от OZON FRESH
Самый вкусный выбор
OZON fresh
Заказать сейчас
www.ozon.ru
Зорге_06.JPG|hot&fresh by ozon fresh|2026 ГОД АЛЕКСАНДРА БАЙКОВА в Ростове-на-Дону
БАЙКОВ АНДРЕЙ МАТВЕЕВИЧ
ПРИ ПОДДЕРЖКЕ СТРОИТЕЛЬНОЙ КОМПАНИИ
СК10
Малиновского(_10.JPG|Ozon|OZON
fresh
ООО «АРТУМ» ПРОДУКЦИЯ: ОВОЩИ, ФРЕШ-ПРОДУКТЫ, КУРИНЫЕ ПОСТРОЙКИ, И Т.Д.

Вавилова52_15.JPG|Ozon fresh|49 Р
МОРОЖЕНОЕ
OZON fresh
6+
Стачки_41_02.JPG|Ozon|OOO «Интернет-релейн»: 123/2, г. Москва, Проспект Гагарина, д. 40. 
Тел. (495) 778-26-04.
Добровольского17_01.JPG|Ozon Bank|Кредитная карта до 140 дней
ОЦЕНИВАЙТЕ СВОИ ФИНАНСОВЫЕ ВОЗМОЖНОСТИ И ДЕНЬ КАК МИНУТ. УДИЛИВШИЕ РАЗРЯДЫ ПРОДУКТОВ В ЭЛЕГАНТНЫХ ЦЕНИКАХ.
Зорге_12.JPG|Ozon|119 Р
КОЛБАСА ВАРЁНАЯ
Ozon fresh
6+
Комарова13_17.JPG|Ozon|OZON fresh
ЛОД-КУЛТУРПЕТ ПИЛЕМНИК - СЦИПА, ГОРОДА, ЛЮБОЙ КРАСНЫХ ОТВЕТОВ. А. И.
38 42 ТОМ. I ЕДНАЯ Б У ДИ ПО137705453
ПОВЕРХНОСТЬ ЧДЕСЬ
Малиновского(_15.JPG|OZON fresh|199 ₽
СЫР ГАВДА
ПРЕМИУМ
OZON fresh
• Матрацы
• Möbel
• Oberbetten
• Heimtextilien
• Gartenmöb
Qualität sehr preiswert.
Комарова13_01.JPG|Ozon Fresh|OZON
fresh
СКИДКА
20% — СЕЙЧАС
204.45 → 163.64
ВНИМАНИЕ: 
ОБНОВЛЕНЫЕ ПРЕДЛОЖЕНИЯ! 
ПРОДУКТЫ ОЗОН FRESH - БУДЬТЕ В СИСТЕМЕ!
Малиновского(_06.JPG|ozon fresh|249Р КЛУБНИКА
ozon
fresh
Комарова13_12.JPG|Ozon fresh|ОБЪЕДИНЯЕМ ТЕХ, КТО СОЗДАЕТ БУДУЩЕЕ! КВАС ПОДКЛЮЧИТЕ МАГАЗИН
sqlite>

---

