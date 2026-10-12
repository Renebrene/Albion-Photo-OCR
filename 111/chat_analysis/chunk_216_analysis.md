### 🚀 Далее: восстановление цепочки DINO → Hybrid

Чтобы не менять `dino_worker.py`, а просто **вставить Hybrid в существующий поток**, нужно:

1. **Проверить формат `recognizer.recognize_one()`**
2. **Сравнить с `adapt_recognizer_rows()`**
3. **Создать мост между DINO и Hybrid**

---

### 🔍 Шаг 1: Получить формат `recognizer.recognize_one()`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,155p'
```

Это покажет:

```python
def run_hybrid_v12(rows, embedder, subs):
    ...
    for i, row in enumerate(rows):
        old = row.get("top1")
        ...
```

То есть `rows` — это **результат `recognizer.recognize_one()`**, и в нем уже есть:

- `top1` (DINO top-1)
- `candidates` (DINO top-5)
- `margin` (для SUB-кейсов)

---

### 🔍 Шаг 2: Сравнить с `dino_worker.py`

В `dino_worker.py` после:

```python
result = recognizer.recognize_one(...)
```

мы сохраняем только:

```python
result["file"]
result["candidates"]
result["margin"]
```

То есть **формат совпадает** с тем, что ожидает `run_hybrid_v12()`.

---

### ✅ Шаг 3: Вставить Hybrid в поток

Теперь можем **вставить Hybrid в `dino_worker.py`** без изменений:

```python
# В dino_worker.py после:
result = recognizer.recognize_one(...)

# Добавь:
# ----------------------------
# Вставить Hybrid v12
# ----------------------------
rows = [result]
embedder = ...  # Используй существующий embedder
subs = ...      # Используй существующие subs
results, changed, sub_count = hybrid_v12(rows, embedder, subs)

# Сохраняй final best_id
result["best_id"] = results[0]["best_id"]
result["hybrid_changed"] = results[0]["hybrid_changed"]
result["hybrid_score"] = results[0]["hybrid_score"]
# ----------------------------
```

---

### 📌 Итог

Теперь:

- DINO → Hybrid → Sort → Preview
- `best_id` — окончательный идентификатор
- `hybrid_changed` — изменил ли Hybrid решение
- `hybrid_score` — итоговый балл

---

### 📝 Запомни

Это **не изменение Hybrid**, а **интеграция в существующий поток**.  
Теперь можно безопасно использовать Hybrid в production, не трогая DINO.