## СЕССИЯ: ЛОРА ФИНАЛ 17 авг

**Создано:** 2026-08-16 21:41:46
**Обновлено:** 2026-08-19 17:07:59
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a820465-6788-83ea-b30d-7b8dfc43468a](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a820465-6788-83ea-b30d-7b8dfc43468a)

---

### 🤖 **Assistant** — 2026-08-16 21:51:38

Да, именно. **Создание fingerprint — отдельная операция**, и её не надо смешивать с обработкой фотографий.

Тогда фиксируем архитектуру так:

```text
┌─────────────────────────────┐
│       ТЕХНИЧЕСКИЙ РАЗДЕЛ    │
└─────────────────────────────┘

СИСТЕМА
  └─ CPU / GPU / RAM / VRAM / сеть

ФОТООТЧЁТ
  └─ рабочая обработка фотографий
     DINOv2/v33
       ↓
     первый кандидат
       ↓
     присвоение адреса
       ↓
     копирование / переименование
       ↓
     Qwen — если требуется

FINGERPRINTS
  └─ создание / обновление слепков
     отдельная операция

ПОСЛЕДНЯЯ ОБРАБОТКА
  └─ история именно рабочих запусков ФОТООТЧЁТА
```

А текущий:

```text
app/pipeline/worker.py
```

оставляем как **worker для fingerprint**, не используем его для `ФОТООТЧЁТА`.

И тогда следующий правильный шаг — найти **реальный рабочий запуск сортировки фотографий**, а не `FingerprintWorker`.

У нас уже есть `scripts/sort_test_and_report_v2.py`, но я бы сейчас посмотрел, **какой именно скрипт является финальным рабочим вариантом**, чтобы не подключить старую тестовую версию.

