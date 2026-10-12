## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 🤖 **Assistant** — 2026-08-20 21:47:16

Да. Следующий этап я бы сделал **сразу правильно по структуре БД**, но пока без изменения логики интерфейса.

У нас уже есть `users` и `user_settings`, поэтому менеджера отдельно создавать не надо.

## 1. Справочник адресов

Адрес — фиксированная сущность. Его ID = текущий локальный номер fingerprint.

Создаём:

```sql
address_directory
```

с запасом до 100:

```text
id              integer PRIMARY KEY
legal_address   text
simple_address  text
active          boolean
sort_order      integer
```

Например:

```text
78 | Ростовская область, ... | Комарова 13 | true
79 | ...                     | ...         | true
...
95 | ...                     | ...         | true
```

**Важно:** `78–95` — это не просто порядковый номер строки. Это именно наш `address_id`, который соответствует fingerprint.

---

## 2. Клиенты

Клиенты не фиксированы, поэтому отдельный справочник:

```sql
client_directory
```

```text
id           integer PRIMARY KEY
name         text
simple_name  text
active       boolean
sort_order   integer
```

А в `photos` остаются:

```text
client
client_normalized
```

То есть:

```text
Qwen:
"Яндекс.Маркет"

        ↓

normalizer

        ↓

client_normalized:
"Яндекс Маркет"

        ↓

client_directory:
id = 7
name = "Яндекс Маркет"
```

Позже можно будет вообще добавить в `photos`:

```text
client_id integer
```

Но **я бы пока не добавлял**, пока не отладим нормализацию.

---

# 3. Варианты написания клиентов

Вот это как раз решает твою проблему с OCR/Qwen.

```sql
client_aliases
```

```text
id          bigint
client_id   integer
raw_name    text
```

Например:

```text
"Яндекс.Маркет"  →  Яндекс Маркет
"Яндекс Маркет"  →  Яндекс Маркет
"ЯНДЕКС МАРКЕТ"  →  Яндекс Маркет
"Яндекс.Маркет " →  Яндекс Маркет
"Яндекс Маркеп"  →  Яндекс Маркет
```

Последний вариант можно будет добавить вручную после обнаружения ошибки.

---

# 4. Подборки

Вот здесь я бы **не хранил подборки в `user_settings`**.

Потому что подборка — самостоятельный объект.

Нужна таблица:

```sql
collections
```

```text
id
user_id
name
kind
scope
created_at
updated_at
```

Например:

```text
1 | менеджер 1 | Важное          | Моя | addresses
2 | менеджер 1 | На согласование  | Моя | addresses
3 | менеджер 2 | Важное          | Моя | addresses
4 | менеджер 1 | Самокат август   | Клиентская | clients
```

То есть **каждый менеджер имеет свои подборки**.

---

# 5. Содержимое подборок

Поскольку у нас три типа объектов:

```text
адреса
клиенты
фото
```

я бы не делал три разные таблицы.

Сделаем:

```sql
collection_members
```

```text
collection_id
member_type
member_id
```

Например:

```text
collection 1 | address | 78
collection 1 | address | 85
collection 1 | address | 91
```

Для клиентской:

```text
collection 5 | client | 7
collection 5 | client | 12
```

Для фотографий:

```text
collection 8 | photo | 154
collection 8 | photo | 219
```

Это позволит одной системой обслуживать все три типа подборок.

---

# 6. Состояние чекбоксов

И вот это **отдельно от подборок**.

Подборка говорит:

> какие элементы сохранены менеджером.

А состояние чекбоксов говорит:

> что менеджер сейчас выбрал на экране.

Это разные вещи.

Поэтому:

```sql
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

Или ещё лучше — хранить состояние выборки более явно:

```sql
manager_selections
```

```text
user_id
item_type
item_id
checked
updated_at
```

Например:

```text
user 1 | address | 78 | true
user 1 | address | 85 | true
user 1 | address | 90 | false

user 2 | address | 78 | false
user 2 | address | 85 | true
```

Таким образом **чекбоксы одного менеджера вообще никак не влияют на другого**.

---

# 7. `user_settings` оставляем

Текущий:

```text
user_settings
    user_id
    settings jsonb
```

оставляем для настроек интерфейса:

```json
{
  "dark_mode": false,
  "grid_columns": 5,
  "show_period": false,
  "sort": "date",
  "date_filter": "taken"
}
```

А не для содержимого подборок.

---

# 8. Получается хорошая архитектура

```text
                    PostgreSQL
                         │
          ┌──────────────┴──────────────┐
          │                             │
       PHOTOS                       СПРАВОЧНИКИ
          │                             │
          │                    ┌────────┴─────────┐
          │                    │                  │
          │             address_directory   client_directory
          │                    │                  │
          │                    │             client_aliases
          │                    │
          │
          ├── address_id
          ├── legal_address
          ├── simple_address
          ├── client
          └── client_normalized

                    USERS
                      │
             ┌────────┴────────┐
             │                 │
       collections       manager_selections
             │
      collection_members
```

И это уже хорошо масштабируется.

---

## 9. Главное изменение в UI

После этого логика будет такая.

### Левая панель адресов

Показываем:

```text
☐ Комарова 13
☐ Ленина 25
☐ Пушкинская 42
...
```

Но внутренне checkbox работает не со строкой `"Комарова 13"`.

Он работает с:

```text
address_id = 78
```

То есть:

```text
UI:
"Комарова 13"

DB:
78
```

---

### Грид

Грид показывает:

```text
Комарова 13
```

а при наведении/открытии превью:

```text
Ростовская область,
г. Ростов-на-Дону,
ул. Комарова, д. 13
```

То есть:

**checkbox + grid → `simple_address`**

**preview → `legal_address`**

Именно так, как ты предложил.

---

## 10. И главное — обновление грида

Событие checkbox:

```text
checkbox изменён
       ↓
manager_selection изменён
       ↓
STATE.selected_addresses обновлён
       ↓
refresh_photos()
       ↓
