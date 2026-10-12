## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 🤖 **Assistant** — 2026-08-21 01:05:47

Да — **после сортировки источником адреса должен быть `hybrid_final_id`**, а не исходный `dino_fingerprint`.

Правильная логика для проекта сейчас такая:

```text
DINO
 ↓
dino_fingerprint
 ↓
сортировка / соседние фото / hybrid
 ↓
hybrid_final_id
 ↓
ВИРТУАЛЬНЫЙ АДРЕС
```

То есть:

- **до сортировки** → адрес берём из `dino_fingerprint`;
- **после сортировки**, если `hybrid_final_id` заполнен → адрес берём из `hybrid_final_id`;
- если `hybrid_final_id` отсутствует → используем `dino_fingerprint` как fallback.

Например:

```text
dino_fingerprint = 85_v33
hybrid_final_id  = 78_v33
```

Фото должно попасть в **адрес 78**, потому что сортировка изменила итоговый fingerprint.

Именно поэтому мой предыдущий ответ был неточным: я слишком рано зафиксировал `dino_fingerprint` как окончательный источник.

### `address_fingerprints` при этом

Оно **не должно определять, показывать ли фото**.

То есть:

```text
hybrid_final_id = 78_v33
address_fingerprints:
78_v33 → 78
```

→ адрес 78.

Но если записи ещё нет:

```text
hybrid_final_id = 80_v33
address_fingerprints:
нет 80_v33
```

→ всё равно **адрес 80**, а не `UNASSIGNED`.

Иными словами, приоритет:

```text
hybrid_final_id
      ↓ если нет
dino_fingerprint
      ↓
нормализация _v33
      ↓
виртуальный адрес
```

А `address_fingerprints` — **справочная/административная связь**, но не обязательный gate для фотографии.

И это хорошо совпадает с тем, что у тебя в `photo_db.py` уже есть оба поля:

```text
dino_fingerprint
hybrid_original_id
hybrid_final_id
```

Теперь надо проверить **как именно `build_photo_index()` выбирает между `hybrid_final_id` и `dino_fingerprint`**. В показанном тобой участке сейчас он использует только `dino_fingerprint`, значит это как раз место, которое нужно исправлять.

---

### 👤 **User** — 2026-08-21 01:06:08

далее

---

### 🤖 **Assistant** — 2026-08-21 01:06:09

Да. Дальше делаем **точечно в `photos.py`**: итоговый адрес должен определяться через `hybrid_final_id`, с fallback на `dino_fingerprint`.

Но сначала нужно увидеть начало функции, чтобы не патчить вслепую — особенно где формируется `PHOTO_RECORD_INDEX`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PHOTO INDEX FUNCTION ================" && \
nl -ba app/web/components/photos.py | sed -n '240,410p'
```

И сразу второй вывод — чтобы убедиться, что `hybrid_final_id` действительно уже приходит в `PHOTO_RECORD_INDEX`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID USAGE ================" && \
grep -RniE \
'hybrid_final_id|hybrid_original_id|hybrid_changed' \
app/web/components/photos.py \
app/web/photo_db.py \
--include="*.py"
```

### Целевой код будет примерно такой

После проверки контекста заменим нынешнее:

```python
fingerprint = str(
    record.get("dino_fingerprint") or ""
).strip()
```

на логику:

```python
fingerprint = str(
    record.get("hybrid_final_id")
    or record.get("dino_fingerprint")
    or ""
).strip()
```

То есть:

```text
hybrid_final_id есть?
        │
       ДА ──→ используем его
        │
       НЕТ
        ↓
dino_fingerprint
```

А затем уже:

```text
78_v33 → 78
79_v33 → 79
...
95_v33 → 95
```

При этом **`address_fingerprints` вообще не участвует в построении основного PHOTO_INDEX**.

После этого отдельно проверим сортировку, чтобы убедиться, что `hybrid_final_id` действительно содержит **итоговый fingerprint после анализа соседних фотографий**, а не промежуточное значение.

---

### 👤 **User** — 2026-08-21 01:06:33

int_mvp_v02 && \
echo "================ PHOTO INDEX FUNCTION ================" && \
nl -ba app/web/components/photos.py | sed -n '240,410p'
================ PHOTO INDEX FUNCTION ================
   240	
   241	        value = get_photo_taken_date(
   242	            path
   243	        )
   244	
   245	        if not value:
   246	            return False
   247	
   248	    if date_from and value < date_from:
   249	        return False
   250	
   251	    if date_to and value > date_to:
   252	        return False
   253	
   254	    return True
   255	
   256	
   257	
   258	def build_photo_index():
   259	
   260	    PHOTO_INDEX.clear()
   261	
   262	    # ========================================================
   263	    # POSTGRESQL = ЕДИНЫЙ ИСТОЧНИК ИСТИНЫ
   264	    # ========================================================
   265	
   266	    try:
   267	        PHOTO_RECORD_INDEX.clear()
   268	
   269	        PHOTO_RECORD_INDEX.update(
   270	            build_photo_record_index(PROJECT_ROOT)
   271	        )
   272	
   273	        print(
   274	            "[PHOTO RECORD INDEX]",
   275	            "records=",
   276	            len(PHOTO_RECORD_INDEX),
   277	            flush=True,
   278	        )
   279	
   280	    except Exception as exc:
   281	
   282	        print(
   283	            "[PHOTO RECORD INDEX ERROR]",
   284	            repr(exc),
   285	            flush=True,
   286	        )
   287	
   288	        return
   289	
   290	    # ========================================================
   291	    # ВИРТУАЛЬНАЯ СОРТИРОВКА
   292	    #
   293	    # Никакого output/daily.
   294	    # Никакого копирования файлов.
   295	    # Физические фотографии остаются в source_path.
   296	    # ========================================================
   297	
   298	    address_files = {}
   299	    unassigned = []
   300	
   301	    for record in PHOTO_RECORD_INDEX.values():
   302	
   303	        # Не обрабатываем fallback-ключи:
   304	        # __ADDR_FILE__:address:filename
   305	        if not str(record.get("photo_id") or "").strip():
   306	            continue
   307	
   308	        # ----------------------------------------------------
   309	        # Физический путь фотографии
   310	        # ----------------------------------------------------
   311	
   312	        raw_path = (
   313	            record.get("source_path")
   314	            or record.get("path")
   315	        )
   316	
   317	        if not raw_path:
   318	            continue
   319	
   320	        path = Path(raw_path)
   321	
   322	        if not path.is_absolute():
   323	            path = PROJECT_ROOT / path
   324	
   325	        path = path.resolve()
   326	
   327	        if not path.exists():
   328	            print(
   329	                "[PHOTO FILE NOT FOUND]",
   330	                path,
   331	                flush=True,
   332	            )
   333	            continue
   334	
   335	        if (
   336	            not path.is_file()
   337	            or path.suffix.lower() not in IMAGE_EXTENSIONS
   338	        ):
   339	            continue
   340	
   341	        # ----------------------------------------------------
   342	        # ВИРТУАЛЬНЫЙ АДРЕС
   343	        #
   344	        # На данном этапе единственный источник адреса:
   345	        # dino_fingerprint.
   346	        #
   347	        # hybrid_final_id и client normalization здесь
   348	        # НЕ используются.
   349	        #
   350	        # Если DINO fingerprint отсутствует —
   351	        # фотография в основной грид НЕ попадает.
   352	        # ----------------------------------------------------
   353	
   354	        fingerprint = str(
   355	            record.get("dino_fingerprint") or ""
   356	        ).strip()
   357	
   358	        if not fingerprint:
   359	            continue
   360	
   361	        # ----------------------------------------------------
   362	        # ВИРТУАЛЬНЫЙ АДРЕС
   363	        #
   364	        # На данном этапе dino_fingerprint сам является
   365	        # источником виртуального адреса.
   366	        #
   367	        # address_fingerprints пока НЕ ограничивает грид.
   368	        # Соответствия для новых fingerprint будут добавлены
   369	        # позже.
   370	        #
   371	        # Например:
   372	        #   78_v33 -> 78
   373	        #   79_v33 -> 79
   374	        #   85_v33 -> 85
   375	        #   95_v33 -> 95
   376	        # ----------------------------------------------------
   377	
   378	        address = fingerprint
   379	
   380	        if (
   381	            address.endswith("_v33")
   382	            and address[:-4].isdigit()
   383	        ):
   384	            address = address[:-4]
   385	
   386	        address = address.strip()
   387	
   388	        if not address:
   389	            continue
   390	
   391	        address_files.setdefault(
   392	            address,
   393	            []
   394	        ).append(path)
   395	
   396	    # ========================================================
   397	    # АДРЕСА
   398	    # ========================================================
   399	
   400	    addresses = sorted(
   401	        address_files.keys(),
   402	        key=lambda value: (
   403	            (0, int(value))
   404	            if value.isdigit()
   405	            else (1, value.lower())
   406	        ),
   407	    )
   408	
   409	    # ========================================================
   410	    # СОХРАНЯЕМ ИНДЕКС
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID USAGE ================" && \
grep -RniE \
'hybrid_final_id|hybrid_original_id|hybrid_changed' \
app/web/components/photos.py \
app/web/photo_db.py \
--include="*.py"
================ HYBRID USAGE ================
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/web/photo_db.py:50:            hybrid_changed,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:06:35