Дай команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -R -n -E \
"scene-fingerprint recognize|sort_test_and_report|test_sorted_v2|data/output|first_candidate|first candidate|v33" \
scripts app \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -250
```

После этого привяжем **`ФОТООТЧЁТ → ЗАПУСТИТЬ ОБРАБОТКУ` именно к финальному рабочему пайплайну**, а `ПОСЛЕДНЯЯ ОБРАБОТКА` будем строить уже поверх его результатов.

---

### 👤 **User** — 2026-08-16 21:52:21

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -R -n -E \
"scene-fingerprint recognize|sort_test_and_report|test_sorted_v2|data/output|first_candidate|first candidate|v33" \
scripts app \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -250
scripts/sort_neighbor_v35_benchmark.py:12:SOURCE_JSON = PROJECT / "data/output/benchmark_v1/benchmark.json"
scripts/sort_neighbor_v35_benchmark.py:168:            "v33": current,
scripts/sort_neighbor_v35_benchmark.py:199:                "v33",
scripts/benchmark_sub_rerank_v04.py:16:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_sub_rerank_v04.py:26:    "data/output/benchmark_sub_rerank_v04.json"
scripts/benchmark_sub_rerank_v04.py:116:    # 84_v33_sub_2 -> 84_v33
scripts/sort_test_and_report_v2.py:18:OUTPUT_DIR = PROJECT / "data/output/test_sorted_v2"
scripts/sort_test_and_report_v2.py:21:    f"{i}_v33"
scripts/make_subfingerprints_v2.py:59:    Затем используется v33 weighting.
scripts/make_subfingerprints_v2.py:348:            "  uv run python scripts/make_subfingerprints_v2.py 78_v33"
scripts/benchmark_test_v1.py:15:OUT_DIR = PROJECT / "data/output/benchmark_v1"
scripts/benchmark_test_v1.py:17:FINGERPRINTS = [f"{i}_v33" for i in range(78, 96)]
scripts/banner_search_v03.py:21:OUTPUT_DIR = PROJECT / "data/output/banner_search"
scripts/benchmark_test_sub_exp.py:15:OUT_DIR = PROJECT / "data/output/benchmark_sub_exp"
scripts/benchmark_test_sub_exp.py:18:    "84_v33_sub_1",
scripts/benchmark_test_sub_exp.py:19:    "84_v33_sub_2",
scripts/benchmark_test_sub_exp.py:20:    "85_v33_sub_1",
scripts/benchmark_test_sub_exp.py:21:    "85_v33_sub_2",
scripts/benchmark_test_sub_exp.py:22:    "87_v33_sub_1",
scripts/benchmark_test_sub_exp.py:23:    "87_v33_sub_2",
scripts/benchmark_test_sub_exp.py:24:    "89_v33_sub_1",
scripts/benchmark_test_sub_exp.py:25:    "89_v33_sub_2",
scripts/benchmark_test_sub_exp.py:26:    "89_v33_sub_3",
scripts/benchmark_test_sub_exp.py:27:    "92_v33_sub_1",
scripts/benchmark_test_sub_exp.py:28:    "92_v33_sub_2",
scripts/benchmark_test_sub_exp.py:29:    "94_v33_sub_1",
scripts/benchmark_test_sub_exp.py:30:    "94_v33_sub_2",
scripts/benchmark_test_sub_exp.py:31:    "94_v33_sub_3",
scripts/benchmark_test_sub_exp.py:32:    "95_v33_sub_1",
scripts/benchmark_test_sub_exp.py:33:    "95_v33_sub_2",
scripts/benchmark_test_sub_exp.py:34:    "95_v33_sub_3",
scripts/benchmark_test_sub_exp.py:36:FINGERPRINTS = [f"{i}_v33" for i in range(78, 96)]
scripts/banner_search_v03_2.py:22:OUTPUT_DIR = PROJECT / "data/output/banner_search_v03_2"
scripts/sort_test_and_report.py:14:OUTPUT_DIR = Path("data/output_test")
scripts/sort_test_and_report.py:110:        # Убираем суффикс _v33
scripts/sort_test_and_report.py:111:        if best_id.endswith("_v33"):
scripts/sort_margin005_best.py:140:        folder = assigned.replace("_v33", "")
scripts/banner_crop_search_v02.py:21:OUTPUT_DIR = PROJECT / "data/output/found_banners_debug"
scripts/benchmark_hybrid_v08.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v08.py:27:    "data/output/benchmark_hybrid_v08.json"
scripts/benchmark_hybrid_v03.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v03.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/import_qwen_to_db.py:130:            / "data/output/test_sorted_v2"
scripts/import_qwen_to_db.py:143:            / "data/output/test_sorted_v2"
scripts/sort_sequence_v38_1_subtest.py:15:    "data/output/benchmark_v1/benchmark.json"
scripts/benchmark_hybrid_v12_full.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v12_full.py:27:    "data/output/full_recognize_hybrid_v12_test.json"
scripts/search_banners_v01.py:17:OUTPUT_DIR = PROJECT / "data/output/found_banners"
scripts/benchmark_hybrid_v10_debug.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v10_debug.py:27:    "data/output/benchmark_hybrid_v09.json"
scripts/sort_sequence_v39.py:15:    "data/output/benchmark_v1/benchmark.json"
scripts/benchmark_sub_rerank_v03.py:16:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_sub_rerank_v03.py:26:    "data/output/benchmark_sub_rerank_v03.json"
scripts/benchmark_sub_rerank_v03.py:132:                "_v33",
scripts/benchmark_sub_rerank_v03.py:165:                            "_v33"
scripts/benchmark_sub_rerank_v01.py:15:    / "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_sub_rerank_v01.py:26:    / "data/output/benchmark_sub_rerank_v01.json"
scripts/benchmark_sub_rerank_v01.py:42:    return str(x).replace("_v33", "")
scripts/benchmark_hybrid_v11.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v11.py:27:    "data/output/benchmark_hybrid_v11.json"
scripts/benchmark_hybrid_v02.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v02.py:27:    "data/output/benchmark_hybrid_v02.json"
scripts/banner_llm_folder_search_v01.py:26:    "data/output/found_banners"
scripts/build_subfingerprints_exp.py:24:    for addr in sorted(SRC.glob("*_v33")):
scripts/make_subfingerprints.py:121:    Это особенно важно для случаев вроде 81_v33,
scripts/make_subfingerprints.py:417:        help="Fingerprint ID, e.g. 78_v33",
scripts/sort_neighbor_v37.py:11:SOURCE_JSON = PROJECT / "data/output/benchmark_img/benchmark.json"
scripts/sort_neighbor_v37.py:22:        return int(str(x).replace("_v33", ""))
scripts/sort_neighbor_v37.py:145:    v33 = rec["top1"]
scripts/sort_neighbor_v37.py:149:    final = v33
scripts/sort_neighbor_v37.py:213:    if final != v33:
scripts/sort_neighbor_v37.py:216:            "v33": v33,
scripts/sort_neighbor_v37.py:228:        "v33": v33,
scripts/sort_neighbor_v37.py:269:            "v33",
scripts/sort_neighbor_v37.py:312:            f"{x['v33']} -> {x['final']} "
scripts/sort_baseline.py:10:BASE = Path("data/output/baseline_v33")
scripts/sort_baseline.py:17:    "78_v33", "79_v33", "80_v33", "81_v33", "82_v33",
scripts/sort_baseline.py:18:    "83_v33", "84_v33", "85_v33", "86_v33", "87_v33",
scripts/sort_baseline.py:19:    "88_v33", "89_v33", "90_v33", "91_v33", "92_v33",
scripts/sort_baseline.py:20:    "93_v33", "94_v33", "95_v33",
scripts/sort_baseline.py:37:        (OUT / fp.replace("_v33", "")).mkdir(exist_ok=True)
scripts/sort_baseline.py:48:        folder = best_id.replace("_v33", "")
scripts/build_margin_best_from_benchmark.py:12:    / "data/output/benchmark_v1/benchmark.json"
scripts/build_margin_best_from_benchmark.py:25:    return str(x).replace("_v33", "")
scripts/banner_crop_search_v01.py:19:OUTPUT_DIR = PROJECT / "data/output/found_banners_debug"
scripts/qwen4b_output_v01_before_compact_prompt.py:14:INPUT_DIR = PROJECT / "data" / "output" / "test_sorted_v2"
scripts/qwen4b_output_v01.py:14:INPUT_DIR = PROJECT / "data" / "output" / "test_sorted_v2"
scripts/banner_candidates_v01.py:19:OUTPUT_DIR = PROJECT / "data/output/banner_candidates"
scripts/banner_search_v02.py:19:    "data/output/found_banners"
scripts/banner_search_v03_3.py:19:OUTPUT_DIR = PROJECT / "data/output/banner_search_v03_3"
scripts/crop_test_banner.py:10:    "data/output/banner_debug/Ashhabadskiy_01"
scripts/benchmark_hybrid_v05.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v05.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v04.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v04.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v01.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v01.py:27:    "data/output/benchmark_hybrid_v01.json"
scripts/benchmark_hybrid_v01.py:58:    if "_v33" in x:
scripts/make_subcluster_contact.py:9:    "87_v33/cluster_1",
scripts/make_subcluster_contact.py:10:    "89_v33/cluster_0",
scripts/make_subcluster_contact.py:11:    "92_v33/cluster_0",
scripts/make_subcluster_contact.py:12:    "94_v33/cluster_2",
scripts/make_subcluster_contact.py:13:    "95_v33/cluster_2",
scripts/banner_search_v01.py:19:    "data/output/found_banners"
scripts/sort_neighbor_v36_img.py:11:SOURCE_JSON = PROJECT / "data/output/benchmark_img/benchmark.json"
scripts/sort_neighbor_v36_img.py:23:    return str(x).replace("_v33", "")
scripts/sort_neighbor_v36_img.py:227:            "v33": current,
scripts/sort_neighbor_v36_img.py:278:        "v33",
scripts/sort_neighbor_v36_img.py:341:                f"    {x['v33']} -> {x['final']}"
scripts/sort_neighbor_v36.py:11:SOURCE_JSON = PROJECT / "data/output/benchmark_v1/benchmark.json"
scripts/sort_neighbor_v36.py:23:    return str(x).replace("_v33", "")
scripts/sort_neighbor_v36.py:227:            "v33": current,
scripts/sort_neighbor_v36.py:278:        "v33",
scripts/sort_neighbor_v36.py:341:                f"    {x['v33']} -> {x['final']}"
scripts/sort_sequence_v38.py:15:    "data/output/benchmark_v1/benchmark.json"
scripts/benchmark_hybrid_v07.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v07.py:27:    "data/output/benchmark_hybrid_v07.json"
scripts/llm_resolver_v01.py:50:        a = int(rows[i - 1]["v33"])
scripts/llm_resolver_v01.py:51:        b = int(rows[i]["v33"])
scripts/llm_resolver_v01.py:102:            "top1": int(r["v33"]),
scripts/sort_sequence_sub_v01.py:15:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/export_subclusters.py:20:    "84_v33",
scripts/export_subclusters.py:21:    "85_v33",
scripts/export_subclusters.py:22:    "87_v33",
scripts/export_subclusters.py:23:    "89_v33",
scripts/export_subclusters.py:24:    "92_v33",
scripts/export_subclusters.py:25:    "94_v33",
scripts/export_subclusters.py:26:    "95_v33",
scripts/benchmark_hybrid_v06.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v06.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_sub_rerank_v02.py:18:    / "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_sub_rerank_v02.py:28:    / "data/output/benchmark_sub_rerank_v02.json"
scripts/benchmark_sub_rerank_v02.py:147:                        "_v33",
scripts/benchmark_sub_rerank_v02.py:194:                sub_best["address"]+"_v33"
scripts/sort_sequence_v38_1.py:15:    "data/output/benchmark_v1/benchmark.json"
scripts/compare_benchmark_sub.py:12:    / "data/output/benchmark_v1/benchmark.json"
scripts/compare_benchmark_sub.py:17:    / "data/output/benchmark_sub_exp/benchmark.json"
scripts/export_visual_compare.py:8:OUT = Path("data/output/check_visual")
scripts/export_visual_compare.py:11:def export_v33():
scripts/export_visual_compare.py:15:            "data/output/full_recognize_v33_test_clean.json",
scripts/export_visual_compare.py:26:            "v33" /
scripts/export_visual_compare.py:44:            "data/output/full_recognize_hybrid_v12_test.json",
scripts/export_visual_compare.py:72:export_v33()
scripts/analyze_sequence_v38.py:30:    prev = int(rows[i - 1]["v33"])
scripts/analyze_sequence_v38.py:31:    cur = int(rows[i]["v33"])
scripts/analyze_sequence_v38.py:48:            f"{rows[i-1]['v33']} -> {rows[i]['v33']}"
scripts/analyze_sequence_v38.py:68:                f"TOP1={r['v33']:>2} "
scripts/analyze_sequence_v38.py:129:                f"TOP1={r['v33']:>2} "
scripts/analyze_sequence_v38.py:147:current = int(rows[0]["v33"])
scripts/analyze_sequence_v38.py:151:    value = int(rows[i]["v33"])
scripts/analyze_sequence_v38.py:179:                f"TOP1={r['v33']} "
scripts/benchmark_hybrid_v09.py:17:    "data/output/benchmark_sub_exp/benchmark.json"
scripts/benchmark_hybrid_v09.py:27:    "data/output/benchmark_hybrid_v09.json"
scripts/qwen_prompt_ablation.py:12:    "data/output/test_sorted_v2/78_v33/Комарова13_04.JPG"
scripts/sort_neighbor_v35.py:43:    return value.replace("_v33", "")
scripts/sort_neighbor_v35.py:155:            # Иначе сохраняем v33.
scripts/sort_neighbor_v35.py:223:            "v33": current,
scripts/sort_neighbor_v35.py:297:        "v33",
app/web/components/photos.py.before_pg_link_20260816_183647:35:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_pg_link_20260816_183647:101:            ).replace("_v33", "")
app/web/components/photos.py.before_pg_link_20260816_183647:717:                                    "_v33",
app/web/components/photos.py.before_client_filter:36:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_client_filter:102:            ).replace("_v33", "")
app/web/components/photos.py.before_client_filter:758:                                    "_v33",
app/web/components/photos_before_cache_20260816_145128.py:24:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos_before_cache_20260816_145128.py:59:            "_v33",
app/web/components/photos_before_cache_20260816_145128.py:350:                                    "_v33",
app/web/components/photos.py.before_info_panel_20260816_184210:36:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_info_panel_20260816_184210:102:            ).replace("_v33", "")
app/web/components/photos.py.before_info_panel_20260816_184210:718:                                    "_v33",
app/web/components/photos.py.before_viewer_layout_20260816_183842:36:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_viewer_layout_20260816_183842:102:            ).replace("_v33", "")
app/web/components/photos.py.before_viewer_layout_20260816_183842:718:                                    "_v33",
app/web/components/technical_modules/photo_processing.py:30:                value="/data/output/test_sorted_v2"
app/web/components/technical_modules/photo_processing.py:43:            "DINO / v33 → определение адреса → сортировка → Qwen3-VL 4B"
app/web/components/technical_modules/fingerprints.py:17:            "Рабочая версия: DINO / v33"
app/web/components/addresses.py:16:    return PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_client_filter_v3:38:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_client_filter_v3:104:            ).replace("_v33", "")
app/web/components/photos.py.before_client_filter_v3:746:                                    "_v33",
app/web/components/photos.py:61:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py:127:            ).replace("_v33", "")
app/web/components/photos.py:699:                            "_v33",
app/web/components/photos.py:1024:                                    "_v33",
app/web/components/photos.py.before_client_filter_v2:36:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_client_filter_v2:102:            ).replace("_v33", "")
app/web/components/photos.py.before_client_filter_v2:758:                                    "_v33",
app/web/config.py:10:# Результат тестового распознавания v33.
app/web/config.py:16:    / "test_sorted_v2"
app/web/client_db.py:30:                            '_v33$',
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 21:52:22

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed scene fingerprint architecture and recognition workflow**
>
> 
>
> Worked for 7s

Да. Теперь картина ясная.

**Создание fingerprint сюда не подключаем.** Оно остаётся отдельной операцией.

Для кнопки **«ЗАПУСТИТЬ ОБРАБОТКУ»** нам нужен именно рабочий pipeline:

**папка фотографий → DINO/v33 → первый кандидат → присвоение адреса → сортировка → отчёт → затем Qwen3-VL 4B**

При этом существующий `JobQueue`/`Worker` сейчас заточен под **создание fingerprint**, поэтому напрямую использовать его для этой кнопки не надо.

Следующий шаг - найти **реальный готовый скрипт, который уже делает распознавание + сортировку**, чтобы не изобретать алгоритм заново.

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "=== SORT V2 ===" && \
cat -n scripts/sort_test_and_report_v2.py && \
echo "=== SORT BASELINE ===" && \
cat -n scripts/sort_baseline.py && \
echo "=== RECOGNIZER ===" && \
cat -n app/core/recognizer.py
```

