## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-20 23:39:51

"port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

def main():

    conn = psycopg2.connect(**DB_CONFIG)

PY  main()_ == "__main__":ructed from the current DB fields alone.")e")ors, ensu
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/diagnose_dino_hybrid_db.py

====================================================================================================
DINO -> POSTGRES -> HYBRID DIAGNOSTIC
====================================================================================================

Rows: 30

----------------------------------------------------------------------------------------------------
id                  : 526
photo_id            : PH_00000526
filename            : Шолохова 127 А (9).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8843672466278076
dino_second_score   : 0.8525879204273223
dino_margin         : 0.03177932620048529
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 525
photo_id            : PH_00000525
filename            : Шолохова 127 А (8).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8970452749729155
dino_second_score   : 0.8808208197355271
dino_margin         : 0.01622445523738847
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 524
photo_id            : PH_00000524
filename            : Шолохова 127 А (7).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8904132449626921
dino_second_score   : 0.8756258612871168
dino_margin         : 0.014787383675575305
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 523
photo_id            : PH_00000523
filename            : Шолохова 127 А (6).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8736575585603713
dino_second_score   : 0.8586697649955749
dino_margin         : 0.014987793564796403
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 522
photo_id            : PH_00000522
filename            : Шолохова 127 А (5).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8984276247024536
dino_second_score   : 0.8798490905761719
dino_margin         : 0.018578534126281743
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 521
photo_id            : PH_00000521
filename            : Шолохова 127 А (4).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8974342620372772
dino_second_score   : 0.8775184828042984
dino_margin         : 0.019915779232978714
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 520
photo_id            : PH_00000520
filename            : Шолохова 127 А (3).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.9046348762512207
dino_second_score   : 0.8852626359462736
dino_margin         : 0.019372240304947108
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 519
photo_id            : PH_00000519
filename            : Шолохова 127 А (2).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8618447566032409
dino_second_score   : 0.8615931856632232
dino_margin         : 0.0002515709400177091
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 518
photo_id            : PH_00000518
filename            : Шолохова 127 А (19).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8940805959701538
dino_second_score   : 0.8718812644481658
dino_margin         : 0.02219933152198794
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 517
photo_id            : PH_00000517
filename            : Шолохова 127 А (18).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8924807512760162
dino_second_score   : 0.8799367851018907
dino_margin         : 0.012543966174125565
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 516
photo_id            : PH_00000516
filename            : Шолохова 127 А (17).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8944720298051834
dino_second_score   : 0.8666357392072677
dino_margin         : 0.027836290597915703
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 515
photo_id            : PH_00000515
filename            : Шолохова 127 А (16).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.851322934627533
dino_second_score   : 0.8352598595619203
dino_margin         : 0.016063075065612664
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 514
photo_id            : PH_00000514
filename            : Шолохова 127 А (15).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.7879115408658982
dino_second_score   : 0.7679122918844222
dino_margin         : 0.01999924898147598
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 513
photo_id            : PH_00000513
filename            : Шолохова 127 А (14).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8080845338106155
dino_second_score   : 0.7955688482522965
dino_margin         : 0.012515685558319056
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 512
photo_id            : PH_00000512
filename            : Шолохова 127 А (13).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.7006912517547607
dino_second_score   : 0.6869233208894729
dino_margin         : 0.013767930865287714
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 511
photo_id            : PH_00000511
filename            : Шолохова 127 А (12).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.9007747375965118
dino_second_score   : 0.8843768554925919
dino_margin         : 0.016397882103919903
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 510
photo_id            : PH_00000510
filename            : Шолохова 127 А (11).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8698311281204224
dino_second_score   : 0.8615509045124052
dino_margin         : 0.008280223608017168
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 509
photo_id            : PH_00000509
filename            : Шолохова 127 А (10).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8889733201265334
dino_second_score   : 0.8715850049257278
dino_margin         : 0.017388315200805637
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 508
photo_id            : PH_00000508
filename            : Шолохова 127 А (1).JPG
dino_status         : done
dino_fingerprint    : 94_v33
dino_score          : 0.8989868396520614
dino_second_score   : 0.876552192568779
dino_margin         : 0.022434647083282355
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 507
photo_id            : PH_00000507
filename            : Шеболдаева8_18.JPG
dino_status         : done
dino_fingerprint    : 87_v33
dino_score          : 0.9412475711107254
dino_second_score   : 0.8578296142816544
dino_margin         : 0.08341795682907105
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 506
photo_id            : PH_00000506
filename            : Шеболдаева8_17.JPG
dino_status         : done
dino_fingerprint    : 87_v33
dino_score          : 0.95251056432724
dino_second_score   : 0.8662840563058852
dino_margin         : 0.08622650802135479
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 505
photo_id            : PH_00000505
filename            : Шеболдаева8_16.JPG
dino_status         : done
dino_fingerprint    : 87_v33
dino_score          : 0.8904967111349106
dino_second_score   : 0.8504330492019654
dino_margin         : 0.040063661932945194
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 504
photo_id            : PH_00000504
filename            : Шеболдаева8_15.JPG
dino_status         : done
dino_fingerprint    : 87_v33
dino_score          : 0.8838203406333923
dino_second_score   : 0.8485370391607283
dino_margin         : 0.03528330147266401
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 503
photo_id            : PH_00000503
filename            : Шеболдаева8_14.JPG
dino_status         : done
dino_fingerprint    : 87_v33
dino_score          : 0.9045538741350174
dino_second_score   : 0.8636467719078064
dino_margin         : 0.040907102227211056
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 502
photo_id            : PH_00000502
filename            : Шеболдаева8_13.JPG
dino_status         : done
dino_fingerprint    : 87_v33
dino_score          : 0.8943867772817612
dino_second_score   : 0.8597279000282287
dino_margin         : 0.03465887725353245
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 501
photo_id            : PH_00000501
filename            : Шеболдаева8_12.JPG
dino_status         : done
dino_fingerprint    : 87_v33
dino_score          : 0.9103231596946716
dino_second_score   : 0.8565801537036897
dino_margin         : 0.05374300599098192
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 500
photo_id            : PH_00000500
filename            : Шеболдаева8_11.JPG
dino_status         : done
dino_fingerprint    : 87_v33
dino_score          : 0.8675140887498854
dino_second_score   : 0.8300860309600829
dino_margin         : 0.037428057789802516
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 499
photo_id            : PH_00000499
filename            : Шеболдаева8_10.JPG
dino_status         : done
dino_fingerprint    : 87_v33
dino_score          : 0.9319810193777084
dino_second_score   : 0.8626089876890182
dino_margin         : 0.06937203168869022
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 498
photo_id            : PH_00000498
filename            : Шеболдаева8_08.JPG
dino_status         : done
dino_fingerprint    : 87_v33
dino_score          : 0.9275560045242309
dino_second_score   : 0.8515058219432831
dino_margin         : 0.07605018258094787
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null
----------------------------------------------------------------------------------------------------
id                  : 497
photo_id            : PH_00000497
filename            : Шеболдаева8_07.JPG
dino_status         : done
dino_fingerprint    : 87_v33
dino_score          : 0.9491383659839631
dino_second_score   : 0.881496483683586
dino_margin         : 0.06764188230037704
hybrid_original_id  : None
hybrid_final_id     : None
hybrid_changed      : False
hybrid_old_score    : None
hybrid_score        : None
hybrid_margin       : None
hybrid_neighbors    : null

