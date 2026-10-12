## СЕССИЯ: Использование первого кандидата

**Создано:** 2026-08-14 23:31:05
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f7b07-8df4-83ea-be86-b71f888d7beb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f7b07-8df4-83ea-be86-b71f888d7beb)

---

### 🤖 **Assistant** — 2026-08-15 00:46:24

Да, тогда **84 нельзя считать плохим слепком только потому, что внутри него большой разброс ракурсов**. Это принципиально меняет оценку.

Наоборот, для нашего проекта это полезный fingerprint: один адрес должен быть представлен **разными ракурсами**, чтобы новая фотография могла совпасть с ним независимо от направления съёмки.

### Что тогда нужно изменить

Сейчас у нас есть потенциальная проблема в логике слепка:

```python
centroid = embeddings.mean(axis=0)
```

То есть все 54 фотографии `84` сливаются в **один средний вектор**.

Для адреса с похожими ракурсами это нормально, но для `84`, где ракурсы сильно различаются, средний вектор может оказаться **не очень похожим ни на один конкретный ракурс**.

При этом у нас уже есть:

```python
embeddings
representatives
```

и в `recognizer` мы можем использовать **лучшее совпадение с отдельными фотографиями fingerprint**, а не только similarity с centroid.

### Я бы сделал так

Для каждого адреса считать два показателя:

```text
CENTROID       — насколько фото похоже на общий адрес
BEST_IMAGE     — насколько фото похоже на лучший известный ракурс адреса
```

Например для `84`:

```text
84
CENTROID       0.78
BEST_IMAGE     0.94
```

Это означает:

> В среднем фото не очень похоже на "средний 84", но конкретный ракурс очень хорошо совпадает с одной из фотографий 84.

И это **правильное поведение** для многомаршрутного/многоракурсного слепка.

### Более того

Я бы вообще сделал fingerprint адреса как **набор ракурсов**, а не как один усреднённый объект:

```text
84
 ├── viewpoint_01
 ├── viewpoint_02
 ├── viewpoint_03
 ├── viewpoint_04
 └── ...
```

Но физически отдельные папки создавать не обязательно.

Можно оставить:

```text
84_v33_fast/
    embeddings.npy
    centroid.npy
    representatives.npy
    environment_embeddings.npy
    color_embeddings.npy
    spatial_embeddings.npy
```

и при распознавании спрашивать:

> **На какой фотографии внутри fingerprint этот кадр похож сильнее всего?**

а уже затем агрегировать результат по адресу.

---

### И это особенно важно для нашего финального теста

Мы сейчас получили:

**262 тестовых фотографии × 18 адресов.**

Я бы пока **не делал вывод, что 84 плохой**.

Сначала нужно посмотреть статистику примерно такого вида:

```text
ADDRESS       TEST   TOP1    AVG SCORE   AVG MARGIN
----------------------------------------------------
78             20      18       0.91        0.052
79              8       7       0.89        0.041
80              8       8       0.95        0.118
...
84              8       5       0.84        0.031
...
```

И отдельно:

```text
84:

TOP1=84       5
TOP1=78       2
TOP1=83       1
```

После этого посмотреть **не только score**, но и `best_image`.

Если у ошибочно определённых фотографий `84`:

```text
CENTROID = 0.76
BEST_IMAGE = 0.94
```

то проблема не в слепке — проблема в том, что **финальная формула недостаточно учитывает лучший ракурс**.

А если даже:

```text
BEST_IMAGE = 0.72
```

тогда уже действительно нужно смотреть на исходные фотографии `84`.

**Поэтому 84 сейчас не трогаем и не пересоздаём.** Сначала адаптируем оценку под многоракурсные fingerprint'ы. Это гораздо правильнее для нашей задачи распознавания адресов по окружающей обстановке.

---

### 👤 **User** — 2026-08-15 00:47:43

может быть нужно продолжаем. действительно в слепке можно иметь подслепки из отличающихся раккуросов

---

### 🤖 **Assistant** — 2026-08-15 00:47:44

Да. **Именно это я бы сейчас и сделал.** Для нашей задачи это даже лучше, чем пытаться представить адрес одним усреднённым вектором.

Нужно перейти от модели:

```text
АДРЕС 84
   ↓
один centroid
```

к модели:

```text
АДРЕС 84
   │
   ├── подслепок A — ракурс с одной стороны
   ├── подслепок B — ракурс с другой стороны
   ├── подслепок C — дальний план
   ├── подслепок D — крупный план
   └── ...
```

### Как я предлагаю сделать

При создании fingerprint из 54 фотографий алгоритм автоматически группирует изображения по визуальному сходству.

Например:

```text
84_v34/
├── global
│
├── subfingerprint_01/
│   ├── 12 кадров
│
├── subfingerprint_02/
│   ├── 15 кадров
│
├── subfingerprint_03/
│   ├── 10 кадров
│
└── subfingerprint_04/
    └── 17 кадров
```

Но **не обязательно физически делать такие папки**. Лучше хранить это внутри fingerprint:

```text
embeddings.npy
cluster_labels.npy
sub_centroids.npy
sub_representatives.npy
...
```

Тогда распознавание будет происходить в два этапа:

```text
ТЕСТОВОЕ ФОТО
       │
       ▼
   18 адресов
       │
       ▼
  лучшие подслепки
       │
       ▼
   TOP-1 адрес
```

Например:

```text
Фото test_123

84
 ├─ подслепок 1 = 0.71
 ├─ подслепок 2 = 0.93  ← лучший
 ├─ подслепок 3 = 0.76
 └─ подслепок 4 = 0.81

78
 ├─ подслепок 1 = 0.84
 └─ подслепок 2 = 0.79
```

Тогда выбирается:

```text
84 = 0.93
78 = 0.84

TOP-1 = 84
MARGIN = 0.09
```

Это намного логичнее.

### Причём я бы не задавал количество подслепков вручную

Например, для:

```text
78 — 82 фотографии
```

может получиться:

```text
3 подслепка
```

а для:

```text
84 — 54 фотографии
```

при сильно разных ракурсах:

```text
5 подслепков
```

А если:

```text
90 — 19 фотографий
```

то вполне может остаться:

```text
1–2 подслепка
```

То есть **структура fingerprint сама адаптируется к разнообразию фотографий**.

### И самое важное

Я бы не выбрасывал `centroid`.

Он остаётся полезным как **глобальный признак адреса**:

```text
FINAL SCORE =
    глобальное сходство адреса
    +
    лучшее сходство подслепка
    +
    environment
    +
    color
    +
    spatial
```

Например первоначально:

```text
GLOBAL       0.35
BEST_SUB     0.45
ENVIRONMENT  0.15
COLOR        0.03
SPATIAL      0.02
```

Но **веса пока не меняем**. Сначала реализуем подслепки и проведём тот же тест на 262 фотографиях.

---

## Я предлагаю следующий шаг

Не трогать текущие `78_v33 ... 95_v33_fast`.

Создать экспериментальную версию:

```text
v34
```

Например:

```text
data/fingerprints/
    78_v34
    79_v34
    ...
    95_v34
```

Причём `v34` будет полностью совместим с текущим проектом.

Первым делом я бы сделал **автоматическую кластеризацию DINO-векторов внутри каждого адреса**.

И здесь есть хороший момент: у нас уже есть:

```text
embeddings.npy
```

То есть **не надо заново прогонять DINO для создания подслепков**. Мы можем взять уже рассчитанные 768-мерные embeddings и кластеризовать их.

Это позволит очень быстро экспериментировать с разными вариантами группировки.

**Я бы начал именно с этого:** построить `v34` поверх уже существующих `*_v33_fast`, определить подслепки и затем прогнать те же 262 тестовых фото. Так мы сможем честно сравнить **v33 против v34** на одном и том же тесте.

---

### 👤 **User** — 2026-08-15 00:48:34

как можно распараллелить и ускорить создание слепков

---

### 🤖 **Assistant** — 2026-08-15 00:48:35

Да. Сейчас у тебя создание одного слепка фактически состоит из **двух разных типов вычислений**, и их надо ускорять по-разному.

### Где сейчас тратится время

В `fingerprint.py`:

1. **DINOv2** для всех фотографий:
```python
embeddings = embedder.embed_paths(paths)
```

2. Затем CPU считает три descriptor'а для каждой фотографии:
```python
environment_embeddings
color_embeddings
spatial_embeddings
```

На твоём Ryzen 5 5600 это как раз хорошо распараллеливается.

Но **DINOv2 на RTX 3060 нельзя просто запускать в 6 Python-процессах** — они начнут конкурировать за 11.6 GB VRAM. Здесь лучше **один GPU-процесс + большой batch**.

