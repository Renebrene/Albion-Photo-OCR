## СЕССИЯ: Branch · готовая

**Создано:** 2026-08-16 00:03:27
**Обновлено:** 2026-08-19 17:08:07
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d41d-8908-83ea-b688-e34e85acfaa9](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d41d-8908-83ea-b688-e34e85acfaa9)

---

### 👤 **User** — 2026-08-15 15:28:03

================================================================================
=== dry_run_best_sequence.py ===
================================================================================
     1	#!/usr/bin/env python3
     2	
     3	import csv
     4	import re
     5	from pathlib import Path
     6	
     7	
     8	PROJECT = Path(__file__).resolve().parent.parent
     9	
    10	CSV_PATH = (
    11	    PROJECT
    12	    / "output/benchmark_components/full_analysis/margin_best.csv"
    13	)
    14	
    15	INPUT_DIR = PROJECT / "data/input/test"
    16	
    17	# Смотрим немного шире старого порога 0.005.
    18	MARGIN_LIMIT = 0.020
    19	
    20	# Соседи слева/справа.
    21	NEIGHBOR_RADIUS = 2
    22	
    23	# Минимальная уверенность соседа.
    24	NEIGHBOR_SCORE_MIN = 0.80
    25	
    26	# BEST должен выигрывать хотя бы на столько,
    27	# чтобы считать его убедительным.
    28	BEST_STRONG_DIFF = 0.05
    29	
    30	IMAGE_EXTENSIONS = {
    31	    ".jpg",
    32	    ".jpeg",
    33	    ".JPG",
    34	    ".JPEG",
    35	    ".png",
    36	    ".PNG",
    37	}
    38	
    39	
    40	def natural_key(path):
    41	    parts = re.split(r"(\d+)", path.name)
    42	
    43	    return [
    44	        int(x) if x.isdigit() else x.lower()
    45	        for x in parts
    46	    ]
    47	
    48	
    49	def ffloat(value):
    50	    try:
    51	        return float(value)
    52	    except Exception:
    53	        return None
    54	
    55	
    56	def load_files():
    57	    files = [
    58	        p
    59	        for p in INPUT_DIR.iterdir()
    60	        if p.is_file()
    61	        and p.suffix in IMAGE_EXTENSIONS
    62	    ]
    63	
    64	    files.sort(key=natural_key)
    65	
    66	    return files
    67	
    68	
    69	def load_results():
    70	
    71	    results = {}
    72	
    73	    with CSV_PATH.open(
    74	        "r",
    75	        encoding="utf-8-sig",
    76	        newline="",
    77	    ) as f:
    78	
    79	        for row in csv.DictReader(f):
    80	            results[row["image"]] = row
    81	
    82	    return results
    83	
    84	
    85	def get_neighbors(files, results, index):
    86	
    87	    neighbors = []
    88	
    89	    for delta in range(
    90	        -NEIGHBOR_RADIUS,
    91	        NEIGHBOR_RADIUS + 1,
    92	    ):
    93	
    94	        if delta == 0:
    95	            continue
    96	
    97	        pos = index + delta
    98	
    99	        if pos < 0 or pos >= len(files):
   100	            continue
   101	
   102	        p = files[pos]
   103	
   104	        r = results.get(p.name)
   105	
   106	        if not r:
   107	            continue
   108	
   109	        neighbor_id = r.get(
   110	            "current_first",
   111	            "",
   112	        )
   113	
   114	        score = ffloat(
   115	            r.get("final_first")
   116	        )
   117	
   118	        margin = ffloat(
   119	            r.get("final_margin")
   120	        )
   121	
   122	        neighbors.append({
   123	            "delta": delta,
   124	            "image": p.name,
   125	            "id": neighbor_id,
   126	            "score": score,
   127	            "margin": margin,
   128	        })
   129	
   130	    return neighbors
   131	
   132	
   133	def main():
   134	
   135	    print("=" * 80)
   136	    print("DRY RUN: BEST + SEQUENCE")
   137	    print("=" * 80)
   138	
   139	    print("CSV:", CSV_PATH)
   140	    print("INPUT:", INPUT_DIR)
   141	    print("MARGIN LIMIT:", MARGIN_LIMIT)
   142	    print("BEST STRONG DIFF:", BEST_STRONG_DIFF)
   143	    print("NEIGHBOR RADIUS:", NEIGHBOR_RADIUS)
   144	    print()
   145	
   146	    if not CSV_PATH.exists():
   147	        raise FileNotFoundError(CSV_PATH)
   148	
   149	    if not INPUT_DIR.exists():
   150	        raise FileNotFoundError(INPUT_DIR)
   151	
   152	    files = load_files()
   153	    results = load_results()
   154	
   155	    print(f"Images:     {len(files)}")
   156	    print(f"Recognized: {len(results)}")
   157	    print()
   158	
   159	    checked = 0
   160	    best_changes = 0
   161	    sequence_changes = 0
   162	    ambiguous = 0
   163	    kept = 0
   164	
   165	    print("=" * 80)
   166	    print("SUSPICIOUS FRAMES")
   167	    print("=" * 80)
   168	
   169	    for index, path in enumerate(files):
   170	
   171	        r = results.get(path.name)
   172	
   173	        if not r:
   174	            continue
   175	
   176	        margin = ffloat(
   177	            r.get("final_margin")
   178	        )
   179	
   180	        if margin is None:
   181	            continue
   182	
   183	        if margin >= MARGIN_LIMIT:
   184	            continue
   185	
   186	        checked += 1
   187	
   188	        first = r.get(
   189	            "current_first",
   190	            "",
   191	        )
   192	
   193	        second = r.get(
   194	            "current_second",
   195	            "",
   196	        )
   197	
   198	        first_score = ffloat(
   199	            r.get("final_first")
   200	        )
   201	
   202	        second_score = ffloat(
   203	            r.get("final_second")
   204	        )
   205	
   206	        best_first = ffloat(
   207	            r.get("best_first")
   208	        )
   209	
   210	        best_second = ffloat(
   211	            r.get("best_second")
   212	        )
   213	
   214	        best_diff = ffloat(
   215	            r.get("best_diff")
   216	        )
   217	
   218	        neighbors = get_neighbors(
   219	            files,
   220	            results,
   221	            index,
   222	        )
   223	
   224	        # --------------------------------------------------
   225	        # BEST
   226	        # --------------------------------------------------
   227	
   228	        best_decision = None
   229	        best_reason = ""
   230	
   231	        if (
   232	            best_diff is not None
   233	            and best_diff >= BEST_STRONG_DIFF
   234	        ):
   235	
   236	            best_decision = second
   237	
   238	            best_reason = (
   239	                "BEST strongly supports TOP2"
   240	            )
   241	
   242	        elif (
   243	            best_diff is not None
   244	            and best_diff <= -BEST_STRONG_DIFF
   245	        ):
   246	
   247	            best_decision = first
   248	
   249	            best_reason = (
   250	                "BEST strongly supports TOP1"
   251	            )
   252	
   253	        else:
   254	
   255	            best_reason = (
   256	                "BEST inconclusive"
   257	            )
   258	
   259	        # --------------------------------------------------
   260	        # SEQUENCE
   261	        # --------------------------------------------------
   262	
   263	        neighbor_first_votes = []
   264	        neighbor_second_votes = []
   265	
   266	        for n in neighbors:
   267	
   268	            if (
   269	                n["score"] is not None
   270	                and n["score"] < NEIGHBOR_SCORE_MIN
   271	            ):
   272	                continue
   273	
   274	            if n["id"] == first:
   275	                neighbor_first_votes.append(n)
   276	
   277	            if n["id"] == second:
   278	                neighbor_second_votes.append(n)
   279	
   280	        sequence_decision = None
   281	        sequence_reason = ""
   282	
   283	        if (
   284	            len(neighbor_first_votes)
   285	            >= 2
   286	        ):
   287	
   288	            sequence_decision = first
   289	
   290	            sequence_reason = (
   291	                "neighbors strongly support TOP1"
   292	            )
   293	
   294	        elif (
   295	            len(neighbor_second_votes)
   296	            >= 2
   297	        ):
   298	
   299	            sequence_decision = second
   300	
   301	            sequence_reason = (
   302	                "neighbors strongly support TOP2"
   303	            )
   304	
   305	        else:
   306	
   307	            sequence_reason = (
   308	                "sequence inconclusive"
   309	            )
   310	
   311	        # --------------------------------------------------
   312	        # FINAL PROPOSED DECISION
   313	        #
   314	        # PRIORITY:
   315	        #
   316	        # 1. Strong BEST
   317	        # 2. Strong sequence
   318	        # 3. Keep TOP1
   319	        #
   320	        # This is DRY RUN only.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:28:03

Да, вижу, где мы остановились. Сейчас у тебя открыт `dry_run_best_sequence.py`, и по коду логика такая:

1. Берём только кадры с `final_margin < 0.020`.
2. Для каждого такого кадра смотрим:
   - `TOP1` / `TOP2`;
   - насколько `BEST` поддерживает один из них (`best_diff`);
   - соседей в диапазоне ±2 кадров.
3. Сильный `BEST` имеет приоритет.
4. Затем сильная последовательность соседей.
5. Если оба метода неубедительны - остаётся исходный `TOP1`.
6. Это пока **DRY RUN**, то есть реальные результаты не изменяет.

