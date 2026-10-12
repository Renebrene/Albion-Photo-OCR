### ✅ **Шаг 3: Фильтрация fingerprint'ов в `recognize_folder()`**

Теперь заменяем логику выбора fingerprint'ов в `recognize_folder()`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
text = p.read_text()

old = '''        fingerprints = FingerprintManager(self.settings, self.embedder).list_fingerprints()'''

new = '''        if args.fingerprints:
            fingerprints = [f for f in FingerprintManager(self.settings, self.embedder).list_fingerprints() if f in args.fingerprints.split(",")]
        else:
            fingerprints = FingerprintManager(self.settings, self.embedder).list_fingerprints()'''

if old not in text:
    raise SystemExit("Fingerprint filter logic not found")

p.write_text(text.replace(old, new))

print("OK: Fingerprint filter logic updated")
PY
```

---

### ✅ **Шаг 4: Запуск чистого теста**

Теперь можем запустить:

```bash
uv run scene-fingerprint recognize data/input/test \
  --fingerprints 86_v33_fast,87_v33_fast,88_v33_fast,89_v33_fast,90_v33_fast,91_v33_fast,92_v33_fast,93_v33_fast,94_v33_fast,95_v33_fast \
  --top-k 5 \
  --workers 6
```

---

### 📌 **Что будет дальше?**

1. **Результаты** появятся в JSON-формате (если `--json` включён).
2. После этого я помогу:
   - Собрать статистику (TOP-1, TOP-2, средний score и т.д.);
   - Найти часто путающиеся адреса;
   - Оценить качество новых слепков.

Ты можешь запускать тест сейчас, а я подожду вывода.