грид сразу перерисован
```

То есть кнопки **«Применить» не будет**.

Выставил галочку → грид сразу изменился.

Снял → сразу изменился.

Выбрал несколько → сразу показывает объединённый результат.

---

### Я предлагаю сейчас сделать именно этот этап:

**только PostgreSQL-схему**, без вмешательства в существующий DINO/Hybrid и без изменения рабочего распознавания.

После создания таблиц проверим:

```text
photos
address_directory
client_directory
client_aliases
collections
collection_members
manager_selections
users
user_settings
```

А уже следующим шагом подключим к этому `state.py` и текущий `photos.py`.

---

### 👤 **User** — 2026-08-20 21:48:49

С клиентами также, только Адреса справа, от грида, а клиенты слева

---

### 🤖 **Assistant** — 2026-08-20 21:48:50

Да, тогда фиксируем окончательную схему UI.

### Раскладка

```text
┌──────────────────────┬──────────────────────────────┬──────────────────────┐
│       КЛИЕНТЫ        │            ГРИД              │       АДРЕСА         │
│                      │                              │                      │
│ ☐ Яндекс             │   [ фото ] [ фото ] [ фото ] │ ☐ Комарова 13        │
│ ☐ Самокат             │   [ фото ] [ фото ] [ фото ] │ ☐ Ленина 25          │
│ ☐ Сбер                │   [ фото ] [ фото ] [ фото ] │ ☐ Пушкинская 42      │
│ ☐ Ozon                │   ...                        │ ☐ ...                │
│ ...                   │                              │                      │
└──────────────────────┴──────────────────────────────┴──────────────────────┘
```

То есть:

- **клиенты — слева от грида**;
- **грид — по центру**;
- **адреса — справа от грида**.

### Логика одинаковая

Для клиента:

```text
☑ Яндекс
☑ Самокат
```

→ сразу обновляется грид.

Для адреса:

```text
☑ Комарова 13
☑ Ленина 25
```

→ сразу обновляется грид.

Можно одновременно:

```text
Клиенты:
☑ Яндекс
☑ Сбер

Адреса:
☑ Комарова 13
☑ Ленина 25
```

и фильтр работает по нашей определённой логике `filter_priority`.

---

### Что хранится в PostgreSQL

**Клиенты:**

```text
client_directory
client_aliases
```

**Адреса:**

```text
address_directory
```

**Фотографии:**

```text
photos
```

**Подборки:**

```text
collections
collection_members
```

**Текущее состояние чекбоксов конкретного менеджера:**

```text
manager_selections
```

И принцип для обоих одинаковый:

```text
                    менеджер
                       │
             ┌─────────┴─────────┐
             │                   │
        КЛИЕНТЫ               АДРЕСА
             │                   │
       client_id            address_id
             │                   │
             └─────────┬─────────┘
                       ↓
                    ГРИД
```

Причём **адреса имеют фиксированные ID `78–100`**, а клиенты получают свои собственные ID по мере появления.

И это важно: **ID клиента никак не связан с ID адреса**.

Например:

```text
address_id 85 = конкретный fingerprint/адрес

client_id 85 = совершенно другой клиент
```

Они находятся в разных справочниках.

### Отображение

Для обоих одинаковая идея:

**Клиент:**

```text
checkbox → client_directory.simple_name
грид     → client_directory.simple_name
```

**Адрес:**

```text
checkbox → address_directory.simple_address
грид     → address_directory.simple_address
preview  → address_directory.legal_address
```

А исходные значения Qwen сохраняются отдельно и не уничтожаются.

Это уже можно считать нашей **целевой моделью данных**.

---

### 👤 **User** — 2026-08-20 21:49:28

да

---

### 🤖 **Assistant** — 2026-08-20 21:49:28

Да. Тогда **закрепляем эту архитектуру и начинаем с БД**, не трогая пока рабочий DINO/Hybrid и текущий алгоритм распознавания.

Следующим шагом я дам одну безопасную команду через `uv`, которая создаст недостающие таблицы и индексы, при этом ничего существующего не удалит и не изменит.

---

### 👤 **User** — 2026-08-20 21:49:35

далее

---

### 🤖 **Assistant** — 2026-08-20 21:49:36

Идём дальше. Сейчас создаём **только структуру PostgreSQL**. Данные `photos` не трогаем.

### 1. Создаём справочники, подборки и состояние чекбоксов

Выполни из проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

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

print("=" * 70)
print("CREATING PHOTOBASE UI / DIRECTORY TABLES")
print("=" * 70)

# ============================================================
# АДРЕСА
# ID = локальный ID fingerprint: 78, 79 ... 100 ...
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS address_directory (
    id              integer PRIMARY KEY,
    legal_address   text NOT NULL DEFAULT '',
    simple_address  text NOT NULL DEFAULT '',
    active          boolean NOT NULL DEFAULT true,
    sort_order      integer NOT NULL DEFAULT 0,
    created_at      timestamp without time zone NOT NULL DEFAULT now(),
    updated_at      timestamp without time zone NOT NULL DEFAULT now()
)
""")

# ============================================================
# КЛИЕНТЫ
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS client_directory (
    id              integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name            text NOT NULL,
    simple_name     text NOT NULL DEFAULT '',
    active          boolean NOT NULL DEFAULT true,
    sort_order      integer NOT NULL DEFAULT 0,
    created_at      timestamp without time zone NOT NULL DEFAULT now(),
    updated_at      timestamp without time zone NOT NULL DEFAULT now()
)
""")

cur.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS
idx_client_directory_name_lower
ON client_directory (LOWER(TRIM(name)))
""")

# ============================================================
# ВАРИАНТЫ ИМЁН КЛИЕНТОВ
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS client_aliases (
    id              bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    client_id       integer NOT NULL
                    REFERENCES client_directory(id)
                    ON DELETE CASCADE,
    raw_name        text NOT NULL,
    created_at      timestamp without time zone NOT NULL DEFAULT now()
)
""")

cur.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS
idx_client_aliases_client_raw
ON client_aliases (client_id, LOWER(TRIM(raw_name)))
""")

# ============================================================
# ПОДБОРКИ
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS collections (
    id              bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id         integer NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
    name            text NOT NULL,
    kind            text NOT NULL DEFAULT 'Моя',
    scope           text NOT NULL DEFAULT 'addresses',
    created_at      timestamp with time zone NOT NULL DEFAULT now(),
    updated_at      timestamp with time zone NOT NULL DEFAULT now(),

    CONSTRAINT collections_kind_check
        CHECK (kind IN ('Моя', 'Клиентская')),

    CONSTRAINT collections_scope_check
        CHECK (scope IN ('addresses', 'clients', 'photos'))
)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS
idx_collections_user_id
ON collections(user_id)
""")

# ============================================================
# ЭЛЕМЕНТЫ ПОДБОРОК
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS collection_members (
    id              bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    collection_id   bigint NOT NULL
                    REFERENCES collections(id)
                    ON DELETE CASCADE,
    member_type     text NOT NULL,
    member_id       bigint NOT NULL,
    created_at      timestamp with time zone NOT NULL DEFAULT now(),

    CONSTRAINT collection_members_type_check
        CHECK (member_type IN ('address', 'client', 'photo'))
)
""")

cur.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS
idx_collection_members_unique
ON collection_members (
    collection_id,
    member_type,
    member_id
)
""")

# ============================================================
# ТЕКУЩЕЕ СОСТОЯНИЕ ЧЕКБОКСОВ МЕНЕДЖЕРА
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS manager_selections (
    user_id         integer NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
    item_type       text NOT NULL,
    item_id         bigint NOT NULL,
    checked         boolean NOT NULL DEFAULT true,
    updated_at      timestamp with time zone NOT NULL DEFAULT now(),

    PRIMARY KEY (user_id, item_type, item_id),

    CONSTRAINT manager_selections_type_check
        CHECK (item_type IN ('address', 'client', 'photo'))
)
""")

print()
print("TABLES CREATED / ALREADY EXIST:")
print()

cur.execute("""
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
      'address_directory',
      'client_directory',
      'client_aliases',
      'collections',
      'collection_members',
      'manager_selections'
  )
ORDER BY table_name
""")

for (name,) in cur.fetchall():
    print("  OK:", name)

cur.close()
conn.close()

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY
```

