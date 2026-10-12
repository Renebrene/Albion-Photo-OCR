## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 👤 **User** — 2026-08-15 02:51:33

02

echo "================ PROJECT ================"
pwd

echo
echo "================ RECOGNIZER FILES ================"
find . -type f $ \
  -iname '*recogniz*' -o \
  -iname '*fingerprint*' -o \
  -iname '*scene_analy*' \
$ -not -path './.venv/*' -not -path './.git/*' | sort

echo
echo "================ BACKUPS / OLD VERSIONS ================"
find . -type f $ \
  -name '*.bak' -o \
  -name '*.old' -o \
  -name '*.orig' -o \
  -name '*.backup' -o \
  -name '*~' \
$ -not -path './.venv/*' -not -path './.git/*' | sort

  2>/dev/null | head -n 300ogn|recognize|classify|assign|candidate' \"
bash: cd: /home/alexice/scene_fingerprint_mvp_v02: No such file or directory
================ PROJECT ================
/home/alexice/projects/scene_fingerprint_mvp_v02

================ RECOGNIZER FILES ================
./app_backup_before_patch/core/fingerprint.py
./app_backup_before_patch/core/__pycache__/fingerprint.cpython-312.pyc
./app_backup_before_patch/core/__pycache__/recognizer.cpython-312.pyc
./app_backup_before_patch/core/__pycache__/scene_analyzer.cpython-312.pyc
./app_backup_before_patch/core/recognizer.py
./app_backup_before_patch/core/scene_analyzer.py
./app/core/fingerprint.py
./app/core/fingerprint.py.bak_before_create_opt
./app/core/fingerprint.py.before_patchfix
./app/core/__pycache__/fingerprint.cpython-312.pyc
./app/core/__pycache__/recognizer.cpython-312.pyc
./app/core/__pycache__/scene_analyzer.cpython-312.pyc
./app/core/recognizer.py
./app/core/recognizer.py.backup_before_force_match
./app/core/recognizer.py.backup_before_optimization
./app/core/recognizer.py.before_patchfix
./app/core/scene_analyzer.py
./app/core/scene_analyzer.py.backup_before_optimization
./app/core/scene_analyzer.py.bak_before_create_opt
./backup_patch_tokens_20260808_131532/fingerprint.py
./backup_patch_tokens_20260808_131532/recognizer.py
./backup_patch_tokens_20260808_131532/scene_analyzer.py
./backup_v31_dynamic_20260808_231245/app/core/fingerprint.py
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py
./backup_v31_dynamic_20260808_231245/app/core/scene_analyzer.py
./backup_v31_final_20260808_231056/app/core/fingerprint.py
./backup_v31_final_20260808_231056/app/core/recognizer.py
./backup_v31_final_20260808_231056/app/core/scene_analyzer.py
./backup_v31_fix_20260808_230926/fingerprint.py
./backup_v31_fix_20260808_230926/recognizer.py
./backup_v31_fix_20260808_230926/scene_analyzer.py
./scripts/make_subfingerprints.py
./scripts/make_subfingerprints_v2.py

================ BACKUPS / OLD VERSIONS ================

