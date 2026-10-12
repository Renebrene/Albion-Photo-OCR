### 🛠️ **Решение проблемы: доступ к изображениям через HTTP**

#### 🔍 **Что происходит**
В коде используется путь `display_path`, который ссылается на файлы внутри проекта (например, `/data/output/daily/.../preview/...jpg`). Однако **HTTP-сервер FastAPI не настроен на раздачу этих файлов**, поэтому браузер не может получить доступ к ним.

---

### ✅ **Шаг 1: Проверить текущие настройки статики**

В `main.py` есть монтирование `/v2` для фронтенда:

```python
app.mount(
    "/v2",
    StaticFiles(
        directory=Path("app/web/frontend_v2").resolve(),
        html=True,
    ),
    name="frontend_v2",
)
```

Это **не настраивает доступ к изображениям** в `/data/output` или `/data/preview`.

---

### ✅ **Шаг 2: Добавить монтирование для изображений**

Добавь в `main.py` следующие строки:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/output", StaticFiles(directory="data/output"))
app.mount("/preview", StaticFiles(directory="data/preview"))
```

Это позволит браузеру получить доступ к изображениям по адресам:

- `http://192.168.1.5:8081/output/...jpg`
- `http://192.168.1.5:8081/preview/...jpg`

---

### ✅ **Шаг 3: Проверить пути в коде**

В `photos.py` используется:

```python
display_path = preview_path if preview_path else photo.path
```

Если `preview_path` — это путь в `/data/preview`, то после монтирования `/preview` браузер сможет получить доступ к файлам.

---

### ✅ **Шаг 4: Проверить права доступа**

Убедись, что папки `/data/output` и `/data/preview` доступны для чтения:

```bash
chmod -R 755 data/output data/preview
```

---

### ✅ **Шаг 5: Перезапустить сервер**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && uvicorn app.web.main:app --reload
```

---

### 🧪 **Проверка**

Открой в браузере:

```
http://192.168.1.5:8081/v2/
```

Если фото отображаются — **всё работает**. Если нет — проверь:

1. Правильно ли настроены маршруты `/output` и `/preview`.
2. Доступ к файлам в `/data/output` и `/data/preview`.
3. Логи FastAPI (проверь, не возникает ли ошибок 404).

---

### 📌 **Важно**
Если фото всё ещё не отображаются, можно временно использовать `FileResponse` для отдачи изображений, но это менее оптимально. Лучше настроить статику как в шаге 2.