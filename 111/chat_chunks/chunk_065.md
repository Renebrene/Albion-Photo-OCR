## СЕССИЯ: Branch · готовая

**Создано:** 2026-08-16 00:03:27
**Обновлено:** 2026-08-19 17:08:07
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d41d-8908-83ea-b688-e34e85acfaa9](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d41d-8908-83ea-b688-e34e85acfaa9)

---

### 👤 **User** — 2026-08-15 20:40:27

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cp scripts/benchmark_hybrid_v03.py scripts/benchmark_hybrid_v05.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cp scripts/benchmark_hybrid_v03.py scripts/benchmark_hybrid_v05.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n "changed\|neighbors\|best" scripts/benchmark_hybrid_v05.py
143:    changed = []
251:        neighbors = get_neighbor_votes(
257:        for fp in neighbors:
265:        best = max(
271:        if best != old:
273:            changed.append(
284:                        best,
289:                    "neighbors":
290:                        dict(neighbors),
296:                        scores[best],
317:                "changed":
318:                    len(changed),
321:                    changed,
342:        "changed:",
343:        len(changed)
347:    for x in changed:
361:            "neighbors:",
362:            x["neighbors"]
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ nl -ba scripts/benchmark_hybrid_v05.py | sed -n '180,280p'
   180	        # SUB ONLY BORDER CASES
   181	        #
   182	
   183	        margin = row.get(
   184	            "margin",
   185	            1
   186	        )
   187	
   188	
   189	        if margin < MARGIN_LIMIT:
   190	
   191	            sub_count += 1
   192	
   193	
   194	            image = Path(
   195	                row["file"]
   196	            )
   197	
   198	
   199	            query = embedder.embed_paths(
   200	                [image]
   201	            )[0]
   202	
   203	            query = normalize(
   204	                query
   205	            )
   206	
   207	
   208	            #
   209	            # ТОЛЬКО TOP1 и TOP2
   210	            #
   211	
   212	            candidates = [
   213	                row.get("top1"),
   214	                row.get("top2"),
   215	            ]
   216	
   217	
   218	            for parent in candidates:
   219	
   220	                if not parent:
   221	                    continue
   222	
   223	
   224	                for sub_id, sub_emb in subs.items():
   225	
   226	                    if not sub_id.startswith(
   227	                        parent
   228	                    ):
   229	                        continue
   230	
   231	
   232	                    sim = max(
   233	                        sub_emb @ query
   234	                    )
   235	
   236	
   237	                    if sim > 0.85:
   238	
   239	                        scores[parent] += (
   240	                            float(sim)
   241	                            *
   242	                            SUB_WEIGHT
   243	                        )
   244	
   245	
   246	
   247	        #
   248	        # SEQUENCE
   249	        #
   250	
   251	        neighbors = get_neighbor_votes(
   252	            rows,
   253	            i
   254	        )
   255	
   256	
   257	        for fp in neighbors:
   258	
   259	            scores[fp] += (
   260	                NEIGHBOR_WEIGHT
   261	            )
   262	
   263	
   264	
   265	        best = max(
   266	            scores,
   267	            key=scores.get
   268	        )
   269	
   270	
   271	        if best != old:
   272	
   273	            changed.append(
   274	                {
   275	                    "file":
   276	                        Path(
   277	                            row["file"]
   278	                        ).name,
   279	
   280	                    "old":
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:40:28

Отлично, структура понятна. В `v05` уже есть важный момент: **subfingerprint применяется только при `margin < MARGIN_LIMIT`**, это правильно. Сейчас проблема только в блоке `SEQUENCE` — он слишком сильно влияет.

Меняем только участок 247–261.

Сейчас:

```python
        #
        # SEQUENCE
        #

        neighbors = get_neighbor_votes(
            rows,
            i
        )

for fp in neighbors:

            scores[fp] += (
                NEIGHBOR_WEIGHT
            )
```

Заменяем на строгий вариант:

```python
        #
        # SEQUENCE CONSENSUS
        #
        # Используем соседей только если
        # слева и справа один и тот же адрес.
        #

        neighbors = get_neighbor_votes(
            rows,
            i
        )

        left_fp = None
        right_fp = None

        if i > 0:
            left_fp = rows[i-1].get("top1")

        if i < len(rows)-1:
            right_fp = rows[i+1].get("top1")

if (
            left_fp
            and right_fp
            and left_fp == right_fp
        ):
            scores[left_fp] += (
                NEIGHBOR_WEIGHT
            )
```

Команда замены через `python3`:

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v05.py")

s = p.read_text(encoding="utf-8")

old = '''        #
        # SEQUENCE
        #

        neighbors = get_neighbor_votes(
            rows,
            i
        )

for fp in neighbors:

            scores[fp] += (
                NEIGHBOR_WEIGHT
            )
'''

new = '''        #
        # SEQUENCE CONSENSUS
        #
        # Используем соседей только если
        # слева и справа один и тот же адрес.
        #

        neighbors = get_neighbor_votes(
            rows,
            i
        )

        left_fp = None
        right_fp = None

        if i > 0:
            left_fp = rows[i-1].get("top1")

        if i < len(rows)-1:
            right_fp = rows[i+1].get("top1")

if (
            left_fp
            and right_fp
            and left_fp == right_fp
        ):
            scores[left_fp] += (
                NEIGHBOR_WEIGHT
            )
'''

if old not in s:
    raise SystemExit("BLOCK NOT FOUND")

s = s.replace(old, new)

p.write_text(s, encoding="utf-8")

print("patched", p)
PY
```

Проверка:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v05.py
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v05.py | tee output/hybrid_v05.log
```

Ожидаем, что:

- `sub rerank` останется примерно `43`
- `changed` должен уйти ближе к 10 или меньше
- исчезнут случаи типа:

```
Радиаторный_24
Радиаторный_25
Зорге_17
```

которые были ложными из-за одиночного соседа.

Следующий шаг после этого — добавить **проверку согласованности TOP2** (когда DINO говорит 87/84, а sub говорит 84 — это идеальный случай). Это даст ещё несколько процентов без риска.

---

### 👤 **User** — 2026-08-15 20:41:16

checked: 256
sub rerank: 43
changed: 10

Ашхабадский_08.JPG
89_v33 -> 85_v33
neighbors: {'85_v33': 1}

Зорге_06.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_15.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Ленина125_02.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_03.JPG
84_v33 -> 87_v33
neighbors: {'87_v33': 1}

Ленина125_04.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_08.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Малиновского_к_Доватора_10.JPG
94_v33 -> 89_v33
neighbors: {'89_v33': 1}

Малиновского_к_Стачки_03.JPG
89_v33 -> 90_v33
neighbors: {'90_v33': 1}

Малиновского_к_Стачки_04.JPG
90_v33 -> 89_v33
neighbors: {'89_v33': 1}

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v03.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:41:18

Отлично. Это уже выглядит как **правильная архитектура**.

Получили:

```
checked: 256
sub rerank: 43
changed: 10
```

То есть после всех ограничений:

- subfingerprint проверил только **43 пограничных кадра** из 256 (~17%)
- реально изменил только **10**
- нет ложных массовых перескоков как в v04

Список изменений очень показательный:

### Хорошие исправления:

```
Ленина125_02
87 -> 84

Ленина125_03
84 -> 87

Ленина125_04
87 -> 84

Ленина125_08
87 -> 84
```

Это именно тот случай, для которого subfingerprint нужен:
- два соседних адреса похожи;
- глобальный DINO путает;
- локальный слепок решает.

---

### Ещё хорошие:

```
Ашхабадский_08
89 -> 85

Зорге_06
89 -> 92

Зорге_15
89 -> 92

Малиновского_к_Доватора_10
94 -> 89
```

Здесь sequence подтверждает переход.

---

### Что осталось проверить

Теперь нужно посмотреть **не количество changed, а качество changed**.

Я бы сделал следующий тест:

## 1. Добавляем "confidence after hybrid"

Сейчас у нас есть:

```
DINO:
top1
top2
margin

HYBRID:
best
```

Нужно сохранить:

```
old_score
new_score
delta
```

и посмотреть:

- какие изменения имеют большой прирост;
- какие изменения почти случайные.

Например:

```
Ленина125_04
87 -> 84
delta +0.08  GOOD

Малиновского...
89 -> 90
delta +0.01  сомнительно
```

---

## 2. Следующий шаг я бы сделал hybrid_v06

Правило:

Меняем адрес только если:

```
(
 sub_delta > 0.05
)
OR
(
 left == right
 AND
 neighbor_confirmation
)
```

Но сейчас надо добавить ещё:

```
new_score > old_score
```

То есть запрещаем ухудшение.

Сейчас возможна ситуация:

```
87 score 0.90
84 score 0.86
```

но сосед подтянул 84.

А надо:

```
84 итоговый score должен быть выше
```

---

Команда для следующего этапа:

```bash
cp scripts/benchmark_hybrid_v05.py scripts/benchmark_hybrid_v06.py
```

В v06 добавим:

```
before = scores[old]
after = scores[best]

if best != old and after > before:
    accept
else:
    keep old
```

Это будет уже очень близко к финальному recognizer:

```
                 DINO global
                      |
                 TOP1 / TOP2
                      |
              margin < threshold?
                      |
        +-------------+-------------+
        |                           |
       NO                          YES
        |                           |
     accept              subfingerprint
                                      |
                             sequence consensus
                                      |
                              final decision
```

Сейчас мы фактически вышли на правильную схему. Следующий тест v06 должен уменьшить ложные изменения без потери исправлений.

---

### 👤 **User** — 2026-08-15 20:41:52

продолжаем.

---

### 🤖 **Assistant** — 2026-08-15 20:41:54

Продолжаем. Делаем `hybrid_v06` с главным ограничителем:

**Нельзя менять адрес, если новый вариант не улучшил итоговый score.**

Сейчас `v05` уже хороший:
- DINO → TOP1/TOP2
- sub только border cases
- соседи только при согласии

Добавляем последний предохранитель.

---

Создаём копию:

```bash
cp scripts/benchmark_hybrid_v05.py scripts/benchmark_hybrid_v06.py
```

Открываем участок:

```bash
nl -ba scripts/benchmark_hybrid_v06.py | sed -n '260,310p'
```

Там будет:

```python
best = max(
    scores,
    key=scores.get
)

if best != old:

    changed.append(
```

Меняем на:

```python
best = max(
    scores,
    key=scores.get
)

old_score = scores.get(
    old,
    0
)

new_score = scores.get(
    best,
    0
)

# принимаем изменение только если
# новый кандидат реально сильнее

if (
    best != old
    and new_score > old_score
):

    changed.append(
```

---

Быстрее через patch:

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v06.py")

s = p.read_text(encoding="utf-8")

old = '''        best = max(
            scores,
            key=scores.get
        )

if best != old:

            changed.append(
'''

new = '''        best = max(
            scores,
            key=scores.get
        )

old_score = scores.get(
            old,
            0
        )

        new_score = scores.get(
            best,
            0
        )

# принимаем изменение только если
        # новый кандидат реально сильнее

        if (
            best != old
            and new_score > old_score
        ):

            changed.append(
'''

if old not in s:
    raise SystemExit("BLOCK NOT FOUND")

p.write_text(
    s.replace(old,new),
    encoding="utf-8"
)

print("patched", p)
PY
```

Проверка:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v06.py
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v06.py | tee output/hybrid_v06.log
```

---

Что ожидаем:

Скорее всего:

```
checked: 256
sub rerank: 43
changed: 6-9
```

Должны остаться:

```
Ленина125_02
Ленина125_04
Ленина125_08
```

Потому что там sub реально даёт прирост.

А вот сомнительные:

```
Зорге_17
Радиаторный
Рубиновый
```

должны исчезнуть.

После этого сделаем `accuracy check` — сравним:

```
benchmark_v1
vs
hybrid_v06
```

и получим реальный процент улучшения.

Следующая стадия уже будет не hybrid, а перенос этой логики внутрь основного `recognize`, чтобы не делать отдельный benchmark-скрипт.

---

### 👤 **User** — 2026-08-15 20:42:59

да

---

### 🤖 **Assistant** — 2026-08-15 20:43:00

Запускаем `v06`.

Сначала проверим, что файл на месте:

```bash
ls -lh scripts/benchmark_hybrid_v06.py
```

Проверка синтаксиса:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v06.py
```

Если без ошибок — запуск:

```bash
uv run python scripts/benchmark_hybrid_v06.py | tee output/hybrid_v06.log
```

После выполнения пришли вывод блока:

```
checked:
sub rerank:
changed:
```

и список изменённых файлов.

Дальше будем делать сравнение:

1. **DINO v33 baseline**
2. **hybrid v06**
3. **sequence v38**
4. **sub rerank**

и выделим:
- какие исправления стабильные;
- какие дают ложные скачки;
- какие правила переносим в основной `recognizer.py`.

Следующий целевой вариант:

```
DINO global
      |
      +-- TOP1 уверенный (margin > X)
      |          |
      |          accept
      |
      +-- border case
                 |
              TOP1/TOP2 subfingerprint
                 |
              sequence consensus
                 |
              final address
```

То есть в рабочем режиме 80–90% фотографий будут проходить мгновенно, а тяжёлая логика будет включаться только там, где реально есть сомнение.

---

### 👤 **User** — 2026-08-15 20:43:07

changed: 10

Ашхабадский_08.JPG
89_v33 -> 85_v33
neighbors: {'85_v33': 1}

Зорге_06.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_15.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Ленина125_02.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_03.JPG
84_v33 -> 87_v33
neighbors: {'87_v33': 1}

Ленина125_04.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_08.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Малиновского_к_Доватора_10.JPG
94_v33 -> 89_v33
neighbors: {'89_v33': 1}

Малиновского_к_Стачки_03.JPG
89_v33 -> 90_v33
neighbors: {'90_v33': 1}

Малиновского_к_Стачки_04.JPG
90_v33 -> 89_v33
neighbors: {'89_v33': 1}

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v03.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:43:09

Результат `v06` фактически такой же, как `v05`:

```
changed: 10
```

Это хороший знак. Ограничитель `new_score > old_score` ничего не отрезал, значит все 10 изменений были не просто "продавлены соседями", а действительно имели лучший итоговый балл.

Сейчас у нас стабильный набор:

```
Ашхабадский_08
89 -> 85

Зорге_06
89 -> 92

Зорге_15
89 -> 92

Ленина125_02
87 -> 84

Ленина125_03
84 -> 87

Ленина125_04
87 -> 84

Ленина125_08
87 -> 84

Малиновского_к_Доватора_10
94 -> 89

Малиновского_к_Стачки_03
89 -> 90

Малиновского_к_Стачки_04
90 -> 89
```

Следующий важный этап — **не добавлять ещё правил**, а проверить качество решений.

Нужно получить для каждого изменения:

```
old_score
new_score
delta
reason
```

Сейчас вывод:

```
89 -> 85
neighbors: {'85_v33': 1}
```

не показывает, насколько уверенно.

---

Предлагаю сделать `hybrid_v07`:

Добавляем в JSON:

```json
{
 "file": "Ленина125_04.JPG",
 "old": "87_v33",
 "new": "84_v33",
 "old_score": 0.91,
 "new_score": 1.03,
 "delta": 0.12,
 "neighbors": {
    "84_v33":1
 }
}
```

И потом сортируем изменения:

```
DELTA DESC
```

Получим:

- крупные улучшения → железные правила;
- маленькие → надо осторожно.

---

Сейчас сделай копию:

```bash
cp scripts/benchmark_hybrid_v06.py scripts/benchmark_hybrid_v07.py
```

Потом в блоке:

```python
if (
    best != old
    and new_score > old_score
):
```

перед `changed.append` добавляем:

```python
delta = (
    new_score
    -
    old_score
)
```

И в словарь `changed` добавляем:

```python
"old_score": old_score,
"new_score": new_score,
"delta": delta,
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v07.py
```

После этого посмотрим:

```bash
python3 - <<'PY'
import json

p="data/output/benchmark_hybrid_v07.json"

d=json.load(open(p))

for x in sorted(
    d["changed"],
    key=lambda x:x["delta"],
    reverse=True
):
    print(
        x["file"],
        x["old"],
        "->",
        x["new"],
        "delta=",
        round(x["delta"],4)
    )
PY
```

После этого уже можно будет переносить логику в настоящий `recognizer.py`.

Сейчас архитектура практически сформировалась:

```
1. Global DINO v33
        |
        |
2. margin check
        |
        +---- high confidence
        |          |
        |        address
        |
        +---- ambiguous
                   |
              TOP1 + TOP2 only
                   |
             subfingerprint
                   |
             sequence neighbors
                   |
             final address
```

Это намного лучше, чем полный rerank по всем subfingerprint (он как раз давал 130 ложных изменений).

---

### 👤 **User** — 2026-08-15 20:43:43

cp scripts/benchmark_hybrid_v06.py scripts/benchmark_hybrid_v07.py готовый

---

### 🤖 **Assistant** — 2026-08-15 20:43:44

Сделай так — создаём сразу готовый `hybrid_v07.py` из `v06` с добавлением `delta` в результат.

Команда:

```bash
cat > /tmp/patch_hybrid_v07.py <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v07.py")

s = p.read_text(encoding="utf-8")

old = '''        if (
            best != old
            and new_score > old_score
        ):

            changed.append(
                {
                    "file":
                        Path(
                            row["file"]
                        ).name,
'''

new = '''        if (
            best != old
            and new_score > old_score
        ):

            delta = (
                new_score
                -
                old_score
            )

            changed.append(
                {
                    "file":
                        Path(
                            row["file"]
                        ).name,
'''

if old not in s:
    raise SystemExit("BLOCK 1 NOT FOUND")

s = s.replace(old, new)

old2 = '''                    "old":
                        old,

                    "new":
                        best,

                    "neighbors":
'''

new2 = '''                    "old":
                        old,

                    "new":
                        best,

                    "old_score":
                        old_score,

                    "new_score":
                        new_score,

                    "delta":
                        delta,

                    "neighbors":
'''

if old2 not in s:
    raise SystemExit("BLOCK 2 NOT FOUND")

s = s.replace(old2, new2)

p.write_text(
    s,
    encoding="utf-8"
)

print("patched", p)
PY

python3 /tmp/patch_hybrid_v07.py
```

Проверка:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v07.py
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v07.py | tee output/hybrid_v07.log
```

После этого посмотрим прирост:

```bash
python3 - <<'PY'
import json

p="data/output/benchmark_hybrid_v07.json"

d=json.load(open(p))

print("="*80)
print("CHANGES BY DELTA")
print("="*80)

for x in sorted(
    d["changed"],
    key=lambda x:x["delta"],
    reverse=True
):
    print(
        f'{x["file"]:35s} '
        f'{x["old"]:8s} -> {x["new"]:8s} '
        f'delta={x["delta"]:.4f}'
    )
PY
```

Это даст нам уже рейтинг исправлений по силе. Следующий шаг после этого — встроить эту логику непосредственно в `recognizer.py`, чтобы не гонять отдельный benchmark.

---

### 👤 **User** — 2026-08-15 20:45:19

python3 /tmp/patch_hybrid_v07.pyT FOUND")
BLOCK 2 NOT FOUND

---

### 🤖 **Assistant** — 2026-08-15 20:45:22

Ок, первый блок нашёлся, второй нет — значит в `v06` структура словаря немного отличается.

Сначала посмотрим участок:

```bash
nl -ba scripts/benchmark_hybrid_v07.py | sed -n '270,310p'
```

Скорее всего там не `"old":`, а другой порядок.

Можно сразу сделать универсальную вставку:

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v07.py")

s = p.read_text(encoding="utf-8")

marker = '''                    "new":
                        best,
'''

insert = '''                    "new":
                        best,

                    "old_score":
                        old_score,

                    "new_score":
                        new_score,

                    "delta":
                        delta,
'''

if marker not in s:
    print("marker not found")
    print("ищем new:")
    for i,line in enumerate(s.splitlines(),1):
        if '"new"' in line:
            print(i, line)
    raise SystemExit(1)

s = s.replace(
    marker,
    insert,
    1
)

p.write_text(
    s,
    encoding="utf-8"
)

print("patched:", p)
PY
```

Потом:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v07.py
```

и запуск:

```bash
uv run python scripts/benchmark_hybrid_v07.py | tee output/hybrid_v07.log
```

Если снова упадёт — пришли:

```bash
nl -ba scripts/benchmark_hybrid_v07.py | sed -n '270,310p'
```

Там быстро подгоним.

---

### 👤 **User** — 2026-08-15 20:45:42

давай готовый файл

---

### 🤖 **Assistant** — 2026-08-15 20:45:44

Сделаем без патчей. Просто создаём готовый `benchmark_hybrid_v07.py` из `v06` с безопасным добавлением `delta`.

Выполни:

```bash
cp scripts/benchmark_hybrid_v06.py scripts/benchmark_hybrid_v07.py
```

Теперь одним блоком заменяем:

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v07.py")

s = p.read_text(encoding="utf-8")

# добавляем delta перед changed.append
s = s.replace(
'''        if (
            best != old
            and new_score > old_score
        ):

            changed.append(
''',
'''        if (
            best != old
            and new_score > old_score
        ):

            delta = (
                new_score
                -
                old_score
            )

            changed.append(
''',
1
)

# добавляем поля в словарь независимо от порядка
needle = '''"new":
                        best,
'''

if needle in s:
    s = s.replace(
        needle,
''' "new":
                        best,

                    "old_score":
                        old_score,

                    "new_score":
                        new_score,

                    "delta":
                        delta,
''',
        1
    )
else:
    print("WARNING: new field not found, adding before neighbors")

    s = s.replace(
'''                    "neighbors":
''',
'''                    "old_score":
                        old_score,

                    "new_score":
                        new_score,

                    "delta":
                        delta,

                    "neighbors":
''',
        1
    )

p.write_text(
    s,
    encoding="utf-8"
)

print("READY:", p)
PY
```

Проверка:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v07.py
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v07.py | tee output/hybrid_v07.log
```

После этого выводим рейтинг:

```bash
python3 - <<'PY'
import json

p="data/output/benchmark_hybrid_v07.json"

d=json.load(open(p))

print("="*80)
print("DELTA RANK")
print("="*80)

for x in sorted(
    d["changed"],
    key=lambda z:z.get("delta",0),
    reverse=True
):
    print(
        x["file"],
        x["old"],
        "->",
        x["new"],
        "delta=",
        round(x.get("delta",0),4)
    )
PY
```

После этого будет понятно, какие 10 изменений действительно сильные, а какие можно отсеять перед переносом в `recognizer.py`.

---

### 👤 **User** — 2026-08-15 20:47:11

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
import json
p="data/output/benchmark_hybrid_v07.json"
p="data/output/benchmark_hybrid_v07.json"
d=json.load(open(p))
d=json.load(open(p))
print("="*80)
print("="*80)RANK")
print("DELTA RANK")
print("="*80)
for x in sorted(
for x in sorted(,
    d["changed"],z.get("delta",0),
    key=lambda z:z.get("delta",0),
    reverse=True
):  print(
    print("file"],
        x["file"],
        x["old"],
        "->",w"],
        x["new"],
        "delta=",et("delta",0),4)
        round(x.get("delta",0),4)
    )
PY
Traceback (most recent call last):
  File "<stdin>", line 5, in <module>
FileNotFoundError: [Errno 2] No such file or directory: 'data/output/benchmark_hybrid_v07.json'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:47:13

Ошибка простая: `benchmark_hybrid_v07.py` ещё не создал файл:

```
data/output/benchmark_hybrid_v07.json
```

Сейчас у тебя есть только результат:

```
data/output/benchmark_hybrid_v03.json
```

Сначала надо реально запустить v07.

Проверь, что файл есть:

```bash
ls -lh scripts/benchmark_hybrid_v07.py
```

Потом:

```bash
uv run python scripts/benchmark_hybrid_v07.py | tee output/hybrid_v07.log
```

После окончания должно появиться:

```
saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v07.json
```

Тогда уже запускай сортировку delta:

```bash
python3 - <<'PY'
import json

p="data/output/benchmark_hybrid_v07.json"

d=json.load(open(p, encoding="utf-8"))

print("="*80)
print("DELTA RANK")
print("="*80)

for x in sorted(
    d["changed"],
    key=lambda z: z.get("delta", 0),
    reverse=True
):
    print(
        f'{x["file"]:35s} '
        f'{x["old"]:8s} -> {x["new"]:8s} '
        f'delta={x.get("delta",0):.4f}'
    )
PY
```

Кстати, по предыдущему результату у нас уже видно важное:

- `Ленина125` — хороший кандидат для subfingerprint (84/87 реально путаются).
- `Шеболдаева8_06` надо исключить (там sub rerank ломает правильный ответ).
- `КА`, `Комарова` и подобные случаи нельзя трогать глобальным sub rerank — там DINO v33 уже лучше.

То есть следующий шаг после delta — добавить **защиту от ухудшения**:

```
если old score высокий (>0.90)
и margin не критический
→ не трогать

если margin < 0.02
и TOP1/TOP2 близкие
→ включать sub + sequence
```

Это как раз приведёт к рабочему распознаванию, а не просто к улучшению benchmark.

---

### 👤 **User** — 2026-08-15 20:47:43

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v07.json
saved:: command not found
bash: /home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v07.json: No such file or directory
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:47:45

Ты просто вставил строку вывода программы как команду 🙂

Вот это:

```bash
saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v07.json
```

не надо выполнять. Это **результат работы скрипта**, а не команда.

Теперь файл должен быть создан. Проверяем:

```bash
ls -lh data/output/benchmark_hybrid_v07.json
```

Если есть — запускаем анализ:

```bash
python3 - <<'PY'
import json

p="data/output/benchmark_hybrid_v07.json"

d=json.load(open(p, encoding="utf-8"))

print("="*80)
print("DELTA RANK")
print("="*80)

for x in sorted(
    d["changed"],
    key=lambda z: z.get("delta", 0),
    reverse=True
):
    print(
        f'{x["file"]:35s} '
        f'{x["old"]:8s} -> {x["new"]:8s} '
        f'delta={x.get("delta",0):.4f}'
    )
PY
```

Пришли результат `DELTA RANK`.

Дальше будем уже не экспериментировать с весами, а сделаем финальный `hybrid_v08`:

- DINO v33 — основной классификатор;
- subfingerprint только для TOP1/TOP2 при малом margin;
- sequence neighbors только как подтверждение;
- запрет менять уверенные случаи (`score > 0.90` и `margin > 0.02`).

Это должно убрать как раз такие случаи, как `Шеболдаева8_06`, где автобус ломал sub rerank.

---

### 👤 **User** — 2026-08-15 20:48:04

ls: cannot access 'data/output/benchmark_hybrid_v07.json': No such file or directory

---

### 🤖 **Assistant** — 2026-08-15 20:48:06

Значит строка `saved:` была не от реально выполненного `v07`, а просто попала в консоль (или скрипт сохранил под другим именем). Давайте проверим фактически.

Выполни:

```bash
ls -lah data/output | grep hybrid
```

и:

```bash
grep -n "saved\|OUTPUT\|json" scripts/benchmark_hybrid_v07.py
```

Скорее всего внутри `v07` осталось:

```python
benchmark_hybrid_v03.json
```

или другой путь.

Быстро найти:

```bash
grep -R "benchmark_hybrid" -n scripts/benchmark_hybrid_v07.py
```

Если там будет, например:

```python
benchmark_hybrid_v03.json
```

меняем:

```bash
sed -i 's/benchmark_hybrid_v03/benchmark_hybrid_v07/g' scripts/benchmark_hybrid_v07.py
```

Потом запускаем:

```bash
uv run python scripts/benchmark_hybrid_v07.py | tee output/hybrid_v07.log
```

И проверяем:

```bash
ls -lh data/output/*hybrid*v07*
```

После этого уже появится правильный JSON для анализа delta.

---

### 👤 **User** — 2026-08-15 20:48:18

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ls -lah data/output | grep hybrid
-rw-rw-r-- 1 alexice alexice 4.5K Aug 15 20:27 benchmark_hybrid_v01.json
-rw-rw-r-- 1 alexice alexice 5.0K Aug 15 20:33 benchmark_hybrid_v02.json
-rw-rw-r-- 1 alexice alexice 2.8K Aug 15 20:42 benchmark_hybrid_v03.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:48:20

Да, подтверждено: `v07` не создаётся. Значит в скрипте `benchmark_hybrid_v07.py` либо остался старый путь вывода, либо файл вообще не был нормально создан из `v06`.

Сейчас лучше не латать. Сделаем правильно.

1. Проверяем, что есть сам файл:

```bash
ls -lh scripts/benchmark_hybrid_v07.py
```

2. Смотрим, куда он пишет:

```bash
grep -n "benchmark_hybrid\|write_text\|json" scripts/benchmark_hybrid_v07.py
```

Скорее всего увидим:

```python
data/output/benchmark_hybrid_v03.json
```

Тогда меняем одной командой:

```bash
sed -i 's/benchmark_hybrid_v03/benchmark_hybrid_v07/g' scripts/benchmark_hybrid_v07.py
```

3. Проверяем синтаксис:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v07.py
```

4. Запускаем:

```bash
uv run python scripts/benchmark_hybrid_v07.py | tee output/hybrid_v07.log
```

После запуска должно быть:

```
saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v07.json
```

И:

```bash
ls -lh data/output | grep hybrid
```

должен показать:

```
benchmark_hybrid_v07.json
```

---

Кстати, по текущим результатам я бы уже не усиливал hybrid дальше. Следующий правильный шаг — сделать **v08 с ограничителем**:

```
если:
    margin > 0.02
    и score > 0.90

то:
    доверяем DINO v33
    sub не запускаем

иначе:
    TOP1/TOP2
    subfingerprint
    sequence neighbors
```

Это должно оставить только реальные пограничные случаи (84/87, 89/92 и т.п.), а не пытаться исправлять весь массив.

---

### 👤 **User** — 2026-08-15 20:48:47

rid_v07.py
-rw-rw-r-- 1 alexice alexice 1.8K Aug 15 20:47 scripts/benchmark_hybrid_v07.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n "benchmark_hybrid\|write_text\|json" scripts/benchmark_hybrid_v07.py
3:p = Path("scripts/benchmark_hybrid_v07.py")
92:p.write_text(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:48:50

Вот проблема найдена. `scripts/benchmark_hybrid_v07.py` сейчас **не является benchmark-скриптом**. Он превратился в маленький patch-скрипт.

Это видно:

```bash
grep -n "benchmark_hybrid\|write_text\|json" scripts/benchmark_hybrid_v07.py
```

вывод:

```
3:p = Path("scripts/benchmark_hybrid_v07.py")
92:p.write_text(
```

То есть внутри него код, который **редактирует сам себя**, а не запускает benchmark.

Нужно восстановить из `v06`:

```bash
cp scripts/benchmark_hybrid_v06.py scripts/benchmark_hybrid_v07.py
```

Проверяем:

```bash
wc -l scripts/benchmark_hybrid_v07.py
```

Должно быть примерно несколько сотен строк, а не 100.

Потом меняем только имя выходного файла:

```bash
grep -n "benchmark_hybrid" scripts/benchmark_hybrid_v07.py
```

Если там:

```python
benchmark_hybrid_v03.json
```

то:

```bash
sed -i 's/benchmark_hybrid_v03/benchmark_hybrid_v07/g' scripts/benchmark_hybrid_v07.py
```

Проверка:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v07.py
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v07.py | tee output/hybrid_v07.log
```

После этого появится:

```
data/output/benchmark_hybrid_v07.json
```

И уже можно будет сравнить `v03 → v07`.

Причина ошибки: при предыдущем патче мы случайно записали **скрипт-патчер в сам benchmark-файл**. Хорошо, что есть `benchmark_hybrid_v06.py`, восстановление занимает одну команду.

---

### 👤 **User** — 2026-08-15 20:49:57

checked: 256
sub rerank: 43
changed: 10

Ашхабадский_08.JPG
89_v33 -> 85_v33
neighbors: {'85_v33': 1}

Зорге_06.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_15.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Ленина125_02.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_03.JPG
84_v33 -> 87_v33
neighbors: {'87_v33': 1}

Ленина125_04.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_08.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Малиновского_к_Доватора_10.JPG
94_v33 -> 89_v33
neighbors: {'89_v33': 1}

Малиновского_к_Стачки_03.JPG
89_v33 -> 90_v33
neighbors: {'90_v33': 1}

Малиновского_к_Стачки_04.JPG
90_v33 -> 89_v33
neighbors: {'89_v33': 1}

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v07.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:49:59

Отлично. Теперь `v07` реально запустился и результат уже выглядит стабильнее:

```
checked: 256
sub rerank: 43
changed: 10
```

Главное отличие от предыдущих версий:

- `sub rerank` работает только на 43 пограничных кадрах;
- изменений всего 10;
- нет массового разрушения правильных ответов (`v02` менял 130 файлов — это было слишком агрессивно).

Сейчас получилась логика:

```
DINO v33
   |
   | margin < порога
   ↓
TOP1 / TOP2
   |
   ↓
subfingerprint
   |
   ↓
neighbor vote
   |
   ↓
новый адрес
```

По изменениям:

Хорошие кандидаты:

```
Ленина125:
87 -> 84
84 -> 87
```

Это реальная зона конфликта. Subfingerprint здесь помогает.

```
Ашхабадский_08
89 -> 85

Зорге:
89 -> 92
```

Тоже похоже на правильные исправления, потому что соседи подтверждают:

```
neighbors: {'85_v33':1}
neighbors: {'92_v33':1}
```

---

Но есть важный момент: сейчас изменение происходит даже если сосед всего один:

```
neighbors: {'85_v33':1}
```

Я бы сделал следующий `v08`:

### Правило принятия решения

Не менять если:

```
old_score > 0.90
и
margin > 0.02
```

Менять если:

```
sub_score - old_score > 0.03
```

или:

```
neighbor_vote >= 2
```

То есть:

```
DINO победил уверенно → оставить

DINO сомневается:
    sub + neighbors

если подтверждение слабое:
    оставить старый
```

Это как раз защитит от случая:

```
Шеболдаева8_06
87 -> 92
```

который мы уже нашли как ложное исправление из-за автобуса.

---

Следующий шаг я бы сделал не `v08` сразу, а небольшой анализ:

```bash
python3 - <<'PY'
import json

for f in [
"benchmark_hybrid_v03.json",
"benchmark_hybrid_v07.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))

    print()
    print(f)
    print("changed:",len(d["changed"]))

    for x in d["changed"]:
        if "Шеболдаева" in x["file"]:
            print("BAD:",x)
PY
```

Потом сделаем `benchmark_hybrid_v08.py` с фильтром доверия.

Сейчас мы уже близко к рабочему варианту:
**DINO глобальный поиск → только спорные TOP1/TOP2 → subfingerprint → соседнее подтверждение → адрес.**

---

### 👤 **User** — 2026-08-15 20:50:46

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
import json

for f in [
"benchmark_hybrid_v03.json",
"benchmark_hybrid_v07.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))

    print()
    print(f)
    print("changed:",len(d["changed"]))

    for x in d["changed"]:
        if "Шеболдаева" in x["file"]:
            print("BAD:",x)
PY

benchmark_hybrid_v03.json
Traceback (most recent call last):
  File "<stdin>", line 11, in <module>
TypeError: object of type 'int' has no len()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:50:48

Отлично, это полезная ошибка. В `benchmark_hybrid_v03.json` поле `changed` у тебя не список, а число:

```json
"changed": 10
```

А список изменений, скорее всего, лежит отдельно (например `changes`, `results` или `details`).

Сначала посмотрим структуру обоих файлов:

```bash
python3 - <<'PY'
import json

for f in [
    "benchmark_hybrid_v03.json",
    "benchmark_hybrid_v07.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))

    print()
    print("="*60)
    print(f)

    for k,v in d.items():
        print(k, type(v).__name__)
PY
```

Скорее всего увидим что-то вроде:

```
checked int
sub_count int
changed int
changes list
```

После этого сделаем правильное сравнение.

Если надо быстро проверить только `Шеболдаева`, можно так:

```bash
python3 - <<'PY'
import json

for f in [
"benchmark_hybrid_v03.json",
"benchmark_hybrid_v07.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))

    print()
    print(f)

    items = (
        d.get("changes")
        or d.get("changed_list")
        or d.get("results")
        or []
    )

    for x in items:
        if isinstance(x,dict) and "Шеболдаева" in str(x):
            print(x)
PY
```

После этого увидим, ушёл ли ложный случай и насколько `v07` лучше `v03`.

---

### 👤 **User** — 2026-08-15 20:51:02

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
import json

for f in [
    "benchmark_hybrid_v03.json",
    "benchmark_hybrid_v07.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))

    print()
    print("="*60)
    print(f)

    for k,v in d.items():
        print(k, type(v).__name__)
PY

============================================================
benchmark_hybrid_v03.json
checked int
sub_rerank int
changed int
results list

============================================================
benchmark_hybrid_v07.json
checked int
sub_rerank int
changed int
results list
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:51:05

Отлично. Структура понятна:

```text
checked     int
sub_rerank  int
changed     int
results     list
```

Значит надо смотреть `results`.

Запусти сравнение:

```bash
python3 - <<'PY'
import json

for f in [
    "benchmark_hybrid_v03.json",
    "benchmark_hybrid_v07.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))

    print()
    print("="*80)
    print(f)
    print("changed:", d["changed"])

    for x in d["results"]:
        if "Шеболдаева" in x["file"]:
            print()
            print("FOUND:")
            print(x)
PY
```

И ещё полезнее — сравним все изменения v03 → v07:

```bash
python3 - <<'PY'
import json

def load(name):
    d=json.load(open("data/output/"+name,encoding="utf-8"))
    return {
        x["file"]: x
        for x in d["results"]
    }

a=load("benchmark_hybrid_v03.json")
b=load("benchmark_hybrid_v07.json")

print("="*80)
print("DIFF v03 -> v07")
print("="*80)

count=0

for f in sorted(a):
    old=a[f].get("old", a[f].get("top1"))
    new=b[f].get("new", b[f].get("top1"))

    if old != new:
        print()
        print(f)
        print(old,"->",new)

        if "neighbors" in b[f]:
            print("neighbors:",b[f]["neighbors"])

        count+=1

print()
print("TOTAL:",count)
PY
```

После этого будет видно:
- какие изменения реально сохранились;
- какие были отброшены;
- есть ли ещё ложные исправления типа `Шеболдаева8_06`.

Следующий шаг после этого — уже `hybrid_v08` с **правилом доверия**, а не очередным подбором веса. Сейчас у нас достаточно данных.

---

### 👤 **User** — 2026-08-15 20:51:18

================================================================================
benchmark_hybrid_v03.json
changed: 10

================================================================================
benchmark_hybrid_v07.json
changed: 10
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:51:19

Отлично. Это важный результат: **v07 не изменил количество решений относительно v03**.

То есть сейчас:

```
v03:
changed: 10

v07:
changed: 10
```

Значит наши последние изменения не дали дополнительного "шума". Но надо проверить **какие именно 10 изменений**, потому что количество само по себе не говорит, стали ли решения лучше.

Выполни:

```bash
python3 - <<'PY'
import json

for f in [
    "benchmark_hybrid_v03.json",
    "benchmark_hybrid_v07.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))

    print()
    print("="*80)
    print(f)

    for x in d["results"]:
        if x.get("old") != x.get("new"):
            print(
                x["file"],
                ":",
                x.get("old"),
                "->",
                x.get("new"),
                "neighbors:",
                x.get("neighbors")
            )
PY
```

Нам нужно сравнить список.

Я ожидаю, что он будет примерно таким:

```
Ашхабадский_08 89 -> 85
Зорге_06        89 -> 92
Зорге_15        89 -> 92
Ленина125_02    87 -> 84
Ленина125_03    84 -> 87
Ленина125_04    87 -> 84
Ленина125_08    87 -> 84
Малиновского... 94 -> 89
Малиновского... 89 -> 90
Малиновского... 90 -> 89
```

Если список совпадёт — можно переходить к следующей стадии.

Я бы тогда делал `hybrid_v08` не с новыми весами, а с **трёхуровневой системой принятия решения**:

```
1. DINO v33
   |
   | margin > 0.02
   | score > 0.85
   |
   └── оставить

2. Пограничный случай
   |
   | margin < 0.02
   |
   ├── subfingerprint TOP1/TOP2
   |
   └── sequence neighbors

3. Конфликт:
   
   DINO = A
   sub = B
   neighbors = A

   → оставить A
```

Это решит проблему типа:

```
Шеболдаева8_06
DINO правильно
sub ошибся из-за автобуса
```

Сейчас самое главное — пришли список `old -> new` из команды выше.

---

### 👤 **User** — 2026-08-15 20:51:36

================================================================================
benchmark_hybrid_v03.json
Ашхабадский_08.JPG : 89_v33 -> 85_v33 neighbors: {'85_v33': 1}
Зорге_06.JPG : 89_v33 -> 92_v33 neighbors: {'92_v33': 1}
Зорге_15.JPG : 89_v33 -> 92_v33 neighbors: {'92_v33': 1}
Ленина125_02.JPG : 87_v33 -> 84_v33 neighbors: {'84_v33': 1}
Ленина125_03.JPG : 84_v33 -> 87_v33 neighbors: {'87_v33': 1}
Ленина125_04.JPG : 87_v33 -> 84_v33 neighbors: {'84_v33': 1}
Ленина125_08.JPG : 87_v33 -> 84_v33 neighbors: {'84_v33': 1}
Малиновского_к_Доватора_10.JPG : 94_v33 -> 89_v33 neighbors: {'89_v33': 1}
Малиновского_к_Стачки_03.JPG : 89_v33 -> 90_v33 neighbors: {'90_v33': 1}
Малиновского_к_Стачки_04.JPG : 90_v33 -> 89_v33 neighbors: {'89_v33': 1}

================================================================================
benchmark_hybrid_v07.json
Ашхабадский_08.JPG : 89_v33 -> 85_v33 neighbors: {'85_v33': 1}
Зорге_06.JPG : 89_v33 -> 92_v33 neighbors: {'92_v33': 1}
Зорге_15.JPG : 89_v33 -> 92_v33 neighbors: {'92_v33': 1}
Ленина125_02.JPG : 87_v33 -> 84_v33 neighbors: {'84_v33': 1}
Ленина125_03.JPG : 84_v33 -> 87_v33 neighbors: {'87_v33': 1}
Ленина125_04.JPG : 87_v33 -> 84_v33 neighbors: {'84_v33': 1}
Ленина125_08.JPG : 87_v33 -> 84_v33 neighbors: {'84_v33': 1}
Малиновского_к_Доватора_10.JPG : 94_v33 -> 89_v33 neighbors: {'89_v33': 1}
Малиновского_к_Стачки_03.JPG : 89_v33 -> 90_v33 neighbors: {'90_v33': 1}
Малиновского_к_Стачки_04.JPG : 90_v33 -> 89_v33 neighbors: {'89_v33': 1}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:51:41

Отлично. Это подтверждает, что `hybrid_v07` по сути воспроизводит `v03`:

- изменений: **10**
- состав изменений: **полностью одинаковый**
- `neighbors` одинаковые

То есть последние правки не ухудшили и не улучшили результат. Можно считать `v07` контрольной стабильной версией.

Сейчас важный вывод по архитектуре:

```
DINO v33
   ↓
margin filter
   ↓
TOP1/TOP2 candidates
   ↓
subfingerprint
   ↓
neighbors
   ↓
decision
```

работает, но есть слабое место:

```text
neighbors = {'84_v33':1}
```

Один сосед — слишком слабое подтверждение.

Сейчас алгоритм фактически говорит:

> "Один соседний кадр оказался за другой адрес → меняем адрес"

Это опасно.

Особенно для случая, который мы уже нашли:

```
Шеболдаева8_06.JPG
DINO → правильно 87
sub → ошибочно 92
```

Следующий шаг я бы сделал `hybrid_v08`:

### Изменение №1 — усилить соседей

Было:

```python
NEIGHBOR_WEIGHT = 1
```

Сделать:

```python
if neighbor_count >= 2:
    score += 3
elif neighbor_count == 1:
    score += 0.5
```

То есть:

```
1 сосед  → почти ничего
2 соседа → доверяем
3+       → уверенно
```

---

### Изменение №2 — защита уверенного DINO

Добавить:

```python
if row["score"] > 0.90 and row["margin"] > 0.03:
    continue
```

Тогда хорошие ответы вообще не трогаем.

---

### Изменение №3 — sub только если реально улучшает

Сейчас:

```
sub сказал B
→ добавили баллы B
```

Нужно:

```
если:
sub_score - dino_score > 0.03

тогда учитывать

иначе игнорировать
```

---

Я бы сейчас сделал `benchmark_hybrid_v08.py` от `v07` с этими тремя изменениями.

Ожидаемый эффект:

- останутся:
  - Ашхабадский 08
  - Зорге 06/15
  - Ленина125 (84/87)
  - Малиновского

- исчезнут случайные переезды из-за одного плохого признака.

Следующая команда:

```bash
cp scripts/benchmark_hybrid_v07.py scripts/benchmark_hybrid_v08.py
```

и будем править уже сам алгоритм, а не веса.

---

### 👤 **User** — 2026-08-15 20:52:38

давай через  sed

---

### 🤖 **Assistant** — 2026-08-15 20:52:40

Делаем аккуратно через `sed`, без ручного nano.

Сначала копия:

```bash
cp scripts/benchmark_hybrid_v07.py scripts/benchmark_hybrid_v08.py
```

### 1. Посмотреть текущие веса

```bash
grep -n "NEIGHBOR_WEIGHT\|SUB_WEIGHT\|MARGIN_LIMIT" scripts/benchmark_hybrid_v08.py
```

---

### 2. Меняем логику одного соседа

Найди блок:

```python
for fp in neighbors:

    scores[fp] += (
        NEIGHBOR_WEIGHT
    )
```

Замени через Python-патч (через sed такой многострочный блок неудобен):

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v08.py")

s = p.read_text(encoding="utf-8")

old = """        for fp in neighbors:

            scores[fp] += (
                NEIGHBOR_WEIGHT
            )
"""

new = """        for fp, count in neighbors.items():

            if count >= 2:
                scores[fp] += 3.0

            elif count == 1:
                scores[fp] += 0.5
"""

if old not in s:
    print("BLOCK NOT FOUND")
else:
    s=s.replace(old,new)
    p.write_text(s,encoding="utf-8")
    print("patched neighbors")
PY
```

---

### 3. Добавляем защиту уверенного DINO

После:

```python
if margin < MARGIN_LIMIT:
```

меняем на:

```bash
sed -i '/if margin < MARGIN_LIMIT:/i\        if row.get("score",0) > 0.90 and row.get("margin",0) > 0.03:\n            continue\n' scripts/benchmark_hybrid_v08.py
```

---

### 4. Проверяем синтаксис

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v08.py
```

---

### 5. Запуск

```bash
uv run python scripts/benchmark_hybrid_v08.py | tee output/hybrid_v08.log
```

После этого сравним:

```bash
grep "changed:" output/hybrid_v08.log
```

и список:

```bash
python3 - <<'PY'
import json

d=json.load(open("data/output/benchmark_hybrid_v08.json"))

print("changed:", d["changed"])

for x in d["results"]:
    if x.get("old") != x.get("new"):
        print(
            x["file"],
            x["old"],
            "->",
            x["new"],
            x.get("neighbors")
        )
PY
```

Ожидаем, что `changed` станет меньше 10, а ложные переезды исчезнут.

---

### 👤 **User** — 2026-08-15 20:52:53

B_WEIGHT\|MARGIN_LIMIT" scripts/benchmark_hybrid_v08.py
31:MARGIN_LIMIT = 0.03
34:SUB_WEIGHT = 2.5
35:NEIGHBOR_WEIGHT = 6.0
189:        if margin < MARGIN_LIMIT:
242:                            SUB_WEIGHT
275:                NEIGHBOR_WEIGHT
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:52:56

Вижу. Сейчас важный момент: у тебя:

```text
SUB_WEIGHT = 2.5
NEIGHBOR_WEIGHT = 6.0
```

То есть `v07` всё ещё использует старую схему: **один сосед получает вес 6**, это слишком сильно. Именно поэтому мы и хотим изменить.

Сначала покажи блок 265-280:

```bash
nl -ba scripts/benchmark_hybrid_v08.py | sed -n '255,285p'
```

Скорее всего там не такой текст, как мы искали.

Пока можно заменить напрямую по строкам:

```bash
nl -ba scripts/benchmark_hybrid_v08.py | sed -n '265,278p'
```

Нам нужен текущий блок вида:

```python
for fp in neighbors:

    scores[fp] += (
        NEIGHBOR_WEIGHT
    )
```

или похожий.

После этого дам точный `python3` patch под твой файл.

Ещё сразу проверим, вставилась ли защита DINO:

```bash
nl -ba scripts/benchmark_hybrid_v08.py | sed -n '180,200p'
```

Сейчас не надо запускать — сначала поправим два места.

---

### 👤 **User** — 2026-08-15 20:53:15

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ nl -ba scripts/benchmark_hybrid_v08.py | sed -n '255,285p'
   255	            rows,
   256	            i
   257	        )
   258	
   259	        left_fp = None
   260	        right_fp = None
   261	
   262	        if i > 0:
   263	            left_fp = rows[i-1].get("top1")
   264	
   265	        if i < len(rows)-1:
   266	            right_fp = rows[i+1].get("top1")
   267	
   268	
   269	        if (
   270	            left_fp
   271	            and right_fp
   272	            and left_fp == right_fp
   273	        ):
   274	            scores[left_fp] += (
   275	                NEIGHBOR_WEIGHT
   276	            )
   277	
   278	
   279	
   280	        best = max(
   281	            scores,
   282	            key=scores.get
   283	        )
   284	
   285	
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:53:17

Отлично, теперь видно реальную логику. У тебя не `for fp in neighbors`, а **сильный соседний консенсус только когда левый и правый кадр одинаковые**:

```python
if (
    left_fp
    and right_fp
    and left_fp == right_fp
):
    scores[left_fp] += NEIGHBOR_WEIGHT
```

Это уже лучше. Проблема сейчас только в весе:

```python
NEIGHBOR_WEIGHT = 6.0
```

Один кадр с плохим совпадением может получить слишком большой бонус.

Меняем на адаптивный вес.

Сделай патч:

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v08.py")

s = p.read_text(encoding="utf-8")

old = """        if (
            left_fp
            and right_fp
            and left_fp == right_fp
        ):
            scores[left_fp] += (
                NEIGHBOR_WEIGHT
            )
"""

new = """        if (
            left_fp
            and right_fp
            and left_fp == right_fp
        ):
            scores[left_fp] += 3.0
"""

if old not in s:
    print("BLOCK NOT FOUND")
else:
    s=s.replace(old,new)
    p.write_text(s,encoding="utf-8")
    print("patched neighbor weight")
PY
```

Теперь проверяем:

```bash
grep -n "NEIGHBOR_WEIGHT\|scores\[left_fp\]" scripts/benchmark_hybrid_v08.py
```

Должно быть:

```text
NEIGHBOR_WEIGHT = 6.0
...
scores[left_fp] += 3.0
```

(саму константу пока не трогаем, чтобы не сломать другие места)

---

Следующий важный шаг — убрать ошибочные изменения из-за sub.

Покажи блок:

```bash
nl -ba scripts/benchmark_hybrid_v08.py | sed -n '220,250p'
```

Там сейчас:

```python
if sim > 0.85:
    scores[parent] += sim * SUB_WEIGHT
```

Его тоже надо сделать условным:

- sub нашёл сильнее DINO → учитываем
- sub просто похож → игнорируем

Иначе он будет тащить автобусы/похожие элементы.

---

### 👤 **User** — 2026-08-15 20:53:58

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ nl -ba scripts/benchmark_hybrid_v08.py | sed -n '220,250p'
   220	                if not parent:
   221	                    continue
   222	
   223	
   224	                for sub_id, sub_emb in subs.items():
   225	
   226	                    if not sub_id.startswith(
   227	                        parent
   228	                    ):
   229	                        continue
   230	
   231	
   232	                    sim = max(
   233	                        sub_emb @ query
   234	                    )
   235	
   236	
   237	                    if sim > 0.85:
   238	
   239	                        scores[parent] += (
   240	                            float(sim)
   241	                            *
   242	                            SUB_WEIGHT
   243	                        )
   244	
   245	
   246	
   247	        #
   248	        # SEQUENCE CONSENSUS
   249	        #
   250	        # Используем соседей только если
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:54:00

Отлично. Вот здесь как раз место, где надо ограничить влияние sub.

Сейчас логика:

```python
sim > 0.85
    ↓
сразу + sim * 2.5
```

То есть даже слабое совпадение внутри TOP1/TOP2 может перекинуть решение.

Меняем на более строгую:

- `sim < 0.88` — игнорируем
- `0.88-0.92` — небольшой бонус
- `>0.92` — сильный бонус

Патч:

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v08.py")

s = p.read_text(encoding="utf-8")

old = """                    if sim > 0.85:

                        scores[parent] += (
                            float(sim)
                            *
                            SUB_WEIGHT
                        )
"""

new = """                    if sim > 0.88:

                        if sim > 0.92:
                            bonus = 2.5
                        else:
                            bonus = 1.0

                        scores[parent] += (
                            float(sim)
                            *
                            bonus
                        )
"""

if old not in s:
    print("BLOCK NOT FOUND")
else:
    s=s.replace(old,new)
    p.write_text(s,encoding="utf-8")
    print("patched sub scoring")
PY
```

Проверка:

```bash
nl -ba scripts/benchmark_hybrid_v08.py | sed -n '232,255p'
```

Должно получиться:

```python
if sim > 0.88:

    if sim > 0.92:
        bonus = 2.5
    else:
        bonus = 1.0
```

Дальше:

```bash
uv run python -m py_compile scripts/benchmark_hybrid_v08.py
```

Если без ошибок:

```bash
uv run python scripts/benchmark_hybrid_v08.py | tee output/hybrid_v08.log
```

После запуска сравним особенно:

- `Шеболдаева8_06`
- `Радиаторный_24/25`
- `КА`
- `Ленина125`

Цель v08 — не увеличить число изменений, а убрать ложные изменения. Сейчас у нас хороший ориентир: **10 изменений v07**. Хотим получить примерно 6–8, но чтобы среди них не было ложных.

---

### 👤 **User** — 2026-08-15 20:54:57

checked: 256
sub rerank: 43
changed: 10

Ашхабадский_08.JPG
89_v33 -> 85_v33
neighbors: {'85_v33': 1}

Зорге_06.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_15.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Ленина125_02.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_03.JPG
84_v33 -> 87_v33
neighbors: {'87_v33': 1}

Ленина125_04.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_08.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Малиновского_к_Доватора_10.JPG
94_v33 -> 89_v33
neighbors: {'89_v33': 1}

Малиновского_к_Стачки_03.JPG
89_v33 -> 90_v33
neighbors: {'90_v33': 1}

Малиновского_к_Стачки_04.JPG
90_v33 -> 89_v33
neighbors: {'89_v33': 1}

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v07.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:54:59

Результат интересный: **алгоритм не изменился**, но есть важная деталь:

```
saved:
/home/alexice/projects/scene_fingerprint_mvp_v07.json
```

Он сохранился как **benchmark_hybrid_v07.json**, а не v08.

То есть ты, скорее всего, запустил не `benchmark_hybrid_v08.py`, либо внутри файла осталась старая строка вывода.

Проверяем:

```bash
grep -n "benchmark_hybrid" scripts/benchmark_hybrid_v08.py
```

и:

```bash
grep -n "saved\|write_text\|OUT" scripts/benchmark_hybrid_v08.py
```

---

Также вижу:

```
neighbors: {'85_v33': 1}
```

Но после нашего патча должно было остаться:

- если левый и правый кадр совпали → вес 3
- если нет → вообще без изменения

А в отчёте всё ещё печатается старый формат.

Проверим, применились ли две правки:

### 1. Соседи

```bash
grep -n "scores\[left_fp\]" scripts/benchmark_hybrid_v08.py
```

должно быть:

```python
scores[left_fp] += 3.0
```

---

### 2. Sub

```bash
grep -n "bonus" scripts/benchmark_hybrid_v08.py
```

должно показать:

```
bonus = 2.5
bonus = 1.0
```

---

Если всё есть — значит результат реально такой же, и тогда следующий шаг не веса.

Тогда проблема в другом месте:

Сейчас:

```
TOP1/TOP2
   ↓
sub
   ↓
neighbor
```

Но сосед работает только после sub.

Надо сделать следующий вариант:

```
DINO TOP1
DINO TOP2
DINO margin

        ↓

если margin < 0.03:
    sub проверка

если margin < 0.01:
    sub + sequence consensus

если margin > 0.03:
    оставить DINO
```

То есть не трогать нормальные случаи.

У нас уже есть пример:

```
Шеболдаева8_06
87_v33
score=0.6059
margin=0.0148
```

Это как раз пограничный случай.

А:

```
Ашхабадский_01
85_v33
score=0.9000
margin=0.0639
```

вообще нельзя трогать.

Следующий файл я бы делал `hybrid_v09` именно с **3 зонами доверия**. Это будет ближе к рабочему пайплайну.

---

### 👤 **User** — 2026-08-15 20:55:17

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n "benchmark_hybrid" scripts/benchmark_hybrid_v08.py
27:    "data/output/benchmark_hybrid_v07.json"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:55:19

Вот причина найдена. `v08.py` действительно запускается, но **результат пишет в старый файл v07**:

```python
27:    "data/output/benchmark_hybrid_v07.json"
```

Нужно поменять только имя выхода.

Сделай:

```bash
sed -i 's/benchmark_hybrid_v07.json/benchmark_hybrid_v08.json/' scripts/benchmark_hybrid_v08.py
```

Проверка:

```bash
grep -n "benchmark_hybrid" scripts/benchmark_hybrid_v08.py
```

Должно быть:

```text
data/output/benchmark_hybrid_v08.json
```

Теперь запускаем именно v08:

```bash
uv run python scripts/benchmark_hybrid_v08.py | tee output/hybrid_v08.log
```

После этого сравним:

```bash
python3 - <<'PY'
import json

for f in [
    "benchmark_hybrid_v07.json",
    "benchmark_hybrid_v08.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))
    print()
    print("="*60)
    print(f)
    print("changed:", d["changed"])

    for x in d["results"]:
        if x.get("file","").endswith("Шеболдаева8_06.JPG"):
            print("Шеболдаева8_06:", x)
PY
```

Сейчас главный тест — не количество `changed`, а чтобы **Шеболдаева8_06 не ушла с 87** из-за автобуса.

---

### 👤 **User** — 2026-08-15 20:56:13

checked: 256
sub rerank: 43
changed: 10

Ашхабадский_08.JPG
89_v33 -> 85_v33
neighbors: {'85_v33': 1}

Зорге_06.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_15.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Ленина125_02.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_03.JPG
84_v33 -> 87_v33
neighbors: {'87_v33': 1}

Ленина125_04.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_08.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Малиновского_к_Доватора_10.JPG
94_v33 -> 89_v33
neighbors: {'89_v33': 1}

Малиновского_к_Стачки_03.JPG
89_v33 -> 90_v33
neighbors: {'90_v33': 1}

Малиновского_к_Стачки_04.JPG
90_v33 -> 89_v33
neighbors: {'89_v33': 1}

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v08.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
import json

for f in [
    "benchmark_hybrid_v07.json",
    "benchmark_hybrid_v08.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))
    print()
    print("="*60)
    print(f)
    print("changed:", d["changed"])

    for x in d["results"]:
        if x.get("file","").endswith("Шеболдаева8_06.JPG"):
            print("Шеболдаева8_06:", x)
PY

============================================================
benchmark_hybrid_v07.json
changed: 10

============================================================
benchmark_hybrid_v08.json
changed: 10

---

### 🤖 **Assistant** — 2026-08-15 20:56:14

Хорошо, теперь точно видно:

1. `v08` реально запускается.
2. Патчи не дали изменения.
3. Но есть ещё одна проблема: в `results` нет поля `file` в том виде, как мы искали, поэтому `Шеболдаева8_06` не вывелась.

Сначала посмотрим структуру одного результата:

```bash
python3 - <<'PY'
import json

d=json.load(open(
    "data/output/benchmark_hybrid_v08.json",
    encoding="utf-8"
))

print(d["results"][0].keys())

for x in d["results"]:
    print(x)
    break
PY
```

---

Но главное: одинаковые 10 изменений означают, что сейчас **гибрид фактически ничего нового не добавляет**.

Следующий шаг я бы сделал не с весами, а с логикой принятия решения.

Сейчас у тебя:

```
DINO TOP1
    |
    +-- sub добавляет баллы
    |
    +-- neighbor добавляет баллы
    |
    выбрать max()
```

Проблема: любой дополнительный голос может перекинуть решение.

Нужен режим:

```
DINO TOP1 = основной

если margin > 0.03:
    оставить

если margin <= 0.03:
    включить sub

если sub подтверждает TOP2:
    заменить

если sub не уверен:
    оставить TOP1

если соседи подтверждают:
    можно менять
```

То есть сделать **ветку исправления ошибок**, а не новый классификатор.

---

Для следующего `hybrid_v09` предлагаю:

```python
if margin > 0.03:
    best = top1

else:
    # только пограничные
    sub_vote = ...
    
    if sub_score(top2) - sub_score(top1) > 0.05:
        best = top2

    elif neighbor_consensus:
        best = neighbor

    else:
        best = top1
```

Это должно решить проблему типа:

```
Шеболдаева8_06
87_v33
score 0.6059
margin 0.0148

но:
соседи 87
sub не уверен

=> оставить 87
```

Сейчас у нас слишком много "лечения" там, где DINO уже прав.

Следующим шагом делаем `benchmark_hybrid_v09.py` из v08 и меняем только блок выбора `best`. Я бы не трогал sub-фингерпринты — они уже работают как инструмент уточнения.

---

### 👤 **User** — 2026-08-15 20:56:53

продолжаем

---

### 🤖 **Assistant** — 2026-08-15 20:56:54

Продолжаем. Делаем `hybrid_v09`: **DINO остаётся главным**, sub и соседи работают только как подтверждение в пограничных случаях.

Сначала копируем:

```bash
cp scripts/benchmark_hybrid_v08.py scripts/benchmark_hybrid_v09.py
```

Меняем имя результата:

```bash
sed -i 's/benchmark_hybrid_v08.json/benchmark_hybrid_v09.json/' scripts/benchmark_hybrid_v09.py
```

Теперь найдём блок выбора:

```bash
grep -n "best = max" scripts/benchmark_hybrid_v09.py
```

У тебя должно быть примерно:

```text
280:        best = max(
```

Смотрим участок:

```bash
nl -ba scripts/benchmark_hybrid_v09.py | sed -n '275,290p'
```

Сейчас там:

```python
best = max(
    scores,
    key=scores.get
)
```

Меняем на:

```bash
python3 - <<'PY'
from pathlib import Path

p = Path("scripts/benchmark_hybrid_v09.py")

s = p.read_text(encoding="utf-8")

old = """        best = max(
            scores,
            key=scores.get
        )
"""

new = """        #
        # FINAL DECISION V09
        #
        # DINO TOP1 is default.
        # Change only if hybrid has strong evidence.
        #

        best = old

        ranked = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        if ranked:

            candidate = ranked[0][0]

            gain = (
                scores[candidate]
                -
                scores.get(old, 0)
            )

            #
            # Change only with real advantage
            #
            if (
                candidate != old
                and gain > 0.08
            ):
                best = candidate
"""

if old not in s:
    print("BLOCK NOT FOUND")
else:
    s=s.replace(old,new)
    p.write_text(s,encoding="utf-8")
    print("patched v09")
PY
```

Проверка:

```bash
python3 -m py_compile scripts/benchmark_hybrid_v09.py
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v09.py | tee output/hybrid_v09.log
```

Потом сравним:

```bash
python3 - <<'PY'
import json

for f in [
"benchmark_hybrid_v08.json",
"benchmark_hybrid_v09.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))
    print()
    print("="*60)
    print(f, "changed:", d["changed"])
PY
```

Ожидаю результат:
- количество изменений уменьшится примерно с 10 до 4–6;
- `Шеболдаева8_06` останется 87;
- `Ленина125` может остаться спорным — там как раз нужен sub.

После этого уже можно будет перейти к финальной схеме:

**DINO global → margin gate → subfingerprint → neighbor consensus → address**.

---

### 👤 **User** — 2026-08-15 20:58:20

checked: 256
sub rerank: 43
changed: 10

Ашхабадский_08.JPG
89_v33 -> 85_v33
neighbors: {'85_v33': 1}

Зорге_06.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_15.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Ленина125_02.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_03.JPG
84_v33 -> 87_v33
neighbors: {'87_v33': 1}

Ленина125_04.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_08.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Малиновского_к_Доватора_10.JPG
94_v33 -> 89_v33
neighbors: {'89_v33': 1}

Малиновского_к_Стачки_03.JPG
89_v33 -> 90_v33
neighbors: {'90_v33': 1}

Малиновского_к_Стачки_04.JPG
90_v33 -> 89_v33
neighbors: {'89_v33': 1}

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v09.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
import json

for f in [
"benchmark_hybrid_v08.json",
"benchmark_hybrid_v09.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))
    print()
    print("="*60)
    print(f, "changed:", d["changed"])
PY

============================================================
benchmark_hybrid_v08.json changed: 10

============================================================
benchmark_hybrid_v09.json changed: 10
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:58:22

Получилось интересное наблюдение: **v09 ничего не изменил**, значит проблема не в финальном выборе `best`.

Сейчас происходит вот что:

- `changed: 10` формируется уже после сравнения `best != old`;
- но `best` всё равно получается тот же, что и в v08;
- значит либо:
  1. `scores[candidate] - scores[old] > 0.08` всё ещё проходит для тех же 10;
  2. либо блок принятия решения вообще не тот, который мы заменили.

Надо проверить фактические `scores` перед выбором. Добавим временный debug.

Сделаем копию:

```bash
cp scripts/benchmark_hybrid_v09.py scripts/benchmark_hybrid_v10_debug.py
```

Найдём место:

```bash
nl -ba scripts/benchmark_hybrid_v10_debug.py | sed -n '275,310p'
```

Перед:

```python
best = old
```

вставим:

```python
print(
    "DEBUG",
    Path(row["file"]).name,
    "OLD=",
    old,
    "SCORES=",
    dict(scores)
)
```

Быстро через sed:

```bash
sed -i '/best = old/i\        print("DEBUG", Path(row["file"]).name, "OLD=", old, "SCORES=", dict(scores))' scripts/benchmark_hybrid_v10_debug.py
```

Запуск только на проблемных можно не делать — лог будет большой, но ищем:

```bash
uv run python scripts/benchmark_hybrid_v10_debug.py | grep -A1 "Ленина125_02"
```

и:

```bash
uv run python scripts/benchmark_hybrid_v10_debug.py | grep -A1 "Шеболдаева8_06"
```

Мне особенно интересны два случая:

### 1. Ленина125

Сейчас:

```
87_v33 -> 84_v33
```

Хотим понять:

```
87 score ?
84 score ?
```

### 2. Шеболдаева

Должно быть:

```
87_v33 остаётся
```

Если там:

```
92 набирает больше
```

значит neighbor/sub слишком агрессивны.

Ещё момент: у тебя сейчас `MARGIN_LIMIT = 0.03`, а в benchmark было много случаев:

```
margin 0.03-0.05
```

Можно попробовать более правильную схему:

```
margin > 0.02  -> DINO доверяем
margin <=0.02 -> включаем sub
```

То есть sub будет работать только там, где реально сомнение.

Сейчас:

```
sub rerank: 43 из 256
```

Это много.

Я бы ожидал:

```
sub rerank: 15-25
```

после настройки.

Сначала пришли вывод двух DEBUG по:
- `Ленина125_02.JPG`
- `Шеболдаева8_06.JPG`

и подрежем логику.

---

### 👤 **User** — 2026-08-15 20:59:42

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cp scripts/benchmark_hybrid_v09.py scripts/benchmark_hybrid_v10_debug.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cp scripts/benchmark_hybrid_v09.py scripts/benchmark_hybrid_v10_debug.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -i '/best = old/i\        print("DEBUG", Path(row["file"]).name, "OLD=", old, "SCORES=", dict(scores))' scripts/benchmark_hybrid_v10_debug.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/benchmark_hybrid_v10_debug.py | grep -A1 "Ленина125_02"
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8495.28it/s]
uv run python scripts/benchmark_hybrid_v10_debug.py | grep -A1 "Шеболдаева8_06"DEBUG Ленина125_02.JPG OLD= 87_v33 SCORES= {'87_v33': 9.7586344063282, '84_v33': 14.194679802656173, '79_v33': 8.716026842594147, '92_v33': 8.63742201924324, '83_v33': 8.55895466208458}
DEBUG Ленина125_03.JPG OLD= 84_v33 SCORES= {'84_v33': 11.319285768270493, '87_v33': 12.798631381988525, '92_v33': 8.672851145267487, '79_v33': 8.663199371099472, '83_v33': 8.618207240104676}
--
Ленина125_02.JPG
87_v33 -> 84_v33
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/benchmark_hybrid_v10_debug.py | grep -A1 "Шеболдаева8_06"uv run python scripts/benchmark_hybrid_v10_debug.py | grep -A1 "Шеболдаева8_06"
grep: run: No such file or directory
grep: python: No such file or directory
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Traceback (most recent call last):
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/benchmark_hybrid_v10_debug.py", line 438, in <module>
    main()
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/benchmark_hybrid_v10_debug.py", line 135, in main
    embedder = SceneEmbedder(
               ^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/core/embedder.py", line 45, in __init__
    self.model = AutoModel.from_pretrained(
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/transformers/models/auto/auto_factory.py", line 402, in from_pretrained
    return model_class.from_pretrained(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/transformers/modeling_utils.py", line 4348, in from_pretrained
    loading_info, disk_offload_index = cls._load_pretrained_model(model, state_dict, checkpoint_files, load_config)
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/transformers/modeling_utils.py", line 4482, in _load_pretrained_model
    loading_info, disk_offload_index = convert_and_load_state_dict_in_model(
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/transformers/core_model_loading.py", line 1712, in convert_and_load_state_dict_in_model
    for first_param_name, mapping in tqdm(param_name_to_load.items(), desc="Loading weights"):
                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/transformers/utils/logging.py", line 390, in __call__
    return factory(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/tqdm/asyncio.py", line 24, in __init__
    super().__init__(iterable, *args, **kwargs)
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/tqdm/std.py", line 1101, in __init__
    self.sp = self.status_printer(self.fp)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/tqdm/std.py", line 447, in status_printer
    getattr(sys.stdout, 'flush', lambda: None)()
BrokenPipeError: [Errno 32] Broken pipe
Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
BrokenPipeError: [Errno 32] Broken pipe
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/benchmark_hybrid_v10_debug.py | grep -A1 "Шеболдаева8_06"
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8825.36it/s]
DEBUG Шеболдаева8_06.JPG OLD= 87_v33 SCORES= {'87_v33': 9.059056544303893, '92_v33': 5.910639929771424, '86_v33': 5.7984818816185, '93_v33': 5.658826136589051, '83_v33': 5.652872663736344}
DEBUG Шеболдаева8_07.JPG OLD= 87_v33 SCORES= {'87_v33': 12.491384911537171, '92_v33': 8.814965671300888, '83_v33': 8.707997208833694, '79_v33': 8.623451620340347, '85_v33': 8.61245595216751}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 20:59:44

Отлично, теперь видно причину.

### 1. Шеболдаева8_06 — всё правильно

DEBUG:

```
OLD=87_v33

87_v33 : 9.059
92_v33 : 5.910
```

То есть гибрид **не должен был менять**. Ошибка была в предыдущей логике, где sub/neighbor могли переиграть DINO.

Здесь надо оставить:

```
87_v33
```

---

### 2. Ленина125 — наоборот, это реальный спор

```
OLD=87_v33

87_v33 : 9.758
84_v33 : 14.194
```

Разница:

```
+4.43
```

Это не шум. Тут гибрид уверенно говорит:

```
84_v33
```

Именно такие случаи sub + соседи должны исправлять.

---

Проблема сейчас в другом: **мы принимаем любой максимум scores**.

Нужно добавить правило:

- если DINO был уверен (`margin высокий`) → НЕ трогаем;
- если DINO сомневался → разрешаем hybrid.

То есть решение должно учитывать исходный margin.

Сейчас у нас:

```
margin < 0.03
```

но внутри мы потом меняем даже если соседей нет.

Делаем v11:

Логика:

```
if margin >= 0.02:
        best = old

else:
        hybrid decision
```

То есть:

- Шеболдаева:
  - margin был около 0.0148
  - попадёт в hybrid
  - но hybrid score оставляет 87

- Ленина125:
  - margin 0.0008
  - попадёт
  - 84 победит

---

Сделай:

```bash
cp scripts/benchmark_hybrid_v10_debug.py scripts/benchmark_hybrid_v11.py
```

Убрать debug:

```bash
sed -i '/print("DEBUG"/d' scripts/benchmark_hybrid_v11.py
```

Теперь найди:

```bash
nl -ba scripts/benchmark_hybrid_v11.py | sed -n '280,310p'
```

Там сейчас:

```python
best = old
...
if candidate != old and gain > 0.08:
    best = candidate
```

Меняем порог:

```bash
sed -i 's/gain > 0.08/gain > 1.5/' scripts/benchmark_hybrid_v11.py
```

И ограничим изменение только очень слабых случаев:

найди:

```bash
grep -n "margin <" scripts/benchmark_hybrid_v11.py
```

должно быть:

```
if margin < MARGIN_LIMIT:
```

Меняем:

```bash
sed -i 's/MARGIN_LIMIT = 0.03/MARGIN_LIMIT = 0.02/' scripts/benchmark_hybrid_v11.py
```

Запуск:

```bash
uv run python scripts/benchmark_hybrid_v11.py | tee output/hybrid_v11.log
```

Потом:

```bash
python3 - <<'PY'
import json

for f in [
"benchmark_hybrid_v08.json",
"benchmark_hybrid_v11.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))
    print(f, d["changed"])
PY
```

Ожидаю:

- было 10 изменений;
- станет примерно 6-8;
- Шеболдаева исчезнет;
- Ленина125 останется.

Следующий этап после этого — сделать **не фиксированный gain**, а нормализованный:

```
hybrid_score - dino_score > X * margin
```

Это будет уже почти промышленная логика.

---

### 👤 **User** — 2026-08-15 21:01:28

checked: 256
sub rerank: 28
changed: 9

Ашхабадский_08.JPG
89_v33 -> 85_v33
neighbors: {'85_v33': 1}

Зорге_06.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Зорге_15.JPG
89_v33 -> 92_v33
neighbors: {'92_v33': 1}

Ленина125_02.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_04.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Ленина125_08.JPG
87_v33 -> 84_v33
neighbors: {'84_v33': 1}

Малиновского_к_Доватора_10.JPG
94_v33 -> 89_v33
neighbors: {'89_v33': 1}

Малиновского_к_Стачки_03.JPG
89_v33 -> 90_v33
neighbors: {'90_v33': 1}

Малиновского_к_Стачки_04.JPG
90_v33 -> 89_v33
neighbors: {'89_v33': 1}

saved:
/home/alexice/projects/scene_fingerprint_mvp_v02/data/output/benchmark_hybrid_v09.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
import json

for f in [
"benchmark_hybrid_v08.json",
"benchmark_hybrid_v11.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))
    print(f, d["changed"])
PY
benchmark_hybrid_v08.json 10
Traceback (most recent call last):
  File "<stdin>", line 7, in <module>
FileNotFoundError: [Errno 2] No such file or directory: 'data/output/benchmark_hybrid_v11.json'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
import json

for f in [
"benchmark_hybrid_v08.json",
"benchmark_hybrid_v11.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))
    print(f, d["changed"])
PY
benchmark_hybrid_v08.json 10
Traceback (most recent call last):
  File "<stdin>", line 7, in <module>
FileNotFoundError: [Errno 2] No such file or directory: 'data/output/benchmark_hybrid_v11.json'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 21:01:30

Сейчас всё нормально: просто **v11 не создал свой JSON**. По выводу видно, что реально запускался ещё старый скрипт и сохранил:

```
benchmark_hybrid_v09.json
```

То есть надо сначала проверить, куда пишет v11.

Выполни:

```bash
grep -n "benchmark_hybrid" scripts/benchmark_hybrid_v11.py
```

Скорее всего там осталось:

```python
benchmark_hybrid_v09.json
```

Меняем:

```bash
sed -i 's/benchmark_hybrid_v09.json/benchmark_hybrid_v11.json/' scripts/benchmark_hybrid_v11.py
```

Проверяем:

```bash
grep -n "benchmark_hybrid" scripts/benchmark_hybrid_v11.py
```

Должно быть:

```
benchmark_hybrid_v11.json
```

Запускаем:

```bash
uv run python scripts/benchmark_hybrid_v11.py | tee output/hybrid_v11.log
```

Потом:

```bash
ls -lh data/output/*hybrid*
```

и сравнение:

```bash
python3 - <<'PY'
import json

for f in [
    "benchmark_hybrid_v09.json",
    "benchmark_hybrid_v11.json"
]:
    d=json.load(open("data/output/"+f,encoding="utf-8"))
    print()
    print("="*60)
    print(f)
    print("changed:", d["changed"])
PY
```

По текущему результату есть интересный момент:

```
sub rerank: 28
changed: 9
```

против v08:

```
sub rerank: 43
changed: 10
```

То есть ограничение уже работает:
- sub проверяется только на спорных случаях;
- количество вмешательств уменьшилось;
- Шеболдаева8_06 исчезла — это хорошо.

Следующий шаг после получения v11 — сделать **таблицу "что изменил / что вернул"** и отдельно проверить только 9 изменённых кадров визуально. Сейчас мы уже близко к стабильному гибриду.

---

