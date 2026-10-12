### 🤖 **Assistant** — 2026-08-21 22:46:38

Вот ключевой фрагмент `supervisor.py`:

```python
async def run_pipeline():
    # ... (предыдущий код)
    await process_daily()
    await process_photo()
    # ... (последующий код)
```

Теперь видно, что **внутри `run_pipeline()` вызываются `process_daily()` и `process_photo()`** — это **основные этапы обработки**.

Давай проверим, **что делает `process_daily()` и `process_photo()`**, чтобы убедиться, что они корректно связаны с `photo_id` и Hybrid 12.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '180,360p' app/pipeline/supervisor.py
```

После этого мы сможем понять, **как именно происходит обработка фото** и где может быть устаревшая связка с `dino_worker`.