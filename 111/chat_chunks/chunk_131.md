## СЕССИЯ: вторник

**Создано:** 2026-08-18 18:12:03
**Обновлено:** 2026-08-22 20:16:20
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1)

---

### 👤 **User** — 2026-08-18 21:41:07

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,340p' app/core/recognizer.py
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
            max_workers=worker_count
        ) as executor:

            descriptor_results = executor.map(
                calculate_descriptors,
                paths,
            )

            query_descriptors = dict(
                descriptor_results
            )

        for path, query_embedding in zip(
            paths,
            queries,
        ):
            ranked = []

            descriptors = query_descriptors[
                str(path)
            ]

            for fingerprint_id, data in loaded_fingerprints:

                # First use the analyzer.
                # This calculates the full v3.3 score.
                try:
                    score = self.analyzer.compare(
                        Path(path),
                        fingerprint_id,
                        query_global=query_embedding,
                        query_environment=descriptors[
                            "environment"
                        ],
                        query_color=descriptors[
                            "color"
                        ],
                        query_spatial=descriptors[
                            "spatial"
                        ],
                    )

                except (
                    FileNotFoundError,
                    ValueError,
                    OSError,
                ) as exc:

                    print(
                        f"[Recognizer] SKIP "
                        f"{fingerprint_id} "
                        f"for "
                        f"{Path(path).name}: "
                        f"{exc}"
                    )

                    continue

                ranked.append(
                    {
                        "id": fingerprint_id,

                        "score": float(
                            score.get(
                                "final_score",
                                0.0,
                            )
                        ),

                        "global": float(
                            score.get(
                                "global_score",
                                0.0,
                            )
                        ),

                        "environment": float(
                            score.get(
                                "environment_score",
                                0.0,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE "recognize|candidates|top1|margin|dino_score|dino_second_score" \
app scripts \
--include="*.py" | head -150
app/web/components/technical_modules/data.py:88:    candidates = []
app/web/components/technical_modules/data.py:93:        candidates.append(root_summary)
app/web/components/technical_modules/data.py:96:        candidates.extend(
app/web/components/technical_modules/data.py:102:    if not candidates:
app/web/components/technical_modules/data.py:114:        candidates,
app/web/components/technical_modules/qwen.py:33:    candidates = []
app/web/components/technical_modules/qwen.py:38:        candidates.append(root_summary)
app/web/components/technical_modules/qwen.py:42:        candidates.extend(
app/web/components/technical_modules/qwen.py:48:    if not candidates:
app/web/components/technical_modules/qwen.py:52:        candidates,
app/web/components/photos.py:530:                # RECOGNIZED INFORMATION
app/web/frontend_v02.py:90:    margin: 0;
app/web/frontend_v02.py:116:    margin-top: 4px;
app/web/frontend_v01_backup_before_modular.py:49:    margin: 0;
app/web/frontend_v01_backup_before_modular.py:86:    margin-top: 5px;
app/web/frontend_v01.py:49:    margin: 0;
app/web/frontend_v01.py:86:    margin-top: 5px;
app/core/scene_analyzer.py:377:        supplied already calculated by the recognizer.
app/core/recognizer.py:15:class SceneRecognizer:
app/core/recognizer.py:17:    Scene Fingerprint v3.3 compact recognizer.
app/core/recognizer.py:30:        margin to second-best candidate
app/core/recognizer.py:38:    HIGH_MARGIN = 0.03
app/core/recognizer.py:39:    PROBABLE_MARGIN = 0.015
app/core/recognizer.py:60:        margin,
app/core/recognizer.py:63:        margin = float(margin)
app/core/recognizer.py:67:            and margin >= cls.HIGH_MARGIN
app/core/recognizer.py:73:            and margin >= cls.PROBABLE_MARGIN
app/core/recognizer.py:97:    def recognize_folder(
app/core/recognizer.py:115:            f"[Recognizer] "
app/core/recognizer.py:161:                    f"[Recognizer] SKIP "
app/core/recognizer.py:176:                    f"[Recognizer] SKIP old "
app/core/recognizer.py:197:            "[Recognizer] Fingerprints: "
app/core/recognizer.py:256:            f"[Recognizer] CPU workers: "
app/core/recognizer.py:310:                        f"[Recognizer] SKIP "
app/core/recognizer.py:392:                        "margin": 0.0,
app/core/recognizer.py:395:                        "candidates": [],
app/core/recognizer.py:414:            margin = (
app/core/recognizer.py:422:                    margin,
app/core/recognizer.py:459:                    "margin": float(
app/core/recognizer.py:460:                        margin
app/core/recognizer.py:478:                    "candidates": ranked,
app/core/recognizer.py:484:    def recognize(
app/core/recognizer.py:490:        return self.recognize_folder(
app/main.py:6:from app.core.recognizer import SceneRecognizer
app/main.py:10:recognizer = SceneRecognizer(settings, embedder, manager)
app/main.py:19:        recognize_tab = ui.tab("Распознавание")
app/main.py:38:        with ui.tab_panel(recognize_tab):
app/main.py:48:                    rows = recognizer.recognize_folder(
app/main.py:58:                            for c in row["candidates"]:
app/web_v01_backup_20260816_142053/frontend_v02.py:90:    margin: 0;
app/web_v01_backup_20260816_142053/frontend_v02.py:116:    margin-top: 4px;
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:49:    margin: 0;
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:86:    margin-top: 5px;
app/web_v01_backup_20260816_142053/frontend_v01.py:49:    margin: 0;
app/web_v01_backup_20260816_142053/frontend_v01.py:86:    margin-top: 5px;
app/cli.py:11:from app.core.recognizer import SceneRecognizer
app/cli.py:124:    # RECOGNIZE
app/cli.py:127:    recognize_parser = subparsers.add_parser(
app/cli.py:128:        "recognize",
app/cli.py:129:        help="Recognize images",
app/cli.py:132:    recognize_parser.add_argument(
app/cli.py:137:    recognize_parser.add_argument(
app/cli.py:141:        help="Number of candidates",
app/cli.py:144:    recognize_parser.add_argument(
app/cli.py:151:    recognize_parser.add_argument(
app/cli.py:158:    recognize_parser.add_argument(
app/cli.py:165:    recognize_parser.add_argument(
app/cli.py:256:    margin = float(
app/cli.py:258:            "margin",
app/cli.py:289:        f"MARGIN       "
app/cli.py:290:        f"{margin:.4f}"
app/cli.py:313:    candidates = result.get(
app/cli.py:314:        "candidates",
app/cli.py:318:    if candidates:
app/cli.py:321:            "TOP CANDIDATES"
app/cli.py:325:            candidates,
app/cli.py:589:    # RECOGNIZE
app/cli.py:592:    if args.command == "recognize":
app/cli.py:613:        recognizer = SceneRecognizer(
app/cli.py:629:            recognizer.recognize_folder(
app/ocr/ocr_pipeline.py:40:    def recognize(self, image_path: str | Path) -> list[OCRResult]:
app/ocr/ocr_pipeline.py:102:    results = ocr.recognize(
app/ocr/plate_detector.py:69:    candidates = []
app/ocr/plate_detector.py:109:        candidates.append(
app/ocr/plate_detector.py:121:    candidates.sort(
app/ocr/plate_detector.py:129:    for index, candidate in enumerate(candidates):
app/ocr/plate_detector.py:167:    return candidates
app/ocr/plate_detector.py:172:        description="Detect white rectangular plate candidates"
app/ocr/plate_detector.py:182:        default="data/ocr_debug/plate_candidates.jpg",
app/ocr/plate_detector.py:188:    candidates = detect_white_rectangles(
app/ocr/plate_detector.py:198:    print(f"Candidates: {len(candidates)}")
app/ocr/plate_detector.py:200:    for i, candidate in enumerate(candidates, 1):
scripts/sort_neighbor_v35_benchmark.py:18:MARGIN_LIMIT = 0.005
scripts/sort_neighbor_v35_benchmark.py:53:    for key in ("top1", "top2", "top3", "top4", "top5"):
scripts/sort_neighbor_v35_benchmark.py:82:    print(f"Margin limit : {MARGIN_LIMIT}")
scripts/sort_neighbor_v35_benchmark.py:93:        current = norm_id(row.get("top1"))
scripts/sort_neighbor_v35_benchmark.py:96:        top1_score = float(row.get("top1_score") or 0)
scripts/sort_neighbor_v35_benchmark.py:99:        margin = top1_score - top2_score
scripts/sort_neighbor_v35_benchmark.py:107:        if margin < MARGIN_LIMIT and second is not None:
scripts/sort_neighbor_v35_benchmark.py:119:                n_candidates = candidate_ids(neighbor)
scripts/sort_neighbor_v35_benchmark.py:121:                if second in n_candidates:
scripts/sort_neighbor_v35_benchmark.py:126:                if current in n_candidates:
scripts/sort_neighbor_v35_benchmark.py:160:                "margin": margin,
scripts/sort_neighbor_v35_benchmark.py:171:            "margin": margin,
scripts/sort_neighbor_v35_benchmark.py:202:                "margin",
scripts/sort_neighbor_v35_benchmark.py:244:    margin_count = sum(
scripts/sort_neighbor_v35_benchmark.py:245:        float(d["margin"]) < MARGIN_LIMIT
scripts/sort_neighbor_v35_benchmark.py:254:    print(f"Margin < {MARGIN_LIMIT}:      {margin_count}")
scripts/sort_neighbor_v35_benchmark.py:269:                f"    margin={x['margin']:.6f}"
scripts/benchmark_sub_rerank_v04.py:156:        top_candidates = [
scripts/benchmark_sub_rerank_v04.py:157:            row["top1"],
scripts/benchmark_sub_rerank_v04.py:176:        best_parent = row["top1"]
scripts/benchmark_sub_rerank_v04.py:177:        best_score = row["top1_score"]
scripts/benchmark_sub_rerank_v04.py:182:        for parent in top_candidates:
scripts/benchmark_sub_rerank_v04.py:211:                        row["top1_score"]
scripts/benchmark_sub_rerank_v04.py:228:        if best_parent != row["top1"]:
scripts/benchmark_sub_rerank_v04.py:233:                    "old": row["top1"],
scripts/benchmark_sub_rerank_v04.py:237:                    "old_score": row["top1_score"],
scripts/benchmark_sub_rerank_v04.py:241:                        row["top1_score"]
scripts/sort_test_and_report_v2.py:67:        [Recognizer]
scripts/sort_test_and_report_v2.py:99:        "recognize",
scripts/sort_test_and_report_v2.py:133:            f"recognize завершился с кодом {process.returncode}"
scripts/sort_test_and_report_v2.py:179:        candidates = item.get("candidates", [])
scripts/sort_test_and_report_v2.py:187:            "margin": item.get("margin"),
scripts/sort_test_and_report_v2.py:206:        if candidates:
scripts/sort_test_and_report_v2.py:207:            c = candidates[0]
scripts/sort_test_and_report_v2.py:214:        for n in range(1, min(5, len(candidates))):
scripts/sort_test_and_report_v2.py:215:            c = candidates[n]
scripts/sort_test_and_report_v2.py:237:        "margin",
scripts/sort_test_and_report_v2.py:267:    margins = [
scripts/sort_test_and_report_v2.py:268:        float(x["margin"])
scripts/sort_test_and_report_v2.py:270:        if x["margin"] is not None
scripts/sort_test_and_report_v2.py:306:        "margin": {
scripts/sort_test_and_report_v2.py:307:            "min": min(margins) if margins else None,
scripts/sort_test_and_report_v2.py:308:            "mean": sum(margins) / len(margins) if margins else None,
scripts/sort_test_and_report_v2.py:309:            "max": max(margins) if margins else None,
scripts/sort_test_and_report_v2.py:408:    print("MARGIN")
scripts/sort_test_and_report_v2.py:409:    print(f"  min:              {stats['margin']['min']:.4f}")
scripts/sort_test_and_report_v2.py:410:    print(f"  mean:             {stats['margin']['mean']:.4f}")
scripts/sort_test_and_report_v2.py:411:    print(f"  max:              {stats['margin']['max']:.4f}")
scripts/make_subfingerprints_v2.py:146:        candidates = [
scripts/make_subfingerprints_v2.py:152:        if len(candidates) > MAX_CORE:
scripts/make_subfingerprints_v2.py:153:            candidates = sorted(
scripts/make_subfingerprints_v2.py:154:                candidates,
scripts/make_subfingerprints_v2.py:161:        if len(candidates) < MIN_CORE:
scripts/make_subfingerprints_v2.py:167:            "members": sorted(candidates),
scripts/make_subfingerprints_v2.py:174:        for i in candidates:
scripts/benchmark_test_v1.py:93:        "recognize",
scripts/benchmark_test_v1.py:126:            f"recognize failed: {proc.returncode}"
scripts/benchmark_test_v1.py:184:        candidates = x.get("candidates", [])
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:41:08

Да, теперь картина ясная. **Существующий `SceneRecognizer v3.3` можно использовать как основу, но для очереди лучше не вызывать `recognize_folder()` на каждый файл.**

У нас уже видно главное:

- DINO embedding сейчас действительно идёт через `SceneEmbedder`;
- текущая версия — **v3.3 compact**;
- `embed_paths()` может обработать изображение;
- затем `SceneAnalyzer.compare()` считает полный v3.3 score;
- результат уже содержит `score`, `margin`, `candidates`;
- CPU-дескрипторы сейчас считаются через `ThreadPoolExecutor(max_workers=6)`;
- для фонового обработчика нам нужен **один постоянно живущий worker**, который загрузит DINO один раз и будет последовательно брать `pending`.

### Я бы сейчас сделал так

```text
                    PostgreSQL
                         │
              ┌──────────┴──────────┐
              │                     │
        dino_status=pending   qwen_status=pending
              │                     │
              ▼                     ▼
       DINO WORKER             QWEN WORKER
       1 процесс               1 процесс
       CPU                     GPU
              │                     │
              └──────────┬──────────┘
                         ▼
                    photos
```

Причём **DINO и Qwen независимы**.

Для одной фотографии:

```text
PH_00000527
      │
      ├──────► DINO ──► dino_status=ok
      │
      └──────► QWEN ──► qwen_status=ok
```

А не:

```text
DINO → Qwen → следующая
```

---

## Но есть важная оптимизация

Текущий `recognize_folder()` делает:

1. загружает все fingerprints;
2. делает DINO для всех фотографий;
3. считает descriptors для всех фотографий;
4. сравнивает каждую фотографию со всеми fingerprints.

Для интегратора это избыточно.

Нам нужен метод примерно такого вида:

```text
recognize_one(path)
```

который:

- получает **один файл**;
- делает один DINO embedding;
- считает нужные compact descriptors;
- сравнивает со всеми уже загруженными fingerprint'ами;
- возвращает тот же результат, что нынешний recognizer;
- ничего не знает о PostgreSQL.

А worker уже занимается базой:

```text
SELECT ... FOR UPDATE SKIP LOCKED
```

→ получил одну фотографию

→ `recognize_one()`

→ записал:

```text
dino_status
dino_fingerprint
dino_score
dino_second_score
dino_margin
dino_time_sec
```

---

## И ещё лучше: DINO загружаем один раз

При старте:

```text
DinoWorker
   ↓
SceneEmbedder
   ↓
загрузка facebook/dinov2-base
   ↓
SceneRecognizer
   ↓
[готов]
```

После этого:

```text
PH_00000001 → обработать
PH_00000002 → обработать
PH_00000003 → обработать
...
PH_00000526 → обработать
```

Без повторной загрузки модели.

И когда появится новая фотография:

```text
PH_00000527 → pending
```

worker её увидит и обработает.

То есть это уже практически **постоянный конвейер**.

### А Qwen аналогично

Qwen через Ollama:

```text
QwenWorker
   ↓
localhost:11434
   ↓
qwen3-vl:4b-instruct
   ↓
GPU
```

Модель также не надо запускать отдельным процессом на каждую фотографию. Ollama сама держит модель загруженной некоторое время.

---

### Следующее действие

Нам теперь нужно увидеть **остаток `recognizer.py` с 330-й строки**, потому что именно там находится точная логика формирования `margin`, `confidence` и `candidates`.

Выполни:

```bash id="r8f4m2"
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '330,510p' app/core/recognizer.py
```

После этого я дам **готовый `recognize_one()` + первый `dino_worker.py`**, не меняя существующий алгоритм v3.3.

---

### 👤 **User** — 2026-08-18 21:42:22

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '330,510p' app/core/recognizer.py
                        "global": float(
                            score.get(
                                "global_score",
                                0.0,
                            )
                        ),

                        "environment": float(
                            score.get(
                                "environment_score",
                                0.0,
                            )
                        ),

                        "color": float(
                            score.get(
                                "color_score",
                                0.0,
                            )
                        ),

                        "spatial": float(
                            score.get(
                                "spatial_score",
                                0.0,
                            )
                        ),

                        "best_image": score.get(
                            "best_image"
                        ),

                        "best_image_score": float(
                            score.get(
                                "best_image_score",
                                0.0,
                            )
                        ),
                    }
                )

            ranked.sort(
                key=lambda item: item[
                    "score"
                ],
                reverse=True,
            )

            ranked = ranked[
                :max(
                    1,
                    int(top_k),
                )
            ]

            if not ranked:
                results.append(
                    {
                        "file": str(path),
                        "best_id": None,
                        "score": 0.0,
                        "second_score": 0.0,
                        "margin": 0.0,
                        "confidence": "NO_MATCH",
                        "status": "NO_MATCH",
                        "candidates": [],
                    }
                )

                continue

            best = ranked[0]

            best_score = float(
                best["score"]
            )

            if len(ranked) >= 2:
                second_score = float(
                    ranked[1]["score"]
                )
            else:
                second_score = 0.0

            margin = (
                best_score
                - second_score
            )

            confidence = (
                self._confidence(
                    best_score,
                    margin,
                )
            )

            status = (
                self._status_from_confidence(
                    confidence
                )
            )

            # Always use the best available candidate.
            #
            # The threshold is NO LONGER a rejection gate.
            # Even a weak candidate is accepted as the best
            # available address. The score/confidence are kept
            # for diagnostics.
            if best_score < threshold:
                best_id = None
                status = "NO_MATCH"
            else:
                best_id = best["id"]
                status = self._status_from_confidence(
                    confidence
                )

            results.append(
                {
                    "file": str(path),

                    "best_id": best_id,

                    "score": best_score,

                    "second_score": (
                        second_score
                    ),

                    "margin": float(
                        margin
                    ),

                    "confidence": confidence,

                    "status": status,

                    "best_image": best.get(
                        "best_image"
                    ),

                    "best_image_score": float(
                        best.get(
                            "best_image_score",
                            0.0,
                        )
                    ),

                    "candidates": ranked,
                }
            )

        return results

    def recognize(
        self,
        folder,
        top_k=5,
        threshold=0.65,
    ):
        return self.recognize_folder(
            folder,
            top_k=top_k,
            threshold=threshold,
        )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:42:24

Да. Теперь у нас есть **полная логика v3.3**, и её можно переносить в очередь без изменения алгоритма.

Я бы сделал следующий шаг именно так:

### 1. Не трогаем `recognize_folder()`

Он остаётся для ручного пакетного распознавания и тестов.

### 2. Добавляем в `SceneRecognizer` метод `recognize_one()`

Он будет использовать **абсолютно ту же последовательность**, что сейчас:

```text
файл
 ↓
DINO embedding 768
 ↓
environment descriptor
color descriptor
spatial descriptor
 ↓
SceneAnalyzer.compare()
 ↓
сравнение со всеми v3.3 fingerprints
 ↓
sort по score
 ↓
top1
top2
 ↓
margin = top1 - top2
 ↓
confidence
 ↓
threshold
```

То есть существующая логика:

```python
best_score
second_score
margin
confidence
status
best_id
candidates
```

останется один-в-один.

### 3. Worker будет работать последовательно

Для DINO:

```text
DinoWorker
   │
   ├─ забрал PH_00000001
   ├─ обработал
   ├─ записал результат
   │
   ├─ забрал PH_00000002
   ├─ обработал
   ├─ записал результат
   │
   └─ ...
```

**Не 526 процессов. Не 526 загрузок DINO.**

DINO-модель загружается один раз.

### 4. При этом Qwen работает независимо

Получается именно тот параллельный конвейер, который ты хотел:

```text
                         ┌── DINO CPU ──► результат
                         │
PH_00000527 ─────────────┤
                         │
                         └── QWEN GPU ──► результат
```

А следующие фотографии уже стоят в очереди:

```text
PH_00000528 pending
PH_00000529 pending
PH_00000530 pending
...
```

---

## И база уже идеально подходит

Например после DINO:

```text
photo_id       PH_00000527
dino_status    ok
dino_fingerprint  78_v33
dino_score     0.8734
dino_second_score 0.8611
dino_margin    0.0123
dino_time_sec  0.42
```

Qwen в это же время может независимо заполнить:

```text
qwen_status
qwen_time_sec
text_json
colors_json
objects_json
environment_json
image_quality_json
camera_view_json
scene_objects_json
analysis_quality_json
raw_json
```

А потом отдельный `sort_worker` использует уже готовые результаты.

---

### Поэтому сейчас пишем не «большой интегратор», а сначала два маленьких слоя

```text
app/core/recognizer.py
        ↓
    recognize_one()
        ↓
workers/dino_worker.py
        ↓
PostgreSQL
```

И отдельно:

```text
workers/qwen_worker.py
        ↓
PostgreSQL
```

После этого поверх них уже можно сделать единый **Integrator**, который запускается:

- кнопкой;
- по расписанию;
- постоянно наблюдая за `daily/`.

Это будет правильная архитектура: **очередь является центром системы, а не папка**.

---

### 👤 **User** — 2026-08-18 21:42:51

lf

---

### 🤖 **Assistant** — 2026-08-18 21:42:52

Да. Идём дальше. Следующий шаг — **сделать `recognize_one()`**, не меняя текущий v3.3.

Скажи, когда готов — дам точную команду для вставки в `app/core/recognizer.py`.

---

### 👤 **User** — 2026-08-18 21:42:59

давай

---

### 🤖 **Assistant** — 2026-08-18 21:43:00

Да. Сделаем аккуратно: **не переписываем существующий `recognize_folder()`**, а добавляем рядом `recognize_one()`. Алгоритм остаётся тот же v3.3.

Сначала сделаем резервную копию:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/core/recognizer.py app/core/recognizer.py.bak_before_worker
```

Теперь вставим метод **перед `def recognize(`**, то есть непосредственно перед последними строками файла.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
text = p.read_text()

marker = '''    def recognize(
        self,
        folder,
        top_k=5,
        threshold=0.65,
    ):
'''

if "    def recognize_one(" in text:
    raise SystemExit("recognize_one() уже существует — ничего не меняю")

method = '''    def recognize_one(
        self,
        path,
        top_k=5,
        threshold=0.65,
        fingerprints=None,
    ):
        """
        Recognize ONE image using the same v3.3 compact
        recognition logic as recognize_folder().

        Intended for queue/worker processing.

        Returns the same result structure as one item
        returned by recognize_folder().
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(path)

        # -------------------------------------------------
        # LOAD COMPATIBLE FINGERPRINTS
        # -------------------------------------------------

        allowed_fingerprints = None

        if fingerprints is not None:
            allowed_fingerprints = {
                str(item).strip()
                for item in fingerprints
                if str(item).strip()
            }

        loaded_fingerprints = []

        for metadata in self.manager.list_fingerprints():
            fingerprint_id = metadata.get("id")

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
                    f"{fingerprint_id}: {exc}"
                )
                continue

            if str(
                data["metadata"].get(
                    "version",
                    "",
                )
            ) != self.VERSION:
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

        # -------------------------------------------------
        # DINO
        # -------------------------------------------------

        queries = self.embedder.embed_paths(
            [path]
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

        query_embedding = queries[0]

        # -------------------------------------------------
        # CPU COMPACT DESCRIPTORS
        # -------------------------------------------------

        descriptors = {
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
        }

        # -------------------------------------------------
        # COMPARE WITH ALL FINGERPRINTS
        # -------------------------------------------------

        ranked = []

        for fingerprint_id, data in loaded_fingerprints:

            try:
                score = self.analyzer.compare(
                    path,
                    fingerprint_id,
                    query_global=query_embedding,
                    query_environment=(
                        descriptors["environment"]
                    ),
                    query_color=(
                        descriptors["color"]
                    ),
                    query_spatial=(
                        descriptors["spatial"]
                    ),
                )

            except (
                FileNotFoundError,
                ValueError,
                OSError,
            ) as exc:

                print(
                    f"[Recognizer] SKIP "
                    f"{fingerprint_id} "
                    f"for {path.name}: {exc}"
                )

                continue

            ranked.append(
                {
                    "id": fingerprint_id,

                    "score": float(
                        score.get(
                            "final_score",
                            0.0,
                        )
                    ),

                    "global": float(
                        score.get(
                            "global_score",
                            0.0,
                        )
                    ),

                    "environment": float(
                        score.get(
                            "environment_score",
                            0.0,
                        )
                    ),

                    "color": float(
                        score.get(
                            "color_score",
                            0.0,
                        )
                    ),

                    "spatial": float(
                        score.get(
                            "spatial_score",
                            0.0,
                        )
                    ),

                    "best_image": score.get(
                        "best_image"
                    ),

                    "best_image_score": float(
                        score.get(
                            "best_image_score",
                            0.0,
                        )
                    ),
                }
            )

        # -------------------------------------------------
        # RANK
        # -------------------------------------------------

        ranked.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        ranked = ranked[
            :max(
                1,
                int(top_k),
            )
        ]

        if not ranked:
            return {
                "file": str(path),
                "best_id": None,
                "score": 0.0,
                "second_score": 0.0,
                "margin": 0.0,
                "confidence": "NO_MATCH",
                "status": "NO_MATCH",
                "candidates": [],
            }

        best = ranked[0]

        best_score = float(
            best["score"]
        )

        if len(ranked) >= 2:
            second_score = float(
                ranked[1]["score"]
            )
        else:
            second_score = 0.0

        margin = (
            best_score
            - second_score
        )

        confidence = self._confidence(
            best_score,
            margin,
        )

        status = self._status_from_confidence(
            confidence
        )

        # Same threshold behaviour as recognize_folder().
        if best_score < threshold:
            best_id = None
            status = "NO_MATCH"
        else:
            best_id = best["id"]
            status = self._status_from_confidence(
                confidence
            )

        return {
            "file": str(path),

            "best_id": best_id,

            "score": best_score,

            "second_score": second_score,

            "margin": float(
                margin
            ),

            "confidence": confidence,

            "status": status,

            "best_image": best.get(
                "best_image"
            ),

            "best_image_score": float(
                best.get(
                    "best_image_score",
                    0.0,
                )
            ),

            "candidates": ranked,
        }

'''

text = text.replace(
    marker,
    method + marker,
    1,
)

p.write_text(text)

print("OK: recognize_one() added")
PY
```

Проверяем синтаксис:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile app/core/recognizer.py && \
echo "PYCOMPILE: OK"
```

И сразу проверим, что метод действительно появился:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -nE "def recognize_one|def recognize\(" app/core/recognizer.py
```

Должно быть примерно:

```text
...
484:    def recognize_one(
...
720:    def recognize(
```

### Пока базу НЕ трогаем

Это важно. Сначала проверяем новый метод на **одной фотографии** и убеждаемся, что он выдаёт тот же результат, что старый `recognize_folder()`.

После успешного теста следующим шагом сделаем:

**`dino_worker.py` → `SELECT ... FOR UPDATE SKIP LOCKED` → `recognize_one()` → UPDATE `photos`**.

И уже потом параллельно подключим Qwen на GPU.

---

### 👤 **User** — 2026-08-18 21:43:38

проверяем

---

### 🤖 **Assistant** — 2026-08-18 21:43:38

Да. Проверяем сначала синтаксис, потом **одну реальную фотографию**, не изменяя БД.

### 1. Синтаксис

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile app/core/recognizer.py && \
echo "PYCOMPILE: OK"
```

### 2. Проверяем, что метод есть

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -nE "def recognize_one|def recognize\(" app/core/recognizer.py
```

### 3. Запускаем `recognize_one()` на той же фотографии

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer

settings = Settings()

print("=" * 70)
print("SETTINGS DEVICE:", settings.device)
print("=" * 70)

embedder = SceneEmbedder(settings)
manager = FingerprintManager(settings)

recognizer = SceneRecognizer(
    settings,
    embedder,
    manager,
)

image = Path(
    "data/input/daily/Шолохова 127 А (9).JPG"
)

print()
print("IMAGE:", image)
print()

result = recognizer.recognize_one(
    image,
    top_k=5,
    threshold=0.65,
)

print()
print("=" * 70)
print("RESULT")
print("=" * 70)

print("best_id      :", result["best_id"])
print("score        :", result["score"])
print("second_score :", result["second_score"])
print("margin       :", result["margin"])
print("confidence   :", result["confidence"])
print("status       :", result["status"])
print("best_image   :", result["best_image"])
print("best_img_scr :", result["best_image_score"])

print()
print("CANDIDATES:")
for i, candidate in enumerate(
    result["candidates"],
    1,
):
    print(
        f"{i}. "
        f"{candidate['id']} "
        f"score={candidate['score']:.6f} "
        f"global={candidate['global']:.6f} "
        f"env={candidate['environment']:.6f} "
        f"color={candidate['color']:.6f} "
        f"spatial={candidate['spatial']:.6f}"
    )

print("=" * 70)
PY
```

**Важно:** сейчас это только тест. Он **не пишет ничего в `photos`**.

Пришли вывод этих трёх команд. Если результат нормальный, следующим шагом сделаем DINO worker, который будет брать `dino_status='pending'` из PostgreSQL и записывать результат обратно.

---

### 👤 **User** — 2026-08-18 21:43:58

======================================================================
SETTINGS DEVICE: cuda
======================================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9268.40it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
Traceback (most recent call last):
  File "<stdin>", line 15, in <module>
TypeError: FingerprintManager.__init__() missing 1 required positional argument: 'embedder'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:43:59

Отлично — и здесь как раз обнаружилась важная вещь: **DINO сейчас действительно работает на CUDA**:

```text
SETTINGS DEVICE: cuda
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
```

Ошибка только в моём тестовом коде: `FingerprintManager` у тебя принимает ещё `embedder`.

Ничего в проекте менять не надо. Просто повторяем тест с правильным созданием менеджера.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer

settings = Settings()

print("=" * 70)
print("SETTINGS DEVICE:", settings.device)
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

image = Path(
    "data/input/daily/Шолохова 127 А (9).JPG"
)

print()
print("IMAGE:", image)
print()

result = recognizer.recognize_one(
    image,
    top_k=5,
    threshold=0.65,
)

print()
print("=" * 70)
print("RESULT")
print("=" * 70)

print("best_id      :", result["best_id"])
print("score        :", result["score"])
print("second_score :", result["second_score"])
print("margin       :", result["margin"])
print("confidence   :", result["confidence"])
print("status       :", result["status"])
print("best_image   :", result["best_image"])
print("best_img_scr :", result["best_image_score"])

print()
print("CANDIDATES:")

for i, candidate in enumerate(
    result["candidates"],
    1,
):
    print(
        f"{i}. "
        f"{candidate['id']} "
        f"score={candidate['score']:.6f} "
        f"global={candidate['global']:.6f} "
        f"env={candidate['environment']:.6f} "
        f"color={candidate['color']:.6f} "
        f"spatial={candidate['spatial']:.6f}"
    )

print("=" * 70)
PY
```

### Что сейчас проверяем

Нас интересуют три вещи:

1. **DINO → RTX 3060**, а не CPU.
2. `recognize_one()` корректно выдаёт результат.
3. Результат соответствует старой логике `recognize_folder()`.

После этого уже можно строить схему:

```text
                 PostgreSQL
                     │
             dino_status=pending
                     │
                     ▼
              ┌─────────────┐
              │ DINO worker │
              └──────┬──────┘
                     │
              recognize_one()
                     │
                     ▼
             dino_* поля в DB
                     │
              dino_status=done
                     │
                     ├──────────────► Qwen worker
                     │                  GPU
                     │
                     ├──────────────► Preview worker
                     │
                     └──────────────► Sort worker
```

И **DINO и Qwen смогут работать параллельно**: DINO через PyTorch/CUDA, Qwen через Ollama/CUDA. При этом они будут брать независимые очереди из PostgreSQL.

---

### 👤 **User** — 2026-08-18 21:44:28

IMAGE: data/input/daily/Шолохова 127 А (9).JPG

======================================================================
RESULT
======================================================================
best_id      : 94_v33
score        : 0.8843672466278076
second_score : 0.8525879204273223
margin       : 0.03177932620048529
confidence   : PROBABLE
status       : PROBABLE_MATCH
best_image   : 94_052.JPG
best_img_scr : 0.8472332954406738

CANDIDATES:
1. 94_v33 score=0.884367 global=0.867729 env=0.926189 color=0.899141 spatial=0.959309
2. 95_v33 score=0.852588 global=0.839217 env=0.896689 color=0.829273 spatial=0.924975
3. 91_v33 score=0.834339 global=0.807157 env=0.882077 color=0.933352 spatial=0.919295
4. 92_v33 score=0.833428 global=0.795643 env=0.920576 color=0.907246 spatial=0.961853
5. 89_v33 score=0.828466 global=0.794878 env=0.896209 color=0.920592 spatial=0.945613
======================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:44:29

Да. **Тест прошёл нормально.** Причём он подтвердил именно то, что нам нужно для новой очереди.

### DINO

Сейчас фактически:

- **устройство:** CUDA
- **GPU:** RTX 3060
- **DINO:** `facebook/dinov2-base`
- **embedding:** 768
- **patch extraction:** отключён, используется наш компактный v3.3
- результат распознавания корректный.

Для этой фотографии:

```text
94_v33
score       0.884367
second      0.852588
margin      0.031779
confidence  PROBABLE
status      PROBABLE_MATCH
```

То есть DINO дал вполне нормальное распознавание: `94_v33`.

### И главное

Теперь у нас подтверждена архитектура, которую мы хотели:

```text
                 526 фотографий
                       │
                       ▼
                ┌─────────────┐
                │ PostgreSQL  │
                │   photos    │
                └──────┬──────┘
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
       dino_status          qwen_status
         pending               pending
             │                   │
             ▼                   ▼
      ┌────────────┐      ┌────────────┐
      │DINO worker │      │Qwen worker │
      │   CUDA     │      │   Ollama   │
      └─────┬──────┘      └──────┬─────┘
            │                    │
            ▼                    ▼
       dino_* поля          qwen_* поля
            │                    │
            └─────────┬──────────┘
                      ▼
                 одна запись
                 одной фотографии
```

То есть **DINO и Qwen не должны ждать друг друга**.

DINO берёт следующую фотографию со статусом:

```text
dino_status = pending
```

Qwen одновременно берёт другую/ту же фотографию независимо:

```text
qwen_status = pending
```

И каждый пишет только свою часть результата.

---

### Но есть ещё один важный момент

У тебя уже есть в PostgreSQL всё необходимое для DINO:

```text
dino_fingerprint
dino_score
dino_second_score
dino_margin
dino_time_sec
```

И для Qwen:

```text
qwen_time_sec
text_json
colors_json
objects_json
environment_json
image_quality_json
camera_view_json
scene_objects_json
analysis_quality_json
raw_json
```

То есть **схему БД расширять сейчас не требуется**.

А очереди уже индексированы:

```text
idx_photos_dino_queue
idx_photos_qwen_queue
```

Это очень хорошо.

### Следующий шаг

Я бы сейчас **не трогал `recognizer.py`** и не переделывал существующий алгоритм.

Нужно сделать отдельно:

```text
app/workers/
    dino_worker.py
    qwen_worker.py
```

Причём DINO worker должен использовать **тот же `SceneRecognizer`**, который мы только что проверили, а не копировать его алгоритм.

И сначала запустить **DINO worker на 526 pending-фото**, посмотреть скорость, загрузку RTX 3060 и результат в PostgreSQL.

После этого подключаем Qwen параллельно. Это будет гораздо безопаснее, чем сразу запускать два процесса на все 526.

---

### 👤 **User** — 2026-08-18 21:45:04

да

---

### 🤖 **Assistant** — 2026-08-18 21:45:05

Да. Тогда делаем **первый рабочий этап — только DINO worker**, Qwen пока не запускаем.

Но перед записью в БД я бы сделал worker максимально безопасным: `pending → processing → done/error`, чтобы при падении процесса фотографии не терялись и чтобы два worker-а случайно не взяли одну запись.

Сначала посмотрим, как сейчас устроен `Settings` и `FingerprintManager`, чтобы не придумывать интерфейсы. Дай команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,220p' app/core/config.py && \
echo "==================== FINGERPRINT MANAGER ====================" && \
grep -nE "class FingerprintManager|def __init__|def list_fingerprints|def load" \
app/core/fingerprint.py
```

После этого я дам **готовый `dino_worker.py` целиком**, который будет работать с твоей существующей БД `photobase` и существующим DINO v3.3.

---

### 👤 **User** — 2026-08-18 21:45:27

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,220p' app/core/config.py && \
echo "==================== FINGERPRINT MANAGER ====================" && \
grep -nE "class FingerprintManager|def __init__|def list_fingerprints|def load" \
app/core/fingerprint.py
from dataclasses import dataclass
from pathlib import Path
import os
import torch

@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("SCENE_HOST", "127.0.0.1")
    port: int = int(os.getenv("SCENE_PORT", "8080"))
    data_dir: Path = Path(os.getenv("SCENE_DATA", "data"))
    model_name: str = os.getenv(
        "SCENE_MODEL",
        "facebook/dinov2-base"
    )
    device: str = os.getenv(
        "SCENE_DEVICE",
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    batch_size: int = int(
        os.getenv(
            "SCENE_BATCH",
            "16"
        )
    )

    @property
    def fingerprints_dir(self):
        return Path(
            os.getenv(
                "SCENE_FINGERPRINTS",
                str(self.data_dir / "fingerprints")
            )
        )

settings = Settings()
==================== FINGERPRINT MANAGER ====================
14:class FingerprintManager:
38:    def __init__(
66:    def list_fingerprints(self):
460:    def load(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:45:28

Отлично. Теперь видно главное: **DINO действительно может работать на CUDA**, а `Settings()` автоматически выбирает RTX 3060.

И ещё важный момент: `FingerprintManager` требует `embedder`, поэтому предыдущую ошибку мы теперь можем правильно обойти.

Следующим шагом я предлагаю сделать **один тестовый DINO worker на 1 фото**, который:

1. берёт `dino_status = pending`;
2. блокирует эту запись;
3. прогоняет фото через существующий `SceneEmbedder`;
4. сравнивает с существующими `v33` fingerprint;
5. записывает:
   - `dino_fingerprint`
   - `dino_score`
   - `dino_second_score`
   - `dino_margin`
   - `dino_time_sec`
6. ставит `dino_status = done`;
7. при ошибке — `dino_status = error` + `error_message`;
8. **ничего не меняет в Qwen/sort/preview**.

Но сначала нам нужен полный конструктор менеджера и его методы загрузки/списка, чтобы worker использовал именно твою текущую архитектуру.

Дай **только эту команду**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,90p' app/core/fingerprint.py && \
echo "==================== LOAD ====================" && \
sed -n '430,510p' app/core/fingerprint.py && \
echo "==================== MAIN INIT ====================" && \
sed -n '1,35p' app/main.py
```

После этого уже дам готовый worker без изменения существующего `recognizer.py`.

---

### 👤 **User** — 2026-08-18 21:46:02

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,90p' app/core/fingerprint.py && \
echo "==================== LOAD ====================" && \
sed -n '430,510p' app/core/fingerprint.py && \
echo "==================== MAIN INIT ====================" && \
sed -n '1,35p' app/main.py
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import faiss
import numpy as np

from .image import image_files
from .scene_analyzer import CompactDescriptor

class FingerprintManager:
    """
    Fingerprint storage for Scene Fingerprint v3.3 compact.

    Stored:

        embeddings.npy
        centroid.npy
        representatives.npy
        representative_indices.npy

        environment_embeddings.npy
        color_embeddings.npy
        spatial_embeddings.npy

        faiss.index
        metadata.json

    Patch storage:
        DISABLED
    """

    VERSION = "3.3"

    def __init__(
        self,
        settings,
        embedder,
        root=None,
    ):
        self.settings = settings
        self.embedder = embedder

        self.root = (
            Path(root)
            if root is not None
            else settings.fingerprints_dir
        )

        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _path(
        self,
        fingerprint_id,
    ):
        return (
            self.root / str(fingerprint_id)
        )

    def list_fingerprints(self):
        result = []

        root = self.root

if not root.exists():
            return result

        for directory in sorted(
            root.iterdir()
        ):
            if not directory.is_dir():
                continue

            metadata_file = (
                directory
                / "metadata.json"
            )

            if not metadata_file.exists():
                continue

            try:
                metadata = json.loads(
==================== LOAD ====================
        )

        print(
            f"[Fingerprint v3.3] "
            f"global={embeddings.shape}"
        )

        print(
            f"[Fingerprint v3.3] "
            f"environment="
            f"{environment_embeddings.shape}"
        )

        print(
            f"[Fingerprint v3.3] "
            f"color={color_embeddings.shape}"
        )

        print(
            f"[Fingerprint v3.3] "
            f"spatial={spatial_embeddings.shape}"
        )

        print(
            "[Fingerprint v3.3] "
            "PATCH STORAGE = DISABLED"
        )

        return metadata

    def load(
        self,
        fingerprint_id,
    ):
        fingerprint_id = str(
            fingerprint_id
        )

        output = self._path(
            fingerprint_id
        )

        if not output.exists():
            raise FileNotFoundError(
                f"Fingerprint "
                f"'{fingerprint_id}' "
                f"not found"
            )

        required = [
            "embeddings.npy",
            "centroid.npy",
            "representatives.npy",
            "representative_indices.npy",
            "environment_embeddings.npy",
            "color_embeddings.npy",
            "spatial_embeddings.npy",
            "faiss.index",
            "metadata.json",
        ]

        missing = [
            name
            for name in required
            if not (
                output / name
            ).exists()
        ]

        if missing:
            raise FileNotFoundError(
                f"Fingerprint "
                f"'{fingerprint_id}' "
                f"is incomplete. "
                f"Missing: "
                f"{', '.join(missing)}"
            )

        with (
            output / "metadata.json"
        ).open(
==================== MAIN INIT ====================
from pathlib import Path
from nicegui import ui
from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer

embedder = SceneEmbedder(settings)
manager = FingerprintManager(settings, embedder)
recognizer = SceneRecognizer(settings, embedder, manager)

@ui.page("/")
def page():
    ui.label("Scene Fingerprint").classes("text-3xl font-bold")
    ui.label("Распознавание локации по визуальному окружению").classes("text-lg text-gray-600")

    with ui.tabs().classes("w-full") as tabs:
        create_tab = ui.tab("Создать слепок")
        recognize_tab = ui.tab("Распознавание")
        db_tab = ui.tab("База слепков")

    with ui.tab_panels(tabs, value=create_tab).classes("w-full"):
        with ui.tab_panel(create_tab):
            ui.label("Новый визуальный слепок").classes("text-2xl")
            fp_id = ui.input("ID локации / конструкции", placeholder="78").classes("w-96")
            folder = ui.input("Папка эталонных фотографий", value="data/input/78").classes("w-full")
            info = ui.label("")

            def create():
                try:
                    r = manager.create(fp_id.value.strip(), folder.value.strip())
                    info.text = f"Создан: {r['id']} | {r['images']} фото | {r['dimension']}D"
                except Exception as e:
                    info.text = f"Ошибка: {e}"

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:46:07

Отлично. Теперь архитектура понятна. `FingerprintManager` уже полностью готов для использования существующих `v33`, а `main.py` подтверждает правильную связку:

```text
Settings
   ↓
SceneEmbedder
   ↓
FingerprintManager
   ↓
SceneRecognizer
```

**Но сейчас я не хочу сразу писать worker.** Есть одна несостыковка, которую лучше поймать сейчас: в показанном тобой `recognizer.py` есть `recognize_folder()` и `recognize()`, но нет `recognize_one()`, хотя предыдущий тест с `recognize_one()` у тебя реально отработал и дал правильный результат.

Поэтому сначала проверим, что именно сейчас находится на диске:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "===== RECOGNIZER METHODS =====" && \
grep -nE "^[[:space:]]+def " app/core/recognizer.py && \
echo "===== FILE TAIL =====" && \
tail -80 app/core/recognizer.py
```

И ещё сразу проверим PostgreSQL-драйвер:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
try:
    import psycopg
    print("PSYCOPG: OK", psycopg.__version__)
except Exception as e:
    print("PSYCOPG: NO", e)

try:
    import psycopg2
    print("PSYCOPG2: OK", psycopg2.__version__)
except Exception as e:
    print("PSYCOPG2: NO", e)
PY
```

После этого уже сделаем **`dino_worker.py` правильно**, без копирования алгоритма распознавания и без изменения текущей логики v3.3.

---

### 👤 **User** — 2026-08-18 21:46:39

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "===== RECOGNIZER METHODS =====" && \
grep -nE "^[[:space:]]+def " app/core/recognizer.py && \
echo "===== FILE TAIL =====" && \
tail -80 app/core/recognizer.py
===== RECOGNIZER METHODS =====
41:    def __init__(
57:    def _confidence(
83:    def _status_from_confidence(
97:    def recognize_folder(
226:        def calculate_descriptors(path):
484:    def recognize_one(
799:    def recognize(
===== FILE TAIL =====

        best = ranked[0]

        best_score = float(
            best["score"]
        )

        if len(ranked) >= 2:
            second_score = float(
                ranked[1]["score"]
            )
        else:
            second_score = 0.0

        margin = (
            best_score
            - second_score
        )

        confidence = self._confidence(
            best_score,
            margin,
        )

        status = self._status_from_confidence(
            confidence
        )

        # Same threshold behaviour as recognize_folder().
        if best_score < threshold:
            best_id = None
            status = "NO_MATCH"
        else:
            best_id = best["id"]
            status = self._status_from_confidence(
                confidence
            )

        return {
            "file": str(path),

            "best_id": best_id,

            "score": best_score,

            "second_score": second_score,

            "margin": float(
                margin
            ),

            "confidence": confidence,

            "status": status,

            "best_image": best.get(
                "best_image"
            ),

            "best_image_score": float(
                best.get(
                    "best_image_score",
                    0.0,
                )
            ),

            "candidates": ranked,
        }

    def recognize(
        self,
        folder,
        top_k=5,
        threshold=0.65,
    ):
        return self.recognize_folder(
            folder,
            top_k=top_k,
            threshold=threshold,
        )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
try:
    import psycopg
    print("PSYCOPG: OK", psycopg.__version__)
except Exception as e:
    print("PSYCOPG: NO", e)

try:
    import psycopg2
    print("PSYCOPG2: OK", psycopg2.__version__)
except Exception as e:
    print("PSYCOPG2: NO", e)
PY
PSYCOPG: NO No module named 'psycopg'
PSYCOPG2: OK 2.9.12 (dt dec pq3 ext lo64)

---

### 🤖 **Assistant** — 2026-08-18 21:46:40

Отлично. Теперь всё сходится.

### Что имеем

**Recognizer:**
```text
recognize_folder()
recognize_one()
recognize()
```

Причём `recognize_one()` уже полностью реализован и мы его только что проверили на реальном фото.

**PostgreSQL:**
```text
psycopg2 2.9.12 — есть
psycopg  — не нужен
```

Значит, **ничего устанавливать не надо**.

### Делаем worker

Я предлагаю первый вариант сделать максимально консервативным:

- один процесс DINO;
- одна модель DINO на RTX 3060;
- берём фотографии через PostgreSQL;
- `FOR UPDATE SKIP LOCKED`, чтобы потом можно было безопасно запустить несколько worker-ов;
- статус:
  ```text
  pending → processing → done
  ```
- ошибка:
  ```text
  processing → error
  ```
- результат `recognize_one()` записывается в существующие поля;
- Qwen вообще не затрагивается;
- `sort_status` и `preview_status` не затрагиваются.

И **первый запуск сделаем только на 1 фото**, чтобы проверить запись в БД.

Создай worker:

```bash id="9h5w5c"
cd ~/projects/scene_fingerprint_mvp_v02 && \
mkdir -p app/workers && \
cat > app/workers/dino_worker.py <<'PY'
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

    try:
        while True:
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
PY
```

Потом **пока не запускай 526 фото**.

Сначала проверим, что файл компилируется:

```bash id="v4z5p6"
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile app/workers/dino_worker.py && \
echo "DINO WORKER: SYNTAX OK"
```

И затем покажи:

```bash id="n8p0ec"
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT photo_id, dino_status, dino_fingerprint, dino_score FROM photos ORDER BY id LIMIT 3;"
```

**После этого запустим ровно одну фотографию**, а не всю очередь. Если запись в БД окажется правильной — тогда уже снимаем ограничение и запускаем все 526.

---

### 👤 **User** — 2026-08-18 21:47:22

DINO WORKER: SYNTAX OK
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT photo_id, dino_status, dino_fingerprint, dino_score FROM photos ORDER BY id LIMIT 3;"
  photo_id   | dino_status | dino_fingerprint | dino_score 
-------------+-------------+------------------+------------
 PH_00000001 | pending     |                  |           
 PH_00000002 | pending     |                  |           
 PH_00000003 | pending     |                  |           
(3 rows)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:47:23

Отлично. Worker компилируется, а первые 3 записи чистые: `pending`, результатов пока нет.

Теперь запускаем **ровно один элемент очереди**. Но текущий worker пока будет обрабатывать всю очередь, поэтому перед первым запуском лучше добавить безопасный режим `DINO_MAX_ITEMS=1`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/workers/dino_worker.py")
s = p.read_text()

s = s.replace(
    '    print("[DINO] Worker ready.")',
    '''    print("[DINO] Worker ready.")

    max_items = int(os.getenv("DINO_MAX_ITEMS", "0"))
    processed = 0'''
)

s = s.replace(
    '            if row is None:\n                print("[DINO] Queue empty.")\n                break',
    '''            if row is None:
                print("[DINO] Queue empty.")
                break

            if max_items > 0 and processed >= max_items:
                print(
                    f"[DINO] Reached max_items={max_items}."
                )
                break'''
)

s = s.replace(
    '''                print(
                    f"[DINO] DONE "
                    f"{photo_key} "
                    f"-> {result.get('best_id')} "
                    f"score={result.get('score', 0):.6f} "
                    f"margin={result.get('margin', 0):.6f} "
                    f"time={elapsed:.2f}s"
                )''',
    '''                print(
                    f"[DINO] DONE "
                    f"{photo_key} "
                    f"-> {result.get('best_id')} "
                    f"score={result.get('score', 0):.6f} "
                    f"margin={result.get('margin', 0):.6f} "
                    f"time={elapsed:.2f}s"
                )

                processed += 1'''
)

p.write_text(s)
print("UPDATED")
PY
```

Проверяем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile app/workers/dino_worker.py && \
echo "SYNTAX OK"
```

И запускаем **одну**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
DINO_MAX_ITEMS=1 uv run python -m app.workers.dino_worker
```

После завершения:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT photo_id, dino_status, dino_fingerprint, dino_score, dino_second_score, dino_margin, dino_time_sec, error_message FROM photos ORDER BY id LIMIT 3;"
```

И ещё:

```bash
nvidia-smi
```

Нам нужны три подтверждения:

**1.** Первая запись стала `done`.

**2.** В ней появились примерно такие данные:

```text
dino_fingerprint = 94_v33
dino_score       = 0.884...
dino_second_score= 0.852...
dino_margin      = 0.031...
dino_time_sec    = ...
```

**3.** Во время обработки DINO действительно использовал RTX 3060.

После этого можно будет запускать уже все **526 фото**, а затем параллельно поднять Qwen worker.

---

### 👤 **User** — 2026-08-18 21:48:13

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT photo_id, dino_status, dino_fingerprint, dino_score, dino_second_score, dino_margin, dino_time_sec, error_message FROM photos ORDER BY id LIMIT 3;"
  photo_id   | dino_status | dino_fingerprint |     dino_score     | dino_second_score  |     dino_margin     |   dino_time_sec    | error_message 
-------------+-------------+------------------+--------------------+--------------------+---------------------+--------------------+---------------
 PH_00000001 | done        |                  | 0.4969405257701874 | 0.4236461520195008 | 0.07329437375068659 | 0.2630825860032928 | 
 PH_00000002 | processing  |                  |                    |                    |                     |                    | 
 PH_00000003 | pending     |                  |                    |                    |                     |                    | 
(3 rows)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:48:16

Вот здесь мы обнаружили **две вещи**, и одна из них — моя ошибка в worker.

### 1. DINO отработал

`PH_00000001`:

```text
status       = done
score        = 0.49694
second       = 0.42365
margin       = 0.07329
time         = 0.263 сек
```

То есть **DINO реально обработал фотографию примерно за 0.26 секунды**. Это очень хороший результат для RTX 3060.

Но `dino_fingerprint` пустой не из-за ошибки worker.

В `recognizer.py` сейчас действует:

```text
score < 0.65 → NO_MATCH → best_id = None
```

Поэтому:

```text
0.4969 < 0.65
```

и адрес не записался.

Это соответствует текущей логике recognizer.

---

### 2. А вот `PH_00000002 = processing` — это моя ошибка

Worker проверил лимит **после того, как успел взять следующую запись**.

Поэтому получилось:

```text
PH_00000001 → done
PH_00000002 → processing
PH_00000003 → pending
```

`PH_00000002` надо вернуть в `pending`.

Сделаем это сейчас:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "UPDATE photos SET dino_status='pending', updated_at=CURRENT_TIMESTAMP WHERE photo_id='PH_00000002' AND dino_status='processing';"
```

Проверяем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT photo_id, dino_status FROM photos ORDER BY id LIMIT 3;"
```

Должно быть:

```text
PH_00000001 | done
PH_00000002 | pending
PH_00000003 | pending
```

### Но есть ещё важный вопрос перед запуском 526

Я бы **не запускал всю очередь прямо сейчас**.

Нужно решить одну вещь: для нашей новой базы мы действительно хотим сохранять:

```text
dino_fingerprint = NULL
```

при score < 0.65?

Потому что раньше мы обсуждали, что DINO должен давать **первого кандидата**, а степень уверенности хранить отдельно. А текущий `recognizer.py` делает другое:

```text
score < 0.65
       ↓
NO_MATCH
       ↓
best_id = NULL
```

Для нашей новой БД я считаю более правильным разделить:

```text
dino_fingerprint = лучший кандидат
dino_score       = его score
dino_margin      = разница
dino_status      = done
```

а уже **уверенность/качество** определять отдельно.

Иначе фотография обработана DINO, но `dino_fingerprint` остаётся пустым, хотя кандидат объективно найден.

**Я бы не менял старый recognizer**, а в worker сохранял `candidates[0]["id"]` независимо от порога. Это не ломает старую систему распознавания, но делает новую очередь полноценной.

Если согласен, следующим шагом именно это поправим, затем повторим `PH_00000001`, и только после этого пускаем все 526.

---

### 👤 **User** — 2026-08-18 21:49:08

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "UPDATE photos SET dino_status='pending', updated_at=CURRENT_TIMESTAMP WHERE photo_id='PH_00000002' AND dino_status='processing';"
UPDATE 1
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT photo_id, dino_status FROM photos ORDER BY id LIMIT 3;"
  photo_id   | dino_status 
-------------+-------------
 PH_00000001 | done
 PH_00000002 | pending
 PH_00000003 | pending
(3 rows)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