Отлично. Теперь точно видно: **`hybrid_final_id` уже загружается из PostgreSQL в `PHOTO_RECORD_INDEX`, но вообще нигде не используется при построении виртуального адреса.**

Значит, исправляем именно это место.

### Правило

При построении грида:

```text
hybrid_final_id
    ↓ если заполнен
итоговый fingerprint
    ↓ если пуст
dino_fingerprint
    ↓
адрес
```

То есть сортировка имеет приоритет.

Но перед патчем я хочу проверить фактические данные — действительно ли `hybrid_final_id` уже заполнен после твоей сортировки.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -h localhost -U lora -d photobase -c "
SELECT
    dino_fingerprint,
    hybrid_original_id,
    hybrid_final_id,
    hybrid_changed,
    COUNT(*) AS photos
FROM photos
WHERE dino_fingerprint IS NOT NULL
GROUP BY
    dino_fingerprint,
    hybrid_original_id,
    hybrid_final_id,
    hybrid_changed
ORDER BY dino_fingerprint, hybrid_final_id;
"
```

### Что ожидаем увидеть

Например:

```text
dino_fingerprint | hybrid_final_id | hybrid_changed
-----------------+-----------------+---------------
78_v33           | 78_v33          | f
85_v33           | 78_v33          | t
...
```

Если так — всё однозначно: фото с `85_v33`, которые сортировщик перевёл в `78_v33`, должны отображаться **в адресе 78**.

После этого внесём небольшой патч только в строки **342–389**.

Целевой фрагмент будет:

```python
# ----------------------------------------------------
# ВИРТУАЛЬНЫЙ АДРЕС
#
# После виртуальной сортировки приоритет имеет
# hybrid_final_id.
#
# Если сортировка ещё не дала итоговый fingerprint,
# используем исходный dino_fingerprint.
# ----------------------------------------------------

fingerprint = str(
    record.get("hybrid_final_id")
    or record.get("dino_fingerprint")
    or ""
).strip()

if not fingerprint:
    continue

address = fingerprint

if (
    address.endswith("_v33")
    and address[:-4].isdigit()
):
    address = address[:-4]

address = address.strip()

if not address:
    continue
```

**`address_fingerprints` здесь вообще не трогаем.**

После патча проверим три вещи:

1. `hybrid_final_id` действительно меняет адрес в гриде.
2. Если `hybrid_final_id` `NULL`/пустой — работает fallback на `dino_fingerprint`.
3. Отсутствие записи в `address_fingerprints` **не убирает фотографию из грида**.

Сначала дай вывод SQL выше — по нему сразу станет видно, можем ли патчить без дополнительной логики.

---

### 👤 **User** — 2026-08-21 01:07:05

dino_fingerprint | hybrid_original_id | hybrid_final_id | hybrid_changed | photos 
------------------+--------------------+-----------------+----------------+--------
 78_v33           |                    |                 | f              |     84
 79_v33           |                    |                 | f              |     31
 80_v33           |                    |                 | f              |     10
 81_v33           |                    |                 | f              |     16
 82_v33           |                    |                 | f              |     12
 83_v33           |                    |                 | f              |     17
 84_v33           |                    |                 | f              |     16
 85_v33           |                    |                 | f              |     23
 86_v33           |                    |                 | f              |     22
 87_v33           |                    |                 | f              |

---

### 🤖 **Assistant** — 2026-08-21 01:07:07

Вот это важный момент: **сейчас `hybrid_final_id` у всех этих записей пустой**.

То есть текущая БД показывает:

```text
dino_fingerprint | hybrid_final_id
-----------------+----------------
78_v33           | NULL
79_v33           | NULL
80_v33           | NULL
...
```

Следовательно, если мы сейчас просто сделаем:

```python
record.get("hybrid_final_id") or record.get("dino_fingerprint")
```

то **поведение грида фактически не изменится** — он продолжит брать `dino_fingerprint`.

### Значит, порядок работы такой

Сейчас:

```text
DINO
 ↓
dino_fingerprint
 ↓
грид
```

А после запуска/применения сортировки должно стать:

```text
DINO
 ↓
dino_fingerprint
 ↓
СОРТИРОВКА
 ↓
hybrid_final_id
 ↓
