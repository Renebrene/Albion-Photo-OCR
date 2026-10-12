### 🧠 **Алгоритм действий**

1. **Сохранение исходных файлов**
2. **Анализ текущего кода**
3. **Изменение структуры `main.py`**
4. **Проверка корректности работы**

---

### ✅ **Шаг 1: Сохранение исходных файлов**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/main.py /tmp/main.py.before && \
cp app/web/components/clients.py /tmp/clients.py.before && \
cp app/web/components/addresses.py /tmp/addresses.py.before && \
cp app/web/components/photos.py /tmp/photos.py.before && \
echo "BACKUP_OK"
```

---

### ✅ **Шаг 2: Анализ текущего кода**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ CLIENTS ================" && \
nl -ba app/web/components/clients.py | sed -n '1,320p' && \
echo "================ ADDRESSES ================" && \
nl -ba app/web/components/addresses.py | sed -n '1,320p' && \
echo "================ SCROLLS ================" && \
grep -RniE 'ui\.scroll_area|overflow-y|overflow-x|h-full|flex-1|min-h-0' \
app/web/main.py \
app/web/components/photos.py \
app/web/components/clients.py \
app/web/components/addresses.py
```

---

### ✅ **Шаг 3: Изменение структуры `main.py`**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -c "import sys; sys.path.append('app/web'); from main import app; app.run()" && \
echo "CHANGES_APPLIED"
```

---

### ✅ **Шаг 4: Проверка корректности работы**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -c "import sys; sys.path.append('app/web'); from main import app; app.run()" && \
echo "CHECK_OK"
```

---

### 📌 **Важно**

- Убедитесь, что фотографии отображаются и скролл работает.
- Проверьте, что нижняя панель всегда видна.
- Если всё работает, можно возвращаться к добавлению фильтров, настроек и других элементов.

Если возникнут ошибки, вернитесь к сохранённым файлам из `/tmp/` и повторите шаги.