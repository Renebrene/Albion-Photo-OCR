## СЕССИЯ: ФОТОБАЗА ОФИС

**Создано:** 2026-08-16 00:03:58
**Обновлено:** 2026-08-19 21:49:51
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df)

---

### 🤖 **Assistant** — 2026-08-16 02:26:57

Отлично. Вот теперь видно, что **первая версия базы реально работает**.

Мы получили то, что хотели:

```
запрос: Ozon

↓

SQLite

↓

список фотографий с этим клиентом
```

Причём качество уже достаточно хорошее.

Например:

```
Комарова13_01.JPG
client:
Ozon Fresh

text:
OZON
fresh
СКИДКА 20%
...
```

или:

```
Добровольского17_01.JPG

client:
Ozon Bank

text:
Кредитная карта...
```

---

Но сейчас видно важный момент для следующего этапа.

Qwen сделал **хорошее описание**, но есть проблема:

### 1. Клиенты пишутся в разных вариантах

Сейчас в базе:

```
Ozon
Ozon Fresh
OZON fresh
hot&fresh by ozon fresh
Ozon Bank
```

Для человека это одно семейство, для SQL — разные строки.

Нужно добавить нормализацию:

```
client_original:
"OZON fresh"

client_normalized:
"ozon"
```

---

### 2. OCR/Qwen иногда смешивает соседние объекты

Например:

```
Зорге_08.JPG
client:
hot&fresh by ozon fresh

text:
БАЙКОВ...
```

Там уже видно, что на фото может быть политический баннер рядом с Ozon.

Значит нужна следующая логика:

```
Qwen описание
        |
        |
        +---- клиент
        |
        +---- текст
        |
        +---- уверенность
```

Добавляем:

```sql
confidence
```

---

## Следующий шаг: Banner Search v01

Я предлагаю сделать уже не просто SQL, а нормальный поиск.

Команда:

```bash
uv run python scripts/banner_search_v01.py Ozon
```

Результат:

```
================================================

QUERY: Ozon

FOUND: 24

1.
Комарова13_01.JPG

CLIENT:
Ozon Fresh

TEXT:
СКИДКА 20%

MATCH:
100%

--------------------------------

2.
Стачки_41_03.JPG

CLIENT:
Ozon fresh

TEXT:
ФИЛЕ ГРУДКИ

MATCH:
98%

================================================
```

И автоматически:

```
data/output/found_banners/Ozon/
```

копируются найденные фото.

---

А дальше уже добавляем самое интересное:

## Banner Search v02

Поиск макетом:

```
бетсити.png
       |
       |
    Qwen3-VL

"синий спортивный баннер
логотип Бетсити
футбол"

       |
       |
    banner.db

       |
       |

Добровольского17_07.JPG
```

То есть мы объединяем:

```
текстовый поиск
+
визуальный поиск
+
DINO similarity
+
финальная проверка Qwen
```

---

Сейчас база уже достаточно хорошая, поэтому следующий файл логично сделать:

**`scripts/banner_search_v01.py`**

с двумя режимами:

1.

```bash
banner_search_v01.py "Ozon"
```

2.

```bash
banner_search_v01.py "Бетсити"
```

и сразу копирование результатов в `data/output/found_banners/`.

Это будет первый рабочий инструмент для отдела.

---

### 👤 **User** — 2026-08-16 02:27:58

продолжай - проверим

---

### 🤖 **Assistant** — 2026-08-16 02:27:59

> **Searching the web**
>
>
> **Searching 9 websites**
>
> 
>
> Worked for a couple of seconds

Продолжаем. Делаем **Banner Search v01**.

Первая версия будет простой и проверяемой:

- поиск по `client`
- поиск по `text`
- поиск по `description`
- нечувствительность к регистру
- копирование найденных фото
- вывод рейтинга совпадения

Создаем файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nano scripts/banner_search_v01.py
```

Вставить:

```python
#!/usr/bin/env python3

import sqlite3
import shutil
import sys

from pathlib import Path

DB_PATH = Path(
    "data/banner_database/banner.db"
)

PHOTO_DIR = Path(
    "data/input/test"
)

OUTPUT_DIR = Path(
    "data/output/found_banners"
)

def normalize(text):

    if not text:
        return ""

    return text.lower()

def search(query):

    con = sqlite3.connect(
        DB_PATH
    )

    cur = con.cursor()

q = f"%{query.lower()}%"

cur.execute(
    """
    SELECT
        file,
        client,
        text,
        colors,
        description

    FROM banners

    WHERE
        lower(client) LIKE ?
        OR lower(text) LIKE ?
        OR lower(description) LIKE ?

    """,
    (
        q,
        q,
        q
    ))

    rows = cur.fetchall()

con.close()

return rows

def copy_results(rows, query):

out = OUTPUT_DIR / query

    out.mkdir(
        parents=True,
        exist_ok=True
    )

for row in rows:

        src = PHOTO_DIR / row[0]

        if src.exists():

            shutil.copy2(
                src,
                out / src.name
            )

return out

def main():

    if len(sys.argv)<2:

        print(
            "Usage:"
        )

        print(
            "python banner_search_v01.py <text>"
        )

        return

query = " ".join(
        sys.argv[1:]
    )

print("="*60)

    print(
        "SEARCH:",
        query
    )

    print("="*60)

rows = search(
        query
    )

print(
        "FOUND:",
        len(rows)
    )

for i,row in enumerate(rows,1):

        print()

        print(
            i,
            row[0]
        )

        print(
            "CLIENT:",
            row[1]
        )

        print(
            "TEXT:",
            row[2][:150].replace(
                "\n",
                " "
            )
        )

        print(
            "COLORS:",
            row[3]
        )

if rows:

        out = copy_results(
            rows,
            query.replace(" ","_")
        )

        print()

        print(
            "COPIED TO:"
        )

        print(
            out
        )

print()

    print(
        "DONE"
    )

if __name__=="__main__":

    main()
```

---

Запускаем первый тест:

### Ozon

```bash
uv run python scripts/banner_search_v01.py Ozon
```

Ожидаем:

```text
SEARCH: Ozon

FOUND: 20+

1 Комарова13_01.JPG
CLIENT: Ozon Fresh

2 Стачки_41_03.JPG
CLIENT: Ozon fresh

...

COPIED TO:
data/output/found_banners/Ozon
```

---

Проверка:

```bash
ls data/output/found_banners/Ozon
```

---

Потом тестируем:

```bash
uv run python scripts/banner_search_v01.py Бетсити
```

и:

```bash
uv run python scripts/banner_search_v01.py аккумуляторы
```

---

После этого добавим v02:

**умный поиск:**

```
запрос:
"зеленый баннер с человеком и автомобилем"

↓

Qwen3-VL описание запроса

↓

поиск по banner.db

↓

результат
```

Сейчас главное проверить, что база → поиск → копирование работает.

---

### 👤 **User** — 2026-08-16 02:29:50

проверяем

---

### 🤖 **Assistant** — 2026-08-16 02:29:51

Отлично. Запускаем проверку по шагам.

### 1. Проверяем Ozon

В корне проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/banner_search_v01.py Ozon
```

Ожидаем что-то вроде:

```text
============================================================
SEARCH: Ozon
============================================================

FOUND: 20+

1 Комарова13_01.JPG
CLIENT: Ozon Fresh
TEXT: OZON fresh ...

2 Стачки_41_03.JPG
CLIENT: Ozon fresh
TEXT: 269 Р ...

...

COPIED TO:
data/output/found_banners/Ozon

DONE
```

Потом:

```bash
ls -lah data/output/found_banners/Ozon
```

---

### 2. Проверяем Бетсити

```bash
uv run python scripts/banner_search_v01.py Бетсити
```

Ожидаем найти:

```text
Добровольского17_07.JPG
```

Проверка:

```bash
ls data/output/found_banners/Бетсити
```

---

### 3. Проверяем поиск по тексту

Например:

```bash
uv run python scripts/banner_search_v01.py "КРЕДИТНАЯ КАРТА"
```

Должен найти:

```text
Добровольского17_01.JPG
```

---

### 4. Проверяем поиск по описанию

Например:

```bash
uv run python scripts/banner_search_v01.py "футбол"
```

или:

```bash
uv run python scripts/banner_search_v01.py "мяч"
```

---

После этого пришли вывод одного запуска:

```bash
uv run python scripts/banner_search_v01.py Бетсити
```

Особенно интересно:
- нашёл ли он `Добровольского17_07.JPG`;
- сколько ложных совпадений;
- как работает копирование.

Дальше уже будем делать **v02 — поиск по макету через Qwen3-VL + база описаний**.

---

### 👤 **User** — 2026-08-16 02:30:49

_search_v01.py Бетсити
============================================================
SEARCH: Бетсити
============================================================
FOUND: 0

DONE

---

### 🤖 **Assistant** — 2026-08-16 02:30:51

Отличный тест. И он сразу показал важный момент: **поиск работает, но проблема в нормализации данных**.

Мы ранее видели в базе:

```text
Добровольского17_07.JPG|Бетсити|БЕТСИТИ
СУПЕРЛГА ПО ФУТЗАЛУ
```

Но запрос:

```bash
Бетсити
```

не нашёл.

Причина почти наверняка в том, что SQLite `LIKE` и `lower()` плохо работают с кириллицей в стандартной сборке SQLite.

То есть:

```sql
lower("Бетсити")
```

может остаться:

```text
Бетсити
```

а:

```sql
lower("БЕТСИТИ")
```

не станет:

```text
бетсити
```

---

Исправляем правильно: добавляем Python-нормализацию, а не полагаемся на SQLite.

Будет так:

```text
БЕТСИТИ
Бетсити
бетсити
БЕТСИТИ
```

→

```text
бетсити
```

---

Заменяем `banner_search_v01.py`.

Самое простое — изменить функцию `search()`.

Было:

```python
def search(query):

    con = sqlite3.connect(
        DB_PATH
    )

    cur = con.cursor()

q = f"%{query.lower()}%"

cur.execute(
    """
    SELECT
        file,
        client,
        text,
        colors,
        description

    FROM banners

    WHERE
        lower(client) LIKE ?
        OR lower(text) LIKE ?
        OR lower(description) LIKE ?

    """,
    (
        q,
        q,
        q
    ))

    rows = cur.fetchall()

con.close()

return rows
```

Меняем на:

```python
def search(query):

    query = query.lower()

con = sqlite3.connect(
        DB_PATH
    )

    cur = con.cursor()

cur.execute(
    """
    SELECT
        file,
        client,
        text,
        colors,
        description

    FROM banners

    """
    )

all_rows = cur.fetchall()

con.close()

result=[]

for row in all_rows:

        blob = " ".join(
            [
                str(row[1]),
                str(row[2]),
                str(row[4])
            ]
        ).lower()

if query in blob:

            result.append(
                row
            )

return result
```

---

Теперь повторяем:

```bash
uv run python scripts/banner_search_v01.py Бетсити
```

Ожидаем:

```text
FOUND: 1

1 Добровольского17_07.JPG

CLIENT:
Бетсити

TEXT:
БЕТСИТИ
СУПЕРЛИГА ПО ФУТЗАЛУ
```

---

