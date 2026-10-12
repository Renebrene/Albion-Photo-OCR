## СЕССИЯ: Использование первого кандидата

**Создано:** 2026-08-14 23:31:05
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f7b07-8df4-83ea-be86-b71f888d7beb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7f7b07-8df4-83ea-be86-b71f888d7beb)

---

### 👤 **User** — 2026-08-15 00:22:20

ecognizer.py
            f"[Recognizer] "
            f"Query images: {len(paths)}"
        )

        fingerprints = []

        for metadata in (
            self.manager.list_fingerprints()
        ):
            fingerprint_id = (
                metadata.get("id")
            )

            if not fingerprint_id:
                continue

            try:
                data = self.manager.load(
                    fingerprint_id
                )

            except (
                FileNotFoundError,
                ValueError,
                OSError,
            ) as exc:

                print(
                    f"[Recognizer] SKIP "
                    f"{fingerprint_id}: "
                    f"{exc}"
                )

                continue

            if str(
                data["metadata"].get(
                    "version",
                    "",
                )
            ) != self.VERSION:

                print(
                    f"[Recognizer] SKIP old "
                    f"fingerprint "
                    f"{fingerprint_id}"
                )

                continue

            fingerprints.append(
                (
                    fingerprint_id,
                    data,
                )
            )

        if not fingerprints:
            raise ValueError(
                "No compatible v3.3 compact "
                "fingerprints found."
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:22:21

Да, этот участок подходит. Сейчас добавим фильтр **до загрузки fingerprint'а**, поэтому старые адреса вообще не будут читаться.

### 1. Замени этот блок

Выполни:

```bash id="8r9f6v"
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
text = p.read_text()

old = '''        fingerprints = []

        for metadata in (
            self.manager.list_fingerprints()
        ):
            fingerprint_id = (
                metadata.get("id")
            )

            if not fingerprint_id:
                continue

            try:
'''

new = '''        fingerprints = []

        # Optional whitelist of fingerprints.
        # If provided, ONLY these fingerprints are used.
        if fingerprints is not None:
            allowed_fingerprints = {
                str(item).strip()
                for item in fingerprints
                if str(item).strip()
            }
        else:
            allowed_fingerprints = None

        for metadata in (
            self.manager.list_fingerprints()
        ):
            fingerprint_id = (
                metadata.get("id")
            )

            if not fingerprint_id:
                continue

            if (
                allowed_fingerprints is not None
                and str(fingerprint_id)
                not in allowed_fingerprints
            ):
                continue

            try:
'''

if old not in text:
    raise SystemExit("Fingerprint loading block not found")

p.write_text(text.replace(old, new))

print("OK: fingerprint whitelist added")
PY
```

### 2. Передаём список из CLI

Теперь заменим вызов:

```bash id="0j7z7h"
python3 - <<'PY'
from pathlib import Path

p = Path("app/cli.py")
text = p.read_text()

old = '''        results = (
            recognizer.recognize_folder(
                folder,
                top_k=args.top_k,
                threshold=args.threshold,
                workers=args.workers,
            )
        )
'''

new = '''        selected_fingerprints = None

        if args.fingerprints:
            selected_fingerprints = [
                item.strip()
                for item in args.fingerprints.split(",")
                if item.strip()
            ]

        results = (
            recognizer.recognize_folder(
                folder,
                top_k=args.top_k,
                threshold=args.threshold,
                workers=args.workers,
                fingerprints=selected_fingerprints,
            )
        )
'''

if old not in text:
    raise SystemExit("recognize_folder CLI call not found")

p.write_text(text.replace(old, new))

print("OK: CLI passes fingerprint whitelist")
PY
```

### 3. Проверяем синтаксис

```bash id="a2n5o5"
uv run python -m py_compile app/core/recognizer.py
```

```bash id="kz9p7k"
uv run python -m py_compile app/cli.py
```

Обе команды должны закончиться **без вывода**.

### 4. Проверяем help

```bash id="5u0j7p"
uv run scene-fingerprint recognize --help | grep -A2 fingerprints
```

Должно появиться примерно:

```text
--fingerprints FINGERPRINTS
    Comma-separated fingerprint IDs to use
```

---

## И затем запускаем чистый тест

Но **пока не запускай весь тест**.

Сначала сделаем контроль на 5 фотографиях, чтобы убедиться, что whitelist реально работает:

```bash id="44sj9v"
find data/input/test -type f | head -5
```

Если там обычная структура с фотографиями прямо в `test`, тогда следующим шагом запустим небольшой тест.

Если `test` содержит подкаталоги — покажи вывод этой команды, и я дам правильную команду для теста.

**Главное сейчас — выполни пункты 1–4 и пришли вывод.**

---

### 👤 **User** — 2026-08-15 00:23:38

OK: fingerprints parameter added
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '115,175p' app/core/recognizer.py
            f"[Recognizer] "
            f"Query images: {len(paths)}"
        )

        fingerprints = []

        for metadata in (
            self.manager.list_fingerprints()
        ):
            fingerprint_id = (
                metadata.get("id")
            )

            if not fingerprint_id:
                continue

            try:
                data = self.manager.load(
                    fingerprint_id
                )

            except (
                FileNotFoundError,
                ValueError,
                OSError,
            ) as exc:

                print(
                    f"[Recognizer] SKIP "
                    f"{fingerprint_id}: "
                    f"{exc}"
                )

                continue

            if str(
                data["metadata"].get(
                    "version",
                    "",
                )
            ) != self.VERSION:

                print(
                    f"[Recognizer] SKIP old "
                    f"fingerprint "
                    f"{fingerprint_id}"
                )

                continue

            fingerprints.append(
                (
                    fingerprint_id,
                    data,
                )
            )

        if not fingerprints:
            raise ValueError(
                "No compatible v3.3 compact "
                "fingerprints found."
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
text = p.read_text()

old = '''        fingerprints = []

        for metadata in (
            self.manager.list_fingerprints()
        ):
            fingerprint_id = (
                metadata.get("id")
            )

            if not fingerprint_id:
                continue

            try:
'''

PYint("OK: fingerprint whitelist added")g block not found")
OK: fingerprint whitelist added
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
from pathlib import Path

p = Path("app/cli.py")
text = p.read_text()

old = '''        results = (
            recognizer.recognize_folder(
                folder,
                top_k=args.top_k,
                threshold=args.threshold,
                workers=args.workers,
            )
        )
'''

new = '''        selected_fingerprints = None

        if args.fingerprints:
            selected_fingerprints = [
                item.strip()
                for item in args.fingerprints.split(",")
                if item.strip()
PYint("OK: CLI passes fingerprint whitelist")ll not found")
OK: CLI passes fingerprint whitelist
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m py_compile app/core/recognizer.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m py_compile app/cli.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run scene-fingerprint recognize --help | grep -A2 fingerprints
                                   [--fingerprints FINGERPRINTS] [--json]
                                   folder

--
  --fingerprints FINGERPRINTS
                        Comma-separated fingerprint IDs to use
  --json                Output JSON
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ find data/input/test -type f | head -5
data/input/test/Стачки Зорге А (2).JPG
data/input/test/Нагибина 24 А (10).JPG
data/input/test/Вавилова 52 А (1).JPG
data/input/test/1 Конной Армии А (18).JPG
data/input/test/Малиновского 25 к Доватора (6).JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:23:40

Да. Сейчас всё готово для **контрольного прогона `test` только по нужным слепкам**.

Но перед запуском я бы сделал один важный момент: у тебя сейчас есть слепки `86_v33_fast ... 95_v33_fast`, а `78–85` тоже существуют в разных вариантах. Поэтому для чистого теста лучше явно задать **один набор из 78–95**, чтобы старые `78`, `79`, `80` и т. п. случайно не участвовали.

Сначала проверим, что whitelist действительно работает:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint recognize \
  data/input/test \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33_fast,87_v33_fast,88_v33_fast,89_v33_fast,90_v33_fast,91_v33_fast,92_v33_fast,93_v33_fast,94_v33_fast,95_v33_fast \
  --top-k 5 \
  --workers 6
```

### Но есть нюанс

Мы должны убедиться, что `78_v33 ... 85_v33` действительно существуют и являются именно теми слепками, которые хотим использовать.

Выполни:

```bash
for id in {78..95}; do
    if [ -d "data/fingerprints/${id}_v33_fast" ]; then
        echo "$id  v33_fast"
    elif [ -d "data/fingerprints/${id}_v33" ]; then
        echo "$id  v33"
    elif [ -d "data/fingerprints/$id" ]; then
        echo "$id  OLD"
    else
        echo "$id  MISSING"
    fi
done
```

И пришли вывод.

После этого я дам **одну готовую команду**, которая:

- возьмёт все 250 фото из `data/input/test`;
- использует **только один слепок каждого адреса 78–95**;
- `TOP-1` всегда будет назначаться, даже если score слабый;
- использует `6` CPU workers;
- сохранит результаты в JSON;
- затем мы сделаем **статистику TOP-1** и посмотрим, какие адреса чаще всего путаются.

И это уже будет гораздо более показательный тест качества всей системы.

---

### 👤 **User** — 2026-08-15 00:24:06

Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/scene-fingerprint", line 10, in <module>
    sys.exit(main())
             ^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/cli.py", line 409, in main
    recognizer.recognize_folder(
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/recognizer.py", line 191, in recognize_folder
    raise ValueError(
ValueError: No compatible v3.3 compact fingerprints found.

---

### 🤖 **Assistant** — 2026-08-15 00:24:13

Да, это моя ошибка в предыдущем изменении: **whitelist мы добавили в CLI, но в `recognizer.py` он, судя по ошибке, не был корректно встроен в загрузку слепков**. Поэтому `recognize_folder()` в итоге не нашёл подходящих fingerprint'ов.

Сейчас не будем переделывать всё. Исправим аккуратно.

### 1. Покажи текущий участок `recognizer.py`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '95,205p' app/core/recognizer.py
```

и:

```bash
sed -n '380,425p' app/cli.py
```

Пришли оба вывода.

**Пока ничего больше не запускай.**

Я посмотрю, что именно сейчас получилось после наших замен, и дам точную команду-патч. Нам нужно добиться такого поведения:

```text
--fingerprints 78_v33,79_v33,...,95_v33_fast
```

→ загружаются **только эти 18 слепков**;

→ старые `78`, `79`, `80` и т. п. не участвуют;

→ все 250 фотографий `data/input/test` проходят;

→ даже при score 0.40, 0.50 и т. п. **TOP-1 всё равно назначается**;

→ `--workers 6` продолжает работать.

После этого уже нормально сделаем большой контрольный прогон.

---

### 👤 **User** — 2026-08-15 00:24:39

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '95,205p' app/core/recognizer.py
        return "NO_MATCH"

    def recognize_folder(
        self,
        folder,
        top_k=5,
        threshold=0.65,
        workers=6,
        fingerprints=None,
    ):
        folder = Path(folder)

        paths = image_files(
            folder
        )

        if not paths:
            return []

        print(
            f"[Recognizer] "
            f"Query images: {len(paths)}"
        )

        fingerprints = []

        # Optional whitelist of fingerprints.
        # If provided, ONLY these fingerprints are used.
        if fingerprints is not None:
            allowed_fingerprints = {
                str(item).strip()
                for item in fingerprints
                if str(item).strip()
            }
        else:
            allowed_fingerprints = None

        for metadata in (
            self.manager.list_fingerprints()
        ):
            fingerprint_id = (
                metadata.get("id")
            )

            if not fingerprint_id:
                continue

            if (
                allowed_fingerprints is not None
                and str(fingerprint_id)
                not in allowed_fingerprints
            ):
                continue

            try:
                data = self.manager.load(
                    fingerprint_id
                )

            except (
                FileNotFoundError,
                ValueError,
                OSError,
            ) as exc:

                print(
                    f"[Recognizer] SKIP "
                    f"{fingerprint_id}: "
                    f"{exc}"
                )

                continue

            if str(
                data["metadata"].get(
                    "version",
                    "",
                )
            ) != self.VERSION:

                print(
                    f"[Recognizer] SKIP old "
                    f"fingerprint "
                    f"{fingerprint_id}"
                )

                continue

            fingerprints.append(
                (
                    fingerprint_id,
                    data,
                )
            )

        if not fingerprints:
            raise ValueError(
                "No compatible v3.3 compact "
                "fingerprints found."
            )

        print(
            "[Recognizer] Fingerprints: "
            + ", ".join(
                fp_id
                for fp_id, _ in fingerprints
            )
        )

        # One DINO pass for all query images.
        queries = self.embedder.embed_paths(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '380,425p' app/cli.py
                f"Folder not found: "
                f"{folder}"
            )

        embedder = SceneEmbedder(
            settings
        )

        manager = FingerprintManager(
            settings,
            embedder,
        )

        recognizer = SceneRecognizer(
            settings,
            embedder,
            manager,
        )

        selected_fingerprints = None

        if args.fingerprints:
            selected_fingerprints = [
                item.strip()
                for item in args.fingerprints.split(",")
                if item.strip()
            ]

        results = (
            recognizer.recognize_folder(
                folder,
                top_k=args.top_k,
                threshold=args.threshold,
                workers=args.workers,
                fingerprints=selected_fingerprints,
            )
        )

        if args.json:
            print(
                json.dumps(
                    results,
                    ensure_ascii=False,
                    indent=2,
                )
            )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:24:40

Нашёл ошибку. Причина очень конкретная:

```python
fingerprints = []
```

внутри `recognize_folder()` **затирает параметр `fingerprints`**, который пришёл из CLI.

То есть whitelist приходит, а первой же строкой превращается в пустой список.

Нужно заменить только одну строку.

### 1. Исправляем

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
text = p.read_text()

old = '''        fingerprints = []

        # Optional whitelist of fingerprints.
'''

new = '''        loaded_fingerprints = []

        # Optional whitelist of fingerprints.
'''

if old not in text:
    raise SystemExit("ERROR: target block not found")

text = text.replace(old, new, 1)

text = text.replace(
    '''            fingerprints.append(
                (
                    fingerprint_id,
                    data,
                )
            )
''',
    '''            loaded_fingerprints.append(
                (
                    fingerprint_id,
                    data,
                )
            )
''',
    1
)

text = text.replace(
    '''        if not fingerprints:
''',
    '''        if not loaded_fingerprints:
''',
    1
)

text = text.replace(
    '''                fp_id
                for fp_id, _ in fingerprints
''',
    '''                fp_id
                for fp_id, _ in loaded_fingerprints
''',
    1
)

text = text.replace(
    '''            for fingerprint_id, data in fingerprints:
''',
    '''            for fingerprint_id, data in loaded_fingerprints:
''',
    1
)

p.write_text(text)

print("OK: whitelist variable fixed")
PY
```

### 2. Проверяем синтаксис

```bash
uv run python -m py_compile app/core/recognizer.py
```

Должно просто вернуться в приглашение без ошибок.

### 3. Проверяем, какие слепки реально будут использоваться

Сначала лучше не запускать 250 фотографий. Сделаем короткий тест на 2–3 фото:

```bash
find data/input/test -type f | head -3
```

Затем:

```bash
mkdir -p /tmp/lora_test3

find data/input/test -type f | head -3 | while read f; do
    cp "$f" /tmp/lora_test3/
done
```

И запускаем:

```bash
uv run scene-fingerprint recognize \
  /tmp/lora_test3 \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33_fast,87_v33_fast,88_v33_fast,89_v33_fast,90_v33_fast,91_v33_fast,92_v33_fast,93_v33_fast,94_v33_fast,95_v33_fast \
  --top-k 5 \
  --workers 6
```

В самом начале должен появиться примерно такой список:

```text
[Recognizer] Query images: 3
[Recognizer] Fingerprints: 78_v33, 79_v33, ... 95_v33_fast
```

**Это главное.**

Если он покажет весь нужный набор — значит whitelist работает.

После этого уже запускаем все `test` из 250 фото.

---

### 👤 **User** — 2026-08-15 00:25:58

[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Recognizer] Query images: 3
[Recognizer] Fingerprints: 78_v33, 79_v33, 80_v33, 81_v33, 82_v33, 83_v33, 84_v33, 85_v33, 86_v33_fast, 87_v33_fast, 88_v33_fast, 89_v33_fast, 90_v33_fast, 91_v33_fast, 92_v33_fast, 93_v33_fast, 94_v33_fast, 95_v33_fast
[Recognizer] CPU workers: 6
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/scene-fingerprint", line 10, in <module>
    sys.exit(main())
             ^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/cli.py", line 409, in main
    recognizer.recognize_folder(
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/recognizer.py", line 288, in recognize_folder
    score = self.analyzer.compare(
            ^^^^^^^^^^^^^^^^^^^^^^
TypeError: SceneAnalyzer.compare() got an unexpected keyword argument 'query_global'

---

### 🤖 **Assistant** — 2026-08-15 00:25:59

Да. Это уже **следующая конкретная ошибка**, и она хорошая с точки зрения диагностики: whitelist работает, `workers=6` тоже дошёл до recognizer. Теперь несовместимы наши изменения в `recognizer.py` и `scene_analyzer.py`.

Ошибка:

```text
TypeError: SceneAnalyzer.compare() got an unexpected keyword argument 'query_global'
```

Значит, `recognizer.py` уже пытается передавать предварительно рассчитанный DINO embedding:

```python
query_global=...
```

а текущий `SceneAnalyzer.compare()` всё ещё имеет старую сигнатуру:

```python
def compare(
    self,
    image_path: Path,
    fingerprint_id: str,
):
```

### Исправляем правильно

Нам как раз нужно это сделать, потому что иначе ускорение CPU/DINO будет неполным: сейчас DINO уже считается пачкой, но `compare()` снова пытается его считать для каждого fingerprint.

Сначала покажи текущий участок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '315,430p' app/core/recognizer.py
```

И:

```bash
sed -n '205,390p' app/core/scene_analyzer.py
```

**Пока ничего не меняй.**

Я дам точную замену `compare()`, которая будет принимать:

```python
query_global
query_environment
query_color
query_spatial
```

и тогда для 3 фотографий × 18 слепков не будет повторно загружаться/обрабатываться изображение для каждого сравнения.

В результате получим архитектуру:

```text
250 фото
   │
   ├── DINO → один раз для всех фото
   │
   └── CPU descriptors → 6 workers
              │
              ▼
       готовые признаки
              │
              ▼
       18 fingerprint × 250
              │
              ▼
       только математика
```

Это как раз то, что нам нужно для большого теста 250 фото.

---

### 👤 **User** — 2026-08-15 00:26:37

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '205,390p' app/core/scene_analyzer.py

                y1 = gy_idx * h // 4
                y2 = (gy_idx + 1) * h // 4

                x1 = gx_idx * w // 4
                x2 = (gx_idx + 1) * w // 4

                cell = gray[y1:y2, x1:x2]

                descriptor.extend(
                    [
                        float(cell.mean()),
                        float(cell.std()),
                    ]
                )

        return cls._normalize(
            np.asarray(
                descriptor,
                dtype=np.float32,
            )
        )

    @classmethod
    def spatial(cls, path: Path):
        image = cls._load(path)
        return cls.spatial_from_image(image)

    @classmethod
    def all_from_image(cls, image):
        """
        Calculate all compact descriptors from one already
        loaded/resized image.

        Returns:
            environment: 640
            color:       48
            spatial:     32
        """

        return (
            cls.environment_from_image(image),
            cls.color_from_image(image),
            cls.spatial_from_image(image),
        )

    @classmethod
    def all(cls, path: Path):
        image = cls._load(path)
        return cls.all_from_image(image)

class SceneAnalyzer:
    """
    v3.3 compact scene comparison.

    Weights:
        global       0.70
        environment  0.20
        color        0.07
        spatial      0.03

    Patch storage is disabled.
    """

    GLOBAL_WEIGHT = 0.70
    ENVIRONMENT_WEIGHT = 0.20
    COLOR_WEIGHT = 0.07
    SPATIAL_WEIGHT = 0.03

    def __init__(
        self,
        embedder,
        manager,
    ):
        self.embedder = embedder
        self.manager = manager

    @staticmethod
    def cosine(a, b):
        a = np.asarray(
            a,
            dtype=np.float32,
        ).reshape(-1)

        b = np.asarray(
            b,
            dtype=np.float32,
        ).reshape(-1)

        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)

        if na == 0.0 or nb == 0.0:
            return 0.0

        return float(
            np.dot(a, b)
            / (na * nb)
        )

    @staticmethod
    def descriptor_similarity(
        query,
        references,
    ):
        q = np.asarray(
            query,
            dtype=np.float32,
        ).reshape(-1)

        refs = np.asarray(
            references,
            dtype=np.float32,
        )

        if refs.ndim == 1:
            refs = refs.reshape(1, -1)

        if len(refs) == 0:
            return 0.0

        q_norm = np.linalg.norm(q)

        if q_norm == 0.0:
            return 0.0

        q = q / q_norm

        ref_norms = np.linalg.norm(
            refs,
            axis=1,
            keepdims=True,
        )

        ref_norms[
            ref_norms == 0.0
        ] = 1.0

        refs = refs / ref_norms

        scores = refs @ q

        k = max(
            3,
            int(len(scores) * 0.10),
        )

        k = min(
            k,
            len(scores),
        )

        return float(
            np.mean(
                np.sort(scores)[-k:]
            )
        )

    def compare(
        self,
        image_path: Path,
        fingerprint_id: str,
    ):
        data = self.manager.load(
            fingerprint_id
        )

        query_global = (
            self.embedder.embed_paths(
                [Path(image_path)]
            )[0]
        )

        query_global = np.asarray(
            query_global,
            dtype=np.float32,
        )

        global_score = self.cosine(
            query_global,
            data["centroid"],
        )

        image_scores = (
            data["embeddings"]
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:26:39

Отлично. Теперь причина полностью ясна. У тебя `scene_analyzer.py` уже содержит оптимизированные `all_from_image()`, но сам `compare()` остался старым.

Сделаем совместимо и быстро: `compare()` будет принимать уже рассчитанные признаки, но при необходимости сможет работать и по-старому. Это важно, чтобы не сломать `analyze`.

### 1. Заменяем `compare()` целиком

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/core/scene_analyzer.py")
text = p.read_text()

start = text.index("    def compare(\n")
end = text.index("    def analyze(\n", start)

new = '''    def compare(
        self,
        image_path: Path,
        fingerprint_id: str,
        query_global=None,
        query_environment=None,
        query_color=None,
        query_spatial=None,
    ):
        """
        Compare one image against one fingerprint.

        For fast recognition the query descriptors can be
        supplied already calculated by the recognizer.

        If they are not supplied, calculate them here for
        backward compatibility with `analyze`.
        """

        data = self.manager.load(
            fingerprint_id
        )

        # --------------------------------------------------
        # GLOBAL DINO
        # --------------------------------------------------

        if query_global is None:
            query_global = (
                self.embedder.embed_paths(
                    [Path(image_path)]
                )[0]
            )

        query_global = np.asarray(
            query_global,
            dtype=np.float32,
        )

        global_score = self.cosine(
            query_global,
            data["centroid"],
        )

        image_scores = (
            data["embeddings"]
            @ query_global
        )

        best_index = int(
            np.argmax(image_scores)
        )

        best_image_score = float(
            image_scores[best_index]
        )

        image_names = (
            data["metadata"]
            .get(
                "image_names",
                [],
            )
        )

        if best_index < len(image_names):
            best_image = image_names[
                best_index
            ]
        else:
            best_image = str(
                best_index
            )

        # --------------------------------------------------
        # COMPACT DESCRIPTORS
        # --------------------------------------------------

        if (
            query_environment is None
            or query_color is None
            or query_spatial is None
        ):
            image = CompactDescriptor._load(
                Path(image_path)
            )

            (
                query_environment,
                query_color,
                query_spatial,
            ) = CompactDescriptor.all_from_image(
                image
            )

        environment_score = (
            self.descriptor_similarity(
                query_environment,
                data[
                    "environment_embeddings"
                ],
            )
        )

        color_score = (
            self.descriptor_similarity(
                query_color,
                data[
                    "color_embeddings"
                ],
            )
        )

        spatial_score = (
            self.descriptor_similarity(
                query_spatial,
                data[
                    "spatial_embeddings"
                ],
            )
        )

        # --------------------------------------------------
        # FINAL SCORE
        # --------------------------------------------------

        final_score = (
            self.GLOBAL_WEIGHT
            * global_score
            + self.ENVIRONMENT_WEIGHT
            * environment_score
            + self.COLOR_WEIGHT
            * color_score
            + self.SPATIAL_WEIGHT
            * spatial_score
        )

        return {
            "global_score": float(
                global_score
            ),

            "best_image_score": float(
                best_image_score
            ),

            "patch_score": 0.0,

            "color_score": float(
                color_score
            ),

            "spatial_score": float(
                spatial_score
            ),

            "environment_score": float(
                environment_score
            ),

            "final_score": float(
                final_score
            ),

            "best_image": best_image,

            "fingerprint_version": (
                data["metadata"]
                .get(
                    "version",
                    "3.3",
                )
            ),
        }

'''

text = text[:start] + new + text[end:]

p.write_text(text)

print("OK: SceneAnalyzer.compare optimized")
PY
```

### 2. Проверяем

```bash
uv run python -m py_compile app/core/scene_analyzer.py
```

Должно быть просто:

```text
OK...
```

без traceback.

### 3. Теперь снова запускаем наши 3 тестовых фотографии

```bash
uv run scene-fingerprint recognize \
  /tmp/lora_test3 \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33_fast,87_v33_fast,88_v33_fast,89_v33_fast,90_v33_fast,91_v33_fast,92_v33_fast,93_v33_fast,94_v33_fast,95_v33_fast \
  --top-k 5 \
  --workers 6
```

Если всё нормально, ожидаем:

```text
[Recognizer] Query images: 3
[Recognizer] Fingerprints: ...
[Recognizer] CPU workers: 6

## ...
MATCH ...
SCORE ...
...
```

И **не должно быть повторного DINO для каждого fingerprint**.

После этого уже можно запускать все 250 фото.

---

### 👤 **User** — 2026-08-15 00:27:19

все ок

---

### 🤖 **Assistant** — 2026-08-15 00:27:20

Отлично. Тогда оптимизация работает как задумано.

Теперь делаем **контрольный прогон всей папки `test`** по адресам **78-95**.

Я бы сохранил результат сразу в JSON, чтобы потом автоматически посчитать TOP-1 и матрицу ошибок.

### Полный прогон

```bash
cd ~/projects/scene_fingerprint_mvp_v02

time uv run scene-fingerprint recognize \
  data/input/test \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33_fast,87_v33_fast,88_v33_fast,89_v33_fast,90_v33_fast,91_v33_fast,92_v33_fast,93_v33_fast,94_v33_fast,95_v33_fast \
  --top-k 5 \
  --workers 6 \
  --json > test_78_95_results.json
```

### Важный момент

Файл будет содержать **и служебный вывод**, если `SceneEmbedder`/`Recognizer` печатают в stdout. Поэтому после завершения сначала проверим JSON:

```bash
head -5 test_78_95_results.json
```

Если там начинается с:

```json
[
  {
```

- отлично.

Если там перед JSON есть строки типа:

```text
[SceneEmbedder] ...
[Recognizer] ...
```

- тоже не страшно, я дам команду, которая отделит результаты.

### По времени

У тебя раньше:

```text
111 фото → ~21.4 сек
```

Сейчас после оптимизации при 250 фото ожидаем примерно **45-60 секунд**, возможно быстрее/медленнее в зависимости от загрузки GPU и CPU.

После окончания пришли:

```text
REAL TIME: ...
CPU: ...
```

и первые несколько строк:

```bash
head -10 test_78_95_results.json
```

**Следующим шагом уже не будем смотреть результаты вручную.** Я дам скрипт, который автоматически покажет:

- TOP-1 по каждому фото;
- сколько раз каждый адрес выбран;
- распределение score;
- TOP-2 / TOP-3;
- какие пары адресов чаще всего путаются;
- и, главное, **насколько хорошо TOP-1 работает по всей выборке**.

---

### 👤 **User** — 2026-08-15 00:28:08

Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8640.46it/s]

---

### 🤖 **Assistant** — 2026-08-15 00:28:10

Да, это **не ошибка**.

`Loading weights: 100%` — модель DINOv2 успешно загрузилась.

Предупреждение:

```text
Warning: You are sending unauthenticated requests to the HF Hub.
Please set a HF_TOKEN...
```

означает только, что Hugging Face используется **без авторизации**. Для уже скачанной модели это обычно не мешает работе.

Если сейчас распознавание продолжилось после этой строки — **ничего менять не нужно**.

Для нашего текущего теста я бы пока оставил как есть и дождался полного прогона `test`. Затем уже посмотрим:

- сколько TOP-1 совпало;
- какие адреса чаще всего путаются;
- средний `score`;
- `margin` между TOP-1 и TOP-2;
- какие адреса требуют улучшения слепка.

Это сейчас гораздо важнее, чем настройка HF_TOKEN.

---

### 👤 **User** — 2026-08-15 00:28:34

real	0m51.108s
user	1m35.619s
sys	0m18.495s

---

### 🤖 **Assistant** — 2026-08-15 00:28:35

Отлично. **51 секунда на весь тест — очень хороший результат.**

По твоим цифрам:

- **REAL:** 51.1 с
- **USER CPU:** 95.6 с
- **SYS:** 18.5 с
- **250 фото × 18 адресов**
- 6 CPU workers
- DINO считается один раз на каждое фото

То есть сейчас система уже достаточно быстрая для рабочего конвейера.

Но теперь самое важное — **не ускорять дальше, а измерить качество TOP-1**.

### 1. Проверим, что JSON нормальный

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

head -5 test_78_95_results.json
```

И:

```bash
tail -5 test_78_95_results.json
```

Если JSON действительно записался корректно, следующим шагом я дам тебе готовый скрипт `evaluate_test.py`, который автоматически разберёт все 250 результатов.

Он сможет показать примерно такую таблицу:

```text
ADDRESS    TOP1    TOP2    AVG SCORE    AVG MARGIN
78          14       2       0.873       0.061
79          12       3       0.841       0.044
80          16       1       0.891       0.073
...
95          19       2       0.856       0.039
```

И отдельно:

```text
TOP-1 ACCURACY: 87.6%

MOST CONFUSED:
78 -> 82 : 5
84 -> 85 : 4
91 -> 93 : 3
...
```

**Но есть важная вещь:** чтобы реально посчитать точность TOP-1, нам надо определить правильный адрес для каждого тестового файла. У тебя, судя по именам вроде:

```text
Стачки Зорге А (2).JPG
Нагибина 24 А (10).JPG
Вавилова 52 А (1).JPG
```

адрес зашит в имени файла.

Поэтому после проверки JSON мы можем автоматически извлечь **эталонный адрес из имени файла** и сравнить его с `best_id`.

Это будет уже настоящий тест качества, а не визуальная оценка результатов.

---

### 👤 **User** — 2026-08-15 00:29:02

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

head -5 test_78_95_results.json
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
[SceneEmbedder] embedding dimension=768
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ tail -5 test_78_95_results.json
        "best_image_score": 0.7822959423065186
      }
    ]
  }
]
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:29:04

Отлично. JSON корректный — просто в начале находятся служебные сообщения, а сам JSON начинается ниже.

Теперь **не будем вручную вырезать JSON**. Сделаем скрипт, который найдёт начало массива `[` и автоматически разберёт результаты.

Но есть важный нюанс: для оценки точности нам нужно сопоставить имя файла с адресом. Судя по твоим именам, это можно сделать, но сначала лучше посмотреть, **как именно записаны `file` и `best_id`**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path
import json

p = Path("test_78_95_results.json")
text = p.read_text(encoding="utf-8")

start = text.find("[")
data = json.loads(text[start:])

print("RESULTS:", len(data))
print()

for r in data[:15]:
    print(
        f"{Path(r['file']).name[:55]:55} "
        f"TOP1={r.get('best_id')} "
        f"SCORE={r.get('score', 0):.4f} "
        f"SECOND={r.get('second_score', 0):.4f} "
        f"MARGIN={r.get('margin', 0):.4f}"
    )
PY
```

Это даст нам первые 15 строк примерно такого вида:

```text
Стачки Зорге А (2).JPG                         TOP1=...
Нагибина 24 А (10).JPG                         TOP1=...
Вавилова 52 А (1).JPG                          TOP1=...
...
```

**Пришли этот вывод.**

После этого я сделаю тебе нормальный `evaluate_test.py`, который будет учитывать реальные правила именования твоих фотографий и выдаст:

1. **TOP-1 accuracy**
2. TOP-2 accuracy
3. TOP-3 accuracy
4. средний score
5. средний margin
6. список правильных/ошибочных распознаваний
7. **матрицу путаницы 78–95**
8. какие адреса распознаются хуже всего
9. какие пары адресов визуально наиболее похожи.

И вот после этого уже можно будет решить, **нужно ли менять веса `0.70 / 0.20 / 0.07 / 0.03` или сначала улучшать слепки**.

---

### 👤 **User** — 2026-08-15 00:29:22

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02
python3 - <<'PY'
python3 - <<'PY'ort Path
from pathlib import Path
import json
p = Path("test_78_95_results.json")
p = Path("test_78_95_results.json"))
text = p.read_text(encoding="utf-8")
start = text.find("[")
start = text.find("[")[start:])
data = json.loads(text[start:])
print("RESULTS:", len(data))
print("RESULTS:", len(data))
print()
for r in data[:15]:
for r in data[:15]:
    print({Path(r['file']).name[:55]:55} "
        f"{Path(r['file']).name[:55]:55} "
        f"TOP1={r.get('best_id')} ".4f} "
        f"SCORE={r.get('score', 0):.4f} "):.4f} "
        f"SECOND={r.get('second_score', 0):.4f} "
        f"MARGIN={r.get('margin', 0):.4f}"
    )
PY
Traceback (most recent call last):
  File "<stdin>", line 8, in <module>
  File "/usr/lib/python3.12/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/json/decoder.py", line 337, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/lib/python3.12/json/decoder.py", line 355, in raw_decode
    raise JSONDecodeError("Expecting value", s, err.value) from None
json.decoder.JSONDecodeError: Expecting value: line 1 column 2 (char 1)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:29:23

Да, команда у тебя при вставке **исказилась** — видно повторяющиеся строки вроде `python3 - <<'PY'` и обрывки f-string. Поэтому ошибка сейчас не в JSON, а в нашем диагностическом скрипте.

Сделаем надёжнее: **вообще не будем искать `[` вручную**. Уберём служебный вывод из файла и получим чистый JSON из исходного результата.

### 1. Сначала проверим, где начинается настоящий JSON

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -n '^\[' test_78_95_results.json | head
```

Если увидишь что-то вроде:

```text
7:[
```

или:

```text
8:[
```

значит всё просто.

### 2. А пока можно сразу сделать чистый JSON

Если первая команда покажет, например, `7:[`, выполни:

```bash
tail -n +7 test_78_95_results.json > test_78_95_clean.json
```

Но **не делай этот шаг пока**, если номер строки будет другим.

Пришли мне результат:

```bash
grep -n '^\[' test_78_95_results.json | head
```

И я дам одну точную команду.

После этого уже спокойно считаем **TOP-1 по всем 250 фотографиям**.

---

### 👤 **User** — 2026-08-15 00:29:40

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -n '^\[' test_78_95_results.json | head
1:[SceneEmbedder] device=cuda
2:[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
3:[SceneEmbedder] VRAM=11.6 GB
4:[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
5:[SceneEmbedder] embedding dimension=768
6:[SceneEmbedder] patch extraction=DISABLED (compact)
7:[SceneEmbedder] Ready.
8:[Recognizer] Query images: 262
9:[Recognizer] Fingerprints: 78_v33, 79_v33, 80_v33, 81_v33, 82_v33, 83_v33, 84_v33, 85_v33, 86_v33_fast, 87_v33_fast, 88_v33_fast, 89_v33_fast, 90_v33_fast, 91_v33_fast, 92_v33_fast, 93_v33_fast, 94_v33_fast, 95_v33_fast
10:[Recognizer] CPU workers: 6
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:29:42

Да, проблема понятна: `test_78_95_results.json` содержит **служебный вывод программы перед JSON**, поэтому `json.loads()` падает.

Но тут есть ещё важный момент: строка

```text
[Recognizer] Query images: 262
```

означает, что тест уже содержит **262 фотографии** — отлично, это как раз хороший объём для проверки TOP-1.

### 1. Сначала извлечём настоящий JSON

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path
import json

p = Path("test_78_95_results.json")
text = p.read_text(encoding="utf-8")

# JSON начинается с первой строки, которая содержит только '['
lines = text.splitlines()

start = None
for i, line in enumerate(lines):
    if line.strip() == "[":
        start = i
        break

if start is None:
    raise RuntimeError("JSON array not found")

json_text = "\n".join(lines[start:])
data = json.loads(json_text)

print("RESULTS:", len(data))
print()

for r in data[:20]:
    name = Path(r["file"]).name

    print(
        f"{name[:55]:55} "
        f"TOP1={str(r.get('best_id')):12} "
        f"SCORE={r.get('score', 0):.4f} "
        f"SECOND={r.get('second_score', 0):.4f} "
        f"MARGIN={r.get('margin', 0):.4f}"
    )
PY
```

---

### 2. Но для нашей задачи лучше сразу посчитать правильность TOP-1

У тебя в именах фотографий есть адрес. Например:

```text
Стачки Зорге А (2).JPG
Нагибина 24 А (10).JPG
Вавилова 52 А (1).JPG
Малиновского 25 к Доватора (6).JPG
```

А fingerprint имеет ID `78...95`.

Нам нужно автоматически определить **ожидаемый адрес из имени файла**, сопоставить его с ID слепка и получить:

- TOP-1 правильный / неправильный
- TOP-2
- TOP-3
- средний score
- средний margin
- сколько случаев `FORCED_MATCH`
- какие адреса чаще всего путаются
- какие фотографии являются проблемными

Но для этого сначала надо увидеть, **как именно связаны названия файлов с номерами 78–95**. Сейчас из приведённых имён это не всегда очевидно.

Поэтому я бы **не стал пока вручную считать TOP-1**.

### 3. Главное — результат уже получен

У нас сейчас:

```text
Query images: 262
Fingerprints: 18
```

То есть тестовая выборка:

**262 фотографии × 18 адресов**

и система сравнивает каждый кадр со всеми 18 слепками.

Это уже достаточно серьёзный тест.

Причём у тебя сейчас очень удачная конфигурация:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
83_v33
84_v33
85_v33
86_v33_fast
...
95_v33_fast
```

То есть адреса **78–95 полностью представлены**.

---

### Я предлагаю следующий шаг

Не просто смотреть первые 15 результатов, а сделать один анализатор:

```text
========== TEST 78-95 ==========

Photos:             262
Addresses:           18

TOP-1 accuracy:     XX.X%
TOP-2 accuracy:     XX.X%
TOP-3 accuracy:     XX.X%

Average score:      X.XXXX
Average margin:     X.XXXX

HIGH confidence:    XXX
MEDIUM confidence:  XXX
LOW confidence:     XXX
FORCED_MATCH:       XXX
```

И ниже:

```text
MOST CONFUSED

78 -> 83    7 times
84 -> 86    5 times
91 -> 94    4 times
...
```

А затем вывести **все неправильные TOP-1**:

```text
Файл                         Ожидалось   TOP1       SCORE   SECOND  MARGIN
--------------------------------------------------------------------------
...
```

Это будет намного полезнее, чем просто смотреть JSON.

**Сейчас выполни только первый скрипт выше.** Если он покажет `RESULTS: 262`, дальше сделаем автоматическую проверку TOP-1 по всем 262 фотографиям.

---

### 👤 **User** — 2026-08-15 00:30:05

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path
import json

p = Path("test_78_95_results.json")
text = p.read_text(encoding="utf-8")

# JSON начинается с первой строки, которая содержит только '['
lines = text.splitlines()

start = None
for i, line in enumerate(lines):
    if line.strip() == "[":
        start = i
        break

if start is None:
    raise RuntimeError("JSON array not found")

json_text = "\n".join(lines[start:])
PY  )   f"MARGIN={r.get('margin', 0):.4f}":.4f} "
RESULTS: 262

00 (1).JPG                                              TOP1=78_v33       SCORE=0.9475 SECOND=0.8923 MARGIN=0.0552
00 (10).JPG                                             TOP1=78_v33       SCORE=0.9384 SECOND=0.8793 MARGIN=0.0591
00 (11).JPG                                             TOP1=78_v33       SCORE=0.9336 SECOND=0.8903 MARGIN=0.0433
00 (12).JPG                                             TOP1=78_v33       SCORE=0.9301 SECOND=0.8894 MARGIN=0.0406
00 (2).JPG                                              TOP1=78_v33       SCORE=0.9375 SECOND=0.8844 MARGIN=0.0531
00 (3).JPG                                              TOP1=78_v33       SCORE=0.9057 SECOND=0.8515 MARGIN=0.0542
00 (4).JPG                                              TOP1=78_v33       SCORE=0.9513 SECOND=0.8834 MARGIN=0.0679
00 (5).JPG                                              TOP1=78_v33       SCORE=0.9300 SECOND=0.8905 MARGIN=0.0396
00 (6).JPG                                              TOP1=78_v33       SCORE=0.9470 SECOND=0.8897 MARGIN=0.0573
00 (7).JPG                                              TOP1=78_v33       SCORE=0.9341 SECOND=0.9007 MARGIN=0.0334
00 (8).JPG                                              TOP1=79_v33       SCORE=0.9177 SECOND=0.8628 MARGIN=0.0549
00 (9).JPG                                              TOP1=78_v33       SCORE=0.9364 SECOND=0.8898 MARGIN=0.0466
001.JPG                                                 TOP1=78_v33       SCORE=0.9475 SECOND=0.8886 MARGIN=0.0589
002.JPG                                                 TOP1=78_v33       SCORE=0.9476 SECOND=0.8896 MARGIN=0.0580
003.JPG                                                 TOP1=78_v33       SCORE=0.9519 SECOND=0.9013 MARGIN=0.0506
004.JPG                                                 TOP1=78_v33       SCORE=0.9416 SECOND=0.8888 MARGIN=0.0528
005.JPG                                                 TOP1=78_v33       SCORE=0.9470 SECOND=0.8805 MARGIN=0.0664
006.JPG                                                 TOP1=80_v33       SCORE=0.9667 SECOND=0.8219 MARGIN=0.1447
007.JPG                                                 TOP1=80_v33       SCORE=0.9676 SECOND=0.8340 MARGIN=0.1336
008.JPG                                                 TOP1=83_v33       SCORE=0.9096 SECOND=0.9082 MARGIN=0.0014
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 00:30:07

Да. И уже по этим первым 20 результатам видно **важную вещь**: система работает, но сейчас нельзя оценивать точность по обрезанному имени файла (`00 (1).JPG`) — мы потеряли начало названия при выводе.

Например:

- `006.JPG → 80_v33`, score `0.9667`, margin `0.1447` — очень уверенный результат.
- `008.JPG → 83_v33`, score `0.9096`, **margin всего 0.0014** — это практически ничья, такой кадр надо считать проблемным независимо от TOP-1.
- `00 (8).JPG → 79_v33` — возможно правильный адрес, но по обрезанному имени определить нельзя.

### Давай сейчас сделаем правильный анализ всех 262

Нам нужно вывести **полное имя файла**, TOP-1, TOP-2, score и margin, а затем отдельно список слабых результатов.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path
import json

p = Path("test_78_95_results.json")
lines = p.read_text(encoding="utf-8").splitlines()

# Находим начало JSON
start = next(
    i for i, line in enumerate(lines)
    if line.strip() == "["
)

data = json.loads("\n".join(lines[start:]))

print("=" * 120)
print(f"TOTAL RESULTS: {len(data)}")
print("=" * 120)

print()
print("ALL RESULTS")
print("-" * 120)

for i, r in enumerate(data, 1):
    name = Path(r["file"]).name

    print(
        f"{i:3d}  "
        f"{name[:65]:65}  "
        f"TOP1={str(r.get('best_id')):12} "
        f"SCORE={r.get('score', 0):.4f} "
        f"SECOND={r.get('second_score', 0):.4f} "
        f"MARGIN={r.get('margin', 0):.4f}"
    )

print()
print("=" * 120)
print("WEAK MATCHES: MARGIN < 0.02")
print("=" * 120)

weak = [
    r for r in data
    if r.get("margin", 0) < 0.02
]

print(f"COUNT: {len(weak)} / {len(data)}")

for r in weak:
    name = Path(r["file"]).name

    print(
        f"{name[:70]:70} "
        f"TOP1={r.get('best_id'):12} "
        f"SCORE={r.get('score',0):.4f} "
        f"SECOND={r.get('second_score',0):.4f} "
        f"MARGIN={r.get('margin',0):.4f}"
    )

print()
print("=" * 120)
print("VERY WEAK: MARGIN < 0.005")
print("=" * 120)

very_weak = [
    r for r in data
    if r.get("margin", 0) < 0.005
]

print(f"COUNT: {len(very_weak)} / {len(data)}")

for r in very_weak:
    name = Path(r["file"]).name

    print(
        f"{name[:70]:70} "
        f"TOP1={r.get('best_id'):12} "
        f"SCORE={r.get('score',0):.4f} "
        f"SECOND={r.get('second_score',0):.4f} "
        f"MARGIN={r.get('margin',0):.4f}"
    )
PY
```

### Почему сейчас именно margin важнее threshold

Мы уже сделали `FORCED_MATCH`: система **всегда выбирает лучший адрес**.

Поэтому теперь:

```text
SCORE
```

показывает абсолютное сходство, а

```text
MARGIN = TOP1 - TOP2
```

показывает, **насколько TOP-1 лучше ближайшего конкурента**.

Например:

```text
TOP1  0.9096
TOP2  0.9082
MARGIN 0.0014
```

Это плохой случай: модель практически не различает два адреса.

А:

```text
TOP1  0.9667
TOP2  0.8219
MARGIN 0.1447
```

— отличный случай.

---

**Но самое главное:** после этого нам нужно получить **реальную TOP-1 accuracy**. Для этого я хочу использовать структуру твоих папок `data/input/78 ... 95` как эталон: если тестовое фото физически находится/было сформировано из соответствующего адреса, мы можем автоматически узнать правильный ID и не заниматься ручной разметкой 262 фотографий.

То есть следующий этап я бы сделал уже как полноценный **benchmark 78–95**:

```text
262 тестовых фото
       ↓
18 fingerprint
       ↓
TOP-1 / TOP-2 / TOP-3
       ↓
accuracy
       ↓
confusion matrix
       ↓
пары адресов, которые путаются
       ↓
проблемные фотографии
```

И тогда мы уже будем решать не «кажется, работает», а **насколько хорошо v3.3 реально распознаёт адреса**.

---

### 👤 **User** — 2026-08-15 00:31:00

еще их нужно раскидать по папкам в output test_classified

---

### 🤖 **Assistant** — 2026-08-15 00:31:00

Да. И лучше сделать это **одновременно с анализом**: каждое фото из `data/input/test` положить в `output/test_classified/<TOP1_ID>/`.

Причём я предлагаю сразу сделать две вещи:

1. `output/test_classified/78_v33/` — фотографии, распознанные как 78.
2. `output/test_classified/83_v33/` — как 83 и т.д.
3. Отдельно `output/test_classified/_LOW_CONFIDENCE/` — фотографии с маленьким `margin`, чтобы быстро проверить спорные кадры.
4. Ничего не удаляем и не перемещаем — **только копируем**.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > classify_test_results.py <<'PY'
from pathlib import Path
import json
import shutil
import re

RESULTS = Path("test_78_95_results.json")
OUTPUT = Path("output/test_classified")

# Порог для отдельной папки сомнительных результатов
LOW_MARGIN = 0.02
VERY_LOW_MARGIN = 0.005

# --------------------------------------------------
# LOAD JSON
# --------------------------------------------------

lines = RESULTS.read_text(encoding="utf-8").splitlines()

start = next(
    i for i, line in enumerate(lines)
    if line.strip() == "["
)

data = json.loads(
    "\n".join(lines[start:])
)

print(f"Results loaded: {len(data)}")

# --------------------------------------------------
# OUTPUT
# --------------------------------------------------

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)

# --------------------------------------------------
# SAFE COPY
# --------------------------------------------------

def safe_copy(src, dst_dir):
    dst_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    dst = dst_dir / src.name

    # Если одинаковое имя уже существует —
    # добавляем номер.
    if dst.exists():
        stem = src.stem
        suffix = src.suffix

        n = 2

        while True:
            candidate = (
                dst_dir
                / f"{stem}__{n}{suffix}"
            )

            if not candidate.exists():
                dst = candidate
                break

            n += 1

    shutil.copy2(
        src,
        dst,
    )

    return dst

# --------------------------------------------------
# CLASSIFY
# --------------------------------------------------

stats = {}

for r in data:

    src = Path(
        r["file"]
    )

    if not src.exists():
        print(
            f"[WARN] File not found: {src}"
        )
        continue

    best_id = r.get(
        "best_id"
    )

    score = float(
        r.get(
            "score",
            0.0,
        )
    )

    second = float(
        r.get(
            "second_score",
            0.0,
        )
    )

    margin = float(
        r.get(
            "margin",
            0.0,
        )
    )

    if not best_id:
        best_id = "NO_MATCH"

    # Основная папка TOP-1
    main_dir = (
        OUTPUT
        / str(best_id)
    )

    safe_copy(
        src,
        main_dir,
    )

    stats.setdefault(
        str(best_id),
        0,
    )

    stats[str(best_id)] += 1

    # --------------------------------------------------
    # LOW CONFIDENCE
    # --------------------------------------------------

    if margin < LOW_MARGIN:

        low_dir = (
            OUTPUT
            / "_LOW_CONFIDENCE"
            / str(best_id)
        )

        safe_copy(
            src,
            low_dir,
        )

    # --------------------------------------------------
    # VERY LOW CONFIDENCE
    # --------------------------------------------------

    if margin < VERY_LOW_MARGIN:

        very_low_dir = (
            OUTPUT
            / "_VERY_LOW_CONFIDENCE"
            / str(best_id)
        )

        safe_copy(
            src,
            very_low_dir,
        )

# --------------------------------------------------
# REPORT
# --------------------------------------------------

print()
print("=" * 70)
print("CLASSIFICATION COMPLETE")
print("=" * 70)

print(
    f"Total results: {len(data)}"
)

print()

for fingerprint_id in sorted(
    stats,
    key=lambda x: (
        int(
            re.search(
                r"\d+",
                x,
            ).group()
        )
        if re.search(
            r"\d+",
            x,
        )
        else 9999
    )
):

    print(
        f"{fingerprint_id:20} "
        f"{stats[fingerprint_id]:4d}"
    )

print()
print(
    f"Output: {OUTPUT}"
)
print()
print(
    "LOW_CONFIDENCE: "
    f"margin < {LOW_MARGIN}"
)
print(
    "VERY_LOW_CONFIDENCE: "
    f"margin < {VERY_LOW_MARGIN}"
)
PY

uv run python classify_test_results.py
```

После этого структура будет примерно такая:

```text
output/
└── test_classified/
    ├── 78_v33/
    │   ├── фото1.JPG
    │   ├── фото2.JPG
    │   └── ...
    │
    ├── 79_v33/
    │   └── ...
    │
    ├── 80_v33/
    │   └── ...
    │
    ├── ...
    │
    ├── 95_v33_fast/
    │   └── ...
    │
    ├── _LOW_CONFIDENCE/
    │   ├── 78_v33/
    │   ├── 83_v33/
    │   └── ...
    │
    └── _VERY_LOW_CONFIDENCE/
        ├── 78_v33/
        └── ...
```

### Это особенно полезно для нашей проверки

Например, если после классификации увидим:

```text
83_v33       17 фото
84_v33       31 фото
85_v33       12 фото
```

можно сразу открыть папки и визуально проверить результат.

А `_VERY_LOW_CONFIDENCE` даст нам самые интересные случаи — например твой:

```text
008.JPG
TOP1 = 83_v33
SCORE = 0.9096
SECOND = 0.9082
MARGIN = 0.0014
```

Он попадёт сюда:

```text
output/test_classified/_VERY_LOW_CONFIDENCE/83_v33/
```

**Важно:** скрипт копирует фотографии, поэтому исходная `data/input/test` останется нетронутой.

После запуска пришли вывод `CLASSIFICATION COMPLETE` — по нему уже можно будет увидеть распределение 262 фотографий по 18 адресам.

---

### 👤 **User** — 2026-08-15 00:31:59

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat > classify_test_results.py <<'PY'
from pathlib import Path
import json
import shutil
import re

RESULTS = Path("test_78_95_results.json")
OUTPUT = Path("output/test_classified")

# Порог для отдельной папки сомнительных результатов
LOW_MARGIN = 0.02
VERY_LOW_MARGIN = 0.005

# --------------------------------------------------
# LOAD JSON
# --------------------------------------------------

lines = RESULTS.read_text(encoding="utf-8").splitlines()

start = next(
    i for i, line in enumerate(lines)
uv run python classify_test_results.py------------------
Results loaded: 262

======================================================================
CLASSIFICATION COMPLETE
======================================================================
Total results: 262

78_v33                 20
79_v33                  8
80_v33                  8
81_v33                 16
82_v33                  9
83_v33                 18
84_v33                  8
85_v33                 17
86_v33_fast            15
87_v33_fast            20
88_v33_fast            16
89_v33_fast            20
90_v33_fast             3
91_v33_fast            13
92_v33_fast            18
93_v33_fast            12
94_v33_fast            24
95_v33_fast            17

Output: output/test_classified

LOW_CONFIDENCE: margin < 0.02
VERY_LOW_CONFIDENCE: margin < 0.005

---

### 🤖 **Assistant** — 2026-08-15 00:31:59

Отлично. **Все 262 фотографии успешно классифицированы**, ни один результат не потерялся.

Распределение:

| Слепок | Фото |
|---|---:|
| 78 | 20 |
| 79 | 8 |
| 80 | 8 |
| 81 | 16 |
| 82 | 9 |
| 83 | 18 |
| 84 | 8 |
| 85 | 17 |
| 86 | 15 |
| 87 | 20 |
| 88 | 16 |
| 89 | 20 |
| 90 | 3 |
| 91 | 13 |
| 92 | 18 |
| 93 | 12 |
| 94 | 24 |
| 95 | 17 |
| **Всего** | **262** |

Это уже хороший результат для визуальной проверки.

### Следующий шаг — самый важный

Теперь надо выяснить **не просто сколько фотографий попало в каждую папку, а сколько из них попало ПРАВИЛЬНО**.

Причём у нас есть идеальный источник истины: **имя исходной фотографии содержит адрес**, а наши слепки соответствуют адресам 78–95.

Я предлагаю сейчас сделать автоматический отчёт:

```text
==============================
BENCHMARK 78-95
==============================

TOTAL: 262

TOP-1 CORRECT:       XXX
TOP-1 WRONG:         XXX
ACCURACY:            XX.X%

TOP-2:               XX.X%
TOP-3:               XX.X%

------------------------------
CONFUSION
------------------------------

78 -> 79    X
78 -> 83    X
...
```

И самое полезное:

```text
==============================
WRONG TOP-1
==============================

Файл                              REAL    TOP1    SCORE   MARGIN
----------------------------------------------------------------
...
```

Но здесь есть нюанс: **сначала надо определить, как в твоих тестовых именах кодируется реальный адрес**. Судя по примерам вроде `Малиновского 25...`, реальный ID `90` и т. п. не записан напрямую в имени.

Поэтому лучше не делать предположений и не получить ложную accuracy.

### Зато можем прямо сейчас проверить распределение

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== LOW CONFIDENCE ==="
find output/test_classified/_LOW_CONFIDENCE -type f | wc -l

echo "=== VERY LOW CONFIDENCE ==="
find output/test_classified/_VERY_LOW_CONFIDENCE -type f | wc -l

echo
echo "=== CLASSIFIED ==="
find output/test_classified -mindepth 1 -maxdepth 1 -type d \
    ! -name "_LOW_CONFIDENCE" \
    ! -name "_VERY_LOW_CONFIDENCE" \
    -exec sh -c 'printf "%-20s %s\n" "$(basename "$1")" "$(find "$1" -type f | wc -l)"' _ {} \;
```

И **я бы ещё сделал одну очень полезную вещь**: создать `CSV`/таблицу со всеми 262 результатами:

```text
filename
TOP1
TOP2
score
second_score
margin
confidence
```

Тогда мы сможем сортировать их по `margin` и быстро найти **20–30 наиболее спорных фотографий**.

Сейчас у нас уже есть всё необходимое для этого.

---

### 👤 **User** — 2026-08-15 00:33:01

на адрес пока можно не обращать внимания - названия произвольные

---

### 🤖 **Assistant** — 2026-08-15 00:33:02

Да, тогда **вообще не используем имена файлов для оценки правильности**. В этом тесте у нас пока нет ground truth, поэтому считаем задачу именно как **разбор поведения распознавания**.

И я бы сейчас не трогал accuracy. Гораздо полезнее посмотреть:

1. какие TOP-1 получились;
2. насколько уверенно они получились;
3. какие адреса система чаще всего путает;
4. сколько фотографий имеют почти равные TOP-1/TOP-2;
5. какие конкретно кадры стоит проверить глазами.

У тебя уже есть `output/test_classified`, поэтому можно сделать очень наглядный отчёт.

### 1. Посчитать уверенность

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path
import json
from collections import Counter

p = Path("test_78_95_results.json")
lines = p.read_text(encoding="utf-8").splitlines()

start = next(
    i for i, line in enumerate(lines)
    if line.strip() == "["
)

data = json.loads("\n".join(lines[start:]))

margins = [float(r.get("margin", 0)) for r in data]
scores = [float(r.get("score", 0)) for r in data]

print("=" * 70)
print("TEST 78-95 / 262 PHOTOS")
print("=" * 70)

print(f"Photos:              {len(data)}")
print(f"Average score:       {sum(scores)/len(scores):.4f}")
print(f"Average margin:      {sum(margins)/len(margins):.4f}")

print()
print("MARGIN DISTRIBUTION")
print("-" * 70)

groups = [
    ("< 0.005", lambda x: x < 0.005),
    ("0.005 - 0.010", lambda x: 0.005 <= x < 0.010),
    ("0.010 - 0.020", lambda x: 0.010 <= x < 0.020),
    ("0.020 - 0.050", lambda x: 0.020 <= x < 0.050),
    ("0.050 - 0.100", lambda x: 0.050 <= x < 0.100),
    (">= 0.100", lambda x: x >= 0.100),
]

for name, fn in groups:
    count = sum(fn(x) for x in margins)
    print(f"{name:18} {count:4}  ({count/len(data)*100:5.1f}%)")

print()
print("TOP-1 DISTRIBUTION")
print("-" * 70)

counter = Counter(
    str(r.get("best_id"))
    for r in data
)

for fp, count in sorted(
    counter.items(),
    key=lambda x: int(
        ''.join(
            c for c in x[0]
            if c.isdigit()
        )
    )
):
    print(f"{fp:20} {count:4}")

print()
print("=" * 70)
PY
```

### 2. И отдельно — самые спорные кадры

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path
import json

p = Path("test_78_95_results.json")
lines = p.read_text(encoding="utf-8").splitlines()

start = next(
    i for i, line in enumerate(lines)
    if line.strip() == "["
)

data = json.loads("\n".join(lines[start:]))

data.sort(
    key=lambda r: float(
        r.get("margin", 0)
    )
)

print("=" * 120)
print("20 MOST AMBIGUOUS PHOTOS")
print("=" * 120)

for i, r in enumerate(data[:20], 1):

    name = Path(
        r["file"]
    ).name

    candidates = r.get(
        "candidates",
        []
    )

    top1 = candidates[0] if len(candidates) > 0 else {}
    top2 = candidates[1] if len(candidates) > 1 else {}

    print()
    print(
        f"{i:2}. {name}"
    )

    print(
        f"    TOP1   {top1.get('id')} "
        f"score={top1.get('score', 0):.4f}"
    )

    print(
        f"    TOP2   {top2.get('id')} "
        f"score={top2.get('score', 0):.4f}"
    )

    print(
        f"    MARGIN {r.get('margin', 0):.4f}"
    )
PY
```

### И вот это будет особенно интересно

Мы уже разложили фотографии:

```text
output/test_classified/78_v33/
output/test_classified/79_v33/
...
output/test_classified/95_v33_fast/
```

Поэтому можно **визуально открыть каждую папку и сравнить**, что система туда положила.

А `_VERY_LOW_CONFIDENCE` — это практически готовая папка:

> **«Покажи мне фотографии, в которых DINO не уверен между двумя адресами».**

Для нашего проекта это даже важнее искусственной accuracy, пока у нас нет размеченного тестового набора.

**Следующим этапом я бы сделал confusion matrix по TOP-1 → TOP-2**, например:

```text
78 → 79   3
78 → 83   1
83 → 84   5
84 → 86   2
...
```

Это покажет, **какие именно адреса визуально неразличимы для текущего fingerprint v3.3**.

---

### 👤 **User** — 2026-08-15 00:34:36

давай прогоним еще раз финальный тест, для вывода будем использовать /home/alexice/projects/scene_fingerprint_mvp_v02/data/output/test_classified

---

### 🤖 **Assistant** — 2026-08-15 00:34:37

Да. Сейчас лучше сделать **чистый финальный прогон** по `data/input/test`, используя все слепки `78–95`, а результат сразу раскладывать в:

`/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/test_classified`

Причём названия файлов пока **не используем для оценки правильности** — только `best_id`, score и margin.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf data/output/test_classified
mkdir -p data/output/test_classified

time uv run scene-fingerprint recognize \
    data/input/test \
    --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33_fast,87_v33_fast,88_v33_fast,89_v33_fast,90_v33_fast,91_v33_fast,92_v33_fast,93_v33_fast,94_v33_fast,95_v33_fast \
    --top-k 5 \
    --workers 6 \
    --json \
    > final_test_78_95.json
```

После окончания проверь:

```bash
tail -20 final_test_78_95.json
```

Но **важный момент:** как и раньше, в `final_test_78_95.json` будут диагностические строки перед JSON. Поэтому для дальнейшего анализа используем не сам файл напрямую, а извлечём JSON-массив.

### Затем автоматически разложим результаты

Сначала создай новый классификатор:

```bash
cat > classify_final_test.py <<'PY'
from pathlib import Path
import json
import shutil

RESULTS = Path("final_test_78_95.json")
SOURCE = Path("data/input/test")
OUTPUT = Path("data/output/test_classified")

LOW_MARGIN = 0.02
VERY_LOW_MARGIN = 0.005

OUTPUT.mkdir(parents=True, exist_ok=True)

# -----------------------------
# LOAD JSON
# -----------------------------

lines = RESULTS.read_text(encoding="utf-8").splitlines()

start = None

for i, line in enumerate(lines):
    if line.strip() == "[":
        start = i
        break

if start is None:
    raise RuntimeError("JSON array not found")

data = json.loads("\n".join(lines[start:]))

print(f"Results loaded: {len(data)}")

# -----------------------------
# CLASSIFICATION
# -----------------------------

counts = {}

for r in data:

    file_path = Path(r["file"])
    filename = file_path.name

    best_id = r.get("best_id")

    if not best_id:
        folder_name = "NO_MATCH"
    else:
        margin = float(r.get("margin", 0))

        if margin < VERY_LOW_MARGIN:
            folder_name = "_VERY_LOW_CONFIDENCE"
        elif margin < LOW_MARGIN:
            folder_name = "_LOW_CONFIDENCE"
        else:
            folder_name = str(best_id)

    destination_dir = OUTPUT / folder_name
    destination_dir.mkdir(parents=True, exist_ok=True)

    source_file = SOURCE / filename
    destination_file = destination_dir / filename

    if source_file.exists():
        shutil.copy2(source_file, destination_file)
    else:
        # fallback: use original path from JSON
        if file_path.exists():
            shutil.copy2(file_path, destination_file)
        else:
            print(f"WARNING: source not found: {filename}")
            continue

    counts[folder_name] = counts.get(folder_name, 0) + 1

# -----------------------------
# REPORT
# -----------------------------

print()
print("=" * 70)
print("FINAL CLASSIFICATION")
print("=" * 70)

for name, count in sorted(counts.items()):
    print(f"{name:25} {count:4}")

print()
print(f"TOTAL: {sum(counts.values())}")
print(f"OUTPUT: {OUTPUT}")
PY
```

И запусти:

```bash
uv run python classify_final_test.py
```

После этого структура будет примерно:

```text
data/output/test_classified/
├── 78_v33/
├── 79_v33/
├── 80_v33/
├── 81_v33/
├── ...
├── 95_v33_fast/
├── _LOW_CONFIDENCE/
└── _VERY_LOW_CONFIDENCE/
```

### И главное

После этого **не будем смотреть на названия адресов**. Следующий этап я бы сделал гораздо полезнее: получить сводку вида

```text
FINGERPRINT       IMAGES   AVG SCORE   AVG MARGIN
78_v33               20      0.93        0.051
79_v33                8      0.91        0.044
...
```

и отдельно:

```text
VERY LOW MARGIN       7
LOW MARGIN           23
NORMAL               232
```

Это покажет, **насколько система уверенно различает 18 адресов**, даже пока мы не знаем, какой TOP-1 фактически правильный.

---

### 👤 **User** — 2026-08-15 00:41:12

а если рассортировывать файлы даже с низкой степень уверенности - по первому кандидату

---

### 🤖 **Assistant** — 2026-08-15 00:41:12

Да. **Именно так я бы и сделал для финального теста.**

У нас задача не «отбраковать» фотографии, а **всегда определить наиболее вероятный адрес**. Поэтому:

- TOP-1 → **всегда определяет папку**
- score → сохраняем для анализа
- margin → сохраняем для анализа
- низкая уверенность **не меняет папку**
- `NO_MATCH` не нужен, если вообще есть хотя бы один кандидат

То есть даже:

```text
TOP1 = 83_v33
SCORE = 0.71
TOP2 = 0.70
MARGIN = 0.01
```

фото всё равно идёт в:

```text
data/output/test_classified/83_v33/
```

А не в `_LOW_CONFIDENCE`.

### Делаем именно так

Перепиши `classify_final_test.py`:

```bash id="g8z1pv"
cd ~/projects/scene_fingerprint_mvp_v02

cat > classify_final_test.py <<'PY'
from pathlib import Path
import json
import shutil

RESULTS = Path("final_test_78_95.json")
SOURCE = Path("data/input/test")
OUTPUT = Path("data/output/test_classified")

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)

# --------------------------------------------------
# LOAD JSON
# --------------------------------------------------

lines = RESULTS.read_text(
    encoding="utf-8"
).splitlines()

start = None

for i, line in enumerate(lines):
    if line.strip() == "[":
        start = i
        break

if start is None:
    raise RuntimeError(
        "JSON array not found"
    )

data = json.loads(
    "\n".join(lines[start:])
)

print(
    f"Results loaded: {len(data)}"
)

# --------------------------------------------------
# COPY BY TOP-1
# --------------------------------------------------

counts = {}

for r in data:

    file_path = Path(
        r["file"]
    )

    filename = file_path.name

    # TOP-1 ALWAYS WINS
    best_id = r.get(
        "best_id"
    )

    # Если best_id отсутствует,
    # берём первого кандидата.
    if not best_id:

        candidates = r.get(
            "candidates",
            []
        )

        if candidates:
            best_id = candidates[0].get(
                "id"
            )

    # Только если вообще нет кандидата
    if not best_id:
        folder_name = "NO_CANDIDATE"
    else:
        folder_name = str(
            best_id
        )

    destination_dir = (
        OUTPUT / folder_name
    )

    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_file = (
        SOURCE / filename
    )

    if not source_file.exists():

        if file_path.exists():
            source_file = file_path

        else:
            print(
                f"[WARNING] "
                f"Source not found: "
                f"{filename}"
            )
            continue

    destination_file = (
        destination_dir
        / filename
    )

    # Защита от одинаковых имён
    if destination_file.exists():

        stem = destination_file.stem
        suffix = destination_file.suffix

        n = 2

        while True:

            candidate = (
                destination_dir
                / f"{stem}__{n}{suffix}"
            )

            if not candidate.exists():
                destination_file = candidate
                break

            n += 1

    shutil.copy2(
        source_file,
        destination_file,
    )

    counts[folder_name] = (
        counts.get(
            folder_name,
            0,
        ) + 1
    )

# --------------------------------------------------
# REPORT
# --------------------------------------------------

print()
print("=" * 70)
print("FINAL TOP-1 CLASSIFICATION")
print("=" * 70)

total = 0

for name in sorted(
    counts,
    key=lambda x: (
        int(
            "".join(
                c
                for c in x
                if c.isdigit()
            )
        )
        if any(
            c.isdigit()
            for c in x
        )
        else 9999
    ),
):

    count = counts[name]
    total += count

    print(
        f"{name:20} {count:4}"
    )

print()
print(
    f"TOTAL COPIED: {total}"
)

print(
    f"OUTPUT: {OUTPUT}"
)
PY
```

Затем:

```bash id="y9l9jd"
rm -rf data/output/test_classified

uv run python classify_final_test.py
```

### Получим именно такую логику

```text
262 фотографии
       │
       ▼
18 fingerprint
       │
       ▼
┌──────────────────────┐
│ выбираем TOP-1       │
│ независимо от score  │
└──────────┬───────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
 83_v33        91_v33
    │             │
    ▼             ▼
папка 83       папка 91
```

А `score` и `margin` остаются в `final_test_78_95.json`, поэтому **мы ничего не теряем**.

Это как раз соответствует твоей задаче: **для каждой фотографии всегда дать наиболее вероятный адрес**, даже если модель уверена всего на 51%.

И я бы оставил это поведение основным для будущего рекламного пайплайна: оператору важнее получить **предполагаемый адрес**, чем получить `NO_MATCH`.

---

### 👤 **User** — 2026-08-15 00:45:30

в каждой папке есть как минимум 1 визуально определяемая ошибка. Про84 кажется - плохо создан слепок

---

### 🤖 **Assistant** — 2026-08-15 00:45:34

Да. И это уже важный результат: **ошибки есть не только в распознавании, но и в самих fingerprint'ах**.

Для `84` я бы действительно пока **не пытался подкручивать алгоритм**. Если в папке `84` есть визуально очевидные фотографии, которые не похожи на остальные, значит сначала нужно проверить качество исходного набора и пересоздать слепок.

Я предлагаю следующий порядок:

1. **Не учитывать названия файлов** — только визуальное соответствие.
2. Все 262 фото пока раскладывать **строго по TOP-1**, даже при низком score/margin.
3. Получаем `test_classified/78...95`.
4. В каждой папке смотрим выбросы.
5. Для `84` отдельно проверяем исходные 54 фотографии:
   - нет ли фотографий другого адреса;
   - нет ли сильно отличающихся ракурсов;
   - нет ли плохих/размытых кадров;
   - нет ли серии, которая фактически относится к другому месту.
6. После очистки `84` пересоздаём `84_v33_fast`.
7. Повторяем тест **только 84** и смотрим, ушли ли ошибки.
8. Если качество заметно улучшилось — аналогично проверяем остальные fingerprint'ы.

### Важный момент

Сейчас у нас:

- 262 тестовых фотографии;
- 18 fingerprint'ов: `78–95`;
- TOP-1 всегда назначается;
- `margin` показывает, насколько уверенно выбран первый кандидат относительно второго.

Например:

```text
008.JPG
TOP1=83_v33
SCORE=0.9096
SECOND=0.9082
MARGIN=0.0014
```

Это **очень подозрительный результат**. Алгоритм практически не различает `83` и второго кандидата.

А вот:

```text
006.JPG
TOP1=80_v33
SCORE=0.9667
SECOND=0.8219
MARGIN=0.1447
```

— очень сильное распознавание.

Поэтому я бы **не отбрасывал слабые результаты**, как ты предложил. Их нужно раскладывать по TOP-1, но одновременно сохранять score/margin для последующего анализа.

И ещё: **не надо сейчас менять веса `0.70 / 0.20 / 0.07 / 0.03`**. Сначала выясним качество fingerprint'ов. Иначе мы начнём компенсировать плохой слепок настройками распознавания.

Если хочешь, следующим шагом можем сделать **автоматический аудит всех 18 слепков**: программа сама найдёт фотографии внутри каждого fingerprint, которые наиболее сильно отличаются от остальных, и выведет, например:

```text
84_v33_fast
--------------------------------
54 images
10 подозрительных
  01.jpg  similarity=0.61
  17.jpg  similarity=0.64
  31.jpg  similarity=0.66
...
```

Это как раз позволит быстро понять, **какие исходные фотографии портят каждый слепок**, не просматривая вручную все ~1000 снимков.

---

### 👤 **User** — 2026-08-15 00:46:24

84 специально сделан с разных ракурсов - надо это учесть

---

