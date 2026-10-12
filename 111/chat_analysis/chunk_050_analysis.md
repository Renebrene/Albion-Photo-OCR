### ✅ **Итоговая структура проекта после очистки**

```
scene_fingerprint_mvp_v02/
│
├── data/
│   ├── input/
│   │   └── .gitkeep
│   └── fingerprints/
│       ├── 78_v33
│       ├── 79_v33
│       ├── ...
│       └── 95_v33
│
├── output/
│   └── .gitkeep
│
├── scripts/
│   ├── benchmark_test_v1.py
│   ├── sort_sequence_v38_1.py
│   ├── analyze_subfingerprints.py
│   ├── export_subclusters.py
│   └── build_margin_best_from_benchmark.py
│
├── pyproject.toml
├── uv.lock
└── README.md
```

---

### 🔧 **Действия для выполнения**

#### 1. **Удалить `data/input/test_img` и `data/input/new`**
```bash
cd ~/projects/scene_fingerprint_mvp_v02

# Удалить папки
rm -rf data/input/test_img
rm -rf data/input/new

# Оставить .gitkeep в папке input
touch data/input/.gitkeep
```

---

#### 2. **Оставить только последние `fingerprints` (v33)**
Предположим, что "последние v33" — это папки с названиями вида `78_v33`, `79_v33`, и т.д. Убедитесь, что в `data/fingerprints/` осталось только эти папки.

```bash
cd data/fingerprints

# Удалить старые версии (если они есть)
# Пример: удаляем папки, которые не соответствуют v33
rm -rf 78
rm -rf 78_patch
rm -rf 78_v3
rm -rf 78_v31
rm -rf 78_v32
rm -rf 84_v34_test
rm -rf 84_v35_test
```

Проверка:
```bash
ls -la
```

---

#### 3. **Очистить `output` и оставить `.gitkeep`**
```bash
cd output

# Удалить всё содержимое
rm -rf *

# Оставить .gitkeep
touch .gitkeep
```

---

#### 4. **Проверить структуру и размер папок**
```bash
cd ~/projects/scene_fingerprint_mvp_v02

# Проверить структуру
tree -L 2 -d

# Проверить размер папок
du -h --max-depth=2 | sort -h
```

---

### 📁 **Итоговая структура для деплоя**
Теперь проект готов к деплою:
- `data/input` — принимает новые фотографии.
- `data/fingerprints` — содержит рабочие слепки.
- `output` — создаётся заново при каждом запуске.
- Старые эксперименты сохранены в `output_backup_v38_1.tar.gz`.

Если нужно, я могу помочь с настройкой CI/CD или добавлением логирования.