## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-20 23:53:00

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DINO WORKER ================" && \
nl -ba app/workers/dino_worker.py | sed -n '1,500p' && \
echo && \
echo "================ QWEN WORKER ================" && \
nl -ba app/workers/qwen_worker.py | sed -n '1,500p'
================ DINO WORKER ================
     1	from __future__ import annotations
     2	
     3	import os
     4	import time
     5	from pathlib import Path
     6	
     7	import psycopg2
     8	from psycopg2.extras import RealDictCursor
     9	
    10	from app.core.config import Settings
    11	from app.core.embedder import SceneEmbedder
    12	from app.core.fingerprint import FingerprintManager
    13	from app.core.recognizer import SceneRecognizer
    14	
    15	
    16	DB_CONFIG = {
    17	    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    18	    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    19	    "user": os.getenv("PHOTOBASE_USER", "lora"),
    20	    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    21	    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
    22	}
    23	
    24	
    25	# ============================================================
    26	# DATABASE
    27	# ============================================================
    28	
    29	def get_connection():
    30	    return psycopg2.connect(**DB_CONFIG)
    31	
    32	
    33	def reset_processing(conn):
    34	    """
    35	    Возвращает зависшие DINO-задачи обратно в очередь.
    36	
    37	    Это позволяет продолжить работу после:
    38	        - остановки процесса
    39	        - перезагрузки
    40	        - падения Python
    41	        - аварии машины
    42	    """
    43	
    44	    with conn.cursor() as cur:
    45	        cur.execute(
    46	            """
    47	            UPDATE photos
    48	            SET
    49	                dino_status = 'pending',
    50	                updated_at = CURRENT_TIMESTAMP
    51	            WHERE dino_status = 'processing'
    52	            """
    53	        )
    54	
    55	        count = cur.rowcount
    56	
    57	    conn.commit()
    58	
    59	    if count:
    60	        print(
    61	            f"[DINO] Reset stale processing jobs: {count}"
    62	        )
    63	
    64	
    65	def claim_photo(conn):
    66	    """
    67	    Забирает следующую фотографию из DINO-очереди.
    68	
    69	    ВАЖНО:
    70	
    71	    Qwen здесь вообще не учитывается.
    72	
    73	    DINO получает фотографию только потому,
    74	    что у неё уже существует photo_id и
    75	    dino_status = pending.
    76	    """
    77	
    78	    with conn.cursor(
    79	        cursor_factory=RealDictCursor
    80	    ) as cur:
    81	
    82	        cur.execute(
    83	            """
    84	            SELECT
    85	                id,
    86	                photo_id,
    87	                initial_id,
    88	                source_path,
    89	                filename
    90	            FROM photos
    91	            WHERE
    92	                dino_status = 'pending'
    93	                AND source_path IS NOT NULL
    94	                AND source_path <> ''
    95	            ORDER BY id
    96	            FOR UPDATE SKIP LOCKED
    97	            LIMIT 1
    98	            """
    99	        )
   100	
   101	        row = cur.fetchone()
   102	
   103	        if row is None:
   104	            conn.commit()
   105	            return None
   106	
   107	        cur.execute(
   108	            """
   109	            UPDATE photos
   110	            SET
   111	                dino_status = 'processing',
   112	                updated_at = CURRENT_TIMESTAMP
   113	            WHERE
   114	                id = %s
   115	                AND dino_status = 'pending'
   116	            """,
   117	            (row["id"],),
   118	        )
   119	
   120	        conn.commit()
   121	
   122	        return row
   123	
   124	
   125	# ============================================================
   126	# RESULT
   127	# ============================================================
   128	
   129	def mark_done(
   130	    conn,
   131	    db_id,
   132	    result,
   133	    elapsed,
   134	):
   135	    """
   136	    Сохраняет результат DINO.
   137	
   138	    Главный результат нового слоя:
   139	
   140	        address_id = адрес, определённый DINO.
   141	
   142	    photo_id остаётся независимым идентификатором фотографии.
   143	    """
   144	
   145	    address_id = result.get("best_id")
   146	
   147	    with conn.cursor() as cur:
   148	
   149	        cur.execute(
   150	            """
   151	            UPDATE photos
   152	            SET
   153	                dino_status = 'done',
   154	
   155	                address_id = %s,
   156	
   157	                dino_fingerprint = %s,
   158	                dino_score = %s,
   159	                dino_second_score = %s,
   160	                dino_margin = %s,
   161	                dino_time_sec = %s,
   162	
   163	                error_message = NULL,
   164	                updated_at = CURRENT_TIMESTAMP
   165	
   166	            WHERE id = %s
   167	            """,
   168	            (
   169	                address_id,
   170	
   171	                # Старое поле оставляем для совместимости
   172	                # со старым кодом и статистикой.
   173	                address_id,
   174	
   175	                result.get("score"),
   176	                result.get("second_score"),
   177	                result.get("margin"),
   178	
   179	                elapsed,
   180	
   181	                db_id,
   182	            ),
   183	        )
   184	
   185	    conn.commit()
   186	
   187	
   188	def mark_error(
   189	    conn,
   190	    db_id,
   191	    error,
   192	):
   193	    """
   194	    Фиксирует ошибку конкретной фотографии.
   195	
   196	    Qwen-status при этом НЕ меняется.
   197	    """
   198	
   199	    message = str(error)
   200	
   201	    with conn.cursor() as cur:
   202	
   203	        cur.execute(
   204	            """
   205	            UPDATE photos
   206	            SET
   207	                dino_status = 'error',
   208	                error_message = %s,
   209	                updated_at = CURRENT_TIMESTAMP
   210	            WHERE id = %s
   211	            """,
   212	            (
   213	                message[:4000],
   214	                db_id,
   215	            ),
   216	        )
   217	
   218	    conn.commit()
   219	
   220	
   221	# ============================================================
   222	# WORKER
   223	# ============================================================
   224	
   225	def main():
   226	
   227	    settings = Settings()
   228	
   229	    print("=" * 70)
   230	    print("DINO WORKER")
   231	    print("=" * 70)
   232	    print("device  :", settings.device)
   233	    print("database:", DB_CONFIG["dbname"])
   234	    print("=" * 70)
   235	
   236	    # --------------------------------------------------------
   237	    # MODEL
   238	    # --------------------------------------------------------
   239	
   240	    print("[DINO] Loading SceneEmbedder...")
   241	
   242	    embedder = SceneEmbedder(settings)
   243	
   244	    manager = FingerprintManager(
   245	        settings,
   246	        embedder,
   247	    )
   248	
   249	    recognizer = SceneRecognizer(
   250	        settings,
   251	        embedder,
   252	        manager,
   253	    )
   254	
   255	    # --------------------------------------------------------
   256	    # DATABASE
   257	    # --------------------------------------------------------
   258	
   259	    conn = get_connection()
   260	
   261	    print("[DINO] Database connected.")
   262	
   263	    # --------------------------------------------------------
   264	    # RECOVERY
   265	    # --------------------------------------------------------
   266	
   267	    reset_processing(conn)
   268	
   269	    print("[DINO] Worker ready.")
   270	
   271	    max_items = int(
   272	        os.getenv(
   273	            "DINO_MAX_ITEMS",
   274	            "0",
   275	        )
   276	    )
   277	
   278	    processed = 0
   279	    errors = 0
   280	
   281	    try:
   282	
   283	        while True:
   284	
   285	            # ------------------------------------------------
   286	            # LIMIT
   287	            # ------------------------------------------------
   288	
   289	            if (
   290	                max_items > 0
   291	                and processed >= max_items
   292	            ):
   293	                print(
   294	                    f"[DINO] "
   295	                    f"Reached max_items={max_items}."
   296	                )
   297	                break
   298	
   299	            # ------------------------------------------------
   300	            # CLAIM
   301	            # ------------------------------------------------
   302	
   303	            row = claim_photo(conn)
   304	
   305	            if row is None:
   306	
   307	                print(
   308	                    "[DINO] Queue empty."
   309	                )
   310	
   311	                break
   312	
   313	            db_id = row["id"]
   314	            photo_id = row["photo_id"]
   315	            initial_id = row["initial_id"]
   316	            source_path = Path(
   317	                row["source_path"]
   318	            )
   319	
   320	            print()
   321	            print("-" * 70)
   322	
   323	            print(
   324	                "[DINO]",
   325	                photo_id,
   326	                "| initial_id:",
   327	                initial_id,
   328	                "| file:",
   329	                source_path.name,
   330	            )
   331	
   332	            started = time.perf_counter()
   333	
   334	            # ------------------------------------------------
   335	            # PROCESS
   336	            # ------------------------------------------------
   337	
   338	            try:
   339	
   340	                if not source_path.exists():
   341	                    raise FileNotFoundError(
   342	                        f"Photo not found: {source_path}"
   343	                    )
   344	
   345	                if not source_path.is_file():
   346	                    raise FileNotFoundError(
   347	                        f"Not a file: {source_path}"
   348	                    )
   349	
   350	                result = recognizer.recognize_one(
   351	                    source_path,
   352	                    top_k=5,
   353	                    threshold=0.65,
   354	                )
   355	
   356	                elapsed = (
   357	                    time.perf_counter()
   358	                    - started
   359	                )
   360	
   361	                # ------------------------------------------------
   362	                # SAVE
   363	                # ------------------------------------------------
   364	
   365	                mark_done(
   366	                    conn,
   367	                    db_id,
   368	                    result,
   369	                    elapsed,
   370	                )
   371	
   372	                address_id = result.get(
   373	                    "best_id"
   374	                )
   375	
   376	                print(
   377	                    f"[DINO] DONE "
   378	                    f"{photo_id}"
   379	                    f" -> address_id={address_id}"
   380	                    f" score={result.get('score', 0):.6f}"
   381	                    f" margin={result.get('margin', 0):.6f}"
   382	                    f" time={elapsed:.2f}s"
   383	                )
   384	
   385	                processed += 1
   386	
   387	            # ------------------------------------------------
   388	            # ERROR
   389	            # ------------------------------------------------
   390	
   391	            except Exception as exc:
   392	
   393	                errors += 1
   394	
   395	                elapsed = (
   396	                    time.perf_counter()
   397	                    - started
   398	                )
   399	
   400	                print(
   401	                    f"[DINO] ERROR "
   402	                    f"{photo_id}: {exc}"
   403	                    f" time={elapsed:.2f}s"
   404	                )
   405	
   406	                try:
   407	
   408	                    mark_error(
   409	                        conn,
   410	                        db_id,
   411	                        exc,
   412	                    )
   413	
   414	                except Exception as db_error:
   415	
   416	                    print(
   417	                        "[DINO] "
   418	                        "DB ERROR while marking error:",
   419	                        db_error,
   420	                    )
   421	
   422	    finally:
   423	
   424	        conn.close()
   425	
   426	        print()
   427	        print("=" * 70)
   428	        print("DINO WORKER STOPPED")
   429	        print("=" * 70)
   430	
   431	        print(
   432	            "PROCESSED:",
   433	            processed,
   434	        )
   435	
   436	        print(
   437	            "ERRORS:",
   438	            errors,
   439	        )
   440	
   441	
   442	if __name__ == "__main__":
   443	    main()

