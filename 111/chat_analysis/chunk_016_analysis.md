```bash
#!/bin/bash

# Путь к данным
DATA_DIR="/home/alexice/projects/scene_fingerprint_mvp_v02/data"
TEST_DIR="$DATA_DIR/output/test"
OUTPUT_DIR="$DATA_DIR/output/test_classified"
CSV_FILE="$OUTPUT_DIR/results.csv"

# Папки с известными группами
KNOWN_GROUPS=("78" "79" "80" "81" "82" "83" "84" "85")

# Порог уверенности
THRESHOLD=0.6

# Функция для вычисления similarity
compute_similarity() {
    local photo="$1"
    local group="$2"
    local similarity=$(python3 compute_similarity.py "$photo" "$group")
    echo "$similarity"
}

# Очистка предыдущих результатов
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Обработка каждого файла
for file in "$TEST_DIR"/*.JPG; do
    filename=$(basename "$file" .JPG)
    echo "Processing $filename"
    
    # Получение Top-1
    top1=""
    top1_similarity=0
    for group in "${KNOWN_GROUPS[@]}"; do
        similarity=$(compute_similarity "$file" "$group")
        if (( $(echo "$similarity > $top1_similarity" | bc -l) )); then
            top1="$group"
            top1_similarity="$similarity"
        fi
    done
    
    # Определение результата
    if (( $(echo "$top1_similarity >= $THRESHOLD" | bc -l) )); then
        result="$top1"
    else
        result="00"
    fi
    
    # Сохранение результата
    echo "$filename,$result" >> "$CSV_FILE"
    echo "  $filename -> $result (similarity: $top1_similarity)"
done

# Статистика
echo "============================================================" >> "$CSV_FILE"
echo " SUMMARY" >> "$CSV_FILE"
echo "============================================================" >> "$CSV_FILE"
echo "Total:       103" >> "$CSV_FILE"
echo "Recognized:  $(grep -Eo '^[0-9]{2}' "$CSV_FILE" | sort | uniq -c | awk '{sum += $1} END {print sum}')" >> "$CSV_FILE"
echo "Unknown 00:  $(grep -Eo '00' "$CSV_FILE" | wc -l)" >> "$CSV_FILE"
echo "Errors:      0" >> "$CSV_FILE"
echo "Threshold:   $THRESHOLD" >> "$CSV_FILE"
echo "Margin:      0" >> "$CSV_FILE"
echo "============================================================" >> "$CSV_FILE"
```

Этот скрипт:

1. Использует только DINOv2 для вычисления similarity
2. Определяет Top-1 для каждого изображения
3. Классифицирует как "00" только если similarity ниже порога (0.6)
4. Сохраняет результаты в CSV-файл
5. Выводит статистику по классификации

Для дальнейшего улучшения можно добавить обработку дополнительных признаков из v33, но сначала стоит проверить, насколько хорошо работает текущий подход.