Это даже лучше для нашей архитектуры.

Почему:

Сейчас у нас всего 257 фото — полный проход по базе мгновенный.

Когда будет 100 000 фото, сделаем уже правильно:

```
SQLite FTS5
+
нормализованное поле client_search
+
embedding
```

Но для MVP сейчас такой вариант надёжнее.

После этого проверим:

```bash
uv run python scripts/banner_search_v01.py Ozon
```

и:

```bash
uv run python scripts/banner_search_v01.py Сбер
```

И уже можно переходить к **поиску по изображению макета**.

---

### 👤 **User** — 2026-08-16 02:31:43

давай готовый файл или sed

---

### 🤖 **Assistant** — 2026-08-16 02:31:44

Сделаем проще — **готовый файл целиком**.  
Это будет `banner_search_v02.py`, чтобы не ломать рабочий `v01`.

Создайте:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nano scripts/banner_search_v02.py
```

Вставьте:

```python
#!/usr/bin/env python3

import sqlite3
import shutil
import sys

from pathlib import Path

DB_PATH = Path(
    "data/banner_database/banner.db"
)

PHOTO_DIR = Path(
    "data/input/test"
)

OUTPUT_DIR = Path(
    "data/output/found_banners"
)

def normalize(text):

    if text is None:
        return ""

    return str(text).lower().strip()

def search(query):

    query = normalize(query)

con = sqlite3.connect(
        DB_PATH
    )

    cur = con.cursor()

cur.execute(
    """
    SELECT
        file,
        client,
        text,
        colors,
        description

    FROM banners
    """
    )

rows = cur.fetchall()

con.close()

result = []

for row in rows:

searchable = " ".join(
            [
                row[0],
                row[1],
                row[2],
                row[3],
                row[4]
            ]
        )

searchable = normalize(
            searchable
        )

if query in searchable:

            result.append(
                row
            )

return result

def copy_results(rows, query):

    out = OUTPUT_DIR / query.replace(
        " ",
        "_"
    )

out.mkdir(
        parents=True,
        exist_ok=True
    )

for row in rows:

        src = PHOTO_DIR / row[0]

if src.exists():

            shutil.copy2(
                src,
                out / src.name
            )

return out

def main():

    if len(sys.argv) < 2:

        print(
            "Usage:"
        )

        print(
            "python banner_search_v02.py <query>"
        )

        return

query = " ".join(
        sys.argv[1:]
    )

print("="*60)
    print(
        "SEARCH:",
        query
    )
    print("="*60)

rows = search(
        query
    )

print(
        "FOUND:",
        len(rows)
    )

for i,row in enumerate(rows,1):

        print()

        print(
            f"{i}. {row[0]}"
        )

        print(
            "CLIENT:",
            row[1]
        )

        print(
            "TEXT:",
            row[2][:200].replace(
                "\n",
                " "
            )
        )

        print(
            "COLORS:",
            row[3]
        )

if rows:

        out = copy_results(
            rows,
            query
        )

        print()

        print(
            "COPIED:"
        )

        print(
            out
        )

print()
    print(
        "DONE"
    )

if __name__ == "__main__":

    main()
```

Сохранить:

`Ctrl+O` → Enter → `Ctrl+X`

---

Тест:

### Бетсити

```bash
uv run python scripts/banner_search_v02.py Бетсити
```

Ожидаем:

```text
FOUND: 1

1. Добровольского17_07.JPG
CLIENT: Бетсити
TEXT: БЕТСИТИ СУПЕРЛИГА ПО ФУТЗАЛУ

COPIED:
data/output/found_banners/Бетсити
```

---

Потом:

```bash
uv run python scripts/banner_search_v02.py Ozon
```

и:

```bash
ls data/output/found_banners
```

Если это заработает — следующим шагом добавляем **поиск по макету изображения**:

```
макет.jpg
    |
    v
Qwen3-VL описание
    |
    v
banner.db
    |
    v
найденные фото
```

и это уже будет близко к конечному варианту.

---

### 👤 **User** — 2026-08-16 02:33:12

SEARCH: Ozon
============================================================
FOUND: 24

1. Вавилова52_12.JPG
CLIENT: Ozon Fresh
TEXT: 189₽ БЕДРО ПО-КАВКАЗУ Озон fresh ООО «Интернет-реклама» всё с агрокомпанией, тракторами и молоком — от 3 до 10% в год. Полюс побежден. Дары познания. Сотрудникам, которые хотят поднимать уровень.
COLORS: pink, cyan

2. Стачки_41_03.JPG
CLIENT: Ozon fresh
TEXT: 269 Р ФИЛЕ ГРУДКИ 1 кг БлагоЯр OZON fresh ПОЛУЧАЙТЕ ПРОМОКОДЫ: — на любой товар, — на оплату доставки. ЗАПРЕЩЕННЫЕ ОТВЕТЫ — по всем вопросам и предложениям: 8-800-500-77-96.
COLORS: pink, light blue, white, red, black

3. Комарова13_06.JPG
CLIENT: 
TEXT: 
COLORS: 

4. Комарова13_20.JPG
CLIENT: БИФЕСТ
TEXT: БИФЕСТ 221° 135° Больше выгоды до 1 февраля Бег Хет
COLORS: blue, red, white, green, black

5. Малиновского(_08.JPG
CLIENT: Ozon fresh
TEXT: 249Р ВЕТКИНА ДЛЯ ЗАВТРАКА OZON fresh 6+
COLORS: pink, blue, white

6. Менжинского_14.JPG
CLIENT: 
TEXT: 
COLORS: 

7. Комарова13_16.JPG
CLIENT: Ozon
TEXT: 199₽ СЫР ГАУДА ПРЕМИУМ Сыр Антон, 2017 OZON fresh
COLORS: pink, cyan

8. Рубиновый_05.JPG
CLIENT: OZON fresh
TEXT: ООО «Интернет-Решения» (г. Зеленый, Россия), ГУДЗЕНСКИЙ ПЛ. Д. 10 37 АТ ПОМ. СВОБ. ЛУГА, В ТОРГОВЫХ ОТЕЛОНАХ
COLORS: green, pink, white

9. Комарова13_09.JPG
CLIENT: Самокат
TEXT: 199 ₽ -40% 337 Особенности кормления Двигательный топт  OZON fresh 6+ Предназначен для детей старше 6 лет. Карточные батончики с чистым вкусом и привлекательным внешним видом.
COLORS: red, white, blue, black

10. Зорге_08.JPG
CLIENT: hot&fresh by ozon fresh
TEXT: 2026 ГОД АМ. БАЙКОВА в Ростове-на-Дону БАЙКОВ АНДЕРЁЙ МАТВЕЕВИЧ
COLORS: pink, white, black

11. Рубиновый_02.JPG
CLIENT: Ozon
TEXT: 259 ₽ СОФРЕЛЬ СЛАДОСТОПЕНАЯ Напиток, 500 г. OZON fresh 
COLORS: pink, light blue

12. Ленина125_09.JPG
CLIENT: СБЕР МОБАЙЛ
TEXT: Для всех и каждого Тариф за 390 ₽ выгоднее с Прайм Звонок 5016
COLORS: red, white, green

13. Шеболдаева8_16.JPG
CLIENT: Ozon Fresh
TEXT: 399Р ПЕЛЬМЕНИ НАМИ! Онлайн-магазин Свежие пельмени от OZON FRESH Самый вкусный выбор OZON fresh Заказать сейчас www.ozon.ru
COLORS: pink, light blue, black, white

14. Зорге_06.JPG
CLIENT: hot&fresh by ozon fresh
TEXT: 2026 ГОД АЛЕКСАНДРА БАЙКОВА в Ростове-на-Дону БАЙКОВ АНДРЕЙ МАТВЕЕВИЧ ПРИ ПОДДЕРЖКЕ СТРОИТЕЛЬНОЙ КОМПАНИИ СК10
COLORS: pink, white, black

15. Малиновского(_10.JPG
CLIENT: Ozon
TEXT: OZON fresh ООО «АРТУМ» ПРОДУКЦИЯ: ОВОЩИ, ФРЕШ-ПРОДУКТЫ, КУРИНЫЕ ПОСТРОЙКИ, И Т.Д. 
COLORS: cyan, pink, white

16. Вавилова52_15.JPG
CLIENT: Ozon fresh
TEXT: 49 Р МОРОЖЕНОЕ OZON fresh 6+
COLORS: pink, blue, white

17. Стачки_41_02.JPG
CLIENT: Ozon
TEXT: OOO «Интернет-релейн»: 123/2, г. Москва, Проспект Гагарина, д. 40.  Тел. (495) 778-26-04.
COLORS: blue, pink

18. Добровольского17_01.JPG
CLIENT: Ozon Bank
TEXT: Кредитная карта до 140 дней ОЦЕНИВАЙТЕ СВОИ ФИНАНСОВЫЕ ВОЗМОЖНОСТИ И ДЕНЬ КАК МИНУТ. УДИЛИВШИЕ РАЗРЯДЫ ПРОДУКТОВ В ЭЛЕГАНТНЫХ ЦЕНИКАХ.
COLORS: blue, white, purple

19. Зорге_12.JPG
CLIENT: Ozon
TEXT: 119 Р КОЛБАСА ВАРЁНАЯ Ozon fresh 6+
COLORS: pink, cyan

20. Комарова13_17.JPG
CLIENT: Ozon
TEXT: OZON fresh ЛОД-КУЛТУРПЕТ ПИЛЕМНИК - СЦИПА, ГОРОДА, ЛЮБОЙ КРАСНЫХ ОТВЕТОВ. А. И. 38 42 ТОМ. I ЕДНАЯ Б У ДИ ПО137705453 ПОВЕРХНОСТЬ ЧДЕСЬ
COLORS: cyan, pink, black, white

21. Малиновского(_15.JPG
CLIENT: OZON fresh
TEXT: 199 ₽ СЫР ГАВДА ПРЕМИУМ OZON fresh • Матрацы • Möbel • Oberbetten • Heimtextilien • Gartenmöb Qualität sehr preiswert.
COLORS: pink, blue

22. Комарова13_01.JPG
CLIENT: Ozon Fresh
TEXT: OZON fresh СКИДКА 20% — СЕЙЧАС 204.45 → 163.64 ВНИМАНИЕ:  ОБНОВЛЕНЫЕ ПРЕДЛОЖЕНИЯ!  ПРОДУКТЫ ОЗОН FRESH - БУДЬТЕ В СИСТЕМЕ!
COLORS: cyan, pink, white

23. Малиновского(_06.JPG
CLIENT: ozon fresh
TEXT: 249Р КЛУБНИКА ozon fresh
COLORS: pink, light blue, red, white

24. Комарова13_12.JPG
CLIENT: Ozon fresh
TEXT: ОБЪЕДИНЯЕМ ТЕХ, КТО СОЗДАЕТ БУДУЩЕЕ! КВАС ПОДКЛЮЧИТЕ МАГАЗИН
COLORS: blue, red, white, black

COPIED:
data/output/found_banners/Ozon

DONE
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 

  есть коне что совсем лишнее\

---

### 🤖 **Assistant** — 2026-08-16 02:33:13

Да, результат уже очень показательный. Сам поиск работает, но видно **главную проблему базы**: сейчас мы ищем по всему `blob`, а Qwen иногда записал в описание соседние элементы или ошибочный текст.

Например:

### Ложные:

```
Комарова13_20.JPG
CLIENT: БИФЕСТ
TEXT: БИФЕСТ...
```

Попало, потому что где-то в `description` или `raw_json` есть слово Ozon.

---

```
Зорге_08.JPG
CLIENT: hot&fresh by ozon fresh

