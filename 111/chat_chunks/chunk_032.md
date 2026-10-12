## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 👤 **User** — 2026-08-15 03:07:11

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

diff -u \
  app/core/scene_analyzer.py.backup_before_optimization \
  app/core/scene_analyzer.py \
  > /tmp/scene_analyzer_diff.txt

echo "=== DIFF SIZE ==="
wc -l /tmp/scene_analyzer_diff.txt

echo
echo "=== DIFF ==="
cat /tmp/scene_analyzer_diff.txt
=== DIFF SIZE ===
249 /tmp/scene_analyzer_diff.txt

=== DIFF ===
--- app/core/scene_analyzer.py.backup_before_optimization	2026-08-14 23:56:43.519007834 +0300
+++ app/core/scene_analyzer.py	2026-08-15 00:26:48.823804479 +0300
@@ -10,7 +10,10 @@
     """
     Scene Fingerprint v3.3 compact descriptors.
 
-    No DINOv2 patch tokens.
+    Optimized version.
+
+    The image is loaded/resized once and the three
+    descriptors are calculated from the same image.
 
     environment:
         8x8 grid x 10 values = 640 floats
@@ -61,9 +64,7 @@
         return vector.astype(np.float32)
 
     @classmethod
-    def environment(cls, path: Path):
-        image = cls._load(path)
-
+    def environment_from_image(cls, image):
         hsv = cv2.cvtColor(
             image,
             cv2.COLOR_BGR2HSV,
@@ -138,9 +139,12 @@
         )
 
     @classmethod
-    def color(cls, path: Path):
+    def environment(cls, path: Path):
         image = cls._load(path)
+        return cls.environment_from_image(image)
 
+    @classmethod
+    def color_from_image(cls, image):
         hsv = cv2.cvtColor(
             image,
             cv2.COLOR_BGR2HSV,
@@ -181,9 +185,12 @@
         return cls._normalize(descriptor)
 
     @classmethod
-    def spatial(cls, path: Path):
+    def color(cls, path: Path):
         image = cls._load(path)
+        return cls.color_from_image(image)
 
+    @classmethod
+    def spatial_from_image(cls, image):
         gray = cv2.cvtColor(
             image,
             cv2.COLOR_BGR2GRAY,
@@ -218,6 +225,34 @@
             )
         )
 
+    @classmethod
+    def spatial(cls, path: Path):
+        image = cls._load(path)
+        return cls.spatial_from_image(image)
+
+    @classmethod
+    def all_from_image(cls, image):
+        """
+        Calculate all compact descriptors from one already
+        loaded/resized image.
+
+        Returns:
+            environment: 640
+            color:       48
+            spatial:     32
+        """
+
+        return (
+            cls.environment_from_image(image),
+            cls.color_from_image(image),
+            cls.spatial_from_image(image),
+        )
+
+    @classmethod
+    def all(cls, path: Path):
+        image = cls._load(path)
+        return cls.all_from_image(image)
+
 
 class SceneAnalyzer:
     """
@@ -225,9 +260,9 @@
 
     Weights:
         global       0.70
