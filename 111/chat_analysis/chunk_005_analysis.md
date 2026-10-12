### ✅ Успешное выполнение шагов

#### 📁 Проверка содержимого `78_v31`
```bash
find data/fingerprints/78_v31 -maxdepth 1 -type f -printf '%f\n' | sort
```

**Ожидаемый вывод:**
```
centroid.npy
color_centroid.npy
color_embeddings.npy
embeddings.npy
environment_centroid.npy
environment_embeddings.npy
faiss.index
metadata.json
patch_centroid.npy
patch_embeddings.npy
patch_representatives.npy
representatives.npy
```

Если всё верно, можно продолжить анализ.

---

### 🧪 Анализ `78_v31` против `data/input/new`

```bash
uv run scene-fingerprint analyze \
    data/input/new \
    --fingerprint 78_v31
```

**Ожидаемый вывод:**
```
## [Имя файла]
GLOBAL        0.8543
PATCH         0.7891
COLOR         0.6543
ENVIRONMENT   0.9210
FINAL         0.8324
BEST MATCH    [Имя изображения из 78]
```

---

### 📌 Важные моменты

1. **Environment Score** должен быть **высоким** (например, `0.9210`), что указывает на успешное распознавание окружения.
2. **FINAL Score** должен быть **выше порога** (`0.65`), чтобы подтверждение было успешным.
3. **BEST MATCH** должен отображать имя изображения из оригинального `78`, что подтверждает корректность анализа.

---

### 🚀 Далее: Создание `79_v31`, `80_v31`, `81_v31`

**Только после успешного анализа `78_v31`**:
```bash
rm -rf data/fingerprints/79_v31
uv run scene-fingerprint create 79_v31 data/input/79

rm -rf data/fingerprints/80_v31
uv run scene-fingerprint create 80_v31 data/input/80

rm -rf data/fingerprints/81_v31
uv run scene-fingerprint create 81_v31 data/input/81
```

---

### 🧠 Заключение

- Убедитесь, что **environment score** работает корректно.
- Только после этого создавайте новые fingerprints.
- Проводите анализ для каждого нового fingerprint, чтобы убедиться в корректности распознавания.

Если всё прошло успешно, вы готовы к тестированию разделения объектов по окружению! 🚀