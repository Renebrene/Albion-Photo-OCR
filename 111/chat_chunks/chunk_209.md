## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 🤖 **Assistant** — 2026-08-20 22:05:16

Да. Здесь причина простая: **`client_directory` пока пустой**, поэтому нормализатор закономерно возвращает `None`.

И это как раз правильная архитектура: Qwen пишет исходное `photos.client`, а нормализация будет отдельным слоем.

Следующим шагом я бы **не трогал `photos.client` вообще**, а заполнил справочник клиентов и сделал функцию:

`raw client → client_aliases → client_directory → simple_name`

Например:

```text
"Яндекс"       ─┐
"яндекс"       ├──> Яндекс
"Яндеск"       ┘

"Сбер"         ───> Сбер

"Самокат"      ───> Самокат
```

А в PostgreSQL:

```text
client_directory
────────────────────────────────
id | name    | simple_name
1  | Яндекс  | Яндекс
2  | Сбер    | Сбер
3  | Самокат | Самокат
```

и:

```text
client_aliases
──────────────────────────────
client_id | raw_name
1         | Яндекс
1         | яндекс
1         | Яндеск
```

### Важный момент

Для **явных опечаток** лучше не делать автоматическое `fuzzy match` без ограничений. Например:

```text
Яндеск → Яндекс       да
Янекс → Яндекс        возможно
Альбион → Альбион-Тур возможно
Сбербанк → Сбер       нельзя автоматически
```

То есть справочник должен быть **главным источником истины**, а fuzzy-нормализация — только помощником при наполнении справочника.

И аналогично с адресами:

```text
Qwen / исходные данные
        ↓
photos.address
        ↓
нормализация
        ↓
address_directory
        ↓
78 → Комарова, 13
79 → Комарова-Добровольского, поз.1
```

Причём **адрес должен определяться fingerprint → address_fingerprints**, а не Qwen.

---

Сейчас нужно сделать следующий маленький шаг: **заполнить `client_directory` реальными клиентами из текущих `photos.client`, без изменения самих фотографий**.

Дай выполнить сначала диагностику:

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
print("CURRENT RAW CLIENTS")
print("=" * 70)

cur.execute("""
    SELECT
        TRIM(client) AS client,
        COUNT(*) AS cnt
    FROM photos
    WHERE client IS NOT NULL
      AND TRIM(client) <> ''
    GROUP BY LOWER(TRIM(client))
    ORDER BY COUNT(*) DESC, LOWER(TRIM(client))
""")

for client, cnt in cur.fetchall():
    print(f"{cnt:5}  {client}")

print()
print("=" * 70)
print("CLIENT DIRECTORY")
print("=" * 70)