TEXT:
2026 ГОД БАЙКОВ...
```

Это уже интересный случай: возможно рядом баннер Ozon + другой баннер политика.

---

```
Добровольского17_01.JPG
CLIENT:
Ozon Bank
```

Это спорно. Если задача "найти все Ozon" — это правильный результат.

---

## Что надо изменить

Нужно разделить поля:

Сейчас:

```
client
text
description
```

и поиск:

```
client + text + description
```

слишком широкий.

Сделаем веса:

```
client      × 5
text        × 3
description × 1
```

То есть:

Если клиент:

```
Ozon
```

совпало → высокий балл.

Если только описание содержит Ozon → низкий.

---

Например:

```
Комарова13_20.JPG

client:
БИФЕСТ

description:
рядом виден логотип Ozon
```

получит:

```
score 1
```

и уйдет вниз.

---

Предлагаю следующий файл:

`banner_search_v03.py`

Вывод:

```
SEARCH: Ozon

FOUND: 18

01  SCORE 9
Комарова13_01.JPG
CLIENT: Ozon Fresh

02 SCORE 9
Стачки_41_03.JPG
CLIENT: Ozon fresh

03 SCORE 8
Добровольского17_01.JPG
CLIENT: Ozon Bank

04 SCORE 3
Зорге_08.JPG
description only
```

И добавим режим:

```bash
--strict
```

только клиент + текст:

```bash
uv run python scripts/banner_search_v03.py Ozon --strict
```

---

Еще важный момент.

Сейчас у нас 257 фото.

Я бы добавил отдельное поле:

```sql
client_normalized
```

Например:

```
OZON fresh
Ozon Fresh
ozon
Ozon Bank

↓

ozon
```

Тогда запрос:

```
Ozon
```

будет искать семью бренда.

---

Следующий шаг я бы сделал так:

1. `banner_search_v03.py` — умный поиск по весам.
2. `banner_index_normalize.py` — один раз нормализует базу.
3. Потом подключаем Qwen для запроса:

```
"найди баннеры озон с розовым фоном"
```

и он будет искать:

```
client = ozon
colors = pink
```

У нас база уже готова на 80%. Сейчас надо только убрать шум.

---

### 👤 **User** — 2026-08-16 11:40:08

по идее, возможно давать задание нейросети "сделай мне подборку из трехфотографий с таких-то адресов, одна из этих фотографий должна быть, к пример, выборы"?

---

### 🤖 **Assistant** — 2026-08-16 11:40:09

Да, именно это — и это уже следующий уровень системы. Причём ваша текущая база `banner.db` как раз к этому подводит.

Сейчас у нас схема:

```
Фотографии дня
        |
        v
DINOv2
        |
        v
распознавание адреса
        |
        v
папки:
Ашхабадский
Стачки
Озёрная
...
```

А дальше можно добавить **агента-планировщика**.

Например пользователь пишет:

> Сделай подборку из 3 фотографий:
> - адреса Ашхабадский 13
> - одна фотография должна быть с выборами
> - одна с Ozon
> - третья любая хорошая

---

Система делает:

## 1. LLM разбирает задачу

Qwen3:

```json
{
 "count":3,
 "addresses":[
   "Ашхабадский_13"
 ],
 "requirements":[
   {
     "type":"election",
     "count":1
   },
   {
     "brand":"ozon",
     "count":1
   }
 ]
}
```

---

## 2. SQL ищет кандидатов

Например:

### выборы

```sql
SELECT file
FROM banners
WHERE 
client LIKE '%выбор%'
OR text LIKE '%кандидат%'
OR text LIKE '%2026%'
```

получаем:

```
Ашхабадский_01.JPG
```

---

### Ozon

```sql
SELECT file
FROM banners
WHERE client LIKE '%ozon%'
```

получаем:

```
Ашхабадский_05.JPG
Ашхабадский_09.JPG
```

---

### третья фотография

Берем:

- лучший кадр по качеству
- без сильного перекрытия
- лучший score DINO

---

## 3. LLM делает финальный выбор

Например:

Кандидаты:

```
Ашхабадский_01.JPG
выборы
score 0.95

Ашхабадский_05.JPG
Ozon
score 0.91

Ашхабадский_07.JPG
обычный баннер
score 0.82
```

Ответ:

```
Готово:

1. Ашхабадский_01.JPG
   причина:
   баннер выборы

2. Ашхабадский_05.JPG
   причина:
   Ozon Fresh

3. Ашхабадский_07.JPG
   общий вид
```

И копирует:

```
data/output/jobs/job_001/

01.jpg
02.jpg
03.jpg
```

---

Причём можно делать гораздо интереснее.

Например:

> Найди 5 фотографий:
> - район Северный
> - один баннер с политикой
> - один с продуктами
> - один с ярким красным фоном

LLM превращает это в фильтры:

```
район = Северный

category:
politics
food

color:
red
```

---

То есть конечная архитектура:

```
                 ┌─────────────┐
                 │  Пользователь│
                 └──────┬──────┘
                        |
                        v
                 Qwen3-VL / LLM
                        |
              понимает задание
                        |
        ┌───────────────┼───────────────┐
        v               v               v

   SQLite banner.db   DINOv2        адресная база

        |
        v

   список кандидатов

        |
        v

      LLM rerank

        |
        v

   готовая подборка
```

---

Причём самое важное: **вам не нужно каждый раз гонять Vision по всем фотографиям**.

Vision один раз создаёт карточку:

```json
{
"file":"Ашхабадский_01.JPG",

"address":"Ашхабадский 13",

"client":"Байков",

"category":[
"выборы",
"политика"
],

"colors":[
"blue",
"white"
],

"text":[
"Андрей Байков",
"2026"
],

"description":
"Портрет кандидата на синем фоне"
}
```

И дальше поиск — миллисекунды.

---

Я бы следующим этапом сделал таблицу `assets`:

```
photos
 |
 +-- address
 +-- banner_id
 +-- ai_tags
 +-- embedding
 +-- quality_score
```

Тогда система станет уже не просто распознавателем, а **поисковой системой рекламного отдела**.

Следующий практичный шаг: сделать `job_request_v01.py`, который принимает текст задания и выдаёт папку подборки. Это уже можно подключать к вашему будущему MAX/ВК боту.

---

### 👤 **User** — 2026-08-16 11:41:24

сработает ли наш проект, если файлы test будут в локальной сети?

---

### 🤖 **Assistant** — 2026-08-16 11:41:25

Да, **сработает**, но зависит от того, что именно вы подразумеваете под "файлы test в локальной сети".

Сейчас ваш проект работает с обычными путями:

```python
data/input/test
```

То есть для него файл — это просто:

```
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test/Ашхабадский_01.JPG
```

Если сделать сетевую папку доступной как обычный каталог, проекту всё равно.

---

## Вариант 1 (лучший): примонтировать сетевую папку

Например есть компьютер рекламного отдела:

```
\\SERVER\PHOTO\test
```

На Linux:

```bash
sudo mount -t cifs //SERVER/PHOTO /mnt/photos \
-o username=user,password=pass
```

Получаем:

```
/mnt/photos/test
```

И запускаем:

```bash
uv run python scripts/banner_search_v03.py Ozon
```

или меняем:

```python
PHOTO_DIR = Path("/mnt/photos/test")
```

Для программы это будет обычная папка.

---

## Вариант 2: NAS

Например:

```
Synology
TrueNAS
обычный Windows PC
```

Структура:

```
NAS
 |
 +-- photo_archive
      |
      +-- 2026-08-16
             |
             +-- Ашхабадский_01.JPG
```

Монтируем:

```
/data/photo_archive
```

и всё работает.

---

## Вариант 3: Windows-шара напрямую

Можно даже:

```
\\192.168.1.50\photos
```

через Python:

```python
PHOTO_DIR = Path(
    "//192.168.1.50/photos"
)
```

Но я бы не рекомендовал для постоянной работы.

---

## Что будет с вашим пайплайном

Сейчас:

```
Фото за день
      |
      v
data/input/test
      |
      v
DINOv2
      |
      v
распознавание адресов
      |
      v
переименование
      |
      v
banner.db
```

В сети будет:

```
Общий сервер фото
        |
        v
scene_fingerprint
        |
        v
результат
        |
        v
\\server\result
```

---

## Но есть важный момент

Ваши фотографии:

- 3500×2500
- ~4.5 МБ
- 200–300 штук

Это:

```
300 × 4.5 МБ ≈ 1.3 ГБ
```

Если читать их через Wi-Fi:

```
100 Мбит/с
```

только загрузка:

```
≈ 2 минуты
```

Плюс обработка.

Лучше:

```
NAS/сервер
    |
    +-- копируем новые фото локально
    |
    +-- обработка GPU
```

Например:

```
\\server\incoming
        |
        |
        v
rsync
        |
        |
        v
SSD локального ПК
        |
        |
        v
DINO + Qwen
```

---

## Для вашей архитектуры я бы сделал так:

```
          Рекламный отдел

              |
              |
        \\SERVER\PHOTO\DAY

              |
              v

   scene_fingerprint сервер
   Ryzen 5600 + RTX3060

              |
      ┌───────┴────────┐

      DINOv2       Qwen3-VL

              |
              v

        banner.db

              |
              v

      MAX / Web интерфейс
```

То есть да — ваш проект изначально хорошо подходит для сетевой работы.

Более того, с вашим планом (бот MAX/ВК + база баннеров + поиск по заданиям) **лучше сразу проектировать его как серверное приложение**, а не как локальный скрипт.

---

### 👤 **User** — 2026-08-16 11:42:36

если через lan 100mb и 1000mb

---

### 🤖 **Assistant** — 2026-08-16 11:42:38

Для вашего сценария разница между **LAN 100 Мбит/с и 1000 Мбит/с** будет заметной, но не во всех местах.

Посчитаем на ваших данных:

- фото: ~4.5 МБ
- за день: 200–300 фото
- общий объём: примерно **900 МБ – 1.4 ГБ**

---

### LAN 100 Мбит/с (Fast Ethernet)

Теоретически:

```
100 Мбит/с / 8 = 12.5 МБ/с
```

Реально:

```
8–11 МБ/с
```

Передача 300 фото:

```
1.3 ГБ / 10 МБ/с ≈ 130 секунд
```

То есть:

**2–3 минуты только на копирование.**

---

### LAN 1000 Мбит/с (Gigabit Ethernet)

Теоретически:

```
1000 Мбит/с / 8 = 125 МБ/с
```

Реально:

```
80–110 МБ/с
```

Передача:

```
1.3 ГБ / 100 МБ/с ≈ 13 секунд
```

---

## Но в вашем проекте сеть не будет главным тормозом

Сейчас у вас:

- RTX 3060
- DINOv2
- Qwen3-VL
- обработка окон баннеров

Время примерно:

### Копирование

| Сеть | 300 фото |
|-|-:|
| 100 Мбит | 2–3 мин |
| 1000 Мбит | 10–20 сек |

---

### DINO распознавание

Примерно:

```
300 фото × несколько секунд
```

будет:

```
10–20 минут
```

(зависит от режима)

---

### Qwen3-VL описание баннеров

Это ещё тяжелее:

```
257 фото
≈ 20–40 минут
```

если по одному.

---

## Поэтому для вашей архитектуры:

### 100 Мбит

Работать будет.

Но:

```
фото → сеть → обработка
```

будет ощущаться.

---

### 1000 Мбит

Это уже комфортно:

```
фото за день
        |
        | 15 секунд
        v
