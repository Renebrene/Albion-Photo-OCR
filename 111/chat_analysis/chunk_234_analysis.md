## 1. ЗАДАЧА  
Обсудить изменения в архитектуре проекта: заменить отдельный DINO_WORKER на интеграцию DINO 33 в Hybrid v12, убрать Qwen как отдельный worker, и начать чистый прогон базы данных с присвоением `photo_id`.

---

## 2. ФАЙЛЫ И МОДУЛИ  
- `app/pipeline/supervisor.py` — содержит функцию `run_pipeline()`, управляющую запуском DINO и Qwen как отдельных процессов.  
- `run_hybrid_v12.py` — планируемый модуль, который должен заменить DINO_WORKER и интегрировать DINO 33 внутрь Hybrid v12.  

---

## 3. АРХИТЕКТУРА  
- **Технология/фреймворк**:  
  - `asyncio` для асинхронного управления процессами (DINO, Qwen).  
  - PostgreSQL для хранения состояний (`dino_status`, `qwen_status`).  
- **Паттерны проектирования**:  
  - **Асинхронное программирование** (использование `async/await`).  
  - **Синглтон-подход** для управления жизненным циклом процессов.  
- **Структура данных**:  
  - Использование `returncode` для отслеживания статуса завершения процессов.  
  - Параллельная обработка данных через асинхронные задачи.  

---

## 4. НАПИСАННЫЙ КОД  
Ключевые фрагменты из `supervisor.py`:  
```python
async def run_pipeline():
    """
    Один полный запуск DINO + Qwen.
    """
    dino_process, dino_output = await start_worker(DINO_WORKER, "DINO")
    qwen_process, qwen_output = await start_worker(QWEN_WORKER, "QWEN")

    while True:
        dino_running = process_running(dino_process)
        qwen_running = process_running(qwen_process)
        if not dino_running and not qwen_running:
            break
        if is_stop_requested():
            await stop_process(dino_process, "DINO")
            await stop_process(qwen_process, "QWEN")
            break
        await asyncio.sleep(POLL_INTERVAL)

    dino_code = dino_process.returncode if dino_process is not None else None
    qwen_code = qwen_process.returncode if qwen_process is not None else None

    await stop_process(dino_process, "DINO")
    await stop_process(qwen_process, "QWEN")
```

---

## 5. НЕЗАВЕРШЁННОЕ  
- [ ] Замена DINO_WORKER на Hybrid v12 (не реализована).  
- [ ] Очистка PostgreSQL-базы и присвоение `photo_id` (планируется, но не выполнено).  
- [ ] Интеграция Qwen в Hybrid v12 (не реализована).  

---

## 6. КЛЮЧЕВЫЕ РЕШЕНИЯ  
- **Удаление DINO_WORKER** → Замена на Hybrid v12, где DINO 33 запускается внутрь (ускорение обработки, устранение избыточности).  
- **Чистый прогон базы** → Очистка PostgreSQL перед тестированием, чтобы избежать влияния старых данных.  
- **Асинхронное управление процессами** → Обеспечение параллельной обработки DINO и Qwen без блокировки основного потока.