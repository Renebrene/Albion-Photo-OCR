### 🚀 `app/pipeline/controller.py`

```python
from __future__ import annotations

from typing import Optional

from psycopg import connect
from psycopg.rows import dict_row
from psycopg_pool import PoolConfig, create_pool

from app.pipeline.modes import (
    MODE_MANUAL,
    MODE_AUTOMATIC,
    MODE_WATCHER,
    PipelineMode,
    build_manual_mode,
    build_automatic_mode,
    build_watcher_mode,
    reset_to_manual,
)

from app.pipeline.queue import (
    get_next_photo,
    mark_done,
    mark_error,
)

from app.pipeline.worker import (
    run_photo_ingest,
    run_dino,
    run_qwen,
    run_sort,
    run_preview,
)

import os
import time
import logging

# Инициализация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация пула подключений
POOL_CONFIG = PoolConfig(
    conninfo=os.getenv("DATABASE_URL"),
    min_size=1,
    max_size=5,
    timeout=30,
)

def get_pipeline_mode() -> PipelineMode:
    """Получить текущий режим из базы данных"""
    with create_pool(POOL_CONFIG).connect() as conn:
        conn.execute("SET LOCAL statement_timeout = '30s'")
        conn.execute("SET LOCAL lock_timeout = '10s'")
        
        result = conn.execute(
            """
            SELECT 
                mode,
                auto_enabled,
                auto_time,
                watcher_enabled,
                watcher_path,
                running,
                stop_requested,
                started_at,
                stopped_at
            FROM pipeline_control
            WHERE id = 1
            FOR UPDATE
            """
        ).fetchone()

        if not result:
            return build_manual_mode()

        return PipelineMode(
            mode=result[0],
            auto_enabled=result[1],
            auto_time=result[2],
            watcher_enabled=result[3],
            watcher_path=result[4],
            running=result[5],
            stop_requested=result[6],
        )

def set_pipeline_mode(mode: str) -> None:
    """Установить новый режим в базе данных"""
    with create_pool(POOL_CONFIG).connect() as conn:
        conn.execute("SET LOCAL statement_timeout = '30s'")
        conn.execute("SET LOCAL lock_timeout = '10s'")
        
        if mode == MODE_MANUAL:
            conn.execute(
                """
                UPDATE pipeline_control
                SET 
                    mode = 'manual',
                    auto_enabled = FALSE,
                    auto_time = NULL,
                    watcher_enabled = FALSE,
                    watcher_path = NULL,
                    running = FALSE,
                    stop_requested = FALSE,
                    started_at = NULL,
                    stopped_at = NULL
                WHERE id = 1
                """
            )
        elif mode == MODE_AUTOMATIC:
            conn.execute(
                """
                UPDATE pipeline_control
                SET 
                    mode = 'automatic',
                    auto_enabled = TRUE,
                    auto_time = (SELECT auto_time FROM pipeline_control WHERE id = 1),
                    watcher_enabled = FALSE,
                    watcher_path = NULL,
                    running = FALSE,
                    stop_requested = FALSE,
                    started_at = NULL,
                    stopped_at = NULL
                WHERE id = 1
                """
            )
        elif mode == MODE_WATCHER:
            conn.execute(
                """
                UPDATE pipeline_control
                SET 
                    mode = 'watcher',
                    auto_enabled = FALSE,
                    auto_time = NULL,
                    watcher_enabled = TRUE,
                    watcher_path = (SELECT watcher_path FROM pipeline_control WHERE id = 1),
                    running = FALSE,
                    stop_requested = FALSE,
                    started_at = NULL,
                    stopped_at = NULL
                WHERE id = 1
                """
            )
        else:
            raise ValueError(f"Unknown pipeline mode: {mode}")

def start_manual() -> None:
    """Запустить ручной режим"""
    current = get_pipeline_mode()
    
    if not current.can_manual_start():
        raise RuntimeError("Cannot start manual mode: invalid state")
    
    # Установить режим
    set_pipeline_mode(MODE_MANUAL)
    
    # Запустить процесс
    _run_pipeline()

def request_stop() -> None:
    """Запрос на остановку"""
    current = get_pipeline_mode()
    
    if not current.can_stop():
        raise RuntimeError("Cannot request stop: invalid state")
    
    # Установить флаг остановки
    with create_pool(POOL_CONFIG).connect() as conn:
        conn.execute("SET LOCAL statement_timeout = '30s'")
        conn.execute("SET LOCAL lock_timeout = '10s'")
        
        conn.execute(
            """
            UPDATE pipeline_control
            SET 
                stop_requested = TRUE
            WHERE id = 1
            """
        )

def reset_to_manual() -> None:
    """Вернуться в ручной режим"""
    current = get_pipeline_mode()
    
    if current.mode != MODE_MANUAL:
        set_pipeline_mode(MODE_MANUAL)
    
    # Установить состояние
    with create_pool(POOL_CONFIG).connect() as conn:
        conn.execute("SET LOCAL statement_timeout = '30s'")
        conn.execute("SET LOCAL lock_timeout = '10s'")
        
        conn.execute(
            """
            UPDATE pipeline_control
            SET 
                running = FALSE,
                stop_requested = FALSE,
                started_at = NULL,
                stopped_at = NOW()
            WHERE id = 1
            """
        )

def _run_pipeline() -> None:
    """Запустить полный pipeline"""
    current = get_pipeline_mode()
    
    if current.mode != MODE_MANUAL:
        raise RuntimeError("Invalid mode for pipeline execution")
    
    if current.running:
        raise RuntimeError("Pipeline is already running")
    
    # Установить стартовое время
    with create_pool(POOL_CONFIG).connect() as conn:
        conn.execute("SET LOCAL statement_timeout = '30s'")
        conn.execute("SET LOCAL lock_timeout = '10s'")
        
        conn.execute(
            """
            UPDATE pipeline_control
            SET 
                running = TRUE,
                started_at = NOW()
            WHERE id = 1
            """
        )
    
    try:
        while True:
            # Получить следующую фотографию
            photo = get_next_photo()
            
            if not photo:
                break
                
            # Запустить ingest
            run_photo_ingest(photo)
            
            # Запустить DINO
            run_dino(photo)
            
            # Запустить Qwen
            run_qwen(photo)
            
            # Запустить сортировку
            run_sort(photo)
            
            # Запустить preview
            run_preview(photo)
            
            # Проверить флаг остановки
            current = get_pipeline_mode()
            
            if current.stop_requested:
                break
                
        # Завершить выполнение
        with create_pool(POOL_CONFIG).connect() as conn:
            conn.execute("SET LOCAL statement_timeout = '30s'")
            conn.execute("SET LOCAL lock_timeout = '10s'")
            
            conn.execute(
                """
                UPDATE pipeline_control
                SET 
                    running = FALSE,
                    stop_requested = FALSE,
                    stopped_at = NOW()
                WHERE id = 1
                """
            )
    
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        # Восстановить состояние
        with create_pool(POOL_CONFIG).connect() as conn:
            conn.execute("SET LOCAL statement_timeout = '30s'")
            conn.execute("SET LOCAL lock_timeout = '10s'")
            
            conn.execute(
                """
                UPDATE pipeline_control
                SET 
                    running = FALSE,
                    stop_requested = FALSE,
                    stopped_at = NOW()
                WHERE id = 1
                """
            )
```

