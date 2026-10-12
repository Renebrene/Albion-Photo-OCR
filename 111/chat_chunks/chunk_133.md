## СЕССИЯ: вторник

**Создано:** 2026-08-18 18:12:03
**Обновлено:** 2026-08-22 20:16:20
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1)

---

### 👤 **User** — 2026-08-18 22:28:54

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

find app scripts -type f -name "*.py" -print | sort | \
grep -Ei 'qwen|worker'
app/pipeline/worker.py
app/web/components/technical_modules/qwen.py
app/workers/dino_worker.py
scripts/banner_qwen25vl_test_v01.py
scripts/banner_qwen4b_test_v01.py
scripts/import_qwen_to_db.py
scripts/qwen4b_output_v01_before_compact_prompt.py
scripts/qwen4b_output_v01.py
scripts/qwen_prompt_ablation.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,280p' app/pipeline/worker.py

echo
echo "================ QWEN MODULE ================"

sed -n '1,260p' app/web/components/technical_modules/qwen.py

echo
echo "================ QWEN REFERENCES ================"

grep -RniE "qwen_status|qwen4b|qwen3|ollama|Qwen|qwen" \
  app scripts \
  --include="*.py" | head -250
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.pipeline.queue import JobQueue

class FingerprintWorker:

    def __init__(self):
        self.queue = JobQueue(
            settings.data_dir / "jobs.db"
        )

        print("[Worker] Loading SceneEmbedder...")

        self.embedder = SceneEmbedder(
            settings
        )

        self.manager = FingerprintManager(
            settings,
            self.embedder,
        )

    def run_once(self):
        job = self.queue.claim()

        if job is None:
            return False

        job_id = job["id"]
        fingerprint_id = job["fingerprint_id"]
        source_folder = Path(
            job["source_folder"]
        )

        print()
        print("=" * 60)
        print(f"[Worker] Job {job_id}")
        print(f"[Worker] Fingerprint: {fingerprint_id}")
        print(f"[Worker] Folder: {source_folder}")
        print("=" * 60)

        try:
            self.manager.create(
                fingerprint_id,
                source_folder,
                self.embedder,
            )

            self.queue.complete(
                job_id
            )

            print(
                f"[Worker] DONE: {fingerprint_id}"
            )

            return True

        except Exception as exc:
            self.queue.fail(
                job_id,
                repr(exc),
            )

            print(
                f"[Worker] FAILED: "
                f"{fingerprint_id}: {exc}"
            )

            return True

    def run(self):
        print("[Worker] Starting batch processing")

        processed = 0

        while True:
            result = self.run_once()

            if not result:
                break

            processed += 1

        print()
        print("=" * 60)
        print(
            f"[Worker] Batch complete. "
            f"Processed: {processed}"
        )
        print("=" * 60)

def main():
    worker = FingerprintWorker()
    worker.run()

if __name__ == "__main__":
    main()

================ QWEN MODULE ================
import asyncio
import json
from pathlib import Path

from nicegui import ui

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"

QWEN_ROOT = (
    PROJECT
    / "data"
    / "metadata"
    / "qwen4b"
)

DAILY_ROOT = (
    PROJECT
    / "data"
    / "output"
    / "daily"
)

QWEN_SCRIPT = (
    PROJECT
    / "scripts"
    / "qwen4b_output_v01.py"
)

def _find_latest_summary():

    candidates = []

    root_summary = QWEN_ROOT / "summary.json"

    if root_summary.exists():
        candidates.append(root_summary)

    if QWEN_ROOT.exists():

        candidates.extend(
            p
            for p in QWEN_ROOT.glob("*/summary.json")
            if p.is_file()
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda p: p.stat().st_mtime,
    )

def _load_qwen_status():

    summary_path = _find_latest_summary()

    if summary_path is None:

        return {
            "state": "НЕТ ДАННЫХ",
            "processed": 0,
            "ok": 0,
            "skipped": 0,
            "errors": 0,
            "addresses": 0,
            "avg_time": 0.0,
            "avg_confidence": 0.0,
            "model": "Qwen3-VL 4B",
            "run": "—",
            "summary": None,
        }

    try:

        with open(
            summary_path,
            "r",
            encoding="utf-8",
        ) as f:

            summary = json.load(f)

        results = summary.get(
            "results",
            [],
        )

        if not isinstance(results, list):

            raise ValueError(
                "поле results отсутствует или имеет неверный формат"
            )

        ok_results = [
            x
            for x in results
            if x.get("status") == "ok"
        ]

        skipped_results = [
            x
            for x in results
            if x.get("status") == "skipped"
        ]

        error_results = [
            x
            for x in results
            if x.get("status") == "error"
        ]

        addresses = {
            x.get("address")
            for x in results
            if x.get("address")
        }

        times = [
            float(x["time_sec"])
            for x in ok_results
            if x.get("time_sec") is not None
        ]

        confidences = [
            float(x["confidence"])
            for x in ok_results
            if x.get("confidence") not in (
                None,
                "",
            )
        ]

        return {
            "state": "ГОТОВ",
            "processed": len(results),
            "ok": len(ok_results),
            "skipped": len(skipped_results),
            "errors": len(error_results),
            "addresses": len(addresses),
            "avg_time": (
                sum(times) / len(times)
                if times
                else 0.0
            ),
            "avg_confidence": (
                sum(confidences) / len(confidences)
                if confidences
                else 0.0
            ),
            "model": summary.get(
                "model",
                "Qwen3-VL 4B",
            ),
            "run": summary_path.parent.name,
            "summary": summary_path,
        }

    except Exception as exc:

        return {
            "state": "ОШИБКА ФОРМАТА",
            "processed": 0,
            "ok": 0,
            "skipped": 0,
            "errors": 0,
            "addresses": 0,
            "avg_time": 0.0,
            "avg_confidence": 0.0,
            "model": "Qwen3-VL 4B",
            "run": summary_path.parent.name,
            "summary": summary_path,
            "error": str(exc),
        }

def _find_latest_hybrid():

    if not DAILY_ROOT.exists():
        return None

    runs = [
        p
        for p in DAILY_ROOT.iterdir()
        if p.is_dir()
    ]

    if not runs:
        return None

    return max(
        runs,
        key=lambda p: p.name,
    )

