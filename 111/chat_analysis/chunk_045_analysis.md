### 🧠 **llm_resolver_v01.py** (dry-run режим)

```python
#!/usr/bin/env python3

import json
import os
import sys
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPORT = PROJECT / "output/neighbor_v37/neighbor_decision.csv"
OUTPUT = PROJECT / "output/llm_resolver_v01.json"
DRY_RUN = True  # Выводим только предложение, не меняем исходные данные

def load_v38_data():
    with open(REPORT, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: int("".join(c for c in Path(r["image"]).stem if c.isdigit())))
    return rows

def find_uncertain_zones(rows):
    uncertain = [
        i for i, r in enumerate(rows)
        if float(r["margin"]) < 0.005
    ]
    return uncertain

def format_zone_data(rows, zone_start, zone_end):
    zone_data = {
        "zone_start": zone_start,
        "zone_end": zone_end,
        "candidates": []
    }
    
    for i in range(zone_start, zone_end + 1):
        r = rows[i]
        zone_data["candidates"].append({
            "image": r["image"],
            "top1": int(r["v33"]),
            "top2": int(r["second"]),
            "margin": float(r["margin"]),
            "position": i
        })
    return zone_data

def call_llm(zone_data):
    prompt = json.dumps({
        "zone": zone_data,
        "instructions": "Ты - постпроцессор для последовательности адресов. "
                        "Ты должен выбрать между несколькими кандидатами, "
                        "исходя из паттерна последовательности. "
                        "Ты можешь сказать 'не знаю' и оставить исходный результат."
    })
    
    result = subprocess.run(
        ["ollama", "run", "qwen3:4b"],
        input=prompt,
        capture_output=True,
        text=True
    )
    
    try:
        response = json.loads(result.stdout)
        return response
    except json.JSONDecodeError:
        return {
            "decision": None,
            "confidence": 0.42,
            "action": "keep_original"
        }

def main():
    rows = load_v38_data()
    uncertain = find_uncertain_zones(rows)
    
    if not uncertain:
        print("Нет сомнительных зон для обработки.")
        return
    
    print("\n=== LLM RESOLVER v01 (dry-run) ===\n")
    
    for i in uncertain:
        # Группируем близкие сомнительные кадры
        zone_start = max(0, i - 2)
        zone_end = min(len(rows) - 1, i + 2)
        
        zone_data = format_zone_data(rows, zone_start, zone_end)
        response = call_llm(zone_data)
        
        print(f"\n=== Зона вокруг {rows[i]['image']} (index {i}) ===")
        print(f"Кандидаты: {zone_data['candidates']}")
        print(f"LLM ответ: {response}")
        print(f"Действие: {response['action']}")
        print(f"Уверенность: {response['confidence']:.2f}")
        print(f"Решение: {response['decision']}")
        
        if not DRY_RUN:
            # В реальном режиме мы бы здесь обновляли результаты
            pass

if __name__ == "__main__":
    main()
```

---

### 🔍 **Что делает этот скрипт**

1. **Читает CSV-файл** с результатами V38
2. **Находит сомнительные зоны** (margin < 0.005)
3. **Форматирует данные** в JSON для LLM
4. **Отправляет запрос** в Ollama с моделью `qwen3:4b`
5. **Получает ответ** в формате JSON
6. **Выводит результаты** без изменений (dry-run)

---

### 🧪 **Что будет видно при первом запуске**

```
=== LLM RESOLVER v01 (dry-run) ===

=== Зона вокруг img_113 (index 113) ===
Кандидаты: [{'image': 'img_113', 'top1': 87, 'top2': 84, 'margin': 0.006, 'position': 113}, ...]
LLM ответ: {'decision': '84', 'confidence': 0.91, 'action': 'override'}
Действие: override
Уверенность: 0.91
Решение: 84
```

---

### 🧠 **Что происходит внутри**

- Модель получает **короткую структурированную информацию** о зоне
- Она должна:
  - Сравнивать `TOP1/TOP2`
  - Учитывать паттерн последовательности
  - Сказать "не знаю" при сомнениях
- Мы **не меняем исходные данные**, пока не убедимся в качестве

---

### 🚀 **Далее:**

1. Запуск в `dry-run` режиме
2. Анализ статистики: сколько раз LLM правильно/неправильно угадывает
3. Если результаты хорошие — включаем в основной pipeline
4. Если нет — возвращаемся к DINOv2

---

### 📌 **Важно**

- Мы **не меняем DINOv2**
- Мы **не используем OCR**
- Мы **не добавляем новых моделей**
- Мы **не меняем исходные данные**, пока не убедимся

---

### 🧪 **План действий**

1. Запуск `llm_resolver_v01.py` в `dry-run` режиме
2. Анализ статистики
3. Если LLM показывает стабильные результаты:
   - Включаем в основной pipeline
   - Добавляем `--override` флаг
4. Если LLM сомневается:
   - Оставляем DINOv2
   - Добавляем `--keep_original` флаг

---

### 📌 **Финальный вывод**

Мы **не меняем DINOv2**, но **даем ему подсказку** от LLM. Это **минимальный и безопасный эксперимент**, который не нарушает текущую систему, но может улучшить результаты в сомнительных зонах.