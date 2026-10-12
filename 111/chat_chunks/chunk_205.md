## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 🤖 **Assistant** — 2026-08-20 21:18:22

Да. И я бы сейчас **не восстанавливал старую архитектуру грида**. По тем файлам, которые ты показал, уже видно, что старый `PHOTO_INDEX` стал лишним промежуточным слоем.

Новая логика должна быть такой:

```text
                    PostgreSQL / photos
                           │
             ┌─────────────┴─────────────┐
             │                           │
        DINO + Hybrid                  Qwen
             │                           │
        final address                  client
             │                           │
             └─────────────┬─────────────┘
                           │
                    ФИЛЬТРЫ UI
                 ┌─────────┴─────────┐
                 │                   │
             адрес выбран?       клиент выбран?
                 │                   │
                 └─────────┬─────────┘
                           │
                         GRID
                           │
                    source_path
                  / preview_path
```

### Ключевой момент

**PSQL — единый источник данных для грида.**

Не:

```text
PSQL → построить PHOTO_INDEX → взять адреса → потом искать файлы
```

а:

```text
PSQL → SELECT нужные фотографии → применить фильтры → GRID
```

При этом:

- **адрес** берём из `hybrid_final_id`, а если его нет — из `dino_fingerprint`;
- **клиента** берём из `client`, который появляется после Qwen;
- если `client IS NULL` или пустой — это **«Другие»**;
- Qwen не должен запускаться для построения списка клиентов — его результат просто появляется в PSQL;
- при появлении результата Qwen фотография автоматически начинает относиться к соответствующему клиенту;
- до этого она находится в **«Другие»**;
- физический файл берём по `source_path`/`path`;
- `preview_path` используем для быстрого отображения, если он существует.

И тогда поведение будет именно таким, как ты описал:

### Например

Фото №123:

```text
dino_fingerprint = 85_v33
hybrid_final_id = 85_v33
client = NULL
qwen_status = pending
```

Грид видит:

```text
address = 85
client = Другие
```

Если выбраны:

```text
Адреса:
☑ 85

Клиенты:
☑ Яндекс
☑ Другие
```

фото показывается.

После Qwen:

```text
client = Яндекс
qwen_status = done
```

та же запись **без каких-либо переносов файла** начинает попадать в:

```text
Яндекс
```

и исчезает из:

```text
Другие
```

если «Другие» не выбран.

Это гораздо чище.

---

## А сейчас нам надо проверить реальную структуру PSQL

Твоя команда сломалась только потому, что на Ubuntu нет `python`, есть `python3`.

Запусти **вот этот блок целиком**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="lora",
    dbname="photobase",
)

cur = conn.cursor()

print("=" * 70)
print("TABLES")
print("=" * 70)

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")

for row in cur.fetchall():
    print(row[0])

print()
print("=" * 70)
print("PHOTOS COLUMNS")
print("=" * 70)

cur.execute("""
    SELECT
        ordinal_position,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'photos'
    ORDER BY ordinal_position
""")

for position, name, data_type in cur.fetchall():
    print(f"{position:3}  {name:30} {data_type}")

print()
print("=" * 70)
print("PHOTO COUNTS")
print("=" * 70)

cur.execute("""
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (
            WHERE hybrid_final_id IS NOT NULL
              AND TRIM(hybrid_final_id) <> ''
        ) AS hybrid_done,
        COUNT(*) FILTER (
            WHERE dino_fingerprint IS NOT NULL
              AND TRIM(dino_fingerprint) <> ''
        ) AS dino_done,
        COUNT(*) FILTER (
            WHERE client IS NOT NULL
              AND TRIM(client) <> ''
        ) AS client_done
    FROM photos
""")

print(cur.fetchone())

print()
print("=" * 70)
print("ADDRESSES")
print("=" * 70)

cur.execute("""
    SELECT
        COALESCE(
            NULLIF(TRIM(hybrid_final_id), ''),
            NULLIF(TRIM(dino_fingerprint), '')
        ) AS fingerprint,
        COUNT(*)
    FROM photos
    WHERE COALESCE(
        NULLIF(TRIM(hybrid_final_id), ''),
        NULLIF(TRIM(dino_fingerprint), '')
    ) IS NOT NULL
    GROUP BY 1
    ORDER BY 1
""")

for row in cur.fetchall():
    print(row)

print()
print("=" * 70)
print("CLIENTS")
print("=" * 70)

cur.execute("""
    SELECT
        CASE
            WHEN client IS NULL OR TRIM(client) = ''
                THEN 'Другие'
            ELSE TRIM(client)
        END AS client_name,
        COUNT(*)
    FROM photos
    GROUP BY 1
    ORDER BY LOWER(1)
""")

for row in cur.fetchall():
    print(row)

print()
print("=" * 70)
print("SAMPLE")
print("=" * 70)

cur.execute("""
    SELECT
        id,
        photo_id,
        source_path,
        path,
        preview_path,
        dino_fingerprint,
        dino_status,
        hybrid_final_id,
        hybrid_score,
        hybrid_margin,
        client,
        qwen_status,
        sort_status
    FROM photos
    ORDER BY id DESC
    LIMIT 10
""")

columns = [d[0] for d in cur.description]

for row in cur.fetchall():
    print(dict(zip(columns, row)))

cur.close()
conn.close()
PY
```

### Зачем это нужно

Особенно хочу увидеть `SAMPLE`.

Потому что после него мы сможем сделать **новый `photo_db.py`**, примерно с такой моделью:

```python
get_grid_photos(
    selected_addresses,
    selected_clients,
    search_query,
    date_from,
    date_to,
)
```

и SQL будет сразу делать нужную выборку.

То есть `photos.py` больше не будет:

```python
build_photo_index()
```

сканировать фотографии и создавать виртуальные адресные папки.

А будет примерно:

```text
build_photos()
       ↓
get_grid_photos_from_postgres()
       ↓
SQL WHERE
   address
   client
   dates
   search
       ↓
GRID
```

---

### И ещё одно важное изменение

Сейчас в `state.py` у нас есть явная проблема:

```python
clients = [
    "Все клиенты",
    "Единая Россия",
    "Яндекс",
    ...
]
```

и:

```python
addresses = [
    "78",
    "79",
    ...
]
```

**Это надо убрать.**

Они больше не должны быть частью состояния приложения.

Должно быть:

```python
clients = []
addresses = []
```

или вообще не хранить полный список в `STATE`, а получать его из PSQL при построении панели.

Потому что иначе у нас одновременно существуют две базы:

```text
STATE.clients       ← старая искусственная
PSQL.photos.client  ← настоящая
```

и

```text
STATE.addresses     ← сейчас формируется из DINO
PSQL                ← настоящий backend
```

Это и создаёт нынешнюю путаницу.

---

## Предлагаю сделать именно новый слой

Не чинить старую цепочку `PHOTO_INDEX → addresses → grid`, а заменить её:

**1. `photo_db.py`**

Единый SQL API для грида.

**2. `clients.py`**

Только отображает:

```text
Все
Другие
Яндекс
Сбер
...
```

полученные из PSQL.

**3. `addresses.py`**

Только отображает адреса, вычисленные из:

```text
hybrid_final_id
    ↓ если нет
