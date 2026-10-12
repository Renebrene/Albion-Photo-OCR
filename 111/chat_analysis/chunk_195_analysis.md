Вот окончательный и готовый `/tmp/run_qwen_20.sh` с:

- **`num_ctx=8192`** (для увеличения контекста)
- **`num_predict=600`** (ограничение выходных токенов)
- **выгрузкой модели после каждого теста**
- **отдельным CSV-файлом**
- **временем загрузки/инференса**
- **`prompt_tokens` / `output_tokens` / `tok/s`**
- **корректным подсчётом успешных/ошибочных фото**

---

### ✅ **Готовый `/tmp/run_qwen_20.sh`**

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/run_qwen_20.sh <<'SH'
#!/bin/bash

set -u

INPUT="/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily"

MODELS=(
    "qwen2.5vl:7b"
    "qwen3-vl:4b-instruct"
)

OUTDIR="data/benchmark_qwen_vl_20"

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
echo "INPUT: $INPUT"
echo "PHOTOS: ${#IMAGES[@]}"
echo

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

    printf "photo\tseconds\tprompt_tokens\toutput_tokens\ttokens_sec\ttotal_tokens\tstatus\n" \
        > "$RESULT"

    TOTAL_TIME=0
    TOTAL_OUTPUT_TOKENS=0
    TOTAL_PROMPT_TOKENS=0
    N=0
    SUCCESS=0
    FAIL=0

    for IMAGE in "${IMAGES[@]}"; do

        N=$((N + 1))

        echo
        echo "[$N/${#IMAGES[@]}] $(basename "$IMAGE")"

        REQUEST_FILE=$(mktemp)
        RESPONSE_FILE=$(mktemp)

        # --------------------------------------------------------
        # Создание JSON-запроса
        # --------------------------------------------------------

        uv run python - "$MODEL" "$IMAGE" > "$REQUEST_FILE" <<'PY'
import base64
import json
import sys

model = sys.argv[1]
image = sys.argv[2]

with open(image, "rb") as f:
    encoded = base64.b64encode(f.read()).decode()

payload = {
    "model": model,
    "prompt": """Проанализируй рекламную конструкцию на фотографии.
Определи клиента, бренд, категорию, читаемый текст,
объекты на рекламной конструкции, основные цвета
и краткое описание.
Отвечай структурированно и без лишних рассуждений.""",
    "images": [encoded],
    "stream": False,
    "options": {
        "temperature": 0,
        "num_ctx": 8192,
        "num_predict": 600
    }
}

print(json.dumps(payload, ensure_ascii=False))
PY

        START=$(date +%s.%N)

        # --------------------------------------------------------
        # Ollama
        # Ответ сразу в файл — не держим огромный JSON в аргументе
        # --------------------------------------------------------

        curl -s \
            http://127.0.0.1:11434/api/generate \
            -H "Content-Type: application/json" \
            --data-binary "@$REQUEST_FILE" \
            > "$RESPONSE_FILE"

        END=$(date +%s.%N)

        rm -f "$REQUEST_FILE"

        # --------------------------------------------------------
        # Разбор ответа Ollama
        # --------------------------------------------------------

        METRICS=$(uv run python - "$RESPONSE_FILE" <<'PY'
import json
import sys

path = sys.argv[1]

try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "error" in data:
        print("ERROR")
        print(data["error"])
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

except Exception as e:
    print("ERROR")
    print(str(e))
    print("0")
    print("0")
    print("0")
    print("0")
PY
)

        STATUS=$(printf '%s\n' "$METRICS" | sed -n '1p')

        if [ "$STATUS" = "ERROR" ]; then

            ERROR_TEXT=$(printf '%s\n' "$METRICS" | sed -n '2p')

            echo "  ERROR:   $ERROR_TEXT"
            echo "  time:    $(uv run python - "$START" "$END" <<'PY'
