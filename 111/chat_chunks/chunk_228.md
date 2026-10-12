## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-21 00:59:33

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ FILTER UI LOCATIONS ================" && \
grep -RniE \
'selected_addresses|selected_clients|STATE\.addresses|STATE\.clients|ui\.checkbox|ui\.select|Адрес|Клиент' \
app/web \
--include="*.py" \
| head -400
================ FILTER UI LOCATIONS ================
app/web/components/photos_before_cache_20260816_145128.py:22:    for address in STATE.addresses:
app/web/components/photos_before_cache_20260816_145128.py:49:    selected = STATE.selected_addresses
app/web/components/photos_before_cache_20260816_145128.py:240:                "Фильтрация по адресам"
app/web/components/photos_before_cache_20260816_145128.py:335:                                ui.checkbox(
app/web/components/search.py:182:                "Поиск по клиенту, бренду, "
app/web/components/technical_modules/fingerprints.py:13:            "Используется для добавления новых адресов."
app/web/components/technical_modules/fingerprints.py:21:            "Адресов со слепками: 18"
app/web/components/technical_modules/data.py:278:                "Адресов",
app/web/components/technical_modules/data.py:362:                f"Адресов: {daily['addresses']}"
app/web/components/technical_modules/data.py:417:                f"Адресов: {qwen['addresses']}"
app/web/components/technical_modules/data.py:441:                "Клиенты",
app/web/components/technical_modules/data.py:446:                "Адреса",
app/web/components/technical_modules/users.py:104:                ui.checkbox(
app/web/components/technical_modules/users.py:164:                    color_select = ui.select(
app/web/components/technical_modules/users.py:278:                    color_select = ui.select(
app/web/components/technical_modules/automation.py:294:            time_select = ui.select(
app/web/components/technical_modules/qwen.py:253:            ui.label("Адресов")
app/web/components/addresses.py:62:            "Адреса"
app/web/components/addresses.py:68:            "Фильтр по адресам"
app/web/components/addresses.py:102:                    STATE.selected_addresses
app/web/components/addresses.py:114:                STATE.selected_addresses = set(
app/web/components/addresses.py:116:                    for address in STATE.addresses
app/web/components/addresses.py:131:                STATE.selected_addresses.clear()
app/web/components/addresses.py:164:            Единый обработчик клика по checkbox и названию адреса.
app/web/components/addresses.py:186:        # адреса никогда не скрываем при выборе подборки.
app/web/components/addresses.py:196:            for address in STATE.addresses:
app/web/components/addresses.py:212:                        STATE.selected_addresses.add(
app/web/components/addresses.py:218:                        STATE.selected_addresses.discard(
app/web/components/addresses.py:227:                            STATE.selected_addresses
app/web/components/addresses.py:239:                    checkbox = ui.checkbox(
app/web/components/addresses.py:242:                            in STATE.selected_addresses
app/web/components/collections.py:24:        kind = ui.select(
app/web/components/collections.py:25:            ["Моя", "Клиентская"],
app/web/components/collections.py:34:        client = ui.select(
app/web/components/collections.py:44:            label="Клиент",
app/web/components/collections.py:185:                    ui.checkbox(
app/web/components/header.py:24:      - видит все адреса;
app/web/components/header.py:53:    STATE.selected_addresses = {
app/web/components/header.py:55:        for address in STATE.addresses
app/web/components/header.py:66:        "addresses=", sorted(STATE.selected_addresses),
app/web/components/photos.py:342:        # ВИРТУАЛЬНЫЙ АДРЕС
app/web/components/photos.py:344:        # На данном этапе единственный источник адреса:
app/web/components/photos.py:362:        # ВИРТУАЛЬНЫЙ АДРЕС
app/web/components/photos.py:365:        # источником виртуального адреса.
app/web/components/photos.py:397:    # АДРЕСА
app/web/components/photos.py:431:    STATE.addresses = addresses
app/web/components/photos.py:433:    # Сбрасываем выбранные адреса,
app/web/components/photos.py:435:    STATE.selected_addresses.intersection_update(
app/web/components/photos.py:436:        STATE.addresses
app/web/components/photos.py:442:        len(STATE.addresses),
app/web/components/photos.py:453:        STATE.addresses,
app/web/components/photos.py:468:    for address in STATE.addresses:
app/web/components/photos.py:509:        if STATE.selected_addresses:
app/web/components/photos.py:514:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py:696:            selected_addresses = STATE.selected_addresses
app/web/components/photos.py:698:            # None = адресный фильтр не установлен.
app/web/components/photos.py:699:            if selected_addresses is None:
app/web/components/photos.py:704:            elif not selected_addresses:
app/web/components/photos.py:712:                for address in STATE.addresses:
app/web/components/photos.py:714:                    if address not in selected_addresses:
app/web/components/photos.py:726:            # Режим "только клиенты":
app/web/components/photos.py:727:            # адреса полностью игнорируются.
app/web/components/photos.py:769:    selected_clients = STATE.selected_clients
app/web/components/photos.py:771:    # None = все клиенты.
app/web/components/photos.py:772:    if selected_clients is None:
app/web/components/photos.py:776:    if not selected_clients:
app/web/components/photos.py:781:        for client in selected_clients
app/web/components/photos.py:946:                        ui.label("Клиент").classes(
app/web/components/photos.py:1133:    # При первом построении индекса выбираем все адреса.
app/web/components/photos.py:1142:        STATE.selected_addresses = {
app/web/components/photos.py:1152:            sorted(STATE.selected_addresses),
app/web/components/photos.py:1309:                    # из разных адресов.
app/web/components/photos.py:1669:                                    checkbox = ui.checkbox(
app/web/components/photos.py:1863:            "selected_addresses=",
app/web/components/photos.py:1864:            STATE.selected_addresses,
app/web/components/clients.py:39:        STATE.selected_clients = None
app/web/components/clients.py:53:        STATE.selected_clients = set()
app/web/components/clients.py:76:        if STATE.selected_clients is None:
app/web/components/clients.py:78:            STATE.selected_clients = set(
app/web/components/clients.py:87:            STATE.selected_clients.add(name)
app/web/components/clients.py:89:            STATE.selected_clients.discard(name)
app/web/components/clients.py:96:        if STATE.selected_clients == all_clients:
app/web/components/clients.py:97:            STATE.selected_clients = None
app/web/components/clients.py:104:            "STATE.selected_clients=",
app/web/components/clients.py:105:            repr(STATE.selected_clients),
app/web/components/clients.py:113:        Единый обработчик клика по checkbox и названию клиента.
app/web/components/clients.py:142:            "Клиенты"
app/web/components/clients.py:159:                "Выбор клиентов"
app/web/components/clients.py:202:                    checkbox = ui.checkbox(
app/web/components/clients.py:204:                            STATE.selected_clients is None
app/web/components/clients.py:205:                            or name in STATE.selected_clients
app/web/client_aliases.py:2:Реестр нормализации названий клиентов.
app/web/client_aliases.py:8:    нормальное имя -> варианты, которые считаются тем же клиентом
app/web/client_aliases.py:56:    Возвращает нормальное имя клиента.
app/web/photo_db.py:178:        # Ключ: адрес + имя файла
app/web/frontend_v02.py:27:    ("Все клиенты", "apps"),
app/web/frontend_v02.py:57:        "Избранные адреса": [
app/web/frontend_v02.py:196:current_client = {"value": "Все клиенты"}
app/web/frontend_v02.py:228:            manager_select = ui.select(
app/web/frontend_v02.py:253:            "Поиск по описанию, клиенту, адресу..."
app/web/frontend_v02.py:291:            "Клиенты"
app/web/frontend_v02.py:308:                ui.checkbox().props(
app/web/frontend_v02.py:469:            "Адреса и подборки"
app/web/frontend_v02.py:513:                                ui.checkbox().props(
app/web/frontend_v02.py:568:        ui.select(
app/web/frontend_v02.py:601:        ui.select(
app/web/frontend_v02.py:605:                "По адресу",
app/web/frontend_v02.py:606:                "По клиенту",
app/web/filters.py:16:        ui.select(
app/web/filters.py:37:        ui.select(
app/web/filters.py:40:                "Адрес",
app/web/filters.py:41:                "Клиент",
app/web/client_normalizer.py:14:    Безопасная нормализация клиента.
app/web/main.py:401:                            "Период • дата • адрес • клиент • подборка"
app/web/frontend_v01_backup_before_modular.py:16:    ("Все клиенты", "apps"),
app/web/frontend_v01_backup_before_modular.py:27:    "Все адреса",
app/web/frontend_v01_backup_before_modular.py:236:            "Введите запрос: клиент, адрес, описание, "
app/web/frontend_v01_backup_before_modular.py:281:            "Клиенты"
app/web/frontend_v01_backup_before_modular.py:291:                ui.checkbox().props(
app/web/frontend_v01_backup_before_modular.py:452:            "Адреса"
app/web/frontend_v01_backup_before_modular.py:464:                ui.checkbox().props(
app/web/frontend_v01_backup_before_modular.py:516:        ui.select(
app/web/frontend_v01_backup_before_modular.py:551:        ui.select(
app/web/frontend_v01_backup_before_modular.py:555:                "По адресу",
app/web/frontend_v01_backup_before_modular.py:556:                "По клиенту",
app/web/frontend_v01.py:16:    ("Все клиенты", "apps"),
app/web/frontend_v01.py:27:    "Все адреса",
app/web/frontend_v01.py:236:            "Введите запрос: клиент, адрес, описание, "
app/web/frontend_v01.py:281:            "Клиенты"
app/web/frontend_v01.py:291:                ui.checkbox().props(
app/web/frontend_v01.py:452:            "Адреса"
app/web/frontend_v01.py:464:                ui.checkbox().props(
app/web/frontend_v01.py:516:        ui.select(
app/web/frontend_v01.py:551:        ui.select(
app/web/frontend_v01.py:555:                "По адресу",
app/web/frontend_v01.py:556:                "По клиенту",
app/web/state.py:19:    # "Моя" или "Клиентская"
app/web/state.py:22:    # Для клиентской подборки можно указать клиента.
app/web/state.py:26:    # "addresses" — адреса
app/web/state.py:27:    # "clients"   — клиенты
app/web/state.py:45:        "Все клиенты",
app/web/state.py:77:        # Адресные подборки
app/web/state.py:93:            "Для клиента",
app/web/state.py:100:        # Клиентские подборки
app/web/state.py:103:            "Клиентская",
app/web/state.py:110:            "Клиентская",
app/web/state.py:117:    # None = все клиенты, set() = ничего не выбрано
app/web/state.py:118:    selected_clients: set[str] | None = None
app/web/state.py:119:    selected_addresses: set[str] = field(default_factory=set)
app/web/state.py:124:    # addresses = только адреса
app/web/state.py:125:    # clients   = только клиенты
app/web/state.py:126:    # both      = адреса + клиенты
app/web/client_dictionary.py:17:    Импорт справочника клиентов.
app/web/directory_db.py:13:# АДРЕСА
app/web/directory_db.py:18:    Возвращает справочник адресов.
app/web/directory_db.py:82:    Полная информация об адресе fingerprint.
app/web/directory_db.py:107:# КЛИЕНТЫ
app/web/directory_db.py:112:    Возвращает нормализованный справочник клиентов.
app/web/directory_db.py:186:    Возвращает отображаемое имя клиента.
app/web/client_db.py:14:    Возвращает клиентов из результатов Qwen.
app/web/client_db.py:17:    для которых Qwen определил клиента.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ STATE ================" && \
grep -RniE \
'class .*State|selected_addresses|selected_clients|addresses *=|clients *=' \
app/web \
--include="*.py" \
| head -250
================ STATE ================
app/web/components/photos_before_cache_20260816_145128.py:49:    selected = STATE.selected_addresses
app/web/components/technical_modules/data.py:203:    addresses = {
app/web/components/technical_modules/qwen.py:116:        addresses = {
app/web/components/technical_modules/qwen.py:470:            addresses = set()
app/web/components/addresses.py:102:                    STATE.selected_addresses
app/web/components/addresses.py:114:                STATE.selected_addresses = set(
app/web/components/addresses.py:131:                STATE.selected_addresses.clear()
app/web/components/addresses.py:212:                        STATE.selected_addresses.add(
app/web/components/addresses.py:218:                        STATE.selected_addresses.discard(
app/web/components/addresses.py:227:                            STATE.selected_addresses
app/web/components/addresses.py:242:                            in STATE.selected_addresses
app/web/components/header.py:53:    STATE.selected_addresses = {
app/web/components/header.py:66:        "addresses=", sorted(STATE.selected_addresses),
app/web/components/photos.py:400:    addresses = sorted(
app/web/components/photos.py:431:    STATE.addresses = addresses
app/web/components/photos.py:435:    STATE.selected_addresses.intersection_update(
app/web/components/photos.py:441:        "addresses=",
app/web/components/photos.py:509:        if STATE.selected_addresses:
app/web/components/photos.py:514:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py:696:            selected_addresses = STATE.selected_addresses
app/web/components/photos.py:699:            if selected_addresses is None:
app/web/components/photos.py:704:            elif not selected_addresses:
app/web/components/photos.py:714:                    if address not in selected_addresses:
app/web/components/photos.py:769:    selected_clients = STATE.selected_clients
app/web/components/photos.py:772:    if selected_clients is None:
app/web/components/photos.py:776:    if not selected_clients:
app/web/components/photos.py:781:        for client in selected_clients
app/web/components/photos.py:1142:        STATE.selected_addresses = {
app/web/components/photos.py:1152:            sorted(STATE.selected_addresses),
app/web/components/photos.py:1180:        f"addresses={len(PHOTO_INDEX)}",
app/web/components/photos.py:1863:            "selected_addresses=",
app/web/components/photos.py:1864:            STATE.selected_addresses,
app/web/components/clients.py:15:        clients = get_clients_with_address_counts()
app/web/components/clients.py:25:        clients = []
app/web/components/clients.py:39:        STATE.selected_clients = None
app/web/components/clients.py:53:        STATE.selected_clients = set()
app/web/components/clients.py:67:        all_clients = {
app/web/components/clients.py:76:        if STATE.selected_clients is None:
app/web/components/clients.py:78:            STATE.selected_clients = set(
app/web/components/clients.py:87:            STATE.selected_clients.add(name)
app/web/components/clients.py:89:            STATE.selected_clients.discard(name)
app/web/components/clients.py:96:        if STATE.selected_clients == all_clients:
app/web/components/clients.py:97:            STATE.selected_clients = None
app/web/components/clients.py:104:            "STATE.selected_clients=",
app/web/components/clients.py:105:            repr(STATE.selected_clients),
app/web/components/clients.py:204:                            STATE.selected_clients is None
app/web/components/clients.py:205:                            or name in STATE.selected_clients
app/web/frontend_v02.py:26:CLIENTS = [
app/web/main.py:92:        clients = get_clients_with_address_counts()
app/web/frontend_v01_backup_before_modular.py:15:CLIENTS = [
app/web/frontend_v01_backup_before_modular.py:26:ADDRESSES = [
app/web/frontend_v01.py:15:CLIENTS = [
app/web/frontend_v01.py:26:ADDRESSES = [
app/web/state.py:38:class AppState:
app/web/state.py:118:    selected_clients: set[str] | None = None
app/web/state.py:119:    selected_addresses: set[str] = field(default_factory=set)
app/web/state.py:124:    # addresses = только адреса
app/web/state.py:125:    # clients   = только клиенты
app/web/client_dictionary.py:33:    imported_clients = 0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 00:59:38

Да. Следующий шаг — **не менять пока саму механику фильтра**, а сначала посмотреть, откуда сейчас строятся два списка:

1. **Адреса** — должны быть постоянным справочником из `address_directory`, сейчас целесообразно заранее создать 99 записей.
2. **Клиенты** — наоборот, **не постоянный справочник**: список должен строиться из результатов Qwen и зависеть от текущего периода + выбранных адресов.
3. `dino_fingerprint` оставляем в `PHOTO_RECORD_INDEX` — он нужен как диагностический источник для контроля ошибок определения адреса, но **не участвует в выборе адреса UI**.
4. Адрес фотографии должен определяться через:
   `hybrid_final_id → address_fingerprints → address_id → address_directory`.
5. Если для fingerprint пока нет связи в `address_fingerprints`, фото не должно самовольно получать адрес по номеру fingerprint.
6. При этом список из 99 адресов не должен исчезать из-за отсутствия фотографий в текущем периоде: у такого адреса показываем **(0)**.

Сейчас нужны два файла, чтобы сделать это без поломки существующей логики:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ ADDRESSES.PY ================" && \
nl -ba app/web/components/addresses.py | sed -n '1,300p' && \
echo "================ CLIENTS.PY ================" && \
nl -ba app/web/components/clients.py | sed -n '1,280p' && \
echo "================ CLIENT DB ================" && \
nl -ba app/web/client_db.py | sed -n '1,240p'
```

И отдельно посмотрим, **какие именно поля Qwen сейчас записывает в `photos`**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'qwen|client|description|hybrid_final_id' \
app/web/photo_db.py \
app/web/client_db.py \
app/workers/qwen_worker.py \
--include="*.py" \
| head -350
```

После этого уже можно будет сделать правильную схему, не затрагивая `dino_fingerprint` и не возвращая физическую сортировку.

---

### 👤 **User** — 2026-08-21 01:00:46

Если для fingerprint пока нет связи в `address_fingerprints`, фото не должно самовольно получать адрес по номеру fingerprint.
Неверно - =пусть получает по фингепринту
alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ ADDRESSES.PY ================" && \
nl -ba app/web/components/addresses.py | sed -n '1,300p' && \
echo "================ CLIENTS.PY ================" && \
nl -ba app/web/components/clients.py | sed -n '1,280p' && \
echo "================ CLIENT DB ================" && \
nl -ba app/web/client_db.py | sed -n '1,240p'
================ ADDRESSES.PY ================
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
================ CLIENTS.PY ================
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice\@NEURO:\~/Desktop$ cd \~/projects/scene\_fingerprint\_mvp\_v02 && \\
grep -RniE \\
'qwen|client|description|hybrid\_final\_id' \\
app/web/photo\_db.py \\
app/web/client\_db.py \\
app/workers/qwen\_worker.py \\
\--include="\*.py" \\
\| head -350
app/web/photo\_db.py:27:            client,
app/web/photo\_db.py:30:            description,
app/web/photo\_db.py:32:            qwen\_status,
app/web/photo\_db.py:33:            qwen\_time\_sec,
app/web/photo\_db.py:49:            hybrid\_final\_id,
app/web/photo\_db.py:68:                for desc in cur.description
app/web/photo\_db.py:81:    Быстрая статистика независимых веток DINO и Qwen.
app/web/photo\_db.py:106:                WHERE qwen\_status = 'done'
app/web/photo\_db.py:107:            ) AS qwen\_done,
app/web/photo\_db.py:110:                WHERE qwen\_status = 'processing'
app/web/photo\_db.py:111:            ) AS qwen\_processing,
app/web/photo\_db.py:114:                WHERE qwen\_status = 'pending'
app/web/photo\_db.py:115:            ) AS qwen\_pending,
app/web/photo\_db.py:118:                WHERE qwen\_status = 'error'
app/web/photo\_db.py:119:            ) AS qwen\_error
app/web/photo\_db.py:139:        "qwen": {
app/web/client\_db.py:12\:def get\_clients\_with\_address\_counts() -> list[tuple[str, int]]:
app/web/client\_db.py:14:    Возвращает клиентов из результатов Qwen.
app/web/client\_db.py:17:    для которых Qwen определил клиента.
app/web/client\_db.py:22:            MIN(TRIM(client)) AS client,
app/web/client\_db.py:26:            client IS NOT NULL
app/web/client\_db.py:27:            AND TRIM(client) <> ''
app/web/client\_db.py:28:        GROUP BY LOWER(TRIM(client))
app/web/client\_db.py:29:        ORDER BY LOWER(MIN(TRIM(client)))
app/workers/qwen\_worker.py:28:# QWEN
app/workers/qwen\_worker.py:31\:MODEL = "qwen3-vl:4b-instruct"
app/workers/qwen\_worker.py:53:  "client": "",
app/workers/qwen\_worker.py:59:  "description": "",
app/workers/qwen\_worker.py:93\:client — компания, организация или заказчик.
app/workers/qwen\_worker.py:99\:description — краткое описание композиции баннера, максимум 300 символов.
app/workers/qwen\_worker.py:129\:client = ""
app/workers/qwen\_worker.py:135\:description = ""
app/workers/qwen\_worker.py:156:    Берём следующую фотографию, которая ещё не обработана Qwen.
app/workers/qwen\_worker.py:159:        Qwen работает независимо от DINO.
app/workers/qwen\_worker.py:162:        photo\_id -> результат Qwen
app/workers/qwen\_worker.py:177:            WHERE qwen\_status = 'pending'
app/workers/qwen\_worker.py:196:                qwen\_status = 'processing',
app/workers/qwen\_worker.py:199:              AND qwen\_status = 'pending'
app/workers/qwen\_worker.py:216:    Сохраняет результат Qwen.
app/workers/qwen\_worker.py:244:                qwen\_status = 'done',
app/workers/qwen\_worker.py:246:                client = %s,
app/workers/qwen\_worker.py:249:                description = %s,
app/workers/qwen\_worker.py:252:                qwen\_time\_sec = %s,
app/workers/qwen\_worker.py:269:                result.get("client") or None,
app/workers/qwen\_worker.py:272:                result.get("description") or None,
app/workers/qwen\_worker.py:330:                qwen\_status = 'error',
app/workers/qwen\_worker.py:356:# QWEN REQUEST
app/workers/qwen\_worker.py:481:            description = str(
app/workers/qwen\_worker.py:483:                    "description"
app/workers/qwen\_worker.py:487:            if description:
app/workers/qwen\_worker.py:498:                    "[QWEN RETRY]",
app/workers/qwen\_worker.py:499:                    "description empty",
app/workers/qwen\_worker.py:517:                "[QWEN JSON ERROR]",
app/workers/qwen\_worker.py:546:    print("QWEN3-VL 4B — DATABASE WORKER")
app/workers/qwen\_worker.py:552:        "[QWEN] Works independently from DINO."
app/workers/qwen\_worker.py:555:        "[QWEN] Source: photos.source\_path"
app/workers/qwen\_worker.py:558:        "[QWEN] Identity: photos.photo\_id"
app/workers/qwen\_worker.py:569:            "QWEN\_MAX\_ITEMS",
app/workers/qwen\_worker.py:582:                WHERE qwen\_status = 'pending'
app/workers/qwen\_worker.py:602:                    "[QWEN] Reached "
app/workers/qwen\_worker.py:615:                    "[QWEN] Queue empty."
app/workers/qwen\_worker.py:628:                f"[QWEN] {photo\_id}"
app/workers/qwen\_worker.py:668:                    "[QWEN] DONE",
app/workers/qwen\_worker.py:676:                    "| client:",
app/workers/qwen\_worker.py:678:                        "client",
app/workers/qwen\_worker.py:694:                    "DESCRIPTION:",
app/workers/qwen\_worker.py:696:                        "description",
app/workers/qwen\_worker.py:713:                    "[QWEN] ERROR",
app/workers/qwen\_worker.py:735:                        "[QWEN] DB ERROR:",
app/workers/qwen\_worker.py:745:        print("QWEN WORKER STOPPED")
alexice\@NEURO:\~/projects/scene\_fingerprint\_mvp\_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:00:47

Да. Теперь картина достаточно ясная. И здесь надо **разделить два понятия**:

1. **Какой адрес показываем фотографии сейчас** — пока разрешаем `86_v33 → 86`, `95_v33 → 95` и т. д.
2. **Как контролируем правильность этого определения** — `dino_fingerprint` сохраняем в PostgreSQL и используем как диагностический источник, чтобы потом видеть ошибки/переназначения.

То есть на текущем этапе делаем именно так:

### Адреса

**Справочник `address_directory` — постоянный.**  
Нужно заранее создать 99 адресов: `1 ... 99`.

При этом список адресов в UI **не строится из фотографий текущего периода**.

Например:

| Адрес | Фото за выбранный период |
|---|---:|
| 1 | 0 |
| 2 | 17 |
| 3 | 0 |
| 4 | 8 |
| ... | ... |
| 86 | 24 |
| 95 | 0 |
| 99 | 0 |

То есть адрес **всегда существует в списке**, а число справа считается уже после применения периода.

Это полностью соответствует твоему требованию: если у адреса сейчас нет фотографий — показываем `(0)`, а не убираем строку.

---

### Откуда берём адрес фотографии

На данном этапе:

```text
photos.hybrid_final_id
        │
        ▼
     86_v33
        │
        ▼
      адрес 86
```

И аналогично:

```text
95_v33 → 95
78_v33 → 78
79_v33 → 79
```

То есть **`hybrid_final_id` — основной источник виртуальной адресной сортировки**.

Физического:

```text
output/daily/86_v33/
output/daily/95_v33/
```

для работы интерфейса вообще не требуется.

Фото остаётся там, где оно физически лежит, например:

```text
source_path
```

а адрес — виртуальное свойство записи PostgreSQL.

---

### `dino_fingerprint` не удаляем

Это важно.

В записи фотографии оставляем, например:

```text
dino_fingerprint = 86_v33
hybrid_final_id  = 86_v33
```

или впоследствии:

```text
dino_fingerprint = 86_v33
hybrid_final_id  = 95_v33
```

Вот второй случай как раз позволит увидеть:

> DINO определил 86, а гибридная логика в итоге назначила 95.

То есть `dino_fingerprint` становится **диагностическим следом DINO**, а не источником отображаемого адреса.

---

## Клиенты — принципиально иначе

Здесь ты прав: **справочник клиентов постоянным не является**.

Сейчас уже есть правильная основа:

```python
get_clients_with_address_counts()
```

и источник:

```sql
FROM photos
WHERE client IS NOT NULL
  AND TRIM(client) <> ''
```

То есть список клиентов должен строиться **из результатов Qwen**.

И главное — список должен зависеть от текущего контекста:

```text
выбранный период
        +
выбранные адреса
        ↓
фотографии
        ↓
Qwen client
        ↓
уникальные клиенты
        ↓
чекбоксы
```

Поэтому если, например:

```text
ООО Ромашка
```

есть в базе вообще, но:

- в выбранном периоде его нет → **не показываем**
- на выбранном адресе его нет → **не показываем**
- при комбинации выбранных адресов его нет → **не показываем**

Не должно быть:

```text
ООО Ромашка (0)
```

для клиентов.

Для адресов — **да**.

Для клиентов — **нет**.

---

## Что сейчас надо менять

Сейчас `photos.py` строит:

```python
address_files = {}
```

из `dino_fingerprint` и затем делает:

```python
STATE.addresses = addresses
```

Это надо перестроить.

### Должно стать концептуально:

```text
address_directory
       ↓
постоянные адреса 1..99
       ↓
STATE.addresses
```

а отдельно:

```text
photos.hybrid_final_id
       ↓
виртуальный адрес фотографии
       ↓
PHOTO_INDEX
```

То есть `PHOTO_INDEX` может содержать только реально присутствующие фотографии:

```python
PHOTO_INDEX["86"] = [...]
PHOTO_INDEX["95"] = [...]
```

но:

```python
STATE.addresses
```

должен содержать:

```python
["1", "2", "3", ..., "99"]
```

Даже если:

```python
PHOTO_INDEX["1"] отсутствует
PHOTO_INDEX["2"] отсутствует
PHOTO_INDEX["95"] отсутствует
```

`address_photo_count()` уже корректно вернёт `0`, потому что там:

```python
PHOTO_INDEX.get(address, [])
```

---

### И ещё один важный момент

В `get_filtered_photos()` сейчас адресная фильтрация идёт по:

```python
STATE.addresses
```

Это нормально **после изменения источника `PHOTO_INDEX` на `hybrid_final_id`**.

А вот этот участок:

```python
db_address = str(
    record.get("address") or ""
).replace("_v33", "")
```

в `get_db_search_photos()` тоже надо привести к той же модели — адрес должен определяться через `hybrid_final_id`, а не через старое поле `address`.

---

## Итоговая модель

Получается очень чистая архитектура:

```text
                     PostgreSQL photos
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
      source_path     dino_fingerprint   hybrid_final_id
             │              │              │
             │              │              ▼
             │              │          виртуальный
             │              │            адрес
             │              │              │
             │              │              ▼
             │              │          PHOTO_INDEX
             │              │
             │              ▼
             │          диагностика
             │          ошибок DINO
             │
             ▼
       физический файл
       остаётся на месте

address_directory
       │
       ▼
постоянные адреса 1..99
       │
       ▼
   UI адресов
       │
       ├── 1 (0)
       ├── 2 (17)
       ├── 3 (0)
       ├── ...
       ├── 86 (24)
       └── 99 (0)

photos.client
       │
       ▼
результаты Qwen
       │
       + выбранный период
       + выбранные адреса
       ▼
динамический список клиентов
```

**Именно эту схему я бы сейчас зафиксировал и уже под неё правил код.** Не трогая пока сам `dino_fingerprint`, не удаляя его из БД и не вводя `address_fingerprints` как обязательное условие отображения.

---

### 👤 **User** — 2026-08-21 01:02:46

давай.

---

### 🤖 **Assistant** — 2026-08-21 01:02:48

Да. Делаем **поэтапно**, чтобы не сломать уже работающий фильтр.

Первым шагом я бы **не менял UI**. Сначала меняем источник адреса в `photos.py`:

- `hybrid_final_id` → виртуальный адрес;
- `dino_fingerprint` оставляем в записи;
- `address_fingerprints` пока не является обязательным условием;
- физические папки `_v33` не используются как источник адреса;
- список адресов потом переведём на постоянный `1..99`;
- клиенты пока не трогаем.

### Шаг 1 — покажи текущий блок построения `PHOTO_INDEX`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PHOTO INDEX 320-550 ================" && \
nl -ba app/web/components/photos.py | sed -n '300,550p' && \
echo "================ PHOTO DB ================" && \
nl -ba app/web/photo_db.py | sed -n '1,180p'
```

И пришли вывод.

После этого я дам **конкретный patch только для первого шага**, чтобы мы могли сразу проверить:

```text
hybrid_final_id → адрес
dino_fingerprint → сохранён для диагностики
```

а затем перейдём к постоянному справочнику `1..99` и динамическому списку клиентов.

---

### 👤 **User** — 2026-08-21 01:03:14

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PHOTO INDEX 320-550 ================" && \
nl -ba app/web/components/photos.py | sed -n '300,550p' && \
echo "================ PHOTO DB ================" && \
nl -ba app/web/photo_db.py | sed -n '1,180p'
================ PHOTO INDEX 320-550 ================
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
   344	        # На данном этапе единственный источник адреса:
   345	        # dino_fingerprint.
   346	        #
   347	        # hybrid_final_id и client normalization здесь
   348	        # НЕ используются.
   349	        #
   350	        # Если DINO fingerprint отсутствует —
   351	        # фотография в основной грид НЕ попадает.
   352	        # ----------------------------------------------------
   353	
   354	        fingerprint = str(
   355	            record.get("dino_fingerprint") or ""
   356	        ).strip()
   357	
   358	        if not fingerprint:
   359	            continue
   360	
   361	        # ----------------------------------------------------
   362	        # ВИРТУАЛЬНЫЙ АДРЕС
   363	        #
   364	        # На данном этапе dino_fingerprint сам является
   365	        # источником виртуального адреса.
   366	        #
   367	        # address_fingerprints пока НЕ ограничивает грид.
   368	        # Соответствия для новых fingerprint будут добавлены
   369	        # позже.
   370	        #
   371	        # Например:
   372	        #   78_v33 -> 78
   373	        #   79_v33 -> 79
   374	        #   85_v33 -> 85
   375	        #   95_v33 -> 95
   376	        # ----------------------------------------------------
   377	
   378	        address = fingerprint
   379	
   380	        if (
   381	            address.endswith("_v33")
   382	            and address[:-4].isdigit()
   383	        ):
   384	            address = address[:-4]
   385	
   386	        address = address.strip()
   387	
   388	        if not address:
   389	            continue
   390	
   391	        address_files.setdefault(
   392	            address,
   393	            []
   394	        ).append(path)
   395	
   396	    # ========================================================
   397	    # АДРЕСА
   398	    # ========================================================
   399	
   400	    addresses = sorted(
   401	        address_files.keys(),
   402	        key=lambda value: (
   403	            (0, int(value))
   404	            if value.isdigit()
   405	            else (1, value.lower())
   406	        ),
   407	    )
   408	
   409	    # ========================================================
   410	    # СОХРАНЯЕМ ИНДЕКС
   411	    # ========================================================
   412	
   413	    for address in addresses:
   414	
   415	        files = address_files.get(
   416	            address,
   417	            [],
   418	        )
   419	
   420	        # Убираем возможные дубликаты
   421	        unique = {}
   422	
   423	        for path in files:
   424	            unique[str(path)] = path
   425	
   426	        PHOTO_INDEX[address] = sorted(
   427	            unique.values(),
   428	            key=lambda p: p.name.lower(),
   429	        )
   430	
   431	    STATE.addresses = addresses
   432	
   433	    # Сбрасываем выбранные адреса,
   434	    # которых больше нет в текущем индексе.
   435	    STATE.selected_addresses.intersection_update(
   436	        STATE.addresses
   437	    )
   438	
   439	    print(
   440	        "[VIRTUAL PHOTO INDEX]",
   441	        "addresses=",
   442	        len(STATE.addresses),
   443	        "photos=",
   444	        sum(
   445	            len(files)
   446	            for files in PHOTO_INDEX.values()
   447	        ),
   448	        flush=True,
   449	    )
   450	
   451	    print(
   452	        "[VIRTUAL ADDRESSES]",
   453	        STATE.addresses,
   454	        flush=True,
   455	    )
   456	
   457	    print(
   458	        "[ADDRESS FILTER]",
   459	        "only photos with DINO fingerprint + address_directory",
   460	        flush=True,
   461	    )
   462	
   463	
   464	def get_all_indexed_photos():
   465	
   466	    result = []
   467	
   468	    for address in STATE.addresses:
   469	
   470	        # UNASSIGNED никогда не показываем в основном гриде.
   471	        if address == "__UNASSIGNED__":
   472	            continue
   473	
   474	        result.extend(
   475	            PHOTO_INDEX.get(
   476	                address,
   477	                [],
   478	            )
   479	        )
   480	
   481	    return result
   482	
   483	
   484	def get_db_search_photos():
   485	
   486	    if not STATE.search_query:
   487	        return []
   488	
   489	    result = []
   490	
   491	    for record in STATE.search_results:
   492	
   493	        db_path = record.get("path")
   494	
   495	        if not db_path:
   496	            continue
   497	
   498	        path = Path(db_path)
   499	
   500	        if not path.is_absolute():
   501	            path = PROJECT_ROOT / path
   502	
   503	        if not path.exists():
   504	            path = PROJECT_ROOT / db_path
   505	
   506	        if not path.exists():
   507	            continue
   508	
   509	        if STATE.selected_addresses:
   510	            db_address = str(
   511	                record.get("address") or ""
   512	            ).replace("_v33", "")
   513	
   514	            if db_address not in STATE.selected_addresses:
   515	                continue
   516	
   517	        # photo_grid() ожидает именно Path
   518	        result.append(path)
   519	
   520	    return result
   521	
   522	
   523	
   524	
   525	# ============================================================
   526	# EXIF DATE CACHE
   527	# ============================================================
   528	
   529	PHOTO_TAKEN_DATE_CACHE: dict[str, str | None] = {}
   530	
   531	
   532	def get_photo_taken_date(path):
   533	    """
   534	    Возвращает дату съёмки из EXIF DateTimeOriginal.
   535	
   536	    Результат:
   537	        YYYY-MM-DD
   538	        или None.
   539	
   540	    Значение кэшируется по абсолютному пути.
   541	    """
   542	
   543	    key = str(path.resolve())
   544	
   545	    if key in PHOTO_TAKEN_DATE_CACHE:
   546	        return PHOTO_TAKEN_DATE_CACHE[key]
   547	
   548	    result = None
   549	
   550	    try:
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:03:15

> **Searching Address Fingerprint Mappings**
>
>
> **Searching Address Fingerprint Mappings**
>
> 
>
> Worked for a couple of seconds

Да. Исправляем именно логику: **fingerprint должен сам давать адресу право быть источником адреса**, а `address_fingerprints` не должен блокировать это.

То есть сейчас строки `364–378` в `photos.py` как раз делают нужное:

- `dino_fingerprint = 78_v33`
- нормализуем → `78`
- фото попадает в адрес `78`

А `address_fingerprints` должен использоваться **только как дополнительная связь/справочник**, а не как условие допуска фотографии в адрес.

Нужно проверить, где именно сейчас `address_fingerprints` вмешивается в построение индекса, потому что в показанном фрагменте `photos.py` его вообще нет.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ ADDRESS_FINGERPRINTS ================" && \
grep -RniE \
'address_fingerprints|fingerprint.*address|address.*fingerprint' \
app scripts \
--include="*.py" \
| head -300
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DB TABLE ================" && \
psql -h localhost -U lora -d photobase -c \
"\d address_fingerprints"
```

Если таблица существует, ещё:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -h localhost -U lora -d photobase -c \
"SELECT * FROM address_fingerprints ORDER BY 1 LIMIT 50;"
```

**Целевая логика должна быть такой:**

```text
photo
  ↓
dino_fingerprint
  ↓
есть fingerprint?
  ├─ нет → фото без адреса / не в адресном гриде
  │
  └─ да
       ↓
   fingerprint → адрес
       ↓
   78_v33 → 78
   85_v33 → 85
   95_v33 → 95
       ↓
   показываем фото по этому адресу
```

А `address_fingerprints`:

```text
address_fingerprints
        ↓
дополнительная связь / справочник
        ↓
не является обязательным условием
```

То есть **не надо делать**:

```python
if fingerprint not in address_fingerprints:
    address = "__UNASSIGNED__"
```

или:

```python
if not mapping:
    continue
```

Нам сейчас нужно найти именно тот участок, где такая проверка существует. Пришли вывод двух первых команд — после этого дам точечный патч, без переделки остального фильтра адресов/клиентов.

---

### 👤 **User** — 2026-08-21 01:03:58

================ ADDRESS_FINGERPRINTS ================
app/web/components/photos.py:367:        # address_fingerprints пока НЕ ограничивает грид.
app/web/components/photos.py:378:        address = fingerprint
app/web/components/photos.py:459:        "only photos with DINO fingerprint + address_directory",
app/web/directory_db.py:52:def get_address_by_fingerprint(fingerprint_id):
app/web/directory_db.py:54:    Возвращает address_id для fingerprint.
app/web/directory_db.py:63:        FROM address_fingerprints
app/web/directory_db.py:80:def get_address_for_fingerprint(fingerprint_id):
app/web/directory_db.py:85:    address_id = get_address_by_fingerprint(
scripts/llm_resolver_v01.py:119:            "Determine the most likely address/fingerprint for the "
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ "\d address_fingerprints"
================ DB TABLE ================
                      Table "public.address_fingerprints"
     Column     |            Type             | Collation | Nullable | Default 
----------------+-----------------------------+-----------+----------+---------
 fingerprint_id | text                        |           | not null | 
 address_id     | integer                     |           | not null | 
 active         | boolean                     |           | not null | true
 created_at     | timestamp without time zone |           | not null | now()
 updated_at     | timestamp without time zone |           | not null | now()
Indexes:
    "address_fingerprints_pkey" PRIMARY KEY, btree (fingerprint_id)
    "idx_address_fingerprints_address_id" btree (address_id)
Foreign-key constraints:
    "address_fingerprints_address_id_fkey" FOREIGN KEY (address_id) REFERENCES address_directory(id) ON DELETE RESTRICT

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$  fingerprint_id | address_id | active |         created_at         |         updated_at         
----------------+------------+--------+----------------------------+----------------------------
 78_v33         |         78 | t      | 2026-08-20 22:00:25.121179 | 2026-08-20 22:00:25.121179
 79_v33         |         79 | t      | 2026-08-20 22:00:25.123891 | 2026-08-20 22:00:25.123891
(2 rows)

---

### 🤖 **Assistant** — 2026-08-21 01:03:59

Да, теперь картина ясна.

У тебя **сейчас уже почти правильная архитектура**, но надо разделить два понятия:

1. `dino_fingerprint` — **определяет адрес фотографии**.
2. `address_fingerprints` — **хранит связь fingerprint → address_id** в справочнике.

И главное: **если записи в `address_fingerprints` пока нет, fingerprint всё равно должен дать фотографии адрес.**

### Что сейчас происходит

В `photos.py` уже есть:

```python
fingerprint = str(
    record.get("dino_fingerprint") or ""
).strip()

if not fingerprint:
    continue

address = fingerprint

if (
    address.endswith("_v33")
    and address[:-4].isdigit()
):
    address = address[:-4]
```

То есть:

```text
78_v33 → 78
79_v33 → 79
85_v33 → 85
95_v33 → 95
```

Это **правильно**.

Но у тебя есть `directory_db.py`, который делает другое:

```text
fingerprint_id
      ↓
address_fingerprints
      ↓
address_id
      ↓
address_directory
```

И вот здесь нам надо посмотреть реализацию, чтобы понять, **где UI сейчас может получать адрес не из fingerprint, а из справочника**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DIRECTORY DB ================" && \
nl -ba app/web/directory_db.py | sed -n '1,240p'
```

И ещё очень важная проверка — какие реальные fingerprint сейчас есть в `photos`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -h localhost -U lora -d photobase -c "
SELECT
    dino_fingerprint,
    COUNT(*) AS photos
FROM photos
WHERE dino_fingerprint IS NOT NULL
  AND TRIM(dino_fingerprint) <> ''
GROUP BY dino_fingerprint
ORDER BY dino_fingerprint;
"
```

### Целевое поведение фиксируем

Например, сейчас в БД есть только:

```text
78_v33 → 78
79_v33 → 79
```

Но если в `photos` появится:

```text
85_v33
95_v33
```

то **фото должны сразу попадать соответственно в адреса 85 и 95**, даже если:

```text
address_fingerprints

85_v33 — отсутствует
95_v33 — отсутствует
```

То есть отсутствие записи в `address_fingerprints` **не должно означать `UNASSIGNED` и не должно исключать фото**.

А когда позже появится:

```text
85_v33 → 85
```

это не должно менять сам принцип отображения — оно лишь формализует связь в справочнике.

**И ещё:** я бы пока вообще ничего не патчил. По `photos.py` нужная логика уже присутствует. Сначала посмотрим `directory_db.py`, потому что именно там может находиться старая логика, которая конфликтует с новым правилом.

---

### 👤 **User** — 2026-08-21 01:05:07

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DIRECTORY DB ================" && \
nl -ba app/web/directory_db.py | sed -n '1,240p'
================ DIRECTORY DB ================
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
    12	# ============================================================
    13	# АДРЕСА
    14	# ============================================================
    15	
    16	def get_address_directory():
    17	    """
    18	    Возвращает справочник адресов.
    19	
    20	    {
    21	        78: {
    22	            "simple": "Комарова, 13",
    23	            "legal": "...",
    24	        },
    25	        ...
    26	    }
    27	    """
    28	
    29	    sql = """
    30	        SELECT
    31	            id,
    32	            simple_address,
    33	            legal_address
    34	        FROM address_directory
    35	        WHERE active = TRUE
    36	        ORDER BY sort_order, id
    37	    """
    38	
    39	    with psycopg2.connect(**PG_CONFIG) as conn:
    40	        with conn.cursor() as cur:
    41	            cur.execute(sql)
    42	
    43	            return {
    44	                int(row[0]): {
    45	                    "simple": row[1] or "",
    46	                    "legal": row[2] or "",
    47	                }
    48	                for row in cur.fetchall()
    49	            }
    50	
    51	
    52	def get_address_by_fingerprint(fingerprint_id):
    53	    """
    54	    Возвращает address_id для fingerprint.
    55	
    56	    Например:
    57	
    58	        78_v33 -> 78
    59	    """
    60	
    61	    sql = """
    62	        SELECT address_id
    63	        FROM address_fingerprints
    64	        WHERE fingerprint_id = %s
    65	          AND active = TRUE
    66	        LIMIT 1
    67	    """
    68	
    69	    with psycopg2.connect(**PG_CONFIG) as conn:
    70	        with conn.cursor() as cur:
    71	            cur.execute(sql, (fingerprint_id,))
    72	            row = cur.fetchone()
    73	
    74	            if row is None:
    75	                return None
    76	
    77	            return int(row[0])
    78	
    79	
    80	def get_address_for_fingerprint(fingerprint_id):
    81	    """
    82	    Полная информация об адресе fingerprint.
    83	    """
    84	
    85	    address_id = get_address_by_fingerprint(
    86	        fingerprint_id
    87	    )
    88	
    89	    if address_id is None:
    90	        return None
    91	
    92	    directory = get_address_directory()
    93	
    94	    data = directory.get(address_id)
    95	
    96	    if data is None:
    97	        return None
    98	
    99	    return {
   100	        "id": address_id,
   101	        "simple": data["simple"],
   102	        "legal": data["legal"],
   103	    }
   104	
   105	
   106	# ============================================================
   107	# КЛИЕНТЫ
   108	# ============================================================
   109	
   110	def get_clients():
   111	    """
   112	    Возвращает нормализованный справочник клиентов.
   113	    """
   114	
   115	    sql = """
   116	        SELECT
   117	            id,
   118	            name,
   119	            simple_name
   120	        FROM client_directory
   121	        WHERE active = TRUE
   122	        ORDER BY sort_order, LOWER(name)
   123	    """
   124	
   125	    with psycopg2.connect(**PG_CONFIG) as conn:
   126	        with conn.cursor() as cur:
   127	            cur.execute(sql)
   128	
   129	            return [
   130	                {
   131	                    "id": int(row[0]),
   132	                    "name": row[1] or "",
   133	                    "simple": row[2] or "",
   134	                }
   135	                for row in cur.fetchall()
   136	            ]
   137	
   138	
   139	def normalize_client(raw_client):
   140	    """
   141	    Возвращает client_id по точному имени
   142	    или зарегистрированному alias.
   143	
   144	    Никакого fuzzy matching здесь пока нет.
   145	    """
   146	
   147	    if not raw_client:
   148	        return None
   149	
   150	    raw = raw_client.strip()
   151	
   152	    if not raw:
   153	        return None
   154	
   155	    sql = """
   156	        SELECT id
   157	        FROM client_directory
   158	        WHERE LOWER(TRIM(name)) = LOWER(TRIM(%s))
   159	
   160	        UNION
   161	
   162	        SELECT client_id
   163	        FROM client_aliases
   164	        WHERE LOWER(TRIM(raw_name)) = LOWER(TRIM(%s))
   165	
   166	        LIMIT 1
   167	    """
   168	
   169	    with psycopg2.connect(**PG_CONFIG) as conn:
   170	        with conn.cursor() as cur:
   171	            cur.execute(
   172	                sql,
   173	                (raw, raw),
   174	            )
   175	
   176	            row = cur.fetchone()
   177	
   178	            if row is None:
   179	                return None
   180	
   181	            return int(row[0])
   182	
   183	
   184	def get_client_name(client_id):
   185	    """
   186	    Возвращает отображаемое имя клиента.
   187	    """
   188	
   189	    if client_id is None:
   190	        return None
   191	
   192	    sql = """
   193	        SELECT
   194	            COALESCE(NULLIF(TRIM(simple_name), ''), name)
   195	        FROM client_directory
   196	        WHERE id = %s
   197	          AND active = TRUE
   198	        LIMIT 1
   199	    """
   200	
   201	    with psycopg2.connect(**PG_CONFIG) as conn:
   202	        with conn.cursor() as cur:
   203	            cur.execute(sql, (client_id,))
   204	            row = cur.fetchone()
   205	
   206	            return row[0] if row else None
   207	
   208	
   209	print(
   210	    "[DIRECTORY DB] loaded",
   211	    flush=True,
   212	)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$  dino_fingerprint | photos 
------------------+--------
 78_v33           |     84
 79_v33           |     31
 80_v33           |     10
 81_v33           |     16
 82_v33           |     12
 83_v33           |     17
 84_v33           |     16
 85_v33           |     23
 86_v33           |     22
 87_v33           |     19
 88_v33           |     14
 89_v33           |     34
 90_v33           |      3
 91_v33           |     15
 92_v33           |     36
 93_v33           |     30
 94_v33           |    119
 95_v33           |     18
(18 rows)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:05:08

Да. Теперь видно точно, где проблема.

Сейчас у тебя **18 fingerprint'ов в `photos`**, но в `address_fingerprints` зарегистрированы только:

```text
78_v33 → 78
79_v33 → 79
```

При этом фотографии есть для всех:

```text
78_v33 ... 95_v33
```

### Правило должно быть таким

Источник адреса — **всегда `dino_fingerprint`**.

То есть:

```text
photos.dino_fingerprint
        │
        ├── 78_v33 → адрес 78
        ├── 79_v33 → адрес 79
        ├── 80_v33 → адрес 80
        ├── ...
        └── 95_v33 → адрес 95
```

`address_fingerprints` **не должен быть разрешением на использование fingerprint**.

Он нужен для явной связи:

```text
fingerprint_id → address_id
```

но отсутствие этой записи **не отменяет адрес, полученный из fingerprint**.

---

## Где сейчас надо менять

Вот этот участок `photos.py`:

```python
address = fingerprint

if (
    address.endswith("_v33")
    and address[:-4].isdigit()
):
    address = address[:-4]
```

**оставляем.**

Он как раз делает то, что ты сейчас уточнил.

А вот комментарии вокруг него сейчас вводят в заблуждение:

```text
address_fingerprints пока НЕ ограничивает грид.
Соответствия для новых fingerprint будут добавлены позже.
```

Это фактически описывает правильное поведение, но формулировка «пока» неправильная.

Нужно зафиксировать архитектурно:

> `dino_fingerprint` является непосредственным источником виртуального адреса фотографии.  
> `address_fingerprints` не является обязательным условием отображения фотографии.

---

### Но есть важный второй момент

У тебя `address_directory` — это уже **справочник адресов**, а `address_fingerprints` — таблица связей.

Поэтому надо различать:

**Фотография:**

```text
dino_fingerprint = 94_v33
```

→ виртуальный адрес:

```text
94
```

**Отображение названия адреса:**

```text
94 → address_directory
```

А `address_fingerprints` нужен для управления связью fingerprint с адресом, но не для того, чтобы решать, показывать фотографию или нет.

---

## Что я предлагаю сделать сейчас

Не трогать `directory_db.py`.

В нём функция:

```python
get_address_by_fingerprint()
```

нормальная и полезная для тех мест, где действительно требуется **зарегистрированная связь**.

Нужно проверить другое: **не используется ли `get_address_for_fingerprint()` при построении основного PHOTO_INDEX или списка адресов.**

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DIRECTORY USAGE ================" && \
grep -RniE \
'get_address_by_fingerprint|get_address_for_fingerprint|address_fingerprints' \
app \
--include="*.py"
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ ADDRESS DIRECTORY USAGE ================" && \
grep -RniE \
'get_address_directory|address_directory' \
app/web \
--include="*.py"
```

**Особенно интересует первый вывод.**

Потому что сам `build_photo_index()` уже правильно делает `80_v33 → 80`, `81_v33 → 81` и т.д. Нам надо найти, **почему UI после этого может всё-таки считать адреса 80–95 неподтверждёнными**.

После этих двух grep уже можно будет сделать точечный патч, не ломая работающую часть.

---

### 👤 **User** — 2026-08-21 01:05:46

`dino_fingerprint` является непосредственным источником виртуального адреса фотографии.  или hybrid -после сортировки?

---

