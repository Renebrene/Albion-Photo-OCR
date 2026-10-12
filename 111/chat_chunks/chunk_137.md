## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 👤 **User** — 2026-08-18 23:03:47

физиической сортировки не будет

---

### 🤖 **Assistant** — 2026-08-18 23:03:48

Да. **Физической сортировки не будет.**

То есть исходные фотографии остаются **там, где они лежат в INPUT** — ничего не копируем, не перемещаем и не переименовываем.

Сортировка будет **виртуальной, на уровне БД/индекса и UI**:

- фото остаются в исходных каталогах;
- в БД храним путь/ссылку на оригинал;
- fingerprint/результат распознавания привязывается к записи фото;
- UI строит виртуальные группы: клиент → адрес → дата → результат → соседние фото и т. п.;
- чекбоксы и выбранный пользователь определяют, **что и как показывать в гриде**;
- соседние фотографии тоже участвуют в логике определения/сортировки, но физически никуда не перемещаются;
- в `OUTPUT` при необходимости можно хранить БД, JSON, хеши, превью и служебные данные, **но не копии всех исходных фото**.

То есть фактически делаем **файловое хранилище + виртуальный индекс поверх него**. Это как раз лучше подходит под ту архитектуру, которую мы сейчас собираем.

---

### 👤 **User** — 2026-08-18 23:03:57

продолжаем

---

### 🤖 **Assistant** — 2026-08-18 23:03:58

Да, продолжаем.

Тогда фиксируем текущую архитектуру как базовую:

**INPUT**
- оригинальные фото;
- физически ничего не меняем;
- новые фото можно добавлять в существующие каталоги.

**Индекс / БД**
- путь к оригиналу;
- имя файла;
- клиент;
- адрес;
- дата/месяц;
- fingerprint;
- результат распознавания;
- соседние фото и связанные результаты;
- технические признаки и хеши.

**OUTPUT**
- БД;
- JSON;
- fingerprint/слепки;
- превью;
- служебные индексы;
- отчёты.

**WEB UI**
- грид сразу показывает фотографии;
- настройки отображения берутся из текущего пользователя и его чекбоксов;
- фильтрация и группировка виртуальные;
- выбор клиента/адреса не требует физической перестройки файлов;
- сортировка — только логическая;
- соседние фотографии доступны алгоритму как дополнительный контекст.

И главное: **`INPUT → INDEX → WEB GRID`**, а не `INPUT → физическая сортировка → WEB GRID`.

Следующий логичный шаг — разобраться с текущим кодом и довести именно **виртуальный грид + индексацию + сортировку по соседним фото**, не ломая уже замороженное распознавание v33.

---

### 👤 **User** — 2026-08-18 23:04:21

да

---

### 🤖 **Assistant** — 2026-08-18 23:04:22

Тогда идём от текущего проекта и **не трогаем замороженный recognition v33**.

Первым делом я бы проверил, где сейчас реализованы три вещи:

1. **Откуда грид получает список фотографий.**
2. **Где формируется сортировка/группировка**, включая соседние фото.
3. **Как выбранный пользователь и чекбоксы влияют на отображение.**

У тебя в предыдущем поиске уже фигурировали важные места вроде `sort_status`, `source_path`, `dino_fingerprint`, `hybrid_final_id`, `output/daily`, `_v33`.

Давай сейчас не гадать по архитектуре. Выполни из корня проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
'grid|photo|photos|sort_status|source_path|dino_fingerprint|hybrid_final_id|selected_clients|checkbox|user' \
app scripts \
--include="*.py" | head -n 300
```

**Пришли весь вывод.**

По нему я сначала нарисую тебе фактическую цепочку:

`БД → выбор пользователя → чекбоксы → фильтры → виртуальная сортировка → соседние фото → GRID`

и уже после этого будем менять код.

---

### 👤 **User** — 2026-08-18 23:04:49

сортировка у меня вместе с дино - запускается командой из тех окна

---

### 🤖 **Assistant** — 2026-08-18 23:04:50

Да, тогда важное уточнение: **сортировка не является частью WEB UI**.

У нас получается два отдельных контура:

### 1. Обработка / DINO / виртуальная сортировка

Запускается **командой из терминального окна**.

Там происходит:

`INPUT → DINO → fingerprint → кандидаты → анализ соседних фото → итоговый результат сортировки`

Но при этом **никаких физических перемещений файлов** больше не делаем.

Результат работы сортировки сохраняется как данные:

- какой файл;
- его `source_path`;
- какой адрес/клиент определён;
- fingerprint;
- итоговый ID;
- соседние фото;
- уверенность/статусы;
- прочие результаты алгоритма.

### 2. WEB UI

WEB уже **не сортирует фотографии заново**.

Он читает результаты обработки и строит поверх них виртуальное представление:

```text
INPUT
  │
  ├── photo_001.jpg
  ├── photo_002.jpg
  ├── photo_003.jpg
  └── ...
       │
       ▼
  DINO + SORT
       │
       ▼
   БАЗА / JSON
       │
       ▼
    WEB GRID
       │
       ├── клиент
       ├── адрес
       ├── дата
       ├── группы
       ├── соседние фото
       └── фильтры пользователя
```

И это даже лучше: **тяжёлая логика остаётся в отдельном процессе**, а WEB работает как быстрый просмотрщик/интерфейс над результатами.

Поэтому сейчас я бы **вообще не трогал команду DINO/sort**. Сначала надо посмотреть, **какой именно результат она уже оставляет после работы**, и от него построить GRID.

Если хочешь продолжить именно с этого места — пришли команду, которой ты сейчас запускаешь DINO+сортировку из терминала, или последний скрипт/команду, которую мы зафиксировали.

---

### 👤 **User** — 2026-08-18 23:05:07

смотрим

---

### 🤖 **Assistant** — 2026-08-18 23:05:08

> **Remembering**
>
>
> ****
>
> 
>
> **Recalled and preserved scene fingerprinting and recognition workflow**
>
> 
>
> Worked for 10s

Да, смотрим именно существующую цепочку, а не придумываем новую.

У нас зафиксировано, что слой сортировки - `scripts/sort_test_and_report_v2.py`, а результаты складываются в `data/output/test_sorted_v2/`. При этом распознавание остаётся на базе **v33**, с TOP-1 как основным решением и дополнительной логикой sub-fingerprint / sequence / соседей.

Давай прямо сейчас посмотрим, **что реально запускается из терминала и куда идут результаты**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
'sort_test_and_report|test_sorted_v2|scene-fingerprint recognize|neighbor|sequence|subfingerprint|hybrid' \
scripts app \
--include="*.py" --include="*.sh" | head -n 300
```

И отдельно:

```bash
ls -lah data/output/test_sorted_v2 2>/dev/null
```

Пришли вывод обоих команд. По нему восстановим **фактическую текущую схему DINO → сортировка → соседние фото → результат**, не затрагивая физические файлы и замороженный v33.

---

### 👤 **User** — 2026-08-18 23:05:44

смотрим технический раздел веб интерфейса окно запустить обработку

---

### 🤖 **Assistant** — 2026-08-18 23:05:44

Да. Тогда сейчас смотрим **технический раздел WEB → окно «Запустить обработку»**.

Нам нужно понять только его текущую реализацию:

- какие поля/настройки там отображаются;
- какую команду он формирует;
- какой скрипт запускает;
- куда передаёт `INPUT`;
- где получает результат;
- что сейчас отображается пользователю во время обработки;
- и что из этого нужно оставить/изменить с учётом **виртуальной сортировки**.

Сделаем поиск именно по этому окну, без захода пока в алгоритм DINO.

