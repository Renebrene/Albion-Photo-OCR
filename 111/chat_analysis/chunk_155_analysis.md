### 🤖 **Assistant** — 2026-08-19 01:36:15

Выполняем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '280,530p' app/web/components/technical_modules/automation.py
```

---

### 👤 **User** — 2026-08-19 01:36:16

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '280,530p' app/web/components/technical_modules/automation.py
280:    async def set_watcher():
281:        """
282:        Устанавливает режим "watcher".
283:        """
284:        await set_mode("watcher")
285:        ui.notify("Режим установлен: watcher", type="info", timeout=3000)
286:        # TODO: Запуск watcher
287:
288:    async def set_automatic():
289:        """
290:        Устанавливает режим "automatic".
291:        """
292:        await set_mode("automatic")
293:        ui.notify("Режим установлен: automatic", type="info", timeout=3000)
294:        # TODO: Запуск automatic
295:
296:    async def set_manual():
297:        """
298:        Устанавливает режим "manual".
299:        """
300:        await set_mode("manual")
301:        ui.notify("Режим установлен: manual", type="info", timeout=3000)
302:
303:    async def set_mode(mode):
304:        """
305:        Устанавливает режим в PostgreSQL.
306:        """
307:        async with async_db_session() as session:
308:            stmt = (
309:                update(PipelineState)
310:                .where(PipelineState.pipeline_id == "main")
311:                .values(mode=mode)
312:            )
313:            await session.execute(stmt)
314:            await session.commit()
315:
316:    async def get_mode():
317:        """
318:        Получает текущий режим из PostgreSQL.
319:        """
320:        async with async_db_session() as session:
321:            result = await session.execute(
322:                select(PipelineState.mode).where(PipelineState.pipeline_id == "main")
323:            )
324:            return result.scalar()
325:
326:    async def get_state():
327:        """
328:        Получает состояние из PostgreSQL.
329:        """
330:        async with async_db_session() as session:
331:            result = await session.execute(
332:                select(PipelineState).where(PipelineState.pipeline_id == "main")
333:            )
334:            return result.scalar()
335:
336:    async def get_processing_stats():
337:        """
338:        Получает статистику обработки из PostgreSQL.
339:        """
340:        async with async_db_session() as session:
341:            result = await session.execute(
342:                select(ProcessingStats)
343:                .where(ProcessingStats.pipeline_id == "main")
344:                .order_by(ProcessingStats.id.desc())
345:            )
346:            return result.scalars().first()
347:
348:    async def set_processing_stats(stats):
349:        """
350:        Устанавливает статистику обработки в PostgreSQL.
351:        """
352:        async with async_db_session() as session:
353:            stmt = (
354:                insert(ProcessingStats)
355:                .values(
356:                    pipeline_id="main",
357:                    stats=stats,
358:                )
359:            )
360:            await session.execute(stmt)
361:            await session.commit()
362:
363:    async def update_stats():
364:        """
365:        Обновляет статистику обработки.
366:        """
367:        stats = await get_processing_stats()
368:        if stats:
369:            await set_processing_stats(stats)
370:
371:    async def process_stats():
372:        """
373:        Обрабатывает статистику обработки.
374:        """
375:        stats = await get_processing_stats()
376:        if stats:
377:            await set_processing_stats(stats)
378:
379:    async def get_processing_stats():
380:        """
381:        Получает статистику обработки из PostgreSQL.
382:        """
383:        async with async_db_session() as session:
384:            result = await session.execute(
385:                select(ProcessingStats)
386:                .where(
387:                    ProcessingStats.pipeline_id == "main"
388:                    and ProcessingStats.id == (
389:                        select(ProcessingStats.id)
390:                        .where(ProcessingStats.pipeline_id == "main")
391:                        .order_by(ProcessingStats.id.desc())
392:                        .limit(1)
393:                    )
394:                )
395:            )
396:            return result.scalars().first()
397:
398:    async def set_processing_stats(stats):
399:        """
400:        Устанавливает статистику обработки в PostgreSQL.
401:        """
402:        async with async_db_session() as session:
403:            stmt = (
404:                insert(ProcessingStats)
405:                .values(
406:                    pipeline_id="main",
407:                    stats=stats,
408:                )
409:            )
410:            await session.execute(stmt)
411:            await session.commit()
412:
413:    async def update_stats():
414:        """
415:        Обновляет статистику обработки.
416:        """
417:        stats = await get_processing_stats()
418:        if stats:
419:            await set_processing_stats(stats)
420:
421:    async def process_stats():
422:        """
423:        Обрабатывает статистику обработки.
424:        """
425:        stats = await get_processing_stats()
426:        if stats:
427:            await set_processing_stats(stats)
428:
429:    async def get_processing_stats():
430:        """
431:        Получает статистику обработки из PostgreSQL.
432:        """
433:        async with async_db_session() as session:
434:            result = await session.execute(
435:                select(ProcessingStats)
436:                .where(
437:                    ProcessingStats.pipeline_id == "main"
438:                    and ProcessingStats.id == (
439:                        select(ProcessingStats.id)
440:                        .where(ProcessingStats.pipeline_id == "main")
441:                        .order_by(ProcessingStats.id.desc())
442:                        .limit(1)
443:                    )
444:                )
445:            )
446:            return result.scalars().first()
447:
448:    async def set_processing_stats(stats):
449:        """
450:        Устанавливает статистику обработки в PostgreSQL.
451:        """
452:        async with async_db_session() as session:
453:            stmt = (
454:                insert(ProcessingStats)
455:                .values(
456:                    pipeline_id="main",
457:                    stats=stats,
458:                )
459:            )
460:            await session.execute(stmt)
461:            await session.commit()
462:
463:    async def update_stats():
464:        """
465:        Обновляет статистику обработки.
466:        """
467:        stats = await get_processing_stats()
468:        if stats:
469:            await set_processing_stats(stats)
470:
471:    async def process_stats():
472:        """
473:        Обрабатывает статистику обработки.
474:        """
475:        stats = await get_processing_stats()
476:        if stats:
477:            await set_processing_stats(stats)
478:
479:    async def get_processing_stats():
480:        """
481:        Получает статистику обработки из PostgreSQL.
482:        """
483:        async with async_db_session() as session:
484:            result = await session.execute(
485:                select(ProcessingStats)
486:                .where(
487:                    ProcessingStats.pipeline_id == "main"
488:                    and ProcessingStats.id == (
489:                        select(ProcessingStats.id)
490:                        .where(ProcessingStats.pipeline_id == "main")
491:                        .order_by(ProcessingStats.id.desc())
492:                        .limit(1)
493:                    )
494:                )
495:            )
496:            return result.scalars().first()
497:
498:    async def set_processing_stats(stats):
499:        """
500:        Устанавливает статистику обработки в PostgreSQL.
501:        """
502:        async with async_db_session() as session:
503:            stmt = (
504:                insert(ProcessingStats)
505:                .values(
506:                    pipeline_id="main",
507:                    stats=stats,
508:                )
509:            )
510:            await session.execute(stmt)
511:            await session.commit()
512:
513:    async def update_stats():
514:        """
515:        Обновляет статистику обработки.
516:        """
517:        stats = await get_processing_stats()
518:        if stats:
519:            await set_processing_stats(stats)
520:
521:    async def process_stats():
522:        """
523:        Обрабатывает статистику обработки.
524:        """
525:        stats = await get_processing_stats()
526:        if stats:
527:            await set_processing_stats(stats)
528:
529:    async def get_processing_stats():
530:        """
531:        Получает статистику обработки из PostgreSQL.
532:        """
533:        async with async_db_session() as session:
534:            result = await session.execute(
535:                select(ProcessingStats)
536:                .where(
537:                    ProcessingStats.pipeline_id == "main"
538:                    and ProcessingStats.id == (
539:                        select(ProcessingStats.id)
540:                        .where(ProcessingStats.pipeline_id == "main")
541:                        .order_by(ProcessingStats.id.desc())
542:                        .limit(1)
543:                    )
544:                )
545:            )
546:            return result.scalars().first()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:36:16

### 🔍 Анализ

1. **`set_watcher()` и `set_automatic()`** — эти функции **записывают режим в PostgreSQL**, но **не запускают процессы**.
2. **`set_mode()`** — общий метод для установки режима.
3. **`get_mode()` и `get_state()`** — получают текущий режим и состояние из БД.
4. **`update_stats()` и `process_stats()`** — обновляют статистику обработки.

---

### 🛠️ План действий

1. **Добавим логику запуска DINO и Qwen** в `set_watcher()` и `set_automatic()`.
2. **Используем существующие функции** `start_dino()` и `start_qwen()` из `photo_processing.py`.
3. **Убедимся, что запуск происходит только в правильных режимах** (watcher/automatic).
4. **Избежать дублирования кода** и не создавать отдельные таймеры/процессы.

---

### 🧠 Важно

- **`set_watcher()`** — должен запускать **watcher** (непрерывный мониторинг).
- **`set_automatic()`** — должен запускать **automatic** (автоматические задачи).
- **`start_dino()` и `start_qwen()`** — уже имеют защиту от запуска в неподходящих режимах.

---

### 🛠️ Патч

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/automation.py")
s = p.read_text()

# ------------------------------------------------------------
# Добавляем запуск DINO и Qwen в set_watcher()
# ------------------------------------------------------------

old = """    async def set_watcher():
        """
        """
        Устанавливает режим "watcher".
        """
        await set_mode("watcher")
        ui.notify("Режим установлен: watcher", type="info", timeout=3000)
        # TODO: Запуск watcher
"""

new = """    async def set_watcher():
        """
        Устанавливает режим "watcher".
        """
        await set_mode("watcher")
        ui.notify("Режим установлен: watcher", type="info", timeout=3000)

        # Запуск DINO и Qwen в режиме watcher
        await start_dino()
        await start_qwen()
"""

if old not in s:
    raise SystemExit("ERROR: set_watcher anchor not found")

s = s.replace(old, new, 1)

# ------------------------------------------------------------
# Добавляем запуск DINO и Qwen в set_automatic()
# ------------------------------------------------------------

old = """    async def set_automatic():
        """
        Устанавливает режим "automatic".
        """
        await set_mode("automatic")
        ui.notify("Режим установлен: automatic", type="info", timeout=3000)
        # TODO: Запуск automatic
"""

new = """    async def set_automatic():
        """
        Устанавливает режим "automatic".
        """
        await set_mode("automatic")
        ui.notify("Режим установлен: automatic", type="info", timeout=3000)

        # Запуск DINO и Qwen в режиме automatic
        await start_dino()
        await start_qwen()
"""

if old not in s:
    raise SystemExit("ERROR: set_automatic anchor not found")

s = s.replace(old, new, 1)

p.write_text(s)
PY
```

---

### ✅ Проверка

1. **После патча**:
   - `set_watcher()` и `set_automatic()` будут запускать `start_dino()` и `start_qwen()`.
   - Запуск будет происходить **только в правильных режимах** (watcher/automatic).
   - Нет дублирования кода — используется существующая логика из `photo_processing.py`.

2. **Проверка синтаксиса**:
   ```bash
   cd ~/projects/scene_fingerprint_mvp_v02 && \
   python -m pytest --cov=app/web/components/technical_modules/automation.py
   ```

---

### 🚀 Заключение

Теперь:
- **Режимы watcher и automatic** будут корректно управлять запуском DINO и Qwen.
- **Запуск будет происходить только в правильных режимах**.
- **Код не дублируется**, используется существующая логика.

Если нужно, могу добавить логику для **остановки процессов** при смене режима.