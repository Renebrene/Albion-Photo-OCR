### 🧠 **Анализ данных и следующие шаги**

#### 1. **Проверка сохранения JSON-отчётов**
Сначала убедимся, что отчёты были сохранены в правильных форматах. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

ls -lh data/output/test_classified/*.json
ls -lh data/output/test_classified/*.csv
```

Если отчёты есть, мы можем сразу приступить к анализу. Если нет — проверь, не завершился ли скрипт с ошибкой.

---

#### 2. **Получение и анализ отчётов**
После подтверждения сохранения запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

# Показываем структуру отчётов
find data/output/test_classified -type f -name '*.json' -exec ls -l {} \;

# Показываем содержимое JSON-отчёта
cat data/output/test_classified/final_test_78_95.json | jq .
```

Если `jq` не установлен, установи его:

```bash
sudo apt install jq
```

---

#### 3. **Ключевые метрики для анализа**
В отчёте ищем:

- **`status`**: `NO_MATCH`, `HIGH`, `PROBABLE`, `AMBIGUOUS` — это ключевые признаки ошибок.
- **`score`** и **`margin`**: 
  - `score` — уверенность в первом кандидате.
  - `margin` — разница между первым и вторым кандидатом.
- **`candidate_2`, `candidate_3`** и т.д. — проверяем, есть ли правильный адрес среди кандидатов.

Пример анализа:

```bash
grep -E 'status|score|margin|candidate_' data/output/test_classified/final_test_78_95.json | jq .
```

---

#### 4. **Построение матрицы ошибок**
Создадим матрицу, где по оси X — предсказанные адреса, по оси Y — реальные адреса. Это покажет, где система путает адреса.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

# Генерируем матрицу ошибок
python scripts/sort_test_and_report_v2.py --matrix
```

Если скрипт не работает, вручную построим матрицу из JSON:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

# Извлекаем уникальные адреса
grep -Eo '"real": "[^"]+"' data/output/test_classified/final_test_78_95.json | cut -d '"' -f 4 | sort | uniq > unique_addresses.txt

# Строим матрицу
while read -r real; do
    while read -r predicted; do
        echo -e "$real\t$predicted"
    done < unique_addresses.txt
done < unique_addresses.txt > matrix.txt
```

---

#### 5. **Ключевые вопросы для анализа**
- **Какие адреса чаще всего путаются?** (например, 83 ↔ 81)
- **Почему правильный адрес не попадает в топ-1?** (низкий `score`, маленький `margin`)
- **Какие `NO_MATCH` имеют высокий `score`?** (например, `score=0.7`, `margin=0.001`)
- **Какой адрес имеет наибольшее количество ошибок?** (например, 94 → 24, но 94_v33_fast → 12)

---

#### 6. **Дополнительный анализ**
Если есть время, можно добавить:

```bash
# Средние значения
grep -E 'score|margin' data/output/test_classified/final_test_78_95.json | jq 'mean(.score), mean(.margin)'
```

---

### 🚀 **Далее:**
1. **Проверь, какие адреса чаще всего ошибаются.**
2. **Определи, почему правильный адрес не попадает в топ-1.**
3. **Проверь, не нужно ли перенастроить `threshold` или улучшить модель.**

Если хочешь, я могу помочь с конкретным анализом — например, построить матрицу или посчитать статистику.