====================================================================================================
SUMMARY
====================================================================================================

DINO done           : 30
DINO with fingerprint: 30
Hybrid final present: 0
Hybrid changed      : 0

DINO fingerprints:
  94_v33               19
  87_v33               11

====================================================================================================
IMPORTANT
====================================================================================================

PostgreSQL currently contains:
  dino_fingerprint
  dino_score
  dino_second_score
  dino_margin

But old Hybrid v12 requires:
  TOP1
  TOP2
  TOP3
  TOP4
  TOP5

Therefore exact old V12 Global TOP-5 cannot yet be
reconstructed from the current DB fields alone.

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:39:55

Да. Теперь картина стала намного яснее.

**Сейчас у нас есть разрыв именно между DINO и Hybrid:**

`dino_worker.py` записывает в PostgreSQL:

- `dino_fingerprint`
- `dino_score`
- `dino_second_score`
- `dino_margin`

Но старый **Hybrid v12** ожидает на вход не эти 4 поля, а полноценный набор:

- `top1`
- `top1_score`
- `top2`
- `top2_score`
- `top3`
- `top3_score`
- `top4`
- `top4_score`
- `top5`
- `top5_score`

И это принципиально важно: **Hybrid v12 не должен заново получать фотографии из своей логики.** Он должен работать поверх результатов DINO/БД.

При этом сам найденный `run_hybrid_v12.py` показывает, что старая связка была другой: он **сам запускал `scene-fingerprint recognize`**, получал TOP-5, затем применял Hybrid и только после этого формировал `best_id`.

То есть сейчас надо не переписывать Hybrid наугад, а **восстановить старую рабочую точку интеграции DINO → TOP-5 → Hybrid → PostgreSQL**.

