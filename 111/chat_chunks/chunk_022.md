## СЕССИЯ: Использование первого кандидата

**Создано:** 2026-08-14 23:31:05
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f7b07-8df4-83ea-be86-b71f888d7beb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f7b07-8df4-83ea-be86-b71f888d7beb)

---

### 🤖 **Assistant** — 2026-08-15 01:09:11

Да. Делаем именно это — **удобное массовое добавление каталогов в очередь**, без изменения алгоритма слепка.

### 1. Добавляем `queue-batch-add`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/cli.py")
text = p.read_text()

marker = '''    # --------------------------------------------------
    # ANALYZE
    # --------------------------------------------------
'''

block = '''    # --------------------------------------------------
    # QUEUE BATCH ADD
    # --------------------------------------------------

    queue_batch_parser = subparsers.add_parser(
        "queue-batch-add",
        help="Add a range of folders to fingerprint queue",
    )

    queue_batch_parser.add_argument(
        "start",
        type=int,
        help="First address ID",
    )

    queue_batch_parser.add_argument(
        "end",
        type=int,
        help="Last address ID",
    )

    queue_batch_parser.add_argument(
        "--priority",
        type=int,
        default=0,
        help="Queue priority",
    )

'''

if "queue-batch-add" not in text:
    if marker not in text:
        raise RuntimeError("CLI insertion point not found")

    text = text.replace(
        marker,
        block + marker,
        1,
    )

p.write_text(text)

print("OK: queue-batch-add parser added")
PY
```

### 2. Добавляем обработчик команды

Теперь вставляем обработку перед `ANALYZE`:

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("app/cli.py")
text = p.read_text()

marker = '''    # --------------------------------------------------
    # ANALYZE
    # --------------------------------------------------

    if args.command == "analyze":
'''

block = '''    # --------------------------------------------------
    # QUEUE BATCH ADD
    # --------------------------------------------------

    if args.command == "queue-batch-add":

        from app.pipeline.queue import JobQueue

        queue = JobQueue(
            settings.data_dir / "jobs.db"
        )

        if args.end < args.start:
            raise ValueError(
                "END must be greater than or equal to START"
            )

        added = 0
        skipped_existing = 0
        skipped_queue = 0
        missing = 0

        for fingerprint_id in range(
            args.start,
            args.end + 1,
        ):
            fingerprint_id = str(
                fingerprint_id
            )

            source_folder = (
                settings.data_dir
                / "input"
                / fingerprint_id
            )

            if not source_folder.exists():
                print(
                    f"[Queue] MISSING: "
                    f"{source_folder}"
                )
                missing += 1
                continue

            image_files = [
                p
                for p in source_folder.iterdir()
                if p.is_file()
                and p.suffix.lower()
                in {
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                }
            ]

            if not image_files:
                print(
                    f"[Queue] NO IMAGES: "
                    f"{source_folder}"
                )
                missing += 1
                continue

            fingerprint_dir = (
                settings.fingerprints_dir
                / fingerprint_id
            )

            if fingerprint_dir.exists():
                print(
                    f"[Queue] SKIP EXISTING: "
                    f"{fingerprint_id}"
                )
                skipped_existing += 1
                continue

            existing_jobs = queue.list()

            already_queued = any(
                str(job["fingerprint_id"])
                == fingerprint_id
                and job["status"]
                in {
                    "PENDING",
                    "PROCESSING",
                    "DONE",
                }
                for job in existing_jobs
            )

            if already_queued:
                print(
                    f"[Queue] SKIP QUEUED: "
                    f"{fingerprint_id}"
                )
                skipped_queue += 1
                continue

            job_id = queue.add(
                source_folder,
                fingerprint_id,
                priority=args.priority,
            )

            print(
                f"[Queue] ADD "
                f"{fingerprint_id} "
                f"({len(image_files)} images) "
                f"job={job_id}"
            )

            added += 1

        print()
        print("=" * 60)
        print("[Queue] BATCH COMPLETE")
        print("=" * 60)
        print(f"Added:             {added}")
        print(f"Skipped existing:  {skipped_existing}")
        print(f"Skipped queued:    {skipped_queue}")
        print(f"Missing/no images: {missing}")
        print()
        print("Queue:", queue.counts())

        return 0

'''

if "if args.command == \"queue-batch-add\"" not in text:
    if marker not in text:
        raise RuntimeError("CLI handler insertion point not found")

    text = text.replace(
        marker,
        block + marker,
        1,
    )

p.write_text(text)

print("OK: queue-batch-add handler added")
PY
```

### 3. Проверяем

```bash
uv run python -m py_compile app/cli.py
```

Затем:

```bash
uv run scene-fingerprint --help
```

В списке должно появиться:

```text
{create,queue-batch-add,analyze,recognize}
```

И:

```bash
uv run scene-fingerprint queue-batch-add --help
```

### 4. Пока ничего не добавляем

Сначала просто покажи вывод этих двух проверок.

После этого протестируем команду на небольшом диапазоне, например `96–98`, чтобы не создать случайно лишние задачи.

---

### 👤 **User** — 2026-08-15 01:10:06

elp
usage: scene-fingerprint [-h]
                         {create,queue-add,queue-batch-add,analyze,recognize}
                         ...

Scene fingerprinting and recognition v3.3 compact

positional arguments:
  {create,queue-add,queue-batch-add,analyze,recognize}
    create              Create v3.3 compact fingerprint
    queue-add           Add fingerprint creation job to queue
    queue-batch-add     Add a range of folders to fingerprint queue
    analyze             Analyze one fingerprint
    recognize           Recognize images

options:
  -h, --help            show this help message and exit
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run scene-fingerprint queue-batch-add --help
usage: scene-fingerprint queue-batch-add [-h] [--priority PRIORITY] start end

positional arguments:
  start                First address ID
  end                  Last address ID

options:
  -h, --help           show this help message and exit
  --priority PRIORITY  Queue priority

---

### 🤖 **Assistant** — 2026-08-15 01:10:07

Отлично. Команда зарегистрирована корректно.

Теперь сделаем **безопасный тест**, не затрагивая существующие `83–95`.

Возьмём, например, диапазон `96–98` — только если такие каталоги действительно есть.

Сначала:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for id in {96..98}; do
    echo "=== $id ==="
    find "data/input/$id" -maxdepth 1 -type f 2>/dev/null | wc -l
done
```

Покажи результат.

Если там есть фотографии, следующим шагом запустим:

```bash
uv run scene-fingerprint queue-batch-add 96 98
```

и проверим, что **все три задачи корректно попали в SQLite**, но пока **не будем запускать worker**.

---

### 👤 **User** — 2026-08-15 01:10:23

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

for id in {96..98}; do
    echo "=== $id ==="
    find "data/input/$id" -maxdepth 1 -type f 2>/dev/null | wc -l
done
=== 96 ===
0
=== 97 ===
0
=== 98 ===
0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:10:24

Да, значит `96–98` для теста не подходят — каталогов с фотографиями там нет. Ничего не добавляем.

У нас уже есть рабочие каталоги `78–95`, поэтому лучше протестировать **сам механизм пропуска существующих слепков**. Это как раз важнее.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint queue-batch-add 78 95
```

### Что мы должны увидеть

Для каталогов, где уже есть fingerprint с таким же ID:

```text
[Queue] SKIP EXISTING: 78
[Queue] SKIP EXISTING: 79
...
```

Но здесь есть один нюанс: сейчас у нас fingerprints называются, например:

```text
78_v33
79_v33
86_v33_fast
```

а каталог:

```text
data/fingerprints/78
```

тоже существует.

То есть для `78–82` пропуск сработает.

Для `83–95` существующие слепки имеют **другие ID**, поэтому наша текущая проверка их не увидит и может поставить новые задачи `83`, `84` и т.д.

**Поэтому пока не запускай команду `78 95`.**

Нам нужно сначала поправить логику: считать адрес уже имеющим слепок, если существует **любой fingerprint, начинающийся с этого ID**, например:

```text
84_v33
84_v33_fast
84_batch_test
```

Тогда `84` будет корректно считаться уже обработанным.

Это небольшая, но важная правка перед использованием `queue-batch-add` на реальных данных.

---

### 👤 **User** — 2026-08-15 01:11:15

даваай

---

### 🤖 **Assistant** — 2026-08-15 01:11:16

Да. Исправляем именно это и больше ничего не меняем.

Сейчас логика должна считать адрес обработанным, если существует **любой каталог fingerprint с префиксом адреса**:

```text
84
84_v33
84_v33_fast
84_batch_test
```

Для `84` это означает **SKIP**, а не создание новой задачи.

### 1. Заменяем проверку существующего fingerprint

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/cli.py")
text = p.read_text()

old = '''            fingerprint_dir = (
                settings.fingerprints_dir
                / fingerprint_id
            )

            if fingerprint_dir.exists():
                print(
                    f"[Queue] SKIP EXISTING: "
                    f"{fingerprint_id}"
                )
                skipped_existing += 1
                continue
'''

new = '''            # Address is considered already processed
            # if ANY fingerprint directory starts with
            # this address ID:
            #
            #   84
            #   84_v33
            #   84_v33_fast
            #   84_batch_test
            #
            # This prevents duplicate jobs for the
            # same address.

            fingerprint_prefix = (
                f"{fingerprint_id}_"
            )

            existing_fingerprint = False

            if settings.fingerprints_dir.exists():
                for item in (
                    settings.fingerprints_dir.iterdir()
                ):
                    if not item.is_dir():
                        continue

                    name = item.name

                    if (
                        name == fingerprint_id
                        or name.startswith(
                            fingerprint_prefix
                        )
                    ):
                        existing_fingerprint = True
                        break

            if existing_fingerprint:
                print(
                    f"[Queue] SKIP EXISTING: "
                    f"{fingerprint_id}"
                )
                skipped_existing += 1
                continue
'''

if old not in text:
    raise RuntimeError(
        "Existing fingerprint block not found"
    )

text = text.replace(
    old,
    new,
    1,
)

p.write_text(text)

print(
    "OK: fingerprint prefix detection updated"
)
PY
```

### 2. Проверяем синтаксис

```bash
uv run python -m py_compile app/cli.py
```

### 3. Теперь безопасно проверяем весь диапазон 78–95

```bash
uv run scene-fingerprint queue-batch-add 78 95
```

**Worker пока НЕ запускаем.**

Покажи весь вывод команды.

Мы должны увидеть примерно:

```text
[Queue] SKIP EXISTING: 78
[Queue] SKIP EXISTING: 79
...
[Queue] SKIP EXISTING: 95

