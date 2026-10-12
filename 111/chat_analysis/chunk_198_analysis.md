```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/main.py app/web/main.py.bak_before_filter_bar_$(date +%Y%m%d_%H%M%S) && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/main.py")
s = p.read_text()

# Удаляем старый блок периода (включая все содержимое)
start_marker = "        # ====================================================\n        # ACTION BAR\n"
end_marker = "        # ====================================================\n        # CLIENTS + PHOTOS + ADDRESSES"

start = s.find(start_marker)
end = s.find(end_marker, start)

if start != -1 and end != -1:
    s = s[:start] + s[end:]

# Заменяем импорт
s = s.replace(
    "from app.web.components.filters import build_filters\n",
    "from app.web.components.filter_bar import build_filter_bar\n"
)

# Вставляем новый компонент в место старой панели
new_block = '''        # ====================================================
        # FILTER BAR
        #
        # Собственная HTML/CSS/JS панель.
        # Календарь открывается только после нажатия «Период».
        # ====================================================

        build_filter_bar()

'''

s = s.replace(
    "        # ====================================================\n        # ACTION BAR\n",
    "        # ====================================================\n        # FILTER BAR\n\n" + new_block
)

p.write_text(s)

print("PATCH OK")
print("MAIN:", p)
PY
```

После этого создайте файл `app/web/components/filter_bar.py` с содержимым:

```python
from pathlib import Path
from nicegui import ui

def build_filter_bar():
    with ui.row().classes("w-full h-full items-center gap-4 px-3"):
        # Календарь (HTML/CSS/JS)
        ui.html('''
            <div id="filter-bar" class="flex items-center gap-4">
                <button id="period-btn" class="bg-blue-500 text-white px-4 py-2 rounded">
                    Период
                </button>
                <div id="calendar" class="hidden">
                    <input type="date" id="date-filter" class="bg-white text-black">
                </div>
                <button id="address-btn" class="bg-green-500 text-white px-4 py-2 rounded">
                    Адрес
                </button>
                <button id="client-btn" class="bg-purple-500 text-white px-4 py-2 rounded">
                    Клиент
                </button>
                <button id="collection-btn" class="bg-yellow-500 text-white px-4 py-2 rounded">
                    Подборка
                </button>
            </div>
        ''')

        # Обработчики событий
        ui.script('''
            document.getElementById('period-btn').addEventListener('click', () => {
                document.getElementById('calendar').classList.toggle('hidden');
            });

            document.getElementById('date-filter').addEventListener('change', () => {
                const date = document.getElementById('date-filter').value;
                if (date) {
                    // Отправляем дату на сервер
                    fetch('/filter', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ date: date })
                    });
                }
            });
        ''')
```

Теперь запустите приложение и проверьте, что календарь открывается только после нажатия на кнопку "Период", а остальные фильтры работают как отдельные кнопки.