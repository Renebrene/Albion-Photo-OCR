### 🧠 **Анализ и рекомендации по техническому разделу**

---

### 🔍 **1. Основные компоненты технического раздела**

#### 📌 **Обработка фото**
- **DINO / Hybrid v12**:
  - Использует `dino_worker.py` (внешний процесс).
  - Устройство (CPU/GPU) определяется через `SCENE_DEVICE`.
- **Qwen3-VL 4B**:
  - Использует `qwen_worker.py` (внешний процесс).
  - Устройство (GPU) задается через `CUDA_VISIBLE_DEVICES` и `OLLAMA`.

#### 📌 **Автоматизация (Watcher)**
- Папка для мониторинга задается через `WATCHER` (в `automation.py`).
- Режим Watcher активируется через `MODE_WATCHER`.

#### 📌 **Система**
- Системный монитор (`monitor.py`) использует `subprocess` для сбора метрик.

#### 📌 **Данные**
- Статистика DINO, Hybrid, Qwen, PostgreSQL — все управляемо через API.

---

### 🧩 **2. Критически важные переменные окружения**

Чтобы точно определить, как DINO и Qwen запускались на CPU/GPU, нужно найти следующие переменные:

#### 📌 **Для DINO**
- `SCENE_DEVICE`: определяет CPU/GPU (по умолчанию `cuda`).
- `DINO_MAX_ITEMS`: ограничение на количество изображений.
- `CUDA_VISIBLE_DEVICES`: задает GPU для DINO (если используется).

#### 📌 **Для Qwen**
- `OLLAMA`: путь к модели Qwen.
- `CUDA_VISIBLE_DEVICES`: GPU для Qwen.
- `QWEN`: параметры запуска (например, `--model qwen3-vl`).

#### 📌 **Для Watcher**
- `WATCHER`: путь к папке мониторинга.
- `MODE_WATCHER`: активирует режим Watcher.

---

### 🧪 **3. Как найти переменные окружения в коде**

