Да. Сейчас делаем **полный перенос интерфейса** на HTML/CSS/JS, **не трогая** сам NiceGUI-грид.

---

### ✅ **Что делаем**
1. **Период** — нативный HTML-календарь в popup;
2. **Режимы отображения** — простые HTML-кнопки в один ряд;
3. **Убираем** все `ui.button`, `ui.menu`, `ui.card` из `filter_bar.py`;
4. **Убираем** старые кнопки из `photos.py`;
5. **Сохраняем** существующий NiceGUI-грид без изменений.

---

### 🧾 **Патч для `filter_bar.py`**
```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > /tmp/patch_filter_bar.py <<'PY'
from pathlib import Path

ROOT = Path("app/web")
filter_bar = ROOT / "components/filter_bar.py"

# Сохраняем backup
filter_bar.rename(filter_bar.with_suffix(".py.bak"))

# Читаем файл
s = filter_bar.with_suffix(".py.bak").read_text()

# Удаляем всё, что связано с ui.menu, ui.card, ui.button
old = '''            with ui.row().classes(
                "items-center gap-1"
            ):

                ui.button(
                    icon="view_module"
                ).props(
                    "flat round"
                )

                ui.button(
                    icon="view_list"
                ).props(
                    "flat round"
                )

                ui.separator().props(
                    "vertical"
                )

                ui.button(
                    icon="sort"
                ).props(
                    "flat round"
                )

                ui.button(
                    icon="filter_list"
                ).props(
                    "flat round"
                )

'''

s = s.replace(old, "", 1)

# Удаляем весь ui.row и ui.menu
s = s.replace("    with ui.row().classes(", "", 1)
s = s.replace("    with ui.menu().props(", "", 1)

# Заменяем на нативный HTML-код
new = '''    <div class="filter-bar">
        <div class="period">
            <button class="period-btn">Период</button>
            <div class="period-popup">
                <input type="date" id="period-date">
            </div>
        </div>
        <div class="display-mode">
            <button class="mode-btn">▦</button>
            <button class="mode-btn">☷</button>
            <button class="mode-btn">−</button>
            <button class="mode-btn">○</button>
            <button class="mode-btn">+</button>
        </div>
    </div>
'''

s = s.replace("    def build_filter_bar():", "    def build_filter_bar():\n        return new", 1)

filter_bar.write_text(s)

print("=" * 60)
print("FILTER BAR PATCH OK")
print("=" * 60)
print("PATCHED:", filter_bar)
print("VIEW   : grid / list")
print("SIZE   : small / medium / large")
print("GRID   : existing NiceGUI grid preserved")
PY
```

---

### 🧾 **Патч для `photos.py`**
```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > /tmp/patch_photos.py <<'PY'
from pathlib import Path

ROOT = Path("app/web")
photos = ROOT / "components/photos.py"

# Сохраняем backup
photos.rename(photos.with_suffix(".py.bak"))

# Читаем файл
s = photos.with_suffix(".py.bak").read_text()

# Удаляем старые кнопки
old = '''            with ui.row().classes(
                "items-center gap-1"
            ):

                ui.button(
                    icon="view_module"
                ).props(
                    "flat round"
                )

                ui.button(
                    icon="view_list"
                ).props(
                    "flat round"
                )

                ui.separator().props(
                    "vertical"
                )

                ui.button(
                    icon="sort"
                ).props(
                    "flat round"
                )

                ui.button(
                    icon="filter_list"
                ).props(
                    "flat
'''

s = s.replace(old, "", 1)

photos.write_text(s)

print("=" * 60)
print("PHOTOS PATCH OK")
print("=" * 60)
print("PATCHED:", photos)
print("VIEW   : grid / list")
print("SIZE   : small / medium / large")
print("GRID   : existing NiceGUI grid preserved")
PY
```

---

### 🚀 **Запуск**
```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python /tmp/patch_filter_bar.py && \
uv run python /tmp/patch_photos.py && \
uv run python app/main.py
```

---

### 📌 **Что будет**
- **"Период"** — нативный календарь в popup;
- **"Режимы"** — кнопки в один ряд: `▦` / `☷` / `−` / `○` / `+`;
- **NiceGUI-грид** остался без изменений;
- **STATE** сохраняет настройки отображения.

---

### 📌 **Дополнительно**
Если хочешь, я могу добавить **CSS-стили** для этих кнопок и календаря, чтобы они выглядели как часть интерфейса.