Следующий шаг предлагаю сделать диагностическим, ничего пока не менять.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ dino_worker ================" && \
nl -ba app/workers/dino_worker.py | sed -n '1,240p' && \
echo && \
echo "================ daily hybrid ================" && \
nl -ba scripts/run_daily_hybrid_v12.sh | sed -n '1,140p' && \
echo && \
echo "================ hybrid DB/output ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '420,740p'
```

**Особенно нас интересуют последние ~300 строк `run_hybrid_v12.py`.**

Там будет видно, куда старый Hybrid писал свой результат и почему сейчас PostgreSQL остаётся с `hybrid_* = NULL`.

После этого мы сможем зафиксировать связку как архитектуру:

**DINO worker → PostgreSQL → Hybrid v12 → `hybrid_final_id`**

и уже потом сделать её постоянной, чтобы к этому больше не возвращаться.

---

### 👤 **User** — 2026-08-20 23:40:48

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ dino_worker ================" && \
nl -ba app/workers/dino_worker.py | sed -n '1,240p' && \
echo && \
echo "================ daily hybrid ================" && \
nl -ba scripts/run_daily_hybrid_v12.sh | sed -n '1,140p' && \
echo && \
echo "================ hybrid DB/output ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '420,740p'
================ dino_worker ================
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

================ daily hybrid ================
     1	#!/usr/bin/env bash
     2	
     3	set -euo pipefail
     4	
     5	PROJECT="$HOME/projects/scene_fingerprint_mvp_v02"
     6	
     7	INPUT="$PROJECT/data/input/daily"
     8	
     9	TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
    10	
    11	OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"
    12	
    13	echo
    14	echo "================================================================================"
    15	echo "SCENE FINGERPRINT — DAILY HYBRID V12"
    16	echo "================================================================================"
    17	echo
    18	echo "INPUT : $INPUT"
    19	echo "OUTPUT: $OUTPUT"
    20	echo
    21	
    22	if [ ! -d "$INPUT" ]; then
    23	    echo "ERROR: input directory does not exist:"
    24	    echo "$INPUT"
    25	    exit 1
    26	fi
    27	
    28	COUNT=$(find "$INPUT" -maxdepth 1 -type f \
    29	    $ -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" $ \
    30	    | wc -l)
    31	
    32	echo "Images: $COUNT"
    33	echo
    34	
    35	if [ "$COUNT" -eq 0 ]; then
    36	    echo "ERROR: no images found in $INPUT"
    37	    exit 1
    38	fi
    39	
    40	mkdir -p "$OUTPUT"
    41	
    42	/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
    43	    --input "$INPUT" \
    44	    --output "$OUTPUT" \
    45	    --first-address 78 \
    46	    --last-address 95
    47	
    48	echo
    49	echo "================================================================================"
    50	echo "DAILY PIPELINE FINISHED"
    51	echo "================================================================================"
    52	echo
    53	echo "Images : $COUNT"
    54	echo "Output : $OUTPUT"
    55	echo

================ hybrid DB/output ================
   420	
   421	        source = Path(
   422	            item["file"]
   423	        )
   424	
   425	        assigned_id = item.get(
   426	            "best_id"
   427	        )
   428	
   429	        if not assigned_id:
   430	            continue
   431	
   432	        destination_dir = (
   433	            output_dir / assigned_id
   434	        )
   435	
   436	        destination_dir.mkdir(
   437	            parents=True,
   438	            exist_ok=True,
   439	        )
   440	
   441	        destination = (
   442	            destination_dir / source.name
   443	        )
   444	
   445	        shutil.copy2(
   446	            source,
   447	            destination,
   448	        )
   449	
   450	        counters[assigned_id] += 1
   451	
   452	        sorted_rows.append(
   453	            {
   454	                "file": str(source),
   455	                "filename": source.name,
   456	                "assigned_id": assigned_id,
   457	                "original_best_id": item.get(
   458	                    "original_best_id"
   459	                ),
   460	                "hybrid_changed": item.get(
   461	                    "hybrid_changed"
   462	                ),
   463	                "score": item.get("score"),
   464	                "second_score": item.get(
   465	                    "second_score"
   466	                ),
   467	                "margin": item.get("margin"),
   468	                "confidence": item.get(
   469	                    "confidence"
   470	                ),
   471	                "status": item.get("status"),
   472	                "best_image": item.get(
   473	                    "best_image"
   474	                ),
   475	                "best_image_score": item.get(
   476	                    "best_image_score"
   477	                ),
   478	                "hybrid_old_score": item.get(
   479	                    "hybrid_old_score"
   480	                ),
   481	                "hybrid_score": item.get(
   482	                    "hybrid_score"
   483	                ),
   484	            }
   485	        )
   486	
   487	    for k in sorted(
   488	        counters,
   489	        key=lambda x: int(
   490	            x.split("_")[0]
   491	        ),
   492	    ):
   493	        print(
   494	            f"{k:10s} {counters[k]:4d}"
   495	        )
   496	
   497	    return sorted_rows, counters
   498	
   499	
   500	def main():
   501	
   502	    parser = argparse.ArgumentParser(
   503	        description="Production runner for frozen Hybrid v12"
   504	    )
   505	
   506	    parser.add_argument(
   507	        "--input",
   508	        required=True,
   509	        type=Path,
   510	    )
   511	
   512	    parser.add_argument(
   513	        "--output",
   514	        required=True,
   515	        type=Path,
   516	    )
   517	
   518	    parser.add_argument(
   519	        "--first-address",
   520	        type=int,
   521	        default=78,
   522	    )
   523	
   524	    parser.add_argument(
   525	        "--last-address",
   526	        type=int,
   527	        default=95,
   528	    )
   529	
   530	    args = parser.parse_args()
   531	
   532	    input_dir = args.input
   533	    output_dir = args.output
   534	
   535	    if not input_dir.exists():
   536	        raise RuntimeError(
   537	            f"Нет папки: {input_dir}"
   538	        )
   539	
   540	    fingerprints = [
   541	        f"{i}_v33"
   542	        for i in range(
   543	            args.first_address,
   544	            args.last_address + 1,
   545	        )
   546	    ]
   547	
   548	    print()
   549	    print("=" * 80)
   550	    print("SCENE FINGERPRINT — HYBRID V12 RUNNER")
   551	    print("=" * 80)
   552	    print()
   553	    print("INPUT :", input_dir)
   554	    print("OUTPUT:", output_dir)
   555	    print()
   556	    print("CONTROL:")
   557	    print("  DINO        : v33")
   558	    print("  HYBRID      : v12")
   559	    print("  ADDRESSES   :", f"{args.first_address}-{args.last_address}")
   560	    print()
   561	
   562	    total_start = time.perf_counter()
   563	
   564	    # --------------------------------------------------------
   565	    # 1. DINO
   566	    # --------------------------------------------------------
   567	
   568	    recognition, recognition_time = run_recognition(
   569	        input_dir,
   570	        fingerprints,
   571	    )
   572	
   573	    # --------------------------------------------------------
   574	    # 2. Load Hybrid subfingerprints
   575	    # --------------------------------------------------------
   576	
   577	    print()
   578	    print("=" * 80)
   579	    print("LOADING HYBRID SUBFINGERPRINTS")
   580	    print("=" * 80)
   581	
   582	    subs = load_subs()
   583	
   584	    print("Subfingerprints:", len(subs))
   585	
   586	    # --------------------------------------------------------
   587	    # 3. Hybrid v12
   588	    # --------------------------------------------------------
   589	
   590	    print()
   591	    print("=" * 80)
   592	    print("HYBRID V12")
   593	    print("=" * 80)
   594	
   595	    settings = Settings()
   596	
   597	    embedder = SceneEmbedder(
   598	        settings
   599	    )
   600	
   601	    recognition = adapt_recognizer_rows(recognition)
   602	
   603	    hybrid_rows, changed, sub_count = hybrid_v12(
   604	        recognition,
   605	        embedder,
   606	        subs,
   607	    )
   608	
   609	    print()
   610	    print("Checked:", len(hybrid_rows))
   611	    print("Border cases:", sub_count)
   612	    print("Hybrid changes:", len(changed))
   613	
   614	    for item in changed:
   615	        print()
   616	        print(
   617	            item["file"]
   618	        )
   619	        print(
   620	            item["old"],
   621	            "->",
   622	            item["new"],
   623	        )
   624	        print(
   625	            "margin:",
   626	            item["margin"],
   627	        )
   628	        print(
   629	            "neighbors:",
   630	            item["neighbors"],
   631	        )
   632	
   633	    # --------------------------------------------------------
   634	    # 4. Sort
   635	    # --------------------------------------------------------
   636	
   637	    sorted_rows, counters = sort_results(
   638	        hybrid_rows,
   639	        output_dir,
   640	    )
   641	
   642	    # --------------------------------------------------------
   643	    # 5. Reports
   644	    # --------------------------------------------------------
   645	
   646	    output_dir.mkdir(
   647	        parents=True,
   648	        exist_ok=True,
   649	    )
   650	
   651	    recognition_json = (
   652	        output_dir / "recognition.json"
   653	    )
   654	
   655	    hybrid_json = (
   656	        output_dir / "hybrid_v12.json"
   657	    )
   658	
   659	    report_json = (
   660	        output_dir / "report.json"
   661	    )
   662	
   663	    statistics_json = (
   664	        output_dir / "statistics.json"
   665	    )
   666	
   667	    recognition_json.write_text(
   668	        json.dumps(
   669	            recognition,
   670	            ensure_ascii=False,
   671	            indent=2,
   672	        ),
   673	        encoding="utf-8",
   674	    )
   675	
   676	    hybrid_json.write_text(
   677	        json.dumps(
   678	            hybrid_rows,
   679	            ensure_ascii=False,
   680	            indent=2,
   681	        ),
   682	        encoding="utf-8",
   683	    )
   684	
   685	    report_json.write_text(
   686	        json.dumps(
   687	            sorted_rows,
   688	            ensure_ascii=False,
   689	            indent=2,
   690	        ),
   691	        encoding="utf-8",
   692	    )
   693	
   694	    total_time = (
   695	        time.perf_counter()
   696	        - total_start
   697	    )
   698	
   699	    statistics = {
   700	        "total_images": len(hybrid_rows),
   701	        "sorted_images": len(sorted_rows),
   702	        "recognition_time_seconds": recognition_time,
   703	        "total_wall_time_seconds": total_time,
   704	        "hybrid_border_cases": sub_count,
   705	        "hybrid_changed": len(changed),
   706	        "assigned": dict(counters),
   707	        "control": {
   708	            "recognizer": "DINOv2 v33",
   709	            "rerank": "Hybrid v12",
   710	            "margin_limit": MARGIN_LIMIT,
   711	            "global_weight": GLOBAL_WEIGHT,
   712	            "sub_weight": SUB_WEIGHT,
   713	            "neighbor_weight": NEIGHBOR_WEIGHT,
   714	        },
   715	    }
   716	
   717	    statistics_json.write_text(
   718	        json.dumps(
   719	            statistics,
   720	            ensure_ascii=False,
   721	            indent=2,
   722	        ),
   723	        encoding="utf-8",
   724	    )
   725	
   726	    print()
   727	    print("=" * 80)
   728	    print("DONE")
   729	    print("=" * 80)
   730	    print()
   731	    print("Images:", len(hybrid_rows))
   732	    print("Hybrid changes:", len(changed))
   733	    print(f"Recognition: {recognition_time:.2f} sec")
   734	    print(f"Total:       {total_time:.2f} sec")
   735	    print()
   736	    print("Output:")
   737	    print(output_dir)
   738	
   739	
   740	if __name__ == "__main__":
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:40:52

Да. Теперь картина уже однозначная.

### Что сейчас происходит

У нас **два разных контура**, и они пока не соединены:

**1. DINO worker → PostgreSQL**

`app/workers/dino_worker.py` после распознавания записывает:

- `address_id`
- `dino_fingerprint`
- `dino_score`
- `dino_second_score`
- `dino_margin`

То есть для фотографии:

`PH_00000526 → 94_v33`

это результат **чистого DINO**.

**2. Hybrid v12 → отдельный файловый результат**

`run_daily_hybrid_v12.sh` запускает:

```text
scripts/run_hybrid_v12.py
```

А тот:

```text
DINO recognition
        ↓
