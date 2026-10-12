## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 🤖 **Assistant** — 2026-08-18 23:18:20

Да. Это **очень важное разделение**, и я бы сейчас его зафиксировал как основу новой архитектуры.

У нас должны быть **два разных ID**, и смешивать их нельзя.

### 1. `photo_id` — внутренний ID фотографии

Это ID, который появляется **сразу при постановке фотографии в обработку**.

Он не означает адрес.

Например:

```text
photo_id = P000001
photo_id = P000002
photo_id = P000003
```

Он является **псевдонимом/ключом фотографии** для всей системы.

Именно по нему связываются:

```text
файл
→ DINO
→ Hybrid
→ Qwen
→ OCR
→ метаданные
→ база
→ результаты
```

Причём совершенно неважно:

- как называется файл;
- где он физически находится;
- был ли он перемещён;
- какой адрес ему потом назначит DINO.

---

### 2. `address_id` — результат DINO

После DINO появляется уже другой идентификатор:

```text
photo_id = P000001
address_id = 78
```

То есть:

```text
P000001
   │
   ├── source_path = /input/IMG_8472.JPG
   │
   ├── DINO
   │      └── address_id = 78
   │
   └── Qwen
          └── результаты привязаны к P000001
```

И именно **`address_id` отображается в гриде как адрес**.

---

## Тогда структура получается такая

```text
                    ФОТО
                      │
                      ▼
                 photo_id
                 P000001
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
        DINO                     QWEN
          │                       │
          ▼                       │
     address_id                   │
         78                       │
          │                       │
          └───────────┬───────────┘
                      ▼
                   DATABASE
                      │
                      ▼
                    GRID
                 Адрес: 78
```

### И это решает сразу несколько проблем

Например, сегодня файл:

```text
IMG_8472.JPG
```

лежит:

```text
/input/2026/08/
```

завтра его физическое расположение изменилось, а имя стало:

```text
Комарова13_06.JPG
```

Но:

```text
photo_id = P000001
```

остаётся тем же идентификатором записи.

---

## Для Qwen это особенно важно

Qwen **не должен идентифицировать фотографию по имени файла**.

Он получает:

```text
photo_id = P000001
source_path = ...
address_id = 78
```

и записывает свои результаты:

```text
photo_id = P000001
qwen_result = ...
```

Поэтому потом в базе:

```text
P000001
├── файл
├── address_id = 78
├── DINO result
├── Hybrid result
└── Qwen result
```

Всё однозначно сводится в одну запись.

---

## И ещё один нюанс

Я бы даже **не называл первый ID `id`**.

Чтобы через несколько месяцев не было путаницы:

```text
photo_id       ← внутренний постоянный идентификатор
address_id     ← адрес, назначенный DINO
```

А в базе:

```text
photo_id
source_path
filename
file_hash

dino_status
address_id
dino_version

qwen_status
qwen_version
qwen_result
```

Позже можно добавить:

```text
ocr_status
ocr_result
```

и т.д.

---

### Грид

Грид вообще не должен знать про внутреннюю механику.

Он получает:

```text
photo_id: P000001
address_id: 78
preview: ...
```

и показывает:

```text
┌──────────────────┐
│                  │
│      PHOTO       │
│                  │
├──────────────────┤
│ Адрес: 78        │
│ P000001          │
└──────────────────┘
```

При этом `P000001` пользователю можно вообще **не показывать**, он нужен системе.

**Итого: `photo_id` — сквозной ключ всей обработки. `address_id` — результат DINO и пользовательский адрес в гриде.**

Это разделение я бы зафиксировал до того, как начнём менять код.

---

### 👤 **User** — 2026-08-18 23:19:27

ок

---

### 🤖 **Assistant** — 2026-08-18 23:19:28

Ок, фиксируем.

**Базовая модель:**

- `photo_id` — внутренний сквозной ID фотографии, создаётся при поступлении в обработку.
- `address_id` — ID адреса, который назначает DINO/Hybrid.
- `photo_id` связывает результаты DINO, Qwen и будущих модулей независимо от имени и расположения файла.
- `address_id` используется для отображения адреса в гриде.
- Фотографии физически не сортируются и не копируются.
- DINO и Qwen работают независимо.
- Qwen получает фотографию только после появления её финального `address_id`.
- Обработка возобновляется после остановки.
- Уже обработанное по умолчанию пропускается.
- Можно выбрать повторную обработку — отдельно для DINO/Qwen или для всех.

Следующий шаг — посмотреть оставшиеся строки `run_hybrid_v12.py` (`530–760`), чтобы аккуратно отделить существующую frozen-логику от нового слоя очереди/индекса.

---

### 👤 **User** — 2026-08-18 23:20:29

Qwen получает фотографию после присовения photo_id - квену все равно какой там адрес, он только описывает и это описание потом подтягивается к файлук в гриде на основании этого phot id

---

### 🤖 **Assistant** — 2026-08-18 23:20:29

Да, именно. Тогда я поправляю предыдущую схему: **Qwen вообще не зависит от `address_id`**.

Правильная последовательность:

```text
ФОТО
 │
 ▼
создаём photo_id
 │
 ├──────────────► QWEN
 │                  │
 │                  ▼
 │              описание
 │
 ▼
DINO / Hybrid
 │
 ▼
address_id
 │
 ▼
ГРИД
```

### Что это означает

Как только фото получило:

```text
photo_id = P000001
```

оно уже может уходить в Qwen.

Qwen получает примерно:

```text
photo_id = P000001
source_path = /input/whatever/IMG_1234.JPG
```

Ему **совершенно не нужен `address_id`**.

Qwen делает:

```text
P000001
   ↓
описание / признаки / результаты Qwen
```

и сохраняет результат, например:

```text
photo_id = P000001
qwen_status = DONE
qwen_description = "..."
```

---

### DINO идёт независимо

DINO работает с тем же:

```text
photo_id = P000001
```

и в результате добавляет:

```text
address_id = 78
```

Получается единая запись:

```text
P000001
│
├── source_path
├── file_hash
│
├── DINO
│    ├── status = DONE
│    └── address_id = 78
│
└── QWEN
     ├── status = DONE
     └── description = "..."
```

---

### А грид собирает всё по `photo_id`

Гриду не надо связывать данные по имени файла или пути.

Он делает условно:

```text
photo_id = P000001
```

и получает:

```text
фотография
+
address_id = 78
+
Qwen description
+
прочие метаданные
```

И показывает:

```text
┌─────────────────────┐
│                     │
│       ФОТО          │
│                     │
├─────────────────────┤
│ Адрес: 78           │
│                     │
│ Описание Qwen:      │
│ ...                 │
└─────────────────────┘
```

Причём если DINO ещё не закончил:

```text
Адрес: —
Описание: ...
```

А когда DINO присвоит адрес — грид автоматически увидит:

```text
Адрес: 78
```

**без повторной обработки Qwen.**

Это даже лучше для нашей архитектуры: `photo_id` становится настоящим **первичным ключом всей фотобазы**, а `address_id` — всего лишь одним из результатов обработки.

---

### 👤 **User** — 2026-08-18 23:21:11

в гриде отображаются файлы тольк опосле присвоения адреса

---

### 🤖 **Assistant** — 2026-08-18 23:21:12

Да. Тогда фиксируем ещё точнее.

### Жизненный цикл фотографии

```text
INPUT
  │
  ▼
photo_id
  │
  ├──────────────► Qwen
  │                  │
  │                  ▼
  │              описание
  │
  ▼
DINO / Hybrid
  │
  ▼
address_id
  │
  ▼
ГРИД
```

То есть:

**`photo_id` создаётся первым.**

После этого **Qwen уже может работать**.

DINO независимо определяет:

```text
photo_id → address_id
```

И **только после появления `address_id` фотография становится видимой в гриде**.

### Поэтому состояния могут быть такими

```text
photo_id создан
        │
        ├── Qwen: WAITING / PROCESSING / DONE
        │
        └── DINO: WAITING / PROCESSING
                         │
                         ▼
                    address_id
                         │
                         ▼
                    GRID = SHOW
```

Если Qwen закончил первым:

```text
Qwen = DONE
DINO = PROCESSING
GRID = НЕ ПОКАЗЫВАЕТ
```

Если DINO закончил первым:

```text
DINO = DONE
address_id = 78
Qwen = PROCESSING

GRID = ПОКАЗЫВАЕТ
```

В гриде при этом описание Qwen сначала может быть:

```text
Описание: обрабатывается...
```

а после завершения Qwen оно автоматически подтягивается по `photo_id`.

