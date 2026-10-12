> **Inspecting photo processing module**
>
>
> **Inspecting photo processing module**
>
> 
>
> Worked for a couple of seconds

Делаем подключение Qwen к кнопке. Нужно:

1. Сохранить бэкап
2. Добавить запуск Qwen после Hybrid v12
3. Передать папку результата
4. Создать отдельную папку `metadata/qwen4b/<timestamp>`
5. Отображать прогресс в интерфейсе
6. Не брать весь Hybrid как неуспешный при ошибке Qwen

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/technical_modules/photo_processing.py \
   app/web/components/technical_modules/photo_processing.py.bak_before_qwen_integration && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/photo_processing.py")
s = p.read_text(encoding="utf-8")

old = '''            status_label.text = (
                "✓ Сортировка завершена → "
                "готово к Qwen"
            )

            ui.notify(
                "✓ Фотографии рассортированы. "
                "Следующий этап: Qwen3-VL 4B.",
                type="positive",
                timeout=5000,
            )'''

new = '''            status_label.text = (
                "✓ Сортировка завершена → "
                "готово к Qwen"
            )

            ui.notify(
                "✓ Фотографии рассортированы. "
                "Следующий этап: Qwen3-VL 4B.",
                type="positive",
                timeout=5000,
            )

            # ====================================================
            # QWEN
            # ====================================================
            try:
                # Создаём отдельную папку для Qwen
                qwen_output_dir = Path(
                    "data/metadata/qwen4b"
                ) / result_dir.name

                qwen_output_dir.mkdir(parents=True, exist_ok=True)

                # Запускаем Qwen с текущей папкой результата
                qwen_cmd = [
                    "uv", "run", "python", "scripts/qwen4b_output_v01.py",
                    "--input", str(result_dir),
                    "--output", str(qwen_output_dir),
                    "--limit", "1"
                ]

                print("Qwen command:", " ".join(qwen_cmd))

                result = subprocess.run(
                    qwen_cmd,
                    capture_output=True,
                    text=True,
                    check=False
                )

                if result.returncode == 0:
                    ui.notify(
                        "Qwen3-VL 4B: ✓ завершён",
                        type="positive",
                        timeout=5000
                    )
                    status_label.text = (
                        "✓ Hybrid v12: сортировка завершена → "
                        "Qwen3-VL 4B: завершён"
                    )
                else:
                    ui.notify(
                        f"Qwen3-VL 4B: ✗ ошибка ({result.returncode})",
                        type="negative",
                        timeout=8000
                    )
                    status_label.text = (
                        "✓ Hybrid v12: сортировка завершена → "
                        "Qwen3-VL 4B: ошибка"
                    )

            except Exception as e:
                ui.notify(
                    f"Qwen3-VL 4B: ✗ ошибка ({e})",
                    type="negative",
                    timeout=8000
                )
                status_label.text = (
                    "✓ Hybrid v12: сортировка завершена → "
                    "Qwen3-VL 4B: ошибка"
                )

            finally:
                run_button.enable()
'''

if old not in s:
    raise SystemExit("ERROR: expected block not found")

p.write_text(s.replace(old, new), encoding="utf-8")

print("PATCH: OK")
PY

uv run python -m py_compile app/web/components/technical_modules/photo_processing.py && \
echo "QWEN PYCOMPILE: OK"
```

После этого:

1. Запуск Hybrid v12 → ✅
2. Запуск Qwen3-VL 4B → ✅
3. В интерфейсе будет:
   - `✓ Hybrid v12: сортировка завершена → Qwen3-VL 4B: завершён`
   - или `✓ Hybrid v12: сортировка завершена → Qwen3-VL 4B: ошибка`

**Важно:**  
- Qwen запускается **только после успешного Hybrid v12**
- Ошибки Qwen **не брать за весь Hybrid**
- Папка `metadata/qwen4b/<timestamp>` создаётся **отдельно**
- Пока обрабатываем **1 файл** для теста

Теперь можно запускать полный цикл:  
`Hybrid v12 → Qwen3-VL 4B`  
с отслеживанием прогресса в интерфейсе.