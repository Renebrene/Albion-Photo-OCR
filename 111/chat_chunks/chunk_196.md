## СЕССИЯ: Проверка синтаксиса Bash

**Создано:** 2026-08-19 21:50:09
**Обновлено:** 2026-08-20 23:29:40
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a85fade-41f8-83ea-a515-bd8459637026](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a85fade-41f8-83ea-a515-bd8459637026)

---

### 🤖 **Assistant** — 2026-08-19 22:01:21

Да. Ниже полный готовый файл. Он:

- тестирует `qwen2.5vl:7b` и `qwen3-vl:4b-instruct`;
- берёт 20 фото;
- `num_ctx = 8192`;
- `num_predict = 600`;
- сохраняет запрос/ответ через временные файлы, без огромных Bash-аргументов;
- считает `prompt_tokens`, `output_tokens`, `tok/s`;
- отдельно считает успешные/ошибочные фото;
- **после каждого модельного теста выгружает модель из памяти** через `keep_alive: 0`;
- CSV перезаписывает заново.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/run_qwen_20.sh <<'SH'
#!/bin/bash

set -u

PROJECT="/home/alexice/projects/scene_fingerprint_mvp_v02"
INPUT="$PROJECT/data/input/daily"
OUTDIR="$PROJECT/data/benchmark_qwen_vl_20"

OLLAMA_URL="http://127.0.0.1:11434/api/generate"

MODELS=(
    "qwen2.5vl:7b"
    "qwen3-vl:4b-instruct"
)

NUM_CTX=8192
NUM_PREDICT=600
TEMPERATURE=0

mkdir -p "$OUTDIR"

mapfile -t IMAGES < <(
    find "$INPUT" -type f \
        \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) \
        | sort \
        | head -n 20
)

echo "============================================================"
echo "QWEN 20 PHOTO BENCHMARK"
echo "============================================================"
echo "INPUT:       $INPUT"
echo "PHOTOS:      ${#IMAGES[@]}"
echo "NUM_CTX:     $NUM_CTX"
echo "NUM_PREDICT: $NUM_PREDICT"
echo

if [ "${#IMAGES[@]}" -eq 0 ]; then
    echo "ERROR: фотографии не найдены"
    exit 1
fi

if [ "${#IMAGES[@]}" -lt 20 ]; then
    echo "WARNING: найдено меньше 20 фотографий"
fi

for MODEL in "${MODELS[@]}"; do

    SAFE_NAME="${MODEL//:/_}"
    RESULT="$OUTDIR/${SAFE_NAME}.csv"

    echo
    echo "============================================================"
    echo "MODEL: $MODEL"
    echo "============================================================"

    printf "photo\tstatus\tseconds\tprompt_tokens\toutput_tokens\ttokens_sec\ttotal_tokens\n" \
        > "$RESULT"

    TOTAL_TIME=0
    TOTAL_PROMPT_TOKENS=0
    TOTAL_OUTPUT_TOKENS=0
    SUCCESS=0
    ERRORS=0
    N=0

    for IMAGE in "${IMAGES[@]}"; do

        N=$((N + 1))

        BASENAME="$(basename "$IMAGE")"

        echo
        echo "[$N/${#IMAGES[@]}] $BASENAME"

        REQUEST_FILE=$(mktemp)
        RESPONSE_FILE=$(mktemp)

        # --------------------------------------------------------
        # Создаём JSON-запрос
        # --------------------------------------------------------

        uv run python - "$MODEL" "$IMAGE" "$NUM_CTX" "$NUM_PREDICT" "$TEMPERATURE" \
            > "$REQUEST_FILE" <<'PY'
import base64
import json
import sys

model = sys.argv[1]
image = sys.argv[2]
num_ctx = int(sys.argv[3])
num_predict = int(sys.argv[4])
temperature = float(sys.argv[5])

with open(image, "rb") as f:
    encoded = base64.b64encode(f.read()).decode()

payload = {
    "model": model,

    "prompt": """Проанализируй рекламную конструкцию на фотографии.

Определи:
1. клиента или бренд;
2. категорию рекламы;
3. читаемый текст;
4. основные объекты на рекламной конструкции;
5. основные цвета;
6. краткое описание изображения.

Отвечай кратко и структурированно.
Не добавляй лишних рассуждений.""",

    "images": [encoded],

    "stream": False,

    "keep_alive": "5m",

    "options": {
        "temperature": temperature,
        "num_ctx": num_ctx,
        "num_predict": num_predict
    }
}