И главное: **видимость в гриде определяется исключительно наличием `address_id`, а не состоянием Qwen.**

Это очень чисто разделяет три вещи:

- `photo_id` — кто это за фотография;
- `address_id` — куда её отнести в фотобазе;
- Qwen-результат — что находится/происходит на фотографии.

---

### 👤 **User** — 2026-08-18 23:21:46

далее

---

### 🤖 **Assistant** — 2026-08-18 23:21:49

Далее я бы зафиксировал **структуру данных и очереди**, прежде чем трогать UI. Тогда код технического окна будет строиться уже на правильной модели.

### 1. Одна запись на фотографию

Например:

```text
photo_id
source_path
filename
file_hash

dino_status
address_id
dino_result

qwen_status
qwen_result

visible_in_grid
```

Где:

```text
visible_in_grid = True
```

только если:

```text
address_id != NULL
```

Отдельное поле `visible_in_grid` даже можно вообще не хранить, а вычислять:

```text
address_id есть → показываем
address_id нет → не показываем
```

Я бы предпочёл именно так — меньше риска рассинхронизации.

---

### 2. При поступлении фотографии

Создаётся:

```text
P000001
```

и сразу:

```text
DINO = WAITING
QWEN = WAITING
address_id = NULL
```

Qwen может взять её:

```text
QWEN → PROCESSING
```

DINO одновременно:

```text
DINO → PROCESSING
```

---

### 3. DINO закончил

Получаем:

```text
photo_id = P000001
address_id = 78
dino_status = DONE
```

**В этот момент фото появляется в гриде.**

Неважно, что Qwen:

```text
PROCESSING
```

или даже:

```text
ERROR
```

Фото всё равно должно быть в гриде, потому что адрес уже известен.

---

### 4. Qwen закончил

Просто обновляет ту же запись:

```text
photo_id = P000001
qwen_status = DONE
qwen_result = ...
```

Грид находит:

```text
P000001
```

и подтягивает новое описание.

---

## 5. Очереди

Получается две независимые очереди.

### DINO queue

```text
WAITING
   ↓
PROCESSING
   ↓
DONE + address_id
```

### Qwen queue

```text
WAITING
   ↓
PROCESSING
   ↓
DONE
```

Они связаны только через `photo_id`.

**Никакой зависимости Qwen от адреса нет.**

---

## 6. Возобновление

При остановке:

```text
P001 DINO DONE
P002 DINO DONE
P003 DINO PROCESSING
P004 DINO WAITING
```

После нового запуска:

```text
P001 → пропустить
P002 → пропустить
P003 → проверить/повторить
P004 → продолжить
```

То же независимо для Qwen.

---

## 7. Очень важный момент с «обработать заново»

Здесь я бы сделал выбор **перед запуском каждой ветки**:

```text
DINO
○ Продолжить
○ Обработать заново

QWEN
○ Продолжить
○ Обработать заново
```

И общий вариант:

```text
☐ Применить к обоим
```

Тогда, например:

```text
DINO → продолжить
Qwen → обработать заново
```

совершенно нормальный сценарий.

---

## 8. И только после этого UI

Техническое окно будет отражать именно эти состояния:

```text
ФОТООТЧЁТ

Источник [________________] [Выбрать]
Результаты [________________________]

[ ▶ ЗАПУСТИТЬ ] [ ■ ОСТАНОВИТЬ ]

🟠 ОБРАБОТКА

DINO v33 / Hybrid v12
[▶ Запустить] [■ Остановить]

██████████████░░░░░░  142 / 200
Готово: 142
Ошибки: 0

Qwen3-VL 4B
[▶ Запустить] [■ Остановить]

████████░░░░░░░░░░░░  83 / 200
Готово: 83
В очереди: 59
```

А **грид вообще не должен быть частью этого процесса управления**. Он просто читает базу и показывает фотографии, у которых уже появился `address_id`.

---

Следующий технический шаг я бы сделал таким: **посмотреть существующие `app/pipeline/queue.py` и `app/pipeline/worker.py`**. У тебя там уже есть `PROCESSING`, `DONE`, `FAILED`, поэтому вполне возможно, что нам **не нужно изобретать новую систему очередей с нуля** — можно адаптировать существующую.

---

### 👤 **User** — 2026-08-18 23:22:57

давай

---

### 🤖 **Assistant** — 2026-08-18 23:22:57

> **Remembering**
>
>
> **Reviewed scene fingerprint pipeline, queue handling, model plans, and photo resumption**
>
> 
>
> Worked for 14s

Да. Но здесь важный момент: **я не буду сейчас менять существующие `queue.py` и `worker.py` вслепую**.

У нас уже есть старые `app/pipeline/queue.py` и `app/pipeline/worker.py`, но они относятся к существующей очереди проекта. Ранее мы отдельно фиксировали, что эту систему пока не трогаем. Поэтому сначала посмотрим их фактическое содержимое и решим, **используем ли её как основу или только возьмём из неё идеи**.

На твоём `NEURO` выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "================ QUEUE ================"
sed -n '1,320p' app/pipeline/queue.py

echo
echo "================ WORKER ================"
sed -n '1,280p' app/pipeline/worker.py
```

И пришли вывод.

После этого разберём именно в таком порядке:

1. что из существующей очереди можно сохранить;
2. где добавить `photo_id`;
3. как разделить состояния **DINO** и **Qwen**;
4. как сделать `STOP → CONTINUE`;
5. как сделать `SKIP / REPROCESS`;
6. как Qwen забирает фото сразу после появления `photo_id`;
7. как DINO независимо позже добавляет `address_id`;
8. и только потом переделаем техническое окно.

**Существующую frozen-логику DINO v33 / Hybrid v12 при этом не трогаем.**

---

### 👤 **User** — 2026-08-18 23:23:38

args = parser.parse_args()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "================ QUEUE ================"
sed -n '1,320p' app/pipeline/queue.py

echo
echo "================ WORKER ================"
sed -n '1,280p' app/pipeline/worker.py
================ QUEUE ================
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

    def claim(self):
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

    def complete(self, job_id):
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

================ WORKER ================
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:23:39

Да, теперь картина ясная.

**Эту `JobQueue` не стоит переделывать под новую обработку фотографий напрямую.** Она сейчас является очередью **создания fingerprint**, а не очередью обработки отдельных фотографий.

Но её принцип нам подходит.

### Что сохраняем

Из существующей очереди полезны:

- SQLite;
- `PENDING`;
- `PROCESSING`;
- `DONE`;
- `FAILED`;
- `attempts`;
- timestamps;
- `error`;
- атомарный `claim()`.

### Что не подходит

Сейчас запись очереди:

```text
source_folder
fingerprint_id
```

А нам нужна запись **конкретной фотографии**:

```text
photo_id
source_path
file_hash
```

И самое главное — **две независимые обработки**.

---

# Новая модель

Я бы сделал отдельную БД/таблицу для photo processing, например:

```text
data/processing/processing.db
```

Не трогая существующий:

```text
data/jobs.db
```

В ней одна основная запись фотографии:

```text
photos
────────────────────────────────
photo_id
source_path
filename
file_hash
created_at

dino_status
address_id
dino_result
dino_error

qwen_status
qwen_result
qwen_error
```

И отдельные состояния:

```text
DINO:
PENDING
PROCESSING
DONE
FAILED

QWEN:
PENDING
PROCESSING
DONE
FAILED
```

---

# Почему именно так

Например:

```text
P000123
```

### DINO

```text
P000123
DINO = DONE
address_id = 83
```

### Qwen

```text
P000123
QWEN = PROCESSING
```

Фото **уже показывается в гриде**, потому что:

```text
address_id = 83
```

Qwen потом заканчивает:

```text
P000123
QWEN = DONE
description = ...
```

Грид просто подтягивает описание по:

```text
photo_id = P000123
```

---

# А главное — STOP

Это позволит нормально сделать твою кнопку:

**`■ ОСТАНОВИТЬ`**

Она не должна убивать базу или удалять очередь.

Например:

```text
P000001  DINO DONE
P000002  DINO DONE
P000003  DINO PROCESSING
P000004  DINO PENDING

P000001  QWEN DONE
P000002  QWEN PROCESSING
P000003  QWEN PENDING
P000004  QWEN PENDING
```

Нажали STOP.

Текущие процессы останавливаются.

После нового запуска система видит состояния и продолжает.

---

# Но есть ещё важная вещь

Для DINO нельзя просто делать:

```text
P000001 → обработали → сразу окончательный address
P000002 → обработали → сразу окончательный address
```

потому что твой **Hybrid v12 использует соседей**.

То есть текущая frozen-логика:

```text
DINO TOP-5
       ↓