load_subs()
        ↓
Hybrid v12
        ↓
hybrid_rows
        ↓
sort_results()
        ↓
папка 78_v33 / 79_v33 / ... / 95_v33
```

И самое главное: **этот процесс вообще не пишет PostgreSQL**.

Поэтому сейчас абсолютно логично, что в БД:

```text
dino_fingerprint   = 94_v33
hybrid_original_id = None
hybrid_final_id    = None
hybrid_changed     = False
hybrid_score       = None
...
```

`hybrid_changed=False` здесь не означает, что Hybrid проверил фотографию и решил ничего не менять. **Hybrid для этой записи вообще не выполнялся.**

---

### И вот важный момент по твоему замечанию

Ты сказал:

> именно после гибрида образуются точные значения fingerprint id

Да. В текущей архитектуре это нужно понимать именно так:

```text
DINO
    ↓
предварительный fingerprint
    ↓
94_v33
    ↓
HYBRID V12
    ↓
окончательный fingerprint
    ↓
точный ID адреса
```

Причём Hybrid использует не только первоначальный TOP-1 DINO, а свои `subfingerprints`, глобальный score и соседей.

Это видно непосредственно из запуска:

```text
recognition
    ↓
load_subs()
    ↓
hybrid_v12(...)
    ↓
hybrid_rows
```

И затем именно:

```python
assigned_id = item.get("best_id")
```

используется для раскладки фотографии по папке:

```python
destination_dir = output_dir / assigned_id
```

То есть **`best_id` после Hybrid — это фактически финальный fingerprint ID**, которым должна пользоваться Фотобаза.

---

## Сейчас у нас архитектурная проблема

В БД поле называется:

```text
dino_fingerprint
```

но в `dino_worker.py` туда записывается:

```python
address_id = result.get("best_id")
```

а затем:

```python
dino_fingerprint = address_id
```

То есть сейчас:

```text
dino_fingerprint = результат DINO
```

А нам для конечной Фотобазы нужен:

```text
hybrid_final_id = результат HYBRID
```

И уже **после Hybrid**:

```text
финальный fingerprint ID
```

должен становиться главным идентификатором распознанного адреса.

---

### Я бы сейчас ничего не исправлял вслепую

Нужно найти **точку, где запускается текущий production pipeline**, чтобы не сломать уже работающую очередь DINO/Qwen.

Нам надо установить:

```text
upload
  ↓
