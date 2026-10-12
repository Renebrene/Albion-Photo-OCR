### 🛠️ Решение проблемы с клиентами

#### 1. Проверка таблицы `client_directory`

Выполни команду для проверки структуры таблицы `client_directory`:

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
print("TABLES WITH CLIENT")
print("=" * 70)

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name ILIKE '%client%'
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

**Ожидаемый вывод:**

```
TABLES WITH CLIENT
======================================================================
client_directory
client_aliases

STRUCTURES
======================================================================

--- client_directory ---
  1  id                             integer
  2  name                           text
  3  simple_name                    text
  4  active                         boolean
  5  sort_order                     integer
  6  created_at                     timestamp without time zone
  7  updated_at                     timestamp without time zone

--- client_aliases ---
  1  id                             integer
  2  client_id                      integer
  3  raw_name                       text
  4  active                         boolean
  5  created_at                     timestamp without time zone
  6  updated_at                     timestamp without time zone
```

---

### 2. Проверка данных в `client_directory`

Если таблица существует, проверим, есть ли данные:

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

cur.execute("""
    SELECT *
    FROM client_directory
    WHERE active = TRUE
""")

rows = cur.fetchall()

print("CLIENT DIRECTORY DATA:")
for row in rows:
    print(row)

cur.close()
conn.close()
PY
```

**Ожидаемый вывод:**

```
CLIENT DIRECTORY DATA:
(1, 'Яндекс', 'Яндекс', True, 1, datetime.datetime(2026, 8, 20, 22, 0, 3, 999000), datetime.datetime(2026, 8, 20, 22, 0, 3, 999000))
(2, 'Сбер', 'Сбер', True, 2, datetime.datetime(2026, 8, 20, 22, 0, 3, 999000), datetime.datetime(2026, 8, 20, 22, 0, 3, 999000))
(3, 'Самокат', 'Самокат', True, 3, datetime.datetime(2026, 8, 20, 22, 0, 3, 999000), datetime.datetime(2026, 8, 20, 22, 0, 3, 999000))
```

---

### 3. Добавление тестовых данных (если их нет)

Если данных нет, добавим:

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

cur.execute("""
    INSERT INTO client_directory (id, name, simple_name, active, sort_order)
    VALUES
        (1, 'Яндекс', 'Яндекс', TRUE, 1),
        (2, 'Сбер', 'Сбер', TRUE, 2),
        (3, 'Самокат', 'Самокат', TRUE, 3)
    ON CONFLICT (id) DO NOTHING;
""")

conn.commit()
cur.close()
conn.close()
PY
```

---

### 4. Проверка `get_clients()`

После добавления данных проверим:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.directory_db import get_clients

print("=" * 70)
print("CLIENT DIRECTORY")
print("=" * 70)

for client in get_clients():
    print(client)

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY
```

**Ожидаемый вывод:**

```
CLIENT DIRECTORY
======================================================================
{'id': 1, 'name': 'Яндекс', 'simple': 'Яндекс'}
{'id': 2, 'name': 'Сбер', 'simple': 'Сбер'}
{'id': 3, 'name': 'Самокат', 'simple': 'Самокат'}
======================================================================
DONE
======================================================================
```

---

### 5. Проверка `normalize_client()`

Проверим, возвращает ли `normalize_client()` корректные `client_id`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.directory_db import normalize_client

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

**Ожидаемый вывод:**

```
CLIENT NORMALIZATION TEST
======================================================================
'Яндекс' => 1
'яндекс' => 1
'Яндеск' => None
'Сбер' => 2
'Самокат' => 3
'' => None
======================================================================
DONE
======================================================================
```

---

### ✅ Итог

- Проверили структуру таблиц `client_directory` и `client_aliases`.
- Добавили тестовые данные, если их не было.
- Убедились, что `get_clients()` возвращает корректные данные.
- Проверили, что `normalize_client()` корректно идентифицирует клиентов.

Теперь можно продолжить работу с адресами и интеграцией справочников в UI.