### 🤖 **Assistant** — 2026-08-15 19:41:13

Вот, проблема в том, что `FingerprintManager.create()` **не использует весь `fingerprint_id`**, а **обрезает его до базового ID**.

В `fingerprint.py` в `def create()`:

```python
output = self._path(
    fingerprint_id.split("_")[0]
)
```

или:

```python
output = self._path(
    fingerprint_id.split("_")[0]
)
```

То есть, если `fingerprint_id = "84_v33_sub_1"`, то `output = "84_v33"`.

Это приводит к тому, что **все подслепки записываются в одну папку**, и последние перезаписывают старые.

---

### 🔧 **Решение**

Исправим `fingerprint.py`:

```python
output = self._path(
    fingerprint_id
)
```

или, если нужно сохранять структуру:

```python
output = self._path(
    fingerprint_id
)
```

---

### 📁 **Проверка**

После исправления:

```bash
rm -rf data/fingerprints_sub_exp
mkdir -p data/fingerprints_sub_exp

uv run python scripts/build_subfingerprint_database.py
```

Ожидаемый результат:

```
created: 17
```

и:

```bash
find data/fingerprints_sub_exp -maxdepth 1 -type d | sort
```

должен показать:

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

---

### 📌 **Важно**

Теперь можно запускать сравнительный тест:

**вариант А:** только `*_v33`  
**вариант Б:** `*_v33` + `*_sub_*`

и сравнивать, улучшились ли 7 ошибочных кадров из V38.1.