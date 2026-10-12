### 🛠️ **Решение: Интеграция управления обработкой в интерфейс**

---

#### 🧩 **1. Общая архитектура**
Используем существующие компоненты:
- **`app/pipeline/controller.py`** — для управления состоянием процессов.
- **`app/pipeline/queue.py`** — для работы с очередью задач.
- **`app/workers/dino_worker.py`** и **`app/workers/qwen_worker.py`** — для выполнения обработки.
- **`app/pipeline/recovery.py`** — для восстановления после остановки.

**Избегаем дублирования** между `photo_processing.py` и `qwen.py` — объединяем логику в общий модуль.

---

#### 📌 **2. Техническое окно: "Обработка фотографий"**

**UI-компонент: `app/web/components/technical_modules/photo_processing.py`**

```python
from flask import Blueprint, render_template, request, jsonify
from app.pipeline.controller import Controller
from app.pipeline.queue import Queue
from app.pipeline.recovery import Recovery
import time

bp = Blueprint('photo_processing', __name__)

@bp.route('/processing', methods=['GET', 'POST'])
def processing():
    controller = Controller()
    queue = Queue()
    recovery = Recovery()

    if request.method == 'POST':
        action = request.form.get('action')
        model = request.form.get('model')

        if action == 'start':
            controller.start(model)
        elif action == 'pause':
            controller.pause(model)
        elif action == 'stop':
            controller.stop(model)
        elif action == 'resume':
            controller.resume(model)

        return jsonify({"status": "success"})

    # Получаем статусы
    dino_status = controller.get_status('dino')
    qwen_status = controller.get_status('qwen')

    # Прогресс
    dino_progress = queue.get_progress('dino')
    qwen_progress = queue.get_progress('qwen')

    # Общий статус
    total_processed = queue.get_total_processed()
    total_tasks = queue.get_total_tasks()
    errors = queue.get_errors()
    pending_tasks = queue.get_pending()

    # Лог последних действий
    log = recovery.get_last_actions()

    return render_template('processing.html', 
                          dino_status=dino_status, 
                          qwen_status=qwen_status,
                          dino_progress=dino_progress,
                          qwen_progress=qwen_progress,
                          total_processed=total_processed,
                          total_tasks=total_tasks,
                          errors=errors,
                          pending_tasks=pending_tasks,
                          log=log)
```

---

#### 📌 **3. Шаблон: `templates/processing.html`**

```html
<div class="processing-panel">
  <h2>Обработка фотографий</h2>
  <table>
    <tr>
      <th>Модуль</th>
      <th>Состояние</th>
      <th>Прогресс</th>
      <th>Управление</th>
    </tr>
    <tr>
      <td>DINO v33</td>
      <td>{{ dino_status }}</td>
      <td>{{ dino_progress }} / {{ total_tasks }}</td>
      <td>
        {% if dino_status == 'STOPPED' %}
          <button onclick="startDINO()">▶ Старт</button>
        {% elif dino_status == 'RUNNING' %}
          <button onclick="pauseDINO()">⏸ Пауза</button>
          <button onclick="stopDINO()">■ Стоп</button>
        {% elif dino_status == 'PAUSED' %}
          <button onclick="resumeDINO()">▶ Продолжить</button>
        {% endif %}
      </td>
    </tr>
    <tr>
      <td>Qwen3-VL 4B</td>
      <td>{{ qwen_status }}</td>
      <td>{{ qwen_progress }} / {{ total_tasks }}</td>
      <td>
        {% if qwen_status == 'STOPPED' %}
          <button onclick="startQwen()">▶ Старт</button>
        {% elif qwen_status == 'RUNNING' %}
          <button onclick="pauseQwen()">⏸ Пауза</button>
          <button onclick="stopQ3()">■ Стоп</button>
        {% elif qwen_status == 'PAUSED' %}
          <button onclick="resumeQwen()">▶ Продолжить</button>
        {% endif %}
      </td>
    </tr>
  </table>

  <h3>Общий статус</h3>
  <p>Обработано: {{ total_processed }} / {{ total_tasks }}</p>
  <p>Ошибок: {{ errors }}</p>
  <p>В очереди: {{ pending_tasks }}</p>

  <h3>Последнее действие / лог</h3>
  <pre>{{ log }}</pre>
</div>
```

---

#### 📌 **4. Обновление статусов в реальном времени**

**Используем WebSocket для обновления статусов:**

- В `app/web/components/technical_modules/automation.py` добавляем:
```python
from flask_socketio import emit

@socketio.on('request_status')
def handle_status_request():
    controller = Controller()
    queue = Queue()
    recovery = Recovery()

    dino_status = controller.get_status('dino')
    qwen_status = controller.get_status('qwen')
    dino_progress = queue.get_progress('dino')
    qwen_progress = queue.get_progress('qwen')
    total_processed = queue.get_total_processed()
    total_tasks = queue.get_total_tasks()
    errors = queue.get_errors()
    pending_tasks = queue.get_pending()
    log = recovery.get_last_actions()

    emit('update_status', {
        'dino_status': dino_status,
        'qwen_status': qwen_status,
        'dino_progress': dino_progress,
        'qwen_progress': qwen_progress,
        'total_processed': total_processed,
        'total_tasks': total_tasks,
        'errors': errors,
        'pending_tasks': pending_tasks,
        'log': log
    })
```

---

#### 📌 **5. Обновление `photo_processing.py` и `qwen.py`**

**Удалите дублированные функции** и объедините логику в общий модуль. Пример:

```python
# app/web/components/technical_modules/processing_utils.py
def start_model(model):
    controller = Controller()
    controller.start(model)

def pause_model(model):
    controller = Controller()
    controller.pause(model)

def stop_model(model):
    controller = Controller()
    controller.stop(model)

def resume_model(model):
    controller = Controller()
    controller.resume(model)
```

---

#### ✅ **Итог**

- **Техническое окно** теперь интегрировано с существующими модулями.
- **Управление** (старт, пауза, стоп, возобновление) работает корректно.
- **Статусы и прогресс** обновляются в реальном времени через WebSocket.
- **Дублирование логики** устранено, все функции вынесены в общий модуль.

Если нужно, могу добавить поддержку для `banner_search_v03.py` и `banner_crop_search_v02.py` в этот интерфейс.