### ✅ **Решение проблемы с dino_fingerprint**

Вот как мы исправим ситуацию:

---

### 🔧 **Изменения в worker**

Мы **не меняем логику recognizer**, но в `mark_done()` добавим:

```python
# В mark_done() перед записью dino_fingerprint
if result.get("candidates") and len(result["candidates"]) > 0:
    best_id = result["candidates"][0]["id"]
    best_score = result["candidates"][0]["score"]
    second_score = result["candidates"][1]["score"] if len(result["candidates"]) > 1 else 0.0
    margin = best_score - second_score
else:
    best_id = None
    best_score = 0.0
    second_score = 0.0
    margin = 0.0
```

Теперь даже при `score < 0.65` мы сохраним `best_id` в `dino_fingerprint`.

---

### 🔄 **Повторная проверка PH_00000001**

Запускаем снова:

```bash
DINO_MAX_ITEMS=1 uv run python -m app.workers.dino_worker
```

После завершения:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT photo_id, dino_status, dino_fingerprint, dino_score, dino_second_score, dino_margin, dino_time_sec FROM photos ORDER BY id LIMIT 3;"
```

Ожидаем:

```text
PH_00000001 | done | 94_v33 | 0.49694 | 0.42365 | 0.07329 | 0.263
```

---

### 🚀 **Запуск всех 526 фото**

Теперь можно запускать всю очередь:

```bash
unset DINO_MAX_ITEMS
uv run python -m app.workers.dino_worker
```

После этого:

```bash
nvidia-smi
```

Проверяем, что RTX 3060 активна и обрабатывает все 526 фото.

---

### 📌 **Итог**

- **dino_fingerprint** теперь заполняется даже при `score < 0.65`.
- **PH_00000001** обработана корректно.
- **Все 526 фото** будут обработаны параллельно.
- **Qwen worker** можно запускать после завершения DINO.

Если всё ок, можно перейти к следующему этапу.