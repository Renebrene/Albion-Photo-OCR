## СЕССИЯ: вторник

**Создано:** 2026-08-18 18:12:03
**Обновлено:** 2026-08-22 20:16:20
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1)

---

### 👤 **User** — 2026-08-18 20:41:18

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ CLI ================" && \
grep -RniE \
"def recognize|recognize\(|add_parser.*recognize|top-k|fingerprints|batch|workers|ThreadPool|ProcessPool" \
app scripts \
--include="*.py" 2>/dev/null | head -250
================ CLI ================
app/web/components/technical_modules/fingerprints.py:4:def build_fingerprints():
app/web/components/technical.py:21:from app.web.components.technical_modules.fingerprints import (
app/web/components/technical.py:22:    build_fingerprints,
app/web/components/technical.py:193:                    "fingerprints",
app/web/components/technical.py:194:                    label="Fingerprints",
app/web/components/technical.py:239:                    with ui.tab_panel("fingerprints"):
app/web/components/technical.py:240:                        build_fingerprints()
app/core/recognizer.py:3:from concurrent.futures import ThreadPoolExecutor
app/core/recognizer.py:97:    def recognize_folder(
app/core/recognizer.py:102:        workers=6,
app/core/recognizer.py:103:        fingerprints=None,
app/core/recognizer.py:119:        loaded_fingerprints = []
app/core/recognizer.py:121:        # Optional whitelist of fingerprints.
app/core/recognizer.py:122:        # If provided, ONLY these fingerprints are used.
app/core/recognizer.py:123:        if fingerprints is not None:
app/core/recognizer.py:124:            allowed_fingerprints = {
app/core/recognizer.py:126:                for item in fingerprints
app/core/recognizer.py:130:            allowed_fingerprints = None
app/core/recognizer.py:133:            self.manager.list_fingerprints()
app/core/recognizer.py:143:                allowed_fingerprints is not None
app/core/recognizer.py:145:                not in allowed_fingerprints
app/core/recognizer.py:183:            loaded_fingerprints.append(
app/core/recognizer.py:190:        if not loaded_fingerprints:
app/core/recognizer.py:193:                "fingerprints found."
app/core/recognizer.py:197:            "[Recognizer] Fingerprints: "
app/core/recognizer.py:200:                for fp_id, _ in loaded_fingerprints
app/core/recognizer.py:225:        # Use CPU workers to process different images in parallel.
app/core/recognizer.py:252:            int(workers),
app/core/recognizer.py:256:            f"[Recognizer] CPU workers: "
app/core/recognizer.py:260:        with ThreadPoolExecutor(
app/core/recognizer.py:261:            max_workers=worker_count
app/core/recognizer.py:283:            for fingerprint_id, data in loaded_fingerprints:
app/core/recognizer.py:484:    def recognize(
app/core/config.py:20:    batch_size: int = int(
app/core/config.py:22:            "SCENE_BATCH",
app/core/config.py:28:    def fingerprints_dir(self):
app/core/config.py:31:                "SCENE_FINGERPRINTS",
app/core/config.py:32:                str(self.data_dir / "fingerprints")
app/core/embedder.py:68:        batch_size=None,
app/core/embedder.py:70:        batch_size = (
app/core/embedder.py:71:            batch_size
app/core/embedder.py:72:            or self.settings.batch_size
app/core/embedder.py:80:            batch_size,
app/core/embedder.py:82:            batch_images = images[
app/core/embedder.py:83:                i:i + batch_size
app/core/embedder.py:87:                images=batch_images,
app/core/fingerprint.py:4:from concurrent.futures import ThreadPoolExecutor
app/core/fingerprint.py:50:            else settings.fingerprints_dir
app/core/fingerprint.py:66:    def list_fingerprints(self):
app/core/fingerprint.py:274:        workers = min(
app/core/fingerprint.py:284:            f"CPU workers={workers}"
app/core/fingerprint.py:294:        with ThreadPoolExecutor(
app/core/fingerprint.py:295:            max_workers=workers
app/pipeline/worker.py:79:        print("[Worker] Starting batch processing")
app/pipeline/worker.py:94:            f"[Worker] Batch complete. "
app/main.py:41:            topk = ui.number("Top-K", value=5, min=1, max=20).classes("w-32")
app/main.py:73:                    data = manager.list_fingerprints()
app/cli.py:76:    # QUEUE BATCH ADD
app/cli.py:79:    queue_batch_parser = subparsers.add_parser(
app/cli.py:80:        "queue-batch-add",
app/cli.py:84:    queue_batch_parser.add_argument(
app/cli.py:90:    queue_batch_parser.add_argument(
app/cli.py:96:    queue_batch_parser.add_argument(
app/cli.py:138:        "--top-k",
app/cli.py:152:        "--workers",
app/cli.py:155:        help="Number of CPU workers for descriptor calculation",
app/cli.py:159:        "--fingerprints",
app/cli.py:420:    # QUEUE BATCH ADD
app/cli.py:423:    if args.command == "queue-batch-add":
app/cli.py:485:                settings.fingerprints_dir
app/cli.py:536:        print("[Queue] BATCH COMPLETE")
app/cli.py:619:        selected_fingerprints = None
app/cli.py:621:        if args.fingerprints:
app/cli.py:622:            selected_fingerprints = [
app/cli.py:624:                for item in args.fingerprints.split(",")
app/cli.py:633:                workers=args.workers,
app/cli.py:634:                fingerprints=selected_fingerprints,
app/ocr/ocr_pipeline.py:40:    def recognize(self, image_path: str | Path) -> list[OCRResult]:
app/ocr/ocr_pipeline.py:102:    results = ocr.recognize(
app/ocr/grid_ocr.py:249:    workers: int = 4,
app/ocr/grid_ocr.py:296:        f"Workers: {workers}"
app/ocr/grid_ocr.py:350:        processes=workers,
app/ocr/grid_ocr.py:425:            f"WORKERS: "
app/ocr/grid_ocr.py:426:            f"{workers}\n"
app/ocr/grid_ocr.py:502:        "--workers",
app/ocr/grid_ocr.py:507:            "workers (default: 4)"
app/ocr/grid_ocr.py:513:    if args.workers < 1:
app/ocr/grid_ocr.py:515:            "--workers must be >= 1"
app/ocr/grid_ocr.py:520:        workers=args.workers,
scripts/sort_neighbor_v35_benchmark.py:21:FINGERPRINTS = list(range(78, 96))
scripts/sort_neighbor_v35_benchmark.py:290:    for n in FINGERPRINTS:
scripts/benchmark_sub_rerank_v04.py:21:    "data/fingerprints_sub_exp"
scripts/sort_test_and_report_v2.py:20:FINGERPRINTS = [
scripts/sort_test_and_report_v2.py:93:    fp_arg = ",".join(FINGERPRINTS)
scripts/sort_test_and_report_v2.py:101:        "--top-k",
scripts/sort_test_and_report_v2.py:105:        "--fingerprints",
scripts/sort_test_and_report_v2.py:115:    print("Fingerprints:", ", ".join(FINGERPRINTS))
scripts/make_subfingerprints_v2.py:348:            "  uv run python scripts/make_subfingerprints_v2.py 78_v33"
scripts/make_subfingerprints_v2.py:354:    source = Path("data/fingerprints") / fingerprint
scripts/make_subfingerprints_v2.py:372:    print("SUBFINGERPRINTS V2")
scripts/make_subfingerprints_v2.py:414:        Path("data/subfingerprints_v2"),
scripts/benchmark_test_v1.py:17:FINGERPRINTS = [f"{i}_v33" for i in range(78, 96)]
scripts/benchmark_test_v1.py:46:    for fp in FINGERPRINTS:
scripts/benchmark_test_v1.py:47:        p = PROJECT / "data/fingerprints" / fp / "metadata.json"
scripts/benchmark_test_v1.py:95:        "--top-k",
scripts/benchmark_test_v1.py:99:        "--fingerprints",
scripts/benchmark_test_v1.py:100:        ",".join(FINGERPRINTS),
scripts/benchmark_test_v1.py:108:    print("Fingerprints:", len(FINGERPRINTS))
scripts/benchmark_test_v1.py:226:                "fingerprints": FINGERPRINTS,
scripts/banner_search_v03.py:6:from concurrent.futures import ThreadPoolExecutor, as_completed
scripts/banner_search_v03.py:31:WORKERS = min(
scripts/banner_search_v03.py:37:BATCH_SIZE = 96
scripts/banner_search_v03.py:44:print("Workers:", WORKERS)
scripts/banner_search_v03.py:45:print("GPU batch:", BATCH_SIZE)
scripts/banner_search_v03.py:265:        BATCH_SIZE
scripts/banner_search_v03.py:268:        batch = windows[
scripts/banner_search_v03.py:270:            i+BATCH_SIZE
scripts/banner_search_v03.py:276:            batch,
scripts/banner_search_v03.py:385:        "Workers:",
scripts/banner_search_v03.py:386:        WORKERS
scripts/banner_search_v03.py:390:        "GPU batch:",
scripts/banner_search_v03.py:391:        BATCH_SIZE
scripts/banner_search_v03.py:467:    with ThreadPoolExecutor(
scripts/banner_search_v03.py:468:        max_workers=WORKERS
scripts/benchmark_test_sub_exp.py:17:FINGERPRINTS = [
scripts/benchmark_test_sub_exp.py:36:FINGERPRINTS = [f"{i}_v33" for i in range(78, 96)]
scripts/benchmark_test_sub_exp.py:65:    for fp in FINGERPRINTS:
scripts/benchmark_test_sub_exp.py:66:        p = PROJECT / "data/fingerprints" / fp / "metadata.json"
scripts/benchmark_test_sub_exp.py:114:        "--top-k",
scripts/benchmark_test_sub_exp.py:118:        "--fingerprints",
scripts/benchmark_test_sub_exp.py:119:        ",".join(FINGERPRINTS),
scripts/benchmark_test_sub_exp.py:127:    print("Fingerprints:", len(FINGERPRINTS))
scripts/benchmark_test_sub_exp.py:245:                "fingerprints": FINGERPRINTS,
scripts/banner_search_v03_2.py:8:from concurrent.futures import ThreadPoolExecutor
scripts/banner_search_v03_2.py:27:CPU_WORKERS = max(
scripts/banner_search_v03_2.py:32:GPU_BATCH = 96
scripts/banner_search_v03_2.py:206:            GPU_BATCH
scripts/banner_search_v03_2.py:209:            batch = windows[
scripts/banner_search_v03_2.py:210:                i:i+GPU_BATCH
scripts/banner_search_v03_2.py:215:                batch
scripts/banner_search_v03_2.py:322:        "CPU workers:",
scripts/banner_search_v03_2.py:323:        CPU_WORKERS
scripts/banner_search_v03_2.py:327:        "GPU batch:",
scripts/banner_search_v03_2.py:328:        GPU_BATCH
scripts/banner_search_v03_2.py:426:    with ThreadPoolExecutor(
scripts/banner_search_v03_2.py:427:        max_workers=CPU_WORKERS
scripts/banner_crop_search_v02.py:7:from concurrent.futures import ThreadPoolExecutor
scripts/banner_crop_search_v02.py:25:BATCH_SIZE = 32
scripts/banner_crop_search_v02.py:27:WORKERS = max(
scripts/banner_crop_search_v02.py:136:        "/tmp/banner_batch"
scripts/banner_crop_search_v02.py:169:def embed_batch(embedder, items, prefix):
scripts/banner_crop_search_v02.py:188:        "CPU workers:",
scripts/banner_crop_search_v02.py:189:        WORKERS
scripts/banner_crop_search_v02.py:193:        "Batch:",
scripts/banner_crop_search_v02.py:194:        BATCH_SIZE
scripts/banner_crop_search_v02.py:241:        banner_emb = embed_batch(
scripts/banner_crop_search_v02.py:282:                    BATCH_SIZE
scripts/banner_crop_search_v02.py:286:                batch = windows[
scripts/banner_crop_search_v02.py:288:                    start + BATCH_SIZE
scripts/banner_crop_search_v02.py:291:                emb = embed_batch(
scripts/banner_crop_search_v02.py:293:                    batch,
scripts/benchmark_hybrid_v08.py:22:    "data/fingerprints_sub_exp"
scripts/benchmark_hybrid_v03.py:22:    "data/fingerprints_sub_exp"
scripts/sort_test_and_report_hybrid_v12.py:20:FINGERPRINTS = [
scripts/sort_test_and_report_hybrid_v12.py:93:    fp_arg = ",".join(FINGERPRINTS)
scripts/sort_test_and_report_hybrid_v12.py:101:        "--top-k",
scripts/sort_test_and_report_hybrid_v12.py:105:        "--fingerprints",
scripts/sort_test_and_report_hybrid_v12.py:115:    print("Fingerprints:", ", ".join(FINGERPRINTS))
scripts/benchmark_hybrid_v12_full.py:22:    "data/fingerprints_sub_exp"
scripts/benchmark_hybrid_v10_debug.py:22:    "data/fingerprints_sub_exp"
scripts/benchmark_sub_rerank_v03.py:21:    "data/fingerprints_sub_exp"
scripts/benchmark_sub_rerank_v01.py:20:    / "data/fingerprints_sub_exp"
scripts/run_hybrid_v12.py:19:SUB_DIR = PROJECT / "data/fingerprints_sub_exp"
scripts/run_hybrid_v12.py:96:def run_recognition(input_dir, fingerprints):
scripts/run_hybrid_v12.py:103:    fp_arg = ",".join(fingerprints)
scripts/run_hybrid_v12.py:111:        "--top-k",
scripts/run_hybrid_v12.py:115:        "--fingerprints",
scripts/run_hybrid_v12.py:124:    print("Fingerprints:", ", ".join(fingerprints))
scripts/run_hybrid_v12.py:540:    fingerprints = [
scripts/run_hybrid_v12.py:570:        fingerprints,
scripts/run_hybrid_v12.py:574:    # 2. Load Hybrid subfingerprints
scripts/run_hybrid_v12.py:579:    print("LOADING HYBRID SUBFINGERPRINTS")
scripts/run_hybrid_v12.py:584:    print("Subfingerprints:", len(subs))
scripts/benchmark_hybrid_v11.py:22:    "data/fingerprints_sub_exp"
scripts/benchmark_hybrid_v02.py:22:    "data/fingerprints_sub_exp"
scripts/analyze_subfingerprints.py:13:FINGERPRINT_DIR = PROJECT / "data/fingerprints"
scripts/build_subfingerprints_exp.py:11:DST = PROJECT / "data/subfingerprints_exp"
scripts/build_subfingerprints_exp.py:17:    print("BUILD SUBFINGERPRINTS EXP")
scripts/make_subfingerprints.py:247:    fingerprints_root,
scripts/make_subfingerprints.py:253:    source = fingerprints_root / fingerprint
scripts/make_subfingerprints.py:345:        "subfingerprints": len(groups),
scripts/make_subfingerprints.py:395:    print(f"SUBFINGERPRINTS: {len(groups)}")
scripts/make_subfingerprints.py:412:        description="Create subfingerprints from existing v3.3 fingerprints"
scripts/make_subfingerprints.py:439:        "--fingerprints-root",
scripts/make_subfingerprints.py:440:        default="data/fingerprints",
scripts/make_subfingerprints.py:445:        default="data/subfingerprints",
scripts/make_subfingerprints.py:452:        fingerprints_root=Path(
scripts/make_subfingerprints.py:453:            args.fingerprints_root
scripts/sort_baseline.py:16:FINGERPRINTS = [
scripts/sort_baseline.py:36:    for fp in FINGERPRINTS:
scripts/sort_baseline.py:50:        if folder not in FINGERPRINTS:
scripts/sort_baseline.py:143:    for fp in FINGERPRINTS:
scripts/banner_candidates_v01.py:23:BATCH_SIZE = 32
scripts/banner_candidates_v01.py:25:WORKERS = max(
scripts/banner_candidates_v01.py:148:def save_batch(items, prefix):
scripts/banner_candidates_v01.py:187:def embed_batch(embedder, items, prefix):
scripts/banner_candidates_v01.py:189:    paths = save_batch(
scripts/banner_candidates_v01.py:233:        "CPU workers:",
scripts/banner_candidates_v01.py:234:        WORKERS
scripts/banner_candidates_v01.py:238:        "GPU batch:",
scripts/banner_candidates_v01.py:239:        BATCH_SIZE
scripts/banner_candidates_v01.py:292:    banner_emb = embed_batch(
scripts/banner_candidates_v01.py:328:            BATCH_SIZE
scripts/banner_candidates_v01.py:332:        batch = windows[
scripts/banner_candidates_v01.py:334:            start+BATCH_SIZE
scripts/banner_candidates_v01.py:338:        emb = embed_batch(
scripts/banner_candidates_v01.py:340:            batch,
scripts/banner_search_v03_3.py:24:GPU_BATCH = 96
scripts/banner_search_v03_3.py:162:def embed_batch(embedder, batch):
scripts/banner_search_v03_3.py:166:        for x in batch
scripts/banner_search_v03_3.py:214:            GPU_BATCH
scripts/banner_search_v03_3.py:216:        desc="GPU batches"
scripts/banner_search_v03_3.py:219:        batch = windows[
scripts/banner_search_v03_3.py:221:            start+GPU_BATCH
scripts/banner_search_v03_3.py:225:        emb = embed_batch(
scripts/banner_search_v03_3.py:227:            batch
scripts/banner_search_v03_3.py:330:        "GPU batch:",
scripts/banner_search_v03_3.py:331:        GPU_BATCH
scripts/benchmark_hybrid_v05.py:22:    "data/fingerprints_sub_exp"
scripts/benchmark_hybrid_v04.py:22:    "data/fingerprints_sub_exp"
scripts/benchmark_hybrid_v01.py:22:    "data/fingerprints_sub_exp"
scripts/build_subfingerprint_database.py:13:SOURCE = PROJECT / "data/subfingerprints_exp"
scripts/build_subfingerprint_database.py:15:TARGET = PROJECT / "data/fingerprints_sub_exp"
scripts/benchmark_hybrid_v07.py:22:    "data/fingerprints_sub_exp"
scripts/export_subclusters.py:13:FINGERPRINT_DIR = PROJECT / "data/fingerprints"
scripts/benchmark_hybrid_v06.py:22:    "data/fingerprints_sub_exp"
scripts/benchmark_sub_rerank_v02.py:23:    / "data/fingerprints_sub_exp"
scripts/benchmark_sub_rerank_v02.py:109:        "Sub fingerprints:",
scripts/benchmark_hybrid_v09.py:22:    "data/fingerprints_sub_exp"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,260p' app/core/recognizer.py 2>/dev/null
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from .image import image_files
from .scene_analyzer import (
    CompactDescriptor,
    SceneAnalyzer,
)

class SceneRecognizer:
    """
    Scene Fingerprint v3.3 compact recognizer.

    Uses:
        global
        environment
        color
        spatial

    Does NOT use:
        DINO patch tokens

    Recognition decision uses:
        absolute score
        margin to second-best candidate
    """

    VERSION = "3.3"

    HIGH_SCORE = 0.90
    PROBABLE_SCORE = 0.80

    HIGH_MARGIN = 0.03
    PROBABLE_MARGIN = 0.015

    def __init__(
        self,
        settings,
        embedder,
        manager,
    ):
        self.settings = settings
        self.embedder = embedder
        self.manager = manager

        self.analyzer = SceneAnalyzer(
            embedder,
            manager,
        )

    @classmethod
    def _confidence(
        cls,
        score,
        margin,
    ):
        score = float(score)
        margin = float(margin)

        if (
            score >= cls.HIGH_SCORE
            and margin >= cls.HIGH_MARGIN
        ):
            return "HIGH"

        if (
            score >= cls.PROBABLE_SCORE
            and margin >= cls.PROBABLE_MARGIN
        ):
            return "PROBABLE"

        if score >= cls.PROBABLE_SCORE:
            return "AMBIGUOUS"

        return "NO_MATCH"

    @staticmethod
    def _status_from_confidence(
        confidence,
    ):
        if confidence == "HIGH":
            return "CONFIDENT"

        if confidence == "PROBABLE":
            return "PROBABLE_MATCH"

        if confidence == "AMBIGUOUS":
            return "AMBIGUOUS"

        return "NO_MATCH"

    def recognize_folder(
        self,
        folder,
        top_k=5,
        threshold=0.65,
        workers=6,
        fingerprints=None,
    ):
        folder = Path(folder)

        paths = image_files(
            folder
        )

        if not paths:
            return []

        print(
            f"[Recognizer] "
            f"Query images: {len(paths)}"
        )

        loaded_fingerprints = []

        # Optional whitelist of fingerprints.
        # If provided, ONLY these fingerprints are used.
        if fingerprints is not None:
            allowed_fingerprints = {
                str(item).strip()
                for item in fingerprints
                if str(item).strip()
            }
        else:
            allowed_fingerprints = None

        for metadata in (
            self.manager.list_fingerprints()
        ):
            fingerprint_id = (
                metadata.get("id")
            )

            if not fingerprint_id:
                continue

            if (
                allowed_fingerprints is not None
                and str(fingerprint_id)
                not in allowed_fingerprints
            ):
                continue

            try:
                data = self.manager.load(
                    fingerprint_id
                )

            except (
                FileNotFoundError,
                ValueError,
                OSError,
            ) as exc:

                print(
                    f"[Recognizer] SKIP "
                    f"{fingerprint_id}: "
                    f"{exc}"
                )

                continue

            if str(
                data["metadata"].get(
                    "version",
                    "",
                )
            ) != self.VERSION:

                print(
                    f"[Recognizer] SKIP old "
                    f"fingerprint "
                    f"{fingerprint_id}"
                )

                continue

            loaded_fingerprints.append(
                (
                    fingerprint_id,
                    data,
                )
            )

        if not loaded_fingerprints:
            raise ValueError(
                "No compatible v3.3 compact "
                "fingerprints found."
            )

        print(
            "[Recognizer] Fingerprints: "
            + ", ".join(
                fp_id
                for fp_id, _ in loaded_fingerprints
            )
        )

        # One DINO pass for all query images.
        queries = self.embedder.embed_paths(
            paths
        )

        queries = np.asarray(
            queries,
            dtype=np.float32,
        )

        if queries.ndim == 1:
            queries = queries.reshape(
                1,
                -1,
            )

        results = []

        # Calculate CPU descriptors ONCE per image.
        # They do not depend on the fingerprint.
        #
        # Use CPU workers to process different images in parallel.
        def calculate_descriptors(path):
            path = Path(path)

            return (
                str(path),
                {
                    "environment": (
                        CompactDescriptor.environment(
                            path
                        )
                    ),
                    "color": (
                        CompactDescriptor.color(
                            path
                        )
                    ),
                    "spatial": (
                        CompactDescriptor.spatial(
                            path
                        )
                    ),
                },
            )

        worker_count = max(
            1,
            int(workers),
        )

        print(
            f"[Recognizer] CPU workers: "
            f"{worker_count}"
        )

        with ThreadPoolExecutor(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:41:19

Да. Теперь картина уже достаточно ясная.

**У нас сейчас DINO уже имеет встроенный `ThreadPoolExecutor` и по умолчанию `workers=6`.** То есть гипотезу про 6 CPU-воркеров не нужно придумывать заново — это уже существующая архитектура.

Но есть важный момент: **6 воркеров сейчас относятся не ко всему DINO**. В `recognize_folder()` сначала выполняется:

1. загрузка слепков;
2. **один общий DINO pass по всем фотографиям** через `embedder.embed_paths(paths)`;
3. затем CPU-дескрипторы (`environment/color/spatial`) распределяются между 6 потоками;
4. затем выполняется сравнение с fingerprint'ами.

То есть `workers=6` не означает «6 независимых DINO-моделей».

### Поэтому я бы сейчас не менял код

У нас есть хорошая точка для эксперимента:

- **DINO:** существующая реализация, `workers=6`;
- **Qwen:** GPU через Ollama;
- **preview:** отдельно, 1–2 CPU worker;
- **основные оригинальные файлы:** не перемещаем;
- **результаты:** в `output`;
- **ID:** присваиваем файлу независимо от физического перемещения.

И главное — мы уже получили очень интересный результат:

| Режим | 262 фото |
|---|---:|
| DINO CPU | **5.78 с** |
| DINO CUDA | **6.44 с** |

То есть на этом объёме **GPU пока даже не быстрее CPU**. Поэтому архитектурно имеет смысл проверить именно параллельную работу **DINO CPU + Qwen GPU**.

### Следующий эксперимент

Не надо пока переделывать pipeline.

Нужно запустить одновременно:

**терминал 1**
```bash
env SCENE_DEVICE=cpu \
uv run scene-fingerprint recognize data/input/test \
  --top-k 5 \
  --threshold 0.0 \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33,87_v33,88_v33,89_v33,90_v33,91_v33,92_v33,93_v33,94_v33,95_v33 \
  --json \
  > /tmp/dino_cpu_parallel.json
```

И одновременно **Qwen на том же наборе фотографий**, но лучше сначала измерить его отдельно.

После этого уже можно сделать настоящий тест:

> **DINO CPU + Qwen GPU одновременно**

и посмотреть:

- время DINO отдельно;
- время Qwen отдельно;
- время обоих одновременно;
- загрузку CPU;
- загрузку GPU;
- VRAM;
- RAM.

Если суммарное время параллельного запуска примерно равно `max(DINO, Qwen)`, значит наша идея работает отлично.

**И только после этого** будем решать, сколько давать DINO CPU workers: 6, 4, 8 и т.д.

А архитектуру я бы зафиксировал пока именно такую:

```text
ОРИГИНАЛЬНЫЕ ФОТО
       │
       ├──────────────► Qwen GPU
       │                  │
       │                  └── JSON
       │
       └──────────────► DINO CPU
                          │
                          └── ID
                               │
                               ├── виртуальная сортировка
                               ├── preview
                               ├── hash
                               └── metadata
                                      │
                                      ▼
                                  ОБЩАЯ БД
```

И это лучше прежней схемы `DINO → физическая сортировка → Qwen`: **Qwen вообще не должен зависеть от завершения DINO**.

При этом имя файла можно менять независимо, например:

```text
IMG_1234.jpg
       ↓
IMG_1234__ID_85_v33.jpg
```

но физически файл остаётся на месте. В базе при этом можно хранить:

```text
original_path
original_name
assigned_id
current_name
qwen_json
preview_path
hash
dino_score
timestamp
```

Это как раз позволит потом сделать **dry-run**, безопасное удаление preview/cache и восстановление/проверку оригиналов без риска для исходной фототеки.

---

### 👤 **User** — 2026-08-18 20:41:58

давай

---

### 🤖 **Assistant** — 2026-08-18 20:41:59

Да. Идём по порядку.

**Первый шаг — не меняем архитектуру и не трогаем кнопку.** Сначала измеряем Qwen отдельно на том же наборе `data/input/test`, чтобы потом корректно сравнить с DINO.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
/usr/bin/time -f '\nREAL_TIME=%E\nCPU=%P\nMAX_RSS=%M KB' \
.venv/bin/python scripts/qwen4b_output_v01.py \
  --input data/input/test \
  --output /tmp/qwen4b_speed_test
```

После завершения пришли **весь вывод**, особенно строки:

```text
[OLLAMA] ...
```

и в конце:

```text
REAL_TIME=
CPU=
MAX_RSS=
```

Пока **ничего не переделываем**.

После этого сделаем второй тест:

```text
DINO CPU
      +
QWEN GPU
      одновременно
```

и сравним:

```text
                    отдельно       параллельно
DINO CPU             ? сек           ?
Qwen GPU             ? сек           ?
DINO + Qwen                         ? сек
```

Если параллельный вариант действительно почти не замедляет ни один процесс, тогда уже спокойно строим новый режим обработки с **6 DINO workers + 1–2 preview workers + Qwen на GPU**.

---

### 👤 **User** — 2026-08-18 20:42:13

QWEN3-VL 4B — OUTPUT ANALYSIS
================================================================================

MODEL: qwen3-vl:4b-instruct
INPUT: /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test
OUTPUT: /tmp/qwen4b_speed_test
FOUND: 0
NUM_CTX: 16384
TEMPERATURE: 0

No images found.

REAL_TIME=0:00.09
CPU=98%
MAX_RSS=28928 KB
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:42:14

Да, здесь просто выяснилась одна вещь: **Qwen-скрипт не нашёл фотографии**, потому что `qwen4b_output_v01.py` ожидает свои аргументы/формат входа и в текущем запуске получил `FOUND: 0`.

Это не проблема Qwen и не результат теста скорости.

Нужно посмотреть нижнюю часть скрипта — там уже есть CLI и обработка `--input`. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '240,480p' scripts/qwen4b_output_v01.py
```

Пришли вывод.

После этого я дам **точную команду теста на тех же 262 фотографиях**, без изменения самого скрипта.

И пока важный вывод по предыдущему эксперименту сохраняется:

- DINO CPU: **5.78 с**
- DINO CUDA: **6.44 с**
- Qwen текущий тест: **не состоялся**, `FOUND: 0`

Так что пока вывод о параллельной загрузке GPU/CPU делать рано.

---

### 👤 **User** — 2026-08-18 20:42:34

MAX_RSS=28928 KB
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '240,480p' scripts/qwen4b_output_v01.py

            print(
                "[QWEN JSON ERROR]",
                repr(exc),
                "| attempt:",
                attempt,
                flush=True,
            )

            if attempt < MAX_ATTEMPTS:
                continue

            result = {
                "raw_answer": answer
            }

            result["_time_sec"] = round(elapsed, 2)
            return result

def find_images():

    files = []

    for path in INPUT_DIR.rglob("*"):

        if (
            path.is_file()
            and path.suffix.lower() in IMAGE_EXTENSIONS
        ):
            files.append(path)

    return sorted(files, key=lambda p: str(p).lower())

def output_path(source: Path) -> Path:

    relative = source.relative_to(INPUT_DIR)

    address = relative.parts[0]

    return (
        OUTPUT_DIR
        / address
        / f"{source.stem}.json"
    )

def process(files):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    total_start = time.time()

    results = []

    for index, source in enumerate(files, 1):

        destination = output_path(source)

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        print()
        print("=" * 80)
        print(
            f"[{index}/{len(files)}] "
            f"{source.parent.name}/{source.name}"
        )

        if destination.exists():

            try:
                existing = json.loads(
                    destination.read_text(
                        encoding="utf-8"
                    )
                )

                description = str(
                    existing.get("description") or ""
                ).strip()

            except Exception:
                description = ""

            if description:
                print("SKIP — metadata already exists")

                results.append({
                    "file": source.name,
                    "address": source.parent.name,
                    "status": "skipped",
                })

                continue

            print(
                "REPROCESS — description empty"
            )

        try:

            result = ask(source)

            result["address"] = source.parent.name
            result["source_file"] = str(
                source.relative_to(PROJECT)
            )

            with open(
                destination,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    result,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            elapsed = result.get(
                "_time_sec",
                0
            )

            print(
                "OK",
                "| time:",
                elapsed,
                "sec",
                "| client:",
                result.get("client", ""),
                "| brand:",
                result.get("brand", ""),
                "| confidence:",
                result.get("confidence", "")
            )

            quality = result.get(
                "image_quality",
                {}
            )

            print(
                "QUALITY:",
                quality.get("overall", ""),
                "| sharpness:",
                quality.get("sharpness", ""),
                "| banner:",
                quality.get("banner_visible", "")
            )

            environment = result.get(
                "environment",
                {}
            )

            print(
                "ENV:",
                environment.get("season", ""),
                "|",
                environment.get("weather", ""),
                "|",
                environment.get("precipitation", "")
            )

            results.append({
                "file": source.name,
                "address": source.parent.name,
                "status": "ok",
                "time_sec": elapsed,
                "client": result.get("client", ""),
                "brand": result.get("brand", ""),
                "category": result.get("category", ""),
                "confidence": result.get("confidence", ""),
            })

        except Exception as error:

            print(
                "ERROR:",
                error
            )

            results.append({
                "file": source.name,
                "address": source.parent.name,
                "status": "error",
                "error": str(error),
            })

    total_elapsed = round(
        time.time() - total_start,
        2
    )

    summary = {
        "model": MODEL,
        "input": str(INPUT_DIR),
        "output": str(OUTPUT_DIR),
        "files_in_run": len(files),
        "elapsed_sec": total_elapsed,
        "results": results,
    }

    with open(
        OUTPUT_DIR / "summary.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)
    print(
        "Processed:",
        sum(
            1
            for x in results
            if x["status"] == "ok"
        )
    )
    print(
        "Skipped:",
        sum(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:42:37

Вот теперь причина полностью понятна: **`find_images()` ищет относительно глобального `INPUT_DIR`**, а не относительно `--input`. Значит, передача `--input` в текущем скрипте либо вообще не реализована, либо внизу только меняет переменные после `find_images()`.

Нужно посмотреть последние ~100 строк, где находится `argparse` и `main()`.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
tail -n 120 scripts/qwen4b_output_v01.py
```

После этого я дам одну правильную команду.

И да — **сам скрипт пока не меняем**. Сначала разберём его CLI, затем замерим Qwen на тех же 262 фото.

Кстати, по архитектуре обнаружился ещё один важный момент: текущий Qwen работает **строго последовательно, по одному изображению**:

```text
for image:
    ask(image)
    сохранить JSON
```

То есть пока у него **1 worker**. Это даже хорошо для первого теста: сначала узнаем реальную скорость одного Qwen-потока на GPU, а уже потом проверим, имеет ли смысл 1 или 2 параллельных запроса к Ollama.

---

### 👤 **User** — 2026-08-18 20:42:52

int_mvp_v02 && \
tail -n 120 scripts/qwen4b_output_v01.py
        2
    )

    summary = {
        "model": MODEL,
        "input": str(INPUT_DIR),
        "output": str(OUTPUT_DIR),
        "files_in_run": len(files),
        "elapsed_sec": total_elapsed,
        "results": results,
    }

    with open(
        OUTPUT_DIR / "summary.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)
    print(
        "Processed:",
        sum(
            1
            for x in results
            if x["status"] == "ok"
        )
    )
    print(
        "Skipped:",
        sum(
            1
            for x in results
            if x["status"] == "skipped"
        )
    )
    print(
        "Errors:",
        sum(
            1
            for x in results
            if x["status"] == "error"
        )
    )
    print(
        "Total time:",
        total_elapsed,
        "sec"
    )

def main():

    global INPUT_DIR, OUTPUT_DIR

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only N images"
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_DIR,
        help="Input directory with sorted photos"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for Qwen metadata"
    )

    args = parser.parse_args()

    INPUT_DIR = args.input.expanduser().resolve()
    OUTPUT_DIR = args.output.expanduser().resolve()

    files = find_images()

    print("=" * 80)
    print("QWEN3-VL 4B — OUTPUT ANALYSIS")
    print("=" * 80)
    print()
    print("MODEL:", MODEL)
    print("INPUT:", INPUT_DIR)
    print("OUTPUT:", OUTPUT_DIR)
    print("FOUND:", len(files))
    print("NUM_CTX:", NUM_CTX)
    print("TEMPERATURE:", TEMPERATURE)
    print()

    if args.limit is not None:
        files = files[:args.limit]
        print("LIMIT:", args.limit)
        print()

    if not files:
        print("No images found.")
        return

    process(files)

if __name__ == "__main__":
    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:42:52

Да, теперь всё ясно. **`--input` работает правильно.** Предыдущий `FOUND: 0` означает просто, что в `data/input/test` на самом деле нет JPG/PNG/WebP на этом уровне/в этой структуре, а Qwen-скрипт ищет рекурсивно. Значит, надо дать ему **тот же каталог, который реально содержит фотографии**.

У нас в текущем pipeline после DINO сейчас фотографии попадают в результат Hybrid. Но для честного теста Qwen нам нужен каталог с теми же 262 оригиналами.

### 1. Сначала найдём, где лежат эти 262 фото

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
find data -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  | wc -l
```

И сразу:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
find data -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  | head -30
```

### Почему это важно

Мы хотим получить **один и тот же набор фотографий**:

```text
262 фото
   │
   ├── DINO CPU → замер
   │
   └── Qwen GPU → замер
```

а затем:

```text
262 фото
   │
   ├── DINO CPU ──────────┐
   │                      ├── одновременно
   └── Qwen GPU ──────────┘
```

И только после этого будем решать, как организовать реальные воркеры.

**Пока ничего в коде не меняем.** Сначала найдём правильный входной каталог.

---

### 👤 **User** — 2026-08-18 20:43:21

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
find data -type f \
  $ -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" $ \ 
  | wc -l
4347
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
find data -type f \
  $ -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" $ \ 
  | head -30
data/output/daily/20260816_230042/95_v33/Вавилова52_12.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_13.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_07.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_09.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_16.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_05.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_11.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_10.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_06.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_14.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_15.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_04.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_01.JPG
data/output/daily/20260816_230042/95_v33/Зорге_17.jpg
data/output/daily/20260816_230042/95_v33/Вавилова52_02.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_03.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_08.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_05.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_13.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_02.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_03.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_08.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_18.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_10.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_07.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_16.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_04.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_14.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_01.JPG
data/output/daily/20260816_230042/87_v33/Шеболдаева8_06.JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:43:22

Да. Теперь картина уже достаточно ясная. **Останавливаемся на этапе проектирования новой схемы и пока ничего не переписываем.**

Сейчас у нас фактически старая цепочка:

```text
КНОПКА в technical window
        ↓
photo_processing.py
        ↓
run_daily_hybrid_v12.sh
        ↓
DINO / Hybrid v12
        ↓
физическая сортировка
        ↓
data/output/daily/YYYYMMDD_HHMMSS/
        ↓
qwen4b_output_v01.py
        ↓
metadata/qwen4b/...
```

И это подтверждается кодом кнопки: она **ждёт завершения Hybrid**, получает `Output`, а только потом запускает Qwen с `--input result_dir`.

Но мы уже пришли к более правильной архитектуре.

### Новая схема

```text
                    ┌──────────────→ DINO / Hybrid → виртуальное присвоение адреса
                    │                         ↓
ОРИГИНАЛЬНЫЙ ФАЙЛ → ID ─────────────────→ результат DINO
                    │
                    ├──────────────→ Qwen3-VL → описание
                    │
                    └──────────────→ превью
                             
                              ↓
                       ОБЩАЯ БАЗА
                              ↓
                         GRID
```

При этом:

- **оригинальные фотографии физически остаются на месте**;
- независимый процесс сразу присваивает каждой фотографии `photo_id`;
- DINO работает с оригинальным файлом и определяет адрес;
- сортировка становится **виртуальной**, то есть `95_v33` — это атрибут/результат, а не обязательно физическая папка;
- Qwen получает **тот же `photo_id`**, но ему совершенно не нужно ждать DINO;
- превью создаются независимо;
- JSON/кэш/хэши/логи — в `output`;
- база постепенно получает данные от разных процессов;
- Grid может показывать уже готовые части результата.

И очень важный момент: **имя файла лучше не использовать как единственный ID**. Можно дополнительно дописывать адрес к имени, если это удобно для человека, но внутренним ключом должен быть стабильный `photo_id`.

---

### Что сейчас важно проверить

У нас уже есть подтверждение, что текущая `SceneRecognizer` имеет:

```text
workers=6
```

и использует:

```python
ThreadPoolExecutor(max_workers=worker_count)
```

То есть **6 воркеров уже предусмотрены на уровне recognizer**. Но есть важное отличие:

> 6 воркеров сейчас относятся к вычислению CPU-дескрипторов, а сам DINO embedding проходит отдельным батчем.

Поэтому просто сказать «поставим 6 воркеров DINO» пока неправильно. Мы сначала должны посмотреть, **как именно `run_hybrid_v12.py` вызывает recognizer и где там находится самый дорогой участок**.

И ещё: твой CPU/GPU тест дал интересный результат:

```text
CPU: 5.78 s
GPU: 6.44 s
```

для 262 фотографий в конкретном запуске. Поэтому пока **не надо заранее фиксировать 6 DINO workers**. Возможно, на реальном daily-потоке оптимальная схема будет другой.

---

## Следующий шаг

Сейчас я бы проверил **только три файла**, чтобы не гадать:

1. `scripts/run_daily_hybrid_v12.sh` — что именно запускает кнопка.
2. `scripts/run_hybrid_v12.py` — где происходит DINO/Hybrid и физическая сортировка.
3. `scripts/qwen4b_output_v01.py` — как лучше отвязать Qwen от сортировки.

Начнём с первого:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat scripts/run_daily_hybrid_v12.sh
```

Потом посмотрим ключевые части `run_hybrid_v12.py`.

**После этого уже решим, где вставить независимый `photo_id` и как превратить физическую сортировку в виртуальную, не ломая нынешний рабочий Hybrid v12.**

---

### 👤 **User** — 2026-08-18 20:43:56

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
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

---

### 🤖 **Assistant** — 2026-08-18 20:43:57

Отлично. Теперь видно точку входа целиком.

### Что происходит сейчас

Кнопка запускает:

```text
photo_processing.py
        ↓
run_daily_hybrid_v12.sh
        ↓
run_hybrid_v12.py
        ↓
Hybrid v12
        ↓
OUTPUT/YYYYMMDD_HHMMSS/
```

А уже **после полного завершения** `run_daily_hybrid_v12.py` кнопка запускает Qwen.

То есть сейчас у нас действительно есть искусственная зависимость:

```text
DINO ────────────────┐
                     ↓
                  сортировка
                     ↓
                    Qwen
```

А мы хотим:

```text
                    ┌──→ DINO → адрес
                    │
оригинал → photo_id ┼──→ Qwen → описание
                    │
                    └──→ preview
                           ↓
                    общая БД / GRID
```

---

## И самое важное

Я бы **не переделывал сразу `run_daily_hybrid_v12.py`**.

Этот файл сейчас очень простой и хороший:

```bash
INPUT="$PROJECT/data/input/daily"
OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"
```

Он всего лишь создаёт запуск и передаёт параметры:

```bash
--input "$INPUT"
--output "$OUTPUT"
--first-address 78
--last-address 95
```

Это удобно сохранить.

Лучше сделать так, чтобы он стал **оркестратором нового режима**, например:

```text
run_daily_v13.sh
       │
       ├── 1. ID / manifest
       │
       ├── 2. DINO worker
       │
       ├── 3. Qwen worker
       │
       ├── 4. Preview worker
       │
       └── 5. DB/index merge
```

При этом старый `run_daily_hybrid_v12.sh` **не трогаем**, пока новая схема не проверена.

---

### И ещё одна важная вещь из твоего последнего вывода

Сейчас в `data` уже лежит:

```text
data/output/daily/20260816_230042/95_v33/Вавилова52_12.JPG
data/output/daily/20260816_230042/95_v33/Вавилова52_13.JPG
...
data/output/daily/20260816_230042/87_v33/Шеболдаева8_05.JPG
```

То есть старый Hybrid действительно делает **физическую копию/сортировку по адресам**.

В новой архитектуре мы можем сохранить эту информацию, но представить её как:

```text
photo_id: 8f3a... 
original: data/input/daily/Вавилова52_12.JPG

dino:
    fingerprint: 95_v33
    address: ...
    score: ...
    status: ...

qwen:
    description: ...
    client: ...
    brand: ...
    
preview:
    path: ...

hash:
    sha256: ...
```

А Grid уже сам решает:

```text
выбран клиент
     ↓
адрес
     ↓
виртуальная выборка фотографий
```

**без физического перемещения фотографий.**

---

## Теперь следующий файл — самый важный

Давай посмотрим, где именно `run_hybrid_v12.py` делает:

- загрузку фотографий;
- DINO;
- определение адреса;
- физическое копирование;
- переименование;
- создание output.

Не надо пока весь файл.

Дай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,180p' scripts/run_hybrid_v12.py && \
echo "==================== PART 2 ====================" && \
sed -n '500,680p' scripts/run_hybrid_v12.py
```

После этого мы уже точно нарисуем **что оставить от Hybrid v12, а что вынести в новый независимый слой**.

---

### 👤 **User** — 2026-08-18 20:44:25

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ INPUT="$PROJECT/data/input/daily"
OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ^C

---

### 🤖 **Assistant** — 2026-08-18 20:44:26

Да, это просто случайно вставилась часть команды из предыдущего примера и shell её выполнил. Ничего страшного — **проект не изменился**.

Продолжаем. Выполни именно эту команду целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,180p' scripts/run_hybrid_v12.py && \
echo "==================== PART 2 ====================" && \
sed -n '500,680p' scripts/run_hybrid_v12.py
```

Нам сейчас нужно найти **границу между распознаванием DINO и физической сортировкой**. Именно там потом можно будет поставить независимый `photo_id` и сделать два параллельных потока:

```text
                    photo_id
                       │
             ┌─────────┴─────────┐
             ↓                   ↓
       DINO / Hybrid            Qwen
             ↓                   ↓
       virtual address       description
             │                   │
             └─────────┬─────────┘
                       ↓
                    БД / Grid
```

Пока **ничего в коде не меняем**. Сначала найдём точное место.

---

### 👤 **User** — 2026-08-18 20:44:39

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ^Ccd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,180p' scripts/run_hybrid_v12.py && \
echo "==================== PART 2 ====================" && \
sed -n '500,680p' scripts/run_hybrid_v12.py
Command 'cd' not found, did you mean:
  command 'bcd' from deb bsdgames (2.17-30)
  command 'hcd' from deb hfsutils (3.2.6-15build2)
  command 'mcd' from deb mtools (4.0.43-1)
Try: sudo apt install <deb name>
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:44:39

Да, вижу причину: `^C` оказался **перед `cd`**, поэтому shell получил что-то вроде `^Ccd` и воспринял это как команду `cd` с лишним символом.

Ничего не изменилось.

Давай без переноса строк — **одной командой**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && sed -n '1,180p' scripts/run_hybrid_v12.py && echo '==================== PART 2 ====================' && sed -n '500,680p' scripts/run_hybrid_v12.py
```

Просто скопируй строку целиком и нажми Enter.

---

### 👤 **User** — 2026-08-18 20:45:04

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && sed -n '1,180p' scripts/run_hybrid_v12.py && echo '==================== PART 2 ====================' && sed -n '500,680p' scripts/run_hybrid_v12.py
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
==================== PART 2 ====================
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

    input_dir = args.input
    output_dir = args.output

    if not input_dir.exists():
        raise RuntimeError(
            f"Нет папки: {input_dir}"
        )

    fingerprints = [
        f"{i}_v33"
        for i in range(
            args.first_address,
            args.last_address + 1,
        )
    ]

    print()
    print("=" * 80)
    print("SCENE FINGERPRINT — HYBRID V12 RUNNER")
    print("=" * 80)
    print()
    print("INPUT :", input_dir)
    print("OUTPUT:", output_dir)
    print()
    print("CONTROL:")
    print("  DINO        : v33")
    print("  HYBRID      : v12")
    print("  ADDRESSES   :", f"{args.first_address}-{args.last_address}")
    print()

    total_start = time.perf_counter()

    # --------------------------------------------------------
    # 1. DINO
    # --------------------------------------------------------

    recognition, recognition_time = run_recognition(
        input_dir,
        fingerprints,
    )

    # --------------------------------------------------------
    # 2. Load Hybrid subfingerprints
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("LOADING HYBRID SUBFINGERPRINTS")
    print("=" * 80)

    subs = load_subs()

    print("Subfingerprints:", len(subs))

    # --------------------------------------------------------
    # 3. Hybrid v12
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("HYBRID V12")
    print("=" * 80)

    settings = Settings()

    embedder = SceneEmbedder(
        settings
    )

    recognition = adapt_recognizer_rows(recognition)

    hybrid_rows, changed, sub_count = hybrid_v12(
        recognition,
        embedder,
        subs,
    )

    print()
    print("Checked:", len(hybrid_rows))
    print("Border cases:", sub_count)
    print("Hybrid changes:", len(changed))

    for item in changed:
        print()
        print(
            item["file"]
        )
        print(
            item["old"],
            "->",
            item["new"],
        )
        print(
            "margin:",
            item["margin"],
        )
        print(
            "neighbors:",
            item["neighbors"],
        )

    # --------------------------------------------------------
    # 4. Sort
    # --------------------------------------------------------

    sorted_rows, counters = sort_results(
        hybrid_rows,
        output_dir,
    )

    # --------------------------------------------------------
    # 5. Reports
    # --------------------------------------------------------

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    recognition_json = (
        output_dir / "recognition.json"
    )

    hybrid_json = (
        output_dir / "hybrid_v12.json"
    )

    report_json = (
        output_dir / "report.json"
    )

    statistics_json = (
        output_dir / "statistics.json"
    )

    recognition_json.write_text(
        json.dumps(
            recognition,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    hybrid_json.write_text(
        json.dumps(
            hybrid_rows,
            ensure_ascii=False,
            indent=2,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:45:05

Вот теперь мы точно нашли архитектурную границу. И она очень удачная для переделки.

Сейчас `run_hybrid_v12.py` делает **пять последовательных этапов**:

```text
1. DINO recognition
        ↓
2. загрузка subfingerprints
        ↓
3. Hybrid v12
        ↓
4. ФИЗИЧЕСКАЯ сортировка
        ↓
5. JSON-отчёты
```

Причём пункт 4 — это как раз тот отдельный слой, о котором ты говорил раньше.

### Поэтому Hybrid v12 трогать не надо

Нам нужно сохранить его контрольную логику:

```text
DINO v33
   ↓
Hybrid v12
   ↓
адрес
```

А вот это:

```text
адрес
 ↓
sort_results()
 ↓
копирование файлов по папкам
```

мы можем заменить на **виртуальное присвоение результата**.

И это хорошо согласуется с твоей новой идеей.

---

### Я бы сейчас сделал так

Независимый первый этап:

```text
ORIGINAL FILE
     ↓
photo_id
     ↓
manifest.json / SQLite
```

Например:

```json
{
  "photo_id": "p_000001",
  "source": "data/input/daily/Вавилова52_12.JPG",
  "sha256": "...",
  "original_name": "Вавилова52_12.JPG"
}
```

И **сразу после создания ID запускаются параллельно**:

```text
                 photo_id
                    │
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
       DINO                  QWEN
          │                   │
          ▼                   ▼
      address             description
          │                   │
          └─────────┬─────────┘
                    ▼
                  DB
```

А превью может идти третьим лёгким потоком:

```text
                 photo_id
                    │
             ┌──────┴──────┐
             ▼             ▼
            Qwen           Preview
```

---

### Причём `photo_id` лучше создать ДО DINO

Это решает сразу несколько проблем.

Если DINO работает 5–10 минут, Qwen работает независимо:

```text
photo_id 001 → Qwen → готово
photo_id 002 → Qwen → готово
photo_id 003 → Qwen → готово

photo_id 001 → DINO → 95_v33
photo_id 002 → DINO → 87_v33
...
```

База постепенно превращается из:

```text
photo_id | file | address | qwen | preview
```

в:

```text
001 | file | 95_v33 | ✓ | ✓
002 | file | 87_v33 | ✓ | ✓
003 | file | NULL   | ✓ | ✓
```

И Grid уже может работать даже при неполной обработке.

---

## Но перед изменениями нам надо посмотреть `sort_results()`

Это сейчас **ключевой кусок старой системы**. Именно его мы будем превращать из физической сортировки в виртуальную.

Дай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -B 15 -A 100 "def sort_results" scripts/run_hybrid_v12.py
```

После этого я покажу, **что именно из старого сортировщика сохраняем, а что заменяем**.

И пока ничего не меняем — сначала полностью разложим текущий pipeline.

---

### 👤 **User** — 2026-08-18 20:45:47

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -B 15 -A 100 "def sort_results" scripts/run_hybrid_v12.py
386-                    "file": Path(
387-                        row["file"]
388-                    ).name,
389-                    "old": old,
390-                    "new": best,
391-                    "margin": margin,
392-                    "neighbors": dict(neighbors),
393-                    "old_score": scores[old],
394-                    "new_score": scores[best],
395-                }
396-            )
397-
398-    return results, changed, sub_count
399-
400-
401:def sort_results(rows, output_dir):
402-    """
403-    Copy photos according to FINAL Hybrid best_id.
404-    """
405-
406-    print()
407-    print("=" * 80)
408-    print("SORTING")
409-    print("=" * 80)
410-
411-    output_dir.mkdir(
412-        parents=True,
413-        exist_ok=True,
414-    )
415-
416-    counters = Counter()
417-    sorted_rows = []
418-
419-    for item in rows:
420-
421-        source = Path(
422-            item["file"]
423-        )
424-
425-        assigned_id = item.get(
426-            "best_id"
427-        )
428-
429-        if not assigned_id:
430-            continue
431-
432-        destination_dir = (
433-            output_dir / assigned_id
434-        )
435-
436-        destination_dir.mkdir(
437-            parents=True,
438-            exist_ok=True,
439-        )
440-
441-        destination = (
442-            destination_dir / source.name
443-        )
444-
445-        shutil.copy2(
446-            source,
447-            destination,
448-        )
449-
450-        counters[assigned_id] += 1
451-
452-        sorted_rows.append(
453-            {
454-                "file": str(source),
455-                "filename": source.name,
456-                "assigned_id": assigned_id,
457-                "original_best_id": item.get(
458-                    "original_best_id"
459-                ),
460-                "hybrid_changed": item.get(
461-                    "hybrid_changed"
462-                ),
463-                "score": item.get("score"),
464-                "second_score": item.get(
465-                    "second_score"
466-                ),
467-                "margin": item.get("margin"),
468-                "confidence": item.get(
469-                    "confidence"
470-                ),
471-                "status": item.get("status"),
472-                "best_image": item.get(
473-                    "best_image"
474-                ),
475-                "best_image_score": item.get(
476-                    "best_image_score"
477-                ),
478-                "hybrid_old_score": item.get(
479-                    "hybrid_old_score"
480-                ),
481-                "hybrid_score": item.get(
482-                    "hybrid_score"
483-                ),
484-            }
485-        )
486-
487-    for k in sorted(
488-        counters,
489-        key=lambda x: int(
490-            x.split("_")[0]
491-        ),
492-    ):
493-        print(
494-            f"{k:10s} {counters[k]:4d}"
495-        )
496-
497-    return sorted_rows, counters
498-
499-
500-def main():
501-
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:45:48

Да. Теперь всё окончательно сходится.

### Что делает старый `sort_results()`

Он **не сортирует алгоритмически**. DINO + Hybrid уже приняли решение:

```text
best_id = 95_v33
```

А `sort_results()` делает только физическое действие:

```python
shutil.copy2(source, destination)
```

то есть:

```text
data/input/daily/Вавилова52_12.JPG
        ↓
data/output/daily/20260816_230042/95_v33/Вавилова52_12.JPG
```

И именно **этот кусок нам больше не нужен как обязательный этап**.

---

# Новая логика

Я бы сейчас зафиксировал архитектуру именно так.

```text
                   ORIGINAL
                      │
                      ▼
                ┌───────────┐
                │ PHOTO ID  │
                └─────┬─────┘
                      │
             photo_id + source
                      │
          ┌───────────┼────────────┐
          │           │            │
          ▼           ▼            ▼
        DINO         QWEN        PREVIEW
          │           │            │
          ▼           ▼            ▼
      best_id      metadata      preview
          │           │            │
          └───────────┼────────────┘
                      ▼
                 PHOTO DB
                      │
                      ▼
                    GRID
```

### DINO

Оставляем практически неизменным:

```text
DINO v33
   ↓
Hybrid v12
   ↓
best_id
```

То есть вся проверенная логика распознавания остаётся.

### Что меняем

Вместо:

```python
shutil.copy2(source, destination)
```

будет примерно:

```text
photo_id
source
assigned_id
score
confidence
status
...
```

записано в индекс/БД.

Это и есть **виртуальная сортировка**.

---

# И вот здесь появляется важная вещь, которую ты вспомнил

Ты говорил про **безопасное/умное удаление превью и файлов**.

Я бы это разделил на два совершенно разных понятия.

### 1. Оригиналы

```text
data/input/daily
```

**Никогда автоматически не удаляем.**

Система работает с ними как с источником истины.

Даже если:

- DINO ошибся;
- Qwen ошибся;
- пользователь удалил запись из Grid;
- пересоздали превью;
- изменили алгоритм.

Оригинал остаётся.

---

### 2. Производные данные

А вот это можно удалять/пересоздавать:

```text
output/
    previews/
    cache/
    qwen/
    dino/
    logs/
    json/
    hashes/
```

Причём безопасно:

```text
оригинал
   ↑
   │
photo_id
   │
   ├── preview
   ├── qwen json
   ├── dino json
   ├── cache
   └── hash
```

Если удалить preview — **ничего не потеряно**, его можно создать заново.

Если удалить Qwen JSON — описание можно пересчитать.

Если удалить DINO cache — распознавание можно повторить.

---

# И поэтому я бы добавил ещё один принцип

**ID должен быть независимым от имени файла.**

Например:

```text
photo_id = 01J....
```

или другой стабильный UUID.

Тогда можно даже сделать:

```text
Вавилова52_12.JPG
```

→

```text
Вавилова52_12__p01JABC....JPG
```

если тебе хочется видеть ID непосредственно в имени.

Но база всё равно должна ориентироваться на:

```text
photo_id
```

а не на filename.

---

## И ещё одна хорошая новость

Текущий `sort_results()` уже формирует почти готовую структуру данных:

```python
{
    "file": str(source),
    "filename": source.name,
    "assigned_id": assigned_id,
    "original_best_id": ...,
    "hybrid_changed": ...,
    "score": ...,
    "second_score": ...,
    "margin": ...,
    "confidence": ...,
    "status": ...,
    "best_image": ...,
    "best_image_score": ...,
    "hybrid_old_score": ...,
    "hybrid_score": ...
}
```

То есть нам **не надо заново придумывать результат DINO**.

Мы можем оставить эту структуру как основу записи в БД.

---

### Сейчас я бы НЕ трогал код.

Следующий шаг — посмотреть, **откуда `item["file"]` приходит и какой там полный путь**, потому что для новой архитектуры именно там надо аккуратно добавить `photo_id`.

Дай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -B 20 -A 80 "def adapt_recognizer_rows" scripts/run_hybrid_v12.py
```

Это будет последний кусок, который нам нужен, чтобы понять полный путь:

**оригинал → DINO → Hybrid → результат → виртуальная сортировка.**

---

### 👤 **User** — 2026-08-18 20:47:17

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -B 20 -A 80 "def adapt_recognizer_rows" scripts/run_hybrid_v12.py
159-            )
160-
161-            if isinstance(candidate, list):
162-                data = candidate
163-                break
164-
165-        except json.JSONDecodeError:
166-            pass
167-
168-    if data is None:
169-        raise RuntimeError(
170-            "Не удалось найти JSON-массив в выводе recognition"
171-        )
172-
173-    print("Images:", len(data))
174-    print(f"Recognition time: {elapsed:.2f} sec")
175-
176-    return data, elapsed
177-
178-
179:def adapt_recognizer_rows(rows):
180-    """
181-    Convert current recognizer output into the legacy
182-    top1..top5 format required by frozen Hybrid v12.
183-    """
184-
185-    adapted = []
186-
187-    for row in rows:
188-        item = dict(row)
189-
190-        candidates = row.get("candidates", [])
191-
192-        for n in range(1, 6):
193-            item[f"top{n}"] = None
194-            item[f"top{n}_score"] = 0.0
195-
196-        for n, candidate in enumerate(candidates[:5], start=1):
197-            item[f"top{n}"] = candidate.get("id")
198-            item[f"top{n}_score"] = float(
199-                candidate.get("score", 0.0)
200-            )
201-
202-        adapted.append(item)
203-
204-    return adapted
205-
206-
207-def hybrid_v12(rows, embedder, subs):
208-    """
209-    Exact production adaptation of the frozen Hybrid v12 logic.
210-
211-    Input:
212-        recognizer rows containing top1..top5.
213-
214-    Output:
215-        rows with final best_id.
216-    """
217-
218-    changed = []
219-    results = []
220-    sub_count = 0
221-
222-    for i, row in enumerate(rows):
223-
224-        old = row.get("top1")
225-
226-        scores = defaultdict(float)
227-
228-        # ====================================================
229-        # GLOBAL TOP-5
230-        # ====================================================
231-
232-        for k in range(1, 6):
233-
234-            fp = row.get(f"top{k}")
235-            sc = row.get(f"top{k}_score")
236-
237-            if fp:
238-                scores[fp] += (
239-                    float(sc)
240-                    * GLOBAL_WEIGHT
241-                )
242-
243-        # ====================================================
244-        # SUB ONLY BORDER CASES
245-        # ====================================================
246-
247-        margin = row.get(
248-            "margin",
249-            1,
250-        )
251-
252-        if margin < MARGIN_LIMIT:
253-
254-            sub_count += 1
255-
256-            image = Path(
257-                row["file"]
258-            )
259-
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:47:19

Да. Теперь картина достаточно ясная.

**Сейчас узкое место действительно DINO**, а архитектура `run_hybrid_v12.py` пока последовательная:

1. DINO recognition.
2. загрузка subfingerprints.
3. Hybrid v12.
4. физическое копирование фото по папкам.
5. отчёты.

Причём сортировка сейчас вообще не вычислительная - она делает `shutil.copy2()` для каждого файла. 

А самое важное: `adapt_recognizer_rows()` уже превращает результат DINO в строки, которые можно использовать как основу общей записи. 

### Я бы сделал именно тот режим, который мы обсуждали

Не менять существующий `HYBRID V12`, а добавить **параллельный production-режим**:

```text
                    НОВЫЕ ФОТО
                         │
                         ▼
                [ID / регистрация]
                         │
             ┌───────────┴───────────┐
             │                       │
             ▼                       ▼
       DINO pipeline             QWEN pipeline
       6 workers ?               GPU
             │                       │
       recognition              description
       hybrid v12                quality
       virtual sorting           environment
             │                       │
             └───────────┬───────────┘
                         ▼
                    PHOTO DB
```

### Ключевой момент - ID

**ID должен появляться до DINO и Qwen.**

Причём это должен быть не `78_v33`, не результат распознавания и вообще не результат AI.

Например:

```text
photo_id = 20260818_000001
```

И для каждого оригинального файла создаём запись:

```json
{
  "photo_id": "20260818_000001",
  "original_file": ".../Вавилова52_12.JPG",
  "original_name": "Вавилова52_12.JPG",
  "created_at": "...",
  "dino": null,
  "qwen": null
}
```

После этого два процесса могут совершенно независимо дописывать:

```json
"dino": {
    "best_id": "95_v33",
    "score": 0.91,
    "status": "CONFIDENT"
}
```

и:

```json
"qwen": {
    "description": "...",
    "quality": {...},
    "environment": {...}
}
```

### И тогда физически сортировать фото вообще необязательно

Вот это особенно хорошо совпадает с тем, что мы обсуждали раньше.

Вместо:

```text
output/
 ├── 95_v33/
 │    ├── Вавилова52_12.JPG
 │    └── ...
 ├── 87_v33/
 └── ...
```

можно иметь:

```text
photo_db/
    photos.sqlite
```

и:

```text
photo_id
original_path
original_name
dino_address
dino_score
qwen_description
qwen_quality
preview_path
...
```

А интерфейс уже **виртуально показывает**:

```text
95_v33
 ├── Вавилова52_12.JPG
 ├── Вавилова52_13.JPG
 └── ...
```

То есть папка `95_v33` фактически не существует - это фильтр базы.

---

### По ресурсам

Твой вариант:

```text
DINO + подготовка/сортировка     6 workers
Preview                           1-2 workers
Qwen3-VL 4B                      GPU
```

логичный как **первый режим тестирования**.

Но я бы сделал число DINO workers параметром:

```bash
--dino-workers 6
```

чтобы потом легко проверить:

```text
4
6
8
10
```

Потому что наши текущие результаты показывают интересную вещь:

- CPU DINO: **5.78 с**
- GPU DINO: **6.44 с**

Это на тестовых 262 фотографиях и с текущей реализацией. То есть GPU сейчас **не ускорил весь recognition**, потому что большая часть работы после embedding идёт через CPU. В `recognizer.py` прямо предусмотрен `ThreadPoolExecutor`, причём descriptor calculation выполняется по изображениям параллельно.  

Поэтому прежде чем фиксировать `6`, имеет смысл сделать **короткий benchmark 4/6/8 workers**. Тогда мы увидим, где у нас реальный оптимум.

И ещё: Qwen сейчас не нашёл изображения просто потому, что ты дал ему `data/input/test`, а реальные JPG у тебя находятся в `data/output/daily/...`. Сам скрипт Qwen ищет изображения рекурсивно внутри указанного `INPUT_DIR`, так что проблема была именно в пути, а не в модели.

**Следующий шаг я бы сделал очень маленьким:** не трогать DINO/Hybrid v12, а сначала добавить независимый `photo_id` + единый `photos.jsonl`/SQLite и научить оба процесса дописывать результат по этому ID. После этого уже подключаем параллельный Qwen и виртуальную сортировку.

---

### 👤 **User** — 2026-08-18 20:47:59

огласен

---

### 🤖 **Assistant** — 2026-08-18 20:47:59

Да. Тогда **замораживаем эту архитектуру**.

### Первый этап

Делаем независимый слой регистрации:

```text
оригинальный файл
      ↓
PHOTO_ID
      ↓
единая запись о фотографии
      ↓
 ┌───────────────┬───────────────┐
 │               │               │
 DINO            QWEN            Preview
 │               │               │
 результат       описание        миниатюра
 │               │               │
 └───────────────┴───────────────┘
             ↓
        единая БД
```

**Важно:** ни DINO, ни Qwen не создают ID.

### Предлагаю сразу SQLite

Для 4–5 тысяч фотографий и дальнейшего роста это удобнее JSONL.

Минимальная таблица:

```text
photos
------------------------------------------------
id
original_path
original_name
file_size
file_mtime
created_at

dino_status
dino_address
dino_score
dino_margin
dino_confidence

qwen_status
qwen_description
qwen_client
qwen_brand
qwen_category
qwen_confidence

preview_status
preview_path
```

И ещё отдельные поля/таблицы потом можно добавить для:

- хэшей;
- fingerprint;
- subfingerprint;
- OCR;
- баннеров;
- технических параметров;
- истории обработки.

### Главное преимущество

После регистрации:

```text
photo_id = 000001
```

DINO может закончить через 5 секунд, Qwen — через условные 10–30 секунд, preview — ещё отдельно.

База постепенно превращается из:

```text
000001 → зарегистрирован
```

в:

```text
000001
 ├── DINO ✓
 ├── QWEN ✓
 ├── PREVIEW ✓
 └── READY
```

И UI сможет **сразу показывать фотографию**, не дожидаясь окончания всей обработки.

А `95_v33` будет уже не физическим местом хранения, а **результатом классификации/виртуальной группировкой**.

Следующим шагом я бы сделал именно **регистратор фотографий + SQLite**, не трогая пока существующий `run_hybrid_v12.py`. После этого аккуратно подключим к нему DINO и Qwen.

---

### 👤 **User** — 2026-08-18 20:48:36

у меня используется postgresql с квен

---

