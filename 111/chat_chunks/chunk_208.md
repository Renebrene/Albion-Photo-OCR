## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-20 22:01:58

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ CLIENTS UI ================" && \
nl -ba app/web/components/clients.py | sed -n '1,260p' && \
echo "================ ADDRESSES UI ================" && \
nl -ba app/web/components/addresses.py | sed -n '1,300p' && \
echo "================ PHOTO FILTERS ================" && \
grep -RniE \
'selected_clients|selected_addresses|STATE\.clients|STATE\.addresses|refresh_photos|filter_priority' \
app/web/components app/web \
--include="*.py" \
--exclude="*.bak*" \
| head -400
================ CLIENTS UI ================
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
   131	    # --------------------------------------------------------
   132	
   133	    with ui.card().classes(
   134	        "w-full h-full min-h-0"
   135	    ).style(
   136	        "display:flex;"
   137	        "flex-direction:column;"
   138	        "overflow:hidden;"
   139	    ):
   140	
   141	        ui.label(
   142	            "Клиенты"
   143	        ).classes(
   144	            "text-lg font-bold"
   145	        )
   146	
   147	        ui.separator()
   148	
   149	        # ----------------------------------------------------
   150	        # CONTROLS
   151	        # ----------------------------------------------------
   152	
   153	        with ui.row().classes(
   154	            "w-full items-center justify-between "
   155	            "px-1 py-1 gap-1"
   156	        ):
   157	
   158	            ui.label(
   159	                "Выбор клиентов"
   160	            ).classes(
   161	                "text-sm font-medium"
   162	            )
   163	
   164	            with ui.row().classes(
   165	                "items-center gap-1"
   166	            ):
   167	
   168	                ui.button(
   169	                    "Все",
   170	                    icon="done_all",
   171	                    on_click=select_all_clients,
   172	                ).props(
   173	                    "flat dense"
   174	                )
   175	
   176	                ui.button(
   177	                    "Снять",
   178	                    icon="remove_done",
   179	                    on_click=clear_clients,
   180	                ).props(
   181	                    "flat dense"
   182	                )
   183	
   184	        ui.separator()
   185	
   186	        # ----------------------------------------------------
   187	        # CLIENT LIST
   188	        # ----------------------------------------------------
   189	
   190	        with ui.column().classes(
   191	            "w-full flex-1 min-h-0"
   192	        ).style(
   193	            "overflow-y:auto;"
   194	        ):
   195	
   196	            for name, address_count in clients:
   197	
   198	                with ui.row().classes(
   199	                    "w-full items-center gap-1 px-1 py-1"
   200	                ):
   201	
   202	                    checkbox = ui.checkbox(
   203	                        value=(
   204	                            STATE.selected_clients is None
   205	                            or name in STATE.selected_clients
   206	                        ),
   207	                        on_change=lambda e, n=name:
   208	                            select_client(e, n),
   209	                    ).props(
   210	                        "dense"
   211	                    )
   212	
   213	                    client_checkboxes[name] = checkbox
   214	
   215	                    ui.label(
   216	                        name
   217	                    ).classes(
   218	                        "cursor-pointer flex-grow"
   219	                    ).on(
   220	                        "click",
   221	                        lambda e, n=name, cb=checkbox:
   222	                            toggle_client(n, cb),
   223	                    )
   224	
   225	                    ui.label(
   226	                        f"({address_count})"
   227	                    ).classes(
   228	                        "text-xs text-grey-6"
   229	                    )
   230	
   231	        build_collections("clients")
================ ADDRESSES UI ================
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
   231	
   232	                    refresh_photos()
   233	
   234	                with ui.row().classes(
   235	                    "w-full items-center "
   236	                    "justify-between"
   237	                ):
   238	
   239	                    checkbox = ui.checkbox(
   240	                        value=(
   241	                            address
   242	                            in STATE.selected_addresses
   243	                        ),
   244	                        on_change=change_address,
   245	                    ).props(
   246	                        "dense"
   247	                    ).classes(
   248	                        "cursor-pointer"
   249	                    )
   250	
   251	                    address_checkboxes[
   252	                        address
   253	                    ] = checkbox
   254	
   255	                    ui.label(
   256	                        str(address)
   257	                    ).classes(
   258	                        "cursor-pointer flex-grow"
   259	                    ).on(
   260	                        "click",
   261	                        lambda e, a=address, cb=checkbox:
   262	                            toggle_address(a, cb),
   263	                    )
   264	
   265	                    ui.label(
   266	                        str(count)
   267	                    ).classes(
   268	                        "text-xs text-grey-6 mr-1"
   269	                    )
   270	
