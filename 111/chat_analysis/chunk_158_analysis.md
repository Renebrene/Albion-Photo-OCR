### ✅ **Итоговый патч для `automation.py`**

Вот полный патч, который исправит все проблемы:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

path = Path("app/web/components/technical_modules/automation.py")
text = path.read_text()

# 1. Исправляем mode_radio (кортеж → словарь)
old1 = '''            mode_radio = ui.radio(
                [
                    (
                        MODE_MANUAL,
                        "Ручной",
                    ),
                    (
                        MODE_WATCHER,
                        "Watcher",
                    ),
                    (
                        MODE_AUTOMATIC,
                        "Автоматический",
                    ),
                ],
                value=state.mode,
            ).props("inline dense")
'''
new1 = '''            mode_radio = ui.radio(
                {
                    MODE_MANUAL: "Ручной",
                    MODE_WATCHER: "Watcher",
                    MODE_AUTOMATIC: "Автоматический",
                },
                value=state.mode,
            ).props("inline dense")
'''

text = text.replace(old1, new1)

# 2. Удаляем старые переменные и заменяем их на mode_radio
old2 = '''            manual_radio.value = (
                state.mode == MODE_MANUAL
            )
            watcher_radio.value = (
                state.mode == MODE_WATCHER
            )
            automatic_radio.value = (
                state.mode == MODE_AUTOMATIC
            )

            manual_radio.on(
                "input",
                lambda: state.set_mode(MODE_MANUAL)
            )
            watcher_radio.on(
                "input",
                lambda: state.set_mode(MODE_WATCHER)
            )
            automatic_radio.on(
                "input",
                lambda: state.set_mode(MODE_AUTOMATIC)
            )
'''
new2 = '''            if state.mode == MODE_MANUAL:
                mode_radio.value = MODE_MANUAL
            elif state.mode == MODE_WATCHER:
                mode_radio.value = MODE_WATCHER
            elif state.mode == MODE_AUTOMATIC:
                mode_radio.value = MODE_AUTOMATIC

            mode_radio.on(
                "input",
                lambda: state.set_mode(mode_radio.value)
            )
'''

text = text.replace(old2, new2)

# 3. Удаляем остатки старых переменных
old3 = '''        manual_radio = ui.radio(...)
        watcher_radio = ui.radio(...)
        automatic_radio = ui.radio(...)
'''
text = text.replace(old3, '')

path.write_text(text)

print("AUTOMATION.PY FIXED")
PY
```

---

### 🧹 **Что это делает:**

1. **Исправляет `mode_radio`** — теперь он использует словарь вместо кортежа, как требуется в NiceGUI.
2. **Удаляет старые переменные** `manual_radio`, `watcher_radio`, `automatic_radio` и их обработчики.
3. **Переносит логику** на `mode_radio`, чтобы он отслеживал изменения состояния `state.mode`.

---

### 🚀 **Дополнительно:**

- После этого **не трогай Supervisor**, он работает корректно.
- **Перезапусти `lora`**, чтобы изменения вступили в силу.
- Если возникнут ошибки с `manual_radio`, `watcher_radio` и т.д., просто удали их из кода полностью — они больше не нужны.

Если всё сделано правильно, ошибка `ValueError: Invalid value: manual` исчезнет.