---

# Я бы сделал 3 уровня ускорения

### 1. DINO — увеличить batch

Сейчас надо посмотреть, какой batch использует `SceneEmbedder`.

Если там, например:

```python
batch_size = 8
```

можно попробовать:

```text
8 → 16 → 24 → 32
```

для RTX 3060.

Это обычно даст гораздо больший выигрыш, чем CPU workers.

---

### 2. Compact descriptors — 6 CPU workers

Вот эти три операции:

```text
environment
color
spatial
```

для каждой фотографии независимы.

Сейчас они идут последовательно:

```text
photo1 → environment
photo2 → environment
photo3 → environment
...
```

Нужно:

```text
CPU 0 ─ photo 1
CPU 1 ─ photo 2
CPU 2 ─ photo 3
CPU 3 ─ photo 4
CPU 4 ─ photo 5
CPU 5 ─ photo 6
...
```

Причём **читать JPEG лучше один раз**, а не три раза.

Это ещё важнее.

Сейчас для каждой фотографии происходит:

```text
cv2.imread()
↓
environment
```

потом:

```text
cv2.imread()
↓
color
```

потом:

```text
cv2.imread()
↓
spatial
```

То есть одна фотография читается с диска **3 раза**.

Лучше:

```text
cv2.imread()
      ↓
resize
      ↓
┌───────────────┬────────────┬────────────┐
environment     color        spatial
```

Это уменьшит нагрузку на диск и декодирование JPEG.

---

# 3. Создание нескольких fingerprint одновременно

У тебя сейчас:

```text
78 → DINO → descriptors → save

79 → DINO → descriptors → save

80 → ...
```

Можно сделать очередь:

```text
             RTX 3060
                │
        ┌───────┴───────┐
        │   DINO batch  │
        └───────┬───────┘
                │
       ┌────────┼────────┐
       ↓        ↓        ↓
     CPU 1    CPU 2    CPU 3 ...
       │        │        │
       └────────┼────────┘
                ↓
          fingerprint
```

Но **не запускать 18 отдельных DINO-процессов**.

---

# Оптимальная схема для твоего компьютера

У тебя:

```text
Ryzen 5 5600
6 ядер / 12 потоков
RTX 3060 12 GB
```

Я бы начал с:

```text
DINO batch       16–24
CPU workers       6
OpenCV threads    1 на worker
GPU processes     1
```

Почему OpenCV threads = 1?

Потому что если запустить:

```text
6 Python workers
×
OpenCV 12 threads
```

получишь до 72 конкурирующих потоков и вместо ускорения можешь получить тормоза.

---

# И есть ещё более интересная оптимизация

Для создания fingerprint нам **не обязательно считать environment/color/spatial после DINO отдельно**.

Можно сделать единый worker:

```python
def process_image(path):
    image = cv2.imread(...)
    image = resize(...)

    environment = ...
    color = ...
    spatial = ...

    return environment, color, spatial
```

И:

```python
with ProcessPoolExecutor(max_workers=6) as pool:
    descriptors = list(
        pool.map(process_image, paths)
    )
```

Получаем:

```text
54 фотографии
       ↓
6 CPU workers
       ↓
9 фотографий на worker
```

---

## Но я бы пошёл ещё дальше

Для твоего проекта **создание fingerprint можно сделать двухфазным**.

### Фаза A — DINO

Один процесс:

```text
RTX 3060
     ↓
batch 24
     ↓
78 → embeddings.npy
79 → embeddings.npy
...
95 → embeddings.npy
```

### Фаза B — descriptors

CPU:

```text
6 workers
     ↓
environment
color
spatial
```

И самое приятное — эти фазы можно **кэшировать**.

То есть если мы потом решим изменить кластеризацию подслепков:

```text
DINO повторно НЕ считается.
```

Если поменяем веса:

```text
DINO повторно НЕ считается.
```

Если поменяем алгоритм подслепков:

```text
DINO повторно НЕ считается.
```

---

# Для твоих 78–95 это особенно выгодно

Всего у тебя примерно:

```text
78  82
79  65
80  37
81  65
82  67
83  68
84  54
85  58
86  58
87  50
88  54
89  64
90  19
91  41
92  57
93  51
94  67
95  86
```

Это около **1000 фотографий**.

Если сейчас создавать каждый fingerprint отдельно, много времени уходит на повторяющиеся операции.

Можно сделать:

```text
                 ВСЕ ФОТО
                    │
             ┌──────┴──────┐
             │             │
          DINO GPU       JPEG/CPU
             │             │
       embeddings       descriptors
             │             │
             └──────┬──────┘
                    ↓
              18 fingerprints
```

И тогда создание всех слепков станет значительно быстрее.

---

### Я бы сейчас не переписывал весь проект

Сначала оптимизируем **`fingerprint.py` + `scene_analyzer.py`**, не меняя формат v3.3.

Сделаем:

```text
create
  ↓
DINO batch
  ↓
6 CPU workers
  ↓
однократное чтение каждой фотографии
  ↓
environment/color/spatial
  ↓
сохранение v3.3
```

А уже потом поверх этого добавим **v34 с подслепками по ракурсам**.

Это даст нам одновременно **быстрое создание слепков + возможность многократно экспериментировать с подслепками без повторного DINO**.

---

### 👤 **User** — 2026-08-15 00:50:11

в будущем каталогов для слепков будет очень много и надо будет делать оптимизацию под пакетную обработку - очереди т.п

---

### 🤖 **Assistant** — 2026-08-15 00:50:11

Да. Если каталогов будет **сотни/тысячи**, сейчас лучше не оптимизировать только `fingerprint.py`. Надо сразу заложить **batch-пайплайн с очередью задач**.

Я бы архитектуру сделал так:

```text
                 ┌──────────────────────┐
                 │  INCOMING FOLDERS    │
                 │  78,79,80,...,1000   │
                 └──────────┬───────────┘
                            ↓
                    ┌──────────────┐
                    │ JOB QUEUE    │
                    │ pending      │
                    │ processing   │
                    │ done         │
                    │ failed       │
                    └──────┬───────┘
                           ↓
             ┌─────────────────────────┐
             │       WORKER MANAGER    │
             └────────────┬────────────┘
                          ↓
             ┌────────────────────────┐
             │      GPU WORKER        │
             │ RTX 3060               │
             │ DINO batch processing  │
             └───────────┬────────────┘
                         ↓
             ┌────────────────────────┐
             │      CPU WORKERS       │
             │ 6 процессов            │
             │ descriptors            │
             └───────────┬────────────┘
                         ↓
                  ┌──────────────┐
                  │ FINGERPRINT  │
                  │ DB / STORAGE │
                  └──────────────┘
```

### Главное — очередь должна быть постоянной

Я бы **не делал очередь просто Python `multiprocessing.Queue`**.

Для будущего проекта лучше SQLite:

```text
jobs.db
```

Например:

```text
jobs
--------------------------------
id
source_folder
fingerprint_id
status
priority
created_at
started_at
finished_at
attempts
error
```

Статусы:

```text
PENDING
PROCESSING
DONE
FAILED
```

Тогда если компьютер выключился на 700-м адресе из 1000:

**не надо начинать сначала.**

После запуска:

```text
700 DONE
701 DONE
702 PROCESSING  ← проверяем
703 PENDING
...
1000 PENDING
```

---

# И очень важный момент для твоей RTX 3060

Я бы сделал **один GPU worker**.

Не:

```text
GPU worker 1
GPU worker 2
GPU worker 3
```

А:

```text
                 RTX 3060
                    │
              GPU Worker
                    │
          ┌─────────┼─────────┐
          ↓         ↓         ↓
        batch     batch     batch
         24        24        24
```

GPU постоянно получает очередные изображения.

---

# CPU отдельно

CPU workers:

```text
Ryzen 5600
│
├── worker 1
├── worker 2
├── worker 3
├── worker 4
├── worker 5
└── worker 6
```

Они могут параллельно заниматься:

```text
JPEG decode
resize
environment
color
spatial
```

При этом DINO работает независимо на GPU.

---

# Ещё лучше — общий кэш embeddings

Это будет очень полезно.

Например:

```text
cache/
   dino/
      a8/
        a8f32....npy
        b73d1....npy
```

Для каждой фотографии вычисляем hash:

```text
SHA256(photo)
```

или быстрее:

```text
mtime + size + path
```

и проверяем:

```text
DINO embedding существует?
        │
     ┌──┴──┐
    YES    NO
     │      │
используем DINO
            ↓
         считаем
            ↓
          cache
```

