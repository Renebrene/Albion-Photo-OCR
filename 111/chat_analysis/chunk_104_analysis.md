### 🧠 **Решение: Интеграция Hybrid v12 в production-поток без изменения существующего кода**

#### 📌 **Цель**
Использовать Hybrid v12 для принятия окончательного решения о `best_id`, не меняя логику DINO v33 и существующего sorter'а.

---

### 🚀 **Шаги интеграции**

#### 1. **Сбор данных от DINO v33**
- В `run_recognition()` сохраняем не только `best_id`, но и `top1..top5` + `margin`:
  ```python
  data = find_json(combined)
  ```

#### 2. **Формирование входного JSON для Hybrid v12**
- Создаем `benchmark.json` из `data`, как в `benchmark_hybrid_v12_full.py`:
  ```python
  with open(BENCHMARK, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
  ```

#### 3. **Запуск Hybrid v12**
- Выполняем команду:
  ```bash
  scene-fingerprint hybrid --json benchmark.json --output hybrid_output.json
  ```

#### 4. **Парсинг результата Hybrid v12**
- Читаем `hybrid_output.json` и извлекаем `new` (окончательный `best_id`):
  ```python
  with open("hybrid_output.json", "r") as f:
      hybrid_result = json.load(f)
  final_best_id = hybrid_result["new"]
  ```

#### 5. **Интеграция в существующий workflow**
- Заменяем `assigned_id = item.get("best_id")` на:
  ```python
  assigned_id = final_best_id
  ```

---

### 📁 **Структура проекта (рекомендуемая)**

```
app/
├── pipeline/
│   ├── recognition.py       # DINO v33
│   ├── hybrid.py            # Hybrid v12
│   └── sorter.py            # Существующий sorter
├── data/
│   ├── input/
│   ├── output/
│   └── benchmark.json
└── utils/
    └── find_json.py         # Для парсинга JSON из stdout
```

---

### 🧪 **Тестирование**
1. Запуск DINO v33:
   ```bash
   scene-fingerprint recognize --json input_dir --output benchmark.json
   ```
2. Запуск Hybrid v12:
   ```bash
   scene-fingerprint hybrid --json benchmark.json --output hybrid_output.json
   ```
3. Проверка `hybrid_output.json` на наличие `new` (окончательный `best_id`).

---

### 📝 **Важно**
- **Не меняем веса, пороги, rules Hybrid v12** — оставляем их как есть.
- **Не модифицируем `sort_test_and_report_v2.py`** — он остаётся рабочим.
- **Все метрики и отчёты остаются без изменений**.

---

### 📌 **Финальный вывод**
Этот подход позволяет:
- Использовать Hybrid v12 для улучшения точности выбора `best_id`.
- Сохранить существующий workflow и отчёты.
- Избежать изменения DINO v33 и sorter'а.

Теперь вы можете запускать Hybrid v12 как отдельный этап в production-потоке без риска нарушить существующую логику.