def build_qwen():

    with ui.card().classes("w-full"):

        ui.label(
            "QWEN3-VL 4B"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            ui.label(
                "Анализ содержимого фотографий"
            ).classes(
                "text-base font-medium"
            )

            status_label = ui.label(
                "● НЕТ ДАННЫХ"
            ).classes(
                "text-sm"
            )

        with ui.grid(columns=2).classes(
            "w-full gap-2"
        ):

            ui.label("Статус")
            state_label = ui.label("—")

            ui.label("Последний запуск")
            run_label = ui.label("—")

            ui.label("Модель")
            model_label = ui.label("—")

            ui.label("Обработано")
            processed_label = ui.label("0")

            ui.label("OK")
            ok_label = ui.label("0")

            ui.label("Пропущено")
            skipped_label = ui.label("0")

            ui.label("Ошибок")
            errors_label = ui.label("0")

            ui.label("Адресов")
            addresses_label = ui.label("0")

            ui.label("Среднее время")
            avg_time_label = ui.label("0.00 сек")

            ui.label("Средняя уверенность")
            avg_confidence_label = ui.label("0.0%")

================ QWEN REFERENCES ================
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:59:            qwen_status,
app/web/components/search.py:60:            qwen_time_sec,
app/web/components/technical_modules/photo_processing.py:191:            # QWEN3-VL 4B
app/web/components/technical_modules/photo_processing.py:194:            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"
app/web/components/technical_modules/photo_processing.py:196:            if not qwen_script.exists():
app/web/components/technical_modules/photo_processing.py:199:                    "✓ Hybrid завершён → Qwen script не найден"
app/web/components/technical_modules/photo_processing.py:203:                    f"Не найден Qwen script: {qwen_script}",
app/web/components/technical_modules/photo_processing.py:214:            qwen_output = (
app/web/components/technical_modules/photo_processing.py:218:                / "qwen4b"
app/web/components/technical_modules/photo_processing.py:222:            qwen_output.mkdir(
app/web/components/technical_modules/photo_processing.py:228:                "▶ Qwen3-VL 4B: выполняется..."
app/web/components/technical_modules/photo_processing.py:233:                "Запускается Qwen3-VL 4B.",
app/web/components/technical_modules/photo_processing.py:240:                qwen_process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:242:                    str(qwen_script),
app/web/components/technical_modules/photo_processing.py:246:                    str(qwen_output),
app/web/components/technical_modules/photo_processing.py:252:                qwen_lines = []
app/web/components/technical_modules/photo_processing.py:256:                    line = await qwen_process.stdout.readline()
app/web/components/technical_modules/photo_processing.py:266:                    qwen_lines.append(text)
app/web/components/technical_modules/photo_processing.py:271:                qwen_returncode = await qwen_process.wait()
app/web/components/technical_modules/photo_processing.py:273:                if qwen_returncode != 0:
app/web/components/technical_modules/photo_processing.py:277:                        "Qwen3-VL 4B: ошибка"
app/web/components/technical_modules/photo_processing.py:282:                        "но Qwen3-VL 4B завершился с ошибкой.",
app/web/components/technical_modules/photo_processing.py:290:                    "✓ Hybrid v12 + Qwen3-VL 4B: готово"
app/web/components/technical_modules/photo_processing.py:299:                    "Hybrid v12 + Qwen3-VL 4B.",
app/web/components/technical_modules/photo_processing.py:304:            except Exception as qwen_error:
app/web/components/technical_modules/photo_processing.py:308:                    "Qwen3-VL 4B: ошибка запуска"
app/web/components/technical_modules/photo_processing.py:312:                    f"Ошибка запуска Qwen: {qwen_error}",
app/web/components/technical_modules/photo_processing.py:384:            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
app/web/components/technical_modules/data.py:13:QWEN_ROOT = PROJECT / "data" / "metadata" / "qwen4b"
app/web/components/technical_modules/data.py:78:def qwen_stats():
app/web/components/technical_modules/data.py:80:    Статистика Qwen3-VL 4B.
app/web/components/technical_modules/data.py:90:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/data.py:95:    if QWEN_ROOT.exists():
app/web/components/technical_modules/data.py:98:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/data.py:243:    qwen = qwen_stats()
app/web/components/technical_modules/data.py:368:        # QWEN
app/web/components/technical_modules/data.py:378:                    "Qwen3-VL 4B"
app/web/components/technical_modules/data.py:389:            qwen_color = (
app/web/components/technical_modules/data.py:391:                if qwen["status"] == "ГОТОВ"
app/web/components/technical_modules/data.py:396:                qwen["status"],
app/web/components/technical_modules/data.py:397:                color=qwen_color,
app/web/components/technical_modules/data.py:405:                f"Обработано: {qwen['photos']}"
app/web/components/technical_modules/data.py:409:                f"OK: {qwen['ok']}"
app/web/components/technical_modules/data.py:413:                f"Ошибок: {qwen['errors']}"
app/web/components/technical_modules/data.py:417:                f"Адресов: {qwen['addresses']}"
app/web/components/technical_modules/data.py:421:                f"Среднее время: {qwen['avg_time']:.2f} сек"
app/web/components/technical_modules/data.py:425:                f"Средняя уверенность: {qwen['avg_confidence']:.1f}%"
app/web/components/technical_modules/qwen.py:10:QWEN_ROOT = (
app/web/components/technical_modules/qwen.py:14:    / "qwen4b"
app/web/components/technical_modules/qwen.py:24:QWEN_SCRIPT = (
app/web/components/technical_modules/qwen.py:27:    / "qwen4b_output_v01.py"
app/web/components/technical_modules/qwen.py:35:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/qwen.py:40:    if QWEN_ROOT.exists():
app/web/components/technical_modules/qwen.py:44:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/qwen.py:57:def _load_qwen_status():
app/web/components/technical_modules/qwen.py:72:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:156:                "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:173:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:200:def build_qwen():
app/web/components/technical_modules/qwen.py:205:            "QWEN3-VL 4B"
app/web/components/technical_modules/qwen.py:269:                "▶ Запустить Qwen",
app/web/components/technical_modules/qwen.py:275:                "■ Остановить Qwen",
app/web/components/technical_modules/qwen.py:294:    qwen_process = None
app/web/components/technical_modules/qwen.py:295:    qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:297:    async def stop_qwen():
app/web/components/technical_modules/qwen.py:298:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:299:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:301:        if qwen_process is None:
app/web/components/technical_modules/qwen.py:304:        qwen_stop_requested = True
app/web/components/technical_modules/qwen.py:307:            f"[QWEN MANUAL] STOP REQUESTED PID={qwen_process.pid}",
app/web/components/technical_modules/qwen.py:312:            qwen_process.terminate()
app/web/components/technical_modules/qwen.py:317:                f"[QWEN MANUAL] STOP FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:321:    async def run_qwen():
app/web/components/technical_modules/qwen.py:323:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:324:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:326:        print("[QWEN MANUAL] START", flush=True)
app/web/components/technical_modules/qwen.py:328:        qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:335:            if not QWEN_SCRIPT.exists():
app/web/components/technical_modules/qwen.py:338:                    f"[QWEN MANUAL] SCRIPT NOT FOUND: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:343:                    f"Не найден Qwen script: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:355:                    "[QWEN MANUAL] HYBRID RUN NOT FOUND",
app/web/components/technical_modules/qwen.py:382:                    f"[QWEN MANUAL] NO IMAGES: {result_dir}",
app/web/components/technical_modules/qwen.py:396:            qwen_output = QWEN_ROOT / run_name
app/web/components/technical_modules/qwen.py:397:            qwen_output.mkdir(
app/web/components/technical_modules/qwen.py:403:                f"[QWEN MANUAL] INPUT: {result_dir}",
app/web/components/technical_modules/qwen.py:408:                f"[QWEN MANUAL] OUTPUT: {qwen_output}",
app/web/components/technical_modules/qwen.py:413:                f"[QWEN MANUAL] IMAGES: {total_images}",
app/web/components/technical_modules/qwen.py:420:            model_label.text = "qwen3-vl:4b-instruct"
app/web/components/technical_modules/qwen.py:435:                f"Запуск Qwen3-VL 4B: {total_images} фото",
app/web/components/technical_modules/qwen.py:447:                str(QWEN_SCRIPT),
app/web/components/technical_modules/qwen.py:451:                str(qwen_output),
app/web/components/technical_modules/qwen.py:457:            qwen_process = process
app/web/components/technical_modules/qwen.py:460:                f"[QWEN MANUAL] PID: {process.pid}",
app/web/components/technical_modules/qwen.py:488:                    f"[QWEN] {text}",
app/web/components/technical_modules/qwen.py:530:                if "[QWEN] OK |" in text:
app/web/components/technical_modules/qwen.py:580:                    "[QWEN] ERROR" in text
app/web/components/technical_modules/qwen.py:581:                    or "[QWEN] FAILED" in text
app/web/components/technical_modules/qwen.py:617:                if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:627:                f"[QWEN MANUAL] FINISHED "
app/web/components/technical_modules/qwen.py:632:            if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:638:                    f"Qwen остановлен: "
app/web/components/technical_modules/qwen.py:650:                    "✓ Qwen3-VL 4B завершён",
app/web/components/technical_modules/qwen.py:660:                status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:663:                    f"Qwen завершился с ошибкой: {returncode}",
app/web/components/technical_modules/qwen.py:671:                f"[QWEN MANUAL] EXCEPTION: {exc!r}",
app/web/components/technical_modules/qwen.py:676:            status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:680:                    f"Ошибка запуска Qwen: {exc}",
app/web/components/technical_modules/qwen.py:689:            qwen_process = None
app/web/components/technical_modules/qwen.py:690:            qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:706:                    f"[QWEN MANUAL] UI REFRESH FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:712:        data = _load_qwen_status()
app/web/components/technical_modules/qwen.py:772:    run_button.on_click(run_qwen)
app/web/components/technical_modules/qwen.py:773:    stop_button.on_click(stop_qwen)
app/web/components/photos.py:445:                        if value("qwen_status") != "—":
app/web/components/photos.py:448:                                f"Qwen: {value('qwen_status')}"
app/web/components/photos.py:1234:                                # QWEN DESCRIPTION
app/web/components/technical.py:12:from app.web.components.technical_modules.qwen import (
app/web/components/technical.py:13:    build_qwen,
app/web/components/technical.py:175:                    "qwen",
app/web/components/technical.py:176:                    label="Qwen",
app/web/components/technical.py:230:                    with ui.tab_panel("qwen"):
app/web/components/technical.py:231:                        build_qwen()
app/web/client_aliases.py:4:Qwen может распознавать одно и то же название с ошибками,
app/web/photo_db.py:28:            qwen_status,
app/web/photo_db.py:29:            qwen_time_sec,
app/web_v01_backup_20260816_142053/components/technical.py:84:                    "Qwen3-VL 4B",
app/web_v01_backup_20260816_142053/components/technical.py:85:                    "Qwen2.5-VL 3B",
app/web_v01_backup_20260816_142053/components/technical.py:86:                    "Qwen3-VL 2B",
app/web_v01_backup_20260816_142053/components/technical.py:88:                value="Qwen3-VL 4B",
scripts/banner_model_compare_v04.py:19:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v04.py:20:    "qwen2.5vl:3b",
scripts/banner_model_compare_v04.py:23:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v04.py:135:        OLLAMA_URL,
scripts/banner_qwen25vl_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen25vl_test_v01")
scripts/banner_qwen25vl_test_v01.py:14:MODEL = "qwen2.5vl:3b"
scripts/banner_qwen25vl_test_v01.py:16:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_qwen25vl_test_v01.py:104:        OLLAMA_URL,
scripts/banner_qwen25vl_test_v01.py:159:    print("QWEN2.5-VL 3B TEST")
scripts/banner_model_compare_v05.py:16:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v05.py:17:    "qwen2.5vl:3b",
scripts/banner_model_compare_v05.py:20:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v05.py:113:        OLLAMA_URL,
scripts/banner_llm_full_v02.py:11:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_llm_full_v02.py:109:    print("Sending to Ollama...")
scripts/banner_llm_full_v02.py:141:    print("QWEN3-VL BANNER TEST")
scripts/photo_ingest.py:131:    Никаких DINO/Qwen/сортировок здесь нет.
scripts/photo_ingest.py:151:                qwen_status,
scripts/import_qwen_to_db.py:10:QWEN_DIR = PROJECT / "data/metadata/qwen4b"
scripts/import_qwen_to_db.py:53:            qwen_status TEXT,
scripts/import_qwen_to_db.py:54:            qwen_time_sec REAL,
scripts/import_qwen_to_db.py:90:        ON photos(qwen_status)
scripts/import_qwen_to_db.py:114:    relative = json_path.relative_to(QWEN_DIR)
scripts/import_qwen_to_db.py:178:            qwen_status,
scripts/import_qwen_to_db.py:179:            qwen_time_sec,
scripts/import_qwen_to_db.py:216:            qwen_status = excluded.qwen_status,
scripts/import_qwen_to_db.py:217:            qwen_time_sec = excluded.qwen_time_sec,
scripts/import_qwen_to_db.py:264:    QWEN_DIR.mkdir(
scripts/import_qwen_to_db.py:275:        QWEN_DIR.rglob("*.json")
scripts/import_qwen_to_db.py:279:    print("QWEN → SQLITE")
scripts/import_qwen_to_db.py:283:    print("QWEN DIR:", QWEN_DIR)
scripts/banner_qwen4b_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen4b_test_v01")
scripts/banner_qwen4b_test_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_qwen4b_test_v01.py:16:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_qwen4b_test_v01.py:104:        OLLAMA_URL,
scripts/banner_qwen4b_test_v01.py:159:    print("QWEN3-VL 4B TEST")
scripts/banner_llm_folder_search_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01_before_compact_prompt.py:15:OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"
scripts/qwen4b_output_v01_before_compact_prompt.py:17:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01_before_compact_prompt.py:18:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/qwen4b_output_v01_before_compact_prompt.py:351:        OLLAMA_URL,
scripts/qwen4b_output_v01_before_compact_prompt.py:363:    # Ollama performance diagnostics
scripts/qwen4b_output_v01_before_compact_prompt.py:386:        "[OLLAMA]",
scripts/qwen4b_output_v01_before_compact_prompt.py:649:    print("QWEN3-VL 4B — OUTPUT ANALYSIS")
scripts/qwen4b_output_v01.py:15:OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"
scripts/qwen4b_output_v01.py:17:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01.py:18:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/qwen4b_output_v01.py:167:            OLLAMA_URL,
scripts/qwen4b_output_v01.py:201:            "[OLLAMA]",
scripts/qwen4b_output_v01.py:228:                    "[QWEN RETRY]",
scripts/qwen4b_output_v01.py:242:                "[QWEN JSON ERROR]",
scripts/qwen4b_output_v01.py:525:        help="Output directory for Qwen metadata"
scripts/qwen4b_output_v01.py:536:    print("QWEN3-VL 4B — OUTPUT ANALYSIS")
scripts/banner_llm_full_v01.py:9:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_model_compare_v02.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v02.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v02.py:27:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v02.py:98:        OLLAMA_URL,
scripts/banner_model_compare_v01.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v01.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v01.py:28:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v01.py:103:        OLLAMA_URL,
scripts/banner_database_v02.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/migrate_sqlite_to_postgres.py:75:                qwen_status,
scripts/migrate_sqlite_to_postgres.py:76:                qwen_time_sec,
scripts/migrate_sqlite_to_postgres.py:111:                row["qwen_status"],
scripts/migrate_sqlite_to_postgres.py:112:                row["qwen_time_sec"],
scripts/migrate_sqlite_to_postgres.py:165:                    qwen_status,
scripts/migrate_sqlite_to_postgres.py:166:                    qwen_time_sec,
scripts/banner_database_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/llm_resolver_v01.py:11:MODEL = "qwen3:4b"
scripts/llm_resolver_v01.py:168:            "ollama",
scripts/llm_resolver_v01.py:224:        print("--- QWEN3:4B ---")
scripts/qwen_prompt_ablation.py:15:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen_prompt_ablation.py:16:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/qwen_prompt_ablation.py:162:            OLLAMA_URL,
scripts/qwen_prompt_ablation.py:193:        print("OLLAMA TOTAL:    ", round(stats["total"], 2), "sec")
scripts/qwen_prompt_ablation.py:218:    print("QWEN3-VL 4B — PROMPT ABLATION TEST")
scripts/banner_model_compare_v03.py:19:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v03.py:20:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v03.py:23:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v03.py:116:        OLLAMA_URL,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:28:58

Да. Теперь картина ясная.

У нас **Qwen уже действительно отдельный процесс**, привязанный к кнопке в «Технические → Qwen». Это хорошо: его не нужно смешивать с DINO.

Но сейчас архитектура ещё не соответствует нашей целевой схеме.

### Целевая схема

```text
                    НОВЫЕ ФОТО
                         │
                         ▼
                PostgreSQL / photos
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        DINO WORKER             QWEN WORKER
          CPU only                GPU only
              │                     │
              │                     │
      fingerprint/address      description/status
      score/margin/status           │
              │                     │
              └──────────┬──────────┘
                         ▼
                   PostgreSQL
                         │
                         ▼
                 ВИРТУАЛЬНЫЙ GRID
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
       фото уже есть            описание Qwen
       сразу после DINO         появляется позже
```

Именно это нам и нужно.

### Что уже есть

**DINO:**
- берёт `pending`;
- ставит `processing`;
- распознаёт;
- пишет `dino_fingerprint`, `dino_score`, `dino_margin`;
- ставит `done`;
- работает на CPU;
- сейчас около **0.35–0.55 сек/фото**, при загрузке CPU примерно до 25%.

**Qwen:**
- отдельный запуск;
- отдельный процесс;
- запускается кнопкой;
- работает через Ollama;
- GPU остаётся за ним;
- результаты уже имеют `qwen_status`, `qwen_time_sec` и т.д.

То есть **разделение ресурсов уже получилось**.

### Чего сейчас не хватает

Главное — сделать Qwen не «пакетным анализатором последнего запуска», а **вторым независимым потребителем очереди фотографий**.

Тогда не будет:

```text
DINO → закончить все 526 → Qwen → обработать 526
```

а будет:

```text
DINO:
526 → 525 → 524 → 523 → ...

Qwen:
             526 → 525 → 524 → ...
```

Причём Qwen должен брать **только фотографии, у которых DINO уже определил адрес**.

И тогда Grid сможет работать вообще без ожидания завершения обоих процессов:

```text
фото 526
   ↓
DINO
   ↓
94_v33
   ↓
GRID показывает фото в группе 94
   ↓
Qwen ещё думает...
   ↓
Qwen готов
   ↓
описание появляется у этого же фото
```

Это как раз соответствует твоей идее: **сначала максимально быстро получить структуру фотобазы через DINO, затем постепенно обогащать её Qwen.**

---

### И ещё важный момент

Не надо делать 2–4 процесса DINO.

При нашей текущей цели лучше:

**1 DINO CPU worker + 1 Qwen GPU worker.**

DINO сейчас потребляет примерно 25% CPU, поэтому у нас остаётся большой запас для веб-интерфейса, PostgreSQL, подготовки изображений и прочего.

А RTX 3060 остаётся практически полностью свободной для Qwen.

Следующий правильный шаг — **переделать именно очередь Qwen**, не трогая уже работающий DINO. Тогда мы сможем запустить оба одновременно и посмотреть реальную картину:

- DINO → адреса в БД;
- Grid → показывает их сразу;
- Qwen → постепенно заполняет описания;
- CPU остаётся ограниченным;
- GPU занимается только Qwen.

---

### 👤 **User** — 2026-08-18 22:29:53

мы уже сдеали 2 процесса дино - проверим 2 дино + квекн и 1 дино+ квен в праллели

---

### 🤖 **Assistant** — 2026-08-18 22:29:59

Да. Тогда сейчас **ничего не меняем в коде**, а делаем чистый сравнительный замер:

1. **1 DINO + Qwen**
2. **2 DINO + Qwen**

На одних и тех же 526 фото.

### Важный момент

Qwen у нас запускается **кнопкой в веб-интерфейсе**, поэтому замеряем реальную работу именно в этой конфигурации, а не отдельный тестовый скрипт.

---

## Тест №1 — 1 DINO + Qwen

Сначала очистить состояния DINO для тестовых 526:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "UPDATE photos SET dino_status='pending', dino_fingerprint=NULL, dino_score=NULL, dino_second_score=NULL, dino_margin=NULL, dino_time_sec=NULL, error_message=NULL, updated_at=CURRENT_TIMESTAMP;"
```

Проверяем:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT dino_status, count(*) FROM photos GROUP BY dino_status ORDER BY dino_status;"
```

Должно быть примерно:

```text
 pending | 526
```

### Терминал №1 — DINO

```bash
cd ~/projects/scene_fingerprint_mvp_v02
time uv run python app/workers/dino_worker.py
```

### Сразу после запуска DINO

В веб-интерфейсе:

**Технические → Qwen → Запустить Qwen**

И одновременно смотрим:

```bash
watch -n 2 '
psql -X -P pager=off -h localhost -p 5432 -U lora -d photobase \
-c "SELECT dino_status, count(*) FROM photos GROUP BY dino_status ORDER BY dino_status;"
'
```

И отдельно:

```bash
watch -n 2 'nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader'
```

---

## Тест №2 — 2 DINO + Qwen

Опять сбрасываем DINO:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "UPDATE photos SET dino_status='pending', dino_fingerprint=NULL, dino_score=NULL, dino_second_score=NULL, dino_margin=NULL, dino_time_sec=NULL, error_message=NULL, updated_at=CURRENT_TIMESTAMP;"
```

Проверяем:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT dino_status, count(*) FROM photos GROUP BY dino_status ORDER BY dino_status;"
```

### Терминал №1

```bash
cd ~/projects/scene_fingerprint_mvp_v02
time uv run python app/workers/dino_worker.py
```

### Терминал №2 — второй DINO

**сразу же:**

```bash
cd ~/projects/scene_fingerprint_mvp_v02
time uv run python app/workers/dino_worker.py
```

`FOR UPDATE SKIP LOCKED` уже позволяет им безопасно делить очередь — один DINO забирает одну фотографию, второй другую.

### И одновременно

Запускаем Qwen кнопкой:

**Технические → Qwen → Запустить Qwen**

---

## Что сравниваем

Нам сейчас интересны не только `real time`.

| Показатель | 1 DINO + Qwen | 2 DINO + Qwen |
|---|---:|---:|
| Общее время 526 фото | ? | ? |
| DINO время | ? | ? |
| Среднее DINO/фото | ? | ? |
| Qwen время | ? | ? |
| CPU загрузка | ? | ? |
| GPU загрузка | ? | ? |
| VRAM | ? | ? |
| Когда Grid начинает заполняться | ? | ? |

И **особенно важен один показатель**:

> **через сколько секунд после старта начинает появляться поток готовых фотографий в Grid.**

Потому что наша цель теперь не просто «закончить 526 быстрее».

Нам нужна именно такая конвейерная работа:

```text
DINO-1 ─┐
        ├──► PostgreSQL ──► GRID ──► фото появляется
DINO-2 ─┘                       │
                                │
                                ▼
                           Qwen → описание
```

Если два DINO дадут, например, условно 2× скорость, но начнут сильно мешать Qwen по CPU/подготовке изображений — оставляем один.

Если **2 DINO почти удваивают throughput и Qwen при этом продолжает нормально использовать GPU**, тогда это будет наш оптимальный режим.

**Пока код не трогаем. Сначала получаем эти два замера.**

---

### 👤 **User** — 2026-08-18 22:30:04

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

find app scripts -type f -name "*.py" -print | sort | \
grep -Ei 'qwen|worker'
app/pipeline/worker.py
app/web/components/technical_modules/qwen.py
app/workers/dino_worker.py
scripts/banner_qwen25vl_test_v01.py
scripts/banner_qwen4b_test_v01.py
scripts/import_qwen_to_db.py
scripts/qwen4b_output_v01_before_compact_prompt.py
scripts/qwen4b_output_v01.py
scripts/qwen_prompt_ablation.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,280p' app/pipeline/worker.py

echo
echo "================ QWEN MODULE ================"

sed -n '1,260p' app/web/components/technical_modules/qwen.py

echo
echo "================ QWEN REFERENCES ================"

grep -RniE "qwen_status|qwen4b|qwen3|ollama|Qwen|qwen" \
  app scripts \
  --include="*.py" | head -250
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.pipeline.queue import JobQueue

class FingerprintWorker:

    def __init__(self):
        self.queue = JobQueue(
            settings.data_dir / "jobs.db"
        )

        print("[Worker] Loading SceneEmbedder...")

        self.embedder = SceneEmbedder(
            settings
        )

        self.manager = FingerprintManager(
            settings,
            self.embedder,
        )

    def run_once(self):
        job = self.queue.claim()

        if job is None:
            return False

        job_id = job["id"]
        fingerprint_id = job["fingerprint_id"]
        source_folder = Path(
            job["source_folder"]
        )

        print()
        print("=" * 60)
        print(f"[Worker] Job {job_id}")
        print(f"[Worker] Fingerprint: {fingerprint_id}")
        print(f"[Worker] Folder: {source_folder}")
        print("=" * 60)

        try:
            self.manager.create(
                fingerprint_id,
                source_folder,
                self.embedder,
            )

            self.queue.complete(
                job_id
            )

            print(
                f"[Worker] DONE: {fingerprint_id}"
            )

            return True

        except Exception as exc:
            self.queue.fail(
                job_id,
                repr(exc),
            )

            print(
                f"[Worker] FAILED: "
                f"{fingerprint_id}: {exc}"
            )

            return True

    def run(self):
        print("[Worker] Starting batch processing")

        processed = 0

        while True:
            result = self.run_once()

            if not result:
                break

            processed += 1

        print()
        print("=" * 60)
        print(
            f"[Worker] Batch complete. "
            f"Processed: {processed}"
        )
        print("=" * 60)

def main():
    worker = FingerprintWorker()
    worker.run()

if __name__ == "__main__":
    main()

================ QWEN MODULE ================
import asyncio
import json
from pathlib import Path

from nicegui import ui

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"

QWEN_ROOT = (
    PROJECT
    / "data"
    / "metadata"
    / "qwen4b"
)

DAILY_ROOT = (
    PROJECT
    / "data"
    / "output"
    / "daily"
)

QWEN_SCRIPT = (
    PROJECT
    / "scripts"
    / "qwen4b_output_v01.py"
)

def _find_latest_summary():

    candidates = []

    root_summary = QWEN_ROOT / "summary.json"

    if root_summary.exists():
        candidates.append(root_summary)

    if QWEN_ROOT.exists():

        candidates.extend(
            p
            for p in QWEN_ROOT.glob("*/summary.json")
            if p.is_file()
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda p: p.stat().st_mtime,
    )

def _load_qwen_status():

    summary_path = _find_latest_summary()

    if summary_path is None:

        return {
            "state": "НЕТ ДАННЫХ",
            "processed": 0,
            "ok": 0,
            "skipped": 0,
            "errors": 0,
            "addresses": 0,
            "avg_time": 0.0,
            "avg_confidence": 0.0,
            "model": "Qwen3-VL 4B",
            "run": "—",
            "summary": None,
        }

    try:

        with open(
            summary_path,
            "r",
            encoding="utf-8",
        ) as f:

            summary = json.load(f)

        results = summary.get(
            "results",
            [],
        )

        if not isinstance(results, list):

            raise ValueError(
                "поле results отсутствует или имеет неверный формат"
            )

        ok_results = [
            x
            for x in results
            if x.get("status") == "ok"
        ]

        skipped_results = [
            x
            for x in results
            if x.get("status") == "skipped"
        ]

        error_results = [
            x
            for x in results
            if x.get("status") == "error"
        ]

        addresses = {
            x.get("address")
            for x in results
            if x.get("address")
        }

        times = [
            float(x["time_sec"])
            for x in ok_results
            if x.get("time_sec") is not None
        ]

        confidences = [
            float(x["confidence"])
            for x in ok_results
            if x.get("confidence") not in (
                None,
                "",
            )
        ]

        return {
            "state": "ГОТОВ",
            "processed": len(results),
            "ok": len(ok_results),
            "skipped": len(skipped_results),
            "errors": len(error_results),
            "addresses": len(addresses),
            "avg_time": (
                sum(times) / len(times)
                if times
                else 0.0
            ),
            "avg_confidence": (
                sum(confidences) / len(confidences)
                if confidences
                else 0.0
            ),
            "model": summary.get(
                "model",
                "Qwen3-VL 4B",
            ),
            "run": summary_path.parent.name,
            "summary": summary_path,
        }

    except Exception as exc:

        return {
            "state": "ОШИБКА ФОРМАТА",
            "processed": 0,
            "ok": 0,
            "skipped": 0,
            "errors": 0,
            "addresses": 0,
            "avg_time": 0.0,
            "avg_confidence": 0.0,
            "model": "Qwen3-VL 4B",
            "run": summary_path.parent.name,
            "summary": summary_path,
            "error": str(exc),
        }

def _find_latest_hybrid():

    if not DAILY_ROOT.exists():
        return None

    runs = [
        p
        for p in DAILY_ROOT.iterdir()
        if p.is_dir()
    ]

    if not runs:
        return None

    return max(
        runs,
        key=lambda p: p.name,
    )

def build_qwen():

    with ui.card().classes("w-full"):

        ui.label(
            "QWEN3-VL 4B"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            ui.label(
                "Анализ содержимого фотографий"
            ).classes(
                "text-base font-medium"
            )

            status_label = ui.label(
                "● НЕТ ДАННЫХ"
            ).classes(
                "text-sm"
            )

        with ui.grid(columns=2).classes(
            "w-full gap-2"
        ):

            ui.label("Статус")
            state_label = ui.label("—")

            ui.label("Последний запуск")
            run_label = ui.label("—")

            ui.label("Модель")
            model_label = ui.label("—")

            ui.label("Обработано")
            processed_label = ui.label("0")

            ui.label("OK")
            ok_label = ui.label("0")

            ui.label("Пропущено")
            skipped_label = ui.label("0")

            ui.label("Ошибок")
            errors_label = ui.label("0")

            ui.label("Адресов")
            addresses_label = ui.label("0")

            ui.label("Среднее время")
            avg_time_label = ui.label("0.00 сек")

            ui.label("Средняя уверенность")
            avg_confidence_label = ui.label("0.0%")

================ QWEN REFERENCES ================
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:59:            qwen_status,
app/web/components/search.py:60:            qwen_time_sec,
app/web/components/technical_modules/photo_processing.py:191:            # QWEN3-VL 4B
app/web/components/technical_modules/photo_processing.py:194:            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"
app/web/components/technical_modules/photo_processing.py:196:            if not qwen_script.exists():
app/web/components/technical_modules/photo_processing.py:199:                    "✓ Hybrid завершён → Qwen script не найден"
app/web/components/technical_modules/photo_processing.py:203:                    f"Не найден Qwen script: {qwen_script}",
app/web/components/technical_modules/photo_processing.py:214:            qwen_output = (
app/web/components/technical_modules/photo_processing.py:218:                / "qwen4b"
app/web/components/technical_modules/photo_processing.py:222:            qwen_output.mkdir(
app/web/components/technical_modules/photo_processing.py:228:                "▶ Qwen3-VL 4B: выполняется..."
app/web/components/technical_modules/photo_processing.py:233:                "Запускается Qwen3-VL 4B.",
app/web/components/technical_modules/photo_processing.py:240:                qwen_process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:242:                    str(qwen_script),
app/web/components/technical_modules/photo_processing.py:246:                    str(qwen_output),
app/web/components/technical_modules/photo_processing.py:252:                qwen_lines = []
app/web/components/technical_modules/photo_processing.py:256:                    line = await qwen_process.stdout.readline()
app/web/components/technical_modules/photo_processing.py:266:                    qwen_lines.append(text)
app/web/components/technical_modules/photo_processing.py:271:                qwen_returncode = await qwen_process.wait()
app/web/components/technical_modules/photo_processing.py:273:                if qwen_returncode != 0:
app/web/components/technical_modules/photo_processing.py:277:                        "Qwen3-VL 4B: ошибка"
app/web/components/technical_modules/photo_processing.py:282:                        "но Qwen3-VL 4B завершился с ошибкой.",
app/web/components/technical_modules/photo_processing.py:290:                    "✓ Hybrid v12 + Qwen3-VL 4B: готово"
app/web/components/technical_modules/photo_processing.py:299:                    "Hybrid v12 + Qwen3-VL 4B.",
app/web/components/technical_modules/photo_processing.py:304:            except Exception as qwen_error:
app/web/components/technical_modules/photo_processing.py:308:                    "Qwen3-VL 4B: ошибка запуска"
app/web/components/technical_modules/photo_processing.py:312:                    f"Ошибка запуска Qwen: {qwen_error}",
app/web/components/technical_modules/photo_processing.py:384:            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
app/web/components/technical_modules/data.py:13:QWEN_ROOT = PROJECT / "data" / "metadata" / "qwen4b"
app/web/components/technical_modules/data.py:78:def qwen_stats():
app/web/components/technical_modules/data.py:80:    Статистика Qwen3-VL 4B.
app/web/components/technical_modules/data.py:90:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/data.py:95:    if QWEN_ROOT.exists():
app/web/components/technical_modules/data.py:98:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/data.py:243:    qwen = qwen_stats()
app/web/components/technical_modules/data.py:368:        # QWEN
app/web/components/technical_modules/data.py:378:                    "Qwen3-VL 4B"
app/web/components/technical_modules/data.py:389:            qwen_color = (
app/web/components/technical_modules/data.py:391:                if qwen["status"] == "ГОТОВ"
app/web/components/technical_modules/data.py:396:                qwen["status"],
app/web/components/technical_modules/data.py:397:                color=qwen_color,
app/web/components/technical_modules/data.py:405:                f"Обработано: {qwen['photos']}"
app/web/components/technical_modules/data.py:409:                f"OK: {qwen['ok']}"
app/web/components/technical_modules/data.py:413:                f"Ошибок: {qwen['errors']}"
app/web/components/technical_modules/data.py:417:                f"Адресов: {qwen['addresses']}"
app/web/components/technical_modules/data.py:421:                f"Среднее время: {qwen['avg_time']:.2f} сек"
app/web/components/technical_modules/data.py:425:                f"Средняя уверенность: {qwen['avg_confidence']:.1f}%"
app/web/components/technical_modules/qwen.py:10:QWEN_ROOT = (
app/web/components/technical_modules/qwen.py:14:    / "qwen4b"
app/web/components/technical_modules/qwen.py:24:QWEN_SCRIPT = (
app/web/components/technical_modules/qwen.py:27:    / "qwen4b_output_v01.py"
app/web/components/technical_modules/qwen.py:35:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/qwen.py:40:    if QWEN_ROOT.exists():
app/web/components/technical_modules/qwen.py:44:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/qwen.py:57:def _load_qwen_status():
app/web/components/technical_modules/qwen.py:72:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:156:                "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:173:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:200:def build_qwen():
app/web/components/technical_modules/qwen.py:205:            "QWEN3-VL 4B"
app/web/components/technical_modules/qwen.py:269:                "▶ Запустить Qwen",
app/web/components/technical_modules/qwen.py:275:                "■ Остановить Qwen",
app/web/components/technical_modules/qwen.py:294:    qwen_process = None
app/web/components/technical_modules/qwen.py:295:    qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:297:    async def stop_qwen():
app/web/components/technical_modules/qwen.py:298:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:299:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:301:        if qwen_process is None:
app/web/components/technical_modules/qwen.py:304:        qwen_stop_requested = True
app/web/components/technical_modules/qwen.py:307:            f"[QWEN MANUAL] STOP REQUESTED PID={qwen_process.pid}",
app/web/components/technical_modules/qwen.py:312:            qwen_process.terminate()
app/web/components/technical_modules/qwen.py:317:                f"[QWEN MANUAL] STOP FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:321:    async def run_qwen():
app/web/components/technical_modules/qwen.py:323:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:324:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:326:        print("[QWEN MANUAL] START", flush=True)
app/web/components/technical_modules/qwen.py:328:        qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:335:            if not QWEN_SCRIPT.exists():
app/web/components/technical_modules/qwen.py:338:                    f"[QWEN MANUAL] SCRIPT NOT FOUND: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:343:                    f"Не найден Qwen script: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:355:                    "[QWEN MANUAL] HYBRID RUN NOT FOUND",
app/web/components/technical_modules/qwen.py:382:                    f"[QWEN MANUAL] NO IMAGES: {result_dir}",
app/web/components/technical_modules/qwen.py:396:            qwen_output = QWEN_ROOT / run_name
app/web/components/technical_modules/qwen.py:397:            qwen_output.mkdir(
app/web/components/technical_modules/qwen.py:403:                f"[QWEN MANUAL] INPUT: {result_dir}",
app/web/components/technical_modules/qwen.py:408:                f"[QWEN MANUAL] OUTPUT: {qwen_output}",
app/web/components/technical_modules/qwen.py:413:                f"[QWEN MANUAL] IMAGES: {total_images}",
app/web/components/technical_modules/qwen.py:420:            model_label.text = "qwen3-vl:4b-instruct"
app/web/components/technical_modules/qwen.py:435:                f"Запуск Qwen3-VL 4B: {total_images} фото",
app/web/components/technical_modules/qwen.py:447:                str(QWEN_SCRIPT),
app/web/components/technical_modules/qwen.py:451:                str(qwen_output),
app/web/components/technical_modules/qwen.py:457:            qwen_process = process
app/web/components/technical_modules/qwen.py:460:                f"[QWEN MANUAL] PID: {process.pid}",
app/web/components/technical_modules/qwen.py:488:                    f"[QWEN] {text}",
app/web/components/technical_modules/qwen.py:530:                if "[QWEN] OK |" in text:
app/web/components/technical_modules/qwen.py:580:                    "[QWEN] ERROR" in text
app/web/components/technical_modules/qwen.py:581:                    or "[QWEN] FAILED" in text
app/web/components/technical_modules/qwen.py:617:                if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:627:                f"[QWEN MANUAL] FINISHED "
app/web/components/technical_modules/qwen.py:632:            if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:638:                    f"Qwen остановлен: "
app/web/components/technical_modules/qwen.py:650:                    "✓ Qwen3-VL 4B завершён",
app/web/components/technical_modules/qwen.py:660:                status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:663:                    f"Qwen завершился с ошибкой: {returncode}",
app/web/components/technical_modules/qwen.py:671:                f"[QWEN MANUAL] EXCEPTION: {exc!r}",
app/web/components/technical_modules/qwen.py:676:            status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:680:                    f"Ошибка запуска Qwen: {exc}",
app/web/components/technical_modules/qwen.py:689:            qwen_process = None
app/web/components/technical_modules/qwen.py:690:            qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:706:                    f"[QWEN MANUAL] UI REFRESH FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:712:        data = _load_qwen_status()
app/web/components/technical_modules/qwen.py:772:    run_button.on_click(run_qwen)
app/web/components/technical_modules/qwen.py:773:    stop_button.on_click(stop_qwen)
app/web/components/photos.py:445:                        if value("qwen_status") != "—":
app/web/components/photos.py:448:                                f"Qwen: {value('qwen_status')}"
app/web/components/photos.py:1234:                                # QWEN DESCRIPTION
app/web/components/technical.py:12:from app.web.components.technical_modules.qwen import (
app/web/components/technical.py:13:    build_qwen,
app/web/components/technical.py:175:                    "qwen",
app/web/components/technical.py:176:                    label="Qwen",
app/web/components/technical.py:230:                    with ui.tab_panel("qwen"):
app/web/components/technical.py:231:                        build_qwen()
app/web/client_aliases.py:4:Qwen может распознавать одно и то же название с ошибками,
app/web/photo_db.py:28:            qwen_status,
app/web/photo_db.py:29:            qwen_time_sec,
app/web_v01_backup_20260816_142053/components/technical.py:84:                    "Qwen3-VL 4B",
app/web_v01_backup_20260816_142053/components/technical.py:85:                    "Qwen2.5-VL 3B",
app/web_v01_backup_20260816_142053/components/technical.py:86:                    "Qwen3-VL 2B",
app/web_v01_backup_20260816_142053/components/technical.py:88:                value="Qwen3-VL 4B",
scripts/banner_model_compare_v04.py:19:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v04.py:20:    "qwen2.5vl:3b",
scripts/banner_model_compare_v04.py:23:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v04.py:135:        OLLAMA_URL,
scripts/banner_qwen25vl_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen25vl_test_v01")
scripts/banner_qwen25vl_test_v01.py:14:MODEL = "qwen2.5vl:3b"
scripts/banner_qwen25vl_test_v01.py:16:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_qwen25vl_test_v01.py:104:        OLLAMA_URL,
scripts/banner_qwen25vl_test_v01.py:159:    print("QWEN2.5-VL 3B TEST")
scripts/banner_model_compare_v05.py:16:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v05.py:17:    "qwen2.5vl:3b",
scripts/banner_model_compare_v05.py:20:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v05.py:113:        OLLAMA_URL,
scripts/banner_llm_full_v02.py:11:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_llm_full_v02.py:109:    print("Sending to Ollama...")
scripts/banner_llm_full_v02.py:141:    print("QWEN3-VL BANNER TEST")
scripts/photo_ingest.py:131:    Никаких DINO/Qwen/сортировок здесь нет.
scripts/photo_ingest.py:151:                qwen_status,
scripts/import_qwen_to_db.py:10:QWEN_DIR = PROJECT / "data/metadata/qwen4b"
scripts/import_qwen_to_db.py:53:            qwen_status TEXT,
scripts/import_qwen_to_db.py:54:            qwen_time_sec REAL,
scripts/import_qwen_to_db.py:90:        ON photos(qwen_status)
scripts/import_qwen_to_db.py:114:    relative = json_path.relative_to(QWEN_DIR)
scripts/import_qwen_to_db.py:178:            qwen_status,
scripts/import_qwen_to_db.py:179:            qwen_time_sec,
scripts/import_qwen_to_db.py:216:            qwen_status = excluded.qwen_status,
scripts/import_qwen_to_db.py:217:            qwen_time_sec = excluded.qwen_time_sec,
scripts/import_qwen_to_db.py:264:    QWEN_DIR.mkdir(
scripts/import_qwen_to_db.py:275:        QWEN_DIR.rglob("*.json")
scripts/import_qwen_to_db.py:279:    print("QWEN → SQLITE")
scripts/import_qwen_to_db.py:283:    print("QWEN DIR:", QWEN_DIR)
scripts/banner_qwen4b_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen4b_test_v01")
scripts/banner_qwen4b_test_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_qwen4b_test_v01.py:16:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_qwen4b_test_v01.py:104:        OLLAMA_URL,
scripts/banner_qwen4b_test_v01.py:159:    print("QWEN3-VL 4B TEST")
scripts/banner_llm_folder_search_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01_before_compact_prompt.py:15:OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"
scripts/qwen4b_output_v01_before_compact_prompt.py:17:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01_before_compact_prompt.py:18:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/qwen4b_output_v01_before_compact_prompt.py:351:        OLLAMA_URL,
scripts/qwen4b_output_v01_before_compact_prompt.py:363:    # Ollama performance diagnostics
scripts/qwen4b_output_v01_before_compact_prompt.py:386:        "[OLLAMA]",
scripts/qwen4b_output_v01_before_compact_prompt.py:649:    print("QWEN3-VL 4B — OUTPUT ANALYSIS")
scripts/qwen4b_output_v01.py:15:OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"
scripts/qwen4b_output_v01.py:17:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01.py:18:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/qwen4b_output_v01.py:167:            OLLAMA_URL,
scripts/qwen4b_output_v01.py:201:            "[OLLAMA]",
scripts/qwen4b_output_v01.py:228:                    "[QWEN RETRY]",
scripts/qwen4b_output_v01.py:242:                "[QWEN JSON ERROR]",
scripts/qwen4b_output_v01.py:525:        help="Output directory for Qwen metadata"
scripts/qwen4b_output_v01.py:536:    print("QWEN3-VL 4B — OUTPUT ANALYSIS")
scripts/banner_llm_full_v01.py:9:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_model_compare_v02.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v02.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v02.py:27:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v02.py:98:        OLLAMA_URL,
scripts/banner_model_compare_v01.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v01.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v01.py:28:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v01.py:103:        OLLAMA_URL,
scripts/banner_database_v02.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/migrate_sqlite_to_postgres.py:75:                qwen_status,
scripts/migrate_sqlite_to_postgres.py:76:                qwen_time_sec,
scripts/migrate_sqlite_to_postgres.py:111:                row["qwen_status"],
scripts/migrate_sqlite_to_postgres.py:112:                row["qwen_time_sec"],
scripts/migrate_sqlite_to_postgres.py:165:                    qwen_status,
scripts/migrate_sqlite_to_postgres.py:166:                    qwen_time_sec,
scripts/banner_database_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/llm_resolver_v01.py:11:MODEL = "qwen3:4b"
scripts/llm_resolver_v01.py:168:            "ollama",
scripts/llm_resolver_v01.py:224:        print("--- QWEN3:4B ---")
scripts/qwen_prompt_ablation.py:15:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen_prompt_ablation.py:16:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/qwen_prompt_ablation.py:162:            OLLAMA_URL,
scripts/qwen_prompt_ablation.py:193:        print("OLLAMA TOTAL:    ", round(stats["total"], 2), "sec")
scripts/qwen_prompt_ablation.py:218:    print("QWEN3-VL 4B — PROMPT ABLATION TEST")
scripts/banner_model_compare_v03.py:19:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v03.py:20:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v03.py:23:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v03.py:116:        OLLAMA_URL,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:30:07

> **Inspecting DINO and Qwen script arguments**
>
>
> ****
>
> 
>
> **Inspected DINO and Qwen script arguments**
>
> 
>
> Worked for 11s

Да. Сейчас уже можно **честно сравнить два режима**:

1. **1 DINO + Qwen**
2. **2 DINO + Qwen**

Причём Qwen должен стартовать **одновременно**, а не после завершения DINO. Нам важен именно общий `real` и загрузка CPU/GPU.

Но сначала нужно увидеть точный интерфейс `dino_worker.py` и аргументы Qwen, чтобы не дать тебе неправильную команду.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "================ DINO WORKER ================"
sed -n '1,320p' app/workers/dino_worker.py

echo
echo "================ QWEN ARGS ================"
grep -nE 'ArgumentParser|add_argument|if __name__|def main' \
    scripts/qwen4b_output_v01.py
```

И ещё:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
'dino_worker|DINO.*worker|python.*dino_worker' \
app scripts \
--include="*.py" | head -100
```

**После этого я дам две готовые команды для теста:**

```text
ТЕСТ A:
DINO ×1  ─────┐
              ├── одновременно
QWEN  ────────┘

ТЕСТ B:
DINO ×2  ─────┐
DINO ×2  ─────┤── одновременно
QWEN  ────────┘
```

И будем смотреть не только `real`, но и:

- CPU %
- GPU %
- VRAM
- скорость DINO
- скорость Qwen
- сколько времени занял весь проход

**Цель сейчас не выжать максимальный DINO, а найти оптимальный баланс**, чтобы CPU был примерно в районе твоих желаемых **≤50%**, а RTX 3060 одновременно нормально занималась Qwen.

---

### 👤 **User** — 2026-08-18 22:30:47

scripts/qwen4b_output_v01.py
================ DINO WORKER ================
from __future__ import annotations

import os
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def claim_photo(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                id,
                photo_id,
                source_path
            FROM photos
            WHERE dino_status = 'pending'
            ORDER BY id
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )

        row = cur.fetchone()

        if row is None:
            conn.commit()
            return None

        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (row["id"],),
        )

        conn.commit()

        return row

def mark_done(
    conn,
    photo_id,
    result,
    elapsed,
):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'done',
                dino_fingerprint = %s,
                dino_score = %s,
                dino_second_score = %s,
                dino_margin = %s,
                dino_time_sec = %s,
                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                result.get("best_id"),
                result.get("score"),
                result.get("second_score"),
                result.get("margin"),
                elapsed,
                photo_id,
            ),
        )

    conn.commit()

def mark_error(
    conn,
    photo_id,
    error,
):
    message = str(error)

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'error',
                error_message = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                message[:4000],
                photo_id,
            ),
        )

    conn.commit()

def main():
    settings = Settings()

    print("=" * 70)
    print("DINO WORKER")
    print("=" * 70)
    print("device:", settings.device)
    print("database:", DB_CONFIG["dbname"])
    print("=" * 70)

    embedder = SceneEmbedder(settings)

    manager = FingerprintManager(
        settings,
        embedder,
    )

    recognizer = SceneRecognizer(
        settings,
        embedder,
        manager,
    )

    conn = get_connection()

    print("[DINO] Worker ready.")

    max_items = int(os.getenv("DINO_MAX_ITEMS", "0"))
    processed = 0

    try:
        while True:
            if max_items > 0 and processed >= max_items:
                print(
                    f"[DINO] Reached max_items={max_items}."
                )
                break

            row = claim_photo(conn)

            if row is None:
                print("[DINO] Queue empty.")
                break

            photo_id = row["id"]
            photo_key = row["photo_id"]
            source_path = Path(row["source_path"])

            print()
            print("-" * 70)
            print(
                f"[DINO] "
                f"{photo_key} "
                f"{source_path.name}"
            )

            started = time.perf_counter()

            try:
                if not source_path.exists():
                    raise FileNotFoundError(
                        f"Photo not found: {source_path}"
                    )

                result = recognizer.recognize_one(
                    source_path,
                    top_k=5,
                    threshold=0.65,
                )

                elapsed = time.perf_counter() - started

                mark_done(
                    conn,
                    photo_id,
                    result,
                    elapsed,
                )

                print(
                    f"[DINO] DONE "
                    f"{photo_key} "
                    f"-> {result.get('best_id')} "
                    f"score={result.get('score', 0):.6f} "
                    f"margin={result.get('margin', 0):.6f} "
                    f"time={elapsed:.2f}s"
                )

                processed += 1

            except Exception as exc:
                elapsed = time.perf_counter() - started

                print(
                    f"[DINO] ERROR "
                    f"{photo_key}: {exc}"
                )

                try:
                    mark_error(
                        conn,
                        photo_id,
                        exc,
                    )
                except Exception as db_error:
                    print(
                        "[DINO] "
                        f"DB ERROR while marking error: "
                        f"{db_error}"
                    )

    finally:
        conn.close()
        print()
        print("[DINO] Worker stopped.")

if __name__ == "__main__":
    main()

================ QWEN ARGS ================
501:def main():
505:    parser = argparse.ArgumentParser()
507:    parser.add_argument(
514:    parser.add_argument(
521:    parser.add_argument(
559:if __name__ == "__main__":
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
'dino_worker|DINO.*worker|python.*dino_worker' \
app scripts \
--include="*.py" | head -100
app/workers/dino_worker.py:131:    print("DINO WORKER")
app/workers/dino_worker.py:152:    print("[DINO] Worker ready.")
app/workers/dino_worker.py:241:        print("[DINO] Worker stopped.")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:30:48

Да, теперь всё понятно. У нас `dino_worker.py` уже **правильно сделан под параллельный запуск**:

- каждый DINO-процесс берет `pending` через `FOR UPDATE SKIP LOCKED`;
- второй процесс не возьмёт ту же фотографию;
- оба работают с одной PostgreSQL;
- Qwen — отдельный процесс через Ollama;
- поэтому можем запускать **1 или 2 DINO независимо от Qwen**.

### Тест 1 — 1 DINO + Qwen

Сначала сбросим тестовые фотографии в `pending` — если они сейчас уже `done`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -h localhost -U lora -d photobase -c "
UPDATE photos
SET dino_status='pending',
    dino_fingerprint=NULL,
    dino_score=NULL,
    dino_second_score=NULL,
    dino_margin=NULL,
    dino_time_sec=NULL
WHERE photo_id IN (
    SELECT photo_id
    FROM photos
    ORDER BY id
    LIMIT 526
);
"
```

Потом **в одном терминале**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

time env DINO_MAX_ITEMS=526 \
uv run python -u app/workers/dino_worker.py
```

И **одновременно во втором терминале** запускаем тот самый Qwen, который используется кнопкой:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python scripts/qwen4b_output_v01.py --help
```

Это сначала покажет точные обязательные аргументы. **Пришли этот вывод**, и я дам команду запуска Qwen именно для нашего текущего тестового набора.

---

### Тест 2 — 2 DINO + Qwen

После первого теста опять сбрасываем тот же набор в `pending`.

Затем запускаем **два независимых DINO**:

Терминал №1:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

time env DINO_MAX_ITEMS=263 \
uv run python -u app/workers/dino_worker.py
```

Терминал №2:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

time env DINO_MAX_ITEMS=263 \
uv run python -u app/workers/dino_worker.py
```

И одновременно в терминале №3 — Qwen.

Здесь важный момент: **526 / 2 = 263**, поэтому каждый DINO должен обработать примерно половину очереди.

Но даже лучше вообще не делить `263/263`: можно обоим поставить `DINO_MAX_ITEMS=0`, и они сами разберут очередь:

```bash
uv run python -u app/workers/dino_worker.py
```

в каждом из двух терминалов.

`SKIP LOCKED` как раз для этого и нужен.

---

### Что мы будем сравнивать

| Режим | DINO | Qwen | Цель |
|---|---:|---:|---|
| A | 1 | 1 | базовый параллельный режим |
| B | 2 | 1 | найти оптимум |
| C | 2 | 0 | контрольная скорость DINO |

И во время каждого теста:

```bash
watch -n 1 '
echo "===== GPU ====="
nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu \
--format=csv,noheader
echo
echo "===== CPU ====="
top -bn1 | grep "Cpu(s)"
'
```

**Особенно интересует тест B.**

У тебя сейчас уже очень хороший ориентир:

- 1 DINO: примерно **0.35–0.37 с/фото**
- CPU около **25%**
- VRAM около **2 GB**
- RTX 3060 имеет большой запас.

Поэтому вполне возможно, что **2 DINO + Qwen будет именно тем режимом, который нам нужен**: DINO достаточно быстро разбирает очередь и пишет адреса в БД, а Qwen независимо грузит GPU и постепенно заполняет описания.

И главное — нам сейчас **не надо менять архитектуру**. Она уже позволяет сделать этот тест.

---

### 👤 **User** — 2026-08-18 22:31:27

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

python scripts/qwen4b_output_v01.py --help
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:31:28

Да, это просто потому, что в системе нет глобальной команды `python`. У нас проект работает через **uv**, поэтому запускать Qwen тоже нужно через `uv run`.

Проверь:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/qwen4b_output_v01.py --help
```

Это правильный вариант для нашего окружения.

**Пока ничего устанавливать через `apt` не надо.** `uv run python` уже использует `.venv` проекта, где у нас установлен нужный Python и зависимости.

Пришли вывод `--help` — после этого сразу дам точную команду для **одновременного теста 1 DINO + Qwen**, а затем 2 DINO + Qwen.

---

### 👤 **User** — 2026-08-18 22:31:48

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/qwen4b_output_v01.py --help
usage: qwen4b_output_v01.py [-h] [--limit LIMIT] [--input INPUT]
                            [--output OUTPUT]

options:
  -h, --help       show this help message and exit
  --limit LIMIT    Process only N images
  --input INPUT    Input directory with sorted photos
  --output OUTPUT  Output directory for Qwen metadata
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:31:49

Отлично. Теперь можем провести **чистый тест 1 DINO + 1 Qwen**, а затем **2 DINO + 1 Qwen**.

Причём Qwen запускаем именно тем же скриптом, который привязан к кнопке в технастройках.

### Тест №1 — 1 DINO + Qwen одновременно

Нам нужно взять **тот же набор 526 фотографий**, на котором ты уже мерил DINO.

**Терминал 1 — DINO:**

```bash id="1k3d2q"
cd ~/projects/scene_fingerprint_mvp_v02

time env DINO_MAX_ITEMS=526 \
uv run python -u app/workers/dino_worker.py
```

**Терминал 2 — Qwen:**

Qwen должен получить именно каталог отсортированных фотографий текущего hybrid-запуска. Поэтому сначала посмотрим, какой каталог сейчас актуальный:

```bash id="x2f9wa"
cd ~/projects/scene_fingerprint_mvp_v02

find data/output/daily -maxdepth 2 -type d | sort | tail -20
```

Пришли вывод.

После этого я дам **конкретную команду Qwen** вида:

```bash
uv run python -u scripts/qwen4b_output_v01.py \
  --limit 526 \
  --input "..." \
  --output "..."
```

---

### Почему пока не запускаем Qwen вслепую

У него есть:

```text
--input
--output
```

и мы знаем, что веб-модуль перед запуском ищет последний `hybrid` результат:

```text
data/output/daily/<run>
```

Нужно использовать **точно тот же input**, чтобы сравнение было честным.

После этого сделаем:

**Тест A**

```text
1 × DINO ──────────────┐
                       ├── 526 фото
1 × Qwen (GPU) ────────┘
```

и затем:

**Тест B**

```text
DINO #1 ───────────────┐
DINO #2 ───────────────┤
                      ├── 526 фото
Qwen ──────────────────┘
```

И посмотрим главное: **сократится ли общее время при 2 DINO, не мешая Qwen на GPU**, при твоём ограничении CPU примерно до 50%.

---

### 👤 **User** — 2026-08-18 22:32:23

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

find data/output/daily -maxdepth 2 -type d | sort | tail -20
data/output/daily
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:32:25

Да, значит сейчас **в `data/output/daily` нет готового Hybrid-запуска**, а Qwen из кнопки технических настроек обычно берет именно оттуда.

Но для нашего теста это даже удобно: **не надо запускать весь Hybrid**. Нам нужно проверить именно конкуренцию ресурсов:

> DINO на CPU ↔ Qwen на GPU.

Сначала посмотрим, какие входы ожидает Qwen и откуда он реально берет изображения. Выполни:

```bash id="qwen-input-inspect"
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,120p' scripts/qwen4b_output_v01.py

echo
echo "================ QWEN INPUT LOGIC ================"

sed -n '120,280p' scripts/qwen4b_output_v01.py
```

Особенно интересует участок, где формируется список `images` / `input_dir`.

**Пока DINO не запускай.** После этого мы найдём подходящую папку с теми же 526 фото и запустим первый эксперимент:

```text
1 DINO CPU
      +
1 Qwen GPU
      ↓
526 одинаковых фото
```

А затем второй:

```text
2 DINO CPU
      +
1 Qwen GPU
      ↓
526 одинаковых фото
```

Так мы получим действительно сравнимые результаты.

---

### 👤 **User** — 2026-08-18 22:32:43

надо фото брать из инпут

---

### 🤖 **Assistant** — 2026-08-18 22:32:44

Да. Тогда ещё проще: **Qwen берём прямо из `data/input`**, без `data/output/daily`.

Для первого теста запускаем оба процесса на одном и том же наборе фото из `data/input`.

### 1 DINO + Qwen

**Терминал 1 — DINO:**

```bash
cd ~/projects/scene_fingerprint_mvp_v02

time env DINO_MAX_ITEMS=526 \
uv run python -u app/workers/dino_worker.py
```

**Терминал 2 — Qwen:**

```bash
cd ~/projects/scene_fingerprint_mvp_v02

time uv run python -u scripts/qwen4b_output_v01.py \
  --input data/input \
  --limit 526 \
  --output data/metadata/qwen4b/test_parallel_1dino
```

Но есть один важный момент: **DINO и Qwen должны видеть абсолютно одинаковые 526 фотографий**. Если `data/input` содержит ровно эти 526 — отлично.

Перед стартом можно проверить:

```bash
find data/input -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l
```

Если покажет `526`, запускаем именно так.

После этого делаем второй тест:

### 2 DINO + Qwen

Два терминала DINO:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

time env DINO_MAX_ITEMS=0 \
uv run python -u app/workers/dino_worker.py
```

и второй:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

time env DINO_MAX_ITEMS=0 \
uv run python -u app/workers/dino_worker.py
```

Qwen:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

time uv run python -u scripts/qwen4b_output_v01.py \
  --input data/input \
  --limit 526 \
  --output data/metadata/qwen4b/test_parallel_2dino
```

Здесь `SKIP LOCKED` распределит 526 фотографий между двумя DINO автоматически.

**Но сначала проверь количество фото.** Если там не 526, скажи число — под него настроим тест.

---

### 👤 **User** — 2026-08-18 22:33:00

/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily

---

### 🤖 **Assistant** — 2026-08-18 22:33:02

Да, понял. **Источник для обоих процессов — именно:**

```text
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily
```

Тогда не трогаем `data/output/daily`.

Сначала проверим количество фотографий:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find data/input/daily -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) | wc -l
```

Если там наши **526 фото**, первый эксперимент такой.

**Терминал 1 — DINO:**

```bash
cd ~/projects/scene_fingerprint_mvp_v02

time env DINO_MAX_ITEMS=526 \
uv run python -u app/workers/dino_worker.py
```

**Терминал 2 — Qwen:**

```bash
cd ~/projects/scene_fingerprint_mvp_v02

time uv run python -u scripts/qwen4b_output_v01.py \
  --input /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily \
  --limit 526 \
  --output data/metadata/qwen4b/test_parallel_1dino
```

Но есть **важный нюанс**: DINO сейчас берёт фото из PostgreSQL (`source_path`), а не непосредственно сканирует `data/input/daily`. Поэтому для честного теста надо убедиться, что записи `photos` действительно указывают на эти же файлы.

То есть схема у нас должна быть:

```text
                    526 фото
                       │
             data/input/daily
                  ┌────┴────┐
                  ↓         ↓
              DINO CPU    Qwen GPU
                  │         │
                  ↓         ↓
              PostgreSQL  metadata
                  │
                  └────┬────┘
                       ↓
                    GRID
```

Именно это нам и нужно проверить: **Qwen работает независимо на GPU, пока DINO на CPU распознаёт и записывает результат в БД.**

---

