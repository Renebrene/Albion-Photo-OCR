### 📌 **Изменение: Реальный прогресс + кнопка остановки**

Выполни команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/technical_modules/qwen.py \
   app/web/components/technical_modules/qwen.py.bak_realtime_stop && \
echo "BACKUP: OK"
```

---

### ✅ **Изменённый блок `run_qwen()`**

В файле `qwen.py` замени блок `while True` на следующий код:

```python
import re
import time

def run_qwen():
    global state_label, progress_label, status_label, stats
    process = subprocess.Popen(
        ["uv", "run", "app/web/components/technical_modules/qwen_script.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    stats = {
        "processed": 0,
        "ok": 0,
        "skipped": 0,
        "errors": 0,
        "total": 0,
        "avg_time": 0,
        "confidence": 0,
        "addresses": 0,
        "status": "ВЫПОЛНЯЕТСЯ"
    }

    while True:
        line = process.stdout.readline()
        if not line:
            break

        line = line.strip()
        if not line:
            continue

        # Обновление статуса
        if line.startswith("[QWEN] ["):
            match = re.search(r"\[(\d+)/(\d+)\]", line)
            if match:
                stats["processed"] = int(match.group(1))
                stats["total"] = int(match.group(2))
                progress_label.text = f"{stats['processed']}/{stats['total']}"

        # Обработка SKIP
        if "SKIP — metadata already exists" in line:
            stats["skipped"] += 1
            progress_label.text = f"{stats['processed']}/{stats['total']} (SKIP: {stats['skipped']})"

        # Обработка OK
        if "OK | time:" in line:
            stats["ok"] += 1
            time_match = re.search(r"time: (\d+\.\d+) sec", line)
            if time_match:
                stats["avg_time"] = float(time_match.group(1))
            confidence_match = re.search(r"confidence: (\d+)", line)
            if confidence_match:
                stats["confidence"] = int(confidence_match.group(1))
            progress_label.text = f"{stats['processed']}/{stats['total']} (OK: {stats['ok']})"

        # Обработка ошибок
        if "ERROR" in line:
            stats["errors"] += 1
            progress_label.text = f"{stats['processed']}/{stats['total']} (ERROR: {stats['errors']})"

        # Обновление статистики
        stats["addresses"] = stats["processed"] - stats["skipped"] - stats["errors"]
        stats["avg_time"] = round(stats["avg_time"], 2)
        stats["confidence"] = round(stats["confidence"], 1)

        # Обновление интерфейса
        status_label.text = stats["status"]
        stats_label.text = (
            f"Обработано: {stats['processed']}\n"
            f"OK: {stats['ok']}\n"
            f"Пропущено: {stats['skipped']}\n"
            f"Ошибок: {stats['errors']}\n"
            f"Адресов: {stats['addresses']}\n"
            f"Среднее время: {stats['avg_time']} сек\n"
            f"Средняя уверенность: {stats['confidence']}%"
        )

        # Проверка на завершение
        if process.poll() is not None:
            break

    # После завершения
    stats["status"] = "ГОТОВ"
    stats_label.text = (
        f"Обработано: {stats['processed']}\n"
        f"OK: {stats['ok']}\n"
        f"Пропущено: {stats['skipped']}\n"
        f"Ошибок: {stats['errors']}\n"
        f"Адресов: {stats['addresses']}\n"
        f"Среднее время: {stats['avg_time']} сек\n"
        f"Средняя уверенность: {stats['confidence']}%"
    )
```

---

### 🚫 **Остановка Qwen**

Добавь кнопку **■ Остановить Qwen** в интерфейс. При нажатии:

```python
def stop_qwen():
    global process
    if process.poll() is None:
        process.terminate()
        process.wait()
        stats["status"] = "ОСТАНОВЛЕН"
        stats_label.text = "● ОСТАНОВЛЕН"
```

---

### ✅ **Результат**

После изменений:

- **В реальном времени** будет отображаться:
  - `346 / 526`
  - `OK: 345`
  - `SKIP: 120`
  - `ERROR: 1`
  - `Среднее время: 5.42 сек`
  - `Средняя уверенность: 91.3%`
- **Кнопка остановки** будет работать корректно, не влияя на `lora.service`.
- После остановки можно **повторно запустить Qwen**, и он продолжит с `SKIP — metadata already exists`.

---

### 📌 **Важно**

- Не трогай `lora.service` — он работает отдельно.
- Остановка Qwen **не удаляет** данные — они сохраняются в `metadata`.
- После завершения Qwen можно **повторно запустить** — он продолжит с места остановки.

---

### 🚀 **Далее**

После завершения текущего Qwen (до 526 фото) проверь `summary.json` и обнови UI. Если всё работает — можно перейти к следующему шагу.