грид
```

Причём `hybrid_final_id` должен быть заполнен **только там, где сортировка действительно изменила итог**.

---

### Но здесь есть ещё один нюанс

У тебя:

```text
hybrid_changed = f
hybrid_original_id = NULL
hybrid_final_id = NULL
```

для всех записей.

Это может означать не ошибку, а то, что **сортировщик пока вообще не записал результаты hybrid в `photos`**.

Поэтому сейчас **не надо ещё патчить `photos.py` вслепую**.

Нужно найти код сортировки, который должен заполнять:

```text
hybrid_original_id
hybrid_final_id
hybrid_changed
hybrid_score
hybrid_margin
hybrid_neighbors
```

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID WRITES ================" && \
grep -RniE \
'hybrid_final_id|hybrid_original_id|hybrid_changed|hybrid_score|hybrid_margin|hybrid_neighbors' \
app scripts \
--include="*.py" \
| head -500
```

**Особенно нужен код, где есть `UPDATE photos` или `SET hybrid_...`.**

Потому что мы уже знаем архитектурное правило:

> **Итоговый адрес = `hybrid_final_id`, если сортировка его определила; иначе `dino_fingerprint`.**

А теперь надо убедиться, что сама сортировка действительно записывает `hybrid_final_id`. Именно это сейчас следующий узел, который надо проверить.

---

