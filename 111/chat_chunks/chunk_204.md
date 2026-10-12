## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-20 21:07:42

alexice@NEURO:~$ cd ~/projects/scene_fingerprint_mvp_v02

nl -ba app/web/main.py | sed -n '50,110p'
    50	        print(
    51	            "[WEB] Pipeline Supervisor already running",
    52	            flush=True,
    53	        )
    54	        return
    55	
    56	    print(
    57	        "[WEB] Starting Pipeline Supervisor",
    58	        flush=True,
    59	    )
    60	
    61	    _supervisor_task = asyncio.create_task(
    62	        supervisor_loop()
    63	    )
    64	
    65	
    66	ui.timer(
    67	    0.1,
    68	    start_pipeline_supervisor,
    69	    once=True,
    70	)
    71	
    72	
    73	# ============================================================
    74	# PAGE
    75	# ============================================================
    76	
    77	@ui.page("/")
    78	def index():
    79	
    80	    # ========================================================
    81	    # HEADER
    82	    #
    83	    # ui.header() должен быть прямым элементом страницы.
    84	    # ========================================================
    85	
    86	    build_header()
    87	
    88	    # ========================================================
    89	    # GLOBAL PAGE
    90	    # ========================================================
    91	
    92	    with ui.column().classes(
    93	        "w-full h-screen min-h-0 gap-0"
    94	    ).style(
    95	        """
    96	        display:flex;
    97	        flex-direction:column;
    98	        overflow:hidden;
    99	        min-height:0;
   100	        """
   101	    ):
   102	
   103	        # ====================================================
   104	        # SEARCH
   105	        # ====================================================
   106	
   107	        with ui.row().classes(
   108	            "w-full shrink-0 items-center px-3 py-0 leading-none gap-0"
   109	        ).style(
   110	            """
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "================ MAIN IMPORTS ================"
nl -ba app/web/main.py | sed -n '1,50p'

echo "================ PHOTO INDEX INIT ================"
nl -ba app/web/components/photos.py | sed -n '250,430p'

echo "================ PHOTO COMPONENT START ================"
nl -ba app/web/components/photos.py | sed -n '1080,1140p'
================ MAIN IMPORTS ================
     1	import asyncio
     2	
     3	from nicegui import ui, app
     4	
     5	from app.web.config import HOST, PORT
     6	from app.web.state import STATE
     7	from app.web.components.header import build_header
     8	from app.web.components.search import build_search
     9	from app.web.components.clients import build_clients_panel
    10	from app.web.components.photos import build_photos
    11	from app.web.components.addresses import build_addresses
    12	from app.web.components.filter_bar import build_filter_bar
    13	from app.pipeline.supervisor import supervisor_loop
    14	
    15	
    16	# ============================================================
    17	# FRONTEND V2 STATIC
    18	# ============================================================
    19	
    20	from pathlib import Path
    21	from fastapi.staticfiles import StaticFiles
    22	
    23	
    24	app.mount(
    25	    "/v2",
    26	    StaticFiles(
    27	        directory=Path(
    28	            "app/web/frontend_v2"
    29	        ).resolve(),
    30	        html=True,
    31	    ),
    32	    name="frontend_v2",
    33	)
    34	
    35	
    36	
    37	# =================================# PIPELINE SUPERVISOR
    38	# ============================================================
    39	
    40	_supervisor_task = None
    41	
    42	
    43	async def start_pipeline_supervisor():
    44	    global _supervisor_task
    45	
    46	    if (
    47	        _supervisor_task is not None
    48	        and not _supervisor_task.done()
    49	    ):
    50	        print(
================ PHOTO INDEX INIT ================
   250	
   251	    if date_to and value > date_to:
   252	        return False
   253	
   254	    return True
   255	
   256	
   257	
   258	def build_photo_index():
   259	
   260	    PHOTO_INDEX.clear()
   261	
   262	    # ========================================================
   263	    # POSTGRESQL = ЕДИНЫЙ ИСТОЧНИК ИСТИНЫ
   264	    # ========================================================
   265	
   266	    try:
   267	        PHOTO_RECORD_INDEX.clear()
   268	
   269	        PHOTO_RECORD_INDEX.update(
   270	            build_photo_record_index(PROJECT_ROOT)
   271	        )
   272	
   273	        print(
   274	            "[PHOTO RECORD INDEX]",
   275	            "records=",
   276	            len(PHOTO_RECORD_INDEX),
   277	            flush=True,
   278	        )
   279	
   280	    except Exception as exc:
   281	
   282	        print(
   283	            "[PHOTO RECORD INDEX ERROR]",
   284	            repr(exc),
   285	            flush=True,
   286	        )
   287	
   288	        return
   289	
   290	    # ========================================================
   291	    # ВИРТУАЛЬНАЯ СОРТИРОВКА
   292	    #
   293	    # Никакого output/daily.
   294	    # Никакого копирования файлов.
   295	    # Физические фотографии остаются в source_path.
   296	    # ========================================================
   297	
   298	    address_files = {}
   299	    unassigned = []
   300	
   301	    for record in PHOTO_RECORD_INDEX.values():
   302	
   303	        # Не обрабатываем fallback-ключи:
   304	        # __ADDR_FILE__:address:filename
   305	        if not str(record.get("photo_id") or "").strip():
   306	            continue
   307	
   308	        # ----------------------------------------------------
   309	        # Физический путь фотографии
   310	        # ----------------------------------------------------
   311	
   312	        raw_path = (
   313	            record.get("source_path")
   314	            or record.get("path")
   315	        )
   316	
   317	        if not raw_path:
   318	            continue
   319	
   320	        path = Path(raw_path)
   321	
   322	        if not path.is_absolute():
   323	            path = PROJECT_ROOT / path
   324	
   325	        path = path.resolve()
   326	
   327	        if not path.exists():
   328	            print(
   329	                "[PHOTO FILE NOT FOUND]",
   330	                path,
   331	                flush=True,
   332	            )
   333	            continue
   334	
   335	        if (
   336	            not path.is_file()
   337	            or path.suffix.lower() not in IMAGE_EXTENSIONS
   338	        ):
   339	            continue
   340	
   341	        # ----------------------------------------------------
   342	        # ВИРТУАЛЬНЫЙ АДРЕС
   343	        #
   344	        # Hybrid имеет приоритет.
   345	        # Если Hybrid ещё не рассчитан —
   346	        # используем результат DINO.
   347	        # ----------------------------------------------------
   348	
   349	        address = (
   350	            record.get("hybrid_final_id")
   351	            or record.get("dino_fingerprint")
   352	        )
   353	
   354	        address = str(address or "").strip()
   355	
   356	        # ----------------------------------------------------
   357	        # Без результата распознавания
   358	        # ----------------------------------------------------
   359	
   360	        if not address:
   361	            unassigned.append(path)
   362	            continue
   363	
   364	        # 85_v33 -> 85
   365	        if (
   366	            address.endswith("_v33")
   367	            and address[:-4].isdigit()
   368	        ):
   369	            address = address[:-4]
   370	
   371	        address_files.setdefault(
   372	            address,
   373	            []
   374	        ).append(path)
   375	
   376	    # ========================================================
   377	    # АДРЕСА
   378	    # ========================================================
   379	
   380	    addresses = sorted(
   381	        address_files.keys(),
   382	        key=lambda value: (
   383	            (0, int(value))
   384	            if value.isdigit()
   385	            else (1, value.lower())
   386	        ),
   387	    )
   388	
   389	    # Специальная виртуальная группа
   390	    # для фотографий без результата DINO.
   391	    if unassigned:
   392	        address_files["__UNASSIGNED__"] = sorted(
   393	            unassigned,
   394	            key=lambda p: p.name.lower(),
   395	        )
   396	
   397	        addresses.append("__UNASSIGNED__")
   398	
   399	    # ========================================================
   400	    # СОХРАНЯЕМ ИНДЕКС
   401	    # ========================================================
   402	
   403	    for address in addresses:
   404	
   405	        files = address_files.get(
   406	            address,
   407	            [],
   408	        )
   409	
   410	        # Убираем возможные дубликаты
   411	        unique = {}
   412	
   413	        for path in files:
   414	            unique[str(path)] = path
   415	
   416	        PHOTO_INDEX[address] = sorted(
   417	            unique.values(),
   418	            key=lambda p: p.name.lower(),
   419	        )
   420	
   421	    STATE.addresses = addresses
   422	
   423	    # Сбрасываем выбранные адреса,
   424	    # которых больше нет в текущем индексе.
   425	    STATE.selected_addresses.intersection_update(
   426	        STATE.addresses
   427	    )
   428	
   429	    print(
   430	        "[VIRTUAL PHOTO INDEX]",
================ PHOTO COMPONENT START ================
  1080	                "Сохранить фото",
  1081	                icon="download",
  1082	                on_click=lambda: (
  1083	                    dialog.close(),
  1084	                    ui.notify(
  1085	                        "Экспорт будет подключён позже"
  1086	                    ),
  1087	                ),
  1088	            ).props(
  1089	                "flat align-left w-full"
  1090	            )
  1091	
  1092	            ui.button(
  1093	                "Добавить в подборку",
  1094	                icon="folder",
  1095	                on_click=lambda: (
  1096	                    dialog.close(),
  1097	                    ui.notify(
  1098	                        "Подборки будут подключены позже"
  1099	                    ),
  1100	                ),
  1101	            ).props(
  1102	                "flat align-left w-full"
  1103	            )
  1104	
  1105	    dialog.open()
  1106	
  1107	
  1108	# ============================================================
  1109	# BUILD PHOTOS
  1110	# ============================================================
  1111	
  1112	def build_photos():
  1113	
  1114	    # --------------------------------------------------------
  1115	    # Сканируем базу ОДИН РАЗ
  1116	    # --------------------------------------------------------
  1117	
  1118	    build_photo_index()
  1119	
  1120	    # ========================================================
  1121	    # LAZY GRID
  1122	    # ========================================================
  1123	
  1124	    GRID_PAGE_SIZE = 40
  1125	
  1126	    # --------------------------------------------------------
  1127	    # DISPLAY SETTINGS
  1128	    # --------------------------------------------------------
  1129	
  1130	    if not hasattr(STATE, "photo_view_mode"):
  1131	        STATE.photo_view_mode = "grid"
  1132	
  1133	    if not hasattr(STATE, "photo_size"):
  1134	        STATE.photo_size = "medium"
  1135	
  1136	    grid_loaded = 0
  1137	
  1138	    total_photos = len(
  1139	        get_all_indexed_photos()
  1140	    )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo "================ CLIENTS INIT ================"
grep -RniE \
'STATE\.clients|clients\s*=|build_.*client|load_.*client|load_.*address|build_.*address|STATE\.addresses' \
app/web/components app/web/main.py \
--include="*.py" | grep -v '\.bak' | head -150
================ CLIENTS INIT ================
app/web/components/photos_before_cache_20260816_145128.py:22:    for address in STATE.addresses:
app/web/components/addresses.py:51:def build_addresses(refresh_photos):
app/web/components/addresses.py:116:                    for address in STATE.addresses
app/web/components/addresses.py:196:            for address in STATE.addresses:
app/web/components/header.py:55:        for address in STATE.addresses
app/web/components/photos.py:421:    STATE.addresses = addresses
app/web/components/photos.py:426:        STATE.addresses
app/web/components/photos.py:432:        len(STATE.addresses),
app/web/components/photos.py:443:        STATE.addresses,
app/web/components/photos.py:458:    for address in STATE.addresses:
app/web/components/photos.py:702:                for address in STATE.addresses:
app/web/components/photos.py:759:    selected_clients = STATE.selected_clients
app/web/components/clients.py:8:def build_clients_panel(refresh_photos):
app/web/components/clients.py:15:        clients = get_clients_with_address_counts()
app/web/components/clients.py:25:        clients = []
app/web/components/clients.py:39:        STATE.selected_clients = None
app/web/components/clients.py:53:        STATE.selected_clients = set()
app/web/components/clients.py:67:        all_clients = {
app/web/components/clients.py:78:            STATE.selected_clients = set(
app/web/components/clients.py:96:        if STATE.selected_clients == all_clients:
app/web/components/clients.py:97:            STATE.selected_clients = None
app/web/components/clients.py:104:            "STATE.selected_clients=",
app/web/components/clients.py:231:        build_collections("clients")
app/web/main.py:9:from app.web.components.clients import build_clients_panel
app/web/main.py:11:from app.web.components.addresses import build_addresses
app/web/main.py:355:                build_clients_panel(
app/web/main.py:397:                build_addresses(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 21:07:43

> **Diagnosing Main Calls and Client Functions**
>
>
> **Diagnosing Main Calls and Client Functions**
>
> 
>
> Worked for 4s

Да. По текущему коду уже видно важное:

**клиенты и адреса действительно должны приходить из PostgreSQL**, а `build_photo_index()` сейчас формирует `STATE.addresses` **из индекса фотографий**, то есть это не тот источник, из которого должны строиться панели клиентов/адресов.

Нужно проверить две вещи:
1. вызываются ли `build_clients_panel()` и `build_addresses()` при создании страницы;
2. действительно ли их функции получают данные из PSQL.

Выполни, пожалуйста, **одну команду из проекта**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ MAIN 330-410 ================" && \
nl -ba app/web/main.py | sed -n '320,410p' && \
echo "================ CLIENTS ================" && \
nl -ba app/web/components/clients.py | sed -n '1,130p' && \
echo "================ ADDRESSES ================" && \
nl -ba app/web/components/addresses.py | sed -n '1,230p' && \
echo "================ PSQL HELPERS ================" && \
grep -RniE \
'get_clients_with_address_counts|psycopg|postgres|photobase|client.*address|address.*client' \
app/web \
--include="*.py" | grep -v '\.bak' | head -150
```

**Пока ничего не исправляем.**

Особенно хочу увидеть `main.py` **330–410**: там, судя по твоему grep, уже есть вызовы:

```python
build_clients_panel(...)
build_addresses(...)
```

Если они вызываются **после `build_photos()`**, то проблема может быть ещё проще: новая страница сейчас строится с пустым `STATE`, а панели не получают/не восстанавливают PSQL-данные.

И ещё важный момент: строки

```text
[PHOTO GRID INITIAL LOAD]
loaded= 0 total= 0
[PHOTO RECORD LINK] linked= 0 total= 0
```

говорят, что проблема шире, чем только отображение клиентов. Надо одновременно проверить, **почему `build_photo_record_index(PROJECT_ROOT)` возвращает 0 записей**. Это сейчас главный подозреваемый.

---

### 👤 **User** — 2026-08-20 21:08:44

грид отображает фото прошедшие фильтрацию адресов и клиентов на основе даннызх из psql

---

### 🤖 **Assistant** — 2026-08-20 21:08:44

Да, тогда логика ясна. И это важное уточнение.

**PSQL — источник клиентов и адресов для фильтрации, а грид показывает физические фотографии, отфильтрованные по этим данным.**  
`build_photo_index()` не должен подменять список адресов PSQL списком адресов, найденных в фотоиндексе.

Сейчас у нас потенциально две разные сущности:

```text
                 PostgreSQL
              ┌───────────────┐
              │ Клиенты        │
              │ Адреса         │
              │ Фото           │
              │ связи          │
              └───────┬───────┘
                      │
             фильтрация по
          клиентам / адресам
                      │
                      ▼
              ┌───────────────┐
              │   PHOTO GRID  │
              │               │
              │ физические    │
              │ файлы          │
              └───────────────┘
```

А сейчас в `photos.py` есть:

```python
STATE.addresses = addresses
```

где `addresses` получены из:

```python
for record in PHOTO_RECORD_INDEX.values():
    ...
    address = (
        record.get("hybrid_final_id")
        or record.get("dino_fingerprint")
    )
```

То есть `STATE.addresses` **перезаписывается результатами индекса фотографий**.

Это может объяснить, почему после последних изменений новая страница получается пустой/без клиентов и адресов.

### Но сначала проверим фактическую цепочку

Нам нужно увидеть `main.py` вокруг строк 330–410 и реализацию PSQL-запросов клиентов/адресов. Выполни команду из предыдущего сообщения:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ MAIN 320-410 ================" && \
nl -ba app/web/main.py | sed -n '320,410p' && \
echo "================ CLIENTS ================" && \
nl -ba app/web/components/clients.py | sed -n '1,130p' && \
echo "================ ADDRESSES ================" && \
nl -ba app/web/components/addresses.py | sed -n '1,230p' && \
echo "================ PSQL HELPERS ================" && \
grep -RniE \
'get_clients_with_address_counts|psycopg|postgres|photobase|client.*address|address.*client' \
app/web \
--include="*.py" | grep -v '\.bak' | head -150
```

После этого уже можно будет точно восстановить правильную схему, **не ломая текущую виртуальную сортировку и фильтрацию грида**.

---

### 👤 **User** — 2026-08-20 21:09:35

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ MAIN 320-410 ================" && \
nl -ba app/web/main.py | sed -n '320,410p' && \
echo "================ CLIENTS ================" && \
nl -ba app/web/components/clients.py | sed -n '1,130p' && \
echo "================ ADDRESSES ================" && \
nl -ba app/web/components/addresses.py | sed -n '1,230p' && \
echo "================ PSQL HELPERS ================" && \
grep -RniE \
'get_clients_with_address_counts|psycopg|postgres|photobase|client.*address|address.*client' \
app/web \
--include="*.py" | grep -v '\.bak' | head -150
================ MAIN 320-410 ================
   320	
   321	        ui.separator()
   322	
   323	        # =================================================
   324	        # CLIENTS + PHOTOS + ADDRESSES
   325	        #
   326	        # Три независимые панели в одной горизонтальной строке.
   327	        # =================================================
   328	
   329	        with ui.row().classes(
   330	            "flex-1 w-full min-h-0 min-w-0 gap-0"
   331	        ).style(
   332	            """
   333	            display:flex;
   334	            flex-direction:row;
   335	            overflow:hidden;
   336	            min-height:0;
   337	            """
   338	        ):
   339	
   340	            # =================================================
   341	            # CLIENTS
   342	            # =================================================
   343	
   344	            with ui.column().classes(
   345	                "w-[280px] min-w-[280px] h-full min-h-0"
   346	            ).style(
   347	                """
   348	                display:flex;
   349	                flex-direction:column;
   350	                overflow:hidden;
   351	                min-height:0;
   352	                """
   353	            ):
   354	
   355	                build_clients_panel(
   356	                    lambda: (
   357	                        STATE.refresh_photos()
   358	                        if STATE.refresh_photos
   359	                        else None
   360	                    )
   361	                )
   362	
   363	            # =================================================
   364	            # PHOTOS
   365	            # =================================================
   366	
   367	            with ui.column().classes(
   368	                "flex-1 min-w-0 h-full min-h-0"
   369	            ).style(
   370	                """
   371	                display:flex;
   372	                flex-direction:column;
   373	                overflow:hidden;
   374	                min-height:0;
   375	                """
   376	            ):
   377	
   378	                refresh_photos = build_photos()
   379	
   380	                STATE.refresh_photos = refresh_photos
   381	
   382	            # =================================================
   383	            # ADDRESSES
   384	            # =================================================
   385	
   386	            with ui.column().classes(
   387	                "w-[280px] min-w-[280px] h-full min-h-0"
   388	            ).style(
   389	                """
   390	                display:flex;
   391	                flex-direction:column;
   392	                overflow:hidden;
   393	                min-height:0;
   394	                """
   395	            ):
   396	
   397	                build_addresses(
   398	                    lambda: (
   399	                        STATE.refresh_photos()
   400	                        if STATE.refresh_photos
   401	                        else None
   402	                    )
   403	                )
   404	
   405	        # ====================================================
   406	        # STATUS BAR
   407	        #
   408	        # Фиксированный нижний ограничитель.
   409	        # Позже сюда:
   410	        # статистика / сообщения / прогресс.
================ CLIENTS ================
     1	from nicegui import ui
     2	
     3	from app.web.state import STATE
     4	from app.web.components.collections import build_collections
     5	from app.web.client_db import get_clients_with_address_counts
     6	
     7	
     8	def build_clients_panel(refresh_photos):
     9	
    10	    # --------------------------------------------------------
    11	    # LOAD CLIENTS
    12	    # --------------------------------------------------------
    13	
    14	    try:
    15	        clients = get_clients_with_address_counts()
    16	
    17	    except Exception as exc:
    18	
    19	        print(
    20	            "[CLIENT DB ERROR]",
    21	            repr(exc),
    22	            flush=True,
    23	        )
    24	
    25	        clients = []
    26	
    27	    # --------------------------------------------------------
    28	    # CHECKBOX REFERENCES
    29	    # --------------------------------------------------------
    30	
    31	    client_checkboxes = {}
    32	
    33	    # --------------------------------------------------------
    34	    # CLIENT ACTIONS
    35	    # --------------------------------------------------------
    36	
    37	    def select_all_clients():
    38	
    39	        STATE.selected_clients = None
    40	
    41	        print(
    42	            "[CLIENT SELECT ALL]",
    43	            flush=True,
    44	        )
    45	
    46	        for checkbox in client_checkboxes.values():
    47	            checkbox.value = True
    48	
    49	        refresh_photos()
    50	
    51	    def clear_clients():
    52	
    53	        STATE.selected_clients = set()
    54	
    55	        print(
    56	            "[CLIENT CLEAR]",
    57	            flush=True,
    58	        )
    59	
    60	        for checkbox in client_checkboxes.values():
    61	            checkbox.value = False
    62	
    63	        refresh_photos()
    64	
    65	    def select_client(e, name):
    66	
    67	        all_clients = {
    68	            client
    69	            for client, _ in clients
    70	        }
    71	
    72	        # ----------------------------------------------------
    73	        # Был режим "Все"
    74	        # ----------------------------------------------------
    75	
    76	        if STATE.selected_clients is None:
    77	
    78	            STATE.selected_clients = set(
    79	                all_clients
    80	            )
    81	
    82	        # ----------------------------------------------------
    83	        # Реальное состояние checkbox
    84	        # ----------------------------------------------------
    85	
    86	        if e.value:
    87	            STATE.selected_clients.add(name)
    88	        else:
    89	            STATE.selected_clients.discard(name)
    90	
    91	        # ----------------------------------------------------
    92	        # Если снова выбраны все —
    93	        # возвращаем компактное состояние "Все"
    94	        # ----------------------------------------------------
    95	
    96	        if STATE.selected_clients == all_clients:
    97	            STATE.selected_clients = None
    98	
    99	        print(
   100	            "[CLIENT SELECT]",
   101	            repr(name),
   102	            "checked=",
   103	            e.value,
   104	            "STATE.selected_clients=",
   105	            repr(STATE.selected_clients),
   106	            flush=True,
   107	        )
   108	
   109	        refresh_photos()
   110	
   111	    def toggle_client(name, checkbox):
   112	        """
   113	        Единый обработчик клика по checkbox и названию клиента.
   114	        STATE меняется явно, затем грид сразу обновляется.
   115	        """
   116	
   117	        checked = not checkbox.value
   118	        checkbox.value = checked
   119	
   120	        class Event:
   121	            pass
   122	
   123	        event = Event()
   124	        event.value = checked
   125	
   126	        select_client(event, name)
   127	
   128	
   129	    # --------------------------------------------------------
   130	    # PANEL
================ ADDRESSES ================
     1	from nicegui import ui
     2	
     3	from app.web.components.photos import get_latest_daily_root
     4	from app.web.state import STATE
     5	from app.web.components.collections import build_collections
     6	
     7	
     8	IMAGE_EXTENSIONS = {
     9	    ".jpg",
    10	    ".jpeg",
    11	    ".png",
    12	    ".webp",
    13	}
    14	
    15	
    16	def address_folder(address):
    17	    daily_root = get_latest_daily_root()
    18	
    19	    if daily_root is None:
    20	        return None
    21	
    22	    return daily_root / f"{address}_v33"
    23	
    24	
    25	def address_photo_count(address):
    26	
    27	    # Источник количества — виртуальный индекс,
    28	    # а не физические папки output/daily.
    29	    try:
    30	        from app.web.components.photos import PHOTO_INDEX
    31	
    32	        return len(
    33	            PHOTO_INDEX.get(
    34	                address,
    35	                [],
    36	            )
    37	        )
    38	
    39	    except Exception as exc:
    40	
    41	        print(
    42	            "[ADDRESS COUNT ERROR]",
    43	            address,
    44	            repr(exc),
    45	            flush=True,
    46	        )
    47	
    48	        return 0
    49	
    50	
    51	def build_addresses(refresh_photos):
    52	
    53	    with ui.card().classes(
    54	        "w-full h-full min-h-0"
    55	    ).style(
    56	        "display: flex;"
    57	        "flex-direction: column;"
    58	        "overflow: hidden;"
    59	    ):
    60	
    61	        ui.label(
    62	            "Адреса"
    63	        ).classes(
    64	            "text-lg font-bold"
    65	        )
    66	
    67	        ui.label(
    68	            "Фильтр по адресам"
    69	        ).classes(
    70	            "text-sm text-grey-6"
    71	        )
    72	
    73	        # ========================================================
    74	        # CONTROLS
    75	        # ========================================================
    76	
    77	        with ui.row().classes(
    78	            "w-full gap-1 mt-2"
    79	        ):
    80	
    81	            address_checkboxes = {}
    82	
    83	            def sync_collection():
    84	
    85	                collection = getattr(
    86	                    STATE,
    87	                    "active_collection",
    88	                    None,
    89	                )
    90	
    91	                if collection is None:
    92	                    return
    93	
    94	                if getattr(
    95	                    collection,
    96	                    "scope",
    97	                    "addresses",
    98	                ) != "addresses":
    99	                    return
   100	
   101	                collection.members = set(
   102	                    STATE.selected_addresses
   103	                )
   104	
   105	                print(
   106	                    "[COLLECTION SYNC]",
   107	                    collection.name,
   108	                    sorted(collection.members),
   109	                    flush=True,
   110	                )
   111	
   112	            def select_all():
   113	
   114	                STATE.selected_addresses = set(
   115	                    address
   116	                    for address in STATE.addresses
   117	                    if address != "__UNASSIGNED__"
   118	                )
   119	
   120	                for address, checkbox in (
   121	                    address_checkboxes.items()
   122	                ):
   123	                    checkbox.value = True
   124	
   125	                sync_collection()
   126	
   127	                refresh_photos()
   128	
   129	            def clear_all():
   130	
   131	                STATE.selected_addresses.clear()
   132	
   133	                for address, checkbox in (
   134	                    address_checkboxes.items()
   135	                ):
   136	                    checkbox.value = False
   137	
   138	                sync_collection()
   139	
   140	                refresh_photos()
   141	
   142	            ui.button(
   143	                "Все",
   144	                icon="done_all",
   145	                on_click=select_all,
   146	            ).props(
   147	                "flat dense"
   148	            )
   149	
   150	            ui.button(
   151	                "Снять",
   152	                icon="remove_done",
   153	                on_click=clear_all,
   154	            ).props(
   155	                "flat dense"
   156	            )
   157	
   158	        ui.separator().classes(
   159	            "my-2"
   160	        )
   161	
   162	        def toggle_address(address, checkbox):
   163	            """
   164	            Единый обработчик клика по checkbox и названию адреса.
   165	            STATE меняется явно, затем грид сразу обновляется.
   166	            """
   167	
   168	            checked = not checkbox.value
   169	            checkbox.value = checked
   170	
   171	            class Event:
   172	                pass
   173	
   174	            event = Event()
   175	            event.value = checked
   176	
   177	            change_address(
   178	                event,
   179	                address,
   180	            )
   181	
   182	        # ========================================================
   183	        # ADDRESS LIST
   184	        #
   185	        # Важно:
   186	        # адреса никогда не скрываем при выборе подборки.
   187	        # Подборка только меняет состояние checkbox.
   188	        # ========================================================
   189	
   190	        with ui.column().classes(
   191	            "w-full flex-1 min-h-0"
   192	        ).style(
   193	            "overflow-y: auto;"
   194	        ):
   195	
   196	            for address in STATE.addresses:
   197	
   198	                if address == "__UNASSIGNED__":
   199	                    continue
   200	
   201	                count = address_photo_count(
   202	                    address
   203	                )
   204	
   205	                def change_address(
   206	                    e,
   207	                    address=address,
   208	                ):
   209	
   210	                    if e.value:
   211	
   212	                        STATE.selected_addresses.add(
   213	                            address
   214	                        )
   215	
   216	                    else:
   217	
   218	                        STATE.selected_addresses.discard(
   219	                            address
   220	                        )
   221	
   222	                    sync_collection()
   223	
   224	                    print(
   225	                        "[UI] selected:",
   226	                        sorted(
   227	                            STATE.selected_addresses
   228	                        ),
   229	                        flush=True,
   230	                    )
================ PSQL HELPERS ================
app/web/components/search.py:1:import psycopg2
app/web/components/search.py:9:# POSTGRESQL
app/web/components/search.py:15:    "dbname": "photobase",
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:90:    with psycopg2.connect(**PG_CONFIG) as conn:
app/web/components/search.py:138:                "[PostgreSQL search ERROR]",
app/web/components/search.py:143:                f"Ошибка поиска PostgreSQL: {exc}",
app/web/components/technical_modules/photo_processing.py:712:            # Фиксируем намерение остановки в PostgreSQL.
app/web/components/technical_modules/photo_processing.py:1061:            "Состояние очередей определяется по PostgreSQL."
app/web/components/technical_modules/data.py:283:                "Записей PostgreSQL",
app/web/components/photos.py:196:        PostgreSQL created_at.
app/web/components/photos.py:263:    # POSTGRESQL = ЕДИНЫЙ ИСТОЧНИК ИСТИНЫ
app/web/components/photos.py:599:        PostgreSQL created_at.
app/web/components/photos.py:1436:                    # корневой путь, чем запись PostgreSQL.
app/web/components/clients.py:5:from app.web.client_db import get_clients_with_address_counts
app/web/components/clients.py:15:        clients = get_clients_with_address_counts()
app/web/components/clients.py:196:            for name, address_count in clients:
app/web/photo_db.py:1:import psycopg2
app/web/photo_db.py:7:    "dbname": "photobase",
app/web/photo_db.py:14:    Загружает все записи фотографий из PostgreSQL.
app/web/photo_db.py:62:    with psycopg2.connect(**PG_CONFIG) as conn:
app/web/photo_db.py:82:    Источник истины — PostgreSQL таблица photos.
app/web/photo_db.py:124:    with psycopg2.connect(**PG_CONFIG) as conn:
app/web/photo_db.py:150:    Создаёт индекс PostgreSQL-записей по абсолютному пути файла.
app/web/frontend_v02.py:489:        for client_name, groups in ADDRESS_GROUPS.items():
app/web/main.py:324:        # CLIENTS + PHOTOS + ADDRESSES
app/web/users_db.py:3:import psycopg2
app/web/users_db.py:9:# POSTGRESQL
app/web/users_db.py:13:    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
app/web/users_db.py:14:    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
app/web/users_db.py:15:    "user": os.getenv("PHOTOBASE_USER", "lora"),
app/web/users_db.py:16:    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
app/web/users_db.py:17:    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
app/web/users_db.py:39:    return psycopg2.connect(**PG_CONFIG)
app/web/users_db.py:44:    Инициализация PostgreSQL-таблиц пользователей.
app/web/users_db.py:213:    except psycopg2.IntegrityError:
app/web/users_db.py:244:    except psycopg2.IntegrityError:
app/web/state.py:152:    # upload = дата загрузки / создания записи в PostgreSQL
app/web/client_db.py:1:import psycopg2
app/web/client_db.py:7:    "dbname": "photobase",
app/web/client_db.py:12:def get_clients_with_address_counts() -> list[tuple[str, int]]:
app/web/client_db.py:32:    with psycopg2.connect(**PG_CONFIG) as conn:
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 21:09:37

Теперь причина стала намного яснее.

### Что сейчас происходит

Порядок создания страницы такой:

```text
CLIENTS
  ↓
PHOTOS
  ↓
ADDRESSES
```

При этом:

- **Клиенты** напрямую читаются из PSQL через `get_clients_with_address_counts()` — это правильно.
- **Фотографии** строят `STATE.addresses` через `build_photo_index()`.
- **Адреса** потом читают `STATE.addresses`.

И вот здесь проблема:

```python
build_photos()
    ↓
build_photo_index()
    ↓
build_photo_record_index(PROJECT_ROOT)
    ↓
PHOTO_RECORD_INDEX = 0
    ↓
STATE.addresses = []
    ↓
build_addresses()
    ↓
адресов нет
```

То есть **адресная панель сейчас зависит от успешного построения фотоиндекса**, хотя ты правильно уточнил: **список адресов должен приходить из PSQL**, а грид уже должен фильтроваться по этим адресам.

И отдельно надо разобраться, почему `PHOTO_RECORD_INDEX` сейчас стал `0`.

---

### Сначала не меняем код

Давай точно установим оба источника:

1. что возвращает `client_db`;
2. что именно делает `build_photo_record_index()` и почему он возвращает 0.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \

echo "================ CLIENT DB ================" && \
nl -ba app/web/client_db.py | sed -n '1,140p' && \

echo "================ PHOTO DB ================" && \
nl -ba app/web/photo_db.py | sed -n '1,190p' && \

echo "================ IMPORTS PHOTOS ================" && \
nl -ba app/web/components/photos.py | sed -n '1,80p' && \

echo "================ RECORD INDEX DEFINITION ================" && \
grep -RniE \
'def build_photo_record_index|build_photo_record_index' \
app \
--include="*.py" | grep -v '\.bak'
```

Особенно нужен результат:

```text
def build_photo_record_index(...)
```

### Что мы будем исправлять

Архитектуру лучше оставить такой:

```text
                    PSQL
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
      КЛИЕНТЫ                   АДРЕСА
          │                       │
          └───────────┬───────────┘
                      ▼
                 ФИЛЬТРЫ STATE
                      │
                      ▼
              PHOTO_RECORD_INDEX
                      │
                      ▼
                  PHOTO GRID
```

А не:

```text
PHOTO_RECORD_INDEX
       │
       ▼
STATE.addresses
       │
       ▼
ADDRESS PANEL
```

Последняя схема как раз сейчас и получилась.

**Причём `build_photo_index()` может продолжать использовать `hybrid_final_id / dino_fingerprint` для виртуальной сортировки фотографий — это не надо ломать.** Нужно просто отделить **справочник адресов PSQL** от **адресов, реально присутствующих в фотоиндексе**.

И ещё: клиенты уже вызываются **до** `build_photos()`, поэтому если клиентов тоже физически нет на новой странице, посмотрим `[CLIENT DB ERROR]` — это будет отдельная проблема с PSQL/запросом, а не с `build_photo_index()`.

Скинь вывод команды выше.

---

### 👤 **User** — 2026-08-20 21:11:55

может быть не стоит восстанвливать то, что было, а сделат новое - с учетом бекенда. ?  
Источником фотографий для фотогрида является данные из PSQL возникающие после работы DINO + Hybrid, но прошедешие через фильтра Адресов и Клиентов. Данные квен - подкачиваются при просмотре из PSQL также

---

### 🤖 **Assistant** — 2026-08-20 21:11:56

Да. **Я бы именно так и сделал.** Не восстанавливать старую цепочку, а зафиксировать новую архитектуру поверх уже готового backend.

Сейчас у нас хороший момент для этого: backend уже определяет, **какие фотографии существуют, какой у них адрес, клиент и результаты DINO/Hybrid**, а UI должен быть только представлением и фильтрацией этих данных.

### Новая правильная схема

```text
                 BACKEND / PSQL
                       │
        ┌──────────────┼──────────────┐
        │              │              │
     CLIENTS         ADDRESSES       PHOTOS
        │              │              │
        │              │       DINO + Hybrid
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
                WEB STATE / FILTERS
                       │
             ┌─────────┴─────────┐
             │                   │
       Клиент выбран?       Адрес выбран?
             │                   │
             └─────────┬─────────┘
                       ▼
                 SQL / index
                       │
                       ▼
                 PHOTO GRID
                       │
                       ▼
              запрос Qwen при
                просмотре
```

### То есть источник грида — не файловая система

Это принципиально.

**Не надо делать:**

```python
scan folders
    ↓
найти JPG
    ↓
определить адрес
    ↓
построить PHOTO_INDEX
```

И не надо:

```python
STATE.addresses = addresses_from_photo_index
```

Это наследие старой архитектуры.

---

## Как должно быть

### 1. PSQL — единственный источник фотографий

После pipeline в PostgreSQL уже есть запись фотографии:

```text
photo
├── photo_id
├── source_path
├── client
├── address
├── dino_fingerprint
├── hybrid_final_id
├── ...
```

Тогда UI получает примерно:

```python
photos = get_photos(
    clients=STATE.selected_clients,
    addresses=STATE.selected_addresses,
    date_from=STATE.date_from,
    date_to=STATE.date_to,
)
```

И всё.

**Никакого сканирования `output/daily`.**

---

### 2. Адреса — из PSQL

Панель адресов должна делать:

```python
addresses = get_addresses_from_db()
```

а не:

```python
addresses = STATE.addresses
```

где `STATE.addresses` случайно появился после построения индекса фотографий.

---

### 3. Клиенты — из PSQL

Это у нас уже практически есть:

```python
get_clients_with_address_counts()
```

Оставляем эту идею, но делаем её частью общей модели данных.

---

### 4. Фильтры — только состояние UI

Например:

```python
STATE.selected_clients
STATE.selected_addresses
STATE.date_type
STATE.date_from
STATE.date_to
```

Они **не являются источником данных**.

Они только говорят backend/query:

> покажи мне вот эти фотографии.

---

### 5. Грид

Грид получает уже отфильтрованный список:

```text
PSQL
 ↓
WHERE client IN (...)
AND address IN (...)
AND date BETWEEN ...
 ↓
photos
 ↓
grid
```

Можно делать lazy loading:

```text
SELECT ...
LIMIT 40 OFFSET 0
```

потом:

```text
LIMIT 40 OFFSET 40
```

А ещё лучше — cursor pagination, когда дойдём до оптимизации.

---

# А Qwen здесь вообще отдельно

И это тоже очень правильно.

При открытии/просмотре фотографии:

```text
PHOTO GRID
   │
   │ photo_id
   ▼
PSQL
   │
   ├── Qwen description
   ├── Qwen tags
   ├── Qwen OCR/analysis
   └── metadata
```

Если Qwen уже рассчитан — берём из PSQL.

Если нет — можно будет отдельно решить, запускать ли расчёт.

**Грид не должен ждать Qwen.**

То есть:

```text
DINO + Hybrid
       ↓
PSQL
       ↓
фильтр
       ↓
ГРИД
       ↓
просмотр
       ↓
Qwen data из PSQL
```

Это очень чистая архитектура.

---

# И самое главное

Я бы сейчас **вообще убрал концепцию `PHOTO_INDEX` как источника истины для UI**.

Она может остаться как внутренний кэш, если понадобится производительность:

```python
PHOTO_INDEX
```

но тогда:

> **PSQL → PHOTO_INDEX → GRID**

а не:

> **filesystem → PHOTO_INDEX → GRID**

И `STATE.addresses` тоже не должен заполняться из `PHOTO_INDEX`.

---

## Предлагаю сейчас не чинить старый `photos.py`

А сделать новый небольшой слой:

```text
app/web/
    db/
       photos.py
       clients.py
       addresses.py

    components/
       clients.py
       addresses.py
       photos.py
```

или, если хотим минимально менять проект:

```text
app/web/photo_db.py
app/web/client_db.py
app/web/address_db.py
```

и дать им очень чёткие обязанности:

```text
client_db.py
    ↓
клиенты

address_db.py
    ↓
адреса

photo_db.py
    ↓
фотографии + фильтрация

photos.py
    ↓
только отображение грида
```

Это будет гораздо надёжнее, чем сейчас пытаться восстановить цепочку из многочисленных `.bak`.

**Я за новый UI/data-flow с сохранением существующего backend DINO + Hybrid + PSQL.** Старую визуальную часть можно постепенно перенести, а старую логику поиска фотографий по папкам — больше не использовать.

---

### 👤 **User** — 2026-08-20 21:15:14

клиента определяет КВен, после дино и гибрида известен только адрес. Логика будет такая: 

- идет процесс Дино ГИбрид - Грид получает фото с учетом фильтра адресов и  с учетом фильтра клиентов (если клиент еще не определен квен, то фото отображается в чекбоксе у киентов, как другие

---

### 🤖 **Assistant** — 2026-08-20 21:15:17

Да. **Я бы не восстанавливал старую логику.** Сейчас у нас уже изменился backend-контракт, поэтому правильнее сделать новый слой отображения, который напрямую опирается на PSQL.

И я бы зафиксировал именно такую архитектуру.

### 1. Источник данных для грида

**PSQL — единственный источник истины для фотографий.**

После обработки:

```text
Фото
 ↓
DINO
 ↓
Hybrid
 ↓
PSQL
```

В PSQL для фотографии уже известно:

```text
photo
source_path
address / dino_fingerprint
hybrid_final_id
client        ← если Qwen уже определил
qwen_*        ← остальные данные Qwen
```

Грид **не должен сканировать `output/daily`**, искать папки `_v33` или строить собственную базу фотографий.

---

### 2. Адрес определяется раньше клиента

Это ключевой момент:

```text
DINO
  ↓
Hybrid
  ↓
АДРЕС
  ↓
PSQL
  ↓
Qwen
  ↓
КЛИЕНТ
```

То есть после DINO + Hybrid:

```text
photo_001.jpg → адрес 78 → client = NULL
photo_002.jpg → адрес 78 → client = "Газпром"
photo_003.jpg → адрес 82 → client = NULL
photo_004.jpg → адрес 82 → client = "Роснефть"
```

И это нормально.

---

### 3. Фильтр адресов

Грид сначала применяет адресный фильтр:

```text
STATE.selected_addresses
```

Например:

```text
[78, 82, 85]
```

Тогда из PSQL выбираются только фотографии:

```text
address IN (78, 82, 85)
```

---

### 4. Фильтр клиентов

Затем применяется клиентский фильтр.

И здесь как раз нужно учесть твою новую логику.

Если выбраны:

```text
Газпром
Роснефть
Другие
```

то:

```text
client = "Газпром"  → показываем
client = "Роснефть" → показываем
client IS NULL       → показываем как "Другие"
```

А если выбрано только:

```text
Газпром
```

то:

```text
client = "Газпром" → показываем
client = "Роснефть" → скрываем
client IS NULL → скрываем
```

Если выбран:

```text
Другие
```

то:

```text
client IS NULL → показываем
```

---

## 5. Что должно происходить с клиентской панелью

Вот это особенно важно.

**Клиенты не должны определяться из `PHOTO_INDEX`.**

Панель клиентов должна получать агрегат непосредственно из PSQL:

```text
Газпром       124
Роснефть       87
Лукойл         43
...
Другие         156
```

Где:

```text
Другие = фотографии, для которых Qwen еще не определил клиента
```

То есть после запуска DINO/Hybrid новые фотографии автоматически появляются в категории:

> **Другие**

А когда Qwen определит клиента:

```text
client = NULL
        ↓
client = "Газпром"
```

фотография автоматически перестает быть `Другие` и начинает относиться к `Газпром`.

Это гораздо чище старой архитектуры.

---

## 6. Важный нюанс с Qwen

Ты написал:

> Данные квен - подкачиваются при просмотре из PSQL также

И это тоже правильно.

**Не надо заставлять Qwen участвовать в построении грида.**

Грид получает из PSQL минимальный набор:

```text
photo_id
source_path
address
client
```

А когда пользователь открывает/смотрит фотографию, тогда из PSQL подгружаются:

```text
qwen description
qwen confidence
qwen objects
qwen text
...
```

То есть:

```text
                 PSQL
                  │
        ┌─────────┴─────────┐
        ↓                   ↓
   GRID QUERY          PHOTO VIEWER
        │                   │
 address/client       Qwen metadata
        │                   │
        ↓                   ↓
      фото              детали фото
```

---

# 7. Тогда `photos.py` надо упростить

Сейчас у нас старый слой:

```python
build_photo_index()
```

делает слишком много:

```text
PSQL
 ↓
PHOTO_RECORD_INDEX
 ↓
проверка физических файлов
 ↓
virtual address_files
 ↓
PHOTO_INDEX
 ↓
STATE.addresses
```

Это уже становится неправильным уровнем абстракции.

Новая модель должна быть примерно:

```python
query_photos_from_psql(
    addresses=STATE.selected_addresses,
    clients=STATE.selected_clients,
)
```

и возвращать:

```python
[
    {
        "photo_id": ...,
        "source_path": ...,
        "address": "78",
        "client": "Газпром",
    },
    ...
]
```

А грид просто отображает результат.

---

# 8. Архитектура целиком

Я бы сейчас зафиксировал её так:

```text
                 ┌──────────────────┐
                 │      ФОТО         │
                 └────────┬─────────┘
                          ↓
                       DINO
                          ↓
                       HYBRID
                          ↓
                    определить адрес
                          ↓
                     ┌─────────┐
                     │  PSQL   │
                     └────┬────┘
                          │
             ┌────────────┴────────────┐
             ↓                         ↓
       адрес известен             client = NULL
             │                         │
             │                       Qwen
             │                         ↓
             │                  определить клиента
             │                         │
             └────────────┬────────────┘
                          ↓
                         PSQL
                          ↓
              ┌───────────────────────┐
              │       WEB UI          │
              └───────────┬───────────┘
                          ↓
                фильтр АДРЕСОВ
                          ↓
                фильтр КЛИЕНТОВ
                          ↓
                        GRID
```

И главное:

**DINO/Hybrid создают адресную принадлежность.  
Qwen дополняет запись клиентом.  
PSQL хранит состояние.  
WEB только запрашивает и отображает.**

---

### И я бы сейчас вообще не трогал `build_photo_index()`

Не надо пытаться его чинить под новую задачу.

Лучше сделать новый слой, например:

```text
app/web/photo_query.py
```

с функциями:

```python
get_filtered_photos()
get_clients()
get_addresses()
get_photo_metadata()
```

и постепенно перевести:

```text
clients.py
addresses.py
photos.py
```

на него.

Тогда мы сохраним рабочий DINO + Hybrid backend и **полностью отвяжем новый грид от старой виртуальной файловой сортировки**.

Это, на мой взгляд, сейчас значительно надежнее, чем пытаться оживить старый `PHOTO_INDEX`.

---

### 👤 **User** — 2026-08-20 21:17:01

да

---

### 🤖 **Assistant** — 2026-08-20 21:17:38

Да. Тогда **старую логику не восстанавливаем**. Делаем новый PSQL-driven слой, не ломая DINO/Hybrid.

Первый шаг — **ничего пока не менять**. Сначала посмотрим точную структуру PSQL и текущий `client_db.py` / `photo_db.py`, чтобы новый запрос строился по реальным полям.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "================ PHOTO DB ================"
nl -ba app/web/photo_db.py | sed -n '1,190p'

echo "================ CLIENT DB ================"
nl -ba app/web/client_db.py | sed -n '1,160p'

echo "================ SEARCH DB ================"
nl -ba app/web/components/search.py | sed -n '1,180p'

echo "================ STATE ================"
nl -ba app/web/state.py | sed -n '1,230p'
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="lora",
    dbname="photobase",
)

cur = conn.cursor()

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")

print("TABLES:")
for row in cur.fetchall():
    print(row[0])

cur.close()
conn.close()
PY
```

После этого мы сначала определим **реальный контракт PSQL → WEB**.

Целевая схема будет:

```text
PSQL
 │
 ├── addresses
 │
 ├── clients
 │
 └── photos
       │
       ├── source_path
       ├── address        ← DINO + Hybrid
       └── client        ← Qwen / NULL
              │
              ↓
       новый photo_query.py
              │
       ┌──────┴──────┐
       ↓             ↓
  фильтр адресов  фильтр клиентов
       └──────┬──────┘
              ↓
             GRID
```

А `Qwen`-метаданные будем **не тащить при построении грида**, а получать из PSQL только для конкретного фото при открытии/просмотре.

Особенно важно: **`client = NULL` не является ошибкой**. Это полноценное состояние `Другие`, пока Qwen не определил клиента.

Пришли вывод этих команд — и следующим шагом сделаем новый `photo_query.py`, не трогая пока существующий `build_photo_index()`.

---

### 👤 **User** — 2026-08-20 21:18:19

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

echo "================ PHOTO DB ================"
nl -ba app/web/photo_db.py | sed -n '1,190p'

echo "================ CLIENT DB ================"
nl -ba app/web/client_db.py | sed -n '1,160p'

echo "================ SEARCH DB ================"
nl -ba app/web/components/search.py | sed -n '1,180p'

echo "================ STATE ================"
nl -ba app/web/state.py | sed -n '1,230p'
================ PHOTO DB ================
     1	import psycopg2
     2	
     3	
     4	PG_CONFIG = {
     5	    "host": "localhost",
     6	    "port": 5432,
     7	    "dbname": "photobase",
     8	    "user": "lora",
     9	}
    10	
    11	
    12	def get_photo_records() -> list[dict]:
    13	    """
    14	    Загружает все записи фотографий из PostgreSQL.
    15	    """
    16	
    17	    sql = """
    18	        SELECT
    19	            id,
    20	            photo_id,
    21	            address,
    22	            filename,
    23	            path,
    24	            source_path,
    25	            original_filename,
    26	            preview_path,
    27	            client,
    28	            brand,
    29	            category,
    30	            description,
    31	            confidence,
    32	            qwen_status,
    33	            qwen_time_sec,
    34	            text_json,
    35	            colors_json,
    36	            objects_json,
    37	            environment_json,
    38	            image_quality_json,
    39	            camera_view_json,
    40	            scene_objects_json,
    41	            analysis_quality_json,
    42	            raw_json,
    43	            created_at,
    44	            dino_fingerprint,
    45	            dino_score,
    46	            dino_second_score,
    47	            dino_margin,
    48	            hybrid_original_id,
    49	            hybrid_final_id,
    50	            hybrid_changed,
    51	            hybrid_old_score,
    52	            hybrid_score,
    53	            hybrid_margin,
    54	            hybrid_neighbors,
    55	            status,
    56	            dino_status,
    57	            sort_status
    58	        FROM photos
    59	        ORDER BY id
    60	    """
    61	
    62	    with psycopg2.connect(**PG_CONFIG) as conn:
    63	        with conn.cursor() as cur:
    64	            cur.execute(sql)
    65	
    66	            columns = [
    67	                desc[0]
    68	                for desc in cur.description
    69	            ]
    70	
    71	            rows = cur.fetchall()
    72	
    73	    return [
    74	        dict(zip(columns, row))
    75	        for row in rows
    76	    ]
    77	
    78	
    79	def get_processing_stats() -> dict:
    80	    """
    81	    Быстрая статистика независимых веток DINO и Qwen.
    82	    Источник истины — PostgreSQL таблица photos.
    83	    """
    84	
    85	    sql = """
    86	        SELECT
    87	            COUNT(*) AS total,
    88	
    89	            COUNT(*) FILTER (
    90	                WHERE dino_status = 'done'
    91	            ) AS dino_done,
    92	
    93	            COUNT(*) FILTER (
    94	                WHERE dino_status = 'processing'
    95	            ) AS dino_processing,
    96	
    97	            COUNT(*) FILTER (
    98	                WHERE dino_status = 'pending'
    99	            ) AS dino_pending,
   100	
   101	            COUNT(*) FILTER (
   102	                WHERE dino_status = 'error'
   103	            ) AS dino_error,
   104	
   105	            COUNT(*) FILTER (
   106	                WHERE qwen_status = 'done'
   107	            ) AS qwen_done,
   108	
   109	            COUNT(*) FILTER (
   110	                WHERE qwen_status = 'processing'
   111	            ) AS qwen_processing,
   112	
   113	            COUNT(*) FILTER (
   114	                WHERE qwen_status = 'pending'
   115	            ) AS qwen_pending,
   116	
   117	            COUNT(*) FILTER (
   118	                WHERE qwen_status = 'error'
   119	            ) AS qwen_error
   120	
   121	        FROM photos
   122	    """
   123	
   124	    with psycopg2.connect(**PG_CONFIG) as conn:
   125	        with conn.cursor() as cur:
   126	            cur.execute(sql)
   127	            row = cur.fetchone()
   128	
   129	    return {
   130	        "total": row[0] or 0,
   131	
   132	        "dino": {
   133	            "done": row[1] or 0,
   134	            "processing": row[2] or 0,
   135	            "pending": row[3] or 0,
   136	            "error": row[4] or 0,
   137	        },
   138	
   139	        "qwen": {
   140	            "done": row[5] or 0,
   141	            "processing": row[6] or 0,
   142	            "pending": row[7] or 0,
   143	            "error": row[8] or 0,
   144	        },
   145	    }
   146	
   147	
   148	def build_photo_record_index(project_root):
   149	    """
   150	    Создаёт индекс PostgreSQL-записей по абсолютному пути файла.
   151	    """
   152	
   153	    records = get_photo_records()
   154	
   155	    index = {}
   156	
   157	    for record in records:
   158	
   159	        path = record.get("path")
   160	
   161	        if not path:
   162	            continue
   163	
   164	        from pathlib import Path
   165	
   166	        db_path = Path(path)
   167	
   168	        if not db_path.is_absolute():
   169	            db_path = project_root / db_path
   170	
   171	        # Основной индекс: полный абсолютный путь
   172	        index[str(db_path.resolve())] = record
   173	
   174	        # Fallback для daily/test_sorted_v2 и других
   175	        # запусков, где один и тот же файл имеет разные
   176	        # корневые каталоги.
   177	        #
   178	        # Ключ: адрес + имя файла
   179	        address = str(record.get("address") or "").strip()
   180	        filename = db_path.name
   181	
   182	        if address and filename:
   183	            index[f"__ADDR_FILE__:{address}:{filename}"] = record
   184	
   185	    return index
================ CLIENT DB ================
     1	import psycopg2
     2	
     3	
     4	PG_CONFIG = {
     5	    "host": "localhost",
     6	    "port": 5432,
     7	    "dbname": "photobase",
     8	    "user": "lora",
     9	}
    10	
    11	
    12	def get_clients_with_address_counts() -> list[tuple[str, int]]:
    13	    """
    14	    Возвращает клиентов из результатов Qwen.
    15	
    16	    Количество — количество фотографий,
    17	    для которых Qwen определил клиента.
    18	    """
    19	
    20	    sql = """
    21	        SELECT
    22	            MIN(TRIM(client)) AS client,
    23	            COUNT(*) AS photo_count
    24	        FROM photos
    25	        WHERE
    26	            client IS NOT NULL
    27	            AND TRIM(client) <> ''
    28	        GROUP BY LOWER(TRIM(client))
    29	        ORDER BY LOWER(MIN(TRIM(client)))
    30	    """
    31	
    32	    with psycopg2.connect(**PG_CONFIG) as conn:
    33	        with conn.cursor() as cur:
    34	
    35	            cur.execute(sql)
    36	
    37	            return [
    38	                (
    39	                    row[0],
    40	                    int(row[1] or 0),
    41	                )
    42	                for row in cur.fetchall()
    43	            ]
================ SEARCH DB ================
     1	import psycopg2
     2	
     3	from nicegui import ui
     4	
     5	from app.web.state import STATE
     6	
     7	
     8	# ============================================================
     9	# POSTGRESQL
    10	# ============================================================
    11	
    12	PG_CONFIG = {
    13	    "host": "localhost",
    14	    "port": 5432,
    15	    "dbname": "photobase",
    16	    "user": "lora",
    17	}
    18	
    19	
    20	def search_database(query: str) -> list[dict]:
    21	    """
    22	    Поиск фотографий только по данным Qwen в PostgreSQL.
    23	
    24	    DINO / fingerprint здесь НЕ используется.
    25	
    26	    Ищем по:
    27	        filename
    28	        address
    29	        client
    30	        brand
    31	        category
    32	        description
    33	        text_json
    34	        colors_json
    35	        objects_json
    36	        environment_json
    37	        camera_view_json
    38	        scene_objects_json
    39	    """
    40	
    41	    query = (query or "").strip()
    42	
    43	    if not query:
    44	        return []
    45	
    46	    pattern = f"%{query}%"
    47	
    48	    sql = """
    49	        SELECT
    50	            id,
    51	            address,
    52	            filename,
    53	            path,
    54	            client,
    55	            brand,
    56	            category,
    57	            description,
    58	            confidence,
    59	            qwen_status,
    60	            qwen_time_sec,
    61	            text_json,
    62	            colors_json,
    63	            objects_json,
    64	            environment_json,
    65	            image_quality_json,
    66	            camera_view_json,
    67	            scene_objects_json,
    68	            analysis_quality_json,
    69	            raw_json,
    70	            imported_at
    71	        FROM photos
    72	        WHERE
    73	            filename ILIKE %s
    74	            OR address ILIKE %s
    75	            OR client ILIKE %s
    76	            OR brand ILIKE %s
    77	            OR category ILIKE %s
    78	            OR description ILIKE %s
    79	            OR text_json::text ILIKE %s
    80	            OR colors_json::text ILIKE %s
    81	            OR objects_json::text ILIKE %s
    82	            OR environment_json::text ILIKE %s
    83	            OR camera_view_json::text ILIKE %s
    84	            OR scene_objects_json::text ILIKE %s
    85	        ORDER BY id DESC
    86	    """
    87	
    88	    params = (pattern,) * 12
    89	
    90	    with psycopg2.connect(**PG_CONFIG) as conn:
    91	        with conn.cursor() as cur:
    92	
    93	            cur.execute(sql, params)
    94	
    95	            columns = [
    96	                desc[0]
    97	                for desc in cur.description
    98	            ]
    99	
   100	            rows = cur.fetchall()
   101	
   102	    return [
   103	        dict(zip(columns, row))
   104	        for row in rows
   105	    ]
   106	
   107	
   108	def run_search(query: str):
   109	    query = (query or "").strip()
   110	
   111	    STATE.search_query = query
   112	
   113	    if query:
   114	
   115	        try:
   116	            STATE.search_results = search_database(
   117	                query
   118	            )
   119	
   120	            count = len(
   121	                STATE.search_results
   122	            )
   123	
   124	            ui.notify(
   125	                f"Найдено: {count}",
   126	                type=(
   127	                    "positive"
   128	                    if count
   129	                    else "warning"
   130	                ),
   131	            )
   132	
   133	        except Exception as exc:
   134	
   135	            STATE.search_results = []
   136	
   137	            print(
   138	                "[PostgreSQL search ERROR]",
   139	                repr(exc),
   140	            )
   141	
   142	            ui.notify(
   143	                f"Ошибка поиска PostgreSQL: {exc}",
   144	                type="negative",
   145	            )
   146	
   147	    else:
   148	
   149	        STATE.search_results = []
   150	
   151	        ui.notify(
   152	            "Поиск очищен",
   153	            type="info",
   154	        )
   155	
   156	    if STATE.refresh_photos:
   157	        STATE.refresh_photos()
   158	
   159	
   160	def upload_photo():
   161	    ui.notify(
   162	        "Загрузка фотографий будет подключена "
   163	        "следующим этапом",
   164	        type="info",
   165	    )
   166	
   167	
   168	def build_search():
   169	
   170	    with ui.row().classes(
   171	        "w-full items-center gap-2 px-3 py-0"
   172	    ).style(
   173	        """
   174	        margin:0;
   175	        padding-top:0;
   176	        padding-bottom:0;
   177	        """
   178	    ):
   179	
   180	        search = ui.input(
================ STATE ================
     1	from dataclasses import dataclass, field
     2	from pathlib import Path
     3	from datetime import datetime
     4	
     5	
     6	@dataclass
     7	class Photo:
     8	    path: Path
     9	    selected: bool = False
    10	    db_record: dict | None = None
    11	
    12	
    13	@dataclass
    14	class Collection:
    15	    # Название подборки
    16	    name: str
    17	
    18	    # Владелец/тип подборки:
    19	    # "Моя" или "Клиентская"
    20	    kind: str = "Моя"
    21	
    22	    # Для клиентской подборки можно указать клиента.
    23	    client: str = ""
    24	
    25	    # Что хранит подборка:
    26	    # "addresses" — адреса
    27	    # "clients"   — клиенты
    28	    scope: str = "addresses"
    29	
    30	    # Сохранённые элементы подборки.
    31	    # Здесь лежат именно значения checkbox:
    32	    # {"78", "79", "83"} или
    33	    # {"Яндекс", "Сбер"}
    34	    members: set[str] = field(default_factory=set)
    35	
    36	
    37	@dataclass
    38	class AppState:
    39	    manager: str = ""
    40	    user_id: int | None = None
    41	
    42	    dark_mode: bool = False
    43	
    44	    clients: list[str] = field(default_factory=lambda: [
    45	        "Все клиенты",
    46	        "Единая Россия",
    47	        "Яндекс",
    48	        "Самокат",
    49	        "Сбер",
    50	        "Ozon",
    51	        "Бетсити",
    52	        "Альбион-Тур",
    53	    ])
    54	
    55	    addresses: list[str] = field(default_factory=lambda: [
    56	        "78",
    57	        "79",
    58	        "80",
    59	        "81",
    60	        "82",
    61	        "83",
    62	        "84",
    63	        "85",
    64	        "86",
    65	        "87",
    66	        "88",
    67	        "89",
    68	        "90",
    69	        "91",
    70	        "92",
    71	        "93",
    72	        "94",
    73	        "95",
    74	    ])
    75	
    76	    collections: list[Collection] = field(default_factory=lambda: [
    77	        # Адресные подборки
    78	        Collection(
    79	            "Важное",
    80	            "Моя",
    81	            "",
    82	            "addresses",
    83	            set(),
    84	        ),
    85	        Collection(
    86	            "На согласование",
    87	            "Моя",
    88	            "",
    89	            "addresses",
    90	            set(),
    91	        ),
    92	        Collection(
    93	            "Для клиента",
    94	            "Моя",
    95	            "",
    96	            "addresses",
    97	            set(),
    98	        ),
    99	
   100	        # Клиентские подборки
   101	        Collection(
   102	            "Самокат — август",
   103	            "Клиентская",
   104	            "Самокат",
   105	            "clients",
   106	            set(),
   107	        ),
   108	        Collection(
   109	            "Яндекс — Москва",
   110	            "Клиентская",
   111	            "Яндекс",
   112	            "clients",
   113	            set(),
   114	        ),
   115	    ])
   116	
   117	    # None = все клиенты, set() = ничего не выбрано
   118	    selected_clients: set[str] | None = None
   119	    selected_addresses: set[str] = field(default_factory=set)
   120	
   121	    # ========================================================
   122	    # FILTER PRIORITY
   123	    #
   124	    # addresses = только адреса
   125	    # clients   = только клиенты
   126	    # both      = адреса + клиенты
   127	    # ========================================================
   128	
   129	    filter_priority: str = "both"
   130	
   131	    # ========================================================
   132	    # ПОДБОРКИ
   133	    # ========================================================
   134	
   135	    # Несколько выбранных подборок одновременно.
   136	    # Их элементы объединяются.
   137	    selected_collections: set[str] = field(
   138	        default_factory=set
   139	    )
   140	
   141	    # Оставляем для совместимости со старым кодом.
   142	    active_collection: Collection | None = None
   143	
   144	    # ========================================================
   145	    # ЕДИНЫЕ ФИЛЬТРЫ
   146	    # ========================================================
   147	
   148	    # ========================================================
   149	    # DATE FILTER
   150	    #
   151	    # taken  = дата съёмки EXIF
   152	    # upload = дата загрузки / создания записи в PostgreSQL
   153	    # ========================================================
   154	
   155	    date_filter_type: str = "taken"
   156	
   157	    date_from: str | None = None
   158	    date_to: str | None = None
   159	
   160	    # Старое поле оставляем временно для совместимости
   161	    # с уже существующими компонентами.
   162	    selected_period: str = field(
   163	        default_factory=lambda: datetime.now().strftime("%Y-%m")
   164	    )
   165	
   166	    # ========================================================
   167	    # TOP ACTION BAR CALLBACKS
   168	    download_selected_zip = None
   169	    download_selected_files = None
   170	    add_selected_to_collection = None
   171	
   172	    # ПОИСК
   173	    # ========================================================
   174	
   175	    search_query: str = ""
   176	    search_results: list[dict] = field(default_factory=list)
   177	
   178	    photos: list[Photo] = field(default_factory=list)
   179	    selected_photos: set[str] = field(default_factory=set)
   180	
   181	    refresh_photos: object = None
   182	
   183	
   184	STATE = AppState()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

python - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="lora",
    dbname="photobase",
)

cur = conn.cursor()

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")

print("TABLES:")
for row in cur.fetchall():
PYnn.close()w[0])
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
,

---

