## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-21 00:37:56

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ CREATE PREVIEWS ================" && \
nl -ba scripts/create_previews_v01.py | sed -n '1,180p' && \
echo "================ PHOTO INGEST PREVIEW ================" && \
nl -ba scripts/photo_ingest.py | sed -n '210,285p' && \
echo "================ MAIN PREVIEW ================" && \
nl -ba app/web/main.py | sed -n '210,245p' && \
echo "================ PHOTO GRID PREVIEW ================" && \
nl -ba app/web/components/photos.py | sed -n '1570,1620p'
================ CREATE PREVIEWS ================
     1	#!/usr/bin/env python3
     2	
     3	import argparse
     4	from pathlib import Path
     5	from PIL import Image
     6	
     7	
     8	IMAGE_EXTENSIONS = {
     9	    ".jpg",
    10	    ".jpeg",
    11	    ".png",
    12	    ".webp",
    13	}
    14	
    15	MAX_SIZE = 1200
    16	QUALITY = 82
    17	
    18	
    19	def create_preview(source: Path, destination: Path):
    20	    destination.parent.mkdir(
    21	        parents=True,
    22	        exist_ok=True,
    23	    )
    24	
    25	    if destination.exists():
    26	        return "skip"
    27	
    28	    with Image.open(source) as image:
    29	        image = image.convert("RGB")
    30	        image.thumbnail(
    31	            (MAX_SIZE, MAX_SIZE),
    32	            Image.Resampling.LANCZOS,
    33	        )
    34	
    35	        image.save(
    36	            destination,
    37	            "JPEG",
    38	            quality=QUALITY,
    39	            optimize=True,
    40	        )
    41	
    42	    return "created"
    43	
    44	
    45	def main():
    46	
    47	    parser = argparse.ArgumentParser(
    48	        description="Create web previews for processed photos"
    49	    )
    50	
    51	    parser.add_argument(
    52	        "--input",
    53	        required=True,
    54	        help="Hybrid output directory",
    55	    )
    56	
    57	    parser.add_argument(
    58	        "--output",
    59	        required=True,
    60	        help="Preview output directory",
    61	    )
    62	
    63	    args = parser.parse_args()
    64	
    65	    input_dir = Path(args.input).expanduser().resolve()
    66	    output_dir = Path(args.output).expanduser().resolve()
    67	
    68	    if not input_dir.exists():
    69	        raise SystemExit(
    70	            f"ERROR: input directory does not exist: {input_dir}"
    71	        )
    72	
    73	    files = sorted(
    74	        [
    75	            p
    76	            for p in input_dir.rglob("*")
    77	            if p.is_file()
    78	            and p.suffix.lower() in IMAGE_EXTENSIONS
    79	        ],
    80	        key=lambda p: str(p).lower(),
    81	    )
    82	
    83	    print("=" * 80)
    84	    print("PHOTO PREVIEW WORKER V01")
    85	    print("=" * 80)
    86	    print("INPUT :", input_dir)
    87	    print("OUTPUT:", output_dir)
    88	    print("FILES :", len(files))
    89	    print("MAX   :", MAX_SIZE)
    90	    print("QUALITY:", QUALITY)
    91	    print()
    92	
    93	    created = 0
    94	    skipped = 0
    95	    errors = 0
    96	
    97	    for index, source in enumerate(files, 1):
    98	
    99	        relative = source.relative_to(input_dir)
   100	
   101	        destination = (
   102	            output_dir
   103	            / relative.parent
   104	            / f"{source.stem}.jpg"
   105	        )
   106	
   107	        try:
   108	
   109	            result = create_preview(
   110	                source,
   111	                destination,
   112	            )
   113	
   114	            if result == "created":
   115	                created += 1
   116	            else:
   117	                skipped += 1
   118	
   119	            if index % 25 == 0 or index == len(files):
   120	                print(
   121	                    f"[{index}/{len(files)}] "
   122	                    f"created={created} "
   123	                    f"skipped={skipped} "
   124	                    f"errors={errors}",
   125	                    flush=True,
   126	                )
   127	
   128	        except Exception as error:
   129	
   130	            errors += 1
   131	
   132	            print(
   133	                f"ERROR: {source}: {error}",
   134	                flush=True,
   135	            )
   136	
   137	    print()
   138	    print("=" * 80)
   139	    print("PREVIEW FINISHED")
   140	    print("=" * 80)
   141	    print("Created:", created)
   142	    print("Skipped:", skipped)
   143	    print("Errors :", errors)
   144	    print("Output :", output_dir)
   145	    print()
   146	
   147	
   148	if __name__ == "__main__":
   149	    main()
================ PHOTO INGEST PREVIEW ================
   210	    initial_id,
   211	    source_path,
   212	):
   213	    """
   214	    Создаёт единую первичную запись фотографии.
   215	
   216	    На этом этапе НЕ происходит:
   217	
   218	        - DINO
   219	        - Qwen
   220	        - сортировка
   221	        - определение адреса
   222	        - создание превью
   223	
   224	    Здесь только создаётся объект PHOTО.
   225	    """
   226	
   227	    source = Path(source_path)
   228	
   229	    filename = source.name
   230	
   231	    with conn.cursor() as cur:
   232	
   233	        cur.execute(
   234	            """
   235	            INSERT INTO photos (
   236	                photo_id,
   237	                initial_id,
   238	
   239	                source_path,
   240	                path,
   241	
   242	                filename,
   243	                original_filename,
   244	
   245	                status,
   246	
   247	                dino_status,
   248	                qwen_status,
   249	                sort_status,
   250	                preview_status
   251	            )
   252	            VALUES (
   253	                %s,
   254	                %s,
   255	
   256	                %s,
   257	                %s,
   258	
   259	                %s,
   260	                %s,
   261	
   262	                'pending',
   263	
   264	                'pending',
   265	                'pending',
   266	                'pending',
   267	                'pending'
   268	            )
   269	            """,
   270	            (
   271	                photo_id,
   272	                initial_id,
   273	
   274	                source_path,
   275	                source_path,
   276	
   277	                filename,
   278	                filename,
   279	            ),
   280	        )
   281	
   282	
   283	# ============================================================
   284	# INGEST
   285	# ============================================================
================ MAIN PREVIEW ================
   210	                and record_address.casefold()
   211	                != address_filter
   212	            ):
   213	                continue
   214	
   215	            result.append(
   216	                {
   217	                    "id": record.get("id"),
   218	                    "photo_id": record.get("photo_id"),
   219	                    "address": record_address,
   220	                    "filename": (
   221	                        record.get("filename")
   222	                        or record.get("original_filename")
   223	                        or ""
   224	                    ),
   225	                    "client": record_client,
   226	                    "brand": (
   227	                        record.get("brand")
   228	                        or ""
   229	                    ),
   230	                    "preview_path": (
   231	                        record.get("preview_path")
   232	                        or ""
   233	                    ),
   234	                    "path": (
   235	                        record.get("path")
   236	                        or ""
   237	                    ),
   238	                }
   239	            )
   240	
   241	        return result
   242	
   243	    except Exception as exc:
   244	        print(
   245	            "[V2 PHOTOS ERROR]",
================ PHOTO GRID PREVIEW ================
  1570	                                "hover:shadow-lg"
  1571	                            ):
  1572	
  1573	                                # ----------------------------
  1574	                                # IMAGE
  1575	                                # ----------------------------
  1576	
  1577	                                with ui.element(
  1578	                                    "div"
  1579	                                ).classes(
  1580	                                    "relative "
  1581	                                    "w-full h-44 "
  1582	                                    "bg-grey-2 "
  1583	                                    "flex items-center "
  1584	                                    "justify-center"
  1585	                                ).on(
  1586	                                    "contextmenu.prevent",
  1587	                                    lambda e, p=photo:
  1588	                                        photo_menu(p),
  1589	                                ):
  1590	
  1591	                                    # В ГРИДЕ показываем PREVIEW.
  1592	                                    # Оригинал открывается только
  1593	                                    # после клика.
  1594	                                    preview_path = (
  1595	                                        get_preview_path(
  1596	                                            photo.path
  1597	                                        )
  1598	                                    )
  1599	
  1600	                                    display_path = (
  1601	                                        preview_path
  1602	                                        if preview_path
  1603	                                        else photo.path
  1604	                                    )
  1605	
  1606	                                    ui.image(
  1607	                                        str(display_path)
  1608	                                    ).classes(
  1609	                                        "w-full h-full "
  1610	                                        "object-contain"
  1611	                                    ).on(
  1612	                                        "click",
  1613	                                        lambda e, p=photo:
  1614	                                            open_photo(p),
  1615	                                    )
  1616	
  1617	                                    # ----------------------------
  1618	                                    # AI / QWEN STATUS
  1619	                                    # ----------------------------
  1620	
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 

