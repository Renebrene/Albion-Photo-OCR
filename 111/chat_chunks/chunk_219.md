## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-20 23:43:55

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba app/core/recognizer.py | sed -n '350,560p'
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
   484	    def recognize_one(
   485	        self,
   486	        path,
   487	        top_k=5,
   488	        threshold=0.65,
   489	        fingerprints=None,
   490	    ):
   491	        """
   492	        Recognize ONE image using the same v3.3 compact
   493	        recognition logic as recognize_folder().
   494	
   495	        Intended for queue/worker processing.
   496	
   497	        Returns the same result structure as one item
   498	        returned by recognize_folder().
   499	        """
   500	        path = Path(path)
   501	
   502	        if not path.exists():
   503	            raise FileNotFoundError(path)
   504	
   505	        # -------------------------------------------------
   506	        # LOAD COMPATIBLE FINGERPRINTS
   507	        # -------------------------------------------------
   508	
   509	        allowed_fingerprints = None
   510	
   511	        if fingerprints is not None:
   512	            allowed_fingerprints = {
   513	                str(item).strip()
   514	                for item in fingerprints
   515	                if str(item).strip()
   516	            }
   517	
   518	        loaded_fingerprints = []
   519	
   520	        for metadata in self.manager.list_fingerprints():
   521	            fingerprint_id = metadata.get("id")
   522	
   523	            if not fingerprint_id:
   524	                continue
   525	
   526	            if (
   527	                allowed_fingerprints is not None
   528	                and str(fingerprint_id)
   529	                not in allowed_fingerprints
   530	            ):
   531	                continue
   532	
   533	            try:
   534	                data = self.manager.load(
   535	                    fingerprint_id
   536	                )
   537	
   538	            except (
   539	                FileNotFoundError,
   540	                ValueError,
   541	                OSError,
   542	            ) as exc:
   543	                print(
   544	                    f"[Recognizer] SKIP "
   545	                    f"{fingerprint_id}: {exc}"
   546	                )
   547	                continue
   548	
   549	            if str(
   550	                data["metadata"].get(
   551	                    "version",
   552	                    "",
   553	                )
   554	            ) != self.VERSION:
   555	                continue
   556	
   557	            loaded_fingerprints.append(
   558	                (
   559	                    fingerprint_id,
   560	                    data,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:43:57

Да. Теперь видно, что здесь происходит.

**Ключевой момент:** текущий DINO действительно сначала строит **TOP-5**, но `run_hybrid_v12.py` использует эти пять кандидатов не совсем так, как можно ожидать.

Цепочка сейчас такая:

```text
Фото
  ↓
DINO v33
  ↓
полный список fingerprint'ов 78–95
  ↓
ranked.sort()
  ↓
TOP-5
  ↓
┌───────────────────────────────┐
│ Hybrid v12                    │
│                               │
│ 1. TOP-5 global score × 10    │
│                               │
│ 2. если margin < 0.02:        │
│    TOP1 + TOP2 → sub          │
│                               │
│ 3. соседние фото:             │
│    left TOP1 == right TOP1    │
│    → +3.0                     │
│                               │
│ 4. выбрать победителя         │
└───────────────────────────────┘
  ↓
FINAL best_id
  ↓
сортировка
```

И вот здесь есть очень важная деталь.

### 1. DINO уже делает всю основную работу

В `recognizer.py`:

```python
ranked.sort(
    key=lambda item: item["score"],
    reverse=True,
)

ranked = ranked[:max(1, int(top_k))]
```

При `--top-k 5` Hybrid получает именно:

```text
top1
top2
top3
top4
top5
```

Причём каждый кандидат уже содержит:

- `score`
- `global`
- `environment`
- `color`
- `spatial`
- `best_image`
- `best_image_score`

То есть Hybrid **не пересчитывает обычный DINO/v33 score для всех адресов**.

---

## 2. Что реально делает Hybrid с TOP-5

Вот эта часть:

```python
for k in range(1, 6):

    fp = row.get(f"top{k}")
    sc = row.get(f"top{k}_score")

    if fp:
        scores[fp] += (
            float(sc)
            * GLOBAL_WEIGHT
        )
```

При:

```python
GLOBAL_WEIGHT = 10.0
```

получается:

```text
TOP1 score × 10
TOP2 score × 10
TOP3 score × 10
TOP4 score × 10
TOP5 score × 10
```

То есть **все пять кандидатов участвуют в итоговом голосовании**.

Это важно: TOP-3/TOP-4/TOP-5 не выбрасываются.

---

# 3. Но SUB-механизм работает только для TOP1 и TOP2

Вот это:

```python
if margin < MARGIN_LIMIT:
```

где:

```python
MARGIN_LIMIT = 0.02
```

То есть только если:

```text
TOP1 - TOP2 < 0.02
```

тогда запускается дополнительный механизм.

И дальше:

```python
candidates = [
    row.get("top1"),
    row.get("top2"),
]
```

То есть **SUB вообще не проверяет TOP3, TOP4, TOP5**.

Получается:

```text
TOP1 ─┐
      ├── SUB
TOP2 ─┘

TOP3 ── не участвует в SUB
TOP4 ── не участвует в SUB
TOP5 ── не участвует в SUB
```

---

# 4. SUB действительно запускает отдельный DINO-проход

Вот это особенно интересно:

```python
query = embedder.embed_paths(
    [image]
)[0]
```

То есть для пограничного изображения Hybrid **ещё раз получает embedding изображения**.

Затем:

```python
for parent in candidates:
```

для TOP1 и TOP2.

И:

```python
for sub_id, sub_emb in subs.items():

    if not sub_id.startswith(parent):
        continue

    sim = max(
        sub_emb @ query
    )
```

То есть для каждого из двух родителей ищутся его subfingerprints.

Условно:

```text
TOP1 = 82_v33

82_xxx
82_xxx
82_xxx
...

TOP2 = 85_v33

85_xxx
85_xxx
85_xxx
...
```

И фотография сравнивается с этими subfingerprints.

---

# 5. А потом подключается соседний механизм

Вот это уже третий источник информации:

```python
left_fp = rows[i - 1].get("top1")
right_fp = rows[i + 1].get("top1")
```

и:

```python
if (
    left_fp
    and right_fp
    and left_fp == right_fp
):
    scores[left_fp] += 3.0
```

То есть если последовательность такая:

```text
фото 101 → 82
фото 102 → 85
фото 103 → 82
```

для фотографии 102:

```text
левый сосед  = 82
правый сосед = 82
```

значит:

```text
82 получает +3
```

И это **может изменить результат**.

---

# 6. Поэтому твоя фраза «гибрид запускает весь механизм» — абсолютно по делу

Фактически Hybrid v12 использует **три независимых источника информации**:

### A. DINO TOP-5

```text
TOP1
TOP2
TOP3
TOP4
TOP5
```

с весом:

```text
×10
```

### B. Subfingerprint

Только для:

```text
margin < 0.02
```

и только:

```text
TOP1
TOP2
```

### C. Соседи

Если:

```text
previous TOP1 == next TOP1
```

то:

```text
+3
```

---

# 7. Но я вижу один очень интересный недостаток

Сейчас Hybrid фактически **не может выбрать адрес, которого нет в TOP-5 DINO**.

Потому что `scores` первоначально создаётся только из:

```python
top1
top2
top3
top4
top5
```

А SUB добавляет баллы только:

```python
scores[parent]
```

где `parent` тоже:

```text
TOP1 / TOP2
```

А сосед добавляет:

```python
scores[left_fp]
```

где `left_fp` — TOP1 соседнего изображения.

То есть если DINO выдал:

```text
TOP-5:

85  0.881
82  0.879
91  0.861
78  0.850
93  0.841
```

Hybrid может усилить:

```text
85
82
91
78
93
```

но **не сможет внезапно открыть 88**, если 88 вообще не попал в TOP-5.

Это принципиальное ограничение текущей архитектуры.

---

# 8. И ещё важнее: TOP-5 здесь не «пять независимых механизмов»

Сейчас это:

```text
DINO
 ↓
TOP-5
 ↓
Hybrid
```

а не:

```text
DINO TOP-5
 ↓
для каждого из 5
 ↓
полный повторный анализ
 ↓
выбор
```

То есть Hybrid работает **поверх уже сокращённого пространства кандидатов**.

---

## Что я предлагаю изучить дальше

Не менять код пока вообще.

Я бы сейчас посмотрел **конкретный реальный JSON одной фотографии**, где DINO дал 5 кандидатов, и вручную восстановил для неё весь Hybrid:

```text
DINO:

82  0.xxx
85  0.xxx
91  0.xxx
78  0.xxx
93  0.xxx

↓

GLOBAL ×10

↓

margin

↓

если margin < 0.02:
    SUB TOP1
    SUB TOP2

↓

соседи

↓

+3

↓

финальные scores

↓

best_id
```

И тогда станет совершенно прозрачно, **почему Hybrid оставляет TOP1 или почему переключает его на TOP2/TOP3/соседа**.

Для этого следующим шагом нам нужен **один конкретный результат `recognition.json` + `hybrid_v12.json`**, желательно с фотографией, где `hybrid_changed = true`. Тогда разберём один случай буквально по цифрам.

---

### 👤 **User** — 2026-08-20 23:45:36

гибрид в12 - отточенный механизм, от него требуется только вывод

---

### 🤖 **Assistant** — 2026-08-20 23:45:37

Да. Тогда фиксируем это как принцип архитектуры.

**Hybrid v12 не трогаем вообще.** Это эталонный, уже отточенный механизм принятия решения.

От него требуется только:

```text
DINO → TOP-5
        ↓
   Hybrid v12
        ↓
    FINAL RESULT
```

То есть задача сейчас **не улучшать Hybrid**, не менять веса, пороги, SUB или соседей.

### Что нам нужно сделать

Нужно перенести в текущий DB-пайплайн **полный вход Hybrid v12 и его выход**.

Сейчас проблема только в том, что `dino_worker.py` сохраняет:

```text
dino_fingerprint
dino_score
dino_second_score
dino_margin
```

а для запуска старого Hybrid нужны как минимум:

```text
TOP1
TOP2
TOP3
TOP4
TOP5
```

Причём лучше не пересобирать их из БД, а **сразу после DINO получить полноценный результат `recognize_one()`**, потому что он уже возвращает:

```python
"candidates": ranked
```

где `ranked` содержит реальные TOP-5.

Дальше эти данные передаются в **тот же самый `hybrid_v12()`**, который уже существует в `scripts/run_hybrid_v12.py`.

Получается правильная схема:

```text
                  ┌─────────────────┐
                  │   DINO v33      │
                  │                 │
                  │ TOP1 ... TOP5   │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   Hybrid v12    │
                  │                 │
                  │ НЕ МЕНЯЕМ       │
                  │ НЕ УЛУЧШАЕМ     │
                  │ НЕ ПЕРЕПИСЫВАЕМ│
                  └────────┬────────┘
                           │
                           ▼
                     final best_id
                           │
                           ▼
                       PostgreSQL
```

### И ещё один важный момент

В текущем `run_hybrid_v12.py` уже есть функция:

```python
hybrid_v12(
    recognition,
    embedder,
    subs,
)
```

Поэтому **не надо создавать новый `HybridWorker`, `Hybrid v13`, `Hybrid DB` и т. п.**

Нужно сделать тонкий адаптер:

```text
DB photo
   ↓
SceneRecognizer.recognize_one()
   ↓
TOP-5
   ↓
adapt_recognizer_rows()
   ↓
существующий hybrid_v12()
   ↓
final best_id
   ↓
DB
```

И тем самым **логика принятия решения останется ровно той, которая уже проверена на daily pipeline**.

---

Следующий шаг я бы сделал очень аккуратно: посмотреть **оставшуюся часть `recognize_one()`**, потому что сейчас мы видели только до строки 560. Нужно убедиться, что она действительно возвращает тот же `candidates`, что и `recognize_folder()`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba app/core/recognizer.py | sed -n '560,760p'
```

После этого уже можно будет спроектировать **минимальный вызов существующего Hybrid v12 без изменения самого Hybrid**.

---

### 👤 **User** — 2026-08-20 23:46:27

recognizer.py  - он же делает вывод?

---

### 🤖 **Assistant** — 2026-08-20 23:46:28

Да. **`recognizer.py` уже делает вывод DINO.** И это важно разделить.

Он делает:

```text
фото
 ↓
DINO v33
 ↓
сравнение со всеми fingerprint
 ↓
сортировка
 ↓
TOP-5
 ↓
результат
```

В частности, вот здесь:

```python
ranked.sort(
    key=lambda item: item["score"],
    reverse=True,
)

ranked = ranked[:max(1, int(top_k))]
```

После этого он формирует результат:

```python
{
    "file": str(path),
    "best_id": best_id,
    "score": best_score,
    "second_score": second_score,
    "margin": margin,
    "confidence": confidence,
    "status": status,
    "best_image": ...,
    "best_image_score": ...,
    "candidates": ranked,
}
```

То есть `recognizer.py` выдаёт **и TOP-1, и TOP-5**.

---

### А Hybrid v12 делает следующий уровень

`recognizer.py`:

```text
DINO
 ↓
TOP-5
 ↓
candidates
```

`run_hybrid_v12.py`:

```text
candidates
 ↓
GLOBAL
 ↓
SUB
 ↓
NEIGHBORS
 ↓
FINAL best_id
```

Поэтому если говорить именно о **выводе конечного адреса**, то:

- `recognizer.py` → **предварительный DINO-вывод**
- `Hybrid v12` → **окончательный вывод**

И вот это как раз нам нужно сохранить.

**Не надо заставлять `recognizer.py` самому делать Hybrid.** Он уже правильно выполняет свою роль: выдать кандидатов.

Наша задача — взять его `candidates` и **отдать их неизменённому Hybrid v12**, после чего записать `best_id`, который вернул Hybrid.

То есть:

```text
recognizer.py
     │
     │ candidates = TOP-5
     ▼
Hybrid v12
     │
     │ best_id
     ▼
PostgreSQL
```

Это наиболее чистый вариант.

---

### 👤 **User** — 2026-08-20 23:47:03

на этом и остановимся

---

### 🤖 **Assistant** — 2026-08-20 23:47:04

Да, останавливаемся на этом.

Зафиксировали архитектуру:

```text
DINO v33 / recognizer.py
        ↓
      TOP-5
        ↓
   Hybrid v12
        ↓
   окончательный ID
```

**`recognizer.py` не меняем.  
Hybrid v12 не меняем.**

Текущий DB-диагностический вывод показал только то, что в PostgreSQL пока сохраняется недостаточно данных для восстановления полного TOP-5 после факта. Это отдельная задача, к которой вернёмся позже.

---

### 👤 **User** — 2026-08-20 23:47:59

эта архитектура может брать из ПСКЛ фото_ид для работы и дописывать результат к текому же фото_ид

---

### 🤖 **Assistant** — 2026-08-20 23:48:00

Да. Именно так её и стоит строить.

```text
PostgreSQL
photos
   │
   ├── photo_id
   └── source_path
          │
          ▼
     DINO / recognizer.py
          │
          └── TOP-5
                 │
                 ▼
            Hybrid v12
                 │
                 └── final best_id
                        │
                        ▼
PostgreSQL
тот же photo_id
   ├── dino_...
   └── hybrid_...
```

То есть **`photo_id` остаётся главным ключом записи**. Никакого нового идентификатора фотографии создавать не нужно.

Например:

```text
PH_00000519
```

забирается из PostgreSQL → по `source_path` читается соответствующий файл → проходит:

```text
DINO → TOP-5 → Hybrid v12
```

и результат записывается обратно именно в:

```text
PH_00000519
```

Можно сохранять отдельно:

```text
dino_fingerprint
dino_score
dino_second_score
dino_margin

hybrid_original_id
hybrid_final_id
hybrid_changed
hybrid_old_score
hybrid_score
hybrid_margin
hybrid_neighbors
```

При этом **`photo_id` не меняется вообще**.

Это как раз хорошо ложится на уже существующий `dino_worker.py`: он умеет брать очередь из PostgreSQL и обновлять конкретную строку по `id`.

Главное — **не переносить логику Hybrid в `dino_worker.py`**. Worker должен быть оркестратором:

```text
ПСКЛ → фото → recognizer → TOP-5 → Hybrid v12 → ПСКЛ
```

а сам `Hybrid v12` остаётся единственным источником окончательного решения.

---

### 👤 **User** — 2026-08-20 23:48:51

что есть в дино воркере? он работает на цпу - я его переводил на цпу?

---

### 🤖 **Assistant** — 2026-08-20 23:48:52

Да, по показанному `dino_worker.py` видно, что **сам worker явно не переводит DINO на CPU**.

В нём есть:

```python
settings = Settings()
```

и затем:

```python
SceneEmbedder(settings)
```

То есть устройство берётся из `Settings`.

А в самом worker при старте оно только выводится:

```python
print("device  :", settings.device)
```

### Что это означает

Сейчас цепочка такая:

```text
dino_worker.py
    ↓
Settings()
    ↓
settings.device
    ↓
SceneEmbedder(settings)
    ↓
DINO
```

Поэтому по одному `dino_worker.py` **нельзя сказать, что DINO работает на CPU**.

И ещё важный момент: в worker есть:

```python
ThreadPoolExecutor
```

но это относится не к DINO, а к тому, что делает `SceneRecognizer` внутри своих CPU-дескрипторов. Сам DINO вызывается через:

```python
self.embedder.embed_paths(...)
```

### Проверим точно

Нужно посмотреть `Settings` и `SceneEmbedder`, потому что именно там определяется `cpu/cuda`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SETTINGS ================" && \
nl -ba app/core/config.py | sed -n '1,260p' && \
echo && \
echo "================ EMBEDDER ================" && \
nl -ba app/core/embedder.py | sed -n '1,320p'
```

По этим двум файлам я точно скажу, **на каком устройстве сейчас работает DINO worker и переводил ли ты его специально на CPU**.

---

### 👤 **User** — 2026-08-20 23:49:28

int_mvp_v02 && \
echo "================ SETTINGS ================" && \
nl -ba app/core/config.py | sed -n '1,260p' && \
echo && \
echo "================ EMBEDDER ================" && \
nl -ba app/core/embedder.py | sed -n '1,320p'
================ SETTINGS ================
     1	from dataclasses import dataclass
     2	from pathlib import Path
     3	import os
     4	import torch
     5	
     6	
     7	@dataclass(frozen=True)
     8	class Settings:
     9	    host: str = os.getenv("SCENE_HOST", "127.0.0.1")
    10	    port: int = int(os.getenv("SCENE_PORT", "8080"))
    11	    data_dir: Path = Path(os.getenv("SCENE_DATA", "data"))
    12	    model_name: str = os.getenv(
    13	        "SCENE_MODEL",
    14	        "facebook/dinov2-base"
    15	    )
    16	    device: str = os.getenv(
    17	        "SCENE_DEVICE",
    18	        "cuda" if torch.cuda.is_available() else "cpu"
    19	    )
    20	    batch_size: int = int(
    21	        os.getenv(
    22	            "SCENE_BATCH",
    23	            "16"
    24	        )
    25	    )
    26	
    27	    @property
    28	    def fingerprints_dir(self):
    29	        return Path(
    30	            os.getenv(
    31	                "SCENE_FINGERPRINTS",
    32	                str(self.data_dir / "fingerprints")
    33	            )
    34	        )
    35	
    36	
    37	settings = Settings()

================ EMBEDDER ================
     1	from __future__ import annotations
     2	
     3	import numpy as np
     4	import torch
     5	from PIL import Image
     6	from transformers import AutoImageProcessor, AutoModel
     7	
     8	
     9	class SceneEmbedder:
    10	    """DINOv2 ViT-B/14 global embedding service.
    11	
    12	    Uses Hugging Face Transformers instead of torch.hub.
    13	
    14	    Output:
    15	        global embedding: [N, 768]
    16	    """
    17	
    18	    def __init__(self, settings):
    19	        self.settings = settings
    20	        self.device = torch.device(settings.device)
    21	
    22	        print(f"[SceneEmbedder] device={self.device}")
    23	
    24	        if self.device.type == "cuda":
    25	            print(
    26	                f"[SceneEmbedder] GPU="
    27	                f"{torch.cuda.get_device_name(0)}"
    28	            )
    29	            print(
    30	                f"[SceneEmbedder] VRAM="
    31	                f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
    32	            )
    33	
    34	        self.model_name = settings.model_name
    35	
    36	        print(
    37	            f"[SceneEmbedder] Loading DINOv2: "
    38	            f"{self.model_name}"
    39	        )
    40	
    41	        self.processor = AutoImageProcessor.from_pretrained(
    42	            self.model_name
    43	        )
    44	
    45	        self.model = AutoModel.from_pretrained(
    46	            self.model_name
    47	        )
    48	
    49	        self.model = self.model.to(self.device)
    50	        self.model.eval()
    51	
    52	        self.dimension = 768
    53	
    54	        print(
    55	            f"[SceneEmbedder] embedding dimension="
    56	            f"{self.dimension}"
    57	        )
    58	        print(
    59	            "[SceneEmbedder] patch extraction=DISABLED "
    60	            "(compact)"
    61	        )
    62	        print("[SceneEmbedder] Ready.")
    63	
    64	    @torch.inference_mode()
    65	    def embed_images(
    66	        self,
    67	        images: list[Image.Image],
    68	        batch_size=None,
    69	    ):
    70	        batch_size = (
    71	            batch_size
    72	            or self.settings.batch_size
    73	        )
    74	
    75	        vectors = []
    76	
    77	        for i in range(
    78	            0,
    79	            len(images),
    80	            batch_size,
    81	        ):
    82	            batch_images = images[
    83	                i:i + batch_size
    84	            ]
    85	
    86	            inputs = self.processor(
    87	                images=batch_images,
    88	                return_tensors="pt",
    89	            )
    90	
    91	            inputs = {
    92	                key: value.to(
    93	                    self.device,
    94	                    non_blocking=True,
    95	                )
    96	                for key, value in inputs.items()
    97	            }
    98	
    99	            outputs = self.model(**inputs)
   100	
   101	            # DINOv2 CLS token.
   102	            features = outputs.last_hidden_state[:, 0, :]
   103	
   104	            features = torch.nn.functional.normalize(
   105	                features,
   106	                dim=1,
   107	            )
   108	
   109	            vectors.append(
   110	                features.float()
   111	                .cpu()
   112	                .numpy()
   113	            )
   114	
   115	        if not vectors:
   116	            return np.empty(
   117	                (0, self.dimension),
   118	                dtype=np.float32,
   119	            )
   120	
   121	        return np.concatenate(
   122	            vectors,
   123	            axis=0,
   124	        ).astype("float32")
   125	
   126	    def embed_paths(self, paths):
   127	        from .image import load_image
   128	
   129	        images = [
   130	            load_image(path)
   131	            for path in paths
   132	        ]
   133	
   134	        return self.embed_images(images)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:49:29

Нет — **по этому коду DINO worker сейчас не переведён на CPU принудительно**.

Наоборот, по умолчанию он работает на GPU, если CUDA доступна.

Вот ключевое место в `config.py`:

```python
device: str = os.getenv(
    "SCENE_DEVICE",
    "cuda" if torch.cuda.is_available() else "cpu"
)
```

То есть:

```text
SCENE_DEVICE задан → используется его значение
SCENE_DEVICE НЕ задан → CUDA есть → cuda
                         CUDA нет → cpu
```

А `embedder.py` реально переносит модель именно туда:

```python
self.device = torch.device(settings.device)

self.model = self.model.to(self.device)
```

И входные тензоры тоже туда:

```python
inputs = {
    key: value.to(self.device)
    for key, value in inputs.items()
}
```

### Значит сейчас

Если ты запускаешь обычным образом:

```bash
uv run ...
```

и CUDA доступна, то:

```text
DINO → RTX 3060
```

а не CPU.

---

### Откуда могло возникнуть ощущение, что worker CPU

В `recognizer.py` действительно есть CPU-часть:

```python
ThreadPoolExecutor(max_workers=worker_count)
```

Она рассчитывает:

```text
environment
color
spatial
```

и это отдельные CPU-дескрипторы.

Получается:

```text
                 DINO
                  │
                  ▼
              RTX 3060
                  │
                  ▼
        global embedding
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
 CPU descriptors       DINO score
 environment
 color
 spatial
        └─────────┬─────────┘
                  ▼
             v3.3 score
```

### И ещё важный момент

В `embed_images()` результат в конце действительно переносится обратно:

```python
features.float().cpu().numpy()
```

Но это **не означает, что DINO работает на CPU**.

Это означает:

```text
GPU вычисляет embedding
        ↓
готовый embedding
        ↓
переносится GPU → RAM
        ↓
NumPy
```

То есть вычисление DINO остаётся на GPU.

---

Если ты **раньше действительно переводил worker на CPU**, то это, скорее всего, было сделано через переменную окружения, например:

```bash
SCENE_DEVICE=cpu
```

или в `.env`/скрипте запуска.

Сам код `dino_worker.py` этого не делает.

И хорошая новость для нашей будущей схемы: **Hybrid v12 использует тот же `SceneEmbedder`, поэтому при обычном запуске он тоже будет использовать RTX 3060.**

---

### 👤 **User** — 2026-08-20 23:51:16

я делал гибрид и дино на ЦПУ, а квен параллельно на ГПУ. меня устраивает скорость гибрид цпу. кстати в старом интерфейсе в техническом разделе сть закладка и там описание запуска квен и дино - нужно изучить

---

### 🤖 **Assistant** — 2026-08-20 23:51:18

Да, тогда картина становится понятной: **ты сознательно разделял ресурсы**:

```text
CPU
 ├── DINO
 └── Hybrid v12

GPU
 └── Qwen
```

И если скорость DINO + Hybrid на CPU тебя устраивает, **ничего с этим пока не меняем**.

А вот старый интерфейс действительно стоит изучить — особенно техническую вкладку, потому что там, судя по твоему описанию, уже зафиксирована логика запуска и распределения ресурсов для **DINO / Hybrid / Qwen**.

Нам нужно найти в старом UI:

1. **как запускается DINO;**
2. **как задаётся `SCENE_DEVICE=cpu`;**
3. **как запускается Hybrid;**
4. **как Qwen получает GPU;**
5. **какие параметры/переменные передаются каждому процессу;**
6. главное — **не сломать уже работающую схему распределения CPU/GPU**.

Я бы сейчас **не менял ни одной строки**. Сначала найдём старую техническую вкладку и посмотрим, что там реально реализовано.

Если старый интерфейс — это текущий `app/main.py` или отдельный файл, дай мне вывод поиска по проекту:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ TECHNICAL / DINO / QWEN ================" && \
grep -RniE \
'техничес|technical|SCENE_DEVICE|SCENE_MODEL|qwen|ollama|dino_worker|hybrid|Qwen|DINO' \
app scripts \
--include="*.py" \
--include="*.sh" | head -n 300
```

По нему сначала найдём **старую вкладку и её обработчики**, а потом уже посмотрим конкретный код запуска.

---

### 👤 **User** — 2026-08-20 23:51:46

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ TECHNICAL / DINO / QWEN ================" && \
grep -RniE \
'техничес|technical|SCENE_DEVICE|SCENE_MODEL|qwen|ollama|dino_worker|hybrid|Qwen|DINO' \
app scripts \
--include="*.py" \
--include="*.sh" | head -n 300
================ TECHNICAL / DINO / QWEN ================
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:24:    DINO / fingerprint здесь НЕ используется.
app/web/components/search.py:59:            qwen_status,
app/web/components/search.py:60:            qwen_time_sec,
app/web/components/technical_modules/photo_processing.py:21:DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
app/web/components/technical_modules/photo_processing.py:22:QWEN_WORKER = PROJECT / "app" / "workers" / "qwen_worker.py"
app/web/components/technical_modules/photo_processing.py:45:    dino_process = None
app/web/components/technical_modules/photo_processing.py:46:    qwen_process = None
app/web/components/technical_modules/photo_processing.py:48:    dino_stopping = False
app/web/components/technical_modules/photo_processing.py:49:    qwen_stopping = False
app/web/components/technical_modules/photo_processing.py:144:        dino = data.get("dino", {})
app/web/components/technical_modules/photo_processing.py:145:        qwen = data.get("qwen", {})
app/web/components/technical_modules/photo_processing.py:148:        # DINO
app/web/components/technical_modules/photo_processing.py:151:        dino_done = int(dino.get("done", 0))
app/web/components/technical_modules/photo_processing.py:152:        dino_processing = int(
app/web/components/technical_modules/photo_processing.py:153:            dino.get("processing", 0)
app/web/components/technical_modules/photo_processing.py:155:        dino_pending = int(
app/web/components/technical_modules/photo_processing.py:156:            dino.get("pending", 0)
app/web/components/technical_modules/photo_processing.py:158:        dino_error = int(
app/web/components/technical_modules/photo_processing.py:159:            dino.get("error", 0)
app/web/components/technical_modules/photo_processing.py:162:        dino_finished = (
app/web/components/technical_modules/photo_processing.py:163:            dino_done + dino_error
app/web/components/technical_modules/photo_processing.py:166:        dino_progress = (
app/web/components/technical_modules/photo_processing.py:170:                    dino_finished
app/web/components/technical_modules/photo_processing.py:179:        dino_progress_bar.value = (
app/web/components/technical_modules/photo_processing.py:180:            dino_progress / 100
app/web/components/technical_modules/photo_processing.py:183:        dino_progress_label.text = (
app/web/components/technical_modules/photo_processing.py:184:            f"{dino_finished} / {total}"
app/web/components/technical_modules/photo_processing.py:187:        dino_done_label.text = str(
app/web/components/technical_modules/photo_processing.py:188:            dino_done
app/web/components/technical_modules/photo_processing.py:191:        dino_processing_label.text = str(
app/web/components/technical_modules/photo_processing.py:192:            dino_processing
app/web/components/technical_modules/photo_processing.py:195:        dino_pending_label.text = str(
app/web/components/technical_modules/photo_processing.py:196:            dino_pending
app/web/components/technical_modules/photo_processing.py:199:        dino_error_label.text = str(
app/web/components/technical_modules/photo_processing.py:200:            dino_error
app/web/components/technical_modules/photo_processing.py:204:        # QWEN
app/web/components/technical_modules/photo_processing.py:207:        qwen_done = int(qwen.get("done", 0))
app/web/components/technical_modules/photo_processing.py:208:        qwen_processing = int(
app/web/components/technical_modules/photo_processing.py:209:            qwen.get("processing", 0)
app/web/components/technical_modules/photo_processing.py:211:        qwen_pending = int(
app/web/components/technical_modules/photo_processing.py:212:            qwen.get("pending", 0)
app/web/components/technical_modules/photo_processing.py:214:        qwen_error = int(
app/web/components/technical_modules/photo_processing.py:215:            qwen.get("error", 0)
app/web/components/technical_modules/photo_processing.py:218:        qwen_finished = (
app/web/components/technical_modules/photo_processing.py:219:            qwen_done + qwen_error
app/web/components/technical_modules/photo_processing.py:222:        qwen_progress = (
app/web/components/technical_modules/photo_processing.py:226:                    qwen_finished
app/web/components/technical_modules/photo_processing.py:235:        qwen_progress_bar.value = (
app/web/components/technical_modules/photo_processing.py:236:            qwen_progress / 100
app/web/components/technical_modules/photo_processing.py:239:        qwen_progress_label.text = (
app/web/components/technical_modules/photo_processing.py:240:            f"{qwen_finished} / {total}"
app/web/components/technical_modules/photo_processing.py:243:        qwen_done_label.text = str(
app/web/components/technical_modules/photo_processing.py:244:            qwen_done
app/web/components/technical_modules/photo_processing.py:247:        qwen_processing_label.text = str(
app/web/components/technical_modules/photo_processing.py:248:            qwen_processing
app/web/components/technical_modules/photo_processing.py:251:        qwen_pending_label.text = str(
app/web/components/technical_modules/photo_processing.py:252:            qwen_pending
app/web/components/technical_modules/photo_processing.py:255:        qwen_error_label.text = str(
app/web/components/technical_modules/photo_processing.py:256:            qwen_error
app/web/components/technical_modules/photo_processing.py:263:        dino_running = process_running(
app/web/components/technical_modules/photo_processing.py:264:            dino_process
app/web/components/technical_modules/photo_processing.py:267:        qwen_running = process_running(
app/web/components/technical_modules/photo_processing.py:268:            qwen_process
app/web/components/technical_modules/photo_processing.py:279:            and not dino_running
app/web/components/technical_modules/photo_processing.py:280:            and not qwen_running
app/web/components/technical_modules/photo_processing.py:294:            dino_status_label,
app/web/components/technical_modules/photo_processing.py:295:            dino_running,
app/web/components/technical_modules/photo_processing.py:296:            dino_error > 0,
app/web/components/technical_modules/photo_processing.py:300:            qwen_status_label,
app/web/components/technical_modules/photo_processing.py:301:            qwen_running,
app/web/components/technical_modules/photo_processing.py:302:            qwen_error > 0,
app/web/components/technical_modules/photo_processing.py:309:        if dino_running or qwen_running:
app/web/components/technical_modules/photo_processing.py:316:        elif dino_error or qwen_error:
app/web/components/technical_modules/photo_processing.py:335:            dino_running
app/web/components/technical_modules/photo_processing.py:336:            or qwen_running
app/web/components/technical_modules/photo_processing.py:340:            dino_running
app/web/components/technical_modules/photo_processing.py:341:            or qwen_running
app/web/components/technical_modules/photo_processing.py:344:        dino_run_button.enabled = not (
app/web/components/technical_modules/photo_processing.py:345:            dino_running
app/web/components/technical_modules/photo_processing.py:348:        dino_stop_button.enabled = (
app/web/components/technical_modules/photo_processing.py:349:            dino_running
app/web/components/technical_modules/photo_processing.py:352:        qwen_run_button.enabled = not (
app/web/components/technical_modules/photo_processing.py:353:            qwen_running
app/web/components/technical_modules/photo_processing.py:356:        qwen_stop_button.enabled = (
app/web/components/technical_modules/photo_processing.py:357:            qwen_running
app/web/components/technical_modules/photo_processing.py:404:    # START DINO
app/web/components/technical_modules/photo_processing.py:407:    async def start_dino():
app/web/components/technical_modules/photo_processing.py:409:        nonlocal dino_process
app/web/components/technical_modules/photo_processing.py:410:        nonlocal dino_stopping
app/web/components/technical_modules/photo_processing.py:417:                "DINO нельзя запускать вручную в текущем режиме.",
app/web/components/technical_modules/photo_processing.py:423:        if process_running(dino_process):
app/web/components/technical_modules/photo_processing.py:436:        if not DINO_WORKER.exists():
app/web/components/technical_modules/photo_processing.py:439:                f"Не найден DINO worker: {DINO_WORKER}",
app/web/components/technical_modules/photo_processing.py:446:        dino_stopping = False
app/web/components/technical_modules/photo_processing.py:464:            dino_process = (
app/web/components/technical_modules/photo_processing.py:469:                    str(DINO_WORKER),
app/web/components/technical_modules/photo_processing.py:478:                f"[WEB] DINO START PID={dino_process.pid}",
app/web/components/technical_modules/photo_processing.py:484:                    dino_process,
app/web/components/technical_modules/photo_processing.py:485:                    "DINO",
app/web/components/technical_modules/photo_processing.py:490:                "DINO запущен",
app/web/components/technical_modules/photo_processing.py:497:            dino_process = None
app/web/components/technical_modules/photo_processing.py:500:                "[WEB] DINO START ERROR:",
app/web/components/technical_modules/photo_processing.py:506:                f"Ошибка запуска DINO: {exc}",
app/web/components/technical_modules/photo_processing.py:512:    # STOP DINO
app/web/components/technical_modules/photo_processing.py:515:    async def stop_dino():
app/web/components/technical_modules/photo_processing.py:517:        nonlocal dino_stopping
app/web/components/technical_modules/photo_processing.py:519:        if not process_running(dino_process):
app/web/components/technical_modules/photo_processing.py:522:        dino_stopping = True
app/web/components/technical_modules/photo_processing.py:526:            dino_process.terminate()
app/web/components/technical_modules/photo_processing.py:529:                "DINO останавливается",
app/web/components/technical_modules/photo_processing.py:540:                f"Ошибка остановки DINO: {exc}",
app/web/components/technical_modules/photo_processing.py:546:    # START QWEN
app/web/components/technical_modules/photo_processing.py:549:    async def start_qwen():
app/web/components/technical_modules/photo_processing.py:551:        nonlocal qwen_process
app/web/components/technical_modules/photo_processing.py:552:        nonlocal qwen_stopping
app/web/components/technical_modules/photo_processing.py:559:                "Qwen нельзя запускать вручную в текущем режиме.",
app/web/components/technical_modules/photo_processing.py:565:        if process_running(qwen_process):
app/web/components/technical_modules/photo_processing.py:578:        if not QWEN_WORKER.exists():
app/web/components/technical_modules/photo_processing.py:581:                f"Не найден Qwen worker: {QWEN_WORKER}",
app/web/components/technical_modules/photo_processing.py:588:        qwen_stopping = False
app/web/components/technical_modules/photo_processing.py:606:            qwen_process = (
app/web/components/technical_modules/photo_processing.py:611:                    str(QWEN_WORKER),
app/web/components/technical_modules/photo_processing.py:620:                f"[WEB] QWEN START PID={qwen_process.pid}",
app/web/components/technical_modules/photo_processing.py:626:                    qwen_process,
app/web/components/technical_modules/photo_processing.py:627:                    "QWEN",
app/web/components/technical_modules/photo_processing.py:632:                "Qwen запущен",
app/web/components/technical_modules/photo_processing.py:639:            qwen_process = None
app/web/components/technical_modules/photo_processing.py:642:                "[WEB] QWEN START ERROR:",
app/web/components/technical_modules/photo_processing.py:648:                f"Ошибка запуска Qwen: {exc}",
app/web/components/technical_modules/photo_processing.py:654:    # STOP QWEN
app/web/components/technical_modules/photo_processing.py:657:    async def stop_qwen():
app/web/components/technical_modules/photo_processing.py:659:        nonlocal qwen_stopping
app/web/components/technical_modules/photo_processing.py:661:        if not process_running(qwen_process):
app/web/components/technical_modules/photo_processing.py:664:        qwen_stopping = True
app/web/components/technical_modules/photo_processing.py:668:            qwen_process.terminate()
app/web/components/technical_modules/photo_processing.py:671:                "Qwen останавливается",
app/web/components/technical_modules/photo_processing.py:682:                f"Ошибка остановки Qwen: {exc}",
app/web/components/technical_modules/photo_processing.py:693:        await start_dino()
app/web/components/technical_modules/photo_processing.py:697:        await start_qwen()
app/web/components/technical_modules/photo_processing.py:706:            process_running(dino_process)
app/web/components/technical_modules/photo_processing.py:707:            or process_running(qwen_process)
app/web/components/technical_modules/photo_processing.py:716:            await stop_dino()
app/web/components/technical_modules/photo_processing.py:717:            await stop_qwen()
app/web/components/technical_modules/photo_processing.py:720:                "Остановка DINO и Qwen запрошена",
app/web/components/technical_modules/photo_processing.py:868:        # DINO
app/web/components/technical_modules/photo_processing.py:884:                    "DINO v33 / Hybrid v12"
app/web/components/technical_modules/photo_processing.py:889:                dino_status_label = ui.label(
app/web/components/technical_modules/photo_processing.py:899:                dino_run_button = ui.button(
app/web/components/technical_modules/photo_processing.py:901:                    on_click=start_dino,
app/web/components/technical_modules/photo_processing.py:906:                dino_stop_button = ui.button(
app/web/components/technical_modules/photo_processing.py:908:                    on_click=stop_dino,
app/web/components/technical_modules/photo_processing.py:917:            dino_progress_bar = ui.linear_progress(
app/web/components/technical_modules/photo_processing.py:925:            dino_progress_label = ui.label(
app/web/components/technical_modules/photo_processing.py:937:                dino_done_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:943:                dino_processing_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:949:                dino_pending_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:955:                dino_error_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:960:        # QWEN
app/web/components/technical_modules/photo_processing.py:976:                    "Qwen3-VL 4B"
app/web/components/technical_modules/photo_processing.py:981:                qwen_status_label = ui.label(
app/web/components/technical_modules/photo_processing.py:991:                qwen_run_button = ui.button(
app/web/components/technical_modules/photo_processing.py:993:                    on_click=start_qwen,
app/web/components/technical_modules/photo_processing.py:998:                qwen_stop_button = ui.button(
app/web/components/technical_modules/photo_processing.py:1000:                    on_click=stop_qwen,
app/web/components/technical_modules/photo_processing.py:1009:            qwen_progress_bar = ui.linear_progress(
app/web/components/technical_modules/photo_processing.py:1017:            qwen_progress_label = ui.label(
app/web/components/technical_modules/photo_processing.py:1029:                qwen_done_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:1035:                qwen_processing_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:1041:                qwen_pending_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:1047:                qwen_error_label = ui.label("0").classes(
app/web/components/technical_modules/photo_processing.py:1060:            "DINO и Qwen работают независимо. "
app/web/components/technical_modules/photo_processing.py:1071:    dino_stop_button.disable()
app/web/components/technical_modules/photo_processing.py:1072:    qwen_stop_button.disable()
app/web/components/technical_modules/fingerprints.py:17:            "Рабочая версия: DINO / v33"
app/web/components/technical_modules/data.py:13:QWEN_ROOT = PROJECT / "data" / "metadata" / "qwen4b"
app/web/components/technical_modules/data.py:78:def qwen_stats():
app/web/components/technical_modules/data.py:80:    Статистика Qwen3-VL 4B.
app/web/components/technical_modules/data.py:90:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/data.py:95:    if QWEN_ROOT.exists():
app/web/components/technical_modules/data.py:98:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/data.py:243:    qwen = qwen_stats()
app/web/components/technical_modules/data.py:298:        # DINO
app/web/components/technical_modules/data.py:308:                    "DINO v33"
app/web/components/technical_modules/data.py:327:        # HYBRID
app/web/components/technical_modules/data.py:337:                    "Hybrid v12"
app/web/components/technical_modules/data.py:368:        # QWEN
app/web/components/technical_modules/data.py:378:                    "Qwen3-VL 4B"
app/web/components/technical_modules/data.py:389:            qwen_color = (
app/web/components/technical_modules/data.py:391:                if qwen["status"] == "ГОТОВ"
app/web/components/technical_modules/data.py:396:                qwen["status"],
app/web/components/technical_modules/data.py:397:                color=qwen_color,
app/web/components/technical_modules/data.py:405:                f"Обработано: {qwen['photos']}"
app/web/components/technical_modules/data.py:409:                f"OK: {qwen['ok']}"
app/web/components/technical_modules/data.py:413:                f"Ошибок: {qwen['errors']}"
app/web/components/technical_modules/data.py:417:                f"Адресов: {qwen['addresses']}"
app/web/components/technical_modules/data.py:421:                f"Среднее время: {qwen['avg_time']:.2f} сек"
app/web/components/technical_modules/data.py:425:                f"Средняя уверенность: {qwen['avg_confidence']:.1f}%"
app/web/components/technical_modules/qwen.py:10:QWEN_ROOT = (
app/web/components/technical_modules/qwen.py:14:    / "qwen4b"
app/web/components/technical_modules/qwen.py:24:QWEN_SCRIPT = (
app/web/components/technical_modules/qwen.py:27:    / "qwen4b_output_v01.py"
app/web/components/technical_modules/qwen.py:35:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/qwen.py:40:    if QWEN_ROOT.exists():
app/web/components/technical_modules/qwen.py:44:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/qwen.py:57:def _load_qwen_status():
app/web/components/technical_modules/qwen.py:72:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:156:                "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:173:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:180:def _find_latest_hybrid():
app/web/components/technical_modules/qwen.py:200:def build_qwen():
app/web/components/technical_modules/qwen.py:205:            "QWEN3-VL 4B"
app/web/components/technical_modules/qwen.py:269:                "▶ Запустить Qwen",
app/web/components/technical_modules/qwen.py:275:                "■ Остановить Qwen",
app/web/components/technical_modules/qwen.py:294:    qwen_process = None
app/web/components/technical_modules/qwen.py:295:    qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:297:    async def stop_qwen():
app/web/components/technical_modules/qwen.py:298:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:299:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:301:        if qwen_process is None:
app/web/components/technical_modules/qwen.py:304:        qwen_stop_requested = True
app/web/components/technical_modules/qwen.py:307:            f"[QWEN MANUAL] STOP REQUESTED PID={qwen_process.pid}",
app/web/components/technical_modules/qwen.py:312:            qwen_process.terminate()
app/web/components/technical_modules/qwen.py:317:                f"[QWEN MANUAL] STOP FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:321:    async def run_qwen():
app/web/components/technical_modules/qwen.py:323:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:324:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:326:        print("[QWEN MANUAL] START", flush=True)
app/web/components/technical_modules/qwen.py:328:        qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:335:            if not QWEN_SCRIPT.exists():
app/web/components/technical_modules/qwen.py:338:                    f"[QWEN MANUAL] SCRIPT NOT FOUND: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:343:                    f"Не найден Qwen script: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:350:            result_dir = _find_latest_hybrid()
app/web/components/technical_modules/qwen.py:355:                    "[QWEN MANUAL] HYBRID RUN NOT FOUND",
app/web/components/technical_modules/qwen.py:360:                    "Не найден ни один запуск Hybrid.",
app/web/components/technical_modules/qwen.py:382:                    f"[QWEN MANUAL] NO IMAGES: {result_dir}",
app/web/components/technical_modules/qwen.py:387:                    f"В последнем Hybrid нет фотографий: {result_dir}",
app/web/components/technical_modules/qwen.py:396:            qwen_output = QWEN_ROOT / run_name
app/web/components/technical_modules/qwen.py:397:            qwen_output.mkdir(
app/web/components/technical_modules/qwen.py:403:                f"[QWEN MANUAL] INPUT: {result_dir}",
app/web/components/technical_modules/qwen.py:408:                f"[QWEN MANUAL] OUTPUT: {qwen_output}",
app/web/components/technical_modules/qwen.py:413:                f"[QWEN MANUAL] IMAGES: {total_images}",
app/web/components/technical_modules/qwen.py:420:            model_label.text = "qwen3-vl:4b-instruct"
app/web/components/technical_modules/qwen.py:435:                f"Запуск Qwen3-VL 4B: {total_images} фото",
app/web/components/technical_modules/qwen.py:447:                str(QWEN_SCRIPT),
app/web/components/technical_modules/qwen.py:451:                str(qwen_output),
app/web/components/technical_modules/qwen.py:457:            qwen_process = process
app/web/components/technical_modules/qwen.py:460:                f"[QWEN MANUAL] PID: {process.pid}",
app/web/components/technical_modules/qwen.py:488:                    f"[QWEN] {text}",
app/web/components/technical_modules/qwen.py:530:                if "[QWEN] OK |" in text:
app/web/components/technical_modules/qwen.py:580:                    "[QWEN] ERROR" in text
app/web/components/technical_modules/qwen.py:581:                    or "[QWEN] FAILED" in text
app/web/components/technical_modules/qwen.py:617:                if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:627:                f"[QWEN MANUAL] FINISHED "
app/web/components/technical_modules/qwen.py:632:            if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:638:                    f"Qwen остановлен: "
app/web/components/technical_modules/qwen.py:650:                    "✓ Qwen3-VL 4B завершён",
app/web/components/technical_modules/qwen.py:660:                status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:663:                    f"Qwen завершился с ошибкой: {returncode}",
app/web/components/technical_modules/qwen.py:671:                f"[QWEN MANUAL] EXCEPTION: {exc!r}",
app/web/components/technical_modules/qwen.py:676:            status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:680:                    f"Ошибка запуска Qwen: {exc}",
app/web/components/technical_modules/qwen.py:689:            qwen_process = None
app/web/components/technical_modules/qwen.py:690:            qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:706:                    f"[QWEN MANUAL] UI REFRESH FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:712:        data = _load_qwen_status()
app/web/components/technical_modules/qwen.py:772:    run_button.on_click(run_qwen)
app/web/components/technical_modules/qwen.py:773:    stop_button.on_click(stop_qwen)
app/web/components/header.py:16:from app.web.components.technical import show_technical
app/web/components/header.py:185:        # USER / TECHNICAL DIALOG LOCK
app/web/components/header.py:189:        technical_dialog_state = {"open": False}
app/web/components/header.py:200:            if technical_dialog_state["open"]:
app/web/components/header.py:202:                    "Сначала закройте «Технический раздел»",
app/web/components/header.py:466:        # TECHNICAL
app/web/components/header.py:469:        def open_technical():
app/web/components/header.py:471:            if technical_dialog_state["open"]:
app/web/components/header.py:481:            technical_dialog_state["open"] = True
app/web/components/header.py:483:            def technical_closed():
app/web/components/header.py:484:                technical_dialog_state["open"] = False
app/web/components/header.py:486:            show_technical(
app/web/components/header.py:487:                on_close=technical_closed,
app/web/components/header.py:491:            "Технический раздел",
app/web/components/header.py:493:            on_click=open_technical,
app/web/components/photos.py:345:        # dino_fingerprint.
app/web/components/photos.py:347:        # hybrid_final_id и client normalization здесь
app/web/components/photos.py:350:        # Если DINO fingerprint отсутствует —
app/web/components/photos.py:355:            record.get("dino_fingerprint") or ""
app/web/components/photos.py:364:        # На данном этапе dino_fingerprint сам является
app/web/components/photos.py:459:        "only photos with DINO fingerprint + address_directory",
app/web/components/photos.py:920:                        if value("qwen_status") != "—":
app/web/components/photos.py:923:                                f"Qwen: {value('qwen_status')}"
app/web/components/photos.py:1618:                                    # AI / QWEN STATUS
app/web/components/photos.py:1621:                                    qwen_status = (
app/web/components/photos.py:1623:                                            "qwen_status"
app/web/components/photos.py:1643:                                        qwen_status,
app/web/components/photos.py:1719:                                # QWEN DESCRIPTION
app/web/components/technical.py:3:from app.web.components.technical_modules.photo_processing import (
app/web/components/technical.py:6:from app.web.components.technical_modules.last_run import (
app/web/components/technical.py:9:from app.web.components.technical_modules.automation import (
app/web/components/technical.py:12:from app.web.components.technical_modules.data import (
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:51:48

Да. По этому выводу видно, что **старый технический раздел действительно сохранил отдельный запуск DINO и Qwen**, причём DINO обозначен как:

- **DINO v33 / Hybrid v12**
- отдельный `dino_worker.py`
- Qwen — отдельный `qwen_worker.py`
- UI позволяет запускать/останавливать их независимо;
- в интерфейсе прямо указано: **«DINO и Qwen работают независимо»**.

Но важный момент: по одному `grep` пока нельзя доказать, **на каком устройстве сейчас реально запускается `dino_worker.py`**. `config.py` показывает:

```text
SCENE_DEVICE
→ если переменная не задана:
   CUDA, если torch.cuda.is_available()
   иначе CPU
```

То есть **текущий `SceneEmbedder` по умолчанию GPU**, а не CPU.

Если ты раньше переводил DINO на CPU именно для старого worker-а, это должно быть видно либо в самом `dino_worker.py`, либо в команде его запуска через `SCENE_DEVICE=cpu`.

### Следующий правильный шаг

Ничего пока не менять. Посмотрим именно старый worker и его запуск:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DINO WORKER ================" && \
nl -ba app/workers/dino_worker.py | sed -n '1,360p' && \
echo && \
echo "================ DINO START BLOCK ================" && \
nl -ba app/web/components/technical_modules/photo_processing.py | sed -n '400,510p'
```

Тогда точно установим:

1. **DINO действительно CPU или GPU**;
2. какие именно скрипты запускаются;
3. запускается ли там **чистый recognizer или весь Hybrid v12**;
4. где находятся вход/выход;
5. как старый интерфейс организовывал параллельную работу **DINO CPU + Qwen GPU**.

И уже после этого можно будет аккуратно вернуть именно эту архитектуру, **не трогая отточенный Hybrid v12**.

---

### 👤 **User** — 2026-08-20 23:52:18

нам нужны именно эти файлы и механизм их запуска отдельный `dino_worker.py` 

1.  Qwen — отдельный `qwen_worker.py`

---

### 🤖 **Assistant** — 2026-08-20 23:52:19

Да. Тогда фиксируем архитектуру именно так:

### Нужны два независимых worker-а

**1. `app/workers/dino_worker.py`**

Его задача — весь DINO-механизм распознавания/гибрида в отдельном процессе:

`DINO → 5 кандидатов → Hybrid v12 → финальный результат`

При этом **Hybrid v12 не переписываем**. Он остаётся тем самым отточенным механизмом, который уже работает на CPU.

**2. `app/workers/qwen_worker.py`**

Отдельный процесс:

`фото → Qwen3-VL 4B → результат → PostgreSQL`

Он работает независимо от DINO и может занимать GPU.

### В итоге получаем

```text
                    ФОТО
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
 dino_worker.py            qwen_worker.py
       CPU                       GPU
          │                       │
          ▼                       ▼
 DINO v33                    Qwen3-VL 4B
 5 кандидатов                    │
          │                      ▼
          ▼                 описание / адрес
     Hybrid v12                   │
          │                       │
          ▼                       │
   final dino result              │
          │                       │
          └───────────┬───────────┘
                      ▼
                 PostgreSQL
                 один фото_id
```

И это хорошо совпадает с тем, что мы уже нашли в старом интерфейсе: DINO и Qwen запускаются **как два отдельных процесса**, поэтому их можно выполнять параллельно.

Причём для нашей текущей задачи я бы **не переносил Hybrid внутрь `recognizer.py`**. `recognizer.py` должен оставаться источником **DINO TOP-5**, а `dino_worker.py` — оркестратором, который получает эти кандидаты и запускает существующий Hybrid v12.

Теперь надо посмотреть **ровно два файла**, без лишнего:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ DINO WORKER ================" && \
nl -ba app/workers/dino_worker.py | sed -n '1,500p' && \
echo && \
echo "================ QWEN WORKER ================" && \
nl -ba app/workers/qwen_worker.py | sed -n '1,500p'
```

После этого уже можно будет точно восстановить **старый механизм запуска**, включая CPU/GPU, вход, выход и запись результата к тому же `photo_id`.

---

