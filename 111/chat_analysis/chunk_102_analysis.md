### 🛠️ **Шаг 1: Найти точку входа кнопки "Распознать" в веб-интерфейсе**

Поскольку ты работаешь в проекте на `NEURO`, выполним команду для поиска всех файлов, связанных с кнопкой "Распознать" и обработкой распознавания:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -R -n -E \
'Распознать|Распозна|recognize|recognition|sort_test_and_report|qwen|Qwen' \
app \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -300
```

**Ожидаемый результат:**
- Найдутся файлы, связанные с веб-интерфейсом (например, `app/web/routes.py`, `app/web/controllers.py`, `app/web/views.py`).
- В них будет вызываться функция, которая запускает `recognize` или `sort_test_and_report`.

---

### 🧠 **Шаг 2: Убедиться, что распознаватель не трогается**

Важно: **алгоритм v33 и `recognize` не трогаются**. Мы просто встраиваем его в пайплайн.

**Проверяем, что:**
1. `recognize` возвращает `TOP-N` кандидатов.
2. `sort_test_and_report` работает поверх `recognize`.
3. `Qwen` запускается после сортировки.

---

### 🧩 **Шаг 3: Встроить последовательный пайплайн в веб-интерфейс**

После нахождения точки входа, вставляем следующий пайплайн:

```python
def handle_recognize_button():
    # 1. Проверка входной папки
    input_folder = get_input_folder()
    if not os.path.exists(input_folder):
        return {"error": "Папка с фотографиями не найдена"}

    # 2. DINO / v33
    dino_results = run_dino_v33(input_folder)
    if not dino_results:
        return {"error": "DINO не вернул результатов"}

    # 3. РАСПОЗНАВАТЕЛЬ (hybrid-логика)
    final_address = run_hybrid_recognizer(dino_results)
    if not final_address:
        return {"error": "Распознаватель не определил адрес"}

    # 4. Сортировка фотографий
    sort_photos_by_address(final_address)

    # 5. Qwen3-VL 4B
    qwen_results = run_qwen_analysis(final_address)

    return {
        "address": final_address,
        "qwen_results": qwen_results,
        "status": "success"
    }
```

---

### 📁 **Шаг 4: Убедиться, что создание fingerprint отделено**

В отдельном скрипте (например, `create_fingerprint.py`) должен быть код:

```python
def create_fingerprint(input_folder):
    # Логика создания fingerprint v33
    pass
```

Это **отдельный процесс**, не связанный с кнопкой "Распознать".

---

### 📌 **Итог**

- Кнопка "Распознать" запускает **последовательный пайплайн**:
  1. DINO / v33 → TOP-N
  2. Hybrid-распознаватель → финальный адрес
  3. Сортировка
  4. Qwen3-VL 4B
- Создание fingerprint — **отдельный процесс**, не связанный с кнопкой.
- Алгоритм v33 и `recognize` **не трогаются**.

Если ты хочешь, я могу помочь с реализацией конкретного файла (например, `app/web/controllers.py`), чтобы вставить этот пайплайн.