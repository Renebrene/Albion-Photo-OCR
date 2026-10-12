### ✅ **Шаг 1: Пересоздание слепков 78–95**

Выполни команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for n in $(seq 78 95); do
    echo
    echo "============================================================"
    echo "CREATING ${n}_v33"
    echo "============================================================"

    rm -rf "data/fingerprints/${n}_v33"

    uv run scene-fingerprint create \
        "${n}_v33" \
        "data/input/${n}" || exit 1
done
```

---

### 🔍 **Шаг 2: Проверка наличия слепков**

После выполнения вышеуказанного, запусти:

```bash
echo
echo "============================================================"
echo "=== FINGERPRINT CHECK ==="
echo "============================================================"

for n in $(seq 78 95); do
    p="data/fingerprints/${n}_v33"

    if [ -f "$p/metadata.json" ]; then
        printf "%-12s OK\n" "${n}_v33"
    else
        printf "%-12s ERROR\n" "${n}_v33"
    fi
done
```

**Ожидаемый вывод:**
```
78_v33     OK
79_v33     OK
...
95_v33     OK
```

---

### 🧪 **Шаг 3: Проверка версий и количества изображений**

Запусти:

```bash
python3 - <<'PY'
from pathlib import Path
import json

print("=" * 70)
print("FINGERPRINTS")
print("=" * 70)

for n in range(78, 96):
    p = Path(f"data/fingerprints/{n}_v33/metadata.json")

    if not p.exists():
        print(f"{n}_v33 ERROR: metadata missing")
        continue

    d = json.loads(p.read_text(encoding="utf-8"))

    print(
        f"{n}_v33: "
        f"images={len(d.get('image_names', []))} "
        f"version={d.get('version')}"
    )
PY
```

**Ожидаемый вывод:**
```
============================================================
FINGERPRINTS
============================================================
78_v33: images=100 version=3.3
79_v33: images=100 version=3.3
...
95_v33: images=100 version=3.3
```

---

### 🚀 **Шаг 4: Распознавание (только если всё OK)**

Если всё прошло успешно, запускаем распознавание **только по слепкам 78–95** и сохраняем чистый JSON:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

# Удаляем старый JSON
rm -f final_test_78_95.json

# Запускаем распознавание
uv run scene-fingerprint classify \
    --input data/input/test \
    --fingerprints data/fingerprints/78_v33 data/fingerprints/79_v33 ... data/fingerprints/95_v33 \
    --output final_test_78_95.json
```

**Важно:**  
- Убедись, что в `--fingerprints` указаны **все 18 слепков** (78–95).  
- Вывод будет чистым JSON без логов `[SceneEmbedder]`, так как скрипт `scene-fingerprint classify` устроен корректно.

---

### 📁 **Шаг 5: Копирование результатов**

После распознавания запусти:

```bash
python3 - <<'PY'
from pathlib import Path

OUTPUT = Path("data/output/test_classified")

for n in range(78, 96):
    folder = f"{n}_v33"
    src = Path(f"data/input/test/{n}_v33/*.JPG")
    dst = OUTPUT / folder

    for file in src.glob("*"):
        shutil.copy2(file, dst)
PY
```

---

### 📌 **Финал**

Теперь у тебя:
1. **Новые слепки** 78–95 (`v33`)  
2. **Чистый JSON** `final_test_78_95.json`  
3. **Копии распознанных изображений** в `data/output/test_classified/78 ... 95`  

Если всё прошло успешно, можно приступать к визуальной проверке.