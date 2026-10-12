## СЕССИЯ: 19-2

**Создано:** 2026-08-19 14:18:36
**Обновлено:** 2026-08-20 00:17:26
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a859109-7218-83ea-9de2-3480a4713401](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a859109-7218-83ea-9de2-3480a4713401)

---

### 👤 **User** — 2026-08-19 23:21:54

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ STATE ================" && \
nl -ba app/web/state.py | sed -n '1,360p' && \
echo "================ HEADER AUTH ================" && \
nl -ba app/web/components/header.py | sed -n '1,260p' && \
echo "================ SEARCH ================" && \
nl -ba app/web/components/search.py | sed -n '1,360p' && \
echo "================ USERS DB ================" && \
nl -ba app/web/users_db.py | sed -n '1,360p'
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
    39	    manager: str = "Вихляева Алена"
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
   167	    # ПОИСК
   168	    # ========================================================
   169	
   170	    search_query: str = ""
   171	    search_results: list[dict] = field(default_factory=list)
   172	
   173	    photos: list[Photo] = field(default_factory=list)
   174	    selected_photos: set[str] = field(default_factory=set)
   175	
   176	    refresh_photos: object = None
   177	
   178	
   179	STATE = AppState()
================ HEADER AUTH ================
     1	from nicegui import ui
     2	
     3	from app.web.config import LOGO_PATH
     4	from app.web.state import STATE
     5	from app.web.users_db import (
     6	    init_users_db,
     7	    get_users,
     8	    check_user_password,
     9	    get_user_auth_settings,
    10	)
    11	from app.web.components.technical import show_technical
    12	
    13	
    14	def build_header():
    15	
    16	    init_users_db()
    17	
    18	    # ========================================================
    19	    # HEADER
    20	    # ========================================================
    21	
    22	    with ui.header().classes(
    23	        "items-center justify-between px-4 py-2"
    24	    ).style(
    25	        "position: relative; z-index: 1000;"
    26	    ):
    27	
    28	        # ----------------------------------------------------
    29	        # LEFT
    30	        # ----------------------------------------------------
    31	
    32	        with ui.row().classes(
    33	            "items-center gap-3"
    34	        ):
    35	
    36	            if LOGO_PATH.exists():
    37	
    38	                ui.image(
    39	                    str(LOGO_PATH)
    40	                ).style(
    41	                    """
    42	                    width: 150px;
    43	                    height: 56px;
    44	                    object-fit: contain;
    45	                    object-position: left center;
    46	                    """
    47	                )
    48	
    49	            else:
    50	
    51	                ui.icon(
    52	                    "photo_library",
    53	                    size="42px",
    54	                )
    55	
    56	            with ui.column().classes("gap-0"):
    57	
    58	                ui.label(
    59	                    "АЛЬБИОН. ОФИС: Фотобаза. Экраны"
    60	                ).classes(
    61	                    "text-xl font-bold"
    62	                )
    63	
    64	                ui.label(
    65	                    'Рекламное агентство "Альбион" 320-30-20'
    66	                ).classes(
    67	                    "text-sm opacity-80"
    68	                )
    69	
    70	    # ========================================================
    71	    # FOREGROUND
    72	    # ========================================================
    73	
    74	    with ui.element("div").classes(
    75	        "fixed top-3 right-4 "
    76	        "flex items-center gap-2"
    77	    ).style(
    78	        """
    79	        z-index: 99999;
    80	        pointer-events: auto;
    81	        """
    82	    ):
    83	
    84	        # ----------------------------------------------------
    85	        # CURRENT USER BUTTON
    86	        # ----------------------------------------------------
    87	
    88	        user_button = ui.button(
    89	            STATE.manager or "Пользователь",
    90	            icon="person",
    91	        ).props(
    92	            "unelevated dense"
    93	        ).classes(
    94	            "min-w-[210px] font-medium"
    95	        ).style(
    96	            "color: white;"
    97	        )
    98	
    99	        # ----------------------------------------------------
   100	        # APPLY COLOR
   101	        # ----------------------------------------------------
   102	
   103	        def apply_user_color(color):
   104	
   105	            if not color:
   106	                return
   107	
   108	            user_button.style(
   109	                f"""
   110	                background-color: {color} !important;
   111	                color: white !important;
   112	                z-index: 100000 !important;
   113	                """
   114	            )
   115	
   116	        # ----------------------------------------------------
   117	        # USER SWITCHER
   118	        # ----------------------------------------------------
   119	
   120	        def open_user_switcher():
   121	
   122	            dialog = ui.dialog().props("persistent")
   123	
   124	            with dialog:
   125	                with ui.card().classes(
   126	                    "w-[380px] max-w-[92vw]"
   127	                ):
   128	                    ui.label(
   129	                        "Выбор пользователя"
   130	                    ).classes(
   131	                        "text-lg font-bold mb-2"
   132	                    )
   133	
   134	                    user_list = ui.column().classes(
   135	                        "w-full gap-1"
   136	                    )
   137	
   138	                    def password_dialog(
   139	                        user_id,
   140	                        name,
   141	                        color,
   142	                    ):
   143	                        auth = get_user_auth_settings(user_id)
   144	
   145	                        if not auth or not auth["active"]:
   146	                            ui.notify(
   147	                                "Пользователь недоступен",
   148	                                type="negative",
   149	                            )
   150	                            return
   151	
   152	                        # Пользователь без пароля.
   153	                        # Например: Гость.
   154	                        if not auth["password_required"]:
   155	                            STATE.user_id = user_id
   156	                            STATE.manager = name
   157	
   158	                            user_button.text = name
   159	
   160	                            apply_user_color(
   161	                                color
   162	                            )
   163	
   164	                            print(
   165	                                "[USER SELECT]",
   166	                                user_id,
   167	                                repr(name),
   168	                                color,
   169	                                "(без пароля)",
   170	                                flush=True,
   171	                            )
   172	
   173	                            dialog.close()
   174	                            return
   175	
   176	                        with ui.dialog().props("persistent") as password_dialog:
   177	
   178	                            with ui.card().classes(
   179	                                "w-[360px] max-w-[90vw]"
   180	                            ):
   181	                                ui.label(
   182	                                    f"Вход: {name}"
   183	                                ).classes(
   184	                                    "text-lg font-bold"
   185	                                )
   186	
   187	                                ui.label(
   188	                                    "Введите пароль пользователя"
   189	                                ).classes(
   190	                                    "text-sm text-grey-7 mb-2"
   191	                                )
   192	
   193	                                password_input = ui.input(
   194	                                    "Пароль",
   195	                                    password=True,
   196	                                    password_toggle_button=True,
   197	                                ).classes(
   198	                                    "w-full"
   199	                                )
   200	
   201	                                def check():
   202	
   203	                                    password = (
   204	                                        password_input.value or ""
   205	                                    )
   206	
   207	                                    if not check_user_password(
   208	                                        user_id,
   209	                                        password,
   210	                                    ):
   211	                                        ui.notify(
   212	                                            "Неверный пароль",
   213	                                            type="negative",
   214	                                        )
   215	                                        password_input.value = ""
   216	                                        password_input.update()
   217	                                        return
   218	
   219	                                    STATE.user_id = user_id
   220	                                    STATE.manager = name
   221	
   222	                                    user_button.text = name
   223	
   224	                                    apply_user_color(
   225	                                        color
   226	                                    )
   227	
   228	                                    print(
   229	                                        "[USER SELECT]",
   230	                                        user_id,
   231	                                        repr(name),
   232	                                        color,
   233	                                        flush=True,
   234	                                    )
   235	
   236	                                    password_dialog.close()
   237	                                    dialog.close()
   238	
   239	                                with ui.row().classes(
   240	                                    "w-full justify-end gap-2 mt-3"
   241	                                ):
   242	                                    ui.button(
   243	                                        "Отмена",
   244	                                        on_click=password_dialog.close,
   245	                                    ).props(
   246	                                        "flat dense"
   247	                                    )
   248	
   249	                                    ui.button(
   250	                                        "Войти",
   251	                                        icon="login",
   252	                                        on_click=check,
   253	                                    ).props(
   254	                                        "dense"
   255	                                    )
   256	
   257	                                password_input.on(
   258	                                    "keydown.enter",
   259	                                    lambda e: check(),
   260	                                )
