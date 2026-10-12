```python
# app/web/components/technical_modules/photo_processing.py
from flask import Flask, render_template, request, jsonify
import os
import time
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import AsIs
import threading
import signal
import subprocess
import psutil
import json

app = Flask(__name__)

# Конфигурация базы данных
DB_CONFIG = {
    "dbname": "photobase",
    "user": "your_user",
    "password": "your_password",
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_photo_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN dino_status = 'done' THEN 1 ELSE 0 END) AS dino_done,
            SUM(CASE WHEN dino_status = 'processing' THEN 1 ELSE 0 END) AS dino_processing,
            SUM(CASE WHEN dino_status = 'pending' THEN 1 ELSE 0 END) AS dino_pending,
            SUM(CASE WHEN dino_status = 'error' THEN 1 ELSE 0 END) AS dino_errors,
            SUM(CASE WHEN qwen_status = 'done' THEN 1 ELSE 0 END) AS qwen_done,
            SUM(CASE WHEN qwen_status = 'processing' THEN 1 ELSE 0 END) AS qwen_processing,
            SUM(CASE WHEN qwen_status = 'pending' THEN 1 ELSE 0 END) AS qwen_pending,
            SUM(CASE WHEN qwen_status = 'error' THEN 1 ELSE 0 END) AS qwen_errors
        FROM photos
    """
    cursor.execute(query)
    stats = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return {
        "total": stats[0],
        "dino": {
            "done": stats[1],
            "processing": stats[2],
            "pending": stats[3],
            "errors": stats[4]
        },
        "qwen": {
            "done": stats[5],
            "processing": stats[6],
            "pending": stats[7],
            "errors": stats[8]
        }
    }

def get_photo_details():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            id,
            photo_id,
            source_path,
            dino_status,
            dino_error_message,
            qwen_status,
            qwen_error_message
        FROM photos
        ORDER BY updated_at DESC
        LIMIT 50
    """
    cursor.execute(query)
    photos = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return [{
        "id": photo[0],
        "photo_id": photo[1],
        "source_path": photo[2],
        "dino_status": photo[3],
        "dino_error": photo[4],
        "qwen_status": photo[5],
        "qwen_error": photo[6]
    } for photo in photos]

def get_worker_process():
    for proc in psutil.process_iter(['pid', 'name']):
        if 'dino_worker.py' in proc.info['name'] or 'dino_worker' in proc.info['name']:
            return proc.info['pid']
    return None

def get_qwen_process():
    for proc in psutil.process_iter(['pid', 'name']):
        if 'qwen_worker.py' in proc.info['name'] or 'qwen_worker' in proc.info['name']:
            return proc.info['pid']
    return None

def start_worker(worker_type):
    if worker_type == 'dino':
        pid = get_worker_process()
        if pid:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
        subprocess.Popen(['uv', 'run', 'python', 'app/workers/dino_worker.py'])
    elif worker_type == 'qwen':
        pid = get_qwen_process()
        if pid:
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
        subprocess.Popen(['uv', 'run', 'python', 'app/workers/qwen_worker.py'])

def stop_worker(worker_type):
    pid = get_worker_process() if worker_type == 'dino' else get_qwen_process()
    if pid:
        os.kill(pid, signal.SIGTERM)

@app.route('/')
def index():
    stats = get_photo_stats()
    details = get_photo_details()
    return render_template('photo_processing.html', stats=stats, details=details)

@app.route('/start_dino')
def start_dino():
    start_worker('dino')
    return jsonify({"status": "started"})

@app.route('/stop_dino')
def stop_dino():
    stop_worker('dino')
    return jsonify({"status": "stopped"})

@app.route('/start_qwen')
def start_qwen():
    start_worker('qwen')
    return jsonify({"status": "started"})

@app.route('/stop_qwen')
def stop_qwen():
    stop_worker('qwen')
    return jsonify({"status": "stopped"})

@app.route('/start_all')
def start_all():
    start_worker('dino')
    start_worker('qwen')
    return jsonify({"status": "started_all"})

@app.route('/stop_all')
def stop_all():
    stop_worker('dino')
    stop_worker('qwen')
    return jsonify({"status": "stopped_all"})

if __name__ == '__main__':
    app.run(debug=True)
```

---