print(json.dumps(payload, ensure_ascii=False))
PY

        START=$(date +%s.%N)

        # --------------------------------------------------------
        # Ollama
        # Ответ сразу пишем в файл
        # --------------------------------------------------------

        HTTP_CODE=$(curl -s \
            -o "$RESPONSE_FILE" \
            -w "%{http_code}" \
            "$OLLAMA_URL" \
            -H "Content-Type: application/json" \
            --data-binary "@$REQUEST_FILE")

        END=$(date +%s.%N)

        rm -f "$REQUEST_FILE"

        # --------------------------------------------------------
        # Разбор ответа
        # --------------------------------------------------------

        METRICS=$(uv run python - "$RESPONSE_FILE" <<'PY'
import json
import sys

path = sys.argv[1]

try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

except Exception as e:
    print("ERROR")
    print(f"JSON parse error: {e}")
    print("0")
    print("0")
    print("0")
    print("0")
    raise SystemExit

if "error" in data:
    error = data["error"]

    if isinstance(error, dict):
        error_text = json.dumps(
            error,
            ensure_ascii=False,
            separators=(",", ":")
        )
    else:
        error_text = str(error)

    print("ERROR")
    print(error_text)
    print("0")
    print("0")
    print("0")
    print("0")
    raise SystemExit

prompt_tokens = int(data.get("prompt_eval_count", 0))
output_tokens = int(data.get("eval_count", 0))
eval_ns = int(data.get("eval_duration", 0))

total_tokens = prompt_tokens + output_tokens

if eval_ns > 0:
    tokens_sec = output_tokens / (eval_ns / 1e9)
else:
    tokens_sec = 0

print("OK")
print("")
print(prompt_tokens)
print(output_tokens)
print(tokens_sec)
print(total_tokens)
PY
)

        STATUS=$(printf '%s\n' "$METRICS" | sed -n '1p')

        ELAPSED=$(uv run python - "$START" "$END" <<'PY'
import sys

print(float(sys.argv[2]) - float(sys.argv[1]))
PY
)

        if [ "$STATUS" = "ERROR" ]; then

            ERROR_TEXT=$(printf '%s\n' "$METRICS" | sed -n '2p')

            ERRORS=$((ERRORS + 1))

            echo "  status:  ERROR"
            echo "  HTTP:    $HTTP_CODE"
            echo "  time:    ${ELAPSED}s"
            echo "  error:   $ERROR_TEXT"

            printf "%s\tERROR\t%.3f\t0\t0\t0\t0\n" \
                "$BASENAME" \
                "$ELAPSED" \
                >> "$RESULT"

            rm -f "$RESPONSE_FILE"

            TOTAL_TIME=$(uv run python - "$TOTAL_TIME" "$ELAPSED" <<'PY'
import sys

print(float(sys.argv[1]) + float(sys.argv[2]))
PY
)

            continue
        fi

        PROMPT_TOKENS=$(printf '%s\n' "$METRICS" | sed -n '3p')
        OUTPUT_TOKENS=$(printf '%s\n' "$METRICS" | sed -n '4p')
        TOKENS_SEC=$(printf '%s\n' "$METRICS" | sed -n '5p')
        TOTAL_TOKENS=$(printf '%s\n' "$METRICS" | sed -n '6p')

        SUCCESS=$((SUCCESS + 1))

        printf "%s\tOK\t%.3f\t%d\t%d\t%.2f\t%d\n" \
            "$BASENAME" \
            "$ELAPSED" \
            "$PROMPT_TOKENS" \
            "$OUTPUT_TOKENS" \
            "$TOKENS_SEC" \
            "$TOTAL_TOKENS" \
            >> "$RESULT"

        TOTAL_TIME=$(uv run python - "$TOTAL_TIME" "$ELAPSED" <<'PY'
import sys

print(float(sys.argv[1]) + float(sys.argv[2]))
PY
)

        TOTAL_PROMPT_TOKENS=$(
            uv run python - \
                "$TOTAL_PROMPT_TOKENS" \
                "$PROMPT_TOKENS" <<'PY'
import sys

print(int(sys.argv[1]) + int(sys.argv[2]))
PY
)

        TOTAL_OUTPUT_TOKENS=$(
            uv run python - \
                "$TOTAL_OUTPUT_TOKENS" \
                "$OUTPUT_TOKENS" <<'PY'
import sys

print(int(sys.argv[1]) + int(sys.argv[2]))
PY
)

        echo "  status:  OK"
        echo "  time:    ${ELAPSED}s"
        echo "  prompt:  ${PROMPT_TOKENS} tokens"
        echo "  output:  ${OUTPUT_TOKENS} tokens"
        echo "  tok/s:   ${TOKENS_SEC}"

        rm -f "$RESPONSE_FILE"

    done

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------

    AVG_TIME=$(uv run python - \
        "$TOTAL_TIME" \
        "${#IMAGES[@]}" <<'PY'
import sys

total = float(sys.argv[1])
count = int(sys.argv[2])

print(total / count if count else 0)
PY
)

    if [ "$SUCCESS" -gt 0 ]; then

        AVG_PROMPT=$(uv run python - \
            "$TOTAL_PROMPT_TOKENS" \
            "$SUCCESS" <<'PY'
import sys

print(float(sys.argv[1]) / int(sys.argv[2]))
PY
)

        AVG_OUTPUT=$(uv run python - \
            "$TOTAL_OUTPUT_TOKENS" \
            "$SUCCESS" <<'PY'
import sys

print(float(sys.argv[1]) / int(sys.argv[2]))
PY
)

    else
        AVG_PROMPT=0
        AVG_OUTPUT=0
    fi

    echo
    echo "------------------------------------------------------------"
    echo "SUMMARY: $MODEL"
    echo "------------------------------------------------------------"
    echo "Photos:              ${#IMAGES[@]}"
    echo "Successful:          $SUCCESS"
    echo "Errors:              $ERRORS"
    echo "Total time:          ${TOTAL_TIME}s"
    echo "Average / photo:     ${AVG_TIME}s"
    echo "Average prompt:      ${AVG_PROMPT} tokens"
    echo "Average output:      ${AVG_OUTPUT} tokens"
    echo "Context:             ${NUM_CTX}"
    echo "Max output:          ${NUM_PREDICT}"
    echo "Results:             $RESULT"

    # ------------------------------------------------------------
    # ВЫГРУЗКА МОДЕЛИ ИЗ VRAM
    # ------------------------------------------------------------

    echo
    echo "Unloading model: $MODEL"

    curl -s \
        "$OLLAMA_URL" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$MODEL\",\"prompt\":\"\",\"keep_alive\":0}" \
        > /dev/null

    sleep 2

    echo "Model unloaded."