Create preview должен создавать маленькие превью средние для просмотра - в разные папки с одним phot id

---

### 🤖 **Assistant** — 2026-08-21 00:37:59

Да. Тогда делаем **нормальную систему превью после Hybrid**, а не один универсальный файл.

Я бы зафиксировал структуру именно так:

```text
data/preview/
├── small/
│   ├── 1.jpg
│   ├── 2.jpg
│   ├── 3.jpg
│   └── ...
│
└── medium/
    ├── 1.jpg
    ├── 2.jpg
    ├── 3.jpg
    └── ...
```

То есть один и тот же `photos.id`:

```text
photos.id = 527

data/preview/small/527.jpg
data/preview/medium/527.jpg
```

### Размеры

Предлагаю:

- **small** — для плотного грида: `400 × 400` максимум;
- **medium** — для просмотра выбранной фотографии: `1200 × 1200` максимум.

При этом сохраняем пропорции, как сейчас делает PIL через `thumbnail()`.

Например исходник:

```text
6000 × 4000
```

получит:

```text
small  → 400 × 267
medium → 1200 × 800
```

### Главное изменение

Текущий `create_previews_v01.py` сейчас делает:

```text
input/
   85_v33/
      Ашхабадский_01.JPG
          ↓
preview/
   85_v33/
      Ашхабадский_01.jpg
```

Это больше не нужно.

Новый worker должен работать примерно так:

```text
Hybrid output
      ↓
находим запись PostgreSQL
      ↓
photos.id
      ↓
┌───────────────────────┐
│                       │
▼                       ▼
small/<id>.jpg       medium/<id>.jpg
```

И в БД можно хранить:

```text
preview_small_path
preview_medium_path
```

Это **лучше, чем пытаться запихнуть два пути в один `preview_path`**.

Сейчас у нас уже есть:

```text
preview_path
preview_status
```

