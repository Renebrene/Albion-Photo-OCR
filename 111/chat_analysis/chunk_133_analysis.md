### ✅ **Все готово к тесту 1 DINO + Qwen**

#### 📌 **Проверка количества фото в `data/input/daily`**
```bash
cd ~/projects/scene_fingerprint_mvp_v02

find data/input/daily -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l
```

Если выведет **526**, запускаем тест.

---

### 🚀 **Тест A: 1 DINO + 1 Qwen (параллельно)**

#### 🧠 **Терминал 1 — DINO (CPU)**
```bash
cd ~/projects/scene_fingerprint_mvp_v02

time env DINO_MAX_ITEMS=526 \
uv run python -u app/workers/dino_worker.py
```

#### 🧠 **Терминал 2 — Qwen (GPU)**
```bash
cd ~/projects/scene_fingerprint_mvp_v02

time uv run python -u scripts/qwen4b_output_v01.py \
  --input data/input/daily \
  --limit 526 \
  --output data/metadata/qwen4b/test_parallel_1dino
```

---

### 🚀 **Тест B: 2 DINO + 1 Qwen (параллельно)**

#### 🧠 **Терминал 1 — DINO #1 (CPU)**
```bash
cd ~/projects/scene_fingerprint_mvp_v02

time env DINO_MAX_ITEMS=0 \
uv run python -u app/workers/dino_worker.py
```

#### 🧠 **Терминал 2 — DINO #2 (CPU)**
```bash
cd ~/projects/scene_fingerprint_mvp_v02

time env DINO_MAX_ITEMS=0 \
uv run python -u app/workers/dino_worker.py
```

#### 🧠 **Терминал 3 — Qwen (GPU)**
```bash
cd ~/projects/scene_fingerprint_mvp_v02

time uv run python -u scripts/qwen4b_output_v01.py \
  --input data/input/daily \
  --limit 526 \
  --output data/metadata/qwen4b/test_parallel_2dino
```

---

### 📊 **Мониторинг ресурсов (в отдельном терминале)**

```bash
watch -n 1 '
echo "===== GPU ====="
nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu \
--format=csv,noheader
echo
echo "===== CPU ====="
top -bn1 | grep "Cpu(s)"
'
```

---

### 📌 **Что мы будем сравнивать**
| Режим | DINO | Qwen | Цель |
|---|---:|---:|---|
| A | 1 | 1 | Базовый параллельный режим |
| B | 2 | 1 | Оптимизация производительности |

---

### 📌 **Что делать после теста**
1. Проверь, сколько фото обработал DINO в каждом случае.
2. Сравни время выполнения и загрузку GPU/CPU.
3. Отправь выводы — я помогу выбрать оптимальный режим.