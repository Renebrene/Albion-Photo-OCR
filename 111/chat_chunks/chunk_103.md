## СЕССИЯ: ЛОРА ФИНАЛ 17 авг

**Создано:** 2026-08-16 21:41:46
**Обновлено:** 2026-08-19 17:07:59
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a820465-6788-83ea-b30d-7b8dfc43468a](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a820465-6788-83ea-b30d-7b8dfc43468a)

---

### 👤 **User** — 2026-08-16 21:58:47

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -R -n -E \
'Распознать|Распозна|recognize|recognition|sort_test_and_report|qwen|Qwen' \
app \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -300
app/web/components/photos.py.before_pg_link_20260816_183647:286:                            f"Qwen: {value('qwen_status')}"
app/web/components/photos.py.before_pg_link_20260816_183647:318:                            "Распознано"
app/web/components/photos.py.before_client_filter:255:                        if value("qwen_status") != "—":
app/web/components/photos.py.before_client_filter:258:                                f"Qwen: {value('qwen_status')}"
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:59:            qwen_status,
app/web/components/search.py:60:            qwen_time_sec,
app/web/components/photos.py.before_info_panel_20260816_184210:295:                        f"Qwen: {value('qwen_status')}"
app/web/components/photos.py.before_viewer_layout_20260816_183842:287:                            f"Qwen: {value('qwen_status')}"
app/web/components/photos.py.before_viewer_layout_20260816_183842:319:                            "Распознано"
app/web/components/technical_modules/photo_processing.py:43:            "DINO / v33 → определение адреса → сортировка → Qwen3-VL 4B"
app/web/components/technical_modules/qwen.py:4:def build_qwen():
app/web/components/technical_modules/qwen.py:13:            "Qwen3-VL 4B"
app/web/components/technical_modules/qwen.py:29:                    "Настройки Qwen будут подключены следующим этапом"
app/web/components/technical_modules/qwen.py:34:                "▶  Повторно запустить Qwen",
app/web/components/technical_modules/qwen.py:36:                    "Повторный запуск Qwen будет подключён следующим этапом"
app/web/components/photos.py.before_client_filter_v3:257:                        if value("qwen_status") != "—":
app/web/components/photos.py.before_client_filter_v3:260:                                f"Qwen: {value('qwen_status')}"
app/web/components/photos.py:323:                        if value("qwen_status") != "—":
app/web/components/photos.py:326:                                f"Qwen: {value('qwen_status')}"
app/web/components/technical.py.before_modular_20260816_191419:248:                    "Qwen3-VL 4B",
app/web/components/photos.py.before_client_filter_v2:255:                        if value("qwen_status") != "—":
app/web/components/photos.py.before_client_filter_v2:258:                                f"Qwen: {value('qwen_status')}"
app/web/components/technical.py:12:from app.web.components.technical_modules.qwen import (
app/web/components/technical.py:13:    build_qwen,
app/web/components/technical.py:175:                    "qwen",
app/web/components/technical.py:176:                    label="Qwen",
app/web/components/technical.py:230:                    with ui.tab_panel("qwen"):
app/web/components/technical.py:231:                        build_qwen()
app/web/client_aliases.py:4:Qwen может распознавать одно и то же название с ошибками,
app/web/photo_db.py:28:            qwen_status,
app/web/photo_db.py:29:            qwen_time_sec,
app/core/recognizer.py.before_restore_old_matching_20260815_025751:17:    Scene Fingerprint v3.3 compact recognizer.
app/core/recognizer.py.before_restore_old_matching_20260815_025751:97:    def recognize_folder(
app/core/recognizer.py.before_restore_old_matching_20260815_025751:484:    def recognize(
app/core/recognizer.py.before_restore_old_matching_20260815_025751:490:        return self.recognize_folder(
app/core/recognizer.py.before_restore_old_matching_20260815_025724:17:    Scene Fingerprint v3.3 compact recognizer.
app/core/recognizer.py.before_restore_old_matching_20260815_025724:97:    def recognize_folder(
app/core/recognizer.py.before_restore_old_matching_20260815_025724:484:    def recognize(
app/core/recognizer.py.before_restore_old_matching_20260815_025724:490:        return self.recognize_folder(
app/core/scene_analyzer.py:376:        For fast recognition the query descriptors can be
app/core/scene_analyzer.py:377:        supplied already calculated by the recognizer.
app/core/recognizer.py:17:    Scene Fingerprint v3.3 compact recognizer.
app/core/recognizer.py:97:    def recognize_folder(
app/core/recognizer.py:484:    def recognize(
app/core/recognizer.py:490:        return self.recognize_folder(
app/core/scene_analyzer.py.v33_working:376:        For fast recognition the query descriptors can be
app/core/scene_analyzer.py.v33_working:377:        supplied already calculated by the recognizer.
app/core/recognizer.py.backup_before_optimization:13:    Scene Fingerprint v3.3 compact recognizer.
app/core/recognizer.py.backup_before_optimization:93:    def recognize_folder(
app/core/recognizer.py.backup_before_optimization:395:    def recognize(
app/core/recognizer.py.backup_before_optimization:401:        return self.recognize_folder(
app/core/recognizer.py.before_patchfix:140:    def recognize_folder(
app/core/recognizer.py.backup_before_force_match:13:    Scene Fingerprint v3.3 compact recognizer.
app/core/recognizer.py.backup_before_force_match:93:    def recognize_folder(
app/core/recognizer.py.backup_before_force_match:387:    def recognize(
app/core/recognizer.py.backup_before_force_match:393:        return self.recognize_folder(
app/core/recognizer.py.v33_working:17:    Scene Fingerprint v3.3 compact recognizer.
app/core/recognizer.py.v33_working:97:    def recognize_folder(
app/core/recognizer.py.v33_working:484:    def recognize(
app/core/recognizer.py.v33_working:490:        return self.recognize_folder(
app/core/recognizer.py.before_restore_old_matching_20260815_025737:17:    Scene Fingerprint v3.3 compact recognizer.
app/core/recognizer.py.before_restore_old_matching_20260815_025737:97:    def recognize_folder(
app/core/recognizer.py.before_restore_old_matching_20260815_025737:484:    def recognize(
app/core/recognizer.py.before_restore_old_matching_20260815_025737:490:        return self.recognize_folder(
app/main.py:6:from app.core.recognizer import SceneRecognizer
app/main.py:10:recognizer = SceneRecognizer(settings, embedder, manager)
app/main.py:15:    ui.label("Распознавание локации по визуальному окружению").classes("text-lg text-gray-600")
app/main.py:19:        recognize_tab = ui.tab("Распознавание")
app/main.py:38:        with ui.tab_panel(recognize_tab):
app/main.py:39:            ui.label("Распознавание папки").classes("text-2xl")
app/main.py:45:            def run_recognition():
app/main.py:48:                    rows = recognizer.recognize_folder(
app/main.py:64:            ui.button("РАСПОЗНАТЬ", on_click=run_recognition)
app/web_v01_backup_20260816_142053/components/technical.py:77:                "Распознавание"
app/web_v01_backup_20260816_142053/components/technical.py:84:                    "Qwen3-VL 4B",
app/web_v01_backup_20260816_142053/components/technical.py:85:                    "Qwen2.5-VL 3B",
app/web_v01_backup_20260816_142053/components/technical.py:86:                    "Qwen3-VL 2B",
app/web_v01_backup_20260816_142053/components/technical.py:88:                value="Qwen3-VL 4B",
app/cli.py:11:from app.core.recognizer import SceneRecognizer
app/cli.py:21:            "recognition v3.3 compact"
app/cli.py:127:    recognize_parser = subparsers.add_parser(
app/cli.py:128:        "recognize",
app/cli.py:132:    recognize_parser.add_argument(
app/cli.py:137:    recognize_parser.add_argument(
app/cli.py:144:    recognize_parser.add_argument(
app/cli.py:151:    recognize_parser.add_argument(
app/cli.py:158:    recognize_parser.add_argument(
app/cli.py:165:    recognize_parser.add_argument(
app/cli.py:225:def print_recognition_result(
app/cli.py:592:    if args.command == "recognize":
app/cli.py:613:        recognizer = SceneRecognizer(
app/cli.py:629:            recognizer.recognize_folder(
app/cli.py:648:                print_recognition_result(
app/ocr/ocr_pipeline.py:40:    def recognize(self, image_path: str | Path) -> list[OCRResult]:
app/ocr/ocr_pipeline.py:102:    results = ocr.recognize(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 21:58:48

Да. Теперь точка входа найдена.

Главное: **кнопка «РАСПОЗНАТЬ» сейчас напрямую вызывает `recognizer.recognize_folder()`** в `app/main.py`:

```text
app/main.py
    ↓
run_recognition()
    ↓
recognizer.recognize_folder(...)
```

То есть сейчас веб-кнопка фактически обходит тот сложный pipeline, который мы разработали в `benchmark_hybrid_v12_full.py`.

### Что делаем

Не трогаем создание fingerprint — это отдельный процесс.

Для кнопки **РАСПОЗНАТЬ** строим отдельный последовательный pipeline:

```text
ФОТОГРАФИИ
    │
    ▼
┌─────────────────────┐
│  1. DINO / v33      │
│  TOP-5 кандидатов   │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────┐
│  2. РАСПОЗНАВАТЕЛЬ           │
│                              │
│  • global                    │
│  • environment               │
│  • color                     │
│  • spatial                   │
│  • margin                    │
│  • subfingerprints           │
│  • sequence consensus        │
│  • hybrid decision           │
└──────────┬───────────────────┘
           │
           ▼
       FINAL ADDRESS
           │
           ▼
┌─────────────────────┐
│  3. SORTING         │
│  копирование        │
│  по папкам адресов  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  4. QWEN3-VL 4B     │
│  анализ фотографий  │
└─────────────────────┘
```

И принципиально:

**Qwen не должен участвовать в определении адреса.**  
Адрес определяет наш распознаватель. Qwen работает **после сортировки**.

Это соответствует и текущему описанию модуля обработки:

> `DINO / v33 → определение адреса → сортировка → Qwen3-VL 4B`

что уже зафиксировано в `photo_processing.py`.

### Но есть важный нюанс

`benchmark_hybrid_v12_full.py` — это **исследовательский/benchmark-скрипт**, а не готовый production-модуль. Поэтому я бы не стал просто вызывать его из `main.py`.

Нормальная архитектура будет:

```text
app/core/
    recognizer.py          ← базовый DINO/v33
    hybrid_recognizer.py   ← новый production-рерайт
    sorter.py              ← сортировка
    qwen_processor.py      ← Qwen
    pipeline.py            ← последовательный orchestration

app/main.py
    ↓
pipeline.run()
```

А кнопка делает только:

```python
pipeline.run(input_folder)
```

То есть **кнопка ничего не знает про DINO, subfingerprint, Qwen и отдельные скрипты**.

Это особенно важно, потому что дальше мы сможем добавлять этапы, не переписывая UI.

### Следующий шаг

Сейчас я бы **сначала посмотрел `app/main.py` целиком и текущий `app/core/recognizer.py`**, чтобы аккуратно вынести orchestration, не ломая уже замороженный v33.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ app/main.py ================" && \
cat -n app/main.py && \
echo "================ recognizer.py ================" && \
cat -n app/core/recognizer.py | head -560
```

После этого уже можно будет сделать **конкретную схему `pipeline.py` и команду внесения изменений**, не затрагивая создание fingerprint.

---

### 👤 **User** — 2026-08-16 22:02:42

scene_fingerprint_mvp_v02

BASE:
DINOv2 v33 fingerprints

RERANK:
Hybrid v12

TEST:
256 images

RESULT:
247 / 256 совпали автоматически
9 изменений hybrid подтверждены
визуальная проверка:
≈97.3% правильной классификации

---

### 🤖 **Assistant** — 2026-08-16 22:02:44

Да. Это фиксируем как **текущую эталонную конфигурацию распознавания**.

### `scene_fingerprint_mvp_v02`

| Этап | Версия |
|---|---|
| База | **DINOv2 / v33 fingerprints** |
| Первичное распознавание | **TOP-N кандидатов** |
| Rerank | **Hybrid v12** |
| Дополнительные признаки | global + subfingerprint + sequence |
| Тестовая выборка | **256 фотографий** |
| Совпали без изменения | **247 / 256** |
| Изменены Hybrid | **9** |
| Итог после визуальной проверки | **≈97.3%** |

И главное - **Hybrid v12 теперь считаем частью production-распознавателя**, а не отдельным экспериментом.

Целевая схема кнопки **РАСПОЗНАТЬ**:

```text
                    РАСПОЗНАТЬ
                         │
                         ▼
                  папка фотографий
                         │
                         ▼
                 ┌──────────────┐
                 │  DINO v33    │
                 │  TOP-5       │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │  HYBRID v12  │
                 │              │
                 │ global       │
                 │ sub          │
                 │ margin       │
                 │ sequence     │
                 └──────┬───────┘
                        │
                        ▼
                  FINAL ADDRESS
                        │
                        ▼
                 ┌──────────────┐
                 │   SORTING    │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   QWEN 3-VL  │
                 │     4B       │
                 └──────────────┘
```

**Создание fingerprint здесь вообще не участвует.** Оно остаётся отдельной операцией:

```text
Создать fingerprint
        ↑
        │ отдельный процесс
        │
data/input/address
        ↓
DINOv2
        ↓
address_v33
```

А рабочая кнопка:

```text
РАСПОЗНАТЬ
    ↓
DINO v33
    ↓
Hybrid v12
    ↓
адрес
    ↓
сортировка
    ↓
Qwen
```

И ещё один важный момент: **247 случаев, которые уже правильно определились DINO, Hybrid не должен без необходимости пересматривать**. В v12 как раз заложен принцип: DINO TOP1 является базовым решением, а изменение происходит только при наличии достаточно сильного дополнительного сигнала.

Так что **97.3% - это сейчас наша контрольная точка**, с которой будем сравнивать production-реализацию.

---

### 👤 **User** — 2026-08-16 22:03:03

далее

---

### 🤖 **Assistant** — 2026-08-16 22:03:06

Далее — **не меняем алгоритм**, а переносим проверенный Hybrid v12 в рабочий pipeline кнопки.

### Шаг 1. Сначала смотрим текущую точку входа

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ app/main.py ================" && \
cat -n app/main.py && \
echo "================ recognizer.py ================" && \
cat -n app/core/recognizer.py | head -560
```

После этого я определю:

1. где именно запускается `DINO/v33`;
2. какой формат результата он отдаёт;
3. куда вставить **Hybrid v12**;
4. где сейчас происходит сортировка;
5. где подключается Qwen;
6. как сделать одну последовательную функцию:

```text
РАСПОЗНАТЬ
    ↓
DINO v33
    ↓
Hybrid v12
    ↓
FINAL ADDRESS
    ↓
SORT
    ↓
Qwen
    ↓
готовый результат
```

**Fingerprint creation пока вообще не трогаем.**

И ещё: будем сохранять промежуточные результаты, чтобы при сбое Qwen не приходилось повторно гонять DINO и Hybrid. Это пригодится уже для рабочего режима на 200–300 фотографий.

---

### 👤 **User** — 2026-08-16 22:03:33

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ app/main.py ================" && \
cat -n app/main.py && \
echo "================ recognizer.py ================" && \
cat -n app/core/recognizer.py | head -560
================ app/main.py ================
     1	from pathlib import Path
     2	from nicegui import ui
     3	from app.core.config import settings
     4	from app.core.embedder import SceneEmbedder
     5	from app.core.fingerprint import FingerprintManager
     6	from app.core.recognizer import SceneRecognizer
     7	
     8	embedder = SceneEmbedder(settings)
     9	manager = FingerprintManager(settings, embedder)
    10	recognizer = SceneRecognizer(settings, embedder, manager)
    11	
    12	@ui.page("/")
    13	def page():
    14	    ui.label("Scene Fingerprint").classes("text-3xl font-bold")
    15	    ui.label("Распознавание локации по визуальному окружению").classes("text-lg text-gray-600")
    16	
    17	    with ui.tabs().classes("w-full") as tabs:
    18	        create_tab = ui.tab("Создать слепок")
    19	        recognize_tab = ui.tab("Распознавание")
    20	        db_tab = ui.tab("База слепков")
    21	
    22	    with ui.tab_panels(tabs, value=create_tab).classes("w-full"):
    23	        with ui.tab_panel(create_tab):
    24	            ui.label("Новый визуальный слепок").classes("text-2xl")
    25	            fp_id = ui.input("ID локации / конструкции", placeholder="78").classes("w-96")
    26	            folder = ui.input("Папка эталонных фотографий", value="data/input/78").classes("w-full")
    27	            info = ui.label("")
    28	
    29	            def create():
    30	                try:
    31	                    r = manager.create(fp_id.value.strip(), folder.value.strip())
    32	                    info.text = f"Создан: {r['id']} | {r['images']} фото | {r['dimension']}D"
    33	                except Exception as e:
    34	                    info.text = f"Ошибка: {e}"
    35	
    36	            ui.button("СОЗДАТЬ СЛЕПОК", on_click=create)
    37	
    38	        with ui.tab_panel(recognize_tab):
    39	            ui.label("Распознавание папки").classes("text-2xl")
    40	            folder2 = ui.input("Папка", value="data/input/new").classes("w-full")
    41	            topk = ui.number("Top-K", value=5, min=1, max=20).classes("w-32")
    42	            threshold = ui.number("Порог", value=0.65, min=0, max=1, step=0.01).classes("w-32")
    43	            results_box = ui.column().classes("w-full")
    44	
    45	            def run_recognition():
    46	                results_box.clear()
    47	                try:
    48	                    rows = recognizer.recognize_folder(
    49	                        folder2.value, int(topk.value), float(threshold.value)
    50	                    )
    51	                    with results_box:
    52	                        for row in rows:
    53	                            ui.label(
    54	                                f"{Path(row['file']).name} → "
    55	                                f"{row['best_id'] or 'UNKNOWN'} "
    56	                                f"{row['score']:.3f}"
    57	                            )
    58	                            for c in row["candidates"]:
    59	                                ui.label(f"    {c['id']}: {c['score']:.3f}").classes("text-gray-500")
    60	                except Exception as e:
    61	                    with results_box:
    62	                        ui.label(f"Ошибка: {e}")
    63	
    64	            ui.button("РАСПОЗНАТЬ", on_click=run_recognition)
    65	
    66	        with ui.tab_panel(db_tab):
    67	            ui.label("База слепков").classes("text-2xl")
    68	            rows = ui.column().classes("w-full")
    69	
    70	            def refresh():
    71	                rows.clear()
    72	                with rows:
    73	                    data = manager.list_fingerprints()
    74	                    if not data:
    75	                        ui.label("База пуста.")
    76	                    for x in data:
    77	                        ui.label(
    78	                            f"№{x['id']} — {x['images']} фото — "
    79	                            f"{x['dimension']}D — {x['model']}"
    80	                        )
    81	
    82	            ui.button("Обновить", on_click=refresh)
    83	            refresh()
    84	
    85	ui.run(host=settings.host, port=settings.port, title="Scene Fingerprint")
================ recognizer.py ================
     1	from __future__ import annotations
     2	
     3	from concurrent.futures import ThreadPoolExecutor
     4	from pathlib import Path
     5	
     6	import numpy as np
     7	
     8	from .image import image_files
     9	from .scene_analyzer import (
    10	    CompactDescriptor,
    11	    SceneAnalyzer,
    12	)
    13	
    14	
    15	class SceneRecognizer:
    16	    """
    17	    Scene Fingerprint v3.3 compact recognizer.
    18	
    19	    Uses:
    20	        global
    21	        environment
    22	        color
    23	        spatial
    24	
    25	    Does NOT use:
    26	        DINO patch tokens
    27	
    28	    Recognition decision uses:
    29	        absolute score
    30	        margin to second-best candidate
    31	    """
    32	
    33	    VERSION = "3.3"
    34	
    35	    HIGH_SCORE = 0.90
    36	    PROBABLE_SCORE = 0.80
    37	
    38	    HIGH_MARGIN = 0.03
    39	    PROBABLE_MARGIN = 0.015
    40	
    41	    def __init__(
    42	        self,
    43	        settings,
    44	        embedder,
    45	        manager,
    46	    ):
    47	        self.settings = settings
    48	        self.embedder = embedder
    49	        self.manager = manager
    50	
    51	        self.analyzer = SceneAnalyzer(
    52	            embedder,
    53	            manager,
    54	        )
    55	
    56	    @classmethod
    57	    def _confidence(
    58	        cls,
    59	        score,
    60	        margin,
    61	    ):
    62	        score = float(score)
    63	        margin = float(margin)
    64	
    65	        if (
    66	            score >= cls.HIGH_SCORE
    67	            and margin >= cls.HIGH_MARGIN
    68	        ):
    69	            return "HIGH"
    70	
    71	        if (
    72	            score >= cls.PROBABLE_SCORE
    73	            and margin >= cls.PROBABLE_MARGIN
    74	        ):
    75	            return "PROBABLE"
    76	
    77	        if score >= cls.PROBABLE_SCORE:
    78	            return "AMBIGUOUS"
    79	
    80	        return "NO_MATCH"
    81	
    82	    @staticmethod
    83	    def _status_from_confidence(
    84	        confidence,
    85	    ):
    86	        if confidence == "HIGH":
    87	            return "CONFIDENT"
    88	
    89	        if confidence == "PROBABLE":
    90	            return "PROBABLE_MATCH"
    91	
    92	        if confidence == "AMBIGUOUS":
    93	            return "AMBIGUOUS"
    94	
    95	        return "NO_MATCH"
    96	
    97	    def recognize_folder(
    98	        self,
    99	        folder,
   100	        top_k=5,
   101	        threshold=0.65,
   102	        workers=6,
   103	        fingerprints=None,
   104	    ):
   105	        folder = Path(folder)
   106	
   107	        paths = image_files(
   108	            folder
   109	        )
   110	
   111	        if not paths:
   112	            return []
   113	
   114	        print(
   115	            f"[Recognizer] "
   116	            f"Query images: {len(paths)}"
   117	        )
   118	
   119	        loaded_fingerprints = []
   120	
   121	        # Optional whitelist of fingerprints.
   122	        # If provided, ONLY these fingerprints are used.
   123	        if fingerprints is not None:
   124	            allowed_fingerprints = {
   125	                str(item).strip()
   126	                for item in fingerprints
   127	                if str(item).strip()
   128	            }
   129	        else:
   130	            allowed_fingerprints = None
   131	
   132	        for metadata in (
   133	            self.manager.list_fingerprints()
   134	        ):
   135	            fingerprint_id = (
   136	                metadata.get("id")
   137	            )
   138	
   139	            if not fingerprint_id:
   140	                continue
   141	
   142	            if (
   143	                allowed_fingerprints is not None
   144	                and str(fingerprint_id)
   145	                not in allowed_fingerprints
   146	            ):
   147	                continue
   148	
   149	            try:
   150	                data = self.manager.load(
   151	                    fingerprint_id
   152	                )
   153	
   154	            except (
   155	                FileNotFoundError,
   156	                ValueError,
   157	                OSError,
   158	            ) as exc:
   159	
   160	                print(
   161	                    f"[Recognizer] SKIP "
   162	                    f"{fingerprint_id}: "
   163	                    f"{exc}"
   164	                )
   165	
   166	                continue
   167	
   168	            if str(
   169	                data["metadata"].get(
   170	                    "version",
   171	                    "",
   172	                )
   173	            ) != self.VERSION:
   174	
   175	                print(
   176	                    f"[Recognizer] SKIP old "
   177	                    f"fingerprint "
   178	                    f"{fingerprint_id}"
   179	                )
   180	
   181	                continue
   182	
   183	            loaded_fingerprints.append(
   184	                (
   185	                    fingerprint_id,
   186	                    data,
   187	                )
   188	            )
   189	
   190	        if not loaded_fingerprints:
   191	            raise ValueError(
   192	                "No compatible v3.3 compact "
   193	                "fingerprints found."
   194	            )
   195	
   196	        print(
   197	            "[Recognizer] Fingerprints: "
   198	            + ", ".join(
   199	                fp_id
   200	                for fp_id, _ in loaded_fingerprints
   201	            )
   202	        )
   203	
   204	        # One DINO pass for all query images.
   205	        queries = self.embedder.embed_paths(
   206	            paths
   207	        )
   208	
   209	        queries = np.asarray(
   210	            queries,
   211	            dtype=np.float32,
   212	        )
   213	
   214	        if queries.ndim == 1:
   215	            queries = queries.reshape(
   216	                1,
   217	                -1,
   218	            )
   219	
   220	        results = []
   221	
   222	        # Calculate CPU descriptors ONCE per image.
   223	        # They do not depend on the fingerprint.
   224	        #
   225	        # Use CPU workers to process different images in parallel.
   226	        def calculate_descriptors(path):
   227	            path = Path(path)
   228	
   229	            return (
   230	                str(path),
   231	                {
   232	                    "environment": (
   233	                        CompactDescriptor.environment(
   234	                            path
   235	                        )
   236	                    ),
   237	                    "color": (
   238	                        CompactDescriptor.color(
   239	                            path
   240	                        )
   241	                    ),
   242	                    "spatial": (
   243	                        CompactDescriptor.spatial(
   244	                            path
   245	                        )
   246	                    ),
   247	                },
   248	            )
   249	
   250	        worker_count = max(
   251	            1,
   252	            int(workers),
   253	        )
   254	
   255	        print(
   256	            f"[Recognizer] CPU workers: "
   257	            f"{worker_count}"
   258	        )
   259	
   260	        with ThreadPoolExecutor(
   261	            max_workers=worker_count
   262	        ) as executor:
   263	
   264	            descriptor_results = executor.map(
   265	                calculate_descriptors,
   266	                paths,
   267	            )
   268	
   269	            query_descriptors = dict(
   270	                descriptor_results
   271	            )
   272	
   273	        for path, query_embedding in zip(
   274	            paths,
   275	            queries,
   276	        ):
   277	            ranked = []
   278	
   279	            descriptors = query_descriptors[
   280	                str(path)
   281	            ]
   282	
   283	            for fingerprint_id, data in loaded_fingerprints:
   284	
   285	                # First use the analyzer.
   286	                # This calculates the full v3.3 score.
   287	                try:
   288	                    score = self.analyzer.compare(
   289	                        Path(path),
   290	                        fingerprint_id,
   291	                        query_global=query_embedding,
   292	                        query_environment=descriptors[
   293	                            "environment"
   294	                        ],
   295	                        query_color=descriptors[
   296	                            "color"
   297	                        ],
   298	                        query_spatial=descriptors[
   299	                            "spatial"
   300	                        ],
   301	                    )
   302	
   303	                except (
   304	                    FileNotFoundError,
   305	                    ValueError,
   306	                    OSError,
   307	                ) as exc:
   308	
   309	                    print(
   310	                        f"[Recognizer] SKIP "
   311	                        f"{fingerprint_id} "
   312	                        f"for "
   313	                        f"{Path(path).name}: "
   314	                        f"{exc}"
   315	                    )
   316	
   317	                    continue
   318	
   319	                ranked.append(
   320	                    {
   321	                        "id": fingerprint_id,
   322	
   323	                        "score": float(
   324	                            score.get(
   325	                                "final_score",
   326	                                0.0,
   327	                            )
   328	                        ),
   329	
   330	                        "global": float(
   331	                            score.get(
   332	                                "global_score",
   333	                                0.0,
   334	                            )
   335	                        ),
   336	
   337	                        "environment": float(
   338	                            score.get(
   339	                                "environment_score",
   340	                                0.0,
   341	                            )
   342	                        ),
   343	
   344	                        "color": float(
   345	                            score.get(
   346	                                "color_score",
   347	                                0.0,
   348	                            )
   349	                        ),
   350	
   351	                        "spatial": float(
   352	                            score.get(
   353	                                "spatial_score",
   354	                                0.0,
   355	                            )
   356	                        ),
   357	
   358	                        "best_image": score.get(
   359	                            "best_image"
   360	                        ),
   361	
   362	                        "best_image_score": float(
   363	                            score.get(
   364	                                "best_image_score",
   365	                                0.0,
   366	                            )
   367	                        ),
   368	                    }
   369	                )
   370	
   371	            ranked.sort(
   372	                key=lambda item: item[
   373	                    "score"
   374	                ],
   375	                reverse=True,
   376	            )
   377	
   378	            ranked = ranked[
   379	                :max(
   380	                    1,
   381	                    int(top_k),
   382	                )
   383	            ]
   384	
   385	            if not ranked:
   386	                results.append(
   387	                    {
   388	                        "file": str(path),
   389	                        "best_id": None,
   390	                        "score": 0.0,
   391	                        "second_score": 0.0,
   392	                        "margin": 0.0,
   393	                        "confidence": "NO_MATCH",
   394	                        "status": "NO_MATCH",
   395	                        "candidates": [],
   396	                    }
   397	                )
   398	
   399	                continue
   400	
   401	            best = ranked[0]
   402	
   403	            best_score = float(
   404	                best["score"]
   405	            )
   406	
   407	            if len(ranked) >= 2:
   408	                second_score = float(
   409	                    ranked[1]["score"]
   410	                )
   411	            else:
   412	                second_score = 0.0
   413	
   414	            margin = (
   415	                best_score
   416	                - second_score
   417	            )
   418	
   419	            confidence = (
   420	                self._confidence(
   421	                    best_score,
   422	                    margin,
   423	                )
   424	            )
   425	
   426	            status = (
   427	                self._status_from_confidence(
   428	                    confidence
   429	                )
   430	            )
   431	
   432	            # Always use the best available candidate.
   433	            #
   434	            # The threshold is NO LONGER a rejection gate.
   435	            # Even a weak candidate is accepted as the best
   436	            # available address. The score/confidence are kept
   437	            # for diagnostics.
   438	            if best_score < threshold:
   439	                best_id = None
   440	                status = "NO_MATCH"
   441	            else:
   442	                best_id = best["id"]
   443	                status = self._status_from_confidence(
   444	                    confidence
   445	                )
   446	
   447	            results.append(
   448	                {
   449	                    "file": str(path),
   450	
   451	                    "best_id": best_id,
   452	
   453	                    "score": best_score,
   454	
   455	                    "second_score": (
   456	                        second_score
   457	                    ),
   458	
   459	                    "margin": float(
   460	                        margin
   461	                    ),
   462	
   463	                    "confidence": confidence,
   464	
   465	                    "status": status,
   466	
   467	                    "best_image": best.get(
   468	                        "best_image"
   469	                    ),
   470	
   471	                    "best_image_score": float(
   472	                        best.get(
   473	                            "best_image_score",
   474	                            0.0,
   475	                        )
   476	                    ),
   477	
   478	                    "candidates": ranked,
   479	                }
   480	            )
   481	
   482	        return results
   483	
   484	    def recognize(
   485	        self,
   486	        folder,
   487	        top_k=5,
   488	        threshold=0.65,
   489	    ):
   490	        return self.recognize_folder(
   491	            folder,
   492	            top_k=top_k,
   493	            threshold=threshold,
   494	        )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:03:36

Да. Теперь картина полностью складывается.

И главное: **нельзя сводить пайплайн к `папка → DINO → адрес → Qwen`**. У нас уже есть промежуточный полноценный слой распознавания/уточнения.

### Зафиксированная схема

```text
                 ┌─────────────────────┐
                 │  ПАПКА ФОТОГРАФИЙ   │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │      DINOv2 v33     │
                 │   первичное сравнение│
                 └──────────┬──────────┘
                            │
                    TOP-5 кандидатов
                            │
                            ▼
                 ┌─────────────────────┐
                 │  RECOGNIZER v3.3    │
                 │                     │
                 │ global              │
                 │ environment         │
                 │ color               │
                 │ spatial             │
                 │ margin/confidence   │
                 └──────────┬──────────┘
                            │
                       первый кандидат
                            │
                            ▼
                 ┌─────────────────────┐
                 │    HYBRID v12       │
                 │                     │
                 │ sub-fingerprint     │
                 │ border cases        │
                 │ sequence consensus  │
                 │ TOP1/TOP2 rerank    │
                 └──────────┬──────────┘
                            │
                      окончательный ID
                            │
                            ▼
                 ┌─────────────────────┐
                 │ ПРИСВОЕНИЕ АДРЕСА    │
                 │ + сортировка фото    │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │       QWEN3-VL      │
                 │       4B            │
                 │ описание / OCR /    │
                 │ объекты / баннеры   │
                 └─────────────────────┘
```

Причём есть важный технический нюанс.

### Что сейчас уже есть

`recognizer.py` **уже делает большую часть первого этапа**:

```text
DINO embedding
      ↓
global
environment
color
spatial
      ↓
TOP-K
      ↓
score
margin
confidence
```

То есть его **не надо переписывать**.

А `benchmark_hybrid_v12_full.py` — это пока отдельный экспериментальный rerank-слой:

```text
TOP-5 DINO/recognizer
       ↓
border case?
       ↓
sub-fingerprint
       +
соседи последовательности
       ↓
изменение кандидата
```

Именно его теперь нужно **правильно встроить в production-пайплайн**, а не оставлять отдельным benchmark-скриптом.

---

## И ещё один важный момент

В `app/main.py` сейчас кнопка делает только:

```python
rows = recognizer.recognize_folder(...)
```

То есть UI сейчас фактически запускает:

```text
РАСПОЗНАТЬ
    ↓
recognizer
    ↓
результат
```

А нам нужно:

```text
РАСПОЗНАТЬ
    ↓
STEP 1 — DINO / v33
    ↓
STEP 2 — Recognizer v3.3
    ↓
STEP 3 — Hybrid v12
    ↓
STEP 4 — присвоение адреса
    ↓
STEP 5 — сортировка
    ↓
STEP 6 — Qwen
    ↓
готовая фотобаза
```

Причём **кнопка должна быть одна**, а внутри — последовательность отдельных стадий с возможностью видеть статус каждой.

Например:

```text
РАСПОЗНАТЬ

✓ DINOv2 v33              256 / 256
✓ Recognizer v3.3         256 / 256
✓ Hybrid v12              9 corrections
✓ Address assignment      256 / 256
✓ Sorting                 256 / 256
▶ Qwen3-VL 4B             running...

------------------------------------
Готово: 256 фотографий
```

Это существенно лучше, чем зашивать всё непосредственно в `recognize_folder()`.

### Поэтому следующий шаг

**Не трогаем сейчас `recognizer.py`.**

Сначала смотрим существующий модуль пайплайна, который у тебя уже появился:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat -n app/web/components/technical_modules/photo_processing.py && \
echo "================ QWEN ================" && \
cat -n app/web/components/technical_modules/qwen.py && \
echo "================ TECHNICAL ================" && \
cat -n app/web/components/technical.py
```

После этого уже соберём **один production pipeline**, куда аккуратно подключим существующие v33 + Hybrid v12 + сортировку + Qwen, не ломая рабочую часть распознавания.

---

### 👤 **User** — 2026-08-16 22:04:17

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
cat -n app/web/components/technical_modules/photo_processing.py && \
echo "================ QWEN ================" && \
cat -n app/web/components/technical_modules/qwen.py && \
echo "================ TECHNICAL ================" && \
cat -n app/web/components/technical.py
     1	from nicegui import ui
     2	
     3	
     4	def build_photo_processing():
     5	    with ui.card().classes("w-full"):
     6	        ui.label("ФОТООТЧЁТ").classes(
     7	            "text-lg font-bold"
     8	        )
     9	
    10	        ui.separator().classes("my-2")
    11	
    12	        ui.label("Источник фотографий")
    13	
    14	        with ui.row().classes("w-full items-center gap-2"):
    15	            ui.input(
    16	                value="/data/input/test"
    17	            ).props(
    18	                "outlined dense"
    19	            ).classes("flex-1")
    20	
    21	            ui.button(
    22	                "Выбрать",
    23	                icon="folder_open",
    24	            ).props("flat dense")
    25	
    26	        ui.label("Результат")
    27	
    28	        with ui.row().classes("w-full items-center gap-2"):
    29	            ui.input(
    30	                value="/data/output/test_sorted_v2"
    31	            ).props(
    32	                "outlined dense"
    33	            ).classes("flex-1")
    34	
    35	            ui.button(
    36	                "Выбрать",
    37	                icon="folder_open",
    38	            ).props("flat dense")
    39	
    40	        ui.separator().classes("my-2")
    41	
    42	        ui.label(
    43	            "DINO / v33 → определение адреса → сортировка → Qwen3-VL 4B"
    44	        ).classes("text-sm")
    45	
    46	        ui.button(
    47	            "▶  ЗАПУСТИТЬ ОБРАБОТКУ",
    48	            on_click=lambda: ui.notify(
    49	                "Запуск обработки будет подключён следующим этапом"
    50	            ),
    51	        ).props(
    52	            "unelevated"
    53	        ).classes(
    54	            "w-full text-lg font-bold"
    55	        )
    56	
    57	        ui.label(
    58	            "Главная рабочая операция"
    59	        ).classes("text-xs text-grey-6")
================ QWEN ================
     1	from nicegui import ui
     2	
     3	
     4	def build_qwen():
     5	    with ui.card().classes("w-full"):
     6	        ui.label("РАСПОЗНАВАНИЕ").classes(
     7	            "text-lg font-bold"
     8	        )
     9	
    10	        ui.separator().classes("my-2")
    11	
    12	        ui.label(
    13	            "Qwen3-VL 4B"
    14	        ).classes("text-base font-medium")
    15	
    16	        ui.label(
    17	            "● Рабочая модель"
    18	        ).classes("text-sm")
    19	
    20	        ui.checkbox(
    21	            "Автоматически запускать после DINO",
    22	            value=True,
    23	        ).props("dense")
    24	
    25	        with ui.row().classes("gap-2"):
    26	            ui.button(
    27	                "⚙  Настройки распознавания",
    28	                on_click=lambda: ui.notify(
    29	                    "Настройки Qwen будут подключены следующим этапом"
    30	                ),
    31	            ).props("flat")
    32	
    33	            ui.button(
    34	                "▶  Повторно запустить Qwen",
    35	                on_click=lambda: ui.notify(
    36	                    "Повторный запуск Qwen будет подключён следующим этапом"
    37	                ),
    38	            ).props("unelevated")
================ TECHNICAL ================
     1	from nicegui import ui
     2	
     3	from app.web.components.technical_modules.photo_processing import (
     4	    build_photo_processing,
     5	)
     6	from app.web.components.technical_modules.last_run import (
     7	    build_last_run,
     8	)
     9	from app.web.components.technical_modules.automation import (
    10	    build_automation,
    11	)
    12	from app.web.components.technical_modules.qwen import (
    13	    build_qwen,
    14	)
    15	from app.web.components.technical_modules.data import (
    16	    build_data,
    17	)
    18	from app.web.components.technical_modules.system import (
    19	    build_system,
    20	)
    21	from app.web.components.technical_modules.fingerprints import (
    22	    build_fingerprints,
    23	)
    24	from app.web.components.technical_modules.users import build_users
    25	
    26	
    27	TECHNICAL_STORAGE_KEY = "albion_technical_window_size"
    28	
    29	
    30	def _restore_and_watch_size():
    31	    """
    32	    Восстанавливает размер технического окна из localStorage
    33	    и запоминает последующие изменения размера.
    34	    """
    35	
    36	    ui.run_javascript(
    37	        f"""
    38	        setTimeout(() => {{
    39	            const card = document.getElementById('technical-dialog-card');
    40	
    41	            if (!card) {{
    42	                return;
    43	            }}
    44	
    45	            const storageKey = '{TECHNICAL_STORAGE_KEY}';
    46	
    47	            // ------------------------------------------------
    48	            // RESTORE
    49	            // ------------------------------------------------
    50	
    51	            try {{
    52	                const saved = localStorage.getItem(storageKey);
    53	
    54	                if (saved) {{
    55	                    const size = JSON.parse(saved);
    56	
    57	                    if (size.width) {{
    58	                        card.style.width = size.width + 'px';
    59	                    }}
    60	
    61	                    if (size.height) {{
    62	                        card.style.height = size.height + 'px';
    63	                    }}
    64	                }}
    65	            }} catch (error) {{
    66	                console.warn(
    67	                    'Не удалось восстановить размер технического окна',
    68	                    error
    69	                );
    70	            }}
    71	
    72	            // ------------------------------------------------
    73	            // WATCH RESIZE
    74	            // ------------------------------------------------
    75	
    76	            if (card.__albionResizeObserver) {{
    77	                card.__albionResizeObserver.disconnect();
    78	            }}
    79	
    80	            card.__albionResizeObserver = new ResizeObserver(() => {{
    81	                try {{
    82	                    localStorage.setItem(
    83	                        storageKey,
    84	                        JSON.stringify({{
    85	                            width: Math.round(card.offsetWidth),
    86	                            height: Math.round(card.offsetHeight)
    87	                        }})
    88	                    );
    89	                }} catch (error) {{
    90	                    console.warn(
    91	                        'Не удалось сохранить размер технического окна',
    92	                        error
    93	                    );
    94	                }}
    95	            }});
    96	
    97	            card.__albionResizeObserver.observe(card);
    98	
    99	        }}, 100);
   100	        """
   101	    )
   102	
   103	
   104	def show_technical(initial_tab="photo_processing"):
   105	
   106	    with ui.dialog() as dialog:
   107	
   108	        with ui.card().props(
   109	            "id=technical-dialog-card"
   110	        ).classes(
   111	            "technical-dialog-card"
   112	        ).style(
   113	            """
   114	            width: 1000px;
   115	            height: 760px;
   116	            min-width: 700px;
   117	            min-height: 500px;
   118	            max-width: 96vw;
   119	            max-height: 94vh;
   120	            resize: both;
   121	            overflow: hidden;
   122	            """
   123	        ):
   124	
   125	            # ====================================================
   126	            # HEADER
   127	            # ====================================================
   128	
   129	            with ui.row().classes(
   130	                "w-full items-center justify-between"
   131	            ):
   132	
   133	                ui.label(
   134	                    "⚙ Технический раздел"
   135	                ).classes(
   136	                    "text-xl font-bold"
   137	                )
   138	
   139	                ui.button(
   140	                    icon="close",
   141	                    on_click=dialog.close,
   142	                ).props(
   143	                    "flat"
   144	                )
   145	
   146	            ui.separator()
   147	
   148	            # ====================================================
   149	            # TABS
   150	            # ====================================================
   151	
   152	            with ui.tabs().classes(
   153	                "w-full"
   154	            ) as tabs:
   155	
   156	                ui.tab(
   157	                    "photo_processing",
   158	                    label="Обработка фото",
   159	                    icon="photo_library",
   160	                )
   161	
   162	                ui.tab(
   163	                    "last_run",
   164	                    label="Последний запуск",
   165	                    icon="history",
   166	                )
   167	
   168	                ui.tab(
   169	                    "automation",
   170	                    label="Автоматизация",
   171	                    icon="autorenew",
   172	                )
   173	
   174	                ui.tab(
   175	                    "qwen",
   176	                    label="Qwen",
   177	                    icon="smart_toy",
   178	                )
   179	
   180	                ui.tab(
   181	                    "data",
   182	                    label="Данные",
   183	                    icon="storage",
   184	                )
   185	
   186	                ui.tab(
   187	                    "system",
   188	                    label="Система",
   189	                    icon="computer",
   190	                )
   191	
   192	                ui.tab(
   193	                    "fingerprints",
   194	                    label="Fingerprints",
   195	                    icon="fingerprint",
   196	                )
   197	
   198	                ui.tab(
   199	                    "users",
   200	                    label="Пользователи",
   201	                    icon="people",
   202	                )
   203	
   204	            ui.separator()
   205	
   206	            # ====================================================
   207	            # TAB CONTENT
   208	            # ====================================================
   209	
   210	            with ui.scroll_area().classes(
   211	                "w-full flex-1"
   212	            ):
   213	
   214	                with ui.tab_panels(
   215	                    tabs,
   216	                    value="photo_processing",
   217	                ).classes(
   218	                    "w-full"
   219	                ):
   220	
   221	                    with ui.tab_panel("photo_processing"):
   222	                        build_photo_processing()
   223	
   224	                    with ui.tab_panel("last_run"):
   225	                        build_last_run()
   226	
   227	                    with ui.tab_panel("automation"):
   228	                        build_automation()
   229	
   230	                    with ui.tab_panel("qwen"):
   231	                        build_qwen()
   232	
   233	                    with ui.tab_panel("data"):
   234	                        build_data()
   235	
   236	                    with ui.tab_panel("system"):
   237	                        build_system()
   238	
   239	                    with ui.tab_panel("fingerprints"):
   240	                        build_fingerprints()
   241	
   242	                    with ui.tab_panel("users"):
   243	                        build_users()
   244	
   245	    dialog.open()
   246	
   247	    # Открываем нужную вкладку сразу.
   248	    if initial_tab:
   249	        ui.timer(
   250	            0.05,
   251	            lambda: tabs.set_value(initial_tab),
   252	            once=True,
   253	        )
   254	
   255	    _restore_and_watch_size()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:04:18

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed Albion pipeline, benchmarks, processing files, and launch button**
>
> 
>
> Worked for 6s

Да. Теперь картина полностью ясна.

**Следующий шаг — не трогать `recognizer.py`.** Он у нас уже проверенный и зафиксированный результат:

**DINOv2 v33 → Hybrid v12 → адрес**

Тестовая база:
- 256 фото
- 247 совпали автоматически
- 9 исправлены Hybrid
- все 9 подтверждены
- ≈ **97,3% правильной классификации**

А сейчас в UI пайплайн пока только нарисован:

```text
ЗАПУСТИТЬ ОБРАБОТКУ
        ↓
      пока НЕТ
```

Нужно сделать реальный оркестратор:

```text
                    ┌──────────────┐
                    │ Входная папка│
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ DINOv2 v33   │
                    │ fingerprints │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ Recognizer   │
                    │ Hybrid v12   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ адрес        │
                    │ определён    │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ сортировка   │
                    │ по адресам   │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ Qwen3-VL 4B  │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │ результат    │
                    └──────────────┘
```

Причём **Qwen не должен участвовать в определении адреса**. Он запускается **после** того, как фотография уже получила адрес и была разложена.

### Что я предлагаю сделать сейчас

Сначала создать отдельный слой:

```text
app/core/photo_pipeline.py
```

Он будет единственной точкой, которая знает последовательность:

```python
def run_photo_pipeline(input_dir, output_dir):
    # 1. DINO / v33
    # 2. Recognizer / Hybrid v12
    # 3. сортировка
    # 4. Qwen
    # 5. итоговый отчёт
```

А UI:

```text
photo_processing.py
```

только вызывает его и показывает прогресс.

Это важно: **не зашивать всю бизнес-логику в кнопку NiceGUI**.

И ещё один принцип: существующий

```python
SceneRecognizer.recognize_folder(...)
```

оставляем как есть. Новый pipeline использует именно его, а не создаёт второй распознаватель.

---

### Сейчас нужен следующий просмотр кода

Чтобы не писать оркестратор вслепую, давай найдём уже существующую реализацию **Hybrid v12 / сортировки / запуска Qwen**.

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID ================" && \
grep -R -n -E \
'Hybrid|hybrid|v12|rerank|RERANK' \
app scripts \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -300 && \
echo "================ SORT ================" && \
grep -R -n -E \
'sort_test_and_report|sorted|shutil.copy|copy2|mkdir|address|best_id' \
app scripts \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -300 && \
echo "================ QWEN ALL ================" && \
grep -R -n -E \
'Qwen|qwen' \
app scripts \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -300
```

**После этого уже соберём реальный `photo_pipeline.py`**, не меняя проверенный v33/Hybrid v12.

---