============================================================
[Queue] BATCH COMPLETE
============================================================
Added:             0
Skipped existing:  18
Skipped queued:    0
Missing/no images: 0
```

Это будет означать, что механизм теперь правильно понимает: **адрес уже имеет слепок независимо от его версии/суффикса**.

---

### 👤 **User** — 2026-08-15 01:11:30

наверно стоит удалить лишние каталоги слепков

---

### 🤖 **Assistant** — 2026-08-15 01:11:30

Да, **сейчас это разумно сделать**, пока каталогов ещё немного. Но я бы **не удалял вручную вслепую**: у нас есть несколько типов:

```text
78
78_v33
79
79_v33
...
86_v33_fast
...
86_batch_test
...
86_queue_test
```

Нужно оставить по **одному финальному слепку на адрес**, а тестовые удалить.

По текущей истории я бы ориентировался так:

| Адрес | Оставить |
|---|---|
| 78 | `78_v33` |
| 79 | `79_v33` |
| 80 | `80_v33` |
| 81 | `81_v33` |
| 82 | `82_v33` |
| 83 | `83_v33` |
| 84 | `84_v33` |
| 85 | `85_v33` |
| 86–95 | `*_v33_fast` |

А удалить тестовые:

```text
86_queue_test
91_queue_test
92_queue_test
83_batch_test
84_batch_test
85_batch_test
86_batch_test
87_batch_test
88_batch_test
89_batch_test
90_batch_test
91_batch_test
92_batch_test
93_batch_test
94_batch_test
95_batch_test
```

Но **перед удалением лучше сначала получить точный список** того, что реально сейчас лежит в `data/fingerprints`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== ALL FINGERPRINT DIRECTORIES ==="

find data/fingerprints \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    -printf '%f\n' \
    | sort -V
```

Пришли вывод.

После этого я дам **одну безопасную команду удаления только лишних каталогов**, без риска удалить нужные `v33`/`v33_fast`.

---

### 👤 **User** — 2026-08-15 01:11:55

=== ALL FINGERPRINT DIRECTORIES ===
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
83_batch_test
83_v33
84_batch_test
84_v33
85_batch_test
85_v33
86_batch_test
86_queue_test
86_v33_fast
87_batch_test
87_v33_fast
88_batch_test
88_v33_fast
89_batch_test
89_v33_fast
90_batch_test
90_v33_fast
91_batch_test
91_queue_test
91_v33_fast
92_batch_test
92_queue_test
92_v33_fast
93_batch_test
93_v33_fast
94_batch_test
94_v33_fast
95_batch_test
95_v33_fast

---

### 🤖 **Assistant** — 2026-08-15 01:11:56

Да. Теперь список чистый и можно удалить **только тестовые слепки**.

Оставляем:

```text
78_v33
79_v33
80_v33
81_v33
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
```

Удаляем:

```text
83_batch_test
84_batch_test
85_batch_test
86_batch_test
86_queue_test
87_batch_test
88_batch_test
89_batch_test
90_batch_test
91_batch_test
91_queue_test
92_batch_test
92_queue_test
93_batch_test
94_batch_test
95_batch_test
```

И старые:

```text
78
79
80
81
82
```

**Я бы их тоже удалил**, поскольку у нас есть соответствующие `*_v33`.

### Сначала покажем, что именно будет удалено

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for d in \
    78 79 80 81 82 \
    83_batch_test \
    84_batch_test \
    85_batch_test \
    86_batch_test \
    86_queue_test \
    87_batch_test \
    88_batch_test \
    89_batch_test \
    90_batch_test \
    91_batch_test \
    91_queue_test \
    92_batch_test \
    92_queue_test \
    93_batch_test \
    94_batch_test \
    95_batch_test
do
    echo "DELETE: data/fingerprints/$d"
done
```

Если список совпадает, тогда удаляем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf \
    data/fingerprints/78 \
    data/fingerprints/79 \
    data/fingerprints/80 \
    data/fingerprints/81 \
    data/fingerprints/82 \
    data/fingerprints/83_batch_test \
    data/fingerprints/84_batch_test \
    data/fingerprints/85_batch_test \
    data/fingerprints/86_batch_test \
    data/fingerprints/86_queue_test \
    data/fingerprints/87_batch_test \
    data/fingerprints/88_batch_test \
    data/fingerprints/89_batch_test \
    data/fingerprints/90_batch_test \
    data/fingerprints/91_batch_test \
    data/fingerprints/91_queue_test \
    data/fingerprints/92_batch_test \
    data/fingerprints/92_queue_test \
    data/fingerprints/93_batch_test \
    data/fingerprints/94_batch_test \
    data/fingerprints/95_batch_test
```

После удаления:

```bash
find data/fingerprints \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    -printf '%f\n' \
    | sort -V
```

В итоге должны остаться **ровно 18 рабочих слепков — 78–95**.

---

### 👤 **User** — 2026-08-15 01:12:39

fast надо переименовать под 33

---

### 🤖 **Assistant** — 2026-08-15 01:12:40

Да. Лучше привести всё к единому формату `XX_v33`, а тестовые каталоги удалить.

Сейчас:
- `86_v33_fast` → `86_v33`
- …
- `95_v33_fast` → `95_v33`

Но **86_v33 уже существует**, поэтому сначала надо проверить, что именно в нём лежит, чтобы ничего ценного не затереть.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for id in {86..95}; do
    echo "=== $id ==="
    ls -ld "data/fingerprints/${id}_v33" \
           "data/fingerprints/${id}_v33_fast" 2>/dev/null
done
```

Пришли вывод. После этого дам **одну безопасную команду**, которая:
1. сохранит нужные `*_v33_fast`;
2. уберёт тестовые `*_batch_test` и `*_queue_test`;
3. переименует `*_v33_fast` в нормальные `*_v33`;
4. ничего случайно не перезапишет.

---

### 👤 **User** — 2026-08-15 01:12:56

done
=== 86 ===
drwxrwxr-x 2 alexice alexice 4096 Aug 15 00:15 data/fingerprints/86_v33_fast
=== 87 ===
drwxrwxr-x 2 alexice alexice 4096 Aug 15 00:16 data/fingerprints/87_v33_fast
=== 88 ===
drwxrwxr-x 2 alexice alexice 4096 Aug 15 00:16 data/fingerprints/88_v33_fast
=== 89 ===
drwxrwxr-x 2 alexice alexice 4096 Aug 15 00:16 data/fingerprints/89_v33_fast
=== 90 ===
drwxrwxr-x 2 alexice alexice 4096 Aug 15 00:14 data/fingerprints/90_v33_fast
=== 91 ===
drwxrwxr-x 2 alexice alexice 4096 Aug 15 00:16 data/fingerprints/91_v33_fast
=== 92 ===
drwxrwxr-x 2 alexice alexice 4096 Aug 15 00:16 data/fingerprints/92_v33_fast
=== 93 ===
drwxrwxr-x 2 alexice alexice 4096 Aug 15 00:17 data/fingerprints/93_v33_fast
=== 94 ===
drwxrwxr-x 2 alexice alexice 4096 Aug 15 00:17 data/fingerprints/94_v33_fast
=== 95 ===
drwxrwxr-x 2 alexice alexice 4096 Aug 15 00:17 data/fingerprints/95_v33_fast
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:12:58

Отлично. Значит `86_v33`–`95_v33` **свободны**, можно спокойно переименовать `*_v33_fast`.

И одновременно уберём временные `*_batch_test` и `*_queue_test`.

### Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== УДАЛЯЕМ ТЕСТОВЫЕ СЛЕПКИ ==="

rm -rf \
    data/fingerprints/83_batch_test \
    data/fingerprints/84_batch_test \
    data/fingerprints/85_batch_test \
    data/fingerprints/86_batch_test \
    data/fingerprints/86_queue_test \
    data/fingerprints/87_batch_test \
    data/fingerprints/88_batch_test \
    data/fingerprints/89_batch_test \
    data/fingerprints/90_batch_test \
    data/fingerprints/91_batch_test \
    data/fingerprints/91_queue_test \
    data/fingerprints/92_batch_test \
    data/fingerprints/92_queue_test \
    data/fingerprints/93_batch_test \
    data/fingerprints/94_batch_test \
    data/fingerprints/95_batch_test

echo
echo "=== ПЕРЕИМЕНОВЫВАЕМ FAST → V33 ==="

for id in {86..95}; do
    mv "data/fingerprints/${id}_v33_fast" \
       "data/fingerprints/${id}_v33"
done

echo
echo "=== ИТОГ ==="
ls -1 data/fingerprints | sort
```

После этого структура должна стать примерно такой:

```text
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
86_v33
87_v33
88_v33
89_v33
90_v33
91_v33
92_v33
93_v33
94_v33
95_v33
```

То есть **единый рабочий формат `NN_v33`**, без `fast`, `batch_test`, `queue_test`.

После этого уже можно переходить к следующему шагу — у нас фактически готова база из **18 рабочих слепков 78–95**, и очередь можно использовать для дальнейшего массового добавления.

---

### 👤 **User** — 2026-08-15 01:13:32

мы собирались делать слепки с подслепками - надо будет заново все пронать и создать V34

---

### 🤖 **Assistant** — 2026-08-15 01:13:33

Да. Тогда **V33 не трогаем как контрольную версию**, а создаём новую версию **V34**, где один слепок сможет содержать несколько подслепков по разным ракурсам.

И я бы сейчас действительно **не усложнял архитектуру**. Делаем следующий шаг минимально:

### План V34

```text
data/input/84/
    ├── фото ракурса A
    ├── фото ракурса A
    ├── фото ракурса B
    ├── фото ракурса B
    └── ...

        ↓

84_v34/
    ├── embeddings.npy
    ├── centroid.npy
    ├── representatives.npy
    ├── ...
    └── metadata.json
```

Но внутри `metadata.json` добавляем информацию о **подслепках**:

```text
84_v34
 ├── subfingerprint_01
 ├── subfingerprint_02
 ├── subfingerprint_03
 └── global
```

При распознавании изображение сначала сравнивается с **подслепками**, а не только с одним средним centroid.

