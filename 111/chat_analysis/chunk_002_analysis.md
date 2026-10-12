### 🛠️ **Решение проблемы: `AttributeError: 'FingerprintManager' object has no attribute 'load'`**

Ошибка возникает потому, что в коде `recognizer.py` вызывается метод `self.manager.load(fp["id"])`, но в классе `FingerprintManager` такого метода **нет**. Нужно добавить метод `load()` в `FingerprintManager`, чтобы он мог загружать данные по ID слепка.

---

### ✅ **Шаг 1: Добавим метод `load()` в `FingerprintManager`**

Открой файл:  
```bash
nano app/core/fingerprint.py
```

Найди класс `FingerprintManager` и добавь метод `load()`:

```python
class FingerprintManager:
    def __init__(self, settings, embedder):
        self.settings = settings
        self.embedder = embedder
        self.fingerprints = self.list_fingerprints()

    def list_fingerprints(self):
        """Список всех слепков в директории."""
        fingerprints_dir = self.settings.fingerprints_dir
        return [
            str(fp.name)
            for fp in fingerprints_dir.iterdir()
            if fp.is_dir()
        ]

    def load(self, fp_id):
        """Загрузка данных слепка по ID."""
        out = self.settings.fingerprints_dir / fp_id

        if not out.exists():
            raise FileNotFoundError(f"Fingerprint '{fp_id}' not found: {out}")

        return {
            "embeddings": np.load(out / "embeddings.npy"),
            "centroid": np.load(out / "centroid.npy"),
            "representatives": np.load(out / "representatives.npy"),
            "index": faiss.read_index(str(out / "faiss.index")),
            "metadata": json.loads(
                (out / "metadata.json").read_text(encoding="utf-8")
            ),
        }
```

Сохраните файл (`Ctrl+O → Enter → Ctrl+X`).

---

### ✅ **Шаг 2: Проверим структуру файлов**

Убедись, что файлы находятся в правильной директории:

```bash
find data/fingerprints -maxdepth 2 -type f -print
```

**Ожидаемый вывод:**

```text
data/fingerprints/78/embeddings.npy
data/fingerprints/78/centroid.npy
data/fingerprints/78/representatives.npy
data/fingerprints/78/fa
```