После этого мы не будем трогать v33-алгоритм. **Просто обернём уже проверенную обработку в backend-функцию**, а кнопку в `photo_processing.py` подключим к ней.

И отдельно сделаем так, чтобы «Последняя обработка» могла читать результат этого запуска.

---

### 👤 **User** — 2026-08-16 21:52:55

папка фотографий → DINO/v33 → первый кандидат → присвоение адреса   схема у мня была сложнее

---

### 🤖 **Assistant** — 2026-08-16 21:52:55

Да, верно. Я слишком упростил схему.

**Fingerprint creation вообще отдельная ветка.** А рабочая обработка фотографий у нас была построена как более сложный каскад, где **v33 — только первый этап определения кандидата**, а не весь алгоритм.

По тому, что мы зафиксировали в проекте, правильнее мыслить так:

```text
ФОТОГРАФИИ ДНЯ
      │
      ▼
  подготовка / загрузка
      │
      ▼
 DINOv2 / v33
      │
      ▼
 первый кандидат
      │
      ├───────────────► уверенный случай
      │                       │
      │                       ▼
      │                 адрес найден
      │
      └───────────────► сложный случай
                              │
                              ▼
                    дополнительные признаки
                    / subfingerprint
                    / соседние кадры
                    / последовательность
                              │
                              ▼
                       уточнение кандидата
                              │
                              ▼
                       ФИНАЛЬНЫЙ АДРЕС
                              │
                              ▼
                    копирование / переименование
                    / раскладывание по папкам
                              │
                              ▼
                         ОТЧЁТ
                              │
                              ▼
                    Qwen3-VL 4B — следующий
                         этап обработки
```

И особенно важно: мы **не должны сейчас переносить в web-интерфейс какую-нибудь `sort_test_and_report_v2.py` только потому, что она умеет сортировать**. Это могло бы случайно подменить утверждённый алгоритм.

У нас были отдельные эксперименты с:

- `v33`
- `subfingerprints`
- последовательностью кадров
- rerank
- neighbor/sequence
- hybrid
- выбором **первого кандидата как основы**
- специальными сложными случаями

И в конце мы как раз **заморозили рабочую логику v33 + первого кандидата**, после проверки 78–95.

Поэтому сейчас правильный шаг другой:

### Сначала восстановим именно утверждённый production-пайплайн

Нужно найти **тот конкретный скрипт/версию**, которую мы признали финальной для:

> тестовая папка → распознавание → первый кандидат → финальное назначение → сортировка → report

а уже потом вынести её в backend.

