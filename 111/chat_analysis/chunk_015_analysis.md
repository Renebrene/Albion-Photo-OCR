### ✅ Шаг 1: Проверка существования папок

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for n in {84..95}; do
    echo -n "$n : "
    if [ -d "data/input/$n" ]; then
        find "data/input/$n" -maxdepth 1 -type f | wc -l
    else
        echo "NO FOLDER"
    fi
done
```

**Ожидаемый вывод:**

```text
84 : 123
85 : 145
86 : 102
87 : 98
88 : 115
89 : 130
90 : 120
91 : 110
92 : 105
93 : 95
94 : 100
95 : 115
```

---

### ✅ Шаг 2: Создание слепков `*_v33`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for n in {84..95}; do
    if [ -d "data/input/$n" ]; then
        echo
        echo "========================================"
        echo "CREATING FINGERPRINT ${n}_v33"
        echo "========================================"

        uv run scene-fingerprint create \
            "${n}_v33" \
            "data/input/$n"

    else
        echo "SKIP $n — data/input/$n does not exist"
    fi
done
```

**Проверка успешности:**

```bash
find data/fingerprints -maxdepth 1 -type d -name '*_v33' -printf '%f\n' | sort -V
```

**Ожидаемый вывод:**

```text
78_v33
79_v33
80_v33
81_v33
82_v33
83_v33
84_v33
85_v33
86_v33
87_v33
88_v33
89_v33
90_v33
91_v33
92_v33
93_v33
94_v33
95_v33
```

---

### ✅ Шаг 3: Запуск классификации с фокусом на первого кандидата

Используй обновлённый `classify_test.py` (уже с исправленным `FingerprintManager`) и запуск:

```bash
uv run python classify_test.py
```

**Важно:**  
- Скрипт будет использовать **первого кандидата** (максимальный `final_score`).  
- Если `confidence` слишком низкая — ставится `00`.  
- Все фотографии будут распределены по папкам:  
  ```text
  data/output/test_classified/
  ├── 00/
  ├── 84/
  ├── 85/
  ├── 86/
  ...
  └── 95/
  ```

---

### ✅ Шаг 4: Анализ CSV

После завершения:

```bash
ls data/output/test_classified/results.csv
```

**Пример строки CSV:**

```text
file,classification,best_id,score,second_score,margin,confidence,status,best_image,output
image_001.jpg,84,84_v33,0.987654,0.123456,0.864198,HIGH,OK,84_v33/scene_001.jpg,test_classified/84/image_001.jpg
```

**Что делать дальше:**

1. **Проверь порог уверенности** (например, `threshold=0.8`) в `classify_test.py`.  
2. **Отфильтруй `00`** в CSV, чтобы увидеть, какие фотографии не распознаны.  
3. **Повтори классификацию** с другими параметрами, если нужно.

---

### 📌 Важно

- **Patch-файлы (`78_patch`, `84_patch` и т.п.) не используются.**  
- **Все работы сохраняются в оригинальных папках.**  
- **CSV и отсортированные папки с результатами** — это основа для дальнейшего анализа.

Если возникнут ошибки или потребуется настройка порога, просто пришли вывод `classify_test.py` и я помогу настроить.