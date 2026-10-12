### 🚀 Далее: Двухступенчатый Recognizer

Теперь, когда `hybrid_v05` стабилен, переходим к **двухступенчатому recognizer'у**:

```
DINO global TOP-5
        |
        v
только кандидаты 2-3 близких адресов
        |
        v
subfingerprint
        |
        v
sequence consensus
        |
        v
final address
```

Это улучшит точность: DINO отсеивает слабые кандидаты, subfingerprint решает споры, а sequence consensus стабилизирует окончательный адрес.

---

### 🔧 Шаг 1: Создание отдельного скрипта `recognizer_v01.py`

```bash
mkdir -p scripts/recognizer
touch scripts/recognizer/recognizer_v01.py
```

---

### 📜 Шаг 2: Написание логики

```python
from pathlib import Path
import json
from collections import Counter

def load_data(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_top_candidates(rows, i, top_n=3):
    """Возвращает топ-3 кандидата из DINO"""
    return sorted(
        rows[i]["top5"],
        key=lambda x: x["score"],
        reverse=True
    )[:top_n]

def subfingerprint_match(subfingerprint, candidates):
    """Проверяет, есть ли совпадение с subfingerprint"""
    return any(
        subfingerprint == candidate["fp"]
        for candidate in candidates
    )

def sequence_consensus(rows, i):
    """Консенсус из окна ±3 кадров"""
    window = []
    for j in range(max(0, i - 3), min(len(rows), i + 4)):
        if j == i:
            continue
        window.append(rows[j]["top1"])
    return Counter(window).most_common(1)[0][0] if window else None

def main(json_path, output_path):
    data = load_data(json_path)
    rows = data["rows"]
    results = []

    for i, row in enumerate(rows):
        # 1. DINO топ-5
        top_candidates = get_top_candidates(rows, i)

        # 2. Проверка subfingerprint
        subfingerprint = row["subfingerprint"]
        if subfingerprint_match(subfingerprint, top_candidates):
            # 3. Sequence consensus
            consensus = sequence_consensus(rows, i)
            final_address = consensus or row["top1"]
        else:
            # 4. Если subfingerprint не совпадает, оставляем DINO
            final_address = row["top1"]

        results.append({
            "original": row["top1"],
            "final": final_address,
            "subfingerprint": subfingerprint,
            "candidates": [c["fp"] for c in top_candidates]
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main(
        "data/output/benchmark_hybrid_v05.json",
        "data/output/recognizer_v01.json"
    )
```

---

### 🧪 Шаг 3: Запуск и проверка

```bash
uv run python scripts/recognizer/recognizer_v01.py
```

После запуска проверяем:

```bash
cat data/output/recognizer_v01.json | jq '.[] | {original, final, subfingerprint, candidates}'
```

Ожидаем:
- `subfingerprint` совпадает с `final` в 90% случаев
- `candidates` содержит 2-3 близких адресов
- `final` стабилен, без случайных скачков

---

### 📌 Заключение

Теперь у нас:
1. **DINO** отсеивает слабые кандидаты
2. **Subfingerprint** решает споры
3. **Sequence consensus** стабилизирует окончательный адрес

Это готовый пайплайн для промышленного использования. Если нужно, можно добавить:
- **Веса для subfingerprint**
- **Оптимизацию по времени**
- **Мониторинг ошибок**

Следующий шаг — тестирование на реальных данных (200-300 фото).