margin
       ↓
sub
       ↓
neighbor
       ↓
Hybrid
       ↓
address_id
```

должна остаться.

Поэтому я бы разделил DINO на два внутренних этапа:

```text
DINO RECOGNITION
        ↓
recognition result
        ↓
HYBRID
        ↓
address_id
```

Но для Qwen этого ожидания нет.

---

# И получается настоящая параллельность

```text
                    PHOTO
                      │
                      ▼
                  photo_id
                      │
              ┌───────┴───────┐
              │               │
              ▼               ▼
            DINO             QWEN
              │               │
              │               └──→ description
              │
              ▼
          Hybrid v12
              │
              ▼
          address_id
              │
              ▼
             GRID
```

Qwen может идти **сразу после создания `photo_id`**.

DINO может идти независимо.

Грид ждёт только `address_id`.

---

# И UI теперь тоже становится понятным

Главная:

```text
┌─────────────────────────────────────────────┐
│            ФОТООБРАБОТКА                    │
│                                             │
│ Источник [ /data/input/daily ] [Выбрать]   │
│ Результаты [ /data/output/daily ]          │
│                                             │
│       [ ▶ ЗАПУСТИТЬ ] [ ■ ОСТАНОВИТЬ ]    │
│                                             │
│                 🟠 ИДЁТ ОБРАБОТКА          │
└─────────────────────────────────────────────┘
```

Под ней:

```text
DINO v33 / Hybrid v12

[ ▶ Запустить ] [ ■ Остановить ]

████████████░░░░░░░░  142 / 200
Готово: 142   В работе: 1   Ошибки: 0
```

И отдельно:

```text
Qwen3-VL 4B

[ ▶ Запустить ] [ ■ Остановить ]

████████░░░░░░░░░░░░  83 / 200
Готово: 83   В работе: 1   В очереди: 116
```

### Главный индикатор

Твоя идея с цветом тоже хорошо ложится:

- 🟢 **зелёный** — готов / ничего не выполняется;
- 🟠 **мигающий** — хотя бы один процесс работает;
- 🔴 **красный** — ошибка;
- после STOP — зелёный, но состояние очереди сохраняется.

И главное: **главная кнопка управляет обеими ветками**, а индивидуальные кнопки позволяют управлять DINO и Qwen отдельно.

---

## Следующий шаг

Теперь уже можно смотреть не `queue.py`, а **как именно сейчас Qwen получает входные фотографии и что сохраняет**.

Покажи:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,360p' scripts/qwen4b_output_v01.py
```

Это сейчас самый важный следующий файл, потому что нам нужно сделать так, чтобы Qwen перестал ждать физически отсортированный `OUTPUT/TIMESTAMP/address/` и работал с **индексом фотографий по `photo_id`**.

---

### 👤 **User** — 2026-08-18 23:24:58

пауза - желтый

---

### 🤖 **Assistant** — 2026-08-18 23:24:58

Да. Тогда фиксируем состояния главного индикатора так:

- 🟢 **Зелёный** — готов / ожидание.
- 🟠 **Мигающий оранжевый** — обработка идёт.
- 🟡 **Жёлтый** — **пауза**.
- 🔴 **Красный** — ошибка.

При **STOP** я бы разделил два понятия:

**Пауза**
- текущая обработка корректно останавливается;
- незавершённые фото остаются в очереди;
- ничего не теряется;
- главный индикатор → 🟡;
- кнопка становится **`▶ ПРОДОЛЖИТЬ`**.

**Ошибка**
- процесс завершился аварийно;
- главный индикатор → 🔴;
- показываем ошибку;
- после устранения можно выбрать **продолжить** или **обработать заново**.

То есть:

```text
🟢 ГОТОВ

🟠 ИДЁТ ОБРАБОТКА
   ↓
🟡 ПАУЗА
   ↓
🟠 ПРОДОЛЖЕНИЕ
   ↓
🟢 ГОТОВО
```

А при аварии:

```text
🟠 ИДЁТ ОБРАБОТКА
   ↓
🔴 ОШИБКА
```

И это состояние должно быть **отдельно для DINO и Qwen**, плюс один общий индикатор сверху.

---

### 👤 **User** — 2026-08-18 23:25:12

ок

---

### 🤖 **Assistant** — 2026-08-18 23:25:13

Ок, фиксируем эту схему.

Следующий шаг — **Qwen `qwen4b_output_v01.py`**, чтобы переделывать архитектуру параллельной обработки уже без физической сортировки и с `photo_id`.

Команда:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,360p' scripts/qwen4b_output_v01.py
```

Пришли вывод — разберём его и определим, что именно нужно оставить, а что изменить.

---

### 👤 **User** — 2026-08-18 23:25:37

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,360p' scripts/qwen4b_output_v01.py
#!/usr/bin/env python3

import argparse
import base64
import json
import os
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
import requests

# ============================================================
# CONFIG
# ============================================================

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

MODEL = "qwen3-vl:4b-instruct"
OLLAMA_URL = "http://localhost:11434/api/chat"

NUM_CTX = 16384
TEMPERATURE = 0

# ============================================================
# PROMPT
# ============================================================

PROMPT = r"""
Ты анализируешь фотографию с улицы для базы наружной рекламы.

Найди рекламный баннер и верни ТОЛЬКО JSON.
Не добавляй пояснений вне JSON.
Не повторяй информацию.
Не придумывай отсутствующую информацию.

Формат:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "banner_type": "видеоэкран",

  "environment": {
    "weather": "",
    "precipitation": "",
    "lighting": ""
  },

  "image_quality": {
    "overall": "",
    "sharpness": "",
    "exposure": "",
    "visibility": "",
    "banner_visible": true,
    "banner_readability": "",
    "motion_blur": false,
    "occlusion": false
  },

  "camera_view": {
    "distance": "",
    "angle": ""
  },

  "analysis_quality": {
    "banner_analysis": "",
    "text_analysis": ""
  },

  "confidence": 0
}

БАННЕР:
client — компания, организация или заказчик.
brand — торговая марка, имя кандидата или рекламируемый бренд.
category — категория рекламы.
text — читаемые надписи на баннере.
colors — основные цвета самого баннера.
objects — основные изображения и предметы НА БАННЕРЕ.
description — краткое описание композиции баннера, максимум 300 символов.
banner_type — на данном этапе "видеоэкран".

ОКРУЖЕНИЕ:
Определи ТОЛЬКО:
weather — солнечно / пасмурно / облачно / туман / неизвестно.
precipitation — нет / дождь / снег / мокрый снег / неизвестно.
lighting — яркий день / дневной свет / сумерки / ночь / искусственное освещение / неизвестно.

Не описывай окружающую сцену.
Не описывай здания, дороги, автомобили, автобусы, людей,
дорожные знаки, провода или растительность.

КАЧЕСТВО:
Оцени только качество фотографии и видимость баннера.

overall — хорошее / удовлетворительное / плохое.
sharpness — резкое / слегка размыто / сильно размыто / неизвестно.
exposure — нормальная / пересвечено / недоэкспонировано / очень тёмное / неизвестно.
visibility — хорошо виден / частично виден / плохо виден / не виден.
banner_visible — true или false.
banner_readability — высокая / средняя / низкая / невозможно определить.
motion_blur — true или false.
occlusion — true или false.

КАМЕРА:
distance — далеко / средняя дистанция / близко / неизвестно.
angle — прямо / слева / справа / сверху / снизу / косой ракурс / неизвестно.

Если баннер не виден:
client = ""
brand = ""
category = ""
text = []
colors = []
objects = []
description = ""
banner_visible = false

Массивы должны содержать только действительно важные элементы.
Не более 10 элементов в каждом массиве.
Не повторяй элементы.

confidence — уверенность в анализе от 0 до 100.
"""

# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def claim_photo(conn):
    """
    Берёт одну фотографию из очереди Qwen.

    Для Qwen источником всегда является source_path.
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:

        cur.execute(
            """
            SELECT
                id,
                photo_id,
                source_path,
                filename
            FROM photos
            WHERE qwen_status = 'pending'
              AND source_path IS NOT NULL
              AND source_path <> ''
            ORDER BY id
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )

        row = cur.fetchone()

        if row is None:
            conn.commit()
            return None

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (row["id"],),
        )

        conn.commit()

        return row

def mark_done(conn, photo_id, result, elapsed):
    """
    Сохраняет Qwen-результат непосредственно в PostgreSQL.
    """

    text_json = result.get("text", [])
    colors_json = result.get("colors", [])
    objects_json = result.get("objects", [])
    environment_json = result.get("environment", {})
    image_quality_json = result.get("image_quality", {})
    camera_view_json = result.get("camera_view", {})
    scene_objects_json = result.get("objects", [])
    analysis_quality_json = result.get("analysis_quality", {})

    raw_json = dict(result)

    # В БД служебное время отдельно.
    raw_json.pop("_time_sec", None)

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'done',

                client = %s,
                brand = %s,
                category = %s,
                description = %s,
                confidence = %s,

                qwen_time_sec = %s,

                text_json = %s::jsonb,
                colors_json = %s::jsonb,
                objects_json = %s::jsonb,
                environment_json = %s::jsonb,
                image_quality_json = %s::jsonb,
                camera_view_json = %s::jsonb,
                scene_objects_json = %s::jsonb,
                analysis_quality_json = %s::jsonb,
                raw_json = %s::jsonb,

                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = %s
            """,
            (
                result.get("client") or None,
                result.get("brand") or None,
                result.get("category") or None,
                result.get("description") or None,
                result.get("confidence"),

                elapsed,

                json.dumps(
                    text_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    colors_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    objects_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    environment_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    image_quality_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    camera_view_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    scene_objects_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    analysis_quality_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    raw_json,
                    ensure_ascii=False,
                ),

                photo_id,
            ),
        )

    conn.commit()

def mark_error(conn, photo_id, error):
    message = str(error)

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'error',
                error_message = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                message[:4000],
                photo_id,
            ),
        )

    conn.commit()

# ============================================================
# IMAGE
# ============================================================

def image64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ============================================================
# QWEN
# ============================================================

def ask(path):

    max_attempts = 2

    for attempt in range(1, max_attempts + 1):

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT,
                    "images": [image64(path)],
                }
            ],
            "stream": False,
            "options": {
                "num_ctx": NUM_CTX,
                "temperature": TEMPERATURE,
                "num_predict": 800,
            },
        }

        started = time.time()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:25:38

Да, этого куска уже достаточно, чтобы увидеть важное: **Qwen у нас фактически уже почти готов к новой архитектуре.**

Он уже работает через PostgreSQL `photos`, а не через физическую структуру адресных папок.

Ключевой момент здесь:

```text id="3o1z0x"
SELECT
    id,
    photo_id,
    source_path,
    filename
