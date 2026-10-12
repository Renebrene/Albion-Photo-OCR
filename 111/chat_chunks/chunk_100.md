## СЕССИЯ: Технический раздел кнопки

**Создано:** 2026-08-16 19:16:59
**Обновлено:** 2026-08-22 20:21:24
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a81e277-f7b8-83ea-b0b2-cc6dab947d2d](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a81e277-f7b8-83ea-b0b2-cc6dab947d2d)

---

### 🤖 **Assistant** — 2026-08-16 21:39:44

Да. Теперь данных достаточно. Я бы сделал **«Система» живым мониторингом**, но без лишнего нагромождения.

Получим:

- CPU — текущая загрузка;
- RAM — `7.3 / 31 GB`;
- GPU — RTX 3060;
- GPU utilization;
- VRAM — `886 / 12288 MB`;
- диск `/` — `473 / 937 GB`;
- uptime;
- hostname;
- ОС;
- ZeroTier — состояние;
- приложение — состояние;
- автообновление примерно раз в 2 секунды.

И важный момент: **это должен быть backend-модуль**, а не выполнение `nvidia-smi` из браузера.

Давай сначала создадим отдельный мониторинг:

```bash id="5xk8mz"
cd ~/projects/scene_fingerprint_mvp_v02 && \
mkdir -p app/web/system && \
touch app/web/system/__init__.py && \
cat > app/web/system/monitor.py <<'PY'
import os
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path

def _read_cpu_times():
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()

        values = list(map(int, line.split()[1:]))

        idle = values[3]
        total = sum(values)

        return total, idle

    except Exception:
        return None, None

def cpu_percent(interval=0.2):
    total1, idle1 = _read_cpu_times()

    if total1 is None:
        return 0.0

    time.sleep(interval)

    total2, idle2 = _read_cpu_times()

    if total2 is None:
        return 0.0

    total_delta = total2 - total1
    idle_delta = idle2 - idle1

    if total_delta <= 0:
        return 0.0

    return round(
        100.0 * (1.0 - idle_delta / total_delta),
        1,
    )

def memory_info():
    try:
        data = {}

        with open("/proc/meminfo", "r") as f:
            for line in f:
                key, value = line.split(":", 1)
                data[key] = int(value.strip().split()[0])

        total = data.get("MemTotal", 0)
        available = data.get("MemAvailable", 0)

        used = total - available

        return {
            "total_gb": round(total / 1024 / 1024, 1),
            "used_gb": round(used / 1024 / 1024, 1),
            "available_gb": round(available / 1024 / 1024, 1),
            "percent": round(
                used / total * 100,
                1,
            ) if total else 0,
        }

    except Exception:
        return {
            "total_gb": 0,
            "used_gb": 0,
            "available_gb": 0,
            "percent": 0,
        }

def disk_info(path="/"):
    try:
        usage = shutil.disk_usage(path)

        return {
            "total_gb": round(
                usage.total / 1024**3,
                1,
            ),
            "used_gb": round(
                usage.used / 1024**3,
                1,
            ),
            "free_gb": round(
                usage.free / 1024**3,
                1,
            ),
            "percent": round(
                usage.used / usage.total * 100,
                1,
            ),
        }

    except Exception:
        return {
            "total_gb": 0,
            "used_gb": 0,
            "free_gb": 0,
            "percent": 0,
        }

def gpu_info():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,"
                "utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )

        if result.returncode != 0:
            return None

        line = result.stdout.strip().splitlines()[0]

        parts = [
            x.strip()
            for x in line.split(",")
        ]

        if len(parts) < 5:
            return None

        total = float(parts[1])
        used = float(parts[2])

        return {
            "name": parts[0],
            "vram_total_mb": int(total),
            "vram_used_mb": int(used),
            "vram_percent": round(
                used / total * 100,
                1,
            ) if total else 0,
            "utilization": int(parts[3]),
            "temperature": int(parts[4]),
        }

    except Exception:
        return None

def uptime():
    try:
        seconds = float(
            Path("/proc/uptime")
            .read_text()
            .split()[0]
        )

        seconds = int(seconds)

        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)

        if days:
            return f"{days} д {hours:02d}:{minutes:02d}"

        return f"{hours:02d}:{minutes:02d}"

    except Exception:
        return "—"

def zerotier_status():
    try:
        result = subprocess.run(
            [
                "systemctl",
                "is-active",
                "zerotier-one",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )

        return result.stdout.strip() == "active"

    except Exception:
        return False

def collect():
    gpu = gpu_info()

    return {
        "hostname": socket.gethostname(),
        "os": platform.platform(),
        "cpu": cpu_percent(),
        "memory": memory_info(),
        "disk": disk_info("/"),
        "gpu": gpu,
        "uptime": uptime(),
        "zerotier": zerotier_status(),
        "pid": os.getpid(),
    }
PY
```