photo_ingest
  ↓
DINO worker
  ↓
Qwen worker
  ↓
???
  ↓
Hybrid
  ↓
PostgreSQL
```

Сейчас мы точно видим только:

```text
DINO → PostgreSQL
```

и отдельно:

```text
daily → run_hybrid_v12.py → output folders
```

### Следующая проверка

Выполни **одну команду**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID FUNCTIONS ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,420p' && \
echo && \
echo "================ PIPELINE LAUNCHERS ================" && \
grep -RniE \
'run_daily_hybrid|run_hybrid_v12|dino_worker|qwen_worker|photo_ingest|subprocess|hybrid' \
app scripts \
--include="*.py" \
--include="*.sh" | \
grep -vE '__pycache__|benchmark|export_visual' | \
head -n 300
```

**Особенно интересуют строки `run_hybrid_v12.py` 1–420.**

Там мы увидим точный алгоритм, который превращает первоначальный:

```text
94_v33
```

в финальный:

```text
XX_v33
```

и, главное, **какое именно поле `best_id` после Hybrid является тем самым окончательным fingerprint ID**.

После этого уже можно правильно состыковать Hybrid с PostgreSQL, не трогая сам DINO-recognition.

---

### 👤 **User** — 2026-08-20 23:41:43

дино выдает 5 кандидатов, давай изучим тот вариант где гибрид запускает весь механизм

---

### 🤖 **Assistant** — 2026-08-20 23:41:44

Да. Это как раз правильный путь: **не пытаться реконструировать Hybrid из PostgreSQL**, а изучить старую рабочую связку целиком:

**DINO → TOP-5 → Hybrid v12 → финальный `best_id`**.

И у нас уже есть подтверждение, что именно так работает `run_hybrid_v12.py`:

```text
run_recognition()
        ↓
scene-fingerprint recognize
        ↓
--top-k 5
        ↓
adapt_recognizer_rows()
        ↓
top1 ... top5
        ↓
hybrid_v12()
        ↓
best_id
```

Причём DINO запускается здесь:

```python
"scene-fingerprint",
"recognize",
str(input_dir),
"--top-k", "5",
"--threshold", "0.0",
"--fingerprints", fp_arg,
"--json",
```

То есть **TOP-5 действительно получаются непосредственно из DINO recognizer**, а Hybrid уже работает поверх них.

И это намного ближе к тому, что ты описываешь как ранее рабочую систему.

### Давай сейчас изучим именно этот вариант

Ничего пока не меняем. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ 1. RECOGNIZER ================" && \
nl -ba app/core/recognizer.py | sed -n '1,360p' && \
echo && \
echo "================ 2. HYBRID RUNNER ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,420p'
```

Нам нужны **две вещи**:

1. Как `SceneRecognizer` формирует:
   ```text
   top1
   top2
   top3
   top4
   top5
   ```
   и их scores.

2. Как `hybrid_v12()` использует эти пять кандидатов и получает:
   ```text
   original_best_id
   best_id
   hybrid_changed
   ```

После этого я сопоставлю их буквально по цепочке:

```text
фото
 ↓
DINO embedding
 ↓
TOP-1 score
TOP-2 score
TOP-3 score
TOP-4 score
TOP-5 score
 ↓
Hybrid V12
 ├─ GLOBAL TOP-5
 ├─ SUB для TOP-1/TOP-2
 ├─ соседние фото
 └─ gain > 1.5
 ↓