cur.execute("""
    SELECT id, name, simple_name, active
    FROM client_directory
    ORDER BY sort_order, id
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
PY
```

**Пока ничего автоматически не исправляем.** Сначала увидим полный фактический список того, что Qwen уже записал. Потом из него построим справочник и алиасы.

---

### 👤 **User** — 2026-08-20 22:05:36

PYnn.close()w).fetchall():d_name, activelient))
======================================================================
CURRENT RAW CLIENTS
======================================================================
Traceback (most recent call last):
  File "<stdin>", line 16, in <module>
psycopg2.errors.GroupingError: column "photos.client" must appear in the GROUP BY clause or be used in an aggregate function
LINE 3:         TRIM(client) AS client,
                     ^

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:05:37

Да, тут моя ошибка в SQL: PostgreSQL не позволяет одновременно `TRIM(client)` и группировку только по `LOWER(TRIM(client))`.

Исправляем запрос. Заодно сделаем его так, чтобы **показать реальные варианты написания**, а не потерять исходные формы — это нам как раз нужно для будущих алиасов.

Запусти:

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
print("CURRENT RAW CLIENTS")
print("=" * 70)

cur.execute("""
    SELECT
        TRIM(client) AS client,
        COUNT(*) AS cnt
    FROM photos
    WHERE client IS NOT NULL
      AND TRIM(client) <> ''
    GROUP BY TRIM(client)
    ORDER BY COUNT(*) DESC, LOWER(TRIM(client))
""")

for client, cnt in cur.fetchall():
    print(f"{cnt:5}  {client}")

print()
print("=" * 70)
print("CLIENT DIRECTORY")
print("=" * 70)

cur.execute("""
    SELECT
        id,
        name,
        simple_name,
        active
    FROM client_directory
    ORDER BY sort_order, id
""")

rows = cur.fetchall()

if not rows:
    print("(empty)")
else:
    for row in rows:
        print(row)

print()
print("=" * 70)
print("CLIENT ALIASES")
print("=" * 70)

cur.execute("""
    SELECT
        ca.id,
        ca.client_id,
        cd.name,
        ca.raw_name
    FROM client_aliases ca
    JOIN client_directory cd
      ON cd.id = ca.client_id
    ORDER BY cd.name, ca.raw_name
""")

rows = cur.fetchall()

if not rows:
    print("(empty)")
else:
    for row in rows:
        print(row)

cur.close()
conn.close()
PY
```

### Что сейчас важно

Мы пока **ничего не меняем**:

- `photos.client` — оставляем как есть;
- `client_directory` — пока пустой;
- `client_aliases` — пока пустой;
- Qwen продолжает писать свой исходный результат;
- нормализованное значение будем получать отдельно.

После вывода этого списка уже можно будет сделать первый нормализованный справочник клиентов и проверить:

```text
'Яндекс' → Яндекс
'яндекс' → Яндекс
'Яндеск' → Яндекс
'Сбер' → Сбер
'Самокат' → Самокат
```

И затем подключить это к гриду **слева клиенты / справа адреса**, не ломая существующую фильтрацию.

---

### 👤 **User** — 2026-08-20 22:05:55

PYnn.close()t(row)s:) ca.raw_name:TRIM(client))
======================================================================
CURRENT RAW CLIENTS
======================================================================
   43  EMBARGO
   30  Единая Россия
   18  самокат
   18  Сила России
   16  АЛЬБИОН-ТУР
   14  Вольный Дон
   14  Тенет
   11  Ozon
   10  БЕТСИТИ
    9  Пятёрочка
    9  Яндекс
    9  Яндекс Маркет
    8  Магнит
    8  МТС
    7  Волный Дон
    5  ozon fresh
    5  Бигфест
    5  Государственная Дума
    5  Купер
    5  Московский Цирк Никулина
    5  Сбер Мобайл
    4  hh
    4  hh.ru
    4  контракт61.рф
    3  HAVAL
    3  Волынский Дон
    3  Дон
    3  Кинопоиск
    3  Максидом
    3  ОКЕЙ
    3  ООО «Интернет Решений»
    3  Ростов-на-Дону
    3  Яндекс Лавка
    2  EMBAYGO
    2  WINLINE
    2  Бронницкий Ювелир
    2  м.ВИДЕО
    2  ОМОДА
    2  Сбер
    2  СБЕР МОБАЙЛ
    2  СИЛА РОССИИ
    2  Яндекс @Еда
    2  Яндекс Карты
    1  2026 ГОД А.М. БАЙКОВА В РОСТОВЕ - НА - ДОНУ
    1  EMBAICO
    1  EMBAI GO
    1  EMBARCO
    1  EMBARD
    1  EMBARGED
    1  EMBARIO
    1  EMBARO
    1  ESTEO MX
    1  Haval
    1  h h
    1  JELAND
    1  Ozon Bank
    1  PUMA, ПУМА, ООО «ЯНДЕКС МАРКЕТ»
    1  Автандил Очхикидзе
    1  Альбийон-Тур
    1  Альфа-Банк
    1  Ассоциация ветеранов
    1  Астродент
    1  Банк России
    1  БИГФЕСТ
    1  Биг Хит
    1  Большой Комбо
    1  Бронницкий ювелир
    1  Вкусно-и-точка
    1  Военная служба по контракту
    1  Волгий Дон
    1  Волкый Дон
    1  Выборы
    1  ВЫБОРЫ
    1  Гандбольный клуб Ростов-Дон
    1  гипер лента
    1  Годам Байкова
    1  Год А.М. Байкова в Ростове-на-Дону
    1  ГОЛ А.М. БАЙКОВА
    1  Государственная дума
    1  Государственное учреждение
    1  Государственные органы
    1  Государственные учреждения
    1  ЗВЕЗДА
    1  КИНОПОИСК
    1  Комбо
    1  Комитет по выборам
    1  Компания «Конфеты»
    1  контракт61
    1  КП «Единая Россия»
    1  КПР
    1  Курорт «Роза Хутор»
    1  ЛДМУ России
    1  Линдекс Маркет
    1  М.ВИДЕО
    1  м.Видео
    1  Мегафон
    1  музей истории города
    1  Музей истории города Ростова-на-Дону
    1  ОЗОН
    1  Олимпия
    1  ООО «Интернет Решения»
    1  ООО «Рейт Ван»
    1  Оренбург
    1  ОФИСМАГ
    1  ОЦ
    1  Прайм
    1  Рекламный агентство
    1  росмолодёжь
    1  Ростов-Дон
    1  Самокат
    1  СБЕР
    1  СЕР МОБАЙЛ
    1  Союз машиностроителей России
    1  СССР
    1  Стикермания
    1  Тенет Т41
    1  Тенит
    1  Тетн
    1  ТУРПРОНАТ
    1  УРО-ПРО
    1  Цирк Никулина
    1  Черонницкий ювелирный салон
    1  Экотворсервис
    1  Яндекс.Еда
    1  Яндекс.Маркет

======================================================================
CLIENT DIRECTORY
======================================================================
(empty)

======================================================================
CLIENT ALIASES
======================================================================
(empty)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:05:58

Вот теперь картина очень хорошая: **Qwen действительно дал достаточно «грязный» слой, который и надо нормализовать отдельно**.

Я бы сейчас **не пытался автоматически свести все 100+ вариантов**. Здесь есть два разных класса:

### 1. Явные варианты одного клиента — можно нормализовать

Например:

```text
самокат                 → Самокат
Самокат                 → Самокат

Ozon                    → Ozon
ozon fresh              → Ozon Fresh
ОЗОН                    → Ozon
Ozon Bank               → Ozon Bank

Яндекс                   → Яндекс
яндекс                   → Яндекс
Яндеск                   → Яндекс

СБЕР                     → Сбер
Сбер                     → Сбер

СБЕР МОБАЙЛ              → Сбер Мобайл
Сбер Мобайл              → Сбер Мобайл
СЕР МОБАЙЛ               → Сбер Мобайл

АЛЬБИОН-ТУР              → Альбион-Тур
Альбийон-Тур             → Альбион-Тур

М.ВИДЕО                   → М.Видео
м.ВИДЕО                   → М.Видео
м.Видео                   → М.Видео

Тенет                     → Тенет
Тенит                     → Тенет
Тетн                      → Тенет
Тенет Т41                 → Тенет
```

### 2. Сомнительные случаи — **не трогать автоматически**

Например:

```text
Вольный Дон
Волный Дон
Волынский Дон
Волгий Дон
Волкый Дон
Ростов-Дон
Дон
```

Тут алгоритм не должен самостоятельно решить, что всё это один клиент.

И особенно:

```text
Яндекс
Яндекс Маркет
Яндекс Лавка
Яндекс @Еда
Яндекс Карты
Яндекс.Еда
Яндекс.Маркет
```

Это **могут быть разные рекламодатели/заказчики**, поэтому их лучше хранить отдельными клиентами, если пользователь явно не объединил их.

---

## Предлагаю правильную схему

Не делать:

```text
photos.client → исправить
```

А делать:

```text
                    ┌─────────────────────┐
Qwen → photos.client│     исходный текст   │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │   НОРМАЛИЗАТОР      │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ client_aliases      │
                    │ точные соответствия  │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │ client_directory    │
                    │ каноническое имя    │
                    └──────────┬──────────┘
                               ↓
                    photos.client_normalized
```

То есть **`client_normalized` уже существует**, и это именно то поле, которое нам нужно использовать.

---

### А для адресов аналогично

```text
fingerprint
    ↓
address_fingerprints
    ↓
address_directory
    ├── simple_address
    └── legal_address
```

И здесь вообще не нужен Qwen.

---

## Что я предлагаю сделать сейчас

Создать **первоначальный справочник только для очевидных случаев**:

```text
Самокат
EMBARGO
Единая Россия
Сила России
Альбион-Тур
Вольный Дон
Тенет
Ozon
БЕТСИТИ
Пятёрочка
Яндекс
Яндекс Маркет
Магнит
МТС
Бигфест
Государственная Дума
Купер
Московский Цирк Никулина
Сбер Мобайл
hh
контракт61.рф
HAVAL
Кинопоиск
Максидом
ОКЕЙ
Ростов-на-Дону
Яндекс Лавка
...
```

Но **не будем сейчас создавать клиентов из каждого мусорного Qwen-ответа** вроде `EMBAYGO`, `EMBAICO`, `EMBARCO`, `EMBARD` и т. п.

Для них лучше оставить `client_normalized = NULL`, пока мы не решим, что это такое.

И это даст нам очень важное правило:

> **Неуверенность лучше оставить неизвестной, чем неправильно объединить двух разных клиентов.**

После этого можно будет сделать нормализатор с тремя уровнями:

**точное совпадение → алиас → осторожный fuzzy-match**, причём fuzzy-match только предлагает вариант, а не молча меняет данные.

---

### 👤 **User** — 2026-08-20 22:06:50

для клиентов - будет возможнот ьподгружать справочник названий на которые нужн ориентироваться

---

### 🤖 **Assistant** — 2026-08-20 22:06:50

Да. И я бы именно так и сделал — **справочник клиентов должен быть главным источником нормализации**, а не набор вручную зашитых правил в Python.

Причём лучше предусмотреть **загрузку справочника**, например из CSV/XLSX:

```text
Каноническое имя | Упрощённое имя | Варианты
Яндекс            | Яндекс         | яндекс; Яндеск; Яндекс.ру
Сбер              | Сбер           | СБЕР; сбер
Самокат           | Самокат        | самокат
Альбион-Тур       | Альбион-Тур    | АЛЬБИОН-ТУР; Альбийон-Тур
```

Но я бы сделал ещё удобнее: **одна строка — одно каноническое название**, а варианты можно загружать отдельным столбцом.

### Архитектура

```text
                 СПРАВОЧНИК КЛИЕНТОВ
                         │
                         ▼
                 client_directory
                         │
                  ┌──────┴──────┐
                  │             │
             name          simple_name
                  │
                  ▼
             client_aliases
                  │
                  ▼
Qwen → photos.client → NORMALIZER
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
           exact       alias       fuzzy
             │           │           │
             └───────────┴───────────┘
                         │
                         ▼
              photos.client_normalized
```

### И самое важное

Справочник можно будет **менять без изменения кода**.

Например, сегодня загружаем:

```text
Яндекс
Сбер
Самокат
Ozon
Альбион-Тур
```

А завтра пользователь загрузил новый справочник:

```text
Лукойл
Газпром
Ростелеком
ВТБ
...
```

Бэкенд просто перечитает его и начнёт ориентироваться на новые названия.

---

### Я бы добавил это в технический раздел «Слепки»

Раз уж там уже будет управление:

**Технический раздел → Слепки**

```text
Слепки
────────────────────────────────────────

Fingerprint     Адрес                 Действие
78_v33          Комарова, 13          [изменить]
79_v33          Комарова-Доброволь... [изменить]

[ Справочник адресов ]

[ Справочник клиентов ]

[ Загрузить справочник ]
[ Скачать текущий справочник ]
```

И отдельно:

**Справочник клиентов**

```text
Каноническое название     Упрощённое название
──────────────────────────────────────────────
Яндекс                    Яндекс
Сбер                      Сбер
Самокат                   Самокат
Ozon                      Ozon
Альбион-Тур               Альбион-Тур
```

Плюс варианты распознавания:

```text
Яндекс
 ├─ яндекс
 ├─ Яндеск
 └─ Яндекс.Еда
```

При этом **исходный `photos.client` никогда не перезаписываем**.

Это позволит потом спокойно менять алгоритм нормализации и переобрабатывать все 526 фотографий заново без повторного запуска Qwen.

**Следующий правильный шаг — сделать формат импортируемого справочника и загрузчик в PostgreSQL.** Сначала именно это, а fuzzy-нормализацию подключим после того, как справочник появится.

---

### 👤 **User** — 2026-08-20 22:07:18

далее

---

### 🤖 **Assistant** — 2026-08-20 22:07:20

Да. Идём дальше: **сначала делаем импорт справочника клиентов**, а уже потом сам нормализатор.

Я предлагаю формат CSV, который легко редактировать и Excel тоже нормально открывает:

```text
name;simple_name;aliases
Яндекс;Яндекс;яндекс|Яндеск
Сбер;Сбер;сбер|СБЕР
Самокат;Самокат;самокат
Ozon;Ozon;озон|ОЗОН
Альбион-Тур;Альбион-Тур;АЛЬБИОН-ТУР|Альбийон-Тур
```

При загрузке:

- `name` → `client_directory.name`
- `simple_name` → `client_directory.simple_name`
- `aliases` → отдельные записи `client_aliases`
- существующие записи обновляются, а не дублируются;
- `photos.client` **не изменяется**;
- после импорта можно пересчитать `photos.client_normalized`.

### Но сначала сделаем сам импортёр

Создай файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

mkdir -p data/dictionaries

cat > app/web/client_dictionary.py <<'PY'
import csv
from pathlib import Path

import psycopg2

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

def import_client_dictionary(csv_path):
    """
    Импорт справочника клиентов.

    Формат CSV:
        name;simple_name;aliases

    aliases:
        вариант1|вариант2|вариант3

    Исходное photos.client НЕ изменяется.
    """

    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    imported_clients = 0
    imported_aliases = 0

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:

            with csv_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as f:

                reader = csv.DictReader(
                    f,
                    delimiter=";",
                )

                required = {
                    "name",
                    "simple_name",
                    "aliases",
                }

                if not required.issubset(
                    reader.fieldnames or set()
                ):
                    raise ValueError(
                        "CSV должен содержать колонки: "
                        "name;simple_name;aliases"
                    )

                for row in reader:

                    name = (row.get("name") or "").strip()
                    simple_name = (
                        row.get("simple_name") or ""
                    ).strip()

                    aliases_raw = (
                        row.get("aliases") or ""
                    ).strip()

                    if not name:
                        continue

                    if not simple_name:
                        simple_name = name

                    # ------------------------------------------------
                    # CLIENT
                    # ------------------------------------------------

                    cur.execute(
                        """
                        INSERT INTO client_directory (
                            name,
                            simple_name,
                            active
                        )
                        VALUES (%s, %s, true)
                        ON CONFLICT (
                            (LOWER(TRIM(name)))
                        )
                        DO UPDATE SET
                            simple_name = EXCLUDED.simple_name,
                            active = true,
                            updated_at = now()
                        RETURNING id
                        """,
                        (
                            name,
                            simple_name,
                        ),
                    )

                    client_id = cur.fetchone()[0]

                    imported_clients += 1

                    # ------------------------------------------------
                    # ALIASES
                    # ------------------------------------------------

                    aliases = [
                        x.strip()
                        for x in aliases_raw.split("|")
                        if x.strip()
                    ]

                    # Каноническое имя тоже считаем допустимым
                    aliases.append(name)

                    for alias in aliases:

                        cur.execute(
                            """
                            INSERT INTO client_aliases (
                                client_id,
                                raw_name
                            )
                            VALUES (%s, %s)
                            ON CONFLICT (
                                client_id,
                                (LOWER(TRIM(raw_name)))
                            )
                            DO NOTHING
                            """,
                            (
                                client_id,
                                alias,
                            ),
                        )

                        imported_aliases += 1

    return {
        "clients": imported_clients,
        "aliases": imported_aliases,
    }
PY
```

После этого **пока не подключаем UI**.

Следующим шагом сделаем тестовый `clients.csv` из нескольких очевидных случаев — Яндекс, Сбер, Самокат, Ozon, Альбион-Тур — загрузим его и проверим, что PostgreSQL правильно строит:

```text
client_directory
        ↓
client_aliases
        ↓
client_normalized
```

А уже после успешного теста подключим кнопку **«Загрузить справочник клиентов»** в технический раздел.

---

### 👤 **User** — 2026-08-20 22:07:39

давай

---

### 🤖 **Assistant** — 2026-08-20 22:07:40

Да. Делаем **тестовый справочник на реальных очевидных случаях**, без fuzzy и без изменения `photos.client`.

Запусти одним блоком:

```bash id="v8p3qk"
cd ~/projects/scene_fingerprint_mvp_v02 && \

cat > data/dictionaries/clients_test.csv <<'CSV'
name;simple_name;aliases
Яндекс;Яндекс;яндекс|Яндеск
Сбер;Сбер;сбер|СБЕР
Самокат;Самокат;самокат
Ozon;Ozon;озон|ОЗОН
Альбион-Тур;Альбион-Тур;АЛЬБИОН-ТУР|Альбийон-Тур
HAVAL;HAVAL;Haval
Бигфест;Бигфест;БИГФЕСТ
Кинопоиск;Кинопоиск;КИНОПОИСК
М.Видео;М.Видео;М.ВИДЕО|м.ВИДЕО|м.Видео
Сбер Мобайл;Сбер Мобайл;СБЕР МОБАЙЛ|СЕР МОБАЙЛ
hh;hh;hh.ru|h h
Тенет;Тенет;Тенит|Тетн
CSV

echo "================ TEST DICTIONARY ================" && \
cat data/dictionaries/clients_test.csv && \

echo && \
echo "================ IMPORT ================" && \

uv run python - <<'PY'
from app.web.client_dictionary import import_client_dictionary

result = import_client_dictionary(
    "data/dictionaries/clients_test.csv"
)

print("IMPORTED CLIENTS :", result["clients"])
print("IMPORTED ALIASES :", result["aliases"])
PY

echo && \
echo "================ DATABASE ================" && \

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
print("CLIENT DIRECTORY")
print("=" * 70)

cur.execute("""
    SELECT
        id,
        name,
        simple_name,
        active
    FROM client_directory
    ORDER BY id
""")

for row in cur.fetchall():
    print(row)

print()
print("=" * 70)
print("CLIENT ALIASES")
print("=" * 70)

cur.execute("""
    SELECT
        ca.client_id,
        cd.name,
        ca.raw_name
    FROM client_aliases ca
    JOIN client_directory cd
      ON cd.id = ca.client_id
    ORDER BY cd.name, ca.raw_name
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
PY
```

### Что должно получиться

Например:

```text
CLIENT DIRECTORY

... Яндекс
... Сбер
... Самокат
... Ozon
... Альбион-Тур
... HAVAL
...
```

и:

```text
CLIENT ALIASES

Яндекс       | Яндекс
Яндекс       | яндекс
Яндекс       | Яндеск

Сбер         | СБЕР
Сбер         | сбер

Альбион-Тур  | АЛЬБИОН-ТУР
Альбион-Тур  | Альбийон-Тур
```

**Особенно важно:** пока мы не запускаем нормализацию `photos.client_normalized`. Сначала проверяем, что сам справочник и алиасы загрузились корректно.

После вывода результата следующим шагом сделаем функцию:

```text
normalize_client("Яндеск")
             ↓
          "Яндекс"

normalize_client("яндекс")
             ↓
          "Яндекс"

normalize_client("EMBAYGO")
             ↓
          None
```

То есть неизвестные варианты **не будут насильно превращаться в ближайшего клиента**.

---

### 👤 **User** — 2026-08-20 22:07:56

CLIENT ALIASES
======================================================================
(6, 'HAVAL', 'Haval')
(11, 'hh', 'h h')
(11, 'hh', 'hh')
(11, 'hh', 'hh.ru')
(4, 'Ozon', 'Ozon')
(4, 'Ozon', 'озон')
(5, 'Альбион-Тур', 'Альбийон-Тур')
(5, 'Альбион-Тур', 'АЛЬБИОН-ТУР')
(7, 'Бигфест', 'БИГФЕСТ')
(8, 'Кинопоиск', 'КИНОПОИСК')
(9, 'М.Видео', 'М.ВИДЕО')
(3, 'Самокат', 'самокат')
(2, 'Сбер', 'сбер')
(10, 'Сбер Мобайл', 'СБЕР МОБАЙЛ')
(10, 'Сбер Мобайл', 'СЕР МОБАЙЛ')
(12, 'Тенет', 'Тенет')
(12, 'Тенет', 'Тенит')
(12, 'Тенет', 'Тетн')
(1, 'Яндекс', 'яндекс')
(1, 'Яндекс', 'Яндеск')
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:07:57

Отлично. Справочник загрузился правильно. Но вижу один важный момент: **каноническое имя автоматически попало в `client_aliases` только если не было конфликта**, поэтому часть канонических значений есть, а часть нет. Это не проблема — нормализатор можно сделать так, чтобы он сначала проверял `client_directory.name`, а потом aliases.

Теперь делаем сам **безопасный нормализатор**.

Логика:

```text
photos.client
      │
      ├── точное совпадение с client_directory.name
      │
      ├── точное совпадение с client_aliases.raw_name
      │
      └── иначе NULL
```

Пока **никакого fuzzy**. Это принципиально: `EMBAYGO` не должен автоматически превратиться в `EMBARGO`.

Создай:

```bash id="2c8s0j"
cd ~/projects/scene_fingerprint_mvp_v02 && \

cat > app/web/client_normalizer.py <<'PY'
import psycopg2

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

def normalize_client(raw_name):
    """
    Безопасная нормализация клиента.

    1. Точное совпадение с canonical name.
    2. Точное совпадение с alias.
    3. Иначе None.

    Исходное значение никогда не изменяется.
    """

    if raw_name is None:
        return None

    raw_name = raw_name.strip()

    if not raw_name:
        return None

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:

            # ----------------------------------------------------
            # 1. CANONICAL NAME
            # ----------------------------------------------------

            cur.execute(
                """
                SELECT name
                FROM client_directory
                WHERE active = true
                  AND LOWER(TRIM(name)) = LOWER(TRIM(%s))
                LIMIT 1
                """,
                (raw_name,),
            )

            row = cur.fetchone()

            if row:
                return row[0]

            # ----------------------------------------------------
            # 2. ALIAS
            # ----------------------------------------------------

            cur.execute(
                """
                SELECT cd.name
                FROM client_aliases ca
                JOIN client_directory cd
                  ON cd.id = ca.client_id
                WHERE cd.active = true
                  AND LOWER(TRIM(ca.raw_name))
                      = LOWER(TRIM(%s))
                LIMIT 1
                """,
                (raw_name,),
            )

            row = cur.fetchone()

            if row:
                return row[0]

    return None
PY

echo "================ NORMALIZATION TEST ================" && \

uv run python - <<'PY'
from app.web.client_normalizer import normalize_client

tests = [
    "Яндекс",
    "яндекс",
    "Яндеск",
    "Сбер",
    "сбер",
    "СБЕР",
    "Самокат",
    "самокат",
    "Ozon",
    "озон",
    "ОЗОН",
    "Альбийон-Тур",
    "АЛЬБИОН-ТУР",
    "Haval",
    "h h",
    "hh.ru",
    "Тенит",
    "Тетн",
    "EMBAYGO",
    "EMBAICO",
    "Волный Дон",
    "",
]

for value in tests:
    print(
        repr(value),
        "=>",
        repr(normalize_client(value)),
    )
PY
```

Ожидаем принципиально такой результат:

```text
'Яндекс'        => 'Яндекс'
'яндекс'        => 'Яндекс'
'Яндеск'        => 'Яндекс'

'Сбер'          => 'Сбер'
'сбер'          => 'Сбер'
'СБЕР'          => 'Сбер'

'Самокат'       => 'Самокат'
'самокат'       => 'Самокат'

'Альбийон-Тур'  => 'Альбион-Тур'
'АЛЬБИОН-ТУР'  => 'Альбион-Тур'

'EMBAYGO'       => None
'EMBAICO'       => None
'Волный Дон'    => None
```

После этого у нас будет готов **первый безопасный слой нормализации**.

Следующий этап уже очень полезный: сделать массовый проход по `photos`:

```text
photos.client
       ↓
normalize_client()
       ↓
photos.client_normalized
```

При этом мы сможем вывести отдельный отчёт:

```text
RAW                    NORMALIZED
-----------------------------------------
Яндеск                 Яндекс
яндекс                 Яндекс
СЕР МОБАЙЛ             Сбер Мобайл
Альбийон-Тур            Альбион-Тур
...
EMBAYGO                ??? 
EMBAICO                ???
```

И вот **неопознанные значения будем отдельно разбирать**, не рискуя испортить базу.

---

### 👤 **User** — 2026-08-20 22:08:17

PY  )   repr(normalize_client(value)),normalize_client====" && \--
================ NORMALIZATION TEST ================
'Яндекс' => 'Яндекс'
'яндекс' => 'Яндекс'
'Яндеск' => 'Яндекс'
'Сбер' => 'Сбер'
'сбер' => 'Сбер'
'СБЕР' => 'Сбер'
'Самокат' => 'Самокат'
'самокат' => 'Самокат'
'Ozon' => 'Ozon'
'озон' => 'Ozon'
'ОЗОН' => 'Ozon'
'Альбийон-Тур' => 'Альбион-Тур'
'АЛЬБИОН-ТУР' => 'Альбион-Тур'
'Haval' => 'HAVAL'
'h h' => 'hh'
'hh.ru' => 'hh'
'Тенит' => 'Тенет'
'Тетн' => 'Тенет'
'EMBAYGO' => None
'EMBAICO' => None
'Волный Дон' => None
'' => None
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:08:18

Отлично. **Первый слой нормализации работает именно так, как задумано.**

Сейчас у нас есть безопасная схема:

```text
Qwen
 ↓
photos.client              ← НЕ ТРОГАЕМ
 ↓
client_normalizer
 ↓
photos.client_normalized   ← каноническое имя
```

И проверка подтверждает:

```text
Яндеск          → Яндекс
СБЕР            → Сбер
Альбийон-Тур    → Альбион-Тур
Haval           → HAVAL
h h             → hh
hh.ru           → hh
Тенит           → Тенет
Тетн            → Тенет
```

А неизвестные:

```text
EMBAYGO         → NULL
EMBAICO         → NULL
Волный Дон      → NULL
```

**Это правильно.**

### Теперь следующий шаг — массовая нормализация

Но перед записью в `photos.client_normalized` я предлагаю сделать **сухой прогон** по всей базе.

Он ничего не изменит, а покажет:

1. сколько всего фотографий;
2. сколько уже нормализуется;
3. сколько останется `NULL`;
4. какие именно неизвестные значения имеются;
5. сколько фотографий приходится на каждый вариант.

Запусти:

```bash id="q2h6rm"
cd ~/projects/scene_fingerprint_mvp_v02 && \

uv run python - <<'PY'
import psycopg2

from app.web.client_normalizer import normalize_client

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

conn = psycopg2.connect(**PG_CONFIG)
cur = conn.cursor()

cur.execute("""
    SELECT
        TRIM(client) AS raw_client,
        COUNT(*) AS cnt
    FROM photos
    WHERE client IS NOT NULL
      AND TRIM(client) <> ''
    GROUP BY TRIM(client)
    ORDER BY COUNT(*) DESC, LOWER(TRIM(client))
""")

rows = cur.fetchall()

matched = []
unknown = []

for raw_client, cnt in rows:

    normalized = normalize_client(raw_client)

    if normalized:
        matched.append(
            (
                raw_client,
                normalized,
                cnt,
            )
        )
    else:
        unknown.append(
            (
                raw_client,
                cnt,
            )
        )

print("=" * 70)
print("CLIENT NORMALIZATION DRY RUN")
print("=" * 70)

print()
print("RAW CLIENT VARIANTS :", len(rows))
print("MATCHED             :", len(matched))
print("UNKNOWN             :", len(unknown))

print()
print("=" * 70)
print("MATCHED")
print("=" * 70)

for raw, normalized, cnt in matched:
    print(
        f"{cnt:5}  "
        f"{raw!r:35} -> {normalized!r}"
    )

print()
print("=" * 70)
print("UNKNOWN")
print("=" * 70)

for raw, cnt in unknown:
    print(
        f"{cnt:5}  {raw!r}"
    )

cur.close()
conn.close()
PY
```

**После этого ничего больше не меняем.**

Посмотрим список `UNKNOWN`. Там, скорее всего, обнаружатся группы вроде `EMBARGO/EMBAYGO/EMBAICO/...`, `Волный Дон/...`, `Год А.М. Байкова/...` и т. д.

И вот тогда мы решим, **что действительно является одним клиентом**, добавим это в загружаемый справочник, повторим dry-run — и только когда результат нас устроит, одним проходом запишем `client_normalized`.

---

### 👤 **User** — 2026-08-20 22:08:36

======================================================================
   43  'EMBARGO'
   30  'Единая Россия'
   18  'Сила России'
   14  'Вольный Дон'
   10  'БЕТСИТИ'
    9  'Пятёрочка'
    9  'Яндекс Маркет'
    8  'Магнит'
    8  'МТС'
    7  'Волный Дон'
    5  'ozon fresh'
    5  'Государственная Дума'
    5  'Купер'
    5  'Московский Цирк Никулина'
    4  'контракт61.рф'
    3  'Волынский Дон'
    3  'Дон'
    3  'Максидом'
    3  'ОКЕЙ'
    3  'ООО «Интернет Решений»'
    3  'Ростов-на-Дону'
    3  'Яндекс Лавка'
    2  'EMBAYGO'
    2  'WINLINE'
    2  'Бронницкий Ювелир'
    2  'ОМОДА'
    2  'СИЛА РОССИИ'
    2  'Яндекс @Еда'
    2  'Яндекс Карты'
    1  '2026 ГОД А.М. БАЙКОВА В РОСТОВЕ - НА - ДОНУ'
    1  'EMBAICO'
    1  'EMBAI GO'
    1  'EMBARCO'
    1  'EMBARD'
    1  'EMBARGED'
    1  'EMBARIO'
    1  'EMBARO'
    1  'ESTEO MX'
    1  'JELAND'
    1  'Ozon Bank'
    1  'PUMA, ПУМА, ООО «ЯНДЕКС МАРКЕТ»'
    1  'Автандил Очхикидзе'
    1  'Альфа-Банк'
    1  'Ассоциация ветеранов'
    1  'Астродент'
    1  'Банк России'
    1  'Биг Хит'
    1  'Большой Комбо'
    1  'Бронницкий ювелир'
    1  'Вкусно-и-точка'
    1  'Военная служба по контракту'
    1  'Волгий Дон'
    1  'Волкый Дон'
    1  'Выборы'
    1  'ВЫБОРЫ'
    1  'Гандбольный клуб Ростов-Дон'
    1  'гипер лента'
    1  'Годам Байкова'
    1  'Год А.М. Байкова в Ростове-на-Дону'
    1  'ГОЛ А.М. БАЙКОВА'
    1  'Государственная дума'
    1  'Государственное учреждение'
    1  'Государственные органы'
    1  'Государственные учреждения'
    1  'ЗВЕЗДА'
    1  'Комбо'
    1  'Комитет по выборам'
    1  'Компания «Конфеты»'
    1  'контракт61'
    1  'КП «Единая Россия»'
    1  'КПР'
    1  'Курорт «Роза Хутор»'
    1  'ЛДМУ России'
    1  'Линдекс Маркет'
    1  'Мегафон'
    1  'музей истории города'
    1  'Музей истории города Ростова-на-Дону'
    1  'Олимпия'
    1  'ООО «Интернет Решения»'
    1  'ООО «Рейт Ван»'
    1  'Оренбург'
    1  'ОФИСМАГ'
    1  'ОЦ'
    1  'Прайм'
    1  'Рекламный агентство'
    1  'росмолодёжь'
    1  'Ростов-Дон'
    1  'Союз машиностроителей России'
    1  'СССР'
    1  'Стикермания'
    1  'Тенет Т41'
    1  'ТУРПРОНАТ'
    1  'УРО-ПРО'
    1  'Цирк Никулина'
    1  'Черонницкий ювелирный салон'
    1  'Экотворсервис'
    1  'Яндекс.Еда'
    1  'Яндекс.Маркет'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:08:39

Да. Сейчас **нормализация клиентов работает правильно**, и главное — она не пытается угадывать неизвестные названия.

Например:

- `яндекс` → `Яндекс`
- `Яндеск` → `Яндекс`
- `сбер` / `СБЕР` → `Сбер`
- `озон` → `Ozon`
- `Альбийон-Тур` → `Альбион-Тур`
- `EMBAYGO` → `None`
- `Вольный Дон` → `None`

То есть текущая схема готова для следующего шага.

### Следующий шаг

Делаем **справочник клиентов источником истины**:

```text
client_directory
    ↓
основные названия клиентов

client_aliases
    ↓
варианты / ошибки / написания

photos.client
    ↓
normalize_client()
    ↓
photos.client_normalized
```

А для неизвестных значений **ничего автоматически не назначаем**.

Например:

```text
EMBARGO       → ?
EMBAYGO       → ?
EMBAICO       → ?
EMBAI GO      → ?
EMBARCO       → ?
EMBARD        → ?
EMBARGED      → ?
EMBARIO       → ?
EMBARO        → ?
```

их пока оставляем как неизвестные, пока ты не загрузишь/задашь эталон.

### И я бы сейчас сделал именно загрузку справочника

В техническом разделе, аналогично адресам, отдельная закладка:

**Слепки | Клиенты | Адреса | ...**

В `Клиенты`:

```text
Справочник клиентов

[ Загрузить справочник ]

Эталонное имя       Алиасы
Яндекс              2
Сбер                1
Ozon                1
Самокат             1
Альбион-Тур         2
...
```

Формат исходного файла можно сделать максимально простым:

```csv
simple_name,alias
Яндекс,яндекс
Яндекс,Яндеск
Сбер,сбер
Сбер,СБЕР
Ozon,озон
Самокат,самокат
Альбион-Тур,Альбийон-Тур
```

Но **лучше позволить загружать и справочник только с эталонными названиями**:

```csv
simple_name
Яндекс
Сбер
Ozon
Самокат
Альбион-Тур
HAVAL
...
```

Тогда уже через интерфейс можно будет добавлять алиасы вручную.

### Сейчас базу не трогаем

У нас уже есть:

```text
client_directory
client_aliases
photos.client_normalized
```

и индексы:

```text
idx_photos_client_normalized
idx_client_aliases_raw_name
```

Это хорошая основа.

**Следующий технический шаг предлагаю сделать без изменения алгоритма:** сначала добавить импорт эталонного списка клиентов из CSV/TXT в `client_directory`, а затем уже интерфейс для назначения алиасов. После этого существующий `normalize_client()` автоматически начнёт работать на загруженном справочнике.

---

### 👤 **User** — 2026-08-20 22:09:05

можно подключить каую либо модель для умного прогона

---

### 🤖 **Assistant** — 2026-08-20 22:09:05

> **Searching the web**
>
>
> **Searching 4 websites**
>
> 
>
> Worked for a few seconds

Да. И для **этой задачи я бы как раз подключил модель**, но не вместо справочника, а как **второй, умный слой нормализации**.

У тебя сейчас есть очень хороший базовый механизм:

```text
точное совпадение
    ↓
client_aliases
    ↓
normalize_client()
    ↓
если не найдено → None
```

Можно сделать:

```text
photos.client
      ↓
1. точный справочник
      ↓
2. алиасы
      ↓
3. если неизвестно → LLM
      ↓
   предложить клиента
      ↓
   confidence
      ↓
  ≥ порога → принять
  ниже → оставить неизвестным
```

### Какую модель

Для твоего проекта я бы сначала попробовал **Qwen3-VL-4B-Instruct**, который у тебя уже фактически используется в проекте через Ollama. У Ollama есть готовая версия `qwen3-vl:4b-instruct`, около 3.3 ГБ в Q4_K_M. ([Ollama](https://ollama.com/library/qwen3-vl%3A4b-instruct?utm_source=chatgpt.com))

Но здесь нам **не нужна картинка**. Мы работаем только с названиями клиентов. Поэтому даже лучше использовать обычную текстовую модель/embedding-модель.

Например:

**Qwen3-Embedding-4B** - специально предназначена для семантического сравнения текстов, поиска и классификации; есть Q4_K_M примерно 2.5 ГБ. ([Ollama](https://ollama.com/library/qwen3-embedding?utm_source=chatgpt.com))

Однако есть важный нюанс.

### Я бы сделал двухступенчатую систему

#### Быстрый слой - Embedding

Например:

```text
"EMBAI GO"
       ↓
embedding
       ↓
сравнение со справочником
       ↓
"EMBARGO" 0.71
"EMBAYGO"  0.94
"EMBAICO"  0.82
...
```

Но embedding **не должен сам решать**, что это один клиент.

Он только выдаёт кандидатов.

#### Умный слой - Qwen

Например, передаём Qwen:

```text
Неизвестное название:
"EMBAI GO"

Кандидаты из справочника:
1. EMBARGO
2. EMBAYGO
3. EMBAICO

Выбери наиболее вероятного клиента.
Если уверенности недостаточно - верни null.
```

И заставляем модель вернуть строго:

```json
{
  "client": "EMBAYGO",
  "confidence": 0.96,
  "reason": "..."
}
```

Ollama позволяет задавать JSON Schema для структурированного ответа, поэтому результат можно получать в контролируемом формате, а не разбирать произвольный текст модели. ([Ollama](https://ollama.com/blog/structured-outputs?utm_source=chatgpt.com))

---

### И вот здесь появляется очень полезная вещь

Мы можем сделать **режим обучения справочника**.

Например, первый прогон выдаёт:

```text
UNKNOWN CLIENTS
================================================

EMBAYGO
 → EMBAYGO       0.99
 → EMBARGO       0.41

EMBAICO
 → EMBAYGO       0.88
 → EMBARGO       0.63

EMBAI GO
 → EMBAYGO       0.97

Волный Дон
 → Вольный Дон   0.98

Волынский Дон
 → Вольный Дон   0.91
```

И в интерфейсе:

```text
┌─────────────────────────────────────────────┐
│ Умная нормализация клиентов                 │
├─────────────────────────────────────────────┤
│ Волный Дон       → Вольный Дон     98%      │
│ Волынский Дон    → Вольный Дон     91%      │
│ EMBAYGO          → EMBAYGO         99%      │
│ EMBAI GO         → EMBAYGO         97%      │
│                                             │
│ [✓ Принять] [✗ Отклонить] [→ В алиасы]     │
└─────────────────────────────────────────────┘
```

После **«Принять»**:

```text
client_aliases

client_id | raw_name
----------+----------
...       | EMBAYGO
...       | EMBAI GO
```

И всё - **в следующий раз LLM уже не вызывается**.

---

## Это особенно хорошо подходит именно твоей базе

У тебя сейчас около сотни различных сырых вариантов клиентов, среди них много очевидных OCR/LLM-ошибок:

```text
Яндекс.Еда
Яндекс @Еда
Яндекс Маркет
Яндекс.Маркет
Линдекс Маркет

Вольный Дон
Волный Дон
Волынский Дон
Волгий Дон
Волкый Дон
Ростов-Дон
Гандбольный клуб Ростов-Дон
```

Здесь **нельзя просто сделать fuzzy matching** - например, `Волный Дон` → `Вольный Дон` выглядит безопасно, а `Ростов-Дон` → `Вольный Дон` уже потенциально опасно.

Поэтому правильная архитектура:

```text
                    СПРАВОЧНИК
                        │
                        ▼
photos.client ──► exact/alias ──► найдено ──► готово
                        │
                       нет
                        │
                        ▼
                   EMBEDDING
                        │
                  top 3 кандидата
                        │
                        ▼
                      QWEN
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
          уверен                 не уверен
             │                     │
             ▼                     ▼
       предложение             UNKNOWN
             │
          оператор
             │
       ┌─────┴─────┐
       ▼           ▼
    принять      отклонить
       │
       ▼
 client_aliases
```

**Это я считаю гораздо лучше, чем заставлять Qwen прогонять все 526 фотографий.** Модель будет работать только с уникальными неизвестными `client`, то есть десятки/сотня строк, а не сотни фотографий.

И ещё важнее: **LLM ничего не меняет автоматически при первом прогоне**. Она только предлагает. После подтверждения человеком результат становится обычным алиасом и дальше работает мгновенно и детерминированно.

Если хочешь, следующим шагом можем сделать именно **`smart_client_normalizer.py` + тестовый прогон по текущим неизвестным клиентам**, не затрагивая пока UI и существующую нормализацию.

---

**Sources:**

- [qwen3-vl:4b-instruct](https://ollama.com/library/qwen3-vl%3A4b-instruct?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-20 22:09:55

Сделай smart_client_normalizer.py и тестовый прогон по текущим неизвестным клиентам

---

### 🤖 **Assistant** — 2026-08-20 22:09:55

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed Albion architecture and continued planning the smart client normalizer**
>
> 
>
> Worked for 8s

Да. Здесь лучше сделать **отдельный `smart_client_normalizer.py`**, который работает поверх уже существующего справочника и **не создаёт новых клиентов**.

Логика будет такая:

1. Сначала обычный `normalize_client()` — точное совпадение/alias.
2. Если не найдено — берём **только текущие неизвестные raw-клиенты**.
3. Передаём их локальному Qwen через Ollama.
4. Qwen получает список допустимых клиентов из `client_directory`.
5. Он может выбрать **только одного из существующих клиентов** или `null`.
6. Никаких записей в БД при тестовом прогоне.
7. Показываем:
   - raw;
   - предложенный клиент;
   - confidence;
   - краткое объяснение.
8. После проверки можно будет отдельным запуском сохранить подтверждённые варианты в `client_aliases`.

Для нашего случая я бы использовал **`qwen3:4b-instruct`** — задача текстовая, поэтому VL здесь не нужен.

Создай файл командой:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > scripts/smart_client_normalizer.py <<'PY'
#!/usr/bin/env python3

import argparse
import json
import re
import sys
from collections import Counter

import psycopg2
import requests

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
DEFAULT_MODEL = "qwen3:4b-instruct"

def get_connection():
    return psycopg2.connect(**PG_CONFIG)

# ============================================================
# CLIENT DIRECTORY
# ============================================================

def get_client_directory(conn):
    sql = """
        SELECT
            id,
            name
        FROM client_directory
        WHERE active = TRUE
        ORDER BY sort_order, name
    """

    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()

# ============================================================
# EXISTING ALIASES
# ============================================================

def get_alias_map(conn):
    sql = """
        SELECT
            ca.raw_name,
            cd.name
        FROM client_aliases ca
        JOIN client_directory cd
          ON cd.id = ca.client_id
        WHERE cd.active = TRUE
    """

    result = {}

    with conn.cursor() as cur:
        cur.execute(sql)

        for raw_name, client_name in cur.fetchall():
            if raw_name is None:
                continue

            key = raw_name.strip().casefold()

            if key:
                result[key] = client_name

    return result

# ============================================================
# CURRENT RAW CLIENTS
# ============================================================

def get_current_raw_clients(conn):
    sql = """
        SELECT
            TRIM(client) AS raw_name,
            COUNT(*) AS cnt
        FROM photos
        WHERE
            client IS NOT NULL
            AND TRIM(client) <> ''
        GROUP BY TRIM(client)
        ORDER BY COUNT(*) DESC, TRIM(client)
    """

    with conn.cursor() as cur:
        cur.execute(sql)

        return [
            (row[0], int(row[1]))
            for row in cur.fetchall()
        ]

# ============================================================
# BASIC NORMALIZATION
# ============================================================

def basic_normalize(raw_name, alias_map, directory_names):
    if not raw_name:
        return None

    value = raw_name.strip()

    # exact case-insensitive alias
    key = value.casefold()

    if key in alias_map:
        return alias_map[key]

    # exact directory name
    directory_map = {
        name.strip().casefold(): name
        for name in directory_names
    }

    return directory_map.get(key)

# ============================================================
# OLLAMA
# ============================================================

def ask_qwen(raw_name, clients, model):
    client_lines = "\n".join(
        f"- {name}"
        for name in clients
    )

    system_prompt = """
Ты нормализуешь названия клиентов для фотобазы.

Твоя задача:
- получить исходное название клиента;
- выбрать наиболее вероятного клиента ТОЛЬКО из переданного справочника;
- исправлять очевидные опечатки, OCR-ошибки, регистр, пробелы,
  перестановки букв и небольшие искажения;
- учитывать очевидные варианты написания;
- НЕ придумывать нового клиента;
- НЕ выбирать клиента только потому, что он семантически похож,
  если уверенности недостаточно.

Особенно важно:
"Волный Дон" может быть опечаткой "Вольный Дон",
"Яндеск" -> "Яндекс",
"Тетн" -> "Тенет".

Если уверенности недостаточно, возвращай null.

Верни ТОЛЬКО JSON:

{
  "client": "название из справочника или null",
  "confidence": 0.0,
  "reason": "краткое объяснение"
}

confidence от 0 до 1.
""".strip()

    user_prompt = f"""
СПРАВОЧНИК ДОПУСТИМЫХ КЛИЕНТОВ:

{client_lines}

ИСХОДНОЕ НАЗВАНИЕ:
{raw_name}

Выбери клиента из справочника либо null.
""".strip()

    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
        },
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()

    content = (
        data
        .get("message", {})
        .get("content", "")
        .strip()
    )

    result = json.loads(content)

    client = result.get("client")
    confidence = result.get("confidence", 0)
    reason = result.get("reason", "")

    if client is not None:
        client = str(client).strip()

    try:
        confidence = float(confidence)
    except Exception:
        confidence = 0.0

    # Защита: Qwen не имеет права придумать клиента.
    if client not in clients:
        client = None
        confidence = 0.0

    confidence = max(
        0.0,
        min(1.0, confidence),
    )

    return {
        "client": client,
        "confidence": confidence,
        "reason": reason,
    }

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Smart normalization of unknown clients using local Qwen."
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model, default: {DEFAULT_MODEL}",
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.80,
        help="Show only proposals above this confidence.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of unknown clients. 0 = all.",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("SMART CLIENT NORMALIZER")
    print("=" * 70)
    print("MODEL:", args.model)
    print("OLLAMA:", OLLAMA_URL)
    print()

    try:
        conn = get_connection()
    except Exception as exc:
        print("[DB ERROR]", repr(exc))
        sys.exit(1)

    try:
        directory_rows = get_client_directory(conn)
        alias_map = get_alias_map(conn)
        raw_clients = get_current_raw_clients(conn)

        directory_names = [
            row[1]
            for row in directory_rows
        ]

        print("=" * 70)
        print("CLIENT DIRECTORY")
        print("=" * 70)

        for client_id, name in directory_rows:
            print(
                f"{client_id:4d}  {name}"
            )

        print()
        print("=" * 70)
        print("ALIASES:", len(alias_map))
        print("RAW CLIENT VALUES:", len(raw_clients))
        print("=" * 70)
        print()

        unknown = []

        for raw_name, count in raw_clients:

            normalized = basic_normalize(
                raw_name,
                alias_map,
                directory_names,
            )

            if normalized is None:
                unknown.append(
                    (raw_name, count)
                )

        if args.limit > 0:
            unknown = unknown[:args.limit]

        print("=" * 70)
        print("UNKNOWN CLIENTS")
        print("=" * 70)
        print("COUNT:", len(unknown))
        print()

        for raw_name, count in unknown:
            print(
                f"{count:4d}  {raw_name!r}"
            )

        print()

        if not unknown:
            print("UNKNOWN CLIENTS: none")
            return

        print("=" * 70)
        print("SMART TEST RUN")
        print("=" * 70)
        print()

        proposals = []

        for index, (raw_name, count) in enumerate(
            unknown,
            start=1,
        ):
            print(
                f"[{index}/{len(unknown)}] "
                f"{raw_name!r} "
                f"({count} photos)"
            )

            try:
                result = ask_qwen(
                    raw_name,
                    directory_names,
                    args.model,
                )

            except Exception as exc:
                print(
                    "  ERROR:",
                    repr(exc),
                )
                print()
                continue

            client = result["client"]
            confidence = result["confidence"]
            reason = result["reason"]

            if client is None:
                print(
                    "  -> NONE"
                )

            else:
                print(
                    f"  -> {client!r}"
                )
                print(
                    f"  confidence: {confidence:.3f}"
                )

                if reason:
                    print(
                        f"  reason: {reason}"
                    )

            if (
                client is not None
                and confidence >= args.min_confidence
            ):
                proposals.append(
                    {
                        "raw_name": raw_name,
                        "count": count,
                        "client": client,
                        "confidence": confidence,
                        "reason": reason,
                    }
                )

            print()

        print("=" * 70)
        print("PROPOSALS")
        print("=" * 70)

        if not proposals:
            print("(none)")
        else:
            for item in proposals:
                print(
                    f"{item['count']:4d}  "
                    f"{item['raw_name']!r}"
                    f" -> "
                    f"{item['client']!r}"
                    f"  "
                    f"[{item['confidence']:.3f}]"
                )

        print()
        print("=" * 70)
        print("IMPORTANT")
        print("=" * 70)
        print("TEST ONLY: database was NOT modified.")
        print()

    finally:
        conn.close()

if __name__ == "__main__":
    main()
PY

chmod +x scripts/smart_client_normalizer.py
python3 -m py_compile scripts/smart_client_normalizer.py && \
echo "SMART NORMALIZER: SYNTAX OK"
```

Затем сначала проверяем, что Qwen доступен:

```bash
ollama list | grep -E 'qwen3:4b-instruct|qwen2.5:7b|qwen'
```

И запускаем **без изменения БД**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 scripts/smart_client_normalizer.py \
  --model qwen3:4b-instruct \
  --min-confidence 0.80
```

### Что особенно важно

Сейчас справочник у нас уже содержит, например:

```text
HAVAL
hh
Ozon
Альбион-Тур
Бигфест
Кинопоиск
М.Видео
Самокат
Сбер
Сбер Мобайл
Тенет
Яндекс
```

Поэтому Qwen **не сможет создать**:

```text
"Новый клиент"
```

Он может только сделать:

```text
"Волный Дон" -> null
```

или, если в справочнике есть `Вольный Дон`:

```text
"Волный Дон" -> "Вольный Дон"
```

А вот такие уже известные варианты вообще не должны доходить до Qwen:

```text
яндекс       -> Яндекс
Яндеск       -> Яндекс
сбер         -> Сбер
самокат      -> Самокат
озон         -> Ozon
Альбийон-Тур -> Альбион-Тур
h h          -> hh
hh.ru        -> hh
Тенит        -> Тенет
Тетн         -> Тенет
```

То есть модель используется **только как второй уровень**, а не вместо справочника.

И главное — текущий запуск **ничего не записывает в PostgreSQL**. Сначала посмотрим его результаты по твоим нынешним неизвестным значениям:

```text
EMBARGO
Сила России
Вольный Дон
Волный Дон
Пятёрочка
Яндекс Маркет
...
EMBAYGO
EMBAICO
EMBAI GO
EMBARCO
...
```

После этого уже сделаем третий уровень: **автоматически добавлять только высокоуверенные результаты Qwen в `client_aliases`, а сомнительные оставлять на ручное подтверждение**.

---

### 👤 **User** — 2026-08-20 22:10:41

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ollama list | grep -E 'qwen3:4b-instruct|qwen2.5:7b|qwen'
qwen2.5vl:7b            5ced39dfa4ba    6.0 GB    24 hours ago    
qwen2.5vl:3b            fb90415cde1e    3.2 GB    4 days ago      
qwen3-vl:2b-instruct    ea422f1e7365    1.9 GB    4 days ago      
qwen3:1.7b              8f68893c685c    1.4 GB    6 days ago      
qwen3:0.6b              7df6b6e09427    522 MB    6 days ago      
qwen3-coder:latest      06c1097efce0    18 GB     10 days ago     
qwen3-vl:4b-instruct    ee4b975b58c1    3.3 GB    10 days ago     
qwen3-32k:latest        b3e2287c81ab    5.2 GB    10 days ago     
qwen3:4b                359d7dd4bcda    2.5 GB    10 days ago     
qwen3:8b                500a1f067a9f    5.2 GB    10 days ago     
qwen2.5-coder:7b        dae161e27b0e    4.7 GB    4 weeks ago     
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:10:42

Отлично. У тебя есть именно то, что нам нужно:

**`qwen3:4b` — 2.5 GB**. Для этой задачи я бы начал с него. `qwen3:8b` оставим как второй вариант, если 4B будет часто ошибаться.

В предыдущей команде я указал `qwen3:4b-instruct`, которого у тебя нет. Исправляем только модель.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 scripts/smart_client_normalizer.py \
  --model qwen3:4b \
  --min-confidence 0.80
```

**База при этом не изменяется.**

Получим примерно:

```text
[1/...] 'Волный Дон' (7 photos)
  -> 'Вольный Дон'
  confidence: 0.96
  reason: очевидная OCR/опечатка

[2/...] 'EMBAICO' (1 photo)
  -> NONE

[3/...] 'Яндекс Маркет' (9 photos)
  -> NONE
```

Причём `Яндекс Маркет` **должен остаться `NONE`, если в справочнике сейчас есть только `Яндекс`**. Это принципиально: не хотим, чтобы модель сама решила, что дочерний/связанный бренд надо приравнять к клиенту.

### После запуска

Пришли сюда **весь блок `SMART TEST RUN` и `PROPOSALS`**.

По нему мы определим, какие случаи Qwen действительно умеет нормально разбирать, а затем я дам следующий шаг — **режим `--apply` с защитой**, который будет записывать подтверждённые aliases в `client_aliases`, не трогая исходный `photos.client`.

---

### 👤 **User** — 2026-08-20 22:11:10

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 scripts/smart_client_normalizer.py \
  --model qwen3:4b \
  --min-confidence 0.80
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/smart_client_normalizer.py", line 9, in <module>
    import psycopg2
ModuleNotFoundError: No module named 'psycopg2'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:11:12

Да, это просто потому, что запуск идёт системным `python3`, а проект работает в `.venv`, где `psycopg2` уже установлен.

Не устанавливаем ничего заново. Запусти через окружение проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
.venv/bin/python scripts/smart_client_normalizer.py \
  --model qwen3:4b \
  --min-confidence 0.80
```

Если `.venv/bin/python` существует, это правильный вариант.

Можно сначала быстро проверить:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
.venv/bin/python -c "import psycopg2; print('psycopg2 OK')"
```

Ожидаем:

```text
psycopg2 OK
```

После этого запускай сам тест. **БД он не изменяет.**

Если вдруг `.venv/bin/python` тоже не увидит `psycopg2`, тогда уже посмотрим, каким именно Python запускается основной проект.

---

### 👤 **User** — 2026-08-20 22:11:22

uv

---

### 🤖 **Assistant** — 2026-08-20 22:11:23

Да, тогда запускаем **через `uv`**, как весь проект.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/smart_client_normalizer.py \
  --model qwen3:4b \
  --min-confidence 0.80
```

Это правильнее, чем системный `python3`: `uv` подхватит зависимости проекта, включая `psycopg2`.

Если всё нормально, получим блок:

```text
======================================================================
SMART TEST RUN
======================================================================

[1/...]
...
======================================================================
PROPOSALS
======================================================================
...
```

**Ничего в БД этот запуск не записывает.**

Пришли результат `SMART TEST RUN` + `PROPOSALS`, и разберём качество нормализации.

---

### 👤 **User** — 2026-08-20 22:12:51

есть ли смысл в модели потупее или поумнее - может быть из серии 2,5

---

### 🤖 **Assistant** — 2026-08-20 22:12:52

Да, смысл есть — и для **этой конкретной задачи** я бы даже не гнался сразу за самой умной моделью.

У нас задача не «понять текст», а **сопоставить искажённое название с небольшим справочником**. Здесь важны устойчивость к опечаткам/OCR, кириллица и строгий выбор из списка.

Из твоих моделей я бы тестировал так:

| Модель | Для client normalization | Скорость | Моё мнение |
|---|---|---:|---|
| **qwen3:1.7b** | ⭐⭐⭐ | очень быстро | попробовать как быстрый baseline |
| **qwen3:4b** | ⭐⭐⭐⭐ | быстро | **основной кандидат** |
| **qwen3:8b** | ⭐⭐⭐⭐⭐ | медленнее | если 4B ошибается |
| **qwen2.5vl:7b** | ⭐⭐⭐⭐ | заметно тяжелее | **избыточна**, VL нам не нужен |
| **qwen3:32k** | ⭐⭐⭐⭐ | тяжелее | контекст здесь не нужен |

### А вот Qwen 2.5 может быть интересным

Если у тебя есть/можешь поставить обычный:

```text
qwen2.5:3b
qwen2.5:7b
```

то **`qwen2.5:7b` я бы обязательно сравнил с `qwen3:4b`**.

Почему: у нас много специфических случаев вроде:

```text
Волный Дон
Волынский Дон
Волгий Дон
Волкый Дон

EMBARGO
EMBAYGO
EMBAICO
EMBAI GO
EMBARCO
EMBARD
EMBARGED
EMBARIO
EMBARO
```

Это уже не простая нормализация регистра. Нужно определить, является ли строка **искажением существующего клиента или самостоятельным названием**.

И здесь более крупная модель может быть лучше.

Но есть важный момент: **мы не должны позволять модели свободно фантазировать**. Правильная архитектура:

```text
                    raw client
                        │
                        ▼
              ┌──────────────────┐
              │ exact / aliases  │
              └────────┬─────────┘
                       │ нет
                       ▼
              ┌──────────────────┐
              │  smart Qwen      │
              │                  │
              │ выбор ТОЛЬКО из  │
              │ client_directory │
              └────────┬─────────┘
                       │
                ┌──────┴──────┐
                ▼             ▼
             уверенно       сомнительно
                │             │
                ▼             ▼
          alias candidate   ручная проверка
```

### Я бы сделал ещё лучше

Не выбирать одну модель наугад, а сделать **маленький benchmark на твоих реальных данных**.

У нас уже есть хороший набор известных пар:

```text
яндекс       → Яндекс
Яндеск       → Яндекс
сбер         → Сбер
самокат      → Самокат
озон         → Ozon
Альбийон-Тур → Альбион-Тур
Haval        → HAVAL
h h          → hh
hh.ru        → hh
Тенит        → Тенет
Тетн         → Тенет
```

И можно добавить специально **ложные совпадения**:

```text
Яндекс Маркет → НЕ Яндекс
Ozon Bank     → НЕ Ozon
Сбер Мобайл   → НЕ Сбер
Яндекс Лавка  → НЕ Яндекс
```

После этого прогнать:

```text
qwen3:1.7b
qwen3:4b
qwen3:8b
qwen2.5:7b
```

и получить примерно:

```text
MODEL          CORRECT   FALSE POSITIVE   NONE
------------------------------------------------
qwen3:1.7b       8/15         2             5
qwen3:4b        12/15         0             3
qwen3:8b        13/15         0             2
qwen2.5:7b      13/15         1             1
```

Тогда выбор будет **по нашей реальной задаче**, а не по общему рейтингу моделей.

И ещё: **`qwen2.5vl:7b` я бы сюда вообще не использовал**. У тебя он уже нужен для визуальных задач с фотографиями, но для нормализации названий клиентов vision-компонент только увеличивает расход ресурсов без пользы.

**Мой первый выбор сейчас — `qwen3:4b`. Второй эксперимент — `qwen2.5:7b`.**

---

### 👤 **User** — 2026-08-20 22:13:21

`qwen2.5:7b` давай сравним

---

### 🤖 **Assistant** — 2026-08-20 22:13:22

Да. Сравним **на тех же самых данных и с теми же параметрами**, чтобы сравнение с `qwen3:4b` было честным.

Сначала проверим, что обычная `qwen2.5:7b` действительно установлена:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
ollama list | grep -E '^qwen2\.5:7b'
```

Если строка есть, запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/smart_client_normalizer.py \
  --model qwen2.5:7b \
  --min-confidence 0.80
```

Это будет **тестовый режим, без записи в БД**.

После этого пришли результат. Я сопоставлю его с предыдущим `qwen3:4b` по трём критериям:

1. **правильные исправления** — `Яндеск → Яндекс`, `Волный Дон → Вольный Дон` и т. п.;
2. **ложные объединения** — например `Яндекс Маркет → Яндекс`, чего нам не нужно;
3. **сомнительные случаи** — `EMBAYGO`, `EMBAICO`, `EMBARCO` и подобные.

И уже после этого решим, какую модель ставить в постоянный smart-нормализатор.

---

### 👤 **User** — 2026-08-20 22:13:38

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
ollama list | grep -E '^qwen2\.5:7b'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:13:39

Да, значит **обычной `qwen2.5:7b` сейчас нет**. Есть только:

```text
qwen2.5vl:7b
```

Но нам нужна именно **текстовая** Qwen 2.5 7B, без VL.

Сначала можно просто скачать её:

```bash
ollama pull qwen2.5:7b
```

После загрузки:

```bash
ollama list | grep -E '^qwen2\.5:7b'
```

Должно появиться примерно:

```text
qwen2.5:7b    ...    ~4.7 GB
```

### Затем сравниваем

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/smart_client_normalizer.py \
  --model qwen2.5:7b \
  --min-confidence 0.80
```

**БД не изменяется.**

После результата у нас будет нормальное сравнение:

```text
qwen3:4b
vs
qwen2.5:7b
```

Причём я бы пока **не устанавливал `qwen2.5:3b`**. Сначала посмотрим, даст ли 7B заметный выигрыш над 4B. Если нет — оставим `qwen3:4b`: он существенно легче и быстрее для этой задачи.

---

### 👤 **User** — 2026-08-20 22:14:53

можно ли использовать каким то образом квен модели не локально а через апи

---

### 🤖 **Assistant** — 2026-08-20 22:14:55

Да. И для нашего **smart-нормализатора клиентов** это вполне имеет смысл.

Есть два принципиально разных варианта:

### 1. Qwen через API - лучший вариант для качества

Можно отправлять в облачную модель только:

```text
справочник клиентов
+
неизвестное название
```

Например:

```text
KNOWN CLIENTS:
Яндекс
Сбер
Самокат
Ozon
HAVAL
Тенет
...

UNKNOWN:
Волный Дон
```

Модель возвращает строго:

```json
{
  "client": "Вольный Дон",
  "confidence": 0.96
}
```

Но важный момент: **`Вольный Дон` должен сначала существовать в нашем справочнике**. API-модель не должна самостоятельно создавать нового клиента.

### 2. Использовать OpenAI API / другие LLM API

Технически наш `smart_client_normalizer.py` можно сделать с переключателем:

```text
--provider ollama
--provider openai
--provider ...
```

Тогда один и тот же нормализатор сможет работать:

```text
                  smart_client_normalizer
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
          Ollama                     API
        qwen3:4b              облачная Qwen/LLM
              │                         │
              └────────────┬────────────┘
                           ▼
                    client_directory
                           │
                           ▼
                     client_aliases
```

### Но есть важное преимущество локального режима

Для твоей фотобазы исходные данные потенциально большие, но **для нормализации клиентов нам вообще не нужно отправлять фотографии**.

Мы отправляем только строки:

```text
EMBAYGO
EMBAICO
Волный Дон
Яндеск
Тетн
...
```

Поэтому API здесь относительно безопасен с точки зрения объёма данных и очень экономичен по токенам.

---

### Что я бы сделал в «Альбионе»

Не заменять локальную модель, а сделать **двухуровневую систему**:

```text
             RAW CLIENT
                  │
                  ▼
        exact / alias lookup
                  │
          ┌───────┴───────┐
          │               │
        найден          не найден
          │               │
          ▼               ▼
       результат       Qwen 4B
                         │
                   confidence
                         │
                ┌────────┴────────┐
                │                 │
             ≥ 0.90             < 0.90
                │                 │
                ▼                 ▼
          предложить alias    API / ручная
                              проверка
```

То есть **API использовать только для сложных случаев**.

Это особенно интересно для твоего списка:

```text
EMBAYGO
EMBAICO
EMBAI GO
EMBARCO
EMBARD
EMBARGED
EMBARIO
EMBARO
```

Локальная 4B может сказать `NONE`. А более сильная облачная модель сможет посмотреть на весь список допустимых клиентов и понять, есть ли среди них действительно соответствие.

**При этом автоматически записывать результат API я бы пока не разрешал.** Сначала режим предложений:

```text
RAW             → SUGGESTION       CONFIDENCE
------------------------------------------------
Яндеск          → Яндекс             0.99
Тетн            → Тенет              0.97
Волный Дон      → Вольный Дон        0.91
EMBAICO         → NONE               0.42
Ozon Bank       → Ozon               0.31  ← ОТКЛОНИТЬ
```

И только после проверки человеком предложение становится `client_alias`.

Если хочешь именно **Qwen в облаке**, я могу посмотреть актуальные варианты Qwen API и цены/лимиты на сегодня и подобрать наиболее разумный для этого нормализатора.

---

### 👤 **User** — 2026-08-20 22:15:49

Подобрать наиболее разумный вариант Qwen API для этого нормализатора

---

### 🤖 **Assistant** — 2026-08-20 22:15:50

> **Searching the web**
>
>
> **Searching www.alibabacloud.com**
>
> 
>
> Worked for 4s

Да. Посмотрел **актуальные официальные варианты Qwen API на август 2026**. Для нашего `smart_client_normalizer.py` я бы **не брал дорогую Qwen Max**.

### Мой выбор: `qwen-flash`

Для нашей задачи это наиболее разумный облачный «второй уровень».

Alibaba сейчас предоставляет Qwen через официальный Model Studio и поддерживает **OpenAI-compatible Chat Completions**, то есть интеграцию можно сделать практически без изменения архитектуры нашего скрипта. ([AlibabaCloud](https://www.alibabacloud.com/help/en/model-studio/qwen-api-reference?utm_source=chatgpt.com))

У `qwen-flash`:

- текстовая модель;
- очень большой контекст;
- structured outputs;
- function calling;
- высокая производительность;
- текущая цена для региона China (Beijing) - **$0.022 / 1M input tokens + $0.216 / 1M output tokens** для контекста до 128K. ([AlibabaCloud](https://www.alibabacloud.com/help/en/model-studio/qwen-flash?utm_source=chatgpt.com))

Для нашего нормализатора это практически копейки.

---

## Но я бы сделал ещё интереснее

Не:

```text
каждый неизвестный клиент → API
```

а:

```text
                RAW CLIENT
                    │
                    ▼
             exact / alias
                    │
              найден?
             /       \
           да         нет
           │           │
           ▼           ▼
       RESULT       qwen3:4b
                       │
                  confidence
                 /           \
             >= 0.90        < 0.90
                │              │
                ▼              ▼
             RESULT        QWEN API
                              │
                              ▼
                        предложенный
                           клиент
```

То есть **локальный Qwen3:4B остаётся основным**, а облачный Qwen используется как арбитр для трудных случаев.

Это особенно подходит для твоих:

```text
EMBAYGO
EMBAICO
EMBAI GO
EMBARCO
EMBARD
EMBARGED
EMBARIO
EMBARO
```

Не надо гонять через API тысячи нормальных:

```text
Яндекс
Сбер
Самокат
Ozon
```

Они уже решаются справочником/alias.

---

## А `qwen3:8b` API?

Тоже хороший вариант, но для нашей задачи я бы его **не ставил первым**.

Официальный `qwen3-8b` сейчас стоит примерно:

**$0.072 / 1M input + $0.287 / 1M output** в глобальных регионах, а thinking output дороже - $0.717/1M. При этом Alibaba прямо указывает, что Qwen3-8B превосходит Qwen2.5-7B по общим возможностям. ([AlibabaCloud](https://www.alibabacloud.com/help/en/model-studio/qwen3-8b?utm_source=chatgpt.com))

Но для сопоставления:

```text
"Яндеск"
```

с:

```text
["Яндекс", "Сбер", "Самокат", ...]
```

нам не требуется такая мощность.

---

## А `qwen3.5-flash`?

Вот это уже очень интересный кандидат.

Сейчас у Alibaba есть `qwen3.5-flash`, который поддерживает текст, изображения и видео, structured output и огромный контекст. Цена в Beijing для первых 128K - **$0.029 / 1M input + $0.287 / 1M output**. ([AlibabaCloud](https://www.alibabacloud.com/help/en/model-studio/qwen3-5-flash?utm_source=chatgpt.com))

Но для **чистого текста клиентов** я бы всё равно начал с `qwen-flash`: нам не нужны vision-возможности.

---

# Что я предлагаю для «Альбиона»

Сделать в `smart_client_normalizer.py` поддержку:

```bash
--provider ollama
--provider qwen-api
```

и:

```bash
--model qwen3:4b
```

или:

```bash
--model qwen-flash
```

При этом API будет работать через OpenAI-compatible интерфейс Alibaba. ([AlibabaCloud](https://www.alibabacloud.com/help/en/model-studio/first-api-call-to-qwen?utm_source=chatgpt.com))

Например:

```bash
export DASHSCOPE_API_KEY="..."
```

и:

```bash
uv run python scripts/smart_client_normalizer.py \
  --provider qwen-api \
  --model qwen-flash \
  --min-confidence 0.80
```

**API-ключ в код проекта не записываем.**

---

### И ещё один важный момент

Для нашего случая я бы **не отправлял весь `photos.client` список в каждом запросе**.

Сделаем так:

```text
client_directory
        │
        ├── Яндекс
        ├── Сбер
        ├── Самокат
        ├── Ozon
        ├── HAVAL
        ├── ...
        │
        ▼
candidate generation
        │
        ▼
5-10 наиболее похожих кандидатов
        │
        ▼
Qwen API
```

То есть Qwen получает не 100+ клиентов, а, например:

```text
RAW:
Волный Дон

CANDIDATES:
1. Вольный Дон
2. Волынский Дон
3. Волгий Дон
4. Ростов-Дон
5. Гандбольный клуб Ростов-Дон
```

И спрашиваем:

> Выбери наиболее вероятное соответствие. Если соответствия нет - `NONE`.

Это будет **намного надёжнее**, чем просто просить LLM «нормализовать название».

---

**Итого:** для первого API-теста я рекомендую **`qwen-flash`**, а локальный `qwen3:4b` оставить основным. `qwen2.5:7b` имеет смысл сравнить локально, но как облачный API я бы уже ориентировался на более новое поколение Qwen3. Официальный Model Studio также поддерживает batch-вызовы, если позже понадобится прогнать сразу весь накопленный массив неизвестных клиентов. ([AlibabaCloud](https://www.alibabacloud.com/help/en/model-studio/openai-compatible-batch-chat?utm_source=chatgpt.com))

Если хочешь, следующим шагом можем **переделать наш `smart_client_normalizer.py` под `--provider ollama/qwen-api` и сразу сделать тест `qwen-flash` на текущих неизвестных клиентах**, не меняя БД.

---

**Sources:**

- [Text Generation API Reference - Alibaba Cloud Model Studio - Alibaba Cloud Documentation Center](https://www.alibabacloud.com/help/en/model-studio/qwen-api-reference?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-20 22:16:48

Qwen3-8B  у меня есть локальный - можно прогнать и тест его, через апи неудобно - закрытая экоситсема

---

### 🤖 **Assistant** — 2026-08-20 22:16:48

> **Searching the web**
>
>
> **Searching ollama.com**
>
> 
>
> Worked for a few seconds

Да. **Для нашего `smart_client_normalizer.py` я бы сейчас именно `qwen3:8b` и тестировал первым.** У тебя он уже есть локально, а для этой задачи важнее не «знания» модели, а способность сопоставлять грязное название с небольшим справочником и не делать слишком смелых совпадений.

`qwen3:8b` в Ollama - это 8.2B-параметровая модель, примерно 5.2 GB в обычной версии; она поддерживает режим без thinking, что нам как раз выгоднее для массовой нормализации. ([Ollama](https://ollama.com/library/qwen3?utm_source=chatgpt.com))

### Я бы сделал тест именно так

Не надо пока менять архитектуру. Сначала прогоняем **текущие неизвестные клиенты** через:

```text
Qwen3:8b
       ↓
справочник клиентов
       ↓
кандидаты
       ↓
JSON:
  input
  match
  confidence
  reason
       ↓
если confidence >= 0.80 → предлагаем/записываем alias
иначе → оставляем неизвестным
```

Причём **не надо давать модели весь список из 100+ клиентов на каждый запрос**. Лучше сначала обычным текстовым поиском сформировать 3-10 кандидатов.

Например:

```text
Вход:
Волный Дон

Кандидаты:
Вольный Дон
Волынский Дон
Ростов-Дон
Дон
```

И уже Qwen решает.

---

### Для нашего случая Qwen3:8b интереснее Qwen3:4b

Я бы сейчас ориентировался примерно так:

| Модель | Нормализация | Скорость | Моё мнение |
|---|---:|---:|---|
| qwen3:1.7b | слабовато | очень высокая | нет |
| qwen3:4b | хорошо | высокая | можно |
| **qwen3:8b** | **лучше** | средняя | **оптимум** |
| qwen2.5:7b | хорошо | средняя | стоит сравнить |
| qwen3:14b | ещё лучше | ниже | для этой задачи избыточно |

У Qwen3 также есть официальная возможность переключать thinking/no-thinking; для нашего нормализатора я бы **жёстко использовал `/no_think`**, чтобы не тратить время на рассуждения. ([Ollama](https://ollama.com/dengcao/Qwen3-8B?utm_source=chatgpt.com))

### И главное

У нас уже есть очень хороший реальный датасет для теста:

```text
EMBAYGO
EMBAICO
EMBAI GO
EMBARCO
EMBARD
EMBARGED
EMBARIO
EMBARO
...
Волный Дон
Волынский Дон
Волгий Дон
Волкый Дон
...
Яндекс.Еда
Яндекс.Маркет
Яндекс Маркет
...
```

То есть **не надо придумывать benchmark** - используем именно текущие данные из `photos`.

Я предлагаю следующим шагом сделать **отдельный benchmark-режим**, который прогонит неизвестные значения через `qwen3:8b` и выдаст примерно:

```text
UNKNOWN                  QWEN MATCH              CONF
-------------------------------------------------------
EMBAYGO                  EMBARGO                 0.91
EMBAICO                  EMBARGO                 0.87
EMBAI GO                 EMBARGO                 0.89
EMBARCO                  EMBARGO                 0.84
Волный Дон               Вольный Дон             0.96
Волынский Дон            Вольный Дон             0.91
Яндекс.Маркет            Яндекс Маркет           0.99
Яндекс.Еда               Яндекс Лавка            0.21
...
```

**И отдельно обязательно показывать `NO_MATCH`**, чтобы Qwen не начал превращать любое похожее слово в существующего клиента.

Для `EMBAYGO → EMBARGO` я бы вообще не разрешал автоматическое принятие только по одному LLM-ответу - это как раз хороший тест на то, насколько модель умеет отличать «похожее» от «того же самого».

Если запускаем тест сейчас, я бы сделал **одинаковый benchmark для `qwen3:4b` и `qwen3:8b`**, а затем тем же набором проверил `qwen2.5:7b`. Тогда у нас будет реальное сравнение на **наших клиентских данных**, а не общие benchmark'и.

---

**Sources:**

- [qwen3](https://ollama.com/library/qwen3?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-20 22:17:38

сделай отдельные тесты для них **`qwen3:8b`**, а затем тем же набором проверил `qwen2.5:7b`

---