После записи проверим **без запуска веб-интерфейса**:

```bash id="d5z7hw"
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -c "from app.web.system.monitor import collect; import pprint; pprint.pp(collect())"
```

У тебя должен получиться примерно такой объект:

```text
{
    'hostname': 'NEURO',
    'cpu': ...,
    'memory': {
        'total_gb': 31.0,
        'used_gb': ...,
        ...
    },
    'disk': {
        'total_gb': 937.0,
        ...
    },
    'gpu': {
        'name': 'NVIDIA GeForce RTX 3060',
        ...
    },
    'uptime': ...,
    'zerotier': True
}
```

**Сейчас только эти две команды.** Если монитор возвращает данные нормально — следующим шагом заменим твой `system.py` на компактное живое окно.

---

### 👤 **User** — 2026-08-16 21:40:05

температуры и скорость сети

---

### 🤖 **Assistant** — 2026-08-16 21:40:05

Да, обязательно добавим.

В **«Система»** я бы оставил:

- **CPU:** загрузка + температура CPU
- **GPU:** RTX 3060 + загрузка + температура
- **RAM:** занято / всего
- **VRAM:** занято / всего
- **Диск:** занято / всего
- **Сеть:** ↓ download / ↑ upload
- **Uptime**
- **ZeroTier**
- **LORA / Uvicorn**

Для сети лучше показывать **текущую скорость**, например:

`↓ 2.4 MB/s   ↑ 180 KB/s`

а не просто состояние интерфейса.

И температуру CPU надо получать отдельно — `nvidia-smi` даёт температуру GPU, но не CPU.

Так что следующим изменением расширим `monitor.py`: **CPU temperature + network RX/TX speed** с расчётом скорости между двумя замерами. Затем уже подключим это к красивому живому `system.py` с автообновлением.

---

### 👤 **User** — 2026-08-16 21:40:29

давай

---

### 🤖 **Assistant** — 2026-08-16 21:40:29

> **No analysis performed**
>
>
> **Reported no analysis performed**
>
> 
>
> Worked for a few seconds

Да. Добавим температуры и скорость сети в существующий `monitor.py`.

Сразу дам команду, которая **целиком заменит файл**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > app/web/system/monitor.py <<'PY'
import os
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path

# ============================================================
# CPU
# ============================================================

def _read_cpu_times():
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()

        values = list(map(int, line.split()[1:]))

        idle = values[3]
        total = sum(values)

        return total, idle

    except Exception:
        return None, None

def cpu_percent(interval=0.2):
    total1, idle1 = _read_cpu_times()

    if total1 is None:
        return 0.0

    time.sleep(interval)

    total2, idle2 = _read_cpu_times()

    if total2 is None:
        return 0.0

    total_delta = total2 - total1
    idle_delta = idle2 - idle1

    if total_delta <= 0:
        return 0.0

    return round(
        100.0 * (1.0 - idle_delta / total_delta),
        1,
    )

# ============================================================
# CPU TEMPERATURE
# ============================================================

def cpu_temperature():
    """
    Читает температуру CPU через /sys/class/thermal.
    Возвращает температуру в °C или None.
    """

    try:
        temperatures = []

        thermal_root = Path(
            "/sys/class/thermal"
        )

        for zone in thermal_root.glob(
            "thermal_zone*"
        ):

            temp_file = zone / "temp"

            if not temp_file.exists():
                continue

            try:
                value = int(
                    temp_file.read_text().strip()
                )

                # Linux обычно отдаёт millidegrees Celsius.
                temp = value / 1000.0

                if -20 < temp < 120:
                    temperatures.append(temp)

            except Exception:
                continue

        if not temperatures:
            return None

        # Берём максимальную температуру —
        # это полезнее для мониторинга нагрузки.
        return round(
            max(temperatures),
            1,
        )

    except Exception:
        return None