FINAL best_id
```

И тогда уже станет понятно, **какую именно старую рабочую связку надо вернуть в текущий pipeline**, не придумывая новую логику.

---

### 👤 **User** — 2026-08-20 23:42:26

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ 1. RECOGNIZER ================" && \
nl -ba app/core/recognizer.py | sed -n '1,360p' && \
echo && \
echo "================ 2. HYBRID RUNNER ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,420p'
================ 1. RECOGNIZER ================
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

================ 2. HYBRID RUNNER ================
     1	#!/usr/bin/env python3
     2	
     3	import argparse
     4	import json
     5	import shutil
     6	import subprocess
     7	import time
     8	from collections import Counter, defaultdict
     9	from pathlib import Path
    10	
    11	import numpy as np
    12	
    13	from app.core.config import Settings
    14	from app.core.embedder import SceneEmbedder
    15	
    16	
    17	PROJECT = Path(__file__).resolve().parent.parent
    18	
    19	SUB_DIR = PROJECT / "data/fingerprints_sub_exp"
    20	
    21	
    22	# ============================================================
    23	# HYBRID V12 — FROZEN CONTROL LOGIC
    24	# ============================================================
    25	
    26	MARGIN_LIMIT = 0.02
    27	
    28	GLOBAL_WEIGHT = 10.0
    29	SUB_WEIGHT = 2.5
    30	NEIGHBOR_WEIGHT = 6.0
    31	
    32	
    33	def normalize(x):
    34	    x = np.asarray(x, dtype=np.float32)
    35	
    36	    n = np.linalg.norm(x)
    37	
    38	    if n > 0:
    39	        x = x / n
    40	
    41	    return x
    42	
    43	
    44	def load_subs():
    45	    result = {}
    46	
    47	    if not SUB_DIR.exists():
    48	        print(f"[Hybrid] WARNING: sub directory not found: {SUB_DIR}")
    49	        return result
    50	
    51	    for d in sorted(SUB_DIR.iterdir()):
    52	
    53	        if not d.is_dir():
    54	            continue
    55	
    56	        f = d / "embeddings.npy"
    57	
    58	        if not f.exists():
    59	            continue
    60	
    61	        emb = np.load(f)
    62	
    63	        emb = np.array(
    64	            [
    65	                normalize(x)
    66	                for x in emb
    67	            ],
    68	            dtype=np.float32,
    69	        )
    70	
    71	        result[d.name] = emb
    72	
    73	    return result
    74	
    75	
    76	def get_neighbor_votes(rows, index):
    77	    votes = Counter()
    78	
    79	    if index <= 0:
    80	        return votes
    81	
    82	    if index >= len(rows) - 1:
    83	        return votes
    84	
    85	    left = rows[index - 1]["top1"]
    86	    right = rows[index + 1]["top1"]
    87	
    88	    # FROZEN V12 RULE:
    89	    # only complete agreement
    90	    if left == right:
    91	        votes[left] = 1
    92	
    93	    return votes
    94	
    95	
    96	def run_recognition(input_dir, fingerprints):
    97	    """
    98	    Run the existing DINO v33 recognizer.
    99	
   100	    The recognizer itself is NOT modified.
   101	    """
   102	
   103	    fp_arg = ",".join(fingerprints)
   104	
   105	    cmd = [
   106	        "uv",
   107	        "run",
   108	        "scene-fingerprint",
   109	        "recognize",
   110	        str(input_dir),
   111	        "--top-k",
   112	        "5",
   113	        "--threshold",
   114	        "0.0",
   115	        "--fingerprints",
   116	        fp_arg,
   117	        "--json",
   118	    ]
   119	
   120	    print("=" * 80)
   121	    print("DINO v33 RECOGNITION")
   122	    print("=" * 80)
   123	    print("Input:", input_dir)
   124	    print("Fingerprints:", ", ".join(fingerprints))
   125	    print()
   126	
   127	    start = time.perf_counter()
   128	
   129	    process = subprocess.run(
   130	        cmd,
   131	        cwd=PROJECT,
   132	        capture_output=True,
   133	        text=True,
   134	    )
   135	
   136	    elapsed = time.perf_counter() - start
   137	
   138	    if process.returncode != 0:
   139	        print(process.stdout)
   140	        print(process.stderr)
   141	
   142	        raise RuntimeError(
   143	            f"recognize завершился с кодом {process.returncode}"
   144	        )
   145	
   146	    combined = process.stdout + "\n" + process.stderr
   147	
   148	    decoder = json.JSONDecoder()
   149	    data = None
   150	
   151	    for i, ch in enumerate(combined):
   152	
   153	        if ch != "[":
   154	            continue
   155	
   156	        try:
   157	            candidate, _ = decoder.raw_decode(
   158	                combined[i:]
   159	            )
   160	
   161	            if isinstance(candidate, list):
   162	                data = candidate
   163	                break
   164	
   165	        except json.JSONDecodeError:
   166	            pass
   167	
   168	    if data is None:
   169	        raise RuntimeError(
   170	            "Не удалось найти JSON-массив в выводе recognition"
   171	        )
   172	
   173	    print("Images:", len(data))
   174	    print(f"Recognition time: {elapsed:.2f} sec")
   175	
   176	    return data, elapsed
   177	
   178	
   179	def adapt_recognizer_rows(rows):
   180	    """
   181	    Convert current recognizer output into the legacy
   182	    top1..top5 format required by frozen Hybrid v12.
   183	    """
   184	
   185	    adapted = []
   186	
   187	    for row in rows:
   188	        item = dict(row)
   189	
   190	        candidates = row.get("candidates", [])
   191	
   192	        for n in range(1, 6):
   193	            item[f"top{n}"] = None
   194	            item[f"top{n}_score"] = 0.0
   195	
   196	        for n, candidate in enumerate(candidates[:5], start=1):
   197	            item[f"top{n}"] = candidate.get("id")
   198	            item[f"top{n}_score"] = float(
   199	                candidate.get("score", 0.0)
   200	            )
   201	
   202	        adapted.append(item)
   203	
   204	    return adapted
   205	
   206	
   207	def hybrid_v12(rows, embedder, subs):
   208	    """
   209	    Exact production adaptation of the frozen Hybrid v12 logic.
   210	
   211	    Input:
   212	        recognizer rows containing top1..top5.
   213	
   214	    Output:
   215	        rows with final best_id.
   216	    """
   217	
   218	    changed = []
   219	    results = []
   220	    sub_count = 0
   221	
   222	    for i, row in enumerate(rows):
   223	
   224	        old = row.get("top1")
   225	
   226	        scores = defaultdict(float)
   227	
   228	        # ====================================================
   229	        # GLOBAL TOP-5
   230	        # ====================================================
   231	
   232	        for k in range(1, 6):
   233	
   234	            fp = row.get(f"top{k}")
   235	            sc = row.get(f"top{k}_score")
   236	
   237	            if fp:
   238	                scores[fp] += (
   239	                    float(sc)
   240	                    * GLOBAL_WEIGHT
   241	                )
   242	
   243	        # ====================================================
   244	        # SUB ONLY BORDER CASES
   245	        # ====================================================
   246	
   247	        margin = row.get(
   248	            "margin",
   249	            1,
   250	        )
   251	
   252	        if margin < MARGIN_LIMIT:
   253	
   254	            sub_count += 1
   255	
   256	            image = Path(
   257	                row["file"]
   258	            )
   259	
   260	            query = embedder.embed_paths(
   261	                [image]
   262	            )[0]
   263	
   264	            query = normalize(query)
   265	
   266	            # FROZEN V12:
   267	            # only TOP1 and TOP2
   268	            candidates = [
   269	                row.get("top1"),
   270	                row.get("top2"),
   271	            ]
   272	
   273	            for parent in candidates:
   274	
   275	                if not parent:
   276	                    continue
   277	
   278	                for sub_id, sub_emb in subs.items():
   279	
   280	                    if not sub_id.startswith(parent):
   281	                        continue
   282	
   283	                    sim = max(
   284	                        sub_emb @ query
   285	                    )
   286	
   287	                    if sim > 0.88:
   288	
   289	                        if sim > 0.92:
   290	                            bonus = 2.5
   291	                        else:
   292	                            bonus = 1.0
   293	
   294	                        scores[parent] += (
   295	                            float(sim)
   296	                            * bonus
   297	                        )
   298	
   299	        # ====================================================
   300	        # SEQUENCE CONSENSUS
   301	        # ====================================================
   302	
   303	        neighbors = get_neighbor_votes(
   304	            rows,
   305	            i,
   306	        )
   307	
   308	        left_fp = None
   309	        right_fp = None
   310	
   311	        if i > 0:
   312	            left_fp = rows[i - 1].get("top1")
   313	
   314	        if i < len(rows) - 1:
   315	            right_fp = rows[i + 1].get("top1")
   316	
   317	        if (
   318	            left_fp
   319	            and right_fp
   320	            and left_fp == right_fp
   321	        ):
   322	            # FROZEN V12:
   323	            # actual implementation uses +3.0
   324	            scores[left_fp] += 3.0
   325	
   326	        # ====================================================
   327	        # FINAL DECISION V12
   328	        # ====================================================
   329	
   330	        best = old
   331	
   332	        ranked = sorted(
   333	            scores.items(),
   334	            key=lambda x: x[1],
   335	            reverse=True,
   336	        )
   337	
   338	        if ranked:
   339	
   340	            candidate = ranked[0][0]
   341	
   342	            gain = (
   343	                scores[candidate]
   344	                - scores.get(old, 0)
   345	            )
   346	
   347	            if (
   348	                candidate != old
   349	                and gain > 1.5
   350	            ):
   351	                best = candidate
   352	
   353	        old_score = scores.get(
   354	            old,
   355	            0,
   356	        )
   357	
   358	        new_score = scores.get(
   359	            best,
   360	            0,
   361	        )
   362	
   363	        hybrid_changed = best != old
   364	
   365	        result = dict(row)
   366	
   367	        result["original_best_id"] = old
   368	        result["best_id"] = best
   369	
   370	        result["hybrid_changed"] = hybrid_changed
   371	
   372	        result["hybrid_old_score"] = old_score
   373	        result["hybrid_score"] = new_score
   374	
   375	        result["hybrid_margin"] = margin
   376	        result["hybrid_neighbors"] = dict(neighbors)
   377	
   378	        results.append(result)
   379	
   380	        if (
   381	            best != old
   382	            and new_score > old_score
   383	        ):
   384	            changed.append(
   385	                {
   386	                    "file": Path(
   387	                        row["file"]
   388	                    ).name,
   389	                    "old": old,
   390	                    "new": best,
   391	                    "margin": margin,
   392	                    "neighbors": dict(neighbors),
   393	                    "old_score": scores[old],
   394	                    "new_score": scores[best],
   395	                }
   396	            )
   397	
   398	    return results, changed, sub_count
   399	
   400	
   401	def sort_results(rows, output_dir):
   402	    """
   403	    Copy photos according to FINAL Hybrid best_id.
   404	    """
   405	
   406	    print()
   407	    print("=" * 80)
   408	    print("SORTING")
   409	    print("=" * 80)
   410	
   411	    output_dir.mkdir(
   412	        parents=True,
   413	        exist_ok=True,
   414	    )
   415	
   416	    counters = Counter()
   417	    sorted_rows = []
   418	
   419	    for item in rows:
   420	
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:42:28

Вот, теперь картина стала полной. И главное — **мы нашли именно тот механизм, который ты хотел изучить**.

### Что реально происходит сейчас

У тебя уже есть готовая связка:

```text
                 DINO v33
                    │
                    ▼
             TOP-5 кандидатов
                    │
                    ▼
          adapt_recognizer_rows()
                    │
          ┌─────────┴─────────┐
          │                   │
       TOP-1..5          их scores
          │                   │
          └─────────┬─────────┘
                    ▼
               Hybrid v12
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
   GLOBAL TOP-5   SUB check    NEIGHBORS
    ×10           border       +3
                    │
                    ▼
               final best_id