done

echo
echo "============================================================"
echo "BENCHMARK FINISHED"
echo "============================================================"
echo
echo "CSV files:"
echo "  $OUTDIR/qwen2.5vl_7b.csv"
echo "  $OUTDIR/qwen3-vl_4b-instruct.csv"
echo
SH

chmod +x /tmp/run_qwen_20.sh

bash -n /tmp/run_qwen_20.sh && echo "SYNTAX OK"
```

После `SYNTAX OK`:

```bash
uv run bash /tmp/run_qwen_20.sh
```

### Что важно в этой версии

В запросе:

```json
"num_ctx": 8192,
"num_predict": 600
```

То есть прежняя ошибка:

```text
request (4108 tokens) exceeds the available context size (4096 tokens)
```

больше не должна возникать из-за лимита 4096.

А после `qwen2.5vl:7b` будет:

```text
Unloading model: qwen2.5vl:7b
Model unloaded.
```

и только потом начнётся:

```text
MODEL: qwen3-vl:4b-instruct
```

Так мы получим **честное сравнение моделей на одинаковых 20 фотографиях и одинаковом лимите генерации 600 токенов**.

---

### 👤 **User** — 2026-08-19 22:05:43

эти модели работают с языковыми запрсами - типа преобразования результатов поиска в базе на человеческий язык

---

### 🤖 **Assistant** — 2026-08-19 22:05:44

> **Searching the web**
>
>
> **Searching 6 websites**
>
> 
>
> Worked for a couple of seconds

Да. **Именно для этого они тоже подходят.** Это не просто «распознаватели картинок», а **vision-language / multimodal language models**: они принимают текстовый запрос и генерируют текстовый ответ. Qwen3-VL прямо заявлен как модель с улучшенным пониманием и генерацией текста, а Qwen2.5-VL поддерживает обычные текстовые ответы, структурированный вывод и image-to-text задачи. ([GitHub](https://github.com/QwenLM/Qwen3-VL?utm_source=chatgpt.com))

Для твоей «Фотобазы. Офис» это означает, что Qwen можно использовать **вообще без изображения**, например:

### 1. Перевод результата поиска на человеческий язык

База вернула:

```json
{
  "client": "Альфа",
  "address": "Ашхабадский 7",
  "matches": 14,
  "best_score": 0.941,
  "status": "CONFIDENT",
  "date_from": "2026-07-01",
  "date_to": "2026-08-18"
}
```

Пользователь спрашивает:

> Найди фотографии Альфы на Ашхабадском за последний месяц.

Qwen получает **только этот JSON + вопрос** и формирует:

> Нашёл 14 фотографий клиента «Альфа» по адресу Ашхабадский 7 за последний месяц. Лучшее совпадение имеет оценку 0,941.

### 2. Диалог с базой

Например:

> Покажи, какие адреса Альфы у нас есть?

Backend делает SQL-поиск:

```text
Ашхабадский 7
Вавилова 52
Комарова 13
```

Qwen превращает это в:

> У клиента «Альфа» сейчас есть фотографии с трёх адресов: Ашхабадский 7, Вавилова 52 и Комарова 13.

### 3. Более сложный запрос

Пользователь:

> Где у нас больше всего фотографий Альфы и когда последний раз снимали?

Backend:

```json
[
  {"address":"Ашхабадский 7","count":184,"last_date":"2026-08-18"},
  {"address":"Вавилова 52","count":91,"last_date":"2026-08-12"},
  {"address":"Комарова 13","count":63,"last_date":"2026-07-29"}
]
```

Qwen:

> Больше всего фотографий «Альфы» - на Ашхабадском 7: 184 снимка. Последняя съёмка там была 18 августа. Далее идут Вавилова 52 - 91 фото и Комарова 13 - 63.

---

### И здесь есть важное разделение для нашего проекта

Я бы **не использовал Qwen для самого поиска**.

Архитектура должна быть:

```text
ПОЛЬЗОВАТЕЛЬ
     │
     │ естественный язык
     ▼
    QWEN
     │
     │ понимает намерение
     ▼
