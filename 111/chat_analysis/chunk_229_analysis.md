### ✅ **Далее: встраиваем сохранение Hybrid в production-поток**

---

### 🔍 **1. Содержимое `run_daily_hybrid_v12.sh`**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DAILY HYBRID SCRIPT ================" && \
nl -ba scripts/run_daily_hybrid_v12.sh | sed -n '1,180p'
```

---

### 🔍 **2. Кто запускает `run_daily_hybrid_v12.sh`?**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DAILY HYBRID CALLERS ================" && \
grep -RniE \
'run_daily_hybrid_v12\.sh|run_daily_hybrid' \
scripts app \
--include="*.py" \
--include="*.sh" \
| head -200
```

---

### ✅ **После этого — минимальный патч**

После получения ответов, я предложу **точный патч** для `run_daily_hybrid_v12.sh`, который:

1. Добавит сохранение `best_id` → `hybrid_final_id`
2. Добавит сохранение `original_best_id` → `hybrid_original_id`
3. Оставит Hybrid v12 без изменений

---

### 🧠 **Почему именно так?**

- **Физические файлы не копируются** — мы используем виртуальную сортировку.
- **Hybrid v12 не меняется** — мы только сохраняем результат.
- **Динамическая сортировка** через `hybrid_final_id` работает как виртуальный адрес.

---

### 🧾 **Пример патча для `run_daily_hybrid_v12.sh`**

```bash
# Добавляем после генерации hybrid_v12.json
python scripts/save_hybrid_to_db.py \
    --input "$OUTPUT/hybrid_v12.json" \
    --db "postgresql://lora@localhost/photobase"
```

И создаем `save_hybrid_to_db.py`:

```python
import json
import psycopg2
from pathlib import Path

def main():
    input_path = Path("hybrid_v12.json")
    data = json.loads(input_path.read_text(encoding="utf-8"))

    conn = psycopg2.connect(
        dbname="photobase",
        user="lora",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()

    for row in data:
        file = row["file"]
        original_best_id = row["original_best_id"]
        best_id = row["best_id"]

        # Ищем photo_id по source_path
        cur.execute("""
            SELECT photo_id
            FROM photos
            WHERE source_path = %s
        """, (file,))

        photo_id = cur.fetchone()

        if photo_id:
            cur.execute("""
                UPDATE photos
                SET
                    hybrid_final_id = %s,
                    hybrid_original_id = %s
                WHERE photo_id = %s
            """, (best_id, original_best_id, photo_id[0]))

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
```

---

### 🚀 **Итог**

Этот патч:

- Не меняет Hybrid v12
- Сохраняет результат в PostgreSQL
- Поддерживает виртуальную сортировку
- Не копирует файлы

Теперь `hybrid_final_id` будет корректно отображать финальный результат сортировки, а `dino_fingerprint` останется как исходный результат для возможного пересчёта.