Но файл у тебя показан только до строки 320 - конец функции `main()` отсутствует. Поэтому прежде чем что-либо менять, я бы **не трогал алгоритм**, а сначала посмотрел оставшуюся часть файла.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nl -ba scripts/dry_run_best_sequence.py | sed -n '315,430p'
```

И пришли вывод.

После этого проверим именно текущую реализацию, **не ломая v33 и существующую оптимизацию**.

---

### 👤 **User** — 2026-08-15 15:28:29

=== dry_run_best_sequence.py ===
================================================================================
     1	#!/usr/bin/env python3
     2	
     3	import csv
     4	import re
     5	from pathlib import Path
     6	
     7	
     8	PROJECT = Path(__file__).resolve().parent.parent
     9	
    10	CSV_PATH = (
    11	    PROJECT
    12	    / "output/benchmark_components/full_analysis/margin_best.csv"
    13	)
    14	
    15	INPUT_DIR = PROJECT / "data/input/test"
    16	
    17	# Смотрим немного шире старого порога 0.005.
    18	MARGIN_LIMIT = 0.020
    19	
    20	# Соседи слева/справа.
    21	NEIGHBOR_RADIUS = 2
    22	
    23	# Минимальная уверенность соседа.
    24	NEIGHBOR_SCORE_MIN = 0.80
    25	
    26	# BEST должен выигрывать хотя бы на столько,
    27	# чтобы считать его убедительным.
    28	BEST_STRONG_DIFF = 0.05
    29	
    30	IMAGE_EXTENSIONS = {
    31	    ".jpg",
    32	    ".jpeg",
    33	    ".JPG",
    34	    ".JPEG",
    35	    ".png",
    36	    ".PNG",
    37	}
    38	
    39	
    40	def natural_key(path):
    41	    parts = re.split(r"(\d+)", path.name)
    42	
    43	    return [
    44	        int(x) if x.isdigit() else x.lower()
    45	        for x in parts
    46	    ]
    47	
    48	
    49	def ffloat(value):
    50	    try:
    51	        return float(value)
    52	    except Exception:
    53	        return None
    54	
    55	
    56	def load_files():
    57	    files = [
    58	        p
    59	        for p in INPUT_DIR.iterdir()
    60	        if p.is_file()
    61	        and p.suffix in IMAGE_EXTENSIONS
    62	    ]
    63	
    64	    files.sort(key=natural_key)
    65	
    66	    return files
    67	
    68	
    69	def load_results():
    70	
    71	    results = {}
    72	
    73	    with CSV_PATH.open(
    74	        "r",
    75	        encoding="utf-8-sig",
    76	        newline="",
    77	    ) as f:
    78	
    79	        for row in csv.DictReader(f):
    80	            results[row["image"]] = row
    81	
    82	    return results
    83	
    84	
    85	def get_neighbors(files, results, index):
    86	
    87	    neighbors = []
    88	
    89	    for delta in range(
    90	        -NEIGHBOR_RADIUS,
    91	        NEIGHBOR_RADIUS + 1,
    92	    ):
    93	
    94	        if delta == 0:
    95	            continue
    96	
    97	        pos = index + delta
    98	
    99	        if pos < 0 or pos >= len(files):
   100	            continue
   101	
   102	        p = files[pos]
   103	
   104	        r = results.get(p.name)
   105	
   106	        if not r:
   107	            continue
   108	
   109	        neighbor_id = r.get(
   110	            "current_first",
   111	            "",
   112	        )
   113	
   114	        score = ffloat(
   115	            r.get("final_first")
   116	        )
   117	
   118	        margin = ffloat(
   119	            r.get("final_margin")
   120	        )
   121	
   122	        neighbors.append({
   123	            "delta": delta,
   124	            "image": p.name,
   125	            "id": neighbor_id,
   126	            "score": score,
   127	            "margin": margin,
   128	        })
   129	
   130	    return neighbors
   131	
   132	
   133	def main():
   134	
   135	    print("=" * 80)
   136	    print("DRY RUN: BEST + SEQUENCE")
   137	    print("=" * 80)
   138	
   139	    print("CSV:", CSV_PATH)
   140	    print("INPUT:", INPUT_DIR)
   141	    print("MARGIN LIMIT:", MARGIN_LIMIT)
   142	    print("BEST STRONG DIFF:", BEST_STRONG_DIFF)
   143	    print("NEIGHBOR RADIUS:", NEIGHBOR_RADIUS)
   144	    print()
   145	
   146	    if not CSV_PATH.exists():
   147	        raise FileNotFoundError(CSV_PATH)
   148	
   149	    if not INPUT_DIR.exists():
   150	        raise FileNotFoundError(INPUT_DIR)
   151	
   152	    files = load_files()
   153	    results = load_results()
   154	
   155	    print(f"Images:     {len(files)}")
   156	    print(f"Recognized: {len(results)}")
   157	    print()
   158	
   159	    checked = 0
   160	    best_changes = 0
   161	    sequence_changes = 0
   162	    ambiguous = 0
   163	    kept = 0
   164	
   165	    print("=" * 80)
   166	    print("SUSPICIOUS FRAMES")
   167	    print("=" * 80)
   168	
   169	    for index, path in enumerate(files):
   170	
   171	        r = results.get(path.name)
   172	
   173	        if not r:
   174	            continue
   175	
   176	        margin = ffloat(
   177	            r.get("final_margin")
   178	        )
   179	
   180	        if margin is None:
   181	            continue
   182	
   183	        if margin >= MARGIN_LIMIT:
   184	            continue
   185	
   186	        checked += 1
   187	
   188	        first = r.get(
   189	            "current_first",
   190	            "",
   191	        )
   192	
   193	        second = r.get(
   194	            "current_second",
   195	            "",
   196	        )
   197	
   198	        first_score = ffloat(
   199	            r.get("final_first")
   200	        )
   201	
   202	        second_score = ffloat(
   203	            r.get("final_second")
   204	        )
   205	
   206	        best_first = ffloat(
   207	            r.get("best_first")
   208	        )
   209	
   210	        best_second = ffloat(
   211	            r.get("best_second")
   212	        )
   213	
   214	        best_diff = ffloat(
   215	            r.get("best_diff")
   216	        )
   217	
   218	        neighbors = get_neighbors(
   219	            files,
   220	            results,
   221	            index,
   222	        )
   223	
   224	        # --------------------------------------------------
   225	        # BEST
   226	        # --------------------------------------------------
   227	
   228	        best_decision = None
   229	        best_reason = ""
   230	
   231	        if (
   232	            best_diff is not None
   233	            and best_diff >= BEST_STRONG_DIFF
   234	        ):
   235	
   236	            best_decision = second
   237	
   238	            best_reason = (
   239	                "BEST strongly supports TOP2"
   240	            )
   241	
   242	        elif (
   243	            best_diff is not None
   244	            and best_diff <= -BEST_STRONG_DIFF
   245	        ):
   246	
   247	            best_decision = first
   248	
   249	            best_reason = (
   250	                "BEST strongly supports TOP1"
   251	            )
   252	
   253	        else:
   254	
   255	            best_reason = (
   256	                "BEST inconclusive"
   257	            )
   258	
   259	        # --------------------------------------------------
   260	        # SEQUENCE
   261	        # --------------------------------------------------
   262	
   263	        neighbor_first_votes = []
   264	        neighbor_second_votes = []
   265	
   266	        for n in neighbors:
   267	
   268	            if (
   269	                n["score"] is not None
   270	                and n["score"] < NEIGHBOR_SCORE_MIN
   271	            ):
   272	                continue
   273	
   274	            if n["id"] == first:
   275	                neighbor_first_votes.append(n)
   276	
   277	            if n["id"] == second:
   278	                neighbor_second_votes.append(n)
   279	
   280	        sequence_decision = None
   281	        sequence_reason = ""
   282	
   283	        if (
   284	            len(neighbor_first_votes)
   285	            >= 2
   286	        ):
   287	
   288	            sequence_decision = first
   289	
   290	            sequence_reason = (
   291	                "neighbors strongly support TOP1"
   292	            )
   293	
   294	        elif (
   295	            len(neighbor_second_votes)
   296	            >= 2
   297	        ):
   298	
   299	            sequence_decision = second
   300	
   301	            sequence_reason = (
   302	                "neighbors strongly support TOP2"
   303	            )
   304	
   305	        else:
   306	
   307	            sequence_reason = (
   308	                "sequence inconclusive"
   309	            )
   310	
   311	        # --------------------------------------------------
   312	        # FINAL PROPOSED DECISION
   313	        #
   314	        # PRIORITY:
   315	        #
   316	        # 1. Strong BEST
   317	        # 2. Strong sequence
   318	        # 3. Keep TOP1
   319	        #
   320	        # This is DRY RUN only.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

nl -ba scripts/dry_run_best_sequence.py | sed -n '315,430p'
   315	        #
   316	        # 1. Strong BEST
   317	        # 2. Strong sequence
   318	        # 3. Keep TOP1
   319	        #
   320	        # This is DRY RUN only.
   321	        # --------------------------------------------------
   322	
   323	        decision = first
   324	        reason = "KEEP_TOP1"
   325	
   326	        if best_decision is not None:
   327	
   328	            decision = best_decision
   329	            reason = best_reason
   330	
   331	            if decision != first:
   332	                best_changes += 1
   333	
   334	        elif sequence_decision is not None:
   335	
   336	            decision = sequence_decision
   337	            reason = sequence_reason
   338	
   339	            if decision != first:
   340	                sequence_changes += 1
   341	
   342	        else:
   343	
   344	            kept += 1
   345	
   346	            if (
   347	                best_diff is not None
   348	                and abs(best_diff)
   349	                < BEST_STRONG_DIFF
   350	            ):
   351	                ambiguous += 1
   352	
   353	        # --------------------------------------------------
   354	        # PRINT
   355	        # --------------------------------------------------
   356	
   357	        print()
   358	        print("-" * 80)
   359	
   360	        print(
   361	            f"{index:4d} {path.name}"
   362	        )
   363	
   364	        print(
   365	            f"  DINO:   "
   366	            f"{first} vs {second} "
   367	            f"margin={margin:.6f}"
   368	        )
   369	
   370	        print(
   371	            f"  SCORE:  "
   372	            f"{first_score if first_score is not None else 0:.4f} "
   373	            f"vs "
   374	            f"{second_score if second_score is not None else 0:.4f}"
   375	        )
   376	
   377	        print(
   378	            f"  BEST:   "
   379	            f"{best_first if best_first is not None else 0:.4f} "
   380	            f"vs "
   381	            f"{best_second if best_second is not None else 0:.4f} "
   382	            f"diff={best_diff if best_diff is not None else 0:+.6f}"
   383	        )
   384	
   385	        print(
   386	            f"  BEST:   "
   387	            f"{best_decision or '-'} "
   388	            f"({best_reason})"
   389	        )
   390	
   391	        if neighbors:
   392	
   393	            text = " | ".join(
   394	                f'{n["delta"]:+d}:'
   395	                f'{n["id"]}'
   396	                f'({n["score"]:.3f}'
   397	                if n["score"] is not None
   398	                else f'{n["delta"]:+d}:{n["id"]}'
   399	                for n in neighbors
   400	            )
   401	
   402	            print(
   403	                f"  NEIGH:  {text}"
   404	            )
   405	
   406	        print(
   407	            f"  SEQ:    "
   408	            f"{sequence_decision or '-'} "
   409	            f"({sequence_reason})"
   410	        )
   411	
   412	        print(
   413	            f"  >>>     "
   414	            f"{first} -> {decision}"
   415	        )
   416	
   417	        print(
   418	            f"  REASON: "
   419	            f"{reason}"
   420	        )
   421	
   422	    print()
   423	    print("=" * 80)
   424	    print("DRY RUN SUMMARY")
   425	    print("=" * 80)
   426	
   427	    print(
   428	        f"Suspicious frames:       {checked}"
   429	    )
   430	
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:28:30

Да. Теперь файл полностью понятен по логике до блока summary. И здесь есть **важный момент**, который я бы проверил до запуска.

### Что сейчас реально делает алгоритм

Для каждого кадра с `margin < 0.020`:

**1. BEST имеет абсолютный приоритет.**

Если:

```text
best_diff >= +0.05
```

то выбирается `TOP2`.

Если:

```text
best_diff <= -0.05
```

то выбирается `TOP1`.

То есть `BEST` может переиграть последовательность соседей.

**2. SEQUENCE работает только если BEST ничего не решил.**

Он смотрит ±2 кадра и считает только соседей с `score >= 0.80`.

Если минимум 2 соседа совпадают с `TOP1` → `TOP1`.

Если минимум 2 соседа совпадают с `TOP2` → `TOP2`.

**3. Если оба метода ничего не сказали → сохраняется TOP1.**

То есть фактический приоритет:

```text
BEST
 ↓