```

И здесь есть очень важный момент.

## 1. DINO уже выдаёт именно 5 кандидатов

`SceneRecognizer` получает `top_k=5`:

```python
recognize_folder(
    ...
    top_k=5,
)
```

А `run_hybrid_v12.py` **не делает второго распознавания**.

Он просто забирает уже готовые:

```python
candidates = row.get("candidates", [])
```

и раскладывает:

```text
top1
top2
top3
top4
top5
```

То есть это именно тот вариант, который мы искали.

---

## 2. Hybrid не заменяет DINO

Это принципиально.

Вот:

```python
old = row.get("top1")
```

`old` — это первоначальный DINO TOP-1.

А дальше Hybrid строит дополнительные голоса:

```python
scores[fp] += score * 10.0
```

для **всех пяти кандидатов**.

То есть:

```text
TOP1 → score × 10
TOP2 → score × 10
TOP3 → score × 10
TOP4 → score × 10
TOP5 → score × 10
```

Это базовая масса Hybrid.

---

# 3. Потом есть специальная проверка SUB

Она запускается **только если DINO margin < 0.02**:

```python
if margin < MARGIN_LIMIT:
```

А `MARGIN_LIMIT`:

```python
MARGIN_LIMIT = 0.02
```

И вот тут очень важно:

### SUB проверяет только TOP-1 и TOP-2

Не все пять.

```python
candidates = [
    row.get("top1"),
    row.get("top2"),
]
```

Дальше ищутся subfingerprints соответствующих адресов.

И получается дополнительный бонус:

```text
sim > 0.88 → + sim × 1.0
sim > 0.92 → + sim × 2.5
```

То есть SUB — это **не новый основной recognizer**, а дополнительный механизм разрешения пограничных случаев.

---

# 4. И самое интересное — соседи

У тебя действительно есть та функция, про которую ты раньше говорил:

```python
get_neighbor_votes(rows, index)
```

Она смотрит:

```text
предыдущее фото → TOP1
следующее фото → TOP1
```

И если:

```text
LEFT == RIGHT
```

то появляется голос за этот fingerprint.

А фактический Hybrid добавляет:

```python
scores[left_fp] += 3.0
```

То есть:

```text
сосед слева = 94_v33
сосед справа = 94_v33