### 👤 **User** — 2026-08-21 01:07:45

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID WRITES ================" && \
grep -RniE \
'hybrid_final_id|hybrid_original_id|hybrid_changed|hybrid_score|hybrid_margin|hybrid_neighbors' \
app scripts \
--include="*.py" \
| head -500
================ HYBRID WRITES ================
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/photo_db.py:48:            hybrid_original_id,
app/web/photo_db.py:49:            hybrid_final_id,
app/web/photo_db.py:50:            hybrid_changed,
app/web/photo_db.py:52:            hybrid_score,
app/web/photo_db.py:53:            hybrid_margin,
app/web/photo_db.py:54:            hybrid_neighbors,
scripts/run_hybrid_v12.py:363:        hybrid_changed = best != old
scripts/run_hybrid_v12.py:370:        result["hybrid_changed"] = hybrid_changed
scripts/run_hybrid_v12.py:373:        result["hybrid_score"] = new_score
scripts/run_hybrid_v12.py:375:        result["hybrid_margin"] = margin
scripts/run_hybrid_v12.py:376:        result["hybrid_neighbors"] = dict(neighbors)
scripts/run_hybrid_v12.py:460:                "hybrid_changed": item.get(
scripts/run_hybrid_v12.py:461:                    "hybrid_changed"
scripts/run_hybrid_v12.py:481:                "hybrid_score": item.get(
scripts/run_hybrid_v12.py:482:                    "hybrid_score"
scripts/run_hybrid_v12.py:705:        "hybrid_changed": len(changed),
scripts/diagnose_dino_hybrid_db.py:34:                    hybrid_original_id,
scripts/diagnose_dino_hybrid_db.py:35:                    hybrid_final_id,
scripts/diagnose_dino_hybrid_db.py:36:                    hybrid_changed,
scripts/diagnose_dino_hybrid_db.py:38:                    hybrid_score,
scripts/diagnose_dino_hybrid_db.py:39:                    hybrid_margin,
scripts/diagnose_dino_hybrid_db.py:40:                    hybrid_neighbors
scripts/diagnose_dino_hybrid_db.py:64:            hybrid_changed = 0
scripts/diagnose_dino_hybrid_db.py:81:                    hybrid_changed_value,
scripts/diagnose_dino_hybrid_db.py:83:                    hybrid_score,
scripts/diagnose_dino_hybrid_db.py:84:                    hybrid_margin,
scripts/diagnose_dino_hybrid_db.py:85:                    hybrid_neighbors,
scripts/diagnose_dino_hybrid_db.py:98:                if hybrid_changed_value:
scripts/diagnose_dino_hybrid_db.py:99:                    hybrid_changed += 1
scripts/diagnose_dino_hybrid_db.py:110:                print(f"hybrid_original_id  : {hybrid_original}")
scripts/diagnose_dino_hybrid_db.py:111:                print(f"hybrid_final_id     : {hybrid_final}")
scripts/diagnose_dino_hybrid_db.py:112:                print(f"hybrid_changed      : {hybrid_changed_value}")
scripts/diagnose_dino_hybrid_db.py:114:                print(f"hybrid_score        : {hybrid_score}")
scripts/diagnose_dino_hybrid_db.py:115:                print(f"hybrid_margin       : {hybrid_margin}")
scripts/diagnose_dino_hybrid_db.py:116:                print(f"hybrid_neighbors    : {json.dumps(hybrid_neighbors, ensure_ascii=False)}")
scripts/diagnose_dino_hybrid_db.py:126:            print("Hybrid changed      :", hybrid_changed)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:07:47

Да, теперь картина ясная.

**Сама hybrid-сортировка есть** — `scripts/run_hybrid_v12.py`. Но в выводе `grep` **нет ни одного `UPDATE photos SET hybrid_...`**. Значит, очень вероятно, что `run_hybrid_v12.py` пока формирует результаты, но не записывает их в PostgreSQL `photos`.

Нам сейчас не надо менять `photos.py`. Сначала надо проверить участок `run_hybrid_v12.py`, где формируется и сохраняется результат.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID 330-510 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '330,510p'
```

И ещё:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID DB / SAVE ================" && \
grep -nEi \
'psycopg2|postgres|photos|UPDATE|INSERT|executemany|execute\(' \
scripts/run_hybrid_v12.py \
| head -250
```

### Что мы хотим получить

Итоговая схема должна быть именно такой:

```text
DINO
  │
  └── dino_fingerprint
          │
          ▼
   hybrid сортировка
          │
          ▼
   hybrid_final_id
          │
          ▼
       PHOTO_INDEX
          │
          ▼
       виртуальный адрес
```

И правило fallback:

```text
hybrid_final_id заполнен
        │
       ДА ─────→ hybrid_final_id
        │
       НЕТ
        ↓
dino_fingerprint
```

При этом `address_fingerprints` — **это уже отдельная связь справочника**:

```text
fingerprint_id → address_id
```

Она **не должна определять, показывать ли фото в гриде**.

То есть твоя исходная поправка была правильной:

> Если для fingerprint нет записи в `address_fingerprints`, фото **всё равно получает адрес**.

А теперь уточнение:

> Если после hybrid-сортировки есть `hybrid_final_id`, адрес берётся **из него**, а не из исходного `dino_fingerprint`.

Сейчас главный вопрос — **записывает ли `run_hybrid_v12.py` результат hybrid в `photos`**. Дай эти два вывода, и дальше уже сделаем конкретный патч без лишних изменений.

---

### 👤 **User** — 2026-08-21 01:08:16

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID 330-510 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '330,510p'
================ HYBRID 330-510 ================
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
   510	    )alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID DB / SAVE ================" && \
grep -nEi \
'psycopg2|postgres|photos|UPDATE|INSERT|executemany|execute\(' \
scripts/run_hybrid_v12.py \
| head -250
================ HYBRID DB / SAVE ================
403:    Copy photos according to FINAL Hybrid best_id.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:08:17

Вот теперь точно установлено.

`run_hybrid_v12.py` **не записывает результат hybrid в PostgreSQL вообще**.

Он делает только:

```text
DINO/result
   ↓
best_id
   ↓
копирование файла в output_dir / best_id
```

То есть сейчас:

- `dino_fingerprint` записан в `photos`;
- `hybrid_final_id` в `photos` не записывается;
- `hybrid_original_id` не записывается;
- `hybrid_changed` не записывается;
- `output/daily/...` получает результат hybrid физически;
- веб-грид об этом результате **не знает** и продолжает использовать `dino_fingerprint`.

### Значит, здесь есть два разных понятия

**1. Результат DINO:**

```text
dino_fingerprint = 85_v33
```

**2. Результат сортировщика:**

```text
best_id = 78_v33
```

И именно `best_id` после hybrid должен стать:

```text
hybrid_final_id = 78_v33
```

для этой фотографии.

---

### И вот главное

Я бы **не стал сейчас писать hybrid-результат непосредственно в `photos` из `run_hybrid_v12.py`**, пока не посмотрим, как именно запускается сортировка и какой идентификатор используется для сопоставления фото с PostgreSQL.

У нас уже есть надёжный идентификатор:

```text
photos.photo_id
```

а сам hybrid сейчас работает с:

```python
item["file"]
```

Нужно правильно связать:

```text
hybrid file
     ↓
photos.source_path / path
     ↓
photos.photo_id
     ↓
hybrid_final_id
```

Иначе можно случайно записать результат не той фотографии.

### Следующий шаг

Покажи начало `run_hybrid_v12.py`, где он **загружает исходные строки `rows`** и формирует `row["file"]`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID START ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,330p'
```

После этого уже можно будет сделать нормальную схему:

```text
photos
  │
  ├── dino_fingerprint
  │
  └── source_path
          ↓
    run_hybrid_v12
          ↓
      best_id
          ↓
  hybrid_final_id
          ↓
    PHOTO_INDEX
          ↓
       адрес
```

И при этом **`address_fingerprints` оставляем справочником связи fingerprint → address, но не используем его как условие допуска фотографии в грид.**

То есть итоговое правило зафиксировано:

```text
hybrid_final_id → если есть
dino_fingerprint → если hybrid_final_id отсутствует
```

А `address_fingerprints` **не блокирует** фотографию.

---

### 👤 **User** — 2026-08-21 01:08:57

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID START ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '1,330p'
================ HYBRID START ================
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:09:01

Да. Теперь картина однозначная.

### Что сейчас происходит

У тебя есть **два разных уровня результата**:

1. **`dino_fingerprint`** — первичный результат распознавания DINO.
2. **`hybrid_final_id` / `best_id`** — финальный результат **после Hybrid v12**, который может изменить DINO, используя:
   - TOP-5 DINO;
   - sub-fingerprint для пограничных случаев;
   - соседние фотографии;
   - правило gain > 1.5.

То есть логически:

```text
ФОТО
  ↓
DINO v33
  ↓
dino_fingerprint = 85_v33
  ↓
Hybrid v12
  ↓
best_id = 84_v33
```

В таком случае **виртуальный адрес фотографии должен определяться `hybrid_final_id`, если Hybrid действительно был применён и дал финальный результат**.

---

### Но сейчас Hybrid у тебя НЕ попадает в PostgreSQL

Это видно очень чётко.

`run_hybrid_v12.py`:

```text
hybrid_v12(...)
    ↓
best_id
    ↓
sort_results(...)
    ↓
output_dir / assigned_id
```

Он **копирует фотографии по `best_id`**, но нигде не делает:

```text
UPDATE photos
SET hybrid_final_id = ...
```

И вообще в нём нет `psycopg2`, `INSERT`, `UPDATE`.

Поэтому твоя БД закономерно показывает:

```text
dino_fingerprint | hybrid_original_id | hybrid_final_id | hybrid_changed
-----------------+--------------------+-----------------+---------------
78_v33           |                    |                 | f
79_v33           |                    |                 | f
...
```

То есть поля Hybrid в таблице `photos` фактически **не заполнены**.

---

## Поэтому текущий `photos.py` использует неправильный уровень результата

Сейчас:

```python
fingerprint = str(
    record.get("dino_fingerprint") or ""
).strip()
```

и дальше:

```python
address = fingerprint
```

Это означает:

> UI всегда показывает фотографию по исходному DINO, независимо от того, была ли она впоследствии переопределена Hybrid.

А ты как раз подтвердил, что Hybrid предназначен для **финальной сортировки**.

---

# Как должно быть

Я бы зафиксировал архитектуру так:

```text
                    ┌─────────────────┐
                    │   DINO v33      │
                    └────────┬────────┘
                             │
                             ▼
                    dino_fingerprint
                             │
                             ▼
                    ┌─────────────────┐
                    │   Hybrid v12    │
                    │                 │
                    │ sub-fingerprint │
                    │ + neighbors     │
                    │ + TOP-5         │
                    └────────┬────────┘
                             │
                             ▼
                     hybrid_final_id
                             │
                             ▼
                    address_fingerprints
                             │
                             ▼
                      address_directory
                             │
                             ▼
                         В UI адрес
```

То есть:

### DINO

Отвечает на вопрос:

> «На какой fingerprint эта фотография похожа изначально?»

Например:

```text
dino_fingerprint = 85_v33
```

### Hybrid

Отвечает:

> «Какой fingerprint является окончательным после анализа соседей и sub-fingerprint?»

Например:

```text
hybrid_original_id = 85_v33
hybrid_final_id    = 84_v33
hybrid_changed     = true
```

### UI

Не должен сам вычислять Hybrid.

Он должен просто брать:

```text
hybrid_final_id
```

если он существует, иначе:

```text
dino_fingerprint
```

---

## И ещё важный момент с `address_fingerprints`

Вот здесь у тебя сейчас тоже есть разрыв.

В БД:

```text
78_v33 → address_id 78
79_v33 → address_id 79
```

Но для:

```text
80_v33
81_v33
...
95_v33
```

соответствий пока нет.

Поэтому нельзя просто сказать:

```python
address = fingerprint[:-4]
```

Это было временное решение.

Правильная цепочка должна быть:

```python
final_fingerprint
        ↓
address_fingerprints
        ↓
address_id
        ↓
address_directory
```

А если соответствия нет — фотография должна быть **UNASSIGNED**, а не автоматически превращаться в адрес `80`, `81`, `82` и т.д.

---

# Что я предлагаю сделать следующим шагом

**Не менять пока код вслепую.**

Сначала надо проверить одну вещь: действительно ли существующий запуск Hybrid когда-либо давал изменения `best_id != top1`.

То есть нам надо получить статистику примерно:

```text
DINO photos:       399
Hybrid processed:  32
Hybrid changed:     X
Hybrid unchanged:   Y
```

И особенно увидеть:

```text
old → new
85_v33 → 84_v33
94_v33 → 92_v33
...
```

Если Hybrid реально меняет результаты, тогда следующим шагом делаем правильно:

1. `run_hybrid_v12.py` сохраняет `best_id` в PostgreSQL;
2. `hybrid_original_id = dino_fingerprint`;
3. `hybrid_final_id = best_id`;
4. `hybrid_changed = best_id != dino_fingerprint`;
5. UI использует **Hybrid final**, а не голый DINO;
6. `address_fingerprints` становится единственным механизмом преобразования fingerprint → адрес;
7. `dino_fingerprint` остаётся исходным результатом и **никогда не затирается**.

Это будет чистая архитектура: **DINO → Hybrid → fingerprint mapping → адрес → UI**.

---

### 👤 **User** — 2026-08-21 01:10:11

`address_fingerprints` пока не трогаем, для отображения используем нормализованный hybrid\_final\_id

---

### 🤖 **Assistant** — 2026-08-21 01:10:12

Да. Тогда фиксируем правильную архитектуру:

- **`dino_fingerprint`** — исходный результат распознавания DINO.
- **`hybrid_final_id`** — итоговый результат сортировки Hybrid и **именно его используем как виртуальный адрес для отображения**.
- Если `hybrid_final_id` пустой → используем `dino_fingerprint` как fallback.
- `address_fingerprints` **пока вообще не участвует** в построении грида.
- Физический файл по-прежнему берём из `source_path` / `path`; ничего не копируем и не перемещаем.
- Для UI `78_v33` → виртуальный адрес `78`, `79_v33` → `79`.

Сейчас проблема очевидна: в `photos.py` строки 354–378 используют только `dino_fingerprint`, поэтому результаты Hybrid вообще не влияют на отображение. Причём в текущем `run_hybrid_v12.py` Hybrid **не записывает результат обратно в PostgreSQL** — он только создаёт `best_id` в своём результате и копирует файлы.

То есть следующий шаг — **не трогать Hybrid-алгоритм**, а сделать сохранение его результата в `photos.hybrid_final_id` и затем переключить `build_photo_index()` на него.

### 1. Сначала проверим схему `photos`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -h localhost -U lora -d photobase -c '\d photos'
```

Нужно убедиться, что `hybrid_final_id`, `hybrid_original_id`, `hybrid_changed`, `hybrid_score`, `hybrid_margin`, `hybrid_neighbors` действительно есть и какого они типа.

После этого сделаем **отдельный аккуратный save-шаг для Hybrid**, не меняя саму frozen V12 логику.

---

### 👤 **User** — 2026-08-21 01:11:02

id                    | bigint                      |           | not null | nextval('photos_id_seq'::regclass)
 photo_id              | text                        |           | not null | 
 source_path           | text                        |           | not null | 
 path                  | text                        |           | not null | 
 filename              | text                        |           | not null | 
 original_filename     | text                        |           |          | 
 address               | text                        |           |          | 
 client                | text                        |           |          | 
 brand                 | text                        |           |          | 
 category              | text                        |           |          | 
 description           | text                        |           |          | 
 status                | text                        |           | not null | 'pending'::text
 dino_status           | text                        |           | not null | 'pending'::text
 qwen_status           | text                        |           | not null | 'pending'::text
:ending'::text
 dino_status           | text                        |           | not null | 'pending'::text
 qwen_status           | text                        |           | not null | 'pending'::text
 sort_status           | text                        |           | not null | 'pending'::text
 preview_status        | text                        |           | not null | 'pending'::text
 error_message         | text                        |           |          | 
 dino_fingerprint      | text                        |           |          | 
 dino_score            | double precision            |           |          | 
 dino_second_score     | double precision            |           |          | 
 dino_margin           | double precision            |           |          | 
 dino_time_sec         | double precision            |           |          | 
 hybrid_original_id    | text                        |           |          | 
 hybrid_final_id       | text                        |           |          | 
 hybrid_changed        | boolean                     |           |          | false
 hybrid_old_score      | double precision            |           |          | 
 hybrid_score          | double precision            |           |          | 
 hybrid_margin         | double precision            |           |          | 
:
hybrid_score          | double precision            |           |          | 
 hybrid_margin         | double precision            |           |          | 
 hybrid_neighbors      | jsonb                       |           |          | 
 confidence            | integer                     |           |          | 
 qwen_time_sec         | double precision            |           |          | 
 text_json             | jsonb                       |           |          | 
 colors_json           | jsonb                       |           |          | 
 objects_json          | jsonb                       |           |          | 
 environment_json      | jsonb                       |           |          | 
 image_quality_json    | jsonb                       |           |          | 
 camera_view_json      | jsonb                       |           |          | 
 scene_objects_json    | jsonb                       |           |          | 
 analysis_quality_json | jsonb                       |           |          | 
 raw_json              | jsonb                       |           |          | 
 preview_path          | text                        |           |          | 
 created_at            | timestamp without time zone |           | not null | CURRENT_TIMESTAMP
 updated_at            | timestamp without time zone |           | not null | CURRENT_TIMESTAMP
 source_id             | text                        |           |          | 
 address_id            | text                        |           |          | 
 initial_id            | text                        |           |          | 
:ENT_TIMESTAMP
 updated_at            | timestamp without time zone |           | not null | CURRENT_TIMESTAMP
 source_id             | text                        |           |          | 
 address_id            | text                        |           |          | 
 initial_id            | text                        |           |          | 
 dino_started_at       | timestamp without time zone |           |          | 
 qwen_started_at       | timestamp without time zone |           |          | 
 legal_address         | text                        |           |          | 
 simple_address        | text                        |           |          | 
 client_normalized     | text                        |           |          | 
Indexes:
    "photos_pkey" PRIMARY KEY, btree (photo_id)
    "idx_photos_address" btree (address)
    "idx_photos_address_id" btree (address_id)
    "idx_photos_client" btree (client)
    "idx_photos_client_normalized" btree (client_normalized)
    "idx_photos_dino_fingerprint" btree (dino_fingerprint)
    "idx_photos_dino_processing" btree (dino_status, dino_started_at)
    "idx_photos_dino_queue" btree (dino_status, id)
    "idx_photos_hybrid_final" btree (hybrid_final_id)
    "idx_photos_initial_id" btree (initial_id)
:idx_photos_address_id" btree (address_id)
    "idx_photos_client" btree (client)
    "idx_photos_client_normalized" btree (client_normalized)
    "idx_photos_dino_fingerprint" btree (dino_fingerprint)
    "idx_photos_dino_processing" btree (dino_status, dino_started_at)
    "idx_photos_dino_queue" btree (dino_status, id)
    "idx_photos_hybrid_final" btree (hybrid_final_id)
    "idx_photos_initial_id" btree (initial_id)
    "idx_photos_preview_queue" btree (preview_status, id)
    "idx_photos_qwen_processing" btree (qwen_status, qwen_started_at)
    "idx_photos_qwen_queue" btree (qwen_status, id)
    "idx_photos_sort_queue" btree (sort_status, id)
    "idx_photos_source_id" btree (source_id)
    "idx_photos_status" btree (status)
    "photos_id_key" UNIQUE CONSTRAINT, btree (id)
    "ux_photos_source_path" UNIQUE, btree (source_path)

---

### 🤖 **Assistant** — 2026-08-21 01:11:03

Да, всё необходимое в `photos` уже есть. Причём есть и индекс `idx_photos_hybrid_final`.

Сейчас картина такая:

```text
DINO recognition
      │
      ▼
dino_fingerprint
      │
      ▼
Hybrid v12
      │
      ▼
best_id
      │
      ├── сейчас → только результат run_hybrid_v12.py
      │
      └── НУЖНО → photos.hybrid_final_id
                         │
                         ▼
                   WEB PHOTO INDEX
                         │
                         ▼
                    виртуальный адрес
```

### Важный момент

`run_hybrid_v12.py` **сейчас вообще не работает с PostgreSQL**. Мы это уже подтвердили:

```text
HYBRID DB / SAVE
403: Copy photos according to FINAL Hybrid best_id.
```

То есть:

- `hybrid_final_id` в БД существует;
- но `run_hybrid_v12.py` его не заполняет;
- `photos.py` его сейчас тоже не читает;
- поэтому UI продолжает показывать адрес из `dino_fingerprint`.

И это хорошо объясняет текущее состояние БД:

```text
dino_fingerprint | hybrid_original_id | hybrid_final_id | hybrid_changed
78_v33           |                    |                 | f
79_v33           |                    |                 | f
...
```

### Как я предлагаю сделать

**Не меняем frozen Hybrid v12.**

Добавляем только DB persistence после расчёта Hybrid:

```text
best_id
   ↓
hybrid_final_id
```

И одновременно:

```text
original_best_id → hybrid_original_id
hybrid_changed   → hybrid_changed
hybrid_old_score → hybrid_old_score
hybrid_score     → hybrid_score
hybrid_margin    → hybrid_margin
hybrid_neighbors → hybrid_neighbors
```

А в `photos.py` меняем источник виртуального адреса:

```python
hybrid_final_id
    ↓ если есть
нормализовать "_v33"
    ↓
address
```

Если `hybrid_final_id` пуст:

```python
dino_fingerprint
    ↓
fallback
```

`address_fingerprints` при этом **вообще не трогаем**.

---

Но перед изменением я хочу проверить ещё одну вещь: **как именно `run_hybrid_v12.py` получает входные `rows` и какой формат `file` там используется**, чтобы DB-save привязать к существующей записи `photos` надёжно, лучше всего по `source_path`, а не по имени файла.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID 500-760 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '500,760p'
```

После этого уже можно будет сделать точечный патч без риска сломать сортировку.

---

### 👤 **User** — 2026-08-21 01:12:36

гибрид вполне возможно работаетс с дино фингерпринт - который сохраняется в базу специально для этого и нужен для возможного пересчета alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID 500-760 ================" && \
nl -ba scripts/run_hybrid_v12.py | sed -n '500,760p'
================ HYBRID 500-760 ================
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
   741	    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:12:37

Да. Теперь видно точнее — **ты прав**: `dino_fingerprint` не является конкурирующим источником для Hybrid. Он является **результатом первичного DINO-распознавания**, который Hybrid использует как вход для пересчёта.

Логика сейчас такая:

```text
                    ФОТО
                      │
                      ▼
                DINO v33
                      │
                      ▼
              dino_fingerprint
              dino_score
              dino_second_score
              dino_margin
                      │
                      ▼
                 HYBRID v12
              ┌───────┴────────┐
              │                │
        TOP-5 DINO       subfingerprints
              │                │
              └───────┬────────┘
                      │
                + соседние фото
                      │
                      ▼
                   best_id
                      │
                      ▼
              hybrid_final_id
                      │
                      ▼
                ВИРТУАЛЬНЫЙ
                   АДРЕС
```

### Что это означает для нашей задачи

`dino_fingerprint` **оставляем как есть**.

Он нужен для:

- исходного результата DINO;
- повторного запуска Hybrid;
- диагностики;
- сравнения `original → final`;
- возможности впоследствии пересчитать Hybrid без потери исходного DINO результата.

А вот для **отображения фотографии в Web UI** используем:

```text
hybrid_final_id
```

и только если он отсутствует — разумный fallback на `dino_fingerprint`.

---

### И ещё важная вещь

Из показанного `run_hybrid_v12.py` видно, что Hybrid **не пересчитывает DINO**.

Он получает:

```python
recognition = run_recognition(...)
```

затем:

```python
recognition = adapt_recognizer_rows(recognition)
```

и передаёт эти данные в:

```python
hybrid_v12(
    recognition,
    embedder,
    subs,
)
```

То есть:

```text
DINO → recognition
          ↓
      top1/top2/top3/top4/top5
          ↓
       Hybrid
```

А `embedder` внутри Hybrid используется **только для border cases**:

```python
if margin < MARGIN_LIMIT:
```

То есть это не новый глобальный DINO fingerprint, а дополнительное сравнение с subfingerprints для пограничных случаев.

---

## Сейчас обнаружилась настоящая проблема

В `run_hybrid_v12.py` есть:

```python
result["original_best_id"] = old
result["best_id"] = best
result["hybrid_changed"] = hybrid_changed
result["hybrid_old_score"] = old_score
result["hybrid_score"] = new_score
result["hybrid_margin"] = margin
result["hybrid_neighbors"] = dict(neighbors)
```

Но затем эти результаты **только пишутся в JSON и используются для копирования**.

В PostgreSQL они не записываются.

Поэтому БД сейчас содержит:

```text
dino_fingerprint = 78_v33
hybrid_final_id  = NULL
```

несмотря на то, что Hybrid мог реально получить:

```text
old  = 78_v33
best = 83_v33
```

---

# Поэтому архитектурно правильно сделать так

### 1. DINO поля — не трогаем

```text
dino_fingerprint
dino_score
dino_second_score
dino_margin
```

Это **первичный результат распознавания**.

### 2. Hybrid поля — результат второго этапа

```text
hybrid_original_id
hybrid_final_id
hybrid_changed
hybrid_old_score
hybrid_score
hybrid_margin
hybrid_neighbors
```

Причём:

```text
hybrid_original_id = DINO top1
hybrid_final_id    = окончательный best_id
```

### 3. Web UI

`photos.py` должен строить виртуальный адрес так:

```text
hybrid_final_id
       ↓
если пуст → dino_fingerprint
       ↓
нормализация
78_v33 → 78
83_v33 → 83
```

Именно это теперь соответствует архитектуре проекта.

---

## Но есть ещё один принципиальный вопрос

Мы пока **не должны просто дописывать сохранение в `run_hybrid_v12.py`**, пока не определим, каким образом текущие строки Hybrid однозначно сопоставляются с PostgreSQL.

Потому что:

```python
row["file"]
```

может быть:

```text
/home/.../какой-то-файл.jpg
```

а в БД есть одновременно:

```text
source_path
path
filename
photo_id
```

При этом `source_path` имеет:

```text
UNIQUE CONSTRAINT
ux_photos_source_path
```

Это практически идеальный ключ для обратной записи.

То есть наиболее безопасная схема:

```text
Hybrid row["file"]
       ↓
нормализованный absolute path
       ↓
photos.source_path
       ↓
UPDATE photos
SET
    hybrid_original_id = ...,
    hybrid_final_id = ...,
    ...
WHERE source_path = ...
```

**Не по filename. Не по адресу. Не по `photo_id`.**

---

И ещё: `address_fingerprints` действительно **не нужно подключать к этому этапу**.

Сейчас у нас две разные сущности:

```text
Hybrid:
"какому fingerprint принадлежит конкретная фотография?"
        ↓
hybrid_final_id
```

и

```text
address_fingerprints:
"какой fingerprint связан с каким адресом?"
        ↓
fingerprint_id → address_id
```

Второе пока не участвует в отображении.

То есть следующим шагом я бы сделал **не изменение логики Hybrid**, а отдельный аккуратный DB-save этап:

```text
hybrid_rows
      ↓
PostgreSQL photos
      ↓
hybrid_* поля
```

После этого уже поменяем `photos.py`, чтобы грид читал `hybrid_final_id`.

И это даст нам именно ту модель, которую ты описал: **DINO остаётся исходным результатом и базой для возможного пересчёта, Hybrid становится финальным результатом сортировки/назначения.**

---

### 👤 **User** — 2026-08-21 01:13:37

далее

---

### 🤖 **Assistant** — 2026-08-21 01:13:39

Да. Идём дальше **без изменения алгоритма Hybrid**.

Сейчас следующий шаг — проверить, как именно `source_path` выглядит в БД и как `row["file"]` выглядит в `hybrid_v12.json`. Это нужно перед записью `hybrid_final_id`, чтобы не сделать неправильный `UPDATE`.

Выполни одним блоком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DB SOURCE PATH ================" && \
psql -h localhost -U lora -d photobase -c "
SELECT
    photo_id,
    source_path,
    path,
    filename,
    dino_fingerprint,
    hybrid_final_id
FROM photos
ORDER BY id
LIMIT 10;
" && \
echo && \
echo "================ HYBRID JSON SAMPLE ================" && \
find data -type f -name "hybrid_v12.json" -print | head -10
```

Если `hybrid_v12.json` найдётся, сразу вторым блоком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python - <<'PY'
import json
from pathlib import Path

files = list(Path("data").rglob("hybrid_v12.json"))

if not files:
    print("HYBRID JSON NOT FOUND")
    raise SystemExit

f = files[0]
print("FILE:", f)

data = json.loads(f.read_text(encoding="utf-8"))

print("ROWS:", len(data))

for row in data[:3]:
    print()
    print("file:", row.get("file"))
    print("original_best_id:", row.get("original_best_id"))
    print("best_id:", row.get("best_id"))
    print("hybrid_changed:", row.get("hybrid_changed"))
    print("hybrid_old_score:", row.get("hybrid_old_score"))
    print("hybrid_score:", row.get("hybrid_score"))
    print("hybrid_margin:", row.get("hybrid_margin"))
    print("hybrid_neighbors:", row.get("hybrid_neighbors"))
PY
```

После этого уже можно будет точно определить **ключ связи Hybrid → `photos`** и написать минимальный патч, не затрагивая сам Hybrid v12.

---

### 👤 **User** — 2026-08-21 01:14:15

PH_00000001 | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Screenshot from 2026-08-16 00-38-11.png | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Screenshot from 2026-08-16 00-38-11.png | Screenshot from 2026-08-16 00-38-11.png |                  | 
 PH_00000002 | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_01.JPG                      | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_01.JPG                      | Ашхабадский_01.JPG                      | 85_v33           | 
 PH_00000003 | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_02.JPG                      | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_02.JPG                      | Ашхабадский_02.JPG                      | 85_v33           | 
 PH_00000004 | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_03.JPG                      | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_03.JPG                      | Ашхабадск:alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
python - <<'PY'
import json
from pathlib import Path

files = list(Path("data").rglob("hybrid_v12.json"))

if not files:
    print("HYBRID JSON NOT FOUND")
    raise SystemExit

f = files[0]
print("FILE:", f)

data = json.loads(f.read_text(encoding="utf-8"))

print("ROWS:", len(data))

for row in data[:3]:
    print()
    print("file:", row.get("file"))
    print("original_best_id:", row.get("original_best_id"))
    print("best_id:", row.get("best_id"))
    print("hybrid_changed:", row.get("hybrid_changed"))
PY  print("hybrid_neighbors:", row.get("hybrid_neighbors"))
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:14:16

Да, первый вывод уже подтверждает главное: **`source_path` в `photos` — абсолютный путь**, и это позволяет безопасно связывать результат Hybrid с конкретной фотографией.

Ошибка второго блока только в том, что в системе нет команды `python`; у проекта есть `uv`, поэтому используем `uv run python`.

Выполни только это:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import json
from pathlib import Path

files = list(Path("data").rglob("hybrid_v12.json"))

if not files:
    print("HYBRID JSON NOT FOUND")
    raise SystemExit

f = files[0]
print("FILE:", f)

data = json.loads(f.read_text(encoding="utf-8"))

print("ROWS:", len(data))

for row in data[:5]:
    print()
    print("file:", row.get("file"))
    print("original_best_id:", row.get("original_best_id"))
    print("best_id:", row.get("best_id"))
    print("hybrid_changed:", row.get("hybrid_changed"))
    print("hybrid_old_score:", row.get("hybrid_old_score"))
    print("hybrid_score:", row.get("hybrid_score"))
    print("hybrid_margin:", row.get("hybrid_margin"))
    print("hybrid_neighbors:", row.get("hybrid_neighbors"))
PY
```

Нам особенно нужны три вещи:

```text
file
original_best_id
best_id
```

Если они соответствуют:

```text
photos.source_path
        ↓
row["file"]

dino_fingerprint
        ↓
original_best_id

hybrid_final_id
        ↓
best_id
```

то дальше можно сделать **отдельный DB-save**, не вмешиваясь в алгоритм Hybrid вообще.

И после этого уже исправим `build_photo_index()`:

```text
hybrid_final_id
      ↓
нормализация "_v33"
      ↓
виртуальный адрес
```

а `dino_fingerprint` останется сохранённым как исходный DINO-результат для будущего пересчёта.

---

### 👤 **User** — 2026-08-21 01:14:30

data = json.loads(f.read_text(encoding="utf-8"))

print("ROWS:", len(data))

for row in data[:5]:
    print()
    print("file:", row.get("file"))
    print("original_best_id:", row.get("original_best_id"))
    print("best_id:", row.get("best_id"))
PY  print("hybrid_neighbors:", row.get("hybrid_neighbors"))
FILE: data/output/test_hybrid_v12/hybrid_v12.json
ROWS: 257

file: data/input/test/Screenshot from 2026-08-16 00-38-11.png
original_best_id: 89_v33
best_id: 89_v33
hybrid_changed: False
hybrid_old_score: 4.969404840469361
hybrid_score: 4.969404840469361
hybrid_margin: 0.0732943737506867
hybrid_neighbors: {}

file: data/input/test/Ашхабадский_01.JPG
original_best_id: 85_v33
best_id: 85_v33
hybrid_changed: False
hybrid_old_score: 9.000321114063263
hybrid_score: 9.000321114063263
hybrid_margin: 0.06387112975120546
hybrid_neighbors: {}

file: data/input/test/Ашхабадский_02.JPG
original_best_id: 85_v33
best_id: 85_v33
hybrid_changed: False
hybrid_old_score: 12.33634147644043
hybrid_score: 12.33634147644043
hybrid_margin: 0.0723714679479599
hybrid_neighbors: {'85_v33': 1}

file: data/input/test/Ашхабадский_03.JPG
original_best_id: 85_v33
best_id: 85_v33
hybrid_changed: False
hybrid_old_score: 12.149948912858964
hybrid_score: 12.149948912858964
hybrid_margin: 0.06999923229217542
hybrid_neighbors: {'85_v33': 1}

file: data/input/test/Ашхабадский_04.JPG
original_best_id: 85_v33
best_id: 85_v33
hybrid_changed: False
hybrid_old_score: 11.131822419166564
hybrid_score: 11.131822419166564
hybrid_margin: 0.06251606285572042
hybrid_neighbors: {'85_v33': 1}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:14:33

Отлично. Теперь цепочка подтверждена полностью.

### Что имеем

В Hybrid:

```text
file
  ↓
original_best_id = результат DINO TOP-1
  ↓
Hybrid v12
  ↓
best_id = окончательный результат Hybrid
```

Например:

```text
Ашхабадский_02.JPG
DINO:   85_v33
Hybrid: 85_v33
```

А если Hybrid действительно исправляет результат, будет:

```text
DINO:   89_v33
Hybrid: 85_v33
```

Именно `best_id` должен становиться `hybrid_final_id`.

---

### Но есть важный момент

Этот конкретный JSON:

```text
data/output/test_hybrid_v12/hybrid_v12.json
```

содержит:

```text
257 rows
```

и относится к:

```text
data/input/test/
```

а PostgreSQL сейчас содержит фотографии из:

```text
data/input/daily/
```

Поэтому **этот JSON сейчас нельзя заливать в `photos`** — пути не совпадают с текущими `source_path`.

Это хорошо, что мы это обнаружили до записи.

---

## Что нужно сделать дальше

Нам надо найти, **как именно сейчас запускается Hybrid для `daily`** и куда он пишет свой `hybrid_v12.json`.

Покажи:

```bash id="w1w3ak"
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID DAILY REFERENCES ================" && \
grep -RniE \
'run_hybrid_v12|test_hybrid_v12|input/daily|hybrid_v12.json|output/daily' \
scripts app \
--include="*.py" \
--include="*.sh" \
| head -300
```

После этого мы определим правильную точку:

```text
daily
  ↓
DINO
  ↓
Hybrid
  ↓
hybrid_v12.json
  ↓
PostgreSQL photos
```

И **только после этого** внесём сохранение `hybrid_final_id`.

`address_fingerprints` пока вообще не трогаем.

---

### 👤 **User** — 2026-08-21 01:14:58

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID DAILY REFERENCES ================" && \
grep -RniE \
'run_hybrid_v12|test_hybrid_v12|input/daily|hybrid_v12.json|output/daily' \
scripts app \
--include="*.py" \
--include="*.sh" \
| head -300
================ HYBRID DAILY REFERENCES ================
scripts/run_daily_hybrid_v12.sh:7:INPUT="$PROJECT/data/input/daily"
scripts/run_daily_hybrid_v12.sh:11:OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"
scripts/run_daily_hybrid_v12.sh:42:/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
scripts/run_hybrid_v12.py:656:        output_dir / "hybrid_v12.json"
app/web/components/addresses.py:28:    # а не физические папки output/daily.
app/web/components/photos.py:293:    # Никакого output/daily.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-21 01:15:00

Да, теперь картина полная.

`run_daily_hybrid_v12.sh` — это **реальный production-запуск Hybrid для `daily`**. Значит, нам не нужно менять сам `run_hybrid_v12.py` для определения результата. Нужно правильно встроить **сохранение результата в PostgreSQL после Hybrid**.

Покажи его целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DAILY HYBRID SCRIPT ================" && \
nl -ba scripts/run_daily_hybrid_v12.sh | sed -n '1,180p'
```

И одновременно покажи, **кто сейчас запускает этот shell-скрипт**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DAILY HYBRID CALLERS ================" && \
grep -RniE \
'run_daily_hybrid_v12\.sh|run_daily_hybrid' \
scripts app \
--include="*.py" \
--include="*.sh" \
| head -200
```

### Почему это следующий шаг

Сейчас цепочка уже доказана:

```text
data/input/daily
        │
        ▼
run_daily_hybrid_v12.sh
        │
        ▼
run_hybrid_v12.py
        │
        ├── DINO v33
        │      ↓
        │   original_best_id
        │
        ├── Hybrid v12
        │      ↓
        │   best_id
        │
        └── hybrid_v12.json
```

Нам нужно добавить сохранение:

```text
best_id
   ↓
photos.hybrid_final_id
```

и:

```text
original_best_id
   ↓
photos.hybrid_original_id
```

плюс остальные поля Hybrid.

При этом **файлы физически никуда копировать для Web UI не надо**. Текущая архитектура уже специально перешла на виртуальную сортировку:

```text
source_path = физическое фото
hybrid_final_id = виртуальный адрес
```

И это как раз то, что нам нужно.

После вывода двух команд я предложу **минимальный патч именно в существующий production-поток**, без изменения frozen Hybrid v12.

---

