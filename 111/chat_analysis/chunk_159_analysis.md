### 🛠️ **Решение: Восстановление `automation.py` без ошибок**

Поскольку в предыдущем патче произошла ошибка `substring not found`, это означает, что строка `def mode_changed(event):` не найдена в файле. Возможно, она была удалена или изменена в процессе. Нам нужно **восстановить исходную структуру** файла, чтобы избежать синтаксических ошибок.

---

### ✅ **Шаг 1: Восстановление исходного кода `automation.py`**

Выполни этот патч, чтобы **восстановить исходную структуру файла** без изменений:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/automation.py")
s = p.read_text()

# Найдём точку вставки
start = s.find("        mode_radio = ui.radio(")
end = s.find("        # ----------------------------------------------------\n        # TOOLTIPS", start)

# Восстанавливаем исходный код
new_code = '''        mode_radio = ui.radio(
            {
                MODE_MANUAL: "Ручной",
                MODE_WATCHER: "Watcher",
                MODE_AUTOMATIC: "Автоматический",
            },
            value=state.mode,
        ).props("inline dense")

'''

s = s[:start] + new_code + s[end:]

p.write_text(s)
print("RESTORE OK")
PY
```

---

### ✅ **Шаг 2: Проверка синтаксиса**

После восстановления проверим, нет ли ошибок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/automation.py
```

Если всё ок, будет просто возврат в prompt.

---

### ✅ **Шаг 3: Проверка импорта**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import app.web.components.technical_modules.automation
print("AUTOMATION IMPORT: OK")
PY
```

Если всё работает, выведет `AUTOMATION IMPORT: OK`.

---

### ✅ **Шаг 4: Перезапуск сервиса**

Теперь можно безопасно перезапустить сервис:

```bash
sudo systemctl restart lora
```

Проверим статус:

```bash
sudo systemctl status lora --no-pager -l
```

Если всё ок, веб-интерфейс должен снова подняться.

---

### ✅ **Шаг 5: Проверка веб-интерфейса**

Открой в браузере:  
`http://<IP>:8081` (или `http://localhost:8081`)

Если веб-интерфейс работает, можно **продолжить с исправлением логики переключения режимов**.

---

### 🚨 **Важно:**

Если веб-интерфейс всё ещё не работает, проверь:

1. **Состояние сервиса**:
   ```bash
   sudo systemctl status lora --no-pager -l
   ```

2. **Последние логи**:
   ```bash
   sudo journalctl -u lora -n 100 --no-pager
   ```

3. **Содержимое файла `automation.py`**:
   ```bash
   cat app/web/components/technical_modules/automation.py
   ```

---

### 🧠 **Примечание:**

Если веб-интерфейс всё же не работает, возможно, есть другие ошибки в коде. В таком случае, **предоставь полный код файла `automation.py`**, чтобы я мог точно определить проблему.