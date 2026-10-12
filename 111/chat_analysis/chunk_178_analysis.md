### 🛠️ **Решение: Восстановление и исправление `clients.py`**

#### 1. **Восстановление файла `clients.py`**
Проверим, что файл `clients.py` полностью восстановлен из бэкапа и синтаксически корректен:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 -m py_compile app/web/components/clients.py && \
echo "CLIENTS FILE OK"
```

Если `py_compile` не выдаёт ошибок, файл готов к работе.

---

### 2. **Проверка конкретных строк (108–210)**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba app/web/components/clients.py | sed -n '108,210p'
```

Ожидаемый вывод (без ошибок отступов):

```text
  108	refresh_photos()
  109	
  110	    # --------------------------------------------------------
  111	    # PANEL
  112	    # --------------------------------------------------------
  113	
  114	    with ui.card().classes(
  115	        "w-full"
  116	    ):
  117	
  118	    ui.label(
  119	        "Клиенты"
  120	    ).classes(
  121	        "text-lg font-bold"
  122	    )
  123	
  124	    ui.separator()
  125	
  126	    # ----------------------------------------------------
  127	    # CONTROLS
  128	    # ----------------------------------------------------
  129	
  130	    with ui.row().classes(
  131	        "w-full items-center justify-between "
  132	        "px-1 py-1 gap-1"
  133	    ):
  134	
  135	    ui.label(
  136	        "Выбор клиентов"
  137	    ).classes(
  138	        "text-sm font-medium"
  139	    )
  140	
  141	    with ui.row().classes(
  142	        "items-center gap-1"
  143	    ):
  144	
  145	    ui.button(
  146	        "Все",
  147	        icon="done_all",
  148	        on_click=select_all_clients,
  149	    ).props(
  150	        "flat dense"
  151	    )
  152	
  153	    ui.button(
  154	        "Снять",
  155	        icon="remove_done",
  156	        on_click=clear_clients,
  157	    ).props(
  158	        "flat dense"
  159	    )
  160	
  161	    ui.separator()
  162	
  163	    # ----------------------------------------------------
  164	    # CLIENT LIST
  165	    # ----------------------------------------------------
  166	
  167	    for name, address_count in clients:
  168	
  169	    with ui.row().classes(
  170	        "w-full items-center gap-1 px-1 py-1"
  171	    ):
  172	
  173	    checkbox = ui.checkbox(
  174	        value=(
  175	            STATE.selected_clients is None
  176	            or name in STATE.selected_clients
  177	        ),
  178	        on_change=lambda e, n=name:
  179	            select_client(e, n),
  180	    ).props(
  181	        "dense"
  182	    )
  183	
  184	    client_checkboxes[name] = checkbox
  185	
  186	    ui.label(
  187	        name
  188	    ).classes(
  189	        "cursor-pointer flex-grow"
  190	    ).on(
  191	        "click",
  192	        lambda e, cb=checkbox:
  193	            setattr(cb, "value", not cb.value),
  194	    )
  195	
  196	    ui.label(
  197	        f"({address_count})"
  198	    ).classes(
  199	        "text-xs text-grey-6"
  200	    )
  201	
  202	    build_collections()
```

---

### 3. **Исправление: Добавление `build_collections("clients")`**

Теперь безопасно внесём изменения в `clients.py`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 <<'PY'
from pathlib import Path

p = Path("app/web/components/clients.py")
s = p.read_text()

# 1. Замена build_collections() на build_collections("clients")
s = s.replace(
    '        build_collections()\n',
    '        build_collections("clients")\n',
    1,
)

p.write_text(s)

print("CLIENTS BUILD_SCOPE FIXED")
PY

python3 -m py_compile app/web/components/clients.py && \
echo "CLIENTS PYTHON OK"
```

---

### 4. **Проверка и завершение**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba app/web/components/clients.py | sed -n '108,210p'
```

Если всё ок, **не трогаем `clients.py`**. Теперь можно безопасно работать с `main.py` и адресами.