### Что это даст

Получим:

```text
address_directory
client_directory
client_aliases
collections
collection_members
manager_selections
```

При этом существующая `photos` останется как есть.

Особенно важно, что состояние чекбоксов будет разделено по `user_id`:

```text
Менеджер 1:
    address 78 = checked
    address 85 = checked

Менеджер 2:
    address 78 = unchecked
    address 85 = checked
```

То есть один менеджер не перезаписывает состояние другого.

---

После выполнения **не надо пока запускать приложение**. Покажи вывод этой команды. Затем следующим шагом заполним `address_directory` адресами **78–95**, используя существующие fingerprint ID, и подготовим задел до `100`.

---

### 👤 **User** — 2026-08-20 21:50:17

cd ~/projects/scene_fingerprint_mvp_v02

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

print("=" * 70)
print("CREATING PHOTOBASE UI / DIRECTORY TABLES")
print("=" * 70)

# ============================================================
# АДРЕСА
# ID = локальный ID fingerprint: 78, 79 ... 100 ...
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS address_directory (
    id              integer PRIMARY KEY,
    legal_address   text NOT NULL DEFAULT '',
    simple_address  text NOT NULL DEFAULT '',
    active          boolean NOT NULL DEFAULT true,
    sort_order      integer NOT NULL DEFAULT 0,
    created_at      timestamp without time zone NOT NULL DEFAULT now(),
    updated_at      timestamp without time zone NOT NULL DEFAULT now()
)
""")

# ============================================================
# КЛИЕНТЫ
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS client_directory (
    id              integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name            text NOT NULL,
    simple_name     text NOT NULL DEFAULT '',
    active          boolean NOT NULL DEFAULT true,
    sort_order      integer NOT NULL DEFAULT 0,
    created_at      timestamp without time zone NOT NULL DEFAULT now(),
    updated_at      timestamp without time zone NOT NULL DEFAULT now()
)
""")

cur.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS
idx_client_directory_name_lower
ON client_directory (LOWER(TRIM(name)))
""")

# ============================================================
# ВАРИАНТЫ ИМЁН КЛИЕНТОВ
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS client_aliases (
    id              bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    client_id       integer NOT NULL
                    REFERENCES client_directory(id)
                    ON DELETE CASCADE,
    raw_name        text NOT NULL,
    created_at      timestamp without time zone NOT NULL DEFAULT now()
)
""")

cur.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS
idx_client_aliases_client_raw
ON client_aliases (client_id, LOWER(TRIM(raw_name)))
""")

# ============================================================
# ПОДБОРКИ
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS collections (
    id              bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    user_id         integer NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
    name            text NOT NULL,
    kind            text NOT NULL DEFAULT 'Моя',
    scope           text NOT NULL DEFAULT 'addresses',
    created_at      timestamp with time zone NOT NULL DEFAULT now(),
    updated_at      timestamp with time zone NOT NULL DEFAULT now(),

    CONSTRAINT collections_kind_check
        CHECK (kind IN ('Моя', 'Клиентская')),

    CONSTRAINT collections_scope_check
        CHECK (scope IN ('addresses', 'clients', 'photos'))
)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS
idx_collections_user_id
ON collections(user_id)
""")

# ============================================================
# ЭЛЕМЕНТЫ ПОДБОРОК
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS collection_members (
    id              bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    collection_id   bigint NOT NULL
                    REFERENCES collections(id)
                    ON DELETE CASCADE,
    member_type     text NOT NULL,
    member_id       bigint NOT NULL,
    created_at      timestamp with time zone NOT NULL DEFAULT now(),

    CONSTRAINT collection_members_type_check
        CHECK (member_type IN ('address', 'client', 'photo'))
)
""")

cur.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS
idx_collection_members_unique
ON collection_members (
    collection_id,
    member_type,
    member_id
)
""")

# ============================================================
# ТЕКУЩЕЕ СОСТОЯНИЕ ЧЕКБОКСОВ МЕНЕДЖЕРА
# ============================================================

cur.execute("""
CREATE TABLE IF NOT EXISTS manager_selections (
    user_id         integer NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
    item_type       text NOT NULL,
    item_id         bigint NOT NULL,
    checked         boolean NOT NULL DEFAULT true,
    updated_at      timestamp with time zone NOT NULL DEFAULT now(),

    PRIMARY KEY (user_id, item_type, item_id),

    CONSTRAINT manager_selections_type_check
        CHECK (item_type IN ('address', 'client', 'photo'))
)
""")

print()
print("TABLES CREATED / ALREADY EXIST:")
print()

cur.execute("""
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
      'address_directory',
      'client_directory',
      'client_aliases',
      'collections',
      'collection_members',
      'manager_selections'
  )
ORDER BY table_name
""")

for (name,) in cur.fetchall():
    print("  OK:", name)

cur.close()
conn.close()

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY

---

### 🤖 **Assistant** — 2026-08-20 21:50:18

Да, именно эту команду можно выполнять. Она корректная и использует твой `uv`/`.venv`.

**Она безопасная для текущей БД:** используются `CREATE TABLE IF NOT EXISTS`, существующая `photos` не изменяется, данные не удаляются.

После выполнения ожидаем:

```text
OK: address_directory
OK: client_aliases
OK: client_directory
OK: collection_members
OK: collections
OK: manager_selections
```

и:

```text
======================================================================
DONE
======================================================================
```

**Выполняй.** После этого покажи вывод —

---

### 👤 **User** — 2026-08-20 21:50:37

TABLES CREATED / ALREADY EXIST:

  OK: address_directory
  OK: client_aliases
  OK: client_directory
  OK: collection_members
  OK: collections
  OK: manager_selections

======================================================================
DONE
======================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 21:50:38

Отлично. Структура БД создана.

Теперь следующий важный шаг — **заполнить справочник адресов**, но не выдумывать юридические названия. У нас сейчас известны только ID fingerprint `78–95`, а сами юридические/упрощённые названия пока должны появиться из твоих данных.

Я предлагаю сначала проверить, какие пользователи уже есть, и заодно посмотреть, нет ли уже где-нибудь в проекте таблицы/конфига с соответствием:

```text
78 → ...
79 → ...
...
95 → ...
```

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

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
print("USERS")
print("=" * 70)

cur.execute("""
    SELECT
        id,
        name,
        active,
        persist_state
    FROM users
    ORDER BY id
""")

for row in cur.fetchall():
    print(row)

print()
print("=" * 70)
print("ADDRESS DIRECTORY")
print("=" * 70)

cur.execute("""
    SELECT
        id,
        legal_address,
        simple_address,
        active,
        sort_order
    FROM address_directory
    ORDER BY id
""")

rows = cur.fetchall()

if not rows:
    print("(empty)")
else:
    for row in rows:
        print(row)

print()
print("=" * 70)
print("PHOTOS: ADDRESS IDS")
print("=" * 70)

cur.execute("""
    SELECT
        address_id,
        COUNT(*) AS photo_count
    FROM photos
    WHERE address_id IS NOT NULL
      AND TRIM(address_id) <> ''
    GROUP BY address_id
    ORDER BY address_id
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
PY
```

### Почему сначала это

У нас уже есть правильная модель:

```text
fingerprint
    ↓
address_id
    ↓
address_directory
    ├── legal_address
    └── simple_address
```

Но **не надо сейчас автоматически переносить `photos.address` в `simple_address` или `legal_address`**. Это разные понятия.

И ещё важный момент: `address_directory.id` будет именно нашим стабильным ID:

```text
78
79
80
...
95
...
100
```

Даже когда физическая структура fingerprint позже изменится, **ID адреса в БД остаётся адресом**, а не именем папки `_v33`.

После этого вывода решим, откуда первоначально взять названия 78–95 и как правильно заполнить справочник.

---

### 👤 **User** — 2026-08-20 21:57:15

USERS
======================================================================
(1, 'Вихляева Алена', True, True)
(2, 'Пятницына Диана', True, True)
(3, 'Аннин Илья', True, True)
(4, 'Иванова Елена', True, True)
(5, 'Марышева Елена', True, True)
(6, 'Бутовченко Ольга', True, True)
(7, 'Кривошлыкова Ангелина', True, True)
(8, 'Теплинская Наталья', True, True)
(9, 'Папикян Эля', True, True)
(10, 'Путилина Татьяна', True, True)
(11, 'Администратор', True, True)
(12, 'Гость', True, False)

======================================================================
ADDRESS DIRECTORY
======================================================================
(empty)

======================================================================
PHOTOS: ADDRESS IDS
======================================================================
('85_v33', 1)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
 соответствия пока нет, но для начала можно сделать
id - упрощенное имя - юридическое
78 
Комарова, 13
бул. Комарова, 13 В / пр. Космонавтов, сторона Б

79
Комарова-Добровольского, поз.1
бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б

остальные потом

---

### 🤖 **Assistant** — 2026-08-20 21:57:17

Да. Тогда сейчас **заполняем только 78 и 79**, остальные строки не создаём заранее. ID остаются фиксированными и будут добавляться по мере появления адресов.

Соответствие:

| ID | Упрощённое имя | Юридический адрес |
|---:|---|---|
| 78 | Комарова, 13 | бул. Комарова, 13 В / пр. Космонавтов, сторона Б |
| 79 | Комарова-Добровольского, поз.1 | бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б |

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

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

addresses = [
    (
        78,
        "Комарова, 13",
        "бул. Комарова, 13 В / пр. Космонавтов, сторона Б",
    ),
    (
        79,
        "Комарова-Добровольского, поз.1",
        "бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б",
    ),
]

for address_id, simple_address, legal_address in addresses:
    cur.execute(
        """
        INSERT INTO address_directory (
            id,
            simple_address,
            legal_address,
            active,
            sort_order
        )
        VALUES (%s, %s, %s, true, %s)
        ON CONFLICT (id)
        DO UPDATE SET
            simple_address = EXCLUDED.simple_address,
            legal_address = EXCLUDED.legal_address,
            active = EXCLUDED.active,
            sort_order = EXCLUDED.sort_order,
            updated_at = now()
        """,
        (
            address_id,
            simple_address,
            legal_address,
            address_id,
        ),
    )

print("=" * 70)
print("ADDRESS DIRECTORY")
print("=" * 70)

cur.execute(
    """
    SELECT
        id,
        simple_address,
        legal_address,
        active,
        sort_order
    FROM address_directory
    ORDER BY id
    """
)

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
PY
```

После этого будет:

```text
78 | Комарова, 13
79 | Комарова-Добровольского, поз.1
```

А **80–100 пока вообще отсутствуют в справочнике** — это правильно. Когда дадим имена, добавим их.

И ещё важный момент: я предлагаю считать `address_directory` **единственным источником отображаемого названия адреса**. То есть в дальнейшем UI не должен брать название из папки `78_v33`, `photos.address` или других старых полей.

Получится:

```text
address_id = 78
       │
       ▼
address_directory
       │
       ├── simple_address → "Комарова, 13"
       │
       └── legal_address  → "бул. Комарова, 13 В / пр. Космонавтов, сторона Б"
```

Это как раз даст нам нужное поведение: **слева/справа checkbox и грид показывают упрощённое имя, а превью — юридическое.**

---

### 👤 **User** — 2026-08-20 21:57:38

далее

---

### 🤖 **Assistant** — 2026-08-20 21:57:39

Дальше я бы **не лез сразу в UI**. Сначала закрепим связь `photos.address_id` с нашим справочником адресов.

Сейчас есть проблема: в `photos.address_id` лежит:

```text
85_v33
```

а новый справочник использует:

```text
85
```

Это надо нормализовать технически, потому что дальше фильтр адресов должен работать именно по **числовому ID адреса**, а не по имени папки fingerprint.

### 1. Сначала проверим все текущие значения `address_id`

```bash
cd ~/projects/scene_fingerprint_mvp_v02

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
    SELECT
        address_id,
        COUNT(*) AS cnt
    FROM photos
    WHERE address_id IS NOT NULL
      AND TRIM(address_id) <> ''
    GROUP BY address_id
    ORDER BY address_id
""")