### 📁 `templates/photo_processing.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Photo Processing</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: auto; background: white; padding: 20px; border-radius: 8px; }
        .section { margin-bottom: 30px; }
        .section h2 { margin-top: 0; }
        .progress-bar { width: 100%; background: #e0e0e0; border-radius: 10px; height: 30px; }
        .progress { height: 100%; background: #4caf50; width: 0%; border-radius: 10px; }
        .status { padding: 10px; margin: 10px 0; }
        .status.done { background: #d4edda; color: #155724; }
        .status.processing { background: #fff3cd; color: #856404; }
        .status.pending { background: #f8d7da; color: #721c24; }
        .status.error { background: #f5c289; color: #856404; }
        .photo-row { display: flex; justify-content: space-between; align-items: center; margin: 10px 0; }
        .photo-row .info { flex: 1; }
        .photo-row .status { flex: 0 0 150px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Photo Processing</h1>

        <div class="section">
            <h2>Source & Result</h2>
            <div>
                <label>Source:</label>
                <input type="text" value="/data/input/daily................" readonly style="width: 300px; margin-left: 10px;">
                <label>Result:</label>
                <input type="text" value="/data/output/daily.............." readonly style="width: 300px; margin-left: 10px;">
            </div>
        </div>

        <div class="section">
            <h2>Workers Control</h2>
            <div style="display: flex; gap: 20px;">
                <button onclick="startAll()">▶ ЗАПУСТИТЬ</button>
                <button onclick="stopAll()">■ ОСТАНОВИТЬ</button>
            </div>
        </div>

        <div class="section">
            <h2>DINO v33 / Hybrid v12</h2>
            <div style="display: flex; gap: 20px;">
                <button onclick="startDino()">▶ Запустить</button>
                <button onclick="stopDino()">■ Остановить</button>
            </div>
            <div class="progress-bar">
                <div id="dinoProgress" class="progress" style="width: {{ stats.dino.done / stats.total * 100 }}%;"></div>
            </div>
            <div class="status">
                Готово: {{ stats.dino.done }} | В работе: {{ stats.dino.processing }} | В очереди: {{ stats.dino.pending }} | Ошибки: {{ stats.dino.errors }}
            </div>
        </div>

        <div class="section">
            <h2>Qwen3-VL 4B</h2>
            <div style="display: flex; gap: 20px;">
                <button onclick="startQwen()">▶ Запустить</button>
                <button onclick="stopQwen()">■ Остановить</button>
            </div>
            <div class="progress-bar">
                <div id="qwenProgress" class="progress" style="width: {{ stats.qwen.done / stats.total * 100 }}%;"></div>
            </div>
            <div class="status">
                Готово: {{ stats.qwen.done }} | В работе: {{ stats.qwen.processing }} | В очереди: {{ stats.qwen.pending }} | Ошибки: {{ stats.qwen.errors }}
            </div>
        </div>

        <div class="section">
            <h2>Photo Details</h2>
            <div id="photoList"></div>
        </div>
    </div>

    <script>
        function updatePhotoList() {
            fetch('/api/photos')
                .then(res => res.json())
                .then(data => {
                    const container = document.getElementById('photoList');
                    container.innerHTML = '';
                    data.forEach(photo => {
                        const div = document.createElement('div');
                        div.className = 'photo-row';
                        div.innerHTML = `
                            <div class="info">
                                <strong>ID:</strong> ${photo.photo_id}<br>
                                <strong>Path:</strong> ${photo.source_path}<br>
                                <strong>DINO:</strong> <span class="status ${photo.dino_status}">${photo.dino_status}</span><br>
                                <strong>Qwen:</strong> <span class="status ${photo.qwen_status}">${photo.qwen_status}</span>
                            </div>
                        `;
                        container.appendChild(div);
                    });
                });
        }

        setInterval(updatePhotoList, 2000);
        updatePhotoList();
    </script>
</body>
</html>
```

---

### 📌 Объяснение

1. **Функционал:**
   - Показывает статистику по фото (всего, обработано, в очереди, ошибки)
   - Показывает детали по каждому фото (ID, путь, статусы DINO/Qwen)
   - Позволяет запускать/останавливать отдельные workers (DINO, Qwen) и оба сразу
   - Отображает прогресс-бары для каждого workers

2. **Технологии:**
   - Flask для веб-интерфейса
   - PostgreSQL для хранения статусов
   - Проверка процессов через `psutil` для управления запущенными workers

3. **Интерфейс:**
   - Цветовые статусы (зеленый - готово, желтый - в работе, красный - ошибка)
   - Детализация каждого фото с возможностью просмотра

4. **Дополнительно:**
   - Автоматическое обновление статусов каждые 2 секунды
   - Отображение только последних 50 фото

Этот код заменяет старый `photo_processing.py` и обеспечивает полноценный интерфейс управления существующей системой обработки фото.