Тогда одна фотография **никогда повторно не проходит DINO**, если она не изменилась.

Это особенно важно, если один и тот же набор фотографий используется для:

- v33
- v34
- разных подслепков
- разных весов
- разных алгоритмов кластеризации.

---

# Я бы разделил систему на 4 слоя

```text
app/
├── pipeline/
│   ├── queue.py
│   ├── scheduler.py
│   ├── gpu_worker.py
│   ├── cpu_worker.py
│   └── jobs.py
│
├── core/
│   ├── embedder.py
│   ├── fingerprint.py
│   ├── recognizer.py
│   └── scene_analyzer.py
│
├── cache/
│   └── embeddings.py
│
└── cli.py
```

Тогда существующий CLI останется:

```bash
uv run scene-fingerprint create 84 data/input/84
```

но появится:

```bash
uv run scene-fingerprint queue add 84 data/input/84
```

и:

```bash
uv run scene-fingerprint queue add 85 data/input/85
uv run scene-fingerprint queue add 86 data/input/86
...
```

а потом:

```bash
uv run scene-fingerprint worker
```

И компьютер сам обрабатывает очередь.

---

# Для массовой обработки я бы добавил приоритеты

Например:

```text
HIGH
NORMAL
LOW
```

Можно поставить:

```text
новый адрес          HIGH
пересоздание слепка  NORMAL
перестроение v34     LOW
```

И worker всегда берёт:

```text
HIGH → NORMAL → LOW
```

---

# И ещё одна важная вещь

Не надо делать:

```text
1000 каталогов
↓
1000 отдельных запусков Python
↓
1000 раз загрузка DINO
```

Это будет очень плохо.

Нужно:

```text
Python процесс
       │
       ├── загрузил DINO один раз
       │
       ├── получил очередь
       │
       ├── обработал 84
       ├── обработал 85
       ├── обработал 86
       ├── ...
       └── обработал 1000
```

**Модель загружается один раз.**

Это даст очень существенный выигрыш.

---

## А для будущего проекта я бы заложил ещё одну вещь

Не связывать fingerprint напрямую с номером адреса.

То есть:

```text
84_v34
```

лучше рассматривать как:

```text
fingerprint_id = UUID
address_id = 84
version = v34
status = active
```

Потому что позже может быть:

```text
address 84
 ├── fingerprint v33
 ├── fingerprint v34
 ├── fingerprint v35
 └── fingerprint v36
```

И можно будет сравнивать версии и выбирать лучшую.

---

**Итого:** да, ты правильно думаешь. При будущем количестве каталогов **очередь + один постоянно загруженный GPU worker + пул CPU workers + кэш DINO embeddings** — это гораздо правильнее, чем просто добавлять `--workers 6`.

И я бы **сейчас заложил эту архитектуру**, до того как мы начнём делать v34 с подслепками. Тогда подслепки будут просто ещё одной стадией pipeline, а не очередным переписыванием всей системы.

---

### 👤 **User** — 2026-08-15 00:51:02

давай начнем , больше не будем пока ничего придумывать иулучшать

---

### 🤖 **Assistant** — 2026-08-15 00:51:03

Да. **Фиксируем текущую архитектуру и больше ничего не добавляем.** Начинаем только с пакетной обработки: очередь → GPU worker → CPU workers → сохранение слепка.

Будем двигаться маленькими проверяемыми шагами, чтобы не сломать рабочий `v3.3`.

### Шаг 1 — сначала зафиксируем текущее состояние

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

git status --short 2>/dev/null || true

echo "=== PYTHON ==="
uv run python --version

echo "=== PROJECT ==="
pwd

echo "=== FINGERPRINTS ==="
ls -1 data/fingerprints | sort

echo "=== CLI ==="
uv run scene-fingerprint --help | head -40
```

И отдельно:

```bash
echo "=== CURRENT FILES ==="
ls -lh app/core/fingerprint.py
ls -lh app/core/recognizer.py
ls -lh app/core/scene_analyzer.py
ls -lh app/cli.py
```

### Что будем делать после этого

**Только 4 компонента:**

```text
1. jobs.db
      ↓
2. queue add
      ↓
3. worker
      ↓
4. fingerprint creation
```

Первый worker будет обрабатывать задания **последовательно**, но внутри создания одного слепка:

- DINO → GPU;
- descriptors → 6 CPU workers;
- результат → существующий формат `v3.3`.

Пока **не трогаем**:

- алгоритм распознавания;
- веса;
- `84`;
- подслепки;
- кластеризацию;
- структуру fingerprint;
- тестовый классификатор.

Сначала сделаем **надёжную очередь**, которая умеет `PENDING → PROCESSING → DONE/FAILED` и переживает перезапуск.

Пришли вывод этого блока — и пойдём с **первого шага**.

---

### 👤 **User** — 2026-08-15 00:51:34

первый шаг

---

### 🤖 **Assistant** — 2026-08-15 00:51:35

Да. Начинаем **только с первого шага** — ничего в рабочем коде пока не меняем.

Выполни из проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== PYTHON ==="
uv run python --version

echo
echo "=== PROJECT ==="
pwd

echo
echo "=== FINGERPRINTS ==="
ls -1 data/fingerprints | sort

echo
echo "=== CLI ==="
uv run scene-fingerprint --help | head -40

echo
echo "=== CURRENT FILES ==="
ls -lh app/core/fingerprint.py
ls -lh app/core/recognizer.py
ls -lh app/core/scene_analyzer.py
ls -lh app/cli.py
```

И пришли **весь вывод**.

После этого сделаем только следующий маленький шаг — создадим основу `jobs.db`.

---

### 👤 **User** — 2026-08-15 00:51:57

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== PYTHON ==="
uv run python --version

echo
echo "=== PROJECT ==="
pwd

echo
echo "=== FINGERPRINTS ==="
ls -1 data/fingerprints | sort

echo
echo "=== CLI ==="
uv run scene-fingerprint --help | head -40

echo
echo "=== CURRENT FILES ==="
ls -lh app/core/fingerprint.py
ls -lh app/core/recognizer.py
ls -lh app/core/scene_analyzer.py
ls -lh app/cli.py
=== PYTHON ===
Python 3.12.3

=== PROJECT ===
/home/alexice/projects/scene_fingerprint_mvp_v02

=== FINGERPRINTS ===
78
78_v33
79
79_v33
80
80_v33
81
81_v33
82
82_v33
83_v33
84_v33
85_v33
86_v33_fast
87_v33_fast
88_v33_fast
89_v33_fast
90_v33_fast
91_v33_fast
92_v33_fast
93_v33_fast
94_v33_fast
95_v33_fast

=== CLI ===
usage: scene-fingerprint [-h] {create,analyze,recognize} ...

Scene fingerprinting and recognition v3.3 compact

positional arguments:
  {create,analyze,recognize}
    create              Create v3.3 compact fingerprint
    analyze             Analyze one fingerprint
    recognize           Recognize images

options:
  -h, --help            show this help message and exit

=== CURRENT FILES ===
-rw-r--r-- 1 alexice alexice 13K Aug 15 00:14 app/core/fingerprint.py
-rw-r--r-- 1 alexice alexice 12K Aug 15 00:24 app/core/recognizer.py
-rw-rw-r-- 1 alexice alexice 12K Aug 15 00:26 app/core/scene_analyzer.py
-rw-r--r-- 1 alexice alexice 8.3K Aug 15 00:22 app/cli.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:51:58

Отлично. Состояние зафиксировали. **Рабочие fingerprint'ы не трогаем.**

### Шаг 2 — создаём только очередь `jobs.db`

Пока **без worker, без изменений `fingerprint.py`, без изменений DINO**.

Создадим отдельный модуль:

```text
app/pipeline/
    __init__.py
    queue.py
```

И SQLite-базу:

```text
data/jobs.db
```

Выполни целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

mkdir -p app/pipeline

touch app/pipeline/__init__.py