структурированный запрос
     │
     ▼
 PHOTOBASE / SQLite / PostgreSQL
     │
     │ точные результаты
     ▼
    QWEN
     │
     │ превращает данные в человеческий ответ
     ▼
ПОЛЬЗОВАТЕЛЬ
```

То есть Qwen - **языковой интерфейс над нашей базой**, а не база и не механизм поиска.

И это очень хорошо сочетается с тем, что мы уже сделали с DINOv2: **распознавание остаётся детерминированным и без LLM**, а Qwen можно поставить сверху исключительно как интерфейс общения с результатами.

Причём для этой второй задачи **изображения вообще не нужны**. Можно использовать тот же `qwen3:4b` / `qwen3:8b`, а VL-модели оставлять для случаев, когда действительно нужно смотреть на фотографию. Qwen3-VL поддерживает генерацию текста из текстовых/мультимодальных входов. ([Mintlify](https://www.mintlify.com/QwenLM/Qwen3-VL/api/generation?utm_source=chatgpt.com))

**И вот здесь я бы разделил наши будущие тесты:**

| Задача | Модель |
|---|---|
| Посмотреть фотографию → понять рекламу | Qwen-VL |
| OCR/понимание баннера | Qwen-VL |
| Сравнить фото/баннеры по содержанию | Qwen-VL |
| SQL/поиск уже найденных данных → человеческий ответ | обычный Qwen |
| Естественный язык → параметры поиска | обычный Qwen |
| Диалог с фотобазой | обычный Qwen + наша БД |

То есть наш нынешний benchmark Qwen-VL проверяет **только первую группу задач**. Для интерфейса «спросить фотобазу человеческим языком» нужно будет сделать **отдельный маленький benchmark**, и там уже имеет смысл сравнить `qwen3:4b`, `qwen3:8b`, возможно `qwen3:1.7b`.

---

**Sources:**

- [GitHub - QwenLM/Qwen3-VL: Qwen3-VL is the multimodal large language model series developed by Qwen team, Alibaba Cloud. · GitHub](https://github.com/QwenLM/Qwen3-VL?utm_source=chatgpt.com)
- [Text Generation - Qwen3-VL](https://www.mintlify.com/QwenLM/Qwen3-VL/api/generation?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-19 22:07:34

модели qwen 3 lдля 12 гб

---

### 🤖 **Assistant** — 2026-08-19 22:07:35

> **Searching the web**
>
>
> **Searching huggingface.co**
>
> 
>
> Worked for a couple of seconds

Если речь именно про **Qwen3 для твоей RTX 3060 12 GB**, то для задачи «естественный язык ↔ результаты фотобазы» я бы смотрел так:

| Модель | Для 12 GB | Мой выбор |
|---|---|---|
| **Qwen3 8B 4-bit** | ✅ примерно на границе, но реально | ⭐ лучший вариант по качеству |
| **Qwen3 4B** | ✅ очень комфортно | ⭐ лучший баланс скорости |
| **Qwen3 1.7B** | ✅ легко | только если нужна максимальная скорость |
| Qwen3 0.6B | ✅ легко | для простых шаблонных задач |

У официального Qwen3-8B полная модель большая, но разработчики указывают, что **4-bit вариант требует около 12 GB GPU-памяти**. ([Hugging Face](https://huggingface.co/Qwen/Qwen3-8B/blob/refs%2Fpr%2F23/README.md?utm_source=chatgpt.com)) При этом сам репозиторий Qwen3-8B занимает около 16.4 GB в полном виде. ([Hugging Face](https://huggingface.co/Qwen/Qwen3-8B/tree/main?utm_source=chatgpt.com))

Qwen3-4B заметно легче: официальный репозиторий модели - около **8.06 GB** в исходном формате. ([Hugging Face](https://huggingface.co/Qwen/Qwen3-4B/tree/main?utm_source=chatgpt.com))

### Для нашей фотобазы я бы сделал так

**Основная LLM: Qwen3 4B**

У тебя уже есть:

```text
qwen3:4b
```

и это как раз очень хороший кандидат для:

```text
Пользователь:
"Покажи последние фотографии Альфы на Ашхабадском"

        ↓