В корне проекта выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
'Запустить обработку|запустить обработку|обработка|processing|run.*process|process.*run' \
app \
--include="*.py" | head -n 300
```

И ещё:

```bash
grep -RniE \
'ui\.button|ui\.select|ui\.checkbox|ui\.input|subprocess|Popen|create_subprocess|scene-fingerprint|sort_test' \
app \
--include="*.py" | head -n 400
```

**Пришли оба вывода.**

После этого разберём конкретно окно **«Запустить обработку»** и будем менять только WEB-обвязку, не трогая рабочий DINO/sort.

---

### 👤 **User** — 2026-08-18 23:06:19

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
'Запустить обработку|запустить обработку|обработка|processing|run.*process|process.*run' \
app \
--include="*.py" | head -n 300
app/web/components/technical_modules/photo_processing.py:12:def build_photo_processing():
app/web/components/technical_modules/photo_processing.py:298:                    "✓ Полная обработка завершена: "
app/web/components/technical_modules/photo_processing.py:390:            "▶  ЗАПУСТИТЬ ОБРАБОТКУ",
app/web/components/technical_modules/last_run.py:6:        ui.label("ПОСЛЕДНЯЯ ОБРАБОТКА").classes(
app/web/components/technical_modules/automation.py:13:            "Автоматическая обработка",
app/web/components/technical.py:3:from app.web.components.technical_modules.photo_processing import (
app/web/components/technical.py:4:    build_photo_processing,
app/web/components/technical.py:104:def show_technical(initial_tab="photo_processing"):
app/web/components/technical.py:157:                    "photo_processing",
app/web/components/technical.py:158:                    label="Обработка фото",
app/web/components/technical.py:216:                    value="photo_processing",
app/web/components/technical.py:221:                    with ui.tab_panel("photo_processing"):
app/web/components/technical.py:222:                        build_photo_processing()
app/web/system/monitor.py:27:        result = subprocess.run(
app/core/recognizer.py:495:        Intended for queue/worker processing.
app/core/fingerprint.py:271:        # One image load per worker + parallel processing.
app/pipeline/worker.py:79:        print("[Worker] Starting batch processing")
app/pipeline/queue.py:14:        PROCESSING
app/pipeline/queue.py:183:                    status = 'PROCESSING',
app/pipeline/queue.py:212:        Mark a processing job as DONE.
app/pipeline/queue.py:227:                    AND status = 'PROCESSING'
app/pipeline/queue.py:242:        Mark a processing job as FAILED.
app/pipeline/queue.py:257:                    AND status = 'PROCESSING'
app/workers/dino_worker.py:55:                dino_status = 'processing',
app/cli.py:505:                    "PROCESSING",
app/ocr/grid_ocr.py:4:import multiprocessing as mp
app/ocr/grid_ocr.py:344:    # multiprocessing
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -RniE \
'ui\.button|ui\.select|ui\.checkbox|ui\.input|subprocess|Popen|create_subprocess|scene-fingerprint|sort_test' \
app \
--include="*.py" | head -n 400
app/web/components/photos_before_cache_20260816_145128.py:90:                ui.button(
app/web/components/photos_before_cache_20260816_145128.py:135:            ui.button(
app/web/components/photos_before_cache_20260816_145128.py:146:            ui.button(
app/web/components/photos_before_cache_20260816_145128.py:159:            ui.button(
app/web/components/photos_before_cache_20260816_145128.py:204:                ui.button(
app/web/components/photos_before_cache_20260816_145128.py:210:                ui.button(
app/web/components/photos_before_cache_20260816_145128.py:220:                ui.button(
app/web/components/photos_before_cache_20260816_145128.py:226:                ui.button(
app/web/components/photos_before_cache_20260816_145128.py:335:                                ui.checkbox(
app/web/components/search.py:174:        search = ui.input(
app/web/components/search.py:190:        ui.button(
app/web/components/search.py:200:        ui.button(
app/web/components/filters.py:14:            ui.select(
app/web/components/filters.py:19:            ui.button(
app/web/components/filters.py:27:            ui.button(
app/web/components/filters.py:31:            ui.button(
app/web/components/filters.py:39:            ui.button(
app/web/components/filters.py:43:            ui.button(
app/web/components/filters.py:49:            ui.button(
app/web/components/technical_modules/photo_processing.py:14:    source_input = ui.input(
app/web/components/technical_modules/photo_processing.py:21:    output_input = ui.input(
app/web/components/technical_modules/photo_processing.py:99:            process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:104:                stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/photo_processing.py:105:                stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/photo_processing.py:240:                qwen_process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:248:                    stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/photo_processing.py:249:                    stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/photo_processing.py:357:            ui.button(
app/web/components/technical_modules/photo_processing.py:374:            ui.button(
app/web/components/technical_modules/photo_processing.py:389:        run_button = ui.button(
app/web/components/technical_modules/fingerprints.py:24:        ui.button(
app/web/components/technical_modules/data.py:440:            ui.button(
app/web/components/technical_modules/data.py:445:            ui.button(
app/web/components/technical_modules/data.py:450:            ui.button(
app/web/components/technical_modules/last_run.py:17:            ui.button(
app/web/components/technical_modules/last_run.py:22:            ui.button(
app/web/components/technical_modules/users.py:76:                ui.checkbox(
app/web/components/technical_modules/users.py:85:                ui.button(
app/web/components/technical_modules/users.py:146:                    name_input = ui.input(
app/web/components/technical_modules/users.py:168:                            ui.button(
app/web/components/technical_modules/users.py:237:                        ui.button(
app/web/components/technical_modules/users.py:244:                        ui.button(
app/web/components/technical_modules/users.py:275:                    name_input = ui.input(
app/web/components/technical_modules/users.py:319:                        ui.button(
app/web/components/technical_modules/users.py:326:                        ui.button(
app/web/components/technical_modules/users.py:376:                        ui.button(
app/web/components/technical_modules/users.py:392:                        ui.button(
app/web/components/technical_modules/users.py:479:                        ui.button(
app/web/components/technical_modules/users.py:539:                                    ui.button(
app/web/components/technical_modules/users.py:614:                                ui.button(
app/web/components/technical_modules/users.py:629:                                ui.button(
app/web/components/technical_modules/automation.py:12:        ui.checkbox(
app/web/components/technical_modules/automation.py:20:            ui.select(
app/web/components/technical_modules/qwen.py:268:            run_button = ui.button(
app/web/components/technical_modules/qwen.py:274:            stop_button = ui.button(
app/web/components/technical_modules/qwen.py:282:            refresh_button = ui.button(
app/web/components/technical_modules/qwen.py:440:            process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/qwen.py:453:                stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/qwen.py:454:                stderr=asyncio.subprocess.STDOUT,
app/web/components/addresses.py:90:            ui.button(
app/web/components/addresses.py:97:            ui.button(
app/web/components/addresses.py:143:                checkbox = ui.checkbox(
app/web/components/collections.py:16:        name = ui.input(
app/web/components/collections.py:24:        kind = ui.select(
app/web/components/collections.py:34:        client = ui.select(
app/web/components/collections.py:53:            ui.button(
app/web/components/collections.py:85:            ui.button(
app/web/components/collections.py:107:        ui.button(
app/web/components/collections.py:129:                    ui.checkbox().props("dense")
app/web/components/collections.py:151:                    ui.checkbox().props("dense")
app/web/components/header.py:81:        user_button = ui.button(
app/web/components/header.py:187:                                ui.button(
app/web/components/header.py:208:                    ui.button(
app/web/components/header.py:226:        ui.button(
app/web/components/photos.py:453:                    ui.button(
app/web/components/photos.py:594:                ui.button(
app/web/components/photos.py:603:            ui.button(
app/web/components/photos.py:614:            ui.button(
app/web/components/photos.py:627:            ui.button(
app/web/components/photos.py:704:                ui.button(
app/web/components/photos.py:710:                ui.button(
app/web/components/photos.py:720:                ui.button(
app/web/components/photos.py:726:                ui.button(
app/web/components/photos.py:917:            ui.button(
app/web/components/photos.py:925:            ui.button(
app/web/components/photos.py:937:            ui.button(
app/web/components/photos.py:945:            ui.button(
app/web/components/photos.py:953:            ui.button(
app/web/components/photos.py:960:            ui.button(
app/web/components/photos.py:979:            show_grid_button = ui.button(
app/web/components/photos.py:1184:                                    checkbox = ui.checkbox(
app/web/components/technical.py:139:                ui.button(
app/web/components/clients.py:146:                ui.button(
app/web/components/clients.py:154:                ui.button(
app/web/components/clients.py:174:                checkbox = ui.checkbox(
app/web/frontend_v02.py:228:            manager_select = ui.select(
app/web/frontend_v02.py:251:    search = ui.input(
app/web/frontend_v02.py:260:    ui.button(
app/web/frontend_v02.py:266:    ui.button(
app/web/frontend_v02.py:308:                ui.checkbox().props(
app/web/frontend_v02.py:316:                button = ui.button(
app/web/frontend_v02.py:337:        ui.button(
app/web/frontend_v02.py:347:        ui.button(
app/web/frontend_v02.py:388:            ui.button(
app/web/frontend_v02.py:394:            ui.button(
app/web/frontend_v02.py:408:            ui.button(
app/web/frontend_v02.py:414:            ui.button(
app/web/frontend_v02.py:475:        ui.button(
app/web/frontend_v02.py:513:                                ui.checkbox().props(
app/web/frontend_v02.py:531:            ui.button(
app/web/frontend_v02.py:540:            ui.button(
app/web/frontend_v02.py:546:            ui.button(
app/web/frontend_v02.py:568:        ui.select(
app/web/frontend_v02.py:585:        ui.button(
app/web/frontend_v02.py:601:        ui.select(
app/web/filters.py:16:        ui.select(
app/web/filters.py:37:        ui.select(
app/web/frontend_v01_backup_before_modular.py:234:    search_input = ui.input(
app/web/frontend_v01_backup_before_modular.py:247:    ui.button(
app/web/frontend_v01_backup_before_modular.py:254:    ui.button(
app/web/frontend_v01_backup_before_modular.py:291:                ui.checkbox().props(
app/web/frontend_v01_backup_before_modular.py:316:        ui.button(
app/web/frontend_v01_backup_before_modular.py:326:        ui.button(
app/web/frontend_v01_backup_before_modular.py:369:                ui.button(
app/web/frontend_v01_backup_before_modular.py:375:                ui.button(
app/web/frontend_v01_backup_before_modular.py:385:                ui.button(
app/web/frontend_v01_backup_before_modular.py:391:                ui.button(
app/web/frontend_v01_backup_before_modular.py:464:                ui.checkbox().props(
app/web/frontend_v01_backup_before_modular.py:482:            ui.button(
app/web/frontend_v01_backup_before_modular.py:492:            ui.button(
app/web/frontend_v01_backup_before_modular.py:516:        ui.select(
app/web/frontend_v01_backup_before_modular.py:533:        ui.button(
app/web/frontend_v01_backup_before_modular.py:551:        ui.select(
app/web/frontend_v01_backup_before_modular.py:584:        ui.button(
app/web/frontend_v01_backup_before_modular.py:591:        ui.button(
app/web/frontend_v01.py:234:    search_input = ui.input(
app/web/frontend_v01.py:247:    ui.button(
app/web/frontend_v01.py:254:    ui.button(
app/web/frontend_v01.py:291:                ui.checkbox().props(
app/web/frontend_v01.py:316:        ui.button(
app/web/frontend_v01.py:326:        ui.button(
app/web/frontend_v01.py:369:                ui.button(
app/web/frontend_v01.py:375:                ui.button(
app/web/frontend_v01.py:385:                ui.button(
app/web/frontend_v01.py:391:                ui.button(
app/web/frontend_v01.py:464:                ui.checkbox().props(
app/web/frontend_v01.py:482:            ui.button(
app/web/frontend_v01.py:492:            ui.button(
app/web/frontend_v01.py:516:        ui.select(
app/web/frontend_v01.py:533:        ui.button(
app/web/frontend_v01.py:551:        ui.select(
app/web/frontend_v01.py:584:        ui.button(
app/web/frontend_v01.py:591:        ui.button(
app/web/system/monitor.py:3:import subprocess
app/web/system/monitor.py:27:        result = subprocess.run(
app/main.py:25:            fp_id = ui.input("ID локации / конструкции", placeholder="78").classes("w-96")
app/main.py:26:            folder = ui.input("Папка эталонных фотографий", value="data/input/78").classes("w-full")
app/main.py:36:            ui.button("СОЗДАТЬ СЛЕПОК", on_click=create)
app/main.py:40:            folder2 = ui.input("Папка", value="data/input/new").classes("w-full")
app/main.py:64:            ui.button("РАСПОЗНАТЬ", on_click=run_recognition)
app/main.py:82:            ui.button("Обновить", on_click=refresh)
app/web_v01_backup_20260816_142053/components/search.py:7:        search = ui.input(
app/web_v01_backup_20260816_142053/components/search.py:13:        ui.button(
app/web_v01_backup_20260816_142053/components/search.py:18:        ui.button(
app/web_v01_backup_20260816_142053/components/filters.py:14:            ui.select(
app/web_v01_backup_20260816_142053/components/filters.py:19:            ui.button(
app/web_v01_backup_20260816_142053/components/filters.py:27:            ui.button(
app/web_v01_backup_20260816_142053/components/filters.py:31:            ui.button(
app/web_v01_backup_20260816_142053/components/filters.py:39:            ui.button(
app/web_v01_backup_20260816_142053/components/filters.py:43:            ui.button(
app/web_v01_backup_20260816_142053/components/filters.py:49:            ui.button(
app/web_v01_backup_20260816_142053/components/addresses.py:39:            ui.button(
app/web_v01_backup_20260816_142053/components/addresses.py:49:                ui.checkbox().props("dense")
app/web_v01_backup_20260816_142053/components/collections.py:25:                ui.checkbox().props("dense")
app/web_v01_backup_20260816_142053/components/collections.py:43:                ui.checkbox().props("dense")
app/web_v01_backup_20260816_142053/components/collections.py:46:    ui.button(
app/web_v01_backup_20260816_142053/components/header.py:35:            ui.select(
app/web_v01_backup_20260816_142053/components/header.py:41:            ui.button(
app/web_v01_backup_20260816_142053/components/technical.py:21:                ui.button(
app/web_v01_backup_20260816_142053/components/technical.py:42:                ui.button(
app/web_v01_backup_20260816_142053/components/technical.py:47:                ui.button(
app/web_v01_backup_20260816_142053/components/technical.py:67:            ui.input(
app/web_v01_backup_20260816_142053/components/technical.py:82:            ui.select(
app/web_v01_backup_20260816_142053/components/clients.py:34:                ui.checkbox().props("dense")
app/web_v01_backup_20260816_142053/frontend_v02.py:228:            manager_select = ui.select(
app/web_v01_backup_20260816_142053/frontend_v02.py:251:    search = ui.input(
app/web_v01_backup_20260816_142053/frontend_v02.py:260:    ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:266:    ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:308:                ui.checkbox().props(
app/web_v01_backup_20260816_142053/frontend_v02.py:316:                button = ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:337:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:347:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:388:            ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:394:            ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:408:            ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:414:            ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:475:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:513:                                ui.checkbox().props(
app/web_v01_backup_20260816_142053/frontend_v02.py:531:            ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:540:            ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:546:            ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:568:        ui.select(
app/web_v01_backup_20260816_142053/frontend_v02.py:585:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v02.py:601:        ui.select(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:234:    search_input = ui.input(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:247:    ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:254:    ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:291:                ui.checkbox().props(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:316:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:326:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:369:                ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:375:                ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:385:                ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:391:                ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:464:                ui.checkbox().props(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:482:            ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:492:            ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:516:        ui.select(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:533:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:551:        ui.select(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:584:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:591:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:234:    search_input = ui.input(
app/web_v01_backup_20260816_142053/frontend_v01.py:247:    ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:254:    ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:291:                ui.checkbox().props(
app/web_v01_backup_20260816_142053/frontend_v01.py:316:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:326:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:369:                ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:375:                ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:385:                ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:391:                ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:464:                ui.checkbox().props(
app/web_v01_backup_20260816_142053/frontend_v01.py:482:            ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:492:            ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:516:        ui.select(
app/web_v01_backup_20260816_142053/frontend_v01.py:533:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:551:        ui.select(
app/web_v01_backup_20260816_142053/frontend_v01.py:584:        ui.button(
app/web_v01_backup_20260816_142053/frontend_v01.py:591:        ui.button(
app/cli.py:18:        prog="scene-fingerprint",

---

### 🤖 **Assistant** — 2026-08-18 23:06:20

Вот, нашли нужное место. **Окно «Запустить обработку» полностью находится в:**

```text
app/web/components/technical_modules/photo_processing.py
```

Причём там уже есть всё необходимое для нашего разбора:

```text
строка 14  → source_input
строка 21  → output_input
строка 99  → запуск внешнего процесса
строка 240 → отдельный запуск Qwen
строка 357  → элементы управления
строка 389  → ▶ ЗАПУСТИТЬ ОБРАБОТКУ
```

То есть сейчас **не надо искать дальше по всему проекту**.

### Следующий шаг

Нам нужно посмотреть сам файл целиком или ключевые участки. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,180p' app/web/components/technical_modules/photo_processing.py
```