================ QWEN WORKER ================
     1	from __future__ import annotations
     2	
     3	import base64
     4	import json
     5	import os
     6	import time
     7	from pathlib import Path
     8	
     9	import psycopg2
    10	import requests
    11	from psycopg2.extras import RealDictCursor
    12	
    13	
    14	# ============================================================
    15	# DATABASE
    16	# ============================================================
    17	
    18	DB_CONFIG = {
    19	    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    20	    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    21	    "user": os.getenv("PHOTOBASE_USER", "lora"),
    22	    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    23	    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
    24	}
    25	
    26	
    27	# ============================================================
    28	# QWEN
    29	# ============================================================
    30	
    31	MODEL = "qwen3-vl:4b-instruct"
    32	OLLAMA_URL = "http://localhost:11434/api/chat"
    33	
    34	NUM_CTX = 16384
    35	TEMPERATURE = 0
    36	
    37	
    38	# ============================================================
    39	# PROMPT
    40	# ============================================================
    41	
    42	PROMPT = r"""
    43	Ты анализируешь фотографию с улицы для базы наружной рекламы.
    44	
    45	Найди рекламный баннер и верни ТОЛЬКО JSON.
    46	Не добавляй пояснений вне JSON.
    47	Не повторяй информацию.
    48	Не придумывай отсутствующую информацию.
    49	
    50	Формат:
    51	
    52	{
    53	  "client": "",
    54	  "brand": "",
    55	  "category": "",
    56	  "text": [],
    57	  "colors": [],
    58	  "objects": [],
    59	  "description": "",
    60	  "banner_type": "видеоэкран",
    61	
    62	  "environment": {
    63	    "weather": "",
    64	    "precipitation": "",
    65	    "lighting": ""
    66	  },
    67	
    68	  "image_quality": {
    69	    "overall": "",
    70	    "sharpness": "",
    71	    "exposure": "",
    72	    "visibility": "",
    73	    "banner_visible": true,
    74	    "banner_readability": "",
    75	    "motion_blur": false,
    76	    "occlusion": false
    77	  },
    78	
    79	  "camera_view": {
    80	    "distance": "",
    81	    "angle": ""
    82	  },
    83	
    84	  "analysis_quality": {
    85	    "banner_analysis": "",
    86	    "text_analysis": ""
    87	  },
    88	
    89	  "confidence": 0
    90	}
    91	
    92	БАННЕР:
    93	client — компания, организация или заказчик.
    94	brand — торговая марка, имя кандидата или рекламируемый бренд.
    95	category — категория рекламы.
    96	text — читаемые надписи на баннере.
    97	colors — основные цвета самого баннера.
    98	objects — основные изображения и предметы НА БАННЕРЕ.
    99	description — краткое описание композиции баннера, максимум 300 символов.
   100	banner_type — на данном этапе "видеоэкран".
   101	
   102	ОКРУЖЕНИЕ:
   103	Определи ТОЛЬКО:
   104	weather — солнечно / пасмурно / облачно / туман / неизвестно.
   105	precipitation — нет / дождь / снег / мокрый снег / неизвестно.
   106	lighting — яркий день / дневной свет / сумерки / ночь / искусственное освещение / неизвестно.
   107	
   108	Не описывай окружающую сцену.
   109	Не описывай здания, дороги, автомобили, автобусы, людей,
   110	дорожные знаки, провода или растительность.
   111	
   112	КАЧЕСТВО:
   113	Оцени только качество фотографии и видимость баннера.
   114	
   115	overall — хорошее / удовлетворительное / плохое.
   116	sharpness — резкое / слегка размыто / сильно размыто / неизвестно.
   117	exposure — нормальная / пересвечено / недоэкспонировано / очень тёмное / неизвестно.
   118	visibility — хорошо виден / частично виден / плохо виден / не виден.
   119	banner_visible — true или false.
   120	banner_readability — высокая / средняя / низкая / невозможно определить.
   121	motion_blur — true или false.
   122	occlusion — true или false.
   123	
   124	КАМЕРА:
   125	distance — далеко / средняя дистанция / близко / неизвестно.
   126	angle — прямо / слева / справа / сверху / снизу / косой ракурс / неизвестно.
   127	
   128	Если баннер не виден:
   129	client = ""
   130	brand = ""
   131	category = ""
   132	text = []
   133	colors = []
   134	objects = []
   135	description = ""
   136	banner_visible = false
   137	
   138	Массивы должны содержать только действительно важные элементы.
   139	Не более 10 элементов в каждом массиве.
   140	Не повторяй элементы.
   141	
   142	confidence — уверенность в анализе от 0 до 100.
   143	"""
   144	
   145	
   146	# ============================================================
   147	# DATABASE
   148	# ============================================================
   149	
   150	def get_connection():
   151	    return psycopg2.connect(**DB_CONFIG)
   152	
   153	
   154	def claim_photo(conn):
   155	    """
   156	    Берём следующую фотографию, которая ещё не обработана Qwen.
   157	
   158	    ВАЖНО:
   159	        Qwen работает независимо от DINO.
   160	
   161	    Единственная связь:
   162	        photo_id -> результат Qwen
   163	
   164	    address_id здесь НЕ используется.
   165	    """
   166	
   167	    with conn.cursor(cursor_factory=RealDictCursor) as cur:
   168	
   169	        cur.execute(
   170	            """
   171	            SELECT
   172	                id,
   173	                photo_id,
   174	                source_path,
   175	                filename
   176	            FROM photos
   177	            WHERE qwen_status = 'pending'
   178	              AND source_path IS NOT NULL
   179	              AND source_path <> ''
   180	            ORDER BY id
   181	            FOR UPDATE SKIP LOCKED
   182	            LIMIT 1
   183	            """
   184	        )
   185	
   186	        row = cur.fetchone()
   187	
   188	        if row is None:
   189	            conn.commit()
   190	            return None
   191	
   192	        cur.execute(
   193	            """
   194	            UPDATE photos
   195	            SET
   196	                qwen_status = 'processing',
   197	                updated_at = CURRENT_TIMESTAMP
   198	            WHERE id = %s
   199	              AND qwen_status = 'pending'
   200	            """,
   201	            (row["id"],),
   202	        )
   203	
   204	        conn.commit()
   205	
   206	        return row
   207	
   208	
   209	def mark_done(
   210	    conn,
   211	    db_id,
   212	    result,
   213	    elapsed,
   214	):
   215	    """
   216	    Сохраняет результат Qwen.
   217	
   218	    db_id — внутренний bigint photos.id.
   219	
   220	    photo_id остаётся постоянным идентификатором
   221	    фотографии и не зависит от адреса.
   222	    """
   223	
   224	    text_json = result.get("text", [])
   225	    colors_json = result.get("colors", [])
   226	    objects_json = result.get("objects", [])
   227	    environment_json = result.get("environment", {})
   228	    image_quality_json = result.get("image_quality", {})
   229	    camera_view_json = result.get("camera_view", {})
   230	    analysis_quality_json = result.get(
   231	        "analysis_quality",
   232	        {},
   233	    )
   234	
   235	    raw_json = dict(result)
   236	    raw_json.pop("_time_sec", None)
   237	
   238	    with conn.cursor() as cur:
   239	
   240	        cur.execute(
   241	            """
   242	            UPDATE photos
   243	            SET
   244	                qwen_status = 'done',
   245	
   246	                client = %s,
   247	                brand = %s,
   248	                category = %s,
   249	                description = %s,
   250	                confidence = %s,
   251	
   252	                qwen_time_sec = %s,
   253	
   254	                text_json = %s::jsonb,
   255	                colors_json = %s::jsonb,
   256	                objects_json = %s::jsonb,
   257	                environment_json = %s::jsonb,
   258	                image_quality_json = %s::jsonb,
   259	                camera_view_json = %s::jsonb,
   260	                analysis_quality_json = %s::jsonb,
   261	                raw_json = %s::jsonb,
   262	
   263	                error_message = NULL,
   264	                updated_at = CURRENT_TIMESTAMP
   265	
   266	            WHERE id = %s
   267	            """,
   268	            (
   269	                result.get("client") or None,
   270	                result.get("brand") or None,
   271	                result.get("category") or None,
   272	                result.get("description") or None,
   273	                result.get("confidence"),
   274	
   275	                elapsed,
   276	
   277	                json.dumps(
   278	                    text_json,
   279	                    ensure_ascii=False,
   280	                ),
   281	                json.dumps(
   282	                    colors_json,
   283	                    ensure_ascii=False,
   284	                ),
   285	                json.dumps(
   286	                    objects_json,
   287	                    ensure_ascii=False,
   288	                ),
   289	                json.dumps(
   290	                    environment_json,
   291	                    ensure_ascii=False,
   292	                ),
   293	                json.dumps(
   294	                    image_quality_json,
   295	                    ensure_ascii=False,
   296	                ),
   297	                json.dumps(
   298	                    camera_view_json,
   299	                    ensure_ascii=False,
   300	                ),
   301	                json.dumps(
   302	                    analysis_quality_json,
   303	                    ensure_ascii=False,
   304	                ),
   305	                json.dumps(
   306	                    raw_json,
   307	                    ensure_ascii=False,
   308	                ),
   309	
   310	                db_id,
   311	            ),
   312	        )
   313	
   314	    conn.commit()
   315	
   316	
   317	def mark_error(
   318	    conn,
   319	    db_id,
   320	    error,
   321	):
   322	    message = str(error)
   323	
   324	    with conn.cursor() as cur:
   325	
   326	        cur.execute(
   327	            """
   328	            UPDATE photos
   329	            SET
   330	                qwen_status = 'error',
   331	                error_message = %s,
   332	                updated_at = CURRENT_TIMESTAMP
   333	            WHERE id = %s
   334	            """,
   335	            (
   336	                message[:4000],
   337	                db_id,
   338	            ),
   339	        )
   340	
   341	    conn.commit()
   342	
   343	
   344	# ============================================================
   345	# IMAGE
   346	# ============================================================
   347	
   348	def image64(path: Path):
   349	    with open(path, "rb") as f:
   350	        return base64.b64encode(
   351	            f.read()
   352	        ).decode()
   353	
   354	
   355	# ============================================================
   356	# QWEN REQUEST
   357	# ============================================================
   358	
   359	def ask(path: Path):
   360	
   361	    max_attempts = 2
   362	
   363	    for attempt in range(
   364	        1,
   365	        max_attempts + 1,
   366	    ):
   367	
   368	        payload = {
   369	            "model": MODEL,
   370	
   371	            "messages": [
   372	                {
   373	                    "role": "user",
   374	                    "content": PROMPT,
   375	                    "images": [
   376	                        image64(path)
   377	                    ],
   378	                }
   379	            ],
   380	
   381	            "stream": False,
   382	
   383	            "options": {
   384	                "num_ctx": NUM_CTX,
   385	                "temperature": TEMPERATURE,
   386	                "num_predict": 800,
   387	            },
   388	        }
   389	
   390	        started = time.time()
   391	
   392	        response = requests.post(
   393	            OLLAMA_URL,
   394	            json=payload,
   395	            timeout=1800,
   396	        )
   397	
   398	        elapsed = time.time() - started
   399	
   400	        if response.status_code != 200:
   401	            raise RuntimeError(
   402	                response.text
   403	            )
   404	
   405	        data = response.json()
   406	
   407	        print(
   408	            "[OLLAMA]",
   409	            {
   410	                "total_duration_sec":
   411	                    round(
   412	                        data.get(
   413	                            "total_duration",
   414	                            0,
   415	                        ) / 1e9,
   416	                        2,
   417	                    ),
   418	                "load_duration_sec":
   419	                    round(
   420	                        data.get(
   421	                            "load_duration",
   422	                            0,
   423	                        ) / 1e9,
   424	                        2,
   425	                    ),
   426	                "prompt_eval_duration_sec":
   427	                    round(
   428	                        data.get(
   429	                            "prompt_eval_duration",
   430	                            0,
   431	                        ) / 1e9,
   432	                        2,
   433	                    ),
   434	                "eval_duration_sec":
   435	                    round(
   436	                        data.get(
   437	                            "eval_duration",
   438	                            0,
   439	                        ) / 1e9,
   440	                        2,
   441	                    ),
   442	                "prompt_eval_count":
   443	                    data.get(
   444	                        "prompt_eval_count"
   445	                    ),
   446	                "eval_count":
   447	                    data.get(
   448	                        "eval_count"
   449	                    ),
   450	            },
   451	            flush=True,
   452	        )
   453	
   454	        answer = data[
   455	            "message"
   456	        ][
   457	            "content"
   458	        ]
   459	
   460	        cleaned = answer.strip()
   461	
   462	        if cleaned.startswith("```"):
   463	
   464	            cleaned = cleaned.replace(
   465	                "```json",
   466	                "",
   467	                1,
   468	            )
   469	
   470	            cleaned = cleaned.replace(
   471	                "```",
   472	                "",
   473	            ).strip()
   474	
   475	        try:
   476	
   477	            result = json.loads(
   478	                cleaned
   479	            )
   480	
   481	            description = str(
   482	                result.get(
   483	                    "description"
   484	                ) or ""
   485	            ).strip()
   486	
   487	            if description:
   488	                result["_time_sec"] = round(
   489	                    elapsed,
   490	                    2,
   491	                )
   492	
   493	                return result
   494	
   495	            if attempt < max_attempts:
   496	
   497	                print(
   498	                    "[QWEN RETRY]",
   499	                    "description empty",
   500	                    "| attempt:",

---

### 🤖 **Assistant** — 2026-08-20 23:53:04

Да. Теперь картина достаточно чёткая.

### Что у нас есть

**1. `dino_worker.py` — отдельный самостоятельный DINO-процесс**

Он:

- берёт `photo_id` из PostgreSQL;
- выбирает `dino_status = 'pending'`;
- блокирует запись через `FOR UPDATE SKIP LOCKED`;
- загружает фото по `source_path`;
- вызывает:

`recognizer.recognize_one(...)`

- получает результат Hybrid/DINO;
- записывает **обратно в ту же строку `photos`**, прежде всего:
  - `address_id`
  - `dino_fingerprint`
  - `dino_score`
  - `dino_second_score`
  - `dino_margin`
  - `dino_time_sec`

При этом `photo_id` не меняется.

То есть архитектурно именно то, о чём мы говорили:

**PostgreSQL → `photo_id` → DINO/Hybrid → результат → та же запись `photo_id`.**

---

**2. `qwen_worker.py` — полностью отдельный процесс**

Он вообще не зависит от DINO:

```text
qwen_status = pending
        ↓
qwen_worker.py
        ↓
Ollama
        ↓
Qwen3-VL 4B
        ↓
та же строка photos
```

И пишет свои поля:

- `client`
- `brand`
- `category`
- `description`
- `confidence`
- `text_json`
- `colors_json`
- `objects_json`
- `environment_json`
- `image_quality_json`
- `camera_view_json`
- `analysis_quality_json`
- `raw_json`
- `qwen_time_sec`

То есть **DINO и Qwen действительно независимы и могут работать параллельно**, используя одну таблицу `photos`.

---

### Важный момент с CPU/GPU DINO

Вот это сейчас принципиально:

```python
device: str = os.getenv(
    "SCENE_DEVICE",
    "cuda" if torch.cuda.is_available() else "cpu"
)
```

Сам `dino_worker.py` **не устанавливает CPU**.

Он делает:

```python
settings = Settings()
```

а дальше:

```python
embedder = SceneEmbedder(settings)
```

и `SceneEmbedder` делает:

```python
self.device = torch.device(settings.device)
```

Поэтому:

- если `SCENE_DEVICE=cpu` → DINO работает на **CPU**;
- если переменная не задана и CUDA доступна → DINO автоматически пойдёт на **GPU**.

То есть если ты раньше специально запускал Hybrid/DINO на CPU, это должно было задаваться **при запуске worker-а через окружение**, например:

```bash
SCENE_DEVICE=cpu python app/workers/dino_worker.py
```

или через `subprocess` из старого технического интерфейса.

### И здесь как раз надо проверить старый механизм запуска

В твоём `photo_processing.py` уже видно, что техническая вкладка запускает:

```text
app/workers/dino_worker.py
app/workers/qwen_worker.py
```

причём это **два отдельных процесса**.

А в старом интерфейсе есть ещё отдельный `qwen.py`, который тоже запускает Qwen и ищет последний Hybrid.

---

### И главное для нашей текущей архитектуры

Я бы **не трогал эти два worker-а без необходимости**.

У нас уже получилась очень правильная схема:

```text
                    PostgreSQL
                        │
              ┌─────────┴─────────┐
              │                   │
       dino_status           qwen_status
              │                   │
              ▼                   ▼
       dino_worker.py       qwen_worker.py
              │                   │
        Hybrid v12              Qwen
        DINO CPU               GPU
              │                   │
              ▼                   ▼
         DINO-поля             Qwen-поля
              │                   │
              └─────────┬─────────┘
                        ▼
                  одна запись
                    photo_id
```

И это как раз соответствует твоему требованию: **Hybrid v12 — уже отточенный механизм, ему не надо ничего придумывать; от него нужен только результат.**

Единственное, что сейчас надо **точно установить** — старый технический запуск действительно выставляет `SCENE_DEVICE=cpu` для DINO, а Qwen оставляет на GPU.

Покажи именно участок `photo_processing.py` примерно **400–480 и 540–620** — там будет окончательно видно, как старый интерфейс запускает оба worker-а и куда именно задаётся CPU/GPU.

---

### 👤 **User** — 2026-08-20 23:53:42

технический раздел нужно пернести полностью, оттуда как раз и запускаются все механизмы и есть настройки вотчера и автоматика

---

### 🤖 **Assistant** — 2026-08-20 23:53:42

Да. Тогда **технический раздел не переписываем по смыслу и не упрощаем** — его нужно перенести **целиком как управляющий слой**.

То есть сохраняем из старого интерфейса:

- запуск/остановку `dino_worker.py`;
- запуск/остановку `qwen_worker.py`;
- настройки DINO, включая **CPU**;
- настройки Qwen/Ollama, включая **GPU**;
- watcher;
- автоматический запуск;
- очереди и статусы;
- мониторинг прогресса;
- восстановление после остановки/сбоя;
- техническую статистику;
- настройки Hybrid/DINO;
- существующую логику запуска процессов;
- всё, что связано с автоматикой.

И при этом **не переносим старую предметную логику интерфейса туда, где она больше не нужна**. Сам механизм остаётся тем же, меняется только место, из которого он управляется.

### Целевая архитектура

```text
                 ТЕХНИЧЕСКИЙ РАЗДЕЛ
                         │
          ┌──────────────┼──────────────┐
          │              │              │
       WATCHER         DINO           QWEN
          │              │              │
          │       dino_worker.py   qwen_worker.py
          │              │              │
          │         Hybrid v12       Qwen3-VL
          │              │              │
          │           CPU             GPU
          │              │              │
          └──────────────┼──────────────┘
                         │
                         ▼
                    PostgreSQL
                       photos
                         │
                 ┌───────┴───────┐
                 │               │
              DINO-поля       Qwen-поля
                 │               │
                 └──── photo_id ─┘
```

**Особенно важно:** технический раздел должен остаться единой точкой управления. Не надо делать отдельные новые кнопки запуска где-то ещё и дублировать автоматику.

И да — с учётом того, что ты сказал раньше, **DINO/Hybrid оставляем на CPU**, потому что текущая скорость тебя устраивает, а **GPU оставляем Qwen**. Это позволит двум механизмам работать параллельно и не конкурировать за видеопамять.

Следующий правильный шаг — **сначала полностью снять старый технический раздел по файлам**, включая watcher и automation, и только после этого переносить его в текущую архитектуру.

---

### 👤 **User** — 2026-08-20 23:54:18

весь тех раздел нужно пернести со всеми закладками - можно даже оставить в nice gui

---

### 🤖 **Assistant** — 2026-08-20 23:54:19

Да, именно так и сделаем.

**Технический раздел переносим целиком, со всеми вкладками и всей существующей логикой.** Если текущая реализация на NiceGUI рабочая, **оставляем NiceGUI** — нет смысла переписывать этот слой.

Что переносим:

- все вкладки технического раздела;
- DINO / Hybrid;
- Qwen;
- watcher;
- автоматику;
- настройки запуска;
- CPU/GPU режимы;
- кнопки запуска/остановки;
- статусы процессов;
- прогресс;
- счётчики `done / processing / pending / error`;
- логи;
- последний запуск;
- статистику;
- восстановление зависших задач;
- все существующие настройки;
- связи с PostgreSQL;
- существующий механизм запуска worker-ов.

**Главный принцип:** не изобретать новый технический раздел, а перенести уже отработанный.

При этом текущая рабочая архитектура остаётся:

```text
PostgreSQL
    │
    ├── dino_status ──> dino_worker.py ──> Hybrid v12 / DINO ── CPU
    │                         │
    │                         └──> результат в ту же photos.photo_id
    │
    └── qwen_status ──> qwen_worker.py ──> Qwen3-VL ── GPU
                              │
                              └──> результат в ту же photos.photo_id

Watcher / Automation
        │
        └── управляет этими механизмами
```

То есть **технический раздел — это панель управления всей этой машиной**, а не отдельный новый механизм обработки.

И NiceGUI здесь вполне подходит. Более того, **лучше пока вообще ничего не менять визуально**, а сначала восстановить функциональность 1:1. Потом уже, если понадобится, аккуратно подчистим интерфейс.

Следовательно, сейчас нам надо найти **весь состав старого Technical Section**, а не только `photo_processing.py`: `technical.py`, все `technical_modules/*`, watcher, automation и связанные настройки/скрипты.

---

### 👤 **User** — 2026-08-20 23:54:37

fdfq

---

### 🤖 **Assistant** — 2026-08-20 23:54:38

Похоже, случайно набралось `fdfq`. Продолжаем с переносом технического раздела.

---

### 👤 **User** — 2026-08-20 23:54:44

да

---

### 🤖 **Assistant** — 2026-08-20 23:54:45

Да. Тогда идём **без переделки архитектуры**.

Первым делом нужно снять полный состав старого технического раздела. Выполни из проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ TECHNICAL TREE ================" && \
find app/web/components/technical_modules -maxdepth 2 -type f -print | sort && \
echo && \
echo "================ TECHNICAL ================" && \
nl -ba app/web/components/technical.py | sed -n '1,500p' && \
echo && \
echo "================ MODULE IMPORTS ================" && \
grep -RniE \
'from .*technical|import .*technical|show_technical|watcher|automation|schedule|watch|timer|subprocess|Popen|DINO_WORKER|QWEN_WORKER' \
app/web app/workers scripts \
--include="*.py" \
--include="*.sh" | head -n 500
```

После этого отдельно снимем **все файлы `technical_modules` целиком**, потому что именно там, судя по уже найденному коду, находится большая часть механики.

Ничего пока не меняем.

Цель первого этапа — получить точную карту:

**Technical → вкладки → watcher → automation → DINO → Hybrid → Qwen → настройки → запуск/остановка → PostgreSQL.**

После этого уже перенесём раздел целиком в текущий NiceGUI.

---

### 👤 **User** — 2026-08-20 23:55:16

echo && \
echo "================ TECHNICAL ================" && \
nl -ba app/web/components/technical.py | sed -n '1,500p' && \
echo && \
echo "================ MODULE IMPORTS ================" && \
grep -RniE \
'from .*technical|import .*technical|show_technical|watcher|automation|schedule|watch|timer|subprocess|Popen|DINO_WORKER|QWEN_WORKER' \
app/web app/workers scripts \
--include="*.py" \
--include="*.sh" | head -n 500
================ TECHNICAL TREE ================
app/web/components/technical_modules/automation.py
app/web/components/technical_modules/automation.py.bak_20260819
app/web/components/technical_modules/automation.py.bak_modes
app/web/components/technical_modules/automation.py.bak_v01
app/web/components/technical_modules/data.py
app/web/components/technical_modules/data.py.bak_qwen_fix
app/web/components/technical_modules/fingerprints.py
app/web/components/technical_modules/__init__.py
app/web/components/technical_modules/last_run.py
app/web/components/technical_modules/photo_processing.py
app/web/components/technical_modules/photo_processing.py.bak
app/web/components/technical_modules/photo_processing.py.bak_before_hybrid_button
app/web/components/technical_modules/photo_processing.py.bak_before_path_fix
app/web/components/technical_modules/photo_processing.py.bak_before_qwen_integration
app/web/components/technical_modules/photo_processing.py.bak_button_error_debug
app/web/components/technical_modules/photo_processing.py.broken_backup
app/web/components/technical_modules/__pycache__/automation.cpython-312.pyc
app/web/components/technical_modules/__pycache__/data.cpython-312.pyc
app/web/components/technical_modules/__pycache__/fingerprints.cpython-312.pyc
app/web/components/technical_modules/__pycache__/__init__.cpython-312.pyc
app/web/components/technical_modules/__pycache__/last_run.cpython-312.pyc
app/web/components/technical_modules/__pycache__/photo_processing.cpython-312.pyc
app/web/components/technical_modules/__pycache__/qwen.cpython-312.pyc
app/web/components/technical_modules/__pycache__/system.cpython-312.pyc
app/web/components/technical_modules/__pycache__/users.cpython-312.pyc
app/web/components/technical_modules/qwen.py
app/web/components/technical_modules/qwen.py.bak
app/web/components/technical_modules/qwen.py.bak_before_safe_manual
app/web/components/technical_modules/qwen.py.bak_click_debug
app/web/components/technical_modules/qwen.py.bak_manual_run
app/web/components/technical_modules/qwen.py.bak_realtime_stop
app/web/components/technical_modules/system.py
app/web/components/technical_modules/system.py.bak_before_monitor
app/web/components/technical_modules/users.py
app/web/components/technical_modules/users.py.bak
app/web/components/technical_modules/users.py.bak_20260819
app/web/components/technical_modules/users.py.bak_20260819_colorfix
app/web/components/technical_modules/users.py.bak_20260819_preview
app/web/components/technical_modules/users.py.bak_before_session_auth
app/web/components/technical_modules/users.py.broken_20260819

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
    12	from app.web.components.technical_modules.data import (
    13	    build_data,
    14	)
    15	from app.web.components.technical_modules.system import (
    16	    build_system,
    17	)
    18	from app.web.components.technical_modules.fingerprints import (
    19	    build_fingerprints,
    20	)
    21	from app.web.components.technical_modules.users import build_users
    22	
    23	
    24	TECHNICAL_STORAGE_KEY = "albion_technical_window_size"
    25	
    26	
    27	def _restore_and_watch_size():
    28	    """
    29	    Восстанавливает размер технического окна из localStorage
    30	    и запоминает последующие изменения размера.
    31	    """
    32	
    33	    ui.run_javascript(
    34	        f"""
    35	        setTimeout(() => {{
    36	            const card = document.getElementById('technical-dialog-card');
    37	
    38	            if (!card) {{
    39	                return;
    40	            }}
    41	
    42	            const storageKey = '{TECHNICAL_STORAGE_KEY}';
    43	
    44	            // ------------------------------------------------
    45	            // RESTORE
    46	            // ------------------------------------------------
    47	
    48	            try {{
    49	                const saved = localStorage.getItem(storageKey);
    50	
    51	                if (saved) {{
    52	                    const size = JSON.parse(saved);
    53	
    54	                    if (size.width) {{
    55	                        card.style.width = size.width + 'px';
    56	                    }}
    57	
    58	                    if (size.height) {{
    59	                        card.style.height = size.height + 'px';
    60	                    }}
    61	                }}
    62	            }} catch (error) {{
    63	                console.warn(
    64	                    'Не удалось восстановить размер технического окна',
    65	                    error
    66	                );
    67	            }}
    68	
    69	            // ------------------------------------------------
    70	            // WATCH RESIZE
    71	            // ------------------------------------------------
    72	
    73	            if (card.__albionResizeObserver) {{
    74	                card.__albionResizeObserver.disconnect();
    75	            }}
    76	
    77	            card.__albionResizeObserver = new ResizeObserver(() => {{
    78	                try {{
    79	                    localStorage.setItem(
    80	                        storageKey,
    81	                        JSON.stringify({{
    82	                            width: Math.round(card.offsetWidth),
    83	                            height: Math.round(card.offsetHeight)
    84	                        }})
    85	                    );
    86	                }} catch (error) {{
    87	                    console.warn(
    88	                        'Не удалось сохранить размер технического окна',
    89	                        error
    90	                    );
    91	                }}
    92	            }});
    93	
    94	            card.__albionResizeObserver.observe(card);
    95	
    96	        }}, 100);
    97	        """
    98	    )
    99	
   100	
   101	def show_technical(
   102	    initial_tab="photo_processing",
   103	    on_close=None,
   104	):
   105	
   106	    with ui.dialog().props("persistent") as dialog:
   107	
   108	        def close_dialog():
   109	            if on_close:
   110	                on_close()
   111	            dialog.close()
   112	
   113	        with ui.card().props(
   114	            "id=technical-dialog-card"
   115	        ).classes(
   116	            "technical-dialog-card"
   117	        ).style(
   118	            """
   119	            width: 1000px;
   120	            height: 760px;
   121	            min-width: 700px;
   122	            min-height: 500px;
   123	            max-width: 96vw;
   124	            max-height: 94vh;
   125	            resize: both;
   126	            overflow: hidden;
   127	            """
   128	        ):
   129	
   130	            # ====================================================
   131	            # HEADER
   132	            # ====================================================
   133	
   134	            with ui.row().classes(
   135	                "w-full items-center justify-between"
   136	            ):
   137	
   138	                ui.label(
   139	                    "⚙ Технический раздел"
   140	                ).classes(
   141	                    "text-xl font-bold"
   142	                )
   143	
   144	                ui.button(
   145	                    icon="close",
   146	                    on_click=close_dialog,
   147	                ).props(
   148	                    "flat"
   149	                )
   150	
   151	            ui.separator()
   152	
   153	            # ====================================================
   154	            # TABS
   155	            # ====================================================
   156	
   157	            with ui.tabs().classes(
   158	                "w-full"
   159	            ) as tabs:
   160	
   161	                ui.tab(
   162	                    "photo_processing",
   163	                    label="Обработка фото",
   164	                    icon="photo_library",
   165	                )
   166	
   167	                ui.tab(
   168	                    "last_run",
   169	                    label="Последний запуск",
   170	                    icon="history",
   171	                )
   172	
   173	                ui.tab(
   174	                    "automation",
   175	                    label="Автоматизация",
   176	                    icon="autorenew",
   177	                )
   178	
   179	                ui.tab(
   180	                    "data",
   181	                    label="Данные",
   182	                    icon="storage",
   183	                )
   184	
   185	                ui.tab(
   186	                    "system",
   187	                    label="Система",
   188	                    icon="computer",
   189	                )
   190	
   191	                ui.tab(
   192	                    "fingerprints",
   193	                    label="Fingerprints",
   194	                    icon="fingerprint",
   195	                )
   196	
   197	                ui.tab(
   198	                    "users",
   199	                    label="Пользователи",
   200	                    icon="people",
   201	                )
   202	
   203	            ui.separator()
   204	
   205	            # ====================================================
   206	            # TAB CONTENT
   207	            # ====================================================
   208	
   209	            with ui.scroll_area().classes(
   210	                "w-full flex-1"
   211	            ):
   212	
   213	                with ui.tab_panels(
   214	                    tabs,
   215	                    value="photo_processing",
   216	                ).classes(
   217	                    "w-full"
   218	                ):
   219	
   220	                    with ui.tab_panel("photo_processing"):
   221	                        build_photo_processing()
   222	
   223	                    with ui.tab_panel("last_run"):
   224	                        build_last_run()
   225	
   226	                    with ui.tab_panel("automation"):
   227	                        build_automation()
   228	
   229	
   230	                    with ui.tab_panel("data"):
   231	                        build_data()
   232	
   233	                    with ui.tab_panel("system"):
   234	                        build_system()
   235	
   236	                    with ui.tab_panel("fingerprints"):
   237	                        build_fingerprints()
   238	
   239	                    with ui.tab_panel("users"):
   240	                        build_users()
   241	
   242	    dialog.open()
   243	
   244	    # Открываем нужную вкладку сразу.
   245	    if initial_tab:
   246	        ui.timer(
   247	            0.05,
   248	            lambda: tabs.set_value(initial_tab),
   249	            once=True,
   250	        )
   251	
   252	    _restore_and_watch_size()

================ MODULE IMPORTS ================
app/web/components/technical_modules/photo_processing.py:21:DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
app/web/components/technical_modules/photo_processing.py:22:QWEN_WORKER = PROJECT / "app" / "workers" / "qwen_worker.py"
app/web/components/technical_modules/photo_processing.py:436:        if not DINO_WORKER.exists():
app/web/components/technical_modules/photo_processing.py:439:                f"Не найден DINO worker: {DINO_WORKER}",
app/web/components/technical_modules/photo_processing.py:465:                await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:469:                    str(DINO_WORKER),
app/web/components/technical_modules/photo_processing.py:472:                    stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/photo_processing.py:473:                    stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/photo_processing.py:578:        if not QWEN_WORKER.exists():
app/web/components/technical_modules/photo_processing.py:581:                f"Не найден Qwen worker: {QWEN_WORKER}",
app/web/components/technical_modules/photo_processing.py:607:                await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:611:                    str(QWEN_WORKER),
app/web/components/technical_modules/photo_processing.py:614:                    stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/photo_processing.py:615:                    stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/photo_processing.py:1078:    ui.timer(
app/web/components/technical_modules/system.py:121:    ui.timer(
app/web/components/technical_modules/automation.py:12:    set_watcher,
app/web/components/technical_modules/automation.py:17:    MODE_WATCHER,
app/web/components/technical_modules/automation.py:28:def build_automation():
app/web/components/technical_modules/automation.py:62:                    MODE_WATCHER: "Watcher",
app/web/components/technical_modules/automation.py:72:                    "[AUTOMATION] MODE CHANGE:",
app/web/components/technical_modules/automation.py:79:                    MODE_WATCHER,
app/web/components/technical_modules/automation.py:94:            "Выберите режим запуска: ручной, Watcher "
app/web/components/technical_modules/automation.py:99:        # WATCHER PATH
app/web/components/technical_modules/automation.py:105:            watcher_path_input = ui.input(
app/web/components/technical_modules/automation.py:106:                "Папка для Watcher",
app/web/components/technical_modules/automation.py:107:                value=state.watcher_path or "",
app/web/components/technical_modules/automation.py:114:            watcher_path_input.tooltip(
app/web/components/technical_modules/automation.py:116:                "контролировать в режиме Watcher. "
app/web/components/technical_modules/automation.py:125:            with ui.dialog() as watcher_folder_dialog, ui.card().classes(
app/web/components/technical_modules/automation.py:129:                    "Выбор папки для Watcher"
app/web/components/technical_modules/automation.py:141:                    "path": state.watcher_path or str(Path.home())
app/web/components/technical_modules/automation.py:207:                            "[AUTOMATION] FOLDER PICKER ERROR:",
app/web/components/technical_modules/automation.py:221:                def open_watcher_folder_dialog():
app/web/components/technical_modules/automation.py:223:                        watcher_path_input.value
app/web/components/technical_modules/automation.py:224:                        or state.watcher_path
app/web/components/technical_modules/automation.py:229:                    watcher_folder_dialog.open()
app/web/components/technical_modules/automation.py:231:                def select_watcher_folder():
app/web/components/technical_modules/automation.py:234:                    watcher_path_input.value = path
app/web/components/technical_modules/automation.py:238:                    if current.mode == MODE_WATCHER:
app/web/components/technical_modules/automation.py:240:                            set_watcher(path)
app/web/components/technical_modules/automation.py:243:                                "[AUTOMATION] WATCHER PATH ERROR:",
app/web/components/technical_modules/automation.py:249:                                f"Ошибка пути Watcher: {exc}",
app/web/components/technical_modules/automation.py:254:                    watcher_folder_dialog.close()
app/web/components/technical_modules/automation.py:258:                        f"Папка Watcher выбрана: {path}",
app/web/components/technical_modules/automation.py:267:                        on_click=watcher_folder_dialog.close,
app/web/components/technical_modules/automation.py:272:                        on_click=select_watcher_folder,
app/web/components/technical_modules/automation.py:277:                on_click=open_watcher_folder_dialog,
app/web/components/technical_modules/automation.py:393:            elif current.mode == MODE_WATCHER:
app/web/components/technical_modules/automation.py:394:                path = current.watcher_path or "—"
app/web/components/technical_modules/automation.py:397:                    "● Режим: Watcher"
app/web/components/technical_modules/automation.py:418:            watcher_enabled = (
app/web/components/technical_modules/automation.py:419:                current.mode == MODE_WATCHER
app/web/components/technical_modules/automation.py:426:            watcher_path_input.enabled = True
app/web/components/technical_modules/automation.py:450:                elif mode == MODE_WATCHER:
app/web/components/technical_modules/automation.py:452:                    watcher_path = (
app/web/components/technical_modules/automation.py:453:                        watcher_path_input.value or ""
app/web/components/technical_modules/automation.py:456:                    if not watcher_path:
app/web/components/technical_modules/automation.py:458:                            "Укажите папку для Watcher",
app/web/components/technical_modules/automation.py:464:                    set_watcher(
app/web/components/technical_modules/automation.py:465:                        watcher_path
app/web/components/technical_modules/automation.py:483:                    "[AUTOMATION] MODE ERROR:",
app/web/components/technical_modules/automation.py:496:        # WATCHER PATH CHANGE
app/web/components/technical_modules/automation.py:499:        def watcher_path_changed(event):
app/web/components/technical_modules/automation.py:503:            if current.mode != MODE_WATCHER:
app/web/components/technical_modules/automation.py:513:                    "Путь Watcher не может быть пустым",
app/web/components/technical_modules/automation.py:522:                set_watcher(path)
app/web/components/technical_modules/automation.py:529:                    "[AUTOMATION] WATCHER PATH ERROR:",
app/web/components/technical_modules/automation.py:535:                    f"Ошибка пути Watcher: {exc}",
app/web/components/technical_modules/automation.py:541:        watcher_path_input.on(
app/web/components/technical_modules/automation.py:543:            watcher_path_changed,
app/web/components/technical_modules/automation.py:572:                    "[AUTOMATION] TIME ERROR:",
app/web/components/technical_modules/qwen.py:440:            process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/qwen.py:453:                stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/qwen.py:454:                stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/qwen.py:778:    ui.timer(
app/web/components/header.py:16:from app.web.components.technical import show_technical
app/web/components/header.py:486:            show_technical(
app/web/components/technical.py:3:from app.web.components.technical_modules.photo_processing import (
app/web/components/technical.py:6:from app.web.components.technical_modules.last_run import (
app/web/components/technical.py:9:from app.web.components.technical_modules.automation import (
app/web/components/technical.py:10:    build_automation,
app/web/components/technical.py:12:from app.web.components.technical_modules.data import (
app/web/components/technical.py:15:from app.web.components.technical_modules.system import (
app/web/components/technical.py:18:from app.web.components.technical_modules.fingerprints import (
app/web/components/technical.py:21:from app.web.components.technical_modules.users import build_users
app/web/components/technical.py:27:def _restore_and_watch_size():
app/web/components/technical.py:70:            // WATCH RESIZE
app/web/components/technical.py:101:def show_technical(
app/web/components/technical.py:174:                    "automation",
app/web/components/technical.py:226:                    with ui.tab_panel("automation"):
app/web/components/technical.py:227:                        build_automation()
app/web/components/technical.py:246:        ui.timer(
app/web/components/technical.py:252:    _restore_and_watch_size()
app/web/main.py:66:ui.timer(
app/web/system/monitor.py:3:import subprocess
app/web/system/monitor.py:27:        result = subprocess.run(
scripts/sort_test_and_report_v2.py:7:import subprocess
scripts/sort_test_and_report_v2.py:33:        result = subprocess.run(
scripts/sort_test_and_report_v2.py:120:    process = subprocess.run(
scripts/benchmark_test_v1.py:5:import subprocess
scripts/benchmark_test_v1.py:113:    proc = subprocess.run(
scripts/benchmark_test_sub_exp.py:5:import subprocess
scripts/benchmark_test_sub_exp.py:132:    proc = subprocess.run(
scripts/sort_test_and_report_hybrid_v12.py:7:import subprocess
scripts/sort_test_and_report_hybrid_v12.py:33:        result = subprocess.run(
scripts/sort_test_and_report_hybrid_v12.py:120:    process = subprocess.run(
scripts/run_hybrid_v12.py:6:import subprocess
scripts/run_hybrid_v12.py:129:    process = subprocess.run(
scripts/benchmark_qwen_vl.py:7:import subprocess
scripts/benchmark_client_models_25.py:6:import subprocess
scripts/benchmark_client_models_25.py:151:        subprocess.run(
scripts/benchmark_client_models_25.py:153:            stdout=subprocess.DEVNULL,
scripts/benchmark_client_models_25.py:154:            stderr=subprocess.DEVNULL,
scripts/llm_resolver_v01.py:5:import subprocess
scripts/llm_resolver_v01.py:166:    result = subprocess.run(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:55:18

Да. Теперь картина уже достаточно ясная.

**Старый технический раздел фактически является готовым управляющим контуром**, и его действительно надо переносить целиком, а не собирать заново.

### Что в нём есть

Главный `technical.py` собирает **7 вкладок**:

1. **Обработка фото**
   - DINO / Hybrid v12
   - Qwen3-VL 4B
   - отдельный запуск/остановка
   - прогресс
   - `pending / processing / done / error`
   - реальные `dino_worker.py` и `qwen_worker.py`

2. **Последний запуск**
   - информация о последнем запуске обработки.

3. **Автоматизация**
   - ручной режим;
   - Watcher;
   - папка Watcher;
   - управление режимом;
   - автоматический запуск;
   - настройки времени/режима.

4. **Данные**
   - статистика DINO;
   - Hybrid v12;
   - Qwen;
   - данные PostgreSQL;
   - состояние обработки.

5. **Система**
   - системный монитор;
   - CPU/GPU/RAM/VRAM и т. д.

6. **Fingerprints**
   - управление/информация по отпечаткам.

7. **Пользователи**
   - пользователи и авторизация.

### Самое важное

У нас уже подтверждена правильная граница:

```text
ТЕХНИЧЕСКИЙ РАЗДЕЛ
        │
        ├── Обработка фото
        │      │
        │      ├── dino_worker.py
        │      │      └── Hybrid v12 / DINO
        │      │
        │      └── qwen_worker.py
        │             └── Qwen3-VL 4B
        │
        ├── Последний запуск
        ├── Автоматизация
        │      └── Watcher
        ├── Данные
        ├── Система
        ├── Fingerprints
        └── Пользователи
```

И запуск уже реализован именно через отдельные процессы:

```python
asyncio.create_subprocess_exec(...)
```

То есть **NiceGUI здесь не выполняет DINO/Qwen внутри веб-процесса**. Он только управляет worker-ами. Это очень хорошая архитектура, её сохраняем.

---

### И ещё один важный момент по твоему вопросу о CPU

В показанном `config.py` **DINO сейчас не принудительно на CPU**:

```python
device = os.getenv(
    "SCENE_DEVICE",
    "cuda" if torch.cuda.is_available() else "cpu"
)
```

То есть если worker запускается в обычном окружении с доступной CUDA, `SceneEmbedder` автоматически выберет:

```text
cuda
```

А `embedder.py` затем делает:

```python
self.model = self.model.to(self.device)
```

Поэтому **сам код worker-а не означает, что DINO работает на CPU**.

Если раньше ты переводил Hybrid/DINO на CPU, это должно было делаться через окружение, например:

```bash
SCENE_DEVICE=cpu
```

И вот это как раз нужно **найти в старом техническом разделе/автоматике**, прежде чем что-либо менять.

---

### Сейчас ничего не исправляем

Следующий шаг я бы сделал очень конкретным: **найти, какие именно environment variables технический раздел выставляет при запуске DINO и Qwen**.

Особенно нужны:

```text
SCENE_DEVICE
SCENE_MODEL
SCENE_BATCH
DINO_MAX_ITEMS
CUDA_VISIBLE_DEVICES
OLLAMA
QWEN
WATCHER
```

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ ENV / DINO / QWEN / WATCHER ================" && \
grep -RniE \
'SCENE_DEVICE|SCENE_MODEL|SCENE_BATCH|DINO_MAX_ITEMS|CUDA_VISIBLE_DEVICES|OLLAMA|QWEN|WATCHER|watcher|environment|env=' \
app scripts \
--include="*.py" \
--include="*.sh" \
| head -n 500
```

**После этого мы точно увидим, где был зафиксирован твой режим: DINO/Hybrid → CPU, Qwen → GPU.**

И только потом будем переносить технический раздел.

---

