### ✅ **Добавляем ручной запуск Qwen в интерфейс**

Вот как мы модифицируем `qwen.py` и добавим кнопку **▶ ЗАПУСТИТЬ QWEN**:

---

### 🔧 **Шаг 1: Добавляем кнопку в интерфейс**

В `build_qwen()` добавим новую кнопку рядом с "↻ Обновить":

```python
        with ui.row().classes("gap-2"):
            ui.button(
                "▶ ЗАПУСТИТЬ QWEN",
                on_click=lambda: run_qwen_manual(),
            ).props("unelevated")
            ui.button(
                "↻ Обновить",
                on_click=lambda: refresh(),
            ).props("unelevated")
```

---

### 🧠 **Шаг 2: Реализуем логику `run_qwen_manual()`**

Добавим функцию `run_qwen_manual()` в `qwen.py`:

```python
def run_qwen_manual():
    try:
        # 1. Находим последний Hybrid
        hybrid_dir = sorted(
            [p for p in Path("data/output/daily").iterdir() if p.is_dir()],
            key=lambda x: x.name,
            reverse=True
        )[0]

        # 2. Проверяем, есть ли summary.json в Hybrid
        hybrid_summary = hybrid_dir / "summary.json"
        if not hybrid_summary.exists():
            ui.notify("Ошибка: Нет summary.json в Hybrid", type="error")
            return

        # 3. Запускаем Qwen вручную
        result = process_qwen(hybrid_summary)

        # 4. Сохраняем результат в data/metadata/qwen4b
        qwen_output_dir = Path("data/metadata/qwen4b") / hybrid_dir.name
        qwen_output_dir.mkdir(parents=True, exist_ok=True)

        # 5. Сохраняем результат в JSON
        (qwen_output_dir / "result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False)
        )

        ui.notify("✅ Запуск Qwen завершён", type="success")

    except Exception as exc:
        ui.notify(f"❌ Ошибка: {str(exc)}", type="error")
```

---

### 🧩 **Шаг 3: Добавляем `process_qwen()`**

Добавим вспомогательную функцию `process_qwen()`:

```python
def process_qwen(hybrid_summary):
    try:
        data = json.loads(hybrid_summary.read_text(encoding="utf-8"))

        if not isinstance(data, dict):
            raise ValueError("Неверный формат summary.json")

        results = data.get("results", [])

        if not isinstance(results, list):
            raise ValueError("Неверный формат results")

        total = len(results)
        ok = sum(
            1
            for row in results
            if isinstance(row, dict)
            and row.get("status") == "ok"
        )
        errors = sum(
            1
            for row in results
            if isinstance(row, dict)
            and row.get("status") == "error"
        )

        times = []
        confidences = []
        addresses = set()

        for row in results:
            if not isinstance(row, dict):
                continue

            value = row.get("time_sec")
            if value is not None:
                try:
                    times.append(float(value))
                except (TypeError, ValueError):
                    pass

            value = row.get("confidence")
            if value not in (None, ""):
                try:
                    confidences.append(float(value))
                except (TypeError, ValueError):
                    pass

            address = row.get("address")
            if address:
                addresses.add(address)

        return {
            "state": "ГОТОВ",
            "processed": total,
            "ok": ok,
            "skipped": total - ok - errors,
            "errors": errors,
            "addresses": len(addresses),
            "avg_time": (
                sum(times) / len(times)
                if times
                else 0
            ),
            "avg_confidence": (
                sum(confidences) / len(confidences)
                if confidences
                else 0
            ),
            "model": "Qwen3-VL 4B",
            "run": hybrid_summary.parent.name,
            "summary": str(hybrid_summary),
        }

    except Exception as exc:
        return {
            "state": "ОШИБКА ФОРМАТА",
            "processed": 0,
            "ok": 0,
            "skipped": 0,
            "errors": 0,
            "addresses": 0,
            "avg_time": 0.0,
            "avg_confidence": 0.0,
            "model": "Qwen3-VL 4B",
            "run": "—",
            "summary": "—",
            "error": str(exc),
        }
```

---

### 🔄 **Шаг 4: Обновляем `refresh()`**

Добавим в `refresh()` обработку ручного запуска:

```python
def refresh():
    data = _load_qwen_status()

    state_label.text = data["state"]

    run_label.text = (
        data["run"]
        if data.get("run")
        else "—"
    )

    model_label.text = data["model"]

    processed_label.text = str(
        data["processed"]
    )

    ok_label.text = str(
        data["ok"]
    )

    skipped_label.text = str(
        data["skipped"]
    )

    errors_label.text = str(
        data["errors"]
    )

    addresses_label.text = str(
        data["addresses"]
    )

    avg_time_label.text = (
        f'{data["avg_time"]:.2f} сек'
    )

    avg_confidence_label.text = (
        f'{data["avg_confidence"]:.1f}%'
    )

    if data["state"] == "ГОТОВ":
        status_label.text = "● ГОТОВ"
    elif data["state"] == "НЕТ ДАННЫХ":
        status_label.text = "● НЕТ ДАННЫХ"
    else:
        status_label.text = "● ОШИБКА"

    if data.get("summary"):
        source_label.text = (
            f'Источник: {data["summary"]}'
        )

    if data.get("error"):
        source_label.text = (
            f'Ошибка: {data["error"]}'
        )
```

---

### 📁 **Шаг 5: Создаём директорию для ручных запусков**

Убедитесь, что существует:

```bash
mkdir -p data/metadata/qwen4b
```

---

### ✅ **Итог**

Теперь:

1. **Автоматический запуск Qwen после Hybrid** работает как раньше.
2. **Ручной запуск Qwen** доступен через кнопку **▶ ЗАПУСТИТЬ QWEN**.
3. Результат сохраняется в `data/metadata/qwen4b/`.

Если нужно, могу добавить отображение результата в интерфейс или логику отслеживания прогресса.