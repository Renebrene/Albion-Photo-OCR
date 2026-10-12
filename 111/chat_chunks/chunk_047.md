## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 👤 **User** — 2026-08-15 15:24:49

int_mvp_v02

uv run python - <<'PY'
import csv

p = "output/neighbor_v37/neighbor_decision.csv"

with open(p, encoding="utf-8") as f:
    r = csv.DictReader(f)
    print(r.fieldnames)
PY
['index', 'image', 'v33', 'second', 'final', 'margin', 'reason', 'forward_support', 'backward_support', 'forward_neighbors', 'backward_neighbors']
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -RniE '\bbest\b|best_candidate|best_score|BEST' \
    app scripts \
    --exclude='*.pyc' \
    2>/dev/null | head -300
app/core/scene_analyzer.py.bak_before_create_opt:389:        best_index = int(
app/core/scene_analyzer.py.bak_before_create_opt:393:        best_image_score = float(
app/core/scene_analyzer.py.bak_before_create_opt:394:            image_scores[best_index]
app/core/scene_analyzer.py.bak_before_create_opt:405:        if best_index < len(image_names):
app/core/scene_analyzer.py.bak_before_create_opt:406:            best_image = image_names[
app/core/scene_analyzer.py.bak_before_create_opt:407:                best_index
app/core/scene_analyzer.py.bak_before_create_opt:410:            best_image = str(
app/core/scene_analyzer.py.bak_before_create_opt:411:                best_index
app/core/scene_analyzer.py.bak_before_create_opt:456:            "best_image_score": float(
app/core/scene_analyzer.py.bak_before_create_opt:457:                best_image_score
app/core/scene_analyzer.py.bak_before_create_opt:472:            "best_image": best_image,
app/core/recognizer.py.before_restore_old_matching_20260815_025751:30:        margin to second-best candidate
app/core/recognizer.py.before_restore_old_matching_20260815_025751:358:                        "best_image": score.get(
app/core/recognizer.py.before_restore_old_matching_20260815_025751:359:                            "best_image"
app/core/recognizer.py.before_restore_old_matching_20260815_025751:362:                        "best_image_score": float(
app/core/recognizer.py.before_restore_old_matching_20260815_025751:364:                                "best_image_score",
app/core/recognizer.py.before_restore_old_matching_20260815_025751:389:                        "best_id": None,
app/core/recognizer.py.before_restore_old_matching_20260815_025751:401:            best = ranked[0]
app/core/recognizer.py.before_restore_old_matching_20260815_025751:403:            best_score = float(
app/core/recognizer.py.before_restore_old_matching_20260815_025751:404:                best["score"]
app/core/recognizer.py.before_restore_old_matching_20260815_025751:415:                best_score
app/core/recognizer.py.before_restore_old_matching_20260815_025751:421:                    best_score,
app/core/recognizer.py.before_restore_old_matching_20260815_025751:432:            # Always use the best available candidate.
app/core/recognizer.py.before_restore_old_matching_20260815_025751:435:            # Even a weak candidate is accepted as the best
app/core/recognizer.py.before_restore_old_matching_20260815_025751:438:            best_id = best["id"]
app/core/recognizer.py.before_restore_old_matching_20260815_025751:440:            if best_score < threshold:
app/core/recognizer.py.before_restore_old_matching_20260815_025751:451:                    "best_id": best_id,
app/core/recognizer.py.before_restore_old_matching_20260815_025751:453:                    "score": best_score,
app/core/recognizer.py.before_restore_old_matching_20260815_025751:467:                    "best_image": best.get(
app/core/recognizer.py.before_restore_old_matching_20260815_025751:468:                        "best_image"
app/core/recognizer.py.before_restore_old_matching_20260815_025751:471:                    "best_image_score": float(
app/core/recognizer.py.before_restore_old_matching_20260815_025751:472:                        best.get(
app/core/recognizer.py.before_restore_old_matching_20260815_025751:473:                            "best_image_score",
app/core/recognizer.py.before_restore_old_matching_20260815_025724:30:        margin to second-best candidate
app/core/recognizer.py.before_restore_old_matching_20260815_025724:358:                        "best_image": score.get(
app/core/recognizer.py.before_restore_old_matching_20260815_025724:359:                            "best_image"
app/core/recognizer.py.before_restore_old_matching_20260815_025724:362:                        "best_image_score": float(
app/core/recognizer.py.before_restore_old_matching_20260815_025724:364:                                "best_image_score",
app/core/recognizer.py.before_restore_old_matching_20260815_025724:389:                        "best_id": None,
app/core/recognizer.py.before_restore_old_matching_20260815_025724:401:            best = ranked[0]
app/core/recognizer.py.before_restore_old_matching_20260815_025724:403:            best_score = float(
app/core/recognizer.py.before_restore_old_matching_20260815_025724:404:                best["score"]
app/core/recognizer.py.before_restore_old_matching_20260815_025724:415:                best_score
app/core/recognizer.py.before_restore_old_matching_20260815_025724:421:                    best_score,
app/core/recognizer.py.before_restore_old_matching_20260815_025724:432:            # Always use the best available candidate.
app/core/recognizer.py.before_restore_old_matching_20260815_025724:435:            # Even a weak candidate is accepted as the best
app/core/recognizer.py.before_restore_old_matching_20260815_025724:438:            best_id = best["id"]
app/core/recognizer.py.before_restore_old_matching_20260815_025724:440:            if best_score < threshold:
app/core/recognizer.py.before_restore_old_matching_20260815_025724:451:                    "best_id": best_id,
app/core/recognizer.py.before_restore_old_matching_20260815_025724:453:                    "score": best_score,
app/core/recognizer.py.before_restore_old_matching_20260815_025724:467:                    "best_image": best.get(
app/core/recognizer.py.before_restore_old_matching_20260815_025724:468:                        "best_image"
app/core/recognizer.py.before_restore_old_matching_20260815_025724:471:                    "best_image_score": float(
app/core/recognizer.py.before_restore_old_matching_20260815_025724:472:                        best.get(
app/core/recognizer.py.before_restore_old_matching_20260815_025724:473:                            "best_image_score",
app/core/scene_analyzer.py:413:        best_index = int(
app/core/scene_analyzer.py:417:        best_image_score = float(
app/core/scene_analyzer.py:418:            image_scores[best_index]
app/core/scene_analyzer.py:429:        if best_index < len(image_names):
app/core/scene_analyzer.py:430:            best_image = image_names[
app/core/scene_analyzer.py:431:                best_index
app/core/scene_analyzer.py:434:            best_image = str(
app/core/scene_analyzer.py:435:                best_index
app/core/scene_analyzer.py:506:            "best_image_score": float(
app/core/scene_analyzer.py:507:                best_image_score
app/core/scene_analyzer.py:528:            "best_image": best_image,
app/core/recognizer.py:30:        margin to second-best candidate
app/core/recognizer.py:358:                        "best_image": score.get(
app/core/recognizer.py:359:                            "best_image"
app/core/recognizer.py:362:                        "best_image_score": float(
app/core/recognizer.py:364:                                "best_image_score",
app/core/recognizer.py:389:                        "best_id": None,
app/core/recognizer.py:401:            best = ranked[0]
app/core/recognizer.py:403:            best_score = float(
app/core/recognizer.py:404:                best["score"]
app/core/recognizer.py:415:                best_score
app/core/recognizer.py:421:                    best_score,
app/core/recognizer.py:432:            # Always use the best available candidate.
app/core/recognizer.py:435:            # Even a weak candidate is accepted as the best
app/core/recognizer.py:438:            if best_score < threshold:
app/core/recognizer.py:439:                best_id = None
app/core/recognizer.py:442:                best_id = best["id"]
app/core/recognizer.py:451:                    "best_id": best_id,
app/core/recognizer.py:453:                    "score": best_score,
app/core/recognizer.py:467:                    "best_image": best.get(
app/core/recognizer.py:468:                        "best_image"
app/core/recognizer.py:471:                    "best_image_score": float(
app/core/recognizer.py:472:                        best.get(
app/core/recognizer.py:473:                            "best_image_score",
app/core/scene_analyzer.py.backup_before_optimization:360:        best_index = int(
app/core/scene_analyzer.py.backup_before_optimization:364:        best_image_score = float(
app/core/scene_analyzer.py.backup_before_optimization:365:            image_scores[best_index]
app/core/scene_analyzer.py.backup_before_optimization:376:        if best_index < len(image_names):
app/core/scene_analyzer.py.backup_before_optimization:377:            best_image = image_names[
app/core/scene_analyzer.py.backup_before_optimization:378:                best_index
app/core/scene_analyzer.py.backup_before_optimization:381:            best_image = str(
app/core/scene_analyzer.py.backup_before_optimization:382:                best_index
app/core/scene_analyzer.py.backup_before_optimization:445:            "best_image_score": float(
app/core/scene_analyzer.py.backup_before_optimization:446:                best_image_score
app/core/scene_analyzer.py.backup_before_optimization:461:            "best_image": best_image,
app/core/scene_analyzer.py.v33_working:413:        best_index = int(
app/core/scene_analyzer.py.v33_working:417:        best_image_score = float(
app/core/scene_analyzer.py.v33_working:418:            image_scores[best_index]
app/core/scene_analyzer.py.v33_working:429:        if best_index < len(image_names):
app/core/scene_analyzer.py.v33_working:430:            best_image = image_names[
app/core/scene_analyzer.py.v33_working:431:                best_index
app/core/scene_analyzer.py.v33_working:434:            best_image = str(
app/core/scene_analyzer.py.v33_working:435:                best_index
app/core/scene_analyzer.py.v33_working:506:            "best_image_score": float(
app/core/scene_analyzer.py.v33_working:507:                best_image_score
app/core/scene_analyzer.py.v33_working:528:            "best_image": best_image,
app/core/recognizer.py.backup_before_optimization:26:        margin to second-best candidate
app/core/recognizer.py.backup_before_optimization:269:                        "best_image": score.get(
app/core/recognizer.py.backup_before_optimization:270:                            "best_image"
app/core/recognizer.py.backup_before_optimization:273:                        "best_image_score": float(
app/core/recognizer.py.backup_before_optimization:275:                                "best_image_score",
app/core/recognizer.py.backup_before_optimization:300:                        "best_id": None,
app/core/recognizer.py.backup_before_optimization:312:            best = ranked[0]
app/core/recognizer.py.backup_before_optimization:314:            best_score = float(
app/core/recognizer.py.backup_before_optimization:315:                best["score"]
app/core/recognizer.py.backup_before_optimization:326:                best_score
app/core/recognizer.py.backup_before_optimization:332:                    best_score,
app/core/recognizer.py.backup_before_optimization:343:            # Always use the best available candidate.
app/core/recognizer.py.backup_before_optimization:346:            # Even a weak candidate is accepted as the best
app/core/recognizer.py.backup_before_optimization:349:            best_id = best["id"]
app/core/recognizer.py.backup_before_optimization:351:            if best_score < threshold:
app/core/recognizer.py.backup_before_optimization:362:                    "best_id": best_id,
app/core/recognizer.py.backup_before_optimization:364:                    "score": best_score,
app/core/recognizer.py.backup_before_optimization:378:                    "best_image": best.get(
app/core/recognizer.py.backup_before_optimization:379:                        "best_image"
app/core/recognizer.py.backup_before_optimization:382:                    "best_image_score": float(
app/core/recognizer.py.backup_before_optimization:383:                        best.get(
app/core/recognizer.py.backup_before_optimization:384:                            "best_image_score",
app/core/recognizer.py.before_patchfix:212:                best = candidates[0]
app/core/recognizer.py.before_patchfix:213:                best_id = best["id"]
app/core/recognizer.py.before_patchfix:214:                best_score = best["score"]
app/core/recognizer.py.before_patchfix:216:                best_id = None
app/core/recognizer.py.before_patchfix:217:                best_score = 0.0
app/core/recognizer.py.before_patchfix:221:                "best_id": best_id,
app/core/recognizer.py.before_patchfix:222:                "score": float(best_score),
app/core/recognizer.py.before_patchfix:266:            # Find best reference image using global embeddings.
app/core/recognizer.py.before_patchfix:277:            best_idx = int(
app/core/recognizer.py.before_patchfix:288:            if best_idx < len(image_names):
app/core/recognizer.py.before_patchfix:289:                best_image = image_names[best_idx]
app/core/recognizer.py.before_patchfix:291:                best_image = str(best_idx)
app/core/recognizer.py.before_patchfix:296:                "best_image_score": float(
app/core/recognizer.py.before_patchfix:297:                    image_scores[best_idx]
app/core/recognizer.py.before_patchfix:302:                "best_match": best_image,
app/core/recognizer.py.backup_before_force_match:26:        margin to second-best candidate
app/core/recognizer.py.backup_before_force_match:269:                        "best_image": score.get(
app/core/recognizer.py.backup_before_force_match:270:                            "best_image"
app/core/recognizer.py.backup_before_force_match:273:                        "best_image_score": float(
app/core/recognizer.py.backup_before_force_match:275:                                "best_image_score",
app/core/recognizer.py.backup_before_force_match:300:                        "best_id": None,
app/core/recognizer.py.backup_before_force_match:312:            best = ranked[0]
app/core/recognizer.py.backup_before_force_match:314:            best_score = float(
app/core/recognizer.py.backup_before_force_match:315:                best["score"]
app/core/recognizer.py.backup_before_force_match:326:                best_score
app/core/recognizer.py.backup_before_force_match:332:                    best_score,
app/core/recognizer.py.backup_before_force_match:344:            if best_score < threshold:
app/core/recognizer.py.backup_before_force_match:345:                best_id = None
app/core/recognizer.py.backup_before_force_match:348:                best_id = best["id"]
app/core/recognizer.py.backup_before_force_match:354:                    "best_id": best_id,
app/core/recognizer.py.backup_before_force_match:356:                    "score": best_score,
app/core/recognizer.py.backup_before_force_match:370:                    "best_image": best.get(
app/core/recognizer.py.backup_before_force_match:371:                        "best_image"
app/core/recognizer.py.backup_before_force_match:374:                    "best_image_score": float(
app/core/recognizer.py.backup_before_force_match:375:                        best.get(
app/core/recognizer.py.backup_before_force_match:376:                            "best_image_score",
app/core/recognizer.py.v33_working:30:        margin to second-best candidate
app/core/recognizer.py.v33_working:358:                        "best_image": score.get(
app/core/recognizer.py.v33_working:359:                            "best_image"
app/core/recognizer.py.v33_working:362:                        "best_image_score": float(
app/core/recognizer.py.v33_working:364:                                "best_image_score",
app/core/recognizer.py.v33_working:389:                        "best_id": None,
app/core/recognizer.py.v33_working:401:            best = ranked[0]
app/core/recognizer.py.v33_working:403:            best_score = float(
app/core/recognizer.py.v33_working:404:                best["score"]
app/core/recognizer.py.v33_working:415:                best_score
app/core/recognizer.py.v33_working:421:                    best_score,
app/core/recognizer.py.v33_working:432:            # Always use the best available candidate.
app/core/recognizer.py.v33_working:435:            # Even a weak candidate is accepted as the best
app/core/recognizer.py.v33_working:438:            if best_score < threshold:
app/core/recognizer.py.v33_working:439:                best_id = None
app/core/recognizer.py.v33_working:442:                best_id = best["id"]
app/core/recognizer.py.v33_working:451:                    "best_id": best_id,
app/core/recognizer.py.v33_working:453:                    "score": best_score,
app/core/recognizer.py.v33_working:467:                    "best_image": best.get(
app/core/recognizer.py.v33_working:468:                        "best_image"
app/core/recognizer.py.v33_working:471:                    "best_image_score": float(
app/core/recognizer.py.v33_working:472:                        best.get(
app/core/recognizer.py.v33_working:473:                            "best_image_score",
app/core/recognizer.py.before_restore_old_matching_20260815_025737:30:        margin to second-best candidate
app/core/recognizer.py.before_restore_old_matching_20260815_025737:358:                        "best_image": score.get(
app/core/recognizer.py.before_restore_old_matching_20260815_025737:359:                            "best_image"
app/core/recognizer.py.before_restore_old_matching_20260815_025737:362:                        "best_image_score": float(
app/core/recognizer.py.before_restore_old_matching_20260815_025737:364:                                "best_image_score",
app/core/recognizer.py.before_restore_old_matching_20260815_025737:389:                        "best_id": None,
app/core/recognizer.py.before_restore_old_matching_20260815_025737:401:            best = ranked[0]
app/core/recognizer.py.before_restore_old_matching_20260815_025737:403:            best_score = float(
app/core/recognizer.py.before_restore_old_matching_20260815_025737:404:                best["score"]
app/core/recognizer.py.before_restore_old_matching_20260815_025737:415:                best_score
app/core/recognizer.py.before_restore_old_matching_20260815_025737:421:                    best_score,
app/core/recognizer.py.before_restore_old_matching_20260815_025737:432:            # Always use the best available candidate.
app/core/recognizer.py.before_restore_old_matching_20260815_025737:435:            # Even a weak candidate is accepted as the best
app/core/recognizer.py.before_restore_old_matching_20260815_025737:438:            best_id = best["id"]
app/core/recognizer.py.before_restore_old_matching_20260815_025737:440:            if best_score < threshold:
app/core/recognizer.py.before_restore_old_matching_20260815_025737:451:                    "best_id": best_id,
app/core/recognizer.py.before_restore_old_matching_20260815_025737:453:                    "score": best_score,
app/core/recognizer.py.before_restore_old_matching_20260815_025737:467:                    "best_image": best.get(
app/core/recognizer.py.before_restore_old_matching_20260815_025737:468:                        "best_image"
app/core/recognizer.py.before_restore_old_matching_20260815_025737:471:                    "best_image_score": float(
app/core/recognizer.py.before_restore_old_matching_20260815_025737:472:                        best.get(
app/core/recognizer.py.before_restore_old_matching_20260815_025737:473:                            "best_image_score",
app/main.py:55:                                f"{row['best_id'] or 'UNKNOWN'} "
app/cli.py:190:        f"BEST IMAGE    "
app/cli.py:191:        f"{result['best_image_score']:.4f}"
app/cli.py:220:        f"BEST MATCH    "
app/cli.py:221:        f"{result['best_image']}"
app/cli.py:238:    best_id = result.get(
app/cli.py:239:        "best_id"
app/cli.py:275:        f"{best_id or 'NONE'}"
app/cli.py:303:    best_image = result.get(
app/cli.py:304:        "best_image"
app/cli.py:307:    if best_image:
app/cli.py:309:            f"BEST IMAGE   "
app/cli.py:310:            f"{best_image}"
scripts/sort_test_and_report_v2.py:164:        # ВСЕГДА используем best_id = первый кандидат.
scripts/sort_test_and_report_v2.py:165:        assigned_id = item.get("best_id")
scripts/sort_test_and_report_v2.py:190:            "best_image": item.get("best_image"),
scripts/sort_test_and_report_v2.py:191:            "best_image_score": item.get("best_image_score"),
scripts/sort_test_and_report_v2.py:240:        "best_image",
scripts/sort_test_and_report_v2.py:241:        "best_image_score",
scripts/benchmark_test_v1.py:216:            "best_image": x.get("best_image"),
scripts/sort_test_and_report.py:108:        best_id = item["best_id"]
scripts/sort_test_and_report.py:111:        if best_id.endswith("_v33"):
scripts/sort_test_and_report.py:112:            address = best_id[:-4]
scripts/sort_test_and_report.py:114:            address = best_id
scripts/sort_test_and_report.py:152:            "fingerprint": best_id,
scripts/sort_test_and_report.py:161:            "best_image": item.get("best_image", ""),
scripts/sort_test_and_report.py:162:            "best_image_score": float(
scripts/sort_test_and_report.py:163:                item.get("best_image_score", 0)
scripts/sort_test_and_report.py:203:        "best_image",
scripts/sort_test_and_report.py:204:        "best_image_score",
scripts/sort_margin005_best.py:13:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_margin005_best.py:52:    print("MARGIN < 0.005 + BEST VISUAL TEST")
scripts/sort_margin005_best.py:100:        best_diff = float(row["best_diff"])
scripts/sort_margin005_best.py:113:            if best_diff > 0:
scripts/sort_margin005_best.py:116:                reason = "BEST"
scripts/sort_margin005_best.py:120:                reason = "FIRST_BEST_LOSES"
scripts/sort_margin005_best.py:159:                "best_diff": best_diff,
scripts/sort_margin005_best.py:182:            "best_diff",
scripts/sort_margin005_best.py:207:        f"Changed by BEST:     {len(changed)}"
scripts/sort_margin005_best.py:227:            f'  best_diff={x["best_diff"]:+.6f}'
scripts/sort_neighbor_v34.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_baseline.py:47:        best_id = item["best_id"]
scripts/sort_baseline.py:48:        folder = best_id.replace("_v33", "")
scripts/sort_baseline.py:52:            folder = best_id
scripts/sort_baseline.py:74:        counts[best_id] += 1
scripts/sort_baseline.py:79:            "assigned_id": best_id,
scripts/sort_baseline.py:90:            "best_image": item.get("best_image"),
scripts/sort_baseline.py:91:            "best_image_score": item.get("best_image_score"),
scripts/sort_neighbor_v35.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:24:51

Да. По этому выводу уже видно важное: **`best` у нас существует и уже рассчитывается на уровне распознавания**, поэтому LLM пока действительно не нужен как первый механизм разрешения выбросов.

Причём есть два разных `best`:

1. **`best_id`** — первый кандидат для фотографии.
2. **`best_image` / `best_image_score`** — лучшая конкретная эталонная фотография внутри выбранного fingerprint.
3. В `sort_margin005_best.py` уже есть отдельная логика **`BEST VISUAL TEST`**, которая сравнивает `best_diff`.

Нам сейчас нужно понять именно **как рассчитывается `best_diff` и что он показывает для спорного кадра**.

Давай сначала **ничего не меняем**, а посмотрим эту существующую логику и данные. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "================================================================================"
echo "=== sort_margin005_best.py ==="
echo "================================================================================"
sed -n '1,260p' scripts/sort_margin005_best.py

echo
echo "================================================================================"
echo "=== sort_neighbor_v34.py ==="
echo "================================================================================"
sed -n '1,260p' scripts/sort_neighbor_v34.py

echo
echo "================================================================================"
echo "=== recognizer.py: BEST LOGIC ==="
echo "================================================================================"
sed -n '330,490p' app/core/recognizer.py

echo
echo "================================================================================"
echo "=== margin_best.csv HEADER + FIRST ROWS ==="
echo "================================================================================"
head -10 output/benchmark_components/full_analysis/margin_best.csv 2>/dev/null || true
```

Особенно интересует вот эта цепочка:

**DINO TOP1/TOP2 → margin → подозрительный кадр → `best_image_score` / `best_diff` → решение.**

И тогда можно построить гораздо более правильную схему:

```text
обычный кадр
    │
    ├── DINO уверенно определил → сразу принимаем TOP1
    │
    └── DINO не уверен
            │
            ├── BEST явно подтверждает TOP1 → принимаем TOP1
            │
            ├── BEST явно подтверждает TOP2 → меняем на TOP2
            │
            └── BEST тоже не уверен
                    │
                    └── только здесь смотрим последовательность
                              │
                              ├── стабильный соседний адрес
                              └── одиночный выброс
```

И это как раз соответствует твоей идее про **единичные фотографии другого адреса**: если отдельный кадр действительно имеет высокий `best_score` на другой fingerprint, **не надо насильно тянуть его к соседней серии**.

То есть LLM я бы пока вообще отложил. Сначала посмотрим, **насколько `BEST` уже способен самостоятельно решать те случаи, для которых мы сейчас вызываем Qwen**.

---

### 👤 **User** — 2026-08-15 15:25:35

echo "================================================================================"
echo "=== sort_margin005_best.py ==="
echo "================================================================================"
sed -n '1,260p' scripts/sort_margin005_best.py

echo
echo "================================================================================"
echo "=== sort_neighbor_v34.py ==="
echo "================================================================================"
sed -n '1,260p' scripts/sort_neighbor_v34.py

echo
echo "================================================================================"
echo "=== recognizer.py: BEST LOGIC ==="
echo "================================================================================"
| true10 output/benchmark_components/full_analysis/margin_best.csv 2>/dev/null |
================================================================================
=== sort_margin005_best.py ===
================================================================================
#!/usr/bin/env python3

import csv
import shutil
from pathlib import Path
from collections import Counter

PROJECT = Path(__file__).resolve().parent.parent

INPUT_CSV = (
    PROJECT
    / "output/benchmark_components/full_analysis/margin_best.csv"
)

SOURCE_DIR = PROJECT / "data/input/test"

OUTPUT_DIR = PROJECT / "output/visual_check_margin005"

CHANGED_DIR = OUTPUT_DIR / "_CHANGED"

MARGIN_THRESHOLD = 0.005

def safe_copy(src, dst_dir):
    dst_dir.mkdir(parents=True, exist_ok=True)

    dst = dst_dir / src.name

    if not dst.exists():
        shutil.copy2(src, dst)
        return dst

    stem = src.stem
    suffix = src.suffix

    n = 2

    while True:
        candidate = dst_dir / f"{stem}__{n}{suffix}"

        if not candidate.exists():
            shutil.copy2(src, candidate)
            return candidate

        n += 1

def main():

    print("=" * 80)
    print("MARGIN < 0.005 + BEST VISUAL TEST")
    print("=" * 80)

    print("CSV   :", INPUT_CSV)
    print("SOURCE:", SOURCE_DIR)
    print("OUTPUT:", OUTPUT_DIR)
    print()

    if not INPUT_CSV.exists():
        raise FileNotFoundError(INPUT_CSV)

    if not SOURCE_DIR.exists():
        raise FileNotFoundError(SOURCE_DIR)

    # Clean only our test output.
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True)

    rows = []

    with INPUT_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

    print(f"CSV rows: {len(rows)}")
    print()

    counters = Counter()
    changed = []
    low_margin = []

    for row in rows:

        image = row["image"]

        current_first = row["current_first"]
        current_second = row["current_second"]

        final_margin = float(row["final_margin"])
        best_diff = float(row["best_diff"])

        # --------------------------------------------------
        # DECISION
        # --------------------------------------------------

        assigned = current_first
        reason = "FIRST"

        if final_margin < MARGIN_THRESHOLD:

            low_margin.append(row)

            if best_diff > 0:

                assigned = current_second
                reason = "BEST"

            else:

                reason = "FIRST_BEST_LOSES"

        # --------------------------------------------------
        # SOURCE
        # --------------------------------------------------

        src = SOURCE_DIR / image

        if not src.exists():

            print(
                f"[WARNING] source not found: {src}"
            )

            continue

        # --------------------------------------------------
        # DESTINATION
        # --------------------------------------------------

        folder = assigned.replace("_v33", "")

        dst_dir = OUTPUT_DIR / folder

        safe_copy(src, dst_dir)

        counters[folder] += 1

        # --------------------------------------------------
        # CHANGED
        # --------------------------------------------------

        if assigned != current_first:

            changed.append({
                "image": image,
                "old": current_first,
                "new": assigned,
                "margin": final_margin,
                "best_diff": best_diff,
            })

            # Put an additional copy into _CHANGED.
            safe_copy(src, CHANGED_DIR)

    # ------------------------------------------------------
    # REPORT
    # ------------------------------------------------------

    report = OUTPUT_DIR / "decision_report.csv"

    with report.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        fields = [
            "image",
            "old",
            "new",
            "margin",
            "best_diff",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()

        writer.writerows(changed)

    print("=" * 80)
    print("RESULT")
    print("=" * 80)

    print(
        f"Total images:        {len(rows)}"
    )

    print(
        f"Margin < 0.005:      {len(low_margin)}"
    )

    print(
        f"Changed by BEST:     {len(changed)}"
    )

    print()

    print("CHANGED:")
    print("-" * 80)

    for x in changed:

        print(
            f'{x["image"]}'
        )

        print(
            f'    {x["old"]} -> {x["new"]}'
        )

        print(
            f'    margin={x["margin"]:.6f}'
            f'  best_diff={x["best_diff"]:+.6f}'
        )

    print()
    print("DISTRIBUTION")
    print("-" * 80)

    for folder in sorted(
        counters,
        key=lambda x: int(x)
    ):

        print(
            f"{folder:10s} {counters[folder]:4d}"
        )

    print("-" * 80)
    print(
        f"{'TOTAL':10s} {sum(counters.values()):4d}"
    )

    print()
    print("OUTPUT:")
    print(
        f"  sorted : {OUTPUT_DIR}"
    )

    print(
        f"  changed: {CHANGED_DIR}"
    )

    print(
        f"  report : {report}"
    )

================================================================================
=== sort_neighbor_v34.py ===
================================================================================
#!/usr/bin/env python3

import csv
import shutil
from pathlib import Path
from collections import Counter

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/test"

SOURCE_CSV = (
    PROJECT
    / "output/benchmark_components/full_analysis/margin_best.csv"
)

OUTPUT_DIR = PROJECT / "output/visual_check_neighbor_v34"
REPORT_CSV = OUTPUT_DIR / "neighbor_decision.csv"

MARGIN_LIMIT = 0.005
NEIGHBOR_RADIUS = 2

# Минимальный score соседнего кадра,
# чтобы считать его уверенным.
NEIGHBOR_SCORE_MIN = 0.80

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".JPG",
    ".JPEG",
    ".png",
    ".PNG",
}

def load_files():
    """
    Получаем порядок фотографий так,
    как они реально находятся в test.
    """

    files = [
        p
        for p in INPUT_DIR.iterdir()
        if p.is_file()
        and p.suffix in IMAGE_EXTENSIONS
    ]

    # Естественная сортировка по имени.
    # Для наших серий это предпочтительнее обычной
    # лексикографической сортировки.
    import re

    def natural_key(path):
        parts = re.split(r"(\d+)", path.name)

        return [
            int(x) if x.isdigit() else x.lower()
            for x in parts
        ]

    files.sort(key=natural_key)

    return files

def load_results():
    results = {}

    with SOURCE_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        for row in csv.DictReader(f):
            results[row["image"]] = row

    return results

def ffloat(value):
    try:
        return float(value)
    except Exception:
        return None

def main():

    if not SOURCE_CSV.exists():
        raise FileNotFoundError(
            f"Не найден CSV: {SOURCE_CSV}"
        )

    files = load_files()
    results = load_results()

    print("=" * 80)
    print("NEIGHBOR CONTEXT V34")
    print("=" * 80)

    print(f"Input images : {len(files)}")
    print(f"Recognition  : {len(results)}")
    print(f"Margin limit : {MARGIN_LIMIT}")
    print(f"Neighbor ±   : {NEIGHBOR_RADIUS}")
    print()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []
    changed = []
    counters = Counter()

    for index, path in enumerate(files):

        name = path.name
        r = results.get(name)

        if r is None:
            continue

        original = r.get("current_first", "")
        second = r.get("current_second", "")

        margin = ffloat(r.get("final_margin"))

        # По умолчанию ничего не меняем.
        final_id = original
        decision = "KEEP"
        reason = "margin>=0.005"

        neighbors = []

        # --------------------------------------------------
        # ONLY LOW-MARGIN CASES
        # --------------------------------------------------

        if (
            margin is not None
            and margin < MARGIN_LIMIT
            and second
        ):

            reason = "low_margin_no_neighbor_support"

            # --------------------------------------------------
            # LOOK ±2
            # --------------------------------------------------

            for delta in range(
                -NEIGHBOR_RADIUS,
                NEIGHBOR_RADIUS + 1,
            ):

                if delta == 0:
                    continue

                pos = index + delta

                if pos < 0 or pos >= len(files):
                    continue

                neighbor_path = files[pos]
                neighbor_result = results.get(
                    neighbor_path.name
                )

                if not neighbor_result:
                    continue

                neighbor_id = (
                    neighbor_result.get("current_first")
                    or ""
                )

                neighbor_score = ffloat(
                    neighbor_result.get("final_first")
                )

                neighbor_margin = ffloat(
                    neighbor_result.get("final_margin")
                )

                neighbors.append({
                    "delta": delta,
                    "file": neighbor_path.name,
                    "id": neighbor_id,
                    "score": neighbor_score,
                    "margin": neighbor_margin,
                })

            # --------------------------------------------------
            # CHECK WHETHER SECOND CANDIDATE
            # APPEARS AMONG NEIGHBORS
            # --------------------------------------------------

            second_votes = []

            for n in neighbors:

                if n["id"] != second:
                    continue

                if (
                    n["score"] is not None
                    and n["score"] >= NEIGHBOR_SCORE_MIN
                ):
                    second_votes.append(n)

            # --------------------------------------------------
            # DECISION
            # --------------------------------------------------

            if second_votes:

                # Второй кандидат подтверждён хотя бы
                # одним уверенным соседним кадром.
                final_id = second
                decision = "SWITCH_TO_SECOND"

                vote_text = ", ".join(
                    f'{x["delta"]:+d}:{x["file"]}'
                    for x in second_votes
                )

                reason = (
                    "second_supported_by_neighbors:"
                    + vote_text
                )

                changed.append({
                    "image": name,
                    "original": original,
                    "second": second,
                    "margin": margin,
                    "reason": reason,
                })

            else:
                reason = (
                    "low_margin_but_no_second_neighbor_support"
                )

        # --------------------------------------------------
        # COPY
        # --------------------------------------------------

        destination_dir = (
            OUTPUT_DIR / final_id
        )

        destination_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

================================================================================
=== recognizer.py: BEST LOGIC ===
================================================================================
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

================================================================================
=== margin_best.csv HEADER + FIRST ROWS ===
================================================================================
image,current_first,current_second,final_first,final_second,final_margin,best_first,best_second,best_diff
00 (1).JPG,78_v33,92_v33,0.946832,0.892311,0.054521,0.956302,0.886462,-0.069840
00 (10).JPG,78_v33,91_v33,0.937443,0.879288,0.058155,0.927204,0.853744,-0.073460
00 (11).JPG,78_v33,95_v33,0.932518,0.890300,0.042218,0.938092,0.881098,-0.056994
00 (12).JPG,78_v33,83_v33,0.929418,0.889445,0.039973,0.928726,0.869961,-0.058765
00 (2).JPG,78_v33,91_v33,0.937333,0.884406,0.052927,0.920193,0.850488,-0.069705
00 (3).JPG,78_v33,93_v33,0.906127,0.851488,0.054639,0.903900,0.822606,-0.081294
00 (4).JPG,78_v33,83_v33,0.950982,0.883375,0.067607,0.949109,0.861064,-0.088045
00 (5).JPG,78_v33,93_v33,0.929355,0.890461,0.038894,0.921265,0.865098,-0.056167
00 (6).JPG,78_v33,92_v33,0.945895,0.889698,0.056197,0.960907,0.879815,-0.081092
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:25:36

Да. Теперь картина стала намного яснее.

**Главный вывод:** `BEST` у нас уже есть, и его нельзя сводить просто к `best_id`. У нас есть независимое сравнение:

- `current_first` — обычный TOP-1;
- `current_second` — TOP-2;
- `final_margin` — насколько TOP-1 опережает TOP-2;
- `best_first` — лучший конкретный reference image для TOP-1;
- `best_second` — лучший reference image для TOP-2;
- `best_diff = best_second - best_first`.

То есть `best_diff > 0` означает: **конкретная лучшая фотография TOP-2 похожа на текущий кадр сильнее, чем лучшая фотография TOP-1**.

И это очень хорошо ложится на нашу новую схему.

### Но есть важный момент

Сейчас `sort_margin005_best.py` использует BEST только при:

```text
final_margin < 0.005
```

То есть если DINO дал:

```text
85 vs 93
margin=0.072
```

BEST вообще не рассматривается.

А нам теперь нужна более умная логика:

```text
DINO уверен
    ↓
оставляем TOP1

DINO НЕ уверен
    ↓
смотрим BEST
    ↓
BEST подтверждает TOP1 → оставляем
BEST подтверждает TOP2 → меняем
BEST тоже неубедителен → смотрим соседнюю последовательность
```

И **только в самом конце**, если и BEST, и последовательность не дают однозначного ответа — LLM.

---

### Ещё важнее: BEST может обнаружить именно тот случай, о котором ты говорил

Например:

```text
кадры 100–120 → адрес 85
кадр 113:
    TOP1 = 85
    TOP2 = 95
    margin = 0.003

BEST:
    best_first  = 0.81
    best_second = 0.94
    best_diff   = +0.13
```

Тогда мы **не должны смотреть на соседей и автоматически ставить 85**.

Это очень похоже на реальный единичный кадр другого адреса.

То есть:

> **последовательность не должна подавлять сильный индивидуальный visual match.**

Это принципиально.

---

### А вот обратный случай

```text
кадр 113:
    TOP1 = 89
    TOP2 = 85
    margin = 0.003

BEST:
    best_first  = 0.79
    best_second = 0.80
    best_diff   = +0.01
```

BEST практически ничего не говорит.

Но:

```text
110 → 85
111 → 85
112 → 85
113 → 89   ← выброс
114 → 85
115 → 85
116 → 85
```

Тогда последовательность имеет очень сильное основание вернуть **85**.

---

## Поэтому я бы сейчас вообще не трогал код

Сначала надо провести **DRY RUN новой логики на уже имеющемся `margin_best.csv`**.

Причём не только `margin < 0.005`.

Я предлагаю проверить несколько порогов:

```text
margin < 0.005
margin < 0.010
margin < 0.020
margin < 0.030
```

и для каждого посмотреть:

```text
сколько кадров попадает в BEST-проверку
сколько BEST меняет TOP1
сколько изменений совпадает с соседней серией
сколько BEST противоречит соседям
```

Это позволит увидеть, **где BEST действительно полезен, а где шумит**.

### И ещё одно

Твой `margin_best.csv` уже содержит именно те данные, которые нужны. Поэтому **Qwen сейчас можно вообще выключить из эксперимента**.

Сначала строим:

**DINO → BEST → sequence**

а уже потом:

**DINO → BEST → sequence → Qwen только если всё ещё неоднозначно.**

Это будет и быстрее, и гораздо более объяснимо.

Если хочешь, следующим шагом сделаем **отдельный `dry_run_best_sequence.py`**, который ничего не меняет и для каждого спорного кадра пишет примерно:

```text
img_007
DINO:      89 vs 85   margin=0.0106
BEST:      89=0.81    85=0.86   diff=+0.05
NEIGHBORS: 85 85 85 85
DECISION:  85
REASON:    BEST weak, sequence strongly supports 85
```

и для настоящего одиночного кадра:

```text
img_113
DINO:      85 vs 95   margin=0.003
BEST:      85=0.79    95=0.94   diff=+0.15
NEIGHBORS: 85 85 85 85
DECISION:  95
REASON:    BEST strongly supports alternative
```

**Вот такой dry-run сейчас будет самым полезным экспериментом.**

---

### 👤 **User** — 2026-08-15 15:26:44

да

---

### 🤖 **Assistant** — 2026-08-15 15:26:45

> **Running a no-op computation**
>
>
> **Running a no-op computation**
>
> 
>
> Worked for a couple of seconds

Да. Сделаем **только DRY RUN**, существующие файлы не трогаем.

Создадим отдельный скрипт, который:

1. берёт `margin_best.csv`;
2. проверяет кадры с `margin < 0.020`;
3. смотрит `BEST`;
4. смотрит соседей ±2;
5. **не меняет файлы и не сортирует**;
6. показывает предлагаемое решение и причину.

Сначала выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/dry_run_best_sequence.py <<'PY'
#!/usr/bin/env python3

import csv
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

CSV_PATH = (
    PROJECT
    / "output/benchmark_components/full_analysis/margin_best.csv"
)

INPUT_DIR = PROJECT / "data/input/test"

# Смотрим немного шире старого порога 0.005.
MARGIN_LIMIT = 0.020

# Соседи слева/справа.
NEIGHBOR_RADIUS = 2

# Минимальная уверенность соседа.
NEIGHBOR_SCORE_MIN = 0.80

# BEST должен выигрывать хотя бы на столько,
# чтобы считать его убедительным.
BEST_STRONG_DIFF = 0.05

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".JPG",
    ".JPEG",
    ".png",
    ".PNG",
}

def natural_key(path):
    parts = re.split(r"(\d+)", path.name)

    return [
        int(x) if x.isdigit() else x.lower()
        for x in parts
    ]

def ffloat(value):
    try:
        return float(value)
    except Exception:
        return None

def load_files():
    files = [
        p
        for p in INPUT_DIR.iterdir()
        if p.is_file()
        and p.suffix in IMAGE_EXTENSIONS
    ]

    files.sort(key=natural_key)

    return files

def load_results():

    results = {}

    with CSV_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        for row in csv.DictReader(f):
            results[row["image"]] = row

    return results

def get_neighbors(files, results, index):

    neighbors = []

    for delta in range(
        -NEIGHBOR_RADIUS,
        NEIGHBOR_RADIUS + 1,
    ):

        if delta == 0:
            continue

        pos = index + delta

        if pos < 0 or pos >= len(files):
            continue

        p = files[pos]

        r = results.get(p.name)

        if not r:
            continue

        neighbor_id = r.get(
            "current_first",
            "",
        )

        score = ffloat(
            r.get("final_first")
        )

        margin = ffloat(
            r.get("final_margin")
        )

        neighbors.append({
            "delta": delta,
            "image": p.name,
            "id": neighbor_id,
            "score": score,
            "margin": margin,
        })

    return neighbors

def main():

    print("=" * 80)
    print("DRY RUN: BEST + SEQUENCE")
    print("=" * 80)

    print("CSV:", CSV_PATH)
    print("INPUT:", INPUT_DIR)
    print("MARGIN LIMIT:", MARGIN_LIMIT)
    print("BEST STRONG DIFF:", BEST_STRONG_DIFF)
    print("NEIGHBOR RADIUS:", NEIGHBOR_RADIUS)
    print()

    if not CSV_PATH.exists():
        raise FileNotFoundError(CSV_PATH)

    if not INPUT_DIR.exists():
        raise FileNotFoundError(INPUT_DIR)

    files = load_files()
    results = load_results()

    print(f"Images:     {len(files)}")
    print(f"Recognized: {len(results)}")
    print()

    checked = 0
    best_changes = 0
    sequence_changes = 0
    ambiguous = 0
    kept = 0

    print("=" * 80)
    print("SUSPICIOUS FRAMES")
    print("=" * 80)

    for index, path in enumerate(files):

        r = results.get(path.name)

        if not r:
            continue

        margin = ffloat(
            r.get("final_margin")
        )

        if margin is None:
            continue

        if margin >= MARGIN_LIMIT:
            continue

        checked += 1

        first = r.get(
            "current_first",
            "",
        )

        second = r.get(
            "current_second",
            "",
        )

        first_score = ffloat(
            r.get("final_first")
        )

        second_score = ffloat(
            r.get("final_second")
        )

        best_first = ffloat(
            r.get("best_first")
        )

        best_second = ffloat(
            r.get("best_second")
        )

        best_diff = ffloat(
            r.get("best_diff")
        )

        neighbors = get_neighbors(
            files,
            results,
            index,
        )

        # --------------------------------------------------
        # BEST
        # --------------------------------------------------

        best_decision = None
        best_reason = ""

        if (
            best_diff is not None
            and best_diff >= BEST_STRONG_DIFF
        ):

            best_decision = second

            best_reason = (
                "BEST strongly supports TOP2"
            )

        elif (
            best_diff is not None
            and best_diff <= -BEST_STRONG_DIFF
        ):

            best_decision = first

            best_reason = (
                "BEST strongly supports TOP1"
            )

        else:

            best_reason = (
                "BEST inconclusive"
            )

        # --------------------------------------------------
        # SEQUENCE
        # --------------------------------------------------

        neighbor_first_votes = []
        neighbor_second_votes = []

        for n in neighbors:

            if (
                n["score"] is not None
                and n["score"] < NEIGHBOR_SCORE_MIN
            ):
                continue

            if n["id"] == first:
                neighbor_first_votes.append(n)

            if n["id"] == second:
                neighbor_second_votes.append(n)

        sequence_decision = None
        sequence_reason = ""

        if (
            len(neighbor_first_votes)
            >= 2
        ):

            sequence_decision = first

            sequence_reason = (
                "neighbors strongly support TOP1"
            )

        elif (
            len(neighbor_second_votes)
            >= 2
        ):

            sequence_decision = second

            sequence_reason = (
                "neighbors strongly support TOP2"
            )

        else:

            sequence_reason = (
                "sequence inconclusive"
            )

        # --------------------------------------------------
        # FINAL PROPOSED DECISION
        #
        # PRIORITY:
        #
        # 1. Strong BEST
        # 2. Strong sequence
        # 3. Keep TOP1
        #
        # This is DRY RUN only.
        # --------------------------------------------------

        decision = first
        reason = "KEEP_TOP1"

        if best_decision is not None:

            decision = best_decision
            reason = best_reason

            if decision != first:
                best_changes += 1

        elif sequence_decision is not None:

            decision = sequence_decision
            reason = sequence_reason

            if decision != first:
                sequence_changes += 1

        else:

            kept += 1

            if (
                best_diff is not None
                and abs(best_diff)
                < BEST_STRONG_DIFF
            ):
                ambiguous += 1

        # --------------------------------------------------
        # PRINT
        # --------------------------------------------------

        print()
        print("-" * 80)

        print(
            f"{index:4d} {path.name}"
        )

        print(
            f"  DINO:   "
            f"{first} vs {second} "
            f"margin={margin:.6f}"
        )

        print(
            f"  SCORE:  "
            f"{first_score if first_score is not None else 0:.4f} "
            f"vs "
            f"{second_score if second_score is not None else 0:.4f}"
        )

        print(
            f"  BEST:   "
            f"{best_first if best_first is not None else 0:.4f} "
            f"vs "
            f"{best_second if best_second is not None else 0:.4f} "
            f"diff={best_diff if best_diff is not None else 0:+.6f}"
        )

        print(
            f"  BEST:   "
            f"{best_decision or '-'} "
            f"({best_reason})"
        )

        if neighbors:

            text = " | ".join(
                f'{n["delta"]:+d}:'
                f'{n["id"]}'
                f'({n["score"]:.3f}'
                if n["score"] is not None
                else f'{n["delta"]:+d}:{n["id"]}'
                for n in neighbors
            )

            print(
                f"  NEIGH:  {text}"
            )

        print(
            f"  SEQ:    "
            f"{sequence_decision or '-'} "
            f"({sequence_reason})"
        )

        print(
            f"  >>>     "
            f"{first} -> {decision}"
        )

        print(
            f"  REASON: "
            f"{reason}"
        )

    print()
    print("=" * 80)
    print("DRY RUN SUMMARY")
    print("=" * 80)

    print(
        f"Suspicious frames:       {checked}"
    )

    print(
        f"Changed by BEST:         {best_changes}"
    )

    print(
        f"Changed by SEQUENCE:     {sequence_changes}"
    )

    print(
        f"Kept TOP1:               {kept}"
    )

    print(
        f"Still ambiguous:         {ambiguous}"
    )

    print()
    print("NO FILES WERE MODIFIED.")
    print("=" * 80)

if __name__ == "__main__":
    main()
PY

chmod +x scripts/dry_run_best_sequence.py

uv run python scripts/dry_run_best_sequence.py
```

Обрати внимание на один принцип: **сильный BEST имеет приоритет над соседями**.

То есть мы специально не повторяем ошибку старой логики `neighbor_v34`, где достаточно было увидеть второго кандидата у соседа.

После запуска пришли вывод `DRY RUN SUMMARY` и несколько первых/самых интересных блоков `SUSPICIOUS FRAMES`. По ним уже настроим реальные пороги `BEST_STRONG_DIFF` и `MARGIN_LIMIT`, прежде чем что-либо подключать к сортировке.

---

### 👤 **User** — 2026-08-15 15:27:09

int_mvp_v02

cat > scripts/dry_run_best_sequence.py <<'PY'
#!/usr/bin/env python3

import csv
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

CSV_PATH = (
    PROJECT
    / "output/benchmark_components/full_analysis/margin_best.csv"
)

INPUT_DIR = PROJECT / "data/input/test"

# Смотрим немного шире старого порога 0.005.
MARGIN_LIMIT = 0.020

# Соседи слева/справа.
uv run python scripts/dry_run_best_sequence.py"anges}" else 0:+.6f}"
================================================================================
DRY RUN: BEST + SEQUENCE
================================================================================
CSV: /home/alexice/projects/scene_fingerprint_mvp_v02/output/benchmark_components/full_analysis/margin_best.csv
INPUT: /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/test
MARGIN LIMIT: 0.02
BEST STRONG DIFF: 0.05
NEIGHBOR RADIUS: 2

Images:     256
Recognized: 262

================================================================================
SUSPICIOUS FRAMES
================================================================================

================================================================================
DRY RUN SUMMARY
================================================================================
Suspicious frames:       0
Changed by BEST:         0
Changed by SEQUENCE:     0
Kept TOP1:               0
Still ambiguous:         0

NO FILES WERE MODIFIED.

---

### 🤖 **Assistant** — 2026-08-15 15:27:10

Да. И здесь результат **0 подозрительных кадров — это подозрительно само по себе**.

Проблема, скорее всего, не в DINO, а в логике нашего dry-run: судя по выводу, скрипт вообще не дошёл до обработки кадров или условие фильтрации отсекает всё.

У нас уже есть важный факт:

- `Images: 256`
- `Recognized: 262`
- `MARGIN LIMIT: 0.020`
- но `Suspicious frames: 0`
- `Kept TOP1: 0`

То есть **даже обычные кадры с margin > 0.02 не попали в `Kept TOP1`**. Значит, проблема почти наверняка в сопоставлении имён файлов или в структуре CSV/условиях цикла.

Давай сначала **не менять код**, а посмотрим сам скрипт целиком. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "================================================================================"
echo "=== dry_run_best_sequence.py ==="
echo "================================================================================"

nl -ba scripts/dry_run_best_sequence.py | sed -n '1,320p'
```

И ещё сразу проверим, какие именно имена видит скрипт с обеих сторон:

```bash
echo
echo "================================================================================"
echo "=== CSV SAMPLE ==="
echo "================================================================================"

python - <<'PY'
import csv
from pathlib import Path

p = Path("output/benchmark_components/full_analysis/margin_best.csv")

with p.open(encoding="utf-8-sig", newline="") as f:
    r = csv.DictReader(f)
    rows = list(r)

print("CSV rows:", len(rows))
print("fields:", r.fieldnames)

for x in rows[:10]:
    print(repr(x["image"]), x["current_first"], x["current_second"], x["final_margin"], x["best_diff"])
PY

echo
echo "================================================================================"
echo "=== TEST FILES ==="
echo "================================================================================"

find data/input/test -maxdepth 1 -type f \
  \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) \
  | sort -V | head -20
```

И отдельно самое важное — проверим пересечение:

```bash
python - <<'PY'
import csv
from pathlib import Path

csv_path = Path("output/benchmark_components/full_analysis/margin_best.csv")
input_dir = Path("data/input/test")

with csv_path.open(encoding="utf-8-sig", newline="") as f:
    csv_names = {r["image"] for r in csv.DictReader(f)}

file_names = {
    p.name
    for p in input_dir.iterdir()
    if p.is_file()
    and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
}

print("CSV names :", len(csv_names))
print("FILE names:", len(file_names))
print("MATCH     :", len(csv_names & file_names))
print("CSV only  :", len(csv_names - file_names))
print("FILE only :", len(file_names - csv_names))

print()
print("CSV only examples:")
for x in sorted(csv_names - file_names)[:10]:
    print(repr(x))

print()
print("FILE only examples:")
for x in sorted(file_names - csv_names)[:10]:
    print(repr(x))
PY
```

### И ещё один момент

Я бы **не использовал пока LLM вообще**.

Наша новая логика должна быть такой:

```text
DINO v33
   ↓
TOP1 + TOP2 + margin
   ↓
если margin нормальный
   → оставить TOP1
   ↓
если margin маленький
   → посмотреть BEST
   ↓
если BEST действительно уверенно меняет кандидата
   → проверить последовательность соседних кадров
   ↓
если последовательность подтверждает
   → изменить TOP1
   ↓
иначе
   → оставить TOP1
```

Причём `BEST` у нас уже есть:

```text
current_first
current_second
final_first
final_second
final_margin

best_first
best_second
best_diff
```

И `best_diff` имеет очень понятный смысл:

```text
best_diff = best_second - best_first
```

Поэтому:

- `best_diff < 0` → BEST тоже считает TOP1 лучше;
- `best_diff > 0` → BEST считает **TOP2 лучше**;
- чем больше `best_diff`, тем сильнее BEST против исходного TOP1.

Например:

```text
TOP1=95
TOP2=94
margin=0.012

best_first=0.71
best_second=0.76
best_diff=+0.05
```

Вот это действительно **подозрительный кадр**.

А если:

```text
margin=0.012
best_diff=-0.06
```

то BEST подтверждает TOP1 — менять ничего не надо.

И уже только после этого смотрим последовательность:

```text
95 95 95 94 95 95
         ↑
      подозрение

BEST → 94
соседи → 94, 94
```

→ меняем.

А вот:

```text
95 95 95 94 95 95
         ↑
      подозрение

BEST → 94
соседи → 95, 95
```

→ **не меняем**.

Это как раз то, что нам нужно вместо Qwen: **DINO + BEST + последовательность**, причём LLM вообще не нужен в штатном пайплайне.

Сейчас главное — понять, почему `dry_run_best_sequence.py` получил **0/0/0/0**. Пришли вывод этих трёх проверок.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)

---