cat > app/pipeline/queue.py <<'PY'
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class JobQueue:
    """
    Persistent SQLite job queue.

    States:
        PENDING
        PROCESSING
        DONE
        FAILED
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
        )

        connection.row_factory = sqlite3.Row

        return connection

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).isoformat()

    def _init_db(self):
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    source_folder TEXT NOT NULL,
                    fingerprint_id TEXT NOT NULL,

                    status TEXT NOT NULL
                        DEFAULT 'PENDING',

                    priority INTEGER NOT NULL
                        DEFAULT 0,

                    attempts INTEGER NOT NULL
                        DEFAULT 0,

                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,

                    error TEXT
                )
                """
            )

            db.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_jobs_status_priority
                ON jobs(status, priority DESC, id)
                """
            )

    def add(
        self,
        source_folder: str | Path,
        fingerprint_id: str,
        priority: int = 0,
    ):
        created_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO jobs (
                    source_folder,
                    fingerprint_id,
                    status,
                    priority,
                    attempts,
                    created_at
                )
                VALUES (?, ?, 'PENDING', ?, 0, ?)
                """,
                (
                    str(source_folder),
                    str(fingerprint_id),
                    int(priority),
                    created_at,
                ),
            )

            return int(cursor.lastrowid)

    def list(
        self,
        status: str | None = None,
    ):
        with self._connect() as db:

            if status is None:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    ORDER BY
                        priority DESC,
                        id ASC
                    """
                )
            else:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE status = ?
                    ORDER BY
                        priority DESC,
                        id ASC
                    """,
                    (status,),
                )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    def counts(self):
        with self._connect() as db:
            cursor = db.execute(
                """
                SELECT
                    status,
                    COUNT(*) AS count
                FROM jobs
                GROUP BY status
                """
            )

            return {
                row["status"]: row["count"]
                for row in cursor.fetchall()
            }

if __name__ == "__main__":
    queue = JobQueue(
        "data/jobs.db"
    )

    print("Queue:", queue.db_path)
    print("Counts:", queue.counts())
PY

uv run python -m py_compile app/pipeline/queue.py

uv run python -m app.pipeline.queue

ls -lh data/jobs.db
```

Ожидаем примерно:

```text
Queue: data/jobs.db
Counts: {}
-rw-r--r-- ... data/jobs.db
```

Это пока **только фундамент очереди**.

Пришли вывод последних команд.

---

### 👤 **User** — 2026-08-15 00:52:27

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

mkdir -p app/pipeline

touch app/pipeline/__init__.py

cat > app/pipeline/queue.py <<'PY'
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class JobQueue:
    """
    Persistent SQLite job queue.

    States:
        PENDING
        PROCESSING
        DONE
        FAILED
ls -lh data/jobs.dbp.pipeline.queueeline/queue.py)REMENT,
Queue: data/jobs.db
Counts: {}
-rw-r--r-- 1 alexice alexice 16K Aug 15 00:52 data/jobs.db
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:52:28

Отлично. **Первый шаг завершён правильно**: SQLite-очередь создана, база `data/jobs.db` существует.

Пока **ничего не улучшаем и не меняем архитектуру**. Следующий шаг — сделать минимальный CLI для постановки задач в очередь.

### Шаг 2 — добавить команду `queue-add`

Она будет принимать, например:

```bash
uv run scene-fingerprint queue-add 86 data/input/86
```

и создавать в `data/jobs.db` одну задачу со статусом `PENDING`.

Но сначала проверим, что твой `queue.py` действительно полностью записался и содержит методы класса.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,260p' app/pipeline/queue.py
```

**Пришли весь вывод.**

После этого дам ровно следующий кусок — без параллельной обработки, без Celery/Redis и без дополнительных оптимизаций. Сначала спокойно построим рабочую очередь `PENDING → PROCESSING → DONE/FAILED`.

---

### 👤 **User** — 2026-08-15 00:52:56

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,260p' app/pipeline/queue.py
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class JobQueue:
    """
    Persistent SQLite job queue.

    States:
        PENDING
        PROCESSING
        DONE
        FAILED
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
        )

        connection.row_factory = sqlite3.Row

        return connection

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).isoformat()

    def _init_db(self):
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    source_folder TEXT NOT NULL,
                    fingerprint_id TEXT NOT NULL,

                    status TEXT NOT NULL
                        DEFAULT 'PENDING',

                    priority INTEGER NOT NULL
                        DEFAULT 0,

                    attempts INTEGER NOT NULL
                        DEFAULT 0,

                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,

                    error TEXT
                )
                """
            )

            db.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_jobs_status_priority
                ON jobs(status, priority DESC, id)
                """
            )

    def add(
        self,
        source_folder: str | Path,
        fingerprint_id: str,
        priority: int = 0,
    ):
        created_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO jobs (
                    source_folder,
                    fingerprint_id,
                    status,
                    priority,
                    attempts,
                    created_at
                )
                VALUES (?, ?, 'PENDING', ?, 0, ?)
                """,
                (
                    str(source_folder),
                    str(fingerprint_id),
                    int(priority),
                    created_at,
                ),
            )

            return int(cursor.lastrowid)

    def list(
        self,
        status: str | None = None,
    ):
        with self._connect() as db:

            if status is None:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    ORDER BY
                        priority DESC,
                        id ASC
                    """
                )
            else:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE status = ?
                    ORDER BY
                        priority DESC,
                        id ASC
                    """,
                    (status,),
                )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    def counts(self):
        with self._connect() as db:
            cursor = db.execute(
                """
                SELECT
                    status,
                    COUNT(*) AS count
                FROM jobs
                GROUP BY status
                """
            )

            return {
                row["status"]: row["count"]
                for row in cursor.fetchall()
            }

if __name__ == "__main__":
    queue = JobQueue(
        "data/jobs.db"
    )

    print("Queue:", queue.db_path)
    print("Counts:", queue.counts())
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:52:57

Да, `queue.py` сейчас **корректный и достаточно минимальный**. Ничего в нём пока не меняем.

Следующий шаг — добавить возможность **поставить задачу в очередь через CLI**.

## Шаг 2. Добавляем `queue-add`

Нам нужна команда:

```bash
uv run scene-fingerprint queue-add 86 data/input/86
```

Она должна создать:

```text
ID:              1
source_folder:   data/input/86
fingerprint_id:  86
status:          PENDING
```

### 1. Открой `app/cli.py`

Сначала посмотрим верхнюю часть файла, чтобы встроить команду без нарушения существующей структуры.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,115p' app/cli.py
```

Пришли вывод.

После этого дам **точную замену командой из терминала**. Пока только `queue-add`; worker и параллельную обработку не трогаем.

---

### 👤 **User** — 2026-08-15 00:53:15

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run scene-fingerprint queue-add 86 data/input/86
usage: scene-fingerprint [-h] {create,analyze,recognize} ...
scene-fingerprint: error: argument command: invalid choice: 'queue-add' (choose from 'create', 'analyze', 'recognize')
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:53:16

Да, это ожидаемо: **`queue-add` мы ещё не подключили к CLI**. Очередь `data/jobs.db` уже есть, теперь только регистрируем команду.

Не надо пока ничего переделывать. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,115p' app/cli.py
```

Пришли вывод. Я дам **одну точную команду**, которая добавит `queue-add`, после чего проверим:

```bash
uv run scene-fingerprint queue-add 86 data/input/86
```

и

```bash
python3 -m app.pipeline.queue
```

Пока остаёмся строго на этом шаге: **добавление заданий в SQLite-очередь**.

---

### 👤 **User** — 2026-08-15 00:53:43

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,115p' app/cli.py
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer
from app.core.scene_analyzer import SceneAnalyzer

def build_parser():
    parser = argparse.ArgumentParser(
        prog="scene-fingerprint",
        description=(
            "Scene fingerprinting and "
            "recognition v3.3 compact"
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------

    create_parser = subparsers.add_parser(
        "create",
        help="Create v3.3 compact fingerprint",
    )

    create_parser.add_argument(
        "fingerprint",
        help="Fingerprint ID",
    )

    create_parser.add_argument(
        "folder",
        help="Folder with reference images",
    )

    # --------------------------------------------------
    # ANALYZE
    # --------------------------------------------------

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze one fingerprint",
    )

    analyze_parser.add_argument(
        "folder",
        help="Folder with query images",
    )

    analyze_parser.add_argument(
        "--fingerprint",
        required=True,
        help="Fingerprint ID",
    )

    # --------------------------------------------------
    # RECOGNIZE
    # --------------------------------------------------

    recognize_parser = subparsers.add_parser(
        "recognize",
        help="Recognize images",
    )

    recognize_parser.add_argument(
        "folder",
        help="Folder with query images",
    )

    recognize_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of candidates",
    )

    recognize_parser.add_argument(
        "--threshold",
        type=float,
        default=0.65,
        help="Minimum absolute match score",
    )

    recognize_parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Number of CPU workers for descriptor calculation",
    )

    recognize_parser.add_argument(
        "--fingerprints",
        type=str,
        default=None,
        help="Comma-separated fingerprint IDs to use",
    )

    recognize_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON",
    )

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:53:44

Отлично. Структура понятна. Добавляем **только `queue-add`**, не трогая существующие `create/analyze/recognize`.