print("=" * 70)
print("CURRENT photos.address_id")
print("=" * 70)

rows = cur.fetchall()

for address_id, cnt in rows:
    print(f"{address_id!r:20} {cnt}")

cur.close()
conn.close()
PY
```

Сейчас мы уже знаем, что есть:

```text
85_v33    1
```

Но перед изменением **проверим полностью**, чтобы случайно не сломать будущие/старые значения.

### 2. После этого

Если действительно только:

```text
85_v33
```

то заменим его на:

```text
85
```

и дальше договоримся:

```text
photos.address_id
        ↓
только ID справочника
        ↓
address_directory.id
```

А `hybrid_original_id` / `hybrid_final_id` оставляем **как есть** — это технические результаты Hybrid и они не становятся справочником адресов.

Это важное разделение:

```text
DINO / Hybrid
     ↓
address_id = 85
     ↓
address_directory
     ↓
simple_address / legal_address
```

Выполни сначала проверку выше и покажи результат.

---

### 👤 **User** — 2026-08-20 21:57:51

int_mvp_v02

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
    SELECT
        address_id,
        COUNT(*) AS cnt
    FROM photos
    WHERE address_id IS NOT NULL
      AND TRIM(address_id) <> ''
    GROUP BY address_id
    ORDER BY address_id
PYnn.close(){address_id!r:20} {cnt}")
======================================================================
CURRENT photos.address_id
======================================================================
'85_v33'             1
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 21:57:54

Да. Сейчас база для справочника уже есть, поэтому следующий шаг — **заполнить первые два адреса**, не трогая пока `photos.address_id`.

Важно разделить:

- `photos.address_id` — техническое значение распознавания/fingerprint (`85_v33` сейчас);
- `address_directory.id` — **постоянный локальный ID адреса**: `78`, `79`, … `100+`;
- `simple_address` — то, что показываем в чекбоксе и рядом с гридом;
- `legal_address` — полное юридическое название, которое показываем в превью/карточке.

Я бы сейчас внес именно эти два адреса:

```text
78 | Комарова, 13
   | бул. Комарова, 13 В / пр. Космонавтов, сторона Б

79 | Комарова-Добровольского, поз.1
   | бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б
```

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

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

addresses = [
    (
        78,
        "Комарова, 13",
        "бул. Комарова, 13 В / пр. Космонавтов, сторона Б",
    ),
    (
        79,
        "Комарова-Добровольского, поз.1",
        "бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б",
    ),
]

for address_id, simple_address, legal_address in addresses:
    cur.execute("""
        INSERT INTO address_directory (
            id,
            simple_address,
            legal_address,
            active,
            sort_order
        )
        VALUES (%s, %s, %s, TRUE, %s)
        ON CONFLICT (id) DO UPDATE SET
            simple_address = EXCLUDED.simple_address,
            legal_address  = EXCLUDED.legal_address,
            active         = EXCLUDED.active,
            sort_order     = EXCLUDED.sort_order,
            updated_at     = now()
    """, (
        address_id,
        simple_address,
        legal_address,
        address_id,
    ))

print("=" * 70)
print("ADDRESS DIRECTORY")
print("=" * 70)

cur.execute("""
    SELECT
        id,
        simple_address,
        legal_address,
        active,
        sort_order
    FROM address_directory
    ORDER BY sort_order, id
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
PY
```

После этого получим:

```text
78  Комарова, 13
    бул. Комарова, 13 В / пр. Космонавтов, сторона Б

79  Комарова-Добровольского, поз.1
    бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б
```

### А дальше я предлагаю сделать следующий слой

Не надо пока связывать `photos.address_id` напрямую с `address_directory.id`. Сначала сделаем **таблицу соответствия технического fingerprint → постоянный адрес**.

Например:

```text
fingerprint_id    address_id
78_v33             78
79_v33             79
80_v33             80
...
```

Но лучше даже не создавать для этого отдельную таблицу сразу: у нас уже есть `address_directory`, и можно добавить туда технический идентификатор:

```text
id = 78
fingerprint_id = 78_v33
simple_address = Комарова, 13
legal_address = ...
```

Это даст нам очень чистую архитектуру:

```text
                 ┌─────────────────────┐
                 │ address_directory    │
                 ├─────────────────────┤
                 │ id = 78              │
                 │ fingerprint_id       │──→ 78_v33
                 │ simple_address       │
                 │ legal_address        │
                 └──────────┬──────────┘
                            │
                            ▼
                       ФОТОГРИД
                            │
                  показывает simple_address
                            │
                            ▼
                       ПРЕВЬЮ
                  показывает legal_address
```

И самое главное — **если алгоритм DINO/hybrid когда-нибудь изменит `_v33` на другую техническую версию, пользовательский ID 78 не изменится**.

Это как раз стоит сделать следующим шагом, прежде чем подключать чекбоксы и обновление грида.

---

### 👤 **User** — 2026-08-20 21:58:24

а

---

### 🤖 **Assistant** — 2026-08-20 21:58:26

Да, я бы **не спешил добавлять `fingerprint_id` в `address_directory`**.

У нас уже есть правильная идея:

- `78`, `79`, … — **постоянные ID адресов**;
- `78_v33`, `79_v33` — **технические ID fingerprint**, которые относятся к механизму распознавания;
- `address_directory` — пользовательский справочник адресов;
- `photos.address_id` сейчас можно оставить как техническое поле переходного периода.

И главное: **DINO/hybrid определяет именно fingerprint ID, а не юридический адрес**. Поэтому лучше не смешивать эти сущности.

Я бы сделал так:

```text
address_directory
────────────────────────────────────────
id              78
simple_address  Комарова, 13
legal_address   бул. Комарова, 13 В / пр. Космонавтов, сторона Б
```

А соответствие:

```text
fingerprint  →  address_directory.id

78_v33       →  78
79_v33       →  79
...
```

можно хранить **отдельно**, когда мы точно определим окончательную схему hybrid.