Это как раз должно решить проблему `84`: фотографии одного адреса могут сильно отличаться по направлению камеры, но принадлежать одной сцене.

### Важный момент

Я бы **не начинал сейчас с автоматического определения ракурсов**.

Первый V34 лучше сделать так:

1. Берём существующие папки `78–95`.
2. DINO получает embedding каждой фотографии.
3. Автоматически группируем фотографии внутри каждого адреса на несколько кластеров.
4. Каждый кластер = подслепок.
5. Для каждого подслепка сохраняем:
   - centroid;
   - embeddings;
   - representatives;
   - количество фотографий.
6. Общий слепок V34 хранит информацию обо всех подслепках.

Например:

```text
84_v34
   global
      centroid

   sub_01
      23 images
      centroid

   sub_02
      18 images
      centroid

   sub_03
      13 images
      centroid
```

### И главное

**V33 оставляем нетронутым.**

Получаем возможность честно сравнить:

```text
V33 → один centroid на адрес

V34 → несколько подслепков на адрес
```

и прогнать тот же тест `test_78_95`, чтобы увидеть, действительно ли V34 уменьшает ошибки.

Следующим шагом я предлагаю сделать только **механику V34 создания подслепков**, без изменения распознавания. Сначала создадим V34 и посмотрим, **как именно автоматически разбились 78–95**. Это будет самый правильный контрольный этап.

---

### 👤 **User** — 2026-08-15 01:13:48

lfdfq

---

### 🤖 **Assistant** — 2026-08-15 01:13:48

Да, понял 🙂 Делаем.

Начинаем **V34 с автоматического выделения подслепков**, V33 не трогаем.

Первым шагом я дам код именно для **создания V34**, затем прогоним на одном адресе, например **84**, и посмотрим, насколько разумно он разбился на ракурсы.

---

### 👤 **User** — 2026-08-15 01:13:58

приступаем

---

### 🤖 **Assistant** — 2026-08-15 01:14:01

Приступаем. **V33 не меняем.** Первый этап V34 — только создание подслепков. Распознавание пока оставляем прежним.

Сделаем отдельный модуль `v34`, чтобы можно было спокойно экспериментировать с разбиением ракурсов.

### Шаг 1 — посмотрим, какие зависимости уже есть

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import numpy
import torch
import transformers

print("numpy:", numpy.__version__)
print("torch:", torch.__version__)
print("transformers:", transformers.__version__)

try:
    import sklearn
    print("sklearn:", sklearn.__version__)
except ImportError:
    print("sklearn: NOT INSTALLED")
PY
```

И сразу покажи структуру одного исходного слепка:

```bash
echo "=== 84 ==="
find data/input/84 -maxdepth 1 -type f | wc -l

echo
echo "=== V33 84 ==="
cat data/fingerprints/84_v33/metadata.json

echo
echo "=== EMBEDDER ==="
sed -n '1,260p' app/core/embedder.py
```

### Что будем делать после этого

Для `84` запустим примерно такую схему:

```text
67 фотографий
       │
       ▼
   DINOv2 768
       │
       ▼
  кластеризация
       │
   ┌───┼────┐
   ▼   ▼    ▼
 sub1 sub2 sub3
  20   25    22
 фото  фото  фото
```

А результат:

```text
data/fingerprints/84_v34/
├── metadata.json
├── embeddings.npy
├── centroid.npy
├── representatives.npy
│
└── subfingerprints/
    ├── sub_01/
    ├── sub_02/
    └── sub_03/
```

**Важный момент:** количество подслепков не будем задавать вручную. Сначала посмотрим, как `84` естественно разбивается по DINO-эмбеддингам. Если получится, например, 3 группы и они визуально действительно соответствуют ракурсам — закрепим этот подход и прогоняем `78–95`.

Пришли вывод этих команд — и следующим сообщением делаем сам `V34`.

---

### 👤 **User** — 2026-08-15 01:14:14

int_mvp_v02
uv run python - <<'PY'
uv run python - <<'PY'
import numpy
import torchformers
import transformers
print("numpy:", numpy.__version__)
print("numpy:", numpy.__version__)
print("torch:", torch.__version__)s.__version__)
print("transformers:", transformers.__version__)
try:
try:import sklearn
    import sklearn:", sklearn.__version__)
    print("sklearn:", sklearn.__version__)
except ImportError: NOT INSTALLED")
    print("sklearn: NOT INSTALLED")
PY
numpy: 2.5.1
torch: 2.13.0+cu130
transformers: 5.15.0
sklearn: NOT INSTALLED
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:14:15

Отлично. Всё необходимое для DINOv2 уже есть, **sklearn не установлен** — и я бы пока его не ставил.

Сделаем V34 на уже имеющихся `numpy + torch`, чтобы не добавлять лишние зависимости.

Следующий шаг — проверить `84` и текущий embedder. Выполни **ровно этот блок**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== INPUT 84 ==="
find data/input/84 -maxdepth 1 -type f | wc -l

echo
echo "=== V33 / 84 ==="
cat data/fingerprints/84_v33/metadata.json

echo
echo "=== EMBEDDER ==="
sed -n '1,280p' app/core/embedder.py
```

Особенно нужен вывод `embedder.py`: V34 должен использовать **тот же DINOv2**, что уже дал нам рабочие V33.

После этого сразу сделаем:

```text
84 → DINO embeddings → автоматическое разбиение на подслепки → 84_v34
```

Причём **исходные фотографии и V33 вообще не изменяем**.

---

### 👤 **User** — 2026-08-15 01:14:42

print("torch:", torch.__version__)s.__version__)
print("transformers:", transformers.__version__)
try:
try:import sklearn
    import sklearn:", sklearn.__version__)
    print("sklearn:", sklearn.__version__)
except ImportError: NOT INSTALLED")
    print("sklearn: NOT INSTALLED")
PY
numpy: 2.5.1
torch: 2.13.0+cu130
transformers: 5.15.0
sklearn: NOT INSTALLED
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=== INPUT 84 ==="
find data/input/84 -maxdepth 1 -type f | wc -l

echo
echo "=== V33 / 84 ==="
cat data/fingerprints/84_v33/metadata.json

echo
echo "=== EMBEDDER ==="
sed -n '1,280p' app/core/embedder.py
=== INPUT 84 ===
54

=== V33 / 84 ===
{
  "id": "84_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 54,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "33 (1).JPG",
    "33 (10).JPG",
    "33 (11).JPG",
    "33 (12).JPG",
    "33 (13).JPG",
    "33 (14).JPG",
    "33 (15).JPG",
    "33 (16).JPG",
    "33 (17).JPG",
    "33 (18).JPG",
    "33 (19).JPG",
    "33 (2).JPG",
    "33 (20).JPG",
    "33 (21).JPG",
    "33 (22).JPG",
    "33 (23).JPG",
    "33 (24).JPG",
    "33 (25).JPG",
    "33 (26).JPG",
    "33 (27).JPG",
    "33 (28).JPG",
    "33 (29).JPG",
    "33 (3).JPG",
    "33 (30).JPG",
    "33 (31).JPG",
    "33 (4).JPG",
    "33 (5).JPG",
    "33 (6).JPG",
    "33 (7).JPG",
    "33 (8).JPG",
    "33 (9).JPG",
    "Ленина 125 А (1).JPG",
    "Ленина 125 А (22).JPG",
    "Ленина 125 А (7).JPG",
    "Ленина 125-127 А (1).JPG",
    "Ленина 125-127 А (11).JPG",
    "Ленина 125-127 А (16).JPG",
    "Ленина 125-127 А (18).JPG",
    "Ленина 125-127 А (2).JPG",
    "Ленина 125-127 А (21).JPG",
    "Ленина 125-127 А (22).JPG",
    "Ленина 125-127 А (25).JPG",
    "Ленина 125-127 А (27).JPG",
    "Ленина 125-127 А (31).JPG",
    "Ленина 125-127 А (33).JPG",
    "Ленина 125-127 А (35).JPG",
    "Ленина 125-127 А (44).JPG",
    "Ленина 125-127 А (50).JPG",
    "Ленина 125-127 А (59).JPG",
    "Ленина 125-127 А (6).JPG",
    "Ленина 125-127 А (69).JPG",
    "Ленина 125-127 А (9).JPG",
    "Ленина 125-127 А3 (19).JPG",
    "Ленина 125-127 А3 (4).JPG"
  ]
}
=== EMBEDDER ===
from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

class SceneEmbedder:
    """DINOv2 ViT-B/14 global embedding service.

    Uses Hugging Face Transformers instead of torch.hub.

    Output:
        global embedding: [N, 768]
    """

    def __init__(self, settings):
        self.settings = settings
        self.device = torch.device(settings.device)

        print(f"[SceneEmbedder] device={self.device}")

        if self.device.type == "cuda":
            print(
                f"[SceneEmbedder] GPU="
                f"{torch.cuda.get_device_name(0)}"
            )
            print(
                f"[SceneEmbedder] VRAM="
                f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
            )

        self.model_name = settings.model_name

        print(
            f"[SceneEmbedder] Loading DINOv2: "
            f"{self.model_name}"
        )

        self.processor = AutoImageProcessor.from_pretrained(
            self.model_name
        )

        self.model = AutoModel.from_pretrained(
            self.model_name
        )

        self.model = self.model.to(self.device)
        self.model.eval()

        self.dimension = 768

        print(
            f"[SceneEmbedder] embedding dimension="
            f"{self.dimension}"
        )
        print(
            "[SceneEmbedder] patch extraction=DISABLED "
            "(compact)"
        )
        print("[SceneEmbedder] Ready.")

    @torch.inference_mode()
    def embed_images(
        self,
        images: list[Image.Image],
        batch_size=None,
    ):
        batch_size = (
            batch_size
            or self.settings.batch_size
        )

        vectors = []

        for i in range(
            0,
            len(images),
            batch_size,
        ):
            batch_images = images[
                i:i + batch_size
            ]

            inputs = self.processor(
                images=batch_images,
                return_tensors="pt",
            )

            inputs = {
                key: value.to(
                    self.device,
                    non_blocking=True,
                )
                for key, value in inputs.items()
            }

            outputs = self.model(**inputs)

            # DINOv2 CLS token.
            features = outputs.last_hidden_state[:, 0, :]

            features = torch.nn.functional.normalize(
                features,
                dim=1,
            )

            vectors.append(
                features.float()
                .cpu()
                .numpy()
            )

        if not vectors:
            return np.empty(
                (0, self.dimension),
                dtype=np.float32,
            )

        return np.concatenate(
            vectors,
            axis=0,
        ).astype("float32")

    def embed_paths(self, paths):
        from .image import load_image

        images = [
            load_image(path)
            for path in paths
        ]

        return self.embed_images(images)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:14:44