-        environment 0.20
-        color       0.07
-        spatial     0.03
+        environment  0.20
+        color        0.07
+        spatial      0.03
 
     Patch storage is disabled.
     """
@@ -310,7 +345,6 @@
 
         scores = refs @ q
 
-        # Strongest 10%, but at least 3 images.
         k = max(
             3,
             int(len(scores) * 0.10),
@@ -331,16 +365,35 @@
         self,
         image_path: Path,
         fingerprint_id: str,
+        query_global=None,
+        query_environment=None,
+        query_color=None,
+        query_spatial=None,
     ):
+        """
+        Compare one image against one fingerprint.
+
+        For fast recognition the query descriptors can be
+        supplied already calculated by the recognizer.
+
+        If they are not supplied, calculate them here for
+        backward compatibility with `analyze`.
+        """
+
         data = self.manager.load(
             fingerprint_id
         )
 
-        query_global = (
-            self.embedder.embed_paths(
-                [Path(image_path)]
-            )[0]
-        )
+        # --------------------------------------------------
+        # GLOBAL DINO
+        # --------------------------------------------------
+
+        if query_global is None:
+            query_global = (
+                self.embedder.embed_paths(
+                    [Path(image_path)]
+                )[0]
+            )
 
         query_global = np.asarray(
             query_global,
@@ -382,11 +435,26 @@
                 best_index
             )
 
-        query_environment = (
-            CompactDescriptor.environment(
+        # --------------------------------------------------
+        # COMPACT DESCRIPTORS
+        # --------------------------------------------------
+
+        if (
+            query_environment is None
+            or query_color is None
+            or query_spatial is None
+        ):
+            image = CompactDescriptor._load(
                 Path(image_path)
             )
-        )
+
+            (
+                query_environment,
+                query_color,
+                query_spatial,
+            ) = CompactDescriptor.all_from_image(
+                image
+            )
 
         environment_score = (
             self.descriptor_similarity(
@@ -397,12 +465,6 @@
             )
         )
 
-        query_color = (
-            CompactDescriptor.color(
-                Path(image_path)
-            )
-        )
-
         color_score = (
             self.descriptor_similarity(
                 query_color,
@@ -412,12 +474,6 @@
             )
         )
 
-        query_spatial = (
-            CompactDescriptor.spatial(
-                Path(image_path)
-            )
-        )
-
         spatial_score = (
             self.descriptor_similarity(
                 query_spatial,
@@ -427,6 +483,10 @@
             )
         )
 
+        # --------------------------------------------------
+        # FINAL SCORE
+        # --------------------------------------------------
+
         final_score = (
             self.GLOBAL_WEIGHT
             * global_score
@@ -442,23 +502,31 @@
             "global_score": float(
                 global_score
             ),
+
             "best_image_score": float(
                 best_image_score
             ),
+
             "patch_score": 0.0,
+
             "color_score": float(
                 color_score
             ),
+
             "spatial_score": float(
                 spatial_score
             ),
+
             "environment_score": float(
                 environment_score
             ),
+
             "final_score": float(
                 final_score
             ),
+
             "best_image": best_image,
+
             "fingerprint_version": (
                 data["metadata"]
                 .get(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=============================================="
echo "=== OLD compare() ==="
echo "=============================================="

nl -ba app/core/scene_analyzer.py.backup_before_optimization \
  | sed -n '350,530p'

echo
echo "=============================================="
echo "=== CURRENT compare() ==="
echo "=============================================="

nl -ba app/core/scene_analyzer.py \
  | sed -n '350,530p'

==============================================
=== OLD compare() ===
==============================================
   350	        global_score = self.cosine(
   351	            query_global,
   352	            data["centroid"],
   353	        )
   354	
   355	        image_scores = (
   356	            data["embeddings"]
   357	            @ query_global
   358	        )
   359	
   360	        best_index = int(
   361	            np.argmax(image_scores)
   362	        )
   363	
   364	        best_image_score = float(
   365	            image_scores[best_index]
   366	        )
   367	
   368	        image_names = (
   369	            data["metadata"]
   370	            .get(
   371	                "image_names",
   372	                [],
   373	            )
   374	        )
   375	
   376	        if best_index < len(image_names):
   377	            best_image = image_names[
   378	                best_index
   379	            ]
   380	        else:
   381	            best_image = str(
   382	                best_index
   383	            )
   384	
   385	        query_environment = (
   386	            CompactDescriptor.environment(
   387	                Path(image_path)
   388	            )
   389	        )
   390	
   391	        environment_score = (
   392	            self.descriptor_similarity(
   393	                query_environment,
   394	                data[
   395	                    "environment_embeddings"
   396	                ],
   397	            )
   398	        )
   399	
   400	        query_color = (
   401	            CompactDescriptor.color(
   402	                Path(image_path)
   403	            )
   404	        )
   405	
   406	        color_score = (
   407	            self.descriptor_similarity(
   408	                query_color,
   409	                data[
   410	                    "color_embeddings"
   411	                ],
   412	            )
   413	        )
   414	
   415	        query_spatial = (
   416	            CompactDescriptor.spatial(
   417	                Path(image_path)
   418	            )
   419	        )
   420	
   421	        spatial_score = (
   422	            self.descriptor_similarity(
   423	                query_spatial,
   424	                data[
   425	                    "spatial_embeddings"
   426	                ],
   427	            )
   428	        )
   429	
   430	        final_score = (
   431	            self.GLOBAL_WEIGHT
   432	            * global_score
   433	            + self.ENVIRONMENT_WEIGHT
   434	            * environment_score
   435	            + self.COLOR_WEIGHT
   436	            * color_score
   437	            + self.SPATIAL_WEIGHT
   438	            * spatial_score
   439	        )
   440	
   441	        return {
   442	            "global_score": float(
   443	                global_score
   444	            ),
   445	            "best_image_score": float(
   446	                best_image_score
   447	            ),
   448	            "patch_score": 0.0,
   449	            "color_score": float(
   450	                color_score
   451	            ),
   452	            "spatial_score": float(
   453	                spatial_score
   454	            ),
   455	            "environment_score": float(
   456	                environment_score
   457	            ),
   458	            "final_score": float(
   459	                final_score
   460	            ),
   461	            "best_image": best_image,
   462	            "fingerprint_version": (
   463	                data["metadata"]
   464	                .get(
   465	                    "version",
   466	                    "3.3",
   467	                )
   468	            ),
   469	        }
   470	
   471	    def analyze(
   472	        self,
   473	        folder,
   474	        fingerprint_id,
   475	    ):
   476	        from .image import image_files
   477	
   478	        paths = image_files(folder)
   479	
   480	        for path in paths:
   481	            result = self.compare(
   482	                Path(path),
   483	                fingerprint_id,
   484	            )
   485	
   486	            result["file"] = str(path)
   487	
   488	            yield result

==============================================
=== CURRENT compare() ===
==============================================
   350	            int(len(scores) * 0.10),
   351	        )
   352	
   353	        k = min(
   354	            k,
   355	            len(scores),
   356	        )
   357	
   358	        return float(
   359	            np.mean(
   360	                np.sort(scores)[-k:]
   361	            )
   362	        )
   363	
   364	    def compare(
   365	        self,
   366	        image_path: Path,
   367	        fingerprint_id: str,
   368	        query_global=None,
   369	        query_environment=None,
   370	        query_color=None,
   371	        query_spatial=None,
   372	    ):
   373	        """
   374	        Compare one image against one fingerprint.
   375	
   376	        For fast recognition the query descriptors can be
   377	        supplied already calculated by the recognizer.
   378	
   379	        If they are not supplied, calculate them here for
   380	        backward compatibility with `analyze`.
   381	        """
   382	
   383	        data = self.manager.load(
   384	            fingerprint_id
   385	        )
   386	
   387	        # --------------------------------------------------
   388	        # GLOBAL DINO
   389	        # --------------------------------------------------
   390	
   391	        if query_global is None:
   392	            query_global = (
   393	                self.embedder.embed_paths(
   394	                    [Path(image_path)]
   395	                )[0]
   396	            )
   397	
   398	        query_global = np.asarray(
   399	            query_global,
   400	            dtype=np.float32,
   401	        )
   402	
   403	        global_score = self.cosine(
   404	            query_global,
   405	            data["centroid"],
   406	        )
   407	
   408	        image_scores = (
   409	            data["embeddings"]
   410	            @ query_global
   411	        )
   412	
   413	        best_index = int(
   414	            np.argmax(image_scores)
   415	        )
   416	
   417	        best_image_score = float(
   418	            image_scores[best_index]
   419	        )
   420	
   421	        image_names = (
   422	            data["metadata"]
   423	            .get(
   424	                "image_names",
   425	                [],
   426	            )
   427	        )
   428	
   429	        if best_index < len(image_names):
   430	            best_image = image_names[
   431	                best_index
   432	            ]
   433	        else:
   434	            best_image = str(
   435	                best_index
   436	            )
   437	
   438	        # --------------------------------------------------
   439	        # COMPACT DESCRIPTORS
   440	        # --------------------------------------------------
   441	
   442	        if (
   443	            query_environment is None
   444	            or query_color is None
   445	            or query_spatial is None
   446	        ):
   447	            image = CompactDescriptor._load(
   448	                Path(image_path)
   449	            )
   450	
   451	            (
   452	                query_environment,
   453	                query_color,
   454	                query_spatial,
   455	            ) = CompactDescriptor.all_from_image(
   456	                image
   457	            )
   458	
   459	        environment_score = (
   460	            self.descriptor_similarity(
   461	                query_environment,
   462	                data[
   463	                    "environment_embeddings"
   464	                ],
   465	            )
   466	        )
   467	
   468	        color_score = (
   469	            self.descriptor_similarity(
   470	                query_color,
   471	                data[
   472	                    "color_embeddings"
   473	                ],
   474	            )
   475	        )
   476	
   477	        spatial_score = (
   478	            self.descriptor_similarity(
   479	                query_spatial,
   480	                data[
   481	                    "spatial_embeddings"
   482	                ],
   483	            )
   484	        )
   485	
   486	        # --------------------------------------------------
   487	        # FINAL SCORE
   488	        # --------------------------------------------------
   489	
   490	        final_score = (
   491	            self.GLOBAL_WEIGHT
   492	            * global_score
   493	            + self.ENVIRONMENT_WEIGHT
   494	            * environment_score
   495	            + self.COLOR_WEIGHT
   496	            * color_score
   497	            + self.SPATIAL_WEIGHT
   498	            * spatial_score
   499	        )
   500	
   501	        return {
   502	            "global_score": float(
   503	                global_score
   504	            ),
   505	
   506	            "best_image_score": float(
   507	                best_image_score
   508	            ),
   509	
   510	            "patch_score": 0.0,
   511	
   512	            "color_score": float(
   513	                color_score
   514	            ),
   515	
   516	            "spatial_score": float(
   517	                spatial_score
   518	            ),
   519	
   520	            "environment_score": float(
   521	                environment_score
   522	            ),
   523	
   524	            "final_score": float(
   525	                final_score
   526	            ),
   527	
   528	            "best_image": best_image,
   529	
   530	            "fingerprint_version": (
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:07:12

Да. По этим выводам уже видно главное:

- `final_test_78_95.json` **не создаётся `classify_final_test.py`** — он только читает его.
- Основной `recognize` идёт через `app/core/recognizer.py → SceneRecognizer.recognize_folder()`.
- Текущий `scene_analyzer.py` отличается от `backup_before_optimization` **не алгоритмом распознавания, а оптимизацией вычислений**.
- В `compare()` математическая формула `final_score` осталась той же:
  - global — 0.70
  - environment — 0.20
  - color — 0.07
  - spatial — 0.03
- Оптимизация сейчас делает разумную вещь: загружает/resize изображение один раз и считает три compact descriptor'а из него.
- Но есть **очень важный момент**: нужно проверить `recognizer.py`, потому что именно там определяется порядок кандидатов и формируется `best_id`. `classify_final_test.py` затем просто раскладывает уже полученный результат по `best_id`.

То есть сейчас **не надо откатывать `scene_analyzer.py` целиком**. Наша цель — сохранить оптимизацию, но убедиться, что старый алгоритм выбора первого кандидата не был изменён.

Давай следующим шагом посмотрим именно `recognizer.py`, особенно участок `recognize_folder()` и место, где вызывается `analyzer.compare()`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== CURRENT recognizer.py ==="
echo "=============================================="

nl -ba app/core/recognizer.py | sed -n '1,560p'
```

И отдельно сразу:

```bash
echo
echo "=============================================="
echo "=== ALL analyzer.compare CALLS ==="
echo "=============================================="

grep -Rni \
'compare(' \
--include='*.py' \
--exclude-dir=.venv \
--exclude-dir=.git \
app scripts classify*.py
```

И ещё очень полезная проверка:

```bash
echo
echo "=============================================="
echo "=== BEST_ID / CANDIDATES LOGIC ==="
echo "=============================================="

grep -RniE \
'best_id|candidates|top_k|threshold|final_score|fingerprint_id' \
--include='*.py' \
--include='*.sh' \
--exclude-dir=.venv \
--exclude-dir=.git \
app scripts classify*.py \
| head -300
```

**После этого мы сможем точно сказать**, что произошло:

`фото → DINO → кандидаты → первый кандидат → адрес`

и отдельно:

`фото → compact descriptors`

При этом оптимизацию загрузки изображения оставим. Если окажется, что именно алгоритм выбора кандидата был изменён, восстановим **старую логику выбора**, не возвращая старую медленную реализацию.

---

### 👤 **User** — 2026-08-15 03:07:55

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== CURRENT recognizer.py ==="
echo "=============================================="

nl -ba app/core/recognizer.py | sed -n '1,560p'
==============================================
=== CURRENT recognizer.py ===
==============================================
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=============================================="
echo "=== ALL analyzer.compare CALLS ==="
echo "=============================================="

grep -Rni \
'compare(' \
--include='*.py' \
--exclude-dir=.venv \
--exclude-dir=.git \
app scripts classify*.py

==============================================
=== ALL analyzer.compare CALLS ===
==============================================
app/core/scene_analyzer.py:364:    def compare(
app/core/scene_analyzer.py:549:            result = self.compare(
app/core/recognizer.py:288:                    score = self.analyzer.compare(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=============================================="
echo "=== BEST_ID / CANDIDATES LOGIC ==="
echo "=============================================="

grep -RniE \
'best_id|candidates|top_k|threshold|final_score|fingerprint_id' \
--include='*.py' \
--include='*.sh' \
--exclude-dir=.venv \
--exclude-dir=.git \
app scripts classify*.py \
| head -300

==============================================
=== BEST_ID / CANDIDATES LOGIC ===
==============================================
app/core/scene_analyzer.py:367:        fingerprint_id: str,
app/core/scene_analyzer.py:384:            fingerprint_id
app/core/scene_analyzer.py:490:        final_score = (
app/core/scene_analyzer.py:524:            "final_score": float(
app/core/scene_analyzer.py:525:                final_score
app/core/scene_analyzer.py:542:        fingerprint_id,
app/core/scene_analyzer.py:551:                fingerprint_id,
app/core/recognizer.py:100:        top_k=5,
app/core/recognizer.py:101:        threshold=0.65,
app/core/recognizer.py:135:            fingerprint_id = (
app/core/recognizer.py:139:            if not fingerprint_id:
app/core/recognizer.py:144:                and str(fingerprint_id)
app/core/recognizer.py:151:                    fingerprint_id
app/core/recognizer.py:162:                    f"{fingerprint_id}: "
app/core/recognizer.py:178:                    f"{fingerprint_id}"
app/core/recognizer.py:185:                    fingerprint_id,
app/core/recognizer.py:283:            for fingerprint_id, data in loaded_fingerprints:
app/core/recognizer.py:290:                        fingerprint_id,
app/core/recognizer.py:311:                        f"{fingerprint_id} "
app/core/recognizer.py:321:                        "id": fingerprint_id,
app/core/recognizer.py:325:                                "final_score",
app/core/recognizer.py:381:                    int(top_k),
app/core/recognizer.py:389:                        "best_id": None,
app/core/recognizer.py:395:                        "candidates": [],
app/core/recognizer.py:434:            # The threshold is NO LONGER a rejection gate.
app/core/recognizer.py:438:            if best_score < threshold:
app/core/recognizer.py:439:                best_id = None
app/core/recognizer.py:442:                best_id = best["id"]
app/core/recognizer.py:451:                    "best_id": best_id,
app/core/recognizer.py:478:                    "candidates": ranked,
app/core/recognizer.py:487:        top_k=5,
app/core/recognizer.py:488:        threshold=0.65,
app/core/recognizer.py:492:            top_k=top_k,
app/core/recognizer.py:493:            threshold=threshold,
app/core/fingerprint.py:53:        fingerprint_id,
app/core/fingerprint.py:57:            / str(fingerprint_id)
app/core/fingerprint.py:153:        fingerprint_id,
app/core/fingerprint.py:157:        fingerprint_id = str(
app/core/fingerprint.py:158:            fingerprint_id
app/core/fingerprint.py:171:            fingerprint_id
app/core/fingerprint.py:181:                    f"Fingerprint '{fingerprint_id}' "
app/core/fingerprint.py:198:            f"Creating '{fingerprint_id}' "
app/core/fingerprint.py:379:            "id": fingerprint_id,
app/core/fingerprint.py:457:        fingerprint_id,
app/core/fingerprint.py:459:        fingerprint_id = str(
app/core/fingerprint.py:460:            fingerprint_id
app/core/fingerprint.py:464:            fingerprint_id
app/core/fingerprint.py:470:                f"'{fingerprint_id}' "
app/core/fingerprint.py:497:                f"'{fingerprint_id}' "
app/core/fingerprint.py:521:                f"'{fingerprint_id}' "
app/core/fingerprint.py:529:            "id": fingerprint_id,
app/pipeline/worker.py:36:        fingerprint_id = job["fingerprint_id"]
app/pipeline/worker.py:44:        print(f"[Worker] Fingerprint: {fingerprint_id}")
app/pipeline/worker.py:50:                fingerprint_id,
app/pipeline/worker.py:60:                f"[Worker] DONE: {fingerprint_id}"
app/pipeline/worker.py:73:                f"{fingerprint_id}: {exc}"
app/pipeline/queue.py:53:                    fingerprint_id TEXT NOT NULL,
app/pipeline/queue.py:84:        fingerprint_id: str,
app/pipeline/queue.py:94:                    fingerprint_id,
app/pipeline/queue.py:104:                    str(fingerprint_id),
app/main.py:42:            threshold = ui.number("Порог", value=0.65, min=0, max=1, step=0.01).classes("w-32")
app/main.py:49:                        folder2.value, int(topk.value), float(threshold.value)
app/main.py:55:                                f"{row['best_id'] or 'UNKNOWN'} "
app/main.py:58:                            for c in row["candidates"]:
app/cli.py:141:        help="Number of candidates",
app/cli.py:145:        "--threshold",
app/cli.py:216:        f"{result['final_score']:.4f}"
app/cli.py:238:    best_id = result.get(
app/cli.py:239:        "best_id"
app/cli.py:275:        f"{best_id or 'NONE'}"
app/cli.py:313:    candidates = result.get(
app/cli.py:314:        "candidates",
app/cli.py:318:    if candidates:
app/cli.py:321:            "TOP CANDIDATES"
app/cli.py:325:            candidates,
app/cli.py:358:            fingerprint_id=args.fingerprint,
app/cli.py:441:        for fingerprint_id in range(
app/cli.py:445:            fingerprint_id = str(
app/cli.py:446:                fingerprint_id
app/cli.py:452:                / fingerprint_id
app/cli.py:486:                / fingerprint_id
app/cli.py:492:                    f"{fingerprint_id}"
app/cli.py:500:                str(job["fingerprint_id"])
app/cli.py:501:                == fingerprint_id
app/cli.py:514:                    f"{fingerprint_id}"
app/cli.py:521:                fingerprint_id,
app/cli.py:527:                f"{fingerprint_id} "
app/cli.py:631:                top_k=args.top_k,
app/cli.py:632:                threshold=args.threshold,
app/ocr/plate_detector.py:44:    _, mask = cv2.threshold(
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
scripts/sort_test_and_report_v2.py:103:        "--threshold",
scripts/sort_test_and_report_v2.py:164:        # ВСЕГДА используем best_id = первый кандидат.
scripts/sort_test_and_report_v2.py:165:        assigned_id = item.get("best_id")
scripts/sort_test_and_report_v2.py:179:        candidates = item.get("candidates", [])
scripts/sort_test_and_report_v2.py:206:        if candidates:
scripts/sort_test_and_report_v2.py:207:            c = candidates[0]
scripts/sort_test_and_report_v2.py:214:        for n in range(1, min(5, len(candidates))):
scripts/sort_test_and_report_v2.py:215:            c = candidates[n]
scripts/make_subfingerprints_v2.py:26:CORE_THRESHOLD = 0.84
scripts/make_subfingerprints_v2.py:146:        candidates = [
scripts/make_subfingerprints_v2.py:148:            if S[seed, i] >= CORE_THRESHOLD
scripts/make_subfingerprints_v2.py:152:        if len(candidates) > MAX_CORE:
scripts/make_subfingerprints_v2.py:153:            candidates = sorted(
scripts/make_subfingerprints_v2.py:154:                candidates,
scripts/make_subfingerprints_v2.py:161:        if len(candidates) < MIN_CORE:
scripts/make_subfingerprints_v2.py:167:            "members": sorted(candidates),
scripts/make_subfingerprints_v2.py:174:        for i in candidates:
scripts/make_subfingerprints_v2.py:311:            "threshold": CORE_THRESHOLD,
scripts/make_subfingerprints_v2.py:381:    print(f"CORE_THRESHOLD: {CORE_THRESHOLD}")
scripts/benchmark_test_v1.py:97:        "--threshold",
scripts/benchmark_test_v1.py:184:        candidates = x.get("candidates", [])
scripts/benchmark_test_v1.py:188:            for c in candidates[:5]
scripts/benchmark_test_v1.py:193:            for c in candidates[:5]
scripts/sort_test_and_report.py:108:        best_id = item["best_id"]
scripts/sort_test_and_report.py:111:        if best_id.endswith("_v33"):
scripts/sort_test_and_report.py:112:            address = best_id[:-4]
scripts/sort_test_and_report.py:114:            address = best_id
scripts/sort_test_and_report.py:139:        candidates = item.get("candidates", [])
scripts/sort_test_and_report.py:152:            "fingerprint": best_id,
scripts/sort_baseline.py:47:        best_id = item["best_id"]
scripts/sort_baseline.py:48:        folder = best_id.replace("_v33", "")
scripts/sort_baseline.py:52:            folder = best_id
scripts/sort_baseline.py:74:        counts[best_id] += 1
scripts/sort_baseline.py:79:            "assigned_id": best_id,
scripts/sort_baseline.py:82:                item["candidates"][1]["id"]
scripts/sort_baseline.py:83:                if len(item.get("candidates", [])) > 1
scripts/sort_baseline.py:93:                item["candidates"][0].get("global")
scripts/sort_baseline.py:94:                if item.get("candidates")
scripts/sort_baseline.py:98:                item["candidates"][0].get("environment")
scripts/sort_baseline.py:99:                if item.get("candidates")
scripts/sort_baseline.py:103:                item["candidates"][0].get("color")
scripts/sort_baseline.py:104:                if item.get("candidates")
scripts/sort_baseline.py:108:                item["candidates"][0].get("spatial")
scripts/sort_baseline.py:109:                if item.get("candidates")
classify_final_test.py:57:    best_id = r.get(
classify_final_test.py:58:        "best_id"
classify_final_test.py:61:    # Если best_id отсутствует,
classify_final_test.py:63:    if not best_id:
classify_final_test.py:65:        candidates = r.get(
classify_final_test.py:66:            "candidates",
classify_final_test.py:70:        if candidates:
classify_final_test.py:71:            best_id = candidates[0].get(
classify_final_test.py:76:    if not best_id:
classify_final_test.py:80:            best_id
classify_test.py:31:TOP_K = 5
classify_test.py:34:THRESHOLD = 0.65
classify_test.py:231:    fingerprint_ids = (
classify_test.py:235:    if not fingerprint_ids:
classify_test.py:246:        f"{len(fingerprint_ids)}"
classify_test.py:252:            fingerprint_ids
classify_test.py:314:        top_k=TOP_K,
classify_test.py:315:        threshold=THRESHOLD,
classify_test.py:342:    for fp in fingerprint_ids:
classify_test.py:378:            best_id = ""
classify_test.py:388:            best_id = result.get(
classify_test.py:389:                "best_id"
classify_test.py:443:            } and best_id:
classify_test.py:446:                    str(best_id)
classify_test.py:489:                "best_id": best_id or "",
classify_test.py:534:                "best_id",
classify_test_results.py:96:    best_id = r.get(
classify_test_results.py:97:        "best_id"
classify_test_results.py:121:    if not best_id:
classify_test_results.py:122:        best_id = "NO_MATCH"
classify_test_results.py:127:        / str(best_id)
classify_test_results.py:136:        str(best_id),
classify_test_results.py:140:    stats[str(best_id)] += 1
classify_test_results.py:151:            / str(best_id)
classify_test_results.py:168:            / str(best_id)
classify_test_results.py:191:for fingerprint_id in sorted(
classify_test_results.py:209:        f"{fingerprint_id:20} "
classify_test_results.py:210:        f"{stats[fingerprint_id]:4d}"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:07:56

Да. По этим выводам уже видно главное: **оптимизация `scene_analyzer.py` не изменила сам алгоритм распознавания v3.3**. Она в основном убрала повторную загрузку/обработку изображения.

Но есть один важный момент, который стоит проверить перед финальным тестом:

- `recognizer.py` действительно вызывает `analyzer.compare()`;
- в `compare()` формула `final_score` осталась прежней;
- веса остались `0.70 / 0.20 / 0.07 / 0.03`;
- `best_image_score` и `best_image` определяются тем же способом;
- сортировка кандидатов идёт по `final_score`;
- `classify_final_test.py` берёт `best_id`, а если его нет — первый `candidates[0]`.

То есть цепочка сейчас такая:

```text
фотография
   ↓
DINO global embedding
   ↓
compact descriptors
   ├── environment
   ├── color
   └── spatial
   ↓
SceneAnalyzer.compare()
   ↓
final_score
   ↓
sort candidates DESC
   ↓
candidates[0]
   ↓
best_id
   ↓
classify_final_test.py
```

### Но я вижу небольшую нестыковку

В `recognizer.py` написано:

```python
# Always use the best available candidate.
#
# The threshold is NO LONGER a rejection gate.
```

но ниже фактически:

```python
if best_score < threshold:
    best_id = None
    status = "NO_MATCH"
else:
    best_id = best["id"]
```

То есть **threshold всё-таки является воротами для `best_id`**.

Однако `classify_final_test.py` специально делает fallback:

```python
if not best_id:
    candidates = r.get("candidates", [])
    if candidates:
        best_id = candidates[0].get("id")
```

Поэтому для `final_test_78_95.json` итоговый адрес всё равно может быть взят из первого кандидата.

---

## Сейчас я бы не менял код

У нас уже есть хороший контрольный вариант:

```text
scene_analyzer.py.backup_before_optimization
```

и текущая оптимизированная версия.

Следующий шаг — **не трогая код, проверить, что результаты старой и новой логики идентичны**.

Причём лучше проверить не весь проект, а именно функцию `compare()` на нескольких фотографиях и нескольких `_v33`.

Дай сейчас вот эту команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== CURRENT WEIGHTS ==="
echo "=============================================="

grep -nE \
'GLOBAL_WEIGHT|ENVIRONMENT_WEIGHT|COLOR_WEIGHT|SPATIAL_WEIGHT' \
app/core/scene_analyzer.py

echo
echo "=============================================="
echo "=== CURRENT RECOGNIZER SETTINGS ==="
echo "=============================================="

grep -nE \
'VERSION|HIGH_SCORE|PROBABLE_SCORE|HIGH_MARGIN|PROBABLE_MARGIN|threshold=' \
app/core/recognizer.py

echo
echo "=============================================="
echo "=== FINAL TEST SCRIPT ==="
echo "=============================================="

nl -ba classify_final_test.py | sed -n '1,180p'

echo
echo "=============================================="
echo "=== RESULT FILE INFO ==="
echo "=============================================="

ls -lh final_test_78_95.json 2>/dev/null || echo "final_test_78_95.json NOT FOUND"
```

**После этого уже проверим сам `final_test_78_95.json`:** сколько фотографий, какие `best_id`, распределение по 78–95 и несколько первых кандидатов. Это даст нам фактическое подтверждение, что текущий v33 работает именно так, как мы хотели.

---

### 👤 **User** — 2026-08-15 03:08:40

давай

---

### 🤖 **Assistant** — 2026-08-15 03:08:41

Давай. Выполни **целиком** этот блок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== CURRENT WEIGHTS ==="
echo "=============================================="

grep -nE \
'GLOBAL_WEIGHT|ENVIRONMENT_WEIGHT|COLOR_WEIGHT|SPATIAL_WEIGHT' \
app/core/scene_analyzer.py

echo
echo "=============================================="
echo "=== CURRENT RECOGNIZER SETTINGS ==="
echo "=============================================="

grep -nE \
'VERSION|HIGH_SCORE|PROBABLE_SCORE|HIGH_MARGIN|PROBABLE_MARGIN|threshold=' \
app/core/recognizer.py

echo
echo "=============================================="
echo "=== FINAL TEST SCRIPT ==="
echo "=============================================="

nl -ba classify_final_test.py | sed -n '1,180p'

echo
echo "=============================================="
echo "=== RESULT FILE INFO ==="
echo "=============================================="

ls -lh final_test_78_95.json 2>/dev/null || \
echo "final_test_78_95.json NOT FOUND"
```

Пришли вывод сюда. **Пока ничего в коде не меняем.** После этого проверим фактические результаты `78–95` и только потом решим, нужен ли возврат какой-либо части старой логики.

---

### 👤 **User** — 2026-08-15 03:08:59

==============================================
=== FINAL TEST SCRIPT ===
==============================================
     1	from pathlib import Path
     2	import json
     3	import shutil
     4	
     5	RESULTS = Path("final_test_78_95.json")
     6	SOURCE = Path("data/input/test")
     7	OUTPUT = Path("data/output/test_classified")
     8	
     9	OUTPUT.mkdir(
    10	    parents=True,
    11	    exist_ok=True,
    12	)
    13	
    14	# --------------------------------------------------
    15	# LOAD JSON
    16	# --------------------------------------------------
    17	
    18	lines = RESULTS.read_text(
    19	    encoding="utf-8"
    20	).splitlines()
    21	
    22	start = None
    23	
    24	for i, line in enumerate(lines):
    25	    if line.strip() == "[":
    26	        start = i
    27	        break
    28	
    29	if start is None:
    30	    raise RuntimeError(
    31	        "JSON array not found"
    32	    )
    33	
    34	data = json.loads(
    35	    "\n".join(lines[start:])
    36	)
    37	
    38	print(
    39	    f"Results loaded: {len(data)}"
    40	)
    41	
    42	# --------------------------------------------------
    43	# COPY BY TOP-1
    44	# --------------------------------------------------
    45	
    46	counts = {}
    47	
    48	for r in data:
    49	
    50	    file_path = Path(
    51	        r["file"]
    52	    )
    53	
    54	    filename = file_path.name
    55	
    56	    # TOP-1 ALWAYS WINS
    57	    best_id = r.get(
    58	        "best_id"
    59	    )
    60	
    61	    # Если best_id отсутствует,
    62	    # берём первого кандидата.
    63	    if not best_id:
    64	
    65	        candidates = r.get(
    66	            "candidates",
    67	            []
    68	        )
    69	
    70	        if candidates:
    71	            best_id = candidates[0].get(
    72	                "id"
    73	            )
    74	
    75	    # Только если вообще нет кандидата
    76	    if not best_id:
    77	        folder_name = "NO_CANDIDATE"
    78	    else:
    79	        folder_name = str(
    80	            best_id
    81	        )
    82	
    83	    destination_dir = (
    84	        OUTPUT / folder_name
    85	    )
    86	
    87	    destination_dir.mkdir(
    88	        parents=True,
    89	        exist_ok=True,
    90	    )
    91	
    92	    source_file = (
    93	        SOURCE / filename
    94	    )
    95	
    96	    if not source_file.exists():
    97	
    98	        if file_path.exists():
    99	            source_file = file_path
   100	
   101	        else:
   102	            print(
   103	                f"[WARNING] "
   104	                f"Source not found: "
   105	                f"{filename}"
   106	            )
   107	            continue
   108	
   109	    destination_file = (
   110	        destination_dir
   111	        / filename
   112	    )
   113	
   114	    # Защита от одинаковых имён
   115	    if destination_file.exists():
   116	
   117	        stem = destination_file.stem
   118	        suffix = destination_file.suffix
   119	
   120	        n = 2
   121	
   122	        while True:
   123	
   124	            candidate = (
   125	                destination_dir
   126	                / f"{stem}__{n}{suffix}"
   127	            )
   128	
   129	            if not candidate.exists():
   130	                destination_file = candidate
   131	                break
   132	
   133	            n += 1
   134	
   135	    shutil.copy2(
   136	        source_file,
   137	        destination_file,
   138	    )
   139	
   140	    counts[folder_name] = (
   141	        counts.get(
   142	            folder_name,
   143	            0,
   144	        ) + 1
   145	    )
   146	
   147	# --------------------------------------------------
   148	# REPORT
   149	# --------------------------------------------------
   150	
   151	print()
   152	print("=" * 70)
   153	print("FINAL TOP-1 CLASSIFICATION")
   154	print("=" * 70)
   155	
   156	total = 0
   157	
   158	for name in sorted(
   159	    counts,
   160	    key=lambda x: (
   161	        int(
   162	            "".join(
   163	                c
   164	                for c in x
   165	                if c.isdigit()
   166	            )
   167	        )
   168	        if any(
   169	            c.isdigit()
   170	            for c in x
   171	        )
   172	        else 9999
   173	    ),
   174	):
   175	
   176	    count = counts[name]
   177	    total += count
   178	
   179	    print(
   180	        f"{name:20} {count:4}"

==============================================
=== RESULT FILE INFO ===
==============================================
-rw-rw-r-- 1 alexice alexice 536K Aug 15 00:35 final_test_78_95.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:09:00

Отлично. `classify_final_test.py` выглядит правильно для нашей задачи: **сортировка идёт строго по TOP-1**, а если `best_id` отсутствует — берётся `candidates[0]`.

Теперь надо посмотреть **сам результат распознавания**, а не менять код.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== RESULT SUMMARY ==="
echo "=============================================="

python3 - <<'PY'
import json
from pathlib import Path
from collections import Counter

p = Path("final_test_78_95.json")

lines = p.read_text(encoding="utf-8").splitlines()

start = next(
    i for i, line in enumerate(lines)
    if line.strip() == "["
)

data = json.loads("\n".join(lines[start:]))

print("TOTAL:", len(data))
print()

# TOP-1 distribution
counts = Counter()

for r in data:
    best_id = r.get("best_id")

    if not best_id:
        candidates = r.get("candidates", [])
        if candidates:
            best_id = candidates[0].get("id")

    counts[str(best_id) if best_id else "NO_CANDIDATE"] += 1

print("=== TOP-1 DISTRIBUTION ===")

for k, v in sorted(
    counts.items(),
    key=lambda x: (
        int("".join(c for c in x[0] if c.isdigit()))
        if any(c.isdigit() for c in x[0])
        else 9999
    )
):
    print(f"{k:20} {v:4}")

print()
print("UNIQUE TOP-1:", len(counts))

print()
print("=== FIRST 5 RESULTS ===")

for r in data[:5]:
    print(
        f"{Path(r['file']).name}: "
        f"best={r.get('best_id')} "
        f"score={r.get('score', 0):.4f} "
        f"margin={r.get('margin', 0):.4f} "
        f"confidence={r.get('confidence')}"
    )

    for c in r.get("candidates", [])[:5]:
        print(
            f"    {c.get('id'):12} "
            f"score={c.get('score', 0):.4f} "
            f"global={c.get('global', 0):.4f} "
            f"env={c.get('environment', 0):.4f} "
            f"color={c.get('color', 0):.4f} "
            f"spatial={c.get('spatial', 0):.4f}"
        )

    print("-" * 70)
PY
```

Это покажет нам три вещи:

1. **Все ли 78–95 реально участвуют в распознавании.**
2. **Как распределились TOP-1 по адресам.**
3. **Не появились ли подозрительные перекосы** — например, почти всё улетает в один адрес.

После этого уже можно будет проверить непосредственно папки:

```text
data/output/test_classified/
```

и визуально посмотреть рассортированные фотографии.

---

### 👤 **User** — 2026-08-15 03:09:24

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== RESULT SUMMARY ==="
echo "=============================================="

python3 - <<'PY'
import json
from pathlib import Path
from collections import Counter

p = Path("final_test_78_95.json")

lines = p.read_text(encoding="utf-8").splitlines()

start = next(
    i for i, line in enumerate(lines)
    if line.strip() == "["
)

data = json.loads("\n".join(lines[start:]))

print("TOTAL:", len(data))
PY  print("-" * 70)al={c.get('spatial', 0):.4f}"")))E"] += 1
==============================================
=== RESULT SUMMARY ===
==============================================
TOTAL: 262

=== TOP-1 DISTRIBUTION ===
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

UNIQUE TOP-1: 18

=== FIRST 5 RESULTS ===
00 (1).JPG: best=78_v33 score=0.9475 margin=0.0552 confidence=HIGH
    78_v33       score=0.9475 global=0.9549 env=0.9361 color=0.8892 spatial=0.9870
    92_v33_fast  score=0.8923 global=0.8787 env=0.9060 color=0.9520 spatial=0.9799
    91_v33_fast  score=0.8882 global=0.8724 env=0.9127 color=0.9349 spatial=0.9856
    95_v33_fast  score=0.8842 global=0.8837 env=0.9053 color=0.7930 spatial=0.9700
    83_v33       score=0.8808 global=0.8717 env=0.9108 color=0.8405 spatial=0.9869
----------------------------------------------------------------------
00 (10).JPG: best=78_v33 score=0.9384 margin=0.0591 confidence=HIGH
    78_v33       score=0.9384 global=0.9357 env=0.9366 color=0.9464 spatial=0.9936
    91_v33_fast  score=0.8793 global=0.8596 env=0.9314 color=0.8815 spatial=0.9871
    93_v33_fast  score=0.8725 global=0.8515 env=0.9193 color=0.9013 spatial=0.9825
    92_v33_fast  score=0.8708 global=0.8475 env=0.9237 color=0.9083 spatial=0.9742
    83_v33       score=0.8669 global=0.8553 env=0.9202 color=0.7797 spatial=0.9834
----------------------------------------------------------------------
00 (11).JPG: best=78_v33 score=0.9336 margin=0.0433 confidence=HIGH
    78_v33       score=0.9336 global=0.9329 env=0.9352 color=0.9124 spatial=0.9904
    95_v33_fast  score=0.8903 global=0.8718 env=0.9461 color=0.8736 spatial=0.9879
    92_v33_fast  score=0.8824 global=0.8607 env=0.9367 color=0.9002 spatial=0.9850
    83_v33       score=0.8818 global=0.8621 env=0.9338 color=0.8848 spatial=0.9877
    91_v33_fast  score=0.8811 global=0.8632 env=0.9323 color=0.8716 spatial=0.9802
----------------------------------------------------------------------
00 (12).JPG: best=78_v33 score=0.9301 margin=0.0406 confidence=HIGH
    78_v33       score=0.9301 global=0.9261 env=0.9476 color=0.8927 spatial=0.9930
    83_v33       score=0.8894 global=0.8736 env=0.9321 color=0.8851 spatial=0.9858
    95_v33_fast  score=0.8816 global=0.8592 env=0.9414 color=0.8905 spatial=0.9853
    91_v33_fast  score=0.8801 global=0.8604 env=0.9403 color=0.8594 spatial=0.9852
    92_v33_fast  score=0.8770 global=0.8532 env=0.9339 color=0.9070 spatial=0.9828
----------------------------------------------------------------------
00 (2).JPG: best=78_v33 score=0.9375 margin=0.0531 confidence=HIGH
    78_v33       score=0.9375 global=0.9345 env=0.9613 color=0.8784 spatial=0.9872
    91_v33_fast  score=0.8844 global=0.8584 env=0.9473 color=0.9190 spatial=0.9902
    95_v33_fast  score=0.8837 global=0.8640 env=0.9395 color=0.8826 spatial=0.9749
    83_v33       score=0.8818 global=0.8558 env=0.9467 color=0.9121 spatial=0.9857
    93_v33_fast  score=0.8818 global=0.8559 env=0.9457 color=0.9132 spatial=0.9872
----------------------------------------------------------------------
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:09:25

Да, **результат очень хороший**. И главное — он показывает, что текущая оптимизированная версия реально работает.

### Что получили

Всего обработано:

**262 фотографии**

Все 18 fingerprint'ов получили хотя бы один TOP-1:

| Fingerprint | Фото |
|---|---:|
| 78_v33 | 20 |
| 79_v33 | 8 |
| 80_v33 | 8 |
| 81_v33 | 16 |
| 82_v33 | 9 |
| 83_v33 | 18 |
| 84_v33 | 8 |
| 85_v33 | 17 |
| 86_v33_fast | 15 |
| 87_v33_fast | 20 |
| 88_v33_fast | 16 |
| 89_v33_fast | 20 |
| 90_v33_fast | 3 |
| 91_v33_fast | 13 |
| 92_v33_fast | 18 |
| 93_v33_fast | 12 |
| 94_v33_fast | **24** |
| 95_v33_fast | 17 |

**Итого: 262.**

То есть нет ситуации, когда новый алгоритм внезапно начал отправлять практически всё в один fingerprint.

### Особенно важен первый пример

Например:

```text
00 (1).JPG
TOP-1 = 78_v33
score = 0.9475
margin = 0.0552
confidence = HIGH
```

При этом второй кандидат:

```text
92_v33_fast = 0.8923
```

Разница:

```text
0.9475 - 0.8923 = 0.0552
```

Это очень хороший запас.

И остальные первые фотографии аналогично:

```text
0.9384 / margin 0.0591
0.9336 / margin 0.0433
0.9301 / margin 0.0406
0.9375 / margin 0.0531
```

То есть **TOP-1 не просто немного выигрывает — он достаточно уверенно отделён от второго кандидата.**

---

## Но сейчас есть один важный момент

Мы видим:

```text
78_v33
...
85_v33

86_v33_fast
...
95_v33_fast
```

То есть у нас фактически **две разновидности fingerprint'ов**:

```text
78–85 → обычный v33
86–95 → v33_fast
```

Это нормально, если именно так мы их создавали, но перед запуском реальной сортировки я бы **не стал пока ничего менять**.

Следующий тест должен быть именно практический:

```text
262 фотографии
       ↓
TOP-1
       ↓
data/output/test_classified/
       ↓
78_v33/
79_v33/
...
95_v33_fast/
```

А затем посмотрим, **что реально лежит внутри каждой папки**.

### Сейчас выполни

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== CLASSIFY FINAL RESULTS ==="
echo "=============================================="

rm -rf data/output/test_classified

python3 classify_final_test.py

echo
echo "=============================================="
echo "=== OUTPUT DISTRIBUTION ==="
echo "=============================================="

find data/output/test_classified \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    -printf '%f\n' \
    | sort -V \
    | while read d; do
        printf "%-20s %4d\n" \
          "$d" \
          "$(find "data/output/test_classified/$d" -maxdepth 1 -type f | wc -l)"
      done

echo
echo "=============================================="
echo "=== TOTAL COPIED ==="
echo "=============================================="

find data/output/test_classified \
    -type f \
    | wc -l
```

После этого мы получим **физическую сортировку 262 фотографий**.

И уже следующим шагом я бы сделал то, что мы планировали раньше: **визуально проверить рассортированные папки**, особенно `90_v33_fast`, потому что там всего 3 фотографии — интересно, действительно ли это отдельный адрес или алгоритм его недораспознаёт.

---

### 👤 **User** — 2026-08-15 03:11:21

90 очень похожа на 89 - поэтому распознана как 89 - но это пока что неважно

---

### 🤖 **Assistant** — 2026-08-15 03:11:21

Да, тогда всё логично. **90 пока не считаем проблемой** — если сцены 89 и 90 действительно очень похожи, то это как раз тот случай, где визуальная проверка важнее текущего TOP-1.

Для текущего этапа главное:

- **262/262** получили TOP-1;
- все **18 fingerprint'ов** участвуют в распределении;
- нет явного «залипания» на одном адресе;
- scores в первых примерах высокие;
- оптимизация не изменила формулу v3.3;
- `classify_final_test.py` действительно раскладывает по первому кандидату.

И я бы сейчас **90 вообще не трогал**.

### Следующий шаг

Запускаем физическую сортировку:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

rm -rf data/output/test_classified

python3 classify_final_test.py

echo
echo "=== DISTRIBUTION ==="

find data/output/test_classified \
    -mindepth 1 \
    -maxdepth 1 \
    -type d \
    -printf '%f\n' \
    | sort -V \
    | while read d; do
        printf "%-20s %4d\n" \
            "$d" \
            "$(find "data/output/test_classified/$d" \
                -maxdepth 1 -type f | wc -l)"
      done

echo
echo "TOTAL:"
find data/output/test_classified -type f | wc -l
```

**После этого ничего больше не меняем.** Смотрим папки визуально и подтверждаем, что текущая связка `DINO → v33 → TOP-1 → сортировка` работает.

---

### 👤 **User** — 2026-08-15 03:12:17

да сейчас хороший результат

---

### 🤖 **Assistant** — 2026-08-15 03:12:17

Да, тогда **фиксируем текущую версию как рабочую**.

По результату:

- **262 фото** обработано.
- Все **18 адресов** получили TOP-1.
- Основная логика v3.3 сохранилась.
- Оптимизация не изменила сам алгоритм сравнения — она убрала повторные загрузки изображения и повторные вычисления дескрипторов.
- `DINO global + environment + color + spatial` работает.
- `TOP-1` действительно используется при сортировке.
- Случай `90 → 89` пока считаем нормальным для очень похожих сцен и **не трогаем алгоритм ради него**.

Я бы сейчас **не оптимизировал распознавание дальше**. Текущий результат лучше сохранить как контрольную точку.

### Следующий разумный шаг

Зафиксировать состояние проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp app/core/scene_analyzer.py \
   app/core/scene_analyzer.py.v33_working

cp app/core/recognizer.py \
   app/core/recognizer.py.v33_working

cp final_test_78_95.json \
   final_test_78_95.working.json
```

И сделать git-коммит, если репозиторий уже есть:

```bash
git status
git add app/core/scene_analyzer.py app/core/recognizer.py
git commit -m "Stable v3.3 recognition with optimized descriptor calculation"
```

**После этого уже можно переходить к следующей части пайплайна — сортировке `test` по папкам адресов и визуальной проверке результатов.**

И главное: **не возвращаем старый `scene_analyzer.py` целиком**. Старый алгоритм v3.3 у нас сохранён, а текущая оптимизация безопасно его ускоряет.

---

### 👤 **User** — 2026-08-15 03:13:18

давай на всякий случай прогоним весь пайплайн с нуля - заново создадим слепки и прогоним распознавание test

---

### 🤖 **Assistant** — 2026-08-15 03:13:18

> **Remembering**
>
>
> **Recreated address fingerprints and checked the stable recognition pipeline**
>
> 
>
> Worked for 5s

Да. Сделаем **полный чистый прогон**, без изменения алгоритма:

1. Удаляем старые `78_v33 … 95_*`.
2. Заново создаём слепки **78–95** из исходных папок.
3. Проверяем, что все 18 слепков корректны.
4. **`data/input/test` не трогаем.**
5. Запускаем распознавание всего `test`.
6. Сохраняем новый результат отдельно, чтобы сравнить с текущим `final_test_78_95.json`.

Сначала давай аккуратно проверим команды создания слепков, чтобы не предположить неправильный CLI. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== CREATE CLI ==="
echo "=============================================="

uv run scene-fingerprint create --help

echo
echo "=============================================="
echo "=== CURRENT FINGERPRINTS ==="
echo "=============================================="

find data/fingerprints -maxdepth 1 -mindepth 1 -type d \
  | sort

echo
echo "=============================================="
echo "=== SOURCE COUNTS 78-95 ==="
echo "=============================================="

for d in data/input/{78..95}; do
    printf "%-12s " "$(basename "$d")"
    find "$d" -maxdepth 1 -type f \
      \( -iname "*.jpg" -o -iname "*.jpeg" \
         -o -iname "*.png" -o -iname "*.webp" \) \
      | wc -l
done

echo
echo "=============================================="
echo "=== TEST COUNT ==="
echo "=============================================="

find data/input/test -maxdepth 1 -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" \
     -o -iname "*.png" -o -iname "*.webp" \) \
  | wc -l
```

**Пока ничего не удаляем.** Покажи вывод — после этого дам один чистый блок команд на пересоздание всех `78–95` и полный прогон `test`.

---

### 👤 **User** — 2026-08-15 03:13:51

lexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ git status
git add app/core/scene_analyzer.py app/core/recognizer.py
git commit -m "Stable v3.3 recognition with optimized descriptor calculation"
fatal: not a git repository (or any of the parent directories): .git
fatal: not a git repository (or any of the parent directories): .git
fatal: not a git repository (or any of the parent directories): .git
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== CREATE CLI ==="
echo "=============================================="

uv run scene-fingerprint create --help

echo
echo "=============================================="
echo "=== CURRENT FINGERPRINTS ==="
echo "=============================================="

find data/fingerprints -maxdepth 1 -mindepth 1 -type d \
  | sort

echo
echo "=============================================="
echo "=== SOURCE COUNTS 78-95 ==="
echo "=============================================="

for d in data/input/{78..95}; do
    printf "%-12s " "$(basename "$d")"
  | wc -liname "*.png" -o -iname "*.webp" \) \======"
==============================================
=== CREATE CLI ===
==============================================
usage: scene-fingerprint create [-h] fingerprint folder

positional arguments:
  fingerprint  Fingerprint ID
  folder       Folder with reference images

options:
  -h, --help   show this help message and exit

==============================================
=== CURRENT FINGERPRINTS ===
==============================================
data/fingerprints/78_v33
data/fingerprints/79_v33
data/fingerprints/80_v33
data/fingerprints/81_v33
data/fingerprints/82_v33
data/fingerprints/83_v33
data/fingerprints/84_v33
data/fingerprints/84_v34_test
data/fingerprints/84_v35_test
data/fingerprints/85_v33
data/fingerprints/86_v33
data/fingerprints/87_v33
data/fingerprints/88_v33
data/fingerprints/89_v33
data/fingerprints/90_v33
data/fingerprints/91_v33
data/fingerprints/92_v33
data/fingerprints/93_v33
data/fingerprints/94_v33
data/fingerprints/95_v33

==============================================
=== SOURCE COUNTS 78-95 ===
==============================================
78           81
79           65
80           37
81           65
82           67
83           68
84           54
85           58
86           58
87           50
88           54
89           64
90           19
91           41
92           57
93           51
94           67
95           86

==============================================
=== TEST COUNT ===
==============================================
262
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:13:52

Отлично. Теперь у нас есть точные исходные данные:

- **18 адресов: 78–95**
- **1022 исходных фотографий** всего
- `test` — **262 фотографии**
- CLI создания слепка подтверждён: `create fingerprint folder`
- Старые слепки имеют имена `*_v33`.
- `84_v34_test` и `84_v35_test` — это экспериментальные, их **не трогаем**.

Git здесь просто отсутствует — ничего страшного. Для контрольной точки позже сделаем обычную резервную копию.

Теперь делаем **полный чистый прогон**.

### 1. Сначала переименуем старые v33, а не удаляем

Так безопаснее: если понадобится сравнить, они останутся.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=============================================="
echo "=== BACKUP OLD V33 FINGERPRINTS ==="
echo "=============================================="

BACKUP="fingerprints_backup_before_clean_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP"

for id in {78..95}; do
    if [ -d "data/fingerprints/${id}_v33" ]; then
        mv \
          "data/fingerprints/${id}_v33" \
          "$BACKUP/${id}_v33"
    fi
done

echo
echo "Backup:"
find "$BACKUP" -maxdepth 1 -mindepth 1 -type d | sort
```

### 2. Пересоздаём все 18 слепков

```bash
echo
echo "=============================================="
echo "=== CREATE FRESH V33 FINGERPRINTS ==="
echo "=============================================="

for id in {78..95}; do

    echo
    echo "----------------------------------------------"
    echo "CREATING ${id}_v33"
    echo "SOURCE: data/input/${id}"
    echo "----------------------------------------------"

    uv run scene-fingerprint create \
        "${id}_v33" \
        "data/input/${id}" \
        || {
            echo
            echo "!!! FAILED: ${id}_v33 !!!"
            exit 1
        }

done

echo
echo "=============================================="
echo "=== ALL FINGERPRINTS CREATED ==="
echo "=============================================="

find data/fingerprints \
    -maxdepth 1 \
    -mindepth 1 \
    -type d \
    | sort
```

Если этот блок завершится без `FAILED`, значит мы получили **полностью новые слепки из исходных 78–95**.

---

### 3. Проверяем, что слепки действительно свежие и полные

```bash
echo
echo "=============================================="
echo "=== VERIFY FINGERPRINTS ==="
echo "=============================================="

for id in {78..95}; do

    echo
    echo "=== ${id}_v33 ==="

    ls -lh "data/fingerprints/${id}_v33"

    if [ ! -f "data/fingerprints/${id}_v33/embeddings.npy" ]; then
        echo "ERROR: embeddings.npy missing"
        exit 1
    fi

    if [ ! -f "data/fingerprints/${id}_v33/centroid.npy" ]; then
        echo "ERROR: centroid.npy missing"
        exit 1
    fi

    if [ ! -f "data/fingerprints/${id}_v33/metadata.json" ]; then
        echo "ERROR: metadata.json missing"
        exit 1
    fi

done
```

---

### 4. И только после этого — распознавание `test`

Причём я предлагаю **не перезаписывать старый результат**.

```bash
echo
echo "=============================================="
echo "=== CLEAN TEST RECOGNITION ==="
echo "=============================================="

rm -f final_test_78_95_clean.json

uv run scene-fingerprint recognize \
    data/input/test \
    --top-k 5 \
    --threshold 0.65 \
    > final_test_78_95_clean.json
```

После этого посмотрим результат:

```bash
echo
echo "=============================================="
echo "=== RESULT FILE ==="
echo "=============================================="

ls -lh final_test_78_95_clean.json

echo
echo "=============================================="
echo "=== RECOGNITION SUMMARY ==="
echo "=============================================="

grep -E \
'Query images|Fingerprints:|Recognized|NO_MATCH|CONFIDENT|PROBABLE|AMBIGUOUS' \
final_test_78_95_clean.json \
| tail -50
```

**Но важный момент:** перед запуском пункта 4 я бы сначала выполнил пункты **1–3** и показал мне вывод. Тогда мы убедимся, что новые слепки действительно созданы из тех же 1022 фотографий и что ни один старый/экспериментальный fingerprint случайно не участвует.

Особенно важно проверить, что распознаватель видит именно:

```text
78_v33
79_v33
...
95_v33
```

а не старые `*_fast` или экспериментальные версии.

---

### 👤 **User** — 2026-08-15 03:18:19

переименуй в input в папках с номерами файлы в такие же номера с индексом

---