================ SEARCH ================
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
   171	        "w-full items-center gap-2 px-3 py-3"
   172	    ):
   173	
   174	        search = ui.input(
   175	            placeholder=(
   176	                "Поиск по клиенту, бренду, "
   177	                "тексту, объектам..."
   178	            )
   179	        ).props(
   180	            "outlined dense clearable"
   181	        ).classes(
   182	            "flex-grow"
   183	        )
   184	
   185	        search.on(
   186	            "keydown.enter",
   187	            lambda e: run_search(search.value),
   188	        )
   189	
   190	        ui.button(
   191	            "Найти",
   192	            icon="search",
   193	            on_click=lambda: run_search(
   194	                search.value
   195	            ),
   196	        ).props(
   197	            "unelevated"
   198	        )
   199	
   200	        ui.button(
   201	            "Фото",
   202	            icon="upload",
   203	            on_click=upload_photo,
   204	        ).props(
   205	            "outline"
   206	        )
================ USERS DB ================
     1	import sqlite3
     2	
     3	from app.web.config import DB_PATH
     4	
     5	
     6	DEFAULT_USERS = [
     7	    ("Вихляева Алена", "#E53935"),
     8	    ("Пятницына Диана", "#D81B60"),
     9	    ("Аннин Илья", "#8E24AA"),
    10	    ("Иванова Елена", "#5E35B1"),
    11	    ("Марышева Елена", "#3949AB"),
    12	    ("Бутовченко Ольга", "#1E88E5"),
    13	    ("Кривошлыкова Ангелина", "#039BE5"),
    14	    ("Теплинская Наталья", "#00ACC1"),
    15	    ("Папикян Эля", "#00897B"),
    16	    ("Путилина Татьяна", "#43A047"),
    17	]
    18	
    19	# Временный пароль для уже существующих пользователей.
    20	# После первого входа его можно изменить в настройках.
    21	INITIAL_PASSWORD = "1234"
    22	
    23	
    24	def get_connection():
    25	    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    26	    return sqlite3.connect(DB_PATH)
    27	
    28	
    29	def init_users_db():
    30	
    31	    with get_connection() as con:
    32	
    33	        con.execute("""
    34	            CREATE TABLE IF NOT EXISTS users (
    35	                id INTEGER PRIMARY KEY AUTOINCREMENT,
    36	                name TEXT NOT NULL UNIQUE,
    37	                color TEXT NOT NULL,
    38	                password TEXT NOT NULL DEFAULT '',
    39	                  password_required INTEGER NOT NULL DEFAULT 1,
    40	                  persist_state INTEGER NOT NULL DEFAULT 1,
    41	                active INTEGER NOT NULL DEFAULT 1,
    42	                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    43	                archived_at TEXT
    44	            )
    45	        """)
    46	
    47	        # --------------------------------------------------------
    48	        # MIGRATION
    49	        # --------------------------------------------------------
    50	
    51	        columns = {
    52	            row[1]
    53	            for row in con.execute(
    54	                "PRAGMA table_info(users)"
    55	            ).fetchall()
    56	        }
    57	
    58	        if "password_required" not in columns:
    59	            con.execute("""
    60	                ALTER TABLE users
    61	                ADD COLUMN password_required INTEGER NOT NULL DEFAULT 1
    62	            """)
    63	
    64	        if "persist_state" not in columns:
    65	            con.execute("""
    66	                ALTER TABLE users
    67	                ADD COLUMN persist_state INTEGER NOT NULL DEFAULT 1
    68	            """)
    69	
    70	        if "password" not in columns:
    71	            con.execute("""
    72	                ALTER TABLE users
    73	                ADD COLUMN password TEXT NOT NULL DEFAULT ''
    74	            """)
    75	
    76	            # Существующие менеджеры получают временный пароль.
    77	            con.execute(
    78	                """
    79	                UPDATE users
    80	                SET password = ?
    81	                WHERE password = ''
    82	                """,
    83	                (INITIAL_PASSWORD,),
    84	            )
    85	
    86	        # --------------------------------------------------------
    87	        # --------------------------------------------------------
    88	        # GUEST
    89	        # --------------------------------------------------------
    90	        guest_exists = con.execute(
    91	            """
    92	            SELECT 1
    93	            FROM users
    94	            WHERE name = ?
    95	            LIMIT 1
    96	            """,
    97	            ("Гость",),
    98	        ).fetchone()
    99	
   100	        if not guest_exists:
   101	            con.execute(
   102	                """
   103	                INSERT INTO users
   104	                    (name, color, password, password_required, persist_state, active)
   105	                VALUES (?, ?, ?, 0, 0, 1)
   106	                """,
   107	                ("Гость", "#78909C", ""),
   108	            )
   109	
   110	
   111	        # INITIAL DATA
   112	        # --------------------------------------------------------
   113	
   114	        # --------------------------------------------------------
   115	        # ADMINISTRATOR
   116	        # --------------------------------------------------------
   117	        # Администратор должен существовать всегда.
   118	        # Если его нет — создаём, не затрагивая существующих
   119	        # пользователей.
   120	        admin_exists = con.execute(
   121	            """
   122	            SELECT 1
   123	            FROM users
   124	            WHERE name = ?
   125	            LIMIT 1
   126	            """,
   127	            ("Администратор",),
   128	        ).fetchone()
   129	
   130	        if not admin_exists:
   131	            con.execute(
   132	                """
   133	                INSERT INTO users
   134	                    (name, color, password, active)
   135	                VALUES (?, ?, ?, 1)
   136	                """,
   137	                (
   138	                    "Администратор",
   139	                    "#263238",
   140	                    INITIAL_PASSWORD,
   141	                ),
   142	            )
   143	
   144	        # --------------------------------------------------------
   145	        # --------------------------------------------------------
   146	        # GUEST
   147	        # --------------------------------------------------------
   148	        guest_exists = con.execute(
   149	            """
   150	            SELECT 1
   151	            FROM users
   152	            WHERE name = ?
   153	            LIMIT 1
   154	            """,
   155	            ("Гость",),
   156	        ).fetchone()
   157	
   158	        if not guest_exists:
   159	            con.execute(
   160	                """
   161	                INSERT INTO users
   162	                    (name, color, password, password_required, persist_state, active)
   163	                VALUES (?, ?, ?, 0, 0, 1)
   164	                """,
   165	                ("Гость", "#78909C", ""),
   166	            )
   167	
   168	
   169	        # INITIAL DATA
   170	        # --------------------------------------------------------
   171	        # Старые DEFAULT_USERS добавляем только если база пустая.
   172	        count = con.execute(
   173	            "SELECT COUNT(*) FROM users"
   174	        ).fetchone()[0]
   175	
   176	        if count == 1:
   177	            con.executemany(
   178	                """
   179	                INSERT INTO users
   180	                    (name, color, password, active)
   181	                VALUES (?, ?, ?, 1)
   182	                """,
   183	                [
   184	                    (
   185	                        name,
   186	                        color,
   187	                        INITIAL_PASSWORD,
   188	                    )
   189	                    for name, color in DEFAULT_USERS
   190	                ],
   191	            )
   192	
   193	        con.commit()
   194	
   195	
   196	def get_users(active_only=True):
   197	
   198	    init_users_db()
   199	
   200	    with get_connection() as con:
   201	
   202	        if active_only:
   203	            rows = con.execute("""
   204	                SELECT id, name, color, active
   205	                FROM users
   206	                WHERE active = 1
   207	                ORDER BY name COLLATE NOCASE
   208	            """).fetchall()
   209	
   210	        else:
   211	            rows = con.execute("""
   212	                SELECT id, name, color, active
   213	                FROM users
   214	                ORDER BY active DESC, name COLLATE NOCASE
   215	            """).fetchall()
   216	
   217	    return rows
   218	
   219	
   220	def get_user_password(user_id):
   221	
   222	    init_users_db()
   223	
   224	    with get_connection() as con:
   225	        row = con.execute(
   226	            """
   227	            SELECT password
   228	            FROM users
   229	            WHERE id = ?
   230	            """,
   231	            (user_id,),
   232	        ).fetchone()
   233	
   234	    return row[0] if row else None
   235	
   236	
   237	def get_user_auth_settings(user_id):
   238	    init_users_db()
   239	
   240	    with get_connection() as con:
   241	        row = con.execute(
   242	            """
   243	            SELECT password_required, persist_state, active
   244	            FROM users
   245	            WHERE id = ?
   246	            """,
   247	            (user_id,),
   248	        ).fetchone()
   249	
   250	    if not row:
   251	        return None
   252	
   253	    return {
   254	        "password_required": bool(row[0]),
   255	        "persist_state": bool(row[1]),
   256	        "active": bool(row[2]),
   257	    }
   258	
   259	
   260	def check_user_password(user_id, password):
   261	
   262	    stored = get_user_password(user_id)
   263	
   264	    if stored is None:
   265	        return False
   266	
   267	    return str(password or "") == str(stored)
   268	
   269	
   270	def update_user_password(user_id, password):
   271	
   272	    password = str(password or "")
   273	
   274	    if not password:
   275	        return False
   276	
   277	    init_users_db()
   278	
   279	    with get_connection() as con:
   280	        con.execute(
   281	            """
   282	            UPDATE users
   283	            SET password = ?
   284	            WHERE id = ?
   285	            """,
   286	            (password, user_id),
   287	        )
   288	        con.commit()
   289	
   290	    return True
   291	
   292	
   293	def add_user(name, color, password=INITIAL_PASSWORD):
   294	
   295	    name = str(name).strip()
   296	    color = str(color or "").strip()
   297	    password = str(password or "").strip()
   298	
   299	    if not name or not color or not password:
   300	        return False
   301	
   302	    init_users_db()
   303	
   304	    try:
   305	        with get_connection() as con:
   306	            con.execute(
   307	                """
   308	                INSERT INTO users
   309	                    (name, color, password, active)
   310	                VALUES (?, ?, ?, 1)
   311	                """,
   312	                (
   313	                    name,
   314	                    color,
   315	                    password,
   316	                ),
   317	            )
   318	            con.commit()
   319	
   320	        return True
   321	
   322	    except sqlite3.IntegrityError:
   323	        return False
   324	
   325	
   326	def update_user_name(user_id, name):
   327	
   328	    name = str(name).strip()
   329	
   330	    if not name:
   331	        return False
   332	
   333	    init_users_db()
   334	
   335	    try:
   336	        with get_connection() as con:
   337	            con.execute(
   338	                """
   339	                UPDATE users
   340	                SET name = ?
   341	                WHERE id = ?
   342	                """,
   343	                (name, user_id),
   344	            )
   345	            con.commit()
   346	
   347	        return True
   348	
   349	    except sqlite3.IntegrityError:
   350	        return False
   351	
   352	
   353	def update_user_color(user_id, color):
   354	
   355	    if not color:
   356	        return False
   357	
   358	    init_users_db()
   359	
   360	    with get_connection() as con:
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 23:21:55

