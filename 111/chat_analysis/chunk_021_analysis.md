### ✅ **Реализация `queue-batch-add`**

Добавим команду `queue-batch-add`, которая:

1. Принимает диапазон ID (например, `83–95`)
2. Проверяет наличие каталогов `data/input/83`, `data/input/84`, ..., `data/input/95`
3. Пропускает каталоги, где уже есть `fingerprint_id`
4. Добавляет в очередь только те, где нет слепка
5. Показывает статистику

---

### 📜 **Создаем `queue-batch-add`**

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/pipeline/queue-batch-add.py <<'PY'
from __future__ import annotations

from pathlib import Path

from app.pipeline.queue import JobQueue
from app.core.config import settings

def add_batch_to_queue(start_id: int, end_id: int):
    queue = JobQueue(
        settings.data_dir / "jobs.db"
    )

    added = 0
    skipped = 0
    missing = 0

    for job_id in range(start_id, end_id + 1):
        source_folder = Path(settings.data_dir) / "input" / f"{job_id}"

        if not source_folder.exists():
            missing += 1
            print(f"[Queue] Missing: {job_id}")
            continue

        fingerprint_id = f"{job_id}_batch_add"
        existing = Path(settings.data_dir) / "fingerprints" / f"{fingerprint_id}"

        if existing.exists():
            skipped += 1
            print(f"[Queue] Skipped: {fingerprint_id} (already exists)")
            continue

        try:
            queue.add(
                fingerprint_id,
                str(source_folder)
            )
            added += 1
            print(f"[Queue] Added: {fingerprint_id}")
        except Exception as exc:
            print(f"[Queue] Failed to add {fingerprint_id}: {exc}")

    print()
    print("=" * 60)
    print(f"[Queue] Summary:")
    print(f"  Added: {added}")
    print(f"  Skipped: {skipped}")
    print(f"  Missing: {missing}")
    print("=" * 60)

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python queue-batch-add.py <start_id> <end_id>")
        sys.exit(1)

    try:
        start_id = int(sys.argv[1])
        end_id = int(sys.argv[2])
    except ValueError:
        print("Error: IDs must be integers")
        sys.exit(1)

    add_batch_to_queue(start_id, end_id)
PY
```

---

### 🧪 **Тестирование `queue-batch-add`**

Запускаем:

```bash
uv run python app/pipeline/queue-batch-add.py 83 95
```

Ожидаем вывод вроде:

```text
[Queue] Added: 83_batch_add
[Queue] Added: 84_batch_add
[Queue] Skipped: 85_batch_add (already exists)
[Queue] Added: 86_batch_add
...
[Queue] Summary:
  Added: 10
  Skipped: 3
  Missing: 0
```

---

### 📌 **Итог**

Теперь у нас:

- **Массовое добавление задач в очередь**
- **Проверка наличия слепка**
- **Избежание дублирования**
- **Статистика по добавленным/пропущенным/отсутствующим каталогам**

Это позволяет:

- Добавлять сотни каталогов за один запуск
- Автоматизировать обработку
- Следить за состоянием очереди
- Избежать ошибок из-за дублирования

---

### 🚀 **Далее**

Теперь можно:

1. Добавить в очередь 100+ каталогов за один запуск
2. Запустить batch-worker, который обработает их последовательно
3. Проверить производительность
4. Оценить, стоит ли распараллеливать

Если всё устраивает — можно перейти к **production-режиму** с очередью и batch-worker'ом.