Дай мне вывод:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "=== FINAL SORT SCRIPTS ===" && \
ls -lt scripts/sort*.py scripts/*sequence*.py scripts/*hybrid*.py 2>/dev/null | head -80 && \
echo "=== FINAL V33 RESULTS ===" && \
find output data/output -maxdepth 3 -type f \
  \( -name '*.json' -o -name '*.csv' -o -name '*.log' \) \
  -printf '%TY-%Tm-%Td %TH:%TM  %p\n' 2>/dev/null | sort -r | head -100
```

**Ничего пока не меняем в коде.** Сначала точно восстановим нашу замороженную схему, и только потом подключим кнопку «Запустить обработку».

---

### 👤 **User** — 2026-08-16 21:53:48

echo "=== FINAL SORT SCRIPTS ===" && \
ls -lt scripts/sort*.py scripts/*sequence*.py scripts/*hybrid*.py 2>/dev/null | head -80 && \
echo "=== FINAL V33 RESULTS ===" && \
find output data/output -maxdepth 3 -type f \
  $ -name '*.json' -o -name '*.csv' -o -name '*.log' $ \
  -printf '%TY-%Tm-%Td %TH:%TM  %p\n' 2>/dev/null | sort -r | head -100
=== FINAL SORT SCRIPTS ===
-rw-rw-r-- 1 alexice alexice  7490 Aug 15 21:12 scripts/benchmark_hybrid_v12_full.py
-rw-rw-r-- 1 alexice alexice  6933 Aug 15 21:01 scripts/benchmark_hybrid_v11.py
-rw-rw-r-- 1 alexice alexice  7019 Aug 15 20:58 scripts/benchmark_hybrid_v10_debug.py
-rw-rw-r-- 1 alexice alexice  6934 Aug 15 20:57 scripts/benchmark_hybrid_v09.py
-rw-rw-r-- 1 alexice alexice  6340 Aug 15 20:55 scripts/benchmark_hybrid_v08.py
-rw-rw-r-- 1 alexice alexice  6239 Aug 15 20:49 scripts/benchmark_hybrid_v07.py
-rw-rw-r-- 1 alexice alexice  6239 Aug 15 20:42 scripts/benchmark_hybrid_v06.py
-rw-rw-r-- 1 alexice alexice  5888 Aug 15 20:40 scripts/benchmark_hybrid_v05.py
-rw-rw-r-- 1 alexice alexice  6216 Aug 15 20:38 scripts/benchmark_hybrid_v04.py
-rw-rw-r-- 1 alexice alexice  5462 Aug 15 20:34 scripts/benchmark_hybrid_v03.py
-rw-rw-r-- 1 alexice alexice  5619 Aug 15 20:32 scripts/benchmark_hybrid_v02.py
-rw-rw-r-- 1 alexice alexice  5441 Aug 15 20:27 scripts/benchmark_hybrid_v01.py
-rw-rw-r-- 1 alexice alexice  4915 Aug 15 20:09 scripts/sort_sequence_sub_v01.py
-rw-rw-r-- 1 alexice alexice  4915 Aug 15 20:09 scripts/sort_sequence_sub_v01.py
-rw-rw-r-- 1 alexice alexice  4909 Aug 15 19:19 scripts/sort_sequence_v38_1_subtest.py
-rw-rw-r-- 1 alexice alexice  4909 Aug 15 19:19 scripts/sort_sequence_v38_1_subtest.py
-rw-rw-r-- 1 alexice alexice  4909 Aug 15 15:46 scripts/sort_sequence_v39.py
-rw-rw-r-- 1 alexice alexice  4909 Aug 15 15:46 scripts/sort_sequence_v39.py
-rw-rw-r-- 1 alexice alexice  4909 Aug 15 15:43 scripts/sort_sequence_v38_1.py
-rw-rw-r-- 1 alexice alexice  4909 Aug 15 15:43 scripts/sort_sequence_v38_1.py
-rw-rw-r-- 1 alexice alexice  4434 Aug 15 15:41 scripts/sort_sequence_v38.py
-rw-rw-r-- 1 alexice alexice  4434 Aug 15 15:41 scripts/sort_sequence_v38.py
-rwxrwxr-x 1 alexice alexice  9006 Aug 15 15:26 scripts/dry_run_best_sequence.py
-rw-rw-r-- 1 alexice alexice  4172 Aug 15 14:55 scripts/analyze_sequence_v38.py
-rw-rw-r-- 1 alexice alexice  8326 Aug 15 14:53 scripts/sort_neighbor_v37.py
-rw-rw-r-- 1 alexice alexice  9715 Aug 15 14:50 scripts/sort_neighbor_v36_img.py
-rw-rw-r-- 1 alexice alexice  9706 Aug 15 14:46 scripts/sort_neighbor_v36.py
-rwxrwxr-x 1 alexice alexice  7876 Aug 15 14:41 scripts/sort_neighbor_v35_benchmark.py
-rwxrwxr-x 1 alexice alexice  9217 Aug 15 13:41 scripts/sort_neighbor_v35.py
-rwxrwxr-x 1 alexice alexice 10446 Aug 15 13:36 scripts/sort_neighbor_v34.py
-rwxrwxr-x 1 alexice alexice  5152 Aug 15 13:08 scripts/sort_margin005_best.py
-rwxrwxr-x 1 alexice alexice  4302 Aug 15 02:26 scripts/sort_baseline.py
-rwxrwxr-x 1 alexice alexice 10682 Aug 15 02:16 scripts/sort_test_and_report_v2.py
-rwxrwxr-x 1 alexice alexice  9500 Aug 15 02:14 scripts/sort_test_and_report.py
=== FINAL V33 RESULTS ===
2026-08-16 14:37  data/output/test_sorted_v2/statistics.json
2026-08-16 14:37  data/output/test_sorted_v2/report.json
2026-08-16 14:37  data/output/test_sorted_v2/report.csv
2026-08-16 14:37  data/output/test_sorted_v2/recognition.json
2026-08-16 01:48  data/output/found_banners/видео_сизякин/results.json
2026-08-16 01:22  data/output/banner_search_v03_3/Нагибина24_06/result.json
2026-08-16 01:22  data/output/banner_search_v03_3/Нагибина24_01/result.json
2026-08-16 01:21  data/output/banner_search_v03_3/Нагибина24_11/result.json
2026-08-16 01:21  data/output/banner_search_v03_3/Малиновского_к_Доватора_01/result.json
2026-08-16 01:21  data/output/banner_search_v03_3/Ленина125_06/result.json
2026-08-16 01:21  data/output/banner_search_v03_3/Комарова13_20/result.json
2026-08-16 01:20  data/output/banner_search_v03_3/Стачки_41_07/result.json
2026-08-16 01:20  data/output/banner_search_v03_3/Радиаторный_22/result.json
2026-08-16 01:20  data/output/banner_search_v03_3/Радиаторный_14/result.json
2026-08-16 01:20  data/output/banner_search_v03_3/Зорге_14/result.json
2026-08-16 01:19  data/output/banner_search_v03_3/Шеболдаева8_05/result.json
2026-08-16 01:19  data/output/banner_search_v03_3/Радиаторный_23/result.json
2026-08-16 01:19  data/output/banner_search_v03_3/КА_04/result.json
2026-08-16 01:19  data/output/banner_search_v03_3/Ашхабадский_17/result.json
2026-08-16 01:18  data/output/banner_search_v03_3/Радиаторный_02/result.json
2026-08-16 01:18  data/output/banner_search_v03_3/Малиновского_к_Доватора_06/result.json
2026-08-16 01:18  data/output/banner_search_v03_3/Малиновского_к_Доватора_04/result.json
2026-08-16 01:18  data/output/banner_search_v03_3/Комарова13_06/result.json
2026-08-16 01:17  data/output/banner_search_v03_3/Стачки_41_03/result.json
2026-08-16 01:17  data/output/banner_search_v03_3/Малиновского(_05/result.json
2026-08-16 01:17  data/output/banner_search_v03_3/Вавилова52_12/result.json
2026-08-16 01:16  data/output/banner_search_v03_3/Радиаторный_05/result.json
2026-08-16 01:16  data/output/banner_search_v03_3/Малиновского_к_Доватора_15/result.json
2026-08-16 01:16  data/output/banner_search_v03_3/Зорге_02/result.json
2026-08-16 01:16  data/output/banner_search_v03_3/Добровольского17_07/result.json
2026-08-16 01:15  data/output/banner_search_v03_3/Стачки_41_01/result.json
2026-08-16 01:15  data/output/banner_search_v03_3/Малиновского_к_Стачки_05/result.json
2026-08-16 01:05  data/output/banner_search/Стачки_41_07/result.json
2026-08-16 01:05  data/output/banner_search/Зорге_14/result.json
2026-08-16 01:04  data/output/banner_search/Шеболдаева8_05/result.json
2026-08-16 01:04  data/output/banner_search/Радиаторный_23/result.json
2026-08-16 01:04  data/output/banner_search/Радиаторный_22/result.json
2026-08-16 01:04  data/output/banner_search/Радиаторный_14/result.json
2026-08-16 01:04  data/output/banner_search/КА_04/result.json
2026-08-16 01:04  data/output/banner_search/Ашхабадский_17/result.json
2026-08-16 01:03  data/output/banner_search/Стачки_41_03/result.json
2026-08-16 01:03  data/output/banner_search/Радиаторный_02/result.json
2026-08-16 01:03  data/output/banner_search/Малиновского_к_Доватора_04/result.json
2026-08-16 01:03  data/output/banner_search/Комарова13_06/result.json
2026-08-16 01:02  data/output/banner_search/Малиновского_к_Доватора_06/result.json
2026-08-16 01:02  data/output/banner_search/Малиновского(_05/result.json
2026-08-16 01:02  data/output/banner_search/Вавилова52_12/result.json
2026-08-16 01:01  data/output/banner_search/Стачки_41_01/result.json
2026-08-16 01:01  data/output/banner_search/Радиаторный_05/result.json
2026-08-16 01:01  data/output/banner_search/Малиновского_к_Стачки_05/result.json
2026-08-16 01:01  data/output/banner_search/Малиновского_к_Доватора_15/result.json
2026-08-16 01:01  data/output/banner_search/Зорге_02/result.json
2026-08-16 01:01  data/output/banner_search/Добровольского17_07/result.json
2026-08-16 00:59  data/output/banner_search/Ашхабадский_01/result.json
2026-08-16 00:59  data/output/banner_search/summary.json
2026-08-16 00:55  data/output/banner_candidates/видео_сизякин/candidates.json
2026-08-16 00:51  data/output/found_banners_debug/видео_сизякин/result.json
2026-08-16 00:51  data/output/found_banners_debug/Screenshot from 2026-08-16 00-38-11/result.json
2026-08-16 00:39  data/output/found_banners/купер/result.json
2026-08-16 00:39  data/output/found_banners/выборы/result.json
2026-08-16 00:39  data/output/found_banners/видео_сизякин/result.json
2026-08-16 00:39  data/output/found_banners/бетсити/result.json
2026-08-16 00:39  data/output/found_banners/Screenshot from 2026-08-16 00-23-32/result.json
2026-08-16 00:33  data/output/found_banners/Screenshot from 2026-08-16 00-22-42/result.json
2026-08-16 00:33  data/output/found_banners/Screenshot from 2026-08-16 00-22-23/result.json
2026-08-16 00:33  data/output/found_banners/Screenshot from 2026-08-16 00-13-31/result.json
2026-08-15 21:12  data/output/full_recognize_hybrid_v12_test.json
2026-08-15 21:11  data/output/benchmark_hybrid_v11.json
2026-08-15 21:04  data/output/full_recognize_v33_test_clean.json
2026-08-15 21:03  data/output/full_recognize_v33_test.json
2026-08-15 21:01  output/hybrid_v11.log
2026-08-15 21:01  data/output/benchmark_hybrid_v09.json
2026-08-15 20:57  output/hybrid_v09.log
2026-08-15 20:55  output/hybrid_v08.log
2026-08-15 20:55  data/output/benchmark_hybrid_v08.json
2026-08-15 20:54  data/output/benchmark_hybrid_v07.json
2026-08-15 20:49  output/hybrid_v07.log
2026-08-15 20:42  output/hybrid_v06.log
2026-08-15 20:42  data/output/benchmark_hybrid_v03.json
2026-08-15 20:41  output/hybrid_v05.log
2026-08-15 20:33  data/output/benchmark_hybrid_v02.json
2026-08-15 20:27  data/output/benchmark_hybrid_v01.json
2026-08-15 20:21  data/output/benchmark_sub_rerank_v04.json
2026-08-15 20:19  data/output/benchmark_sub_rerank_v03.json
2026-08-15 20:15  data/output/benchmark_sub_rerank_v02.json
2026-08-15 20:13  data/output/benchmark_sub_rerank_v01.json
2026-08-15 20:10  output/sequence_sub_v01/run.log
2026-08-15 20:08  output/compare_sub/benchmark_sub.log
2026-08-15 20:08  data/output/benchmark_sub_exp/benchmark.json
2026-08-15 20:04  output/compare_sub/v33_sequence.log
2026-08-15 19:12  output/test_final_v33/run.log
2026-08-15 15:34  data/output/benchmark_v1/benchmark.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 21:53:51

Вот теперь видно гораздо лучше. И главное — **финальная рабочая обработка у нас не совпадает ни с `sort_baseline.py`, ни просто с `v33`**.

По датам получается такая история:

```text
15:34  benchmark_v1
   ↓
19:12  test_final_v33
   ↓
20:04–20:21  sequence / sub-rerank
   ↓
20:27–21:11  hybrid v01 → v11
   ↓
21:12  hybrid v12_full
   ↓
16 августа 14:37
data/output/test_sorted_v2/
    recognition.json
    report.json
    report.csv
    statistics.json
```

То есть **`test_sorted_v2` очень похоже на последний фактический production-like прогон**, а `benchmark_hybrid_v12_full` — на последнюю экспериментальную ветку алгоритма.

Но пока нельзя называть `v12` рабочим алгоритмом: benchmark — это ещё не обязательно тот код, которым реально сортировалась папка.

### Сейчас нужно установить точную цепочку

Дай вывод вот этой команды:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SORT V2 ================" && \
cat -n scripts/sort_test_and_report_v2.py && \
echo "================ HYBRID V12 ================" && \
cat -n scripts/benchmark_hybrid_v12_full.py && \
echo "================ RECOGNITION RESULT ================" && \
python - <<'PY'
import json
from pathlib import Path

for name in [
    "data/output/test_sorted_v2/recognition.json",
    "data/output/test_sorted_v2/report.json",
    "data/output/test_sorted_v2/statistics.json",
    "data/output/full_recognize_hybrid_v12_test.json",
]:
    p = Path(name)
    print(f"\n===== {name} =====")
    if not p.exists():
        print("MISSING")
        continue
    data = json.loads(p.read_text())
    if isinstance(data, dict):
        print("KEYS:", list(data.keys()))
        for k, v in data.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                print(f"{k}: {v}")
            elif isinstance(v, list):
                print(f"{k}: list[{len(v)}]")
            elif isinstance(v, dict):
                print(f"{k}: dict[{len(v)}]")
    else:
        print(type(data).__name__, len(data))
        if data:
            print("FIRST:", data[0])
PY
```

**После этого мы сможем точно восстановить архитектуру**, а не гадать по названиям.

И я уже вижу важное разделение:

### 1. Fingerprint creation

Отдельно:

```text
исходная папка адреса
        ↓
создание / обновление fingerprint
```

**В кнопку обработки фотографий это НЕ входит.**

### 2. Рабочая обработка

Отдельно:

```text
фото дня
   ↓
DINO / v33
   ↓
первичные кандидаты
   ↓
дополнительная логика для неоднозначных случаев
   ↓
финальный кандидат
   ↓
адрес
   ↓
копирование / переименование
   ↓
report
```

### 3. Qwen

И тоже отдельный следующий этап:

```text
результат сортировки
        ↓
Qwen3-VL 4B
        ↓
дальнейшая обработка макетов / баннеров
```

Поэтому **сейчас код UI вообще не трогаем**. Сначала найдём точный алгоритм последнего успешного `test_sorted_v2`, а затем сделаем для него backend-обёртку. Это безопаснее и сохраняет нашу замороженную логику.

---

### 👤 **User** — 2026-08-16 21:54:49

cat -n scripts/benchmark_hybrid_v12_full.py && \
echo "================ RECOGNITION RESULT ================" && \
python - <<'PY'
import json
from pathlib import Path

for name in [
    "data/output/test_sorted_v2/recognition.json",
    "data/output/test_sorted_v2/report.json",
    "data/output/test_sorted_v2/statistics.json",
    "data/output/full_recognize_hybrid_v12_test.json",
]:
    p = Path(name)
    print(f"\n===== {name} =====")
    if not p.exists():
        print("MISSING")
        continue
    data = json.loads(p.read_text())
    if isinstance(data, dict):
PY          print("FIRST:", data[0])en(data)), bool)) or v is None:
================ SORT V2 ================
     1	#!/usr/bin/env python3
     2	
     3	import csv
     4	import json
     5	import os
     6	import shutil
     7	import subprocess
     8	import time
     9	from pathlib import Path
    10	from collections import Counter
    11	
    12	import psutil
    13	
    14	
    15	PROJECT = Path(__file__).resolve().parent.parent
    16	
    17	INPUT_DIR = PROJECT / "data/input/test"
    18	OUTPUT_DIR = PROJECT / "data/output/test_sorted_v2"
    19	
    20	FINGERPRINTS = [
    21	    f"{i}_v33"
    22	    for i in range(78, 96)
    23	]
    24	
    25	RECOGNITION_JSON = OUTPUT_DIR / "recognition.json"
    26	REPORT_CSV = OUTPUT_DIR / "report.csv"
    27	REPORT_JSON = OUTPUT_DIR / "report.json"
    28	STATISTICS_JSON = OUTPUT_DIR / "statistics.json"
    29	
    30	
    31	def gpu_stats():
    32	    try:
    33	        result = subprocess.run(
    34	            [
    35	                "nvidia-smi",
    36	                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
    37	                "--format=csv,noheader,nounits",
    38	            ],
    39	            capture_output=True,
    40	            text=True,
    41	            timeout=3,
    42	        )
    43	
    44	        line = result.stdout.strip().splitlines()[0]
    45	        parts = [x.strip() for x in line.split(",")]
    46	
    47	        return {
    48	            "gpu_name": parts[0],
    49	            "gpu_utilization_percent": float(parts[1]),
    50	            "gpu_memory_used_mb": float(parts[2]),
    51	            "gpu_memory_total_mb": float(parts[3]),
    52	        }
    53	
    54	    except Exception:
    55	        return {
    56	            "gpu_name": None,
    57	            "gpu_utilization_percent": None,
    58	            "gpu_memory_used_mb": None,
    59	            "gpu_memory_total_mb": None,
    60	        }
    61	
    62	
    63	def find_json(text):
    64	    """
    65	    Find the actual JSON array, ignoring messages such as:
    66	        [SceneEmbedder]
    67	        [Recognizer]
    68	    """
    69	
    70	    decoder = json.JSONDecoder()
    71	
    72	    for i, ch in enumerate(text):
    73	        if ch != "[":
    74	            continue
    75	
    76	        candidate = text[i:]
    77	
    78	        try:
    79	            obj, end = decoder.raw_decode(candidate)
    80	
    81	            if isinstance(obj, list):
    82	                return obj
    83	
    84	        except json.JSONDecodeError:
    85	            pass
    86	
    87	    raise RuntimeError("Не удалось найти JSON-массив в выводе recognition")
    88	
    89	
    90	def run_recognition():
    91	    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    92	
    93	    fp_arg = ",".join(FINGERPRINTS)
    94	
    95	    cmd = [
    96	        "uv",
    97	        "run",
    98	        "scene-fingerprint",
    99	        "recognize",
   100	        str(INPUT_DIR),
   101	        "--top-k",
   102	        "5",
   103	        "--threshold",
   104	        "0.0",
   105	        "--fingerprints",
   106	        fp_arg,
   107	        "--json",
   108	    ]
   109	
   110	    print("=" * 80)
   111	    print("RUNNING RECOGNITION")
   112	    print("=" * 80)
   113	
   114	    print("Input:", INPUT_DIR)
   115	    print("Fingerprints:", ", ".join(FINGERPRINTS))
   116	    print()
   117	
   118	    start = time.perf_counter()
   119	
   120	    process = subprocess.run(
   121	        cmd,
   122	        cwd=PROJECT,
   123	        capture_output=True,
   124	        text=True,
   125	    )
   126	
   127	    elapsed = time.perf_counter() - start
   128	
   129	    if process.returncode != 0:
   130	        print(process.stdout)
   131	        print(process.stderr)
   132	        raise RuntimeError(
   133	            f"recognize завершился с кодом {process.returncode}"
   134	        )
   135	
   136	    combined = process.stdout + "\n" + process.stderr
   137	
   138	    data = find_json(combined)
   139	
   140	    RECOGNITION_JSON.write_text(
   141	        json.dumps(data, ensure_ascii=False, indent=2),
   142	        encoding="utf-8",
   143	    )
   144	
   145	    return data, elapsed
   146	
   147	
   148	def copy_images(data):
   149	    print()
   150	    print("=" * 80)
   151	    print("SORTING")
   152	    print("=" * 80)
   153	
   154	    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
   155	
   156	    rows = []
   157	
   158	    counters = Counter()
   159	
   160	    for item in data:
   161	        source = Path(item["file"])
   162	
   163	        # Главный принцип:
   164	        # ВСЕГДА используем best_id = первый кандидат.
   165	        assigned_id = item.get("best_id")
   166	
   167	        if not assigned_id:
   168	            continue
   169	
   170	        destination_dir = OUTPUT_DIR / assigned_id
   171	        destination_dir.mkdir(parents=True, exist_ok=True)
   172	
   173	        destination = destination_dir / source.name
   174	
   175	        shutil.copy2(source, destination)
   176	
   177	        counters[assigned_id] += 1
   178	
   179	        candidates = item.get("candidates", [])
   180	
   181	        row = {
   182	            "file": str(source),
   183	            "filename": source.name,
   184	            "assigned_id": assigned_id,
   185	            "score": item.get("score"),
   186	            "second_score": item.get("second_score"),
   187	            "margin": item.get("margin"),
   188	            "confidence": item.get("confidence"),
   189	            "status": item.get("status"),
   190	            "best_image": item.get("best_image"),
   191	            "best_image_score": item.get("best_image_score"),
   192	            "global": None,
   193	            "environment": None,
   194	            "color": None,
   195	            "spatial": None,
   196	            "candidate_2": None,
   197	            "candidate_2_score": None,
   198	            "candidate_3": None,
   199	            "candidate_3_score": None,
   200	            "candidate_4": None,
   201	            "candidate_4_score": None,
   202	            "candidate_5": None,
   203	            "candidate_5_score": None,
   204	        }
   205	
   206	        if candidates:
   207	            c = candidates[0]
   208	
   209	            row["global"] = c.get("global")
   210	            row["environment"] = c.get("environment")
   211	            row["color"] = c.get("color")
   212	            row["spatial"] = c.get("spatial")
   213	
   214	        for n in range(1, min(5, len(candidates))):
   215	            c = candidates[n]
   216	
   217	            row[f"candidate_{n+1}"] = c.get("id")
   218	            row[f"candidate_{n+1}_score"] = c.get("score")
   219	
   220	        rows.append(row)
   221	
   222	    print()
   223	
   224	    for k in sorted(counters, key=lambda x: int(x.split("_")[0])):
   225	        print(f"{k:10s} {counters[k]:4d}")
   226	
   227	    return rows, counters
   228	
   229	
   230	def write_reports(rows, counters, recognition_time):
   231	    fields = [
   232	        "file",
   233	        "filename",
   234	        "assigned_id",
   235	        "score",
   236	        "second_score",
   237	        "margin",
   238	        "confidence",
   239	        "status",
   240	        "best_image",
   241	        "best_image_score",
   242	        "global",
   243	        "environment",
   244	        "color",
   245	        "spatial",
   246	        "candidate_2",
   247	        "candidate_2_score",
   248	        "candidate_3",
   249	        "candidate_3_score",
   250	        "candidate_4",
   251	        "candidate_4_score",
   252	        "candidate_5",
   253	        "candidate_5_score",
   254	    ]
   255	
   256	    with open(REPORT_CSV, "w", newline="", encoding="utf-8-sig") as f:
   257	        writer = csv.DictWriter(f, fieldnames=fields)
   258	        writer.writeheader()
   259	        writer.writerows(rows)
   260	
   261	    scores = [
   262	        float(x["score"])
   263	        for x in rows
   264	        if x["score"] is not None
   265	    ]
   266	
   267	    margins = [
   268	        float(x["margin"])
   269	        for x in rows
   270	        if x["margin"] is not None
   271	    ]
   272	
   273	    status_counter = Counter(
   274	        x["status"]
   275	        for x in rows
   276	        if x["status"]
   277	    )
   278	
   279	    confidence_counter = Counter(
   280	        x["confidence"]
   281	        for x in rows
   282	        if x["confidence"]
   283	    )
   284	
   285	    process = psutil.Process(os.getpid())
   286	
   287	    stats = {
   288	        "total_images": len(rows),
   289	
   290	        "recognition_time_seconds": recognition_time,
   291	
   292	        "images_per_second":
   293	            len(rows) / recognition_time
   294	            if recognition_time > 0 else None,
   295	
   296	        "milliseconds_per_image":
   297	            recognition_time * 1000 / len(rows)
   298	            if rows else None,
   299	
   300	        "score": {
   301	            "min": min(scores) if scores else None,
   302	            "mean": sum(scores) / len(scores) if scores else None,
   303	            "max": max(scores) if scores else None,
   304	        },
   305	
   306	        "margin": {
   307	            "min": min(margins) if margins else None,
   308	            "mean": sum(margins) / len(margins) if margins else None,
   309	            "max": max(margins) if margins else None,
   310	        },
   311	
   312	        "status": dict(status_counter),
   313	        "confidence": dict(confidence_counter),
   314	
   315	        "assigned": dict(counters),
   316	
   317	        "cpu": {
   318	            "logical_cpus": psutil.cpu_count(),
   319	            "process_cpu_percent": process.cpu_percent(interval=0.5),
   320	        },
   321	
   322	        "ram": {
   323	            "total_mb":
   324	                psutil.virtual_memory().total / 1024 / 1024,
   325	
   326	            "used_mb":
   327	                psutil.virtual_memory().used / 1024 / 1024,
   328	
   329	            "available_mb":
   330	                psutil.virtual_memory().available / 1024 / 1024,
   331	
   332	            "process_rss_mb":
   333	                process.memory_info().rss / 1024 / 1024,
   334	        },
   335	
   336	        "gpu": gpu_stats(),
   337	    }
   338	
   339	    REPORT_JSON.write_text(
   340	        json.dumps(rows, ensure_ascii=False, indent=2),
   341	        encoding="utf-8",
   342	    )
   343	
   344	    STATISTICS_JSON.write_text(
   345	        json.dumps(stats, ensure_ascii=False, indent=2),
   346	        encoding="utf-8",
   347	    )
   348	
   349	    return stats
   350	
   351	
   352	def main():
   353	    print()
   354	    print("=" * 80)
   355	    print("SCENE FINGERPRINT TEST SORTER V2")
   356	    print("=" * 80)
   357	
   358	    if not INPUT_DIR.exists():
   359	        raise RuntimeError(f"Нет папки: {INPUT_DIR}")
   360	
   361	    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
   362	
   363	    start_total = time.perf_counter()
   364	
   365	    data, recognition_time = run_recognition()
   366	
   367	    rows, counters = copy_images(data)
   368	
   369	    stats = write_reports(
   370	        rows,
   371	        counters,
   372	        recognition_time,
   373	    )
   374	
   375	    total_time = time.perf_counter() - start_total
   376	
   377	    stats["total_wall_time_seconds"] = total_time
   378	
   379	    STATISTICS_JSON.write_text(
   380	        json.dumps(stats, ensure_ascii=False, indent=2),
   381	        encoding="utf-8",
   382	    )
   383	
   384	    print()
   385	    print("=" * 80)
   386	    print("STATISTICS")
   387	    print("=" * 80)
   388	
   389	    print(f"Images:             {stats['total_images']}")
   390	    print(f"Recognition time:   {recognition_time:.2f} sec")
   391	    print(f"Total time:         {total_time:.2f} sec")
   392	    print(
   393	        f"Speed:              "
   394	        f"{stats['images_per_second']:.2f} images/sec"
   395	    )
   396	    print(
   397	        f"Per image:          "
   398	        f"{stats['milliseconds_per_image']:.1f} ms"
   399	    )
   400	
   401	    print()
   402	    print("SCORE")
   403	    print(f"  min:              {stats['score']['min']:.4f}")
   404	    print(f"  mean:             {stats['score']['mean']:.4f}")
   405	    print(f"  max:              {stats['score']['max']:.4f}")
   406	
   407	    print()
   408	    print("MARGIN")
   409	    print(f"  min:              {stats['margin']['min']:.4f}")
   410	    print(f"  mean:             {stats['margin']['mean']:.4f}")
   411	    print(f"  max:              {stats['margin']['max']:.4f}")
   412	
   413	    print()
   414	    print("RAM")
   415	    print(
   416	        f"  process RSS:      "
   417	        f"{stats['ram']['process_rss_mb']:.1f} MB"
   418	    )
   419	
   420	    print()
   421	    print("GPU")
   422	    print(f"  name:             {stats['gpu']['gpu_name']}")
   423	    print(
   424	        f"  utilization:      "
   425	        f"{stats['gpu']['gpu_utilization_percent']}%"
   426	    )
   427	    print(
   428	        f"  memory:           "
   429	        f"{stats['gpu']['gpu_memory_used_mb']} / "
   430	        f"{stats['gpu']['gpu_memory_total_mb']} MB"
   431	    )
   432	
   433	    print()
   434	    print("=" * 80)
   435	    print("OUTPUT")
   436	    print("=" * 80)
   437	
   438	    print("Sorted:", OUTPUT_DIR)
   439	    print("CSV:   ", REPORT_CSV)
   440	    print("JSON:  ", REPORT_JSON)
   441	    print("Stats: ", STATISTICS_JSON)
   442	
   443	
   444	if __name__ == "__main__":
   445	    main()
================ HYBRID V12 ================
     1	#!/usr/bin/env python3
     2	
     3	import json
     4	from pathlib import Path
     5	from collections import defaultdict, Counter
     6	
     7	import numpy as np
     8	
     9	from app.core.config import Settings
    10	from app.core.embedder import SceneEmbedder
    11	
    12	
    13	PROJECT = Path(__file__).resolve().parent.parent
    14	
    15	BENCHMARK = (
    16	    PROJECT /
    17	    "data/output/benchmark_sub_exp/benchmark.json"
    18	)
    19	
    20	SUB_DIR = (
    21	    PROJECT /
    22	    "data/fingerprints_sub_exp"
    23	)
    24	
    25	OUT = (
    26	    PROJECT /
    27	    "data/output/full_recognize_hybrid_v12_test.json"
    28	)
    29	
    30	
    31	MARGIN_LIMIT = 0.02
    32	
    33	GLOBAL_WEIGHT = 10.0
    34	SUB_WEIGHT = 2.5
    35	NEIGHBOR_WEIGHT = 6.0
    36	
    37	
    38	
    39	def normalize(x):
    40	
    41	    x = np.asarray(
    42	        x,
    43	        dtype=np.float32
    44	    )
    45	
    46	    n = np.linalg.norm(x)
    47	
    48	    if n > 0:
    49	        x = x / n
    50	
    51	    return x
    52	
    53	
    54	
    55	def load_subs():
    56	
    57	    result = {}
    58	
    59	    for d in sorted(SUB_DIR.iterdir()):
    60	
    61	        if not d.is_dir():
    62	            continue
    63	
    64	        f = d / "embeddings.npy"
    65	
    66	        if not f.exists():
    67	            continue
    68	
    69	        emb = np.load(
    70	            f
    71	        )
    72	
    73	        emb = np.array(
    74	            [
    75	                normalize(x)
    76	                for x in emb
    77	            ]
    78	        )
    79	
    80	        result[d.name] = emb
    81	
    82	
    83	    return result
    84	
    85	
    86	
    87	def get_neighbor_votes(rows, index):
    88	
    89	    votes = Counter()
    90	
    91	
    92	    if index <= 0:
    93	        return votes
    94	
    95	
    96	    if index >= len(rows)-1:
    97	        return votes
    98	
    99	
   100	    left = rows[index-1]["top1"]
   101	    right = rows[index+1]["top1"]
   102	
   103	
   104	    # только полное согласие
   105	
   106	    if left == right:
   107	
   108	        votes[left] = 1
   109	
   110	
   111	    return votes
   112	
   113	
   114	
   115	def main():
   116	
   117	    print("=" * 80)
   118	    print("HYBRID V03")
   119	    print("=" * 80)
   120	
   121	
   122	    with open(
   123	        BENCHMARK,
   124	        encoding="utf-8"
   125	    ) as f:
   126	
   127	        data = json.load(f)
   128	
   129	
   130	    rows = data["results"]
   131	
   132	
   133	    settings = Settings()
   134	
   135	    embedder = SceneEmbedder(
   136	        settings
   137	    )
   138	
   139	
   140	    subs = load_subs()
   141	
   142	
   143	    changed = []
   144	    all_results = []
   145	    sub_count = 0
   146	
   147	
   148	    for i, row in enumerate(rows):
   149	
   150	        old = row["top1"]
   151	
   152	
   153	        scores = defaultdict(float)
   154	
   155	
   156	        #
   157	        # GLOBAL TOP-5
   158	        #
   159	
   160	        for k in range(1, 6):
   161	
   162	            fp = row.get(
   163	                f"top{k}"
   164	            )
   165	
   166	            sc = row.get(
   167	                f"top{k}_score"
   168	            )
   169	
   170	            if fp:
   171	
   172	                scores[fp] += (
   173	                    float(sc)
   174	                    *
   175	                    GLOBAL_WEIGHT
   176	                )
   177	
   178	
   179	
   180	        #
   181	        # SUB ONLY BORDER CASES
   182	        #
   183	
   184	        margin = row.get(
   185	            "margin",
   186	            1
   187	        )
   188	
   189	
   190	        if margin < MARGIN_LIMIT:
   191	
   192	            sub_count += 1
   193	
   194	
   195	            image = Path(
   196	                row["file"]
   197	            )
   198	
   199	
   200	            query = embedder.embed_paths(
   201	                [image]
   202	            )[0]
   203	
   204	            query = normalize(
   205	                query
   206	            )
   207	
   208	
   209	            #
   210	            # ТОЛЬКО TOP1 и TOP2
   211	            #
   212	
   213	            candidates = [
   214	                row.get("top1"),
   215	                row.get("top2"),
   216	            ]
   217	
   218	
   219	            for parent in candidates:
   220	
   221	                if not parent:
   222	                    continue
   223	
   224	
   225	                for sub_id, sub_emb in subs.items():
   226	
   227	                    if not sub_id.startswith(
   228	                        parent
   229	                    ):
   230	                        continue
   231	
   232	
   233	                    sim = max(
   234	                        sub_emb @ query
   235	                    )
   236	
   237	
   238	                    if sim > 0.88:
   239	
   240	                        if sim > 0.92:
   241	                            bonus = 2.5
   242	                        else:
   243	                            bonus = 1.0
   244	
   245	                        scores[parent] += (
   246	                            float(sim)
   247	                            *
   248	                            bonus
   249	                        )
   250	
   251	
   252	
   253	        #
   254	        # SEQUENCE CONSENSUS
   255	        #
   256	        # Используем соседей только если
   257	        # слева и справа один и тот же адрес.
   258	        #
   259	
   260	        neighbors = get_neighbor_votes(
   261	            rows,
   262	            i
   263	        )
   264	
   265	        left_fp = None
   266	        right_fp = None
   267	
   268	        if i > 0:
   269	            left_fp = rows[i-1].get("top1")
   270	
   271	        if i < len(rows)-1:
   272	            right_fp = rows[i+1].get("top1")
   273	
   274	
   275	        if (
   276	            left_fp
   277	            and right_fp
   278	            and left_fp == right_fp
   279	        ):
   280	            scores[left_fp] += 3.0
   281	
   282	
   283	
   284	        #
   285	        # FINAL DECISION V09
   286	        #
   287	        # DINO TOP1 is default.
   288	        # Change only if hybrid has strong evidence.
   289	        #
   290	
   291	        best = old
   292	
   293	        ranked = sorted(
   294	            scores.items(),
   295	            key=lambda x: x[1],
   296	            reverse=True
   297	        )
   298	
   299	        if ranked:
   300	
   301	            candidate = ranked[0][0]
   302	
   303	            gain = (
   304	                scores[candidate]
   305	                -
   306	                scores.get(old, 0)
   307	            )
   308	
   309	            #
   310	            # Change only with real advantage
   311	            #
   312	            if (
   313	                candidate != old
   314	                and gain > 1.5
   315	            ):
   316	                best = candidate
   317	
   318	
   319	        old_score = scores.get(
   320	            old,
   321	            0
   322	        )
   323	
   324	        new_score = scores.get(
   325	            best,
   326	            0
   327	        )
   328	
   329	
   330	        # принимаем изменение только если
   331	        # новый кандидат реально сильнее
   332	
   333	        all_results.append(
   334	            {
   335	                "file":
   336	                    Path(
   337	                        row["file"]
   338	                    ).name,
   339	
   340	                "old":
   341	                    old,
   342	
   343	                "new":
   344	                    best,
   345	
   346	                "score":
   347	                    new_score,
   348	
   349	                "old_score":
   350	                    old_score,
   351	
   352	                "margin":
   353	                    margin,
   354	
   355	                "neighbors":
   356	                    dict(neighbors),
   357	            }
   358	        )
   359	
   360	
   361	
   362	        if (
   363	            best != old
   364	            and new_score > old_score
   365	        ):
   366	
   367	            changed.append(
   368	                {
   369	                    "file":
   370	                        Path(
   371	                            row["file"]
   372	                        ).name,
   373	
   374	                    "old":
   375	                        old,
   376	
   377	                    "new":
   378	                        best,
   379	
   380	                    "margin":
   381	                        margin,
   382	
   383	                    "neighbors":
   384	                        dict(neighbors),
   385	
   386	                    "old_score":
   387	                        scores[old],
   388	
   389	                    "new_score":
   390	                        scores[best],
   391	                }
   392	            )
   393	
   394	
   395	
   396	    OUT.parent.mkdir(
   397	        parents=True,
   398	        exist_ok=True
   399	    )
   400	
   401	
   402	    OUT.write_text(
   403	        json.dumps(
   404	            {
   405	                "checked":
   406	                    len(rows),
   407	
   408	                "sub_rerank":
   409	                    sub_count,
   410	
   411	                "changed":
   412	                    len(changed),
   413	
   414	                "results":
   415	                    all_results,
   416	            },
   417	            ensure_ascii=False,
   418	            indent=2
   419	        ),
   420	        encoding="utf-8"
   421	    )
   422	
   423	
   424	    print()
   425	    print(
   426	        "checked:",
   427	        len(rows)
   428	    )
   429	
   430	    print(
   431	        "sub rerank:",
   432	        sub_count
   433	    )
   434	
   435	    print(
   436	        "changed:",
   437	        len(changed)
   438	    )
   439	
   440	
   441	    for x in changed:
   442	
   443	        print()
   444	        print(
   445	            x["file"]
   446	        )
   447	
   448	        print(
   449	            x["old"],
   450	            "->",
   451	            x["new"]
   452	        )
   453	
   454	        print(
   455	            "neighbors:",
   456	            x["neighbors"]
   457	        )
   458	
   459	
   460	    print()
   461	    print("saved:")
   462	    print(OUT)
   463	
   464	
   465	
   466	if __name__ == "__main__":
   467	    main()
================ RECOGNITION RESULT ================
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 21:54:50

Да. Здесь как раз видно, что моя предыдущая формулировка **слишком упростила твою реальную схему**.

`Fingerprint creation` — это отдельный этап и в рабочую цепочку сортировки его включать нельзя.

А реальная схема у тебя была примерно такая:

```text
ПАПКА С ФОТОГРАФИЯМИ
        │
        ▼
   DINO / v33
        │
        ▼
 GLOBAL TOP-5
        │
        ├── обычный случай
        │      └── TOP-1 → адрес
        │
        └── пограничный случай
               │
               ▼
        margin < 0.02
               │
               ├── SUB-FINGERPRINT
               │      └── проверка TOP-1 / TOP-2
               │
               └── SEQUENCE CONSENSUS
                      └── сосед слева = сосед справа
                              │
                              ▼
                       корректировка кандидата
        │
        ▼
   FINAL DECISION
        │
        ▼
   ПРИСВОЕНИЕ АДРЕСА
        │
        ▼
 КОПИРОВАНИЕ / СОРТИРОВКА
```

Причём из `benchmark_hybrid_v12_full.py` видно важное: **v33 не был просто "первый кандидат и сразу адрес"**.

### Что реально делал последний hybrid

1. **DINO/v33 формировал TOP-5**.

2. Все пять кандидатов участвовали в начальном взвешивании:

```python
scores[fp] += float(sc) * GLOBAL_WEIGHT
```

при:

```python
GLOBAL_WEIGHT = 10.0
```

3. Только для **пограничных случаев**:

```python
if margin < MARGIN_LIMIT:
```

где:

```python
MARGIN_LIMIT = 0.02
```

запускалась дополнительная проверка **sub-fingerprint**.

Причём не всех адресов, а только:

```text
TOP-1
TOP-2
```

И уже там вычислялся `max(sim)` по sub-слепкам.

4. Дополнительно использовалась **последовательность фотографий**:

```text
фото N-1 → TOP1
фото N   → ?
фото N+1 → TOP1
```

Если:

```text
N-1 == N+1
```

то этот адрес получал дополнительный вес:

```python
scores[left_fp] += 3.0
```

5. После этого принималось **финальное решение**, причём v33 TOP-1 являлся исходным решением:

```python
best = old
```

и изменение происходило только при достаточном преимуществе:

```python
candidate != old and gain > 1.5
```

То есть логика была:

```text
DINO TOP-1
   │
   ├── уверенный → оставить
   │
   └── margin маленький
          │
          ├── sub-fingerprint
          ├── TOP-1/TOP-2
          └── согласие соседних кадров
                    │
                    ▼
              hybrid decision
```

### И ещё один важный момент

У тебя существуют **две разные вещи**, которые сейчас легко смешать:

**1. Создание базы fingerprints**

```text
исходные фотографии адреса
        ↓
DINO
        ↓
78_v33 / 79_v33 / ... / 95_v33
```

Это подготовительный этап.

**2. Распознавание рабочей папки**

```text
новые фотографии
        ↓
DINO/v33
        ↓
TOP-5
        ↓
анализ margin
        ↓
при необходимости sub-fingerprint
        ↓
sequence consensus
        ↓
final decision
        ↓
адрес
```

И именно **вторая схема** является алгоритмом сортировки.

---

Причём твой `sort_test_and_report_v2.py`, который ты показал, действительно **уже не содержит hybrid-логику**. Он делает только:

```python
data, recognition_time = run_recognition()
```

а затем:

```python
assigned_id = item.get("best_id")
```

То есть он **берёт результат готового `recognize` и раскладывает фотографии**.

Поэтому его нельзя считать самим алгоритмом распознавания. Это именно **SORT/EXPORT слой**.

А `benchmark_hybrid_v12_full.py` — один из последних экспериментальных слоёв принятия решения, работающий поверх результатов benchmark.

И я бы сейчас **не менял ни алгоритм, ни код**. Сначала надо восстановить точную финальную архитектуру из уже существующих скриптов `v35 → v39 → hybrid v12`, потому что у тебя там было несколько последовательных улучшений, и важно не принять промежуточную версию за финальную.

---

### 👤 **User** — 2026-08-16 21:55:44

надо иметь это ввиду

---

### 🤖 **Assistant** — 2026-08-16 21:55:44

Да, обязательно. **Зафиксировал это как принцип архитектуры проекта.**

Дальше считаем:

```text
FINGERPRINT CREATION
отдельный независимый этап
```

и не смешиваем его с рабочим распознаванием.

А рабочий pipeline рассматриваем как:

```text
ФОТОГРАФИИ
    ↓
DINO / v33
    ↓
TOP-K кандидаты
    ↓
анализ уверенности / margin
    ↓
если пограничный случай:
    ├─ sub-fingerprint
    └─ sequence / соседние кадры
    ↓
HYBRID FINAL DECISION
    ↓
ПРИСВОЕНИЕ АДРЕСА
    ↓
СОРТИРОВКА ФОТО
```

При этом `sort_test_and_report_v2.py` — **не распознаватель**, а слой, который получает результат распознавания и физически раскладывает фотографии + пишет отчёты.

И ещё важнее: **v33 TOP-1 — базовое решение, а дополнительные механизмы должны вмешиваться только там, где для этого есть основания.** Это сохраняем как принцип, пока специально не решим его изменить.

---

### 👤 **User** — 2026-08-16 21:56:30

распознаватель - важная часть - надо его включить в пайплйн после dino И перед qwen

---

### 🤖 **Assistant** — 2026-08-16 21:56:31

Да. Именно так. **Распознаватель — самостоятельный обязательный блок между DINO и Qwen.**

Фиксируем архитектуру:

```text
                    ┌──────────────────────┐
                    │  ПАПКА ФОТОГРАФИЙ    │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │      DINO / v33      │
                    │  получение TOP-K      │
                    │  + scores + margin    │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │    РАСПОЗНАВАТЕЛЬ    │
                    │                      │
                    │ • v33 TOP-1          │
                    │ • TOP-5              │
                    │ • margin             │
                    │ • sub-fingerprint    │
                    │ • sequence consensus │
                    │ • hybrid decision     │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │   ПРИСВОЕНИЕ АДРЕСА  │
                    │   / сортировка фото  │
                    └──────────┬───────────┘
                               ↓
                    ┌──────────────────────┐
                    │       QWEN 3 VL      │
                    │                      │
                    │ • анализ фотографии  │
                    │ • баннеры            │
                    │ • OCR                │
                    │ • дополнительные     │
                    │   признаки           │
                    └──────────────────────┘
```

И **создание fingerprints здесь вообще не находится**:

```text
                 ОТДЕЛЬНАЯ ПОДГОТОВКА БАЗЫ

фотографии адресов
        ↓
DINO
        ↓
fingerprints / v33 / sub-fingerprints
        ↓
       БАЗА
          │
          │
          └──────────────┐
                         ↓
НОВАЯ ПАПКА → DINO → РАСПОЗНАВАТЕЛЬ → АДРЕС → QWEN
```

### Ключевой момент

Я бы даже не называл весь блок после DINO просто `first candidate`.

У нас есть два разных понятия:

**DINO:**

> «Вот мои кандидаты и их сходство».

**Распознаватель:**

> «Учитывая кандидатов DINO, margin, sub-fingerprints и последовательность кадров — вот мой окончательный адрес».

И только **после окончательного адреса** фотография передаётся Qwen.

Это важно и для будущего web-интерфейса: кнопку/модуль **«Распознать»** нельзя сводить к прямому вызову DINO. Внутри неё должен находиться весь зафиксированный механизм принятия решения.

Именно эту архитектуру будем считать базовой дальше.

---

### 👤 **User** — 2026-08-16 21:57:07

ок

---

### 🤖 **Assistant** — 2026-08-16 21:57:08

> **Remembering**
>
>
> **Continued scene fingerprint pipeline with hybrid sequence recognition logic**
>
> 
>
> Worked for 8s

Да. **Фиксируем именно так.**

И важное уточнение: **создание Fingerprint - отдельный технический процесс**, а не шаг обработки каждой входящей фотографии.

### Рабочий runtime-пайплайн

```text
ПАПКА С ФОТОГРАФИЯМИ
        │
        ▼
     DINO / v33
        │
        ▼
   TOP-N кандидатов
        │
        ▼
   РАСПОЗНАВАТЕЛЬ
   ├─ subfingerprint
   ├─ уточнение кандидата
   ├─ sequence / соседние кадры
   └─ hybrid-логика
        │
        ▼
   ФИНАЛЬНЫЙ АДРЕС
        │
        ▼
   сортировка / копирование
        │
        ▼
      QWEN
        │
        ▼
  дальнейший анализ фото
```

То есть **нельзя сейчас упрощать схему до**:

```text
DINO → первый кандидат → адрес → Qwen
```

Правильнее:

```text
DINO/v33 → первичный TOP-N → РАСПОЗНАВАТЕЛЬ → финальный адрес → Qwen
```

Причём из найденного кода видно, что распознаватель уже содержит именно ту логику, которую мы нарабатывали: **global TOP-N → subfingerprint для пограничных случаев → sequence consensus → принятие финального кандидата только при достаточном преимуществе**.

Именно этот слой теперь нужно **встроить в основной веб-пайплайн**, а не создавать новую упрощённую логику.

---

### 👤 **User** — 2026-08-16 21:57:41

да. кнопка расознать должна запускать ереду последовательных криптов

---

### 🤖 **Assistant** — 2026-08-16 21:57:41

Да. **Кнопка «Распознать» должна быть оркестратором последовательного пайплайна**, а не просто вызовом `scene-fingerprint recognize`.

Фиксируем архитектуру:

```text
[ РАСПОЗНАТЬ ]
       │
       ▼
1. Проверка входной папки
       │
       ▼
2. DINO / v33
   первичное распознавание
   TOP-N кандидатов
       │
       ▼
3. РАСПОЗНАВАТЕЛЬ
   ├── subfingerprint
   ├── rerank
   ├── sequence / соседние кадры
   └── hybrid decision
       │
       ▼
4. ФИНАЛЬНОЕ ПРИСВОЕНИЕ АДРЕСА
       │
       ▼
5. Сортировка фотографий
   по адресным папкам
       │
       ▼
6. Qwen3-VL 4B
   анализ уже распределённых фотографий
       │
       ▼
7. Отчёт / статус / результат в WEB UI
```

### При этом разделяем два разных процесса

**Создание базы:**

```text
исходные фотографии адреса
        ↓
создание Fingerprint v33
        ↓
data/fingerprints/...
```

Это отдельная операция.

**Рабочее распознавание:**

```text
data/input/...
      ↓
DINO/v33
      ↓
Recognizer
      ↓
финальный адрес
      ↓
сортировка
      ↓
Qwen
```

И это важно архитектурно: **кнопка «Распознать» не должна сама заниматься созданием fingerprint.**

Следующий шаг я бы сделал не с изменением алгоритма, а с **поиском текущего обработчика кнопки «Распознать» и всех его вызовов**, чтобы аккуратно заменить нынешний короткий путь на этот последовательный pipeline, не сломав уже готовую веб-часть.

---

### 👤 **User** — 2026-08-16 21:58:08

да

---

### 🤖 **Assistant** — 2026-08-16 21:58:09

Да. Я посмотрел найденные материалы и **не буду сейчас менять код наугад**.

У нас уже есть подтверждение, что старый `SceneRecognizer` - это не просто `DINO → best_id`: он использует несколько компонент - `global`, `environment`, `color`, `spatial`, а решение учитывает score и margin. `Pasted text.txt`

Но поверх него мы уже разработали отдельный **hybrid-рерайт**, который работает после первичного TOP-N:

```text
DINO / v33
    │
    ├── TOP 1
    ├── TOP 2
    ├── TOP 3
    ├── TOP 4
    └── TOP 5
          │
          ▼
     РАСПОЗНАВАТЕЛЬ
          │
          ├── global TOP-N
          ├── subfingerprint
          ├── sequence consensus
          └── hybrid decision
          │
          ▼
      FINAL ADDRESS
          │
          ▼
       SORTING
          │
          ▼
         QWEN
```

Причём `subfingerprint` запускается **не для всех фотографий**, а для пограничных случаев по margin - именно так сделано в `benchmark_hybrid_v12_full.py`.

### Поэтому следующий шаг

Нам надо найти **реальный backend-обработчик веб-кнопки «Распознать»**, а не CLI.

И проверить цепочку:

```text
button
  ↓
web/API handler
  ↓
текущий recognize
  ↓
sorting
  ↓
Qwen
```

После этого вставим туда:

```text
DINO/v33
   ↓
hybrid recognizer
   ↓
final address
   ↓
sorting
   ↓
Qwen
```

**При этом сам алгоритм v33 и уже протестированный recognizer не трогаем.** Меняем именно orchestration веб-пайплайна.

И отдельно: в найденном старом CLI `recognize` действительно есть самостоятельная команда распознавания, а `create` отделён от неё как отдельная операция создания fingerprint. `Pasted text(1).txt` Это полностью соответствует тому, что мы сейчас зафиксировали.

Если работа идёт прямо в проекте на `NEURO`, дай следующим сообщением вывод:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -R -n -E \
'Распознать|Распозна|recognize|recognition|sort_test_and_report|qwen|Qwen' \
app \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -300
```

По нему уже точно найдём **точку входа кнопки** и начнём встраивать последовательный pipeline.

---