> **Inspecting web components and application entry point**
>
>
> **Inspected web components and application entry point**
>
> 
>
> Worked for 4s

Да. По этим файлам уже видно, как сделать следующий этап без переделки всей архитектуры.

Сейчас предлагаю идти **в таком порядке**:

1. **Сохранять пользователя в cookies/browser storage**:
   - первый вход → `Гость`;
   - если пользователь уже выбирал менеджера и у него разрешён `persist_state` → при следующем открытии автоматически загружать его;
   - для `Гость` ничего не сохранять;
   - пароль при этом в cookies не хранить.

2. При загрузке:
   - пользователь → `Гость` либо сохранённый менеджер;
   - **все клиенты отмечены**;
   - **все адреса отмечены**;
   - период → **последний месяц**;
   - сортировка → существующая логика, только период выставляем автоматически.

3. Подборки:
   - оставить клиентские;
   - добавить полноценные **адресные подборки**;
   - рядом с названием `КЛИЕНТЫ` / `АДРЕСА` одна кнопка `Все / Снять`;
   - показывать количество элементов в подборке, например `Важное (7)`.

4. В строку управления гридом вынести отдельные кнопки:
   - вид грида;
   - сортировка;
   - скачать;
   - **скачать архивом**;
   - архив формируется по выбранным фото/подборке.