Это особенно важно из-за твоего замечания: **hybrid сравнивает fingerprint'ы**. Значит, пользовательский адрес и технический fingerprint должны быть независимыми.

### Следующий шаг

Сейчас я предлагаю **только заполнить `78` и `79` в `address_directory`**, проверить их, и после этого перейти к схеме:

**менеджер → свои чекбоксы → свои подборки → адреса/клиенты/фото → обновление грида.**

А уже затем подключим `simple_address` и `legal_address` в интерфейс.

---

### 👤 **User** — 2026-08-20 21:59:25

упрощенный и юридический адрес можно будет преопределять для фингепринт_ид через технический раздел - закладка Слепки.

---

### 🤖 **Assistant** — 2026-08-20 21:59:26

Да. **Это даже лучше**, и тогда архитектуру можно сделать гибкой.

Вкладка **«Слепки»** будет техническим справочником, где администратор связывает fingerprint с пользовательским адресом.

### Схема

```text
FINGERPRINT
78_v33
   │
   ├── адрес ID: 78
   ├── упрощённый: Комарова, 13
   └── юридический: бул. Комарова, 13 В / пр. Космонавтов, сторона Б
```

При этом в `address_directory` остаётся:

```text
id = 78
simple_address = Комарова, 13
legal_address = ...
```

А в техническом разделе **«Слепки»** мы можем видеть:

| Fingerprint | Адрес ID | Упрощённый адрес | Юридический адрес |
|---|---:|---|---|
| 78_v33 | 78 | Комарова, 13 | бул. Комарова, 13 В / пр. Космонавтов, сторона Б |
| 79_v33 | 79 | Комарова-Добровольского, поз.1 | бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б |

### И здесь есть важный плюс

Если завтра:

```text
78_v33
```

будет заменён на новую версию:

```text
78_v34
```

или вообще появится другой fingerprint, **адрес 78 не меняется**.

То есть:

```text
ТЕХНИЧЕСКИЙ СЛОЙ
fingerprint → адрес ID

ПОЛЬЗОВАТЕЛЬСКИЙ СЛОЙ
адрес ID → simple/legal address
```

Это правильное разделение.

---

### Я бы только немного изменил текущую таблицу

Добавил бы в `address_directory`:

```sql
fingerprint_id text
```

но **не делал бы его PRIMARY KEY**.

Потому что потенциально у одного адреса могут существовать разные технические fingerprint'ы:

```text
78_v33 ─┐
        ├──> address 78
78_v34 ─┘
```

И тогда один пользовательский адрес может пережить несколько поколений fingerprint.

Поэтому ещё лучше отдельная таблица:

```text
address_fingerprints

fingerprint_id | address_id
---------------+-----------
78_v33         | 78
79_v33         | 79
78_v34         | 78
```

Это будет наиболее чисто.

**И я бы именно так и сделал.** Не трогаем пока `photos.address_id`, а создаём отдельную техническую связь. Затем вкладка **«Слепки»** будет редактировать эту связь и адресные названия.

---

### 👤 **User** — 2026-08-20 21:59:58

да

---

### 🤖 **Assistant** — 2026-08-20 21:59:59

Да. Тогда фиксируем эту архитектуру и делаем следующий шаг: **отдельная таблица `address_fingerprints`**, которая связывает технический fingerprint с постоянным адресом.

Она позволит:

- `78_v33 → 78`
- `79_v33 → 79`
- позже `78_v34 → 78`
- один адрес может иметь несколько fingerprint;
- адрес `78` остаётся постоянным;
- `photos.address_id` пока **не трогаем**;
- вкладка **«Слепки»** в техническом разделе потом станет местом управления этой связью.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

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

print("=" * 70)
print("CREATING ADDRESS ↔ FINGERPRINT LINK")
print("=" * 70)

cur.execute("""
CREATE TABLE IF NOT EXISTS address_fingerprints (
    fingerprint_id  text PRIMARY KEY,

    address_id      integer NOT NULL
                    REFERENCES address_directory(id)
                    ON DELETE RESTRICT,

    active          boolean NOT NULL DEFAULT true,

    created_at      timestamp without time zone
                    NOT NULL DEFAULT now(),

    updated_at      timestamp without time zone
                    NOT NULL DEFAULT now()
)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS
idx_address_fingerprints_address_id
ON address_fingerprints(address_id)
""")

print()
print("TABLE:")
print()

cur.execute("""
SELECT
    ordinal_position,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'address_fingerprints'
ORDER BY ordinal_position
""")

for pos, name, dtype in cur.fetchall():
    print(f"{pos:3}  {name:20} {dtype}")

cur.close()
conn.close()

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY
```

Пока **не заполняем `78_v33 → 78` автоматически**. Сначала посмотрим результат создания таблицы.

После этого следующим шагом сделаем **первоначальное заполнение `address_directory` для 78 и 79 + их связи со слепками**, а затем перейдём к UI вкладки **«Слепки»**.

---

### 👤 **User** — 2026-08-20 22:00:14

CREATING ADDRESS ↔ FINGERPRINT LINK
======================================================================

TABLE:

  1  fingerprint_id       text
  2  address_id           integer
  3  active               boolean
  4  created_at           timestamp without time zone
  5  updated_at           timestamp without time zone

======================================================================
DONE
======================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:00:16

Отлично. Схема теперь правильная.

Следующий шаг — **заполнить первые два адреса и сразу привязать их к fingerprint**. Это не затронет фотографии и не изменит текущую логику DINO/hybrid.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

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

addresses = [
    (
        78,
        "Комарова, 13",
        "бул. Комарова, 13 В / пр. Космонавтов, сторона Б",
        "78_v33",
    ),
    (
        79,
        "Комарова-Добровольского, поз.1",
        "бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б",
        "79_v33",
    ),
]

for address_id, simple_address, legal_address, fingerprint_id in addresses:

    cur.execute("""
        INSERT INTO address_directory (
            id,
            simple_address,
            legal_address,
            active,
            sort_order
        )
        VALUES (%s, %s, %s, TRUE, %s)
        ON CONFLICT (id) DO UPDATE SET
            simple_address = EXCLUDED.simple_address,
            legal_address  = EXCLUDED.legal_address,
            active         = EXCLUDED.active,
            sort_order     = EXCLUDED.sort_order,
            updated_at     = now()
    """, (
        address_id,
        simple_address,
        legal_address,
        address_id,
    ))

    cur.execute("""
        INSERT INTO address_fingerprints (
            fingerprint_id,
            address_id,
            active
        )
        VALUES (%s, %s, TRUE)
        ON CONFLICT (fingerprint_id) DO UPDATE SET
            address_id = EXCLUDED.address_id,
            active = TRUE,
            updated_at = now()
    """, (
        fingerprint_id,
        address_id,
    ))

print("=" * 70)
print("ADDRESS DIRECTORY")
print("=" * 70)

cur.execute("""
    SELECT
        id,
        simple_address,
        legal_address
    FROM address_directory
    ORDER BY id
""")

for row in cur.fetchall():
    print(row)

print()
print("=" * 70)
print("ADDRESS ↔ FINGERPRINT")
print("=" * 70)

cur.execute("""
    SELECT
        af.fingerprint_id,
        af.address_id,
        ad.simple_address,
        ad.legal_address,
        af.active
    FROM address_fingerprints af
    JOIN address_directory ad
      ON ad.id = af.address_id
    ORDER BY af.address_id, af.fingerprint_id
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
PY
```

