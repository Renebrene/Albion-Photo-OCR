### 🧠 **Выводы и рекомендации**

#### 1. **Почему Hybrid не работает в текущем pipeline**
- **Текущий DINO worker** (в `dino_worker.py`) **не передаёт full top-5** в Hybrid.
- Он останавливается на `top1`, `top2`, `margin` и записывает их в БД.
- **Hybrid v12** требует **все 5 кандидатов** (top1–top5) для корректной работы.

#### 2. **Как исправить**
Чтобы **восстановить полный workflow**, нужно:
1. **Убедиться, что DINO выдаёт top-5** (проверить `recognizer.py`).
2. **Передать top-5 в Hybrid** (в `dino_worker.py` или в `run_hybrid_v12.py`).
3. **Обновить БД** чтобы хранить все поля, необходимые Hybrid (top1–top5, scores, margin, neighbors).

---

### 🛠️ **Шаги для исправления**

#### 1. **Проверить DINO output (recognizer.py)**
Найдите в `recognizer.py` (строки ~350–560) как `top_k=5` обрабатывается. Убедитесь, что:
- `candidates` содержит **все 5 кандидатов**.
- `top1`, `top2`, ..., `top5` вычисляются корректно.

#### 2. **Интеграция Hybrid в pipeline**
- **В `dino_worker.py`**:
  - Добавьте логику, чтобы **передавать top-5** в Hybrid.
  - Или **вызовите `hybrid_v12`** после DINO processing.
- **В `run_hybrid_v12.py`**:
  - Убедитесь, что `rows` содержит **все 5 кандидатов** для каждого изображения.

#### 3. **Обновление БД**
- Добавьте в таблицу `dino_fingerprint` поля:
  - `top2`, `top3`, `top4`, `top5`
  - `top2_score`, `top3_score`, `top4_score`, `top5_score`
  - `neighbors` (для consensus)
  - `hybrid_changed`, `hybrid_score`, `hybrid_old_score`, `hybrid_margin`

---

### 🧾 **Пример обновления БД**
```sql
ALTER TABLE dino_fingerprint
ADD COLUMN top2 TEXT,
ADD COLUMN top2_score FLOAT,
ADD COLUMN top3 TEXT,
ADD COLUMN top3_score FLOAT,
ADD COLUMN top4 TEXT,
ADD COLUMN top4_score FLOAT,
ADD COLUMN top5 TEXT,
ADD COLUMN top5_score FLOAT,
ADD COLUMN neighbors JSONB,
ADD COLUMN hybrid_changed BOOLEAN,
ADD COLUMN hybrid_score FLOAT,
ADD COLUMN hybrid_old_score FLOAT,
ADD COLUMN hybrid_margin FLOAT;
```

---

### 🔄 **Тестирование**
1. Запустите `run_hybrid_v12.py` с full top-5.
2. Проверьте, что `hybrid_score`, `hybrid_old_score`, `hybrid_margin` заполняются.
3. Убедитесь, что `best_id` корректно определяется с учётом:
   - Global top-5 scores
   - SUB check (только top1 и top2)
   - Neighbor consensus

---

### 🚀 **Итог**
- **Hybrid v12** — это **дополнительный слой**, который **не заменяет DINO**, но улучшает его решение.
- Для его работы **нужны full top-5** и **дополнительные данные** (neighbors, margin).
- **Текущий pipeline** обрывается на DINO, поэтому Hybrid не работает.
- **Исправление** требует:
  - Проверки DINO output
  - Передачи top-5 в Hybrid
  - Обновления БД
  - Тестирования

Если всё это сделано, **Hybrid v12** будет работать как ожидается, и `hybrid_*` поля заполнятся корректно.