5. Из самого грида убрать старые:
   - `Фильтр`;
   - `Настройки отображения`;
   - `Скачать`.

### Сначала проверим точку запуска NiceGUI

Выполни именно через `uv`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

for f in [
    "app/web/main.py",
    "app/web/components/header.py",
    "app/web/components/collections.py",
]:
    print(f"\n================ {f} ================")
    lines = Path(f).read_text().splitlines()

    if f.endswith("main.py"):
        start, end = 1, len(lines)
    elif f.endswith("header.py"):
        start, end = 250, len(lines)
    else:
        start, end = 1, len(lines)

    for i in range(start, min(end, len(lines)) + 1):
        print(f"{i:4}: {lines[i-1]}")
PY
```

Особенно нужен конец `main.py`, где находится `ui.run(...)`.

**Пока ничего не меняем.** После этого я дам один `uv run python`-скрипт, который аккуратно внесёт сохранение пользователя и первоначальное состояние фильтров, с backup перед изменением.

---

### 👤 **User** — 2026-08-19 23:22:42

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

for f in [
    "app/web/main.py",
    "app/web/components/header.py",
    "app/web/components/collections.py",
]:
    print(f"\n================ {f} ================")
    lines = Path(f).read_text().splitlines()

    if f.endswith("main.py"):
        start, end = 1, len(lines)
    elif f.endswith("header.py"):
        start, end = 250, len(lines)
    else:
        start, end = 1, len(lines)

    for i in range(start, min(end, len(lines)) + 1):
        print(f"{i:4}: {lines[i-1]}")
PY

================ app/web/main.py ================
   1: import asyncio
   2: 
   3: from nicegui import ui
   4: 
   5: from app.web.config import HOST, PORT
   6: from app.web.state import STATE
   7: from app.web.components.header import build_header
   8: from app.web.components.search import build_search
   9: from app.web.components.clients import build_clients_panel
  10: from app.web.components.photos import build_photos
  11: from app.web.components.addresses import build_addresses
  12: from app.pipeline.supervisor import supervisor_loop
  13: 
  14: 
  15: # ============================================================
  16: # PIPELINE SUPERVISOR
  17: # ============================================================
  18: 
  19: _supervisor_task = None
  20: 
  21: 
  22: async def start_pipeline_supervisor():
  23:     global _supervisor_task
  24: 
  25:     if (
  26:         _supervisor_task is not None
  27:         and not _supervisor_task.done()
  28:     ):
  29:         print(
  30:             "[WEB] Pipeline Supervisor already running",
  31:             flush=True,
  32:         )
  33:         return
  34: 
  35:     print(
  36:         "[WEB] Starting Pipeline Supervisor",
  37:         flush=True,
  38:     )
  39: 
  40:     _supervisor_task = asyncio.create_task(
  41:         supervisor_loop()
  42:     )
  43: 
  44: 
  45: ui.timer(
  46:     0.1,
  47:     start_pipeline_supervisor,
  48:     once=True,
  49: )
  50: 
  51: 
  52: # ============================================================
  53: # PAGE
  54: # ============================================================
  55: 
  56: @ui.page("/")
  57: def index():
  58: 
  59:     # ========================================================
  60:     # HEADER
  61:     #
  62:     # ui.header() должен быть прямым элементом страницы.
  63:     # ========================================================
  64: 
  65:     build_header()
  66: 
  67:     # ========================================================
  68:     # GLOBAL PAGE
  69:     # ========================================================
  70: 
  71:     with ui.column().classes(
  72:         "w-full h-screen min-h-0 gap-0"
  73:     ).style(
  74:         """
  75:         display:flex;
  76:         flex-direction:column;
  77:         overflow:hidden;
  78:         min-height:0;
  79:         """
  80:     ):
  81: 
  82:         # ====================================================
  83:         # SEARCH
  84:         # ====================================================
  85: 
  86:         with ui.row().classes(
  87:             "w-full shrink-0 items-center px-3 py-1"
  88:         ).style(
  89:             """
  90:             min-height:0;
  91:             """
  92:         ):
  93:             build_search()
  94: 
  95:         # ====================================================
  96:         # ACTION BAR
  97:         #
  98:         # Сразу после поиска.
  99:         # ====================================================
 100: 
 101:         with ui.card().classes(
 102:             "w-full shrink-0 rounded-none"
 103:         ).style(
 104:             """
 105:             height:56px;
 106:             min-height:56px;
 107:             margin:0;
 108:             box-sizing:border-box;
 109:             overflow:hidden;
 110:             """
 111:         ):
 112: 
 113:             with ui.row().classes(
 114:                 "w-full h-full items-center gap-6 px-3"
 115:             ):
 116: 
 117:                 # ------------------------------
 118:                 # FILTERING
 119:                 # ------------------------------
 120: 
 121:                 with ui.row().classes(
 122:                     "items-center gap-2"
 123:                 ):
 124:                     ui.icon(
 125:                         "filter_alt"
 126:                     ).classes(
 127:                         "text-grey-7"
 128:                     )
 129: 
 130:                     with ui.column().classes(
 131:                         "gap-0"
 132:                     ):
 133:                         ui.label(
 134:                             "Фильтрация"
 135:                         ).classes(
 136:                             "text-sm font-bold"
 137:                         )
 138: 
 139:                         ui.label(
 140:                             "Период • дата • адрес • клиент • подборка"
 141:                         ).classes(
 142:                             "text-xs text-grey-6"
 143:                         )
 144: 
 145:                 ui.separator().props(
 146:                     "vertical"
 147:                 )
 148: 
 149:                 # ------------------------------
 150:                 # DISPLAY SETTINGS
 151:                 # ------------------------------
 152: 
 153:                 with ui.row().classes(
 154:                     "items-center gap-2"
 155:                 ):
 156:                     ui.icon(
 157:                         "tune"
 158:                     ).classes(
 159:                         "text-grey-7"
 160:                     )
 161: 
 162:                     with ui.column().classes(
 163:                         "gap-0"
 164:                     ):
 165:                         ui.label(
 166:                             "Настройки отображения"
 167:                         ).classes(
 168:                             "text-sm font-bold"
 169:                         )
 170: 
 171:                         ui.label(
 172:                             "Размер превью • сортировка • направление • Грид / Таблица"
 173:                         ).classes(
 174:                             "text-xs text-grey-6"
 175:                         )
 176: 
 177:                 ui.separator().props(
 178:                     "vertical"
 179:                 )
 180: 
 181:                 # ------------------------------
 182:                 # SELECTION
 183:                 # ------------------------------
 184: 
 185:                 with ui.row().classes(
 186:                     "items-center gap-2"
 187:                 ):
 188:                     ui.icon(
 189:                         "check_circle"
 190:                     ).classes(
 191:                         "text-grey-7"
 192:                     )
 193: 
 194:                     with ui.column().classes(
 195:                         "gap-0"
 196:                     ):
 197:                         ui.label(
 198:                             "Выбрано"
 199:                         ).classes(
 200:                             "text-sm font-bold"
 201:                         )
 202: 
 203:                         ui.label(
 204:                             "Фотографии"
 205:                         ).classes(
 206:                             "text-xs text-grey-6"
 207:                         )
 208: 
 209:                 ui.separator().props(
 210:                     "vertical"
 211:                 )
 212: 
 213:                 # ------------------------------
 214:                 # DOWNLOAD
 215:                 # ------------------------------
 216: 
 217:                 with ui.row().classes(
 218:                     "items-center gap-2"
 219:                 ):
 220:                     ui.icon(
 221:                         "download"
 222:                     ).classes(
 223:                         "text-grey-7"
 224:                     )
 225: 
 226:                     with ui.column().classes(
 227:                         "gap-0"
 228:                     ):
 229:                         ui.label(
 230:                             "Скачать ..."
 231:                         ).classes(
 232:                             "text-sm font-bold"
 233:                         )
 234: 
 235:                         ui.label(
 236:                             "Выбранные фотографии"
 237:                         ).classes(
 238:                             "text-xs text-grey-6"
 239:                         )
 240: 
 241:         # ====================================================
 242:         # MAIN WORKSPACE
 243:         #
 244:         # CLIENTS | PHOTOS | ADDRESSES
 245:         # ====================================================
 246: 
 247:         with ui.row().classes(
 248:             "w-full flex-1 min-h-0 gap-2 p-2"
 249:         ).style(
 250:             """
 251:             display:flex;
 252:             flex-direction:row;
 253:             overflow:hidden;
 254:             min-height:0;
 255:             """
 256:         ):
 257: 
 258:             # =================================================
 259:             # CLIENTS
 260:             # =================================================
 261: 
 262:             with ui.column().classes(
 263:                 "w-[280px] min-w-[280px] h-full min-h-0"
 264:             ).style(
 265:                 """
 266:                 display:flex;
 267:                 flex-direction:column;
 268:                 overflow:hidden;
 269:                 min-height:0;
 270:                 """
 271:             ):
 272: 
 273:                 build_clients_panel(
 274:                     lambda: (
 275:                         STATE.refresh_photos()
 276:                         if STATE.refresh_photos
 277:                         else None
 278:                     )
 279:                 )
 280: 
 281:             # =================================================
 282:             # PHOTOS
 283:             # =================================================
 284: 
 285:             with ui.column().classes(
 286:                 "flex-1 min-w-0 h-full min-h-0"
 287:             ).style(
 288:                 """
 289:                 display:flex;
 290:                 flex-direction:column;
 291:                 overflow:hidden;
 292:                 min-height:0;
 293:                 """
 294:             ):
 295: 
 296:                 refresh_photos = build_photos()
 297: 
 298:                 STATE.refresh_photos = refresh_photos
 299: 
 300:             # =================================================
 301:             # ADDRESSES
 302:             # =================================================
 303: 
 304:             with ui.column().classes(
 305:                 "w-[280px] min-w-[280px] h-full min-h-0"
 306:             ).style(
 307:                 """
 308:                 display:flex;
 309:                 flex-direction:column;
 310:                 overflow:hidden;
 311:                 min-height:0;
 312:                 """
 313:             ):
 314: 
 315:                 build_addresses(
 316:                     lambda: (
 317:                         STATE.refresh_photos()
 318:                         if STATE.refresh_photos
 319:                         else None
 320:                     )
 321:                 )
 322: 
 323:         # ====================================================
 324:         # STATUS BAR
 325:         #
 326:         # Фиксированный нижний ограничитель.
 327:         # Позже сюда:
 328:         # статистика / сообщения / прогресс.
 329:         # ====================================================
 330: 
 331:         with ui.row().classes(
 332:             "w-full shrink-0 items-center px-3"
 333:         ).style(
 334:             """
 335:             height:30px;
 336:             min-height:30px;
 337:             max-height:30px;
 338:             overflow:hidden;
 339:             border-top:1px solid rgba(0,0,0,0.10);
 340:             box-sizing:border-box;
 341:             """
 342:         ):
 343: 
 344:             ui.icon(
 345:                 "info"
 346:             ).classes(
 347:                 "text-grey-6 text-sm"
 348:             )
 349: 
 350:             ui.label(
 351:                 "Готово"
 352:             ).classes(
 353:                 "text-xs text-grey-6"
 354:             )
 355: 
 356: 
 357: # ============================================================
 358: # RUN
 359: # ============================================================
 360: 
 361: ui.run(
 362:     host=HOST,
 363:     port=PORT,
 364:     reload=False,
 365:     title="АЛЬБИОН. ОФИС: Фотобаза. Экраны",
 366: )

================ app/web/components/header.py ================
 250:                                         "Войти",
 251:                                         icon="login",
 252:                                         on_click=check,
 253:                                     ).props(
 254:                                         "dense"
 255:                                     )
 256: 
 257:                                 password_input.on(
 258:                                     "keydown.enter",
 259:                                     lambda e: check(),
 260:                                 )
 261: 
 262:                         password_dialog.open()
 263: 
 264:                     users = get_users()
 265: 
 266:                     with user_list:
 267: 
 268:                         for (
 269:                             user_id,
 270:                             name,
 271:                             color,
 272:                             active,
 273:                         ) in users:
 274: 
 275:                             is_current = (
 276:                                 user_id == STATE.user_id
 277:                             )
 278: 
 279:                             with ui.row().classes(
 280:                                 "w-full items-center px-2 py-1 rounded"
 281:                             ).style(
 282:                                 (
 283:                                     "background: rgba(0,0,0,.06);"
 284:                                     if is_current
 285:                                     else ""
 286:                                 )
 287:                             ):
 288: 
 289:                                 # Цветовой индикатор
 290:                                 ui.element(
 291:                                     "div"
 292:                                 ).style(
 293:                                     f"""
 294:                                     width: 14px;
 295:                                     height: 14px;
 296:                                     min-width: 14px;
 297:                                     border-radius: 50%;
 298:                                     background: {color};
 299:                                     border: 1px solid rgba(0,0,0,.2);
 300:                                     """
 301:                                 )
 302: 
 303:                                 if is_current:
 304: 
 305:                                     ui.label(
 306:                                         name
 307:                                     ).classes(
 308:                                         "flex-grow text-left px-2 py-2 font-bold"
 309:                                     )
 310: 
 311:                                     ui.label(
 312:                                         "Текущий"
 313:                                     ).classes(
 314:                                         "text-xs text-primary font-medium px-2"
 315:                                     )
 316: 
 317:                                 else:
 318: 
 319:                                     ui.button(
 320:                                         name,
 321:                                         on_click=lambda e,
 322:                                         uid=user_id,
 323:                                         n=name,
 324:                                         c=color:
 325:                                             password_dialog(
 326:                                                 uid,
 327:                                                 n,
 328:                                                 c,
 329:                                             ),
 330:                                     ).props(
 331:                                         "flat"
 332:                                     ).classes(
 333:                                         "flex-grow justify-start"
 334:                                     )
 335: 
 336:                     ui.separator().classes(
 337:                         "my-2"
 338:                     )
 339: 
 340:                     ui.button(
 341:                         "Закрыть",
 342:                         on_click=dialog.close,
 343:                     ).props(
 344:                         "flat"
 345:                     )
 346: 
 347:             dialog.open()
 348: 
 349:         user_button.on(
 350:             "click",
 351:             open_user_switcher,
 352:         )
 353: 
 354:         # ----------------------------------------------------
 355:         # TECHNICAL
 356:         # ----------------------------------------------------
 357: 
 358:         ui.button(
 359:             "Технический раздел",
 360:             icon="settings",
 361:             on_click=show_technical,
 362:         ).props(
 363:             "unelevated dense"
 364:         ).classes(
 365:             "min-w-[190px] font-medium"
 366:         ).style(
 367:             """
 368:             background: white !important;
 369:             color: #333 !important;
 370:             z-index: 100000 !important;
 371:             """
 372:         )
 373: 
 374:     # ========================================================
 375:     # INITIAL COLOR
 376:     # ========================================================
 377: 
 378:     try:
 379: 
 380:         users = get_users()
 381: 
 382:         for (
 383:             user_id,
 384:             name,
 385:             color,
 386:             active,
 387:         ) in users:
 388: 
 389:             if name == STATE.manager:
 390: 
 391:                 STATE.user_id = user_id
 392: 
 393:                 apply_user_color(
 394:                     color
 395:                 )
 396: 
 397:                 break
 398: 
 399:     except Exception as exc:
 400: 
 401:         print(
 402:             "[USER INIT ERROR]",
 403:             repr(exc),
 404:             flush=True,
 405:         )

================ app/web/components/collections.py ================
   1: from nicegui import ui
   2: 
   3: from app.web.state import STATE, Collection
   4: 
   5: 
   6: def add_collection(scope="addresses"):
   7: 
   8:     with ui.dialog() as dialog, ui.card().classes("w-96"):
   9: 
  10:         ui.label(
  11:             "Новая подборка"
  12:         ).classes(
  13:             "text-lg font-bold"
  14:         )
  15: 
  16:         name = ui.input(
  17:             "Название"
  18:         ).props(
  19:             "outlined autofocus"
  20:         ).classes(
  21:             "w-full"
  22:         )
  23: 
  24:         kind = ui.select(
  25:             ["Моя", "Клиентская"],
  26:             value="Моя",
  27:             label="Тип",
  28:         ).props(
  29:             "outlined"
  30:         ).classes(
  31:             "w-full"
  32:         )
  33: 
  34:         client = ui.select(
  35:             [
  36:                 "Единая Россия",
  37:                 "Яндекс",
  38:                 "Самокат",
  39:                 "Сбер",
  40:                 "Ozon",
  41:                 "Бетсити",
  42:                 "Альбион-Тур",
  43:             ],
  44:             label="Клиент",
  45:         ).props(
  46:             "outlined"
  47:         ).classes(
  48:             "w-full"
  49:         )
  50: 
  51:         with ui.row().classes(
  52:             "justify-end w-full"
  53:         ):
  54: 
  55:             ui.button(
  56:                 "Отмена",
  57:                 on_click=dialog.close,
  58:             ).props(
  59:                 "flat"
  60:             )
  61: 
  62:             def save():
  63: 
  64:                 title = str(
  65:                     name.value or ""
  66:                 ).strip()
  67: 
  68:                 if not title:
  69:                     ui.notify(
  70:                         "Введите название",
  71:                         type="warning",
  72:                     )
  73:                     return
  74: 
  75:                 STATE.collections.append(
  76:                     Collection(
  77:                         name=title,
  78:                         kind=kind.value or "Моя",
  79:                         client=client.value or "",
  80:                         scope=scope,
  81:                         members=set(),
  82:                     )
  83:                 )
  84: 
  85:                 ui.notify(
  86:                     f"Подборка «{title}» создана",
  87:                     type="positive",
  88:                 )
  89: 
  90:                 dialog.close()
  91:                 ui.navigate.reload()
  92: 
  93:             ui.button(
  94:                 "Создать",
  95:                 on_click=save,
  96:             ).props(
  97:                 "unelevated"
  98:             )
  99: 
 100:     dialog.open()
 101: 
 102: 
 103: def get_collections(scope):
 104: 
 105:     return [
 106:         collection
 107:         for collection in STATE.collections
 108:         if getattr(
 109:             collection,
 110:             "scope",
 111:             "addresses",
 112:         ) == scope
 113:     ]
 114: 
 115: 
 116: def build_collections(
 117:     scope,
 118:     on_change=None,
 119: ):
 120: 
 121:     collections = get_collections(
 122:         scope
 123:     )
 124: 
 125:     if not collections:
 126:         return
 127: 
 128:     with ui.column().classes(
 129:         "w-full gap-0"
 130:     ):
 131: 
 132:         with ui.row().classes(
 133:             "w-full items-center justify-between"
 134:         ):
 135: 
 136:             ui.label(
 137:                 "Подборки"
 138:             ).classes(
 139:                 "text-sm font-medium"
 140:             )
 141: 
 142:             ui.button(
 143:                 icon="add",
 144:                 on_click=lambda: add_collection(
 145:                     scope
 146:                 ),
 147:             ).props(
 148:                 "flat dense round"
 149:             ).tooltip(
 150:                 "Добавить подборку"
 151:             )
 152: 
 153:         with ui.column().classes(
 154:             "w-full max-h-32 overflow-y-auto"
 155:         ):
 156: 
 157:             for collection in collections:
 158: 
 159:                 checked = (
 160:                     collection.name
 161:                     in STATE.selected_collections
 162:                 )
 163: 
 164:                 with ui.row().classes(
 165:                     "w-full items-center gap-1"
 166:                 ):
 167: 
 168:                     def change_collection(
 169:                         e,
 170:                         selected=collection,
 171:                     ):
 172: 
 173:                         if e.value:
 174:                             STATE.selected_collections.add(
 175:                                 selected.name
 176:                             )
 177:                         else:
 178:                             STATE.selected_collections.discard(
 179:                                 selected.name
 180:                             )
 181: 
 182:                         if on_change:
 183:                             on_change()
 184: 
 185:                     ui.checkbox(
 186:                         value=checked,
 187:                         on_change=change_collection,
 188:                     ).props(
 189:                         "dense"
 190:                     )
 191: 
 192:                     ui.label(
 193:                         f"{collection.name} "
 194:                         f"({len(collection.members)})"
 195:                     ).classes(
 196:                         "truncate flex-grow"
 197:                     )
 198: 
 199:     ui.separator().classes(
 200:         "my-2"
 201:     )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 23:22:44

> ****
>
> 
>
> **Used personal_context tool**
>
> 
>
> Worked for 14s

Да. Продолжаем от текущего состояния.

Следующим шагом я бы **не трогал уже работающую верстку**, а сначала сделал авторизацию/состояние пользователя правильно: `Гость` только при первом входе, а при наличии сохранённого пользователя - восстанавливать его.

После этого уже подключим строку кнопок грида и архивы подборок.

Сейчас выполни через `uv` этот диагностический блок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ CONFIG ================" && \
sed -n '1,260p' app/web/config.py && \
echo "================ PHOTOS ================" && \
sed -n '1,420p' app/web/components/photos.py && \
echo "================ CLIENTS ================" && \
sed -n '1,420p' app/web/components/clients.py && \
echo "================ ADDRESSES ================" && \
sed -n '1,420p' app/web/components/addresses.py && \
echo "================ STORAGE / COOKIES SEARCH ================" && \
grep -RniE \
'app\.storage|storage\.user|storage\.browser|cookie|localStorage|sessionStorage|display|grid|table|download|archive|zip' \
app/web \
--include="*.py" | head -n 300
```

И отдельно проверим, какие параметры запуска NiceGUI уже есть:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import inspect
from nicegui import app

print("NiceGUI app.storage:")
print(type(app.storage))
print()

print("storage attributes:")
print([x for x in dir(app.storage) if not x.startswith("_")])
PY
```

**Важно:** пока ничего не меняй. По этим двум выводам я дам один точный патч через `uv run python`, чтобы:

1. `Гость` был первоначальным пользователем.
2. Последний пользователь сохранялся в cookie/browser storage.
3. При следующем открытии автоматически восстанавливался именно он.
4. Его настройки отображения/фильтров тоже можно было привязать к сохранённому состоянию, не ломая текущий `STATE`.
5. Затем вынесем **Грид / Таблица / размер / сортировку / направление** в строку действий.
6. `Скачать` сделаем отдельной кнопкой, а рядом - **«Скачать подборку»**, которая будет собирать отмеченные чекбоксами фото в ZIP.

---