dino_fingerprint
```

из PSQL.

**4. `photos.py`**

Вообще не знает о физических каталогах `output/daily`.

Он получает уже готовые записи:

```python
[
    {
        "id": ...,
        "address": "85",
        "client": "Яндекс",
        "source_path": "...",
        "preview_path": "...",
        ...
    }
]
```

и рисует грид.

**5. Qwen**

Ничего специально для грида не делает.

Просто пишет:

```text
photos.client
photos.qwen_status
...
```

и при следующем обновлении грида фотография автоматически оказывается в правильном клиенте.

Это как раз соответствует твоей новой архитектуре: **DINO + Hybrid определяют адрес, Qwen определяет клиента, PostgreSQL хранит оба результата, грид является отображением SQL-выборки.**

Сначала дай вывод команды выше. По нему уже можно без гадания написать новый слой выборки.

---

### 👤 **User** — 2026-08-20 21:19:56

в PSQL добавить пока еще неиспользуемые поля: оригинальное имя файла, присвоенныйюридический адрес, упрощенный адрес

---

### 🤖 **Assistant** — 2026-08-20 21:19:57

Да. Это как раз лучше сделать **сейчас, до переделки грида**, чтобы новая архитектура сразу опиралась на правильную модель данных.

Я бы добавил в `photos` три отдельных поля:

```text id="psql-fields"
original_filename   — оригинальное имя файла
legal_address       — присвоенный юридический адрес
simple_address      — упрощённый адрес
```

Но есть важный момент: у тебя **`original_filename` уже существует** в текущем `SELECT` `photo_db.py`:

```python
original_filename,
```

То есть сначала надо проверить схему PSQL — возможно, это поле уже есть и добавлять его повторно не нужно.

### Предлагаю такую семантику

| Поле | Назначение | Кто заполняет |
|---|---|---|
| `original_filename` | Имя файла до переименований/обработки | импорт |
| `legal_address` | Полный юридический адрес объекта | отдельная логика/позже |
| `simple_address` | Упрощённое представление адреса для UI/поиска | отдельная логика/позже |

При этом:

```text id="psql-flow"
DINO + Hybrid
      ↓
hybrid_final_id
      ↓
адрес распознавания
```

и отдельно:

```text id="qwen-flow"
Qwen
  ↓
client
```

а в будущем:

```text id="address-flow"
hybrid_final_id
      ↓
legal_address
      ↓
simple_address
```

То есть **не надо смешивать `hybrid_final_id` с юридическим адресом**.

Например:

```text
hybrid_final_id = 85

legal_address = "г. Москва, ул. Ленина, д. 15"

simple_address = "Ленина 15"
```

Это три разных сущности.

### Сейчас выполни проверку

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="lora",
    dbname="photobase",
)

cur = conn.cursor()

cur.execute("""
    SELECT
        ordinal_position,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'photos'
    ORDER BY ordinal_position
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
PY
```

Если `original_filename` действительно уже есть, добавим только:

```sql
ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS legal_address TEXT,
    ADD COLUMN IF NOT EXISTS simple_address TEXT;
```

Я бы сделал именно `TEXT`, а не `VARCHAR(n)`: ограничения длины здесь никакой пользы не дают.

После этого **эти поля пока оставляем `NULL`**. Не надо искусственно заполнять их текущими данными. Они станут частью новой модели PSQL и будут готовы для следующего этапа.

И ещё: `client`, `legal_address`, `simple_address` лучше рассматривать как **результаты обогащения фотографии**, а `hybrid_final_id` — как результат распознавания адресной группы. Это позволит нам потом нормально разделить DINO/Hybrid, Qwen и адресную справочную информацию.

---

### 👤 **User** — 2026-08-20 21:20:43

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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="lora",
    dbname="photobase",
)

cur = conn.cursor()