SEQUENCE
 ↓
TOP1
```

Это соответствует комментарию в коде.

---

### Но я вижу потенциальную проблему

Вот этот участок:

```python
if best_diff >= BEST_STRONG_DIFF:
    best_decision = second
```

и:

```python
elif best_diff <= -BEST_STRONG_DIFF:
    best_decision = first
```

Мы предполагаем, что `best_diff` рассчитан именно как:

```text
best_first - best_second
```

Если это так — логика правильная.

Но если в `margin_best.csv` `best_diff` имеет обратный знак, то **BEST будет систематически выбирать неправильного кандидата**.

Поэтому перед любыми изменениями я бы сейчас проверил сам CSV и статистику.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== CSV HEADER ==="
head -n 2 output/benchmark_components/full_analysis/margin_best.csv

echo
echo "=== BEST DIFF SAMPLE ==="
python - <<'PY'
import csv

p = "output/benchmark_components/full_analysis/margin_best.csv"

with open(p, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

for r in rows[:20]:
    print(
        r["image"],
        "first=", r["current_first"],
        "second=", r["current_second"],
        "best_first=", r["best_first"],
        "best_second=", r["best_second"],
        "best_diff=", r["best_diff"],
    )
PY
```

И отдельно я хочу увидеть **конец summary**, потому что сейчас вывод оборвался на строке 430:

```bash
nl -ba scripts/dry_run_best_sequence.py | sed -n '422,470p'
```

После этого уже можно будет безопасно запускать `dry_run` и смотреть, **сколько конкретно кадров предлагается перекинуть с TOP1 на TOP2**, не изменяя ни одного файла.

Это сейчас правильный этап: **сначала проверяем логику на существующем CSV → потом dry-run → потом визуально проверяем спорные кадры → и только затем решаем, внедрять ли изменение в реальный recognizer.**

---

### 👤 **User** — 2026-08-15 15:29:19

uv

---

### 🤖 **Assistant** — 2026-08-15 15:29:19

Да, запускаем через `uv`.

Для проверки текущего `dry_run_best_sequence.py`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/dry_run_best_sequence.py
```

Если хочешь сначала проверить `best_diff`, как я предлагал:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import csv

p = "output/benchmark_components/full_analysis/margin_best.csv"

with open(p, encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

for r in rows[:20]:
    print(
        r["image"],
        "first=", r["current_first"],
        "second=", r["current_second"],
        "best_first=", r["best_first"],
        "best_second=", r["best_second"],
        "best_diff=", r["best_diff"],
    )
PY
```

И конец файла:

```bash
nl -ba scripts/dry_run_best_sequence.py | sed -n '422,470p'
```

**Я бы сейчас первым запускал именно:**

```bash
uv run python scripts/dry_run_best_sequence.py
```

Он ничего не меняет — только показывает, что алгоритм предлагает сделать.

---

### 👤 **User** — 2026-08-15 15:29:37

int_mvp_v02

uv run python scripts/dry_run_best_sequence.py
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
================================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:29:37

Да, результат очень показательный.

### Сейчас `dry_run` ничего не проверил

Получили:

```text
Images:     256
Recognized: 262
Suspicious frames: 0
```

Причина простая: **ни один из 256 файлов не имеет `final_margin < 0.020`**.

То есть текущий `dry_run` даже не дошёл до BEST и SEQUENCE.

При этом есть ещё интересная деталь:

```text
Images:     256
Recognized: 262
```

В CSV есть **6 записей, которых нет среди файлов `test`**. Это само по себе стоит проверить, но не является причиной `0 suspicious`.

### Я предлагаю сейчас не менять алгоритм

Нужно понять распределение `final_margin`. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import csv

p = "output/benchmark_components/full_analysis/margin_best.csv"

values = []