### 1. Добавляем импорт `JobQueue`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/cli.py")
text = p.read_text()

old = "from app.core.scene_analyzer import SceneAnalyzer\n"
new = old + "from app.pipeline.queue import JobQueue\n"

if "from app.pipeline.queue import JobQueue" not in text:
    if old not in text:
        raise SystemExit("Import insertion point not found")
    text = text.replace(old, new, 1)

p.write_text(text)
print("OK: JobQueue imported")
PY
```

### 2. Добавляем parser для `queue-add`

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("app/cli.py")
text = p.read_text()

marker = '''    # --------------------------------------------------
    # ANALYZE
    # --------------------------------------------------
'''

block = '''    # --------------------------------------------------
    # QUEUE ADD
    # --------------------------------------------------

    queue_add_parser = subparsers.add_parser(
        "queue-add",
        help="Add fingerprint creation job to queue",
    )

    queue_add_parser.add_argument(
        "fingerprint",
        help="Fingerprint ID",
    )

    queue_add_parser.add_argument(
        "folder",
        help="Folder with reference images",
    )

    queue_add_parser.add_argument(
        "--priority",
        type=int,
        default=0,
        help="Job priority",
    )

'''

if "queue-add" not in text:
    if marker not in text:
        raise SystemExit("Parser insertion point not found")

    text = text.replace(
        marker,
        block + marker,
        1,
    )

p.write_text(text)
print("OK: queue-add parser added")
PY
```

### 3. Добавляем обработчик команды

Сначала найдем место, где начинается обработка `create`. Выполни:

```bash
grep -n "if args.command" app/cli.py
```

Ожидаем что-то вроде:

```text
...
if args.command == "create":
if args.command == "analyze":
if args.command == "recognize":
```

**Пришли этот вывод.**

Пока обработчик не добавляем — это следующий маленький шаг.

---

### 👤 **User** — 2026-08-15 00:54:18

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n "if args.command" app/cli.py
315:    if args.command == "create":
358:    if args.command == "analyze":
399:    if args.command == "recognize":

---

### 🤖 **Assistant** — 2026-08-15 00:54:19

Отлично. Теперь добавляем обработчик **перед `create`**.

Выполни целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/cli.py")
text = p.read_text()

marker = '''    if args.command == "create":
'''

block = '''    if args.command == "queue-add":

        folder = Path(args.folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        queue = JobQueue(
            settings.data_dir / "jobs.db"
        )

        job_id = queue.add(
            source_folder=folder,
            fingerprint_id=args.fingerprint,
            priority=args.priority,
        )

        print(
            f"[Queue] Job added: {job_id}"
        )
        print(
            f"[Queue] fingerprint={args.fingerprint}"
        )
        print(
            f"[Queue] folder={folder}"
        )
        print(
            f"[Queue] priority={args.priority}"
        )
        print(
            "[Queue] status=PENDING"
        )

        return 0

'''

if 'if args.command == "queue-add":' in text:
    print("queue-add handler already exists")
else:
    if marker not in text:
        raise SystemExit("CREATE handler not found")

    text = text.replace(
        marker,
        block + marker,
        1,
    )

    p.write_text(text)
    print("OK: queue-add handler added")
PY
```

Потом проверяем синтаксис:

```bash
uv run python -m py_compile app/cli.py
```

И проверяем CLI:

```bash
uv run scene-fingerprint --help
```

В списке должно появиться:

```text
{queue-add,create,analyze,recognize}
```

Затем **пока не создавай много задач**. Сделаем одну тестовую:

```bash
uv run scene-fingerprint queue-add 86 data/input/86
```

Ожидаем:

```text
[Queue] Job added: 1
[Queue] fingerprint=86
[Queue] folder=data/input/86
[Queue] priority=0
[Queue] status=PENDING
```

И сразу проверим базу:

```bash
python3 -m app.pipeline.queue
```

Должно быть примерно:

```text
Queue: data/jobs.db
Counts: {'PENDING': 1}
```

Если это получится — **первый настоящий элемент пакетного конвейера готов**: папка `86` не обрабатывается сразу, а превращается в постоянную задачу `PENDING`.

---

### 👤 **User** — 2026-08-15 00:55:28

все норм

---

### 🤖 **Assistant** — 2026-08-15 00:55:29

Отлично. Тогда **фиксируем этот этап и ничего лишнего не добавляем**.

Сейчас у нас уже есть:

```text
data/input/86
       │
       ▼
   queue-add
       │
       ▼
   data/jobs.db
       │
       ▼
    PENDING
```

Следующий шаг — **worker**, который будет брать одну задачу:

```text
PENDING
   ↓
PROCESSING
   ↓
создание слепка
   ↓
DONE
```

При ошибке:

```text
PROCESSING
   ↓
FAILED
```

И только после того, как это заработает на **одной папке**, будем переходить к параллельной обработке нескольких задач.

### Шаг 3

Сначала покажи текущий конец `queue.py`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

tail -80 app/pipeline/queue.py
```

После этого добавим **только получение одной задачи из очереди (`PENDING → PROCESSING`)**.

---

### 👤 **User** — 2026-08-15 00:55:47

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

tail -80 app/pipeline/queue.py
                """
                INSERT INTO jobs (
                    source_folder,
                    fingerprint_id,
                    status,
                    priority,
                    attempts,
                    created_at
                )
                VALUES (?, ?, 'PENDING', ?, 0, ?)
                """,
                (
                    str(source_folder),
                    str(fingerprint_id),
                    int(priority),
                    created_at,
                ),
            )

            return int(cursor.lastrowid)

    def list(
        self,
        status: str | None = None,
    ):
        with self._connect() as db:

            if status is None:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    ORDER BY
                        priority DESC,
                        id ASC
                    """
                )
            else:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE status = ?
                    ORDER BY
                        priority DESC,
                        id ASC
                    """,
                    (status,),
                )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    def counts(self):
        with self._connect() as db:
            cursor = db.execute(
                """
                SELECT
                    status,
                    COUNT(*) AS count
                FROM jobs
                GROUP BY status
                """
            )

            return {
                row["status"]: row["count"]
                for row in cursor.fetchall()
            }

if __name__ == "__main__":
    queue = JobQueue(
        "data/jobs.db"
    )

    print("Queue:", queue.db_path)
    print("Counts:", queue.counts())
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:55:48

Отлично. Добавляем сейчас **только метод `claim()`**. Он атомарно забирает одну задачу `PENDING`, переводит её в `PROCESSING` и возвращает её worker'у.

Это важный фундамент для будущего параллельного запуска: несколько worker'ов не должны взять одну и ту же задачу.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/pipeline/queue.py")
text = p.read_text()

marker = '''    def counts(self):
'''

block = '''    def claim(self):
        """
        Atomically take the next PENDING job.

        Returns:
            dict with job data, or None if queue is empty.
        """

        with self._connect() as db:

            db.execute("BEGIN IMMEDIATE")

            cursor = db.execute(
                """
                SELECT *
                FROM jobs
                WHERE status = 'PENDING'
                ORDER BY
                    priority DESC,
                    id ASC
                LIMIT 1
                """
            )

            row = cursor.fetchone()

            if row is None:
                db.commit()
                return None

            job_id = row["id"]
            started_at = self._now()

            db.execute(
                """
                UPDATE jobs
                SET
                    status = 'PROCESSING',
                    attempts = attempts + 1,
                    started_at = ?,
                    error = NULL
                WHERE
                    id = ?
                    AND status = 'PENDING'
                """,
                (
                    started_at,
                    job_id,
                ),
            )

            db.commit()

            return dict(
                db.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE id = ?
                    """,
                    (job_id,),
                ).fetchone()
            )

'''

if "def claim(self):" in text:
    print("claim() already exists")
else:
    if marker not in text:
        raise SystemExit("Insertion point not found")

    text = text.replace(
        marker,
        block + marker,
        1,
    )

    p.write_text(text)
    print("OK: claim() added")
PY
```

Проверяем:

```bash
uv run python -m py_compile app/pipeline/queue.py
```

Теперь добавим **маленький тест**, который заберёт одну задачу:

```bash
uv run python - <<'PY'
from app.pipeline.queue import JobQueue

q = JobQueue("data/jobs.db")

print("BEFORE:", q.counts())

job = q.claim()

print("CLAIMED:")
print(job)

print("AFTER:", q.counts())
PY
```

Если у тебя сейчас есть одна задача `PENDING`, ожидаем:

```text
BEFORE: {'PENDING': 1}

CLAIMED:
{
    ...
    'status': 'PROCESSING',
    ...
}