import sys
print(float(sys.argv[2]) - float(sys.argv[1]))
PY
)s"

            rm -f "$RESPONSE_FILE"

            FAIL=$((FAIL + 1))
            continue
        fi

        PROMPT_TOKENS=$(printf '%s\n' "$METRICS" | sed -n '3p')
        OUTPUT_TOKENS=$(printf '%s\n' "$METRICS" | sed -n '4p')
        TOKENS_SEC=$(printf '%s\n' "$METRICS" | sed -n '5p')
        TOTAL_TOKENS=$(printf '%s\n' "$METRICS" | sed -n '6p')

        ELAPSED=$(uv run python - "$START" "$END" <<'PY'
import sys
print(float(sys.argv[2]) - float(sys.argv[1]))
PY
)

        rm -f "$RESPONSE_FILE"

        printf "%s\t%.3f\t%d\t%d\t%.2f\t%d\tOK\n" \
            "$(basename "$IMAGE")" \
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

        TOTAL_OUTPUT_TOKENS=$((TOTAL_OUTPUT_TOKENS + OUTPUT_TOKENS))
        TOTAL_PROMPT_TOKENS=$((TOTAL_PROMPT_TOKENS + PROMPT_TOKENS))

        SUCCESS=$((SUCCESS + 1))

        echo "  time:    ${ELAPSED}s"
        echo "  prompt:  ${PROMPT_TOKENS} tokens"
        echo "  output:  ${OUTPUT_TOKENS} tokens"
        echo "  tok/s:   ${TOKENS_SEC}"

    done

    # Выгрузка модели после теста
    curl -s http://127.0.0.1:11434/api/generate \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$MODEL\",\"prompt\":\"\",\"keep_alive\":0}" \
        > /dev/null

    AVG_TIME=$(uv run python - "$TOTAL_TIME" "${#IMAGES[@]}" <<'PY'
import sys
print(float(sys.argv[1]) / int(sys.argv[2]))
PY
)

    AVG_OUTPUT=$(uv run python - "$TOTAL_OUTPUT_TOKENS" "${#IMAGES[@]}" <<'PY'
import sys
print(float(sys.argv[1]) / int(sys.argv[2]))
PY
)

    AVG_PROMPT=$(uv run python - "$TOTAL_PROMPT_TOKENS" "${#IMAGES[@]}" <<'PY'
import sys
print(float(sys.argv[1]) / int(sys.argv[2]))
PY
)

    echo
    echo "------------------------------------------------------------"
    echo "SUMMARY: $MODEL"
    echo "------------------------------------------------------------"
    echo "Photos:              ${#IMAGES[@]}"
    echo "Success:             $SUCCESS"
    echo "Failed:              $FAIL"
    echo "Total time:          ${TOTAL_TIME}s"
    echo "Average / photo:     ${AVG_TIME}s"
    echo "Average prompt:      ${AVG_PROMPT} tokens"
    echo "Average output:      ${AVG_OUTPUT} tokens"
    echo "Results:             $RESULT"

done

echo
echo "============================================================"
echo "BENCHMARK FINISHED"
echo "============================================================"
SH

chmod +x /tmp/run_qwen_20.sh

bash -n /tmp/run_qwen_20.sh && echo "SYNTAX OK"
```

---

### 📌 **Что это даёт:**

1. **`num_ctx=8192`** — решает ошибку контекста.
2. **`num_predict=600`** — ограничивает выходные токены.
3. **`keep_alive=0`** — выгружает модель после теста.
4. **CSV-файлы** — отдельно для каждой модели.
5. **Статистика**:
   - Успешные/ошибочные запросы
   - Среднее время
   - Среднее количество токенов
   - `tok/s`

---

### ✅ **Как запустить:**

```bash
uv run bash /tmp/run_qwen_20.sh
```

Результаты будут в:

```
data/benchmark_qwen_vl_20/qwen2.5vl_7b.csv
data/benchmark_qwen_vl_20/qwen3-vl_4b-instruct.csv
```

Теперь можно сравнивать модели по реальным метрикам.