Qwen3 4B

        ↓

структурированный запрос

{
  "client": "Альфа",
  "address": "Ашхабадский",
  "sort": "date_desc"
}

        ↓

PostgreSQL

        ↓

результаты

        ↓

Qwen3 4B

"Нашёл 27 фотографий..."
```

При этом **8B 4-bit** я бы отдельно протестировал. Он может дать более качественное понимание сложных русских запросов и более естественные ответы, но на 12 GB будет гораздо теснее по VRAM. Официальная документация Qwen указывает около 12 GB для 4-bit Qwen3-8B. ([Hugging Face](https://huggingface.co/Qwen/Qwen3-8B/blob/refs%2Fpr%2F23/README.md?utm_source=chatgpt.com))

### А Qwen-VL здесь вообще не нужен

Для этого слоя:

```text
SQL → результаты → человеческий язык
```

лучше обычный:

**`qwen3:4b` / `qwen3:8b`**

а наши:

**`qwen2.5vl:7b` / `qwen3-vl:4b-instruct`**

оставить для работы **с фотографиями**.

То есть архитектурно у нас получится очень чисто:

```text
                 ФОТО
                   │
          ┌────────┴────────┐
          ▼                 ▼
       DINOv2           Qwen-VL
          │                 │
       адрес             визуальный
       /scene             анализ
          │                 │
          └────────┬────────┘
                   ▼
               ФОТОБАЗА
                   │
                   ▼
                Qwen3
             4B / 8B 4-bit
                   │
                   ▼
          ЧЕЛОВЕЧЕСКИЙ ДИАЛОГ