AFTER: {'PROCESSING': 1}
```

**Пока больше ничего не делаем.** Если это сработает, следующим шагом сделаем `DONE/FAILED`, а уже потом сам worker создания слепка.

---

### 👤 **User** — 2026-08-15 00:56:18

все ок

---

### 🤖 **Assistant** — 2026-08-15 00:56:19

Отлично. Сейчас фундамент очереди уже работает:

```text
PENDING
   │
   │ claim()
   ▼
PROCESSING
```

И `claim()` сделан атомарно — это важно для будущих нескольких worker'ов.

### Шаг 4 — завершение задачи

Теперь добавим два метода:

```text
complete(job_id)
```

→ `PROCESSING → DONE`

и

```text
fail(job_id, error)
```

→ `PROCESSING → FAILED`

Пока **без worker'а и без параллельности**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/pipeline/queue.py")
text = p.read_text()

marker = '''    def counts(self):
'''

block = '''    def complete(self, job_id):
        """
        Mark a processing job as DONE.
        """

        finished_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE jobs
                SET
                    status = 'DONE',
                    finished_at = ?,
                    error = NULL
                WHERE
                    id = ?
                    AND status = 'PROCESSING'
                """,
                (
                    finished_at,
                    int(job_id),
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Cannot complete job {job_id}"
                )

    def fail(self, job_id, error):
        """
        Mark a processing job as FAILED.
        """

        finished_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE jobs
                SET
                    status = 'FAILED',
                    finished_at = ?,
                    error = ?
                WHERE
                    id = ?
                    AND status = 'PROCESSING'
                """,
                (
                    finished_at,
                    str(error),
                    int(job_id),
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Cannot fail job {job_id}"
                )

'''

if "def complete(self, job_id):" in text:
    print("complete()/fail() already exist")
else:
    if marker not in text:
        raise SystemExit("Insertion point not found")

    text = text.replace(
        marker,
        block + marker,
        1,
    )

    p.write_text(text)
    print("OK: complete() and fail() added")
PY
```

Проверяем синтаксис:

```bash
uv run python -m py_compile app/pipeline/queue.py
```

И посмотрим состояние нашей тестовой задачи:

```bash
python3 -m app.pipeline.queue
```

Сейчас она должна быть:

```text
PROCESSING
```

После этого **не надо вручную менять базу**. Следующим шагом протестируем:

```text
PROCESSING → DONE
```

и

```text
PROCESSING → FAILED
```

а затем уже соберём первый настоящий worker.

---

### 👤 **User** — 2026-08-15 00:56:52

давай

---

### 🤖 **Assistant** — 2026-08-15 00:56:52

Давай. Сейчас проверим оба перехода на реальных задачах.

### 1. Сначала текущая задача `PROCESSING → DONE`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
from app.pipeline.queue import JobQueue

q = JobQueue("data/jobs.db")

job = q.list("PROCESSING")

print("PROCESSING jobs:", len(job))

if job:
    job_id = job[0]["id"]
    print("Completing job:", job_id)
    q.complete(job_id)

print("COUNTS:", q.counts())
PY
```

Ожидаем:

```text
PROCESSING jobs: 1
Completing job: 1
COUNTS: {'DONE': 1}
```

### 2. Проверяем `FAILED`

Добавим временную тестовую задачу:

```bash
uv run scene-fingerprint queue-add TEST_FAIL data/input/86
```

Затем:

```bash
uv run python - <<'PY'
from app.pipeline.queue import JobQueue

q = JobQueue("data/jobs.db")

job = q.claim()

print("CLAIMED:", job["id"], job["fingerprint_id"])

q.fail(
    job["id"],
    "TEST ERROR: intentional failure"
)

print("COUNTS:", q.counts())
PY
```

Ожидаем примерно:

```text
CLAIMED: 2 TEST_FAIL
COUNTS: {'DONE': 1, 'FAILED': 1}
```

### 3. Посмотрим содержимое

```bash
uv run python - <<'PY'
from app.pipeline.queue import JobQueue

q = JobQueue("data/jobs.db")

for job in q.list():
    print(
        job["id"],
        job["fingerprint_id"],
        job["status"],
        job["attempts"],
        job["error"],
    )
PY
```

Если всё так — **очередь как механизм уже готов**:

```text
add()
  ↓
PENDING
  ↓
claim()
  ↓
PROCESSING
  ├── complete() → DONE
  └── fail()    → FAILED
```

После проверки **удалим тестовый `TEST_FAIL` из базы**, чтобы он не мешал дальнейшей разработке, и перейдём к первому настоящему worker'у, который будет вызывать существующий `FingerprintManager.create()`.

---

### 👤 **User** — 2026-08-15 00:57:34

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m py_compile app/pipeline/queue.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python - <<'PY'
from app.pipeline.queue import JobQueue

q = JobQueue("data/jobs.db")

print("BEFORE:", q.counts())

job = q.claim()

print("CLAIMED:")
print(job)

print("AFTER:", q.counts())
PY
BEFORE: {'PENDING': 1}
CLAIMED:
{'id': 1, 'source_folder': 'data/input/86', 'fingerprint_id': '86', 'status': 'PROCESSING', 'priority': 0, 'attempts': 1, 'created_at': '2026-08-14T21:55:10.990331+00:00', 'started_at': '2026-08-14T21:56:10.124070+00:00', 'finished_at': None, 'error': None}
AFTER: {'PROCESSING': 1}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/pipeline/queue.py")
text = p.read_text()

marker = '''    def counts(self):
'''

block = '''    def complete(self, job_id):
        """
        Mark a processing job as DONE.
        """

PY  print("OK: complete() and fail() added")t found")
OK: complete() and fail() added
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m py_compile app/pipeline/queue.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 -m app.pipeline.queue
Queue: data/jobs.db
Counts: {'PROCESSING': 1}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
from app.pipeline.queue import JobQueue

q = JobQueue("data/jobs.db")

job = q.list("PROCESSING")

print("PROCESSING jobs:", len(job))

if job:
    job_id = job[0]["id"]
    print("Completing job:", job_id)
    q.complete(job_id)

PYint("COUNTS:", q.counts())
PROCESSING jobs: 1
Completing job: 1
COUNTS: {'DONE': 1}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run scene-fingerprint queue-add TEST_FAIL data/input/86
[Queue] Job added: 2
[Queue] fingerprint=TEST_FAIL
[Queue] folder=data/input/86
[Queue] priority=0
[Queue] status=PENDING
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python - <<'PY'
from app.pipeline.queue import JobQueue

q = JobQueue("data/jobs.db")

job = q.claim()

print("CLAIMED:", job["id"], job["fingerprint_id"])

q.fail(
    job["id"],
    "TEST ERROR: intentional failure"
)

print("COUNTS:", q.counts())
PY
CLAIMED: 2 TEST_FAIL
COUNTS: {'DONE': 1, 'FAILED': 1}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python - <<'PY'
from app.pipeline.queue import JobQueue

q = JobQueue("data/jobs.db")

for job in q.list():
    print(
        job["id"],
        job["fingerprint_id"],
        job["status"],
        job["attempts"],
        job["error"],
    )
PY
1 86 DONE 1 None
2 TEST_FAIL FAILED 1 TEST ERROR: intentional failure
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:57:35

Отлично. Всё отработало именно так, как нужно.

Сейчас очередь имеет корректное состояние:

```text
JOB 1   fingerprint=86
        PENDING → PROCESSING → DONE

JOB 2   fingerprint=TEST_FAIL
        PENDING → PROCESSING → FAILED
```

То есть механизм очереди уже проверен на практике.

### Шаг 5 — первый настоящий worker

Теперь самое важное: worker будет брать задачу из SQLite и использовать **уже существующий** `FingerprintManager.create()`.

Логика будет такой:

```text
data/jobs.db
     │
     ▼
  PENDING
     │
   claim()
     ▼
 PROCESSING
     │
     ▼
FingerprintManager.create()
     │
     ├──────────────► DONE
     │
     └──────────────► FAILED
```

При этом пока **только один worker**. Никакого multiprocessing и очередей из Redis — сначала проверяем полностью рабочий цикл на одном слепке.

Но перед созданием worker надо удалить тестовую задачу `TEST_FAIL`, чтобы она не осталась в рабочей очереди.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import sqlite3

db = "data/jobs.db"

with sqlite3.connect(db) as conn:
    conn.execute(
        "DELETE FROM jobs WHERE fingerprint_id = ?",
        ("TEST_FAIL",),
    )

print("TEST_FAIL removed")
PY
```

Проверка:

```bash
python3 -m app.pipeline.queue
```

Должно быть:

```text
Queue: data/jobs.db
Counts: {'DONE': 1}
```

После этого **пришли только этот вывод**. Следующим сообщением сделаем `worker.py`.

---

### 👤 **User** — 2026-08-15 00:58:01

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import sqlite3

db = "data/jobs.db"

with sqlite3.connect(db) as conn:
    conn.execute(
        "DELETE FROM jobs WHERE fingerprint_id = ?",
        ("TEST_FAIL",),
    )

print("TEST_FAIL removed")
PY
TEST_FAIL removed
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 -m app.pipeline.queue
Queue: data/jobs.db
Counts: {'DONE': 1}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:58:02

Отлично. Очередь чистая, тестовая задача удалена.

Теперь делаем **первый настоящий worker**. Он будет использовать существующие `SceneEmbedder` + `FingerprintManager`, то есть мы не меняем алгоритм создания слепка.

### Шаг 5.1 — создаём `worker.py`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/pipeline/worker.py <<'PY'
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.pipeline.queue import JobQueue

class FingerprintWorker:

    def __init__(self):
        self.queue = JobQueue(
            settings.data_dir / "jobs.db"
        )

        print("[Worker] Loading SceneEmbedder...")

        self.embedder = SceneEmbedder(
            settings
        )

        self.manager = FingerprintManager(
            settings,
            self.embedder,
        )

    def run_once(self):
        job = self.queue.claim()

        if job is None:
            print("[Worker] Queue is empty")
            return False

        job_id = job["id"]
        fingerprint_id = job["fingerprint_id"]
        source_folder = Path(
            job["source_folder"]
        )

        print()
        print("=" * 60)
        print(
            f"[Worker] Job {job_id}"
        )
        print(
            f"[Worker] Fingerprint: "
            f"{fingerprint_id}"
        )
        print(
            f"[Worker] Folder: "
            f"{source_folder}"
        )
        print("=" * 60)

        try:
            self.manager.create(
                fingerprint_id,
                source_folder,
                self.embedder,
            )

        except Exception as exc:
            self.queue.fail(
                job_id,
                repr(exc),
            )

            print(
                f"[Worker] FAILED: {exc}"
            )

            return False

        self.queue.complete(
            job_id
        )

        print(
            f"[Worker] DONE: "
            f"{fingerprint_id}"
        )

        return True

def main():
    worker = FingerprintWorker()

    worker.run_once()

if __name__ == "__main__":
    main()
PY
```

Проверяем синтаксис:

```bash
uv run python -m py_compile app/pipeline/worker.py
```

### Пока НЕ запускаем worker

Сначала поставим **одну настоящую задачу**. Возьмём, например, адрес `86`, но поскольку `86_v33_fast` уже существует, создавать его под тем же ID нельзя.

Поэтому для первого теста используем:

```text
86_queue_test
```

Добавляем:

```bash
uv run scene-fingerprint queue-add 86_queue_test data/input/86
```

Проверяем:

```bash
python3 -m app.pipeline.queue
```

Должно быть примерно:

```text
Queue: data/jobs.db
Counts: {'DONE': 1, 'PENDING': 1}
```

### И только после этого запускаем:

```bash
uv run python -m app.pipeline.worker
```

Он должен:

1. загрузить DINO;
2. взять `86_queue_test`;
3. создать настоящий fingerprint;
4. сохранить его в:

```text
data/fingerprints/86_queue_test
```

5. перевести задачу:

```text
PROCESSING → DONE
```

**Запусти до `uv run python -m app.pipeline.worker` только добавление задачи и проверку `Counts`.** Это позволит нам не запустить обработку случайно дважды.

---

### 👤 **User** — 2026-08-15 00:59:11

[Worker] Job 3
[Worker] Fingerprint: 86_queue_test
[Worker] Folder: data/input/86
============================================================
[Fingerprint v3.3] Creating '86_queue_test' from 58 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/86_queue_test
[Fingerprint v3.3] global=(58, 768)
[Fingerprint v3.3] environment=(58, 640)
[Fingerprint v3.3] color=(58, 48)
[Fingerprint v3.3] spatial=(58, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED
[Worker] DONE: 86_queue_test
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:59:12

Отлично. **Первый рабочий цикл очереди полностью прошёл.**

Сейчас у нас уже работает цепочка:

```text
data/input/86
      │
      ▼
   SQLite Queue
      │
      ▼
    Worker
      │
      ▼
 DINOv2 + descriptors
      │
      ▼
data/fingerprints/86_queue_test
      │
      ▼
     DONE
```

Проверим состояние:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 -m app.pipeline.queue
```

И:

```bash
ls -lh data/fingerprints/86_queue_test
```

Должно быть `DONE` и полный набор файлов fingerprint.

### Следующий шаг

Теперь **не меняем алгоритм вообще**. Следующий шаг — сделать worker, который обрабатывает **не одну задачу, а всю очередь последовательно**:

```text
PENDING
   ↓
claim()
   ↓
create fingerprint
   ↓
DONE
   ↓
следующая задача
   ↓
...
```

А затем уже можно будет добавить запуск нескольких независимых worker-процессов, чтобы использовать RTX 3060 максимально эффективно.

Но сначала делаем **один стабильный batch-worker**. Это будет основа всей будущей пакетной обработки.

---

### 👤 **User** — 2026-08-15 00:59:40

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

python3 -m app.pipeline.queue
Queue: data/jobs.db
Counts: {'DONE': 2}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ls -lh data/fingerprints/86_queue_test
total 584K
-rw-rw-r-- 1 alexice alexice 3.2K Aug 15 00:59 centroid.npy
-rw-rw-r-- 1 alexice alexice  11K Aug 15 00:59 color_embeddings.npy
-rw-rw-r-- 1 alexice alexice 175K Aug 15 00:59 embeddings.npy
-rw-rw-r-- 1 alexice alexice 146K Aug 15 00:59 environment_embeddings.npy
-rw-rw-r-- 1 alexice alexice 175K Aug 15 00:59 faiss.index
-rw-rw-r-- 1 alexice alexice 2.0K Aug 15 00:59 metadata.json
-rw-rw-r-- 1 alexice alexice  192 Aug 15 00:59 representative_indices.npy
-rw-rw-r-- 1 alexice alexice  49K Aug 15 00:59 representatives.npy
-rw-rw-r-- 1 alexice alexice 7.4K Aug 15 00:59 spatial_embeddings.npy
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:59:41

Да, всё отлично. **Первый этап пакетного контура работает корректно.**

Сейчас подтверждено:

- SQLite очередь работает.
- `claim()` переводит задачу в `PROCESSING`.
- Worker создаёт fingerprint.
- Все файлы сохраняются корректно.
- Worker переводит задачу в `DONE`.
- В очереди сейчас: **2 DONE, 0 PENDING, 0 FAILED**.
- `86_queue_test` содержит полноценный v3.3 fingerprint: 58 изображений, DINO 768 + environment/color/spatial.

Теперь переходим к **следующему маленькому шагу — batch worker**, без каких-либо изменений алгоритма распознавания или создания слепков.

### 1. Заменяем `run_once()` на обработку всей очереди

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/pipeline/worker.py <<'PY'
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.pipeline.queue import JobQueue

class FingerprintWorker:

    def __init__(self):
        self.queue = JobQueue(
            settings.data_dir / "jobs.db"
        )

        print("[Worker] Loading SceneEmbedder...")

        self.embedder = SceneEmbedder(
            settings
        )

        self.manager = FingerprintManager(
            settings,
            self.embedder,
        )

    def run_once(self):
        job = self.queue.claim()

        if job is None:
            return False

        job_id = job["id"]
        fingerprint_id = job["fingerprint_id"]
        source_folder = Path(
            job["source_folder"]
        )

        print()
        print("=" * 60)
        print(f"[Worker] Job {job_id}")
        print(f"[Worker] Fingerprint: {fingerprint_id}")
        print(f"[Worker] Folder: {source_folder}")
        print("=" * 60)

        try:
            self.manager.create(
                fingerprint_id,
                source_folder,
                self.embedder,
            )

            self.queue.complete(
                job_id
            )

            print(
                f"[Worker] DONE: {fingerprint_id}"
            )

            return True

        except Exception as exc:
            self.queue.fail(
                job_id,
                repr(exc),
            )

            print(
                f"[Worker] FAILED: "
                f"{fingerprint_id}: {exc}"
            )

            return True

    def run(self):
        print("[Worker] Starting batch processing")

        processed = 0

        while True:
            result = self.run_once()

            if not result:
                break

            processed += 1

        print()
        print("=" * 60)
        print(
            f"[Worker] Batch complete. "
            f"Processed: {processed}"
        )
        print("=" * 60)