→ 94_v33 получает +3
```

Это **последовательностный консенсус**.

Именно поэтому Hybrid использует не только само изображение, но и контекст соседних фотографий.

---

# 5. Финальное решение очень конкретное

После всех добавок:

```python
ranked = sorted(
    scores.items(),
    key=lambda x: x[1],
    reverse=True,
)
```

Берётся кандидат с максимальным Hybrid score.

Но есть защита:

```python
if (
    candidate != old
    and gain > 1.5
):
    best = candidate
```

То есть Hybrid **не имеет права легко перекинуть фотографию**.

Чтобы изменить DINO TOP-1:

```text
Hybrid candidate score
       -
DINO TOP-1 Hybrid score

> 1.5
```

Только тогда:

```text
best_id = candidate
```

Иначе остаётся:

```text
best_id = DINO TOP-1
```

---

# 6. Поэтому твоя текущая БД на самом деле хранит только первую половину процесса

Сейчас в PostgreSQL:

```text
dino_fingerprint
dino_score
dino_second_score
dino_margin
```

Это фактически:

```text
TOP-1
TOP-1 score
TOP-2 score
margin
```

Но **TOP-3 / TOP-4 / TOP-5 потеряны**.

А Hybrid требует:

```text
top1
top2
top3
top4
top5
```

Поэтому наши предыдущие `hybrid_*` поля пустые не потому, что Hybrid сломан.

Они пустые потому, что **текущий DINO worker вообще не запускает Hybrid**.

Он заканчивает работу здесь:

```python
address_id = result.get("best_id")
```

и записывает:

```python
address_id
dino_fingerprint
dino_score
dino_second_score
dino_margin
```

Hybrid после этого не вызывается.

---

# 7. И вот здесь обнаруживается очень важная архитектура

Сейчас существуют **два разных pipeline**.

### Старый production daily

```text
photo
 ↓
DINO recognize
 ↓
TOP-5
 ↓
Hybrid v12
 ↓
final best_id
 ↓
копирование
```

Это:

```text
scripts/run_daily_hybrid_v12.sh
        ↓
scripts/run_hybrid_v12.py
```

### Новый web/DB pipeline

```text
photo
 ↓
DINO worker
 ↓
TOP-1
 ↓
PostgreSQL
```

Это:

```text
app/workers/dino_worker.py
```

И **второй pipeline сейчас обрывается до Hybrid**.

---

## 8. Поэтому я бы пока вообще ничего не патчил

Сначала нужно зафиксировать старую рабочую механику.

Следующий очень полезный шаг — посмотреть **оставшуюся часть `recognizer.py`**, начиная примерно со строки 350.

Нам особенно нужны:

```python
candidates
best_id
second_score
margin
```

и как именно `top_k` применяется.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba app/core/recognizer.py | sed -n '350,560p'
```

После этого мы сможем точно восстановить полный контракт:

```text
SceneRecognizer output
        ↓
candidates[0..4]
        ↓
Hybrid v12
        ↓
final best_id
```

И уже затем решим, **как перенести именно этот механизм в текущий DB pipeline**, сохранив его без изменения логики.

---