```

**Для твоих 12 GB я бы первым делом протестировал `qwen3:4b`, а затем нашёл/поставил Qwen3-8B в 4-bit и сравнил именно на русских запросах к нашей базе.**

---

**Sources:**

- [README.md · Qwen/Qwen3-8B at refs/pr/23](https://huggingface.co/Qwen/Qwen3-8B/blob/refs%2Fpr%2F23/README.md?utm_source=chatgpt.com)

---

### 👤 **User** — 2026-08-19 22:09:26

QWEN 20 PHOTO BENCHMARK
============================================================
INPUT:       /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily
PHOTOS:      20
NUM_CTX:     8192
NUM_PREDICT: 600

============================================================
MODEL: qwen2.5vl:7b
============================================================

[1/20] Screenshot from 2026-08-16 00-38-11.png
  status:  OK
  time:    9.317611694335938s
  prompt:  1173 tokens
  output:  229 tokens
  tok/s:   66.08214270049149

[2/20] Ашхабадский_01.JPG
  status:  OK
  time:    11.69313931465149s
  prompt:  4132 tokens
  output:  174 tokens
  tok/s:   64.16144494523968

[3/20] Ашхабадский_02.JPG
  status:  OK
  time:    11.60679292678833s
  prompt:  4132 tokens
  output:  182 tokens
  tok/s:   62.63266424211723

[4/20] Ашхабадский_03.JPG
  status:  OK
  time:    12.254336833953857s
  prompt:  4132 tokens
  output:  217 tokens
  tok/s:   62.754415655173446

[5/20] Ашхабадский_04.JPG
  status:  OK
  time:    10.389655828475952s
  prompt:  4132 tokens
  output:  100 tokens
  tok/s:   62.42306357414487

[6/20] Ашхабадский_05.JPG
  status:  OK
  time:    12.830848455429077s
  prompt:  4132 tokens
  output:  249 tokens
  tok/s:   62.39137886450697

[7/20] Ашхабадский_06.JPG
  status:  OK
  time:    12.39575743675232s
  prompt:  4132 tokens
  output:  222 tokens
  tok/s:   62.47871642824376

[8/20] Ашхабадский_07.JPG
  status:  OK
  time:    12.256915807723999s
  prompt:  4132 tokens
  output:  214 tokens
  tok/s:   62.13475867759813

[9/20] Ашхабадский_08.JPG
  status:  OK
  time:    10.481104373931885s
  prompt:  4132 tokens
  output:  116 tokens
  tok/s:   62.988739676770024

[10/20] Ашхабадский_09.JPG
  status:  OK
  time:    11.7261061668396s
  prompt:  4132 tokens
  output:  194 tokens
  tok/s:   63.745732075373745

[11/20] Ашхабадский_10.JPG
  status:  OK
  time:    10.618232250213623s
  prompt:  4132 tokens
  output:  125 tokens
  tok/s:   63.819695574946536

[12/20] Ашхабадский_11.JPG
  status:  OK
  time:    11.051208972930908s
  prompt:  4132 tokens
  output:  152 tokens
  tok/s:   63.63083399510796

[13/20] Ашхабадский_12.JPG
  status:  OK
  time:    11.269480466842651s
  prompt:  4132 tokens
  output:  166 tokens
  tok/s:   63.71419195243697

[14/20] Ашхабадский_13.JPG
  status:  OK
  time:    11.549387216567993s
  prompt:  4132 tokens
  output:  182 tokens
  tok/s:   63.42950803446243

[15/20] Ашхабадский_14.JPG
  status:  OK
  time:    12.081855773925781s
  prompt:  4132 tokens
  output:  210 tokens
  tok/s:   63.47859048510339

[16/20] Ашхабадский_15.JPG
  status:  OK
  time:    11.945802211761475s
  prompt:  4132 tokens
  output:  213 tokens
  tok/s:   63.89603844561637

[17/20] Ашхабадский_16.JPG
  status:  OK
  time:    12.145289182662964s
  prompt:  4132 tokens
  output:  221 tokens
  tok/s:   63.71856346642825

[18/20] Ашхабадский_17.JPG
  status:  OK
  time:    10.977274656295776s
  prompt:  4132 tokens
  output:  146 tokens
  tok/s:   64.18911343843055

[19/20] Ашхабадский_18.JPG
  status:  OK
  time:    11.667958974838257s
  prompt:  4132 tokens
  output:  161 tokens
  tok/s:   63.80280573828961

[20/20] Вавилова52_01.JPG
  status:  OK
  time:    10.556617975234985s
  prompt:  4132 tokens
  output:  115 tokens
  tok/s:   63.70393513055983

------------------------------------------------------------
SUMMARY: qwen2.5vl:7b
------------------------------------------------------------
Photos:              20
Successful:          20
Errors:              0
Total time:          228.81537652015686s
Average / photo:     11.440768826007844s
Average prompt:      3984.05 tokens
Average output:      179.4 tokens
Context:             8192
Max output:          600
Results:             /home/alexice/projects/scene_fingerprint_mvp_v02/data/benchmark_qwen_vl_20/qwen2.5vl_7b.csv

Unloading model: qwen2.5vl:7b
Model unloaded.

============================================================
MODEL: qwen3-vl:4b-instruct
============================================================

[1/20] Screenshot from 2026-08-16 00-38-11.png
  status:  OK
  time:    8.789360284805298s
  prompt:  1162 tokens
  output:  465 tokens
  tok/s:   91.59065791046845

[2/20] Ашхабадский_01.JPG
  status:  OK
  time:    10.526917457580566s
  prompt:  4121 tokens
  output:  445 tokens
  tok/s:   80.92752767130403

[3/20] Ашхабадский_02.JPG
  status:  OK
  time:    8.925980806350708s
  prompt:  4121 tokens
  output:  311 tokens
  tok/s:   83.49679195123143

[4/20] Ашхабадский_03.JPG
  status:  OK
  time:    8.287278413772583s
  prompt:  4121 tokens
  output:  249 tokens
  tok/s:   82.79990024108405

[5/20] Ашхабадский_04.JPG
  status:  OK
  time:    9.297360897064209s
  prompt:  4121 tokens
  output:  325 tokens
  tok/s:   80.50568469217846

[6/20] Ашхабадский_05.JPG
  status:  OK
  time:    10.992536306381226s
  prompt:  4121 tokens
  output:  442 tokens
  tok/s:   79.40321834537704

[7/20] Ашхабадский_06.JPG
  status:  OK
  time:    9.309238910675049s
  prompt:  4121 tokens
  output:  324 tokens
  tok/s:   79.72976531149853

[8/20] Ашхабадский_07.JPG
  status:  OK
  time:    9.44126582145691s
  prompt:  4121 tokens
  output:  353 tokens
  tok/s:   83.2171318850095

[9/20] Ашхабадский_08.JPG
  status:  OK
  time:    6.793263673782349s
  prompt:  4121 tokens
  output:  139 tokens
  tok/s:   84.0098442614628

[10/20] Ашхабадский_09.JPG
  status:  OK
  time:    8.547576665878296s
  prompt:  4121 tokens
  output:  239 tokens
  tok/s:   77.43742391935103

[11/20] Ашхабадский_10.JPG
  status:  OK
  time:    7.25763201713562s
  prompt:  4121 tokens
  output:  165 tokens
  tok/s:   82.99544128676132

[12/20] Ашхабадский_11.JPG
  status:  OK
  time:    7.711581468582153s
  prompt:  4121 tokens
  output:  199 tokens
  tok/s:   82.61477849690921

[13/20] Ашхабадский_12.JPG
  status:  OK
  time:    9.038147687911987s
  prompt:  4121 tokens
  output:  308 tokens
  tok/s:   82.15048635488424

[14/20] Ашхабадский_13.JPG
  status:  OK
  time:    8.571970462799072s
  prompt:  4121 tokens
  output:  269 tokens
  tok/s:   81.25272981987267

[15/20] Ашхабадский_14.JPG
  status:  OK
  time:    9.154364824295044s
  prompt:  4121 tokens
  output:  318 tokens
  tok/s:   81.51791484351509

[16/20] Ашхабадский_15.JPG
  status:  OK
  time:    8.61631464958191s
  prompt:  4121 tokens
  output:  278 tokens
  tok/s:   82.82585119948517

[17/20] Ашхабадский_16.JPG
  status:  OK
  time:    8.947683572769165s
  prompt:  4121 tokens
  output:  306 tokens
  tok/s:   82.50059853375407

[18/20] Ашхабадский_17.JPG
  status:  OK
  time:    7.019265174865723s
  prompt:  4121 tokens
  output:  149 tokens
  tok/s:   83.1352593931684

[19/20] Ашхабадский_18.JPG
  status:  OK
  time:    7.830482482910156s
  prompt:  4121 tokens
  output:  215 tokens
  tok/s:   83.28668633265477

[20/20] Вавилова52_01.JPG
  status:  OK
  time:    9.847341537475586s
  prompt:  4121 tokens
  output:  386 tokens
  tok/s:   82.5987713325771

------------------------------------------------------------
SUMMARY: qwen3-vl:4b-instruct
------------------------------------------------------------
Photos:              20
Successful:          20
Errors:              0
Total time:          174.9055631160736s
Average / photo:     8.74527815580368s
Average prompt:      3973.05 tokens
Average output:      294.25 tokens
Context:             8192
Max output:          600
Results:             /home/alexice/projects/scene_fingerprint_mvp_v02/data/benchmark_qwen_vl_20/qwen3-vl_4b-instruct.csv

Unloading model: qwen3-vl:4b-instruct
Model unloaded.

============================================================
BENCHMARK FINISHED
============================================================

CSV files:
  /home/alexice/projects/scene_fingerprint_mvp_v02/data/benchmark_qwen_vl_20/qwen2.5vl_7b.csv
  /home/alexice/projects/scene_fingerprint_mvp_v02/data/benchmark_qwen_vl_20/qwen3-vl_4b-instruct.csv

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 22:09:29

Да. Теперь это уже **нормальный чистый benchmark**, и результат довольно однозначный.

### Qwen-VL на твоей RTX 3060 12 GB

| Показатель | Qwen2.5-VL 7B | Qwen3-VL 4B |
|---|---:|---:|
| Фото | 20 | 20 |
| Успешно | 20 | 20 |
| Среднее время | **11.44 с** | **8.75 с** |
| Общее время | 228.8 с | **174.9 с** |
| Prompt | ~3984 | ~3973 |
| Output | 179 | **294** |
| Генерация | ~63–66 tok/s | **~80–92 tok/s** |
| Context | 8192 | 8192 |
| Max output | 600 | 600 |

### Главный вывод

**Qwen3-VL:4B-Instruct однозначно выигрывает.**

Он:

- примерно **на 23.6% быстрее** по среднему времени;
- генерирует примерно **на 31% быстрее**;
- при этом выдаёт **гораздо больше полезного текста** — 294 против 179 токенов;
- все 20 фотографий обработаны без ошибок.

То есть на твоём железе:

> **Qwen3-VL 4B — лучший выбор для визуального слоя фотобазы.**

Причём это особенно интересно с учётом того, что модель в 2 раза меньше по параметрам.

### Но есть важный нюанс

Сейчас почти весь контекст съедается **самой картинкой**:

```text
Qwen2.5-VL:  ~4132 prompt tokens
Qwen3-VL:    ~4121 prompt tokens
```

А текстовая инструкция занимает совсем немного.

То есть увеличение `num_ctx` до 8192 было нужно только потому, что vision encoder превращает фотографию в ~4k токенов.

Для реального применения **не надо ставить `num_predict=600` постоянно**.

Для нашего сценария я бы поставил примерно:

```text
num_ctx     = 8192
num_predict = 250–300
```

Потому что для задачи:

> клиент / бренд / категория / текст / описание

294 токена уже более чем достаточно, а часто хватит 100–200.

Это даст немного меньше времени и исключит бессмысленную генерацию.

---

### А вот для второй задачи — общения с фотобазой — ситуация ещё интереснее

Мы сейчас протестировали:

```text
ФОТО → Qwen-VL → текст
```

Но ты выше правильно сформулировал другую задачу:

```text
БАЗА → результаты поиска → Qwen → человеческий ответ
```

Там **вообще нет этих ~4000 vision tokens**.

Например:

```text
Пользователь:
"Что у нас есть по Альфе на Ашхабадском?"

        ↓