FROM photos
WHERE qwen_status = 'pending'
```

То есть Qwen уже может брать фотографию **по записи в БД**, независимо от её адреса.

И он уже сохраняет результат обратно в ту же запись.

### Что меняем

Сейчас Qwen привязан к:

```text id="0t0x2j"
qwen_status = pending
```

А нам нужно, чтобы запись создавалась сразу после получения `photo_id`:

```text id="7g9r4s"
photo_id
source_path
filename

dino_status = pending
qwen_status = pending

address_id = NULL
```

После этого **два независимых worker-а** могут забрать её:

```text id="l8s8uw"
              PHOTO
                │
             photo_id
                │
       ┌────────┴────────┐
       ▼                 ▼
     DINO              QWEN
       │                 │
       ▼                 ▼
 address_id          описание
       │                 │
       └────────┬────────┘
                ▼
          одна запись PHOTO
```

Причём Qwen вообще не интересует:

```text id="r5b0j5"
address_id = 78
```

Он работает только с:

```text id="x6w9o8"
photo_id
source_path
```

Это полностью соответствует тому, что мы зафиксировали.

---

### Есть ещё один важный нюанс

В `mark_done()` сейчас:

```text id="ym8r6e"
WHERE id = %s
```

а передаётся туда:

```text id="f3v5qh"
photo_id
```

То есть нужно внимательно проверить схему `photos`: похоже, тут потенциально смешаны **внутренний PostgreSQL `id`** и наш логический `photo_id`.

Это как раз надо исправить до запуска новой параллельной системы, иначе можно получить очень неприятную ошибку: Qwen забрал одну фотографию, а результат записал не в ту запись.

---

### Поэтому сейчас ничего не меняем

Нам осталось увидеть вторую половину Qwen-файла — там находится основной цикл worker-а и обработка ошибок/завершения.

Выполни:

```bash id="r0n7qe"
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '360,760p' scripts/qwen4b_output_v01.py
```

После этого уже можно будет спроектировать **конкретно таблицу `photos` + DINO worker + Qwen worker + управление PAUSE/CONTINUE/REPROCESS**, не ломая текущий Qwen.

---

### 👤 **User** — 2026-08-18 23:26:13

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '360,760p' scripts/qwen4b_output_v01.py
        started = time.time()

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=1800,
        )

        elapsed = time.time() - started

        if response.status_code != 200:
            raise RuntimeError(response.text)

        data = response.json()

        stats = {
            "total_duration_sec": round(
                data.get("total_duration", 0) / 1e9,
                2,
            ),
            "load_duration_sec": round(
                data.get("load_duration", 0) / 1e9,
                2,
            ),
            "prompt_eval_duration_sec": round(
                data.get("prompt_eval_duration", 0) / 1e9,
                2,
            ),
            "eval_duration_sec": round(
                data.get("eval_duration", 0) / 1e9,
                2,
            ),
            "prompt_eval_count": data.get(
                "prompt_eval_count"
            ),
            "eval_count": data.get(
                "eval_count"
            ),
        }

        print(
            "[OLLAMA]",
            stats,
            flush=True,
        )

        answer = data["message"]["content"]

        cleaned = answer.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace(
                "```json",
                "",
                1,
            )
            cleaned = cleaned.replace(
                "```",
                "",
            ).strip()

        try:

            result = json.loads(cleaned)

            description = str(
                result.get("description") or ""
            ).strip()

            if description:
                result["_time_sec"] = round(
                    elapsed,
                    2,
                )
                return result

            if attempt < max_attempts:

                print(
                    "[QWEN RETRY]",
                    "description empty",
                    "| attempt:",
                    attempt + 1,
                    flush=True,
                )

                continue

            result["_time_sec"] = round(
                elapsed,
                2,
            )

            return result

        except Exception as exc:

            print(
                "[QWEN JSON ERROR]",
                repr(exc),
                "| attempt:",
                attempt,
                flush=True,
            )

            if attempt < max_attempts:
                continue

            result = {
                "raw_answer": answer,
            }

            result["_time_sec"] = round(
                elapsed,
                2,
            )

            return result