Отлично. Теперь картина ясна.

У `84` **54 фотографии**, причём уже по именам видно, что там минимум два набора:

- `33 (...)` — 31 фото;
- `Ленина 125...` — 23 фото.

То есть `84` действительно хороший тест для V34: один общий слепок содержит разные визуальные группы.

### Делаем первый V34

Пока **не меняем `FingerprintManager`, CLI и распознавание**. Создадим отдельный экспериментальный скрипт:

```text
tools/create_v34_test.py
```

Он:
1. загрузит DINO embeddings всех 54 фотографий;
2. построит попарные cosine similarity;
3. автоматически найдёт группы;
4. сохранит `84_v34_test`;
5. запишет, какие фотографии попали в каждый подслепок.

Без `sklearn`.

Создай файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

mkdir -p tools

cat > tools/create_v34_test.py <<'PY'
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.image import image_files

INPUT = Path("data/input/84")
OUTPUT = Path("data/fingerprints/84_v34_test")

# Минимальная близость фотографий внутри одной группы.
# Начинаем достаточно мягко и посмотрим результат.
SIMILARITY_THRESHOLD = 0.72

def normalize_rows(x):
    x = np.asarray(x, dtype=np.float32)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return x / norms

def build_groups(embeddings):
    """
    Простая агломеративная группировка без sklearn.

    Фотография присоединяется к группе,
    если она достаточно похожа на centroid группы.
    """

    embeddings = normalize_rows(embeddings)

    groups = []

    # Сначала самые "центральные" изображения.
    similarity = embeddings @ embeddings.T
    centrality = similarity.mean(axis=1)

    order = np.argsort(-centrality)

    for idx in order:
        best_group = None
        best_score = -1.0

        for gi, group in enumerate(groups):
            centroid = normalize_rows(
                embeddings[group].mean(axis=0, keepdims=True)
            )[0]

            score = float(
                np.dot(embeddings[idx], centroid)
            )

            if score > best_score:
                best_score = score
                best_group = gi

        if (
            best_group is not None
            and best_score >= SIMILARITY_THRESHOLD
        ):
            groups[best_group].append(int(idx))
        else:
            groups.append([int(idx)])

    # Маленькие группы присоединяем к наиболее близкой
    # существующей группе.
    changed = True

    while changed:
        changed = False

        small = [
            i for i, group in enumerate(groups)
            if len(group) < 3
        ]

        if not small or len(groups) <= 1:
            break

        for gi in reversed(small):
            group = groups[gi]

            if len(groups) == 1:
                break

            group_centroid = normalize_rows(
                embeddings[group].mean(axis=0, keepdims=True)
            )[0]

            best_target = None
            best_score = -1.0

            for tj, target in enumerate(groups):
                if tj == gi:
                    continue

                target_centroid = normalize_rows(
                    embeddings[target].mean(axis=0, keepdims=True)
                )[0]

                score = float(
                    np.dot(
                        group_centroid,
                        target_centroid,
                    )
                )

                if score > best_score:
                    best_score = score
                    best_target = tj

            groups[best_target].extend(group)
            groups.pop(gi)

            changed = True

    return groups