def main():
    worker = FingerprintWorker()
    worker.run()

if __name__ == "__main__":
    main()
PY
```

Проверяем:

```bash
uv run python -m py_compile app/pipeline/worker.py
```

### 2. Сейчас тестируем на двух новых адресах

Например:

```bash
uv run scene-fingerprint queue-add 91_queue_test data/input/91
uv run scene-fingerprint queue-add 92_queue_test data/input/92
```

Проверяем:

```bash
python3 -m app.pipeline.queue
```

Ожидаем:

```text
DONE: 2
PENDING: 2
```

### 3. Запускаем batch

```bash
time uv run python -m app.pipeline.worker
```

Он должен **одним запуском** обработать оба задания:

```text
91_queue_test → DONE
92_queue_test → DONE
```

И после этого:

```bash
python3 -m app.pipeline.queue
```

должно показать:

```text
DONE: 4
```

После этого у нас будет уже нормальный фундамент для следующего шага — **несколько worker'ов + оптимальная загрузка RTX 3060**, но пока туда не лезем.

---

### 👤 **User** — 2026-08-15 01:03:04

real	0m16.701s
user	0m20.898s
sys	0m5.879s
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 -m app.pipeline.queue
Queue: data/jobs.db
Counts: {'DONE': 4}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:03:06

Отлично. **Batch-worker отработал правильно.**

И самое важное — время:

```text
2 слепка: 16.7 сек
```

То есть сейчас в среднем примерно **8.3 сек на один слепок** для каталогов `91` и `92`.

Состояние очереди:

```text
DONE: 4
PENDING: 0
PROCESSING: 0
FAILED: 0
```

Получили именно то, что хотели на первом этапе:

```text
SQLite Queue
    ↓
Batch Worker
    ↓
последовательная обработка
    ↓
FingerprintManager
    ↓
DONE
```

**Пока ничего больше не улучшаем.** Следующим шагом логично будет уже проверить batch на реальном наборе `83–95`, а затем отдельно заняться параллельными worker'ами и загрузкой RTX 3060.

---

### 👤 **User** — 2026-08-15 01:03:21

давай

---

### 🤖 **Assistant** — 2026-08-15 01:03:22

Да. Теперь проверим **реальный batch 83–95**, но уже без создания дубликатов для тех слепков, которые существуют.

У нас сейчас:

- `83_v33` → есть
- `84_v33` → есть
- `85_v33` → есть
- `86_v33_fast` → есть
- …
- `95_v33_fast` → есть

Поэтому сначала сделаем **чистый тест очереди на новых ID**, чтобы не трогать существующие слепки.

### 1. Добавляем 83–95 в очередь

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for id in {83..95}; do
    uv run scene-fingerprint queue-add "${id}_batch_test" "data/input/$id"
done
```

Проверяем:

```bash
python3 -m app.pipeline.queue
```

Должно стать:

```text
DONE: 4
PENDING: 13
```

### 2. Запускаем весь batch

```bash
time uv run python -m app.pipeline.worker
```

**Это уже хороший реальный тест производительности.**

Не прерывай процесс — пусть обработает все 13 каталогов последовательно.

### 3. После завершения

```bash
python3 -m app.pipeline.queue
```

Ожидаем:

```text
DONE: 17
PENDING: 0
PROCESSING: 0
FAILED: 0
```

И проверим созданные слепки:

```bash
for id in {83..95}; do
    test -d "data/fingerprints/${id}_batch_test" \
        && echo "$id OK" \
        || echo "$id MISSING"
done
```

### 4. И главное — покажи мне итоговый `real`

Например:

```text
real    1m45s
user    ...
sys     ...
```

По нему посчитаем:

**среднее время на один каталог → производительность batch → сколько каталогов/час можно обработать.**

После этого уже будет понятно, **есть ли вообще смысл сейчас распараллеливать**, или сначала нужно оптимизировать загрузку DINO/GPU.

**Существующие `83_v33`–`95_v33_fast` при этом не затрагиваем.** Новые результаты будут в `*_batch_test`.

---

### 👤 **User** — 2026-08-15 01:06:41

real	1m27.520s
user	2m17.485s
sys	0m24.119s
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 -m app.pipeline.queue
Queue: data/jobs.db
Counts: {'DONE': 17}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:06:43

Отлично. Тест получился чистый:

- **13 слепков** обработаны.
- `DONE: 17` — все задачи очереди завершены.
- `PENDING: 0`
- `PROCESSING: 0`
- `FAILED: 0`
- Общее время: **1:27.52**
- Среднее: **≈ 6.73 сек на один слепок**.

Причём это уже хороший показатель для текущей последовательной схемы.

### Следующий шаг

Теперь я бы **не трогал создание слепка**, а сделал следующий слой — **несколько worker-процессов**, которые будут брать задачи из одной SQLite-очереди.

То есть:

```text
                 SQLite Queue
                /     |      \
               ↓      ↓       ↓
          Worker 1 Worker 2 Worker 3
               \      |      /
                \     |     /
                  RTX 3060
```

Но здесь есть важный момент: **не надо сразу запускать 3 DINO-модели на одной RTX 3060**. Скорее всего, они начнут конкурировать за VRAM и мы можем получить обратный эффект.

Поэтому следующий эксперимент сделаем аккуратно:

**2 worker-процесса → измеряем время → сравниваем с 87.5 сек.**

Если ускорения нет — оставляем один GPU worker и оптимизируем CPU/декодирование изображений.

Если есть — подбираем оптимальное количество.

И только после этого будем делать нормальный production-режим очереди.

---

### 👤 **User** — 2026-08-15 01:08:25

на самом деле текущий результат вполне устривает. наверно не стоит усложнять - ведь если 7 сек на один слепок - это к примеру 100 слепков - 10 минут. вполне приемлемое время

---

### 🤖 **Assistant** — 2026-08-15 01:08:25

Да, **полностью согласен**. В нашем случае усложнять параллельностью сейчас не стоит.

Текущая производительность:

- ~**6.7 сек / слепок**
- **100 слепков ≈ 11 минут**
- **500 слепков ≈ 56 минут**
- **1000 слепков ≈ 1 ч 52 мин**

Причём это уже включает весь цикл создания fingerprint, а не только один этап.

И главное — у нас теперь есть **очередь**, поэтому не требуется запускать каждый слепок вручную:

```text
каталоги
   ↓
SQLite Queue
   ↓
Batch Worker
   ↓
6–7 сек / слепок
   ↓
готовые fingerprints
```

### Я бы зафиксировал текущую архитектуру

**Не трогаем:**

- DINOv2
- структуру fingerprint v3.3
- веса `0.70 / 0.20 / 0.07 / 0.03`
- CPU workers = 6
- один GPU worker
- текущий batch processing

**Оставляем очередь как основу будущей системы.**

Она нам всё равно пригодится, даже без параллелизации:

- можно поставить 1000 адресов в очередь;
- worker обработает их последовательно;
- при ошибке конкретная задача будет `FAILED`;
- уже обработанные останутся `DONE`;
- можно продолжить после перезапуска;
- не нужно держать весь процесс в голове.

То есть мы получили **достаточно быстрый и при этом простой pipeline**.

Я бы теперь переключился с оптимизации скорости на **качество самих слепков и распознавания** — это сейчас гораздо ценнее.

---

### 👤 **User** — 2026-08-15 01:08:51

продолжаем

---

### 🤖 **Assistant** — 2026-08-15 01:08:52

Продолжаем. Я бы сейчас **не менял производительность**, а довёл очередь до практического рабочего режима.

Следующий шаг — сделать команду, которая позволяет **одним запуском поставить в очередь сразу диапазон каталогов**, например:

```text
83–95
```

И затем worker обработает их.

Сейчас у нас добавление выглядит так:

```bash
uv run scene-fingerprint queue-add 86 data/input/86
```

Для сотен адресов это неудобно.

### Шаг: `queue-batch-add`

Добавим команду:

```bash
uv run scene-fingerprint queue-batch-add 83 95
```

Она должна автоматически:

1. пройти `data/input/83` ... `data/input/95`;
2. проверить наличие фотографий;
3. создать задачи;
4. пропустить уже существующие fingerprint;
5. показать итог:

```text
[Queue] Added: 10
[Queue] Skipped existing: 3
[Queue] Missing folders: 0
```

И **никаких изменений в существующем алгоритме создания слепка**.

Если такой следующий шаг устраивает, можем сразу сделать его командами в терминале.

---

### 👤 **User** — 2026-08-15 01:09:11

продолжаем

---

