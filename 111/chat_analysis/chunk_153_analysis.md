### 🛠️ **Шаг 1: Убираем Qwen из технического окна**

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'build_qwen|technical_modules\.qwen|qwen\.build|QWEN' \
app/web \
--include="*.py" | head -200
```

После этого пришли вывод. Нужно найти, где подключается `qwen.py` в интерфейсе, чтобы убрать только его UI.

---

### 🚀 **Шаг 2: Автоматизация с тремя типами запуска**

После убирания Qwen из UI, займёмся автоматизацией. В `controller.py` добавим три режима запуска:

```python
# app/web/controller.py

class AutomationController:
    def __init__(self):
        self.mode = "manual"  # "manual", "auto", "batch"
        self.batch_schedule = []

    def set_mode(self, mode):
        self.mode = mode

    def schedule_batch(self, schedule):
        self.batch_schedule = schedule

    def run_batch(self):
        for task in self.batch_schedule:
            task()
```

В интерфейсе добавим три кнопки: **Ручной**, **Автоматический**, **Пакетный**. При выборе режима обновляем `self.mode` и настраиваем `self.batch_schedule`.

---

### 📌 **Важно:**
- Не трогаем `qwen.py` и `qwen_worker.py` в backend.
- Убираем только UI-блок Qwen из технического окна.
- Автоматизация добавляется в `controller.py` без изменения существующего кода.

Если хочешь, я могу помочь с конкретной командой для удаления Qwen из UI.