DINO / DB / SQL

        ↓

20 записей JSON

        ↓

Qwen3 4B

        ↓

"По Альфе на Ашхабадском найдено 20 фотографий..."
```

Там Qwen3 4B будет работать **намного быстрее**, чем нынешние 8.75 секунды на фотографию.

И именно для этого слоя твоя уже установленная:

```text
qwen3:4b
```

выглядит очень перспективно.

### Поэтому я бы сейчас зафиксировал архитектуру

```text
                    ФОТО
                      │
             ┌────────┴────────┐
             │                 │
           DINOv2          Qwen3-VL 4B
             │                 │
       распознавание       визуальный анализ
             │                 │
             └────────┬────────┘
                      ▼
                 ФОТОБАЗА
                      │
                      ▼
                  Qwen3 4B
                      │
              человеческий язык
                      │
                      ▼
                   МЕНЕДЖЕР
```

**DINOv2 остаётся основным механизмом распознавания. Qwen3-VL 4B — визуальный помощник. Qwen3 4B — языковой интерфейс к базе.**

И я бы **не ставил Qwen3-VL 4B в основной цикл распознавания всех фотографий** — 8.75 секунды/фото слишком дорого для массовой обработки. Его гораздо разумнее вызывать только там, где требуется визуальное понимание: баннер, сложный поиск, проверка кандидата, описание и т. п.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)

---