локальный SSD

        |
        v

GPU обработка
```

---

## Я бы сделал ещё лучше:

Не обрабатывать прямо из сети.

Например:

```
\\SERVER\PHOTO\2026-08-16
              |
              |
          sync_new.py
              |
              v

SSD:
data/input/today

              |
              v

DINOv2
              |
              v

Qwen3-VL
              |
              v

banner.db
```

Причина: DINO делает много чтений одного файла:

- открыть
- resize
- crop
- patch extraction

По сети это хуже.

---

Для вашего Ryzen 5600 + RTX3060 оптимально:

**Gigabit LAN + локальный NVMe SSD + GPU обработка.**

Тогда узкое место будет уже не сеть, а нейросети.

Кстати, у вас сейчас проект уже близок к серверной схеме: осталось только вынести `data/input/test` и `data/banner_database` в конфиг, чтобы не менять код при переносе на сервер.

---

### 👤 **User** — 2026-08-16 11:44:09

какие минимальные требования к железу для данного проекта, и можно ли развертывать на windows 10/11

---

### 🤖 **Assistant** — 2026-08-16 11:44:11

> **Searching the web**
>
>
> **Searching 7 websites**
>
> 
>
> Worked for a couple of seconds

Для **вашего текущего проекта `scene_fingerprint_mvp_v02`** требования сильно выше, чем у обычной программы, потому что у нас несколько тяжёлых компонентов:

- **DINOv2 ViT-B/14** - распознавание сцен
- **FAISS / embeddings** - база слепков
- **Qwen3-VL** - описание баннеров
- **SQLite** - база
- **NiceGUI/Web UI** - интерфейс

Обычные требования Windows тут не показатель: Windows 11 сама может работать от 4 ГБ ОЗУ, но AI-задачи требуют значительно больше. ([Microsoft Learn](https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements?utm_source=chatgpt.com))

---

# Минимальная конфигурация (запустится)

## CPU

Минимум:

```
Intel Core i5 8 поколения
AMD Ryzen 5 2600
```

или лучше.

Ядра:

```
4 ядра / 8 потоков
```

---

## RAM

Абсолютный минимум:

```
16 ГБ
```

Но:

- DINO + браузер + база - нормально
- Qwen3-VL будет уже тяжело

Рекомендую:

```
32 ГБ
```

---

## GPU

Минимум:

```
NVIDIA GTX 1660 6GB
```

но медленно.

Нормально:

```
RTX 3060 12GB
```

как у вас.

Это очень удачный вариант.

---

## Диск

Обязательно SSD:

```
NVMe 500 ГБ
```

Почему:

модель DINO:

≈ 350 МБ

Qwen:

3-8 ГБ

кэш:

10+ ГБ

фотоархив:

сотни гигабайт

---

# Оптимальная рабочая машина отдела

Я бы закладывал:

```
CPU:
Ryzen 5 5600
или
Ryzen 7 5700X

RAM:
32 ГБ

GPU:
RTX 3060 12GB
RTX 4060 Ti 16GB

SSD:
NVMe 1TB

LAN:
1Gb Ethernet
```

Это практически ваша текущая машина.

---

# Если запускать на Windows 10/11

Да, можно.

Архитектура будет:

```
Windows 10/11

 |
 |
 +-- Python
 |
 +-- uv
 |
 +-- PyTorch CUDA
 |
 +-- Ollama
 |
 +-- SQLite
 |
 +-- NiceGUI
```

---

## Вариант 1 - нативно Windows

Плюсы:

- проще пользователю
- доступ к сетевым папкам
- легко сделать ярлык "Запустить обработку"

Минусы:

- CUDA/PyTorch иногда капризнее
- меньше удобства разработки

---

## Вариант 2 - Windows + WSL2 (я бы выбрал)

Схема:

```
Windows 11

 |
 |
 +-- WSL2 Ubuntu

       |
       +-- scene_fingerprint
       +-- PyTorch CUDA
       +-- Ollama
       +-- SQLite
```

Получаете почти ваш текущий Linux.

Для производства это самый удобный вариант.

---

# Серверный вариант для рекламного отдела

Я бы сделал так:

```
Компьютеры сотрудников

       |
       | LAN 1Gb
       |
       v

AI SERVER

Ryzen 5600
RTX3060 12GB
32GB RAM

       |
       |
       +-- scene_fingerprint
       +-- Qwen
       +-- database

|
       v

Web интерфейс
```

На рабочих компьютерах ничего ставить не надо.

Открывают:

```
http://192.168.1.100:8080
```

и работают.

---

# По количеству фотографий

Ваш текущий поток:

```
200-300 фото / день
```

Для:

### RTX3060

комфортно:

```
до 1000 фото/день
```

---

Если будет:

```
5000-10000 фото/день
```

тогда:

```
RTX 4070 Ti
RTX 4090
64 ГБ RAM
```

---

# Мой вариант для вашей задачи

Я бы не менял вашу текущую машину:

```
Ryzen 5600
RTX3060 12GB
32GB RAM
NVMe
Gigabit LAN
```

Это почти идеальный MVP-сервер.

Следующий шаг я бы сделал не железом, а архитектурой:

```
scene_fingerprint_server

        |
        |
   Web API

        |
        +---- папка incoming
        |
        +---- база banner.db
        |
        +---- задания отдела
```

Тогда хоть Windows 10, хоть Windows 11, хоть Linux-клиенты - без разницы.

---

**Sources:**

- [Windows 11 requirements | Microsoft Learn](https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-16 11:44:54

1650 4GB Ram

---

### 🤖 **Assistant** — 2026-08-16 11:44:56

Если речь про **GTX 1650 4GB + сколько-то RAM (обычно 16/32 ГБ)**, то ситуация такая:

## GTX 1650 4GB

Она **запустит часть проекта**, но будет заметно ограничена.

### Что будет работать нормально:

✅ SQLite база баннеров  
✅ поиск по тексту  
✅ поиск по клиентам  
✅ Web-интерфейс NiceGUI  
✅ работа с уже созданными слепками  
✅ FAISS-поиск по готовым embedding'ам  

---

## DINOv2

Тут зависит от режима.

Ваш текущий:

```
facebook/dinov2-base
ViT-B/14
768 dimension
```

На GTX 1650 4GB:

- загрузится с трудом;
- batch должен быть 1;
- patch processing будет медленный;
- возможны ошибки CUDA по памяти.

Примерно:

RTX 3060 12GB:

```
1 фото ~1-3 сек
```

GTX 1650 4GB:

```
1 фото ~5-15 сек
```

---

## Qwen3-VL

Вот здесь основная проблема.

Ваш:

```
qwen3-vl:4b-instruct
3.3 GB
```

На GTX 1650:

скорее всего **не будет нормально работать через GPU**.

Причина:

сама модель:

≈3.3 ГБ

+ CUDA память

+ промежуточные тензоры

+ контекст

4 ГБ VRAM мало.

Она уйдет:

- либо в CPU,
- либо частично в GPU,
- будет медленно.

---

# Но есть хороший вариант

GTX 1650 можно использовать как **клиентскую машину**.

Например:

```
ПК оператора

GTX1650
16GB RAM
Windows 10

        |
        | LAN
        |
        v

AI сервер

RTX3060
32GB RAM

DINO
Qwen
Ollama
banner.db
```

То есть 1650 вообще не мешает.

---

# Если сделать автономную машину на GTX1650

Я бы поменял настройки:

## DINO

Вместо:

```
dinov2-base
```

использовать:

```
dinov2-small
```

или:

```
MobileNet / CLIP small
```

---

## Vision LLM

Вместо Qwen3-VL 4B:

использовать:

```
qwen3-vl 0.6b
```

или:

```
llava 3B quant
```

Но качество описания будет хуже.

---

# Минимальный ПК для самостоятельной работы

Я бы поставил так:

### Нижний предел:

```
CPU:
i5/Ryzen 5

RAM:
16 GB

GPU:
GTX 1650 4GB

SSD:
500GB
```

Он сможет:

- распознавать адреса;
- искать по базе;
- выполнять простые задачи.

Но:

- создание базы баннеров через Vision будет медленно.

---

### Комфорт:

```
CPU:
Ryzen 5 5600

RAM:
32GB

