### 🧠 **Анализ и решение**

Ваша задача — **интегрировать существующий пайплайн обработки изображений** (v33 → определение адреса → сортировка → Qwen3-VL 4B) с **JobQueue** и **FingerprintWorker**, чтобы создать полноценный рабочий процесс.

---

## 🔍 **Шаг 1: Найдите существующий пайплайн**

Вы уже нашли кандидатов на обработку изображений:

- `scripts/sort_test_and_report_v2.py`
- `scripts/sort_test_and_report.py`

Используйте следующие команды, чтобы проверить их содержимое:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "=== sort_test_and_report_v2.py ===" && \
cat -n scripts/sort_test_and_report_v2.py && \
echo "=== sort_test_and_report.py ===" && \
cat -n scripts/sort_test_and_report.py
```

---

## 🔍 **Шаг 2: Найдите ссылки на пайплайн**

Используйте следующую команду, чтобы найти все упоминания ключевых слов в проекте:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "=== pipeline / sorting references ===" && \
grep -R -n -E \
"sort_test|test_sorted|report.json|report.csv|v33|first candidate|candidate" \
app scripts \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -250
```

---

## 🧩 **Шаг 3: Интеграция с JobQueue**

После анализа файлов, найдите:

1. **Функцию обработки изображений** (v33 → определение адреса → сортировка → Qwen3-VL 4B)
2. **Функцию генерации отчета** (report.json / report.csv)

Интегрируйте их в `JobQueue` как **новые задачи**:

```python
# app/pipeline/queue.py
def add_image_processing_job(
    source_folder: str,
    fingerprint_id: str,
    priority: int = 0
):
    return self.add(
        source_folder,
        fingerprint_id,
        priority
    )
```

---

## 🧩 **Шаг 4: Интеграция с FingerprintWorker**

Используйте `FingerprintWorker` для запуска обработки изображений:

```python
# app/pipeline/worker.py
def run_once(self):
    job = self.queue.claim()

    if job is None:
        return False

    job_id = job["id"]
    fingerprint_id = job["fingerprint_id"]
    source_folder = Path(job["source_folder"])

    print(f"[Worker] Processing job {job_id}")

    try:
        self.manager.process_image(
            fingerprint_id,
            source_folder,
            self.embedder
        )

        self.queue.complete(job_id)

        print(f"[Worker] DONE: {fingerprint_id}")
        return True

    except Exception as exc:
        self.queue.fail(job_id, repr(exc))
        print(f"[Worker] FAILED: {fingerprint_id}: {exc}")
        return True
```

---

## 📄 **Шаг 5: Обновите документацию**

Добавьте в `README.md` или `docs/` описание нового пайплайна:

```markdown
## 🚀 Пайплайн обработки изображений

1. **Загрузка изображений** (v33)
2. **Определение адреса**
3. **Сортировка**
4. **Обработка с Qwen3-VL 4B**
5. **Генерация отчета** (report.json / report.csv)
```

---

## 📌 **Итог**

Теперь у вас есть:

- **JobQueue** для управления задачами
- **FingerprintWorker** для обработки изображений
- **Существующий пайплайн** для обработки и генерации отчетов

Вы можете добавить интерфейс для запуска пайплайна, но **не нужно связывать его с `FingerprintWorker`** — это будет отдельная задача.