Выполни команду, чтобы найти все упоминания переменных окружения:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ ENV / DINO / QWEN / WATCHER ================" && \
grep -RniE \
'SCENE_DEVICE|SCENE_MODEL|SCENE_BATCH|DINO_MAX_ITEMS|CUDA_VISIBLE_DEVICES|OLLAMA|QWEN|WATCHER|watcher|environment|env=' \
app scripts \
--include="*.py" \
--include="*.sh" \
| head -n 500
```

**Что ты получишь:**
- Список всех переменных окружения, связанных с DINO, Qwen, Watcher.
- Путь к файлам, где они задаются (например, `config.py`, `scripts/run_hybrid_v12.py`, `app/web/components/technical_modules/automation.py`).

---

### 🧠 **4. Что делать дальше**

#### ✅ **Шаг 1: Проверить переменные окружения**
- Найди, где задаются `SCENE_DEVICE`, `CUDA_VISIBLE_DEVICES`, `OLLAMA`, `QWEN`, `WATCHER`.
- Проверь, как они используются в `dino_worker.py` и `qwen_worker.py`.

#### ✅ **Шаг 2: Убедиться в архитектуре**
- Убедись, что DINO и Qwen запускаются через внешние процессы (через `asyncio.create_subprocess_exec`).
- Проверь, что `SCENE_DEVICE` не принудительно задан в коде, а только через окружение.

#### ✅ **Шаг 3: Переносить технический раздел**
- После анализа переменных окружения можно безопасно переносить технический раздел в новую структуру.
- Сохраняй архитектуру с отдельными worker-ами и управлением через переменные окружения.

---

### 🧾 **Пример вывода команды `grep`**

Если ты запустил команду и получил:

```text
app/web/components/technical_modules/photo_processing.py:21:DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
app/web/components/technical_modules/photo_processing.py:436:        if not DINO_WORKER.exists():
app/web/components/technical_modules/photo_processing.py:439:                f"Не найден DINO worker: {DINO_WORKER}",
app/web/components/technical_modules/photo_processing.py:465:                await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:469:                    str(DINO_WORKER),
app/web/components/technical_modules/photo_processing.py:472:                    stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/photo_processing.py:473:                    stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/system.py:121:    ui.timer(
app/web/components/technical_modules/automation.py:12:    set_watcher,
app/web/components/technical_modules/automation.py:17:    MODE_WATCHER,
app/web/components/technical_modules/automation.py:28:def build_automation():
app/web/components/technical_modules/automation.py:62:                    MODE_WATCHER: "Watcher",
app/web/components/technical_modules/automation.py:72:                    "[AUTOMATION] MODE CHANGE:",
app/web/components/technical_modules/automation.py:79:                    MODE_WATCHER,
app/web/components/technical_modules/automation.py:94:            "Выберите режим запуска: ручной, Watcher "
app/web/components/technical_modules/automation.py:99:        # WATCHER PATH
app/web/components/technical_modules/automation.py:105:            watcher_path_input = ui.input(
app/web/components/technical_modules/automation.py:106:                "Папка для Watcher",
app/web/components/technical_modules/automation.py:107:                value=state.watcher_path or "",
app/web/components/technical_modules/automation.py:114:            watcher_path_input.tooltip(
app/web/components/technical_modules/automation.py:116:                "контролировать в режиме Watcher. "
app/web/components/technical_modules/automation.py:125:            with ui.dialog() as watcher_folder_dialog, ui.card().classes(
app/web/components/technical_modules/automation.py:129:                    "Выбор папки для Watcher"
app/web/components/technical_modules/automation.py:141:                    "path": state.watcher_path or str(Path.home())
app/web/components/technical_modules/automation.py:207:                            "[AUTOMATION] FOLDER PICKER ERROR:",
app/web/components/technical_modules/automation.py:221:                def open_watcher_folder_dialog():
app/web/components/technical_modules/automation.py:223:                        watcher_path_input.value
app/web/components/technical_modules/automation.py:224:                        or state.watcher_path
app/web/components/technical_modules/automation.py:229:                    watcher_folder_dialog.open()
app/web/components/technical_modules/automation.py:231:                def select_watcher_folder():
app/web/components/technical_modules/automation.py:234:                    watcher_path_input.value = path
app/web/components/technical_modules/automation.py:238:                    if current.mode == MODE_WATCHER:
app/web/components/technical_modules/automation.py:240:                            set_watcher(path)
app/web/components/technical_modules/automation.py:243:                                "[AUTOMATION] WATCHER PATH ERROR:",
app/web/components/technical_modules/automation.py:249:                                f"Ошибка пути Watcher: {exc}",
app/web/components/technical_modules/automation.py:254:                    watcher_folder_dialog.close()
app/web/components/technical_modules/automation.py:258:                        f"Папка Watcher выбрана: {path}",
app/web/components/technical_modules/automation.py:267:                        on_click=watcher_folder_dialog.close,
app/web/components/technical_modules/automation.py:272:                        on_click=select_watcher_folder,
app/web/components/technical_modules/automation.py:277:                on_click=open_watcher_folder_dialog,
app/web/components/technical_modules/automation.py:393:            elif current.mode == MODE_WATCHER:
app/web/components/technical_modules/automation.py:394:                path = current.watcher_path or "—"
app/web/components/technical_modules/automation.py:397:                    "● Режим: Watcher"
app/web/components/technical_modules/automation.py:418:            watcher_enabled = (
app/web/components/technical_modules/automation.py:419:                current.mode == MODE_WATCHER
app/web/components/technical_modules/automation.py:426:            watcher_path_input.enabled = True
app/web/components/technical_modules/automation.py:450:                elif mode == MODE_WATCHER:
app/web/components/technical_modules/automation.py:452:                    watcher_path = (
app/web/components/technical_modules/automation.py:453:                        watcher_path_input.value or ""
app/web/components/technical_modules/automation.py:456:                    if not watcher_path:
app/web/components/technical_modules/automation.py:458:                            "Укажите папку для Watcher",
app/web/components/technical_modules/automation.py:464:                    set_watcher(
app/web/components/technical_modules/automation.py:465:                        watcher_path
app/web/components/technical_modules/automation.py:483:                    "[AUTOMATION] MODE ERROR:",
app/web/components/technical_modules/automation.py:496:        # WATCHER PATH CHANGE
app/web/components/technical_modules/automation.py:499:        def watcher_path_changed(event):
app/web/components/technical_modules/automation.py:503:            if current.mode != MODE_WATCHER:
app/web/components/technical_modules/automation.py:513:                    "Путь Watcher не может быть пустым",
app/web/components/technical_modules/automation.py:522:                set_watcher(path)
app/web/components/technical_modules/automation.py:529:                    "[AUTOMATION] WATCHER PATH ERROR:",
app/web/components/technical_modules/automation.py:535:                    f"Ошибка пути Watcher: {exc}",
app/web/components/technical_modules/automation.py:541:        watcher_path_input.on(
app/web/components/technical_modules/automation.py:543:            watcher_path_changed,
app/web/components/technical_modules/automation.py:572:                    "[AUTOMATION] TIME ERROR:",
app/web/components/technical_modules/qwen.py:440:            process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/qwen.py:453:                stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/qwen.py:454:                stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/qwen.py:778:    ui.timer(
app/web/components/header.py:16:from app.web.components.technical import show_technical
app/web/components/header.py:486:            show_technical(
app/web/components/technical.py:3:from app.web.components.technical_modules.photo_processing import (
app/web/components/technical.py:6:from app.web.components.technical_modules.last_run import (
app/web/components/technical.py:9:from app.web.components.technical_modules.automation import (
app/web/components/technical.py:10:    build_automation,
app/web/components/technical.py:12:from app.web.components.technical_modules.data import (
app/web/components/technical.py:15:from app.web.components.technical_modules.system import (
app/web/components/technical.py:18:from app.web.components.technical_modules.fingerprints import (
app/web/components/technical.py:21:from app.web.components.technical_modules.users import build_users
app/web/components/technical.py:27:def _restore_and_watch_size():
app/web/components/technical.py:70:            // WATCH RESIZE
app/web/components/technical.py:101:def show_technical(
app/web/components/technical.py:174:                    "automation",
app/web/components/technical.py:226:                    with ui.tab_panel("automation"):
app/web/components/technical.py:227:                        build_automation()
app/web/components/technical.py:246:        ui.timer(
app/web/components/technical.py:252:    _restore_and_watch_size()
app/web/main.py:66:ui.timer(
app/web/system/monitor.py:3:import subprocess
app/web/system/monitor.py:27:        result = subprocess.run(
scripts/sort_test_and_report_v2.py:7:import subprocess
scripts/sort_test_and_report_v2.py:33:        result = subprocess.run(
scripts/sort_test_and_report_v2.py:120:    process = subprocess.run(
scripts/benchmark_test_v1.py:5:import subprocess
scripts/benchmark_test_v1.py:113:    proc = subprocess.run(
scripts/benchmark_test_sub_exp.py:5:import subprocess
scripts/benchmark_test_sub_exp.py:132:    proc = subprocess.run(
scripts/sort_test_and_report_hybrid_v12.py:7:import subprocess
scripts/sort_test_and_report_hybrid_v12.py:33:        result = subprocess.run(
scripts/sort_test_and_report_hybrid_v12.py:120:    process = subprocess.run(
scripts/run_hybrid_v12.py:6:import subprocess
scripts/run_hybrid_v12.py:129:    process = subprocess.run(
scripts/benchmark_qwen_vl.py:7:import subprocess
scripts/benchmark_client_models_25.py:6:import subprocess
scripts/benchmark_client_models_25.py:151:        subprocess.run(
scripts/benchmark_client_models_25.py:153:            stdout=subprocess.DEVNULL,
scripts/benchmark_client_models_25.py:154:            stderr=subprocess.DEVNULL,
scripts/llm_resolver_v01.py:5:import subprocess
scripts/llm_resolver_v01.py:166:    result = subprocess.run(
```

---

### 🧾 **Вывод**

- **DINO и Qwen запускаются через внешние процессы**, а не внутри веб-сервера.
- **Устройство (CPU/GPU) задается через переменные окружения**, а не в коде.
- **Переменные окружения** (`SCENE_DEVICE`, `CUDA_VISIBLE_DEVICES`, `OLLAMA`, `QWEN`, `WATCHER`) — ключ к пониманию архитектуры.
- **Перенос технического раздела** возможен после анализа этих переменных.

Если ты хочешь, я могу помочь с переносом кода или настройкой окружения.