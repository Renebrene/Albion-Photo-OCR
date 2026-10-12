```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile app/web/components/clients.py && \
uv run python -m py_compile app/web/components/addresses.py && \
uv run python -m py_compile app/web/components/photos.py && \
echo "CLIENTS/ADDRESSES/PHOTOS PYTHON OK"
```

Если получим `CLIENTS/ADDRESSES/PHOTOS PYTHON OK`, следующим шагом дам **точечный патч через `uv`**, который изменит только контейнер карточки и контейнер списка клиентов.

---

### ✅ Патч для `clients.py`

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import os
from nicegui import ui

def patch_clients():
    file_path = "app/web/components/clients.py"
    with open(file_path, "r") as f:
        lines = f.readlines()
    
    # Найдём контейнер карточки и список
    card_start = None
    list_start = None
    for i, line in enumerate(lines):
        if "ui.card()" in line:
            card_start = i
        if "ui.list()" in line:
            list_start = i
    
    if card_start is not None and list_start is not None:
        # Добавим h-full min-h-0 к карточке
        lines[card_start] = lines[card_start].replace("ui.card()", "ui.card().classes('h-full min-h-0')\n")
        
        # Добавим flex-1 min-h-0 к списку
        lines[list_start] = lines[list_start].replace("ui.list()", "ui.list().classes('flex-1 min-h-0 overflow-y-auto')\n")
    
    with open(file_path, "w") as f:
        f.writelines(lines)

patch_clients()
PY
```

---

### ✅ Патч для `addresses.py`

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import os
from nicegui import ui

def patch_addresses():
    file_path = "app/web/components/addresses.py"
    with open(file_path, "r") as f:
        lines = f.readlines()
    
    # Найдём контейнер карточки и список
    card_start = None
    list_start = None
    for i, line in enumerate(lines):
        if "ui.card()" in line:
            card_start = i
        if "ui.list()" in line:
            list_start = i
    
    if card_start is not None and list
```