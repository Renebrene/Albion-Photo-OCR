## СЕССИЯ: ФОТОБАЗА ОФИС

**Создано:** 2026-08-16 00:03:58
**Обновлено:** 2026-08-19 21:49:51
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df)

---

### 👤 **User** — 2026-08-16 12:07:57

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ollama show llama3.2-vision:11b
  Model
    architecture        mllama    
    parameters          10.7B     
    context length      131072    
    embedding length    4096      
    quantization        Q4_K_M    

  Capabilities
    tools         
    completion    
    vision        

  Parameters
    top_p          0.9    
    temperature    0.6    

  License
    **Llama 3.2** **Acceptable Use Policy**                                                                 
    Meta is committed to promoting safe and fair use of its tools and features,                             
      including Llama 3.2. If you access or use Llama 3.2, you agree to this Acceptable                       
      Use Policy (“**Policy**”). The most recent copy of this policy can be found at                          
      [https://www.llama.com/llama3_2/use-policy](https://www.llama.com/llama3_2/use-policy).                 
    ...

---

### 🤖 **Assistant** — 2026-08-16 12:07:58

Вот теперь картина ясна.

Модель сама по себе **нормальная и действительно vision**:

```text
architecture   mllama
parameters     10.7B
context        131072
vision         yes
Q4_K_M
```

Но ваш `ollama` при запуске передаёт её в `llama-server`, а тот отвечает:

```text
unknown model architecture: 'mllama'
```

То есть проблема возникает **на уровне runtime**, а не при скачивании/описании модели.

### Я предлагаю сейчас не ломать рабочую систему

Для нашего основного эксперимента оставляем:

```text
Qwen3-VL 2B
Qwen3-VL 4B
```

и делаем нормальный тест 50 фотографий.

Причём я бы изменил предыдущий скрипт ещё немного:

**1. Уменьшаем фото до 1600 px**

**2. `num_ctx=16384`**

**3. Не используем `format=json`**

Для Qwen-VL иногда принудительный JSON сам увеличивает нагрузку/вызывает проблемы. Попросим модель вернуть JSON текстом и сами распарсим.

**4. Каждое фото обрабатывается обеими моделями**

**5. Если одна модель ошиблась — тест продолжается**

**6. Сохраняем время и полный ответ**

Получим:

```text
50 фотографий × 2 модели = 100 анализов
```

И уже после этого сравним качество.

---

А Llama 3.2 Vision я бы пока **не удалял**. На RTX 3060 12 GB она потенциально интересна как "экспертная модель", но сначала надо разобраться, почему именно ваш runtime не принимает `mllama`.

Для нашего проекта она вообще не обязательна: если **2B даст 90–95% качества 4B**, это будет гораздо интереснее для обработки 200–300 фотографий в день.

---

### 👤 **User** — 2026-08-16 12:08:59

давай. только пока не уменьшаем фото, оставляем те же параметры как и для 4И

---

### 🤖 **Assistant** — 2026-08-16 12:08:59

Да. Тогда **ничего не уменьшаем**: одинаковые исходные фотографии, одинаковый prompt и одинаковые параметры для обеих Qwen-моделей. Так сравнение будет честным.

Главное исправление — `num_ctx=16384`, чтобы не получать `4131 > 4096`.

Сделаем готовый `v03` только для:

```text
qwen3-vl:4b-instruct
qwen3-vl:2b-instruct
```

50 файлов.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/banner_model_compare_v03.py <<'PY'
#!/usr/bin/env python3

import base64
import json
import time
from pathlib import Path

import requests
from tqdm import tqdm

INPUT_DIR = Path("data/input/test")

OUTPUT_DIR = Path(
    "data/banner_database/model_compare_v03"
)

MODELS = [
    "qwen3-vl:4b-instruct",
    "qwen3-vl:2b-instruct",
]

OLLAMA_URL = "http://localhost:11434/api/chat"

LIMIT = 50

NUM_CTX = 16384

PROMPT = """
Ты анализируешь фотографию с улицы, на которой могут присутствовать
рекламные баннеры.

Нужно максимально подробно описать рекламный баннер, если он присутствует.

Верни строго JSON следующего вида:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "confidence": 0
}

Поля:

client:
Компания, организация, политическая партия или заказчик рекламы.

brand:
Торговая марка или бренд.

category:
Категория рекламы.
Например: продукты, банк, букмекер, выборы, политика,
строительство, одежда, ресторан, автомобиль и т.д.

text:
Массив ВСЕГО читаемого текста на рекламном баннере.
Старайся сохранить цифры, даты, телефоны, названия и имена.

colors:
Основные цвета именно рекламного баннера.

objects:
Главные визуальные объекты:
люди, продукты, автомобили, здания, логотипы, животные и т.д.

description:
Подробное описание баннера и его внешнего вида.
Опиши расположение основных элементов, изображение, логотип,
текст, цветовую схему и характер рекламы.

confidence:
Уверенность от 0 до 100.

Если рекламного баннера нет или его невозможно определить,
оставь соответствующие поля пустыми.

Не придумывай информацию, которой нет на изображении.
"""

def image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def ask_model(model: str, image64: str):

    payload = {
        "model": model,

        "messages": [
            {
                "role": "user",
                "content": PROMPT,
                "images": [image64],
            }
        ],

        "stream": False,

        "options": {
            "num_ctx": NUM_CTX,
            "temperature": 0,
        },
    }

    start = time.time()

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=900,
    )

    elapsed = time.time() - start

    if response.status_code != 200:
        raise RuntimeError(response.text)

    data = response.json()

    answer = data["message"]["content"]

    result = None

    # Пытаемся разобрать JSON.
    try:
        result = json.loads(answer)
    except Exception:
        pass

    # Иногда модель возвращает ```json ... ```
    if result is None:
        cleaned = answer.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "", 1)
            cleaned = cleaned.replace("```", "")
            cleaned = cleaned.strip()

        try:
            result = json.loads(cleaned)
        except Exception:
            result = {
                "raw_answer": answer
            }

    result["_model"] = model
    result["_time_sec"] = round(elapsed, 2)

    return result

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    files = sorted(
        list(INPUT_DIR.glob("*.JPG"))
        + list(INPUT_DIR.glob("*.jpg"))
        + list(INPUT_DIR.glob("*.PNG"))
        + list(INPUT_DIR.glob("*.png"))
    )

    files = files[:LIMIT]

    print("=" * 70)
    print("BANNER MODEL COMPARE v03")
    print("=" * 70)
    print()
    print("FILES:", len(files))
    print()
    print("MODELS:")

    for model in MODELS:
        print(" -", model)

    print()
    print("IMAGE RESIZE: DISABLED")
    print("NUM_CTX:", NUM_CTX)
    print("TEMPERATURE: 0")
    print()

    summary = []

    for image_path in tqdm(files):

        print()
        print("=" * 70)
        print("IMAGE:", image_path.name)
        print("=" * 70)

        image64 = image_to_base64(image_path)

        image_dir = OUTPUT_DIR / image_path.stem

        image_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        for model in MODELS:

            print()
            print("MODEL:", model)

            try:

                result = ask_model(
                    model,
                    image64
                )

                safe_name = (
                    model
                    .replace(":", "_")
                    .replace("/", "_")
                )

                output_file = (
                    image_dir
                    / f"{safe_name}.json"
                )

                with open(
                    output_file,
                    "w",
                    encoding="utf-8"
                ) as f:

                    json.dump(
                        result,
                        f,
                        ensure_ascii=False,
                        indent=2
                    )

                summary.append({
                    "file": image_path.name,
                    "model": model,
                    "status": "OK",
                    "time_sec": result.get(
                        "_time_sec"
                    ),
                    "client": result.get(
                        "client", ""
                    ),
                    "brand": result.get(
                        "brand", ""
                    ),
                    "category": result.get(
                        "category", ""
                    ),
                    "confidence": result.get(
                        "confidence", ""
                    ),
                    "text": result.get(
                        "text", []
                    ),
                    "description": result.get(
                        "description", ""
                    ),
                })

                print(
                    "OK:",
                    result.get("client", ""),
                    "|",
                    result.get("brand", ""),
                    "|",
                    result.get("confidence", "")
                )

                print(
                    "TIME:",
                    result.get("_time_sec"),
                    "sec"
                )

            except Exception as e:

                print()
                print("ERROR:", model)
                print(e)

                summary.append({
                    "file": image_path.name,
                    "model": model,
                    "status": "ERROR",
                    "error": str(e),
                })

    summary_file = (
        OUTPUT_DIR / "summary.json"
    )

    with open(
        summary_file,
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
    print("=" * 70)
    print("DONE")
    print("=" * 70)
    print()
    print("RESULT:", OUTPUT_DIR)
    print("SUMMARY:", summary_file)

if __name__ == "__main__":
    main()
PY

chmod +x scripts/banner_model_compare_v03.py
```

Запускаем:

```bash
uv run python scripts/banner_model_compare_v03.py
```

### Важный момент

Сейчас **фотографии вообще не трогаем**:

```text
3500×2500 → 그대로
```

Обе модели получают абсолютно одинаковый base64 исходного файла.

И одинаковые:

```text
NUM_CTX = 16384
temperature = 0
```

Поэтому сравнение будет максимально чистым:

**4B vs 2B на одной и той же фотографии.**

Результаты появятся здесь:

```text
data/banner_database/model_compare_v03/
```

После окончания я бы уже не делал ручное сравнение 100 JSON. Следующим шагом сделаем автоматический отчёт **4B vs 2B по 50 фотографиям**: полнота текста, определение клиента/бренда, категория, описание и среднее время.

---

### 👤 **User** — 2026-08-16 12:10:13

4B мы уже етстировали. надо 2.5qwen b 2B

---

### 🤖 **Assistant** — 2026-08-16 12:10:14

Да, понял. **4B повторно не гоняем.** У нас уже есть результаты 4B. Сейчас задача — отдельно прогнать **Qwen2.5-VL 3B** и **Qwen3-VL 2B**, по тем же 50 фото и тем же параметрам, а потом сравнить их с уже сохранённым результатом Qwen3-VL 4B.

Но у вас `qwen2.5-vl:3b` через Ollama не существует под этим тегом. Поэтому сначала надо получить точное имя модели. Ollama умеет работать с каталогом через веб, а не через `ollama search`.

Попробуйте:

```bash
curl -s https://ollama.com/api/tags | python3 -m json.tool | grep -i -A5 -B5 "qwen2.5"
```

Если там ничего не будет, проверим каталог напрямую:

```bash
curl -s https://ollama.com/search?q=qwen2.5-vl | head
```

### А Qwen3-VL 2B у вас уже есть

По предыдущему запуску видно:

```text
qwen3-vl:2b-instruct
```

модель существует и доходит до обработки изображения. Она упиралась только в:

```text
4131 tokens > 4096
```

То есть для неё делаем:

```text
Qwen3-VL 2B
50 фото
исходный размер
num_ctx=16384
temperature=0
```

И отдельно:

```text
Qwen2.5-VL 3B
50 фото
исходный размер
num_ctx=16384
temperature=0
```

**4B вообще не запускаем.**

После этого сравнение будет:

| Модель | Источник |
|---|---|
| Qwen3-VL 4B | уже готовые результаты |
| Qwen3-VL 2B | новый прогон |
| Qwen2.5-VL 3B | новый прогон |

И это будет гораздо полезнее, чем повторять 4B.

---

### 👤 **User** — 2026-08-16 12:10:35

NAME                    ID              SIZE      MODIFIED       
qwen2.5vl:3b            fb90415cde1e    3.2 GB    9 minutes ago     
llama3.2-vision:11b     6f2f9757ae97    7.8 GB    14 minutes ago    
qwen3-vl:2b-instruct    ea422f1e7365    1.9 GB    15 minutes ago    
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
qwen2.5-coder:7b        dae161e27b0e    4.7 GB    4 weeks ago       
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 12:10:35

Отлично. Теперь всё, что нужно, установлено:

```text
qwen3-vl:4b-instruct   ← уже тестировали
qwen3-vl:2b-instruct   ← тестируем
qwen2.5vl:3b           ← тестируем
```

Именно эти **два новых прогона** делаем на тех же 50 фотографиях, без уменьшения изображений.

Создаём готовый файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/banner_model_compare_v04.py <<'PY'
#!/usr/bin/env python3

import base64
import json
import time
from pathlib import Path

import requests
from tqdm import tqdm

INPUT_DIR = Path("data/input/test")

OUTPUT_DIR = Path(
    "data/banner_database/model_compare_v04"
)

MODELS = [
    "qwen3-vl:2b-instruct",
    "qwen2.5vl:3b",
]

OLLAMA_URL = "http://localhost:11434/api/chat"

LIMIT = 50

NUM_CTX = 16384

PROMPT = """
Ты анализируешь фотографию с улицы.

На фотографии может находиться рекламный баннер.
Нужно максимально подробно описать баннер, если он присутствует.

Верни строго JSON:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "confidence": 0
}

Определи:

client:
Компания, организация, политическая партия или заказчик рекламы.

brand:
Торговая марка или бренд.

category:
Категория рекламы.
Например: продукты, банк, букмекер, выборы, политика,
строительство, одежда, ресторан, автомобиль и т.д.

text:
Массив ВСЕГО читаемого текста на рекламном баннере.
Особенно важны:
- названия компаний;
- бренды;
- имена;
- даты;
- телефоны;
- цены;
- адреса;
- сайты;
- лозунги.

colors:
Основные цвета рекламного баннера.

objects:
Главные визуальные объекты:
люди, продукты, автомобили, здания, логотипы,
животные и другие заметные объекты.

description:
Подробное описание баннера.
Опиши изображение, расположение элементов,
цветовую схему, логотипы, текст и характер рекламы.

confidence:
Уверенность от 0 до 100.

Если рекламного баннера нет или его невозможно определить,
оставь соответствующие поля пустыми.

Не придумывай информацию, которой нет на фотографии.
"""

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
                ],
            }
        ],

        "stream": False,

        "options": {
            "num_ctx": NUM_CTX,
            "temperature": 0,
        },
    }

start = time.time()

response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=900,
    )

elapsed = time.time() - start

if response.status_code != 200:

        raise RuntimeError(
            response.text
        )

data = response.json()

    answer = data["message"]["content"]

result = None

try:

        result = json.loads(answer)

    except Exception:

        pass

if result is None:

        cleaned = answer.strip()

        if cleaned.startswith("```"):

            cleaned = cleaned.replace(
                "```json",
                "",
                1
            )

            cleaned = cleaned.replace(
                "```",
                ""
            )

            cleaned = cleaned.strip()

try:

            result = json.loads(
                cleaned
            )

        except Exception:

            result = {
                "raw_answer": answer
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
        list(INPUT_DIR.glob("*.PNG"))
        +
        list(INPUT_DIR.glob("*.png"))
    )

files = files[:LIMIT]

print("=" * 70)
    print("BANNER MODEL COMPARE v04")
    print("=" * 70)
    print()

    print("FILES:", len(files))

    print()

    print("MODELS:")

    for model in MODELS:
        print(" -", model)

    print()

    print("IMAGE RESIZE: DISABLED")
    print("NUM_CTX:", NUM_CTX)
    print("TEMPERATURE: 0")

    print()

summary = []

for image_path in tqdm(files):

        print()
        print(
            "IMAGE:",
            image_path.name
        )

image64 = image_to_base64(
            image_path
        )

image_dir = (
            OUTPUT_DIR
            / image_path.stem
        )

image_dir.mkdir(
            parents=True,
            exist_ok=True
        )

for model in MODELS:

            print()
            print(
                "MODEL:",
                model
            )

try:

                result = ask_model(
                    model,
                    image64
                )

safe_name = (
                    model
                    .replace(
                        ":",
                        "_"
                    )
                    .replace(
                        "/",
                        "_"
                    )
                )

output_file = (
                    image_dir
                    / f"{safe_name}.json"
                )

with open(
                    output_file,
                    "w",
                    encoding="utf-8"
                ) as f:

                    json.dump(
                        result,
                        f,
                        ensure_ascii=False,
                        indent=2
                    )

summary.append({

                    "file":
                        image_path.name,

                    "model":
                        model,

                    "status":
                        "OK",

                    "time_sec":
                        result.get(
                            "_time_sec"
                        ),

                    "client":
                        result.get(
                            "client",
                            ""
                        ),

                    "brand":
                        result.get(
                            "brand",
                            ""
                        ),

                    "category":
                        result.get(
                            "category",
                            ""
                        ),

                    "confidence":
                        result.get(
                            "confidence",
                            ""
                        ),

                    "text":
                        result.get(
                            "text",
                            []
                        ),

                    "description":
                        result.get(
                            "description",
                            ""
                        ),

                })

print(
                    "OK:",
                    result.get(
                        "client",
                        ""
                    ),
                    "|",
                    result.get(
                        "brand",
                        ""
                    ),
                    "| confidence:",
                    result.get(
                        "confidence",
                        ""
                    )
                )

print(
                    "TIME:",
                    result.get(
                        "_time_sec"
                    ),
                    "sec"
                )

except Exception as e:

                print()
                print(
                    "ERROR:",
                    model
                )

                print(e)

summary.append({

                    "file":
                        image_path.name,

                    "model":
                        model,

                    "status":
                        "ERROR",

                    "error":
                        str(e),

                })

summary_file = (
        OUTPUT_DIR
        / "summary.json"
    )

with open(
        summary_file,
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
    print("=" * 70)
    print("DONE")
    print("=" * 70)

    print()
    print(
        "RESULT:",
        OUTPUT_DIR
    )

    print(
        "SUMMARY:",
        summary_file
    )

if __name__ == "__main__":
    main()
PY

chmod +x scripts/banner_model_compare_v04.py
```

Запускаем:

```bash
uv run python scripts/banner_model_compare_v04.py
```

### Что получим

Для каждого из 50 файлов:

```text
data/banner_database/model_compare_v04/
    Ашхабадский_01/
        qwen3-vl_2b-instruct.json
        qwen2.5vl_3b.json

    Ашхабадский_02/
        qwen3-vl_2b-instruct.json
        qwen2.5vl_3b.json

    ...
```

И общий:

```text
summary.json
```

**4B здесь вообще не запускается.**

После окончания сравним эти результаты с уже полученными от `qwen3-vl:4b-instruct`. Особенно интересно будет посмотреть не только на `confidence`, а на **реальную полноту текста и правильность клиента/бренда**. Именно это определит, можем ли мы для ежедневных 200–300 фотографий заменить 4B на 2B или 2.5-VL 3B.

---

### 👤 **User** — 2026-08-16 12:14:19

juen kb ,snm njhvjpf bp pf gthtrk.xtybz vjltktq? vj;tn ,snm ntcns gjujyfnm gjcktljdfntkmyj

---

### 🤖 **Assistant** — 2026-08-16 12:14:20

Понял 🙂 Ты имел в виду примерно:

**«Они ли будут тормозить из-за переполнения модели? Может быть тестировать последовательно?»**

Да — **лучше тестировать последовательно**, особенно на RTX 3060 12 GB.

Сейчас у нас две модели:

```text
qwen3-vl:2b
qwen2.5vl:3b
```

Если запускать их одновременно, они могут конкурировать за VRAM и резко замедлиться или уйти частично в RAM.

А текущий скрипт как раз работает **последовательно**:

```text
Фото 1
 ├── Qwen3-VL 2B
 └── Qwen2.5-VL 3B

Фото 2
 ├── Qwen3-VL 2B
 └── Qwen2.5-VL 3B
...
```

Это правильно.

Но есть ещё более интересный вариант для нашего теста: сначала прогнать **все 50 фотографий Qwen3-VL 2B**, затем выгрузить её из GPU и прогнать **все 50 Qwen2.5-VL 3B**.

То есть:

```text
50 фото
     ↓
Qwen3-VL 2B
     ↓
результаты

затем

50 фото
     ↓
Qwen2.5-VL 3B
     ↓
результаты
```

Так мы получим **более чистое сравнение скорости**, потому что модель не будет постоянно переключаться.

И для реальной системы это тоже ближе к правильной архитектуре: **одна модель загружена → обрабатывает всю пачку → следующая модель только при необходимости**.

---

### 👤 **User** — 2026-08-16 12:14:42

да

---

### 🤖 **Assistant** — 2026-08-16 12:14:42

Да. Тогда делаем именно **два последовательных прохода**: сначала все 50 фото `Qwen3-VL 2B`, затем все 50 `Qwen2.5-VL 3B`.

При этом **фото не уменьшаем**, параметры одинаковые, 4B не запускаем.

Создаём готовый файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/banner_model_compare_v05.py <<'PY'
#!/usr/bin/env python3

import base64
import json
import time
from pathlib import Path

import requests
from tqdm import tqdm

INPUT_DIR = Path("data/input/test")
OUTPUT_DIR = Path("data/banner_database/model_compare_v05")

MODELS = [
    "qwen3-vl:2b-instruct",
    "qwen2.5vl:3b",
]

OLLAMA_URL = "http://localhost:11434/api/chat"

LIMIT = 50
NUM_CTX = 16384
TEMPERATURE = 0

PROMPT = """
Ты анализируешь фотографию с улицы.

На фотографии может находиться рекламный баннер.
Нужно максимально подробно описать баннер, если он присутствует.

Верни строго JSON:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "confidence": 0
}

Определи:

client:
Компания, организация, политическая партия или заказчик рекламы.

brand:
Торговая марка или бренд.

category:
Категория рекламы.
Например: продукты, банк, букмекер, выборы, политика,
строительство, одежда, ресторан, автомобиль и т.д.

text:
Массив ВСЕГО читаемого текста на рекламном баннере.
Особенно важны названия компаний, бренды, имена,
даты, телефоны, цены, адреса, сайты и лозунги.

colors:
Основные цвета рекламного баннера.

objects:
Главные визуальные объекты:
люди, продукты, автомобили, здания, логотипы,
животные и другие заметные объекты.

description:
Подробное описание баннера.
Опиши изображение, расположение элементов,
цветовую схему, логотипы, текст и характер рекламы.

confidence:
Уверенность от 0 до 100.

Если рекламного баннера нет или его невозможно определить,
оставь соответствующие поля пустыми.

Не придумывай информацию, которой нет на фотографии.
"""

def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def ask_model(model, image64):

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": PROMPT,
                "images": [image64],
            }
        ],
        "stream": False,
        "options": {
            "num_ctx": NUM_CTX,
            "temperature": TEMPERATURE,
        },
    }

    start = time.time()

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=900,
    )

    elapsed = time.time() - start

    if response.status_code != 200:
        raise RuntimeError(response.text)

    data = response.json()

    answer = data["message"]["content"]

    try:
        result = json.loads(answer)
    except Exception:

        cleaned = answer.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "", 1)
            cleaned = cleaned.replace("```", "")
            cleaned = cleaned.strip()

        try:
            result = json.loads(cleaned)
        except Exception:
            result = {
                "raw_answer": answer
            }

    result["_model"] = model
    result["_time_sec"] = round(elapsed, 2)

    return result

def process_model(model, files, summary):

    print()
    print("=" * 70)
    print("MODEL PASS:", model)
    print("=" * 70)
    print()

    model_start = time.time()

    for image_path in tqdm(
        files,
        desc=model,
        unit="img"
    ):

        print()
        print(image_path.name)

        image64 = image_to_base64(image_path)

        image_dir = OUTPUT_DIR / image_path.stem
        image_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        try:

            result = ask_model(
                model,
                image64
            )

            safe_name = (
                model
                .replace(":", "_")
                .replace("/", "_")
            )

            output_file = (
                image_dir /
                f"{safe_name}.json"
            )

            with open(
                output_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    result,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            summary.append({
                "file": image_path.name,
                "model": model,
                "status": "OK",
                "time_sec": result.get("_time_sec"),
                "client": result.get("client", ""),
                "brand": result.get("brand", ""),
                "category": result.get("category", ""),
                "confidence": result.get("confidence", ""),
                "text": result.get("text", []),
                "description": result.get(
                    "description", ""
                ),
            })

            print(
                "OK |",
                "client=",
                result.get("client", ""),
                "| brand=",
                result.get("brand", ""),
                "| confidence=",
                result.get("confidence", ""),
                "| time=",
                result.get("_time_sec"),
                "sec"
            )

        except Exception as e:

            print(
                "ERROR:",
                model,
                e
            )

            summary.append({
                "file": image_path.name,
                "model": model,
                "status": "ERROR",
                "error": str(e),
            })

    total_time = round(
        time.time() - model_start,
        2
    )

    print()
    print(
        "MODEL FINISHED:",
        model
    )

    print(
        "TOTAL TIME:",
        total_time,
        "sec"
    )

    print(
        "AVERAGE:",
        round(
            total_time / len(files),
            2
        ),
        "sec/photo"
    )

    return total_time

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    files = sorted(
        list(INPUT_DIR.glob("*.JPG"))
        + list(INPUT_DIR.glob("*.jpg"))
        + list(INPUT_DIR.glob("*.PNG"))
        + list(INPUT_DIR.glob("*.png"))
    )

    files = files[:LIMIT]

    print("=" * 70)
    print("BANNER MODEL COMPARE v05")
    print("=" * 70)
    print()

    print("FILES:", len(files))
    print()
    print("PASS 1:", MODELS[0])
    print("PASS 2:", MODELS[1])
    print()
    print("IMAGE RESIZE: DISABLED")
    print("NUM_CTX:", NUM_CTX)
    print("TEMPERATURE:", TEMPERATURE)
    print()
    print("MODELS ARE PROCESSED SEQUENTIALLY")
    print()

    summary = []

    total_start = time.time()

    times = {}

    # ==========================================================
    # PASS 1
    # ==========================================================

    times[MODELS[0]] = process_model(
        MODELS[0],
        files,
        summary
    )

    print()
    print("FIRST MODEL COMPLETE.")
    print("SECOND MODEL STARTING...")
    print()

    # ==========================================================
    # PASS 2
    # ==========================================================

    times[MODELS[1]] = process_model(
        MODELS[1],
        files,
        summary
    )

    total_time = round(
        time.time() - total_start,
        2
    )

    # ==========================================================
    # SAVE SUMMARY
    # ==========================================================

    with open(
        OUTPUT_DIR / "summary.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2
        )

    timing = {
        "files": len(files),
        "models": MODELS,
        "sequential": True,
        "image_resize": False,
        "num_ctx": NUM_CTX,
        "temperature": TEMPERATURE,
        "model_times": times,
        "total_time_sec": total_time,
        "average_total_sec_per_photo_pair":
            round(
                total_time / len(files),
                2
            ),
    }

    with open(
        OUTPUT_DIR / "timing.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            timing,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print()

    print("FILES:", len(files))

    for model, seconds in times.items():

        print(
            model,
            ":",
            seconds,
            "sec"
        )

        print(
            "  average:",
            round(
                seconds / len(files),
                2
            ),
            "sec/photo"
        )

    print()
    print(
        "TOTAL:",
        total_time,
        "sec"
    )

    print()
    print(
        "RESULT:",
        OUTPUT_DIR
    )

if __name__ == "__main__":
    main()
PY

chmod +x scripts/banner_model_compare_v05.py
```

Запуск:

```bash
uv run python scripts/banner_model_compare_v05.py
```

Получим:

```text
data/banner_database/model_compare_v05/
├── summary.json
├── timing.json
├── Ашхабадский_01/
│   ├── qwen3-vl_2b-instruct.json
│   └── qwen2.5vl_3b.json
├── Ашхабадский_02/
│   ├── qwen3-vl_2b-instruct.json
│   └── qwen2.5vl_3b.json
└── ...
```

И главное — в консоли будет отдельно:

```text
MODEL FINISHED: qwen3-vl:2b-instruct
TOTAL TIME: ...
AVERAGE: ... sec/photo

FIRST MODEL COMPLETE.
SECOND MODEL STARTING...

MODEL FINISHED: qwen2.5vl:3b
TOTAL TIME: ...
AVERAGE: ... sec/photo
```

Так мы не только сравним качество с уже имеющимся **Qwen3-VL 4B**, но и увидим реальную разницу по скорости между **2B и 2.5-VL 3B**.

---

### 👤 **User** — 2026-08-16 12:15:56

как выгрузить Ollama из памяти, очитсить vram

---

### 🤖 **Assistant** — 2026-08-16 12:15:57

Да. Для Ollama проще всего принудительно выгрузить модели из VRAM.

### 1. Посмотреть, что сейчас загружено

```bash
ollama ps
```

### 2. Выгрузить конкретную модель

Например:

```bash
ollama stop qwen3-vl:4b-instruct
```

или:

```bash
ollama stop qwen3-vl:2b-instruct
```

Проверка:

```bash
ollama ps
```

Должно стать пусто.

### 3. Если нужно полностью очистить Ollama

Можно остановить сервис:

```bash
sudo systemctl stop ollama
```

После этого проверить VRAM:

```bash
nvidia-smi
```

Если Ollama действительно держал GPU, память должна освободиться.

Запустить обратно:

```bash
sudo systemctl start ollama
```

### Для нашего теста я бы сделал так

Перед переключением с одной модели на другую:

```bash
ollama ps
ollama stop qwen3-vl:2b-instruct
nvidia-smi
```

Потом запускаем:

```bash
ollama run qwen2.5vl:3b
```

Или вообще **не надо вручную запускать модель** — наш Python-скрипт сам загрузит её через API.

**Важно:** `ollama stop` выгружает модель из памяти, но не удаляет её с диска. `ollama rm` нам сейчас **не нужен**.

---

### 👤 **User** — 2026-08-16 12:34:09

OK | client= Единая Россия | brand= Дмитрий Сизякин | confidence= 95 | time= 9.93 sec
qwen3-vl:2b-instruct:   2%|▍                   | 1/50 [00:09<08:06,  9.93s/img]
Ашхабадский_01.JPG
OK | client=  | brand=  | confidence=  | time= 107.56 sec
qwen3-vl:2b-instruct:   4%|▊                   | 2/50 [01:57<53:53, 67.37s/img]
Ашхабадский_02.JPG
OK | client= Российская Федерация | brand= Дмитрий Сизякин | confidence= 95 | time= 8.07 sec
qwen3-vl:2b-instruct:   6%|█▏                  | 3/50 [02:05<31:34, 40.30s/img]
Ашхабадский_03.JPG
OK | client=  | brand=  | confidence=  | time= 109.02 sec
qwen3-vl:2b-instruct:   8%|█▌                  | 4/50 [03:54<51:42, 67.44s/img]
Ашхабадский_04.JPG
OK | client=  | brand=  | confidence=  | time= 8.69 sec
qwen3-vl:2b-instruct:  10%|██                  | 5/50 [04:03<34:41, 46.26s/img]
Ашхабадский_05.JPG
OK | client=  | brand=  | confidence=  | time= 9.3 sec
qwen3-vl:2b-instruct:  12%|██▍                 | 6/50 [04:12<24:42, 33.70s/img]
Ашхабадский_06.JPG
OK | client=  | brand=  | confidence=  | time= 110.97 sec
qwen3-vl:2b-instruct:  14%|██▊                 | 7/50 [06:03<42:15, 58.97s/img]
Ашхабадский_07.JPG 

медленно и нерезультативно

---

### 🤖 **Assistant** — 2026-08-16 12:34:09

Да. По этому результату **Qwen3-VL 2B для нашей задачи выглядит неудачно**.

Особенно показательно:

- хорошие кадры: **8–10 сек**;
- некоторые кадры: **107–111 сек**;
- часть кадров вообще возвращает пустой результат;
- там, где баннер очевиден, иногда определяет его хорошо (`Единая Россия / Дмитрий Сизякин`);
- среднее время из-за отдельных кадров становится неприемлемым.

Это как раз тот случай, когда **меньшая модель не даёт нам нужной экономии**.

### Я бы остановил этот прогон

Нажмите:

```bash
Ctrl+C
```

Результаты уже сохранены по мере обработки, поэтому первые фотографии не потеряются.

Потом:

```bash
ollama stop qwen3-vl:2b-instruct
```

И проверяем:

```bash
ollama ps
nvidia-smi
```

### Следующий тест — Qwen2.5-VL 3B

Вот он сейчас гораздо интереснее. У него 3.2 GB размер модели против 1.9 GB у 2B, но **качество vision может оказаться существенно лучше**, а главное — посмотрим, исчезнут ли эти странные скачки 8 → 110 секунд.

Запускаем наш последовательный тест именно для:

```text
Qwen2.5-VL 3B
50 фото
исходный размер
num_ctx=16384
temperature=0
```

Но я бы **не прогонял сразу все 50**. Сначала сделаем контрольные **10 фотографий**, чтобы не тратить 20–30 минут на заведомо плохой вариант.

Можно прямо сейчас остановить 2B и я дам короткий `v06`, который прогонит **10 тех же первых фотографий только Qwen2.5-VL 3B** и сразу покажет среднее время и качество.

---

### 👤 **User** — 2026-08-16 12:34:39

давай

---

### 🤖 **Assistant** — 2026-08-16 12:34:40

Да. Сделаем **контрольный прогон 10 фотографий только Qwen2.5-VL 3B**. Фото не уменьшаем, параметры те же.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/banner_qwen25vl_test_v01.py <<'PY'
#!/usr/bin/env python3

import base64
import json
import time
from pathlib import Path

import requests

INPUT_DIR = Path("data/input/test")
OUTPUT_DIR = Path("data/banner_database/qwen25vl_test_v01")

MODEL = "qwen2.5vl:3b"

OLLAMA_URL = "http://localhost:11434/api/chat"

LIMIT = 10
NUM_CTX = 16384
TEMPERATURE = 0

PROMPT = """
Ты анализируешь фотографию с улицы.

Найди рекламный баннер, если он присутствует.
Нужно максимально подробно описать именно баннер.

Верни строго JSON:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "confidence": 0
}

client:
Компания, организация, партия или заказчик рекламы.

brand:
Торговая марка, имя кандидата или бренд.

category:
Категория рекламы: продукты, банк, букмекер,
выборы, политика, строительство, магазин и т.д.

text:
ВСЕ читаемые надписи на баннере.
Особенно важны названия, имена, даты, телефоны,
цены, сайты и лозунги.

colors:
Основные цвета баннера.

objects:
Главные изображения и объекты.

description:
Подробно опиши внешний вид баннера,
изображения, логотипы, расположение текста
и цветовую схему.

confidence:
Уверенность от 0 до 100.

Если баннера нет или его невозможно разобрать,
верни пустые поля.

Не придумывай информацию.
"""

def image64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def ask(path):

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT,
                "images": [image64(path)],
            }
        ],
        "stream": False,
        "options": {
            "num_ctx": NUM_CTX,
            "temperature": TEMPERATURE,
        },
    }

    started = time.time()

    r = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=900,
    )

    elapsed = time.time() - started

    if r.status_code != 200:
        raise RuntimeError(r.text)

    data = r.json()

    answer = data["message"]["content"]

    try:
        result = json.loads(answer)
    except Exception:

        cleaned = answer.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace(
                "```json", "", 1
            )
            cleaned = cleaned.replace(
                "```", ""
            ).strip()

        try:
            result = json.loads(cleaned)
        except Exception:
            result = {
                "raw_answer": answer
            }

    result["_time_sec"] = round(elapsed, 2)

    return result

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    files = sorted(
        list(INPUT_DIR.glob("*.JPG"))
        + list(INPUT_DIR.glob("*.jpg"))
        + list(INPUT_DIR.glob("*.PNG"))
        + list(INPUT_DIR.glob("*.png"))
    )[:LIMIT]

    print("=" * 70)
    print("QWEN2.5-VL 3B TEST")
    print("=" * 70)
    print()
    print("MODEL:", MODEL)
    print("FILES:", len(files))
    print("IMAGE RESIZE: DISABLED")
    print("NUM_CTX:", NUM_CTX)
    print("TEMPERATURE:", TEMPERATURE)
    print()

    total_start = time.time()
    results = []

    for i, path in enumerate(files, 1):

        print()
        print(
            f"[{i}/{len(files)}]",
            path.name
        )

        try:

            result = ask(path)

            output = (
                OUTPUT_DIR /
                f"{path.stem}.json"
            )

            with open(
                output,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    result,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            t = result.get(
                "_time_sec",
                0
            )

            client = result.get(
                "client", ""
            )

            brand = result.get(
                "brand", ""
            )

            confidence = result.get(
                "confidence", ""
            )

            print(
                "OK |",
                "client=",
                client,
                "| brand=",
                brand,
                "| confidence=",
                confidence,
                "| time=",
                t,
                "sec"
            )

            results.append({
                "file": path.name,
                "time_sec": t,
                "client": client,
                "brand": brand,
                "confidence": confidence,
                "category": result.get(
                    "category", ""
                ),
                "text": result.get(
                    "text", []
                ),
            })

        except Exception as e:

            print(
                "ERROR:",
                e
            )

            results.append({
                "file": path.name,
                "error": str(e),
            })

    total = round(
        time.time() - total_start,
        2
    )

    with open(
        OUTPUT_DIR / "summary.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    successful = [
        x for x in results
        if "time_sec" in x
    ]

    if successful:

        avg = round(
            sum(
                x["time_sec"]
                for x in successful
            ) / len(successful),
            2
        )

        print()
        print("=" * 70)
        print("RESULT")
        print("=" * 70)
        print()
        print(
            "SUCCESS:",
            len(successful),
            "/",
            len(files)
        )
        print(
            "TOTAL:",
            total,
            "sec"
        )
        print(
            "AVERAGE:",
            avg,
            "sec/photo"
        )

    print()
    print(
        "RESULT DIR:",
        OUTPUT_DIR
    )

if __name__ == "__main__":
    main()
PY

chmod +x scripts/banner_qwen25vl_test_v01.py
```

Перед запуском убедимся, что 2B выгружена:

```bash
ollama stop qwen3-vl:2b-instruct
nvidia-smi
```

Затем:

```bash
uv run python scripts/banner_qwen25vl_test_v01.py
```

### На что смотрим

Для 3B я бы считал результат хорошим, если она даст примерно:

**до 15–20 сек/фото** и при этом нормально определяет баннеры.

Если опять увидим:

```text
9 sec
110 sec
8 sec
105 sec
```

— это уже сигнал, что **проблема не столько в размере модели, сколько в обработке больших исходных фотографий / vision tokenization**.

А если 3B стабильно выдаст, например, **10–15 секунд и хорошие описания**, тогда это практически идеальный кандидат для нашей базы баннеров.

---

### 👤 **User** — 2026-08-16 12:35:57

авай 4B сразу прогоним на этих 10

---

### 🤖 **Assistant** — 2026-08-16 12:35:57

Да, это правильнее: **те же 10 фотографий, те же параметры, но Qwen3-VL 4B**. Тогда сравнение 2B / 3B / 4B будет на абсолютно одинаковом наборе.

Сделаем отдельный короткий тест, чтобы не затрагивать результаты предыдущего большого прогона.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/banner_qwen4b_test_v01.py <<'PY'
#!/usr/bin/env python3

import base64
import json
import time
from pathlib import Path

import requests

INPUT_DIR = Path("data/input/test")
OUTPUT_DIR = Path("data/banner_database/qwen4b_test_v01")

MODEL = "qwen3-vl:4b-instruct"

OLLAMA_URL = "http://localhost:11434/api/chat"

LIMIT = 10
NUM_CTX = 16384
TEMPERATURE = 0

PROMPT = """
Ты анализируешь фотографию с улицы.

Найди рекламный баннер, если он присутствует.
Нужно максимально подробно описать именно баннер.

Верни строго JSON:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "confidence": 0
}

client:
Компания, организация, партия или заказчик рекламы.

brand:
Торговая марка, имя кандидата или бренд.

category:
Категория рекламы: продукты, банк, букмекер,
выборы, политика, строительство, магазин и т.д.

text:
ВСЕ читаемые надписи на баннере.
Особенно важны названия, имена, даты, телефоны,
цены, сайты и лозунги.

colors:
Основные цвета баннера.

objects:
Главные изображения и объекты.

description:
Подробно опиши внешний вид баннера,
изображения, логотипы, расположение текста
и цветовую схему.

confidence:
Уверенность от 0 до 100.

Если баннера нет или его невозможно разобрать,
верни пустые поля.

Не придумывай информацию.
"""

def image64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def ask(path):

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT,
                "images": [image64(path)],
            }
        ],
        "stream": False,
        "options": {
            "num_ctx": NUM_CTX,
            "temperature": TEMPERATURE,
        },
    }

    started = time.time()

    r = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=900,
    )

    elapsed = time.time() - started

    if r.status_code != 200:
        raise RuntimeError(r.text)

    data = r.json()

    answer = data["message"]["content"]

    try:
        result = json.loads(answer)
    except Exception:

        cleaned = answer.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace(
                "```json", "", 1
            )
            cleaned = cleaned.replace(
                "```", ""
            ).strip()

        try:
            result = json.loads(cleaned)
        except Exception:
            result = {
                "raw_answer": answer
            }

    result["_time_sec"] = round(elapsed, 2)

    return result

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    files = sorted(
        list(INPUT_DIR.glob("*.JPG"))
        + list(INPUT_DIR.glob("*.jpg"))
        + list(INPUT_DIR.glob("*.PNG"))
        + list(INPUT_DIR.glob("*.png"))
    )[:LIMIT]

    print("=" * 70)
    print("QWEN3-VL 4B TEST")
    print("=" * 70)
    print()
    print("MODEL:", MODEL)
    print("FILES:", len(files))
    print("IMAGE RESIZE: DISABLED")
    print("NUM_CTX:", NUM_CTX)
    print("TEMPERATURE:", TEMPERATURE)
    print()

    total_start = time.time()
    results = []

    for i, path in enumerate(files, 1):

        print()
        print(
            f"[{i}/{len(files)}]",
            path.name
        )

        try:

            result = ask(path)

            output = (
                OUTPUT_DIR /
                f"{path.stem}.json"
            )

            with open(
                output,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    result,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            t = result.get(
                "_time_sec",
                0
            )

            client = result.get(
                "client", ""
            )

            brand = result.get(
                "brand", ""
            )

            confidence = result.get(
                "confidence", ""
            )

            print(
                "OK |",
                "client=",
                client,
                "| brand=",
                brand,
                "| confidence=",
                confidence,
                "| time=",
                t,
                "sec"
            )

            results.append({
                "file": path.name,
                "time_sec": t,
                "client": client,
                "brand": brand,
                "confidence": confidence,
                "category": result.get(
                    "category", ""
                ),
                "text": result.get(
                    "text", []
                ),
            })

        except Exception as e:

            print(
                "ERROR:",
                e
            )

            results.append({
                "file": path.name,
                "error": str(e),
            })

    total = round(
        time.time() - total_start,
        2
    )

    with open(
        OUTPUT_DIR / "summary.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    successful = [
        x for x in results
        if "time_sec" in x
    ]

    print()
    print("=" * 70)
    print("RESULT")
    print("=" * 70)
    print()
    print(
        "SUCCESS:",
        len(successful),
        "/",
        len(files)
    )
    print(
        "TOTAL:",
        total,
        "sec"
    )

    if successful:
        avg = round(
            sum(
                x["time_sec"]
                for x in successful
            ) / len(successful),
            2
        )

        print(
            "AVERAGE:",
            avg,
            "sec/photo"
        )

    print()
    print(
        "RESULT DIR:",
        OUTPUT_DIR
    )

if __name__ == "__main__":
    main()
PY

chmod +x scripts/banner_qwen4b_test_v01.py
```

Перед запуском лучше очистить VRAM от 3B:

```bash
ollama stop qwen2.5vl:3b
nvidia-smi
```

Затем:

```bash
uv run python scripts/banner_qwen4b_test_v01.py
```

### В итоге получим честную тройку

На **одних и тех же 10 фото**:

| Модель | Что сравниваем |
|---|---|
| Qwen3-VL 2B | уже запускаем |
| Qwen2.5-VL 3B | тестируем |
| Qwen3-VL 4B | этот тест |

И особенно посмотрим на **Ашхабадский_01.JPG** — у 2B там был очень показательный провал в **107.56 сек** и пустой результат. Если 4B обработает этот же кадр нормально за ~10–15 секунд, это будет сильный аргумент в пользу 4B.

---

### 👤 **User** — 2026-08-16 12:39:47

остаемся на 4B , другие несостоятельны QWEN2.5-VL 3B TEST
======================================================================

MODEL: qwen2.5vl:3b
FILES: 10
IMAGE RESIZE: DISABLED
NUM_CTX: 16384
TEMPERATURE: 0

[1/10] Screenshot from 2026-08-16 00-38-11.png
OK | client= Единая Россия | brand= Дмитрий Сизякин | confidence= 90 | time= 12.34 sec

[2/10] Ашхабадский_01.JPG
OK | client=  | brand=  | confidence=  | time= 8.32 sec

[3/10] Ашхабадский_02.JPG
OK | client=  | brand=  | confidence=  | time= 7.91 sec

[4/10] Ашхабадский_03.JPG
OK | client=  | brand=  | confidence=  | time= 8.1 sec

[5/10] Ашхабадский_04.JPG
OK | client=  | brand=  | confidence=  | time= 8.02 sec

[6/10] Ашхабадский_05.JPG
OK | client=  | brand=  | confidence=  | time= 8.55 sec

[7/10] Ашхабадский_06.JPG
OK | client=  | brand=  | confidence=  | time= 8.24 sec

[8/10] Ашхабадский_07.JPG
OK | client=  | brand=  | confidence=  | time= 8.16 sec

[9/10] Ашхабадский_08.JPG
OK | client=  | brand=  | confidence=  | time= 8.02 sec

[10/10] Ашхабадский_09.JPG
OK | client=  | brand=  | confidence=  | time= 8.23 sec

======================================================================
RESULT
======================================================================

SUCCESS: 10 / 10
TOTAL: 86.01 sec
AVERAGE: 8.59 sec/photo

RESULT DIR: data/banner_database/qwen25vl_test_v01
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sudo systemctl stop ollama
[sudo] password for alexice: 
ЙSorry, try again.
[sudo] password for alexice: 
QazSorry, try again.
[sudo] password for alexice: 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ Qazwsxedcasd_1213
Qazwsxedcasd_1213: command not found
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sudo systemctl start ollama
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/banner_qwen4b_test_v01.py <<'PY'
#!/usr/bin/env python3

import base64
import json
import time
from pathlib import Path

import requests

INPUT_DIR = Path("data/input/test")
OUTPUT_DIR = Path("data/banner_database/qwen4b_test_v01")

MODEL = "qwen3-vl:4b-instruct"

OLLAMA_URL = "http://localhost:11434/api/chat"

LIMIT = 10
NUM_CTX = 16384
chmod +x scripts/banner_qwen4b_test_v01.py)ecode().
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/banner_qwen4b_test_v01.py
======================================================================
QWEN3-VL 4B TEST
======================================================================

MODEL: qwen3-vl:4b-instruct
FILES: 10
IMAGE RESIZE: DISABLED
NUM_CTX: 16384
TEMPERATURE: 0

[1/10] Screenshot from 2026-08-16 00-38-11.png
OK | client= Единая Россия | brand= Дмитрий Сизякин | confidence= 95 | time= 16.5 sec

[2/10] Ашхабадский_01.JPG
OK | client= Единая Россия | brand= Дмитрий Сизякин | confidence= 95 | time= 10.4 sec

[3/10] Ашхабадский_02.JPG
OK | client= Единая Россия | brand= Дмитрий Сизякин | confidence= 95 | time= 10.01 sec

[4/10] Ашхабадский_03.JPG
OK | client= Сила России | brand= Сила России | confidence= 95 | time= 9.56 sec

[5/10] Ашхабадский_04.JPG
OK | client= Яндекс | brand= Яндекс Еда | confidence= 95 | time= 10.15 sec

[6/10] Ашхабадский_05.JPG
OK | client= АЛЬБИОН-ТУР | brand= АЛЬБИОН-ТУР | confidence= 95 | time= 10.66 sec

---

### 🤖 **Assistant** — 2026-08-16 12:39:48

Да. **Фиксируем Qwen3-VL 4B как рабочую модель.** Результат сравнения это подтверждает очень хорошо.

### Сравнение на одинаковых 10 фото

| Модель | Скорость | Распознавание |
|---|---:|---|
| **Qwen3-VL 4B** | ~10–16 сек/фото | **хорошее, подробное** |
| Qwen2.5-VL 3B | ~8 сек/фото | практически не распознаёт |
| Qwen3-VL 2B | 8–110 сек/фото | нестабильно + пропуски |

Причём разница между 3B и 4B здесь принципиальная:

**Qwen2.5-VL 3B**

```text
Ашхабадский_01 → пусто
Ашхабадский_02 → пусто
Ашхабадский_03 → пусто
...
```

А 4B:

```text
Ашхабадский_01 → Единая Россия / Дмитрий Сизякин
Ашхабадский_02 → Единая Россия / Дмитрий Сизякин
Ашхабадский_03 → Сила России
Ашхабадский_04 → Яндекс / Яндекс Еда
Ашхабадский_05 → АЛЬБИОН-ТУР
```

Это именно то, что нам нужно от модели.

### И ещё важный момент

**Не надо больше пытаться экономить на модели.**

Для нашего проекта 4B — очень разумный компромисс:

```text
DINOv2 / fingerprint
        ↓
быстрое определение адреса
        ↓
Qwen3-VL 4B
        ↓
описание баннера
        ↓
SQLite
```

И Qwen **не должен заниматься поиском всех баннеров на 200–300 фотографиях с нуля**. Это будет дорого по времени.

Правильная архитектура:

```text
200–300 фото
       │
       ▼
DINOv2 / v33
       │
       ├── адрес определён
       │
       ▼
переименование + сортировка
       │
       ▼
Qwen3-VL 4B
       │
       ▼
описание баннера
       │
       ▼
banner.db
```

То есть Qwen становится **вторым уровнем**, а не основным распознавателем.

И это хорошо ложится на нашу будущую задачу:

> **«Найди три фотографии по таким-то адресам, одна должна быть с выборами»**

Тогда SQL/поиск сначала отбирает фотографии по адресам, а семантический поиск по описаниям выбирает нужный тип баннера.

**4B оставляем. Другие модели отбрасываем.**

---

### 👤 **User** — 2026-08-16 12:45:55

в приницпе схема будет выглядеть вот так:
1) Загрузка фото на сервер в определенный каталог
2) в веб-интерфейсе проверяется , что папка доступна, нажимается кнопка старта 
3) если не происходит ручной запуск - в определенное время стартует автоматическое распознавание.
4) сначала фотографии подписываются и раскладываются по папкам в результативной папке
5) фиксируется отчет о проделанной работе и кол-ве
6) передается команда для прогона модели с целью описания по результативным папкам
7) результаты сохраняются в базу
8) фиксируется отчет о найденных клиентах и не описанных фото
9) на этом процесс завершен, модель ollama выгружается из памяти
10) при необходимости менеджер производит поиск на основании текстового запроса или изображения - результат выводится, сохраняется куда-надо, история поиска сохраняется

---

### 🤖 **Assistant** — 2026-08-16 12:45:56

Да. Это уже выглядит как **цельная рабочая архитектура**, а не набор отдельных скриптов. И я бы именно так её и фиксировал.

### Итоговая схема LORA / Banner Search

```text
                 ┌──────────────────────────┐
                 │       ФОТОСЕРВЕР         │
                 │  входящий каталог / день  │
                 └────────────┬─────────────┘
                              │
                              ▼
                 ┌──────────────────────────┐
                 │      WEB-ИНТЕРФЕЙС       │
                 │                          │
                 │  • папка доступна?       │
                 │  • ручной старт          │
                 │  • расписание            │
                 │  • статус процесса       │
                 └────────────┬─────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │       ЭТАП 1 - DINOv2         │
              │                               │
              │  распознавание адреса         │
              │  fingerprint v33              │
              │  сортировка                   │
              │  переименование               │
              └──────────────┬────────────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │    RESULT / 2026-08-16   │
                 │                          │
                 │  78/Комарова13_01.JPG   │
                 │  79/Стачки_41_03.JPG    │
                 │  80/...                  │
                 │  ...                     │
                 └────────────┬─────────────┘
                              │
                              ▼
                 ┌──────────────────────────┐
                 │       ОТЧЕТ №1           │
                 │                          │
                 │  всего фото: 257        │
                 │  распознано: 248        │
                 │  не распознано: 9       │
                 │  по адресам: ...        │
                 └────────────┬─────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │       ЭТАП 2 - QWEN 4B        │
              │                               │
              │  описание баннеров            │
              │  клиент                        │
              │  бренд                         │
              │  текст                         │
              │  даты                          │
              │  цвета                         │
              │  объекты                       │
              │  категория                     │
              │  подробное описание            │
              └──────────────┬────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   banner.db     │
                    │                 │
                    │ фото            │
                    │ адрес           │
                    │ клиент          │
                    │ бренд           │
                    │ текст           │
                    │ категория       │
                    │ цвета           │
                    │ описание        │
                    │ дата обработки  │
                    └────────┬────────┘
                             │
                             ▼
                 ┌──────────────────────────┐
                 │       ОТЧЕТ №2           │
                 │                          │
                 │ клиентов найдено: 34    │
                 │ баннеров описано: 231   │
                 │ без описания: 17        │
                 └────────────┬─────────────┘
                              │
                              ▼
                    QWEN выгружается
                       из VRAM
                              │
                              ▼
                    ┌─────────────────┐
                    │    ГОТОВО       │
                    └─────────────────┘
```

### А затем начинается совершенно другой режим - работа менеджера

Тут **не надо заново запускать весь pipeline**.

Менеджер пишет:

> Найди макеты Сбера.

Поиск идёт по базе:

```text
SBER
Сбер
Сбербанк
СБЕР
...
```

и возвращаются фотографии.

Или:

> Найди фотографии по адресам Комарова 13 и Стачки 41, где есть выборы.

Тогда движок делает комбинацию:

```text
адрес
   +
категория = выборы
   +
текст/описание
```

И выдаёт нужные фотографии.

---

### Самое интересное - поиск по изображению

Менеджер загружает макет:

```text
        МАКЕТ
          │
          ▼
     Qwen3-VL 4B
          │
          ▼
 "Единая Россия,
 Дмитрий Сизякин,
 выборы,
 голубой/белый,
 фотография мужчины..."
          │
          ▼
       banner.db
          │
          ▼
   похожие фотографии
          │
          ▼
     результат
```

То есть **одна и та же модель используется для индексации и для понимания поискового изображения**. Это очень удобно.

---

## Я бы добавил ещё один обязательный элемент

**Историю всех запусков.**

Например:

```text
jobs
────────────────────────────────────────
ID       Дата         Фото   OK   ERROR
1042     16.08.2026   257    248   9
1041     15.08.2026   312    307   5
1040     14.08.2026   289    281   8
```

И для каждого запуска:

```text
START
END
STATUS
TOTAL_FILES
RECOGNIZED
UNRECOGNIZED
BANNERS_DESCRIBED
BANNERS_FAILED
MODEL
MODEL_TIME
```

Это потом очень пригодится для контроля работы системы.

---

## И ещё важнее - разделить физические каталоги

Я бы сразу заложил:

```text
data/
│
├── incoming/
│      └── 2026-08-16/
│
├── results/
│      └── 2026-08-16/
│            ├── 78/
│            ├── 79/
│            ├── 80/
│            └── ...
│
├── reports/
│      └── 2026-08-16/
│
├── banner_database/
│      └── banner.db
│
└── search/
       └── ...
```

Тогда **оригиналы никогда не трогаем**.

---

### И главное

На этом этапе я бы **не стал больше экспериментировать с моделями**.

У нас уже есть рабочая связка:

**DINOv2 v33 → адрес → Qwen3-VL 4B → описание → SQLite → семантический поиск.**

Теперь гораздо полезнее перейти от экспериментов к **сборке единого production-пайплайна и веб-интерфейса**.

---

### 👤 **User** — 2026-08-16 12:47:58

Да. все ОК -фиксируем, что этап бекэнда практически завершен. Проект "Альбион: Фотобаза. Офис"

---

### 🤖 **Assistant** — 2026-08-16 12:48:01

Да. **Фиксируем.**

# «Альбион: Фотобаза. Офис»

### Статус проекта
**Backend практически завершён.**

Зафиксирована рабочая архитектура:

**DINOv2 v33 → распознавание адреса → сортировка/переименование → отчёт → Qwen3-VL 4B → описание → SQLite → поиск → история.**

Рабочей VLM окончательно выбираем **Qwen3-VL 4B**. Меньшие модели для основной задачи отбрасываем.

### Следующий этап

Теперь **не трогаем алгоритм распознавания и модельную часть без необходимости**.

Переходим к production-обвязке:

1. Веб-интерфейс.
2. Проверка входной папки.
3. Ручной запуск.
4. Автозапуск по расписанию.
5. Мониторинг выполнения.
6. Отчёты по каждому запуску.
7. Управление базой.
8. Поиск по тексту.
9. Поиск по изображению.
10. Выбор и сохранение найденных фотографий.
11. История поисковых запросов.
12. Корректная выгрузка Ollama после обработки.

**Текущий backend считаем базовой стабильной версией проекта.**

---

### 👤 **User** — 2026-08-16 12:48:37

надо почистить папку проекта от output и кэша

---

### 🤖 **Assistant** — 2026-08-16 12:48:38

> **Inspecting Project Outputs And Caches**
>
>
> **Inspected project outputs and caches**
>
> 
>
> Worked for 4s

Да. Но удалять будем **только мусор**, не трогая `data/input`, `data/fingerprints`, `data/banner_database`, `scripts` и `.venv`.

Я не могу напрямую попасть в твой `/home/alexice/...` из текущего окружения, поэтому сначала выполни **безопасную проверку**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== OUTPUT ==="
du -sh output 2>/dev/null || true

echo
echo "=== CACHE / PYTHON CACHE ==="
find . -type d \( \
  -name "__pycache__" \
  -o -name ".pytest_cache" \
  -o -name ".cache" \
  -o -name "cache" \
\) -prune -print

echo
echo "=== TOP LEVEL ==="
du -sh -- * .[^.]* 2>/dev/null | sort -h
```

Если всё выглядит ожидаемо, для **очистки именно мусора**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output

find . -type d \( \
  -name "__pycache__" \
  -o -name ".pytest_cache" \
  -o -name ".cache" \
  -o -name "cache" \
\) -prune -exec rm -rf {} +

echo
echo "=== AFTER CLEANUP ==="
du -sh .
du -sh -- * .[^.]* 2>/dev/null | sort -h
```

**`.venv` не удаляем** — это окружение проекта.

И отдельно: **`data/banner_database/banner.db` оставляем**, потому что это уже рабочая база «Альбион: Фотобаза. Офис», а не кэш.

---

### 👤 **User** — 2026-08-16 12:49:03

=== TOP LEVEL ===
4.0K	classify_final_test.py
4.0K	classify_test_results.py
4.0K	.gitignore
4.0K	pyproject.toml
4.0K	pyproject.toml.backup_before_transformers
4.0K	README.md
4.0K	sort_recognition_output.py
4.0K	upgrade_v31_fix.sh
12K	classify_test.sh
16K	classify_test.py
16K	classify_test_top1.sh
16K	upgrade_v3.sh
24K	upgrade_patch_tokens.sh
24K	upgrade_v31_final.sh
28K	scene_fingerprint.egg-info
28K	tools
32K	fix_v31_final.sh
32K	upgrade_v31.sh
88K	final_test_78_95_clean.json
240K	uv.lock
384K	app
536K	final_test_78_95.working.json
536K	test_78_95_results.json
600K	scripts
3.7G	output
6.3G	.venv
11G	data
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 12:49:04

Да, теперь картина ясная.

**3.7 GB `output` — главный мусор.** Его можно удалять целиком.

Остальное:

- `.venv` — **6.3 GB, НЕ трогаем**, это рабочее окружение.
- `data` — **11 GB, НЕ трогаем**: там fingerprints и `banner.db`.
- `scripts` — оставляем.
- `app` — оставляем.
- `scene_fingerprint.egg-info` — можно оставить, размер смешной.
- `*.json` в корне — это старые результаты тестов. Их можно удалить, **если они больше не нужны**.
- `upgrade_*.sh`, `classify_*.py/sh` — старые служебные скрипты; пока я бы **не удалял**, сначала сделаем архив/разберём.

### Сейчас предлагаю очистить только гарантированный мусор

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf output

find . -type d \( \
  -name "__pycache__" \
  -o -name ".pytest_cache" \
  -o -name ".cache" \
  -o -name "cache" \
\) -prune -exec rm -rf {} +

echo
echo "=== AFTER CLEANUP ==="
du -sh .
du -sh -- * .[^.]* 2>/dev/null | sort -h
```

После этого должно освободиться примерно **3.7 GB**.

### А вот эти JSON пока сохраним

```text
final_test_78_95_clean.json
final_test_78_95.working.json
test_78_95_results.json
```

Они маленькие, всего около **1.2 MB**, и могут пригодиться как исторические результаты.

После очистки можем отдельно сделать **«генеральную уборку» проекта** — убрать старые `upgrade_*`, `classify_*`, backup-файлы и временные тестовые скрипты, но сначала я бы зафиксировал текущую рабочую версию backend.

---

### 👤 **User** — 2026-08-16 12:49:22

нет ли в joutput нужных json?

---

### 🤖 **Assistant** — 2026-08-16 12:49:23

Да, **в `output` вполне могут быть нужные JSON** — особенно результаты последних тестов распознавания. Поэтому **целиком удалять `output` сейчас не стоит**.

Давай сначала посмотрим, что именно там занимает 3.7 GB, не удаляя ничего:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== OUTPUT STRUCTURE ==="
du -h --max-depth=2 output 2>/dev/null | sort -h | tail -50

echo
echo "=== JSON FILES ==="
find output -type f -name "*.json" -printf "%s %p\n" 2>/dev/null \
  | sort -nr \
  | head -50
```

И отдельно:

```bash
echo
echo "=== ALL OUTPUT TOP LEVEL ==="
find output -maxdepth 2 -type f | head -100
```

### Особенно нас интересуют

С учётом того, что мы только что закончили backend, я бы **точно не удалял без проверки**:

- результаты `recognize`;
- `margin_best.csv`;
- результаты v33;
- benchmark;
- JSON с ошибками/сопоставлениями;
- результаты последних тестов 78–95;
- результаты Banner Search;
- результаты сравнения моделей;
- всё, что относится к `banner_database`.

А вот большие промежуточные изображения, копии fingerprint-анализов и старые экспериментальные результаты, скорее всего, можно будет убрать.

**Пока ничего не удаляй.** Выполни три команды выше и пришли вывод — я разберу `output` и скажу **что оставить, что архивировать и что можно безопасно удалить**.

---

### 👤 **User** — 2026-08-16 12:49:40

=== OUTPUT STRUCTURE ===
8.0K	output/test_final_v33
12K	output/compare_sub
190M	output/subclusters/92_v33
193M	output/subclusters/87_v33
264M	output/subclusters/84_v33
273M	output/subclusters/89_v33
278M	output/subclusters/95_v33
284M	output/subclusters/94_v33
298M	output/subclusters/85_v33
997M	output/sequence_sub_v01
997M	output/sequence_sub_v01/sorted
997M	output/sequence_v38_1
997M	output/sequence_v38_1/sorted
1.8G	output/subclusters
3.7G	output

---

### 🤖 **Assistant** — 2026-08-16 12:49:40

Да — теперь видно, что **`output` почти целиком состоит из тяжёлых промежуточных изображений**, а не из критически важных JSON.

Особенно:

```text
1.8G  output/subclusters
997M  output/sequence_sub_v01
997M  output/sequence_v38_1
```

Это почти **3.8 GB**.

Но прежде чем удалять, давай найдём JSON внутри `output` и посмотрим, где они находятся:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== JSON ==="
find output -type f -name "*.json" -printf "%s %p\n" 2>/dev/null | sort -nr

echo
echo "=== CSV ==="
find output -type f -name "*.csv" -printf "%s %p\n" 2>/dev/null | sort -nr

echo
echo "=== OTHER FILES ==="
find output -type f \
  ! -name "*.json" \
  ! -name "*.csv" \
  -printf "%s %p\n" 2>/dev/null \
  | sort -nr | head -30
```

### Предварительно я уже вижу кандидатов на удаление

`sequence_v38_1` и `sequence_sub_v01` — это наши экспериментальные последовательности. Если мы их уже закончили и **не собираемся использовать результаты как эталон**, их можно будет удалить.

`subclusters/*_v33` — тоже выглядят как промежуточные визуальные материалы кластеризации. Они особенно тяжёлые: сотни мегабайт на адрес.

Но **не удаляем пока**.

Пришли вывод трёх блоков — после этого я дам одну команду вида:

```bash
rm -rf ...
```

которая удалит только ненужное и оставит все полезные результаты.

---

### 👤 **User** — 2026-08-16 12:49:51

давай все jpg зачистим

---

### 🤖 **Assistant** — 2026-08-16 12:49:51

Да. Если речь именно о **всех JPG внутри `output`**, это безопаснее, чем удалять весь `output`: JSON/CSV и другие результаты останутся.

Сначала можно посмотреть количество:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find output -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) | wc -l
```

Если удаляем — команда:

```bash
find output -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) -delete
```

После этого:

```bash
du -sh output
```

И проверка, что картинок не осталось:

```bash
find output -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) | wc -l
```

Должно показать:

```text
0
```

**JSON, CSV, `.npy`, `.index` и остальные файлы не затрагиваются.**

---

### 👤 **User** — 2026-08-16 12:50:18

946  - остальное не трогаем

---

### 🤖 **Assistant** — 2026-08-16 12:50:18

Да, фиксируем: **946 JPG удаляем, остальное в `output` не трогаем.**

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find output -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) -delete

echo "Осталось JPG:"
find output -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) | wc -l

echo "Размер output:"
du -sh output
```

Это удалит только эти **946 изображений**. JSON, CSV и прочие результаты останутся.

---

### 👤 **User** — 2026-08-16 12:50:54

смотрим data

---

### 🤖 **Assistant** — 2026-08-16 12:50:54

Да. **`data` сейчас не удаляем вообще** - сначала разберём содержимое.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== DATA STRUCTURE ==="
du -h --max-depth=2 data 2>/dev/null | sort -h
```

Потом:

```bash
echo
echo "=== TOP-LEVEL DATA ==="
find data -maxdepth 2 -type d -print | sort
```

И отдельно самые крупные файлы:

```bash
echo
echo "=== BIGGEST FILES ==="
find data -type f -printf "%s %p\n" 2>/dev/null \
  | sort -nr \
  | head -50
```

Особенно нас интересует:

```text
data/input
data/fingerprints
data/banner_database
data/output
```

**Ничего пока не удаляй.** По выводу разберём, что является рабочими данными проекта «Альбион: Фотобаза. Офис», а что осталось от экспериментов.

---

### 👤 **User** — 2026-08-16 12:51:10

4.0K	data/fingerprints_clean
4.0K	data/output/banner_search_v03_2
8.0K	data/banner_database/model_compare_v03
24K	data/banner_database/model_compare_v02
28K	data/banner_database/qwen4b_test_v01
48K	data/banner_database/qwen25vl_test_v01
68K	data/fingerprints_sub_exp/87_v33_sub_2
68K	data/fingerprints_sub_exp/94_v33_sub_3
72K	data/banner_database/model_compare_v04
132K	data/fingerprints_sub_exp/95_v33_sub_3
160K	data/fingerprints_sub_exp/89_v33_sub_1
164K	data/output/benchmark_sub_exp
164K	data/output/benchmark_v1
176K	data/fingerprints_sub_exp/92_v33_sub_1
204K	data/banner_database/model_compare
224K	data/fingerprints_sub_exp/84_v33_sub_2
236K	data/banner_database/model_compare_v05
244K	data/fingerprints/90_v33
296K	data/fingerprints_sub_exp/89_v33_sub_3
316K	data/fingerprints_sub_exp/85_v33_sub_2
328K	data/fingerprints_sub_exp/94_v33_sub_1
340K	data/fingerprints_sub_exp/89_v33_sub_2
352K	data/fingerprints_sub_exp/85_v33_sub_1
368K	data/fingerprints_sub_exp/95_v33_sub_1
400K	data/fingerprints_sub_exp/94_v33_sub_2
404K	data/fingerprints/80_v33
412K	data/fingerprints_sub_exp/84_v33_sub_1
436K	data/fingerprints/91_v33
460K	data/fingerprints_sub_exp/87_v33_sub_1
472K	data/fingerprints_sub_exp/95_v33_sub_2
476K	data/fingerprints_sub_exp/92_v33_sub_2
484K	data/fingerprints/87_v33
528K	data/fingerprints/88_v33
528K	data/fingerprints/93_v33
552K	data/fingerprints/84_v33
576K	data/fingerprints/86_v33
576K	data/fingerprints/92_v33
588K	data/fingerprints/85_v33
652K	data/fingerprints/79_v33
652K	data/fingerprints/81_v33
664K	data/fingerprints/89_v33
672K	data/fingerprints/82_v33
672K	data/fingerprints/94_v33
684K	data/fingerprints/83_v33
752K	data/input/banners
788K	data/fingerprints/78_v33
836K	data/fingerprints/95_v33
1.4M	data/banner_database
2.4M	data/output/banner_debug
2.5M	data/output/found_banners_debug
3.6M	data/output/banner_candidates
5.0M	data/fingerprints_sub_exp
11M	data/fingerprints
20M	data/output/banner_search
24M	data/output/banner_search_v03_3
65M	data/input/90
113M	data/input/80
187M	data/input/91
190M	data/input/92
190M	data/subfingerprints_exp/92_v33
193M	data/input/87
193M	data/subfingerprints_exp/87_v33
194M	data/input/88
199M	data/input/86
206M	data/input/93
214M	data/input/82
264M	data/input/79
264M	data/input/84
264M	data/subfingerprints_exp/84_v33
271M	data/input/83
273M	data/input/89
273M	data/subfingerprints_exp/89_v33
278M	data/input/95
278M	data/subfingerprints_exp/95_v33
284M	data/input/94
284M	data/subfingerprints_exp/94_v33
294M	data/input/78
298M	data/input/85
298M	data/subfingerprints_exp/85_v33
335M	data/input/81
622M	data/output/found_banners
998M	data/input/test
1001M	data/input/1
1.8G	data/subfingerprints_exp
2.0G	data/output/check_visual
2.7G	data/output
6.0G	data/input
11G	data
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 12:51:12

Да, теперь структура понятна. **Основные рабочие данные здесь сохранены**, а мусор/эксперименты хорошо отделяются.

### Что точно оставляем

```text
data/input/                 6.0G   ← исходные фотографии
data/fingerprints/          11M    ← рабочие v33
data/banner_database/       1.4M   ← база баннеров
data/input/banners/         752K   ← эталонные баннеры
```

Особенно **не трогаем `data/input` и `data/fingerprints`**.

### Что выглядит экспериментальным

```text
data/subfingerprints_exp/       1.8G
data/output/check_visual/       2.0G
data/output/                    2.7G
data/fingerprints_sub_exp/      5.0M
data/output/banner_search...
data/output/found_banners...
data/banner_database/model_compare...
```

`subfingerprints_exp` на **1.8 GB** — это явно старые экспериментальные подслепки. Но я бы пока не удалял их вслепую: часть экспериментов могла пригодиться для истории разработки.

А вот `data/output` почти наверняка можно чистить **по тому же принципу, что мы сделали с верхним `output`: удалить только JPG/JPEG**, оставив JSON/CSV и прочие результаты.

### Предлагаю сначала посчитать

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== JPG/JPEG IN data/output ==="
find data/output -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) | wc -l

echo
echo "=== JPG/JPEG SIZE ==="
find data/output -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) \
  -printf "%s\n" | awk '{s+=$1} END {printf "%.2f GB\n",s/1024/1024/1024}'

echo
echo "=== OTHER LARGE FILES ==="
find data/output -type f \
  ! -iname "*.jpg" ! -iname "*.jpeg" \
  -printf "%s %p\n" | sort -nr | head -30
```

После этого будет видно, **сколько из 2.7 GB `data/output` составляют картинки**.

И ещё: **`data/subfingerprints_exp` пока не трогаем**. Это уже не просто кэш — там экспериментальные данные, которые потенциально могут понадобиться для восстановления/сравнения.

---