# ============================================================
# MEMORY
# ============================================================

def memory_info():
    try:
        data = {}

        with open("/proc/meminfo", "r") as f:
            for line in f:
                key, value = line.split(":", 1)
                data[key] = int(
                    value.strip().split()[0]
                )

        total = data.get(
            "MemTotal",
            0,
        )

        available = data.get(
            "MemAvailable",
            0,
        )

        used = total - available

        return {
            "total_gb": round(
                total / 1024 / 1024,
                1,
            ),
            "used_gb": round(
                used / 1024 / 1024,
                1,
            ),
            "available_gb": round(
                available / 1024 / 1024,
                1,
            ),
            "percent": round(
                used / total * 100,
                1,
            ) if total else 0,
        }

    except Exception:
        return {
            "total_gb": 0,
            "used_gb": 0,
            "available_gb": 0,
            "percent": 0,
        }

# ============================================================
# DISK
# ============================================================

def disk_info(path="/"):
    try:
        usage = shutil.disk_usage(path)

        return {
            "total_gb": round(
                usage.total / 1024**3,
                1,
            ),
            "used_gb": round(
                usage.used / 1024**3,
                1,
            ),
            "free_gb": round(
                usage.free / 1024**3,
                1,
            ),
            "percent": round(
                usage.used / usage.total * 100,
                1,
            ),
        }

    except Exception:
        return {
            "total_gb": 0,
            "used_gb": 0,
            "free_gb": 0,
            "percent": 0,
        }

# ============================================================
# GPU
# ============================================================

def gpu_info():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,"
                "utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )

        if result.returncode != 0:
            return None

        line = (
            result.stdout
            .strip()
            .splitlines()[0]
        )

        parts = [
            x.strip()
            for x in line.split(",")
        ]

        if len(parts) < 5:
            return None

        total = float(parts[1])
        used = float(parts[2])

        return {
            "name": parts[0],
            "vram_total_mb": int(total),
            "vram_used_mb": int(used),
            "vram_percent": round(
                used / total * 100,
                1,
            ) if total else 0,
            "utilization": int(parts[3]),
            "temperature": int(parts[4]),
        }

    except Exception:
        return None

# ============================================================
# NETWORK
# ============================================================

_network_previous = None
_network_previous_time = None

def _read_network_bytes():
    """
    Читает общий RX/TX по всем физическим интерфейсам,
    кроме loopback.
    """

    rx = 0
    tx = 0

    try:
        with open(
            "/proc/net/dev",
            "r",
        ) as f:

            for line in f:

                if ":" not in line:
                    continue

                interface, values = line.split(
                    ":",
                    1,
                )

                interface = interface.strip()

                if interface == "lo":
                    continue

                parts = values.split()

                if len(parts) < 9:
                    continue

                rx += int(parts[0])
                tx += int(parts[8])

        return rx, tx

    except Exception:
        return 0, 0

def network_speed():
    """
    Рассчитывает текущую скорость RX/TX
    между двумя измерениями.

    Возвращает bytes/sec.
    """

    global _network_previous
    global _network_previous_time

    rx, tx = _read_network_bytes()
    now = time.monotonic()

    if (
        _network_previous is None
        or _network_previous_time is None
    ):

        _network_previous = (
            rx,
            tx,
        )

        _network_previous_time = now

        return {
            "download_bps": 0,
            "upload_bps": 0,
        }

    elapsed = (
        now
        - _network_previous_time
    )

    if elapsed <= 0:
        return {
            "download_bps": 0,
            "upload_bps": 0,
        }

    previous_rx, previous_tx = (
        _network_previous
    )

    download = max(
        0,
        rx - previous_rx,
    ) / elapsed

    upload = max(
        0,
        tx - previous_tx,
    ) / elapsed

    _network_previous = (
        rx,
        tx,
    )

    _network_previous_time = now

    return {
        "download_bps": int(download),
        "upload_bps": int(upload),
    }