Ожидаем:

```text
78 | Комарова, 13
79 | Комарова-Добровольского, поз.1
```

и:

```text
78_v33 → 78 → Комарова, 13
79_v33 → 79 → Комарова-Добровольского, поз.1
```

### Важный момент

Мы **не переносим пока эти значения в `photos.address_id`**.

То есть:

```text
photos
   │
   └── DINO/hybrid → fingerprint_id

address_fingerprints
   │
   └── fingerprint_id → address_id

address_directory
   │
   ├── simple_address
   └── legal_address
```

Это позволит потом безболезненно подключить:

**Слепки → выбрать fingerprint → назначить адрес → изменить упрощённое/юридическое название.**

А уже грид будет получать:

```text
fingerprint
    ↓
address_id
    ↓
simple_address
```

и показывать **упрощённый адрес**, а превью — **юридический**.

После проверки этого шага перейдём к **клиентскому справочнику и нормализации клиентов**, а затем уже к сохранению состояния чекбоксов каждого менеджера.

---

### 👤 **User** — 2026-08-20 22:00:30

======================================================================
ADDRESS DIRECTORY
======================================================================
(78, 'Комарова, 13', 'бул. Комарова, 13 В / пр. Космонавтов, сторона Б')
(79, 'Комарова-Добровольского, поз.1', 'бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б')

======================================================================
ADDRESS ↔ FINGERPRINT
======================================================================
('78_v33', 78, 'Комарова, 13', 'бул. Комарова, 13 В / пр. Космонавтов, сторона Б', True)
('79_v33', 79, 'Комарова-Добровольского, поз.1', 'бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б', True)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:00:33

Отлично. **Этот слой готов и зафиксирован.**

Сейчас структура уже такая:

```text
DINO / HYBRID
     │
     │ fingerprint_id
     ▼
address_fingerprints
     │
     │ address_id
     ▼
address_directory
     │
     ├── simple_address  → показываем в чекбоксах и гриде
     │
     └── legal_address   → показываем в превью
```

И сейчас:

```text
78_v33 → 78 → Комарова, 13
79_v33 → 79 → Комарова-Добровольского, поз.1
```

### Следующий слой — клиенты

Здесь предлагаю сделать **аналогичную, но более гибкую систему**.

Поскольку клиентов может быть сколько угодно, их постоянный ID генерирует PostgreSQL:

```text
client_directory

id | name | simple_name
---+------+------------
1  | ...  | ...
2  | ...  | ...
3  | ...  | ...
```

А все варианты, которые пришли из Qwen/OCR:

```text
Самокат
самокат

Ozon
ozon
ОЗОН

СБЕР
Сбер
Сбер Мобайл
```

не должны автоматически становиться разными клиентами.

Для этого уже есть:

```text
client_aliases
```

Получится:

```text
                    ┌─ Самокат
                    └─ самокат
                         │
                         ▼
client_aliases ────── client_id = 1
                         │
                         ▼
                  client_directory
                  id = 1
                  name = Самокат
                  simple_name = Самокат
```

И отдельно:

```text
photos.client
      │
      ▼
нормализация
      │
      ▼
photos.client_normalized
      │
      ▼
client_directory.id
```

Но **не будем сейчас автоматически нормализовать 526 фотографий**. Там много мусорных вариантов, и лучше сначала сделать справочник и механизм назначения.

Следующим шагом я предлагаю создать для клиентов ещё одно поле:

```text
client_directory.normalized_name
```

или, что ещё лучше, использовать `name` как каноническое имя, а `simple_name` — отображаемое имя.

То есть:

- `name` — каноническое название;
- `simple_name` — что видит менеджер;
- `client_aliases.raw_name` — все варианты исходных данных;
- `photos.client_normalized` — результат нормализации конкретной фотографии.

Это позволит потом сделать в техническом разделе **«Клиенты»** примерно такую таблицу:

```text
Канонический клиент      Варианты
────────────────────────────────────────
Самокат                  самокат
                         Самокат

Ozon                     ozon
                         ОЗОН
                         Ozon Bank

Сбер                     СБЕР
                         Сбер
```

И уже после этого подключим **левую панель клиентов**, сохранение её чекбоксов по каждому менеджеру и автоматическое обновление грида.

---

### 👤 **User** — 2026-08-20 22:01:00

да

---

### 🤖 **Assistant** — 2026-08-20 22:01:01

Да. Тогда делаем следующий технический шаг: **клиентский справочник + поле нормализованного клиента уже в `photos` у нас есть**, поэтому структуру расширять не нужно.

Сейчас проверим и создадим базовые индексы для нормализации. Затем можно будет наполнить справочник без изменения фотографий.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

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

print("=" * 70)
print("CLIENT DIRECTORY")
print("=" * 70)

# ------------------------------------------------------------
# Проверяем структуру
# ------------------------------------------------------------

cur.execute("""
    SELECT
        ordinal_position,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'client_directory'
    ORDER BY ordinal_position
""")

for pos, name, dtype in cur.fetchall():
    print(f"{pos:3}  {name:20} {dtype}")

print()
print("=" * 70)
print("CLIENT ALIASES")
print("=" * 70)

cur.execute("""
    SELECT
        ordinal_position,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'client_aliases'
    ORDER BY ordinal_position
""")

for pos, name, dtype in cur.fetchall():
    print(f"{pos:3}  {name:20} {dtype}")

print()
print("=" * 70)
print("PHOTOS NORMALIZED CLIENT")
print("=" * 70)