GPU:
RTX3060 12GB
```

Это ваш текущий уровень.

---

Для вашего проекта я бы сделал разделение:

**рабочие места:**
```
GTX1650
Windows
браузер
```

**один AI-сервер:**
```
RTX3060
Ubuntu
Ollama
DINO
banner.db
```

Тогда даже 10 сотрудников смогут работать через браузер.

---

### 👤 **User** — 2026-08-16 11:45:32

карты 4060 8ГБ ram?

---

### 🤖 **Assistant** — 2026-08-16 11:45:34

Если речь про **RTX 4060 8GB VRAM**, то это уже интересный вариант. Она заметно быстрее GTX 1650 и по современным AI-задачам гораздо ближе к RTX 3060, но есть нюанс — **объём видеопамяти**.

Сравнение для вашего проекта:

| Карта | VRAM | DINOv2 | Qwen3-VL 4B | Общая оценка |
|---|---:|---|---|---|
| GTX 1650 | 4 ГБ | ⚠️ медленно | ❌ почти не подходит | только клиент |
| RTX 4060 | 8 ГБ | ✅ хорошо | ⚠️ с ограничениями | хороший вариант |
| RTX 3060 | 12 ГБ | ✅ отлично | ✅ комфортно | лучший баланс |
| RTX 4070 | 12 ГБ | ✅ отлично | ✅ отлично | быстрее |
| RTX 4060 Ti | 16 ГБ | ✅ отлично | ✅ отлично | очень хороший AI вариант |

---

## RTX 4060 8GB в вашем пайплайне

### 1. Распознавание адресов (DINOv2)

Будет работать хорошо:

```
DINOv2 ViT-B/14
768 dim
FAISS
patch tokens
```

Ограничения:

- batch = 1–4
- без больших параллельных окон

Но для ваших:

```
200–300 фото/день
```

нормально.

---

### 2. Создание базы баннеров (Qwen3-VL 4B)

Вот тут важный момент.

Qwen3-VL:

```
4.4B параметров
Q4_K_M
≈3.3 GB
```

На RTX 4060 8GB:

запустится, но:

```
модель ~4 ГБ
+
CUDA buffers
+
изображение
+
контекст
```

может упираться в память.

Я бы сделал:

- Ollama с GPU offload
- ограниченный context
- обработка по одному изображению

То есть:

```
1 фото
↓
Qwen3-VL
↓
JSON
↓
следующее фото
```

---

## Скорость относительно вашей RTX3060

Примерно:

### DINO

RTX3060 12GB:

```
100%
```

RTX4060:

```
120–140%
```

(она новее и быстрее на ядро)

---

### Qwen

RTX3060 выигрывает иногда из-за VRAM:

RTX4060:

```
быстрее вычисления
но меньше памяти
```

RTX3060:

```
медленнее ядра
но больше пространства
```

Для LLM часто важнее VRAM.

---

## Если покупать специально под ваш проект

Я бы расставил так:

### 1 место — RTX 4060 Ti 16GB

Очень удачно:

- DINO быстро
- Qwen без мучений
- запас под будущие модели

---

### 2 место — RTX 3060 12GB

До сих пор отличный AI-вариант:

- дешёвая
- много VRAM
- проверенная

---

### 3 место — RTX 4060 8GB

Хорошая универсальная карта:

- офис
- игры
- DINO
- лёгкий AI

Но для развития проекта немного тесно.

---

С учётом вашего плана (Qwen-VL → описание баннеров → поиск по базе → агент для рекламного отдела) я бы **не брал 8GB как основную AI-карту**. Минимум:

**12GB VRAM**, а лучше **16GB**.

RTX 4060 8GB отлично подошла бы как машина оператора, а сервер с RTX3060 12GB или RTX4060Ti 16GB — как AI-ядро.

---

### 👤 **User** — 2026-08-16 11:46:26

Qwen3-VL 4B - можно ли заменить на менее емкую модель, возможно 2.5

---

### 🤖 **Assistant** — 2026-08-16 11:46:28

> **Searching the web**
>
>
> **Searching 9 websites**
>
> 
>
> Worked for a couple of seconds

Да, для **вашей задачи** (описание рекламных баннеров, извлечение клиента, текста, цветов, категории) вполне можно заменить **Qwen3-VL 4B** на меньшую модель. Более того, я бы это сделал.

Сейчас у вас задача не требует сложного рассуждения. Вам нужно:

- прочитать текст на баннере;
- понять бренд;
- определить категорию;
- описать изображение;
- вернуть JSON.

Это не "решение задач", а **визуальная индексация**.

Qwen3-VL имеет варианты меньшего размера (семейство включает 2B/4B/8B и другие версии), поэтому уменьшение модели - нормальный путь для edge/локального запуска. ([arXiv](https://arxiv.org/abs/2511.21631?utm_source=chatgpt.com))

---

## Варианты для вашего проекта

### Вариант 1 - Qwen3-VL 2B (лучший кандидат)

Примерно:

```
Qwen3-VL 2B
```

Плюсы:

✅ меньше памяти  
✅ быстрее  
✅ легче для RTX 4060 8GB  
✅ можно запускать много рабочих мест  

Минусы:

- хуже длинные описания;
- иногда хуже понимает сложные композиции.

Для ваших баннеров:

**скорее всего достаточно.**

---

### Вариант 2 - Qwen2.5-VL 3B

Тоже хороший вариант.

Плюсы:

- очень неплохой OCR;
- меньше требований;
- зрелая модель.

Минусы:

- хуже новое понимание сцен.

Qwen2.5-VL также имеет компактные варианты, включая 3B. ([MedRxiv](https://www.medrxiv.org/content/10.64898/2026.03.26.26349455v2.full.pdf?utm_source=chatgpt.com))

---

### Вариант 3 - оставить Qwen3-VL 4B

Я бы оставил его как "эксперт".

То есть:

```
99% фото:

Qwen3-VL 2B

↓

сомнительные случаи:

Qwen3-VL 4B
```

---

# Я бы перестроил ваш пайплайн так

Сейчас:

```
257 фото

↓

Qwen3-VL 4B

↓

database
```

Это дорого.

Сделать:

```
257 фото

↓

DINOv2
(наш слепок)

↓

OCR быстрый

↓

Qwen3-VL 2B

↓

banner.db
```

---

## Например:

Qwen3-VL 2B создаёт:

```json
{
 "client":"Ozon",
 "category":[
   "еда",
   "магазин"
 ],
 "colors":[
   "pink",
   "white"
 ],
 "text":[
   "OZON fresh",
   "249 Р"
 ],
 "description":
 "Рекламный баннер магазина продуктов"
}
```

Для поиска этого достаточно.

---

## По железу

### RTX 4060 8GB

С Qwen3-VL 2B:

отлично.

Схема:

```
RTX4060 8GB

DINOv2
+
Qwen3-VL 2B
+
Ollama
```

будет комфортной.

---

### GTX1650 4GB

Тоже возможно:

```
Qwen3-VL 2B
CPU offload
```

но медленно.

---

### RTX3060 12GB

Идеально:

```
Qwen3-VL 4B
```

оставляем.

---

Мой вариант для вашего проекта:

```
Основная индексация:
Qwen3-VL 2B

Проверка спорных:
Qwen3-VL 4B

Поиск:
DINOv2 + SQLite + embeddings
```

То есть 4B не удаляем, а превращаем в "старшего эксперта".

Следующий логичный шаг - сделать два режима в вашем скрипте:

```bash
banner_ai_index.py --fast
```

→ Qwen3-VL 2B

и

```bash
banner_ai_index.py --quality
```

→ Qwen3-VL 4B

Тогда можно будет гонять ежедневные 300 фото быстро, а глубокий анализ делать только когда нужен.

---

**Sources:**

- [Qwen3-VL Technical Report](https://arxiv.org/abs/2511.21631?utm_source=chatgpt.com)
- [The copyright holder for this preprint](https://www.medrxiv.org/content/10.64898/2026.03.26.26349455v2.full.pdf?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-16 11:49:08

давай протестируем то же самое c Qwen2.5-VL 3B  Qwen3-VL 2B и сравним полноту описаний с текущим вариантом

---

### 🤖 **Assistant** — 2026-08-16 11:49:10

> **Searching the web**
>
>
> **Searching 10 websites**
>
> 
>
> Worked for a couple of seconds

Да, это как раз правильный эксперимент для вашего проекта. Я бы не менял архитектуру, а сделал **один и тот же тестовый набор** и сравнил три модели:

1. **Qwen3-VL 4B** - текущий эталон  
2. **Qwen3-VL 2B** - быстрый вариант  
3. **Qwen2.5-VL 3B** - возможный компромисс по OCR/описанию  

Qwen2.5-VL 3B и Qwen3-VL 2B как раз рассчитаны на более лёгкие deployment-сценарии. Qwen2.5-VL 3B хорошо ориентирован на распознавание текста, графики и структуры изображений, а Qwen3-VL 2B - более новая компактная модель с улучшенным визуальным пониманием. ([Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct?utm_source=chatgpt.com))

---

## Что будем сравнивать

Не просто "красивое описание", а то, что нужно вашей базе `banner.db`.

Для каждого баннера просим одинаковый JSON:

```json
{
 "client": "",
 "brand": "",
 "category": "",
 "text": [],
 "phone": "",
 "date": "",
 "colors": [],
 "objects": [],
 "description": "",
 "confidence": 0
}
```

---

## Тестовый набор

Я бы взял 10 разных случаев:

### Простые:

1. Ozon fresh
2. Бетсити
3. Сбер
4. политический баннер

### Сложные:

5. мелкий текст
6. плохой OCR
7. баннер под углом
8. часть баннера закрыта
9. фото с улицы
10. ночное фото

У вас уже есть хорошие кандидаты:

```
Ашхабадский_01.JPG
видео_сизякин.jpg
Добровольского17_01.JPG
Вавилова52_12.JPG
Стачки_41_03.JPG
```

---

## Какой результат ожидаю

Моя предварительная оценка:

### Qwen3-VL 4B

```
OCR:        95%
бренд:      95%
цвета:      95%
описание:   отлично
скорость:   медленно
```

---

### Qwen2.5-VL 3B

```
OCR:        90-95%
бренд:      90%
цвета:      90%
описание:   хорошо
скорость:   быстрее
```

У него сильная сторона - документы, текст, структура изображения. ([Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct?utm_source=chatgpt.com))

---

### Qwen3-VL 2B

```
OCR:        80-90%
бренд:      85-90%
цвета:      90%
описание:   хорошо
скорость:   самая высокая
```

Qwen3-VL 2B - именно облегчённая версия семейства Qwen3-VL. ([Hugging Face](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct?utm_source=chatgpt.com))

---

## Для вашей задачи возможен интересный результат

Я подозреваю, что победит не 4B.

Потому что у вас:

- баннеры одного типа;
- ограниченный словарь клиентов;
- много повторяющихся брендов;
- нужна индексация, а не философское описание.

Может получиться:

```
Qwen3-VL 2B
        |
        |
        +---- 90% баннеров

Qwen3-VL 4B
        |
        |
        +---- только сложные случаи
```

---

## Делаем правильно: один скрипт

Например:

```
scripts/banner_model_compare_v01.py
```

Запуск:

```bash
uv run python scripts/banner_model_compare_v01.py
```

Он:

1. берёт один файл:

```
Ашхабадский_01.JPG
```

2. гоняет:

```
qwen3-vl:4b-instruct

qwen3-vl:2b-instruct

qwen2.5-vl:3b-instruct
```

3. сохраняет:

```
output/model_compare/

Ашхабадский_01/

   qwen3_4b.json
   qwen3_2b.json
   qwen25_3b.json
```

---

Потом можно сделать автоматический рейтинг:

```
+1 клиент найден
+1 телефон найден
+1 дата найдена
+1 текст похож на OCR
+1 цвета определены
```

и получить:

```
Qwen3-VL 4B     94/100
Qwen2.5-VL 3B   91/100
Qwen3-VL 2B     86/100
```

---

Я бы сейчас сделал **готовый `banner_model_compare_v01.py` под ваш Ollama**, без изменения базы. Он будет работать с уже установленными моделями. После прогона 5-10 баннеров станет понятно, нужна ли вообще 4B.

---

**Sources:**

- [Qwen/Qwen2.5-VL-3B-Instruct · Hugging Face](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-16 11:50:56

надо чтоб эти модели просканировали папку test - хотя бы 50 файлов и сравнить описания с 4B

---

### 🤖 **Assistant** — 2026-08-16 11:50:58

Да, так будет правильнее. Не один баннер, а **реальный прогон по папке test**. Тогда мы увидим не "красивое описание", а пригодность модели для создания вашей базы `banner.db`.

Сделаем так:

```
data/input/test/
        |
        |
        +---- 50 JPG
              |
              |
              +---- Qwen3-VL 4B  (эталон)
              |
              +---- Qwen3-VL 2B
              |
              +---- Qwen2.5-VL 3B
              
              |
              v

output/model_compare/

    summary.csv

    Стачки_41_01/
        qwen3_vl_4b.json
        qwen3_vl_2b.json
        qwen25_vl_3b.json

    ...
```

---

Что сравним:

### 1. Клиент

Например:

```
Ozon
Сбер
Бетсити
```

---

### 2. OCR текст

Сравнение:

```
4B:
OZON fresh
249 ₽
КЛУБНИКА