================ PHOTO FILTERS ================
app/web/components/filter_bar.py:7:    if getattr(STATE, "refresh_photos", None):
app/web/components/filter_bar.py:8:        STATE.refresh_photos()
app/web/components/photos_before_cache_20260816_145128.py:22:    for address in STATE.addresses:
app/web/components/photos_before_cache_20260816_145128.py:49:    selected = STATE.selected_addresses
app/web/components/photos_before_cache_20260816_145128.py:360:    def refresh_photos():
app/web/components/photos_before_cache_20260816_145128.py:363:    return refresh_photos
app/web/components/search.py:156:    if STATE.refresh_photos:
app/web/components/search.py:157:        STATE.refresh_photos()
app/web/components/filters.py:7:def build_filters(refresh_photos):
app/web/components/filters.py:67:        refresh_photos()
app/web/components/filters.py:78:        refresh_photos()
app/web/components/filters.py:89:        refresh_photos()
app/web/components/addresses.py:51:def build_addresses(refresh_photos):
app/web/components/addresses.py:102:                    STATE.selected_addresses
app/web/components/addresses.py:114:                STATE.selected_addresses = set(
app/web/components/addresses.py:116:                    for address in STATE.addresses
app/web/components/addresses.py:127:                refresh_photos()
app/web/components/addresses.py:131:                STATE.selected_addresses.clear()
app/web/components/addresses.py:140:                refresh_photos()
app/web/components/addresses.py:196:            for address in STATE.addresses:
app/web/components/addresses.py:212:                        STATE.selected_addresses.add(
app/web/components/addresses.py:218:                        STATE.selected_addresses.discard(
app/web/components/addresses.py:227:                            STATE.selected_addresses
app/web/components/addresses.py:232:                    refresh_photos()
app/web/components/addresses.py:242:                            in STATE.selected_addresses
app/web/components/header.py:53:    STATE.selected_addresses = {
app/web/components/header.py:55:        for address in STATE.addresses
app/web/components/header.py:66:        "addresses=", sorted(STATE.selected_addresses),
app/web/components/photos.py:421:    STATE.addresses = addresses
app/web/components/photos.py:425:    STATE.selected_addresses.intersection_update(
app/web/components/photos.py:426:        STATE.addresses
app/web/components/photos.py:432:        len(STATE.addresses),
app/web/components/photos.py:443:        STATE.addresses,
app/web/components/photos.py:458:    for address in STATE.addresses:
app/web/components/photos.py:499:        if STATE.selected_addresses:
app/web/components/photos.py:504:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py:671:        filter_priority = getattr(
app/web/components/photos.py:673:            "filter_priority",
app/web/components/photos.py:681:        if filter_priority in (
app/web/components/photos.py:686:            selected_addresses = STATE.selected_addresses
app/web/components/photos.py:689:            if selected_addresses is None:
app/web/components/photos.py:694:            elif not selected_addresses:
app/web/components/photos.py:702:                for address in STATE.addresses:
app/web/components/photos.py:704:                    if address not in selected_addresses:
app/web/components/photos.py:747:    filter_priority = getattr(
app/web/components/photos.py:749:        "filter_priority",
app/web/components/photos.py:753:    if filter_priority not in (
app/web/components/photos.py:759:    selected_clients = STATE.selected_clients
app/web/components/photos.py:762:    if selected_clients is None:
app/web/components/photos.py:766:    if not selected_clients:
app/web/components/photos.py:771:        for client in selected_clients
app/web/components/photos.py:1820:    def refresh_photos():
app/web/components/photos.py:1827:            "selected_addresses=",
app/web/components/photos.py:1828:            STATE.selected_addresses,
app/web/components/photos.py:1853:    STATE.refresh_photos = refresh_photos
app/web/components/photos.py:1855:    return refresh_photos
app/web/components/clients.py:8:def build_clients_panel(refresh_photos):
app/web/components/clients.py:39:        STATE.selected_clients = None
app/web/components/clients.py:49:        refresh_photos()
app/web/components/clients.py:53:        STATE.selected_clients = set()
app/web/components/clients.py:63:        refresh_photos()
app/web/components/clients.py:76:        if STATE.selected_clients is None:
app/web/components/clients.py:78:            STATE.selected_clients = set(
app/web/components/clients.py:87:            STATE.selected_clients.add(name)
app/web/components/clients.py:89:            STATE.selected_clients.discard(name)
app/web/components/clients.py:96:        if STATE.selected_clients == all_clients:
app/web/components/clients.py:97:            STATE.selected_clients = None
app/web/components/clients.py:104:            "STATE.selected_clients=",
app/web/components/clients.py:105:            repr(STATE.selected_clients),
app/web/components/clients.py:109:        refresh_photos()
app/web/components/clients.py:204:                            STATE.selected_clients is None
app/web/components/clients.py:205:                            or name in STATE.selected_clients
app/web/components/filter_bar.py:7:    if getattr(STATE, "refresh_photos", None):
app/web/components/filter_bar.py:8:        STATE.refresh_photos()
app/web/components/photos_before_cache_20260816_145128.py:22:    for address in STATE.addresses:
app/web/components/photos_before_cache_20260816_145128.py:49:    selected = STATE.selected_addresses
app/web/components/photos_before_cache_20260816_145128.py:360:    def refresh_photos():
app/web/components/photos_before_cache_20260816_145128.py:363:    return refresh_photos
app/web/components/search.py:156:    if STATE.refresh_photos:
app/web/components/search.py:157:        STATE.refresh_photos()
app/web/components/filters.py:7:def build_filters(refresh_photos):
app/web/components/filters.py:67:        refresh_photos()
app/web/components/filters.py:78:        refresh_photos()
app/web/components/filters.py:89:        refresh_photos()
app/web/components/addresses.py:51:def build_addresses(refresh_photos):
app/web/components/addresses.py:102:                    STATE.selected_addresses
app/web/components/addresses.py:114:                STATE.selected_addresses = set(
app/web/components/addresses.py:116:                    for address in STATE.addresses
app/web/components/addresses.py:127:                refresh_photos()
app/web/components/addresses.py:131:                STATE.selected_addresses.clear()
app/web/components/addresses.py:140:                refresh_photos()
app/web/components/addresses.py:196:            for address in STATE.addresses:
app/web/components/addresses.py:212:                        STATE.selected_addresses.add(
app/web/components/addresses.py:218:                        STATE.selected_addresses.discard(
app/web/components/addresses.py:227:                            STATE.selected_addresses
app/web/components/addresses.py:232:                    refresh_photos()
app/web/components/addresses.py:242:                            in STATE.selected_addresses
app/web/components/header.py:53:    STATE.selected_addresses = {
app/web/components/header.py:55:        for address in STATE.addresses
app/web/components/header.py:66:        "addresses=", sorted(STATE.selected_addresses),
app/web/components/photos.py:421:    STATE.addresses = addresses
app/web/components/photos.py:425:    STATE.selected_addresses.intersection_update(
app/web/components/photos.py:426:        STATE.addresses
app/web/components/photos.py:432:        len(STATE.addresses),
app/web/components/photos.py:443:        STATE.addresses,
app/web/components/photos.py:458:    for address in STATE.addresses:
app/web/components/photos.py:499:        if STATE.selected_addresses:
app/web/components/photos.py:504:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py:671:        filter_priority = getattr(
app/web/components/photos.py:673:            "filter_priority",
app/web/components/photos.py:681:        if filter_priority in (
app/web/components/photos.py:686:            selected_addresses = STATE.selected_addresses
app/web/components/photos.py:689:            if selected_addresses is None:
app/web/components/photos.py:694:            elif not selected_addresses:
app/web/components/photos.py:702:                for address in STATE.addresses:
app/web/components/photos.py:704:                    if address not in selected_addresses:
app/web/components/photos.py:747:    filter_priority = getattr(
app/web/components/photos.py:749:        "filter_priority",
app/web/components/photos.py:753:    if filter_priority not in (
app/web/components/photos.py:759:    selected_clients = STATE.selected_clients
app/web/components/photos.py:762:    if selected_clients is None:
app/web/components/photos.py:766:    if not selected_clients:
app/web/components/photos.py:771:        for client in selected_clients
app/web/components/photos.py:1820:    def refresh_photos():
app/web/components/photos.py:1827:            "selected_addresses=",
app/web/components/photos.py:1828:            STATE.selected_addresses,
app/web/components/photos.py:1853:    STATE.refresh_photos = refresh_photos
app/web/components/photos.py:1855:    return refresh_photos
app/web/components/clients.py:8:def build_clients_panel(refresh_photos):
app/web/components/clients.py:39:        STATE.selected_clients = None
app/web/components/clients.py:49:        refresh_photos()
app/web/components/clients.py:53:        STATE.selected_clients = set()
app/web/components/clients.py:63:        refresh_photos()
app/web/components/clients.py:76:        if STATE.selected_clients is None:
app/web/components/clients.py:78:            STATE.selected_clients = set(
app/web/components/clients.py:87:            STATE.selected_clients.add(name)
app/web/components/clients.py:89:            STATE.selected_clients.discard(name)
app/web/components/clients.py:96:        if STATE.selected_clients == all_clients:
app/web/components/clients.py:97:            STATE.selected_clients = None
app/web/components/clients.py:104:            "STATE.selected_clients=",
app/web/components/clients.py:105:            repr(STATE.selected_clients),
app/web/components/clients.py:109:        refresh_photos()
app/web/components/clients.py:204:                            STATE.selected_clients is None
app/web/components/clients.py:205:                            or name in STATE.selected_clients
app/web/main.py:357:                        STATE.refresh_photos()
app/web/main.py:358:                        if STATE.refresh_photos
app/web/main.py:378:                refresh_photos = build_photos()
app/web/main.py:380:                STATE.refresh_photos = refresh_photos
app/web/main.py:399:                        STATE.refresh_photos()
app/web/main.py:400:                        if STATE.refresh_photos
app/web/state.py:118:    selected_clients: set[str] | None = None
app/web/state.py:119:    selected_addresses: set[str] = field(default_factory=set)
app/web/state.py:129:    filter_priority: str = "both"
app/web/state.py:181:    refresh_photos: object = None
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:02:00

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed Albion photobase state, addresses, client IDs, and photo selections**
>
> 
>
> Worked for 9s

Да. Сейчас база уже подготовлена правильно: **адреса, клиенты, подборки и персональные состояния чекбоксов вынесены в отдельные сущности**.

Следующий шаг я бы делал **не через переписывание всего `photos.py`**, а аккуратно поверх существующей логики.

### Что фиксируем

**Адрес:**
- `address_directory.id` = постоянный локальный номер fingerprint: `78`, `79`, …, далее до `100+`.
- `simple_address` — то, что показываем слева/справа в UI и в гриде.
- `legal_address` — полное юридическое название, показываемое в превью.
- `fingerprint_addresses` связывает `78_v33` → `78`.

**Клиент:**
- `client_directory.id` — постоянный ID клиента.
- `name` — нормализованное основное имя.
- `simple_name` — короткое имя для UI.
- `client_aliases` — варианты написания/OCR/старые названия.
- `photos.client_normalized` хранит нормализованного клиента.

**Менеджер:**
- `manager_selections` — текущее состояние чекбоксов конкретного менеджера.
- `collections` + `collection_members` — сохранённые подборки.

И главное: **в UI больше не надо использовать название клиента как идентификатор**. Только `client_id`. Аналогично адрес — только `address_id`.

---

### Следующий конкретный этап

Нам нужно сделать слой:

```text
PostgreSQL
   ↓
directory
   ↓
STATE
   ↓
UI checkbox
   ↓
refresh_photos()
   ↓
GRID
```

То есть:

```text
client_id  → simple_name
address_id → simple_address
```

а не:

```text
"name" → фильтр
"78_v33" → отображение
```

При этом существующий DINO/hybrid **не трогаем**. Он продолжает работать со своими:

```text
78_v33
79_v33
...
hybrid_final_id
```

А UI получает человекочитаемое представление через справочники.

---

### И отдельно важный момент

Текущая ошибка:

```text
ORDER BY LOWER(1)
```

возникает потому, что PostgreSQL воспринимает `1` в `ORDER BY` как **номер столбца результата**, а не как строковое значение. Поэтому для клиентов нельзя делать:

```sql
ORDER BY LOWER(1)
```

нужно сортировать непосредственно поле:

```sql
ORDER BY LOWER(TRIM(name))
```

или, после перехода на справочник:

```sql
ORDER BY LOWER(TRIM(simple_name))
```

---

Я предлагаю сейчас сделать **один следующий шаг**: подключить `address_directory` и `client_directory` к существующим `addresses.py` и `clients.py`, **не меняя пока внешний вид**, но перевести внутреннее состояние чекбоксов на ID. После этого уже подключим `manager_selections`, чтобы каждый менеджер автоматически получал своё состояние чекбоксов и оно восстанавливалось после входа.

---

### 👤 **User** — 2026-08-20 22:02:49

да

---

### 🤖 **Assistant** — 2026-08-20 22:02:51

> **Remembering**
>
>
> **Connected Albion directories to models and preserved checkbox identifiers**
>
> 
>
> Worked for 5s

Да. Делаем именно этот этап: **справочники → STATE → чекбоксы → грид**, внешний вид пока не меняем, DINO/Hybrid не трогаем.

Сначала посмотрим текущие `state.py`, `client_db.py` и весь `clients.py`/`addresses.py`, чтобы заменить идентификаторы без побочных изменений.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \

echo "================ STATE ================" && \
nl -ba app/web/state.py | sed -n '1,230p' && \

echo "================ CLIENT DB ================" && \
nl -ba app/web/client_db.py | sed -n '1,300p' && \

echo "================ CLIENTS ================" && \
nl -ba app/web/components/clients.py | sed -n '1,280p' && \

echo "================ ADDRESSES ================" && \
nl -ba app/web/components/addresses.py | sed -n '1,310p'
```

**После этого я дам точечный patch.**

Целевая схема будет такая:

```text
ADDRESS
78
 ├─ simple_address = Комарова, 13
 └─ legal_address  = бул. Комарова, 13 В / пр. Космонавтов, сторона Б

CLIENT
17
 ├─ name        = нормализованное имя
 └─ simple_name = короткое имя
```

В `STATE`:

```text
selected_addresses = {78, 79, ...}
selected_clients   = {17, 23, ...}
```

а не:

```text
selected_addresses = {"78"}
selected_clients   = {"Самокат"}
```

При этом существующая фотография может продолжать содержать:

```text
address_id = "85_v33"
```

и DINO/Hybrid остаются как есть.

Для UI сделаем преобразование:

```text
address_id 78 → «Комарова, 13»
client_id 17  → «Самокат»
```

И уже следующим этапом эти же `address_id/client_id` запишем в `manager_selections`, чтобы состояние чекбоксов было **индивидуальным для каждого менеджера** и восстанавливалось после входа.

---

### 👤 **User** — 2026-08-20 22:03:25

int_mvp_v02 && \

echo "================ STATE ================" && \
nl -ba app/web/state.py | sed -n '1,230p' && \

echo "================ CLIENT DB ================" && \
nl -ba app/web/client_db.py | sed -n '1,300p' && \

echo "================ CLIENTS ================" && \
nl -ba app/web/components/clients.py | sed -n '1,280p' && \

echo "================ ADDRESSES ================" && \
nl -ba app/web/components/addresses.py | sed -n '1,310p'
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
   131	    # --------------------------------------------------------
   132	
   133	    with ui.card().classes(
   134	        "w-full h-full min-h-0"
   135	    ).style(
   136	        "display:flex;"
   137	        "flex-direction:column;"
   138	        "overflow:hidden;"
   139	    ):
   140	
   141	        ui.label(
   142	            "Клиенты"
   143	        ).classes(
   144	            "text-lg font-bold"
   145	        )
   146	
   147	        ui.separator()
   148	
   149	        # ----------------------------------------------------
   150	        # CONTROLS
   151	        # ----------------------------------------------------
   152	
   153	        with ui.row().classes(
   154	            "w-full items-center justify-between "
   155	            "px-1 py-1 gap-1"
   156	        ):
   157	
   158	            ui.label(
   159	                "Выбор клиентов"
   160	            ).classes(
   161	                "text-sm font-medium"
   162	            )
   163	
   164	            with ui.row().classes(
   165	                "items-center gap-1"
   166	            ):
   167	
   168	                ui.button(
   169	                    "Все",
   170	                    icon="done_all",
   171	                    on_click=select_all_clients,
   172	                ).props(
   173	                    "flat dense"
   174	                )
   175	
   176	                ui.button(
   177	                    "Снять",
   178	                    icon="remove_done",
   179	                    on_click=clear_clients,
   180	                ).props(
   181	                    "flat dense"
   182	                )
   183	
   184	        ui.separator()
   185	
   186	        # ----------------------------------------------------
   187	        # CLIENT LIST
   188	        # ----------------------------------------------------
   189	
   190	        with ui.column().classes(
   191	            "w-full flex-1 min-h-0"
   192	        ).style(
   193	            "overflow-y:auto;"
   194	        ):
   195	
   196	            for name, address_count in clients:
   197	
   198	                with ui.row().classes(
   199	                    "w-full items-center gap-1 px-1 py-1"
   200	                ):
   201	
   202	                    checkbox = ui.checkbox(
   203	                        value=(
   204	                            STATE.selected_clients is None
   205	                            or name in STATE.selected_clients
   206	                        ),
   207	                        on_change=lambda e, n=name:
   208	                            select_client(e, n),
   209	                    ).props(
   210	                        "dense"
   211	                    )
   212	
   213	                    client_checkboxes[name] = checkbox
   214	
   215	                    ui.label(
   216	                        name
   217	                    ).classes(
   218	                        "cursor-pointer flex-grow"
   219	                    ).on(
   220	                        "click",
   221	                        lambda e, n=name, cb=checkbox:
   222	                            toggle_client(n, cb),
   223	                    )
   224	
   225	                    ui.label(
   226	                        f"({address_count})"
   227	                    ).classes(
   228	                        "text-xs text-grey-6"
   229	                    )
   230	
   231	        build_collections("clients")
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
   231	
   232	                    refresh_photos()
   233	
   234	                with ui.row().classes(
   235	                    "w-full items-center "
   236	                    "justify-between"
   237	                ):
   238	
   239	                    checkbox = ui.checkbox(
   240	                        value=(
   241	                            address
   242	                            in STATE.selected_addresses
   243	                        ),
   244	                        on_change=change_address,
   245	                    ).props(
   246	                        "dense"
   247	                    ).classes(
   248	                        "cursor-pointer"
   249	                    )
   250	
   251	                    address_checkboxes[
   252	                        address
   253	                    ] = checkbox
   254	
   255	                    ui.label(
   256	                        str(address)
   257	                    ).classes(
   258	                        "cursor-pointer flex-grow"
   259	                    ).on(
   260	                        "click",
   261	                        lambda e, a=address, cb=checkbox:
   262	                            toggle_address(a, cb),
   263	                    )
   264	
   265	                    ui.label(
   266	                        str(count)
   267	                    ).classes(
   268	                        "text-xs text-grey-6 mr-1"
   269	                    )
   270	
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:03:26

> **Remembering**
>
>
> ****
>
> 
>
> **Continued Albion PhotoBase architecture with preserved descriptions and unified normalization**
>
> 
>
> Worked for 6s

Да. Теперь картина уже достаточно полная, и я бы **не переделывал текущие `clients.py` / `addresses.py` радикально**. Следующий шаг - правильно связать UI со справочниками и нормализованными значениями.

### Что сейчас уже есть

**Адреса:**

- `address_directory`
  - `78 → Комарова, 13 → бул. Комарова, 13 В / пр. Космонавтов, сторона Б`
  - `79 → Комарова-Добровольского, поз.1 → ...`
- `fingerprint_addresses`
  - `78_v33 → 78`
  - `79_v33 → 79`

То есть **fingerprint ID остаётся техническим идентификатором**, а человек видит нормальное имя.

**Клиенты:**

- `client_directory`
- `client_aliases`
- `photos.client_normalized`
- индекс `idx_photos_client_normalized`

Это именно то, что нам нужно для нормализации после Qwen.

---

## Как должна работать нормализация

Я предлагаю разделить процесс на два слоя:

```text
                    Qwen
                     │
                     ▼
              photos.client
                     │
                     ▼
            НОРМАЛИЗАТОР
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   точное совпадение       известная ошибка
          │                     │
          └──────────┬──────────┘
                     ▼
          photos.client_normalized
                     │
                     ▼
              client_directory
```

Например:

```text
Qwen написал:

"Яндекс"
"яндекс"
"Yandex"
"Яндеск"
"Яндeкс"
"Яндекс, ООО"

                ↓

        client_normalized

                ↓

             Яндекс
```

При этом **исходное `client` никогда не трогаем**.

Это важно: всегда можно посмотреть, что именно написал Qwen.

---

# Для адресов ещё лучше

Адрес **вообще не должен нормализоваться из текста Qwen**.

У нас источник адреса:

```text
DINO / fingerprint
        ↓
    78_v33
        ↓
fingerprint_addresses
        ↓
        78
        ↓
address_directory
        ↓
Комарова, 13
```

Поэтому здесь нормализация фактически является **справочником отображения**.

То есть:

```text
technical / Слепки

78_v33
   ↓
ID адреса: 78
   ↓
Упрощённый:
Комарова, 13
   ↓
Юридический:
бул. Комарова, 13 В / пр. Космонавтов, сторона Б
```

И именно это потом используется в гриде.

---

# Что я предлагаю сделать сейчас

Не трогать пока фильтры.

Сначала сделать **единый backend-слой справочников**:

```text
app/web/directory_db.py
```

В нём:

```python
get_address_directory()
get_address_by_fingerprint()
get_address_name()
get_address_legal()
get_clients()
get_client_normalized()
```

И отдельно:

```python
normalize_client(raw_client)
```

Логика будет примерно такая:

```text
photos.client
       │
       ├── найден exact alias ──────► client_id
       │
       ├── найдено точное имя ──────► client_id
       │
       └── не найдено ──────────────► оставить NULL
                                     
                                     ↓
                           не угадывать автоматически
```

Это принципиально важно.

**На первом этапе не надо делать "умную" нечёткую нормализацию.**  
Иначе `"Сбер"` можно случайно превратить во что-нибудь похожее.

Сначала:

1. exact match;
2. alias match;
3. ручное добавление alias;
4. потом, когда накопится база ошибок, можно добавить автоматическую обработку очевидных OCR-ошибок.

---

## А UI сделаем уже поверх этого

Слева:

```text
┌─────────────────────┐
│ Клиенты             │
│                     │
│ ☑ Яндекс       (42) │
│ ☑ Сбер         (31) │
│ ☐ Самокат      (18) │
│ ☐ Ozon          (9) │
└─────────────────────┘
```

Грид:

```text
┌───────────────────────────────────────────────┐
│                    ФОТО                       │
│                                               │
│  [photo] [photo] [photo] [photo]              │
│  [photo] [photo] [photo] [photo]              │
└───────────────────────────────────────────────┘
```

Справа:

```text
┌────────────────────────────┐
│ Адреса                     │
│                            │
│ ☑ Комарова, 13        (..) │
│ ☑ Комарова-Добровольского │
│ ☐ ...                      │
└────────────────────────────┘
```

А внутри фильтра **не должно быть больше зависимости от строк `78`, `79` как отображаемых названий**.

Технически:

```text
address_id = 78
```

а UI:

```text
Комарова, 13
```

---

### И главное

Текущий `photos.py` сейчас фильтрует адреса по:

```python
db_address
```

и клиентов по:

```python
client
```

Нам нужно постепенно перевести его на:

```python
address_id
        +
client_normalized
```

То есть получится:

```text
              PHOTO
                │
       ┌────────┴─────────┐
       ▼                  ▼
   address_id       client_normalized
       │                  │
       ▼                  ▼
address_directory   client_directory
       │                  │
       ▼                  ▼
  отображение        отображение
```

**Qwen при этом остаётся только источником `client` и описания. Адреса Qwen не определяет.**

Это архитектурно чистый вариант и позволит потом спокойно написать backend нормализации, не ломая нынешний пайплайн.

---

### 👤 **User** — 2026-08-20 22:03:59

далее

---

### 🤖 **Assistant** — 2026-08-20 22:04:00

Да. Следующий шаг — **не менять UI**, а сначала сделать backend справочников и проверить его на текущих данных.

### Шаг 1. Создаём `directory_db.py`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > app/web/directory_db.py <<'PY'
import psycopg2

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

# ============================================================
# АДРЕСА
# ============================================================

def get_address_directory():
    """
    Возвращает справочник адресов.

    {
        78: {
            "simple": "Комарова, 13",
            "legal": "...",
        },
        ...
    }
    """

    sql = """
        SELECT
            id,
            simple_address,
            legal_address
        FROM address_directory
        WHERE active = TRUE
        ORDER BY sort_order, id
    """

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)

            return {
                int(row[0]): {
                    "simple": row[1] or "",
                    "legal": row[2] or "",
                }
                for row in cur.fetchall()
            }

def get_address_by_fingerprint(fingerprint_id):
    """
    Возвращает address_id для fingerprint.

    Например:

        78_v33 -> 78
    """

    sql = """
        SELECT address_id
        FROM fingerprint_addresses
        WHERE fingerprint_id = %s
          AND active = TRUE
        LIMIT 1
    """

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (fingerprint_id,))
            row = cur.fetchone()

            if row is None:
                return None

            return int(row[0])

def get_address_for_fingerprint(fingerprint_id):
    """
    Полная информация об адресе fingerprint.
    """

    address_id = get_address_by_fingerprint(
        fingerprint_id
    )

    if address_id is None:
        return None

    directory = get_address_directory()

    data = directory.get(address_id)

    if data is None:
        return None

    return {
        "id": address_id,
        "simple": data["simple"],
        "legal": data["legal"],
    }

# ============================================================
# КЛИЕНТЫ
# ============================================================

def get_clients():
    """
    Возвращает нормализованный справочник клиентов.
    """

    sql = """
        SELECT
            id,
            name,
            simple_name
        FROM client_directory
        WHERE active = TRUE
        ORDER BY sort_order, LOWER(name)
    """

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)

            return [
                {
                    "id": int(row[0]),
                    "name": row[1] or "",
                    "simple": row[2] or "",
                }
                for row in cur.fetchall()
            ]

def normalize_client(raw_client):
    """
    Возвращает client_id по точному имени
    или зарегистрированному alias.

    Никакого fuzzy matching здесь пока нет.
    """

    if not raw_client:
        return None

    raw = raw_client.strip()

    if not raw:
        return None

    sql = """
        SELECT id
        FROM client_directory
        WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))

        UNION

        SELECT client_id
        FROM client_aliases
        WHERE LOWER(TRIM(raw_name)) = LOWER(TRIM(%s))

        LIMIT 1
    """

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (raw, raw),
            )

            row = cur.fetchone()

            if row is None:
                return None

            return int(row[0])

def get_client_name(client_id):
    """
    Возвращает отображаемое имя клиента.
    """

    if client_id is None:
        return None

    sql = """
        SELECT
            COALESCE(NULLIF(TRIM(simple_name), ''), name)
        FROM client_directory
        WHERE id = %s
          AND active = TRUE
        LIMIT 1
    """

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (client_id,))
            row = cur.fetchone()

            return row[0] if row else None

print(
    "[DIRECTORY DB] loaded",
    flush=True,
)
PY

python -m py_compile app/web/directory_db.py && \
echo "======================================================================" && \
echo "DIRECTORY DB: SYNTAX OK" && \
echo "======================================================================"
```

После этого проверим его **на наших двух адресах и клиентах**, но пока ничего в `photos` не меняем.

### Шаг 2 — сразу после успешного `SYNTAX OK`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.directory_db import (
    get_address_directory,
    get_address_for_fingerprint,
    get_clients,
    normalize_client,
)

print("=" * 70)
print("ADDRESS DIRECTORY")
print("=" * 70)

for k, v in get_address_directory().items():
    print(
        k,
        "=>",
        v["simple"],
        "||",
        v["legal"],
    )

print()
print("=" * 70)
print("FINGERPRINT -> ADDRESS")
print("=" * 70)

for fp in ("78_v33", "79_v33", "85_v33"):
    print(
        fp,
        "=>",
        get_address_for_fingerprint(fp),
        "=>",
        get_address_for_fingerprint(fp)
        and get_address_for_fingerprint(fp)
    )

print()
print("=" * 70)
print("CLIENT DIRECTORY")
print("=" * 70)

for client in get_clients():
    print(client)

print()
print("=" * 70)
print("CLIENT NORMALIZATION TEST")
print("=" * 70)

for raw in (
    "Яндекс",
    "яндекс",
    "Яндеск",
    "Сбер",
    "Самокат",
    "",
):
    print(
        repr(raw),
        "=>",
        normalize_client(raw),
    )

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY
```

**Пока не подключаем это к `photos.py`.** Сначала убедимся, что слой справочников правильно возвращает данные. Затем следующим шагом подключим его к `clients.py` и `addresses.py`, а уже потом — к фильтрации грида.

---

### 👤 **User** — 2026-08-20 22:04:15

# ============================================================
# АДРЕСА
# ============================================================

def get_address_directory():
    """
    Возвращает справочник адресов.

    {
        78: {
echo "======================================================================" &&
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:04:16

Да, это не ошибка нашего файла. На системе просто нет команды `python`, есть `python3`, а в проекте мы используем `uv run`.

Но вижу важный момент: команда, судя по выводу, **записала файл, а проверка `python -m py_compile` упала**.

Давай проверим через окружение проекта.

### 1. Проверка синтаксиса

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile app/web/directory_db.py && \
echo "======================================================================" && \
echo "DIRECTORY DB: SYNTAX OK" && \
echo "======================================================================"
```

Если получишь:

```text
DIRECTORY DB: SYNTAX OK
```

идём дальше.

### 2. Затем тест самого backend

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.directory_db import (
    get_address_directory,
    get_address_for_fingerprint,
    get_clients,
    normalize_client,
)

print("=" * 70)
print("ADDRESS DIRECTORY")
print("=" * 70)

for k, v in get_address_directory().items():
    print(
        k,
        "=>",
        v["simple"],
        "||",
        v["legal"],
    )

print()
print("=" * 70)
print("FINGERPRINT -> ADDRESS")
print("=" * 70)

for fp in ("78_v33", "79_v33", "85_v33"):
    print(
        fp,
        "=>",
        get_address_for_fingerprint(fp),
        "=>",
        get_address_for_fingerprint(fp)
        and get_address_for_fingerprint(fp)
    )

print()
print("=" * 70)
print("CLIENT DIRECTORY")
print("=" * 70)

for client in get_clients():
    print(client)

print()
print("=" * 70)
print("CLIENT NORMALIZATION TEST")
print("=" * 70)

for raw in (
    "Яндекс",
    "яндекс",
    "Яндеск",
    "Сбер",
    "Самокат",
    "",
):
    print(
        repr(raw),
        "=>",
        normalize_client(raw),
    )

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY
```

**Важно:** пока ничего в `photos.py`, `clients.py` и `addresses.py` не меняем. Сначала проверяем этот слой отдельно.

---

### 👤 **User** — 2026-08-20 22:04:35

FINGERPRINT -> ADDRESS
======================================================================
Traceback (most recent call last):
  File "<stdin>", line 30, in <module>
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/directory_db.py", line 85, in get_address_for_fingerprint
    address_id = get_address_by_fingerprint(
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/directory_db.py", line 71, in get_address_by_fingerprint
    cur.execute(sql, (fingerprint_id,))
psycopg2.errors.UndefinedTable: relation "fingerprint_addresses" does not exist
LINE 3:         FROM fingerprint_addresses
                     ^

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:04:36

Да, нашли причину. **Это моя ошибка в названии таблицы.** Мы создавали связь `address ↔ fingerprint`, но нужно посмотреть её фактическое имя, а не предполагать `fingerprint_addresses`.

Сейчас **ничего не исправляем наугад**. Сначала найдём реальное имя таблицы и её структуру.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="lora",
    dbname="photobase",
)

cur = conn.cursor()

print("=" * 70)
print("TABLES WITH FINGERPRINT / ADDRESS")
print("=" * 70)

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND (
          table_name ILIKE '%fingerprint%'
          OR table_name ILIKE '%address%'
      )
    ORDER BY table_name
""")

tables = [row[0] for row in cur.fetchall()]

for name in tables:
    print(name)

print()
print("=" * 70)
print("STRUCTURES")
print("=" * 70)

for table in tables:
    print()
    print("---", table, "---")

    cur.execute("""
        SELECT
            ordinal_position,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position
    """, (table,))

    for pos, name, dtype in cur.fetchall():
        print(f"{pos:3}  {name:30} {dtype}")

cur.close()
conn.close()

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY
```

Нам особенно нужна таблица, где есть примерно:

```text
fingerprint_id
address_id
active
```

Как только увидим её реальное имя — исправим **только одну строку в `directory_db.py`**.

И ещё: `photos.address_id` пока содержит только:

```text
85_v33
```

это старое/текущее состояние и его **не будем использовать как источник справочника**. Правильная цепочка у нас должна быть:

```text
78_v33
   ↓
таблица fingerprint ↔ address
   ↓
78
   ↓
address_directory
   ↓
Комарова, 13
```

Именно её сейчас восстанавливаем.

---

### 👤 **User** — 2026-08-20 22:04:53

TABLES WITH FINGERPRINT / ADDRESS
======================================================================
address_directory
address_fingerprints

======================================================================
STRUCTURES
======================================================================

--- address_directory ---
  1  id                             integer
  2  legal_address                  text
  3  simple_address                 text
  4  active                         boolean
  5  sort_order                     integer
  6  created_at                     timestamp without time zone
  7  updated_at                     timestamp without time zone

--- address_fingerprints ---
  1  fingerprint_id                 text
  2  address_id                     integer
  3  active                         boolean
  4  created_at                     timestamp without time zone
  5  updated_at                     timestamp without time zone

======================================================================
DONE
======================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:04:55

Отлично. Всё на месте. Просто имя таблицы — **`address_fingerprints`**, а в `directory_db.py` я указал `fingerprint_addresses`.

Исправляем только это.

### 1. Замена имени таблицы

```bash id="x1y6p4"
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -i 's/FROM fingerprint_addresses/FROM address_fingerprints/' \
app/web/directory_db.py && \
uv run python -m py_compile app/web/directory_db.py && \
echo "======================================================================" && \
echo "DIRECTORY DB: SYNTAX OK" && \
echo "TABLE NAME: address_fingerprints" && \
echo "======================================================================"
```

### 2. Повторяем тест

```bash id="f5c9qv"
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.directory_db import (
    get_address_directory,
    get_address_for_fingerprint,
    get_clients,
    normalize_client,
)

print("=" * 70)
print("ADDRESS DIRECTORY")
print("=" * 70)

for k, v in get_address_directory().items():
    print(
        k,
        "=>",
        v["simple"],
        "||",
        v["legal"],
    )

print()
print("=" * 70)
print("FINGERPRINT -> ADDRESS")
print("=" * 70)

for fp in ("78_v33", "79_v33", "85_v33"):
    result = get_address_for_fingerprint(fp)
    print(fp, "=>", result)

print()
print("=" * 70)
print("CLIENT DIRECTORY")
print("=" * 70)

for client in get_clients():
    print(client)

print()
print("=" * 70)
print("CLIENT NORMALIZATION TEST")
print("=" * 70)

for raw in (
    "Яндекс",
    "яндекс",
    "Яндеск",
    "Сбер",
    "Самокат",
    "",
):
    print(
        repr(raw),
        "=>",
        normalize_client(raw),
    )

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY
```

Ожидаем принципиально:

```text
FINGERPRINT -> ADDRESS
======================================================================
78_v33 => 78
79_v33 => 79
85_v33 => None
```

Для `85_v33` `None` сейчас **правильно**, потому что соответствие для него мы ещё не задали.

После этого переходим к следующему шагу: **подключаем `address_directory` к правой панели**, чтобы вместо `78`, `79` она показывала:

```text
☑ Комарова, 13                         (N)
☑ Комарова-Добровольского, поз.1       (N)
```

а внутри всё равно работала по `address_id = 78/79`.

---

### 👤 **User** — 2026-08-20 22:05:15

======================================================================
CLIENT DIRECTORY
======================================================================

======================================================================
CLIENT NORMALIZATION TEST
======================================================================
'Яндекс' => None
'яндекс' => None
'Яндеск' => None
'Сбер' => None
'Самокат' => None
'' => None

======================================================================
DONE
======================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