def main():
    paths = image_files(INPUT)

    if not paths:
        raise RuntimeError(
            f"No images found: {INPUT}"
        )

    print("=" * 70)
    print("V34 TEST")
    print("=" * 70)
    print(f"Input: {INPUT}")
    print(f"Images: {len(paths)}")
    print(
        f"Similarity threshold: "
        f"{SIMILARITY_THRESHOLD}"
    )
    print()

    embedder = SceneEmbedder(settings)

    print("[V34] Creating DINO embeddings...")

    embeddings = embedder.embed_paths(paths)
    embeddings = normalize_rows(embeddings)

    print(
        f"[V34] Embeddings: "
        f"{embeddings.shape}"
    )

    groups = build_groups(embeddings)

    groups.sort(
        key=lambda x: len(x),
        reverse=True,
    )

    print()
    print("=" * 70)
    print("SUBFINGERPRINTS")
    print("=" * 70)

    for i, group in enumerate(groups, 1):
        print(
            f"sub_{i:02d}: "
            f"{len(group)} images"
        )

        for idx in group:
            print(
                f"    {Path(paths[idx]).name}"
            )

        print()

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.save(
        OUTPUT / "embeddings.npy",
        embeddings,
    )

    metadata = {
        "id": "84_v34_test",
        "version": "3.4-test",
        "model": "dinov2_vitb14",
        "images": len(paths),
        "dimension": int(embeddings.shape[1]),
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "subfingerprints": [],
    }

    for i, group in enumerate(groups, 1):
        centroid = normalize_rows(
            embeddings[group].mean(
                axis=0,
                keepdims=True,
            )
        )[0]

        subdir = OUTPUT / f"sub_{i:02d}"
        subdir.mkdir()

        np.save(
            subdir / "embeddings.npy",
            embeddings[group],
        )

        np.save(
            subdir / "centroid.npy",
            centroid,
        )

        names = [
            Path(paths[idx]).name
            for idx in group
        ]

        with (
            subdir / "metadata.json"
        ).open(
            "w",
            encoding="utf-8",
        ) as fh:
            json.dump(
                {
                    "id": f"84_v34_test_sub_{i:02d}",
                    "images": len(group),
                    "image_names": names,
                },
                fh,
                ensure_ascii=False,
                indent=2,
            )

        metadata["subfingerprints"].append(
            {
                "id": f"sub_{i:02d}",
                "images": len(group),
                "image_names": names,
            }
        )

    with (
        OUTPUT / "metadata.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as fh:
        json.dump(
            metadata,
            fh,
            ensure_ascii=False,
            indent=2,
        )

    print("=" * 70)
    print("V34 CREATED")
    print("=" * 70)
    print(f"Output: {OUTPUT}")
    print(f"Subfingerprints: {len(groups)}")

    for i, group in enumerate(groups, 1):
        print(
            f"  sub_{i:02d}: "
            f"{len(group)} images"
        )

if __name__ == "__main__":
    main()
PY
```

Теперь запускаем **только на 84**:

```bash
uv run python tools/create_v34_test.py
```

### Пока ничего больше не меняем

Особенно не трогаем:

- `84_v33`;
- `recognizer.py`;
- `fingerprint.py`;
- очередь;
- остальные слепки.

Нам сейчас нужно увидеть самое главное:

**как V34 разбил 54 фотографии на подслепки.**

Пришли весь вывод `uv run python tools/create_v34_test.py`. По нему уже решим, подходит ли порог `0.72` или его нужно изменить.

---

### 👤 **User** — 2026-08-15 01:15:33

======================================================================
SUBFINGERPRINTS
======================================================================
sub_01: 54 images
    Ленина 125 А (7).JPG
    33 (30).JPG
    Ленина 125-127 А (2).JPG
    33 (16).JPG
    Ленина 125-127 А3 (19).JPG
    Ленина 125-127 А3 (4).JPG
    Ленина 125 А (22).JPG
    33 (1).JPG
    Ленина 125 А (1).JPG
    33 (17).JPG
    33 (15).JPG
    33 (14).JPG
    Ленина 125-127 А (1).JPG
    Ленина 125-127 А (16).JPG
    33 (13).JPG
    33 (23).JPG
    Ленина 125-127 А (27).JPG
    Ленина 125-127 А (31).JPG
    33 (31).JPG
    Ленина 125-127 А (69).JPG
    Ленина 125-127 А (6).JPG
    33 (3).JPG
    Ленина 125-127 А (44).JPG
    33 (28).JPG
    33 (27).JPG
    Ленина 125-127 А (59).JPG
    33 (26).JPG
    Ленина 125-127 А (21).JPG
    Ленина 125-127 А (50).JPG
    33 (9).JPG
    33 (25).JPG
    33 (29).JPG
    33 (20).JPG
    33 (5).JPG
    33 (10).JPG
    33 (12).JPG
    33 (11).JPG
    33 (7).JPG
    33 (24).JPG
    Ленина 125-127 А (18).JPG
    33 (19).JPG
    33 (21).JPG
    Ленина 125-127 А (9).JPG
    Ленина 125-127 А (33).JPG
    Ленина 125-127 А (35).JPG
    33 (6).JPG
    Ленина 125-127 А (22).JPG
    33 (18).JPG
    33 (22).JPG
    Ленина 125-127 А (25).JPG
    33 (4).JPG
    33 (8).JPG
    Ленина 125-127 А (11).JPG
    33 (2).JPG

======================================================================
V34 CREATED
======================================================================
Output: data/fingerprints/84_v34_test
Subfingerprints: 1
  sub_01: 54 images

---

### 🤖 **Assistant** — 2026-08-15 01:15:34

Да. И это **очень полезный результат**: текущий алгоритм не годится для выделения ракурсов.

Причина проста: при `threshold=0.72` все 54 изображения достаточно близки к общему centroid, поэтому алгоритм последовательно складывает их в одну группу. Это не означает, что подслепков нет.

Нам нужен другой принцип.

### Что будем делать в V34

Для подслепков нельзя сравнивать фото только с **общим centroid**. Он как раз «смешивает» разные ракурсы.

Нужно искать **локальные группы**:

```text
54 фото
   ↓
DINO embeddings
   ↓
матрица сходства
   ↓
поиск плотных групп
   ↓
┌─────────┬─────────┬─────────┐
│ ракурс 1│ ракурс 2│ ракурс 3│
│ 18 фото │ 21 фото │ 15 фото │
└─────────┴─────────┴─────────┘
```

Причём нам важно, чтобы **каждая фотография могла иметь соседей**, а не обязательно быть близкой к среднему всей группы.

### Но сначала сделаем правильный эксперимент

Не будем пока писать полноценный V34.

Для `84` построим **таблицу ближайших соседей** для каждого изображения.

Например:

```text
33 (1).JPG

  33 (2).JPG          0.96
  33 (3).JPG          0.95
  33 (4).JPG          0.94
  Ленина 125 А (7)    0.73
  ...
```

Если действительно есть разные ракурсы, мы увидим, что фотографии естественно образуют несколько плотных «островов».

Это даст нам правильный порог для V34, вместо того чтобы гадать `0.72`.

---

### Сейчас сделаем диагностику

Создай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > tools/analyze_v34_neighbors.py <<'PY'
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.image import image_files

INPUT = Path("data/input/84")

TOP_K = 5

def normalize_rows(x):
    x = np.asarray(x, dtype=np.float32)

    norms = np.linalg.norm(
        x,
        axis=1,
        keepdims=True,
    )

    norms[norms == 0] = 1.0

    return x / norms

def main():

    paths = image_files(INPUT)

    print(f"Images: {len(paths)}")

    embedder = SceneEmbedder(settings)

    embeddings = embedder.embed_paths(paths)
    embeddings = normalize_rows(embeddings)

    similarity = embeddings @ embeddings.T

    print()
    print("=" * 80)
    print("NEAREST NEIGHBORS")
    print("=" * 80)

    for i in range(len(paths)):

        scores = similarity[i].copy()

        # Не сравниваем изображение с самим собой.
        scores[i] = -1.0

        indices = np.argsort(
            scores
        )[-TOP_K:][::-1]

        print()
        print(
            f"[{i:02d}] "
            f"{Path(paths[i]).name}"
        )

        for rank, j in enumerate(
            indices,
            1,
        ):
            print(
                f"    {rank}. "
                f"{scores[j]:.4f}  "
                f"{Path(paths[j]).name}"
            )

    print()
    print("=" * 80)
    print("SIMILARITY DISTRIBUTION")
    print("=" * 80)

    upper = similarity[
        np.triu_indices(
            len(paths),
            k=1,
        )
    ]

    for threshold in [
        0.95,
        0.93,
        0.91,
        0.89,
        0.87,
        0.85,
        0.83,
        0.80,
    ]:

        count = int(
            np.sum(
                upper >= threshold
            )
        )

        print(
            f">= {threshold:.2f}: "
            f"{count} pairs"
        )

if __name__ == "__main__":
    main()
PY

uv run python tools/analyze_v34_neighbors.py
```

**Пришли вывод.**

И ещё: созданный нами `84_v34_test` пока можно не трогать. Это просто экспериментальный каталог. После диагностики мы его либо заменим правильным V34, либо удалим.

---

### 👤 **User** — 2026-08-15 01:16:40

================================================================================
NEAREST NEIGHBORS
================================================================================

[00] 33 (1).JPG
    1. 0.9377  33 (30).JPG
    2. 0.9365  Ленина 125 А (1).JPG
    3. 0.9327  33 (31).JPG
    4. 0.9285  33 (23).JPG
    5. 0.9279  Ленина 125 А (7).JPG

[01] 33 (10).JPG
    1. 0.9341  33 (9).JPG
    2. 0.9149  33 (7).JPG
    3. 0.9009  33 (11).JPG
    4. 0.8945  33 (3).JPG
    5. 0.8882  33 (12).JPG

[02] 33 (11).JPG
    1. 0.9151  33 (9).JPG
    2. 0.9009  33 (10).JPG
    3. 0.8920  33 (3).JPG
    4. 0.8916  33 (12).JPG
    5. 0.8895  33 (25).JPG

[03] 33 (12).JPG
    1. 0.9160  33 (9).JPG
    2. 0.9153  Ленина 125-127 А (59).JPG
    3. 0.9139  33 (7).JPG
    4. 0.8975  Ленина 125-127 А (50).JPG
    5. 0.8968  Ленина 125-127 А (2).JPG

[04] 33 (13).JPG
    1. 0.9752  33 (14).JPG
    2. 0.9706  33 (16).JPG
    3. 0.9423  33 (15).JPG
    4. 0.9421  33 (17).JPG
    5. 0.9413  Ленина 125-127 А (2).JPG

[05] 33 (14).JPG
    1. 0.9752  33 (13).JPG
    2. 0.9743  33 (16).JPG
    3. 0.9559  33 (15).JPG
    4. 0.9492  33 (17).JPG
    5. 0.9473  Ленина 125-127 А (1).JPG

[06] 33 (15).JPG
    1. 0.9631  33 (16).JPG
    2. 0.9559  33 (14).JPG
    3. 0.9439  33 (17).JPG
    4. 0.9427  Ленина 125 А (22).JPG
    5. 0.9423  33 (13).JPG

[07] 33 (16).JPG
    1. 0.9743  33 (14).JPG
    2. 0.9706  33 (13).JPG
    3. 0.9631  33 (15).JPG
    4. 0.9522  33 (17).JPG
    5. 0.9407  Ленина 125-127 А (1).JPG

[08] 33 (17).JPG
    1. 0.9522  33 (16).JPG
    2. 0.9492  33 (14).JPG
    3. 0.9439  33 (15).JPG
    4. 0.9421  33 (13).JPG
    5. 0.9298  Ленина 125 А (7).JPG

[09] 33 (18).JPG
    1. 0.9281  33 (4).JPG
    2. 0.9068  33 (6).JPG
    3. 0.8687  Ленина 125 А (22).JPG
    4. 0.8656  33 (26).JPG
    5. 0.8577  33 (28).JPG

[10] 33 (19).JPG
    1. 0.9515  33 (20).JPG
    2. 0.9091  33 (23).JPG
    3. 0.9061  33 (31).JPG
    4. 0.9034  33 (24).JPG
    5. 0.8798  33 (1).JPG

[11] 33 (2).JPG
    1. 0.7947  33 (22).JPG
    2. 0.7905  Ленина 125-127 А (22).JPG
    3. 0.7820  33 (29).JPG
    4. 0.7722  Ленина 125-127 А (11).JPG
    5. 0.7622  33 (28).JPG

[12] 33 (20).JPG
    1. 0.9515  33 (19).JPG
    2. 0.9333  33 (23).JPG
    3. 0.9223  33 (31).JPG
    4. 0.9009  33 (24).JPG
    5. 0.9004  Ленина 125 А (7).JPG

[13] 33 (21).JPG
    1. 0.9010  33 (26).JPG
    2. 0.8917  33 (27).JPG
    3. 0.8906  33 (28).JPG
    4. 0.8802  Ленина 125-127 А3 (4).JPG
    5. 0.8799  Ленина 125-127 А (25).JPG

[14] 33 (22).JPG
    1. 0.8712  33 (29).JPG
    2. 0.8679  33 (28).JPG
    3. 0.8628  33 (26).JPG
    4. 0.8459  33 (27).JPG
    5. 0.8457  33 (25).JPG

[15] 33 (23).JPG
    1. 0.9333  33 (20).JPG
    2. 0.9285  33 (1).JPG
    3. 0.9171  33 (31).JPG
    4. 0.9153  33 (30).JPG
    5. 0.9151  Ленина 125-127 А (2).JPG

[16] 33 (24).JPG
    1. 0.9078  33 (23).JPG
    2. 0.9034  33 (19).JPG
    3. 0.9009  33 (20).JPG
    4. 0.8909  Ленина 125-127 А3 (19).JPG
    5. 0.8854  33 (1).JPG

[17] 33 (25).JPG
    1. 0.9446  33 (27).JPG
    2. 0.9400  33 (26).JPG
    3. 0.9141  33 (23).JPG
    4. 0.9047  Ленина 125 А (7).JPG
    5. 0.8993  33 (30).JPG

[18] 33 (26).JPG
    1. 0.9524  33 (27).JPG
    2. 0.9400  33 (25).JPG
    3. 0.9108  33 (28).JPG
    4. 0.9062  33 (17).JPG
    5. 0.9058  Ленина 125-127 А3 (4).JPG

[19] 33 (27).JPG
    1. 0.9524  33 (26).JPG
    2. 0.9446  33 (25).JPG
    3. 0.9121  33 (30).JPG
    4. 0.9116  Ленина 125 А (7).JPG
    5. 0.9058  Ленина 125-127 А3 (19).JPG

[20] 33 (28).JPG
    1. 0.9287  33 (29).JPG
    2. 0.9186  Ленина 125 А (22).JPG
    3. 0.9155  33 (30).JPG
    4. 0.9137  Ленина 125-127 А3 (4).JPG
    5. 0.9108  33 (26).JPG

[21] 33 (29).JPG
    1. 0.9287  33 (28).JPG
    2. 0.9108  Ленина 125-127 А3 (4).JPG
    3. 0.8972  33 (26).JPG
    4. 0.8893  33 (27).JPG
    5. 0.8858  33 (30).JPG

[22] 33 (3).JPG
    1. 0.9079  33 (9).JPG
    2. 0.9075  33 (5).JPG
    3. 0.9016  Ленина 125 А (7).JPG
    4. 0.9010  Ленина 125-127 А (69).JPG
    5. 0.9006  33 (28).JPG

[23] 33 (30).JPG
    1. 0.9443  Ленина 125 А (7).JPG
    2. 0.9392  Ленина 125-127 А (2).JPG
    3. 0.9382  Ленина 125 А (22).JPG
    4. 0.9378  Ленина 125-127 А3 (19).JPG
    5. 0.9377  33 (1).JPG

[24] 33 (31).JPG
    1. 0.9364  Ленина 125 А (7).JPG
    2. 0.9327  33 (1).JPG
    3. 0.9282  Ленина 125 А (1).JPG
    4. 0.9248  33 (16).JPG
    5. 0.9223  33 (20).JPG

[25] 33 (4).JPG
    1. 0.9379  33 (6).JPG
    2. 0.9281  33 (18).JPG
    3. 0.8606  33 (26).JPG
    4. 0.8587  33 (28).JPG
    5. 0.8539  Ленина 125 А (22).JPG

[26] 33 (5).JPG
    1. 0.9223  33 (7).JPG
    2. 0.9100  Ленина 125-127 А (59).JPG
    3. 0.9075  33 (3).JPG
    4. 0.9043  Ленина 125-127 А (69).JPG
    5. 0.8990  33 (9).JPG

[27] 33 (6).JPG
    1. 0.9379  33 (4).JPG
    2. 0.9068  33 (18).JPG
    3. 0.8812  33 (28).JPG
    4. 0.8698  Ленина 125 А (22).JPG
    5. 0.8624  33 (26).JPG

[28] 33 (7).JPG
    1. 0.9374  33 (9).JPG
    2. 0.9223  33 (5).JPG
    3. 0.9149  33 (10).JPG
    4. 0.9139  33 (12).JPG
    5. 0.9058  Ленина 125-127 А (59).JPG

[29] 33 (8).JPG
    1. 0.8756  33 (11).JPG
    2. 0.8721  33 (10).JPG
    3. 0.8611  33 (9).JPG
    4. 0.8518  33 (7).JPG
    5. 0.8506  33 (5).JPG

[30] 33 (9).JPG
    1. 0.9374  33 (7).JPG
    2. 0.9341  33 (10).JPG
    3. 0.9160  33 (12).JPG
    4. 0.9151  33 (11).JPG
    5. 0.9079  33 (3).JPG

[31] Ленина 125 А (1).JPG
    1. 0.9540  Ленина 125 А (7).JPG
    2. 0.9529  Ленина 125 А (22).JPG
    3. 0.9416  Ленина 125-127 А (1).JPG
    4. 0.9410  Ленина 125-127 А (2).JPG
    5. 0.9375  Ленина 125-127 А (16).JPG

[32] Ленина 125 А (22).JPG
    1. 0.9529  Ленина 125 А (1).JPG
    2. 0.9466  Ленина 125 А (7).JPG
    3. 0.9427  33 (15).JPG
    4. 0.9382  33 (30).JPG
    5. 0.9337  Ленина 125-127 А (1).JPG

[33] Ленина 125 А (7).JPG
    1. 0.9540  Ленина 125 А (1).JPG
    2. 0.9466  Ленина 125 А (22).JPG
    3. 0.9443  33 (30).JPG
    4. 0.9439  Ленина 125-127 А (2).JPG
    5. 0.9388  Ленина 125-127 А (27).JPG

[34] Ленина 125-127 А (1).JPG
    1. 0.9492  Ленина 125-127 А (21).JPG
    2. 0.9473  33 (14).JPG
    3. 0.9437  Ленина 125-127 А (2).JPG
    4. 0.9425  Ленина 125-127 А (31).JPG
    5. 0.9416  Ленина 125 А (1).JPG

[35] Ленина 125-127 А (11).JPG
    1. 0.9537  Ленина 125-127 А (22).JPG
    2. 0.9013  Ленина 125-127 А (33).JPG
    3. 0.9004  Ленина 125-127 А (35).JPG
    4. 0.8183  33 (29).JPG
    5. 0.8171  33 (28).JPG

[36] Ленина 125-127 А (16).JPG
    1. 0.9391  Ленина 125-127 А (2).JPG
    2. 0.9375  Ленина 125 А (1).JPG
    3. 0.9359  Ленина 125-127 А (50).JPG
    4. 0.9324  Ленина 125 А (7).JPG
    5. 0.9225  Ленина 125-127 А (27).JPG

[37] Ленина 125-127 А (18).JPG
    1. 0.9129  Ленина 125-127 А (59).JPG
    2. 0.8961  33 (5).JPG
    3. 0.8944  Ленина 125-127 А (69).JPG
    4. 0.8912  33 (12).JPG
    5. 0.8889  Ленина 125-127 А (2).JPG

[38] Ленина 125-127 А (2).JPG
    1. 0.9531  Ленина 125-127 А (21).JPG
    2. 0.9456  33 (14).JPG
    3. 0.9439  Ленина 125 А (7).JPG
    4. 0.9437  Ленина 125-127 А (1).JPG
    5. 0.9434  Ленина 125-127 А (27).JPG

[39] Ленина 125-127 А (21).JPG
    1. 0.9531  Ленина 125-127 А (2).JPG
    2. 0.9492  Ленина 125-127 А (1).JPG
    3. 0.9353  33 (14).JPG
    4. 0.9318  Ленина 125-127 А (44).JPG
    5. 0.9285  Ленина 125 А (7).JPG

[40] Ленина 125-127 А (22).JPG
    1. 0.9537  Ленина 125-127 А (11).JPG
    2. 0.9419  Ленина 125-127 А (35).JPG
    3. 0.9368  Ленина 125-127 А (33).JPG
    4. 0.8654  33 (28).JPG
    5. 0.8565  33 (29).JPG

[41] Ленина 125-127 А (25).JPG
    1. 0.8799  33 (21).JPG
    2. 0.8746  Ленина 125-127 А3 (4).JPG
    3. 0.8430  33 (29).JPG
    4. 0.8430  Ленина 125-127 А3 (19).JPG
    5. 0.8419  33 (26).JPG

[42] Ленина 125-127 А (27).JPG
    1. 0.9568  Ленина 125-127 А (44).JPG
    2. 0.9434  Ленина 125-127 А (2).JPG
    3. 0.9388  Ленина 125 А (7).JPG
    4. 0.9349  33 (14).JPG
    5. 0.9327  Ленина 125 А (1).JPG

[43] Ленина 125-127 А (31).JPG
    1. 0.9425  Ленина 125-127 А (1).JPG
    2. 0.9354  33 (16).JPG
    3. 0.9341  33 (15).JPG
    4. 0.9340  33 (14).JPG
    5. 0.9291  Ленина 125 А (7).JPG

[44] Ленина 125-127 А (33).JPG
    1. 0.9448  Ленина 125-127 А (35).JPG
    2. 0.9368  Ленина 125-127 А (22).JPG
    3. 0.9013  Ленина 125-127 А (11).JPG
    4. 0.8644  33 (29).JPG
    5. 0.8562  Ленина 125-127 А3 (4).JPG

[45] Ленина 125-127 А (35).JPG
    1. 0.9448  Ленина 125-127 А (33).JPG
    2. 0.9419  Ленина 125-127 А (22).JPG
    3. 0.9004  Ленина 125-127 А (11).JPG
    4. 0.8559  Ленина 125-127 А (50).JPG
    5. 0.8534  33 (28).JPG

[46] Ленина 125-127 А (44).JPG
    1. 0.9568  Ленина 125-127 А (27).JPG
    2. 0.9362  Ленина 125-127 А (2).JPG
    3. 0.9323  Ленина 125-127 А (1).JPG
    4. 0.9321  Ленина 125 А (1).JPG
    5. 0.9318  Ленина 125-127 А (21).JPG

[47] Ленина 125-127 А (50).JPG
    1. 0.9359  Ленина 125-127 А (16).JPG
    2. 0.9230  Ленина 125 А (7).JPG
    3. 0.9102  Ленина 125-127 А (2).JPG
    4. 0.9046  Ленина 125-127 А (27).JPG
    5. 0.8975  33 (12).JPG

[48] Ленина 125-127 А (59).JPG
    1. 0.9285  Ленина 125-127 А (2).JPG
    2. 0.9229  Ленина 125-127 А (69).JPG
    3. 0.9153  33 (12).JPG
    4. 0.9153  33 (1).JPG
    5. 0.9151  Ленина 125-127 А (16).JPG

[49] Ленина 125-127 А (6).JPG
    1. 0.9358  Ленина 125-127 А3 (19).JPG
    2. 0.9287  Ленина 125-127 А (1).JPG
    3. 0.9278  Ленина 125-127 А (2).JPG
    4. 0.9270  Ленина 125-127 А3 (4).JPG
    5. 0.9259  Ленина 125-127 А (21).JPG

[50] Ленина 125-127 А (69).JPG
    1. 0.9229  Ленина 125-127 А (59).JPG
    2. 0.9175  Ленина 125 А (1).JPG
    3. 0.9119  Ленина 125 А (7).JPG
    4. 0.9097  33 (30).JPG
    5. 0.9059  Ленина 125 А (22).JPG

[51] Ленина 125-127 А (9).JPG
    1. 0.8944  Ленина 125-127 А (27).JPG
    2. 0.8912  Ленина 125-127 А (69).JPG
    3. 0.8888  33 (16).JPG
    4. 0.8844  Ленина 125-127 А (44).JPG
    5. 0.8790  Ленина 125-127 А (1).JPG

[52] Ленина 125-127 А3 (19).JPG
    1. 0.9477  Ленина 125-127 А3 (4).JPG
    2. 0.9378  33 (30).JPG
    3. 0.9374  Ленина 125 А (7).JPG
    4. 0.9358  Ленина 125-127 А (6).JPG
    5. 0.9272  Ленина 125 А (22).JPG

[53] Ленина 125-127 А3 (4).JPG
    1. 0.9477  Ленина 125-127 А3 (19).JPG
    2. 0.9339  Ленина 125 А (7).JPG
    3. 0.9270  Ленина 125-127 А (6).JPG
    4. 0.9265  Ленина 125-127 А (2).JPG
    5. 0.9247  33 (17).JPG

================================================================================
SIMILARITY DISTRIBUTION
================================================================================
>= 0.95: 13 pairs
>= 0.93: 74 pairs
>= 0.91: 219 pairs
>= 0.89: 377 pairs
>= 0.87: 570 pairs
>= 0.85: 775 pairs
>= 0.83: 928 pairs
>= 0.80: 1137 pairs

---

### 🤖 **Assistant** — 2026-08-15 01:16:40

Да. По этому тесту уже видно важную вещь: **V34 с одним `sub_01` пока фактически не сделал подслепки** — все 54 изображения попали в одну группу.

При этом сами данные показывают, что внутри `84` действительно есть несколько устойчивых кластеров ракурсов:

- `33 (13–17)` — очень плотная группа, ~0.96–0.98.
- `33 (19–20, 23–24)` — отдельная группа.
- `33 (25–29)` — ещё одна группа.
- `33 (4, 6, 18)` — отдельная.
- `33 (7, 9–12)` — отдельная.
- `Ленина 125-127 А (11, 22, 33, 35)` — очень характерная группа.
- `Ленина 125-127 А (1, 2, 21, 27, 44)` — ещё одна.
- `Ленина 125 А (1, 7, 22)` — отдельная.
- `Ленина 125-127 А3 (4, 19)` — отдельная пара.

То есть **идея подслепков подтверждается самими результатами**.

Но сейчас я бы **не менял алгоритм ещё раз вслепую**. Следующий шаг лучше сделать очень конкретным:

### Шаг 1 — посмотреть, как сейчас V34 формирует `sub_01`

Нам нужно увидеть код, который отвечает именно за создание subfingerprints. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE "subfinger|sub_fingerprint|subfingerprint|sub_01|cluster|clusters" app/core app/pipeline
```

И затем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find app -type f -name "*.py" -print
```

**Пока ничего не исправляем.**

Я хочу сначала увидеть текущую реализацию V34, потому что по результату `54 images -> sub_01: 54 images` похоже, что механизм кластеризации либо слишком мягкий, либо сейчас используется только как заготовка.

После этого сделаем **минимальное изменение именно в V34**, чтобы из этих 54 фотографий получить реальные подслепки по ракурсам, не трогая рабочий V33.

---

### 👤 **User** — 2026-08-15 01:17:17

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE "subfinger|sub_fingerprint|subfingerprint|sub_01|cluster|clusters" app/core app/pipeline
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

find app -type f -name "*.py" -print
app/core/scene_analyzer.py
app/core/recognizer.py
app/core/config.py
app/core/__init__.py
app/core/embedder.py
app/core/fingerprint.py
app/core/image.py
app/pipeline/__init__.py
app/pipeline/worker.py
app/pipeline/queue.py
app/main.py
app/__init__.py
app/cli.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:17:18

Отлично. Теперь ясно: **механизма подслепков в `app` вообще нет**. Значит, тот вывод `sub_01: 54 images` был сделан отдельным тестовым кодом, а не настоящей реализацией V34.

Не будем сейчас усложнять архитектуру. Делаем следующий шаг — **найдём, где именно создавался этот тест V34**, чтобы не переписывать существующий `fingerprint.py` наугад.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE "V34 CREATED|SUBFINGERPRINTS|sub_01|NEAREST NEIGHBORS|SIMILARITY DISTRIBUTION" . \
    --exclude-dir=.venv \
    --exclude-dir=.git \
    --exclude="*.pyc"
```

И ещё:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find . -maxdepth 2 -type f \( \
    -name "*.py" -o \
    -name "*.sh" -o \
    -name "*.json" \
\) | sort
```

### Что сейчас делаем

Пока **ничего не меняем**:

- V33 оставляем как рабочий вариант.
- `84_v34_test` не удаляем.
- `data/jobs.db` не трогаем.
- Очередь тоже не меняем.
- Новый V34 пока не запускаем.

Наша цель сейчас — найти тот тестовый скрипт, который выдал:

```text
SUBFINGERPRINTS
sub_01: 54 images

V34 CREATED
```

После этого я посмотрю его логику и предложу **минимальное изменение**, чтобы получить, например:

```text
84_v34
 ├── sub_01  ~ 10 images
 ├── sub_02  ~ 8 images
 ├── sub_03  ~ 12 images
 ├── sub_04  ~ 7 images
 ...
```

причём **один общий слепок 84 будет содержать эти подслепки**, а не превращаться в набор независимых адресов.

Это как раз соответствует тому, к чему мы пришли: **один объект → несколько устойчивых ракурсов/подслепков**.

---

### 👤 **User** — 2026-08-15 01:17:56

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE "V34 CREATED|SUBFINGERPRINTS|sub_01|NEAREST NEIGHBORS|SIMILARITY DISTRIBUTION" . \
    --exclude-dir=.venv \
    --exclude-dir=.git \
    --exclude="*.pyc"
./data/fingerprints/84_v34_test/sub_01/metadata.json:2:  "id": "84_v34_test_sub_01",
./data/fingerprints/84_v34_test/metadata.json:8:  "subfingerprints": [
./data/fingerprints/84_v34_test/metadata.json:10:      "id": "sub_01",
./tools/create_v34_test.py:167:    print("SUBFINGERPRINTS")
./tools/create_v34_test.py:203:        "subfingerprints": [],
./tools/create_v34_test.py:249:        metadata["subfingerprints"].append(
./tools/create_v34_test.py:271:    print("V34 CREATED")
./tools/create_v34_test.py:274:    print(f"Subfingerprints: {len(groups)}")
./tools/analyze_v34_neighbors.py:44:    print("NEAREST NEIGHBORS")
./tools/analyze_v34_neighbors.py:76:    print("SIMILARITY DISTRIBUTION")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

find . -maxdepth 2 -type f $ \
    -name "*.py" -o \
    -name "*.sh" -o \
    -name "*.json" \
$ | sort
./app_backup_before_patch/cli.py
./app_backup_before_patch/__init__.py
./app_backup_before_patch/main.py
./app/cli.py
./app/__init__.py
./app/main.py
./backup_patch_tokens_20260808_131532/embedder.py
./backup_patch_tokens_20260808_131532/fingerprint.py
./backup_patch_tokens_20260808_131532/recognizer.py
./backup_patch_tokens_20260808_131532/scene_analyzer.py
./backup_v31_final_20260808_231056/cli.py
./backup_v31_fix_20260808_230926/cli.py
./backup_v31_fix_20260808_230926/embedder.py
./backup_v31_fix_20260808_230926/fingerprint.py
./backup_v31_fix_20260808_230926/recognizer.py
./backup_v31_fix_20260808_230926/scene_analyzer.py
./classify_final_test.py
./classify_test.py
./classify_test_results.py
./classify_test.sh
./classify_test_top1.sh
./final_test_78_95.json
./fix_v31_final.sh
./test_78_95_results.json
./tools/analyze_v34_neighbors.py
./tools/create_v34_test.py
./upgrade_patch_tokens.sh
./upgrade_v31_final.sh
./upgrade_v31_fix.sh
./upgrade_v31.sh
./upgrade_v3.sh
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:17:58

Вот теперь всё понятно. 👍

V34 действительно существует как **отдельный экспериментальный инструмент**, и главное — он **не затрагивает рабочий V33**:

```text
tools/create_v34_test.py
tools/analyze_v34_neighbors.py
data/fingerprints/84_v34_test/
```

И сейчас его логика дала:

```text
54 изображения → 1 подслепок
```

Значит, следующий шаг — посмотреть сам алгоритм группировки.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,330p' tools/create_v34_test.py
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,130p' tools/analyze_v34_neighbors.py
```

**Пока ничего не меняй и не запускай.**

После этого я разберу именно существующий V34 и мы сделаем минимальную корректировку кластеризации. Я бы пока не трогал ни `fingerprint.py`, ни `recognizer.py`, ни очередь.

Причём я уже вижу правильную архитектуру для V34:

```text
84
│
├── sub_01  ← один ракурс / сцена
│   ├── изображения
│   └── компактный descriptor
│
├── sub_02  ← другой ракурс
│   ├── изображения
│   └── descriptor
│
├── sub_03
│   └── ...
│
└── общий descriptor 84
```

А при распознавании:

```text
новое фото
      │
      ▼
   V34: 84
      │
      ├── sub_01 → 0.94
      ├── sub_02 → 0.71
      ├── sub_03 → 0.91
      └── ...
      
      ▼
   итоговый match = 0.94
```

То есть **подслепки не заменяют общий слепок, а дают ему несколько "точек зрения"**. Это особенно важно именно для твоего случая с фотографиями одного объекта с разных направлений.

---

### 👤 **User** — 2026-08-15 01:18:26

int_mvp_v02

sed -n '1,330p' tools/create_v34_test.py
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.image import image_files

INPUT = Path("data/input/84")
OUTPUT = Path("data/fingerprints/84_v34_test")

# Минимальная близость фотографий внутри одной группы.
# Начинаем достаточно мягко и посмотрим результат.
SIMILARITY_THRESHOLD = 0.72

def normalize_rows(x):
    x = np.asarray(x, dtype=np.float32)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return x / norms

def build_groups(embeddings):
    """
    Простая агломеративная группировка без sklearn.

    Фотография присоединяется к группе,
    если она достаточно похожа на centroid группы.
    """

    embeddings = normalize_rows(embeddings)

    groups = []

    # Сначала самые "центральные" изображения.
    similarity = embeddings @ embeddings.T
    centrality = similarity.mean(axis=1)

    order = np.argsort(-centrality)

    for idx in order:
        best_group = None
        best_score = -1.0

        for gi, group in enumerate(groups):
            centroid = normalize_rows(
                embeddings[group].mean(axis=0, keepdims=True)
            )[0]

            score = float(
                np.dot(embeddings[idx], centroid)
            )

            if score > best_score:
                best_score = score
                best_group = gi

        if (
            best_group is not None
            and best_score >= SIMILARITY_THRESHOLD
        ):
            groups[best_group].append(int(idx))
        else:
            groups.append([int(idx)])

    # Маленькие группы присоединяем к наиболее близкой
    # существующей группе.
    changed = True

    while changed:
        changed = False

        small = [
            i for i, group in enumerate(groups)
            if len(group) < 3
        ]

        if not small or len(groups) <= 1:
            break

        for gi in reversed(small):
            group = groups[gi]

            if len(groups) == 1:
                break

            group_centroid = normalize_rows(
                embeddings[group].mean(axis=0, keepdims=True)
            )[0]

            best_target = None
            best_score = -1.0

            for tj, target in enumerate(groups):
                if tj == gi:
                    continue

                target_centroid = normalize_rows(
                    embeddings[target].mean(axis=0, keepdims=True)
                )[0]

                score = float(
                    np.dot(
                        group_centroid,
                        target_centroid,
                    )
                )

                if score > best_score:
                    best_score = score
                    best_target = tj

            groups[best_target].extend(group)
            groups.pop(gi)

            changed = True

    return groups

def main():
    paths = image_files(INPUT)

    if not paths:
        raise RuntimeError(
            f"No images found: {INPUT}"
        )

    print("=" * 70)
    print("V34 TEST")
    print("=" * 70)
    print(f"Input: {INPUT}")
    print(f"Images: {len(paths)}")
    print(
        f"Similarity threshold: "
        f"{SIMILARITY_THRESHOLD}"
    )
    print()

    embedder = SceneEmbedder(settings)

    print("[V34] Creating DINO embeddings...")

    embeddings = embedder.embed_paths(paths)
    embeddings = normalize_rows(embeddings)

    print(
        f"[V34] Embeddings: "
        f"{embeddings.shape}"
    )

    groups = build_groups(embeddings)

    groups.sort(
        key=lambda x: len(x),
        reverse=True,
    )

    print()
    print("=" * 70)
    print("SUBFINGERPRINTS")
    print("=" * 70)

    for i, group in enumerate(groups, 1):
        print(
            f"sub_{i:02d}: "
            f"{len(group)} images"
        )

        for idx in group:
            print(
                f"    {Path(paths[idx]).name}"
            )

        print()

    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.save(
        OUTPUT / "embeddings.npy",
        embeddings,
    )

    metadata = {
        "id": "84_v34_test",
        "version": "3.4-test",
        "model": "dinov2_vitb14",
        "images": len(paths),
        "dimension": int(embeddings.shape[1]),
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "subfingerprints": [],
    }

    for i, group in enumerate(groups, 1):
        centroid = normalize_rows(
            embeddings[group].mean(
                axis=0,
                keepdims=True,
            )
        )[0]

        subdir = OUTPUT / f"sub_{i:02d}"
        subdir.mkdir()

        np.save(
            subdir / "embeddings.npy",
            embeddings[group],
        )

        np.save(
            subdir / "centroid.npy",
            centroid,
        )

        names = [
            Path(paths[idx]).name
            for idx in group
        ]

        with (
            subdir / "metadata.json"
        ).open(
            "w",
            encoding="utf-8",
        ) as fh:
            json.dump(
                {
                    "id": f"84_v34_test_sub_{i:02d}",
                    "images": len(group),
                    "image_names": names,
                },
                fh,
                ensure_ascii=False,
                indent=2,
            )

        metadata["subfingerprints"].append(
            {
                "id": f"sub_{i:02d}",
                "images": len(group),
                "image_names": names,
            }
        )

    with (
        OUTPUT / "metadata.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as fh:
        json.dump(
            metadata,
            fh,
            ensure_ascii=False,
            indent=2,
        )

    print("=" * 70)
    print("V34 CREATED")
    print("=" * 70)
    print(f"Output: {OUTPUT}")
    print(f"Subfingerprints: {len(groups)}")

    for i, group in enumerate(groups, 1):
        print(
            f"  sub_{i:02d}: "
            f"{len(group)} images"
        )

if __name__ == "__main__":
    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:18:28

Да. Теперь видно главное: **текущий `create_v34_test.py` технически работает, но алгоритм группировки сейчас слишком мягкий**.

При `SIMILARITY_THRESHOLD = 0.72` он закономерно собрал все 54 фотографии в один `sub_01`. Для наших данных это практически ничего не даёт.

### Что делаем дальше

Не будем усложнять DINO и не будем ставить `sklearn`. У нас уже есть хорошие 768-мерные embeddings.

Нужно подобрать порог именно для **разделения одного адресного слепка на подслепки**.

По твоему выводу видно:

- `0.95+` — всего 13 пар
- `0.93+` — 74 пары
- `0.91+` — 219 пар
- `0.89+` — 377 пар
- `0.87+` — 570 пар
- `0.85+` — 775 пар

То есть `0.72` действительно слишком низко.

### Предлагаю сначала сделать тест порогов

Не трогаем основной V34. Сделаем диагностический прогон для:

**0.85 / 0.87 / 0.89 / 0.91 / 0.93 / 0.95**

и посмотрим, сколько получается групп и какого они размера.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp tools/create_v34_test.py tools/create_v34_sweep.py

python3 - <<'PY'
from pathlib import Path

p = Path("tools/create_v34_sweep.py")
text = p.read_text()

text = text.replace(
    'SIMILARITY_THRESHOLD = 0.72',
    'SIMILARITY_THRESHOLD = 0.90'
)

p.write_text(text)

print("created tools/create_v34_sweep.py")
PY
```

Но **не запускай его пока**.

Я предлагаю чуть лучше: сейчас переделаем этот тест так, чтобы **одним запуском он прогнал все 6 порогов и ничего не сохранял**, только покажет:

```text
THRESHOLD  GROUPS  SIZES
0.85       1       54
0.87       ...
0.89       ...
0.91       ...
0.93       ...
0.95       ...
```

После этого выберем оптимальный порог и уже сделаем настоящий формат:

```text
84_v34/
├── metadata.json
├── embeddings.npy
├── sub_01/
│   ├── embeddings.npy
│   ├── centroid.npy
│   └── metadata.json
├── sub_02/
│   ├── ...
├── sub_03/
│   └── ...
```

И главное — **каждый `sub_*` будет самостоятельным подслепком**, а верхний `84_v34` останется слепком всего адреса.

Это правильная архитектура для следующего этапа распознавания: сначала определяем **адрес**, затем внутри найденного адреса — **подслепок/сцену**.

Давай сейчас сделаем именно **sweep 0.85–0.95**, без изменения рабочих V33.

---

### 👤 **User** — 2026-08-15 01:18:40

main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,130p' tools/analyze_v34_neighbors.py
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.image import image_files

INPUT = Path("data/input/84")

TOP_K = 5

def normalize_rows(x):
    x = np.asarray(x, dtype=np.float32)

    norms = np.linalg.norm(
        x,
        axis=1,
        keepdims=True,
    )

    norms[norms == 0] = 1.0

    return x / norms

def main():

    paths = image_files(INPUT)

    print(f"Images: {len(paths)}")

    embedder = SceneEmbedder(settings)

    embeddings = embedder.embed_paths(paths)
    embeddings = normalize_rows(embeddings)

    similarity = embeddings @ embeddings.T

    print()
    print("=" * 80)
    print("NEAREST NEIGHBORS")
    print("=" * 80)

    for i in range(len(paths)):

        scores = similarity[i].copy()

        # Не сравниваем изображение с самим собой.
        scores[i] = -1.0

        indices = np.argsort(
            scores
        )[-TOP_K:][::-1]

        print()
        print(
            f"[{i:02d}] "
            f"{Path(paths[i]).name}"
        )

        for rank, j in enumerate(
            indices,
            1,
        ):
            print(
                f"    {rank}. "
                f"{scores[j]:.4f}  "
                f"{Path(paths[j]).name}"
            )

    print()
    print("=" * 80)
    print("SIMILARITY DISTRIBUTION")
    print("=" * 80)

    upper = similarity[
        np.triu_indices(
            len(paths),
            k=1,
        )
    ]

    for threshold in [
        0.95,
        0.93,
        0.91,
        0.89,
        0.87,
        0.85,
        0.83,
        0.80,
    ]:

        count = int(
            np.sum(
                upper >= threshold
            )
        )

        print(
            f">= {threshold:.2f}: "
            f"{count} pairs"
        )

if __name__ == "__main__":
    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 01:18:41

Да, этот файл как раз уже даёт нам нужную статистику. Но он считает **пары**, а нам нужно проверить, как именно фотографии разбиваются на **подслепки**.

Предлагаю не трогать `create_v34_test.py`, а сделать отдельный диагностический скрипт на его основе. Он прогонит несколько порогов и покажет размеры групп.

### 1. Создаём sweep

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > tools/sweep_v34_groups.py <<'PY'
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.image import image_files

INPUT = Path("data/input/84")

THRESHOLDS = [
    0.85,
    0.87,
    0.89,
    0.91,
    0.93,
    0.95,
]

def normalize_rows(x):
    x = np.asarray(x, dtype=np.float32)

    norms = np.linalg.norm(
        x,
        axis=1,
        keepdims=True,
    )

    norms[norms == 0] = 1.0

    return x / norms

def build_groups(embeddings, threshold):
    """
    Агломеративная группировка.
    Та же логика, что в create_v34_test.py,
    но без сохранения результатов.
    """

    embeddings = normalize_rows(embeddings)

    similarity = embeddings @ embeddings.T
    centrality = similarity.mean(axis=1)

    order = np.argsort(-centrality)

    groups = []

    for idx in order:

        best_group = None
        best_score = -1.0

        for gi, group in enumerate(groups):

            centroid = normalize_rows(
                embeddings[group].mean(
                    axis=0,
                    keepdims=True,
                )
            )[0]

            score = float(
                np.dot(
                    embeddings[idx],
                    centroid,
                )
            )

            if score > best_score:
                best_score = score
                best_group = gi

        if (
            best_group is not None
            and best_score >= threshold
        ):
            groups[best_group].append(
                int(idx)
            )
        else:
            groups.append([int(idx)])

    return groups

def main():

    paths = image_files(INPUT)

    if not paths:
        raise RuntimeError(
            f"No images found: {INPUT}"
        )

    print("=" * 80)
    print("V34 GROUPING SWEEP")
    print("=" * 80)
    print(f"Input: {INPUT}")
    print(f"Images: {len(paths)}")
    print()

    embedder = SceneEmbedder(settings)

    print("[SWEEP] Creating embeddings...")

    embeddings = embedder.embed_paths(paths)
    embeddings = normalize_rows(embeddings)

    print(
        f"[SWEEP] Embeddings: "
        f"{embeddings.shape}"
    )

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)

    for threshold in THRESHOLDS:

        groups = build_groups(
            embeddings,
            threshold,
        )

        groups.sort(
            key=len,
            reverse=True,
        )

        sizes = [
            len(group)
            for group in groups
        ]

        print()
        print(
            f"THRESHOLD {threshold:.2f}"
        )
        print(
            f"GROUPS    {len(groups)}"
        )
        print(
            f"SIZES     {sizes}"
        )

        for i, group in enumerate(
            groups,
            1,
        ):
            names = [
                Path(paths[idx]).name
                for idx in group
            ]

            print(
                f"  sub_{i:02d} "
                f"({len(group)}): "
                f"{', '.join(names)}"
            )

if __name__ == "__main__":
    main()
PY
```

### 2. Запускаем

```bash
uv run python tools/sweep_v34_groups.py
```

Это займёт примерно столько же, сколько обычный расчёт embeddings, потому что DINO будет загружен **один раз**.

Получим что-то вроде:

```text
THRESHOLD 0.85
GROUPS    3
SIZES     [24, 18, 12]

THRESHOLD 0.87
GROUPS    4
SIZES     [21, 16, 10, 7]

THRESHOLD 0.89
GROUPS    6
SIZES     [18, 12, 9, 7, 5, 3]

...
```

Но важнее не сами цифры, а **состав групп**.

Особенно посмотрим на:

- `0.87`
- `0.89`
- `0.91`
- `0.93`

Я ожидаю, что где-то в этом диапазоне появится разумное разделение фотографий на реальные ракурсы/сцены.

**Пока V34 ничего не создаём и существующие слепки не трогаем.**

Пришли вывод `uv run python tools/sweep_v34_groups.py` целиком — по нему выберем порог и сделаем уже нормальный `V34`.

---