cur.execute("""
    SELECT
        ordinal_position,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'photos'
    ORDER BY ordinal_position
PYnn.close()w).fetchall():
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ModuleNotFoundError: No module named 'psycopg2'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 21:20:45

Да, здесь всё понятно: **системный `python3` не тот Python**, в котором установлен проект и `psycopg2`.

У тебя проект работает через `.venv`, поэтому не надо ничего устанавливать в системный Python.

### 1. Проверяем Python проекта

```bash
cd ~/projects/scene_fingerprint_mvp_v02

.venv/bin/python -c "import psycopg2; print('psycopg2 OK')"
```

Если получим:

```text
psycopg2 OK
```

то используем именно его.

### 2. Сразу посмотрим структуру `photos`

```bash
cd ~/projects/scene_fingerprint_mvp_v02

.venv/bin/python - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="lora",
    dbname="photobase",
)

cur = conn.cursor()

print("=" * 70)
print("PHOTOS COLUMNS")
print("=" * 70)

cur.execute("""
    SELECT
        ordinal_position,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'photos'
    ORDER BY ordinal_position
""")

for position, name, data_type in cur.fetchall():
    print(f"{position:3}  {name:30} {data_type}")

print()
print("=" * 70)
print("PHOTO COUNTS")
print("=" * 70)

cur.execute("""
    SELECT
        COUNT(*) AS total,

        COUNT(*) FILTER (
            WHERE hybrid_final_id IS NOT NULL
              AND TRIM(hybrid_final_id) <> ''
        ) AS hybrid_done,

        COUNT(*) FILTER (
            WHERE dino_fingerprint IS NOT NULL
              AND TRIM(dino_fingerprint) <> ''
        ) AS dino_done,

        COUNT(*) FILTER (
            WHERE client IS NOT NULL
              AND TRIM(client) <> ''
        ) AS client_done
    FROM photos
""")

print(cur.fetchone())

print()
print("=" * 70)
print("CLIENTS INCLUDING OTHER")
print("=" * 70)

cur.execute("""
    SELECT
        CASE
            WHEN client IS NULL OR TRIM(client) = ''
                THEN 'Другие'
            ELSE TRIM(client)
        END AS client_name,
        COUNT(*) AS photo_count
    FROM photos
    GROUP BY 1
    ORDER BY LOWER(1)
""")

for row in cur.fetchall():
    print(row)

print()
print("=" * 70)
print("SAMPLE PHOTOS")
print("=" * 70)

cur.execute("""
    SELECT
        id,
        photo_id,
        filename,
        original_filename,
        source_path,
        preview_path,
        dino_fingerprint,
        dino_status,
        hybrid_final_id,
        hybrid_score,
        hybrid_margin,
        client,
        qwen_status
    FROM photos
    ORDER BY id DESC
    LIMIT 10
""")

columns = [desc[0] for desc in cur.description]

for row in cur.fetchall():
    print(dict(zip(columns, row)))

cur.close()
conn.close()
PY
```

Это даст нам точную картину **без изменения БД**.

---

### 3. После этого добавим два новых поля

Поскольку `original_filename` в твоём `photo_db.py` уже выбирается:

```python
original_filename,
```

**его пока не трогаем** — сначала проверяем, что оно реально есть в PSQL.

Добавляем только:

```sql
legal_address
simple_address
```

Команда будет:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

.venv/bin/python - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="lora",
    dbname="photobase",
)

conn.autocommit = True

cur = conn.cursor()

cur.execute("""
    ALTER TABLE photos
        ADD COLUMN IF NOT EXISTS legal_address TEXT,
        ADD COLUMN IF NOT EXISTS simple_address TEXT
""")

print("OK: legal_address, simple_address")

cur.close()
conn.close()
PY
```

Но **вторую команду пока лучше не запускать**, пока не увидим вывод первой. Возможно, `original_filename` или другие необходимые поля уже есть/имеют другую структуру.

И главное: мы сейчас не пытаемся чинить старый `PHOTO_INDEX`. Мы сначала **фиксируем структуру PSQL**, затем строим новый SQL-источник грида поверх неё.

---

### 👤 **User** — 2026-08-20 21:21:00

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

.venv/bin/python -c "import psycopg2; print('psycopg2 OK')"
psycopg2 OK
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 21:21:01

Да. Теперь можем работать **через `.venv/bin/python`**, и это правильный Python для проекта.

И я бы сейчас **не восстанавливал старую логику грида**. С учетом того, что мы уже зафиксировали архитектуру, лучше сделать новый слой отображения поверх PostgreSQL.

### Фиксируем новую архитектуру

**Источник грида — только PostgreSQL `photos`.**

Поток:

```text
Фото
  │
  ▼
DINO
  │
  ▼
Hybrid
  │
  ├── address              ← уже известен
  ├── dino/hybrid status
  └── остальные поля
  │
  ▼
PostgreSQL.photos
  │
  ├──────────────► ГРИД
  │                 │
  │                 ├─ фильтр адресов
  │                 └─ фильтр клиентов
  │
  └──────────────► Qwen
                      │
                      ├─ client
                      ├─ brand
                      ├─ description
                      └─ прочий анализ
```

При этом **Qwen не участвует в определении того, какое фото вообще существует для грида**. Фото появляется в гриде уже после записи результата DINO/Hybrid в PostgreSQL.

А клиент — дополнительное свойство записи:

```text
client = NULL / ''
        ↓
клиент еще неизвестен
        ↓
фото относится к "Другие"
```

Когда Qwen определил клиента:

```text
client = "Яндекс"
        ↓
фото начинает попадать под фильтр "Яндекс"
```

Это значительно чище.

---

## И поля PSQL тоже сейчас стоит заложить правильно

Ты предложил:

1. оригинальное имя файла;
2. присвоенный юридический адрес;
3. упрощённый адрес.

Причём я бы **не переиспользовал существующее `address` для юридического адреса**.

Лучше разделить семантику:

```text
address
    ↓
адрес, определённый DINO/Hybrid
    например: "78"

legal_address
    ↓
присвоенный юридический адрес
    например: "г. Москва, ул. Ленина, д. 15"

simple_address
    ↓
упрощённое отображаемое имя
    например: "Ленина 15"
```

И:

```text
original_filename
    ↓
исходное имя файла
```

У тебя `original_filename` **уже присутствует в `get_photo_records()`**, значит сначала надо проверить, действительно ли колонка уже есть в PostgreSQL. Возможно, она уже создана, а мы просто хотим добавить две новые.

### Сейчас выполни одну команду

Она использует правильное окружение и просто покажет структуру `photos`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
.venv/bin/python - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="lora",
    dbname="photobase",
)

cur = conn.cursor()

cur.execute("""
    SELECT
        ordinal_position,
        column_name,
        data_type,
        is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'photos'
    ORDER BY ordinal_position
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
PY
```

**Пока ничего в БД не меняем.**

После этого я дам точный `ALTER TABLE`, исходя из фактической структуры. Затем уже можно сделать новый `photo_grid`-слой, который будет получать SQL-выборку примерно такой логики:

```sql
WHERE
    address IN (...)
AND
    (
        client IN (...)
        OR client IS NULL
        OR TRIM(client) = ''
    )
```

Но конкретное поведение `"Другие"` лучше зафиксировать отдельно: **при выборе конкретного клиента показывать только этого клиента или ещё и неопределённых клиентов?** По твоему последнему описанию я понимаю, что **неопределённые должны оставаться видимыми как «Другие»**, то есть они не должны исчезать из грида из-за клиентского фильтра.

---

### 👤 **User** — 2026-08-20 21:21:19

PHOTOS COLUMNS
======================================================================
  1  id                             bigint
  2  photo_id                       text
  3  source_path                    text
  4  path                           text
  5  filename                       text
  6  original_filename              text
  7  address                        text
  8  client                         text
  9  brand                          text
 10  category                       text
 11  description                    text
 12  status                         text
 13  dino_status                    text
 14  qwen_status                    text
 15  sort_status                    text
 16  preview_status                 text
 17  error_message                  text
 18  dino_fingerprint               text
 19  dino_score                     double precision
 20  dino_second_score              double precision
 21  dino_margin                    double precision
 22  dino_time_sec                  double precision
 23  hybrid_original_id             text
 24  hybrid_final_id                text
 25  hybrid_changed                 boolean
 26  hybrid_old_score               double precision
 27  hybrid_score                   double precision
 28  hybrid_margin                  double precision
 29  hybrid_neighbors               jsonb
 30  confidence                     integer
 31  qwen_time_sec                  double precision
 32  text_json                      jsonb
 33  colors_json                    jsonb
 34  objects_json                   jsonb
 35  environment_json               jsonb
 36  image_quality_json             jsonb
 37  camera_view_json               jsonb
 38  scene_objects_json             jsonb
 39  analysis_quality_json          jsonb
 40  raw_json                       jsonb
 41  preview_path                   text
 42  created_at                     timestamp without time zone
 43  updated_at                     timestamp without time zone
 44  source_id                      text
 45  address_id                     text
 46  initial_id                     text
 47  dino_started_at                timestamp without time zone
 48  qwen_started_at                timestamp without time zone

======================================================================
PHOTO COUNTS
======================================================================
(526, 0, 519, 395)

======================================================================
CLIENTS INCLUDING OTHER
======================================================================
Traceback (most recent call last):
  File "<stdin>", line 63, in <module>
psycopg2.errors.UndefinedFunction: function lower(integer) does not exist
LINE 11:     ORDER BY LOWER(1)
                      ^
HINT:  No function matches the given name and argument types. You might need to add explicit type casts.

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 21:21:20

Отлично. Теперь структура БД понятна, и она как раз подтверждает, что **старый грид лучше не восстанавливать**.

### Что уже есть

В `photos` уже присутствует:

```text
original_filename
address
client
address_id
hybrid_final_id
dino_status
qwen_status
...
```

Поэтому добавлять `original_filename` **не нужно**.

Нам нужны только два новых поля:

```text
legal_address   text
simple_address  text
```

Я бы именно так их и назвал.

### Что означают поля

Предлагаю окончательно закрепить:

| Поле | Назначение | Кто заполняет |
|---|---|---|
| `original_filename` | исходное имя файла | импорт |
| `address` | результат DINO + Hybrid, например `78` | DINO/Hybrid |
| `address_id` | технический ID адреса | backend |
| `legal_address` | полный юридический адрес | отдельная логика/справочник |
| `simple_address` | короткое отображаемое название | отдельная логика/справочник |
| `client` | клиент, определённый Qwen | Qwen |

То есть **не смешиваем машинный адрес DINO с человеческим адресом**.

---

### По клиентам тоже всё становится понятно

Ошибка:

```text
function lower(integer) does not exist
```

— это просто ошибка SQL-запроса проверки, а **не проблема данных**. Где-то в запросе получилось `LOWER(1)` вместо `LOWER(client)`.

Но самое главное: нам вообще не нужно сейчас строить отдельную таблицу клиентов для грида.

Клиенты уже являются данными `photos.client`.

Логика может быть:

```text
photos
│
├── address = "78"
│
├── client = "Яндекс"
│
├── client = "Сбер"
│
└── client = NULL
```

А UI динамически строит список клиентов из PostgreSQL:

```text
☑ Все
☑ Яндекс       37
☑ Сбер         21
☑ Самокат      14
☑ Другие       83
```

Где **«Другие» = `client IS NULL OR trim(client) = ''`**.

Это очень важный момент: `"Другие"` — не искусственный клиент в БД. Это представление неопределённых клиентов.

---

## И я предлагаю немного изменить твою последнюю логику

Если выбран:

```text
Адреса:
☑ 78
☑ 83

Клиенты:
☑ Яндекс
☑ Другие
```

то SQL-логика грида:

```sql
address IN ('78', '83')
AND (
    lower(trim(client)) = 'яндекс'
    OR client IS NULL
    OR trim(client) = ''
)
```

То есть:

**DINO/Hybrid определяет множество фотографий по адресу.  
Qwen постепенно уточняет принадлежность к клиенту.  
Грид всегда показывает актуальное состояние PostgreSQL.**

И поэтому когда Qwen закончил анализ очередной фотографии и записал:

```text
client = 'Яндекс'
qwen_status = 'done'
```

фото **автоматически переезжает из «Другие» в «Яндекс»**, без изменения самого файла и без перестройки локального индекса.

Это именно та архитектура, которая сейчас нужна.

---

### Следующий шаг

Сначала добавим два поля:

```sql
ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS legal_address text,
    ADD COLUMN IF NOT EXISTS simple_address text;
```

Я бы сделал это **отдельной миграцией**, а не встраивал случайно в существующий код.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
.venv/bin/python - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="lora",
    dbname="photobase",
)

conn.autocommit = True

cur = conn.cursor()

cur.execute("""
    ALTER TABLE photos
        ADD COLUMN IF NOT EXISTS legal_address text,
        ADD COLUMN IF NOT EXISTS simple_address text
""")

cur.execute("""
    SELECT
        ordinal_position,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'photos'
      AND column_name IN (
          'original_filename',
          'address',
          'address_id',
          'legal_address',
          'simple_address',
          'client'
      )
    ORDER BY ordinal_position
""")

print("RELEVANT PHOTOS COLUMNS")
print("=" * 70)

for position, name, data_type in cur.fetchall():
    print(f"{position:3}  {name:<22} {data_type}")

cur.close()
conn.close()
PY
```

После этого уже **не будем латать `addresses.py` и `clients.py` по старой архитектуре**. Следующим шагом сделаем новый источник данных грида: **один SQL-запрос к `photos` + применение `STATE.selected_addresses` и `STATE.selected_clients`**, а Qwen-поля будут подхватываться из той же записи PostgreSQL.

---

### 👤 **User** — 2026-08-20 21:22:27

у меня uv

---

### 🤖 **Assistant** — 2026-08-20 21:22:28

Да, тогда лучше использовать **`uv run`**, а не напрямую `.venv/bin/python`.

Для миграции:

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

conn.autocommit = True

cur = conn.cursor()

cur.execute("""
    ALTER TABLE photos
        ADD COLUMN IF NOT EXISTS legal_address text,
        ADD COLUMN IF NOT EXISTS simple_address text
""")

cur.execute("""
    SELECT
        ordinal_position,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'photos'
      AND column_name IN (
          'original_filename',
          'address',
          'address_id',
          'legal_address',
          'simple_address',
          'client'
      )
    ORDER BY ordinal_position
""")

print("RELEVANT PHOTOS COLUMNS")
print("=" * 70)

for position, name, data_type in cur.fetchall():
    print(f"{position:3}  {name:<22} {data_type}")

cur.close()
conn.close()
PY
```

Это соответствует твоему проекту с `uv` и использует зависимости из проекта.

**После выполнения пока ничего больше не меняем.** Покажи вывод — проверим, что поля появились, и затем перейдём к новому источнику грида.

---

### 👤 **User** — 2026-08-20 21:22:45

conn.autocommit = True

cur = conn.cursor()

cur.execute("""
    ALTER TABLE photos
        ADD COLUMN IF NOT EXISTS legal_address text,
        ADD COLUMN IF NOT EXISTS simple_address text
""")

cur.execute("""
    SELECT
PYnn.close(){position:3}  {name:<22} {data_type}")
RELEVANT PHOTOS COLUMNS
======================================================================
  6  original_filename      text
  7  address                text
  8  client                 text
 45  address_id             text
 49  legal_address          text
 50  simple_address         text

---

### 🤖 **Assistant** — 2026-08-20 21:22:47

Отлично. **БД подготовлена правильно.** Теперь имеем чистую основу для нового грида.

### Фиксируем структуру `photos`

```text
original_filename   ← оригинал файла
address             ← результат DINO + Hybrid
address_id          ← технический ID
legal_address       ← полный юридический адрес
simple_address      ← короткий адрес для UI
client              ← результат Qwen
```

И главное — теперь можно полностью отказаться от старой идеи, где грид пытается собирать фотографии из физических `output/daily` папок.

### Новый принцип грида

```text
                    PostgreSQL.photos
                           │
             ┌─────────────┴─────────────┐
             │                           │
        DINO + Hybrid                  Qwen
             │                           │
          address                      client
             │                           │
             └─────────────┬─────────────┘
                           │
                           ▼
                     PHOTO GRID
                           │
                ┌──────────┴──────────┐
                │                     │
          фильтр адресов        фильтр клиентов
```

Фото берём **из PSQL**, а не сканируем папки.

---

### Поведение клиента

Это тоже теперь можно сделать очень просто.

`client`:

```text
"Яндекс"       → клиент Яндекс
"Сбер"         → клиент Сбер
NULL / ""      → Другие
```

Причём `Другие` **не записываем в БД**.

Если Qwen ещё не обработал фото:

```text
qwen_status = pending
client = NULL
```

оно попадает в:

```text
Другие
```

После Qwen:

```text
qwen_status = done
client = "Яндекс"
```

оно автоматически становится:

```text
Яндекс
```

---

## Но есть ещё один важный момент

Твой вывод:

```text
526 total
0 ...
519 ...
395 ...
```

показывает, что в БД уже есть **526 записей**, поэтому перед написанием нового грида я бы **не трогал существующие записи вообще**.

Нам нужно только сделать новый слой чтения:

```text
app/web/
    photo_grid_db.py       ← новый
```

который будет отвечать исключительно за:

1. получение фотографий из `photos`;
2. фильтрацию по `address`;
3. фильтрацию по `client`;
4. трактовку `NULL/''` как `Другие`;
5. возврат записей для отображения;
6. использование `preview_path` для картинки;
7. использование `path` как fallback;
8. получение Qwen-данных из той же записи.

А уже `photos.py` потом подключим к нему.

**Старый `PHOTO_INDEX`, `get_latest_daily_root()`, `address_folder()` и подобную логику не переносим в новый грид.**

Это даст нам гораздо более чистую архитектуру.

Следующим шагом я предлагаю сначала посмотреть **текущую реализацию `photos.py`**, но только ту часть, которая непосредственно строит и обновляет грид. Тогда мы заменим источник данных, не ломая уже работающий внешний вид и остальную UI-логику.

---

### 👤 **User** — 2026-08-20 21:24:02

нужно предусмотреть, где хранить подборки: адресов, клиентов, фото. ПРичем у каждого менеджера может быть воя подборка. И надо еще хранить состояние чекбоксов менеджеров

---

### 🤖 **Assistant** — 2026-08-20 21:24:03

Да. И это как раз тот момент, когда **лучше сразу вынести постоянное состояние из `STATE` в PostgreSQL**. `STATE` должен хранить только текущее состояние UI текущей сессии, а всё, что должно переживать перезапуск приложения и быть разным у менеджеров, — в БД.

Я бы спроектировал это так.

## 1. PostgreSQL разделяем на два уровня

### `photos`

Остаётся источником истины по фотографиям:

```text
photos
├── id
├── photo_id
├── path
├── original_filename
├── address
├── address_id
├── legal_address
├── simple_address
├── client
├── dino_*
├── hybrid_*
├── qwen_*
└── ...
```

**Подборки фотографий сюда не записываем.**

---

# 2. Отдельная таблица менеджеров

У вас уже есть пользовательская система, поэтому не надо создавать вторую сущность менеджера.

Используем существующего пользователя:

```text
users
```

У каждого пользователя есть свой `user_id`.

---

# 3. Подборки

Я бы сделал одну универсальную таблицу:

```text
collections
```

Например:

```text
id
user_id
name
kind
scope
client
created_at
updated_at
```

Где:

### `kind`

```text
my
client
```

То есть:

```text
Моя
Клиентская
```

### `scope`

```text
addresses
clients
photos
```

Таким образом одна таблица умеет хранить:

```text
Моя подборка адресов
Моя подборка клиентов
Моя подборка фотографий

Клиентская подборка адресов
Клиентская подборка клиентов
Клиентская подборка фотографий
```

Но здесь есть важный момент.

---

# 4. Элементы подборки — отдельная таблица

Не надо делать:

```text
collections.members = JSON
```

или хранить:

```text
{"78", "83", "91"}
```

в одном поле.

Лучше:

```text
collection_items
```

```text
id
collection_id
item_type
item_id
created_at
```

Например:

### Подборка адресов

```text
collection
-------------
id = 15
user_id = 3
name = "Важные адреса"
scope = "addresses"
```

и:

```text
collection_items
----------------
collection_id = 15
item_type = "address"
item_id = "78"

collection_id = 15
item_type = "address"
item_id = "83"

collection_id = 15
item_type = "address"
item_id = "91"
```

### Подборка клиентов

```text
collection_id = 22
item_type = "client"
item_id = "Яндекс"

collection_id = 22
item_type = "client"
item_id = "Сбер"
```

### Подборка фотографий

Тут **лучше использовать `photos.id`**, а не путь и не filename:

```text
collection_id = 31
item_type = "photo"
item_id = "18472"
```

Это очень важно: файл может быть переименован/перемещён, а `photos.id` остаётся идентификатором записи.

---

# 5. А вот состояние чекбоксов менеджера — отдельно

И это действительно нужно хранить.

Потому что:

> менеджер закрыл программу → открыл завтра → должен увидеть свои предыдущие выбранные адреса и клиентов.

Я бы сделал таблицу:

```text
manager_filter_state
```

Например:

```text
user_id
filter_type
item_id
checked
updated_at
```

Где:

```text
filter_type = address
filter_type = client
```

Например:

```text
user_id = 3
filter_type = address
item_id = 78
checked = true

user_id = 3
filter_type = address
item_id = 83
checked = false

user_id = 3
filter_type = client
item_id = Яндекс
checked = true

user_id = 3
filter_type = client
item_id = Сбер
checked = false
```

Но я бы сделал ещё проще.

## Состояние фильтров можно хранить компактнее

Например:

```text
manager_filter_state

user_id
selected_addresses   jsonb
selected_clients     jsonb
updated_at
```

И запись менеджера:

```json
{
  "selected_addresses": ["78", "83", "91"],
  "selected_clients": ["Яндекс", "Другие"]
}
```

Это вполне нормально, потому что это именно **состояние UI**, а не реляционные данные.

---

# 6. Что тогда остаётся в `STATE`

Вот это очень важно.

Сейчас:

```python
selected_clients
selected_addresses
collections
```

живут в памяти приложения.

Я бы изменил смысл `STATE`.

### `STATE` = временное состояние текущего UI

Например:

```python
STATE.selected_addresses
STATE.selected_clients

STATE.search_query

STATE.selected_photos

STATE.active_collection
```

Но при входе менеджера:

```text
PostgreSQL
     ↓
manager_filter_state
     ↓
STATE
     ↓
UI checkbox
```

А когда менеджер меняет checkbox:

```text
UI
 ↓
STATE
 ↓
PostgreSQL
```

То есть:

```text
             PostgreSQL
             /        \
            ↓          ↑
       загрузка       сохранение
            ↓          ↑
           STATE
             ↓
            UI
```

---

# 7. Что происходит с подборкой

Например менеджер нажал:

```text
Важное
```

и там:

```text
78
83
91
```

Это **не должно менять `STATE.selected_addresses` навсегда**.

Подборка просто устанавливает:

```text
STATE.selected_addresses =
    {"78", "83", "91"}
```

После чего грид обновляется.

А сама подборка остаётся в:

```text
collections
+
collection_items
```

---

# 8. Очень важный момент с несколькими менеджерами

Допустим:

### Менеджер Иван

```text
Важное:
78
83
```

### Менеджер Сергей

```text
Важное:
79
91
95
```

Название одинаковое, но это **две разные подборки**:

```text
collections

id  user_id  name      scope
1   10       Важное    addresses
2   14       Важное    addresses
```

Поэтому `user_id` обязательно входит в подборку.

---

# 9. Фотоподборки

Для фото я бы сделал именно так:

```text
collections
    ↓
collection_items
    ↓
photos.id
```

То есть:

```text
"На отправку клиенту"

photo 184
photo 193
photo 201
photo 224
```

Если физический файл переместили — подборка не ломается.

---

# 10. А клиентские подборки

Здесь можно сделать интересную вещь.

Например:

```text
Самокат — август
```

Это:

```text
kind = client
client = "Самокат"
scope = photos
```

И внутри:

```text
photo 184
photo 193
photo 205
```

То есть `client` у подборки — это **метаданные подборки**, а не способ поиска фотографий.

---

# 11. Что я предлагаю сделать сейчас

Не писать пока код грида.

Сначала правильно заложить БД:

```text
users
   │
   ├────────────── manager_filter_state
   │
   └────────────── collections
                       │
                       └──── collection_items
                                      │
                                      ├── address
                                      ├── client
                                      └── photo → photos.id

photos
  │
  ├── DINO
  ├── Hybrid
  └── Qwen
```

Это даст нам очень хорошую основу.

### И самое главное

**Не надо хранить в `photos` никакие `collection_id`.**

Потому что одна фотография может одновременно быть:

```text
Важное
На согласование
Самокат — август
Избранное
```

и у разных менеджеров находиться в разных подборках.

Связь должна быть **many-to-many**:

```text
manager
   ↓
collection
   ↕
collection_items
   ↕
photo/address/client
```

И тогда новый грид становится практически чистым SQL-представлением поверх `photos` + текущих фильтров менеджера.

Я бы сейчас **сначала создал эти 3 таблицы** (`collections`, `collection_items`, `manager_filter_state`), а затем уже переделывал `photos.py`/грид. Это позволит нам не переделывать архитектуру второй раз.

---

### 👤 **User** — 2026-08-20 21:26:19

у адресов будт фиксированные id и их кол-во определенно - они будут константами. Клиентов кол-во неопределенно и нужно им тоже присваивать id )

---

### 🤖 **Assistant** — 2026-08-20 21:26:19

Да. Тогда архитектуру лучше чуть изменить: **адреса и клиенты должны стать справочниками**, а `photos` должна ссылаться на них через ID. Это будет гораздо правильнее, чем хранить названия напрямую в фильтрах и подборках.

## 1. Адреса — справочник-константа

Создаём:

```text
addresses
```

Например:

| id | code | legal_address | simple_address |
|---:|---|---|---|
| 1 | 78 | ... | ... |
| 2 | 79 | ... | ... |
| 3 | 80 | ... | ... |
| ... | ... | ... | ... |

Но тут есть важный момент: **текущий `address` уже содержит `78`, `79`, `80`...**

Поэтому я бы не создавал искусственные ID `1,2,3`.

Лучше сделать:

```text
addresses
----------------
id
code
legal_address
simple_address
```

где:

```text
id = 78
code = "78"
```

или даже `id` сделать `text`, если есть вероятность нечисловых адресов.

Но поскольку ты говоришь, что ID фиксированные, я бы использовал:

```sql
id integer PRIMARY KEY
```

и:

```text
78
79
80
...
95
```

То есть **ID адреса = его существующий номер**.

---

# 2. Клиенты — отдельный динамический справочник

Создаём:

```text
clients
```

Например:

| id | name |
|---:|---|
| 1 | Яндекс |
| 2 | Сбер |
| 3 | Самокат |
| 4 | Ozon |

Новый клиент появился:

```text
5 | Альфа-Банк
```

Ещё появился:

```text
6 | РЖД
```

И так далее.

ID клиента **никогда не зависит от номера адреса**.

---

# 3. В `photos` тогда нужны ID

Сейчас:

```text
address = "78"
client = "Яндекс"
```

В новой архитектуре лучше:

```text
address_id = 78
client_id = 1
```

А сами названия берём из справочников.

Получаем:

```text
photos
-----------------------------
id
photo_id
address_id
client_id
...
```

При этом я бы **не удалял сразу** существующие:

```text
address
client
```

Сначала переведём код на новые поля, проверим работу, и только потом решим, нужны ли старые поля для совместимости.

---

# 4. Что происходит с Qwen

Вот здесь новая схема особенно полезна.

Qwen определил:

```text
"Яндекс"
```

Backend делает:

```text
SELECT id
FROM clients
WHERE lower(name) = lower('Яндекс')
```

Если найден:

```text
client_id = 1
```

Если не найден:

```text
INSERT INTO clients (name)
VALUES ('Яндекс')
RETURNING id
```

Получили:

```text
id = 17
```

и записываем:

```text
photos.client_id = 17
```

Таким образом **Qwen не присваивает ID сам**. ID выдаёт PostgreSQL.

---

# 5. Что такое «Другие»

Вот тут тоже становится красиво.

**«Другие» не надо создавать как клиента.**

Это специальное состояние:

```text
client_id IS NULL
```

UI показывает:

```text
Клиенты

☑ Все
☑ Яндекс       123
☑ Сбер          86
☑ Самокат       42
☑ Ozon          31
☑ Другие       244
```

`Другие` означает:

```sql
client_id IS NULL
```

То есть:

> клиент ещё не определён Qwen.

После обработки:

```text
client_id = 17
```

фотография автоматически исчезает из `Другие` и появляется у соответствующего клиента.

---

# 6. Подборки теперь тоже становятся правильнее

### Подборка адресов

```text
collection_items
----------------
collection_id
address_id
```

Например:

```text
Важное
78
83
91
```

### Подборка клиентов

```text
collection_items
----------------
collection_id
client_id
```

### Подборка фотографий

```text
collection_items
----------------
collection_id
photo_id
```

И здесь больше не нужны текстовые:

```text
item_type
item_id = "Яндекс"
```

Можно сделать нормальную схему.

---

# 7. Я бы даже разделил элементы подборок

Поскольку у нас всего три типа сущностей:

```text
адрес
клиент
фото
```

можно сделать три таблицы:

```text
collection_addresses
collection_clients
collection_photos
```

Например:

```text
collection_addresses
--------------------
collection_id
address_id

collection_clients
------------------
collection_id
client_id

collection_photos
-----------------
collection_id
photo_id
```

Это немного больше таблиц, зато **БД становится типобезопасной и понятной**.

Не получится случайно записать:

```text
client_id = 78
```

в подборку клиентов, если клиента 78 не существует.

Я бы для твоего проекта выбрал именно этот вариант.

---

# 8. Состояние чекбоксов менеджера

И здесь теперь тоже всё естественно.

Например:

```text
manager_address_filters
-----------------------
user_id
address_id
checked
```

и:

```text
manager_client_filters
----------------------
user_id
client_id
checked
```

Причём `Другие` можно представить специальным `NULL` или отдельным флагом.

Но я бы **не хранил каждую галочку отдельной строкой**, если состояние можно компактно представить JSONB:

```text
manager_filter_state
--------------------
user_id
selected_address_ids jsonb
selected_client_ids  jsonb
show_unknown_clients boolean
updated_at
```

Например:

```json
{
    "selected_address_ids": [78, 83, 91],
    "selected_client_ids": [1, 3, 7],
    "show_unknown_clients": true
}
```

Это состояние интерфейса, поэтому JSONB здесь вполне уместен.

---

# 9. Итоговая модель

Я бы сейчас зафиксировал именно такую:

```text
                    USERS
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
 manager_filter_state        collections
                                  │
                ┌─────────────────┼─────────────────┐
                ▼                 ▼                 ▼
      collection_addresses collection_clients collection_photos
                │                 │                 │
                ▼                 ▼                 ▼
            ADDRESSES          CLIENTS           PHOTOS
                │                 │                 │
                └─────────────────┴─────────────────┘
                                  ▲
                                  │
                         DINO + HYBRID + QWEN
```

А `photos`:

```text
photos
├── address_id   → addresses.id
├── client_id    → clients.id
├── original_filename
├── path
├── preview_path
├── DINO fields
├── Hybrid fields
└── Qwen fields
```

### И это даёт нам главное

**DINO + Hybrid:**

```text
photo → address_id
```

**Qwen:**

```text
photo → client_id
```

**Грид:**

```text
photos
    ↓
address_id IN выбранные адреса
    ↓
client_id IN выбранные клиенты
       OR client_id IS NULL («Другие»)
    ↓
GRID
```

**Подборки:**

```text
менеджер → свои подборки → адреса / клиенты / фото
```

**Состояние чекбоксов:**

```text
менеджер → сохранённые фильтры → при входе восстанавливаем UI
```

Это уже не восстановление старой системы, а нормальная **реляционная модель фотобазы**, соответствующая тому backend, который у нас фактически получился.

---

### 👤 **User** — 2026-08-20 21:26:54

текущий адрес это локальный номер fingerprinbt

---

### 🤖 **Assistant** — 2026-08-20 21:26:54

Да. Тогда я бы **сейчас заложил нормальную модель данных в PostgreSQL**, а не продолжал развивать текущие `STATE.selected_*` и старые `Collection`.

Ключевой момент: **адрес = фиксированный локальный ID fingerprint**, а клиент = динамическая сущность, которую определяет Qwen.

### Предлагаемая модель

#### 1. Адреса

Отдельная таблица:

```text
addresses
---------
id              integer PK
fingerprint_id  integer UNIQUE
name            text
legal_address   text
simple_address  text
```

Но если `78`, `79`, `80` и т.д. — это именно локальные номера fingerprint, то я бы сделал ещё проще:

```text
id              integer PK   -- 78, 79, 80...
legal_address   text
simple_address  text
```

То есть:

```text
id = 78
id = 79
id = 80
...
```

**Это и есть постоянный ID адреса.**

В `photos.address` тогда лучше в перспективе не хранить произвольный текст, а использовать `address_id`.

У нас уже есть:

```text
address_id text
address    text
legal_address text
simple_address text
```

Поэтому можно постепенно перейти к `address_id`.

---

### 2. Клиенты

Клиенты появляются динамически от Qwen, поэтому отдельная таблица:

```text
clients
-------
id              bigint PK
name            text UNIQUE
created_at      timestamp
updated_at      timestamp
```

Например:

```text
1   Яндекс
2   Самокат
3   Сбер
4   Ozon
5   Не определен
...
```

И в `photos`:

```text
client_id
```

А `client` можно пока оставить для совместимости.

Причём я бы **не создавал клиента "Другие" физически**.

Логика грида:

- `client_id IS NULL` → **Другие / клиент ещё не определён**
- `client_id = 17` → конкретный клиент №17.

Это очень хорошо ложится на твоё требование:

> если клиент ещё не определён Qwen, фото отображается в чекбоксе у клиентов как «Другие».

---

# 3. Менеджеры

У тебя уже есть пользователи в PostgreSQL (`users_db.py`), поэтому отдельную сущность менеджера создавать не нужно.

Используем:

```text
users
-----
id
login
...
```

И все персональные данные привязываем к `user_id`.

---

# 4. Состояние чекбоксов

Вот это я бы **обязательно хранил отдельно от подборок**.

Например:

```text
manager_filter_state
--------------------
user_id              bigint
filter_type          text
item_id              bigint
checked               boolean
updated_at            timestamp

PRIMARY KEY (user_id, filter_type, item_id)
```

Где:

```text
filter_type = 'address'
filter_type = 'client'
```

Например менеджер №3:

```text
user_id   filter_type   item_id   checked
3         address       78        true
3         address       79        false
3         address       80        true

3         client        1         true
3         client        2         false
3         client        3         true
```

### Зачем именно отдельное состояние?

Потому что:

**чекбокс ≠ подборка.**

Чекбоксы — это текущий рабочий фильтр менеджера.

Подборка — это сохранённый набор.

Например менеджер сейчас смотрит:

```text
Адреса:
78 ✓
79 ✓
80 ✗
81 ✓
```

Это его **текущее состояние интерфейса**.

Он может потом создать подборку:

```text
"Мои важные адреса"
78
79
81
```

Но изменение чекбоксов после этого **не должно менять подборку**.

---

# 5. Подборки

Я бы сделал **одну универсальную таблицу подборок**:

```text
collections
-----------
id              bigint PK
user_id         bigint NOT NULL
name            text
scope           text
kind            text
client_id       bigint NULL
created_at      timestamp
updated_at      timestamp
```

Например:

```text
id   user_id   name                 scope       kind
1    3         Важное               addresses   personal
2    3         На согласование      addresses   personal
3    3         Самокат август       clients     personal
4    7         Для клиента          photos      personal
```

---

# 6. Состав подборки

И здесь я бы **не пытался запихнуть адреса, клиентов и фотографии в одну колонку**.

Три таблицы связей:

```text
collection_addresses
--------------------
collection_id
address_id
```

```text
collection_clients
------------------
collection_id
client_id
```

```text
collection_photos
-----------------
collection_id
photo_id
```

Так получается очень чисто.

Одна подборка может быть:

### Адресной

```text
collection
    ↓
collection_addresses
    ↓
78
79
83
```

### Клиентской

```text
collection
    ↓
collection_clients
    ↓
Яндекс
Самокат
```

### Фотографической

```text
collection
    ↓
collection_photos
    ↓
photo 18273
photo 18274
photo 19281
```

---

# 7. Очень важное разделение

Получается четыре разных уровня:

```text
                    PostgreSQL
                         │
          ┌──────────────┼──────────────┐
          │              │              │
       PHOTOS         CLIENTS        ADDRESSES
          │              │              │
          │              │              │
       DINO +          QWEN          fingerprint
       HYBRID             │             ID
          │               │              │
          └───────────────┴──────────────┘
                          │
                       ГРИД
                          │
              ┌───────────┴───────────┐
              │                       │
        фильтр адресов          фильтр клиентов
              │                       │
              └───────────┬───────────┘
                          │
                    текущий набор
                          │
                ┌─────────┴─────────┐
                │                   │
        состояние менеджера    сохранённые
           чекбоксов             подборки
```

И это как раз соответствует новой архитектуре, которую мы сейчас описываем.

---

# 8. Что происходит после DINO + Hybrid

DINO/Hybrid знают:

```text
photo
   ↓
address_id = 78
```

Всё.

Qwen работает независимо:

```text
photo
   ↓
client_id = 17
```

или:

```text
client_id = NULL
```

Поэтому грид получает **не физические папки**, а SQL-набор:

```sql
SELECT *
FROM photos
WHERE ...
```

с фильтрами:

```text
address_id IN (...)
AND
(
    client_id IN (...)
    OR client_id IS NULL       -- Другие
)
```

Это намного правильнее нынешней схемы, где `photos.py` ещё пытается строить виртуальный индекс из папок `output/daily`.

---

## И самое главное

Я бы **не стал сейчас чинить старую систему фильтрации**.

Мы уже видим, что она исторически смешала:

- физические папки;
- `PHOTO_INDEX`;
- `STATE.addresses`;
- `STATE.selected_addresses`;
- `STATE.selected_clients`;
- Qwen `client`;
- DINO `address`;
- старые `Collection`.

Сейчас как раз хороший момент сделать **новый слой Grid Query**, который будет единственным источником фотографий для грида:

```text
PostgreSQL
    ↓
Grid Query
    ↓
address filter
    +
client filter
    +
search
    +
date
    ↓
PHOTO GRID
```

А `STATE` оставить только для **UI-состояния текущей сессии**, а постоянное состояние менеджера хранить в PostgreSQL.

### Я бы следующим шагом сделал именно структуру PostgreSQL

Сначала **ничего не ломая в работающем DINO/Qwen**, создать:

```text
addresses
clients
manager_filter_state
collections
collection_addresses
collection_clients
collection_photos
```

и добавить в `photos`:

```text
client_id
```

При этом существующие:

```text
address
client
address_id
original_filename
legal_address
simple_address
```

пока **не удалять**.

После этого уже переделаем `photos.py`/грид на SQL-фильтрацию. Это будет значительно надёжнее, чем продолжать восстанавливать старую логику.

---

### 👤 **User** — 2026-08-20 21:30:27

dibo hybrid сравнивает да

---

### 🤖 **Assistant** — 2026-08-20 21:30:28

> **Searching the web**
>
>
> **Searching 7 websites**
>
> 
>
> Worked for a couple of seconds

Да, верно. **DINO + Hybrid у нас именно сравнивает фотографии и в результате определяет адрес/fingerprint.** Я выше сформулировал это слишком упрощённо.

Точная схема у нас такая:

```text
ФОТО
  │
  ▼
DINO
  │
  ├─ dino_fingerprint
  ├─ dino_score
  ├─ dino_second_score
  └─ dino_margin
  │
  ▼
HYBRID
  │
  ├─ сравнивает результат DINO
  ├─ смотрит соседние фотографии
  ├─ при необходимости меняет fingerprint
  │
  ▼
hybrid_final_id
  │
  ▼
АДРЕС
```

То есть **DINO/Hybrid - это механизм определения адреса**, а не просто предварительная обработка.

И это хорошо согласуется с текущей структурой PostgreSQL:

```text
dino_fingerprint
dino_score
dino_second_score
dino_margin

hybrid_original_id
hybrid_final_id
hybrid_changed
hybrid_old_score
hybrid_score
hybrid_margin
hybrid_neighbors
```

DINOv2 сам по себе действительно используется для визуального сравнения через similarity/nearest-neighbor retrieval; в оригинальной работе similarity считается по embeddings. ([Pierre Fernandez](https://pierrefdz.github.io/assets/publis/dinov2/paper.pdf?utm_source=chatgpt.com))

### Поэтому архитектуру я бы зафиксировал так

**1. DINO + Hybrid определяют `address_id`.**

Это происходит автоматически.

**2. Qwen определяет `client_id`.**

Причём Qwen может ещё не успеть обработать фотографию:

```text
client_id = NULL
```

→ фотография относится к **«Другие»**.

После Qwen:

```text
client_id = 17
```

→ фотография автоматически переходит к клиенту №17.

**3. Грид вообще не должен самостоятельно определять адрес или клиента.**

Он только спрашивает PostgreSQL:

```text
дай фотографии,
где address_id входит в выбранные адреса
и client_id входит в выбранных клиентов
```

с отдельной логикой для `NULL = Другие`.

Именно это я бы сейчас сделал новым слоем **Grid Query**, не восстанавливая старую логику `PHOTO_INDEX`/физических папок.

А `hybrid_final_id` я бы пока **не переименовывал и не ломал** - сначала разберём точно, как сейчас из него получается твой локальный номер адреса `78`, `79`, `80` и т.д., и уже поверх этого построим `address_id`.

---

**Sources:**

- [DINOv2: Learning Robust Visual Features](https://pierrefdz.github.io/assets/publis/dinov2/paper.pdf?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-20 21:31:27

да

---

### 🤖 **Assistant** — 2026-08-20 21:31:28

Да. Тогда двигаемся именно по этой архитектуре.

**Следующий шаг — не менять код грида.** Сначала зафиксируем связь:

```text
DINO → Hybrid → hybrid_final_id → текущий локальный номер fingerprint → address_id
```

Нужно понять, **где сейчас в коде `hybrid_final_id` превращается в `78`, `79`, `80` и т.д.**

Дай команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID FINAL ID ================" && \
grep -RniE \
'hybrid_final_id|hybrid_original_id|fingerprint.*address|address.*fingerprint|_v33|final_id' \
app scripts \
--include="*.py" \
--exclude="*.bak*" \
| head -300
```

И отдельно:

```bash
echo "================ ADDRESS ID ================" && \
grep -RniE \
'address_id|fingerprint_id|ADDRESS.*ID|ID.*ADDRESS' \
app scripts \
--include="*.py" \
--exclude="*.bak*" \
| head -250
```

**Пока ничего не исправляем.**

После вывода я хочу точно установить существующую цепочку:

```text
фото
 ↓
DINO
 ↓
Hybrid
 ↓
hybrid_final_id
 ↓
78_v33
 ↓
78
```

и только после этого спроектировать таблицу `addresses`, чтобы новый `address_id` **не дублировал уже существующий смысл локального fingerprint ID**.

---

