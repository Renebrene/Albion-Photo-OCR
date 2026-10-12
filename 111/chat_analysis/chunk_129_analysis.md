### ✅ **Проверка оборудования и настройка DINO/Qwen**

---

## 🧠 1. Проверка DINO на CPU

### 🔍 Шаг 1: Найдите конфигурацию DINO

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE "device|cuda|torch.device" app/core app --include="*.py" 2>/dev/null | head -100
```

Если в коде есть:

```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
```

и ты хочешь **ограничить DINO только на CPU**, замени на:

```python
device = torch.device("cpu")
```

Или, если хочешь **ограничить использование GPU только для Qwen**, оставь как есть.

---

## 🧠 2. Проверка Qwen на GPU

### 🔍 Шаг 2: Проверь, запущен ли Qwen на GPU

Выполни:

```bash
nvidia-smi
```

и:

```bash
ollama ps
```

Если Qwen не использует GPU, убедись, что:

1. Установлен Ollama с поддержкой GPU.
2. Запущен с флагом `--gpu` или `--device` (если поддерживается).
3. Модель Qwen3-VL-4B-Instruct загружена на GPU.

Если всё не работает, попробуй:

```bash
ollama run qwen3-vl:4b-instruct --device cuda
```

---

## 🧠 3. Проверка обработки одной фотографии

### 🔍 Шаг 3: Проверь, как DINO обрабатывает файл

В `app/core/scene_embedder.py` или аналогичном месте, найди код, где DINO обрабатывает изображение. Убедись, что:

- Файл загружается из `source_path`.
- Обработка происходит на CPU.
- Результат сохраняется в `dino_result` и `dino_score`.

Пример:

```python
from PIL import Image
import torch

def process_dino(photo_id):
    source_path = get_source_path(photo_id)
    image = Image.open(source_path).convert("RGB")
    image = transform(image).unsqueeze(0).to("cpu")
    with torch.no_grad():
        result = model(image)
    save_result(photo_id, result, "dino")
```

---

## 🧠 4. Проверка Qwen на GPU

### 🔍 Шаг 4: Проверь, как Qwen обрабатывает файл

Если Qwen через Ollama, убедись, что:

- Запущен с GPU.
- Модель Qwen3-VL-4B-Instruct загружена на GPU.
- Результаты сохраняются в `qwen_result` и `qwen_confidence`.

Пример:

```bash
ollama run qwen3-vl:4b-instruct --device cuda
```

---

## 🧠 5. Проверка обработки одной фотографии

### 🔍 Шаг 5: Проверь, как обрабатываются данные

После обработки одной фотографии, убедись, что:

- `dino_status` становится `ok`.
- `qwen_status` становится `ok`.
- `sort_status` и `preview_status` остаются `pending`.

Пример:

```sql
SELECT * FROM photos WHERE photo_id = 'PH_00000527';
```

---

## 🧠 6. Запуск worker

### 🔍 Шаг 6: Запусти worker

Теперь можно запустить `photo_worker.py`, который будет обрабатывать фотографии по одному:

```bash
python scripts/photo_worker.py
```

Он будет:

1. Найти одну фотографию с `dino_status = 'pending'`.
2. Обработать её на CPU.
3. Сохранить результат.
4. Перейти к следующей.

---

## 🧠 7. Проверка работы

### 🔍 Шаг 7: Проверь, что всё работает

После запуска worker, проверь:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c "
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE dino_status = 'ok') AS dino_ok,
    COUNT(*) FILTER (WHERE qwen_status = 'ok') AS qwen_ok
FROM photos;
"
```

Если всё работает, ты увидишь:

```text
 total | dino_ok | qwen_ok
-------+---------+---------
  526  |     1   |     1
```

и так далее, пока не обработаются все 526 фотографий.

---

## 🧠 8. Далее: сортировка и preview

### 🔍 Шаг 8: Добавь сортировку и preview

После DINO и Qwen, добавь:

1. **Сортировка** (по `sort_status`).
2. **Preview** (по `preview_status`).

Каждый шаг будет обрабатывать только одну фотографию, и только после завершения предыдущего шага.

---

### ✅ Итог

Теперь у тебя:

- DINO работает на CPU.
- Qwen работает на GPU.
- Worker обрабатывает фотографии по одному.
- ID фотографии не меняется.
- Все результаты сохраняются в базе.

Ты готов к следующему шагу: **настройке сортировки и preview**.