Поэтому надо сначала посмотреть структуру таблицы `photos`, чтобы не придумывать новые поля поверх существующей схемы.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="photobase",
    user="lora",
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'photos'
        ORDER BY ordinal_position
    """)

    for row in cur.fetchall():
        print(row)

conn.close()
PY
```

И отдельно найдем **как именно сейчас запускается создание превью после Hybrid**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'create_previews_v01|preview_status|PREVIEW FINISHED|PHOTO PREVIEW WORKER' \
scripts app \
--include="*.py" \
--include="*.sh"
```

После этого переделаем worker так, чтобы он:

1. запускался **после Hybrid**;
2. получал готовые фотографии;
3. определял их `photos.id`;
4. создавал **small + medium**;
5. складывал их в единую структуру;
6. записывал оба пути в PostgreSQL;
7. выставлял `preview_status = done`;
8. V2 использовал `small` для грида;
9. `medium` — для окна просмотра.

И старую систему `latest_preview_root()` / `get_preview_path(photo_path)` тогда вообще уберём из V2 — она больше не нужна.

---

### 👤 **User** — 2026-08-21 00:38:32

)

with conn.cursor() as cur:
    cur.execute("""
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'photos'
        ORDER BY ordinal_position
    """)

PYnn.close()t(row).fetchall():
('id', 'bigint', 'NO')
('photo_id', 'text', 'NO')
('source_path', 'text', 'NO')
('path', 'text', 'NO')
('filename', 'text', 'NO')
('original_filename', 'text', 'YES')
('address', 'text', 'YES')
('client', 'text', 'YES')
('brand', 'text', 'YES')
('category', 'text', 'YES')
('description', 'text', 'YES')
('status', 'text', 'NO')
('dino_status', 'text', 'NO')
('qwen_status', 'text', 'NO')
('sort_status', 'text', 'NO')
('preview_status', 'text', 'NO')
('error_message', 'text', 'YES')
('dino_fingerprint', 'text', 'YES')
('dino_score', 'double precision', 'YES')
('dino_second_score', 'double precision', 'YES')
('dino_margin', 'double precision', 'YES')
('dino_time_sec', 'double precision', 'YES')
('hybrid_original_id', 'text', 'YES')
('hybrid_final_id', 'text', 'YES')
('hybrid_changed', 'boolean', 'YES')
('hybrid_old_score', 'double precision', 'YES')
('hybrid_score', 'double precision', 'YES')
('hybrid_margin', 'double precision', 'YES')
('hybrid_neighbors', 'jsonb', 'YES')
('confidence', 'integer', 'YES')
('qwen_time_sec', 'double precision', 'YES')
('text_json', 'jsonb', 'YES')
('colors_json', 'jsonb', 'YES')
('objects_json', 'jsonb', 'YES')
('environment_json', 'jsonb', 'YES')
('image_quality_json', 'jsonb', 'YES')
('camera_view_json', 'jsonb', 'YES')
('scene_objects_json', 'jsonb', 'YES')
('analysis_quality_json', 'jsonb', 'YES')
('raw_json', 'jsonb', 'YES')
('preview_path', 'text', 'YES')
('created_at', 'timestamp without time zone', 'NO')
('updated_at', 'timestamp without time zone', 'NO')
('source_id', 'text', 'YES')
('address_id', 'text', 'YES')
('initial_id', 'text', 'YES')
('dino_started_at', 'timestamp without time zone', 'YES')
('qwen_started_at', 'timestamp without time zone', 'YES')
('legal_address', 'text', 'YES')
('simple_address', 'text', 'YES')
('client_normalized', 'text', 'YES')
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 00:38:35

Отлично. Теперь схема понятна.

**Новые поля в БД пока добавлять не обязательно.** У нас уже есть:

- `id` — стабильный внутренний ID фотографии;
- `photo_id` — внешний/логический ID;
- `preview_path` — можем использовать как путь к **medium**;
- `preview_status` — состояние генерации;
- `path` — текущий путь оригинала.

Я бы сделал так:

```text id="rbx5dy"
data/preview/
├── small/
│   ├── 1.jpg
│   ├── 2.jpg
│   └── 527.jpg
│
└── medium/
    ├── 1.jpg
    ├── 2.jpg
    └── 527.jpg
```

А в БД:

```text id="a9p1jy"
preview_path = data/preview/medium/527.jpg
```

А путь `small` **вообще не обязательно хранить** — он детерминированно получается из `id`:

```text id="e6a7u0"
medium → data/preview/medium/527.jpg
small  → data/preview/small/527.jpg
```

Так БД остаётся чистой.

### Но есть ещё более важный момент

Ты сказал:

> Create preview должен создавать маленькие превью средние для просмотра — в разные папки с одним photo id

Значит worker должен работать **не от структуры каталогов**, а от PostgreSQL:

```text
Hybrid finished
       ↓
photos
       ↓
id=527, path=/.../85_v33/xxx.jpg
       ↓
small/527.jpg
medium/527.jpg
       ↓
preview_path = medium/527.jpg
preview_status = done
```

Если Hybrid потом переместит файл:

```text
85_v33/xxx.jpg
```

в:

```text
92_v33/xxx.jpg
```

превью останутся:

```text
small/527.jpg
medium/527.jpg
```

То есть **связь не ломается**.

---

Теперь нужен второй вывод — ты его ещё не прислал. Мы искали, **где именно `create_previews_v01.py` вызывается после Hybrid**.

Выполни:

```bash id="xw6t8v"
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'create_previews_v01|preview_status|PREVIEW FINISHED|PHOTO PREVIEW WORKER' \
scripts app \
--include="*.py" \
--include="*.sh"
```

Это нужно перед изменением worker, потому что я хочу встроить новую генерацию **в существующий post-Hybrid этап**, а не создавать второй независимый запуск.

После этого уже можно будет сделать первый безопасный патч:

**Hybrid → Preview small/medium → PostgreSQL → V2.**

Старые `data/preview/daily/...` пока **не трогаем и не удаляем**.

---

### 👤 **User** — 2026-08-21 00:39:38

после гибрида фото не сортируются в реальности. только виртуальная сортировка

---

### 🤖 **Assistant** — 2026-08-21 00:39:39

Да, тогда это существенно меняет логику.

У нас **Hybrid не перемещает физические файлы**. Он только записывает результат виртуальной сортировки в PostgreSQL:

```text
id="x4m9u2"
оригинал:
data/input/daily/Ашхабадский_01.JPG

        ↓ DINO
85_v33

        ↓ Hybrid
hybrid_final_id = 85_v33

        ↓
БД знает:
photo.id
hybrid_final_id
...
```

Поэтому **preview вообще нельзя строить относительно `data/output/daily/...`**.

### Правильная архитектура

Единая папка:

```text id="z9k3q1"
data/preview/
├── small/
│   ├── 1.jpg
│   ├── 2.jpg
│   ├── 3.jpg
│   └── ...
│
└── medium/
    ├── 1.jpg
    ├── 2.jpg
    ├── 3.jpg
    └── ...
```

Источник берём **из PostgreSQL `photos.path`**:

```text id="n2v7ca"
photos.id = 527
photos.path =
/home/.../data/input/daily/Ашхабадский_01.JPG

              ↓

data/preview/small/527.jpg
data/preview/medium/527.jpg
```

А `hybrid_final_id` вообще **не участвует в поиске preview**.

---

### И это решает сразу несколько проблем

**1. Имена файлов могут измениться**

Неважно:

```text
Ашхабадский_01.JPG
```

стал:

```text
photo_0001.jpg
```

Preview всё равно:

```text
small/527.jpg
medium/527.jpg
```

**2. Виртуальный адрес может измениться**

Например:

```text
hybrid_final_id = 85_v33
```

потом станет:

```text
hybrid_final_id = 91_v33
```

Preview не меняется.

**3. Клиент может измениться**

Preview не зависит от клиента.

**4. Адрес может измениться**

Preview не зависит от адреса.

**5. Главное — стабильная связь через `photos.id`.**

---

### А V2 тогда вообще становится очень простой

Для каждой записи:

```text
photo.id
```

получаем:

```text
data/preview/small/{id}.jpg
```

и показываем его в grid.

При открытии фотографии:

```text
data/preview/medium/{id}.jpg
```

А если medium отсутствует — можно показать оригинал из `photos.path`.

---

### И ещё важный момент по твоим адресам

Ты написал:

> адреса должны брать из базы fingerprint id

Здесь тоже надо разделить две вещи.

В базе сейчас есть:

```text
dino_fingerprint
hybrid_original_id
hybrid_final_id
address
address_id
legal_address
simple_address
```

Для **виртуальной сортировки** правильнее считать:

```text
hybrid_final_id
```

результатом сортировки фотографии.

То есть панель **«Адреса»** не должна сканировать физические папки.

Она должна строиться из PostgreSQL:

```text
photos
   ↓
hybrid_final_id
   ↓
группа фотографий
   ↓
адрес / подпись fingerprint
   ↓
checkbox
```

И соответственно:

```text
☐ 78_v33       24
☐ 79_v33       18
☐ 80_v33       31
☐ 81_v33       12
...
```

При выборе `85_v33` фильтр просто выбирает записи:

```text
record["hybrid_final_id"] == "85_v33"
```

или, если именно `dino_fingerprint` является источником группировки, используем его. **Надо определить, какое из двух полей является окончательным результатом Hybrid**, чтобы не смешать исходный DINO и финальную виртуальную сортировку.

Поэтому следующий шаг я бы сделал не кодированием вслепую, а проверкой нескольких записей:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.photo_db import get_photo_records

rows = get_photo_records()

print("TOTAL:", len(rows))
print()

for r in rows[:30]:
    print(
        "id=", r.get("id"),
        "| photo_id=", r.get("photo_id"),
        "| dino=", r.get("dino_fingerprint"),
        "| hybrid_original=", r.get("hybrid_original_id"),
        "| hybrid_final=", r.get("hybrid_final_id"),
        "| address=", r.get("address"),
        "| address_id=", r.get("address_id"),
        "| simple_address=", r.get("simple_address"),
        "| path=", r.get("path"),
    )
PY
```

**После этого уже точно определим источник панели адресов и сделаем V2 без привязки к физическим папкам.**

---

### 👤 **User** — 2026-08-21 00:40:30

превью можно называть для удобства по фото_ид_смалл фото_ид_медиум

---

### 🤖 **Assistant** — 2026-08-21 00:40:31

Да, так даже удобнее для диагностики и обслуживания.

Я бы зафиксировал единую структуру:

```text
data/preview/
├── small/
│   ├── photo_1_small.jpg
│   ├── photo_2_small.jpg
│   ├── photo_3_small.jpg
│   └── ...
│
└── medium/
    ├── photo_1_medium.jpg
    ├── photo_2_medium.jpg
    ├── photo_3_medium.jpg
    └── ...
```

То есть для PostgreSQL:

```text
photos.id = 527
```

получаем:

```text
data/preview/small/photo_527_small.jpg
data/preview/medium/photo_527_medium.jpg
```

### Размеры

Я бы сделал:

- **small** — примерно `300 px` по длинной стороне, для сетки V2;
- **medium** — примерно `1200 px` по длинной стороне, для просмотра фотографии.

При этом оба файла JPEG, например quality `82`.

### В БД

`preview_path` можно хранить как путь к medium:

```text
data/preview/medium/photo_527_medium.jpg
```

Но сам `small` всегда однозначно вычисляется:

```text
data/preview/small/photo_527_small.jpg
```

То есть нам не нужно добавлять `small_preview_path`.

### Главное

Worker после Hybrid должен брать:

```text
photos.id
photos.path
```

и создавать:

```text
photos.id → small + medium
```

**Не `filename`, не `address`, не `dino_fingerprint`, не `hybrid_final_id`.**

Это полностью соответствует виртуальной сортировке: физический оригинал остаётся там, где он есть, а preview имеет стабильное имя, привязанное к записи фотографии в БД.

И старую схему:

```text
data/preview/daily/20260816_230042/95_v33/...
```

тогда постепенно можно вывести из использования.

---

### 👤 **User** — 2026-08-21 00:41:00

да

---

### 🤖 **Assistant** — 2026-08-21 00:41:03

Тогда фиксируем архитектуру и переходим к реализации.

**Целевая схема:**

```text
PostgreSQL photos
        │
        │ id + path
        ▼
   create previews
        │
        ├── data/preview/small/photo_<id>_small.jpg
        │
        └── data/preview/medium/photo_<id>_medium.jpg
```

- `small` — для грида V2.
- `medium` — для просмотра.
- `preview_path` → путь к `medium`.
- Связь только через `photos.id`.
- Физическая сортировка файлов не используется.
- `hybrid_final_id` используется только как **виртуальная группировка/фильтр**, не для поиска preview.

Перед патчем нужно посмотреть, **где именно сейчас после Hybrid вызывается preview worker**, чтобы встроить это в существующий pipeline, а не сломать порядок обработки.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'create_previews_v01|preview_status|PREVIEW FINISHED|PHOTO PREVIEW WORKER' \
scripts app \
--include="*.py" \
--include="*.sh"
```

И пришли вывод. Дальше дам точный патч.

---

### 👤 **User** — 2026-08-21 00:41:20

int_mvp_v02 && \
grep -RniE \
'create_previews_v01|preview_status|PREVIEW FINISHED|PHOTO PREVIEW WORKER' \
scripts app \
--include="*.py" \
--include="*.sh"
scripts/create_previews_v01.py:84:    print("PHOTO PREVIEW WORKER V01")
scripts/create_previews_v01.py:139:    print("PREVIEW FINISHED")
scripts/photo_ingest.py:250:                preview_status
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 00:41:22

Отлично. Это важный результат: **сейчас preview worker вообще не подключён к основному pipeline**. `create_previews_v01.py` существует отдельно, а `photo_ingest.py` только выставляет `preview_status='pending'`.

Значит, сейчас лучше не делать косметический патч V2, а нормально связать три вещи:

1. **После Hybrid** создаются preview.
2. Preview привязываются к `photos.id`.
3. V2 берёт preview непосредственно по `photos.id`.

И отдельно: **реальная сортировка после Hybrid нам сейчас не нужна** — оставляем виртуальную сортировку по `hybrid_final_id`.

### Что предлагаю сделать

Новый worker условно:

```text
scripts/create_previews_v02.py
```

Он будет:

```text
PostgreSQL
    ↓
SELECT id, path
FROM photos
WHERE hybrid_final_id IS NOT NULL
  AND preview_status != 'done'
    ↓
data/preview/small/photo_<id>_small.jpg
data/preview/medium/photo_<id>_medium.jpg
    ↓
UPDATE photos
SET
    preview_path = 'data/preview/medium/photo_<id>_medium.jpg',
    preview_status = 'done'
```

Размеры:

```text
small  = 300 px
medium = 1200 px
```

При этом исходные фотографии **не перемещаем и не копируем**.

---

### Но сначала нужен один важный кусок

Нужно найти **само место завершения Hybrid**, потому что именно туда мы должны поставить вызов preview worker.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID REFERENCES ================" && \
grep -RniE \
'hybrid_final_id|hybrid_changed|hybrid_neighbors|hybrid_original_id' \
scripts app \
--include="*.py" \
| head -300
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PIPELINE SCRIPTS ================" && \
find scripts -maxdepth 1 -type f -name '*.py' -printf '%f\n' \
| sort
```

По этим двум выводам я определю **точку после Hybrid**, и уже после этого сделаем один согласованный патч: **preview worker + запуск после Hybrid + обновление `preview_path` + V2 grid по `photos.id`**.

---

### 👤 **User** — 2026-08-21 00:41:59

int_mvp_v02 && \
echo "================ HYBRID REFERENCES ================" && \
grep -RniE \
'hybrid_final_id|hybrid_changed|hybrid_neighbors|hybrid_original_id' \
scripts app \
--include="*.py" \
| head -300
================ HYBRID REFERENCES ================
scripts/run_hybrid_v12.py:363:        hybrid_changed = best != old
scripts/run_hybrid_v12.py:370:        result["hybrid_changed"] = hybrid_changed
scripts/run_hybrid_v12.py:376:        result["hybrid_neighbors"] = dict(neighbors)
scripts/run_hybrid_v12.py:460:                "hybrid_changed": item.get(
scripts/run_hybrid_v12.py:461:                    "hybrid_changed"
scripts/run_hybrid_v12.py:705:        "hybrid_changed": len(changed),
scripts/diagnose_dino_hybrid_db.py:34:                    hybrid_original_id,
scripts/diagnose_dino_hybrid_db.py:35:                    hybrid_final_id,
scripts/diagnose_dino_hybrid_db.py:36:                    hybrid_changed,
scripts/diagnose_dino_hybrid_db.py:40:                    hybrid_neighbors
scripts/diagnose_dino_hybrid_db.py:64:            hybrid_changed = 0
scripts/diagnose_dino_hybrid_db.py:81:                    hybrid_changed_value,
scripts/diagnose_dino_hybrid_db.py:85:                    hybrid_neighbors,
scripts/diagnose_dino_hybrid_db.py:98:                if hybrid_changed_value:
scripts/diagnose_dino_hybrid_db.py:99:                    hybrid_changed += 1
scripts/diagnose_dino_hybrid_db.py:110:                print(f"hybrid_original_id  : {hybrid_original}")
scripts/diagnose_dino_hybrid_db.py:111:                print(f"hybrid_final_id     : {hybrid_final}")
scripts/diagnose_dino_hybrid_db.py:112:                print(f"hybrid_changed      : {hybrid_changed_value}")
scripts/diagnose_dino_hybrid_db.py:116:                print(f"hybrid_neighbors    : {json.dumps(hybrid_neighbors, ensure_ascii=False)}")
scripts/diagnose_dino_hybrid_db.py:126:            print("Hybrid changed      :", hybrid_changed)
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/web/photo_db.py:50:            hybrid_changed,
app/web/photo_db.py:54:            hybrid_neighbors,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ scripts/photo_ingest.py:250:                preview_status
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID REFERENCES ================" && \
grep -RniE \
'hybrid_final_id|hybrid_changed|hybrid_neighbors|hybrid_original_id' \
scripts app \
--include="*.py" \
| head -300
================ HYBRID REFERENCES ================
scripts/run_hybrid_v12.py:363:        hybrid_changed = best != old
scripts/run_hybrid_v12.py:370:        result["hybrid_changed"] = hybrid_changed
scripts/run_hybrid_v12.py:376:        result["hybrid_neighbors"] = dict(neighbors)
scripts/run_hybrid_v12.py:460:                "hybrid_changed": item.get(
scripts/run_hybrid_v12.py:461:                    "hybrid_changed"
scripts/run_hybrid_v12.py:705:        "hybrid_changed": len(changed),
scripts/diagnose_dino_hybrid_db.py:34:                    hybrid_original_id,
scripts/diagnose_dino_hybrid_db.py:35:                    hybrid_final_id,
scripts/diagnose_dino_hybrid_db.py:36:                    hybrid_changed,
scripts/diagnose_dino_hybrid_db.py:40:                    hybrid_neighbors
scripts/diagnose_dino_hybrid_db.py:64:            hybrid_changed = 0
scripts/diagnose_dino_hybrid_db.py:81:                    hybrid_changed_value,
scripts/diagnose_dino_hybrid_db.py:85:                    hybrid_neighbors,
scripts/diagnose_dino_hybrid_db.py:98:                if hybrid_changed_value:
scripts/diagnose_dino_hybrid_db.py:99:                    hybrid_changed += 1
scripts/diagnose_dino_hybrid_db.py:110:                print(f"hybrid_original_id  : {hybrid_original}")
scripts/diagnose_dino_hybrid_db.py:111:                print(f"hybrid_final_id     : {hybrid_final}")
scripts/diagnose_dino_hybrid_db.py:112:                print(f"hybrid_changed      : {hybrid_changed_value}")
scripts/diagnose_dino_hybrid_db.py:116:                print(f"hybrid_neighbors    : {json.dumps(hybrid_neighbors, ensure_ascii=False)}")
scripts/diagnose_dino_hybrid_db.py:126:            print("Hybrid changed      :", hybrid_changed)
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/web/photo_db.py:50:            hybrid_changed,
app/web/photo_db.py:54:            hybrid_neighbors,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PIPELINE SCRIPTS ================" && \
find scripts -maxdepth 1 -type f -name '*.py' -printf '%f\n' \
| sort
================ PIPELINE SCRIPTS ================
analyze_sequence_v38.py
analyze_subfingerprints.py
banner_candidates_v01.py
banner_crop_search_v01.py
banner_crop_search_v02.py
banner_database_v01.py
banner_database_v02.py
banner_llm_folder_search_v01.py
banner_llm_full_v01.py
banner_llm_full_v02.py
banner_model_compare_v01.py
banner_model_compare_v02.py
banner_model_compare_v03.py
banner_model_compare_v04.py
banner_model_compare_v05.py
banner_qwen25vl_test_v01.py
banner_qwen4b_test_v01.py
banner_search_v01.py
banner_search_v02.py
banner_search_v03_2.py
banner_search_v03_3.py
banner_search_v03.py
benchmark_client_models_25.py
benchmark_client_normalizer.py
benchmark_hybrid_v01.py
benchmark_hybrid_v02.py
benchmark_hybrid_v03.py
benchmark_hybrid_v04.py
benchmark_hybrid_v05.py
benchmark_hybrid_v06.py
benchmark_hybrid_v07.py
benchmark_hybrid_v08.py
benchmark_hybrid_v09.py
benchmark_hybrid_v10_debug.py
benchmark_hybrid_v11.py
benchmark_hybrid_v12_full.py
benchmark_qwen_vl.py
benchmark_sub_rerank_v01.py
benchmark_sub_rerank_v02.py
benchmark_sub_rerank_v03.py
benchmark_sub_rerank_v04.py
benchmark_test_sub_exp.py
benchmark_test_v1.py
build_margin_best_from_benchmark.py
build_subfingerprint_database.py
build_subfingerprints_exp.py
compare_benchmark_sub.py
create_previews_v01.py
crop_test_banner.py
diagnose_dino_hybrid_db.py
dry_run_best_sequence.py
export_subclusters.py
export_visual_compare.py
import_qwen_to_db.py
llm_resolver_v01.py
make_subcluster_contact.py
make_subfingerprints.py
make_subfingerprints_v2.py
migrate_sqlite_to_postgres.py
photo_ingest.py
qwen4b_output_v01_before_compact_prompt.py
qwen4b_output_v01.py
qwen_prompt_ablation.py
run_hybrid_v12.py
search_banners_v01.py
smart_client_normalizer.py
sort_baseline.py
sort_margin005_best.py
sort_neighbor_v34.py
sort_neighbor_v35_benchmark.py
sort_neighbor_v35.py
sort_neighbor_v36_img.py
sort_neighbor_v36.py
sort_neighbor_v37.py
sort_sequence_sub_v01.py
sort_sequence_v38_1.py
sort_sequence_v38_1_subtest.py
sort_sequence_v38.py
sort_sequence_v39.py
sort_test_and_report_hybrid_v12.py
sort_test_and_report.py
sort_test_and_report_v2.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 00:42:00

Да, теперь картина ясная.

`run_hybrid_v12.py` — нужная точка. Но **не будем пока встраивать preview прямо в Hybrid**. Сначала нужно посмотреть, как он сейчас записывает результат в PostgreSQL и где заканчивается весь запуск. Тогда сделаем preview отдельным этапом **после успешного Hybrid**, не вмешиваясь в сам алгоритм соседей.

Нужно увидеть два участка `run_hybrid_v12.py`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID 330-490 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '330,490p' && \
echo "================ HYBRID 650-730 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '650,730p'
```

И ещё поиск записи в БД:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -nE \
'UPDATE photos|INSERT INTO photos|psycopg|commit\(|hybrid_final_id' \
scripts/run_hybrid_v12.py
```

### Что уже зафиксировано

Будем делать именно так:

```text
                    HYBRID
                      │
                      ▼
              PostgreSQL photos
                      │
          ┌───────────┴───────────┐
          │                       │
      hybrid_final_id          photos.id
          │                       │
   виртуальная группа       идентификатор фото
                                  │
                                  ▼
                         PREVIEW WORKER
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
       data/preview/small/          data/preview/medium/
       photo_123_small.jpg          photo_123_medium.jpg
```

Именно `photos.id` будет **единственным стабильным ключом preview**.

В БД:

```text
id = 123
preview_path = data/preview/medium/photo_123_medium.jpg
preview_status = done
```

Для V2:

- **грид** → `small`;
- **просмотр фотографии** → `medium`;
- оригинал → только при необходимости открыть полный файл;
- имя исходника вообще не участвует в поиске preview;
- адресная папка вообще не участвует;
- `hybrid_final_id` вообще не участвует в поиске preview.

А клиенты и адреса V2 будем строить непосредственно из PostgreSQL:

**Клиенты**
```text
☐ Единая Россия       127
☐ Сила России           84
☐ АЛЬБИОН-ТУР           41
...
```

**Адреса**
```text
☐ 78_v33
☐ 79_v33
☐ 80_v33
...
☐ 95_v33
```

Но адреса я бы **не называл адресами** в логике данных, если фактически это `dino_fingerprint`. Нужно сначала проверить, как именно старый интерфейс использовал `address` и как должен отображаться `hybrid_final_id`. После этого не смешаем три разных понятия: `address`, `dino_fingerprint` и `hybrid_final_id`.

Пришли два вывода выше — после этого можно будет делать первый аккуратный патч.

---

### 👤 **User** — 2026-08-21 00:42:34

sort_test_and_report_v2.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID 330-490 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '330,490p' && \
echo "================ HYBRID 650-730 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '650,730p'
================ HYBRID 330-490 ================
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
================ HYBRID 650-730 ================
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -nE \
'UPDATE photos|INSERT INTO photos|psycopg|commit\(|hybrid_final_id' \
scripts/run_hybrid_v12.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 00:42:36

Вот теперь видно ключевое: **`run_hybrid_v12.py` вообще не работает с PostgreSQL**.

Он делает только:

```text
DINO results
   ↓
Hybrid v12
   ↓
best_id
   ↓
copy2() → output/<best_id>/<filename>
   ↓
JSON отчёты
```

То есть строки 401–445 действительно выполняют **физическое копирование** фотографий в `output/<assigned_id>/`. Но `hybrid_final_id` в PostgreSQL этот скрипт сам не записывает.

Поэтому для новой архитектуры я бы **не встраивал preview в `run_hybrid_v12.py` напрямую**. Сначала нужно понять, какой скрипт сейчас переносит результаты Hybrid в PostgreSQL — судя по структуре проекта, это может быть отдельный этап.

Нужен следующий вывод:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID 490-650 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '490,650p' && \
echo "================ ALL DB HYBRID WRITERS ================" && \
grep -RniE \
'UPDATE[[:space:]]+photos|hybrid_final_id|hybrid_original_id|hybrid_changed' \
scripts app \
--include="*.py" \
| grep -vE 'diagnose|photo_db.py' \
| head -300
```

### Сейчас архитектура получается такая

```text
                DINO
                  │
                  ▼
           Hybrid v12
                  │
                  ├── best_id
                  │
                  ├── hybrid_v12.json
                  ├── report.json
                  └── output/<best_id>/...
                              │
                              │ физические копии
                              ▼
                         НЕ НУЖНЫ V2
```

А V2 нам нужен совсем другой источник:

```text
PostgreSQL photos
│
├── id
├── path
├── client
├── address_id
├── simple_address
├── dino_fingerprint
├── hybrid_final_id
├── hybrid_neighbors
└── preview_path
```

И уже из него:

```text
Клиенты
☐ Клиент 1
☐ Клиент 2
...

Адреса / группы Hybrid
☐ 78_v33
☐ 79_v33
...
☐ 95_v33

Фотографии
┌──────────┐ ┌──────────┐
│  preview │ │  preview │
│ photo_12 │ │ photo_13 │
└──────────┘ └──────────┘
```

**Preview вообще не должен зависеть от физической сортировки.**

И ещё важный момент: у нас уже есть `photos.id` и `preview_path`, поэтому переделывать схему PostgreSQL для этой задачи не требуется.

После вывода `490–650` станет понятно, **где правильно поставить запись Hybrid → PostgreSQL**, а затем туда же последовательно подключим:

**Hybrid → DB → Preview → V2.**

---

### 👤 **User** — 2026-08-21 00:43:02

превью можно создавать после результата гибрида

---

### 🤖 **Assistant** — 2026-08-21 00:43:03

Да. Это как раз самый правильный вариант.

**Preview создаём после завершения Hybrid**, отдельным этапом. Сам Hybrid не трогаем.

И архитектура будет:

```text
DINO
  ↓
Hybrid v12
  ↓
результат Hybrid
  ↓
PostgreSQL
  ↓
CREATE PREVIEWS
  ├── data/preview/small/photo_<id>_small.jpg
  └── data/preview/medium/photo_<id>_medium.jpg
  ↓
V2
```

При этом preview привязывается **только к `photos.id`**.

### Размеры

Предлагаю:

- `small` — максимум **400×400** — для сетки;
- `medium` — максимум **1200×1200** — для просмотра;
- оригинал остаётся в `path`.

Например:

```text
data/preview/
├── small/
│   ├── photo_1_small.jpg
│   ├── photo_2_small.jpg
│   └── ...
└── medium/
    ├── photo_1_medium.jpg
    ├── photo_2_medium.jpg
    └── ...
```

Это лучше нынешней структуры `preview/daily/<run>/<fingerprint>/...`, потому что **ни имя файла, ни папка Hybrid, ни адрес никогда не влияют на поиск preview**.

В PostgreSQL:

```text
id = 526
preview_path = data/preview/medium/photo_526_medium.jpg
preview_status = done
```

Для V2 можно вообще получать оба пути детерминированно по `id`, а `preview_path` оставить как основной medium-путь.

### И главное

**Физическая сортировка и виртуальная сортировка разделяются.**

Hybrid может физически создать:

```text
output/daily/95_v33/...
```

но V2 фотографии получает из PostgreSQL и группирует по:

```text
hybrid_final_id
```

То есть если завтра физические папки изменятся — **V2 не сломается**.

Следующий шаг — посмотреть конец `run_hybrid_v12.py` и найти, **кто после Hybrid записывает `hybrid_final_id` в PostgreSQL**. Именно после этого этапа поставим `create_previews`, чтобы preview создавались уже по окончательному результату Hybrid.

---

### 👤 **User** — 2026-08-21 00:43:14

давай

---

### 🤖 **Assistant** — 2026-08-21 00:43:15

Да. Идём по безопасной схеме: **сначала найдём точку записи результата Hybrid в PostgreSQL, ничего пока не меняем**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID DB WRITERS ================" && \
grep -RniE \
'UPDATE[[:space:]]+photos|INSERT INTO photos|hybrid_final_id|hybrid_original_id|hybrid_changed' \
scripts app \
--include="*.py" \
| grep -vE 'diagnose_dino_hybrid_db.py|photo_db.py' \
| head -300 && \
echo && \
echo "================ HYBRID END ================" && \
nl -ba scripts/run_hybrid_v12.py | tail -180
```

По этому выводу определим конкретное место:

```text
Hybrid v12
   ↓
запись hybrid_final_id в PostgreSQL
   ↓
создание small/medium preview
   ↓
V2 читает PostgreSQL
```

**Сам `run_hybrid_v12.py` пока не изменяем.** Сначала найдём фактический DB writer, чтобы не сломать уже работающий Hybrid.

---

### 👤 **User** — 2026-08-21 00:43:29

727	    print("=" * 80)
   728	    print("DONE")
   729	    print("=" * 80)
   730	    print()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -nE \
'UPDATE photos|INSERT INTO photos|psycopg|commit\(|hybrid_final_id' \
scripts/run_hybrid_v12.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID DB WRITERS ================" && \
grep -RniE \
'UPDATE[[:space:]]+photos|INSERT INTO photos|hybrid_final_id|hybrid_original_id|hybrid_changed' \
scripts app \
--include="*.py" \
| grep -vE 'diagnose_dino_hybrid_db.py|photo_db.py' \
| head -300 && \
echo && \
echo "================ HYBRID END ================" && \
nl -ba scripts/run_hybrid_v12.py | tail -180
================ HYBRID DB WRITERS ================
scripts/photo_ingest.py:235:            INSERT INTO photos (
scripts/import_qwen_to_db.py:166:        INSERT INTO photos (
scripts/run_hybrid_v12.py:363:        hybrid_changed = best != old
scripts/run_hybrid_v12.py:370:        result["hybrid_changed"] = hybrid_changed
scripts/run_hybrid_v12.py:460:                "hybrid_changed": item.get(
scripts/run_hybrid_v12.py:461:                    "hybrid_changed"
scripts/run_hybrid_v12.py:705:        "hybrid_changed": len(changed),
scripts/qwen4b_output_v01.py:174:            UPDATE photos
scripts/qwen4b_output_v01.py:240:            UPDATE photos
scripts/qwen4b_output_v01.py:334:            UPDATE photos
scripts/qwen4b_output_v01.py:438:            UPDATE photos
scripts/migrate_sqlite_to_postgres.py:155:                INSERT INTO photos (
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/pipeline/recovery.py:52:                UPDATE photos
app/pipeline/recovery.py:68:                UPDATE photos
app/workers/qwen_worker.py:194:            UPDATE photos
app/workers/qwen_worker.py:242:            UPDATE photos
app/workers/qwen_worker.py:328:            UPDATE photos
app/workers/dino_worker.py:47:            UPDATE photos
app/workers/dino_worker.py:109:            UPDATE photos
app/workers/dino_worker.py:151:            UPDATE photos
app/workers/dino_worker.py:205:            UPDATE photos

================ HYBRID END ================
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
   741	    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 00:43:33

Да. Теперь картина полностью ясна.

### Что сейчас реально происходит

`run_hybrid_v12.py` заканчивается на:

```text
DINO
 ↓
Hybrid v12
 ↓
sort_results()
 ↓
копирование в output/<best_id>/
 ↓
JSON
```

И **нигде в этом скрипте нет PostgreSQL**.

Более того, поиск по всему проекту показал:

```text
hybrid_final_id
hybrid_original_id
hybrid_changed
hybrid_neighbors
```

используются только для расчёта/диагностики, но **нет ни одного `UPDATE photos SET hybrid_final_id = ...`**.

То есть сейчас `hybrid_final_id` в БД **не является результатом текущего `run_hybrid_v12.py`**.

---

### Поэтому я бы сейчас не трогал Hybrid

Наша правильная архитектура должна быть такой:

```text
                    DINO
                     │
                     ▼
                Hybrid v12
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
     JSON/report          физическая копия
          │                output/daily/...
          │
          ▼
    UPDATE PostgreSQL
          │
          ├── dino_fingerprint
          ├── hybrid_original_id
          ├── hybrid_final_id
          ├── hybrid_changed
          ├── hybrid_score
          ├── hybrid_margin
          └── hybrid_neighbors
          │
          ▼
    CREATE PREVIEWS
          │
          ├── small/photo_<id>_small.jpg
          └── medium/photo_<id>_medium.jpg
          │
          ▼
       V2 frontend
```

И это решает сразу несколько проблем.

### 1. V2 не зависит от физических папок

Фото в БД имеет:

```text
photos.id
photos.photo_id
photos.path
photos.hybrid_final_id
```

Поэтому V2 может показать:

```text
☑ 95_v33
   ├── photo 1
   ├── photo 2
   └── photo 3
```

даже если физически файлы находятся совершенно в другом месте.

### 2. Preview тоже не зависит от имени файла

Будет:

```text
data/preview/
├── small/
│   ├── photo_1_small.jpg
│   ├── photo_2_small.jpg
│   └── ...
└── medium/
    ├── photo_1_medium.jpg
    ├── photo_2_medium.jpg
    └── ...
```

И V2 знает:

```text
photos.id = 526
```

→

```text
photo_526_small.jpg
photo_526_medium.jpg
```

Никаких:

```text
95_v33/
Вавилова52_09.jpg
daily/20260816_230042/
```

для поиска preview больше не требуется.

---

### 3. Но есть один важный момент

Сейчас `run_hybrid_v12.py` получает на вход свои `recognition` rows, а не PostgreSQL `photos.id`.

Поэтому прежде чем писать DB update, нужно установить **как связать строку Hybrid с записью `photos`**.

Судя по текущей БД, для этого есть несколько кандидатов:

```text
photos.photo_id
photos.initial_id
photos.source_path
photos.path
photos.filename
```

Самый надёжный вариант, вероятно, `photo_id`, но **не будем предполагать**.

Дай следующий вывод:

```bash id="0zq3r9"
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID INPUT ROWS ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,180p' && \
echo "================ RECOGNIZER ROW FORMAT ================" && \
grep -nE \
'def run_recognition|recognition|source_path|photo_id|initial_id|file' \
scripts/run_hybrid_v12.py \
| head -120 && \
echo "================ PHOTO ID CREATION ================" && \
grep -RniE \
'photo_id[[:space:]]*=|initial_id[[:space:]]*=|photo_id,' \
scripts/photo_ingest.py \
| head -100
```

После этого мы сможем сделать **один нормальный DB writer для Hybrid**, а уже **после его успешного завершения запускать новый `create_previews`**.

И только потом займёмся V2: **превью + чекбоксы клиентов + чекбоксы fingerprint/address + фильтрация фотографий**.

---

### 👤 **User** — 2026-08-21 00:44:03

физическая копия
          │                output/daily/... физической сортировки не будет

---

### 🤖 **Assistant** — 2026-08-21 00:44:03

Да, понял. **Физической сортировки после Hybrid больше не будет.**

То есть `run_hybrid_v12.py` не должен делать:

```text
output/daily/<fingerprint>/<photo>
```

и вообще не должен раскладывать фотографии по fingerprint-папкам.

Правильная схема теперь такая:

```text
                         DINO
                          │
                          ▼
                      HYBRID v12
                          │
                          ▼
                   результат Hybrid
                          │
                          ▼
                    PostgreSQL
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
   hybrid_final_id     client/address    preview
          │                                │
          │                    ┌───────────┴───────────┐
          │                    ▼                       ▼
          │             small/photo_ID_small   medium/photo_ID_medium
          │
          ▼
       V2 UI
```

### То есть PostgreSQL — источник истины

Для каждой фотографии:

```text
photos.id
photos.photo_id
photos.path
photos.client
photos.address_id
photos.simple_address
photos.dino_fingerprint
photos.hybrid_original_id
photos.hybrid_final_id
photos.hybrid_changed
photos.hybrid_score
photos.hybrid_margin
photos.hybrid_neighbors
photos.preview_path
```

А физический оригинал остаётся **там, где он есть сейчас**.

Hybrid только говорит:

> эта фотография относится к `95_v33`.

И записывает это в БД:

```text
hybrid_final_id = 95_v33
```

### Preview

После Hybrid:

```text
data/preview/
├── small/
│   ├── photo_1_small.jpg
│   ├── photo_2_small.jpg
│   └── ...
└── medium/
    ├── photo_1_medium.jpg
    ├── photo_2_medium.jpg
    └── ...
```

Причём preview создаётся **по `photos.id`**, а не по имени файла или fingerprint.

### V2

Клиенты:

```text
☐ Единая Россия       123
☐ Сила России           87
☐ АЛЬБИОН-ТУР           54
```

Fingerprint:

```text
☐ 78_v33
☐ 79_v33
☐ 80_v33
...
☐ 95_v33
```

Адреса:

```text
☐ Вавилова, 52
☐ Зорге
☐ Шеболдаева, 8
...
```

Все это **виртуальные фильтры по PostgreSQL**, без перемещения файлов.

И фотографии в гриде берутся из БД + `photo_ID_small.jpg`.

---

**Значит, старую функцию `sort_results()` в `run_hybrid_v12.py` нам в новой схеме вообще не нужно использовать.** Она сейчас является именно физической сортировкой через `shutil.copy2()`.

Следующий шаг — определить точное соответствие строки Hybrid → `photos.id`, после чего сделаем запись Hybrid в PostgreSQL и отдельный preview worker.

---

### 👤 **User** — 2026-08-21 00:44:36

гибрид выдает витрутальную сортировку результаты которой записываются в ПСКЛ

---

### 🤖 **Assistant** — 2026-08-21 00:44:37

Да. Именно так фиксируем архитектуру.

### Итоговая схема

```text
ФОТО
  │
  ▼
DINO
  │
  ▼
HYBRID v12
  │
  │ определяет окончательный fingerprint
  ▼
ВИРТУАЛЬНАЯ СОРТИРОВКА
  │
  │ ничего физически не перемещает
  ▼
PostgreSQL
  │
  ├── dino_fingerprint
  ├── hybrid_original_id
  ├── hybrid_final_id   ← результат виртуальной сортировки
  ├── hybrid_changed
  ├── hybrid_score
  ├── hybrid_margin
  └── hybrid_neighbors
  │
  ▼
CREATE PREVIEWS
  │
  ├── small/photo_<DB_ID>_small.jpg
  └── medium/photo_<DB_ID>_medium.jpg
  │
  ▼
V2
```

### Важное разделение

**Hybrid:**

- распознаёт;
- анализирует соседние фотографии;
- меняет `old → final`, если Hybrid считает это правильным;
- формирует виртуальную принадлежность фотографии к fingerprint;
- записывает результат в PostgreSQL;
- **не перемещает и не копирует фотографии**.

**PostgreSQL:**

является источником истины для V2.

Например:

```text
id = 237
filename = Ашхабадский_03.JPG
path = /.../Ашхабадский_03.JPG

dino_fingerprint = 85_v33
hybrid_original_id = 85_v33
hybrid_final_id = 86_v33
hybrid_changed = true
```

V2 показывает эту фотографию **в группе `86_v33`**, хотя физический файл вообще никуда не перемещался.

### Preview

Preview создаётся **после записи результата Hybrid в PostgreSQL**.

И тоже независимо от виртуальной сортировки:

```text
data/preview/small/photo_237_small.jpg
data/preview/medium/photo_237_medium.jpg
```

Поэтому изменение:

```text
85_v33 → 86_v33
```

вообще никак не влияет на preview.

---

И тогда текущий `sort_results()` в `run_hybrid_v12.py` надо будет заменить на **DB update**, а не на `shutil.copy2()`.

Но сначала нужно увидеть, **как `run_hybrid_v12.py` идентифицирует каждую фотографию**, чтобы корректно связать `best_id` с конкретным `photos.id` в PostgreSQL. Это следующий технический шаг.

---

### 👤 **User** — 2026-08-21 00:46:09

т.е. АДРЕСА должны олриентироваться на hybrid_final_id = 86_v33

---

### 🤖 **Assistant** — 2026-08-21 00:46:10

Да, **именно так**.

Если Hybrid определил:

```text
hybrid_final_id = 86_v33
```

то **адресная группа в V2 должна определяться через этот финальный fingerprint**, а не через старый `dino_fingerprint`.

То есть логика:

```text id="1p5u7w"
Фотография
   │
   ├── dino_fingerprint = 85_v33
   │
   └── hybrid_final_id = 86_v33
                         │
                         ▼
                    86_v33
                         │
                         ▼
                 АДРЕС 1
                 АДРЕС 2
                 ...
```

### Но важное уточнение

`86_v33` — это **группа фотографий**, а не обязательно сам адрес.

Поэтому V2 должна строить:

```text id="x0f0r3"
HYBRID FINAL ID
│
├── 78_v33
├── 79_v33
├── ...
└── 86_v33
      │
      ├── адрес A
      ├── адрес B
      └── адрес C
```

То есть **сначала фильтр по `hybrid_final_id`**, затем внутри этой группы показываются связанные адреса.

Если в БД у фотографий:

```text id="qf6g6w"
hybrid_final_id = 86_v33
address = "Вавилова, 52"
```

то эта фотография попадает:

```text
86_v33
└── Вавилова, 52
```

А если другая:

```text id="6d4w8p"
hybrid_final_id = 86_v33
address = "Зорге, 12"
```

то:

```text
86_v33
├── Вавилова, 52
└── Зорге, 12
```

### Поэтому для V2

**Fingerprint — `hybrid_final_id`.**

**Адреса — адреса фотографий, принадлежащих этому `hybrid_final_id`.**

**Клиенты — клиенты фотографий, принадлежащих выбранному `hybrid_final_id` / адресам.**

И всё это **виртуальные фильтры PostgreSQL**, без физической сортировки файлов.

---

### 👤 **User** — 2026-08-21 00:46:41

далее

---

### 🤖 **Assistant** — 2026-08-21 00:46:42

Далее делаем **не UI**, а сначала правильно фиксируем данные в PostgreSQL. Иначе V2 снова будет показывать старые/пустые адреса.

### Шаг 1. Hybrid должен записывать результат в PostgreSQL

Для каждой фотографии:

```text
dino_fingerprint      ← исходный DINO
hybrid_original_id    ← исходный ID перед Hybrid
hybrid_final_id       ← окончательный ID Hybrid
hybrid_changed        ← изменился или нет
hybrid_old_score
hybrid_score
hybrid_margin
hybrid_neighbors
```

При этом:

```text
path
source_path
filename
```

**не меняются.**

Никаких `shutil.copy2()` и физической сортировки.

---

### Шаг 2. После Hybrid создаём preview

Берём `photos.id`:

```text
photos.id = 237
```

и создаём:

```text
data/preview/small/photo_237_small.jpg
data/preview/medium/photo_237_medium.jpg
```

В `preview_path` можно хранить путь к medium:

```text
preview_path = data/preview/medium/photo_237_medium.jpg
```

А small V2 сможет вычислять по `id`.

Размеры предлагаю:

```text
small  = 400 px по длинной стороне
medium = 1200 px по длинной стороне
```

Оригинал остаётся оригиналом.

---

### Шаг 3. V2 читает PostgreSQL

Основная логика:

```text
photos
   │
   ├── hybrid_final_id
   ├── address
   ├── client
   ├── preview_path
   └── id
```

**Не `dino_fingerprint` как основной фильтр.**

---

### Шаг 4. Левая колонка — Клиенты

Из PostgreSQL:

```text
☐ Единая Россия       123
☐ Сила России           87
☐ АЛЬБИОН-ТУР           54
```

Чекбоксы.

---

### Шаг 5. Правая колонка — Адреса

Адреса должны строиться **по текущему `hybrid_final_id`**.

Например выбран:

```text
☑ 86_v33
```

Тогда справа:

```text
Адреса

☐ Вавилова, 52       18
☐ Зорге, 12           7
☐ Шеболдаева, 8       5
```

Если снять `86_v33`, соответствующие адреса исчезают/становятся недоступными.

---

### Шаг 6. Центральная область

Каждая карточка берёт:

```text
photos.id
        ↓
data/preview/small/photo_<id>_small.jpg
```

А при открытии:

```text
data/preview/medium/photo_<id>_medium.jpg
```

или оригинал — только если это предусмотрено просмотром.

---

### Шаг 7. Главное

Получается чистая модель:

```text
ФАЙЛЫ
  │
  │ физически НЕ сортируются
  ▼
PostgreSQL
  │
  ├── DINO
  ├── HYBRID FINAL
  ├── CLIENT
  ├── ADDRESS
  └── PREVIEW
       │
       ▼
     V2 UI
```

То есть **PostgreSQL становится единственным источником виртуальной структуры фотобазы**.

Следующим действием я бы сделал **запись Hybrid → PostgreSQL**, а затем сразу проверил на нескольких реальных `photos.id`, что `hybrid_final_id` действительно записывается правильно. Только после этого подключаем preview worker.

---

### 👤 **User** — 2026-08-21 00:47:56

список АДресов не должен заисеть от того, есть ли в выбранном периоде фотографии этого адреса, если нет - просто (ноль)

---

### 🤖 **Assistant** — 2026-08-21 00:47:57

> **Remembering**
>
>
> ****
>
> 
>
> **Identified address sources, linkage, lists, and zero-photo logic**
>
> 
>
> Worked for 6s

Да. Логика теперь должна быть именно такой:

1. **`hybrid_final_id` - главный идентификатор виртуально отсортированной фотографии.**
   Например:
   `86_v33`.

2. **Адреса не берём из `output/daily/...`** - физической сортировки больше нет.

3. Список адресов строится из **БД + соответствия `hybrid_final_id → address`**.

4. Список адресов является **постоянным** и не фильтруется по текущему периоду.
   - `Вавилова, 52 (15)`
   - `Зорге, 17 (8)`
   - `Шеболдаева, 8 (0)`
   
   То есть `(0)` означает: адрес существует в базе, но в выбранном периоде фотографий для него нет.

5. При выборе адреса фильтрация фотографий уже идёт по:
   **`photos.hybrid_final_id` → адресу этого fingerprint ID**.

6. Аналогично клиенты должны быть независимым постоянным списком, а количество - уже результатом текущего периода.

И главное: **`path`, физическая папка и имя файла не должны участвовать в определении адреса.**

Сейчас следующий шаг - посмотреть, где именно в проекте хранится/определяется соответствие **`86_v33 → конкретный адрес`**, и уже от него построить правильный `addresses.py`.

Дай вывод:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ ADDRESS SOURCES ================" && \
grep -RniE \
'address.*dino|dino.*address|address.*fingerprint|fingerprint.*address|hybrid_final_id.*address|address_id|legal_address|simple_address' \
app scripts \
--include="*.py" \
| head -400
```

После этого будем менять именно источник адресов, а не пытаться восстанавливать их из каталогов.

---

### 👤 **User** — 2026-08-21 00:48:55

пока конкретные адреса не везде присвоены и не все фингепринты готовы

---

### 🤖 **Assistant** — 2026-08-21 00:48:56

Да, тогда **нельзя строить список адресов только из фотографий текущей БД**. Нужно разделить две сущности:

- **Fingerprint ID** — например `86_v33`, уже существует и является виртуальным кластером.
- **Адрес** — может быть пока не назначен этому fingerprint ID.

Поэтому сейчас правильная модель:

```text
86_v33
 ├── address = "Вавилова 52"      ← если уже назначен
 └── photos = ...

87_v33
 ├── address = NULL               ← пока адрес неизвестен
 └── photos = ...

88_v33
 ├── address = "Зорге 17"
 └── photos = ...
```

### В интерфейсе

**Адреса** должны показывать только те fingerprint ID, которым адрес уже присвоен:

```text
Адреса

☐ Вавилова 52       (15)
☐ Зорге 17           (8)
☐ Шеболдаева 8      (0)
```

Но есть важный момент: если адрес уже существует в справочнике, а в выбранном периоде фотографий нет — показываем `(0)`.

При этом fingerprint `87_v33` без адреса **не должен сам превращаться в адрес**.

### И ещё важнее

Нам сейчас не надо пытаться автоматически присваивать:

```text
87_v33 → какой-то адрес
```

Пока это не определено вручную/другим механизмом.

То есть схема должна быть подготовлена под постепенное заполнение:

```text
fingerprint_id    address
────────────────────────────
78_v33            ?
79_v33            ?
80_v33            ?
81_v33            ?
82_v33            ?
83_v33            ?
84_v33            ?
85_v33            ?
86_v33            Вавилова 52
87_v33            ?
88_v33            Зорге 17
...
```

А **Hybrid уже сейчас может работать полностью независимо от этого**: он записывает `hybrid_final_id`, а адресная привязка — отдельный слой.

Это даже лучше архитектурно: **Hybrid не должен знать об адресах вообще.** Он определяет только:

```text
photo → hybrid_final_id
```

а интерфейс потом делает:

```text
hybrid_final_id → address
```

И поэтому, когда позже мы назначим `87_v33 = новый адрес`, интерфейс автоматически сможет показывать этот адрес без переделки Hybrid.

---

### 👤 **User** — 2026-08-21 00:49:06

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ ADDRESS SOURCES ================" && \
grep -RniE \
'address.*dino|dino.*address|address.*fingerprint|fingerprint.*address|hybrid_final_id.*address|address_id|legal_address|simple_address' \
app scripts \
--include="*.py" \
| head -400
================ ADDRESS SOURCES ================
app/web/components/photos.py:367:        # address_fingerprints пока НЕ ограничивает грид.
app/web/components/photos.py:378:        address = fingerprint
app/web/components/photos.py:459:        "only photos with DINO fingerprint + address_directory",
app/web/directory_db.py:32:            simple_address,
app/web/directory_db.py:33:            legal_address
app/web/directory_db.py:52:def get_address_by_fingerprint(fingerprint_id):
app/web/directory_db.py:54:    Возвращает address_id для fingerprint.
app/web/directory_db.py:62:        SELECT address_id
app/web/directory_db.py:63:        FROM address_fingerprints
app/web/directory_db.py:80:def get_address_for_fingerprint(fingerprint_id):
app/web/directory_db.py:85:    address_id = get_address_by_fingerprint(
app/web/directory_db.py:89:    if address_id is None:
app/web/directory_db.py:94:    data = directory.get(address_id)
app/web/directory_db.py:100:        "id": address_id,
app/workers/qwen_worker.py:164:    address_id здесь НЕ используется.
app/workers/dino_worker.py:140:        address_id = адрес, определённый DINO.
app/workers/dino_worker.py:145:    address_id = result.get("best_id")
app/workers/dino_worker.py:155:                address_id = %s,
app/workers/dino_worker.py:169:                address_id,
app/workers/dino_worker.py:173:                address_id,
app/workers/dino_worker.py:372:                address_id = result.get(
app/workers/dino_worker.py:379:                    f" -> address_id={address_id}"
scripts/llm_resolver_v01.py:119:            "Determine the most likely address/fingerprint for the "
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 00:49:08

> **Inspecting Directory Database and Photo Logic**
>
>
> **Inspecting Directory Database and Photo Logic**
>
> 
>
> Worked for a couple of seconds

Вот это уже важная находка. У вас **справочник адресов уже существует**, и даже есть отдельная таблица `address_fingerprints`.

Из grep видно:

```text
app/web/directory_db.py
    get_address_by_fingerprint(fingerprint_id)
    get_address_for_fingerprint(fingerprint_id)

app/web/components/photos.py
    address_fingerprints
```

То есть **не надо создавать новую систему привязки адресов**.

Но сейчас есть принципиальная проблема: `dino_worker.py` записывает `address_id` из `result["best_id"]`. После появления Hybrid это уже неправильно для финального виртуального результата, потому что должно быть:

```text
DINO best_id
      ↓
Hybrid
      ↓
hybrid_final_id
      ↓
address_fingerprints
      ↓
address
```

А не:

```text
DINO best_id
      ↓
address
```

### Что предлагаю сделать

Сначала посмотрим существующую таблицу `address_fingerprints` и код фильтрации. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DIRECTORY DB ================" && \
nl -ba app/web/directory_db.py | sed -n '1,130p' && \
echo && \
echo "================ ADDRESS FILTER ================" && \
nl -ba app/web/components/photos.py | sed -n '330,480p' && \
echo && \
echo "================ ADDRESS_FINGERPRINTS REFERENCES ================" && \
grep -RniE \
'address_fingerprints|get_address_for_fingerprint|get_address_by_fingerprint' \
app scripts \
--include="*.py" \
```

**Пока ничего не меняем.**

Нам нужно увидеть существующую структуру `address_fingerprints`, потому что она как раз может решить нашу задачу:

- `86_v33` → адрес, если уже назначен;
- `87_v33` → `NULL`, если ещё не назначен;
- отсутствующие fingerprint ID не должны ломать интерфейс;
- адреса должны существовать независимо от периода;
- количество фотографий `(N)` считается уже по текущему периоду;
- `(0)` показывается, если адрес есть в справочнике, но фотографий за период нет.

И самое главное — **клиентский/адресный UI будем строить поверх БД, а не поверх физических папок `output/daily`**.

---

### 👤 **User** — 2026-08-21 00:49:31

можно заранее сделать список Адресов в 100 пунктов

---