---

### ✅ Проверка

1. **Синтаксическая проверка**:
   ```bash
   uv run python -m py_compile app/pipeline/controller.py
   ```

2. **Тестирование логики**:
   - Проверьте, что `start_manual()` корректно запускает pipeline
   - Убедитесь, что `request_stop()` корректно устанавливает флаг остановки
   - Проверьте, что `reset_to_manual()` возвращает систему в исходное состояние

3. **Интеграция с UI**:
   - Добавьте кнопки "Запустить", "Остановить" с логикой из `modes.py`
   - Реализуйте tooltip'ы для отображения текущего режима

---

### 📌 Дальнейшие шаги

1. **Watcher режим**:
   - Реализуйте постоянный мониторинг директории
   - При обнаружении новых файлов запускайте `start_manual()`

2. **Автоматический режим**:
   - Добавьте задачу в scheduler (например, с помощью `apscheduler`)
   - При достижении `auto_time` запускайте `start_manual()`

3. **UI интеграция**:
   - Отображайте текущий режим из `pipeline_control`
   - Реализуйте кнопки с логикой из `modes.py`

4. **Мониторинг**:
   - Добавьте метрики для отслеживания производительности
   - Реализуйте логирование для отладки

Готово! Теперь у вас есть центральный контроллер для управления pipeline.