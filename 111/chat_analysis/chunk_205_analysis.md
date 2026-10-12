### 🧠 **Итоговая стратегия**

#### 1. **Связь Hybrid → `hybrid_final_id` → локальный fingerprint ID**
- Нужно найти в коде, как `hybrid_final_id` превращается в `78`, `79`, `80` и т.д.
- Пример: `hybrid_final_id = 78_v33` → `address_id = 78`
- Это преобразование **не должно ломать существующие данные**.

#### 2. **Таблица `addresses`**
```sql
CREATE TABLE addresses (
    id          INTEGER PRIMARY KEY,       -- 78, 79, 80...
    fingerprint_id TEXT UNIQUE,           -- 78_v33, 79_v33...
    name         TEXT,
    legal_address TEXT,
    simple_address TEXT
);
```

#### 3. **Таблица `photos`**
```sql
CREATE TABLE photos (
    id            SERIAL PRIMARY KEY,
    address_id    INTEGER REFERENCES addresses(id),
    client_id     INTEGER REFERENCES clients(id),
    original_filename TEXT,
    path          TEXT,
    preview_path  TEXT,
    dino_fingerprint TEXT,
    dino_score    REAL,
    dino_second_score REAL,
    dino_margin   REAL,
    hybrid_original_id TEXT,
    hybrid_final_id TEXT,
    hybrid_changed BOOLEAN,
    hybrid_old_score REAL,
    hybrid_score  REAL,
    hybrid_margin REAL,
    hybrid_neighbors TEXT[]
);
```

#### 4. **Таблица `clients`**
```sql
CREATE TABLE clients (
    id          BIGINT PRIMARY KEY,
    name        TEXT UNIQUE,
    created_at  TIMESTAMP,
    updated_at  TIMESTAMP
);
```

#### 5. **Фильтрация в гриде**
```sql
SELECT *
FROM photos
WHERE
    (address_id IN (SELECT id FROM addresses WHERE ...))
    AND
    (
        client_id IN (SELECT id FROM clients WHERE ...)
        OR client_id IS NULL
    );
```

#### 6. **Состояние фильтров**
```sql
CREATE TABLE manager_filter_state (
    user_id          BIGINT,
    filter_type      TEXT,        -- 'address' | 'client'
    item_id          INTEGER,
    checked          BOOLEAN,
    updated_at       TIMESTAMP,
    PRIMARY KEY (user_id, filter_type, item_id)
);
```

#### 7. **Подборки**
```sql
CREATE TABLE collections (
    id              BIGINT PRIMARY KEY,
    user_id         BIGINT,
    name            TEXT,
    scope           TEXT,         -- 'addresses' | 'clients' | 'photos'
    kind            TEXT,
    client_id       BIGINT,
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP
);

CREATE TABLE collection_addresses (
    collection_id  BIGINT,
    address_id     INTEGER,
    PRIMARY KEY (collection_id, address_id)
);

CREATE TABLE collection_clients (
    collection_id  BIGINT,
    client_id      BIGINT,
    PRIMARY KEY (collection_id, client_id)
);

CREATE TABLE collection_photos (
    collection_id  BIGINT,
    photo_id       INTEGER,
    PRIMARY KEY (collection_id, photo_id)
);
```

---

### 🛠️ **Действия**
1. **Анализ кода**:
   - Найдите, как `hybrid_final_id` → `address_id`.
   - Убедитесь, что `address_id` в PostgreSQL соответствует локальному номеру fingerprint.

2. **Обновление таблиц**:
   - Добавьте `address_id` и `client_id` в `photos`.
   - Создайте таблицы `addresses` и `clients`.

3. **Фильтрация в гриде**:
   - Используйте SQL-запросы с фильтрами по `address_id` и `client_id`.

4. **Состояние фильтров**:
   - Храните текущее состояние чекбоксов в `manager_filter_state`.

5. **Подборки**:
   - Используйте таблицы `collections`, `collection_addresses`, `collection_clients`, `collection_photos`.

---

### 📌 **Важно**
- **Не ломайте существующие данные**.
- **Сохраните `hybrid_final_id` как часть истории**.
- **Используйте JSONB для сложных фильтров**, если нужно.

Если у вас есть конкретный код или примеры, я помогу адаптировать их под эту модель.