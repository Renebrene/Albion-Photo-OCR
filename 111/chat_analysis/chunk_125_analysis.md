### 🔍 Шаг 1: Найдём код DINO-распознавания

Выполни команды ниже, чтобы получить информацию о коде DINO и его настройках:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ CLI ================" && \
grep -RniE \
"def recognize|recognize\(|add_parser.*recognize|top-k|fingerprints|batch|workers|ThreadPool|ProcessPool" \
app scripts \
--include="*.py" 2>/dev/null | head -250
```

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,260p' app/core/recognizer.py 2>/dev/null
```

Если `recognizer.py` окажется в другом месте — первая команда покажет где.

---

### 🔍 Шаг 2: Проверим, как DINO обрабатывает изображения

Если в коде есть `ThreadPool` или `ProcessPool`, то это уже многопоточная/многопроцессорная реализация. Если нет — это последовательная обработка.

Если в коде нет параметра `--workers`, то нужно понять, как изображения обрабатываются. Например:

- Если используется `ThreadPool`, то можно увеличить количество потоков.
- Если используется `ProcessPool`, то можно увеличить количество процессов.

---

### 🔍 Шаг 3: Проверим, как DINO работает с разным количеством воркеров

Если код поддерживает `--workers`, то запускай тесты:

```bash
# Тест с 1 воркером
scene-fingerprint recognize --workers=1 /data/input/daily/IMG_18452.JPG

# Тест с 2 воркерами
scene-fingerprint recognize --workers=2 /data/input/daily/IMG_18452.JPG

# Тест с 4 воркерами
scene-fingerprint recognize --workers=4 /data/input/daily/IMG_18452.JPG

# Тест с 6 воркерами
scene-fingerprint recognize --workers=6 /data/input/daily/IMG_18452.JPG

# Тест с 8 воркерами
scene-fingerprint recognize --workers=8 /data/input/daily/IMG_18452.JPG

# Тест с 12 воркерами
scene-fingerprint recognize --workers=12 /data/input/daily/IMG_18452.JPG
```

Если `--workers` не поддерживается, то нужно изменить код, чтобы добавить поддержку.

---

### 📊 Шаг 4: Измерим производительность

Создай файл `benchmark.sh` с командами для тестирования:

```bash
#!/bin/bash

# Папка с изображениями
INPUT_DIR="/data/input/daily"
OUTPUT_DIR="/data/output/benchmark"

# Убедимся, что папка существует
mkdir -p "$OUTPUT_DIR"

# Запишем время и количество изображений
echo "Starting benchmark..." > "$OUTPUT_DIR/benchmark.log"
echo "Workers | Time | CPU | RAM | Photos/sec" >> "$OUTPUT_DIR/benchmark.log"

# Тест с 1 воркером
echo "Testing with 1 worker..." >> "$OUTPUT_DIR/benchmark.log"
time scene-fingerprint recognize --workers=1 "$INPUT_DIR" >> "$OUTPUT_DIR/benchmark.log" 2>&1
echo "Done with 1 worker" >> "$OUTPUT_DIR/benchmark.log"

# Тест с 2 воркерами
echo "Testing with 2 workers..." >> "$OUTPUT_DIR/benchmark.log"
time scene-fingerprint recognize --workers=2 "$INPUT_DIR" >> "$OUTPUT_DIR/benchmark.log" 2>&1
echo "Done with 2 workers" >> "$OUTPUT_DIR/benchmark.log"

# Тест с 4 воркерами
echo "Testing with 4 workers..." >> "$OUTPUT_DIR/benchmark.log"
time scene-fingerprint recognize --workers=4 "$INPUT_DIR" >> "$OUTPUT_DIR/benchmark.log" 2>&1
echo "Done with 4 workers" >> "$OUTPUT_DIR/benchmark.log"

# Тест с 6 воркерами
echo "Testing with 6 workers..." >> "$OUTPUT_DIR/benchmark.log"
time scene-fingerprint recognize --workers=6 "$INPUT_DIR" >> "$OUTPUT_DIR/benchmark.log" 2>&1
echo "Done with 6 workers" >> "$OUTPUT_DIR/benchmark.log"

# Тест с 8 воркерами
echo "Testing with 8 workers..." >> "$OUTPUT_DIR/benchmark.log"
time scene-fingerprint recognize --workers=8 "$INPUT_DIR" >> "$OUTPUT_DIR/benchmark.log" 2>&1
echo "Done with 8 workers" >> "$OUTPUT_DIR/benchmark.log"

# Тест с 12 воркерами
echo "Testing with 12 workers..." >> "$OUTPUT_DIR/benchmark.log"
time scene-fingerprint recognize --workers=12 "$INPUT_DIR" >> "$OUTPUT_DIR/benchmark.log" 2>&1
echo "Done with 12 workers" >> "$OUTPUT_DIR/benchmark.log"

echo "Benchmark completed." >> "$OUTPUT_DIR/benchmark.log"
```

Запусти скрипт:

```bash
chmod +x benchmark.sh
./benchmark.sh
```

---

### 📊 Шаг 5: Анализ результатов

После выполнения тестов, посмотри файл `benchmark.log` и определи:

- Какое количество воркеров даёт наилучшую производительность.
- Какие параметры (время, CPU, RAM, фото/сек) наиболее важны для тебя.

---

### 📌 Вывод

После анализа кода и тестирования, ты сможешь определить оптимальное количество воркеров для DINO. Это поможет оптимизировать производительность системы без перегрузки оборудования.