with open(p, encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        try:
            values.append((float(r["final_margin"]), r["image"]))
        except:
            pass

values.sort()

print("=" * 80)
print("FINAL MARGIN DISTRIBUTION")
print("=" * 80)

print(f"Total CSV rows: {len(values)}")
print()

for threshold in [0.005, 0.010, 0.020, 0.030, 0.050, 0.100]:
    n = sum(v < threshold for v, _ in values)
    print(f"margin < {threshold:6.3f}: {n}")

print()
print("10 LOWEST MARGINS:")
print("-" * 80)

for margin, image in values[:10]:
    print(f"{margin:.6f}  {image}")

print()
print("10 HIGHEST MARGINS:")
print("-" * 80)

for margin, image in values[-10:][::-1]:
    print(f"{margin:.6f}  {image}")
PY
```

Это даст нам ответ на главный вопрос:

**`0.020` действительно слишком низкий порог для текущего v33 или в CSV вообще другая шкала margin?**

Если, например, окажется:

```text
margin < 0.020: 0
margin < 0.050: 3
margin < 0.100: 17
```

тогда просто подберём рабочее окно для анализа.

А если даже:

```text
margin < 0.100: 0
```

тогда надо смотреть, **как именно сейчас считается `final_margin`**, а не крутить порог вслепую.

И ещё: `Recognized 262` против `Images 256` я бы после этого отдельно проверил — вероятно, CSV содержит результаты от предыдущего/более широкого запуска.

---

### 👤 **User** — 2026-08-15 15:30:02

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import csv

p = "output/benchmark_components/full_analysis/margin_best.csv"

values = []

with open(p, encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        try:
            values.append((float(r["final_margin"]), r["image"]))
        except:
            pass

values.sort()

print("=" * 80)
print("FINAL MARGIN DISTRIBUTION")
print("=" * 80)

print(f"Total CSV rows: {len(values)}")
PY  print(f"{margin:.6f}  {image}"):-1]:n}")) 0.050, 0.100]:
================================================================================
FINAL MARGIN DISTRIBUTION
================================================================================
Total CSV rows: 262

margin <  0.005: 7
margin <  0.010: 14
margin <  0.020: 32
margin <  0.030: 50
margin <  0.050: 114
margin <  0.100: 233

10 LOWEST MARGINS:
--------------------------------------------------------------------------------
0.001037  Ленина 125-127 А (14).JPG
0.001418  008.JPG
0.001876  Ленина 125-127 А (10).JPG
0.002587  Ленина 125-127 А (17).JPG
0.003229  Вавилова ул. - Радиаторный пер.  A (70).JPG
0.004476  009.JPG
0.004802  Ленина 125-127 А (9).JPG
0.005768  Ленина 125-127 А (8).JPG
0.006080  Ленина 125-127 А (11).JPG
0.006481  Вавилова ул. - Радиаторный пер.  A (63).JPG

10 HIGHEST MARGINS:
--------------------------------------------------------------------------------
0.181591  Малиновского 9 А (29).JPG
0.173871  Малиновского 9 А (19).JPG
0.165013  Малиновского 9 А (6).JPG
0.153786  Малиновского 9 (12).JPG
0.144542  006.JPG
0.143926  Малиновского 9 А (13).JPG
0.138006  Добровольского 17 А (63).JPG
0.137992  Добровольского 17 А (61).JPG
0.133341  007.JPG
0.131058  Малиновского 9 А (18).JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:30:02

Вот теперь картина ясная. **Порог `0.020` нормальный, и dry-run действительно должен был увидеть 32 подозрительных кадра.** Но он увидел `0`, потому что среди 32 строк CSV с маленьким margin есть **6 файлов, которых нет в `data/input/test`**, а остальные 26 должны были попасть.

Однако есть ещё более важный момент: твой вывод `Images: 256 / Recognized: 262` подтверждает, что `margin_best.csv` содержит результаты не только текущей папки `test`.

То есть проблема не в алгоритме BEST/SEQUENCE, а в том, что CSV и `test` сейчас **не синхронизированы по набору файлов**.

### Давай точно выясним, какие 32 подозрительные записи относятся к `test`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import csv
from pathlib import Path

csv_path = Path("output/benchmark_components/full_analysis/margin_best.csv")
input_dir = Path("data/input/test")

files = {
    p.name
    for p in input_dir.iterdir()
    if p.is_file()
}

rows = []

with csv_path.open(encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        try:
            margin = float(r["final_margin"])
        except:
            continue

        if margin < 0.020:
            rows.append((margin, r["image"], r))

rows.sort()

print("=" * 80)
print("SUSPICIOUS CSV ROWS")
print("=" * 80)

in_test = 0
not_in_test = 0

for margin, image, r in rows:
    status = "IN TEST" if image in files else "NOT IN TEST"

    if image in files:
        in_test += 1
    else:
        not_in_test += 1

    print(
        f"{margin:.6f}  {status:12}  {image}"
    )

print()
print("=" * 80)
print(f"TOTAL SUSPICIOUS: {len(rows)}")
print(f"IN TEST:          {in_test}")
print(f"NOT IN TEST:      {not_in_test}")
print("=" * 80)
PY
```

Я ожидаю увидеть примерно:

```text
TOTAL SUSPICIOUS: 32
IN TEST:          26
NOT IN TEST:       6
```

Если так и будет, следующий шаг — **не менять `MARGIN_LIMIT`**, а заставить benchmark/dry-run работать строго с текущим набором `test`.

И ещё я бы после этого посмотрел на эти 26 кадров: именно среди них сейчас находятся кандидаты, где имеет смысл проверить **BEST + последовательность ±2**.

То есть мы уже нашли хорошее рабочее окно:

```text
< 0.005   — 7 кадров, очень сомнительные
< 0.010   — 14
< 0.020   — 32
< 0.030   — 50
```

Для первого эксперимента **`0.020` оставляем**.

---

### 👤 **User** — 2026-08-15 15:30:35

набор файлов менялся и переименовывался. надо пересчитать

---

### 🤖 **Assistant** — 2026-08-15 15:30:35

Да, тогда всё сходится. **`margin_best.csv` устарел** относительно текущего `data/input/test`. Ничего чинить в `dry_run` не нужно — сначала полностью пересчитываем benchmark для текущего набора файлов.

Причём с учётом того, что файлы переименовывались, старый CSV вообще лучше не использовать.

Я бы сделал так:

### 1. Сначала посмотрим, каким скриптом сейчас строится `margin_best.csv`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -R "margin_best.csv" -n scripts app . --exclude-dir=.venv --exclude-dir=.git 2>/dev/null
```

Это найдёт **точный скрипт**, который создаёт `margin_best.csv`.

После этого пересчитаем его на текущем `data/input/test`, затем снова:

```bash
uv run python scripts/dry_run_best_sequence.py
```

И уже получим корректные:

```text
Images:     256
Recognized: 256
Suspicious frames: XX
Changed by BEST: XX
Changed by SEQUENCE: XX
```

**Важно:** пока ничего в `recognizer.py` не меняем. Сначала пересчитываем исходные результаты на актуальном наборе файлов, а уже потом оцениваем BEST + SEQUENCE.

---

### 👤 **User** — 2026-08-15 15:31:28

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -R "margin_best.csv" -n scripts app . --exclude-dir=.venv --exclude-dir=.git 2>/dev/null
scripts/sort_margin005_best.py:13:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_neighbor_v34.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/dry_run_best_sequence.py:12:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_neighbor_v35.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
./scripts/sort_margin005_best.py:13:    / "output/benchmark_components/full_analysis/margin_best.csv"
./scripts/sort_neighbor_v34.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
./scripts/dry_run_best_sequence.py:12:    / "output/benchmark_components/full_analysis/margin_best.csv"
./scripts/sort_neighbor_v35.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:31:28

Да. Значит, **генератор `margin_best.csv` — `scripts/sort_margin005_best.py`**.

Сначала посмотрим его целиком, чтобы не запустить старую логику вслепую:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nl -ba scripts/sort_margin005_best.py | sed -n '1,260p'
```

Пришли вывод.

После этого определим, какие параметры он использует для текущих `v33`, пересчитаем `margin_best.csv` **по актуальным 256 файлам `test`**, и только потом снова запустим:

```bash
uv run python scripts/dry_run_best_sequence.py
```

Старый `margin_best.csv` пока **не удаляем и не перезаписываем**, пока не увидим код генератора.

---

### 👤 **User** — 2026-08-15 15:31:49

int_mvp_v02

nl -ba scripts/sort_margin005_best.py | sed -n '1,260p'
     1	#!/usr/bin/env python3
     2	
     3	import csv
     4	import shutil
     5	from pathlib import Path
     6	from collections import Counter
     7	
     8	
     9	PROJECT = Path(__file__).resolve().parent.parent
    10	
    11	INPUT_CSV = (
    12	    PROJECT
    13	    / "output/benchmark_components/full_analysis/margin_best.csv"
    14	)
    15	
    16	SOURCE_DIR = PROJECT / "data/input/test"
    17	
    18	OUTPUT_DIR = PROJECT / "output/visual_check_margin005"
    19	
    20	CHANGED_DIR = OUTPUT_DIR / "_CHANGED"
    21	
    22	MARGIN_THRESHOLD = 0.005
    23	
    24	
    25	def safe_copy(src, dst_dir):
    26	    dst_dir.mkdir(parents=True, exist_ok=True)
    27	
    28	    dst = dst_dir / src.name
    29	
    30	    if not dst.exists():
    31	        shutil.copy2(src, dst)
    32	        return dst
    33	
    34	    stem = src.stem
    35	    suffix = src.suffix
    36	
    37	    n = 2
    38	
    39	    while True:
    40	        candidate = dst_dir / f"{stem}__{n}{suffix}"
    41	
    42	        if not candidate.exists():
    43	            shutil.copy2(src, candidate)
    44	            return candidate
    45	
    46	        n += 1
    47	
    48	
    49	def main():
    50	
    51	    print("=" * 80)
    52	    print("MARGIN < 0.005 + BEST VISUAL TEST")
    53	    print("=" * 80)
    54	
    55	    print("CSV   :", INPUT_CSV)
    56	    print("SOURCE:", SOURCE_DIR)
    57	    print("OUTPUT:", OUTPUT_DIR)
    58	    print()
    59	
    60	    if not INPUT_CSV.exists():
    61	        raise FileNotFoundError(INPUT_CSV)
    62	
    63	    if not SOURCE_DIR.exists():
    64	        raise FileNotFoundError(SOURCE_DIR)
    65	
    66	    # Clean only our test output.
    67	    if OUTPUT_DIR.exists():
    68	        shutil.rmtree(OUTPUT_DIR)
    69	
    70	    OUTPUT_DIR.mkdir(parents=True)
    71	
    72	    rows = []
    73	
    74	    with INPUT_CSV.open(
    75	        "r",
    76	        encoding="utf-8-sig",
    77	        newline=""
    78	    ) as f:
    79	
    80	        reader = csv.DictReader(f)
    81	
    82	        for row in reader:
    83	            rows.append(row)
    84	
    85	    print(f"CSV rows: {len(rows)}")
    86	    print()
    87	
    88	    counters = Counter()
    89	    changed = []
    90	    low_margin = []
    91	
    92	    for row in rows:
    93	
    94	        image = row["image"]
    95	
    96	        current_first = row["current_first"]
    97	        current_second = row["current_second"]
    98	
    99	        final_margin = float(row["final_margin"])
   100	        best_diff = float(row["best_diff"])
   101	
   102	        # --------------------------------------------------
   103	        # DECISION
   104	        # --------------------------------------------------
   105	
   106	        assigned = current_first
   107	        reason = "FIRST"
   108	
   109	        if final_margin < MARGIN_THRESHOLD:
   110	
   111	            low_margin.append(row)
   112	
   113	            if best_diff > 0:
   114	
   115	                assigned = current_second
   116	                reason = "BEST"
   117	
   118	            else:
   119	
   120	                reason = "FIRST_BEST_LOSES"
   121	
   122	        # --------------------------------------------------
   123	        # SOURCE
   124	        # --------------------------------------------------
   125	
   126	        src = SOURCE_DIR / image
   127	
   128	        if not src.exists():
   129	
   130	            print(
   131	                f"[WARNING] source not found: {src}"
   132	            )
   133	
   134	            continue
   135	
   136	        # --------------------------------------------------
   137	        # DESTINATION
   138	        # --------------------------------------------------
   139	
   140	        folder = assigned.replace("_v33", "")
   141	
   142	        dst_dir = OUTPUT_DIR / folder
   143	
   144	        safe_copy(src, dst_dir)
   145	
   146	        counters[folder] += 1
   147	
   148	        # --------------------------------------------------
   149	        # CHANGED
   150	        # --------------------------------------------------
   151	
   152	        if assigned != current_first:
   153	
   154	            changed.append({
   155	                "image": image,
   156	                "old": current_first,
   157	                "new": assigned,
   158	                "margin": final_margin,
   159	                "best_diff": best_diff,
   160	            })
   161	
   162	            # Put an additional copy into _CHANGED.
   163	            safe_copy(src, CHANGED_DIR)
   164	
   165	    # ------------------------------------------------------
   166	    # REPORT
   167	    # ------------------------------------------------------
   168	
   169	    report = OUTPUT_DIR / "decision_report.csv"
   170	
   171	    with report.open(
   172	        "w",
   173	        encoding="utf-8-sig",
   174	        newline=""
   175	    ) as f:
   176	
   177	        fields = [
   178	            "image",
   179	            "old",
   180	            "new",
   181	            "margin",
   182	            "best_diff",
   183	        ]
   184	
   185	        writer = csv.DictWriter(
   186	            f,
   187	            fieldnames=fields
   188	        )
   189	
   190	        writer.writeheader()
   191	
   192	        writer.writerows(changed)
   193	
   194	    print("=" * 80)
   195	    print("RESULT")
   196	    print("=" * 80)
   197	
   198	    print(
   199	        f"Total images:        {len(rows)}"
   200	    )
   201	
   202	    print(
   203	        f"Margin < 0.005:      {len(low_margin)}"
   204	    )
   205	
   206	    print(
   207	        f"Changed by BEST:     {len(changed)}"
   208	    )
   209	
   210	    print()
   211	
   212	    print("CHANGED:")
   213	    print("-" * 80)
   214	
   215	    for x in changed:
   216	
   217	        print(
   218	            f'{x["image"]}'
   219	        )
   220	
   221	        print(
   222	            f'    {x["old"]} -> {x["new"]}'
   223	        )
   224	
   225	        print(
   226	            f'    margin={x["margin"]:.6f}'
   227	            f'  best_diff={x["best_diff"]:+.6f}'
   228	        )
   229	
   230	    print()
   231	    print("DISTRIBUTION")
   232	    print("-" * 80)
   233	
   234	    for folder in sorted(
   235	        counters,
   236	        key=lambda x: int(x)
   237	    ):
   238	
   239	        print(
   240	            f"{folder:10s} {counters[folder]:4d}"
   241	        )
   242	
   243	    print("-" * 80)
   244	    print(
   245	        f"{'TOTAL':10s} {sum(counters.values()):4d}"
   246	    )
   247	
   248	    print()
   249	    print("OUTPUT:")
   250	    print(
   251	        f"  sorted : {OUTPUT_DIR}"
   252	    )
   253	
   254	    print(
   255	        f"  changed: {CHANGED_DIR}"
   256	    )
   257	
   258	    print(
   259	        f"  report : {report}"
   260	    )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:31:49

Да, теперь видно главное: **`sort_margin005_best.py` не пересчитывает `margin_best.csv` вообще**. Он только читает уже существующий CSV и раскладывает файлы.

То есть мой предыдущий вывод про него как генератор был неправильным.

Сейчас надо найти **скрипт, который создаёт benchmark CSV**. Ищем не только имя файла, а места, где используется `csv.writer`/`DictWriter` для `margin_best` или где рассчитываются `best_diff`, `final_margin`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== best_diff ==="
grep -R "best_diff" -n scripts app --exclude-dir=.venv

echo
echo "=== final_margin ==="
grep -R "final_margin" -n scripts app --exclude-dir=.venv

echo
echo "=== margin_best creation ==="
grep -R "margin_best" -n scripts app --exclude-dir=.venv
```

Особенно нужен скрипт, где встречаются одновременно примерно:

```text
best_first
best_second
best_diff
final_margin
```

Потому что именно его надо запускать заново на **нынешних 256 файлах**.

И ещё важный момент: поскольку набор файлов **менялся и переименовывался**, пересчёт должен быть именно от текущего:

```text
data/input/test
```

а не попытка сопоставлять старый CSV с новым набором.

После того как найдём генератор, сделаем:

```text
текущий test
    ↓
полное распознавание v33
    ↓
новый margin_best.csv (256 строк)
    ↓
dry_run_best_sequence.py
    ↓
анализ BEST + SEQUENCE
```

**Старый `margin_best.csv` пока не трогаем.**

---

### 👤 **User** — 2026-08-15 15:32:07

grep -R "margin_best" -n scripts app --exclude-dir=.venv
=== best_diff ===
scripts/sort_margin005_best.py:100:        best_diff = float(row["best_diff"])
scripts/sort_margin005_best.py:113:            if best_diff > 0:
scripts/sort_margin005_best.py:159:                "best_diff": best_diff,
scripts/sort_margin005_best.py:182:            "best_diff",
scripts/sort_margin005_best.py:227:            f'  best_diff={x["best_diff"]:+.6f}'
scripts/dry_run_best_sequence.py:214:        best_diff = ffloat(
scripts/dry_run_best_sequence.py:215:            r.get("best_diff")
scripts/dry_run_best_sequence.py:232:            best_diff is not None
scripts/dry_run_best_sequence.py:233:            and best_diff >= BEST_STRONG_DIFF
scripts/dry_run_best_sequence.py:243:            best_diff is not None
scripts/dry_run_best_sequence.py:244:            and best_diff <= -BEST_STRONG_DIFF
scripts/dry_run_best_sequence.py:347:                best_diff is not None
scripts/dry_run_best_sequence.py:348:                and abs(best_diff)
scripts/dry_run_best_sequence.py:382:            f"diff={best_diff if best_diff is not None else 0:+.6f}"

=== final_margin ===
scripts/sort_margin005_best.py:99:        final_margin = float(row["final_margin"])
scripts/sort_margin005_best.py:109:        if final_margin < MARGIN_THRESHOLD:
scripts/sort_margin005_best.py:158:                "margin": final_margin,
scripts/sort_neighbor_v34.py:130:        margin = ffloat(r.get("final_margin"))
scripts/sort_neighbor_v34.py:186:                    neighbor_result.get("final_margin")
scripts/dry_run_best_sequence.py:119:            r.get("final_margin")
scripts/dry_run_best_sequence.py:177:            r.get("final_margin")
grep: scripts/__pycache__/sort_neighbor_v35.cpython-312.pyc: binary file matches
scripts/sort_neighbor_v35.py:75:            row["final_margin"]

=== margin_best creation ===
scripts/sort_margin005_best.py:13:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_neighbor_v34.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/dry_run_best_sequence.py:12:    / "output/benchmark_components/full_analysis/margin_best.csv"
grep: scripts/__pycache__/sort_neighbor_v35.cpython-312.pyc: binary file matches
scripts/sort_neighbor_v35.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:32:07

Вот теперь важный вывод: **в `scripts/` генератора `margin_best.csv` нет**. Все найденные скрипты только **читают** этот CSV.

Значит, `margin_best.csv` создаётся другим benchmark-скриптом, вероятно из `output/benchmark_components` или через основной benchmark pipeline.

Найдём его по **самой записи CSV**, а не по имени файла. Выполни:

```bash id="m0v9zj"
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== ALL CSV WRITERS ==="
grep -R -n -E "DictWriter|writerow|writerows" scripts app \
    --exclude-dir=.venv \
    --exclude-dir=__pycache__

echo
echo "=== BENCHMARK SCRIPTS ==="
find scripts app -type f \
    \( -name "*.py" -o -name "*.sh" \) \
    -print | sort
```

Но есть ещё более быстрый вариант — посмотреть структуру benchmark:

```bash id="l1r5j8"
cd ~/projects/scene_fingerprint_mvp_v02

find output/benchmark_components -maxdepth 3 -type f | sort | head -200
```

### Почему это важно

Сейчас у нас:

```text
data/input/test              ← 256 актуальных файлов
margin_best.csv              ← 262 старых результата
```

А поскольку **имена файлов менялись**, нам нельзя просто фильтровать старый CSV. Нужно найти исходный benchmark-процесс и **пересчитать всё с нуля на текущем `test`**.

После этого ожидаем:

```text
Images:     256
Recognized: 256
```

и уже тогда `dry_run_best_sequence.py` покажет реальные подозрительные кадры.

Пока **ничего не удаляем и не меняем**. Нам осталось найти генератор benchmark.

---

### 👤 **User** — 2026-08-15 15:32:24

=== BENCHMARK SCRIPTS ===
app/cli.py
app/core/config.py
app/core/embedder.py
app/core/fingerprint.py
app/core/image.py
app/core/__init__.py
app/core/recognizer.py
app/core/scene_analyzer.py
app/__init__.py
app/main.py
app/ocr/grid_ocr.py
app/ocr/__init__.py
app/ocr/ocr_pipeline.py
app/ocr/plate_detector.py
app/pipeline/__init__.py
app/pipeline/queue.py
app/pipeline/worker.py
scripts/analyze_sequence_v38.py
scripts/benchmark_test_v1.py
scripts/dry_run_best_sequence.py
scripts/llm_resolver_v01.py
scripts/make_subfingerprints.py
scripts/make_subfingerprints_v2.py
scripts/sort_baseline.py
scripts/sort_margin005_best.py
scripts/sort_neighbor_v34.py
scripts/sort_neighbor_v35_benchmark.py
scripts/sort_neighbor_v35.py
scripts/sort_neighbor_v36_img.py
scripts/sort_neighbor_v36.py
scripts/sort_neighbor_v37.py
scripts/sort_test_and_report.py
scripts/sort_test_and_report_v2.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:32:25

Отлично, теперь нашли направление. Судя по списку, генератор почти наверняка находится здесь:

```text
scripts/benchmark_test_v1.py
```

Именно название `benchmark` совпадает с папкой:

```text
output/benchmark_components/full_analysis/
```

Сейчас надо посмотреть его.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nl -ba scripts/benchmark_test_v1.py | sed -n '1,300p'
```

Особенно интересуют места, где он:

- читает `data/input/test`
- вызывает `recognizer`
- пишет CSV
- считает:
  - `final_first`
  - `final_second`
  - `final_margin`
  - `best_first`
  - `best_second`
  - `best_diff`

---

По текущей картине пайплайн, скорее всего, был такой:

```
data/input/test
        |
        v
benchmark_test_v1.py
        |
        v
output/benchmark_components/full_analysis/*.csv
        |
        v
margin_best.csv
        |
        +--> sort_margin005_best.py
        +--> sort_neighbor_v35.py
        +--> dry_run_best_sequence.py
```

То есть надо просто заново прогнать `benchmark_test_v1.py` на текущем `test`, а не чинить `dry_run`.

После пересчёта ожидаем:

```text
Images:     256
Recognized: 256
```

и тогда уже проверяем v33 + BEST + SEQUENCE.

---

### 👤 **User** — 2026-08-15 15:32:47

int_mvp_v02

nl -ba scripts/benchmark_test_v1.py | sed -n '1,300p'
     1	#!/usr/bin/env python3
     2	
     3	import json
     4	import re
     5	import subprocess
     6	import time
     7	from pathlib import Path
     8	from collections import Counter, defaultdict
     9	
    10	import psutil
    11	
    12	
    13	PROJECT = Path(__file__).resolve().parent.parent
    14	TEST_DIR = PROJECT / "data/input/test"
    15	OUT_DIR = PROJECT / "data/output/benchmark_v1"
    16	
    17	FINGERPRINTS = [f"{i}_v33" for i in range(78, 96)]
    18	
    19	
    20	def extract_real_address(filename):
    21	    """
    22	    Используется ТОЛЬКО для benchmark.
    23	
    24	    Примеры:
    25	      Вавилова 52 А (10).JPG -> 83
    26	      1 Конной Армии 32 А (10).JPG -> ...
    27	    """
    28	
    29	    # Пока не угадываем адрес по тексту.
    30	    # Используем соответствие имени через fingerprint image database
    31	    # ниже.
    32	    return None
    33	
    34	
    35	def load_fingerprint_names():
    36	    """
    37	    Строим:
    38	        filename -> fingerprint
    39	
    40	    Это позволяет определить REAL для файлов,
    41	    которые являются копиями/вариантами исходных фотографий.
    42	    """
    43	
    44	    result = {}
    45	
    46	    for fp in FINGERPRINTS:
    47	        p = PROJECT / "data/fingerprints" / fp / "metadata.json"
    48	
    49	        if not p.exists():
    50	            continue
    51	
    52	        with open(p, encoding="utf-8") as f:
    53	            meta = json.load(f)
    54	
    55	        for name in meta.get("image_names", []):
    56	            result[name.lower()] = fp
    57	
    58	    return result
    59	
    60	
    61	def find_real_from_filename(filename, fingerprint_names):
    62	    """
    63	    Сначала пробуем точное имя.
    64	
    65	    Если имя тестового файла отличается от имени fingerprint,
    66	    пытаемся использовать известные группы адресов из имени.
    67	
    68	    Это benchmark-логика и НИКОГДА не передается recognition.
    69	    """
    70	
    71	    key = filename.lower()
    72	
    73	    if key in fingerprint_names:
    74	        return fingerprint_names[key]
    75	
    76	    # Важный случай:
    77	    # тестовые файлы обычно переименованы адресом.
    78	    #
    79	    # Для полноценного benchmark нам нужно заранее составить
    80	    # mapping адрес -> fingerprint.
    81	    #
    82	    # Поэтому пока возвращаем UNKNOWN.
    83	    return None
    84	
    85	
    86	def run_recognition():
    87	    OUT_DIR.mkdir(parents=True, exist_ok=True)
    88	
    89	    cmd = [
    90	        "uv",
    91	        "run",
    92	        "scene-fingerprint",
    93	        "recognize",
    94	        str(TEST_DIR),
    95	        "--top-k",
    96	        "5",
    97	        "--threshold",
    98	        "0.0",
    99	        "--fingerprints",
   100	        ",".join(FINGERPRINTS),
   101	        "--json",
   102	    ]
   103	
   104	    print("=" * 80)
   105	    print("BENCHMARK RECOGNITION")
   106	    print("=" * 80)
   107	    print("Images:", len(list(TEST_DIR.glob("*"))))
   108	    print("Fingerprints:", len(FINGERPRINTS))
   109	    print()
   110	
   111	    t0 = time.perf_counter()
   112	
   113	    proc = subprocess.run(
   114	        cmd,
   115	        cwd=PROJECT,
   116	        capture_output=True,
   117	        text=True,
   118	    )
   119	
   120	    elapsed = time.perf_counter() - t0
   121	
   122	    if proc.returncode != 0:
   123	        print(proc.stdout)
   124	        print(proc.stderr)
   125	        raise RuntimeError(
   126	            f"recognize failed: {proc.returncode}"
   127	        )
   128	
   129	    # Ищем JSON-массив среди служебного вывода.
   130	    decoder = json.JSONDecoder()
   131	
   132	    data = None
   133	
   134	    text = proc.stdout + "\n" + proc.stderr
   135	
   136	    for i, ch in enumerate(text):
   137	        if ch != "[":
   138	            continue
   139	
   140	        try:
   141	            obj, end = decoder.raw_decode(text[i:])
   142	            if isinstance(obj, list):
   143	                data = obj
   144	                break
   145	        except json.JSONDecodeError:
   146	            continue
   147	
   148	    if data is None:
   149	        raise RuntimeError("JSON recognition result not found")
   150	
   151	    return data, elapsed
   152	
   153	
   154	def main():
   155	
   156	    if not TEST_DIR.exists():
   157	        raise RuntimeError(f"Нет папки {TEST_DIR}")
   158	
   159	    OUT_DIR.mkdir(parents=True, exist_ok=True)
   160	
   161	    fingerprint_names = load_fingerprint_names()
   162	
   163	    data, elapsed = run_recognition()
   164	
   165	    print()
   166	    print("=" * 80)
   167	    print("RESULTS")
   168	    print("=" * 80)
   169	
   170	    print("TOTAL:", len(data))
   171	    print("TIME:", f"{elapsed:.2f} sec")
   172	    print(
   173	        "SPEED:",
   174	        f"{len(data)/elapsed:.2f} images/sec"
   175	    )
   176	
   177	    # Пока REAL может быть неизвестен.
   178	    # Но сохраняем всю информацию TOP-5.
   179	
   180	    rows = []
   181	
   182	    for x in data:
   183	
   184	        candidates = x.get("candidates", [])
   185	
   186	        top = [
   187	            c.get("id")
   188	            for c in candidates[:5]
   189	        ]
   190	
   191	        scores = [
   192	            c.get("score")
   193	            for c in candidates[:5]
   194	        ]
   195	
   196	        rows.append({
   197	            "file": x.get("file"),
   198	            "real": find_real_from_filename(
   199	                Path(x.get("file", "")).name,
   200	                fingerprint_names
   201	            ),
   202	            "top1": top[0] if len(top) > 0 else None,
   203	            "top1_score": scores[0] if len(scores) > 0 else None,
   204	            "top2": top[1] if len(top) > 1 else None,
   205	            "top2_score": scores[1] if len(scores) > 1 else None,
   206	            "top3": top[2] if len(top) > 2 else None,
   207	            "top3_score": scores[2] if len(scores) > 2 else None,
   208	            "top4": top[3] if len(top) > 3 else None,
   209	            "top4_score": scores[3] if len(scores) > 3 else None,
   210	            "top5": top[4] if len(top) > 4 else None,
   211	            "top5_score": scores[4] if len(scores) > 4 else None,
   212	            "score": x.get("score"),
   213	            "margin": x.get("margin"),
   214	            "confidence": x.get("confidence"),
   215	            "status": x.get("status"),
   216	            "best_image": x.get("best_image"),
   217	        })
   218	
   219	    # Сохраняем полный benchmark.
   220	    (OUT_DIR / "benchmark.json").write_text(
   221	        json.dumps(
   222	            {
   223	                "total": len(rows),
   224	                "recognition_time_sec": elapsed,
   225	                "images_per_second": len(rows) / elapsed,
   226	                "fingerprints": FINGERPRINTS,
   227	                "results": rows,
   228	            },
   229	            ensure_ascii=False,
   230	            indent=2,
   231	        ),
   232	        encoding="utf-8",
   233	    )
   234	
   235	    # Простая статистика TOP кандидатов.
   236	    top1 = Counter(x["top1"] for x in rows)
   237	    top2 = Counter(x["top2"] for x in rows)
   238	
   239	    print()
   240	    print("TOP-1 DISTRIBUTION")
   241	    for fp, n in sorted(top1.items()):
   242	        print(
   243	            f"{fp:10s} {n:4d} "
   244	            f"{100*n/len(rows):6.2f}%"
   245	        )
   246	
   247	    print()
   248	    print("TOP-2 DISTRIBUTION")
   249	    for fp, n in sorted(top2.items()):
   250	        print(
   251	            f"{fp:10s} {n:4d} "
   252	            f"{100*n/len(rows):6.2f}%"
   253	        )
   254	
   255	    print()
   256	    print("OUTPUT:")
   257	    print(OUT_DIR / "benchmark.json")
   258	
   259	    print()
   260	    print("=" * 80)
   261	    print("NOTE")
   262	    print("=" * 80)
   263	    print(
   264	        "REAL пока не вычисляется автоматически для "
   265	        "переименованных тестовых файлов."
   266	    )
   267	    print(
   268	        "Следующим шагом построим mapping "
   269	        "адрес -> fingerprint и получим настоящий TOP-1/2/3/5 accuracy."
   270	    )
   271	
   272	
   273	if __name__ == "__main__":
   274	    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:32:48

Нашли. Но есть важный нюанс: **`benchmark_test_v1.py` тоже не создаёт `margin_best.csv`**.

Он создаёт только:

```text
data/output/benchmark_v1/benchmark.json
```

И его задача — базовый benchmark распознавания:

```text
test
 ↓
scene-fingerprint recognize
 ↓
benchmark.json
```

А `margin_best.csv` появился уже на следующем этапе обработки.

Сейчас цепочка выглядит так:

```text
data/input/test
        |
        v
benchmark_test_v1.py
        |
        v
data/output/benchmark_v1/benchmark.json
        |
        ?
        |
        v
output/benchmark_components/full_analysis/margin_best.csv
        |
        +--> sort_margin005_best.py
        +--> sort_neighbor_v35.py
        +--> dry_run_best_sequence.py
```

Нам нужен промежуточный скрипт, который берёт `benchmark.json` и строит `full_analysis`.

Ищи по названию папки:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -R "full_analysis" -n scripts app --exclude-dir=.venv --exclude-dir=__pycache__
```

И ещё:

```bash
grep -R "benchmark_v1" -n scripts app --exclude-dir=.venv --exclude-dir=__pycache__
```

---

Но есть ещё хорошая новость: `benchmark_test_v1.py` уже готов для нашего случая.

Он использует:

```python
FINGERPRINTS = [f"{i}_v33" for i in range(78, 96)]
```

То есть текущий эксперимент действительно идёт на:

```text
78_v33 ... 95_v33
```

и не затрагивает старые версии.

После того как найдём генератор `margin_best.csv`, полный пересчёт будет правильным:

```bash
uv run python scripts/benchmark_test_v1.py
```

→ построить full_analysis

→

```bash
uv run python scripts/dry_run_best_sequence.py
```

Сейчас мы на правильном месте: проблема была не в v33 и не в BEST, а в том, что анализировался **старый CSV от другого набора файлов**.

---

### 👤 **User** — 2026-08-15 15:33:09

int_mvp_v02

grep -R "full_analysis" -n scripts app --exclude-dir=.venv --exclude-dir=__pycache__
scripts/sort_margin005_best.py:13:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_neighbor_v34.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/dry_run_best_sequence.py:12:    / "output/benchmark_components/full_analysis/margin_best.csv"
scripts/sort_neighbor_v35.py:14:    / "output/benchmark_components/full_analysis/margin_best.csv"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -R "benchmark_v1" -n scripts app --exclude-dir=.venv --exclude-dir=__pycache__
scripts/sort_neighbor_v35_benchmark.py:12:SOURCE_JSON = PROJECT / "data/output/benchmark_v1/benchmark.json"
scripts/benchmark_test_v1.py:15:OUT_DIR = PROJECT / "data/output/benchmark_v1"
scripts/sort_neighbor_v36.py:11:SOURCE_JSON = PROJECT / "data/output/benchmark_v1/benchmark.json"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:33:10

Отлично. Теперь цепочка стала ясной.

`margin_best.csv` создаётся не из `scripts/benchmark_test_v1.py`, а, скорее всего, из:

```text
scripts/sort_neighbor_v35_benchmark.py
```

или его продолжения `sort_neighbor_v36.py`.

Они читают:

```text
data/output/benchmark_v1/benchmark.json
```

и уже делают расширенный анализ.

Смотрим сначала v35 benchmark:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

nl -ba scripts/sort_neighbor_v35_benchmark.py | sed -n '1,320p'
```

Потом v36:

```bash
nl -ba scripts/sort_neighbor_v36.py | sed -n '1,320p'
```

Нас интересует, где появляется:

```text
margin_best.csv
```

или:

```text
full_analysis
```

---

Сейчас предполагаемая цепочка:

```text
data/input/test
        |
        v
benchmark_test_v1.py
        |
        v
data/output/benchmark_v1/benchmark.json
        |
        v
sort_neighbor_v35_benchmark.py
        |
        v
output/benchmark_components/full_analysis/margin_best.csv
        |
        v
dry_run_best_sequence.py
```

После того как найдём точный генератор, делаем чистый прогон:

1. удалить старый benchmark:

```bash
rm -rf data/output/benchmark_v1
```

2. пересчитать v33:

```bash
uv run python scripts/benchmark_test_v1.py
```

3. пересобрать `margin_best.csv`

4. проверить:

```bash
uv run python scripts/dry_run_best_sequence.py
```

Только после этого можно делать выводы по BEST + SEQUENCE. Сейчас мы уже точно нашли, почему результаты были неправильные: **CSV был от старого набора фотографий.**

---

### 👤 **User** — 2026-08-15 15:33:33

int_mvp_v02

nl -ba scripts/sort_neighbor_v35_benchmark.py | sed -n '1,320p'
     1	#!/usr/bin/env python3
     2	
     3	import csv
     4	import json
     5	import shutil
     6	from pathlib import Path
     7	from collections import Counter
     8	
     9	PROJECT = Path(__file__).resolve().parent.parent
    10	
    11	INPUT_DIR = PROJECT / "data/input/test"
    12	SOURCE_JSON = PROJECT / "data/output/benchmark_v1/benchmark.json"
    13	
    14	OUTPUT_DIR = PROJECT / "output/neighbor_v35_benchmark"
    15	SORTED_DIR = OUTPUT_DIR / "sorted"
    16	REPORT_CSV = OUTPUT_DIR / "neighbor_decision.csv"
    17	
    18	MARGIN_LIMIT = 0.005
    19	NEIGHBOR_RADIUS = 2
    20	
    21	FINGERPRINTS = list(range(78, 96))
    22	
    23	
    24	def norm_id(value):
    25	    if value is None:
    26	        return None
    27	
    28	    s = str(value)
    29	
    30	    if "_" in s:
    31	        s = s.split("_")[0]
    32	
    33	    try:
    34	        return int(s)
    35	    except ValueError:
    36	        return None
    37	
    38	
    39	def load_results():
    40	    with SOURCE_JSON.open(encoding="utf-8") as f:
    41	        data = json.load(f)
    42	
    43	    results = data["results"]
    44	
    45	    # Сохраняем порядок файлов именно такой,
    46	    # в каком benchmark их распознал.
    47	    return results
    48	
    49	
    50	def candidate_ids(row):
    51	    result = []
    52	
    53	    for key in ("top1", "top2", "top3", "top4", "top5"):
    54	        value = norm_id(row.get(key))
    55	        if value is not None:
    56	            result.append(value)
    57	
    58	    return result
    59	
    60	
    61	def main():
    62	
    63	    if not SOURCE_JSON.exists():
    64	        raise RuntimeError(f"Нет benchmark: {SOURCE_JSON}")
    65	
    66	    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    67	    SORTED_DIR.mkdir(parents=True, exist_ok=True)
    68	
    69	    results = load_results()
    70	
    71	    # Для поиска соседей используем только фотографии,
    72	    # реально присутствующие в test.
    73	    results = [
    74	        r for r in results
    75	        if (INPUT_DIR / Path(r["file"]).name).exists()
    76	    ]
    77	
    78	    print("=" * 80)
    79	    print("NEIGHBOR CONTEXT V35 — NEW BENCHMARK")
    80	    print("=" * 80)
    81	    print(f"Input images : {len(results)}")
    82	    print(f"Margin limit : {MARGIN_LIMIT}")
    83	    print(f"Neighbor +/- : {NEIGHBOR_RADIUS}")
    84	    print()
    85	
    86	    decisions = []
    87	    changed = []
    88	
    89	    for i, row in enumerate(results):
    90	
    91	        image = Path(row["file"]).name
    92	
    93	        current = norm_id(row.get("top1"))
    94	        second = norm_id(row.get("top2"))
    95	
    96	        top1_score = float(row.get("top1_score") or 0)
    97	        top2_score = float(row.get("top2_score") or 0)
    98	
    99	        margin = top1_score - top2_score
   100	
   101	        final = current
   102	        reason = "V33"
   103	
   104	        second_neighbors = []
   105	        current_neighbors = []
   106	
   107	        if margin < MARGIN_LIMIT and second is not None:
   108	
   109	            start = max(0, i - NEIGHBOR_RADIUS)
   110	            end = min(len(results), i + NEIGHBOR_RADIUS + 1)
   111	
   112	            for j in range(start, end):
   113	
   114	                if j == i:
   115	                    continue
   116	
   117	                neighbor = results[j]
   118	
   119	                n_candidates = candidate_ids(neighbor)
   120	
   121	                if second in n_candidates:
   122	                    second_neighbors.append(
   123	                        (j - i, Path(neighbor["file"]).name)
   124	                    )
   125	
   126	                if current in n_candidates:
   127	                    current_neighbors.append(
   128	                        (j - i, Path(neighbor["file"]).name)
   129	                    )
   130	
   131	            # Правило:
   132	            # если второй кандидат поддержан минимум 2 соседями
   133	            # и текущий не получает больше поддержки —
   134	            # меняем на второй.
   135	            if (
   136	                len(second_neighbors) >= 2
   137	                and len(second_neighbors) > len(current_neighbors)
   138	            ):
   139	                final = second
   140	                reason = "SECOND_SUPPORTED_BY_2+_NEIGHBORS"
   141	
   142	            elif len(second_neighbors) == 1:
   143	                reason = "ONE_NEIGHBOR_KEEP_V33"
   144	
   145	            elif (
   146	                len(current_neighbors) >= 1
   147	                and len(current_neighbors) >= len(second_neighbors)
   148	            ):
   149	                reason = "CURRENT_SUPPORTED_KEEP_V33"
   150	
   151	            else:
   152	                reason = "NO_NEIGHBOR_EVIDENCE"
   153	
   154	        if final != current:
   155	            changed.append({
   156	                "image": image,
   157	                "old": current,
   158	                "new": final,
   159	                "second": second,
   160	                "margin": margin,
   161	                "reason": reason,
   162	                "second_neighbors": second_neighbors,
   163	                "current_neighbors": current_neighbors,
   164	            })
   165	
   166	        decisions.append({
   167	            "image": image,
   168	            "v33": current,
   169	            "second": second,
   170	            "final": final,
   171	            "margin": margin,
   172	            "second_neighbor_count": len(second_neighbors),
   173	            "current_neighbor_count": len(current_neighbors),
   174	            "reason": reason,
   175	            "second_neighbors": "; ".join(
   176	                f"{offset:+d}:{name}"
   177	                for offset, name in second_neighbors
   178	            ),
   179	            "current_neighbors": "; ".join(
   180	                f"{offset:+d}:{name}"
   181	                for offset, name in current_neighbors
   182	            ),
   183	        })
   184	
   185	    # ------------------------------------------------------------
   186	    # CSV
   187	    # ------------------------------------------------------------
   188	
   189	    with REPORT_CSV.open(
   190	        "w",
   191	        encoding="utf-8-sig",
   192	        newline=""
   193	    ) as f:
   194	
   195	        writer = csv.DictWriter(
   196	            f,
   197	            fieldnames=[
   198	                "image",
   199	                "v33",
   200	                "second",
   201	                "final",
   202	                "margin",
   203	                "second_neighbor_count",
   204	                "current_neighbor_count",
   205	                "reason",
   206	                "second_neighbors",
   207	                "current_neighbors",
   208	            ],
   209	        )
   210	
   211	        writer.writeheader()
   212	        writer.writerows(decisions)
   213	
   214	    # ------------------------------------------------------------
   215	    # SORTED OUTPUT
   216	    # ------------------------------------------------------------
   217	
   218	    for d in decisions:
   219	
   220	        image = d["image"]
   221	        final = d["final"]
   222	
   223	        if final is None:
   224	            continue
   225	
   226	        folder = SORTED_DIR / str(final)
   227	        folder.mkdir(parents=True, exist_ok=True)
   228	
   229	        src = INPUT_DIR / image
   230	        dst = folder / image
   231	
   232	        shutil.copy2(src, dst)
   233	
   234	    # ------------------------------------------------------------
   235	    # STATISTICS
   236	    # ------------------------------------------------------------
   237	
   238	    distribution = Counter(
   239	        d["final"]
   240	        for d in decisions
   241	        if d["final"] is not None
   242	    )
   243	
   244	    margin_count = sum(
   245	        float(d["margin"]) < MARGIN_LIMIT
   246	        for d in decisions
   247	    )
   248	
   249	    print("=" * 80)
   250	    print("RESULT")
   251	    print("=" * 80)
   252	
   253	    print(f"Total images:        {len(decisions)}")
   254	    print(f"Margin < {MARGIN_LIMIT}:      {margin_count}")
   255	    print(f"Changed by neighbors:       {len(changed)}")
   256	
   257	    print()
   258	
   259	    if changed:
   260	        print("CHANGED")
   261	        print("-" * 80)
   262	
   263	        for x in changed:
   264	            print(x["image"])
   265	            print(
   266	                f"    {x['old']} -> {x['new']}"
   267	            )
   268	            print(
   269	                f"    margin={x['margin']:.6f}"
   270	            )
   271	            print(
   272	                f"    reason={x['reason']}"
   273	            )
   274	
   275	            if x["second_neighbors"]:
   276	                print(
   277	                    "    second: "
   278	                    + "; ".join(
   279	                        f"{offset:+d}:{name}"
   280	                        for offset, name
   281	                        in x["second_neighbors"]
   282	                    )
   283	                )
   284	
   285	            print()
   286	
   287	    print("DISTRIBUTION")
   288	    print("-" * 80)
   289	
   290	    for n in FINGERPRINTS:
   291	        print(
   292	            f"{n:<4} {distribution.get(n, 0):4d}"
   293	        )
   294	
   295	    print("-" * 80)
   296	    print(
   297	        f"TOTAL {sum(distribution.values()):10d}"
   298	    )
   299	
   300	    print()
   301	    print("OUTPUT:")
   302	    print(f"  sorted : {SORTED_DIR}")
   303	    print(f"  report : {REPORT_CSV}")
   304	
   305	
   306	if __name__ == "__main__":
   307	    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 15:33:34

Отлично, теперь видно важную вещь.

`sort_neighbor_v35_benchmark.py` **не создаёт `margin_best.csv`**. Он работает напрямую с:

```python
SOURCE_JSON = PROJECT / "data/output/benchmark_v1/benchmark.json"
```

и создаёт:

```text
output/neighbor_v35_benchmark/neighbor_decision.csv
```

То есть это отдельная ветка.

А твой `margin_best.csv` относится к более поздней ветке анализа (`full_analysis`), которой в текущем `scripts` уже нет. Возможно, она была:
- временным скриптом, который потом удалили;
- частью старого benchmark pipeline;
- создана вручную/через отдельный notebook.

Но сейчас нам это даже не нужно.

### Правильный путь сейчас:

У нас есть актуальный генератор:

```text
benchmark_test_v1.py
        ↓
data/output/benchmark_v1/benchmark.json
        ↓
sort_neighbor_v35_benchmark.py
```

И он уже решает главную проблему:

```python
results = [
    r for r in results
    if (INPUT_DIR / Path(r["file"]).name).exists()
]
```

То есть он **не ломается от старых переименований**, он фильтрует только актуальные файлы.

---

Я предлагаю сейчас сделать чистый прогон v35 на текущем `test`.

### 1. Очистить старый benchmark

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf data/output/benchmark_v1
rm -rf output/neighbor_v35_benchmark
```

### 2. Пересчитать распознавание v33

```bash
uv run python scripts/benchmark_test_v1.py
```

Ожидаем:

```text
Images: 256
TOTAL: 256
```

### 3. Запустить v35

```bash
uv run python scripts/sort_neighbor_v35_benchmark.py
```

Он покажет:

```text
Total images: 256
Margin < 0.005: ...
Changed by neighbors: ...
```

---

После этого у нас будет честный результат по текущему набору.

Но ещё я замечу: твой `dry_run_best_sequence.py` сейчас анализирует **другую ветку** (`margin_best.csv`), а `v35` использует более простой и, возможно, более ранний алгоритм.

Я бы после чистого прогона v35 уже сравнил:

- v33 baseline
- v35 neighbor correction
- BEST+SEQUENCE (если восстановим генерацию `margin_best.csv`)

То есть не откатываемся — наоборот, сейчас отделяем рабочую ветку от старого мусора.

---

### 👤 **User** — 2026-08-15 15:35:38

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/benchmark_test_v1.py
================================================================================
BENCHMARK RECOGNITION
================================================================================
Images: 256
Fingerprints: 18

================================================================================
RESULTS
================================================================================
TOTAL: 256
TIME: 52.26 sec
SPEED: 4.90 images/sec

TOP-1 DISTRIBUTION
78_v33       20   7.81%
79_v33        8   3.12%
80_v33        8   3.12%
81_v33       16   6.25%
82_v33        9   3.52%
83_v33       17   6.64%
84_v33        8   3.12%
85_v33       17   6.64%
86_v33       15   5.86%
87_v33       20   7.81%
88_v33       15   5.86%
89_v33       21   8.20%
90_v33        3   1.17%
91_v33       12   4.69%
92_v33       14   5.47%
93_v33       12   4.69%
94_v33       24   9.38%
95_v33       17   6.64%

TOP-2 DISTRIBUTION
78_v33        5   1.95%
79_v33       11   4.30%
80_v33        5   1.95%
81_v33        2   0.78%
82_v33        9   3.52%
83_v33       11   4.30%
84_v33       15   5.86%
85_v33        9   3.52%
86_v33       10   3.91%
87_v33       15   5.86%
88_v33        1   0.39%
89_v33       10   3.91%
90_v33        2   0.78%
91_v33       39  15.23%
92_v33       47  18.36%
93_v33       31  12.11%
94_v33       22   8.59%
95_v33       12   4.69%

---

### 🤖 **Assistant** — 2026-08-15 15:35:39

Отлично. Теперь у нас есть **чистый benchmark на текущем наборе 256 файлов**.

Главное:

```text
TOTAL: 256
TIME: 52.26 sec
SPEED: 4.90 images/sec
```

То есть пересчёт прошёл корректно.

Теперь интересная часть — распределение.

### Что видно по TOP-1

Лидеры:

```
94_v33   24
89_v33   21
78_v33   20
87_v33   20
81_v33   16
83_v33   17
85_v33   17
95_v33   17
```

Распределение достаточно равномерное — это хорошо, значит нет явного "залипания" одной локации.

---

### Но очень интересно TOP-2:

```
92_v33   47 (18.36%)
91_v33   39 (15.23%)
93_v33   31 (12.11%)
94_v33   22 (8.59%)
```

Это означает, что **вторые кандидаты очень часто находятся в группе 91–94**.

Вероятнее всего:

- эти адреса визуально очень похожи;
- возможно, там одинаковые дома/фасады/ракурсы;
- именно здесь должен помочь последовательный анализ.

То есть наш BEST + SEQUENCE подход как раз имеет смысл.

---

Следующий шаг:

запускаем соседний анализ v35:

```bash
uv run python scripts/sort_neighbor_v35_benchmark.py
```

Он сейчас будет уже работать правильно:

```text
benchmark.json
        ↓
256 актуальных файлов
        ↓
neighbor_v35
```

Посмотрим:

1. сколько кадров имеют маленький margin;
2. сколько реально меняются соседями;
3. какие именно адреса перекидываются.

После этого будет понятно, стоит ли возвращать более сильную логику BEST+SEQUENCE или v35 уже закрывает проблему.

Запускай v35.

---