2B:
OZON
249

3B:
OZON fresh
249 ₽ КЛУБНИКА
```

---

### 3. Атрибуты

```
colors:
pink, white

objects:
product package, person, logo

category:
food / bank / politics
```

---

### 4. Полнота

Сделаем итог:

```
FILE                  4B     3B     2B

Вавилова52_12.JPG     96%    93%    88%
Стачки_41_03.JPG      94%    91%    86%
Бетсити.JPG           98%    95%    90%

AVERAGE               96%    93%    88%
```

---

Я бы добавил ещё важный параметр:

## Скорость

Замеряем:

```
file
model
seconds
tokens
```

Потому что для вашего потока:

```
300 фото/день
```

разница критична.

Например:

```
Qwen3-VL 4B
7 секунд/фото

300 фото = 35 минут

Qwen3-VL 2B
3 секунды/фото

300 фото = 15 минут
```

---

Нужен будет один готовый файл:

```
scripts/banner_model_compare_v02.py
```

Он будет использовать ваш текущий Ollama API:

```
http://localhost:11434/api/chat
```

и модели:

```
qwen3-vl:4b-instruct
qwen3-vl:2b-instruct
qwen2.5-vl:3b
```

Перед запуском только проверим названия моделей:

```bash
ollama list
```

У вас сейчас есть:

```
qwen3-vl:4b-instruct
```

А для двух остальных надо увидеть точные ID.

После этого делаем прогон 50 файлов. По результату уже можно будет принять решение:

- оставить 4B;
- перейти на 2B;
- сделать гибрид:
  - 2B массово,
  - 4B только для сомнительных случаев.

Это как раз архитектура, которая лучше всего подходит под ваш рекламный отдел.

---

### 👤 **User** — 2026-08-16 11:51:30

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ollama list
NAME                    ID              SIZE      MODIFIED     
qwen3:1.7b              8f68893c685c    1.4 GB    39 hours ago    
qwen3:0.6b              7df6b6e09427    522 MB    39 hours ago    
qwen3-coder:latest      06c1097efce0    18 GB     6 days ago      
qwen3-vl:4b-instruct    ee4b975b58c1    3.3 GB    6 days ago      
qwq:32b                 009cb3f08d74    19 GB     6 days ago      
qwen3-32k:latest        b3e2287c81ab    5.2 GB    6 days ago      
bge-m3:latest           790764642607    1.2 GB    6 days ago      
qwen3:4b                359d7dd4bcda    2.5 GB    6 days ago      
qwen3:8b                500a1f067a9f    5.2 GB    6 days ago      
deepseek-r1:14b         c333b7232bdb    9.0 GB    4 weeks ago     
llama3.2-vision:11b     6f2f9757ae97    7.8 GB    4 weeks ago     
qwen2.5-coder:7b        dae161e27b0e    4.7 GB    4 weeks ago     
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 11:51:33

Отлично. Сейчас у вас есть только **эталонная модель**:

```text
qwen3-vl:4b-instruct
```

Для честного сравнения нужно добавить ещё две:

1. **Qwen3-VL 2B**
2. **Qwen2.5-VL 3B**

---

## 1. Сначала попробуем скачать Qwen3-VL 2B

```bash
ollama pull qwen3-vl:2b-instruct
```

Проверяем:

```bash
ollama list | grep vl
```

Должно появиться примерно:

```
qwen3-vl:2b-instruct
qwen3-vl:4b-instruct
```

---

## 2. Затем Qwen2.5-VL 3B

```bash
ollama pull qwen2.5-vl:3b
```

Проверяем:

```bash
ollama list | grep vl
```

Получится:

```
qwen2.5-vl:3b
qwen3-vl:2b-instruct
qwen3-vl:4b-instruct
```

---

После этого делаем скрипт сравнения.

Я бы сразу сделал его чуть умнее, не просто JSON.

Он будет сохранять:

```
data/banner_database/model_compare/

├── results.csv
├── scores.csv
│
├── qwen3-vl-4b/
│      Стачки_41_01.json
│
├── qwen3-vl-2b/
│      Стачки_41_01.json
│
└── qwen25-vl-3b/
       Стачки_41_01.json
```

---

Формат JSON будет одинаковый:

```json
{
 "client": "Ozon",
 "text": [
   "OZON fresh",
   "249 ₽"
 ],
 "category": "food",
 "colors": [
   "pink",
   "white"
 ],
 "objects": [
   "product",
   "logo"
 ],
 "description":
 "Рекламный баннер магазина продуктов"
}
```

---

И отдельно сделаем автоматическую оценку:

```
FILE                  4B      3B      2B

Озон_01.JPG            98      96      91
Бетсити.JPG            97      94      89
Сбер.JPG               96      93      88

AVERAGE                97      94      89
```

---

Ещё добавлю замер скорости:

```
MODEL                 TIME

qwen3-vl:4b           7.8 sec
qwen2.5-vl:3b         5.1 sec
qwen3-vl:2b           3.2 sec
```

Это важно, потому что у вас цель:

```
200-300 фото ежедневно
```

---

Сейчас следующий шаг:

запустите:

```bash
ollama pull qwen3-vl:2b-instruct
```

и пришлите вывод.

Если Ollama скажет, что такого имени нет — подберём правильный tag (у Qwen иногда названия отличаются). После этого дам готовый `banner_model_compare_v01.py`.

---

### 👤 **User** — 2026-08-16 11:52:57

ollama pull qwen2.5-vl:3b

---

### 🤖 **Assistant** — 2026-08-16 11:53:00

Да, запускайте:

```bash
ollama pull qwen2.5-vl:3b
```

После окончания проверьте:

```bash
ollama list | grep vl
```

Должно быть примерно:

```text
qwen3-vl:4b-instruct
qwen2.5-vl:3b
```

Потом попробуем найти правильное имя для Qwen3-VL 2B:

```bash
ollama search qwen3-vl
```

(если команда есть в вашей версии Ollama)

или:

```bash
ollama pull qwen3-vl:2b-instruct
```

Если выдаст ошибку `model not found` — подберём тег.

После установки двух моделей сделаем прогон:

```text
data/input/test
        |
        | 50 файлов

---

### 👤 **User** — 2026-08-16 11:53:07

ollama pull qwen2.5-vl:3b
pulling manifest 
Error: pull model manifest: file does not exist

---

### 🤖 **Assistant** — 2026-08-16 11:53:09

Значит в вашем репозитории Ollama нет модели с таким точным именем. У Qwen-VL в Ollama названия отличаются от HuggingFace.

Давайте найдём доступные варианты.

Сначала:

```bash
ollama search qwen2.5
```

Если команда не поддерживается, используем библиотеку Ollama:

```bash
ollama pull qwen2.5vl:3b
```

или:

```bash
ollama pull qwen2.5-vl:3b-instruct
```

Проверяем после каждого:

```bash
ollama list | grep qwen
```

---

Но есть ещё вариант: у вас уже есть очень интересная модель:

```text
llama3.2-vision:11b    7.8 GB
```

Её можно включить в тест тоже, как "тяжёлый эксперт":

Получится:

| Модель | Размер | Роль |
|-|-:|-|
| qwen3-vl:4b-instruct | 3.3 GB | текущий эталон |
| qwen3-vl:2b | ~1.5-2 GB | быстрый |
| llama3.2-vision:11b | 7.8 GB | максимум качества |

---

Для вашего проекта я бы обязательно сравнил:

```
qwen3-vl:4b-instruct
        |
        |
        +---- qwen3-vl:2b (найдём)
        |
        +---- llama3.2-vision:11b
```

Потому что у вас задача не просто OCR — нужно понять:

- "это Ozon"
- "это выборы"
- "это Бетсити"
- "это реклама еды"
- "это баннер политика"

И иногда большая vision-модель может дать лучшее описание.

---

Сейчас сделайте:

```bash
ollama search qwen
```

и пришлите вывод. Если такой команды нет — попробуем через:

```bash
ollama list
```

и я дам точное имя для pull.

---

### 👤 **User** — 2026-08-16 11:54:56

ollama search qwen2.5
Error: unknown command "search" for "ollama"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 11:54:59

Да, у вас версия Ollama без команды `search`. Тогда идём другим путём.

В Ollama имя модели должно точно совпадать с каталогом моделей. Для Qwen2.5-VL попробуйте варианты:

```bash
ollama pull qwen2.5vl:3b
```

если нет:

```bash
ollama pull qwen2.5-vl:3b-instruct
```

если нет:

```bash
ollama pull qwen2.5-vl:3b
```

---

Но я бы сначала проверил доступность через библиотеку Ollama:

Откройте браузер:

```
https://ollama.com/search
```

и найдите:

```
qwen2.5 vl
```

Там будет точное имя для `ollama pull`.

---

Ещё вариант — обновить Ollama (у вас, судя по отсутствию search, возможно старая версия):

Проверка:

```bash
ollama --version
```

---

Кстати, для нашего теста нам **не обязательно ждать Qwen2.5-VL**. У вас уже есть:

```
qwen3-vl:4b-instruct
llama3.2-vision:11b
```

Можно уже сделать первый сравнительный прогон:

```
50 файлов test

qwen3-vl:4b
vs
llama3.2-vision:11b
```

А потом добавить маленькую модель.

Я бы даже добавил `llama3.2-vision:11b`, потому что будет интересно: возможно она будет лучше понимать **контекст улицы и баннера**, а Qwen лучше читать текст.

Для вашей базы `banner.db` это важный тест.

---

### 👤 **User** — 2026-08-16 11:57:44

давай скрипт для 3 моделей, а потом сравнение 4х

---

### 🤖 **Assistant** — 2026-08-16 11:57:46

Да, делаем правильно: сначала прогоняем **три модели**, которые доступны/будут доступны, сохраняем "сырые" описания, потом отдельным скриптом сравниваем 4 модели.

Сейчас у нас точно есть:

```
qwen3-vl:4b-instruct
llama3.2-vision:11b
```

Третью добавим как переменную (после установки):

```
qwen3-vl:2b-instruct
```

---

Создаём файл:

```bash
nano scripts/banner_model_compare_v01.py
```

Вставляем:

```python
#!/usr/bin/env python3

import requests
import base64
import json
import time
from pathlib import Path
from tqdm import tqdm

# ==============================
# SETTINGS
# ==============================

INPUT_DIR = Path("data/input/test")

OUTPUT_DIR = Path(
    "data/banner_database/model_compare"
)

MODELS = [
    "qwen3-vl:4b-instruct",
    "qwen3-vl:2b-instruct",
    "llama3.2-vision:11b",
]

OLLAMA_URL = "http://localhost:11434/api/chat"

LIMIT = 50

PROMPT = """
Ты анализируешь рекламный баннер.

Верни строго JSON:

{
"client":"",
"brand":"",
"category":"",
"text":[],
"colors":[],
"objects":[],
"description":"",
"confidence":0
}

Нужно определить:
- компанию или клиента
- весь читаемый текст
- цвета
- объекты на изображении
- краткое описание баннера

Если не уверен, пиши пустое значение.
"""

# ==============================

def image_to_base64(path):

    with open(path, "rb") as f:
        return base64.b64encode(
            f.read()
        ).decode()

def ask_model(model, image):

    payload = {

        "model": model,

        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": PROMPT
                    },
                    {
                        "type": "image",
                        "image": image
                    }
                ]
            }
        ],

        "stream": False,

        "format": "json"

    }

start = time.time()

    r = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=600
    )

    sec = time.time()-start

    r.raise_for_status()

    data = r.json()

    answer = data["message"]["content"]

    try:
        answer = json.loads(answer)

    except:
        answer = {
            "raw": answer
        }

answer["_time_sec"] = round(sec,2)
    answer["_model"] = model

return answer

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

files = sorted(
        list(INPUT_DIR.glob("*.JPG")) +
        list(INPUT_DIR.glob("*.jpg")) +
        list(INPUT_DIR.glob("*.png"))
    )[:LIMIT]

print("="*60)
    print("BANNER MODEL COMPARE")
    print("="*60)

    print("FILES:",len(files))

for img in tqdm(files):

        b64 = image_to_base64(img)

out_dir = OUTPUT_DIR / img.stem
        out_dir.mkdir(
            exist_ok=True
        )

for model in MODELS:

            print(
                "\n",
                img.name,
                model
            )

try:

                result = ask_model(
                    model,
                    b64
                )

name = (
                    model
                    .replace(":","_")
                    .replace("/","_")
                    + ".json"
                )

with open(
                    out_dir/name,
                    "w",
                    encoding="utf-8"
                ) as f:

                    json.dump(
                        result,
                        f,
                        ensure_ascii=False,
                        indent=2
                    )

except Exception as e:

                print(
                    "ERROR",
                    model,
                    e
                )

print()
    print("DONE")
    print(OUTPUT_DIR)

if __name__=="__main__":
    main()
```

---

Запуск:

```bash
uv run python scripts/banner_model_compare_v01.py
```

---

После окончания структура будет:

```
data/banner_database/model_compare/

Стачки_41_01/

 qwen3-vl_4b-instruct.json
 qwen3-vl_2b-instruct.json
 llama3.2-vision_11b.json

Ozon_01/

 ...
```

---

Потом второй этап:

```
compare_models_v01.py
```

Он сделает:

```
FILE                  4B    2B    LLAMA11B

Стачки_41_01          96    91    94
Ozon_01               98    95    96

AVERAGE               97    93    95
```

И отдельно:

```
Среднее время:

4B       6.4 сек
2B       3.1 сек
11B     14.7 сек
```

---

После этого уже можно принимать архитектурное решение:

- ежедневная обработка → маленькая модель;
- сомнительные баннеры → 4B;
- сложные случаи → 11B.

Это как раз хорошо ложится на вашу идею "AI-архив рекламных конструкций".

---

### 👤 **User** — 2026-08-16 12:00:53

Зорге_06.JPG qwen3-vl:2b-instruct
ERROR qwen3-vl:2b-instruct 400 Client Error: Bad Request for url: http://localhost:11434/api/chat

 Зорге_06.JPG llama3.2-vision:11b
ERROR llama3.2-vision:11b 400 Client Error: Bad Request for url: http://localhost:11434/api/chat
100%|██████████████████████████████████████████| 50/50 [00:10<00:00,  4.62it/s]

DONE
data/banner_database/model_compare

---

### 🤖 **Assistant** — 2026-08-16 12:00:56

Хорошо, тест отработал, но причина ошибки понятна: **скрипт неправильно отправляет vision-запрос для Ollama**.

`qwen3-vl:4b-instruct` у вас прошёл, потому что, скорее всего, он терпимее к формату. А вот:

```
qwen3-vl:2b-instruct
llama3.2-vision:11b
```

вернули:

```
400 Bad Request
```

То есть Ollama получил неправильный JSON.

---

У Ollama Vision API правильный формат другой:

```json
{
  "model": "llama3.2-vision:11b",
  "messages": [
    {
      "role": "user",
      "content": "Опиши изображение",
      "images": [
        "base64..."
      ]
    }
  ],
  "stream": false
}
```

А у нас сейчас:

```json
"content":[
 {
  "type":"text"
 },
 {
  "type":"image"
 }
]
```

Это формат некоторых OpenAI-compatible API, но не Ollama.

---

Исправляем функцию `ask_model`.

Открой:

```bash
nano scripts/banner_model_compare_v01.py
```

Найди:

```python
payload = {
```

и замени всю функцию `ask_model` на эту:

```python
def ask_model(model, image):

    payload = {

        "model": model,

        "messages": [
            {
                "role": "user",
                "content": PROMPT,
                "images": [
                    image
                ]
            }
        ],

        "stream": False,

        "format": "json"

    }

start = time.time()

    r = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=600
    )

    sec = time.time()-start

if r.status_code != 200:
        print(r.text)
        r.raise_for_status()

data = r.json()

    answer = data["message"]["content"]

try:
        answer=json.loads(answer)

    except:
        answer={
            "raw":answer
        }

answer["_time_sec"]=round(sec,2)
    answer["_model"]=model

return answer
```

---

Теперь ещё важный момент.

Проверьте, существуют ли модели:

```bash
ollama list
```

Потому что:

```
qwen3-vl:2b-instruct
```

у вас ещё не было в списке.

Если её нет, будет другая ошибка.

---

Для проверки руками:

### Qwen 2B:

```bash
ollama run qwen3-vl:2b-instruct
```

### Llama Vision:

```bash
ollama run llama3.2-vision:11b
```

Если модель есть — запустится.

---

После исправления повторяем:

```bash
uv run python scripts/banner_model_compare_v01.py
```

Но я бы ещё изменил скрипт:

сейчас он тихо пишет ошибки и идёт дальше.

Добавим в следующий вариант:

```
MODEL STATUS

qwen3-vl:4b-instruct     OK
qwen3-vl:2b-instruct     NOT FOUND
llama3.2-vision:11b      OK
```

чтобы сразу было видно, что загрузилось.

Сейчас у нас уже есть интересный результат: **4B обработала 50 файлов за 10 секунд?** Это подозрительно быстро — похоже, первые два файла были единственными реальными запросами, а остальные падали. После исправления получим настоящий замер.

---

### 👤 **User** — 2026-08-16 12:01:19

давай готовый файл

---

### 🤖 **Assistant** — 2026-08-16 12:01:21

Сделаем сразу исправленный вариант **v02**.

Создайте файл:

```bash
nano scripts/banner_model_compare_v02.py
```

Вставьте полностью:

```python
#!/usr/bin/env python3

import requests
import base64
import json
import time
from pathlib import Path
from tqdm import tqdm

# =========================
# SETTINGS
# =========================

INPUT_DIR = Path("data/input/test")

OUTPUT_DIR = Path(
    "data/banner_database/model_compare_v02"
)

MODELS = [
    "qwen3-vl:4b-instruct",
    "qwen3-vl:2b-instruct",
    "llama3.2-vision:11b",
]

OLLAMA_URL = "http://localhost:11434/api/chat"

LIMIT = 50

PROMPT = """
Ты анализируешь рекламную фотографию.

Верни только JSON:

{
 "client":"",
 "brand":"",
 "category":"",
 "text":[],
 "colors":[],
 "objects":[],
 "description":"",
 "confidence":0
}

Определи:

- клиента или бренд
- весь читаемый текст
- цвета баннера
- объекты
- категорию рекламы
- подробное описание сцены

Если информации нет, оставь пустое поле.
"""

# =========================

def image_to_base64(path):

    with open(path, "rb") as f:
        return base64.b64encode(
            f.read()
        ).decode("utf-8")

def ask_model(model, image64):

    payload = {

        "model": model,

        "messages": [
            {
                "role": "user",
                "content": PROMPT,
                "images": [
                    image64
                ]
            }
        ],

        "stream": False,

        "format": "json"

    }

start = time.time()

    r = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=900
    )

elapsed = time.time() - start

if r.status_code != 200:

        print()
        print("MODEL ERROR:", model)
        print(r.text)

        raise RuntimeError(
            r.text
        )

data = r.json()

    text = data["message"]["content"]

try:
        result = json.loads(text)

    except:

        result = {
            "raw_answer": text
        }

result["_model"] = model
    result["_time_sec"] = round(
        elapsed,
        2
    )

return result

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

files = sorted(
        list(INPUT_DIR.glob("*.JPG"))
        +
        list(INPUT_DIR.glob("*.jpg"))
        +
        list(INPUT_DIR.glob("*.png"))
    )

files = files[:LIMIT]

print("="*70)
    print("BANNER MODEL COMPARE v02")
    print("="*70)

    print("FILES:", len(files))
    print("MODELS:")

    for m in MODELS:
        print(" -",m)

    print()

summary = []

for img in tqdm(files):

        image64 = image_to_base64(img)

folder = OUTPUT_DIR / img.stem

        folder.mkdir(
            exist_ok=True
        )

for model in MODELS:

            print()
            print(
                img.name,
                "=>",
                model
            )

try:

                result = ask_model(
                    model,
                    image64
                )

filename = (
                    model
                    .replace(":","_")
                    .replace("/","_")
                    +
                    ".json"
                )

with open(
                    folder / filename,
                    "w",
                    encoding="utf-8"
                ) as f:

                    json.dump(
                        result,
                        f,
                        ensure_ascii=False,
                        indent=2
                    )

summary.append(
                    {
                        "file":img.name,
                        "model":model,
                        "time":result.get(
                            "_time_sec"
                        ),
                        "client":result.get(
                            "client",""
                        ),
                        "text":str(
                            result.get(
                                "text",""
                            )
                        )
                    }
                )

except Exception as e:

                print(
                    "FAILED:",
                    model,
                    e
                )

                summary.append(
                    {
                        "file":img.name,
                        "model":model,
                        "ERROR":str(e)
                    }
                )

with open(
        OUTPUT_DIR/"summary.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2
        )

print()
    print("="*70)
    print("DONE")
    print(OUTPUT_DIR)

if __name__ == "__main__":
    main()
```

---

Запуск:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/banner_model_compare_v02.py
```

---

После запуска должно быть примерно:

```
BANNER MODEL COMPARE v02
======================================================================

FILES: 50

Зорге_06.JPG => qwen3-vl:4b-instruct
Зорге_06.JPG => qwen3-vl:2b-instruct
Зорге_06.JPG => llama3.2-vision:11b
```

Результат:

```
data/banner_database/model_compare_v02/

summary.json

Зорге_06/
    qwen3-vl_4b-instruct.json
    qwen3-vl_2b-instruct.json
    llama3.2-vision_11b.json
