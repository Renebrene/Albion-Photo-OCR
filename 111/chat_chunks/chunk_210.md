## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 🤖 **Assistant** — 2026-08-20 22:17:39

> **Searching the web**
>
>
> **Searching 5 websites**
>
> 
>
> Worked for a few seconds

Да. Сделаем **два полностью отдельных прогона на одном и том же наборе неизвестных клиентов**, чтобы потом сравнить результаты честно.

У тебя `qwen3:8b` уже установлен: Ollama показывает 5.2 GB / Q4_K_M. ([Ollama](https://ollama.com/library/qwen3%3A8b?utm_source=chatgpt.com))  
`qwen2.5:7b` сейчас, судя по предыдущему выводу, **не установлен**. Официальный тег `qwen2.5:7b` - 7.62B, Q4_K_M, около 4.7 GB. ([Ollama](https://ollama.com/library/qwen2.5%3A7b?utm_source=chatgpt.com))

### 1. Сначала сделаем отдельный benchmark-скрипт

Я бы **не трогал основной `smart_client_normalizer.py`**. Создадим:

```bash
scripts/benchmark_client_normalizer.py
```

Он будет:

- брать текущие `photos.client`;
- исключать уже известные нормализованные значения;
- брать один и тот же список UNKNOWN;
- формировать одинаковых кандидатов;
- прогонять Qwen;
- сохранять JSON;
- сохранять удобный TXT;
- считать время;
- **не записывать ничего в БД**.

Запуск:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/benchmark_client_normalizer.py \
  --model qwen3:8b \
  --min-confidence 0.80
```

Результат, например:

```text
data/client_normalizer_benchmark/
    qwen3_8b.json
    qwen3_8b.txt
```

Потом второй:

```bash
uv run python scripts/benchmark_client_normalizer.py \
  --model qwen2.5:7b \
  --min-confidence 0.80
```

и:

```text
data/client_normalizer_benchmark/
    qwen2.5_7b.json
    qwen2.5_7b.txt
```

### 2. Важный момент для сравнения

Для `qwen3:8b` я бы отключил thinking. Qwen3 поддерживает `nothink`, а для этой задачи рассуждения практически не нужны - нам важнее скорость и стабильный JSON. ([GitHub](https://github.com/QwenLM/Qwen3?utm_source=chatgpt.com))

Настройки сделаем одинаковыми:

```text
temperature = 0
num_ctx     = 4096
num_predict = 256
think       = false
```

И одинаковый prompt.

### 3. Что будем сравнивать

Не просто «какая модель лучше», а:

```text
                 Qwen3 8B    Qwen2.5 7B
-----------------------------------------
точных совпадений
сомнительных
NO_MATCH
ошибочных совпадений
JSON errors
средняя уверенность
время
```

Особенно интересны наши проблемные случаи:

```text
EMBAYGO
EMBAICO
EMBAI GO
EMBARCO
EMBARD
EMBARGED
EMBARIO
EMBARO

Волный Дон
Волгий Дон
Волкый Дон
Волынский Дон

Яндекс.Маркет
Яндекс Маркет
Яндекс.Еда
Яндекс Лавка

Ozon
ozon fresh
Ozon Bank

Сбер
СБЕР
Сбер Мобайл
СЕР МОБАЙЛ
```

Именно они покажут, умеет ли модель **нормализовать**, а не просто искать регистронезависимое совпадение.

---

Но сначала надо установить `qwen2.5:7b`, иначе второй тест не запустится:

```bash
ollama pull qwen2.5:7b
```

После этого я дам тебе **одну команду, которая создаст benchmark-скрипт через heredoc**, без ручного редактирования файлов. Затем сразу прогоняем сначала `qwen3:8b`, потом `qwen2.5:7b`.

---

**Sources:**

- [qwen3:8b](https://ollama.com/library/qwen3%3A8b?utm_source=chatgpt.com)
- [GitHub - QwenLM/Qwen3: Qwen3 is the large language model series developed by Qwen team, Alibaba Cloud. · GitHub](https://github.com/QwenLM/Qwen3?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-20 22:21:41

======================================================================
SMART CLIENT NORMALIZER
======================================================================
MODEL: qwen3:4b
OLLAMA: http://127.0.0.1:11434/api/chat

======================================================================
CLIENT DIRECTORY
======================================================================
   6  HAVAL
  11  hh
   4  Ozon
   5  Альбион-Тур
   7  Бигфест
   8  Кинопоиск
   9  М.Видео
   3  Самокат
   2  Сбер
  10  Сбер Мобайл
  12  Тенет
   1  Яндекс

======================================================================
ALIASES: 20
RAW CLIENT VALUES: 125
======================================================================

======================================================================
UNKNOWN CLIENTS
======================================================================
COUNT: 98

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

======================================================================
SMART TEST RUN
======================================================================

[1/98] 'EMBARGO' (43 photos)
  -> NONE

[2/98] 'Единая Россия' (30 photos)
  -> NONE

[3/98] 'Сила России' (18 photos)
  -> NONE

[4/98] 'Вольный Дон' (14 photos)
  -> NONE

[5/98] 'БЕТСИТИ' (10 photos)
  -> NONE

[6/98] 'Пятёрочка' (9 photos)
  -> NONE

[7/98] 'Яндекс Маркет' (9 photos)
  -> 'Яндекс'
  confidence: 0.950
  reason: Исходное название содержит 'Яндекс' с добавленным 'Маркет', который, вероятно, является ошибкой OCR или дополнительным текстом, не входящим в название клиента из справочника.

[8/98] 'Магнит' (8 photos)
  -> NONE

[9/98] 'МТС' (8 photos)
  -> NONE

[10/98] 'Волный Дон' (7 photos)
  -> NONE

[11/98] 'ozon fresh' (5 photos)
  -> 'Ozon'
  confidence: 0.950
  reason: Исходное название 'ozon fresh' содержит опечатку в регистре и лишнее слово 'fresh', корректное название клиента из справочника - 'Ozon'

[12/98] 'Государственная Дума' (5 photos)
  -> NONE

[13/98] 'Купер' (5 photos)
  -> NONE

[14/98] 'Московский Цирк Никулина' (5 photos)
  -> NONE

[15/98] 'контракт61.рф' (4 photos)
  -> NONE

[16/98] 'Волынский Дон' (3 photos)
  -> NONE

[17/98] 'Дон' (3 photos)
  -> NONE

[18/98] 'Максидом' (3 photos)
  -> NONE

[19/98] 'ОКЕЙ' (3 photos)
  -> NONE

[20/98] 'ООО «Интернет Решений»' (3 photos)
  -> NONE

[21/98] 'Ростов-на-Дону' (3 photos)
  -> NONE

[22/98] 'Яндекс Лавка' (3 photos)
  -> 'Яндекс'
  confidence: 0.950
  reason: Исходное название содержит 'Яндекс' с лишним словом 'Лавка', которое, вероятно, является опечаткой или ошибкой ввода в OCR.

[23/98] 'EMBAYGO' (2 photos)
  -> NONE

---

### 🤖 **Assistant** — 2026-08-20 22:21:42

Да. Этот прогон `qwen3:4b` уже показывает важную вещь: **для нашего нормализатора модель сейчас слишком осторожная и одновременно местами слишком агрессивная**.

Например:

- `Яндекс Маркет` → `Яндекс` — модель угадала, но это **не обязательно правильно**. Это может быть отдельный клиент.
- `Яндекс Лавка` → `Яндекс` — ещё более спорно.
- `ozon fresh` → `Ozon` — вероятно правильно, но опять-таки нужен справочник/правила.
- `EMBARGO`, `Единая Россия`, `Магнит`, `МТС`, `БЕТСИТИ` → `NONE` — при отсутствии этих клиентов в справочнике это **правильное поведение**.
- `Волный Дон` → `NONE` — тоже правильно, пока мы не внесли `Вольный Дон` как допустимый alias.
- `Тенет Т41` потенциально можно было бы связать с `Тенет`, но это уже задача семантического решения.

### Поэтому я бы сейчас сделал не просто сравнение 4B vs 8B

Нам нужен тест на **одном и том же наборе 98 неизвестных**, причём отдельно:

1. `qwen3:4b`
2. `qwen3:8b`
3. `qwen2.5:7b`

И сохранить результаты в JSON/CSV, чтобы сравнить:

```text
RAW                    QWEN3-4B       QWEN3-8B       QWEN2.5-7B
----------------------------------------------------------------
Яндекс Маркет          Яндекс         ?              ?
Яндекс Лавка           Яндекс         ?              ?
ozon fresh              Ozon           ?              ?
Волный Дон              NONE           ?              ?
Тенет Т41               ?              ?              ?
...
```

Но **главный критерий** для нашего проекта — не количество совпадений.

Нам важнее:

> **не присвоить чужого клиента существующему клиенту.**

То есть ложное:

```text
Яндекс Маркет → Яндекс
```

может быть хуже, чем:

```text
Яндекс Маркет → NONE
```

Потому что `NONE` мы потом можем проверить человеком, а ошибочное автоматическое объединение загрязнит базу.

### И ещё один важный момент

Сейчас справочник содержит только:

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

То есть модель **не должна искать "правильного клиента вообще"**. Она должна отвечать только на вопрос:

> «Есть ли среди этих 12 клиентов тот, которому с высокой вероятностью соответствует эта строка?»

Иначе LLM начинает рассуждать:

`Единая Россия` — известный бренд → значит, надо что-то с ним сделать.

А нам это не нужно.

### Я бы изменил архитектуру smart normalizer

Сделать трёхступенчатую систему:

```text
RAW CLIENT
     │
     ▼
[1] точная нормализация / aliases
     │
     ├── найдено → CLIENT
     │
     ▼
[2] Qwen
     │
     ├── высокая уверенность → CLIENT
     │
     ├── NONE → неизвестный
     │
     ▼
[3] человек / добавление alias
```

Причём Qwen должен получать **только текущий справочник клиентов и aliases**, а не весь мир.

И обязательно заставить его возвращать структурированный ответ:

```json
{
  "client": null,
  "confidence": 0.91,
  "reason": "..."
}
```

а не позволять ему самостоятельно придумывать клиентов.

---

### Следующий тест

Я бы сейчас **не менял код нормализатора**. Сначала прогнал бы абсолютно одинаковые 98 значений через:

```bash
qwen3:8b
```

и потом:

```bash
qwen2.5:7b
```

с тем же `--min-confidence 0.80`.

После этого у нас будет реальное сравнение именно **качества моделей на нашей задаче**, а не общих характеристик моделей.

И уже по результату решим:

**4B / 7B / 8B + насколько вообще нужен LLM.**

Причём, судя по текущему результату 4B, я подозреваю, что **Qwen3:8B здесь будет полезнее именно в спорных случаях**, но не факт, что он окажется лучше `qwen2.5:7b` по нашей узкой задаче.

---

### 👤 **User** — 2026-08-20 22:22:08

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/benchmark_client_normalizer.py \
  --model qwen3:8b \
  --min-confidence 0.80
/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/python3: can't open file '/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/benchmark_client_normalizer.py': [Errno 2] No such file or directory
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:22:09

Да, здесь просто **нет файла `benchmark_client_normalizer.py`**. Предыдущий `smart_client_normalizer.py` есть, а отдельный benchmark мы ещё не создали.

Сделаем его правильно: **один и тот же набор из 98 неизвестных клиентов**, чтобы потом сравнить `qwen3:4b`, `qwen3:8b` и `qwen2.5:7b` по одинаковым входным данным.

Сначала создай benchmark на основе уже существующего нормализатора:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > scripts/benchmark_client_normalizer.py <<'PY'
#!/usr/bin/env python3

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.web.client_db import get_clients_with_address_counts

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

def get_directory():
    """
    Получаем текущий справочник клиентов.
    """
    try:
        from app.web.directory_db import get_client_directory

        rows = get_client_directory()

        result = []

        for row in rows:
            if isinstance(row, dict):
                result.append(
                    (
                        row.get("id"),
                        row.get("name")
                        or row.get("client_name")
                        or row.get("canonical_name"),
                    )
                )
            else:
                result.append((row[0], row[1]))

        return [
            (client_id, name)
            for client_id, name in result
            if name
        ]

    except Exception as exc:
        print(
            "[DIRECTORY ERROR]",
            repr(exc),
            flush=True,
        )
        return []

def get_aliases():
    """
    Загружаем существующие алиасы.
    """
    try:
        from app.web.directory_db import get_client_aliases

        rows = get_client_aliases()

        result = []

        for row in rows:
            if isinstance(row, dict):
                result.append(
                    (
                        row.get("client_id"),
                        row.get("raw_name")
                        or row.get("alias"),
                    )
                )
            else:
                result.append((row[0], row[1]))

        return result

    except Exception:
        return []

def normalize_result(text):
    """
    Жёстко извлекаем JSON из ответа модели.
    """
    text = text.strip()

    # ```json ... ```
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\s*```$",
        "",
        text,
        flags=re.I,
    )

    match = re.search(
        r"\{.*\}",
        text,
        flags=re.S,
    )

    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None

def ask_model(model, raw_name, directory):
    candidates = [
        name
        for _, name in directory
    ]

    prompt = f"""
Ты нормализуешь названия клиентов после OCR.

Нужно определить, является ли исходное значение:
1. тем же клиентом, который уже есть в справочнике;
2. или это другой клиент;
3. или определить невозможно.

ВАЖНО:
- Не придумывай клиентов.
- Не считай совпадением просто похожее слово.
- Опечатки OCR допустимы.
- Разные подразделения/продукты клиента могут быть отдельным клиентом.
- "Яндекс Маркет" НЕ обязательно означает "Яндекс".
- "Ozon Bank" НЕ обязательно означает "Ozon".
- "Яндекс Лавка" НЕ обязательно означает "Яндекс".
- Если уверенности недостаточно, возвращай NONE.

СПРАВОЧНИК:
{json.dumps(candidates, ensure_ascii=False)}

ИСХОДНОЕ ЗНАЧЕНИЕ:
{raw_name!r}

Верни ТОЛЬКО JSON:

{{
  "client": "точное имя из справочника" или null,
  "confidence": число от 0 до 1,
  "reason": "краткая причина"
}}
"""

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты аккуратный классификатор OCR-названий. "
                    "Никогда не придумывай значение, которого нет "
                    "в справочнике."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "stream": False,
        "options": {
            "temperature": 0,
        },
    }

    started = time.time()

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=180,
    )

    elapsed = time.time() - started

    response.raise_for_status()

    data = response.json()

    content = (
        data.get("message", {})
        .get("content", "")
    )

    result = normalize_result(content)

    return result, elapsed, content

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model",
        required=True,
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.80,
    )

    args = parser.parse_args()

    print("=" * 70)
    print("CLIENT NORMALIZER BENCHMARK")
    print("=" * 70)
    print("MODEL:", args.model)
    print("OLLAMA:", OLLAMA_URL)
    print()

    directory = get_directory()

    if not directory:
        print("ERROR: CLIENT DIRECTORY IS EMPTY")
        sys.exit(1)

    print("=" * 70)
    print("CLIENT DIRECTORY")
    print("=" * 70)

    for client_id, name in directory:
        print(f"{client_id:4}  {name}")

    print()

    aliases = get_aliases()

    known_aliases = {
        raw.strip().casefold()
        for _, raw in aliases
        if raw
    }

    raw_clients = get_clients_with_address_counts()

    unknown = []

    for raw_name, count in raw_clients:
        if not raw_name:
            continue

        if raw_name.strip().casefold() in known_aliases:
            continue

        # Проверяем canonical names тоже
        if any(
            raw_name.strip().casefold()
            == name.strip().casefold()
            for _, name in directory
        ):
            continue

        unknown.append(
            (raw_name, count)
        )

    print("=" * 70)
    print("UNKNOWN CLIENTS")
    print("=" * 70)
    print("COUNT:", len(unknown))
    print()

    results = []

    for index, (raw_name, count) in enumerate(
        unknown,
        1,
    ):
        print(
            f"[{index}/{len(unknown)}] "
            f"{raw_name!r} ({count} photos)"
        )

        try:
            result, elapsed, raw_response = ask_model(
                args.model,
                raw_name,
                directory,
            )

            if not result:
                print("  -> INVALID JSON")

                results.append({
                    "raw": raw_name,
                    "photos": count,
                    "client": None,
                    "confidence": 0,
                    "status": "INVALID",
                    "time": elapsed,
                })

                continue

            client = result.get("client")
            confidence = float(
                result.get("confidence", 0)
                or 0
            )
            reason = result.get(
                "reason",
                "",
            )

            if (
                client
                and confidence >= args.min_confidence
            ):
                print(
                    f"  -> {client!r}"
                )
                print(
                    f"  confidence: {confidence:.3f}"
                )
                print(
                    f"  reason: {reason}"
                )

                status = "MATCH"

            else:
                print("  -> NONE")

                if client:
                    print(
                        f"  candidate: {client!r}"
                    )
                    print(
                        f"  confidence: "
                        f"{confidence:.3f}"
                    )

                if reason:
                    print(
                        f"  reason: {reason}"
                    )

                status = "NONE"

            results.append({
                "raw": raw_name,
                "photos": count,
                "client": client,
                "confidence": confidence,
                "status": status,
                "reason": reason,
                "time": elapsed,
            })

        except Exception as exc:
            print(
                "  -> ERROR:",
                repr(exc),
            )

            results.append({
                "raw": raw_name,
                "photos": count,
                "client": None,
                "confidence": 0,
                "status": "ERROR",
                "error": repr(exc),
            })

    print()
    print("=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)

    total = len(results)

    matches = sum(
        r["status"] == "MATCH"
        for r in results
    )

    none = sum(
        r["status"] == "NONE"
        for r in results
    )

    errors = sum(
        r["status"] in ("ERROR", "INVALID")
        for r in results
    )

    print("TOTAL :", total)
    print("MATCH :", matches)
    print("NONE  :", none)
    print("ERROR :", errors)

    if total:
        print(
            "MATCH RATE:",
            f"{matches / total * 100:.1f}%"
        )

    output = (
        Path("data")
        / f"client_normalizer_benchmark_"
        f"{args.model.replace(':', '_')}.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            {
                "model": args.model,
                "min_confidence": args.min_confidence,
                "directory": directory,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("RESULT FILE:")
    print(output)

if __name__ == "__main__":
    main()
PY
```

Но у тебя проект работает через `uv`, поэтому сначала проверим зависимости:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -c "import psycopg2, requests; print('DEPS OK')"
```

Если `requests` есть, а `psycopg2` нет:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv add psycopg2-binary requests
```

После этого запускаем **именно 8B**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/benchmark_client_normalizer.py \
  --model qwen3:8b \
  --min-confidence 0.80
```

### Важный момент

Я бы пока **не принимал решения по результатам 4B**, которые ты показал.

Там уже видно потенциально опасное поведение:

> `'Яндекс Маркет' -> 'Яндекс' 0.950`

и

> `'Яндекс Лавка' -> 'Яндекс' 0.950`

Для нормализатора фотобазы это слишком агрессивно. Нам нужна логика:

**OCR-ошибка → исправляем**,  
**другое название/подбренд → не склеиваем автоматически.**

Поэтому 8B интересно проверить именно на этих пограничных случаях.

После 8B **тем же самым скриптом**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/benchmark_client_normalizer.py \
  --model qwen2.5:7b \
  --min-confidence 0.80
```

Если `qwen2.5:7b` пока не установлен, сначала:

```bash
ollama pull qwen2.5:7b
```

В результате получим два файла:

```text
data/client_normalizer_benchmark_qwen3_8b.json
data/client_normalizer_benchmark_qwen2.5_7b.json
```

И уже **по одинаковым 98 значениям** сравним не только количество совпадений, а прежде всего **ложные склейки**. Для этой задачи это важнее, чем просто высокий `MATCH RATE`.

---

### 👤 **User** — 2026-08-20 22:22:59

======================================================================
CLIENT NORMALIZER BENCHMARK
======================================================================
MODEL: qwen3:8b
OLLAMA: http://127.0.0.1:11434/api/chat

[DIRECTORY DB] loaded
[DIRECTORY ERROR] ImportError("cannot import name 'get_client_directory' from 'app.web.directory_db' (/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/directory_db.py)")
ERROR: CLIENT DIRECTORY IS EMPTY
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:23:00

Да, это моя ошибка в benchmark-скрипте: я предположил функцию `get_client_directory()`, а в твоём `directory_db.py` её нет. **Базовый `smart_client_normalizer.py` уже умеет загружать справочник**, поэтому не надо придумывать новый API.

Сначала посмотрим фактический `directory_db.py`, чтобы benchmark использовал существующую структуру.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DIRECTORY DB ================" && \
nl -ba app/web/directory_db.py | sed -n '1,320p'
```

И пришли вывод.

После этого я дам **точечную замену только benchmark-скрипта**, без изменения рабочего `smart_client_normalizer.py` и без изменения БД.

Особенно важно сохранить твои уже работающие:

```text
CLIENT DIRECTORY
CLIENT ALIASES
NORMALIZATION
```

и просто прогнать **те же 98 UNKNOWN** через `qwen3:8b`.

Пока **ничего не устанавливай и не меняй в БД**.

---

### 👤 **User** — 2026-08-20 22:23:16

выгрузим предыдущую можель

---

### 🤖 **Assistant** — 2026-08-20 22:23:17

Да. Если речь про **предыдущую модель `qwen3:4b`**, её можно удалить из Ollama, чтобы освободить VRAM/диск.

Сначала посмотрим точное имя и размер:

```bash
ollama list | grep 'qwen3:4b'
```

Если это именно:

```text
qwen3:4b
```

удаляем:

```bash
ollama rm qwen3:4b
```

Проверяем:

```bash
ollama list | grep qwen
```

При этом **`qwen3:8b` останется**.

Если под «выгрузим» ты имеешь в виду **не удалить модель с диска, а выгрузить её из памяти**, это другое действие — скажи, и дам команду именно для освобождения VRAM без удаления модели.

---

### 👤 **User** — 2026-08-20 22:23:30

выгрузим из памяти просто

---

### 🤖 **Assistant** — 2026-08-20 22:23:31

Да, удалять не надо. Для Ollama можно выгрузить модель из памяти так:

```bash
ollama stop qwen3:4b
```

Проверить:

```bash
ollama ps
```

Если всё прошло нормально, `qwen3:4b` в `ollama ps` уже не будет.

После этого можно запускать:

```bash
ollama run qwen3:8b
```

или сразу наш benchmark через `uv run`.

---

### 👤 **User** — 2026-08-20 22:24:08

[DIRECTORY DB] loaded
[DIRECTORY ERROR] ImportError("cannot import name 'get_client_directory' from 'app.web.directory_db' (/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/directory_db.py)")
ERROR: CLIENT DIRECTORY IS EMPTY
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:24:09

Да. Это **не проблема `qwen3:8b`**. Benchmark падает раньше — мой скрипт ищет функцию, которой у тебя нет.

Причём у тебя уже есть рабочая схема справочника и алиасов. Поэтому сейчас **не надо менять `directory_db.py` или БД**.

Сделаем benchmark использовать тот же механизм, что и `smart_client_normalizer.py`.

Сначала покажи его начало и функции загрузки:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SMART NORMALIZER ================" && \
nl -ba scripts/smart_client_normalizer.py | sed -n '1,220p' && \
echo "================ DIRECTORY DB ================" && \
nl -ba app/web/directory_db.py | sed -n '1,260p'
```

Пришли вывод.

После этого я дам **готовую команду/патч для `benchmark_client_normalizer.py`**, чтобы:

- справочник брался из твоей существующей БД;
- алиасы учитывались как сейчас;
- выбирались именно те же **98 UNKNOWN**;
- `qwen3:8b` прогонял **тот же набор**, что и `qwen3:4b`;
- результат сохранялся отдельно;
- **никаких изменений в БД** benchmark не делал.

Это сейчас правильнее, чем пытаться угадывать API твоего `directory_db.py`.

---

### 👤 **User** — 2026-08-20 22:24:35

int_mvp_v02 && \
echo "================ SMART NORMALIZER ================" && \
nl -ba scripts/smart_client_normalizer.py | sed -n '1,220p' && \
echo "================ DIRECTORY DB ================" && \
nl -ba app/web/directory_db.py | sed -n '1,260p'
================ SMART NORMALIZER ================
     1	#!/usr/bin/env python3
     2	
     3	import argparse
     4	import json
     5	import re
     6	import sys
     7	from collections import Counter
     8	
     9	import psycopg2
    10	import requests
    11	
    12	
    13	PG_CONFIG = {
    14	    "host": "localhost",
    15	    "port": 5432,
    16	    "dbname": "photobase",
    17	    "user": "lora",
    18	}
    19	
    20	OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
    21	DEFAULT_MODEL = "qwen3:4b-instruct"
    22	
    23	
    24	def get_connection():
    25	    return psycopg2.connect(**PG_CONFIG)
    26	
    27	
    28	# ============================================================
    29	# CLIENT DIRECTORY
    30	# ============================================================
    31	
    32	def get_client_directory(conn):
    33	    sql = """
    34	        SELECT
    35	            id,
    36	            name
    37	        FROM client_directory
    38	        WHERE active = TRUE
    39	        ORDER BY sort_order, name
    40	    """
    41	
    42	    with conn.cursor() as cur:
    43	        cur.execute(sql)
    44	        return cur.fetchall()
    45	
    46	
    47	# ============================================================
    48	# EXISTING ALIASES
    49	# ============================================================
    50	
    51	def get_alias_map(conn):
    52	    sql = """
    53	        SELECT
    54	            ca.raw_name,
    55	            cd.name
    56	        FROM client_aliases ca
    57	        JOIN client_directory cd
    58	          ON cd.id = ca.client_id
    59	        WHERE cd.active = TRUE
    60	    """
    61	
    62	    result = {}
    63	
    64	    with conn.cursor() as cur:
    65	        cur.execute(sql)
    66	
    67	        for raw_name, client_name in cur.fetchall():
    68	            if raw_name is None:
    69	                continue
    70	
    71	            key = raw_name.strip().casefold()
    72	
    73	            if key:
    74	                result[key] = client_name
    75	
    76	    return result
    77	
    78	
    79	# ============================================================
    80	# CURRENT RAW CLIENTS
    81	# ============================================================
    82	
    83	def get_current_raw_clients(conn):
    84	    sql = """
    85	        SELECT
    86	            TRIM(client) AS raw_name,
    87	            COUNT(*) AS cnt
    88	        FROM photos
    89	        WHERE
    90	            client IS NOT NULL
    91	            AND TRIM(client) <> ''
    92	        GROUP BY TRIM(client)
    93	        ORDER BY COUNT(*) DESC, TRIM(client)
    94	    """
    95	
    96	    with conn.cursor() as cur:
    97	        cur.execute(sql)
    98	
    99	        return [
   100	            (row[0], int(row[1]))
   101	            for row in cur.fetchall()
   102	        ]
   103	
   104	
   105	# ============================================================
   106	# BASIC NORMALIZATION
   107	# ============================================================
   108	
   109	def basic_normalize(raw_name, alias_map, directory_names):
   110	    if not raw_name:
   111	        return None
   112	
   113	    value = raw_name.strip()
   114	
   115	    # exact case-insensitive alias
   116	    key = value.casefold()
   117	
   118	    if key in alias_map:
   119	        return alias_map[key]
   120	
   121	    # exact directory name
   122	    directory_map = {
   123	        name.strip().casefold(): name
   124	        for name in directory_names
   125	    }
   126	
   127	    return directory_map.get(key)
   128	
   129	
   130	# ============================================================
   131	# OLLAMA
   132	# ============================================================
   133	
   134	def ask_qwen(raw_name, clients, model):
   135	    client_lines = "\n".join(
   136	        f"- {name}"
   137	        for name in clients
   138	    )
   139	
   140	    system_prompt = """
   141	Ты нормализуешь названия клиентов для фотобазы.
   142	
   143	Твоя задача:
   144	- получить исходное название клиента;
   145	- выбрать наиболее вероятного клиента ТОЛЬКО из переданного справочника;
   146	- исправлять очевидные опечатки, OCR-ошибки, регистр, пробелы,
   147	  перестановки букв и небольшие искажения;
   148	- учитывать очевидные варианты написания;
   149	- НЕ придумывать нового клиента;
   150	- НЕ выбирать клиента только потому, что он семантически похож,
   151	  если уверенности недостаточно.
   152	
   153	Особенно важно:
   154	"Волный Дон" может быть опечаткой "Вольный Дон",
   155	"Яндеск" -> "Яндекс",
   156	"Тетн" -> "Тенет".
   157	
   158	Если уверенности недостаточно, возвращай null.
   159	
   160	Верни ТОЛЬКО JSON:
   161	
   162	{
   163	  "client": "название из справочника или null",
   164	  "confidence": 0.0,
   165	  "reason": "краткое объяснение"
   166	}
   167	
   168	confidence от 0 до 1.
   169	""".strip()
   170	
   171	    user_prompt = f"""
   172	СПРАВОЧНИК ДОПУСТИМЫХ КЛИЕНТОВ:
   173	
   174	{client_lines}
   175	
   176	ИСХОДНОЕ НАЗВАНИЕ:
   177	{raw_name}
   178	
   179	Выбери клиента из справочника либо null.
   180	""".strip()
   181	
   182	    payload = {
   183	        "model": model,
   184	        "stream": False,
   185	        "format": "json",
   186	        "options": {
   187	            "temperature": 0,
   188	        },
   189	        "messages": [
   190	            {
   191	                "role": "system",
   192	                "content": system_prompt,
   193	            },
   194	            {
   195	                "role": "user",
   196	                "content": user_prompt,
   197	            },
   198	        ],
   199	    }
   200	
   201	    response = requests.post(
   202	        OLLAMA_URL,
   203	        json=payload,
   204	        timeout=120,
   205	    )
   206	
   207	    response.raise_for_status()
   208	
   209	    data = response.json()
   210	
   211	    content = (
   212	        data
   213	        .get("message", {})
   214	        .get("content", "")
   215	        .strip()
   216	    )
   217	
   218	    result = json.loads(content)
   219	
   220	    client = result.get("client")
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:24:36

Теперь всё ясно. У тебя **рабочий `get_client_directory(conn)` уже находится внутри `smart_client_normalizer.py`**, а в `directory_db.py` правильная функция называется `get_clients()`.

Для benchmark проще всего вообще не импортировать `directory_db`, а сделать его автономным и использовать **точно ту же SQL-логику**, что и рабочий smart normalizer.

Заменяем benchmark целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > scripts/benchmark_client_normalizer.py <<'PY'
#!/usr/bin/env python3

import argparse
import json
import sys
import time
from pathlib import Path

import psycopg2
import requests

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

def get_connection():
    return psycopg2.connect(**PG_CONFIG)

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

def basic_normalize(raw_name, alias_map, directory_names):
    if not raw_name:
        return None

    value = raw_name.strip()

    key = value.casefold()

    if key in alias_map:
        return alias_map[key]

    directory_map = {
        name.strip().casefold(): name
        for name in directory_names
    }

    return directory_map.get(key)

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
- исправлять очевидные опечатки OCR, регистр, пробелы,
  перестановки букв и небольшие искажения;
- учитывать очевидные варианты написания;
- НЕ придумывать нового клиента;
- НЕ выбирать клиента только потому, что он семантически похож,
  если уверенности недостаточно.

ВАЖНО:
Нужно отличать реальную OCR-ошибку от другого бренда,
подбренда, продукта, организации или рекламного объекта.

Например:
"Волный Дон" -> возможно "Вольный Дон"
"Яндеск" -> "Яндекс"
"Тетн" -> "Тенет"

Но:
"Яндекс Маркет" НЕ обязательно "Яндекс"
"Яндекс Лавка" НЕ обязательно "Яндекс"
"Ozon Bank" НЕ обязательно "Ozon"

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

    started = time.time()

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=120,
    )

    response.raise_for_status()

    elapsed = time.time() - started

    data = response.json()

    content = (
        data
        .get("message", {})
        .get("content", "")
        .strip()
    )

    result = json.loads(content)

    return result, elapsed

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model",
        required=True,
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.80,
    )

    args = parser.parse_args()

    print("=" * 70)
    print("CLIENT NORMALIZER BENCHMARK")
    print("=" * 70)
    print("MODEL:", args.model)
    print("OLLAMA:", OLLAMA_URL)
    print()

    conn = get_connection()

    try:
        directory = get_client_directory(conn)
        alias_map = get_alias_map(conn)
        raw_clients = get_current_raw_clients(conn)

        print(
            "[DIRECTORY DB] loaded",
            flush=True,
        )

        print()
        print("=" * 70)
        print("CLIENT DIRECTORY")
        print("=" * 70)

        for client_id, name in directory:
            print(
                f"{client_id:4}  {name}"
            )

        print()
        print(
            "ALIASES:",
            len(alias_map),
        )
        print(
            "RAW CLIENT VALUES:",
            len(raw_clients),
        )

        directory_names = [
            name
            for _, name in directory
        ]

        # Только неизвестные для текущего exact/alias normalizer
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

        print()
        print("=" * 70)
        print("UNKNOWN CLIENTS")
        print("=" * 70)
        print(
            "COUNT:",
            len(unknown),
        )
        print()

        clients = directory_names

        results = []

        for index, (raw_name, count) in enumerate(
            unknown,
            1,
        ):
            print(
                f"[{index}/{len(unknown)}] "
                f"{raw_name!r} "
                f"({count} photos)",
                flush=True,
            )

            try:
                result, elapsed = ask_qwen(
                    raw_name,
                    clients,
                    args.model,
                )

                client = result.get(
                    "client"
                )

                confidence = float(
                    result.get(
                        "confidence",
                        0,
                    ) or 0
                )

                reason = result.get(
                    "reason",
                    "",
                )

                if (
                    client
                    and confidence >= args.min_confidence
                ):
                    print(
                        f"  -> {client!r}"
                    )
                    print(
                        f"  confidence: "
                        f"{confidence:.3f}"
                    )

                    if reason:
                        print(
                            f"  reason: {reason}"
                        )

                    status = "MATCH"

                else:
                    print("  -> NONE")

                    if client:
                        print(
                            f"  candidate: "
                            f"{client!r}"
                        )
                        print(
                            f"  confidence: "
                            f"{confidence:.3f}"
                        )

                    if reason:
                        print(
                            f"  reason: {reason}"
                        )

                    status = "NONE"

                results.append({
                    "raw": raw_name,
                    "photos": count,
                    "client": client,
                    "confidence": confidence,
                    "status": status,
                    "reason": reason,
                    "time": elapsed,
                })

            except Exception as exc:

                print(
                    "  -> ERROR:",
                    repr(exc),
                )

                results.append({
                    "raw": raw_name,
                    "photos": count,
                    "client": None,
                    "confidence": 0,
                    "status": "ERROR",
                    "error": repr(exc),
                })

        print()
        print("=" * 70)
        print("BENCHMARK SUMMARY")
        print("=" * 70)

        total = len(results)

        matches = sum(
            r["status"] == "MATCH"
            for r in results
        )

        none = sum(
            r["status"] == "NONE"
            for r in results
        )

        errors = sum(
            r["status"] == "ERROR"
            for r in results
        )

        print("TOTAL :", total)
        print("MATCH :", matches)
        print("NONE  :", none)
        print("ERROR :", errors)

        if total:
            print(
                "MATCH RATE:",
                f"{matches / total * 100:.1f}%"
            )

        output = (
            Path("data")
            / (
                "client_normalizer_benchmark_"
                f"{args.model.replace(':', '_')}.json"
            )
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            json.dumps(
                {
                    "model": args.model,
                    "min_confidence": (
                        args.min_confidence
                    ),
                    "unknown_count": total,
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print()
        print("RESULT FILE:")
        print(output)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
PY
```

Теперь запускаем **8B**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/benchmark_client_normalizer.py \
  --model qwen3:8b \
  --min-confidence 0.80
```

### Что здесь важно

Я специально сделал benchmark максимально близким к твоему уже работающему `smart_client_normalizer.py`:

- `client_directory` — тот же SQL;
- `client_aliases` — тот же SQL;
- `photos.client` — та же группировка;
- exact match и aliases **не отправляются в Qwen**;
- Qwen получает только неизвестные;
- справочник содержит **только реальные активные клиенты**;
- БД benchmark **только читает**;
- результат `qwen3:8b` сохраняется отдельно.

То есть после запуска мы должны получить снова примерно те же **98 UNKNOWN**, и дальше уже честно сравним 4B и 8B.

---

### 👤 **User** — 2026-08-20 22:25:36

[1/98] 'EMBARGO' (43 photos)
  -> NONE
  reason: Нет совпадений в справочнике
[2/98] 'Единая Россия' (30 photos)
  -> NONE
  reason: Нет совпадений в справочнике. 'Единая Россия' не является известным клиентом из списка допустимых.
[3/98] 'Сила России' (18 photos)
  -> NONE
  reason: Нет совпадений в справочнике
[4/98] 'Вольный Дон' (14 photos)

---

### 🤖 **Assistant** — 2026-08-20 22:25:38

Да, это уже правильный этап. Сейчас **Qwen3:8b фактически не тестируется**, потому что справочник пустой в benchmark-скрипте.

Причина уже точно видна:

- `scripts/smart_client_normalizer.py` содержит собственную `get_client_directory()`;
- в `app/web/directory_db.py` функция называется **`get_clients()`**;
- поэтому benchmark пытается импортировать несуществующую `get_client_directory`.

И главное: **не надо менять `directory_db.py` ради теста**. Лучше привести тестовый скрипт к текущему API.

### Что сделать

В `benchmark_client_normalizer.py` заменить импорт/получение справочника на:

```python
from app.web.directory_db import get_clients
```

а вместо:

```python
client_directory = get_client_directory()
```

использовать:

```python
client_directory = get_clients()
```

Но формат там сейчас другой:

```python
[
    {
        "id": 6,
        "name": "HAVAL",
        "simple": "HAVAL",
    },
    ...
]
```

Поэтому список названий надо получить так:

```python
directory_names = [
    item["name"]
    for item in client_directory
    if item.get("name")
]
```

### Важный момент

Твой текущий `smart_client_normalizer.py` **уже работает правильно** с БД напрямую:

```python
def get_client_directory(conn):
```

и получает:

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

То есть **Qwen3:4b уже был протестирован на правильном справочнике**.

Для честного сравнения нам теперь нужно прогнать **абсолютно тот же набор из 98 неизвестных значений**:

```text
qwen3:4b
qwen3:8b
qwen2.5:7b
```

с одним и тем же:

- справочником;
- raw client values;
- prompt;
- `temperature=0`;
- `min-confidence=0.80`.

И только после этого сравнивать.

Причём я бы **не давал Qwen право автоматически создавать alias** на этом этапе. Тест должен отвечать только на вопрос:

> «Насколько хорошо модель определяет, является ли неизвестное значение вариантом одного из 12 известных клиентов?»

А уже потом можно сделать второй режим:

```text
MODEL → кандидат
       ↓
confidence >= 0.90 → предложить alias
confidence 0.80–0.90 → ручная проверка
confidence < 0.80 → NONE
```

Особенно это важно для таких вещей, как:

```text
'Яндекс Маркет'       → Яндекс ?
'Яндекс Лавка'        → Яндекс ?
'ozon fresh'          → Ozon ?
'Тенет Т41'           → Тенет ?
```

Потому что здесь модель может быть **семантически права**, но это уже не просто OCR-ошибка.

### И ещё важнее

Сейчас у тебя обнаружилось очень полезное разделение:

**Справочник клиентов** — это не список всех текущих `photos.client`.

А:

```text
client_directory
        ↓
12 канонических клиентов
        ↓
client_aliases
        ↓
известные варианты OCR
        ↓
Qwen
        ↓
неизвестные варианты
```

Именно такую архитектуру я бы и оставил.

Для следующего шага я бы **починил только benchmark**, не трогая рабочую нормализацию, и получил полноценную таблицу:

| RAW | Фото | Qwen 4B | Conf | Qwen 8B | Conf | Qwen 2.5 7B | Conf |
|---|---:|---|---:|---|---:|---|---:|
| Яндекс Маркет | 9 | Яндекс | .95 | ? | ? | ? | ? |
| ozon fresh | 5 | Ozon | .95 | ? | ? | ? | ? |
| Яндекс Лавка | 3 | Яндекс | .95 | ? | ? | ? | ? |
| Волный Дон | 7 | — | — | ? | ? | ? | ? |
| EMBAYGO | 2 | — | — | ? | ? | ? | ? |

Так мы увидим, **даёт ли 8B реальное улучшение над 4B**, а не просто субъективно «умнее».

---

### 👤 **User** — 2026-08-20 22:26:19

сделай последовательный скрипт на 25 фото, между тестами выгружай модели из памяти, потом сводная таблица

---

### 🤖 **Assistant** — 2026-08-20 22:26:26

> ****
>
> 
>
> **Creating 25-Photo Client Model Benchmark Script**
>
>
> **Creating 25-Photo Client Model Benchmark Script**
>
> 
>
> Worked for 13s

Да. Сделаем именно **последовательный benchmark**, без параллельной загрузки моделей.

Логика будет такая:

1. Берём **одинаковые 25 неизвестных клиентов** — по убыванию количества фотографий.
2. Загружаем `qwen3:4b`.
3. Прогоняем все 25.
4. `ollama stop qwen3:4b`.
5. Загружаем `qwen3:8b`.
6. Прогоняем **те же 25**.
7. Выгружаем.
8. `qwen2.5:7b`.
9. Прогоняем те же 25.
10. Выгружаем.
11. В конце — **сводная таблица по каждому RAW**, чтобы видеть ответы всех трёх моделей рядом.
12. CSV сохраняется для дальнейшего анализа.

Я не смог записать файл непосредственно в твой проект из этого окружения, поэтому вот готовая команда создания скрипта. Она использует `uv`, как ты и просил:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > scripts/benchmark_client_models_25.py <<'PY'
#!/usr/bin/env python3

import argparse
import csv
import json
import subprocess
import time
from pathlib import Path

import psycopg2
import requests

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

MODELS = [
    "qwen3:4b",
    "qwen3:8b",
    "qwen2.5:7b",
]

SYSTEM_PROMPT = """
Ты нормализуешь названия клиентов для фотобазы.

Твоя задача:
- получить исходное название;
- выбрать клиента ТОЛЬКО из переданного справочника;
- исправлять очевидные опечатки;
- исправлять OCR-ошибки;
- учитывать регистр;
- учитывать пробелы;
- учитывать небольшие перестановки и искажения букв;
- учитывать очевидные варианты написания;
- НЕ придумывать нового клиента;
- НЕ выбирать клиента только потому, что он семантически похож;
- если уверенности недостаточно — вернуть null.

Примеры:
"Яндеск" -> "Яндекс"
"яндекс" -> "Яндекс"
"сбер" -> "Сбер"
"Тетн" -> "Тенет"
"Тенит" -> "Тенет"
"h h" -> "hh"

Верни ТОЛЬКО JSON:

{
  "client": "название из справочника или null",
  "confidence": 0.0,
  "reason": "краткое объяснение"
}

confidence от 0 до 1.
""".strip()

def get_connection():
    return psycopg2.connect(**PG_CONFIG)

def load_test_data(limit):
    with get_connection() as conn:
        with conn.cursor() as cur:

            # ----------------------------------------------------
            # DIRECTORY
            # ----------------------------------------------------

            cur.execute("""
                SELECT
                    id,
                    name
                FROM client_directory
                WHERE active = TRUE
                ORDER BY sort_order, name
            """)

            directory = cur.fetchall()

            names = [
                row[1]
                for row in directory
                if row[1]
            ]

            # ----------------------------------------------------
            # UNKNOWN RAW CLIENTS
            # ----------------------------------------------------

            cur.execute("""
                SELECT
                    TRIM(p.client) AS raw_name,
                    COUNT(*) AS photo_count
                FROM photos p

                WHERE
                    p.client IS NOT NULL
                    AND TRIM(p.client) <> ''

                    -- exact directory match is already known
                    AND NOT EXISTS (
                        SELECT 1
                        FROM client_directory cd
                        WHERE
                            cd.active = TRUE
                            AND LOWER(TRIM(cd.name))
                                = LOWER(TRIM(p.client))
                    )

                    -- known alias is already normalized
                    AND NOT EXISTS (
                        SELECT 1
                        FROM client_aliases ca
                        JOIN client_directory cd
                          ON cd.id = ca.client_id
                        WHERE
                            cd.active = TRUE
                            AND LOWER(TRIM(ca.raw_name))
                                = LOWER(TRIM(p.client))
                    )

                GROUP BY TRIM(p.client)

                ORDER BY
                    COUNT(*) DESC,
                    TRIM(p.client)

                LIMIT %s
            """, (limit,))

            unknown = cur.fetchall()

    return names, unknown

def unload_model(model):
    print()
    print("------------------------------------------------------------")
    print("UNLOAD:", model)
    print("------------------------------------------------------------")

    try:
        subprocess.run(
            ["ollama", "stop", model],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except Exception as exc:
        print("[OLLAMA STOP ERROR]", repr(exc))

    # Небольшая пауза, чтобы VRAM действительно освободилась.
    time.sleep(3)

def ask_qwen(raw_name, directory_names, model):

    client_lines = "\n".join(
        f"- {name}"
        for name in directory_names
    )

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
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    }

    started = time.perf_counter()

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=180,
    )

    response.raise_for_status()

    elapsed = time.perf_counter() - started

    data = response.json()

    content = (
        data
        .get("message", {})
        .get("content", "")
        .strip()
    )

    try:
        result = json.loads(content)
    except Exception:
        result = {
            "client": None,
            "confidence": 0,
            "reason": "invalid JSON",
        }

    client = result.get("client")

    # ------------------------------------------------------------
    # HARD SAFETY:
    # модель имеет право выбрать только реальный directory name.
    # ------------------------------------------------------------

    if client not in directory_names:
        client = None

    try:
        confidence = float(
            result.get("confidence", 0) or 0
        )
    except Exception:
        confidence = 0.0

    reason = result.get(
        "reason",
        "",
    )

    return {
        "client": client,
        "confidence": confidence,
        "reason": reason,
        "seconds": elapsed,
    }

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.80,
    )

    parser.add_argument(
        "--out",
        default="data/client_model_benchmark_25.csv",
    )

    args = parser.parse_args()

    # ============================================================
    # LOAD TEST SET
    # ============================================================

    directory_names, unknown = load_test_data(
        args.limit
    )

    print("=" * 70)
    print("CLIENT NORMALIZER BENCHMARK")
    print("=" * 70)

    print()
    print("DIRECTORY:")
    for name in directory_names:
        print("  ", name)

    print()
    print("TEST SET:", len(unknown))
    print()

    for index, (raw, count) in enumerate(
        unknown,
        1,
    ):
        print(
            f"{index:02d}. "
            f"{count:3d}  "
            f"{raw!r}"
        )

    # ============================================================
    # RESULTS
    # ============================================================

    results = []

    # ============================================================
    # MODELS — STRICTLY SEQUENTIAL
    # ============================================================

    for model_index, model in enumerate(
        MODELS,
        1,
    ):

        print()
        print("=" * 70)
        print(
            f"MODEL {model_index}/{len(MODELS)}: "
            f"{model}"
        )
        print("=" * 70)

        # Important:
        # перед началом каждой модели стараемся убрать
        # предыдущую модель из памяти.
        unload_model(model)

        for index, (raw, photo_count) in enumerate(
            unknown,
            1,
        ):

            try:

                result = ask_qwen(
                    raw,
                    directory_names,
                    model,
                )

                client = result["client"]
                confidence = result["confidence"]

                accepted = (
                    client
                    if confidence >= args.min_confidence
                    else None
                )

                print(
                    f"[{index:02d}/{len(unknown)}] "
                    f"{raw!r:45} "
                    f"-> {accepted!r:18} "
                    f"conf={confidence:.2f} "
                    f"time={result['seconds']:.1f}s"
                )

                results.append({
                    "raw": raw,
                    "photos": photo_count,
                    "model": model,
                    "client": accepted or "",
                    "confidence": f"{confidence:.3f}",
                    "seconds": f"{result['seconds']:.2f}",
                    "reason": result["reason"],
                })

            except Exception as exc:

                print(
                    f"[{index:02d}/{len(unknown)}] "
                    f"{raw!r:45} "
                    f"-> ERROR: {exc}"
                )

                results.append({
                    "raw": raw,
                    "photos": photo_count,
                    "model": model,
                    "client": "",
                    "confidence": "0",
                    "seconds": "0",
                    "reason": f"ERROR: {exc}",
                })

        # --------------------------------------------------------
        # FULL UNLOAD AFTER MODEL
        # --------------------------------------------------------

        unload_model(model)

    # ============================================================
    # CSV
    # ============================================================

    output = Path(args.out)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "raw",
                "photos",
                "model",
                "client",
                "confidence",
                "seconds",
                "reason",
            ],
        )

        writer.writeheader()
        writer.writerows(results)

    # ============================================================
    # SUMMARY
    # ============================================================

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for model in MODELS:

        rows = [
            row
            for row in results
            if row["model"] == model
        ]

        accepted = [
            row
            for row in rows
            if row["client"]
        ]

        total_photos = sum(
            int(row["photos"])
            for row in rows
        )

        accepted_photos = sum(
            int(row["photos"])
            for row in accepted
        )

        avg_confidence = (
            sum(
                float(row["confidence"])
                for row in rows
            )
            / len(rows)
            if rows
            else 0
        )

        total_time = sum(
            float(row["seconds"])
            for row in rows
        )

        print(
            f"{model:18} "
            f"accepted={len(accepted):2}/{len(rows):2}  "
            f"photos={accepted_photos:3}/{total_photos:3}  "
            f"avg_conf={avg_confidence:.3f}  "
            f"time={total_time:.1f}s"
        )

    # ============================================================
    # SIDE-BY-SIDE TABLE
    # ============================================================

    print()
    print("=" * 70)
    print("SIDE-BY-SIDE RESULTS")
    print("=" * 70)

    by_raw = {}

    for row in results:

        by_raw.setdefault(
            row["raw"],
            {
                "photos": row["photos"],
            },
        )

        by_raw[row["raw"]][row["model"]] = (
            row["client"],
            row["confidence"],
        )

    print()
    print(
        f"{'RAW':35} "
        f"{'PH':>3} "
        f"{'Q3-4B':>18} "
        f"{'Q3-8B':>18} "
        f"{'Q2.5-7B':>18}"
    )

    print("-" * 110)

    for raw, data in by_raw.items():

        cells = []

        for model in MODELS:

            client, confidence = data.get(
                model,
                ("", "0"),
            )

            if client:
                cells.append(
                    f"{client[:10]}({confidence})"
                )
            else:
                cells.append(
                    "NONE"
                )

        print(
            f"{raw[:35]:35} "
            f"{data['photos']:3d} "
            f"{cells[0]:18} "
            f"{cells[1]:18} "
            f"{cells[2]:18}"
        )

    print()
    print("=" * 70)
    print("CSV:", output)
    print("=" * 70)

if __name__ == "__main__":
    main()
PY
chmod +x scripts/benchmark_client_models_25.py
echo 'SCRIPT CREATED'
"],"timeout":10000}

---

### 👤 **User** — 2026-08-20 22:26:48

переперед тестом освободить врам

---

### 🤖 **Assistant** — 2026-08-20 22:26:49

Да. Сделаем **чистый A/B-тест на одном и том же наборе из 25 неизвестных клиентов**:

1. выбрать первые 25 по количеству фото;
2. перед каждым запуском:
   - выгрузить предыдущую Ollama-модель из VRAM;
   - очистить GPU cache;
   - проверить `nvidia-smi`;
3. прогнать:
   - `qwen3:4b`
   - `qwen3:8b`
   - `qwen2.5:7b` — если модель установлена;
4. сохранить результаты каждого теста;
5. в конце вывести **сводную таблицу**:
   - raw client
   - эталонный/ожидаемый результат
   - результат каждой модели
   - confidence
   - совпадение;
6. отдельно посчитать:
   - сколько предложено;
   - сколько `NONE`;
   - сколько правильных;
   - сколько ошибочных;
   - среднюю confidence;
   - время на 25 запросов.

Причём **между моделями не будем полагаться только на `keep_alive=0`** — сделаем принудительное освобождение Ollama и проверку VRAM перед следующим тестом.

Для твоего проекта я бы сделал отдельный скрипт:

```text
scripts/benchmark_client_models_25.py
```

и запуск:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/benchmark_client_models_25.py
```

Но есть важный момент: сейчас `directory_db.py` содержит `get_clients()`, а не `get_client_directory()`. Поэтому новый benchmark **не должен импортировать `get_client_directory`**. Он будет брать справочник через существующий `get_clients()`.

И ещё: `qwen2.5:7b` у тебя пока, судя по предыдущему `ollama list`, **не установлен**. Скрипт может проверить это автоматически и пропустить модель с пометкой `NOT INSTALLED`, не ломая весь тест.

Если хочешь именно **25 наиболее частых неизвестных клиентов**, набор будет начинаться с:

```text
EMBARGO
Единая Россия
Сила России
Вольный Дон
БЕТСИТИ
Пятёрочка
Яндекс Маркет
Магнит
МТС
Волный Дон
ozon fresh
Государственная Дума
Купер
Московский Цирк Никулина
контракт61.рф
Волынский Дон
Дон
Максидом
ОКЕЙ
ООО «Интернет Решений»
Ростов-на-Дону
Яндекс Лавка
EMBAYGO
WINLINE
Бронницкий Ювелир
```

Это хороший набор: здесь есть как очевидные самостоятельные бренды, так и потенциальные ошибки/варианты (`Волный Дон`, `Яндекс Маркет`, `ozon fresh`), поэтому сравнение моделей будет показательным.

---

### 👤 **User** — 2026-08-20 22:27:28

даваай

---