# ============================================================
# WORKER
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only N pending photos",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("QWEN3-VL 4B — DATABASE WORKER")
    print("=" * 80)
    print("MODEL:", MODEL)
    print("DATABASE:", DB_CONFIG["dbname"])
    print()

    conn = get_connection()

    processed = 0
    errors = 0

    try:

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM photos
                WHERE qwen_status = 'pending'
                """
            )

            pending = cur.fetchone()[0]

        print(
            "PENDING:",
            pending,
        )
        print()

        while True:

            if (
                args.limit is not None
                and processed >= args.limit
            ):
                print(
                    "LIMIT REACHED:",
                    args.limit,
                )
                break

            row = claim_photo(conn)

            if row is None:

                print(
                    "QWEN QUEUE EMPTY"
                )

                break

            db_id = row["id"]
            photo_id = row["photo_id"]
            source_path = row["source_path"]

            print("=" * 80)
            print(
                f"[{processed + 1}]",
                photo_id,
            )
            print(
                "SOURCE:",
                source_path,
            )

            started = time.time()

            try:

                path = Path(source_path)

                if not path.exists():
                    raise FileNotFoundError(
                        f"Photo not found: {path}"
                    )

                if not path.is_file():
                    raise FileNotFoundError(
                        f"Not a file: {path}"
                    )

                result = ask(path)

                elapsed = time.time() - started

                mark_done(
                    conn,
                    db_id,
                    result,
                    elapsed,
                )

                print(
                    "OK",
                    "| time:",
                    round(elapsed, 2),
                    "sec",
                    "| client:",
                    result.get("client", ""),
                    "| brand:",
                    result.get("brand", ""),
                    "| confidence:",
                    result.get("confidence", ""),
                )

                print(
                    "DESCRIPTION:",
                    result.get(
                        "description",
                        "",
                    ),
                )

                quality = result.get(
                    "image_quality",
                    {},
                )

                print(
                    "QUALITY:",
                    quality.get(
                        "overall",
                        "",
                    ),
                    "| sharpness:",
                    quality.get(
                        "sharpness",
                        "",
                    ),
                    "| banner:",
                    quality.get(
                        "banner_visible",
                        "",
                    ),
                )

                environment = result.get(
                    "environment",
                    {},
                )

                print(
                    "ENV:",
                    environment.get(
                        "weather",
                        "",
                    ),
                    "|",
                    environment.get(
                        "precipitation",
                        "",
                    ),
                )

                processed += 1

            except Exception as exc:

                errors += 1

                elapsed = time.time() - started

                print(
                    "ERROR:",
                    exc,
                    "| time:",
                    round(elapsed, 2),
                    "sec",
                )

                try:
                    mark_error(
                        conn,
                        db_id,
                        exc,
                    )
                except Exception as db_error:

                    print(
                        "DB ERROR:",
                        db_error,
                    )

    finally:

        conn.close()

        print()
        print("=" * 80)
        print("QWEN WORKER STOPPED")
        print("=" * 80)
        print(
            "PROCESSED:",
            processed,
        )
        print(
            "ERRORS:",
            errors,
        )

if __name__ == "__main__":
    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:26:14

Да. Теперь Qwen понятен полностью, и архитектуру можно зафиксировать.

### Что у нас уже хорошо

Qwen **не надо переписывать с нуля**.

Он уже:

- берёт фотографии из PostgreSQL;
- использует `source_path`;
- блокирует запись через `FOR UPDATE SKIP LOCKED`;
- ставит `qwen_status = processing`;
- обрабатывает фото через Ollama;
- сохраняет JSON обратно в `photos`;
- умеет повторную попытку запроса к модели;
- работает независимо от `address_id`.

То есть концепция правильная.

---

## Но исправляем одну ошибку

Сейчас:

```python
def mark_done(conn, photo_id, result, elapsed):
```

а вызывается:

```python
mark_done(
    conn,
    db_id,
    result,
    elapsed,
)
```

То есть имя аргумента `photo_id` вводит в заблуждение: фактически туда передаётся **внутренний `photos.id`**.

То же самое с:

```python
mark_error(conn, db_id, exc)
```

Это не критическая ошибка сейчас, потому что SQL действительно делает:

```sql
WHERE id = %s
```

Но в новой архитектуре это надо привести к нормальному виду.

---

# Главное изменение

Я предлагаю **не делать отдельную SQLite БД для обработки**, раз у нас уже есть PostgreSQL `photobase` и таблица `photos`.

Именно `photos` становится центральным индексом.

То есть:

```text id="p2p4e4"
                 PHOTOS
                   │
          ┌────────┴────────┐
          │                 │
         DINO              QWEN
          │                 │
    address_id          metadata
          │                 │
          └────────┬────────┘
                   │
                  GRID
```

Это намного лучше.

---

# Как будет выглядеть запись

Условно:

```text id="c4cbqz"
photos
──────────────────────────────────────
id                  15237
photo_id            P00015237
source_path         /data/input/daily/xxx.jpg
filename            xxx.jpg
file_hash           ...

dino_status         done
address_id          83
dino_result         {...}

qwen_status         processing
client              ...
brand               ...
description         ...
qwen_result         {...}

created_at
updated_at
```

Причём:

### `photo_id`

Это наш **стабильный идентификатор фотографии**.

Он не меняется.

### `address_id`

Это **результат DINO**.

Он может быть:

```text
NULL
```

пока DINO не закончил.

Именно `address_id` решает:

> показывать фотографию в гриде или нет.

---

# Теперь становится возможен нужный тебе сценарий

Фотография появилась:

```text
id="7q7a3x"
P00015237
```

Сразу:

```text
DINO = pending
QWEN = pending
address_id = NULL
```

### Qwen

забрал:

```text
id="e5s2gq"
QWEN = processing
```

DINO параллельно:

```text
id="b6pkc3"
DINO = processing
```

Qwen закончил:

```text
id="5u7w4d"
QWEN = done
description = "..."
```

**Но в гриде фото ещё нет.**

Потому что:

```text
address_id = NULL
```

---

### DINO закончил

```text
id="g9o0eh"
DINO = done
address_id = 83
```

И сразу:

```text
GRID → показывает P00015237
```

Грид подтягивает Qwen:

```text
description
client
brand
colors
...
```

по тому же:

```text
photo_id = P00015237
```

---

# И соседняя логика DINO остаётся

Это важно.

Мы **не делаем DINO worker "одна фотография → сразу address"**, потому что Hybrid v12 смотрит на соседние результаты.

Значит DINO pipeline остаётся:

```text id="u9xq4n"
source
 ↓
photo_id
 ↓
DINO recognition
 ↓
top-5
 ↓
margin
 ↓
sub
 ↓
neighbor
 ↓
Hybrid v12
 ↓
address_id
```

А Qwen:

```text id="m1jv4n"
source
 ↓
photo_id
 ↓
Qwen
 ↓
metadata
```

---

# Теперь STOP / PAUSE тоже становится нормальным

При нажатии:

**`■ ОСТАНОВИТЬ`**

мы не удаляем ничего.

Например:

```text
DINO
100 done
3 processing
97 pending

QWEN
72 done
1 processing
127 pending
```

Останавливаем workers.

После:

**`▶ ПРОДОЛЖИТЬ`**

они смотрят только на `pending`.

Уже `done` пропускаются.

---

# А «обработать заново»

Здесь тоже всё можно сделать аккуратно.

Для DINO:

```text
Продолжить
Обработать заново
```

Для Qwen:

```text
Продолжить
Обработать заново
```

При **«Обработать заново»** мы не создаём новые фотографии и не меняем `photo_id`.

Просто:

```text
DINO:
done → pending
address_id → NULL
```

или:

```text
QWEN:
done → pending
```

При этом сам файл и его `photo_id` остаются прежними.

---

## И вот теперь можно переходить к DINO

Следующее, что нам нужно посмотреть — **как именно `run_hybrid_v12.py` формирует итоговые результаты и где сейчас создаётся `recognition.json`, `hybrid_v12.json`, `report.json` и т.д.**

Потому что нам нужно отделить:

**результаты DINO → индекс/БД**

от старой:

**физической сортировки → копирование файлов по папкам**.

Сама `sort_results()` нам больше не нужна как рабочая операция.

Покажи оставшуюся часть `run_hybrid_v12.py`:

```bash id="c6ez9f"
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '530,780p' scripts/run_hybrid_v12.py
```

После этого уже сможем спроектировать новый DINO worker, **сохранив frozen Hybrid v12 без изменения алгоритма**.

---

### 👤 **User** — 2026-08-18 23:27:18

нужен еще выбор запуска процесса: watcher который наблюдает и ждет новые файлы,  - ручной запуск, если не выбран watcher - автоматический в определнное время (ручной можно при нем выбрать), при watcher только он

---

### 🤖 **Assistant** — 2026-08-18 23:27:19

Да, это нужно добавить в архитектуру **до реализации кнопок**. И здесь лучше сделать именно взаимоисключающий режим запуска.

### Режим запуска

В техническом разделе:

```text id="d3m8qn"
РЕЖИМ ЗАПУСКА

○ WATCHER
○ ПО РАСПИСАНИЮ
○ РУЧНОЙ
```

Но логика немного особенная, как ты описал:

### 1. WATCHER

```text id="9y2m3p"
● WATCHER
```

Watcher постоянно наблюдает за папкой источника.

Появились новые файлы:

```text id="3l1q5r"
новый JPG
   ↓
photo_id
   ↓
DINO + Qwen
```

**Ручной запуск при этом отключён.**

То есть нельзя случайно одновременно запустить ручную обработку.

---

### 2. РУЧНОЙ

```text id="u2d4qk"
○ РУЧНОЙ
```

Watcher не работает.

Есть:

```text id="9v0h1c"
[ ▶ ЗАПУСТИТЬ ]
```

И можно запускать обработку когда нужно.

---

### 3. ПО РАСПИСАНИЮ

Например:

```text id="7t2f5v"
○ ПО РАСПИСАНИЮ

Время: [ 23:00 ]

[✓] Разрешить ручной запуск
```

Здесь автоматический запуск происходит в заданное время.

И, как ты сказал:

> ручной можно при нём выбрать

То есть:

```text id="5h5k1a"
РАСПИСАНИЕ
23:00

[✓] Ручной запуск разрешён
```

В 23:00 запускается автоматически, но пользователь также может нажать:

```text id="2y3s6x"
▶ ЗАПУСТИТЬ
```

---

## Получается три режима

| Режим | Автоматический запуск | Ручной запуск |
|---|---|---|
| **Watcher** | при появлении новых файлов | ❌ |
| **Расписание** | в заданное время | ✅ если разрешён |
| **Ручной** | ❌ | ✅ |

---

## И ещё важное

Watcher **не должен сам запускать старый `run_daily_hybrid_v12.sh`**.

Он должен только обнаруживать новые файлы и добавлять их в центральный индекс:

```text id="b8j4z2"
SOURCE
  ↓
WATCHER
  ↓
photo_id
  ↓
photos
  ├── DINO = PENDING
  └── QWEN = PENDING
```

После этого независимые workers сами забирают работу.

Это как раз позволит получить настоящую непрерывную обработку:

```text id="1f2x8n"
              WATCHER
                 │
        ┌────────┴────────┐
        ▼                 ▼
      DINO              QWEN
        │                 │
        └───────┬─────────┘
                ▼
              PHOTOS
                │
                ▼
               GRID
```

И если Watcher работает, **кнопка «Запустить обработку» не нужна вообще** — система уже постоянно готова брать новые фотографии.

---

### Я бы ещё добавил состояние Watcher

В UI:

```text id="l5f2k7"
WATCHER

🟢 Наблюдение активно
Папка: /data/input/daily
Новых файлов: 12
Обработано: 8
Ожидают: 4

[ ■ Остановить watcher ]
```

А если выключен:

```text id="a0n6qz"
⚪ Watcher выключен
```

Главный индикатор при этом остаётся именно **индикатором обработки**, а не Watcher:

- 🟢 готов;
- 🟠 идёт обработка;
- 🟡 пауза;
- 🔴 ошибка.

То есть **Watcher может быть активен и при этом главный индикатор быть зелёным**, если сейчас нет обработки.

Это правильнее архитектурно.

---

### 👤 **User** — 2026-08-18 23:29:33

ручной запуск актирует кнопки запустить в UI который выше. При автомате и вотчере кнопка запустить там неактивна. При нажатии остановить в UI где общий, дино и квен - сбрасывается в ручной режим по умолчанию

---

### 🤖 **Assistant** — 2026-08-18 23:29:33

Да, теперь логика полностью определилась. Я бы именно так и зафиксировал.

## Режим запуска

В техническом разделе:

```text
РЕЖИМ ЗАПУСКА

(●) Ручной
( ) По расписанию
( ) Watcher
```

### Ручной

Активны кнопки:

```text
┌─────────────────────────────────────────┐
│ [ ▶ ЗАПУСТИТЬ ]       [ ■ ОСТАНОВИТЬ ] │
└─────────────────────────────────────────┘

DINO
[ ▶ Запустить ] [ ■ Остановить ]

QWEN
[ ▶ Запустить ] [ ■ Остановить ]
```

Можно запускать:

- всё общей кнопкой;
- только DINO;
- только Qwen.

---

### Автоматический режим

Например:

```text
( ) Ручной
(●) По расписанию
( ) Watcher

Время запуска: [ 23:00 ]
[✓] Разрешить ручной запуск
```

Если **ручной запуск разрешён**, кнопки `▶ Запустить` активны.

Если не разрешён:

```text
[ ▶ ЗАПУСТИТЬ ]  ← disabled
```

Автоматический запуск происходит сам.

---

### Watcher

```text
( ) Ручной
( ) По расписанию
(●) Watcher

Наблюдение: 🟢 активно
```

При этом:

```text
[ ▶ ЗАПУСТИТЬ ]  ← disabled
```

И запуск происходит только через обнаружение новых файлов.

**Никакого ручного запуска поверх Watcher.**

---

# Самое важное — кнопка ОСТАНОВИТЬ

Тут твое правило правильное:

> При нажатии остановить в UI сбрасывается в ручной режим по умолчанию.

То есть пользователь нажал:

```text
[ ■ ОСТАНОВИТЬ ]
```

с любого режима:

```text
WATCHER
   ↓
STOP
   ↓
РУЧНОЙ
```

или:

```text
РАСПИСАНИЕ
   ↓
STOP
   ↓
РУЧНОЙ
```

При этом **сама обработка останавливается**, но уже обработанные результаты не теряются.

Состояние:

```text
🟡 ПАУЗА
```

и режим:

```text
Ручной
```

То есть после STOP UI выглядит примерно:

```text
РЕЖИМ ЗАПУСКА

(●) Ручной
( ) По расписанию
( ) Watcher

🟡 ПАУЗА

[ ▶ ЗАПУСТИТЬ ]       [ ■ ОСТАНОВИТЬ ]

DINO
[ ▶ Запустить ]       [ ■ Остановить ]

QWEN
[ ▶ Запустить ]       [ ■ Остановить ]
```

А следующая кнопка `▶ ЗАПУСТИТЬ` означает **продолжить с места остановки**, а не начать всё сначала.

---

## Отдельно «обработать заново»

Чтобы не путать `STOP` и повторную обработку, это остаётся отдельной настройкой:

```text
Для уже обработанных:

(●) Пропустить
( ) Обработать заново
```

Например:

```text
Ручной
Обработанные: [ Пропустить ▼ ]

[ ▶ ЗАПУСТИТЬ ]
```

Поэтому:

**STOP ≠ REPROCESS**

STOP — остановить и потом продолжить.

REPROCESS — сознательно прогнать уже обработанные фотографии ещё раз.

---

### Итоговая логика

```text
                 РЕЖИМ
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
    РУЧНОЙ     РАСПИСАНИЕ    WATCHER
       │           │           │
       │       авто запуск     │
       │       + ручной*       │
       │                       │
       └──────────┬────────────┘
                  │
                STOP
                  │
                  ▼
              РУЧНОЙ
                  │
                  ▼
             🟡 ПАУЗА
                  │
             ЗАПУСТИТЬ
                  │
                  ▼
          продолжить очередь
```

`*` ручной запуск в расписании только если разрешён настройкой.

Это уже можно считать **зафиксированной логикой технического раздела**.

---

### 👤 **User** — 2026-08-18 23:30:23

ок

---

### 🤖 **Assistant** — 2026-08-18 23:30:24

Да. Тогда фиксируем **режимы запуска** и поведение UI так:

### 1. Режим запуска

В техническом разделе отдельный блок:

**РЕЖИМ ЗАПУСКА**

- `○ Ручной`
- `○ Watcher`
- `○ Автоматический`

Дополнительно:

- для **Автоматического** — время запуска, например `02:00`;
- для **Ручного** — кнопки `ЗАПУСТИТЬ` у DINO и Qwen активны;
- для **Watcher** — ручные кнопки запуска заблокированы;
- для **Автоматического** — ручные кнопки запуска тоже заблокированы.

То есть:

| Режим | Что происходит |
|---|---|
| **Ручной** | пользователь запускает DINO/Qwen кнопками |
| **Watcher** | система сама ждёт новые фотографии и запускает обработку |
| **Автоматический** | система запускает обработку в заданное время |
| Watcher + ручной запуск | **не допускаем** — при Watcher ручные кнопки отключены |

### 2. Главные кнопки

Общий блок:

**● ЗАПУСТИТЬ**  
**■ ОСТАНОВИТЬ**

И ниже:

**DINO**  
`ЗАПУСТИТЬ` `ОСТАНОВИТЬ` `[████████░░] 82 / 100`

**Qwen3-VL 4B**  
`ЗАПУСТИТЬ` `ОСТАНОВИТЬ` `[██████░░░░] 61 / 100`

Главная `ЗАПУСТИТЬ` запускает **оба независимых процесса**, а не последовательную цепочку.

### 3. Состояние общего процесса

Индикатор:

- 🟢 **зелёный** — готов / ожидает;
- 🟠 **оранжевый мигающий** — обработка идёт;
- 🟡 **жёлтый** — пауза;
- 🔴 **красный** — ошибка.

Причём общий статус считается активным, пока работает **DINO или Qwen**.

### 4. Самое важное — независимость DINO и Qwen

Старую схему:

`DINO → физическая сортировка → Qwen`

убираем.

Будет:

```text
                    ┌── DINO ──→ photo_id ──→ address_id
INPUT ──→ индекс ───┤
                    └── QWEN ──→ описание
```

Qwen не ждёт окончания DINO.

Как только фотография получила `photo_id`, она становится доступной Qwen.

DINO в свою очередь позднее присваивает ей `address_id`.

А грид показывает фотографию **только после появления `address_id`**.

Таким образом:

```text
photo_id = постоянный идентификатор фотографии
source_path = где физически лежит файл
address_id = результат DINO
qwen_* = результат анализа Qwen
```

Все эти данные связываются через `photo_id`.

### 5. Возобновление

Для каждого процесса состояние хранится в БД.

Например:

```text
DINO:
pending
processing
done
error

QWEN:
pending
processing
done
error
```

При перезапуске:

- `done` → пропускаем;
- `pending` → продолжаем;
- `processing` после аварийного завершения → возвращаем в очередь;
- `error` → зависит от выбранной политики.

### 6. Политика обработки

Перед запуском:

**Уже обработанные:**

`○ Пропускать`  
`○ Обрабатывать заново`

И отдельно:

**Применить ко всем**

То есть можно выбрать:

> **Пропускать уже обработанные**

и запуск продолжится с места остановки.

Либо:

> **Обработать заново**

и существующие результаты соответствующего процесса будут пересчитаны.

Это должно работать **независимо для DINO и Qwen**.

### 7. Остановка

Очень важный момент: кнопка **ОСТАНОВИТЬ** не должна уничтожать состояние.

Она делает:

```text
running
   ↓
stop requested
   ↓
текущая операция корректно завершается
   ↓
незавершённые задания остаются pending
   ↓
process stopped
```

При следующем запуске система продолжает с места остановки.

И, как ты зафиксировал:

> **После нажатия общего `ОСТАНОВИТЬ` режим автоматически возвращается в `Ручной`.**

То есть:

```text
WATCHER
   ↓
ОСТАНОВИТЬ
   ↓
РУЧНОЙ
```

и

```text
АВТОМАТИЧЕСКИЙ
   ↓
ОСТАНОВИТЬ
   ↓
РУЧНОЙ
```

После этого кнопки `ЗАПУСТИТЬ` DINO/Qwen снова становятся активными.

---

И ещё одно: **физическая папка результата больше не должна быть источником истины для Qwen**. `run_hybrid_v12.py` сейчас делает `shutil.copy2()` в адресные папки — это старую архитектуру надо постепенно вынести из рабочего контура. База должна стать главным связующим слоем, а физическое расположение файла — просто `source_path`/`current_path`.

Следующий шаг я бы делал **не переписыванием UI**, а сначала вводом единого состояния `photo_id → DINO status/address_id → Qwen status`, после чего уже подключаем к нему три режима запуска. Это позволит не сломать нынешний рабочий DINO v33/Hybrid v12.

---

### 👤 **User** — 2026-08-18 23:30:53

желательно сделать описание каждого режима через tooltip

---

### 🤖 **Assistant** — 2026-08-18 23:30:53

Да, обязательно. Это как раз лучше сделать **через tooltip**, чтобы основной интерфейс не перегружать.

### Блок «РЕЖИМ ЗАПУСКА»

```text
РЕЖИМ ЗАПУСКА

(●) Ручной     ( ) Watcher     ( ) Автоматический
```

При наведении:

**Ручной**  
> Обработка запускается пользователем вручную.  
> Кнопки «Запустить» DINO и Qwen активны.  
> Можно запускать процессы независимо друг от друга.

**Watcher**  
> Система постоянно наблюдает за папкой источника.  
> При появлении новых фотографий они автоматически добавляются в очередь.  
> Ручной запуск DINO и Qwen недоступен.  
> После остановки режим возвращается в «Ручной».

**Автоматический**  
> Обработка запускается автоматически в заданное время.  
> До наступления времени система ожидает запуска.  
> Ручные кнопки DINO и Qwen недоступны.  
> Время запуска можно изменить.

### Для времени

Рядом с автоматическим режимом:

```text
Время запуска: [ 02:00 ]
```

Tooltip:

> Время ежедневного автоматического запуска.  
> Используется только в режиме «Автоматический».

### Для политики повторной обработки

Тоже tooltip:

```text
Обработанные:
[ Пропускать ▼ ]
```

**Пропускать**:

> Фотографии, для которых соответствующий процесс уже успешно завершён, повторно не обрабатываются.

**Обрабатывать заново**:

> Все выбранные фотографии будут повторно переданы процессу, даже если ранее обработка завершилась успешно.

И я бы сделал ещё tooltip у **общих кнопок**:

**ЗАПУСТИТЬ**

> Запускает доступные процессы согласно текущему режиму и выбранной политике обработки.

**ОСТАНОВИТЬ**

> Останавливает DINO и Qwen, не удаляя результаты и не сбрасывая очередь. Незавершённая обработка может быть продолжена позже. После остановки режим запуска переключается на «Ручной».

Так интерфейс останется компактным, а при наведении пользователь получает полноценное объяснение.

---

### 👤 **User** — 2026-08-18 23:31:03

lfktt

---

### 🤖 **Assistant** — 2026-08-18 23:31:04

Да, идём дальше.

Следующим шагом предлагаю **не менять пока рабочий `run_hybrid_v12.py`**, а сделать новый слой управления процессами:

1. **единая очередь фотографий** с `photo_id`;
2. отдельное состояние **DINO**;
3. отдельное состояние **Qwen**;
4. общий **Process Manager** - запуск/остановка/пауза;
5. три режима - ручной / watcher / автоматический;
6. UI подключаем уже к этому менеджеру.

Так мы не сломаем нынешний рабочий Hybrid v12 и постепенно переведём его на новую архитектуру.

Если продолжаем прямо сейчас - следующим дам **точную структуру таблиц БД и состояний**, которые нужны для этой схемы.

---

### 👤 **User** — 2026-08-18 23:31:15

Дай мне точную структуру таблиц БД и состояний

---

### 🤖 **Assistant** — 2026-08-18 23:31:16

Да. Здесь уже лучше зафиксировать БД как **источник истины**, а не строить логику вокруг папок `output/daily/...`.

Я бы сделал структуру из **5 основных таблиц**. Причём `photo_id` — главный постоянный идентификатор фотографии, а `address_id` — отдельный результат DINO.

## 1. `photos` — главная таблица фотографий

Это центральная таблица.

```sql
CREATE TABLE photos (
    id BIGSERIAL PRIMARY KEY,

    -- Постоянный ID фотографии
    photo_id TEXT NOT NULL UNIQUE,

    -- Псевдоним/ID исходного запуска или группы
    source_id TEXT,

    -- Физическое расположение исходного файла
    source_path TEXT NOT NULL,

    filename TEXT NOT NULL,

    -- Размер/служебная информация
    file_size BIGINT,
    file_mtime TIMESTAMP,

    -- =====================================================
    -- DINO
    -- =====================================================

    dino_status TEXT NOT NULL DEFAULT 'pending',

    -- Результат DINO: именно ID адреса
    address_id TEXT,

    dino_score REAL,
    dino_second_score REAL,
    dino_margin REAL,
    dino_confidence REAL,

    dino_fingerprint_id TEXT,

    dino_started_at TIMESTAMP,
    dino_finished_at TIMESTAMP,

    dino_error TEXT,

    -- =====================================================
    -- QWEN
    -- =====================================================

    qwen_status TEXT NOT NULL DEFAULT 'pending',

    qwen_started_at TIMESTAMP,
    qwen_finished_at TIMESTAMP,

    qwen_time_sec REAL,

    qwen_error TEXT,

    -- =====================================================
    -- QWEN RESULT
    -- =====================================================

    client TEXT,
    brand TEXT,
    category TEXT,
    description TEXT,
    confidence REAL,

    text_json JSONB,
    colors_json JSONB,
    objects_json JSONB,

    environment_json JSONB,
    image_quality_json JSONB,
    camera_view_json JSONB,
    analysis_quality_json JSONB,

    raw_json JSONB,

    -- =====================================================
    -- Служебное
    -- =====================================================

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Ключевой принцип

Вот эта связь является главной:

```text
photo_id
   │
   ├── source_path
   │
   ├── DINO
   │     └── address_id
   │
   └── Qwen
         └── description / client / brand / ...
```

**Qwen вообще не знает и не должен знать `address_id`.**

---

# 2. `processing_jobs` — очередь обработки

Отдельно от `photos`.

Это позволит нормально реализовать:

- продолжение после остановки;
- несколько процессов;
- retry;
- watcher;
- ручной запуск;
- автоматический запуск;
- пропуск уже обработанных.

```sql
CREATE TABLE processing_jobs (
    id BIGSERIAL PRIMARY KEY,

    photo_id TEXT NOT NULL,

    process TEXT NOT NULL,
    -- DINO / QWEN

    status TEXT NOT NULL DEFAULT 'pending',
    -- pending
    -- processing
    -- done
    -- error
    -- paused
    -- cancelled

    attempts INTEGER NOT NULL DEFAULT 0,

    priority INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,

    worker_id TEXT,

    error TEXT,

    UNIQUE(photo_id, process)
);
```

Индекс:

```sql
CREATE INDEX idx_processing_jobs_queue
ON processing_jobs(process, status, priority DESC, id);
```

### Почему отдельная очередь?

Например:

```text
photo_001 | DINO | done
photo_001 | QWEN | processing

photo_002 | DINO | done
photo_002 | QWEN | pending

photo_003 | DINO | processing
photo_003 | QWEN | pending
```

Это идеально соответствует нашей новой архитектуре.

---

# 3. `processing_runs` — конкретные запуски

Нужна для кнопки **ЗАПУСТИТЬ / ОСТАНОВИТЬ**, статистики и возобновления.

```sql
CREATE TABLE processing_runs (
    id BIGSERIAL PRIMARY KEY,

    run_id TEXT NOT NULL UNIQUE,

    mode TEXT NOT NULL,
    -- manual
    -- watcher
    -- automatic

    status TEXT NOT NULL DEFAULT 'idle',
    -- idle
    -- running
    -- stopping
    -- paused
    -- completed
    -- error
    -- stopped

    dino_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    qwen_enabled BOOLEAN NOT NULL DEFAULT TRUE,

    processing_policy TEXT NOT NULL DEFAULT 'skip',
    -- skip
    -- reprocess

    started_at TIMESTAMP,
    stopped_at TIMESTAMP,
    finished_at TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    error TEXT
);
```

Например:

```text
run_id = 20260818_191530_A7F2
mode = manual
status = running
policy = skip
```

---

# 4. `system_settings` — настройки режима

Здесь хранится текущий режим запуска.

```sql
CREATE TABLE system_settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Начальные значения:

```text
run_mode = manual

automatic_time = 02:00

processing_policy = skip

watcher_enabled = false
```

Но я бы **не хранил watcher и mode как две независимые логические настройки**. Главным является:

```text
run_mode
```

и он принимает:

```text
manual
watcher
automatic
```

---

# 5. `processing_events` — журнал

Очень полезная вещь именно для нашего UI.

```sql
CREATE TABLE processing_events (
    id BIGSERIAL PRIMARY KEY,

    run_id TEXT,

    photo_id TEXT,

    process TEXT,
    -- DINO / QWEN / SYSTEM

    event TEXT NOT NULL,

    message TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Например:

```text
SYSTEM | RUN_STARTED
DINO   | PHOTO_STARTED
DINO   | PHOTO_DONE
QWEN   | PHOTO_STARTED
QWEN   | PHOTO_DONE
SYSTEM | STOP_REQUESTED
SYSTEM | RUN_STOPPED
DINO   | ERROR
```

Это даст нам историю и очень сильно упростит диагностику.

---

# Состояния DINO

Я бы зафиксировал **не слишком много состояний**:

```text
pending
processing
done
error
paused
```

### `pending`

Фотография ждёт DINO.

### `processing`

DINO сейчас работает с фотографией.

### `done`

Есть:

```text
address_id
```

То есть фотография уже может появиться в гриде.

### `error`

DINO не смог обработать фотографию.

### `paused`

Обработка была остановлена/поставлена на паузу.

---

# Состояния Qwen

Аналогично:

```text
pending
processing
done
error
paused
```

Но есть важное отличие.

Qwen может перейти:

```text
pending
    ↓
processing
```

**сразу после появления `photo_id`.**

Он не ждёт:

```text
address_id
```

---

# Главное условие появления фотографии в гриде

Вот это я предлагаю сделать жёстким правилом:

```sql
WHERE dino_status = 'done'
  AND address_id IS NOT NULL
```

То есть:

```text
photo_id получен
       │
       ├──────────────→ Qwen
       │
       ↓
      DINO
       │
       ↓
 address_id
       │
       ↓
     GRID
```

Qwen может уже закончить работу, а фотография всё равно не появляется в гриде, пока DINO не присвоил адрес.

---

# Что такое `source_id`

Это как раз тот **начальный ID / псевдоним**, который ты описывал.

Например:

```text
source_id = 78
```

или:

```text
source_id = daily_20260818
```

или:

```text
source_id = Кампания_Август
```

Он нужен для рабочего процесса, но **не должен использоваться как идентификатор фотографии**.

То есть:

```text
source_id
    ↓
группа/запуск/источник

photo_id
    ↓
конкретная фотография

address_id
    ↓
результат DINO
```

Это три совершенно разные сущности.

---

# Важный момент с текущим `photos`

У тебя уже есть PostgreSQL `photobase`, и текущий Qwen использует:

```python
FROM photos
```

Поэтому **не надо создавать новую таблицу фотографий**, если текущая `photos` уже является рабочей.

Лучше сделать **миграцию существующей `photos`**, добавив недостающие поля.

То есть сначала посмотрим:

```bash
psql -h localhost -U lora -d photobase
```

и:

```sql
\d photos
```

А уже после этого я дам **точный ALTER TABLE**, а не будем вслепую создавать вторую таблицу.

---

# Что в итоге получится

Архитектурно:

```text
                    ┌──────────────────────┐
                    │      PHOTOS          │
                    │                      │
                    │ photo_id             │
                    │ source_id            │
                    │ source_path          │
                    │ address_id            │
                    │ dino_*               │
                    │ qwen_*               │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┴─────────────────┐
             │                                   │
             ▼                                   ▼
       processing_jobs                    processing_jobs
          DINO                               QWEN
             │                                   │
             ▼                                   ▼
        address_id                         description
             │                              client
             │                              brand
             ▼                                ...
           GRID
```

А сбоку:

```text
processing_runs
       │
       ├── manual
       ├── watcher
       └── automatic

system_settings

processing_events
```

### И это позволяет реализовать всё, что мы уже зафиксировали:

- DINO и Qwen работают **параллельно**;
- Qwen получает фото сразу после `photo_id`;
- Qwen не зависит от адреса;
- DINO создаёт `address_id`;
- грид показывает только фотографии с `address_id`;
- остановка не теряет прогресс;
- повторный запуск продолжает очередь;
- `skip` пропускает `done`;
- `reprocess` создаёт новую обработку;
- общий `ОСТАНОВИТЬ` останавливает оба процесса;
- после общего `ОСТАНОВИТЬ` режим → **Ручной**;
- Watcher автоматически подхватывает новые фото;
- Automatic запускает очередь по расписанию;
- UI может показывать отдельный прогресс DINO/Qwen и общий статус.

**Следующий технический шаг — посмотреть реальную структуру существующей `photos`.** Тогда мы не будем ломать текущий Qwen и аккуратно встроим новую схему поверх уже работающей БД.

---

### 👤 **User** — 2026-08-18 23:31:57

окдалее

---

### 🤖 **Assistant** — 2026-08-18 23:31:58

Далее — **не меняем код**, сначала фиксируем реальную структуру `photobase.photos`, чтобы новая схема легла без поломки текущего Qwen.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -h localhost -U lora -d photobase -c '\d+ photos'
```

И сразу вторую команду:

```bash
psql -h localhost -U lora -d photobase -c "
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE dino_status = 'done') AS dino_done,
    COUNT(*) FILTER (WHERE qwen_status = 'done') AS qwen_done,
    COUNT(*) FILTER (WHERE address_id IS NOT NULL) AS with_address
FROM photos;
"
```

Если `dino_status` или `address_id` пока отсутствуют — **вторая команда может выдать ошибку, это нормально**.

После этого покажи вывод. По нему я дам **точный `ALTER TABLE` для существующей БД**, а затем сделаем следующим этапом:

```text
photos
   │
   ├── photo_id
   ├── source_id
   ├── source_path
   │
   ├── DINO
   │     └── address_id
   │
   └── QWEN
         └── описание
```

и отдельно подключим `processing_jobs` + `processing_runs`, не ломая текущий рабочий Qwen.

---

### 👤 **User** — 2026-08-18 23:32:32

Column         |            Type             | Collation | Nullable |              Default               | Storage  | Compression | Stats target | Description 
-----------------------+-----------------------------+-----------+----------+------------------------------------+----------+-------------+--------------+-------------
 id                    | bigint                      |           | not null | nextval('photos_id_seq'::regclass) | plain    |             |              | 
 photo_id              | text                        |           | not null |                                    | extended |             |              | 
 source_path           | text                        |           | not null |                                    | extended |             |              | 
 path                  | text                        |           | not null |                                    | extended |             |              | 
 filename              | text                        |           | not null |                                    | extended |             |              | 
 original_filename     | text                        |           |          |                                    | extended |             |              | 
 address               | text                        |           |          |                                    | extended |             |              | 
 client                | text

---