```

После этого будем делать второй файл:

```
compare_models_v01.py
```

который автоматически сравнит:

- кто нашёл клиента;
- кто прочитал больше текста;
- кто лучше определил категорию;
- скорость обработки.

И тогда уже будет видно, стоит ли оставлять 4B или переходить на меньшую модель.

---

### 👤 **User** — 2026-08-16 12:02:53

BANNER MODEL COMPARE v02
======================================================================
FILES: 50
MODELS:
 - qwen3-vl:4b-instruct
 - qwen3-vl:2b-instruct
 - llama3.2-vision:11b

  0%|                                                   | 0/50 [00:00<?, ?it/s]
Screenshot from 2026-08-16 00-38-11.png => qwen3-vl:4b-instruct

Screenshot from 2026-08-16 00-38-11.png => qwen3-vl:2b-instruct

Screenshot from 2026-08-16 00-38-11.png => llama3.2-vision:11b

MODEL ERROR: llama3.2-vision:11b
{"error":"llama-server process has terminated: exit status 1: error loading model: unknown model architecture: 'mllama'\nerror loading model: unknown model architecture: 'mllama'"}
FAILED: llama3.2-vision:11b {"error":"llama-server process has terminated: exit status 1: error loading model: unknown model architecture: 'mllama'\nerror loading model: unknown model architecture: 'mllama'"}
  2%|▊                                          | 1/50 [00:15<12:33, 15.38s/it]
Ашхабадский_01.JPG => qwen3-vl:4b-instruct

MODEL ERROR: qwen3-vl:4b-instruct
{"error":"{\"error\":{\"code\":400,\"message\":\"request (4131 tokens) exceeds the available context size (4096 tokens), try increasing it\",\"type\":\"exceed_context_size_error\",\"n_prompt_tokens\":4131,\"n_ctx\":4096}}"}
FAILED: qwen3-vl:4b-instruct {"error":"{\"error\":{\"code\":400,\"message\":\"request (4131 tokens) exceeds the available context size (4096 tokens), try increasing it\",\"type\":\"exceed_context_size_error\",\"n_prompt_tokens\":4131,\"n_ctx\":4096}}"}

Ашхабадский_01.JPG => qwen3-vl:2b-instruct

MODEL ERROR: qwen3-vl:2b-instruct
{"error":"{\"error\":{\"code\":400,\"message\":\"request (4131 tokens) exceeds the available context size (4096 tokens), try increasing it\",\"type\":\"exceed_context_size_error\",\"n_prompt_tokens\":4131,\"n_ctx\":4096}}"}
FAILED: qwen3-vl:2b-instruct {"error":"{\"error\":{\"code\":400,\"message\":\"request (4131 tokens) exceeds the available context size (4096 tokens), try increasing it\",\"type\":\"exceed_context_size_error\",\"n_prompt_tokens\":4131,\"n_ctx\":4096}}"}

Ашхабадский_01.JPG => llama3.2-vision:11b

MODEL ERROR: llama3.2-vision:11b
{"error":"llama-server process has terminated: exit status 1: error loading model: unknown model architecture: 'mllama'\nerror loading model: unknown model architecture: 'mllama'"}
FAILED: llama3.2-vision:11b {"error":"llama-server process has terminated: exit status 1: error loading model: unknown model architecture: 'mllama'\nerror loading model: unknown model architecture: 'mllama'"}
  4%|█▋                                         | 2/50 [00:23<08:46, 10.97s/it]
Ашхабадский_02.JPG => qwen3-vl:4b-instruct
  4%|█▋                                         | 2/50 [00:25<10:03, 12.58s/it]
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/banner_model_compare_v02.py", line 291, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/banner_model_compare_v02.py", line 204, in main
    result = ask_model(
             ^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/banner_model_compare_v02.py", line 97, in ask_model
    r = requests.post(
        ^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/requests/api.py", line 134, in post
    return request("post", url, data=data, json=json, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/requests/api.py", line 71, in request
    return session.request(method=method, url=url, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/requests/sessions.py", line 651, in request
    resp = self.send(prep, **send_kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/requests/sessions.py", line 784, in send
    r = adapter.send(request, **kwargs)
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/requests/adapters.py", line 696, in send
    resp = conn.urlopen(
           ^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/urllib3/connectionpool.py", line 788, in urlopen
    response = self._make_request(
               ^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/urllib3/connectionpool.py", line 534, in _make_request
    response = conn.getresponse()
               ^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/urllib3/connection.py", line 571, in getresponse
    httplib_response = super().getresponse()
                       ^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/http/client.py", line 1457, in getresponse
    response.begin()
  File "/usr/lib/python3.12/http/client.py", line 336, in begin
    version, status, reason = self._read_status()
                              ^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/http/client.py", line 297, in _read_status
    line = str(self.fp.readline(_MAXLINE + 1), "iso-8859-1")
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/socket.py", line 707, in readinto
    return self._sock.recv_into(b)
           ^^^^^^^^^^^^^^^^^^^^^^^
KeyboardInterrupt
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 12:02:55

Отлично, теперь видно реальные проблемы. Исправляем сразу три момента.

## 1. `llama3.2-vision:11b` не запускается

Ошибка:

```
unknown model architecture: 'mllama'
```

Это не проблема скрипта. Ваша текущая версия Ollama/llama.cpp не поддерживает эту архитектуру.

Проверка:

```bash
ollama --version
```

Скорее всего нужна свежая Ollama.

Обновление:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Потом:

```bash
ollama serve
```

в новом терминале:

```bash
ollama run llama3.2-vision:11b
```

Если заработает — включим обратно.

---

## 2. Главная проблема — context 4096

Ошибка:

```
request (4131 tokens) exceeds the available context size (4096 tokens)
```

Это из-за больших фотографий.

Vision-модели считают картинку как много токенов.

Нужно добавить:

```json
"options": {
    "num_ctx": 16384
}
```

в запрос Ollama.

---

## 3. Сделаем v03 устойчивый

Что поменяем:

### Было:

```python
"stream": False,
"format": "json"
```

Добавляем:

```python
"options": {
    "num_ctx": 16384,
    "temperature":0
}
```

---

### Ещё уменьшим картинку перед отправкой

Сейчас:

```
3500x2500
```

Для LLM это слишком много.

Делаем:

```
1600px по длинной стороне
```

Качество текста почти не потеряем, а скорость увеличится.

---

Создаём:

```bash
nano scripts/banner_model_compare_v03.py
```

Из v02 меняем:

### Добавляем импорт:

```python
from PIL import Image
from io import BytesIO
```

---

Заменяем:

```python
def image_to_base64(path):

    with open(path,"rb") as f:
        return base64.b64encode(
            f.read()
        ).decode()
```

на:

```python
def image_to_base64(path):

    img = Image.open(path)

    img.thumbnail(
        (1600,1600)
    )

    buf = BytesIO()

    img.convert("RGB").save(
        buf,
        format="JPEG",
        quality=90
    )

    return base64.b64encode(
        buf.getvalue()
    ).decode()
```

---

В `payload` добавляем:

```python
"options": {
    "num_ctx":16384,
    "temperature":0
},
```

получится:

```python
payload={

"model":model,

"messages":[
{
"role":"user",
"content":PROMPT,
"images":[image64]
}
],

"stream":False,

"format":"json",

"options":{
    "num_ctx":16384,
    "temperature":0
}

}
```

---

## Модели пока оставляем так:

```python
MODELS=[
"qwen3-vl:4b-instruct",
"qwen3-vl:2b-instruct"
]
```

Llama пока убираем.

---

После исправления запуск:

```bash
uv run python scripts/banner_model_compare_v03.py
```

Ожидаю результат примерно:

```
Screenshot... qwen3-vl:4b  4-7 сек
Screenshot... qwen3-vl:2b  2-4 сек

Ашхабадский_01.JPG OK
```

---

Кстати, важный момент: у вас уже есть подтверждение, что **Qwen3-VL 2B реально установлен и отвечает** — он дошёл до запроса и упал только на context. Значит сравнение 4B vs 2B получится.

После этого сделаем `compare_report_v01.py` и он сравнит качество описаний в `model_compare_v03`.

---

### 👤 **User** — 2026-08-16 12:06:56

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ollama run llama3.2-vision:11b
Error: 500 Internal Server Error: llama-server process has terminated: exit status 1: error loading model: unknown model architecture: 'mllama'
error loading model: unknown model architecture: 'mllama'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 12:06:58

Да, подтверждено: проблема **не в скрипте**, а в связке **Ollama ↔ llama3.2-vision:11b**.

Ошибка:

```
unknown model architecture: 'mllama'
```

означает, что ваш текущий Ollama содержит старый `llama.cpp`, который не умеет загружать архитектуру Meta Llama Vision (`mllama`).

Проверяем версию:

```bash
ollama --version
```

Скорее всего там что-то старое.

---

## Обновляем Ollama

Выполните:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

После установки:

```bash
ollama --version
```

Должно быть что-то новое (0.10+).

---

Потом перезапускаем сервер:

Если Ollama запущен как сервис:

```bash
sudo systemctl restart ollama
```

Проверяем:

```bash
systemctl status ollama
```

---

Теперь пробуем:

```bash
ollama run llama3.2-vision:11b
```

---

Если заработает, возвращаем её в тест:

```python
MODELS=[
    "qwen3-vl:4b-instruct",
    "qwen3-vl:2b-instruct",
    "llama3.2-vision:11b"
]
```

---

Но есть ещё один момент: ваша RTX 3060 12GB.

По памяти:

| Модель | VRAM | Скорость |
|-|-:|-:|
| Qwen3-VL 2B | ~3-4 GB | быстро |
| Qwen3-VL 4B | ~6-8 GB | нормально |
| Llama3.2-Vision 11B | ~9-11 GB | медленно |

Она должна поместиться, но будет близко к пределу.

---

Я бы после обновления сделал ещё один тест:

```bash
ollama show llama3.2-vision:11b
```

и посмотрел:

```
architecture
parameters
quantization
```

---

Кстати, текущий эксперимент уже показал важную вещь:

Для вашего сценария **"ежедневный фотоотчёт 200-300 фото → описание → база"** скорее всего победит не самая большая модель, а связка:

```
DINOv2
 |
 |-- быстрый поиск адреса
 |
Qwen3-VL 2B/4B
 |
SQLite banner.db
 |
текстовый поиск + похожесть
```

А 11B можно оставить как "экспертную кнопку" для спорных случаев.

---

### 👤 **User** — 2026-08-16 12:07:19

ollama version is 0.32.13

---

### 🤖 **Assistant** — 2026-08-16 12:07:19

Тогда причина **точно не в старой версии Ollama**. `0.32.13` — достаточно новая версия.

Ошибка:

```text
unknown model architecture: 'mllama'
```

говорит о проблеме именно при загрузке конкретной модели `llama3.2-vision:11b` через встроенный `llama-server`.

Сначала посмотрим, что именно Ollama видит в модели:

```bash
ollama show llama3.2-vision:11b
```

и:

```bash
ollama show --modelfile llama3.2-vision:11b | head -80
```

Также очень полезно:

```bash
ollama ps
```

### Но я бы пока не тратил время на Llama

Для нашего эксперимента уже есть две рабочие модели:

```text
qwen3-vl:4b-instruct
qwen3-vl:2b-instruct
```

А задача сейчас — выяснить, **может ли 2B заменить 4B**.

Главная ошибка второго запуска была вообще не модельная:

```text
4131 tokens > 4096
```

Поэтому сначала исправляем `num_ctx` и уменьшаем фотографии до ~1600 px. После этого прогоняем **50 одинаковых фотографий на 2B и 4B**.

А `llama3.2-vision:11b` можно разобраться отдельно.

И ещё важное: поскольку `qwen3-vl:2b-instruct` у вас отвечает на запросы, **его устанавливать заново не нужно** — он уже работает.

---