потом:

```bash
sed -n '180,330p' app/web/components/technical_modules/photo_processing.py
```

и:

```bash
sed -n '330,430p' app/web/components/technical_modules/photo_processing.py
```

Пришли вывод.

Я хочу сначала **восстановить существующее окно без изменений**:

```text
SOURCE
OUTPUT
настройки
↓
ЗАПУСТИТЬ ОБРАБОТКУ
↓
какой процесс запускается
↓
куда пишет результат
↓
что WEB показывает
```

И уже потом решим, **что именно в этом окне должно остаться**, учитывая наше новое правило: **фото физически не сортируются, а только индексируются и виртуально группируются**.

---

### 👤 **User** — 2026-08-18 23:07:06

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,180p' app/web/components/technical_modules/photo_processing.py
import asyncio
import re
from pathlib import Path

from nicegui import ui

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"
DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"

def build_photo_processing():

    source_input = ui.input(
        label="Источник фотографий",
        value=str(PROJECT / "data/input/daily"),
    ).props(
        "outlined dense"
    ).classes("flex-1")

    output_input = ui.input(
        label="Результат",
        value=str(PROJECT / "data/output/daily"),
    ).props(
        "outlined dense"
    ).classes("flex-1")

    status_label = ui.label(
        "Готов к запуску"
    ).classes(
        "text-sm text-grey-6"
    )

    run_button = None

    async def run_pipeline():

        input_dir = Path(
            source_input.value
        ).expanduser()

        if not input_dir.is_absolute():
            input_dir = PROJECT / input_dir

        if not input_dir.exists():
            ui.notify(
                f"Папка не найдена: {input_dir}",
                type="negative",
            )
            return

        images = [
            p for p in input_dir.iterdir()
            if p.is_file()
            and p.suffix.lower() in {
                ".jpg",
                ".jpeg",
                ".png",
            }
        ]

        if not images:
            ui.notify(
                "В папке нет фотографий",
                type="negative",
            )
            return

        if not DAILY_SCRIPT.exists():
            ui.notify(
                f"Не найден скрипт: {DAILY_SCRIPT}",
                type="negative",
            )
            return

        run_button.disable()

        status_label.text = (
            f"Запуск Hybrid v12... "
            f"Фотографий: {len(images)}"
        )

        try:

            env = {
                "PATH": (
                    f"{Path.home() / '.local/bin'}:"
                    "/usr/local/sbin:"
                    "/usr/local/bin:"
                    "/usr/sbin:"
                    "/usr/bin:"
                    "/sbin:"
                    "/bin"
                ),
                "HOME": str(Path.home()),
                "PYTHONUNBUFFERED": "1",
            }

            process = await asyncio.create_subprocess_exec(
                "bash",
                str(DAILY_SCRIPT),
                cwd=str(PROJECT),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            output_lines = []

            while True:

                line = await process.stdout.readline()

                if not line:
                    break

                text = line.decode(
                    "utf-8",
                    errors="replace",
                ).rstrip()

                output_lines.append(text)

                if text:
                    status_label.text = text[-180:]

            returncode = await process.wait()

            output = "\n".join(output_lines)

            if returncode != 0:

                status_label.text = (
                    f"✗ Hybrid v12: ошибка ({returncode})"
                )

                ui.notify(
                    "Распознавание завершилось ошибкой",
                    type="negative",
                    timeout=8000,
                )

                return

            match = re.search(
                r"Output\s*:\s*(.+)",
                output,
            )

            if match:

                result_dir = Path(
                    match.group(1).strip()
                )

            else:

                result_dir = None

            if not result_dir or not result_dir.exists():

                status_label.text = (
                    "⚠ Hybrid завершён, "
                    "папка результата не найдена"
                )

                ui.notify(
                    "Hybrid завершён, "
                    "но папка результата не определена.",
                    type="warning",
                    timeout=8000,
                )

                return

            output_input.value = str(
                result_dir
            )

            status_label.text = (
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '180,330p' app/web/components/technical_modules/photo_processing.py
            status_label.text = (
                "✓ Hybrid v12: сортировка завершена"
            )

            ui.notify(
                f"Сортировка завершена: {result_dir}",
                type="positive",
                timeout=5000,
            )

            # ====================================================
            # QWEN3-VL 4B
            # ====================================================

            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"

            if not qwen_script.exists():

                status_label.text = (
                    "✓ Hybrid завершён → Qwen script не найден"
                )

                ui.notify(
                    f"Не найден Qwen script: {qwen_script}",
                    type="warning",
                    timeout=8000,
                )

                return

            # Имя папки Hybrid запуска:
            # 20260816_230042
            run_name = result_dir.name

            qwen_output = (
                PROJECT
                / "data"
                / "metadata"
                / "qwen4b"
                / run_name
            )

            qwen_output.mkdir(
                parents=True,
                exist_ok=True,
            )

            status_label.text = (
                "▶ Qwen3-VL 4B: выполняется..."
            )

            ui.notify(
                "▶ Сортировка завершена. "
                "Запускается Qwen3-VL 4B.",
                type="info",
                timeout=5000,
            )

            try:

                qwen_process = await asyncio.create_subprocess_exec(
                    str(PROJECT / ".venv" / "bin" / "python"),
                    str(qwen_script),
                    "--input",
                    str(result_dir),
                    "--output",
                    str(qwen_output),
                    cwd=str(PROJECT),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )

                qwen_lines = []

                while True:

                    line = await qwen_process.stdout.readline()

                    if not line:
                        break

                    text = line.decode(
                        "utf-8",
                        errors="replace",
                    ).rstrip()

                    qwen_lines.append(text)

                    if status_label:
                        status_label.text = text[-160:]

                qwen_returncode = await qwen_process.wait()

                if qwen_returncode != 0:

                    status_label.text = (
                        "✗ Hybrid v12: ✓  "
                        "Qwen3-VL 4B: ошибка"
                    )

                    ui.notify(
                        "Hybrid завершён успешно, "
                        "но Qwen3-VL 4B завершился с ошибкой.",
                        type="negative",
                        timeout=10000,
                    )

                    return

                status_label.text = (
                    "✓ Hybrid v12 + Qwen3-VL 4B: готово"
                )

                output_input.value = str(
                    result_dir
                )

                ui.notify(
                    "✓ Полная обработка завершена: "
                    "Hybrid v12 + Qwen3-VL 4B.",
                    type="positive",
                    timeout=8000,
                )

            except Exception as qwen_error:

                status_label.text = (
                    "✗ Hybrid: ✓  "
                    "Qwen3-VL 4B: ошибка запуска"
                )

                ui.notify(
                    f"Ошибка запуска Qwen: {qwen_error}",
                    type="negative",
                    timeout=10000,
                )

        except Exception as e:

            status_label.text = (
                "✗ Ошибка запуска"
            )

            ui.notify(
                f"Ошибка запуска: {e}",
                type="negative",
                timeout=8000,
            )

        finally:

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:07:08

Вот теперь видно реальное устройство окна. И здесь есть **важный момент**, который надо исправить концептуально.

### Что сейчас делает окно

Сейчас цепочка такая:

```text
Источник фотографий
        ↓
run_daily_hybrid_v12.sh
        ↓
Hybrid v12
        ↓
ПАПКА РЕЗУЛЬТАТА
        ↓
qwen4b_output_v01.py
        ↓
Qwen3-VL 4B
```

Причём WEB прямо сообщает:

> `✓ Hybrid v12: сортировка завершена`

и затем:

> `▶ Qwen3-VL 4B: выполняется...`

То есть текущий WEB действительно рассчитан на **старую модель: обработка → физически отсортированный output → Qwen работает по output**.

А мы теперь договорились о другой архитектуре:

```text
INPUT
  ↓
DINO / Hybrid
  ↓
РЕЗУЛЬТАТЫ / МЕТАДАННЫЕ
  ↓
БД / индекс
  ↓
WEB GRID
```

**Без физической сортировки исходных фотографий.**

---

### Ещё один интересный момент

`output_input` сейчас фактически является отображением результата Hybrid:

```python
output_input.value = str(result_dir)
```

То есть поле **«Результат»** сейчас означает:

> «папка, куда Hybrid физически положил результат».

В новой архитектуре это уже не совсем правильное понятие.

Логичнее будет:

**Источник фотографий**

```text
/data/input/daily
```

**Результаты обработки**

```text
/data/output/daily/20260818_....
```

где лежат:

- JSON;
- БД/индекс;
- fingerprint;
- хеши;
- превью;
- результаты распознавания;
- служебные файлы.

А **сами исходные фотографии остаются в INPUT**.

---

### И ещё важнее — Qwen

Сейчас Qwen запускается вот так:

```python
qwen_script
    --input result_dir
    --output qwen_output
```

То есть Qwen получает **результат Hybrid**, а не исходный INPUT.

Если мы теперь делаем виртуальную сортировку, надо отдельно решить, **зачем Qwen вообще запускается после DINO**.

И это особенно важно, потому что раньше мы зафиксировали:

> **распознавание адресов — без LLM.**

Поэтому я бы пока **не менял Qwen**, а сначала посмотрел сам `run_daily_hybrid_v12.sh`.

### Следующий шаг

Покажи его:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat scripts/run_daily_hybrid_v12.sh
```

И одновременно:

```bash
sed -n '330,430p' app/web/components/technical_modules/photo_processing.py
```

Тогда мы увидим:

1. **что именно делает Hybrid v12;**
2. действительно ли он сейчас физически копирует/раскладывает фото;
3. какие JSON/метаданные уже создаёт;
4. что именно WEB ждёт от его `Output`;
5. и где лучше всего заменить физическую сортировку на **виртуальный результат**, не ломая рабочий алгоритм DINO.

---

### 👤 **User** — 2026-08-18 23:07:19

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '330,430p' app/web/components/technical_modules/photo_processing.py

            run_button.enable()

    # ============================================================
    # UI
    # ============================================================

    with ui.card().classes("w-full"):

        ui.label(
            "ФОТООТЧЁТ"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        ui.label(
            "Источник фотографий"
        )

        with ui.row().classes(
            "w-full items-center gap-2"
        ):

            source_input

            ui.button(
                "Выбрать",
                icon="folder_open",
            ).props(
                "flat dense"
            )

        ui.label(
            "Результат"
        )

        with ui.row().classes(
            "w-full items-center gap-2"
        ):

            output_input

            ui.button(
                "Выбрать",
                icon="folder_open",
            ).props(
                "flat dense"
            )

        ui.separator().classes("my-2")

        ui.label(
            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
        ).classes(
            "text-sm"
        )

        run_button = ui.button(
            "▶  ЗАПУСТИТЬ ОБРАБОТКУ",
            on_click=run_pipeline,
        ).props(
            "unelevated"
        ).classes(
            "w-full text-lg font-bold"
        )

        status_label

        ui.label(
            "Главная рабочая операция"
        ).classes(
            "text-xs text-grey-6"
        )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:07:20

Да, теперь окно видно целиком. И я бы **пока ничего не переписывал** — сначала посмотрим, что реально делает `Hybrid v12`.

Сейчас UI честно отражает старую цепочку:

```text
ФОТООТЧЁТ

Источник фотографий   [ ... ] [Выбрать]
Результат             [ ... ] [Выбрать]

DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B

[ ▶ ЗАПУСТИТЬ ОБРАБОТКУ ]

статус
```

Но после нашего решения я бы в итоге привёл её к:

```text
ФОТООБРАБОТКА

Источник фотографий   [ INPUT ] [Выбрать]
Результаты             [ OUTPUT ] [Выбрать]

DINO v33 → Hybrid v12 → индексирование → Qwen3-VL 4B

[ ▶ ЗАПУСТИТЬ ОБРАБОТКУ ]

статус
```

При этом **`Qwen3-VL 4B` пока вообще не убираем**. Сначала выясняем его нынешнюю роль.

### Сейчас самое важное

Нам нужен `run_daily_hybrid_v12.sh`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat scripts/run_daily_hybrid_v12.sh
```

И ещё сразу покажи, какие файлы он вызывает:

```bash
grep -nE \
'python|uv run|cp |mv |mkdir|Output|output|sort|recogn|fingerprint' \
scripts/run_daily_hybrid_v12.sh
```

После этого уже будет видно, **где именно происходит физическая сортировка**.

И вот там мы будем принимать решение: что оставить как есть, а что превратить в виртуальный индекс.

---

### 👤 **User** — 2026-08-18 23:08:02

В одну строку, причем источник можно выбирать, а результаты нет Источник фотографий   [ INPUT ] [Выбрать]  Результаты             [ OUTPUT ] [Выбрать]

---

### 🤖 **Assistant** — 2026-08-18 23:08:02

Да, именно так. **В одну строку.**

Я бы сделал:

```text
Источник фотографий [________________________] [Выбрать]    Результаты [________________________]
```

То есть:

- **Источник фотографий** — поле + кнопка **«Выбрать»**;
- **Результаты** — только поле, **без кнопки «Выбрать»**;
- оба элемента находятся **в одной горизонтальной строке**;
- `Результаты` — автоматически заданный каталог `data/output/daily`, пользователь его не выбирает.

И дальше под этой строкой:

```text
DINO v33 → Hybrid v12 → обработка → Qwen3-VL 4B

[ ▶ ЗАПУСТИТЬ ОБРАБОТКУ ]
```

При этом слово **«сортировка»** из интерфейса убираем, поскольку физической сортировки больше нет.

---

### 👤 **User** — 2026-08-18 23:08:24

int_mvp_v02

cat scripts/run_daily_hybrid_v12.sh
#!/usr/bin/env bash

set -euo pipefail

PROJECT="$HOME/projects/scene_fingerprint_mvp_v02"

INPUT="$PROJECT/data/input/daily"

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"

OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"

echo
echo "================================================================================"
echo "SCENE FINGERPRINT — DAILY HYBRID V12"
echo "================================================================================"
echo
echo "INPUT : $INPUT"
echo "OUTPUT: $OUTPUT"
echo

if [ ! -d "$INPUT" ]; then
    echo "ERROR: input directory does not exist:"
    echo "$INPUT"
    exit 1
fi

COUNT=$(find "$INPUT" -maxdepth 1 -type f \
    $ -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" $ \
    | wc -l)

echo "Images: $COUNT"
echo

if [ "$COUNT" -eq 0 ]; then
    echo "ERROR: no images found in $INPUT"
    exit 1
fi

mkdir -p "$OUTPUT"

/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
    --input "$INPUT" \
    --output "$OUTPUT" \
    --first-address 78 \
    --last-address 95

echo
echo "================================================================================"
echo "DAILY PIPELINE FINISHED"
echo "================================================================================"
echo
echo "Images : $COUNT"
echo "Output : $OUTPUT"
echo
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 

echo
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -nE \
'python|uv run|cp |mv |mkdir|Output|output|sort|recogn|fingerprint' \
scripts/run_daily_hybrid_v12.sh
5:PROJECT="$HOME/projects/scene_fingerprint_mvp_v02"
11:OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"
40:mkdir -p "$OUTPUT"
42:/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
44:    --output "$OUTPUT" \
54:echo "Output : $OUTPUT"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:08:24

Да. Теперь стало гораздо яснее.

### Что делает `run_daily_hybrid_v12.sh`

Сам `.sh` **физической сортировки вообще не делает**.

Он только:

```text
data/input/daily
        ↓
подсчитывает фото
        ↓
создаёт
data/output/daily/20260818_XXXXXX
        ↓
запускает
scripts/run_hybrid_v12.py
        ↓
передаёт ему INPUT + OUTPUT
```

То есть физическая сортировка, если она действительно есть, находится **в `run_hybrid_v12.py`**, а не в этом launcher'е.

И это хорошо: сам запускатель уже практически подходит под нашу новую архитектуру.

### Что я бы сейчас изменил в WEB

Не трогаем `.sh`.

В `photo_processing.py` делаем интерфейс:

```text
Источник фотографий [____________________] [Выбрать]    Результаты [____________________]
```

Причём:

- источник можно выбрать;
- результат **не выбирается вручную**;
- результат автоматически формируется самим запуском;
- кнопка запуска остаётся;
- после выполнения `OUTPUT` подставляется автоматически.

### Но есть один важный момент

Сейчас `.sh` **жёстко использует**:

```bash
INPUT="$PROJECT/data/input/daily"
```

Поэтому если пользователь в WEB выберет другой источник, `source_input.value` фактически **не попадёт в `.sh`**.

Это уже реальная проблема текущего интерфейса.

Сейчас WEB проверяет выбранный источник:

```python
input_dir = Path(source_input.value)
```

но затем запускает:

```python
bash run_daily_hybrid_v12.sh
```

а тот всё равно берёт:

```text
data/input/daily
```

То есть поле «Источник фотографий» сейчас **не управляет фактическим INPUT**.

---

### Поэтому следующий файл — главный

Нужно посмотреть:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,260p' scripts/run_hybrid_v12.py
```

И отдельно поиск физических операций:

```bash
grep -nE \
'copy|copy2|copytree|shutil|move|rename|mkdir|os\.rename|Path.*rename|output|sort' \
scripts/run_hybrid_v12.py
```

Вот **этот файл** сейчас покажет нам, что именно означает слово «сортировка» в Hybrid v12.

После этого уже можно будет точно сказать:

**оставляем алгоритм как есть → меняем только способ сохранения результата**, либо действительно требуется убрать физическое копирование внутри Hybrid.

---

### 👤 **User** — 2026-08-18 23:11:41

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,260p' scripts/run_hybrid_v12.py
#!/usr/bin/env python3

import argparse
import json
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder

PROJECT = Path(__file__).resolve().parent.parent

SUB_DIR = PROJECT / "data/fingerprints_sub_exp"

# ============================================================
# HYBRID V12 — FROZEN CONTROL LOGIC
# ============================================================

MARGIN_LIMIT = 0.02

GLOBAL_WEIGHT = 10.0
SUB_WEIGHT = 2.5
NEIGHBOR_WEIGHT = 6.0

def normalize(x):
    x = np.asarray(x, dtype=np.float32)

    n = np.linalg.norm(x)

    if n > 0:
        x = x / n

    return x

def load_subs():
    result = {}

    if not SUB_DIR.exists():
        print(f"[Hybrid] WARNING: sub directory not found: {SUB_DIR}")
        return result

    for d in sorted(SUB_DIR.iterdir()):

        if not d.is_dir():
            continue

        f = d / "embeddings.npy"

        if not f.exists():
            continue

        emb = np.load(f)

        emb = np.array(
            [
                normalize(x)
                for x in emb
            ],
            dtype=np.float32,
        )

        result[d.name] = emb

    return result

def get_neighbor_votes(rows, index):
    votes = Counter()

    if index <= 0:
        return votes

    if index >= len(rows) - 1:
        return votes

    left = rows[index - 1]["top1"]
    right = rows[index + 1]["top1"]

    # FROZEN V12 RULE:
    # only complete agreement
    if left == right:
        votes[left] = 1

    return votes

def run_recognition(input_dir, fingerprints):
    """
    Run the existing DINO v33 recognizer.

    The recognizer itself is NOT modified.
    """

    fp_arg = ",".join(fingerprints)

    cmd = [
        "uv",
        "run",
        "scene-fingerprint",
        "recognize",
        str(input_dir),
        "--top-k",
        "5",
        "--threshold",
        "0.0",
        "--fingerprints",
        fp_arg,
        "--json",
    ]

    print("=" * 80)
    print("DINO v33 RECOGNITION")
    print("=" * 80)
    print("Input:", input_dir)
    print("Fingerprints:", ", ".join(fingerprints))
    print()

    start = time.perf_counter()

    process = subprocess.run(
        cmd,
        cwd=PROJECT,
        capture_output=True,
        text=True,
    )

    elapsed = time.perf_counter() - start

    if process.returncode != 0:
        print(process.stdout)
        print(process.stderr)

        raise RuntimeError(
            f"recognize завершился с кодом {process.returncode}"
        )

    combined = process.stdout + "\n" + process.stderr

    decoder = json.JSONDecoder()
    data = None

    for i, ch in enumerate(combined):

        if ch != "[":
            continue

        try:
            candidate, _ = decoder.raw_decode(
                combined[i:]
            )

            if isinstance(candidate, list):
                data = candidate
                break

        except json.JSONDecodeError:
            pass

    if data is None:
        raise RuntimeError(
            "Не удалось найти JSON-массив в выводе recognition"
        )

    print("Images:", len(data))
    print(f"Recognition time: {elapsed:.2f} sec")

    return data, elapsed

def adapt_recognizer_rows(rows):
    """
    Convert current recognizer output into the legacy
    top1..top5 format required by frozen Hybrid v12.
    """

    adapted = []

    for row in rows:
        item = dict(row)

        candidates = row.get("candidates", [])

        for n in range(1, 6):
            item[f"top{n}"] = None
            item[f"top{n}_score"] = 0.0

        for n, candidate in enumerate(candidates[:5], start=1):
            item[f"top{n}"] = candidate.get("id")
            item[f"top{n}_score"] = float(
                candidate.get("score", 0.0)
            )

        adapted.append(item)

    return adapted

def hybrid_v12(rows, embedder, subs):
    """
    Exact production adaptation of the frozen Hybrid v12 logic.

    Input:
        recognizer rows containing top1..top5.

    Output:
        rows with final best_id.
    """

    changed = []
    results = []
    sub_count = 0

    for i, row in enumerate(rows):

        old = row.get("top1")

        scores = defaultdict(float)

        # ====================================================
        # GLOBAL TOP-5
        # ====================================================

        for k in range(1, 6):

            fp = row.get(f"top{k}")
            sc = row.get(f"top{k}_score")

            if fp:
                scores[fp] += (
                    float(sc)
                    * GLOBAL_WEIGHT
                )

        # ====================================================
        # SUB ONLY BORDER CASES
        # ====================================================

        margin = row.get(
            "margin",
            1,
        )

        if margin < MARGIN_LIMIT:

            sub_count += 1

            image = Path(
                row["file"]
            )

            query = embedder.embed_paths(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -nE \
'copy|copy2|copytree|shutil|move|rename|mkdir|os\.rename|Path.*rename|output|sort' \
scripts/run_hybrid_v12.py
5:import shutil
51:    for d in sorted(SUB_DIR.iterdir()):
132:        capture_output=True,
181:    Convert current recognizer output into the legacy
332:        ranked = sorted(
401:def sort_results(rows, output_dir):
411:    output_dir.mkdir(
417:    sorted_rows = []
433:            output_dir / assigned_id
436:        destination_dir.mkdir(
445:        shutil.copy2(
452:        sorted_rows.append(
487:    for k in sorted(
497:    return sorted_rows, counters
513:        "--output",
533:    output_dir = args.output
554:    print("OUTPUT:", output_dir)
637:    sorted_rows, counters = sort_results(
639:        output_dir,
646:    output_dir.mkdir(
652:        output_dir / "recognition.json"
656:        output_dir / "hybrid_v12.json"
660:        output_dir / "report.json"
664:        output_dir / "statistics.json"
687:            sorted_rows,
701:        "sorted_images": len(sorted_rows),
737:    print(output_dir)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 

в текущем пайплайне все идет последовательно, но у нас удет параллельно.
нужно сделать главную кнопку ЗАПУСТИТЬ и ОСТАНОВИТЬ - она работает на все процессы дино и квен. Индиктор процесса - что вообще идет (мигающая раз в секунду или 2 оранжева кнопка, красный - горит ошибка, зеленый - готово или ждет)
под ней отдельные разделы дино и квен с кнопками запустить и остановить и индикация прогресс бар с цифрами

---

### 🤖 **Assistant** — 2026-08-18 23:11:41

Да, теперь логика понятна. И это уже не просто изменение кнопок — **технический раздел нужно перестроить под управление двумя независимыми процессами**.

### Главная идея

Сейчас:

```text
ЗАПУСТИТЬ
   ↓
DINO / Hybrid
   ↓
Qwen
```

А нам нужно:

```text
                 ОБЩЕЕ УПРАВЛЕНИЕ

             [ ▶ ЗАПУСТИТЬ ] [ ■ ОСТАНОВИТЬ ]
                       │
                       ▼
              ОБЩИЙ ИНДИКАТОР СОСТОЯНИЯ
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
       DINO                       QWEN
   [Запустить] [Стоп]        [Запустить] [Стоп]
       │                         │
   ███████░░░ 72%             ███░░░░░ 31%
   145 / 200                   62 / 200
```

И **DINO и Qwen запускаются параллельно**, а не Qwen автоматически ждёт завершения DINO.

---

### Главная кнопка

Одна общая кнопка:

**▶ ЗАПУСТИТЬ**

запускает весь рабочий контур.

**■ ОСТАНОВИТЬ**

останавливает все процессы, которыми управляет этот запуск:

- DINO / Hybrid;
- Qwen;
- дочерние процессы, если они были запущены этим контуром.

То есть это **master control**.

---

### Общий индикатор

Предлагаю ровно ту логику, которую ты описал:

**🟢 ЗЕЛЁНЫЙ — готово / ожидание**

```text
● ГОТОВО
```

**🟠 ОРАНЖЕВЫЙ — идёт обработка**

Индикатор/кнопка мигает примерно раз в **1–2 секунды**:

```text
● ОБРАБОТКА...
```

Причём текст может показывать, что сейчас происходит:

```text
● DINO + QWEN: выполняется
```

**🔴 КРАСНЫЙ — ошибка**

```text
● ОШИБКА
```

И рядом можно показывать короткую причину.

После исправления/нового запуска снова зелёный.

---

### DINO

Отдельная секция:

```text
DINO v33 / HYBRID v12

[ ▶ ЗАПУСТИТЬ ] [ ■ ОСТАНОВИТЬ ]

██████████████░░░░░░ 72%

145 / 200
```

И желательно ниже текущая стадия:

```text
Распознавание: 145 / 200
```

А когда закончится Hybrid:

```text
████████████████████ 100%

200 / 200

✓ DINO / Hybrid завершён
```

При этом **физическую сортировку здесь не делаем**. `sort_results()` сейчас как раз содержит `shutil.copy2`, поэтому это отдельный участок, который потом нужно переделать на запись виртуальных результатов.

---

### Qwen

Отдельная секция:

```text
QWEN3-VL 4B

[ ▶ ЗАПУСТИТЬ ] [ ■ ОСТАНОВИТЬ ]

███████░░░░░░░░░░░░ 34%

68 / 200
```

И текущая операция:

```text
Анализ: 68 / 200
```

---

### Важный момент по параллельности

Я бы **не запускал Qwen через цепочку внутри `run_pipeline()`**, как сейчас:

```python
await DINO
↓
await Qwen
```

Нужно перейти на два независимых subprocess:

```text
run_all()
 ├── dino_process
 │
 └── qwen_process
```

Оба запускаются одновременно.

При этом Qwen должен получать **не физически отсортированную папку**, а результаты/индекс, которые доступны ему независимо от завершения DINO.

То есть архитектура:

```text
                    INPUT
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
      DINO v33                 QWEN 4B
          │                       │
          ▼                       ▼
    DINO metadata             Qwen metadata
          │                       │
          └───────────┬───────────┘
                      ▼
                   OUTPUT
                      │
                      ▼
                    WEB
```

И это хорошо сочетается с нашим решением **не сортировать физически фотографии**.

### Что я предлагаю сделать сейчас

**Не менять пока `run_hybrid_v12.py`.** Сначала спроектировать именно UI/state-management:

- `RUN_ALL`;
- `STOP_ALL`;
- `DINO_START`;
- `DINO_STOP`;
- `QWEN_START`;
- `QWEN_STOP`;
- состояния `IDLE / RUNNING / ERROR / DONE`;
- PID/процесс для каждого;
- общий индикатор;
- два независимых progress bar;
- счётчики `N / TOTAL`.

А затем уже подключить к этому реальные процессы.

И отдельно зафиксировать: **текущий `sort_results()` с `shutil.copy2()` — это старое физическое сохранение, которое не должно попасть в новую архитектуру.**

---

### 👤 **User** — 2026-08-18 23:12:52

При этом Qwen должен получать **не физически отсортированную папку**, а результаты/индекс, которые доступны ему независимо от завершения DINO.  Квен начинает работу после того, как файлы получили ид,  дино - тоже

---

### 🤖 **Assistant** — 2026-08-18 23:12:52

Да, именно. Тогда параллельность нужно понимать **не как одновременный старт с одним и тем же INPUT**, а как **два независимых воркера с общей готовностью отдельных фотографий**.

Правильная схема:

```text
                    INPUT
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
        DINO                    QWEN
          │                       │
          │                  ждёт ID фото
          │                       │
          ▼                       │
       PHOTO ID ──────────────────┘
          │
          ▼
       результат
```

Но важная деталь: **Qwen не ждёт окончания всего DINO**.

Например:

```text
Фото 001 → DINO → ID 78 → Qwen начинает 001
Фото 002 → DINO → ID 83 → Qwen начинает 002
Фото 003 → DINO → ID 78 → Qwen начинает 003
...
```

То есть появляется **очередь готовых фотографий**.

### Состояние каждой фотографии

Можно мыслить так:

```text
photo_001.jpg

DINO:
  PROCESSING
      ↓
  ID = 78
      ↓
  READY_FOR_QWEN
      ↓
QWEN:
  PROCESSING
      ↓
  DONE
```

А другая фотография в это время может находиться здесь:

```text
photo_002.jpg

DINO: PROCESSING
QWEN: WAITING
```

И ещё одна:

```text
photo_003.jpg

DINO: DONE, ID=83
QWEN: PROCESSING
```

### Поэтому OUTPUT становится индексом

Не нужно:

```text
OUTPUT/
   78/
      photo001.jpg
   83/
      photo002.jpg
```

Вместо этого:

```text
OUTPUT/
   run/
      recognition.json
      hybrid_v12.json
      photos.json
      qwen/
          ...
      previews/
          ...
```

А внутри записи фотографии:

```text
{
    "source_path": ".../photo001.jpg",
    "id": "78",
    "dino_status": "DONE",
    "qwen_status": "PROCESSING"
}
```

Таким образом **одна и та же фотография остаётся в INPUT**, а всё остальное — виртуальные состояния и результаты.

---

### И UI тогда становится очень логичным

**Общий уровень:**

```text
┌──────────────────────────────────────────────┐
│ ▶ ЗАПУСТИТЬ              ■ ОСТАНОВИТЬ       │
│                                              │
│ 🟠 ОБРАБОТКА                                │
└──────────────────────────────────────────────┘
```

**DINO:**

```text
DINO v33 → Hybrid v12

[▶ Запустить] [■ Остановить]

████████████░░░░░░░░  62%

124 / 200
ID назначен: 124
```

**Qwen:**

```text
Qwen3-VL 4B

[▶ Запустить] [■ Остановить]

███████░░░░░░░░░░░░░  35%

70 / 200
Ожидает ID: 54
```

И вот это число **«Ожидает ID»** будет очень полезно: сразу видно, что Qwen не тормозит — ему просто ещё нечего обрабатывать.

### Главное

Получается **конвейер**, а не последовательный pipeline:

```text
DINO:  001 002 003 004 005 006 007 ...
        ↓   ↓   ↓   ↓   ↓
QWEN:      001 002 003 004 ...
```

DINO работает своим темпом, Qwen своим темпом.

И **главная кнопка управляет обоими**, а отдельные кнопки позволяют запускать/останавливать DINO или Qwen независимо.

Это, на мой взгляд, именно та архитектура, к которой мы сейчас должны привести техническое окно.

---

### 👤 **User** — 2026-08-18 23:13:46

да

---

### 🤖 **Assistant** — 2026-08-18 23:13:47

Да. Тогда **фиксируем именно эту архитектуру** и от неё дальше не отходим.

### Технический раздел

Вверху одна строка:

```text
Источник фотографий [____________________] [Выбрать]    Результаты [____________________]
```

`Источник` выбирается пользователем.  
`Результаты` формируются автоматически — кнопки выбора нет.

Далее:

```text
[ ▶ ЗАПУСТИТЬ ]    [ ■ ОСТАНОВИТЬ ]

● ГОТОВО
```

Общий индикатор:

- 🟢 **готово / ожидание**
- 🟠 **обработка** — мигает раз в 1–2 секунды
- 🔴 **ошибка**
- после завершения — 🟢

### DINO

```text
DINO v33 → Hybrid v12

[ ▶ ЗАПУСТИТЬ ] [ ■ ОСТАНОВИТЬ ]

████████████░░░░░░░░  62%
124 / 200

ID назначено: 124
```

DINO обрабатывает фотографии и как только конкретной фотографии присвоен ID, она становится доступной Qwen.

### Qwen

```text
Qwen3-VL 4B

[ ▶ ЗАПУСТИТЬ ] [ ■ ОСТАНОВИТЬ ]

███████░░░░░░░░░░░░░  35%
70 / 200

Ожидает ID: 54
```

Qwen **не ждёт завершения DINO целиком**.

Получил:

```text
photo_071 → ID 83
```

→ сразу может брать `photo_071`.

---

### А главное — физически фото не двигаем

```text
INPUT
├── photo_001.jpg
├── photo_002.jpg
├── photo_003.jpg
└── ...

             ↓

       ОБЩИЙ ИНДЕКС

photo_001 → ID 78 → Qwen DONE
photo_002 → ID 83 → Qwen PROCESSING
photo_003 → ID 78 → Qwen WAITING
```

Все оригиналы остаются в `INPUT`.

`OUTPUT` содержит **данные обработки**, а не физически отсортированные копии.

---

И ещё один принцип я бы зафиксировал: **DINO и Qwen должны иметь собственные состояния и собственные кнопки, но общую очередь/БД состояния фотографий.** Это позволит потом без переделки интерфейса добавить OCR или другие обработчики как третий независимый модуль.

---

### 👤 **User** — 2026-08-18 23:14:43

да. И возможность продолжения с прерывания, и пропуск уже обработанных, но также и возможность обработать заново (выбор - обработать заново -пропустить - для всех)

---

### 🤖 **Assistant** — 2026-08-18 23:14:44

Да. Это обязательно стоит заложить **сразу**, иначе после первого прерывания придётся переделывать очередь.

Фиксируем модель обработки.

### 1. Состояние каждой фотографии

Для каждого файла в индексе храним отдельно:

```text
photo
├── source_path
├── file_hash
├── dino_status
├── dino_id
├── dino_result
├── qwen_status
├── qwen_result
└── updated_at
```

Статусы примерно:

```text
WAITING
PROCESSING
DONE
ERROR
SKIPPED
```

Это позволяет точно понимать, что уже сделано.

---

### 2. Продолжение после остановки

Если обработка была:

```text
200 фото
DINO → 137 / 200
Qwen → 94 / 200
```

нажали **СТОП**.

При следующем запуске:

```text
DINO
137 готовых → пропустить
138 → продолжить

Qwen
94 готовых → пропустить
95 → продолжить
```

То есть **ничего заново пересчитывать не нужно**.

Причём лучше ориентироваться не просто на наличие файла результата, а на:

**`source_path + file_hash + версия алгоритма`**

Так изменение/замена фотографии не будет ошибочно считаться уже обработанной.

---

### 3. Выбор режима при запуске

При запуске нужен режим:

```text
Что делать с уже обработанными?

○ Пропустить
○ Обработать заново
```

И отдельная возможность:

```text
☑ Для всех
```

То есть можно сделать компактно:

```text
Уже обработанные:

[ Пропустить ▼ ]

☑ Применить ко всем
```

или выбрать:

```text
Пропустить
Обработать заново
```

---

### 4. Если выбрано «Пропустить»

Например:

```text
200 фотографий

DONE       120
WAITING     60
ERROR       20
```

Запускаем:

```text
→ 120 пропускаем
→ 60 обрабатываем
→ 20 ERROR тоже можно отправить в обработку
```

Но ошибки я бы **не считал автоматически успешно обработанными**.

---

### 5. Если «Обработать заново»

Тогда существующий результат конкретного этапа сбрасывается:

```text
DINO DONE
     ↓
RESET
     ↓
WAITING
     ↓
DINO снова
```

И аналогично для Qwen.

Это важно сделать **независимо**.

Например:

```text
DINO уже DONE
Qwen ERROR
```

Можно перезапустить **только Qwen**, не гоняя DINO повторно.

---

### 6. Поэтому общий запуск должен спрашивать отдельно

Я бы сделал:

```text
ЗАПУСК ОБРАБОТКИ

DINO
○ Продолжить
○ Обработать заново

Qwen
○ Продолжить
○ Обработать заново

☑ Применить ко всем
```

Но при обычном ежедневном запуске дефолт:

**Продолжить / пропустить уже обработанные.**

---

### 7. И ещё важнее — версия алгоритма

В записи результата надо хранить, например:

```text
dino_version = v33
hybrid_version = v12
qwen_version = qwen3-vl-4b
```

Тогда если завтра мы сделаем `v34`, старые результаты `v33` не будут ошибочно считаться актуальными.

Получается очень надёжная схема:

```text
                    ФОТО
                     │
                file_hash
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
       DINO v33              QWEN 4B
          │                     │
      status/id              status/result
          │                     │
          └──────────┬──────────┘
                     ▼
                   INDEX
                     │
                     ▼
                    WEB
```

И при этом:

**СТОП → продолжить позже → пропустить готовое → обработать только незавершённое.**

А если нужно — **«обработать заново»** для одного этапа или для всех.

Это уже можно считать базовым контрактом технического раздела.

---

### 👤 **User** — 2026-08-18 23:15:34

да

---

### 🤖 **Assistant** — 2026-08-18 23:15:35

Да, фиксируем. Тогда следующий шаг — **не писать код вслепую**, а сначала встроить эту модель в существующий проект.

Сейчас у нас есть три уровня:

```text
1. WEB
   управление процессами и отображение состояния

2. QUEUE / INDEX
   состояние каждой фотографии
   → что обработано
   → что ожидает
   → что выполняется
   → что завершилось ошибкой

3. WORKERS
   DINO / Hybrid
   Qwen
   работают независимо
```

И важный момент: **существующий `run_hybrid_v12.py` сейчас содержит физическое копирование через `shutil.copy2()`**. Мы это пока не меняем, потому что сначала нужно понять весь его выход и логику `sort_results()`.

Следующим посмотрим именно этот участок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '300,530p' scripts/run_hybrid_v12.py
```

Особенно нас интересуют:

```text
hybrid_v12()
sort_results()
main()
```

После этого сможем точно определить, **какие данные уже можно использовать как индекс**, а какие придётся добавить для возобновления, пропуска обработанных и параллельной передачи фотографий из DINO в Qwen.

---

### 👤 **User** — 2026-08-18 23:15:59

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '300,530p' scripts/run_hybrid_v12.py
        # SEQUENCE CONSENSUS
        # ====================================================

        neighbors = get_neighbor_votes(
            rows,
            i,
        )

        left_fp = None
        right_fp = None

        if i > 0:
            left_fp = rows[i - 1].get("top1")

        if i < len(rows) - 1:
            right_fp = rows[i + 1].get("top1")

        if (
            left_fp
            and right_fp
            and left_fp == right_fp
        ):
            # FROZEN V12:
            # actual implementation uses +3.0
            scores[left_fp] += 3.0

        # ====================================================
        # FINAL DECISION V12
        # ====================================================

        best = old

        ranked = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        if ranked:

            candidate = ranked[0][0]

            gain = (
                scores[candidate]
                - scores.get(old, 0)
            )

            if (
                candidate != old
                and gain > 1.5
            ):
                best = candidate

        old_score = scores.get(
            old,
            0,
        )

        new_score = scores.get(
            best,
            0,
        )

        hybrid_changed = best != old

        result = dict(row)

        result["original_best_id"] = old
        result["best_id"] = best

        result["hybrid_changed"] = hybrid_changed

        result["hybrid_old_score"] = old_score
        result["hybrid_score"] = new_score

        result["hybrid_margin"] = margin
        result["hybrid_neighbors"] = dict(neighbors)

        results.append(result)

        if (
            best != old
            and new_score > old_score
        ):
            changed.append(
                {
                    "file": Path(
                        row["file"]
                    ).name,
                    "old": old,
                    "new": best,
                    "margin": margin,
                    "neighbors": dict(neighbors),
                    "old_score": scores[old],
                    "new_score": scores[best],
                }
            )

    return results, changed, sub_count

def sort_results(rows, output_dir):
    """
    Copy photos according to FINAL Hybrid best_id.
    """

    print()
    print("=" * 80)
    print("SORTING")
    print("=" * 80)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    counters = Counter()
    sorted_rows = []

    for item in rows:

        source = Path(
            item["file"]
        )

        assigned_id = item.get(
            "best_id"
        )

        if not assigned_id:
            continue

        destination_dir = (
            output_dir / assigned_id
        )

        destination_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            destination_dir / source.name
        )

        shutil.copy2(
            source,
            destination,
        )

        counters[assigned_id] += 1

        sorted_rows.append(
            {
                "file": str(source),
                "filename": source.name,
                "assigned_id": assigned_id,
                "original_best_id": item.get(
                    "original_best_id"
                ),
                "hybrid_changed": item.get(
                    "hybrid_changed"
                ),
                "score": item.get("score"),
                "second_score": item.get(
                    "second_score"
                ),
                "margin": item.get("margin"),
                "confidence": item.get(
                    "confidence"
                ),
                "status": item.get("status"),
                "best_image": item.get(
                    "best_image"
                ),
                "best_image_score": item.get(
                    "best_image_score"
                ),
                "hybrid_old_score": item.get(
                    "hybrid_old_score"
                ),
                "hybrid_score": item.get(
                    "hybrid_score"
                ),
            }
        )

    for k in sorted(
        counters,
        key=lambda x: int(
            x.split("_")[0]
        ),
    ):
        print(
            f"{k:10s} {counters[k]:4d}"
        )

    return sorted_rows, counters

def main():

    parser = argparse.ArgumentParser(
        description="Production runner for frozen Hybrid v12"
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--first-address",
        type=int,
        default=78,
    )

    parser.add_argument(
        "--last-address",
        type=int,
        default=95,
    )

    args = parser.parse_args()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:16:00

Вот теперь видно точное место. **Логику Hybrid v12 действительно можно сохранить практически целиком.**

Главное изменение будет только в слое выдачи результата.

### Сейчас

После принятия решения:

```text
DINO v33
   ↓
Hybrid v12
   ↓
best_id
   ↓
sort_results()
   ↓
shutil.copy2()
   ↓
OUTPUT/78/photo.jpg
OUTPUT/83/photo.jpg
...
```

Вот этот участок:

```python
shutil.copy2(
    source,
    destination,
)
```

и есть **физическая сортировка**.

### Нам нужно

Оставить:

```text
DINO v33
   ↓
Hybrid v12
   ↓
best_id
   ↓
INDEX / JSON / DB
```

То есть `sort_results()` больше не должен копировать фотографии.

Но сам результат, который сейчас формируется ниже, **очень полезный**:

```text
file
filename
assigned_id
original_best_id
hybrid_changed
score
second_score
margin
confidence
status
best_image
best_image_score
hybrid_old_score
hybrid_score
```

Это уже почти готовая запись для нашего виртуального индекса.

---

## И здесь появляется важная возможность для параллельного Qwen

Как только конкретная фотография получила:

```text
assigned_id = 78
```

она становится:

```text
DINO = DONE
QWEN = READY
```

и Qwen может её забрать.

То есть нам не нужно ждать, пока закончится `sort_results()` для всех 200 фотографий.

Но есть ещё одна особенность: **текущий Hybrid v12 использует соседей**:

```python
left_fp
right_fp
```

Поэтому нельзя просто взять фотографию №1 и окончательно присвоить ей ID, если для её решения нужны результаты соседей.

Это надо сохранить.

То есть последовательность внутри DINO остаётся:

```text
распознавание всех / получение результатов
        ↓
Hybrid учитывает соседей
        ↓
финальный best_id
        ↓
фото становится READY для Qwen
```

А уже **после появления финального ID** Qwen работает независимо.

---

### Поэтому параллельность будет на уровне этапов

Не так:

```text
DINO фото 1 → Qwen фото 1
DINO фото 2 → Qwen фото 2
```

если Hybrid ещё не имеет необходимых соседних результатов.

А так:

```text
DINO
├── распознавание
├── Hybrid / соседние результаты
└── финальные ID
          │
          ├────→ Qwen очередь
          │
          ├────→ Qwen очередь
          │
          └────→ Qwen очередь

Qwen обрабатывает готовые фотографии своим темпом
```

Это соответствует твоему требованию: **Qwen начинает работу с фотографией сразу после того, как DINO/Hybrid дал ей окончательный ID**, но не ждёт окончания всего запуска.

---

## И ещё один важный момент

Для возможности:

- продолжить после остановки;
- пропустить обработанные;
- обработать заново;
- сделать это отдельно для DINO и Qwen;

нам **нельзя использовать только JSON финального запуска**.

Нужен постоянный индекс состояния фотографий.

Минимально:

```text
photo
source_path
file_hash

dino_status
dino_id
dino_version

qwen_status
qwen_version
```

А результаты Hybrid/Qwen храним рядом.

Тогда после `STOP` программа просто смотрит:

```text
file_hash + версия этапа + статус
```

и понимает, что делать.

---

### Следующий кусок надо посмотреть

Ты показал `main()` только до аргументов. Нам нужно увидеть **оставшуюся часть**, где вызываются `run_recognition`, `hybrid_v12`, `sort_results` и записываются JSON.

Выполни:

```bash id="k6t8j4"
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '530,760p' scripts/run_hybrid_v12.py
```

После этого у нас будет полный `Hybrid v12`, и можно будет уже точно спроектировать новый worker, **не меняя саму frozen-логику распознавания и соседей**.

---

### 👤 **User** — 2026-08-18 23:18:20

тут надо разделить - id начальный - который является пседонимом для работы и дино и квен, чтобы результаты в базе сводились воедино независимо от названия и мемтоположения, и ид после Дино - после ДИно это ид Адреса, который будет потом отображаться в гриде

---