cur.execute("""
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (
            WHERE client IS NOT NULL
              AND TRIM(client) <> ''
        ) AS client_filled,
        COUNT(*) FILTER (
            WHERE client_normalized IS NOT NULL
              AND TRIM(client_normalized) <> ''
        ) AS normalized_filled
    FROM photos
""")

print(cur.fetchone())

print()
print("=" * 70)
print("INDEXES")
print("=" * 70)

cur.execute("""
    CREATE INDEX IF NOT EXISTS
    idx_photos_client_normalized
    ON photos(client_normalized)
""")

cur.execute("""
    CREATE INDEX IF NOT EXISTS
    idx_client_aliases_raw_name
    ON client_aliases(LOWER(TRIM(raw_name)))
""")

print("OK: idx_photos_client_normalized")
print("OK: idx_client_aliases_raw_name")

cur.close()
conn.close()

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY
```

После этого **не будем пока автоматически разбирать мусорные варианты клиентов** вроде:

```text
Самокат
самокат

Ozon
ОЗОН
ozon fresh

СБЕР
Сбер
СБЕР МОБАЙЛ
```

Это лучше сделать отдельным механизмом нормализации.

### Следующая логика будет такой

```text
Qwen
  ↓
photos.client
  ↓
normalizer
  ↓
photos.client_normalized
  ↓
client_directory.id
```

А `client_aliases` будет хранить подтверждённые соответствия:

```text
raw_name       → client_id

"самокат"      → 1
"Самокат"      → 1
"САМОКАТ"      → 1
```

При этом **левый список клиентов будет строиться только из `client_directory`**, а не непосредственно из грязного `photos.client`.

Это как раз позволит нам позже сделать нормальную систему:

**лево — клиенты → центр — грид → право — адреса**, причём состояние чекбоксов каждого менеджера будет сохраняться в `manager_selections`.

---

### 👤 **User** — 2026-08-20 22:01:16

======================================================================
CLIENT DIRECTORY
======================================================================
  1  id                   integer
  2  name                 text
  3  simple_name          text
  4  active               boolean
  5  sort_order           integer
  6  created_at           timestamp without time zone
  7  updated_at           timestamp without time zone

======================================================================
CLIENT ALIASES
======================================================================
  1  id                   bigint
  2  client_id            integer
  3  raw_name             text
  4  created_at           timestamp without time zone

======================================================================
PHOTOS NORMALIZED CLIENT
======================================================================
(526, 395, 0)

======================================================================
INDEXES
======================================================================
OK: idx_photos_client_normalized
OK: idx_client_aliases_raw_name

======================================================================
DONE
======================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:01:17

Отлично. Теперь **структура БД готова для следующего этапа**.

Сейчас имеем:

### Адреса

```text
address_directory
    78 → Комарова, 13
    79 → Комарова-Добровольского, поз.1
    ...
```

и связь:

```text
address_fingerprints
    78_v33 → 78
    79_v33 → 79
```

### Клиенты

```text
client_directory
    id → каноническое имя → отображаемое имя

client_aliases
    варианты Qwen → client_id
```

### Фотографии

```text
photos
    client                  ← исходное значение Qwen
    client_normalized       ← пока пусто
```

Сейчас:

```text
526 фотографий
395 имеют client
0 имеют client_normalized
```

Это **правильное состояние** — нормализацию пока не запускали.

---

## Теперь самое важное — менеджеры

У нас уже есть:

```text
users
user_settings
manager_selections
collections
collection_members
```

Поэтому **новых таблиц для чекбоксов создавать не надо**.

`manager_selections` уже позволяет хранить:

```text
user_id | item_type | item_id | checked
```

Например:

```text
11 | address | 78 | true
11 | address | 79 | false

11 | client  | 1  | true
11 | client  | 2  | false
```

То есть у администратора своё состояние.

А у:

```text
1  Вихляева Алена
2  Пятницына Диана
3  Аннин Илья
...
```

будет **полностью независимое состояние**.

---

# И вот теперь можно переходить к UI

Я бы сделал именно так:

```text
┌──────────────────────────────────────────────────────────────┐
│                         ПОИСК                                │
├──────────────┬──────────────────────────────┬───────────────┤
│              │                              │               │
│   КЛИЕНТЫ    │            ГРИД              │   АДРЕСА      │
│              │                              │               │
│ ☑ Самокат    │   📷  📷  📷  📷            │ ☑ Комарова,13 │
│ ☑ Яндекс     │                              │ ☐ Комарова-  │
│ ☐ Сбер       │   📷  📷  📷  📷            │   Доброволь-  │
│ ☐ Ozon       │                              │   ского, поз1 │
│              │                              │               │
└──────────────┴──────────────────────────────┴───────────────┘
```

При изменении любого чекбокса:

```text
checkbox
   ↓
manager_selections
   ↓
STATE
   ↓
refresh_photos()
   ↓
грид обновляется СРАЗУ
```

И при следующем входе менеджера:

```text
users.id
   ↓
manager_selections
   ↓
восстанавливаем checkbox
   ↓
сразу строим грид
```

### Причём список адресов

будет брать **не `STATE.addresses`**:

```python
["78", "79", ... "95"]
```

а из:

```text
address_directory
```

с резервом под будущие:

```text
78 ... 100
```

То есть мы наконец уберём жёстко зашитые адреса из UI.

**Следующий практический шаг — переделать загрузку адресов и клиентов в UI на PostgreSQL и подключить сохранение чекбоксов.** Это уже изменение Python-кода, и здесь лучше сначала посмотреть текущие `clients.py` и `addresses.py`, чтобы не сломать существующий грид.

---

### 👤 **User** — 2026-08-20 22:01:32

да

---

### 🤖 **Assistant** — 2026-08-20 22:01:32

Да. Идём аккуратно: **сначала посмотрим текущую реализацию клиентов и адресов**, ничего пока не меняя.

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
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
```

После вывода я разберу три вещи:

1. **откуда сейчас формируется левый список клиентов**;
2. **откуда формируется правый список адресов**;
3. **где именно происходит обновление грида после checkbox**.

И затем внесём изменения так, чтобы:

```text
PostgreSQL
    ↓
client_directory ──→ КЛИЕНТЫ слева
address_directory ─→ АДРЕСА справа

checkbox
    ↓
manager_selections
    ↓
STATE
    ↓
refresh_photos()
    ↓
ГРИД обновляется сразу
```

При этом существующую логику DINO/hybrid и сам механизм формирования фотографий **не трогаем**.

---

