### 🧠 **Итог: Что делать дальше**

1. **Найди скрипты сортировки и распознавания**  
   Выполни команды ниже, чтобы понять, как устроена текущая система.

2. **Создай отдельную папку для теста**  
   Например: `output/visual_test_margin005/`

3. **Создай CSV-файл для отслеживания изменений**  
   Формат:
   ```csv
   image,old_winner,new_winner,margin,best_diff,changed
   ```

4. **Запусти тестовый прогон**  
   Используй текущий `v33`, но с ограничением на `margin < 0.010`.

---

### 🧪 **Команды для анализа текущей системы**

```bash
cd ~/projects/scene_fingerprint_mvp_v02

# 🔍 Найди скрипты сортировки и распознавания
echo "=== SORT / RECOGNIZE SCRIPTS ==="
find . -maxdepth 3 -type f \( \
    -name "*.py" -o \
    -name "*.sh" \
\) | sort | grep -Ei 'sort|classif|recogn|test|benchmark'

# 📁 Покажи структуру выходных директорий
echo
echo "=== OUTPUT DIRECTORIES ==="
find output -maxdepth 2 -type d | sort

# 🧠 Покажи команды распознавания и сортировки
echo
echo "=== CURRENT RECOGNITION COMMANDS IN PROJECT ==="
grep -RniE 'recognize|copy|shutil.copy|shutil.copy2|mkdir|makedirs' \
    --include="*.py" \
    --include="*.sh" \
    . 2>/dev/null | head -100
```

---

### 📁 **Пример структуры папок после теста**

```bash
output/visual_test_margin005/
├── 84_v33/
├── 87_v33/
├── 78_v33/
...
└── 95_v33/
```

---

### 📤 **Что делать после**

1. **Создай CSV-файл**  
   Пример:
   ```csv
   image,old_winner,new_winner,margin,best_diff,changed
   Ленина 125-127 А (8).JPG,87_v33,84_v33,0.005768,+0.0682,True
   Ленина 125-127 А (10).JPG,87_v33,84_v33,0.001876,+0.0538,True
   Ленина 125-127 А (14).JPG,87_v33,84_v33,0.001037,+0.0574,True
   ```

2. **Запусти тестовый прогон**  
   Используй текущий `v33`, но с ограничением на `margin < 0.010`.

3. **Сравни результаты**  
   Проверь, какие фотографии были изменены, и отправь папку с результатами на визуальный контроль.

---

### 🧩 **Как это будет выглядеть в коде (пример)**

```python
# Пример кода для тестового прогона
import os
import shutil

# Папка с исходными файлами
input_dir = "input/"
# Папка для теста
test_dir = "output/visual_test_margin005/"
# CSV-файл
csv_file = "output/visual_test_margin005.csv"

# Создание папок
os.makedirs(test_dir, exist_ok=True)

# Открытие CSV
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["image", "old_winner", "new_winner", "margin", "best_diff", "changed"])

# Обработка файлов
for filename in os.listdir(input_dir):
    if filename.endswith(".JPG"):
        # Получение данных (пример)
        margin = 0.005  # Замени на реальное значение
        best_diff = 0.0682  # Замени на реальное значение
        old_winner = "87_v33"
        new_winner = "84_v33"
        changed = margin < 0.005 and best_diff > 0.05

        # Копирование файла
        shutil.copy(os.path.join(input_dir, filename), os.path.join(test_dir, filename))

        # Запись в CSV
        with open(csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                filename,
                old_winner,
                new_winner,
                margin,
                best_diff,
                changed
            ])
```

---

### ✅ **Итог**

- Проведи тестовый прогон для 14 фотографий с `margin < 0.010`.
- Используй текущий `v33`, но с ограничением на `margin < 0.005`.
- Сохраняй результаты в отдельную папку и CSV-файл.
- После этого отправь папку с результатами на визуальный контроль.

Если хочешь, я могу помочь адаптировать существующий скрипт под этот тест.