def format_speed(bytes_per_second):
    """
    Форматирует скорость:
    B/s → KB/s → MB/s → GB/s
    """

    value = float(
        bytes_per_second
    )

    if value < 1024:
        return f"{value:.0f} B/s"

    value /= 1024

    if value < 1024:
        return f"{value:.1f} KB/s"

    value /= 1024

    if value < 1024:
        return f"{value:.1f} MB/s"

    value /= 1024

    return f"{value:.2f} GB/s"

# ============================================================
# UPTIME
# ============================================================

def uptime():
    try:
        seconds = float(
            Path("/proc/uptime")
            .read_text()
            .split()[0]
        )

        seconds = int(seconds)

        days, seconds = divmod(
            seconds,
            86400,
        )

        hours, seconds = divmod(
            seconds,
            3600,
        )

        minutes, seconds = divmod(
            seconds,
            60,
        )

        if days:
            return (
                f"{days} д "
                f"{hours:02d}:"
                f"{minutes:02d}"
            )

        return (
            f"{hours:02d}:"
            f"{minutes:02d}"
        )

    except Exception:
        return "—"

# ============================================================
# ZEROTIER
# ============================================================

def zerotier_status():
    try:
        result = subprocess.run(
            [
                "systemctl",
                "is-active",
                "zerotier-one",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )

        return (
            result.stdout.strip()
            == "active"
        )

    except Exception:
        return False

# ============================================================
# COLLECT
# ============================================================

def collect():
    gpu = gpu_info()
    network = network_speed()

    return {
        "hostname": socket.gethostname(),
        "os": platform.platform(),

        "cpu": cpu_percent(),

        "cpu_temperature":
            cpu_temperature(),

        "memory":
            memory_info(),

        "disk":
            disk_info("/"),

        "gpu":
            gpu,

        "network":
            network,

        "network_download":
            format_speed(
                network["download_bps"]
            ),

        "network_upload":
            format_speed(
                network["upload_bps"]
            ),

        "uptime":
            uptime(),

        "zerotier":
            zerotier_status(),

        "pid":
            os.getpid(),
    }
PY
```

Теперь проверяем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -c "from app.web.system.monitor import collect; import pprint; pprint.pp(collect())"
```

**Важно:** при первом запуске скорость сети будет `0 B/s` — это нормально. Она появляется на следующем измерении.

После этого:

```bash
sleep 2 && \
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -c "from app.web.system.monitor import collect; import pprint; pprint.pp(collect())"
```

В результате должны появиться примерно такие поля:

```text
'cpu': 4.2,
'cpu_temperature': 48.0,

'gpu': {
    'name': 'NVIDIA GeForce RTX 3060',
    'vram_total_mb': 12288,
    'vram_used_mb': 886,
    'vram_percent': 7.2,
    'utilization': 0,
    'temperature': 42
},

'network': {
    'download_bps': ...,
    'upload_bps': ...
},

'network_download': '...',
'network_upload': '...'
```

После проверки подключим эти показатели непосредственно в **вкладку «Система»** и сделаем автообновление.

---

### 👤 **User** — 2026-08-16 21:41:21

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -c "from app.web.system.monitor import collect; import pprint; pprint.pp(collect())"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'app.web.system'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 21:41:22

Да, причина простая: каталога `app/web/system` у тебя, судя по всему, **не создалось** или команда записи не выполнилась целиком.

Сделаем аккуратно в два шага.

### 1. Создаём каталог

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
mkdir -p app/web/system && \
touch app/web/system/__init__.py && \
ls -la app/web/system
```

Должно показать:

```text
__init__.py
```

### 2. Проверяем, что Python видит пакет

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -c "import app.web.system; print('SYSTEM MODULE OK')"
```

Если получишь:

```text
SYSTEM MODULE OK
```

— всё нормально.

**После этого не будем заново вслепую вставлять огромный `monitor.py`.** Я дам отдельную команду именно для записи файла и затем сразу проверим CPU/GPU/температуры/сеть.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)

---
