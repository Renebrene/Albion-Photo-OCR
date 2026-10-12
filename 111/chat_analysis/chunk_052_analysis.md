### 🛠️ **Решение проблемы с подслепками**

#### 🔍 **Что происходит?**
Сейчас `FingerprintManager.create()` **перезаписывает** подслепки, потому что:
- `fingerprint_id` в `build_subfingerprint_database.py` формируется как `address_sub_dir_name` (например, `84_v33_sub_1`).
- Но в `fingerprint.py` внутри `create()` используется **частично обрезанный ID**, например, `84_v33`, а не полный `84_v33_sub_1`.

#### 🛠️ **Как исправить?**
Нужно **уточнить логику `_path()`** в `fingerprint.py`, чтобы она использовала **полный `fingerprint_id`**, а не только базовый.

---

### ✅ **Исправление в `fingerprint.py`**

Открой файл:
```bash
nano app/core/fingerprint.py
```

Найди функцию `def _path(...)` и измените её так:

```python
def _path(
    self,
    fingerprint_id,
):
    return (
        self.root / str(fingerprint_id)
    )
```

**Убедись**, что `fingerprint_id` передаётся **полным**, без обрезки. Если в `create()` есть код вроде:
```python
fingerprint_id = fingerprint_id.split("_")[0]
```
— удалите его. Это и есть причина перезаписи.

---

### 🧹 **Проверка и пересборка**

1. **Удалите старую базу:**
```bash
rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp
```

2. **Запустите скрипт:**
```bash
uv run python scripts/build_subfingerprint_database.py
```

3. **Проверьте результат:**
```bash
find data/fingerprints_sub_exp -maxdepth 1 -type d | sort
```

Ожидаемый вывод:
```
84_v33_sub_1
84_v33_sub_2
85_v33_sub_1
85_v33_sub_2
87_v33_sub_1
87_v33_sub_2
89_v33_sub_1
89_v33_sub_2
89_v33_sub_3
92_v33_sub_1
92_v33_sub_2
94_v33_sub_1
94_v33_sub_2
94_v33_sub_3
95_v33_sub_1
95_v33_sub_2
95_v33_sub_3
```

4. **Проверьте количество созданных подслепков:**
```bash
grep -A5 "created:" scripts/build_subfingerprint_database.py | tail -n1
```

Ожидаемый вывод:
```
created: 17
```

---

### 📌 **Итог**
Теперь подслепки будут храниться **отдельно**, и система сможет корректно сравнивать:
- **Вариант А:** только `*_v33`
- **Вариант Б:** `*_v33` + `*_sub_*`

После этого можно запускать тесты на улучшение точности распознавания.