================ NO_MATCH / THRESHOLD / MARGIN ================
./classify_test.sh:28:# Initial thresholds
./classify_test.sh:31:THRESHOLD="${THRESHOLD:-0.60}"
./classify_test.sh:32:MARGIN="${MARGIN:-0.03}"
./classify_test.sh:111:THRESHOLD = float(os.environ["SF_THRESHOLD"])
./classify_test.sh:112:MARGIN = float(os.environ["SF_MARGIN"])
./classify_test.sh:279:    "margin",
./classify_test.sh:359:        margin = (
./classify_test.sh:369:            best_score >= THRESHOLD
./classify_test.sh:370:            and margin >= MARGIN
./classify_test.sh:427:            f"{margin:.6f}",
./classify_test.sh:437:            f"margin={margin:.4f} "
./classify_test.sh:480:print(f"Threshold:   {THRESHOLD}")
./classify_test.sh:481:print(f"Margin:      {MARGIN}")
./classify_test.sh:514:export SF_THRESHOLD="$THRESHOLD"
./classify_test.sh:515:export SF_MARGIN="$MARGIN"
./classify_test.sh:530:echo "      Threshold:    $THRESHOLD"
./classify_test.sh:531:echo "      Margin:       $MARGIN"
./app/core/recognizer.py:30:        margin to second-best candidate
./app/core/recognizer.py:38:    HIGH_MARGIN = 0.03
./app/core/recognizer.py:39:    PROBABLE_MARGIN = 0.015
./app/core/recognizer.py:57:    def _confidence(
./app/core/recognizer.py:60:        margin,
./app/core/recognizer.py:63:        margin = float(margin)
./app/core/recognizer.py:67:            and margin >= cls.HIGH_MARGIN
./app/core/recognizer.py:73:            and margin >= cls.PROBABLE_MARGIN
./app/core/recognizer.py:80:        return "NO_MATCH"
./app/core/recognizer.py:83:    def _status_from_confidence(
./app/core/recognizer.py:84:        confidence,
./app/core/recognizer.py:86:        if confidence == "HIGH":
./app/core/recognizer.py:89:        if confidence == "PROBABLE":
./app/core/recognizer.py:92:        if confidence == "AMBIGUOUS":
./app/core/recognizer.py:95:        return "NO_MATCH"
./app/core/recognizer.py:100:        top_k=5,
./app/core/recognizer.py:101:        threshold=0.65,
./app/core/recognizer.py:381:                    int(top_k),
./app/core/recognizer.py:392:                        "margin": 0.0,
./app/core/recognizer.py:393:                        "confidence": "NO_MATCH",
./app/core/recognizer.py:394:                        "status": "NO_MATCH",
./app/core/recognizer.py:414:            margin = (
./app/core/recognizer.py:419:            confidence = (
./app/core/recognizer.py:420:                self._confidence(
./app/core/recognizer.py:422:                    margin,
./app/core/recognizer.py:427:                self._status_from_confidence(
./app/core/recognizer.py:428:                    confidence
./app/core/recognizer.py:434:            # The threshold is NO LONGER a rejection gate.
./app/core/recognizer.py:436:            # available address. The score/confidence are kept
./app/core/recognizer.py:440:            if best_score < threshold:
./app/core/recognizer.py:443:                status = self._status_from_confidence(
./app/core/recognizer.py:444:                    confidence
./app/core/recognizer.py:459:                    "margin": float(
./app/core/recognizer.py:460:                        margin
./app/core/recognizer.py:463:                    "confidence": confidence,
./app/core/recognizer.py:487:        top_k=5,
./app/core/recognizer.py:488:        threshold=0.65,
./app/core/recognizer.py:492:            top_k=top_k,
./app/core/recognizer.py:493:            threshold=threshold,
./app/core/recognizer.py.backup_before_optimization:26:        margin to second-best candidate
./app/core/recognizer.py.backup_before_optimization:34:    HIGH_MARGIN = 0.03
./app/core/recognizer.py.backup_before_optimization:35:    PROBABLE_MARGIN = 0.015
./app/core/recognizer.py.backup_before_optimization:53:    def _confidence(
./app/core/recognizer.py.backup_before_optimization:56:        margin,
./app/core/recognizer.py.backup_before_optimization:59:        margin = float(margin)
./app/core/recognizer.py.backup_before_optimization:63:            and margin >= cls.HIGH_MARGIN
./app/core/recognizer.py.backup_before_optimization:69:            and margin >= cls.PROBABLE_MARGIN
./app/core/recognizer.py.backup_before_optimization:76:        return "NO_MATCH"
./app/core/recognizer.py.backup_before_optimization:79:    def _status_from_confidence(
./app/core/recognizer.py.backup_before_optimization:80:        confidence,
./app/core/recognizer.py.backup_before_optimization:82:        if confidence == "HIGH":
./app/core/recognizer.py.backup_before_optimization:85:        if confidence == "PROBABLE":
./app/core/recognizer.py.backup_before_optimization:88:        if confidence == "AMBIGUOUS":
./app/core/recognizer.py.backup_before_optimization:91:        return "NO_MATCH"
./app/core/recognizer.py.backup_before_optimization:96:        top_k=5,
./app/core/recognizer.py.backup_before_optimization:97:        threshold=0.65,
./app/core/recognizer.py.backup_before_optimization:292:                    int(top_k),
./app/core/recognizer.py.backup_before_optimization:303:                        "margin": 0.0,
./app/core/recognizer.py.backup_before_optimization:304:                        "confidence": "NO_MATCH",
./app/core/recognizer.py.backup_before_optimization:305:                        "status": "NO_MATCH",
./app/core/recognizer.py.backup_before_optimization:325:            margin = (
./app/core/recognizer.py.backup_before_optimization:330:            confidence = (
./app/core/recognizer.py.backup_before_optimization:331:                self._confidence(
./app/core/recognizer.py.backup_before_optimization:333:                    margin,
./app/core/recognizer.py.backup_before_optimization:338:                self._status_from_confidence(
./app/core/recognizer.py.backup_before_optimization:339:                    confidence
./app/core/recognizer.py.backup_before_optimization:345:            # The threshold is NO LONGER a rejection gate.
./app/core/recognizer.py.backup_before_optimization:347:            # available address. The score/confidence are kept
./app/core/recognizer.py.backup_before_optimization:351:            if best_score < threshold:
./app/core/recognizer.py.backup_before_optimization:354:                status = self._status_from_confidence(
./app/core/recognizer.py.backup_before_optimization:355:                    confidence
./app/core/recognizer.py.backup_before_optimization:370:                    "margin": float(
./app/core/recognizer.py.backup_before_optimization:371:                        margin
./app/core/recognizer.py.backup_before_optimization:374:                    "confidence": confidence,
./app/core/recognizer.py.backup_before_optimization:398:        top_k=5,
./app/core/recognizer.py.backup_before_optimization:399:        threshold=0.65,
./app/core/recognizer.py.backup_before_optimization:403:            top_k=top_k,
./app/core/recognizer.py.backup_before_optimization:404:            threshold=threshold,
./app/core/recognizer.py.before_patchfix:143:        top_k=5,
./app/core/recognizer.py.before_patchfix:144:        threshold=0.65,
./app/core/recognizer.py.before_patchfix:198:                if scores["score"] >= threshold:
./app/core/recognizer.py.before_patchfix:209:            candidates = candidates[:top_k]
./app/core/recognizer.py.backup_before_force_match:26:        margin to second-best candidate
./app/core/recognizer.py.backup_before_force_match:34:    HIGH_MARGIN = 0.03
./app/core/recognizer.py.backup_before_force_match:35:    PROBABLE_MARGIN = 0.015
./app/core/recognizer.py.backup_before_force_match:53:    def _confidence(
./app/core/recognizer.py.backup_before_force_match:56:        margin,
./app/core/recognizer.py.backup_before_force_match:59:        margin = float(margin)
./app/core/recognizer.py.backup_before_force_match:63:            and margin >= cls.HIGH_MARGIN
./app/core/recognizer.py.backup_before_force_match:69:            and margin >= cls.PROBABLE_MARGIN
./app/core/recognizer.py.backup_before_force_match:76:        return "NO_MATCH"
./app/core/recognizer.py.backup_before_force_match:79:    def _status_from_confidence(
./app/core/recognizer.py.backup_before_force_match:80:        confidence,
./app/core/recognizer.py.backup_before_force_match:82:        if confidence == "HIGH":
./app/core/recognizer.py.backup_before_force_match:85:        if confidence == "PROBABLE":
./app/core/recognizer.py.backup_before_force_match:88:        if confidence == "AMBIGUOUS":
./app/core/recognizer.py.backup_before_force_match:91:        return "NO_MATCH"
./app/core/recognizer.py.backup_before_force_match:96:        top_k=5,
./app/core/recognizer.py.backup_before_force_match:97:        threshold=0.65,
./app/core/recognizer.py.backup_before_force_match:292:                    int(top_k),
./app/core/recognizer.py.backup_before_force_match:303:                        "margin": 0.0,
./app/core/recognizer.py.backup_before_force_match:304:                        "confidence": "NO_MATCH",
./app/core/recognizer.py.backup_before_force_match:305:                        "status": "NO_MATCH",
./app/core/recognizer.py.backup_before_force_match:325:            margin = (
./app/core/recognizer.py.backup_before_force_match:330:            confidence = (
./app/core/recognizer.py.backup_before_force_match:331:                self._confidence(
./app/core/recognizer.py.backup_before_force_match:333:                    margin,
./app/core/recognizer.py.backup_before_force_match:338:                self._status_from_confidence(
./app/core/recognizer.py.backup_before_force_match:339:                    confidence
./app/core/recognizer.py.backup_before_force_match:343:            # Threshold is still an absolute safety gate.
./app/core/recognizer.py.backup_before_force_match:344:            if best_score < threshold:
./app/core/recognizer.py.backup_before_force_match:346:                status = "NO_MATCH"
./app/core/recognizer.py.backup_before_force_match:362:                    "margin": float(
./app/core/recognizer.py.backup_before_force_match:363:                        margin
./app/core/recognizer.py.backup_before_force_match:366:                    "confidence": confidence,
./app/core/recognizer.py.backup_before_force_match:390:        top_k=5,
./app/core/recognizer.py.backup_before_force_match:391:        threshold=0.65,
./app/core/recognizer.py.backup_before_force_match:395:            top_k=top_k,
./app/core/recognizer.py.backup_before_force_match:396:            threshold=threshold,
./app/main.py:41:            topk = ui.number("Top-K", value=5, min=1, max=20).classes("w-32")
./app/main.py:42:            threshold = ui.number("Порог", value=0.65, min=0, max=1, step=0.01).classes("w-32")
./app/main.py:49:                        folder2.value, int(topk.value), float(threshold.value)
./app/cli.py:138:        "--top-k",
./app/cli.py:145:        "--threshold",
./app/cli.py:256:    margin = float(
./app/cli.py:258:            "margin",
./app/cli.py:263:    confidence = result.get(
./app/cli.py:264:        "confidence",
./app/cli.py:265:        "NO_MATCH",
./app/cli.py:270:        "NO_MATCH",
./app/cli.py:289:        f"MARGIN       "
./app/cli.py:290:        f"{margin:.4f}"
./app/cli.py:294:        f"CONFIDENCE   "
./app/cli.py:295:        f"{confidence}"
./app/cli.py:631:                top_k=args.top_k,
./app/cli.py:632:                threshold=args.threshold,
./app/ocr/ocr_pipeline.py:14:    confidence: float
./app/ocr/ocr_pipeline.py:63:                confidence = float(line[1][1])
./app/ocr/ocr_pipeline.py:68:                        confidence=confidence,
./app/ocr/ocr_pipeline.py:118:                f"confidence={item.confidence:.4f}"
./app/ocr/grid_ocr.py:44:    confidence: float
./app/ocr/grid_ocr.py:170:            confidence = float(text_info[1])
./app/ocr/grid_ocr.py:176:                    confidence=confidence,
./app/ocr/grid_ocr.py:369:                    f"confidence="
./app/ocr/grid_ocr.py:370:                    f"{item.confidence:.3f} "
./app/ocr/grid_ocr.py:387:            -item.confidence,
./app/ocr/grid_ocr.py:451:                f"confidence="
./app/ocr/grid_ocr.py:452:                f"{item.confidence:.4f} "
./app/ocr/plate_detector.py:44:    _, mask = cv2.threshold(
./README.md:59:uv run scene-fingerprint recognize data/input/new --top-k 5 --threshold 0.65
./final_test_78_95.json:17:    "margin": 0.055172390341758804,
./final_test_78_95.json:18:    "confidence": "HIGH",
./final_test_78_95.json:80:    "margin": 0.05908331394195543,
./final_test_78_95.json:81:    "confidence": "HIGH",
./final_test_78_95.json:143:    "margin": 0.04334602713584912,
./final_test_78_95.json:144:    "confidence": "HIGH",
./final_test_78_95.json:206:    "margin": 0.04064186394214642,
./final_test_78_95.json:207:    "confidence": "HIGH",
./final_test_78_95.json:269:    "margin": 0.053077211380004874,
./final_test_78_95.json:270:    "confidence": "HIGH",
./final_test_78_95.json:332:    "margin": 0.05417974233627321,
./final_test_78_95.json:333:    "confidence": "HIGH",
./final_test_78_95.json:395:    "margin": 0.06788264870643623,
./final_test_78_95.json:396:    "confidence": "HIGH",
./final_test_78_95.json:458:    "margin": 0.03956188082695011,
./final_test_78_95.json:459:    "confidence": "HIGH",
./final_test_78_95.json:521:    "margin": 0.05726868331432344,
./final_test_78_95.json:522:    "confidence": "HIGH",
./final_test_78_95.json:584:    "margin": 0.03339495003223425,
./final_test_78_95.json:585:    "confidence": "HIGH",
./final_test_78_95.json:647:    "margin": 0.054865639209747186,
./final_test_78_95.json:648:    "confidence": "HIGH",
./final_test_78_95.json:710:    "margin": 0.04664526760578147,
./final_test_78_95.json:711:    "confidence": "HIGH",
./final_test_78_95.json:773:    "margin": 0.05892550766468052,
./final_test_78_95.json:774:    "confidence": "HIGH",
./final_test_78_95.json:836:    "margin": 0.05799145579338072,
./final_test_78_95.json:837:    "confidence": "HIGH",
./final_test_78_95.json:899:    "margin": 0.05059978723526015,
./final_test_78_95.json:900:    "confidence": "HIGH",
./final_test_78_95.json:962:    "margin": 0.05278609752655039,
./final_test_78_95.json:963:    "confidence": "HIGH",
./final_test_78_95.json:1025:    "margin": 0.06642506897449485,
./final_test_78_95.json:1026:    "confidence": "HIGH",
./final_test_78_95.json:1088:    "margin": 0.14474267363548265,
./final_test_78_95.json:1089:    "confidence": "HIGH",
./final_test_78_95.json:1151:    "margin": 0.13358657956123332,
./final_test_78_95.json:1152:    "confidence": "HIGH",
./final_test_78_95.json:1214:    "margin": 0.0014180433750151655,
./final_test_78_95.json:1215:    "confidence": "AMBIGUOUS",
./final_test_78_95.json:1277:    "margin": 0.004476211667060914,
./final_test_78_95.json:1278:    "confidence": "AMBIGUOUS",
./final_test_78_95.json:1340:    "margin": 0.05123696506023423,
./final_test_78_95.json:1341:    "confidence": "HIGH",
./final_test_78_95.json:1403:    "margin": 0.07560374617576604,
./final_test_78_95.json:1404:    "confidence": "HIGH",
./final_test_78_95.json:1466:    "margin": 0.0692699843645097,
./final_test_78_95.json:1467:    "confidence": "HIGH",
./final_test_78_95.json:1529:    "margin": 0.0656289201974869,
./final_test_78_95.json:1530:    "confidence": "HIGH",
./final_test_78_95.json:1592:    "margin": 0.06490068495273593,
./final_test_78_95.json:1593:    "confidence": "HIGH",
./final_test_78_95.json:1655:    "margin": 0.035905368328094545,
./final_test_78_95.json:1656:    "confidence": "HIGH",
./final_test_78_95.json:1718:    "margin": 0.03849608361721035,
./final_test_78_95.json:1719:    "confidence": "PROBABLE",
./final_test_78_95.json:1781:    "margin": 0.02907726526260379,
./final_test_78_95.json:1782:    "confidence": "PROBABLE",
./final_test_78_95.json:1844:    "margin": 0.04386175811290771,
./final_test_78_95.json:1845:    "confidence": "HIGH",
./final_test_78_95.json:1907:    "margin": 0.06670816719532002,
./final_test_78_95.json:1908:    "confidence": "HIGH",
./final_test_78_95.json:1970:    "margin": 0.06682182848453533,
./final_test_78_95.json:1971:    "confidence": "HIGH",
./final_test_78_95.json:2033:    "margin": 0.062001544237136774,
./final_test_78_95.json:2034:    "confidence": "HIGH",
./final_test_78_95.json:2096:    "margin": 0.06328806340694437,
./final_test_78_95.json:2097:    "confidence": "HIGH",
./final_test_78_95.json:2159:    "margin": 0.0673971277475357,
./final_test_78_95.json:2160:    "confidence": "HIGH",
./final_test_78_95.json:2222:    "margin": 0.05703924477100375,
./final_test_78_95.json:2223:    "confidence": "PROBABLE",
./final_test_78_95.json:2285:    "margin": 0.06472590327262884,
./final_test_78_95.json:2286:    "confidence": "PROBABLE",
./final_test_78_95.json:2348:    "margin": 0.05709906280040755,
./final_test_78_95.json:2349:    "confidence": "HIGH",
./final_test_78_95.json:2411:    "margin": 0.021502690315246653,
./final_test_78_95.json:2412:    "confidence": "PROBABLE",
./final_test_78_95.json:2474:    "margin": 0.041815704107284635,
./final_test_78_95.json:2475:    "confidence": "HIGH",
./final_test_78_95.json:2537:    "margin": 0.03454017341136928,
./final_test_78_95.json:2538:    "confidence": "HIGH",
./final_test_78_95.json:2600:    "margin": 0.01883472502231598,
./final_test_78_95.json:2601:    "confidence": "NO_MATCH",
./final_test_78_95.json:2602:    "status": "NO_MATCH",
./final_test_78_95.json:2663:    "margin": 0.05187192916870109,
./final_test_78_95.json:2664:    "confidence": "PROBABLE",
./final_test_78_95.json:2726:    "margin": 0.05167678415775301,
./final_test_78_95.json:2727:    "confidence": "PROBABLE",
./final_test_78_95.json:2789:    "margin": 0.05978727221488955,
./final_test_78_95.json:2790:    "confidence": "HIGH",
./final_test_78_95.json:2852:    "margin": 0.01239921510219566,
./final_test_78_95.json:2853:    "confidence": "AMBIGUOUS",
./final_test_78_95.json:2915:    "margin": 0.05480723798274989,
./final_test_78_95.json:2916:    "confidence": "HIGH",
./final_test_78_95.json:2978:    "margin": 0.032756130099296565,
./final_test_78_95.json:2979:    "confidence": "HIGH",
./final_test_78_95.json:3041:    "margin": 0.04840520441532137,
./final_test_78_95.json:3042:    "confidence": "HIGH",
./final_test_78_95.json:3104:    "margin": 0.06663363456726079,
./final_test_78_95.json:3105:    "confidence": "HIGH",
./final_test_78_95.json:3167:    "margin": 0.0563689827919005,
./final_test_78_95.json:3168:    "confidence": "HIGH",
./final_test_78_95.json:3230:    "margin": 0.026986816525459312,
./final_test_78_95.json:3231:    "confidence": "PROBABLE",
./final_test_78_95.json:3293:    "margin": 0.05435425519943238,
./final_test_78_95.json:3294:    "confidence": "HIGH",
./final_test_78_95.json:3356:    "margin": 0.01110450446605682,
./final_test_78_95.json:3357:    "confidence": "NO_MATCH",
./final_test_78_95.json:3358:    "status": "NO_MATCH",
./final_test_78_95.json:3419:    "margin": 0.060913925766944876,
./final_test_78_95.json:3420:    "confidence": "HIGH",
./final_test_78_95.json:3482:    "margin": 0.05434495627880109,
./final_test_78_95.json:3483:    "confidence": "HIGH",
./final_test_78_95.json:3545:    "margin": 0.047714905738830526,
./final_test_78_95.json:3546:    "confidence": "HIGH",
./final_test_78_95.json:3608:    "margin": 0.05786375105381014,
./final_test_78_95.json:3609:    "confidence": "PROBABLE",
./final_test_78_95.json:3671:    "margin": 0.07682474613189705,
./final_test_78_95.json:3672:    "confidence": "HIGH",
./final_test_78_95.json:3734:    "margin": 0.06559846580028528,
./final_test_78_95.json:3735:    "confidence": "HIGH",
./final_test_78_95.json:3797:    "margin": 0.044453635811805836,
./final_test_78_95.json:3798:    "confidence": "HIGH",
./final_test_78_95.json:3860:    "margin": 0.019112910032272334,
./final_test_78_95.json:3861:    "confidence": "PROBABLE",
./final_test_78_95.json:3923:    "margin": 0.06389893352985399,
./final_test_78_95.json:3924:    "confidence": "NO_MATCH",
./final_test_78_95.json:3925:    "status": "NO_MATCH",
./final_test_78_95.json:3986:    "margin": 0.040927788615226834,
./final_test_78_95.json:3987:    "confidence": "HIGH",
./final_test_78_95.json:4049:    "margin": 0.0644290739297867,
./final_test_78_95.json:4050:    "confidence": "HIGH",

================ RECOGNITION FUNCTIONS ================
./app/core/scene_analyzer.py:377:        supplied already calculated by the recognizer.
./app/core/recognizer.py:15:class SceneRecognizer:
./app/core/recognizer.py:17:    Scene Fingerprint v3.3 compact recognizer.
./app/core/recognizer.py:30:        margin to second-best candidate
./app/core/recognizer.py:97:    def recognize_folder(
./app/core/recognizer.py:115:            f"[Recognizer] "
./app/core/recognizer.py:161:                    f"[Recognizer] SKIP "
./app/core/recognizer.py:176:                    f"[Recognizer] SKIP old "
./app/core/recognizer.py:197:            "[Recognizer] Fingerprints: "
./app/core/recognizer.py:256:            f"[Recognizer] CPU workers: "
./app/core/recognizer.py:310:                        f"[Recognizer] SKIP "
./app/core/recognizer.py:395:                        "candidates": [],
./app/core/recognizer.py:432:            # Always use the best available candidate.
./app/core/recognizer.py:435:            # Even a weak candidate is accepted as the best
./app/core/recognizer.py:478:                    "candidates": ranked,
./app/core/recognizer.py:484:    def recognize(
./app/core/recognizer.py:490:        return self.recognize_folder(
./app/main.py:6:from app.core.recognizer import SceneRecognizer
./app/main.py:10:recognizer = SceneRecognizer(settings, embedder, manager)
./app/main.py:19:        recognize_tab = ui.tab("Распознавание")
./app/main.py:38:        with ui.tab_panel(recognize_tab):
./app/main.py:45:            def run_recognition():
./app/main.py:48:                    rows = recognizer.recognize_folder(
./app/main.py:58:                            for c in row["candidates"]:
./app/cli.py:11:from app.core.recognizer import SceneRecognizer
./app/cli.py:124:    # RECOGNIZE
./app/cli.py:127:    recognize_parser = subparsers.add_parser(
./app/cli.py:128:        "recognize",
./app/cli.py:129:        help="Recognize images",
./app/cli.py:132:    recognize_parser.add_argument(
./app/cli.py:137:    recognize_parser.add_argument(
./app/cli.py:141:        help="Number of candidates",
./app/cli.py:144:    recognize_parser.add_argument(
./app/cli.py:151:    recognize_parser.add_argument(
./app/cli.py:158:    recognize_parser.add_argument(
./app/cli.py:165:    recognize_parser.add_argument(
./app/cli.py:225:def print_recognition_result(
./app/cli.py:313:    candidates = result.get(
./app/cli.py:314:        "candidates",
./app/cli.py:318:    if candidates:
./app/cli.py:321:            "TOP CANDIDATES"
./app/cli.py:324:        for index, candidate in enumerate(
./app/cli.py:325:            candidates,
./app/cli.py:330:                f"{candidate['id']:<14} "
./app/cli.py:331:                f"{candidate['score']:.4f}"
./app/cli.py:589:    # RECOGNIZE
./app/cli.py:592:    if args.command == "recognize":
./app/cli.py:613:        recognizer = SceneRecognizer(
./app/cli.py:629:            recognizer.recognize_folder(
./app/ocr/ocr_pipeline.py:40:    def recognize(self, image_path: str | Path) -> list[OCRResult]:
./app/ocr/ocr_pipeline.py:102:    results = ocr.recognize(
./app/ocr/plate_detector.py:69:    candidates = []
./app/ocr/plate_detector.py:109:        candidates.append(
./app/ocr/plate_detector.py:121:    candidates.sort(
./app/ocr/plate_detector.py:129:    for index, candidate in enumerate(candidates):
./app/ocr/plate_detector.py:130:        x, y, w, h = candidate["bbox"]
./app/ocr/plate_detector.py:142:            f"A={candidate['area']:.0f} "
./app/ocr/plate_detector.py:143:            f"R={candidate['aspect']:.2f}"
./app/ocr/plate_detector.py:167:    return candidates
./app/ocr/plate_detector.py:172:        description="Detect white rectangular plate candidates"
./app/ocr/plate_detector.py:182:        default="data/ocr_debug/plate_candidates.jpg",
./app/ocr/plate_detector.py:188:    candidates = detect_white_rectangles(
./app/ocr/plate_detector.py:198:    print(f"Candidates: {len(candidates)}")
./app/ocr/plate_detector.py:200:    for i, candidate in enumerate(candidates, 1):
./app/ocr/plate_detector.py:203:            f"bbox={candidate['bbox']} "
./app/ocr/plate_detector.py:204:            f"area={candidate['area']:.0f} "
./app/ocr/plate_detector.py:205:            f"aspect={candidate['aspect']:.2f} "
./app/ocr/plate_detector.py:206:            f"fill={candidate['fill_ratio']:.2f}"
./backup_v31_fix_20260808_230926/scene_analyzer.py:3:from app.core.recognizer import SceneRecognizer
./backup_v31_fix_20260808_230926/scene_analyzer.py:9:        self.recognizer = SceneRecognizer(
./backup_v31_fix_20260808_230926/scene_analyzer.py:19:        yield from self.recognizer.analyze(
./backup_v31_fix_20260808_230926/recognizer.py:11:class SceneRecognizer:
./backup_v31_fix_20260808_230926/recognizer.py:238:    def recognize_folder(
./backup_v31_fix_20260808_230926/recognizer.py:283:            candidates = []
./backup_v31_fix_20260808_230926/recognizer.py:296:                candidates.append({
./backup_v31_fix_20260808_230926/recognizer.py:301:            candidates.sort(
./backup_v31_fix_20260808_230926/recognizer.py:306:            best = candidates[0]
./backup_v31_fix_20260808_230926/recognizer.py:316:                "candidates": candidates[:top_k],
./backup_v31_fix_20260808_230926/cli.py:10:from app.core.recognizer import SceneRecognizer
./backup_v31_fix_20260808_230926/cli.py:41:        "recognize",
./backup_v31_fix_20260808_230926/cli.py:42:        help="Recognize images against fingerprints",
./backup_v31_fix_20260808_230926/cli.py:116:    # RECOGNIZE
./backup_v31_fix_20260808_230926/cli.py:119:    if args.cmd == "recognize":
./backup_v31_fix_20260808_230926/cli.py:130:        recognizer = SceneRecognizer(
./backup_v31_fix_20260808_230926/cli.py:135:        for result in recognizer.recognize_folder(
./classify_test_results.py:60:            candidate = (
./classify_test_results.py:65:            if not candidate.exists():
./classify_test_results.py:66:                dst = candidate
./classify_test_results.py:79:# CLASSIFY
./classify_final_test.py:65:        candidates = r.get(
./classify_final_test.py:66:            "candidates",
./classify_final_test.py:70:        if candidates:
./classify_final_test.py:71:            best_id = candidates[0].get(
./classify_final_test.py:77:        folder_name = "NO_CANDIDATE"
./classify_final_test.py:124:            candidate = (
./classify_final_test.py:129:            if not candidate.exists():
./classify_final_test.py:130:                destination_file = candidate
./scripts/sort_test_and_report_v2.py:67:        [Recognizer]
./scripts/sort_test_and_report_v2.py:76:        candidate = text[i:]
./scripts/sort_test_and_report_v2.py:79:            obj, end = decoder.raw_decode(candidate)
./scripts/sort_test_and_report_v2.py:90:def run_recognition():
./scripts/sort_test_and_report_v2.py:99:        "recognize",
./scripts/sort_test_and_report_v2.py:133:            f"recognize завершился с кодом {process.returncode}"
./scripts/sort_test_and_report_v2.py:165:        assigned_id = item.get("best_id")
./scripts/sort_test_and_report_v2.py:167:        if not assigned_id:
./scripts/sort_test_and_report_v2.py:170:        destination_dir = OUTPUT_DIR / assigned_id
./scripts/sort_test_and_report_v2.py:177:        counters[assigned_id] += 1
./scripts/sort_test_and_report_v2.py:179:        candidates = item.get("candidates", [])
./scripts/sort_test_and_report_v2.py:184:            "assigned_id": assigned_id,
./scripts/sort_test_and_report_v2.py:196:            "candidate_2": None,
./scripts/sort_test_and_report_v2.py:197:            "candidate_2_score": None,
./scripts/sort_test_and_report_v2.py:198:            "candidate_3": None,
./scripts/sort_test_and_report_v2.py:199:            "candidate_3_score": None,
./scripts/sort_test_and_report_v2.py:200:            "candidate_4": None,
./scripts/sort_test_and_report_v2.py:201:            "candidate_4_score": None,
./scripts/sort_test_and_report_v2.py:202:            "candidate_5": None,
./scripts/sort_test_and_report_v2.py:203:            "candidate_5_score": None,
./scripts/sort_test_and_report_v2.py:206:        if candidates:
./scripts/sort_test_and_report_v2.py:207:            c = candidates[0]
./scripts/sort_test_and_report_v2.py:214:        for n in range(1, min(5, len(candidates))):
./scripts/sort_test_and_report_v2.py:215:            c = candidates[n]
./scripts/sort_test_and_report_v2.py:217:            row[f"candidate_{n+1}"] = c.get("id")
./scripts/sort_test_and_report_v2.py:218:            row[f"candidate_{n+1}_score"] = c.get("score")
./scripts/sort_test_and_report_v2.py:230:def write_reports(rows, counters, recognition_time):
./scripts/sort_test_and_report_v2.py:234:        "assigned_id",
./scripts/sort_test_and_report_v2.py:246:        "candidate_2",
./scripts/sort_test_and_report_v2.py:247:        "candidate_2_score",
./scripts/sort_test_and_report_v2.py:248:        "candidate_3",
./scripts/sort_test_and_report_v2.py:249:        "candidate_3_score",
./scripts/sort_test_and_report_v2.py:250:        "candidate_4",
./scripts/sort_test_and_report_v2.py:251:        "candidate_4_score",
./scripts/sort_test_and_report_v2.py:252:        "candidate_5",
./scripts/sort_test_and_report_v2.py:253:        "candidate_5_score",
./scripts/sort_test_and_report_v2.py:315:        "assigned": dict(counters),
./scripts/make_subfingerprints_v2.py:146:        candidates = [
./scripts/make_subfingerprints_v2.py:152:        if len(candidates) > MAX_CORE:
./scripts/make_subfingerprints_v2.py:153:            candidates = sorted(
./scripts/make_subfingerprints_v2.py:154:                candidates,
./scripts/make_subfingerprints_v2.py:161:        if len(candidates) < MIN_CORE:
./scripts/make_subfingerprints_v2.py:167:            "members": sorted(candidates),
./scripts/make_subfingerprints_v2.py:174:        for i in candidates:
./scripts/benchmark_test_v1.py:86:def run_recognition():
./scripts/benchmark_test_v1.py:93:        "recognize",
./scripts/benchmark_test_v1.py:126:            f"recognize failed: {proc.returncode}"
./scripts/benchmark_test_v1.py:184:        candidates = x.get("candidates", [])
./scripts/benchmark_test_v1.py:188:            for c in candidates[:5]
./scripts/benchmark_test_v1.py:193:            for c in candidates[:5]
./scripts/sort_test_and_report.py:12:RECOGNITION_JSON = Path("/tmp/recognize_test.json")
./scripts/sort_test_and_report.py:22:def load_recognition():
./scripts/sort_test_and_report.py:27:    # [Recognizer] ...
./scripts/sort_test_and_report.py:84:    print("SORT TEST BY FIRST CANDIDATE")
./scripts/sort_test_and_report.py:139:        candidates = item.get("candidates", [])
./scripts/sort_test_and_report.py:144:        # если recognize уже начал их отдавать.
./scripts/sort_test_and_report.py:151:            "assigned_id": address,
./scripts/sort_test_and_report.py:196:        "assigned_id",
./scripts/make_subfingerprints.py:125:    assigned = set()
./scripts/make_subfingerprints.py:128:        assigned.update(g["members"])
./scripts/make_subfingerprints.py:133:        if i in assigned:
./scripts/sort_baseline.py:66:                candidate = dst_dir / f"{stem}__{n}{suffix}"
./scripts/sort_baseline.py:67:                if not candidate.exists():
./scripts/sort_baseline.py:68:                    dst = candidate
./scripts/sort_baseline.py:79:            "assigned_id": best_id,
./scripts/sort_baseline.py:82:                item["candidates"][1]["id"]
./scripts/sort_baseline.py:83:                if len(item.get("candidates", [])) > 1
./scripts/sort_baseline.py:93:                item["candidates"][0].get("global")
./scripts/sort_baseline.py:94:                if item.get("candidates")
./scripts/sort_baseline.py:98:                item["candidates"][0].get("environment")
./scripts/sort_baseline.py:99:                if item.get("candidates")
./scripts/sort_baseline.py:103:                item["candidates"][0].get("color")
./scripts/sort_baseline.py:104:                if item.get("candidates")
./scripts/sort_baseline.py:108:                item["candidates"][0].get("spatial")
./scripts/sort_baseline.py:109:                if item.get("candidates")
./scripts/sort_baseline.py:131:        "rule": "ALWAYS_FIRST_CANDIDATE",
./backup_v31_dynamic_20260808_231245/app/core/scene_analyzer.py:6:    def __init__(self, recognizer):
./backup_v31_dynamic_20260808_231245/app/core/scene_analyzer.py:7:        self.recognizer = recognizer
./backup_v31_dynamic_20260808_231245/app/core/scene_analyzer.py:14:        yield from self.recognizer.analyze(
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py:8:class SceneRecognizer:
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py:140:    def recognize_folder(
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py:189:            candidates = []
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py:199:                    candidates.append({
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py:204:            candidates.sort(
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py:209:            candidates = candidates[:top_k]
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py:211:            if candidates:
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py:212:                best = candidates[0]
./backup_v31_dynamic_20260808_231245/app/core/recognizer.py:223:                "candidates": candidates,
./backup_v31_final_20260808_231056/app/core/scene_analyzer.py:3:from app.core.recognizer import SceneRecognizer
./backup_v31_final_20260808_231056/app/core/scene_analyzer.py:9:        self.recognizer = SceneRecognizer(
./backup_v31_final_20260808_231056/app/core/scene_analyzer.py:19:        yield from self.recognizer.analyze(
./backup_v31_final_20260808_231056/app/core/recognizer.py:11:class SceneRecognizer:
./backup_v31_final_20260808_231056/app/core/recognizer.py:238:    def recognize_folder(
./backup_v31_final_20260808_231056/app/core/recognizer.py:283:            candidates = []
./backup_v31_final_20260808_231056/app/core/recognizer.py:296:                candidates.append({
./backup_v31_final_20260808_231056/app/core/recognizer.py:301:            candidates.sort(
./backup_v31_final_20260808_231056/app/core/recognizer.py:306:            best = candidates[0]
./backup_v31_final_20260808_231056/app/core/recognizer.py:316:                "candidates": candidates[:top_k],
./backup_v31_final_20260808_231056/cli.py:10:from app.core.recognizer import SceneRecognizer
./backup_v31_final_20260808_231056/cli.py:41:        "recognize",
./backup_v31_final_20260808_231056/cli.py:42:        help="Recognize images against fingerprints",
./backup_v31_final_20260808_231056/cli.py:116:    # RECOGNIZE
./backup_v31_final_20260808_231056/cli.py:119:    if args.cmd == "recognize":
./backup_v31_final_20260808_231056/cli.py:130:        recognizer = SceneRecognizer(
./backup_v31_final_20260808_231056/cli.py:135:        for result in recognizer.recognize_folder(
./classify_test.py:12:from app.core.recognizer import SceneRecognizer
./classify_test.py:33:# Existing recognizer settings.
./classify_test.py:288:    recognizer = SceneRecognizer(
./classify_test.py:303:    # Use the existing recognizer.
./classify_test.py:309:        "[Recognizer] Starting recognition..."
./classify_test.py:312:    results = recognizer.recognize_folder(
./classify_test.py:360:    # Classify every image
./classify_test.py:375:            # was skipped by recognizer.
./backup_patch_tokens_20260808_131532/scene_analyzer.py:160:        recognizer/API/GUI code.
./backup_patch_tokens_20260808_131532/recognizer.py:4:class SceneRecognizer:
./backup_patch_tokens_20260808_131532/recognizer.py:10:    def recognize_folder(self, folder, top_k=5, threshold=0.65):
./backup_patch_tokens_20260808_131532/recognizer.py:44:                "candidates": [{"id": i, "score": s} for i, s in ranked],
./app_backup_before_patch/core/scene_analyzer.py:160:        recognizer/API/GUI code.
./app_backup_before_patch/core/recognizer.py:4:class SceneRecognizer:
./app_backup_before_patch/core/recognizer.py:10:    def recognize_folder(self, folder, top_k=5, threshold=0.65):
./app_backup_before_patch/core/recognizer.py:44:                "candidates": [{"id": i, "score": s} for i, s in ranked],
./app_backup_before_patch/main.py:6:from app.core.recognizer import SceneRecognizer
./app_backup_before_patch/main.py:10:recognizer = SceneRecognizer(settings, embedder, manager)
./app_backup_before_patch/main.py:19:        recognize_tab = ui.tab("Распознавание")
./app_backup_before_patch/main.py:38:        with ui.tab_panel(recognize_tab):
./app_backup_before_patch/main.py:45:            def run_recognition():
./app_backup_before_patch/main.py:48:                    rows = recognizer.recognize_folder(
./app_backup_before_patch/main.py:58:                            for c in row["candidates"]:
./app_backup_before_patch/cli.py:7:from app.core.recognizer import SceneRecognizer
./app_backup_before_patch/cli.py:35:    # RECOGNIZE
./app_backup_before_patch/cli.py:38:    recognize = sub.add_parser(
./app_backup_before_patch/cli.py:39:        "recognize",
./app_backup_before_patch/cli.py:40:        help="Recognize images against fingerprints",
./app_backup_before_patch/cli.py:43:    recognize.add_argument("folder")
./app_backup_before_patch/cli.py:45:    recognize.add_argument(
./app_backup_before_patch/cli.py:51:    recognize.add_argument(
./app_backup_before_patch/cli.py:96:    # RECOGNIZE
./app_backup_before_patch/cli.py:99:    if args.cmd == "recognize":
./app_backup_before_patch/cli.py:107:        recognizer = SceneRecognizer(
./app_backup_before_patch/cli.py:113:        results = recognizer.recognize_folder(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 02:51:34

Да, теперь картина понятна.

Главное: **мы находимся в правильном проекте**:

`/home/alexice/projects/scene_fingerprint_mvp_v02`

И у нас действительно сохранилось несколько поколений `recognizer.py`. Это хорошо — можно аккуратно определить, **какая именно версия была до последних оптимизаций**, не ломая текущую v33.

Судя по выводу, особенно важны:

- `app/core/recognizer.py` — текущая версия
- `app/core/recognizer.py.backup_before_optimization`
- `app/core/recognizer.py.backup_before_force_match`
- `app/core/recognizer.py.before_patchfix`
- `app_backup_before_patch/core/recognizer.py`
- `backup_patch_tokens_20260808_131532/recognizer.py`
- `backup_v31_dynamic_...`
- `backup_v31_final_...`

И очень важная находка:

**`backup_before_optimization` и текущий recognizer уже очень похожи**, но текущий содержит дополнительные оптимизации. При этом `backup_before_force_match` отличается логикой принятия кандидата.

Поэтому сейчас **ничего не копируем и не меняем**. Сначала точно выясним, какая версия была нужна.

Выполни вот этот блок — он покажет различия между текущим recognizer и всеми наиболее важными версиями:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "============================================================"
echo " CURRENT vs BACKUP_BEFORE_OPTIMIZATION"
echo "============================================================"
diff -u \
  app/core/recognizer.py.backup_before_optimization \
  app/core/recognizer.py \
  | sed -n '1,260p'

echo
echo "============================================================"
echo " CURRENT vs BACKUP_BEFORE_FORCE_MATCH"
echo "============================================================"
diff -u \
  app/core/recognizer.py.backup_before_force_match \
  app/core/recognizer.py \
  | sed -n '1,260p'

echo
echo "============================================================"
echo " CURRENT vs BEFORE_PATCHFIX"
echo "============================================================"
diff -u \
  app/core/recognizer.py.before_patchfix \
  app/core/recognizer.py \
  | sed -n '1,260p'

echo
echo "============================================================"
echo " CURRENT vs APP_BACKUP_BEFORE_PATCH"
echo "============================================================"
diff -u \
  app_backup_before_patch/core/recognizer.py \
  app/core/recognizer.py \
  | sed -n '1,260p'

echo
echo "============================================================"
echo " CURRENT: IMPORTANT LOGIC"
echo "============================================================"
nl -ba app/core/recognizer.py | sed -n '1,520p'
```

### Что мы ищем

В частности, нам надо установить старую схему:

**DINOv2 → fingerprint v33 → кандидаты → первый кандидат → присвоение адреса**

а не возвращать старый **механизм создания fingerprint** или старый DINOv2.

То есть наша цель:

> **оставить всю нынешнюю оптимизацию, v33, patch/fingerprint инфраструктуру и скорость, но вернуть старую логику выбора результата распознавания.**

Именно поэтому сейчас важно посмотреть `diff`, а не просто взять какой-нибудь `.backup`.

Особенно интересует участок примерно:

```text
candidates.sort(...)
best = candidates[0]
```

против нынешнего участка:

```text
# Always use the best available candidate.
# Even a weak candidate is accepted...
```

Похоже, что последние изменения как раз затронули **правило принятия кандидата**, а это соответствует тому, что мы сейчас хотим вернуть.

Пришли вывод этого блока. После него я скажу **конкретно какой файл/какие строки вернуть**, причём без отката остальных оптимизаций.

---

### 👤 **User** — 2026-08-15 02:52:52

скорее всего это перед оптимизацией

---

### 🤖 **Assistant** — 2026-08-15 02:52:52

Да, **очень похоже, что нужная нам логика — именно `backup_before_optimization`**.

Причём это хорошо совпадает с нашей целью:

- текущую оптимизацию **не откатываем целиком**;
- fingerprint v33 **оставляем**;
- DINOv2 и patch-механику **оставляем**;
- скорость/многопоточность/кэширование **оставляем**;
- возвращаем только **старый алгоритм выбора кандидата** из версии до оптимизации.

Но я бы сейчас не делал `cp backup... recognizer.py`, потому что вместе со старой логикой мы можем случайно вернуть старую реализацию оптимизированных частей.

### Давай точно сравним две версии

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

diff -u \
  app/core/recognizer.py.backup_before_optimization \
  app/core/recognizer.py \
  > /tmp/recognizer_diff.txt

echo "=== DIFF SIZE ==="
wc -l /tmp/recognizer_diff.txt

echo
echo "=== DIFFERENCES ==="
cat /tmp/recognizer_diff.txt
```

Если diff большой — **не надо присылать весь**. Тогда сразу:

```bash
grep -nE \
'^[+-].*(candidate|best|score|threshold|margin|confidence|status|NO_MATCH|sort|rank|accept)' \
/tmp/recognizer_diff.txt
```

### Что я ожидаю увидеть

С высокой вероятностью различие будет примерно в логике:

**старая версия:**

```text
получили кандидатов
        ↓
отсортировали
        ↓
candidates[0]
        ↓
это первый кандидат
        ↓
ему присваиваем адрес
```

А нынешняя версия содержит дополнительную логику:

```text
первый кандидат
        ↓
score
        ↓
margin
        ↓
confidence
        ↓
threshold
        ↓
NO_MATCH / PROBABLE / HIGH
```

И вот **эту часть мы можем вернуть**, не трогая остальную оптимизацию.

Это как раз соответствует тому, что мы обсуждали раньше: **первый кандидат является главным результатом распознавания**, а OCR потом можно использовать как дополнительный механизм для сложных случаев, а не вмешивать его сейчас в основной v33-пайплайн.

Пришли `grep`-вывод — и я покажу, **какие конкретно строки заменить**.

---

### 👤 **User** — 2026-08-15 02:54:27

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

diff -u \
  app/core/recognizer.py.backup_before_optimization \
  app/core/recognizer.py \
  > /tmp/recognizer_diff.txt

echo "=== DIFF SIZE ==="
wc -l /tmp/recognizer_diff.txt

echo
echo "=== DIFFERENCES ==="
cat /tmp/recognizer_diff.txt
=== DIFF SIZE ===
175 /tmp/recognizer_diff.txt

=== DIFFERENCES ===
--- app/core/recognizer.py.backup_before_optimization	2026-08-14 23:56:43.520553773 +0300
+++ app/core/recognizer.py	2026-08-15 00:24:49.418469592 +0300
@@ -1,11 +1,15 @@
 from __future__ import annotations
 
+from concurrent.futures import ThreadPoolExecutor
 from pathlib import Path
 
 import numpy as np
 
 from .image import image_files
-from .scene_analyzer import SceneAnalyzer
+from .scene_analyzer import (
+    CompactDescriptor,
+    SceneAnalyzer,
+)

class SceneRecognizer:
@@ -95,6 +99,8 @@
         folder,
         top_k=5,
         threshold=0.65,
+        workers=6,
+        fingerprints=None,
     ):
         folder = Path(folder)
 
@@ -110,7 +116,18 @@
             f"Query images: {len(paths)}"
         )
 
-        fingerprints = []
+        loaded_fingerprints = []
+
+        # Optional whitelist of fingerprints.
+        # If provided, ONLY these fingerprints are used.
+        if fingerprints is not None:
+            allowed_fingerprints = {
+                str(item).strip()
+                for item in fingerprints
+                if str(item).strip()
+            }
+        else:
+            allowed_fingerprints = None
 
         for metadata in (
             self.manager.list_fingerprints()
@@ -122,6 +139,13 @@
             if not fingerprint_id:
                 continue
 
+            if (
+                allowed_fingerprints is not None
+                and str(fingerprint_id)
+                not in allowed_fingerprints
+            ):
+                continue
+
             try:
                 data = self.manager.load(
                     fingerprint_id
@@ -156,14 +180,14 @@
 
                 continue
 
-            fingerprints.append(
+            loaded_fingerprints.append(
                 (
                     fingerprint_id,
                     data,
                 )
             )
 
-        if not fingerprints:
+        if not loaded_fingerprints:
             raise ValueError(
                 "No compatible v3.3 compact "
                 "fingerprints found."
@@ -173,7 +197,7 @@
             "[Recognizer] Fingerprints: "
             + ", ".join(
                 fp_id
-                for fp_id, _ in fingerprints
+                for fp_id, _ in loaded_fingerprints
             )
         )
 
@@ -195,13 +219,68 @@
 
         results = []
 
+        # Calculate CPU descriptors ONCE per image.
+        # They do not depend on the fingerprint.
+        #
+        # Use CPU workers to process different images in parallel.
+        def calculate_descriptors(path):
+            path = Path(path)
+
+            return (
+                str(path),
+                {
+                    "environment": (
+                        CompactDescriptor.environment(
+                            path
+                        )
+                    ),
+                    "color": (
+                        CompactDescriptor.color(
+                            path
+                        )
+                    ),
+                    "spatial": (
+                        CompactDescriptor.spatial(
+                            path
+                        )
+                    ),
+                },
+            )
+
+        worker_count = max(
+            1,
+            int(workers),
+        )
+
+        print(
+            f"[Recognizer] CPU workers: "
+            f"{worker_count}"
+        )
+
+        with ThreadPoolExecutor(
+            max_workers=worker_count
+        ) as executor:
+
+            descriptor_results = executor.map(
+                calculate_descriptors,
+                paths,
+            )
+
+            query_descriptors = dict(
+                descriptor_results
+            )
+
         for path, query_embedding in zip(
             paths,
             queries,
         ):
             ranked = []
 
-            for fingerprint_id, data in fingerprints:
+            descriptors = query_descriptors[
+                str(path)
+            ]
+
+            for fingerprint_id, data in loaded_fingerprints:
 
                 # First use the analyzer.
                 # This calculates the full v3.3 score.
@@ -209,6 +288,16 @@
                     score = self.analyzer.compare(
                         Path(path),
                         fingerprint_id,
+                        query_global=query_embedding,
+                        query_environment=descriptors[
+                            "environment"
+                        ],
+                        query_color=descriptors[
+                            "color"
+                        ],
+                        query_spatial=descriptors[
+                            "spatial"
+                        ],
                     )
 
                 except (
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -nE \
'^[+-].*(candidate|best|score|threshold|margin|confidence|status|NO_MATCH|sort|rank|accept)' \
/tmp/recognizer_diff.txt
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 02:54:28

Да. Теперь у нас есть **важное подтверждение**.

### Что показал diff

`backup_before_optimization` отличается от текущего `recognizer.py` всего по двум типам изменений:

1. **Оптимизация вычислений**
   - `ThreadPoolExecutor`
   - `workers=6`
   - предварительный расчёт `environment/color/spatial`
   - расчёт дескрипторов **один раз на фотографию**, а не для каждого fingerprint.

2. **Фильтр fingerprints**
   - добавлен параметр `fingerprints=None`
   - возможность ограничить набор используемых слепков.

И главное:

**В diff вообще нет изменений в `candidate / best / score / threshold / margin / confidence / status`.**

То есть наше предположение про `backup_before_optimization` как про версию со старой логикой распознавания **не подтверждается этим сравнением**.

Более того, это очень хорошая новость: **оптимизацию сейчас вообще не надо откатывать**. Судя по diff, текущий `recognizer.py` практически является той же логикой + оптимизация вычислений.

### Где тогда находится изменение алгоритма?

Оно, судя по твоему предыдущему выводу, уже присутствует **в `recognizer.py.backup_before_force_match`**.

Там явно есть:

```text
# Threshold is still an absolute safety gate.
if best_score < threshold:
    status = "NO_MATCH"
```

А в текущем:

```text
# The threshold is NO LONGER a rejection gate.
# available address. The score/confidence are kept
...
# Always use the best available candidate.
# Even a weak candidate is accepted as the best
```

**Вот это и есть изменение алгоритма, которое мы искали.**

То есть структура сейчас выглядит так:

```text
backup_before_optimization
        │
        ├── старая логика распознавания
        │
        └── без последних оптимизаций
                 ↓
           текущий recognizer
                 │
                 ├── та же логика
                 ├── + CPU parallelization
                 ├── + precomputed descriptors
                 └── + fingerprint whitelist
```

А:

```text
backup_before_force_match
        │
        └── версия ДО изменения правила
            "всегда брать первого кандидата"
```

### Поэтому сейчас ничего менять не надо

Нам нужно посмотреть **точный diff `backup_before_force_match` → текущий**. Именно там, скорее всего, находится изменение, которое мы хотим частично вернуть.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

diff -u \
  app/core/recognizer.py.backup_before_force_match \
  app/core/recognizer.py \
  > /tmp/force_match_diff.txt

echo "=== DIFF SIZE ==="
wc -l /tmp/force_match_diff.txt

echo
echo "=== FORCE MATCH DIFFERENCES ==="
cat /tmp/force_match_diff.txt
```

**Вот этот diff сейчас самый важный.**

После него мы сможем сделать именно то, что ты хотел изначально:

**оставить всю текущую оптимизацию v33, но вернуть старое правило распознавания.**

И пока ничего не копируй и не редактируй.

---

### 👤 **User** — 2026-08-15 02:55:23

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

diff -u \
  app/core/recognizer.py.backup_before_force_match \
  app/core/recognizer.py \
  > /tmp/force_match_diff.txt

echo "=== DIFF SIZE ==="
wc -l /tmp/force_match_diff.txt

echo
echo "=== FORCE MATCH DIFFERENCES ==="
cat /tmp/force_match_diff.txt
=== DIFF SIZE ===
200 /tmp/force_match_diff.txt

=== FORCE MATCH DIFFERENCES ===
--- app/core/recognizer.py.backup_before_force_match	2026-08-14 23:39:54.005949318 +0300
+++ app/core/recognizer.py	2026-08-15 00:24:49.418469592 +0300
@@ -1,11 +1,15 @@
 from __future__ import annotations
 
+from concurrent.futures import ThreadPoolExecutor
 from pathlib import Path
 
 import numpy as np
 
 from .image import image_files
-from .scene_analyzer import SceneAnalyzer
+from .scene_analyzer import (
+    CompactDescriptor,
+    SceneAnalyzer,
+)

class SceneRecognizer:
@@ -95,6 +99,8 @@
         folder,
         top_k=5,
         threshold=0.65,
+        workers=6,
+        fingerprints=None,
     ):
         folder = Path(folder)
 
@@ -110,7 +116,18 @@
             f"Query images: {len(paths)}"
         )
 
-        fingerprints = []
+        loaded_fingerprints = []
+
+        # Optional whitelist of fingerprints.
+        # If provided, ONLY these fingerprints are used.
+        if fingerprints is not None:
+            allowed_fingerprints = {
+                str(item).strip()
+                for item in fingerprints
+                if str(item).strip()
+            }
+        else:
+            allowed_fingerprints = None
 
         for metadata in (
             self.manager.list_fingerprints()
@@ -122,6 +139,13 @@
             if not fingerprint_id:
                 continue
 
+            if (
+                allowed_fingerprints is not None
+                and str(fingerprint_id)
+                not in allowed_fingerprints
+            ):
+                continue
+
             try:
                 data = self.manager.load(
                     fingerprint_id
@@ -156,14 +180,14 @@
 
                 continue
 
-            fingerprints.append(
+            loaded_fingerprints.append(
                 (
                     fingerprint_id,
                     data,
                 )
             )
 
-        if not fingerprints:
+        if not loaded_fingerprints:
             raise ValueError(
                 "No compatible v3.3 compact "
                 "fingerprints found."
@@ -173,7 +197,7 @@
             "[Recognizer] Fingerprints: "
             + ", ".join(
                 fp_id
-                for fp_id, _ in fingerprints
+                for fp_id, _ in loaded_fingerprints
             )
         )
 
@@ -195,13 +219,68 @@
 
         results = []
 
+        # Calculate CPU descriptors ONCE per image.
+        # They do not depend on the fingerprint.
+        #
+        # Use CPU workers to process different images in parallel.
+        def calculate_descriptors(path):
+            path = Path(path)
+
+            return (
+                str(path),
+                {
+                    "environment": (
+                        CompactDescriptor.environment(
+                            path
+                        )
+                    ),
+                    "color": (
+                        CompactDescriptor.color(
+                            path
+                        )
+                    ),
+                    "spatial": (
+                        CompactDescriptor.spatial(
+                            path
+                        )
+                    ),
+                },
+            )
+
+        worker_count = max(
+            1,
+            int(workers),
+        )
+
+        print(
+            f"[Recognizer] CPU workers: "
+            f"{worker_count}"
+        )
+
+        with ThreadPoolExecutor(
+            max_workers=worker_count
+        ) as executor:
+
+            descriptor_results = executor.map(
+                calculate_descriptors,
+                paths,
+            )
+
+            query_descriptors = dict(
+                descriptor_results
+            )
+
         for path, query_embedding in zip(
             paths,
             queries,
         ):
             ranked = []
 
-            for fingerprint_id, data in fingerprints:
+            descriptors = query_descriptors[
+                str(path)
+            ]
+
+            for fingerprint_id, data in loaded_fingerprints:
 
                 # First use the analyzer.
                 # This calculates the full v3.3 score.
@@ -209,6 +288,16 @@
                     score = self.analyzer.compare(
                         Path(path),
                         fingerprint_id,
+                        query_global=query_embedding,
+                        query_environment=descriptors[
+                            "environment"
+                        ],
+                        query_color=descriptors[
+                            "color"
+                        ],
+                        query_spatial=descriptors[
+                            "spatial"
+                        ],
                     )
 
                 except (
@@ -340,12 +429,20 @@
                 )
             )
 
-            # Threshold is still an absolute safety gate.
+            # Always use the best available candidate.
+            #
+            # The threshold is NO LONGER a rejection gate.
+            # Even a weak candidate is accepted as the best
+            # available address. The score/confidence are kept
+            # for diagnostics.
+            best_id = best["id"]
+
             if best_score < threshold:
-                best_id = None
-                status = "NO_MATCH"
+                status = "FORCED_MATCH"
             else:
-                best_id = best["id"]
+                status = self._status_from_confidence(
+                    confidence
+                )
 
             results.append(
                 {
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 02:55:24

Вот теперь **точно нашли нужное изменение**.

И оно очень небольшое. В `backup_before_force_match` и текущем `recognizer.py` вся оптимизация отличается отдельно, а изменение алгоритма распознавания — буквально этот блок:

**Было:**

```python
# Threshold is still an absolute safety gate.
if best_score < threshold:
    best_id = None
    status = "NO_MATCH"
else:
    best_id = best["id"]
    status = self._status_from_confidence(
        confidence
    )
```

**Сейчас:**

```python
# Always use the best available candidate.
#
# The threshold is NO LONGER a rejection gate.
# Even a weak candidate is accepted as the best
# available address. The score/confidence are kept
# for diagnostics.
best_id = best["id"]

if best_score < threshold:
    status = "FORCED_MATCH"
else:
    status = self._status_from_confidence(
        confidence
    )
```

То есть мы можем **вернуть старое поведение без отката оптимизации вообще**.

### Что это даст

Будет снова:

```text
лучший кандидат
      ↓
score >= threshold?
      ├── ДА → присваиваем адрес
      │
      └── НЕТ → NO_MATCH
```

Вместо нынешнего:

```text
лучший кандидат
      ↓
в любом случае присваиваем его адрес
      ↓
если score низкий → FORCED_MATCH
```

Это как раз соответствует нашей предыдущей логике **«первый кандидат — основной кандидат»**, но с сохранением защитного порога.

При этом мы **не трогаем**:

- `ThreadPoolExecutor`
- `workers=6`
- предварительный расчёт `environment`
- предварительный расчёт `color`
- предварительный расчёт `spatial`
- `fingerprints=...`
- текущий v33
- текущий `SceneAnalyzer`
- текущий DINOv2
- patch/fingerprint формат.

### Я предлагаю сейчас сделать безопасно

Сначала создаём резервную копию **текущего рабочего recognizer**, затем меняем только эти строки.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp app/core/recognizer.py \
   app/core/recognizer.py.before_restore_old_matching_$(date +%Y%m%d_%H%M%S)

python - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
s = p.read_text()

old = '''            # Always use the best available candidate.
            #
            # The threshold is NO LONGER a rejection gate.
            # Even a weak candidate is accepted as the best
            # available address. The score/confidence are kept
            # for diagnostics.
            best_id = best["id"]

            if best_score < threshold:
                status = "FORCED_MATCH"
            else:
                status = self._status_from_confidence(
                    confidence
                )
'''

new = '''            # Threshold is still an absolute safety gate.
            if best_score < threshold:
                best_id = None
                status = "NO_MATCH"
            else:
                best_id = best["id"]
                status = self._status_from_confidence(
                    confidence
                )
'''

if old not in s:
    raise SystemExit("ERROR: target block was not found; nothing changed")

p.write_text(s.replace(old, new, 1))

print("OK: old matching logic restored")
PY
```

После этого **не запускаем сразу большое распознавание**.

Сначала проверим, что изменился только нужный блок:

```bash
git diff --no-index \
  app/core/recognizer.py.backup_before_force_match \
  app/core/recognizer.py \
  | tail -n 70
```

Но здесь есть нюанс: поскольку `backup_before_force_match` ещё без оптимизаций, diff всё равно покажет большой блок оптимизаций. Поэтому лучше проверить именно участок:

```bash
nl -ba app/core/recognizer.py | sed -n '410,455p'
```

Там должно быть старое:

```text
Threshold is still an absolute safety gate.
...
best_id = None
status = "NO_MATCH"
```

**После этого уже прогоняем тест 78–95.** Это будет очень хороший контрольный тест: мы одновременно проверим, что v33 + оптимизация работают, но при этом старое правило `NO_MATCH` восстановлено.

---

### 👤 **User** — 2026-08-15 02:56:41

давай тогда еще раз прогоним тест и изучим почему слишком много ошибок сейчас

---

### 🤖 **Assistant** — 2026-08-15 02:56:41

Да. И я бы сейчас **не просто прогнал тест, а сделал диагностический прогон**, чтобы понять, откуда берётся большой процент ошибок.

После восстановления старой логики сначала проверь, что блок действительно изменился:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nl -ba app/core/recognizer.py | sed -n '420,455p'
```

Если там `best_id = None` и `status = "NO_MATCH"` — запускаем контрольный тест 78–95.

### 1. Запускаем распознавание 78–95

У нас уже есть `final_test_78_95.json`, поэтому лучше **не перезаписывать его**.

Сначала посмотрим, какие скрипты для этого у нас есть:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

ls -lh \
  classify_test.py \
  classify_final_test.py \
  classify_test_results.py \
  scripts/sort_test_and_report.py \
  scripts/sort_test_and_report_v2.py \
  scripts/benchmark_test_v1.py \
  2>/dev/null
```

И отдельно:

```bash
grep -nE \
'data/input|78|95|fingerprints|threshold|top.k|final_test|recognize' \
classify_test.py \
classify_final_test.py \
scripts/benchmark_test_v1.py \
scripts/sort_test_and_report_v2.py \
2>/dev/null | head -n 250
```

**Пришли этот вывод.**

Я хочу использовать именно тот тест, которым мы уже получили `final_test_78_95.json`, чтобы сравнение было честным.

---

### 2. Что будем анализировать

После прогона нас интересуют не только `HIGH / PROBABLE / NO_MATCH`.

Для **каждой ошибочно определённой фотографии** нам нужны:

```text
реальный адрес
↓
1-й кандидат + score
2-й кандидат + score
3-й кандидат + score
margin
global
environment
color
spatial
confidence
```

Особенно важно увидеть ситуации типа:

```text
REAL: 83
1: 81   0.71
2: 83   0.70
```

и:

```text
REAL: 83
1: 83   0.58
2: 81   0.57
```

Это **совершенно разные проблемы**.

В первом случае алгоритм действительно ошибается на первом кандидате.

Во втором — правильный адрес есть среди кандидатов, но недостаточно хорошо отделяется от соседнего.

---

### И ещё важный момент

В твоём предыдущем `final_test_78_95.json` уже были признаки, что проблема **не только в threshold**:

- были `HIGH`;
- были `PROBABLE`;
- были `AMBIGUOUS`;
- были `NO_MATCH`;
- при этом некоторые `NO_MATCH` имели вполне приличный `score`, но маленький `margin`.

Например, у тебя уже встречался случай примерно:

```text
margin = 0.0014
confidence = AMBIGUOUS
```

То есть нам надо выяснить:

**ошибается сам первый кандидат или правильный кандидат находится вторым/третьим?**

Это принципиально важно для следующего шага.

Сначала пришли вывод двух команд выше — после этого дадим **одну точную команду запуска контрольного теста 78–95**, а затем разберём ошибки по категориям.

---

### 👤 **User** — 2026-08-15 02:57:43

#
            # The threshold is NO LONGER a rejection gate.
            # Even a weak candidate is accepted as the best
            # available address. The score/confidence are kept
            # for diagnostics.
            best_id = best["id"]

            if best_score < threshold:
                status = "FORCED_MATCH"
            else:
                status = self._status_from_confidence(
PYint("OK: old matching logic restored")k was not found; nothing changed")
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 02:57:44

Да, здесь всё понятно: **ничего не изменилось**.

Причина первая — команда `python` у тебя отсутствует в системном PATH. В проекте мы используем **`uv run`**, поэтому лучше вообще не трогать системный Python.

Причина вторая — сообщение `target block was not found` означает, что Python-скрипт даже не дошёл до изменения файла. То есть текущий `recognizer.py` остался прежним.

Давай сделаем безопаснее: **не будем искать весь блок целиком**, а заменим только конкретный участок через `uv run`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp app/core/recognizer.py \
   app/core/recognizer.py.before_restore_old_matching_$(date +%Y%m%d_%H%M%S)

uv run python - <<'PY'
from pathlib import Path

p = Path("app/core/recognizer.py")
s = p.read_text()

old = '''            best_id = best["id"]

            if best_score < threshold:
                status = "FORCED_MATCH"
            else:
                status = self._status_from_confidence(
                    confidence
                )
'''

new = '''            if best_score < threshold:
                best_id = None
                status = "NO_MATCH"
            else:
                best_id = best["id"]
                status = self._status_from_confidence(
                    confidence
                )
'''

if old not in s:
    print("ERROR: target block not found")
    print("Showing actual section:")
    lines = s.splitlines()
    for i, line in enumerate(lines, 1):
        if "best_id = best" in line:
            for n in range(max(1, i-8), min(len(lines), i+15)+1):
                print(f"{n:4}: {lines[n-1]}")
    raise SystemExit(1)

p.write_text(s.replace(old, new, 1))
print("OK: old matching logic restored")
PY
```

После этого сразу:

```bash
nl -ba app/core/recognizer.py | sed -n '425,455p'
```

Должно получиться примерно:

```text
if best_score < threshold:
    best_id = None
    status = "NO_MATCH"
else:
    best_id = best["id"]
    status = self._status_from_confidence(
        confidence
    )
```

### Важное

**Оптимизация при этом останется.** Мы меняем только правило:

`FORCED_MATCH → NO_MATCH`

То есть не откатываем `ThreadPoolExecutor`, `workers=6`, предварительный расчёт дескрипторов и whitelist fingerprint.

После проверки этого блока **сразу прогоним 78–95 и сравним с предыдущим `final_test_78_95.json`**. Тогда уже будем разбирать, почему возникли ошибки: неправильный первый кандидат, маленький margin, плохой score или проблема конкретных адресов.

---

### 👤 **User** — 2026-08-15 02:58:09

давай прогон

---

### 🤖 **Assistant** — 2026-08-15 02:58:12

Да. Давай сразу запускаем **тот же контрольный тест 78–95**, чтобы сравнение с предыдущим результатом было корректным.

Сначала проверим, что старая логика действительно восстановлена:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nl -ba app/core/recognizer.py | sed -n '425,455p'
```

Если там:

```text
best_id = None
status = "NO_MATCH"
```

то запускай:

```bash
uv run python classify_final_test.py
```

Если скрипт ожидает параметры или выдаст ошибку — **ничего не исправляй**, просто пришли вывод.

После завершения получим новый результат и сравним его с:

```text
final_test_78_95.json
```

Особенно нас будут интересовать:

1. сколько всего фотографий;
2. сколько правильно определено;
3. сколько `NO_MATCH`;
4. сколько неправильных первых кандидатов;
5. случаи, где **правильный адрес был кандидатом №2–5**;
6. средний `score` правильного и неправильного кандидата;
7. `margin`.

Именно пункт **№5** сейчас наиболее интересен: если правильный адрес часто находится вторым, значит проблема не в fingerprint, а в механизме выбора первого кандидата.

---

### 👤 **User** — 2026-08-15 03:00:49

FINAL TOP-1 CLASSIFICATION
======================================================================
78_v33                 20
79_v33                  8
80_v33                  8
81_v33                 16
82_v33                  9
83_v33                 18
84_v33                  8
85_v33                 17
86_v33_fast            15
87_v33_fast            20
88_v33_fast            16
89_v33_fast            20
90_v33_fast             3
91_v33_fast            13
92_v33_fast            18
93_v33_fast            12
94_v33_fast            24
95_v33_fast            17

TOTAL COPIED: 262
OUTPUT: data/output/test_classified
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:00:51

> **Remembering**
>
>
> **Reviewed fingerprint results and diagnosed recognition errors**
>
> 
>
> Worked for 4s

Отлично. **Тест реально отработал**: 262 фотографии распределены по 78-95.

Но по одной этой сводке пока нельзя сказать, сколько ошибок - это **раскладка по результату**, а не сравнение с правильным адресом.

Зато сейчас можем сделать гораздо полезнее: **автоматически сравнить фактический адрес каждой фотографии с тем, куда она попала**, и отдельно посмотреть случаи, где правильный адрес был среди кандидатов.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== TEST INPUT ==="
find data/input/test -type f 2>/dev/null | wc -l

echo
echo "=== CLASSIFIED ==="
find data/output/test_classified -type f | wc -l

echo
echo "=== OUTPUT DISTRIBUTION ==="
find data/output/test_classified -mindepth 1 -maxdepth 1 -type d -printf '%f\n' \
  | sort -V \
  | while read d; do
      printf "%-20s %s\n" "$d" "$(find "data/output/test_classified/$d" -type f | wc -l)"
    done
```

Но **главное сейчас - найти JSON текущего прогона**. Выполни:

```bash
echo
echo "=== JSON REPORTS ==="
find data . -maxdepth 3 -type f -name '*.json' \
  -printf '%TY-%Tm-%Td %TH:%TM:%TS %p\n' \
  2>/dev/null | sort -r | head -20
```

И:

```bash
echo
echo "=== SORT SCRIPT ==="
sed -n '1,360p' scripts/sort_test_and_report_v2.py
```

Почему это важно: твой результат показывает, например:

- 78 → 20
- 83 → 18
- 94 → 24
- 90 → всего 3

Но это **не обязательно ошибки**. Нужно знать, сколько фотографий реально принадлежит каждому адресу.

После этого мы сможем построить настоящую матрицу:

```text
             ПРЕДСКАЗАНО
REAL       78  79  80  81 ... 95
78         20   0   0   0
79          0   8   0   0
80          0   0   8   0
...
```

И тогда сразу станет видно, **какие адреса путаются между собой**.

Особенно хочу проверить 90: если у него реально должно быть, например, 20 фотографий, а система дала только 3, то посмотрим **куда ушли остальные 17**. Это уже непосредственно покажет источник ошибок.

---

### 👤 **User** — 2026-08-15 03:01:40

"margin",
        "confidence",
        "status",
        "best_image",
        "best_image_score",
        "global",
        "environment",
        "color",
        "spatial",
        "candidate_2",
        "candidate_2_score",
        "candidate_3",
        "candidate_3_score",
        "candidate_4",
        "candidate_4_score",
        "candidate_5",
        "candidate_5_score",
    ]

    with open(REPORT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    scores = [
        float(x["score"])
        for x in rows
        if x["score"] is not None
    ]

    margins = [
        float(x["margin"])
        for x in rows
        if x["margin"] is not None
    ]

    status_counter = Counter(
        x["status"]
        for x in rows
        if x["status"]
    )

    confidence_counter = Counter(
        x["confidence"]
        for x in rows
        if x["confidence"]
    )

    process = psutil.Process(os.getpid())

    stats = {
        "total_images": len(rows),

        "recognition_time_seconds": recognition_time,

        "images_per_second":
            len(rows) / recognition_time
            if recognition_time > 0 else None,

        "milliseconds_per_image":
            recognition_time * 1000 / len(rows)
            if rows else None,

        "score": {
            "min": min(scores) if scores else None,
            "mean": sum(scores) / len(scores) if scores else None,
            "max": max(scores) if scores else None,
        },

        "margin": {
            "min": min(margins) if margins else None,
            "mean": sum(margins) / len(margins) if margins else None,
            "max": max(margins) if margins else None,
        },

        "status": dict(status_counter),
        "confidence": dict(confidence_counter),

        "assigned": dict(counters),

        "cpu": {
            "logical_cpus": psutil.cpu_count(),
            "process_cpu_percent": process.cpu_percent(interval=0.5),
        },

        "ram": {
            "total_mb":
                psutil.virtual_memory().total / 1024 / 1024,

            "used_mb":
                psutil.virtual_memory().used / 1024 / 1024,

            "available_mb":
                psutil.virtual_memory().available / 1024 / 1024,

            "process_rss_mb":
                process.memory_info().rss / 1024 / 1024,
        },

        "gpu": gpu_stats(),
    }

    REPORT_JSON.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    STATISTICS_JSON.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return stats

def main():
    print()
    print("=" * 80)
    print("SCENE FINGERPRINT TEST SORTER V2")
    print("=" * 80)

    if not INPUT_DIR.exists():
        raise RuntimeError(f"Нет папки: {INPUT_DIR}")

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

