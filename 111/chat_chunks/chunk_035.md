## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 🤖 **Assistant** — 2026-08-15 03:49:21

Да. По этому выводу видно, что **v3.3 сейчас работает и fingerprints 78-95 действительно загружены**, но есть важный момент.

### Что видно по результату

Для большинства фотографий система уверенно выбирает **78_v33**:

- `00 (1).JPG` → 78, **0.9468**
- `00 (4).JPG` → 78, **0.9510**
- `001.JPG` → 78, **0.9470**
- `002.JPG` → 78, **0.9469**
- `003.JPG` → 78, **0.9508**

То есть сам механизм сравнения работает.

Но:

> `00 (8).JPG → 79_v33 0.9180`

Это хороший признак - система **не прибивает всё подряд к 78**, а способна выбрать 79.

### Но есть подозрительный момент

Вторые кандидаты у 78 очень близкие:

```text
78  0.9468
92  0.8923
91  0.8882
95  0.8842
83  0.8808
```

То есть между объектами `78`, `91`, `92`, `95`, `83` существует довольно сильная визуальная похожесть.

Это **не обязательно ошибка**. Для нашего проекта это как раз ожидаемая проблема: соседние/похожие адреса могут иметь практически одинаковый общий фон, дорогу, дома, деревья и т.п.

---

## Сейчас я бы ничего в алгоритме не менял

Мы как раз вернули **старую логику распознавания**, оставив оптимизации v3.3.

Следующий правильный шаг - **не смотреть на отдельные фотографии**, а проверить весь `test` статистически.

Нам нужно получить примерно такую таблицу:

```text
INPUT              MATCH       SCORE    SECOND    MARGIN
00 (1).JPG         78          .9468    92        .0545
00 (8).JPG         79          .9180    92        .0552
...
```

И главное - распределение:

```text
78_v33   120 images
79_v33    35 images
80_v33     8 images
...
95_v33    12 images
```

### Ещё важнее

Нужно проверить **стабильность одного адреса**.

Если, например, 20 фотографий одного места дают:

```text
78 → 18 раз
92 → 1 раз
91 → 1 раз
```

то это нормально.

Если:

```text
78 → 11
92 → 7
91 → 2
```

тогда уже надо разбираться с различением этих адресов.

---

### Поэтому сейчас предлагаю следующий тест

Запустить распознавание всей `test` **только на 78_v33-95_v33** и одновременно сохранить результаты в файл.

У нас CLI уже умеет whitelist через:

```bash
--fingerprints
```

Так что запускаем:

```bash
uv run scene-fingerprint recognize data/input/test \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33,87_v33,88_v33,89_v33,90_v33,91_v33,92_v33,93_v33,94_v33,95_v33 \
  --top-k 5 \
  --threshold 0.65
```

**Но пока не надо ничего менять в коде.**

Сначала получим полный результат. После этого я бы сделал следующий этап: **автоматически собрать статистику по MATCH / SECOND / MARGIN и найти спорные адреса**. Именно они покажут, где старый алгоритм реально ошибается.

---

### 👤 **User** — 2026-08-15 03:50:10

Автоматически собрать статистику по MATCH / SECOND / MARGIN

---

### 🤖 **Assistant** — 2026-08-15 03:50:12

Да. Лучше не менять код распознавания, а сделать **отдельный анализатор уже готового лога**.

Если текущий вывод ещё не сохранён в файл — запусти распознавание так:

```bash
uv run scene-fingerprint recognize data/input/test \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33,87_v33,88_v33,89_v33,90_v33,91_v33,92_v33,93_v33,94_v33,95_v33 \
  --top-k 5 \
  --threshold 0.65 \
  2>&1 | tee /tmp/recognition_test.log
```

Потом автоматически соберём:

- сколько раз выбран каждый `MATCH`;
- средний / минимум / максимум `SCORE`;
- средний `SECOND`;
- средний `MARGIN`;
- количество `HIGH / MEDIUM / LOW`;
- самые спорные фотографии;
- пары адресов, которые чаще всего конкурируют между собой.

### Сразу после распознавания

Выполни этот блок:

```bash
python3 - <<'PY'
from pathlib import Path
import re
from collections import Counter, defaultdict
import statistics

log = Path("/tmp/recognition_test.log").read_text(encoding="utf-8", errors="ignore")

# Разбиваем лог на блоки фотографий
blocks = re.split(r'\n(?=## )', log)

rows = []

for block in blocks:
    m_file = re.search(r'^## (.+)$', block, re.M)
    m_match = re.search(r'^MATCH\s+(\S+)$', block, re.M)
    m_score = re.search(r'^SCORE\s+([0-9.]+)$', block, re.M)
    m_second = re.search(r'^SECOND\s+([0-9.]+)$', block, re.M)
    m_margin = re.search(r'^MARGIN\s+([0-9.]+)$', block, re.M)
    m_conf = re.search(r'^CONFIDENCE\s+(\S+)$', block, re.M)
    m_status = re.search(r'^STATUS\s+(\S+)$', block, re.M)

    if not all([m_file, m_match, m_score, m_second, m_margin]):
        continue

    rows.append({
        "file": m_file.group(1).strip(),
        "match": m_match.group(1),
        "score": float(m_score.group(1)),
        "second": float(m_second.group(1)),
        "margin": float(m_margin.group(1)),
        "confidence": m_conf.group(1) if m_conf else "",
        "status": m_status.group(1) if m_status else "",
    })

print()
print("=" * 90)
print("RECOGNITION STATISTICS")
print("=" * 90)
print(f"Images recognized: {len(rows)}")

if not rows:
    print("NO RESULTS FOUND")
    raise SystemExit

# ------------------------------------------------------------
# MATCH distribution
# ------------------------------------------------------------

cnt = Counter(r["match"] for r in rows)

print()
print("=" * 90)
print("MATCH DISTRIBUTION")
print("=" * 90)

for fp, n in sorted(cnt.items(), key=lambda x: (-x[1], x[0])):
    pct = n / len(rows) * 100
    print(f"{fp:<12} {n:5d}  {pct:6.2f}%")

# ------------------------------------------------------------
# Global statistics
# ------------------------------------------------------------

scores = [r["score"] for r in rows]
seconds = [r["second"] for r in rows]
margins = [r["margin"] for r in rows]

print()
print("=" * 90)
print("GLOBAL SCORE STATISTICS")
print("=" * 90)

def stats(name, values):
    print(
        f"{name:<10} "
        f"mean={statistics.mean(values):.4f}  "
        f"median={statistics.median(values):.4f}  "
        f"min={min(values):.4f}  "
        f"max={max(values):.4f}"
    )

stats("SCORE", scores)
stats("SECOND", seconds)
stats("MARGIN", margins)

# ------------------------------------------------------------
# Confidence
# ------------------------------------------------------------

print()
print("=" * 90)
print("CONFIDENCE")
print("=" * 90)

for k, n in Counter(r["confidence"] for r in rows).most_common():
    print(f"{k:<12} {n:5d}  {n/len(rows)*100:6.2f}%")

# ------------------------------------------------------------
# Status
# ------------------------------------------------------------

print()
print("=" * 90)
print("STATUS")
print("=" * 90)

for k, n in Counter(r["status"] for r in rows).most_common():
    print(f"{k:<16} {n:5d}  {n/len(rows)*100:6.2f}%")

# ------------------------------------------------------------
# Statistics by MATCH
# ------------------------------------------------------------

by_match = defaultdict(list)

for r in rows:
    by_match[r["match"]].append(r)

print()
print("=" * 90)
print("STATISTICS BY MATCH")
print("=" * 90)

print(
    f"{'MATCH':<12}"
    f"{'N':>6}"
    f"{'SCORE':>10}"
    f"{'SECOND':>10}"
    f"{'MARGIN':>10}"
)

for fp in sorted(by_match):
    rs = by_match[fp]

    print(
        f"{fp:<12}"
        f"{len(rs):6d}"
        f"{statistics.mean(r['score'] for r in rs):10.4f}"
        f"{statistics.mean(r['second'] for r in rs):10.4f}"
        f"{statistics.mean(r['margin'] for r in rs):10.4f}"
    )

# ------------------------------------------------------------
# Most ambiguous
# ------------------------------------------------------------

print()
print("=" * 90)
print("MOST AMBIGUOUS IMAGES — LOWEST MARGIN")
print("=" * 90)

for r in sorted(rows, key=lambda x: x["margin"])[:30]:
    print(
        f"{r['file']:<25} "
        f"{r['match']:<10} "
        f"score={r['score']:.4f} "
        f"second={r['second']:.4f} "
        f"margin={r['margin']:.4f}"
    )

# ------------------------------------------------------------
# Lowest SCORE
# ------------------------------------------------------------

print()
print("=" * 90)
print("LOWEST SCORE")
print("=" * 90)

for r in sorted(rows, key=lambda x: x["score"])[:30]:
    print(
        f"{r['file']:<25} "
        f"{r['match']:<10} "
        f"score={r['score']:.4f} "
        f"second={r['second']:.4f} "
        f"margin={r['margin']:.4f}"
    )

# ------------------------------------------------------------
# Most dangerous competing pairs
# ------------------------------------------------------------

pairs = Counter()

for block in blocks:
    m = re.search(r'^MATCH\s+(\S+)', block, re.M)
    candidates = re.findall(
        r'^\d+\.\s+(\S+)\s+[0-9.]+$',
        block,
        re.M
    )

    if m and len(candidates) >= 2:
        a = m.group(1)
        b = candidates[1]

        pair = tuple(sorted((a, b)))
        pairs[pair] += 1

print()
print("=" * 90)
print("MOST FREQUENT COMPETING PAIRS")
print("=" * 90)

for (a, b), n in pairs.most_common(30):
    print(f"{a:<12} <-> {b:<12} {n:5d}")

print()
print("=" * 90)
print("DONE")
print("=" * 90)
PY
```

### Что мы получим

Самое интересное будет примерно такое:

```text
MATCH DISTRIBUTION

78_v33        180   48.13%
79_v33         51   13.64%
80_v33         23    6.15%
...
```

И:

```text
STATISTICS BY MATCH

MATCH            N     SCORE    SECOND    MARGIN
78_v33         180    0.9341    0.8812    0.0529
79_v33          51    0.9217    0.8563    0.0654
...
```

А самое важное:

```text
MOST AMBIGUOUS IMAGES

photo123.JPG    78_v33   score=0.8912 second=0.8879 margin=0.0033
photo456.JPG    92_v33   score=0.9041 second=0.8998 margin=0.0043
```

и:

```text
MOST FREQUENT COMPETING PAIRS

78_v33 <-> 92_v33     37
78_v33 <-> 91_v33     29
83_v33 <-> 95_v33     18
```

**Вот последняя таблица сейчас особенно ценна.** Она покажет, какие именно адреса система постоянно путает. После этого можно будет отдельно проверить эти пары визуально и понять, нужен ли нам OCR/табличка только для сложных случаев, не ломая текущий v3.3.

---

### 👤 **User** — 2026-08-15 03:52:14

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
from pathlib import Path
import re
from collections import Counter, defaultdict
import statistics

log = Path("/tmp/recognition_test.log").read_text(encoding="utf-8", errors="ignore")

# Разбиваем лог на блоки фотографий
blocks = re.split(r'\n(?=## )', log)

rows = []

for block in blocks:
    m_file = re.search(r'^## (.+)$', block, re.M)
    m_match = re.search(r'^MATCH\s+(\S+)$', block, re.M)
    m_score = re.search(r'^SCORE\s+([0-9.]+)$', block, re.M)
    m_second = re.search(r'^SECOND\s+([0-9.]+)$', block, re.M)
    m_margin = re.search(r'^MARGIN\s+([0-9.]+)$', block, re.M)
    m_conf = re.search(r'^CONFIDENCE\s+(\S+)$', block, re.M)
    m_status = re.search(r'^STATUS\s+(\S+)$', block, re.M)

    if not all([m_file, m_match, m_score, m_second, m_margin]):
PYint("=" * 90)<12} <-> {b:<12} {n:5d}")ck, re.M)-------------():

==========================================================================================
RECOGNITION STATISTICS
==========================================================================================
Images recognized: 262

==========================================================================================
MATCH DISTRIBUTION
==========================================================================================
94_v33          24    9.16%
78_v33          20    7.63%
87_v33          19    7.25%
89_v33          19    7.25%
83_v33          18    6.87%
92_v33          18    6.87%
85_v33          17    6.49%
95_v33          17    6.49%
81_v33          16    6.11%
88_v33          16    6.11%
86_v33          15    5.73%
91_v33          13    4.96%
93_v33          12    4.58%
82_v33           9    3.44%
80_v33           8    3.05%
84_v33           8    3.05%
79_v33           7    2.67%
90_v33           3    1.15%
NONE             3    1.15%

==========================================================================================
GLOBAL SCORE STATISTICS
==========================================================================================
SCORE      mean=0.9046  median=0.9182  min=0.6009  max=0.9675
SECOND     mean=0.8464  median=0.8618  min=0.5724  max=0.9186
MARGIN     mean=0.0582  median=0.0547  min=0.0010  max=0.1816

==========================================================================================
CONFIDENCE
==========================================================================================
HIGH           175   66.79%
PROBABLE        55   20.99%
AMBIGUOUS       18    6.87%
NO_MATCH        14    5.34%

==========================================================================================
STATUS
==========================================================================================
CONFIDENT          175   66.79%
PROBABLE_MATCH      55   20.99%
AMBIGUOUS           18    6.87%
NO_MATCH            14    5.34%

==========================================================================================
STATISTICS BY MATCH
==========================================================================================
MATCH            N     SCORE    SECOND    MARGIN
78_v33          20    0.9395    0.8871    0.0525
79_v33           7    0.9420    0.8649    0.0771
80_v33           8    0.9323    0.8346    0.0977
81_v33          16    0.9184    0.8609    0.0575
82_v33           9    0.9458    0.8217    0.1241
83_v33          18    0.9149    0.8811    0.0338
84_v33           8    0.8922    0.8803    0.0119
85_v33          17    0.9187    0.8442    0.0745
86_v33          15    0.8822    0.8108    0.0714
87_v33          19    0.9128    0.8630    0.0498
88_v33          16    0.8391    0.7231    0.1160
89_v33          19    0.8911    0.8245    0.0666
90_v33           3    0.8368    0.7860    0.0508
91_v33          13    0.9158    0.8793    0.0366
92_v33          18    0.9240    0.8839    0.0400
93_v33          12    0.9169    0.8775    0.0393
94_v33          24    0.8944    0.8461    0.0483
95_v33          17    0.9083    0.8669    0.0414
NONE             3    0.6138    0.5963    0.0175

==========================================================================================
MOST AMBIGUOUS IMAGES — LOWEST MARGIN
==========================================================================================
Ленина 125-127 А (14).JPG 87_v33     score=0.8887 second=0.8876 margin=0.0010
008.JPG                   83_v33     score=0.9096 second=0.9082 margin=0.0014
Ленина 125-127 А (10).JPG 87_v33     score=0.8969 second=0.8950 margin=0.0019
Ленина 125-127 А (17).JPG 84_v33     score=0.8958 second=0.8932 margin=0.0026
Вавилова ул. - Радиаторный пер., A (70).JPG 88_v33     score=0.7976 second=0.7943 margin=0.0032
009.JPG                   92_v33     score=0.9097 second=0.9052 margin=0.0045
Ленина 125-127 А (9).JPG  84_v33     score=0.8962 second=0.8914 margin=0.0048
Ленина 125-127 А (8).JPG  87_v33     score=0.8875 second=0.8817 margin=0.0058
Ленина 125-127 А (11).JPG 84_v33     score=0.8994 second=0.8934 margin=0.0061
Вавилова ул. - Радиаторный пер., A (63).JPG 86_v33     score=0.8007 second=0.7942 margin=0.0065
Малиновского 25 к Доватора А (7).JPG 94_v33     score=0.8345 second=0.8274 margin=0.0071
Ленина 125-127 А (16).JPG 84_v33     score=0.8914 second=0.8827 margin=0.0087
менжин (7).JPG            86_v33     score=0.7259 second=0.7165 margin=0.0094
Нагибина Рубиновый А (1).JPG 91_v33     score=0.9248 second=0.9151 margin=0.0097
Вавилова Радиаторный А (1).JPG 94_v33     score=0.7388 second=0.7277 margin=0.0111
Нагибина 24 А (12).JPG    83_v33     score=0.8842 second=0.8731 margin=0.0111
Ленина Ашхабадский А (7).JPG NONE       score=0.6367 second=0.6254 margin=0.0113
Вавилова 52 А (20).JPG    95_v33     score=0.8880 second=0.8756 margin=0.0124
Ленина 125-127 А (12).JPG 84_v33     score=0.8882 second=0.8757 margin=0.0125
Шеболдаева 8 РИИЖТ (25).JPG NONE       score=0.6039 second=0.5911 margin=0.0128
Ленина 125-127 А (13).JPG 84_v33     score=0.9002 second=0.8870 margin=0.0133
Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (20).jpg 95_v33     score=0.8691 second=0.8553 margin=0.0138
Шеболдаева 95 А (8).JPG   91_v33     score=0.8908 second=0.8758 margin=0.0150
Вавилова ул. - Радиаторный пер., A (34).JPG 94_v33     score=0.8724 second=0.8573 margin=0.0151
Стачки Зорге А (25).JPG   89_v33     score=0.8506 second=0.8348 margin=0.0158
Нагибина Рубиновый А (52).JPG 91_v33     score=0.8059 second=0.7884 margin=0.0175
Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (10).JPG 89_v33     score=0.8724 second=0.8548 margin=0.0176
Нагибина 24 А (13).JPG    83_v33     score=0.8830 second=0.8647 margin=0.0182
Комарова Добровольского А (8).JPG 92_v33     score=0.9010 second=0.8824 margin=0.0186
Вавилова 52 А (14).JPG    95_v33     score=0.7992 second=0.7804 margin=0.0188

==========================================================================================
LOWEST SCORE
==========================================================================================
Комарова 20 Добровольского Б (4).JPG NONE       score=0.6009 second=0.5724 margin=0.0285
Шеболдаева 8 РИИЖТ (25).JPG NONE       score=0.6039 second=0.5911 margin=0.0128
Ленина Ашхабадский А (7).JPG NONE       score=0.6367 second=0.6254 margin=0.0113
Малиновского 9 А (23).JPG 88_v33     score=0.6517 second=0.5894 margin=0.0623
Малиновского 9 А (51).JPG 88_v33     score=0.6702 second=0.6036 margin=0.0665
Малиновского 9 А (9).JPG  88_v33     score=0.6806 second=0.6013 margin=0.0793
менжин (7).JPG            86_v33     score=0.7259 second=0.7165 margin=0.0094
менжин (8).JPG            86_v33     score=0.7278 second=0.6934 margin=0.0344
Вавилова Радиаторный А (1).JPG 94_v33     score=0.7388 second=0.7277 margin=0.0111
Малиновского 9 А (12).JPG 88_v33     score=0.7798 second=0.6649 margin=0.1149
Вавилова Радиаторный А (30).JPG 94_v33     score=0.7942 second=0.7303 margin=0.0639
Вавилова ул. - Радиаторный пер., A (70).JPG 88_v33     score=0.7976 second=0.7943 margin=0.0032
Вавилова 52 А (14).JPG    95_v33     score=0.7992 second=0.7804 margin=0.0188
Малиновского 25 к Стачки А (5).JPG 89_v33     score=0.7996 second=0.7747 margin=0.0249
Вавилова ул. - Радиаторный пер., A (63).JPG 86_v33     score=0.8007 second=0.7942 margin=0.0065
Нагибина Рубиновый А (52).JPG 91_v33     score=0.8059 second=0.7884 margin=0.0175
менжин (3).JPG            86_v33     score=0.8098 second=0.7344 margin=0.0754
Ленина Ашхабадский А (3).JPG 85_v33     score=0.8132 second=0.7507 margin=0.0625
Вавилова Радиаторный А (21).JPG 94_v33     score=0.8200 second=0.7621 margin=0.0579
Малиновского 25 к Стачки А (4).JPG 90_v33     score=0.8232 second=0.7996 margin=0.0236
Малиновского 25 к Стачки А (2).JPG 90_v33     score=0.8324 second=0.8064 margin=0.0260
Малиновского 25 к Стачки А (3).JPG 89_v33     score=0.8339 second=0.8126 margin=0.0212
Малиновского 25 к Доватора А (7).JPG 94_v33     score=0.8345 second=0.8274 margin=0.0071
Малиновского 25 к Доватора (17).JPG 89_v33     score=0.8438 second=0.8187 margin=0.0251
Стачки Зорге А (25).JPG   89_v33     score=0.8506 second=0.8348 margin=0.0158
Малиновского 25 к Стачки А (1).JPG 90_v33     score=0.8548 second=0.7520 margin=0.1028
Вавилова 52 А (16).JPG    95_v33     score=0.8596 second=0.8077 margin=0.0519
Шеболдаева РИИЖТ А (89).JPG 87_v33     score=0.8657 second=0.8301 margin=0.0356
Стачки пр-кт - Зорге ул. - пл. Защитников Отечества, A (20).jpg 95_v33     score=0.8691 second=0.8553 margin=0.0138
Ленина Ашхабадский А (4).JPG 85_v33     score=0.8698 second=0.8101 margin=0.0597

==========================================================================================
MOST FREQUENT COMPETING PAIRS
==========================================================================================
94_v33       <-> 95_v33          19
91_v33       <-> 94_v33          14
79_v33       <-> 87_v33          13
81_v33       <-> 84_v33          12
92_v33       <-> 93_v33          11
84_v33       <-> 87_v33          11
82_v33       <-> 86_v33          10
89_v33       <-> 92_v33          10
83_v33       <-> 92_v33           9
83_v33       <-> 91_v33           9
91_v33       <-> 93_v33           9
85_v33       <-> 91_v33           8
88_v33       <-> 92_v33           8
78_v33       <-> 91_v33           7
80_v33       <-> 82_v33           7
78_v33       <-> 95_v33           6
85_v33       <-> 94_v33           6
91_v33       <-> 92_v33           5
85_v33       <-> 93_v33           5
89_v33       <-> 90_v33           5
87_v33       <-> 92_v33           5
86_v33       <-> 92_v33           5
78_v33       <-> 92_v33           4
83_v33       <-> 87_v33           4
83_v33       <-> 93_v33           4
85_v33       <-> 87_v33           4
78_v33       <-> 83_v33           3
78_v33       <-> 93_v33           3
86_v33       <-> 89_v33           3
88_v33       <-> 89_v33           3

==========================================================================================
DONE
==================================================

---

### 🤖 **Assistant** — 2026-08-15 03:52:20

Да. По этим данным **v3.3 работает, но уже хорошо видно, где именно алгоритм путается**.

### Главный результат

Из **262 фотографий**:

- **230 / 262 = 87.8%** получили `HIGH` или `PROBABLE`
- `AMBIGUOUS` — 18 (**6.9%**)
- `NO_MATCH` — 14 (**5.3%**)
- средний `SCORE` — **0.9046**
- медиана `SCORE` — **0.9182**
- средний `MARGIN` — **0.0582**

То есть проблема **не в том, что DINO плохо видит сцену**. Наоборот, scores очень высокие.

Проблема — **разделение похожих адресов**.

### Особенно важный момент

Посмотри:

```text
87_v33:
score  0.9149
second 0.8811
margin 0.0338
```

и

```text
84_v33:
score  0.8922
second 0.8803
margin 0.0119
```

и:

```text
91_v33:
score  0.9158
second 0.8793
margin 0.0366
```

То есть модель часто говорит:

> «Я практически уверен, что это похожая сцена, но между конкретными адресами разница небольшая».

Это как раз **идеальный кандидат для второго этапа распознавания**.

---

## Самое интересное — группы конкурентов

У нас явно формируются кластеры:

```text
94 <-> 95       19
91 <-> 94       14
79 <-> 87       13
81 <-> 84       12
92 <-> 93       11
84 <-> 87       11
82 <-> 86       10
89 <-> 92       10
83 <-> 92        9
83 <-> 91        9
91 <-> 93        9
```

Это очень полезная информация.

Получается, **не нужно пытаться улучшать распознавание всех адресов одинаково**.

Можно сделать:

```text
DINOv2 v3.3
      ↓
первый кандидат
      ↓
если margin большой
      ↓
   сразу MATCH
```

а если:

```text
margin < X
```

то:

```text
               ┌── candidate A
DINO → top 2 ──┤
               └── candidate B
                    ↓
             усиленное сравнение
                    ↓
             A или B или UNKNOWN
```

---

# И вот здесь появляется OCR

Мы как раз обсуждали раньше:

> DINOv2 → fingerprint → первый кандидат → присвоение адреса

Теперь статистика показывает, что это правильная архитектура.

Я бы **не добавлял OCR на все 262 фотографии**.

Это будет лишняя нагрузка.

Лучше:

### Этап 1 — быстрый

```text
Фото
 ↓
DINOv2
 ↓
v3.3 fingerprints
 ↓
TOP-1
```

Если:

```text
margin >= 0.04–0.05
```

и score высокий:

```text
→ принимаем
```

### Этап 2 — только сомнительные

Если:

```text
margin < 0.04
```

то запускаем:

```text
OCR
 ↓
поиск номера/адресной таблички
 ↓
проверка кандидатов
```

Причём OCR можно запускать **не на всей фотографии как сейчас**, а искать табличку по всей сцене.

---

# Есть ещё один очень важный вывод

Вот этот список:

```text
Ленина 125-127 А (14)    87   0.8887 / 0.8876
Ленина 125-127 А (10)    87   0.8969 / 0.8950
Ленина 125-127 А (17)    84   0.8958 / 0.8932
Ленина 125-127 А (9)     84   0.8962 / 0.8914
Ленина 125-127 А (8)     87   0.8875 / 0.8817
Ленина 125-127 А (11)    84   0.8994 / 0.8934
Ленина 125-127 А (12)    84   0.8882 / 0.8757
Ленина 125-127 А (13)    84   0.9002 / 0.8870
```

Это **не случайные ошибки**.

Это практически наверняка **одна физическая локация/очень похожая группа сцен**, где DINO не имеет достаточного визуального признака для различения адресов.

Именно здесь OCR будет очень эффективен.

---

## Я бы сейчас ничего не менял в v3.3

Это важно.

У нас наконец появился **нормальный baseline**.

Сейчас:

```text
fingerprints: 78_v33 ... 95_v33
recognizer: v3.3
262 test images
```

И мы получили измеряемую точку отсчёта.

**Не надо сейчас снова оптимизировать основной алгоритм.**

Следующий шаг лучше сделать экспериментально:

### Сделать отчёт по порогам margin

Например:

| Margin | Фото | Доля |
|---:|---:|---:|
| `< 0.01` | ? | ? |
| `< 0.02` | ? | ? |
| `< 0.03` | ? | ? |
| `< 0.04` | ? | ? |
| `< 0.05` | ? | ? |
| `< 0.06` | ? | ? |
| `< 0.08` | ? | ? |

И отдельно проверить:

```text
margin < 0.02
margin 0.02–0.04
margin 0.04–0.06
margin > 0.06
```

Тогда мы увидим, **какой порог реально отделяет уверенные фотографии от тех, где нужен второй этап**.

А уже после этого можно встроить:

```text
DINO TOP-1
    │
    ├── уверенно → адрес
    │
    └── сомнительно
             ↓
       TOP-2 / TOP-3
             ↓
            OCR
             ↓
        окончательный адрес
```

Это будет гораздо правильнее, чем пытаться заставить один DINOv2 решить задачу, для которой у двух соседних адресов визуальные сцены практически одинаковые.

---

### 👤 **User** — 2026-08-15 03:53:30

давай сделаем визульный вывод в папку output с сортировкойц по номерам

---

### 🤖 **Assistant** — 2026-08-15 03:53:34

Да. Сейчас лучше **не менять распознавание**, а сделать отдельный этап визуального контроля: взять уже полученный `/tmp/recognition_test.log`, найти соответствующие фотографии и разложить копии в `output/78`, `output/79` … `output/95`, `output/NONE`.

Так мы сразу визуально увидим, **какие адреса реально попали в какие папки и где DINO ошибается**.

### 1. Создаём сортировщик

Выполни из проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > sort_recognition_output.py <<'PY'
from pathlib import Path
import re
import shutil

INPUT = Path("data/input/test")
OUTPUT = Path("output")

LOG = Path("/tmp/recognition_test.log")

if not INPUT.exists():
    raise SystemExit(f"ERROR: input folder not found: {INPUT}")

if not LOG.exists():
    raise SystemExit(f"ERROR: log not found: {LOG}")

# Все реальные файлы из test, индексируем по имени
files = {}
for p in INPUT.iterdir():
    if p.is_file():
        files[p.name] = p

log = LOG.read_text(encoding="utf-8", errors="ignore")

# Блоки вида:
#
# ## filename.JPG
#
# MATCH 78_v33
blocks = re.split(r'\n(?=## )', log)

results = []
not_found = []

for block in blocks:
    m_file = re.search(r'^## (.+)$', block, re.M)
    m_match = re.search(r'^MATCH\s+(\S+)$', block, re.M)
    m_score = re.search(r'^SCORE\s+([0-9.]+)$', block, re.M)

    if not m_file or not m_match:
        continue

    filename = m_file.group(1).strip()
    match = m_match.group(1).strip()

    score = float(m_score.group(1)) if m_score else 0.0

    src = files.get(filename)

    if src is None:
        not_found.append(filename)
        continue

    # 78_v33 -> 78
    if match.endswith("_v33"):
        folder = match[:-4]
    else:
        folder = match

    results.append((src, folder, score))

# Пересоздаём output
if OUTPUT.exists():
    shutil.rmtree(OUTPUT)

OUTPUT.mkdir(parents=True)

counters = {}

for src, folder, score in results:
    dst_dir = OUTPUT / folder
    dst_dir.mkdir(parents=True, exist_ok=True)

    dst = dst_dir / src.name
    shutil.copy2(src, dst)

    counters[folder] = counters.get(folder, 0) + 1

print("=" * 70)
print("VISUAL OUTPUT")
print("=" * 70)
print(f"Input : {INPUT}")
print(f"Output: {OUTPUT}")
print(f"Images: {len(results)}")
print()

for folder in sorted(counters, key=lambda x: (x == "NONE", int(x) if x.isdigit() else 9999)):
    print(f"{folder:>6} : {counters[folder]:4d}")

if not_found:
    print()
    print("=" * 70)
    print("NOT FOUND")
    print("=" * 70)

    for name in not_found:
        print(name)

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY
```

### 2. Запускаем

```bash
python3 sort_recognition_output.py
```

Должно получиться:

```text
output/
├── 78/
├── 79/
├── 80/
├── ...
├── 94/
├── 95/
└── NONE/
```

То есть, например:

```text
output/78/
    00 (1).JPG
    00 (2).JPG
    001.JPG
    002.JPG
    ...

output/94/
    ...
```

**Оригиналы `data/input/test` не трогаются** — используется `copy2()`.

После этого можно открыть:

```bash
xdg-open output
```

и визуально пройтись по папкам.

Особенно я бы сначала посмотрел **84, 87, 91, 92, 93, 94, 95** — именно между ними статистика показывает наиболее сильную конкуренцию.

---

### 👤 **User** — 2026-08-15 03:56:46

output 87 и 92 - давай изучим различия фото

---

### 🤖 **Assistant** — 2026-08-15 03:56:46

> **Searching the web**
>
> [[23.04] DINOv2 | DOCSAID](https://docsaid.org/en/papers/contrastive-learning/dinov2/)
> [Similarity Search](https://developers.datature.io/docs/similarity-search)
> [CVPR
#****
CVPR
#****
CVPR 2026 Submission #****.](https://openreview.net/pdf?id=U4WmAUqmAH)
> [An Overview of Visual Place Recognition Based on Street View Images](https://www.dqxxkx.cn/EN/abstract/article/1560-8999/72813)
> [Expanding visual search for online art collections](https://engineering.q42.nl/visual-search/)
> [Revisit Anything: Visual Place Recognition via Image](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/08592.pdf)
> [what is the difference between these two methods of calculating dinov2 feature similarity of 2 images?](https://www.reddit.com/r/computervision/comments/1fzu9vd)
> [Robust Scene Change Detection Using Visual Foundation Models and Cross-Attention Mechanisms](https://arxiv.org/abs/2409.16850)
> [GitHub - facebookresearch/dinov2: PyTorch code and models for the DINOv2 self-supervised learning method. · GitHub](https://github.com/facebookresearch/dinov2)
> [Как мы довели поиск товаров по изображению до 98% совпадений: FastAPI, DINOv2, Qdrant и поиск на фото полки / Хабр](https://habr.com/ru/companies/fix_price/articles/1034664/)
> [Image similarity comparison between CLIP and DINOv2 - laitimes](https://www.laitimes.com/en/article/636dv_6jjhi.html)
> [Scene-Level Triggers Using](https://www.justbetterdata.de/wp-content/uploads/Scene_Level_Triggers_IAVCC.pdf)
>
> **Searched 12 websites**
>
> 
>
> **Inspecting Output Image Files**
>
>
> **Inspected output image files**
>
> 
>
> Worked for 5s

Да. Здесь лучше **не смотреть по одной фотографии**, а сделать визуальное сравнение двух папок **87 и 92 одновременно**. Нам нужно понять, *почему DINO считает их похожими* и какие признаки реально различают адреса.

Сейчас я не вижу сами файлы `output/87` и `output/92` в чате, поэтому давай быстро сделаем контактные листы.

### 1. Сделаем два контактных листа

Из проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
import math

OUT = Path("output")
FONT = ImageFont.load_default()

def make_sheet(folder_name, cols=4, thumb_w=400, thumb_h=300):
    src = OUT / folder_name
    files = sorted([
        p for p in src.iterdir()
        if p.is_file() and p.suffix.lower() in
        {".jpg", ".jpeg", ".png", ".webp"}
    ])

    if not files:
        print(f"{folder_name}: no images")
        return

    cell_w = thumb_w
    cell_h = thumb_h + 32
    rows = math.ceil(len(files) / cols)

    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)

    for i, path in enumerate(files):
        try:
            im = Image.open(path).convert("RGB")
            im.thumbnail((thumb_w - 10, thumb_h - 10))

            x = (i % cols) * cell_w
            y = (i // cols) * cell_h

            px = x + (cell_w - im.width) // 2
            py = y + 5

            sheet.paste(im, (px, py))

            draw.text(
                (x + 5, y + thumb_h + 5),
                path.name,
                fill="black",
                font=FONT
            )

        except Exception as e:
            print("ERROR", path, e)

    dst = OUT / f"_CONTACT_{folder_name}.jpg"
    sheet.save(dst, quality=92)

    print(f"{folder_name}: {len(files)} images -> {dst}")

make_sheet("87")
make_sheet("92")
PY
```

Потом:

```bash
xdg-open output/_CONTACT_87.jpg
xdg-open output/_CONTACT_92.jpg
```

---

### 2. Но ещё полезнее - сделать 87 и 92 в одном листе

Поскольку нас интересует именно **разница между ними**, сделаем один общий лист:

```bash
python3 - <<'PY'
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

OUT = Path("output")
FONT = ImageFont.load_default()

folders = ["87", "92"]

files = {}
for folder in folders:
    files[folder] = sorted([
        p for p in (OUT / folder).iterdir()
        if p.is_file() and p.suffix.lower() in
        {".jpg", ".jpeg", ".png", ".webp"}
    ])

print("87:", len(files["87"]))
print("92:", len(files["92"]))

thumb_w = 360
thumb_h = 270
label_h = 35
gap = 10

# Две колонки:
# 87 слева
# 92 справа

rows = max(len(files["87"]), len(files["92"]))

sheet = Image.new(
    "RGB",
    (thumb_w * 2 + gap * 3, (thumb_h + label_h) * rows + 50),
    "white"
)

draw = ImageDraw.Draw(sheet)

draw.text((10, 10), f"87 - {len(files['87'])} images", fill="black", font=FONT)
draw.text((thumb_w + gap + 10, 10), f"92 - {len(files['92'])} images", fill="black", font=FONT)

for r in range(rows):
    for c, folder in enumerate(folders):
        if r >= len(files[folder]):
            continue

        path = files[folder][r]

        try:
            im = Image.open(path).convert("RGB")
            im.thumbnail((thumb_w - 10, thumb_h - 10))

            x = gap + c * (thumb_w + gap)
            y = 40 + r * (thumb_h + label_h)

            px = x + (thumb_w - im.width) // 2
            py = y + 3

            sheet.paste(im, (px, py))

            draw.text(
                (x + 5, y + thumb_h + 3),
                path.name,
                fill="black",
                font=FONT
            )

        except Exception as e:
            print("ERROR:", path, e)

dst = OUT / "_COMPARE_87_vs_92.jpg"
sheet.save(dst, quality=92)

print("Created:", dst)
PY
```

Открываем:

```bash
xdg-open output/_COMPARE_87_vs_92.jpg
```

### Что будем искать

Я бы при просмотре специально смотрел на 5 вещей:

1. **Одинаковые здания / фасады**
2. **Одинаковая геометрия дороги и перекрёстка**
3. **Рекламные конструкции / билборды**
4. **Деревья, фон, характерные объекты вокруг**
5. **Таблички с адресами**

Особенно интересуют фотографии, где получается:

```text
87 → 92
```

с маленьким `MARGIN`.

У нас уже есть конкретная статистика:

```text
83 ↔ 92
84 ↔ 87
89 ↔ 92
92 ↔ 93
```

Поэтому после 87/92 я бы **точечно посмотрел не все фотографии, а именно ошибочные/сомнительные пары**.

И ещё важнее: если окажется, что на фотографиях **87 и 92 визуально всё действительно очень похоже, но где-то присутствует небольшая табличка/номер дома**, это будет сильным подтверждением нашей идеи:

**DINOv2 определяет район/сцену → OCR определяет конкретный адрес.**

Пришли сюда `_COMPARE_87_vs_92.jpg` - тогда я смогу непосредственно разобрать визуальные различия между двумя группами.

---

### 👤 **User** — 2026-08-15 03:59:16

отличий двольно много в окружении - общего только проспект широкий

---

### 🤖 **Assistant** — 2026-08-15 03:59:16

Да — и это **очень важный результат**. Значит, проблема 87 ↔ 92, скорее всего, не в том, что фотографии реально почти одинаковые.

Если общее в основном только **широкий проспект**, то текущий DINOv2 слишком сильно учитывает **глобальную структуру сцены**:

> широкий проспект + похожая перспектива + дорога + небо + здания по краям → высокий similarity.

При этом он недостаточно сильно использует мелкие локальные признаки, которые для нас как раз являются **идентификаторами адреса**.

### Это объясняет статистику

Например:

```text
87 → score ≈ 0.91
92 → second ≈ 0.88
margin ≈ 0.03
```

Разница всего несколько сотых, хотя человек легко говорит:

> «Это разные места».

То есть **v3.3 хорошо определяет тип/характер сцены, но не всегда достаточно хорошо различает конкретные адреса.**

---

## Я бы сейчас не трогал сам v3.3

У нас появилась хорошая гипотеза, которую можно проверить экспериментом.

Сейчас fingerprint содержит, насколько я понимаю, компактное представление сцены. А нам нужно добавить второй уровень:

```text
                 ФОТО
                   │
                   ▼
              DINOv2 scene
                   │
             TOP кандидаты
                   │
        ┌──────────┴──────────┐
        │                     │
    margin большой        margin маленький
        │                     │
        ▼                     ▼
     MATCH              локальное сравнение
                              │
                              ▼
                    детали окружения
```

### И вот тут DINO patch tokens очень кстати

Мы их уже пробовали вводить раньше.

Для пары:

```text
87
92
```

можно сравнить не только:

```text
global embedding
```

но и:

```text
patch embeddings
```

То есть модель сможет учитывать:

- фасад конкретного здания;
- деревья;
- рекламные щиты;
- столбы;
- дорожные знаки;
- характерные объекты;
- положение объектов относительно дороги.

И при этом **не выбрасывать глобальный признак широкого проспекта**.

---

# Но есть ещё более интересный эксперимент

Я предлагаю сейчас **ничего не переписывать**, а сделать диагностический тест на 87 и 92.

Для каждой фотографии из `output/87` и `output/92` посчитать:

```text
GLOBAL similarity
PATCH similarity
```

И построить:

```text
87 → 87
87 → 92

92 → 92
92 → 87
```

Если получится примерно:

```text
                 GLOBAL       PATCH
87 → 87          0.91         0.82
87 → 92          0.88         0.55

92 → 92          0.92         0.84
92 → 87          0.88         0.57
```

то всё становится понятно:

**глобальный DINO путает их из-за широкого проспекта, а patch-level признаки прекрасно различают окружение.**

И тогда решение будет очень аккуратным:

### v3.3 остаётся первым быстрым фильтром

```text
DINO global
      ↓
TOP-5
```

а только для близких кандидатов:

```text
TOP-5
 ↓
patch comparison
 ↓
пересчёт рейтинга
 ↓
TOP-1
```

Это намного лучше, чем полностью переделывать текущий распознаватель.

**Я бы следующим шагом именно проверил `global vs patch` на 87 и 92.** Это даст нам фактическое подтверждение, что patch tokens решают именно ту проблему, которую мы сейчас увидели глазами.

---

### 👤 **User** — 2026-08-15 04:00:17

патч левел увеличивает обьем файла намного, может быть поиграться с весами

---

### 🤖 **Assistant** — 2026-08-15 04:00:18

Да. **Я бы именно с весами и поигрался, прежде чем возвращать patch-level.** Это гораздо дешевле и проще.

Сейчас у нас фактически есть два сигнала:

```text
GLOBAL DINO
```

хорошо определяет общий тип сцены:

> широкий проспект, похожая перспектива, городская среда

но иногда путает адреса.

Нам нужно заставить итоговый score **сильнее учитывать специфичность сцены**, не увеличивая fingerprint.

### Самый простой эксперимент

Сейчас, судя по статистике, итоговый score примерно такой:

```text
score = similarity(...)
```

Я бы протестировал несколько вариантов **только на существующих v33 fingerprint**, ничего не пересоздавая:

```text
вариант A — текущий
GLOBAL = 1.0

вариант B
GLOBAL = 0.8
SECONDARY = 0.2

вариант C
GLOBAL = 0.7
SECONDARY = 0.3

вариант D
GLOBAL = 0.6
SECONDARY = 0.4
```

Но есть важный нюанс: **если вторичного сигнала сейчас вообще нет, одними весами его не создать**.

Поэтому сначала надо посмотреть, что именно уже есть внутри v3.3.

У нас fingerprint довольно компактный, и вполне возможно, что там уже есть несколько компонентов/представителей, которым можно назначить разные веса.

### Давай сначала посмотрим формулу score

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -nE \
"score|similarity|cosine|weight|weights|centroid|representative|embedding" \
app/core/recognizer.py | head -120
```

И ещё:

```bash
sed -n '215,380p' app/core/recognizer.py
```

Пришли вывод.

Тогда я посмотрю **как именно сейчас считается SCORE**, и мы сможем сделать эксперимент типа:

```text
GLOBAL        0.70
CENTROID      0.15
REPRESENTATIVE 0.15
```

или, если там есть другие компоненты, подобрать веса именно для них.

И главное — можем прогнать **тот же самый `/tmp/recognition_test.log` / test-набор**, чтобы сравнить:

```text
v3.3 current
        ↓
262 фото

v3.3 weights #1
        ↓
262 фото

v3.3 weights #2
        ↓
262 фото
```

и автоматически посмотреть, выросли ли:

- `MARGIN`
- `HIGH`
- `PROBABLE`
- правильность 87 ↔ 92
- количество `NONE`.

**Это будет гораздо более чистый эксперимент, чем сейчас снова менять архитектуру.**

---

### 👤 **User** — 2026-08-15 04:01:01

int_mvp_v02

grep -nE \
"score|similarity|cosine|weight|weights|centroid|representative|embedding" \
app/core/recognizer.py | head -120
29:        absolute score
59:        score,
62:        score = float(score)
66:            score >= cls.HIGH_SCORE
72:            score >= cls.PROBABLE_SCORE
77:        if score >= cls.PROBABLE_SCORE:
273:        for path, query_embedding in zip(
286:                # This calculates the full v3.3 score.
288:                    score = self.analyzer.compare(
291:                        query_global=query_embedding,
323:                        "score": float(
324:                            score.get(
325:                                "final_score",
331:                            score.get(
332:                                "global_score",
338:                            score.get(
339:                                "environment_score",
345:                            score.get(
346:                                "color_score",
352:                            score.get(
353:                                "spatial_score",
358:                        "best_image": score.get(
362:                        "best_image_score": float(
363:                            score.get(
364:                                "best_image_score",
373:                    "score"
390:                        "score": 0.0,
391:                        "second_score": 0.0,
403:            best_score = float(
404:                best["score"]
408:                second_score = float(
409:                    ranked[1]["score"]
412:                second_score = 0.0
415:                best_score
416:                - second_score
421:                    best_score,
436:            # available address. The score/confidence are kept
438:            if best_score < threshold:
453:                    "score": best_score,
455:                    "second_score": (
456:                        second_score
471:                    "best_image_score": float(
473:                            "best_image_score",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 04:01:02

Вот, теперь стало интереснее. У нас **v3.3 уже не просто сравнивает один global embedding**.

В `recognizer.py` видно:

```text
final_score
global_score
environment_score
color_score
spatial_score
best_image_score
```

То есть **веса, скорее всего, находятся не в `recognizer.py`, а внутри `SceneAnalyzer.compare()`**.

Нам сейчас нужно посмотреть именно его.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
"final_score|global_score|environment_score|color_score|spatial_score|weight|weights" \
app/core/scene_analyzer.py app/core/ 2>/dev/null | head -200
```

И затем:

```bash
sed -n '1,280p' app/core/scene_analyzer.py
```

### Что я ожидаю увидеть

Что-то примерно такого типа:

```python
final_score = (
    global_score * 0.5 +
    environment_score * 0.2 +
    color_score * 0.15 +
    spatial_score * 0.15
)
```

Если это так — **мы нашли именно то место, которое надо экспериментально подкрутить**.

И я бы тогда не трогал fingerprints вообще.

Сделаем несколько профилей:

```text
CURRENT
global       50%
environment  20%
color        15%
spatial      15%
```

например:

```text
SCENE
global       40%
environment  35%
color        10%
spatial      15%
```

и:

```text
LOCATION
global       30%
environment  45%
color        10%
spatial      15%
```

Для нашей задачи **LOCATION-профиль может оказаться существенно лучше**, потому что нам не столько важно:

> «это широкий городской проспект»

сколько:

> «это именно тот кусок проспекта с этими зданиями, деревьями и объектами».

Но сначала покажи `scene_analyzer.py`. **Весами сейчас действительно стоит поиграться.**

---

### 👤 **User** — 2026-08-15 04:01:17

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '215,380p' app/core/recognizer.py
            queries = queries.reshape(
                1,
                -1,
            )

        results = []

        # Calculate CPU descriptors ONCE per image.
        # They do not depend on the fingerprint.
        #
        # Use CPU workers to process different images in parallel.
        def calculate_descriptors(path):
            path = Path(path)

            return (
                str(path),
                {
                    "environment": (
                        CompactDescriptor.environment(
                            path
                        )
                    ),
                    "color": (
                        CompactDescriptor.color(
                            path
                        )
                    ),
                    "spatial": (
                        CompactDescriptor.spatial(
                            path
                        )
                    ),
                },
            )

        worker_count = max(
            1,
            int(workers),
        )

        print(
            f"[Recognizer] CPU workers: "
            f"{worker_count}"
        )

        with ThreadPoolExecutor(
            max_workers=worker_count
        ) as executor:

            descriptor_results = executor.map(
                calculate_descriptors,
                paths,
            )

            query_descriptors = dict(
                descriptor_results
            )

        for path, query_embedding in zip(
            paths,
            queries,
        ):
            ranked = []

            descriptors = query_descriptors[
                str(path)
            ]

            for fingerprint_id, data in loaded_fingerprints:

                # First use the analyzer.
                # This calculates the full v3.3 score.
                try:
                    score = self.analyzer.compare(
                        Path(path),
                        fingerprint_id,
                        query_global=query_embedding,
                        query_environment=descriptors[
                            "environment"
                        ],
                        query_color=descriptors[
                            "color"
                        ],
                        query_spatial=descriptors[
                            "spatial"
                        ],
                    )

                except (
                    FileNotFoundError,
                    ValueError,
                    OSError,
                ) as exc:

                    print(
                        f"[Recognizer] SKIP "
                        f"{fingerprint_id} "
                        f"for "
                        f"{Path(path).name}: "
                        f"{exc}"
                    )

                    continue

                ranked.append(
                    {
                        "id": fingerprint_id,

                        "score": float(
                            score.get(
                                "final_score",
                                0.0,
                            )
                        ),

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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 04:01:18

Да, это подтверждает структуру. Но **весов здесь нет** — `recognizer.py` только получает уже рассчитанный `final_score`.

Нам теперь нужен `scene_analyzer.py`, где происходит реальное объединение:

```text
global_score
environment_score
color_score
spatial_score
best_image_score
        ↓
final_score
```

Выполни **только эти две команды**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -nE \
"final_score|global_score|environment_score|color_score|spatial_score|best_image_score|weight|weights" \
app/core/scene_analyzer.py
```

и:

```bash
sed -n '1,360p' app/core/scene_analyzer.py
```

Пришли вывод.

После этого мы сможем сделать аккуратный эксперимент **без пересоздания 18 fingerprints**:

```text
v3.3 текущие fingerprints
          │
          ├── текущие веса
          ├── веса #2
          ├── веса #3
          └── веса #4
```

и прогнать один и тот же `test`.

Причём я бы обязательно сохранил отдельно:

```text
GLOBAL
ENVIRONMENT
COLOR
SPATIAL
BEST_IMAGE
FINAL
```

для каждой пары **87 ↔ 92**.

Тогда мы увидим не просто «новый алгоритм стал лучше», а **какой именно компонент помогает отличать 87 от 92**.

---

### 👤 **User** — 2026-08-15 04:01:58

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -nE \
"final_score|global_score|environment_score|color_score|spatial_score|best_image_score|weight|weights" \
app/core/scene_analyzer.py
403:        global_score = self.cosine(
417:        best_image_score = float(
459:        environment_score = (
468:        color_score = (
477:        spatial_score = (
490:        final_score = (
492:            * global_score
494:            * environment_score
496:            * color_score
498:            * spatial_score
502:            "global_score": float(
503:                global_score
506:            "best_image_score": float(
507:                best_image_score
512:            "color_score": float(
513:                color_score
516:            "spatial_score": float(
517:                spatial_score
520:            "environment_score": float(
521:                environment_score
524:            "final_score": float(
525:                final_score
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '1,360p' app/core/scene_analyzer.py
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

class CompactDescriptor:
    """
    Scene Fingerprint v3.3 compact descriptors.

    Optimized version.

    The image is loaded/resized once and the three
    descriptors are calculated from the same image.

    environment:
        8x8 grid x 10 values = 640 floats

    color:
        HSV histograms = 48 floats

    spatial:
        4x4 grid x 2 values = 32 floats
    """

    GRID = 8
    IMAGE_SIZE = 128

    @staticmethod
    def _load(path: Path):
        image = cv2.imread(
            str(path),
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise ValueError(
                f"Cannot read image: {path}"
            )

        return cv2.resize(
            image,
            (
                CompactDescriptor.IMAGE_SIZE,
                CompactDescriptor.IMAGE_SIZE,
            ),
            interpolation=cv2.INTER_AREA,
        )

    @staticmethod
    def _normalize(vector):
        vector = np.asarray(
            vector,
            dtype=np.float32,
        )

        norm = np.linalg.norm(vector)

        if norm > 0.0:
            vector = vector / norm

        return vector.astype(np.float32)

    @classmethod
    def environment_from_image(cls, image):
        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2HSV,
        ).astype(np.float32)

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        ).astype(np.float32) / 255.0

        gx = cv2.Sobel(
            gray,
            cv2.CV_32F,
            1,
            0,
            ksize=3,
        )

        gy = cv2.Sobel(
            gray,
            cv2.CV_32F,
            0,
            1,
            ksize=3,
        )

        edge = np.clip(
            cv2.magnitude(gx, gy),
            0.0,
            1.0,
        )

        features = []
        size = cls.IMAGE_SIZE

        for gy_idx in range(cls.GRID):
            for gx_idx in range(cls.GRID):

                y1 = gy_idx * size // cls.GRID
                y2 = (gy_idx + 1) * size // cls.GRID

                x1 = gx_idx * size // cls.GRID
                x2 = (gx_idx + 1) * size // cls.GRID

                h = hsv[y1:y2, x1:x2]
                g = gray[y1:y2, x1:x2]
                e = edge[y1:y2, x1:x2]

                features.extend(
                    [
                        float(h[:, :, 0].mean()) / 179.0,
                        float(h[:, :, 1].mean()) / 255.0,
                        float(h[:, :, 2].mean()) / 255.0,

                        float(h[:, :, 0].std()) / 179.0,
                        float(h[:, :, 1].std()) / 255.0,
                        float(h[:, :, 2].std()) / 255.0,

                        float(g.mean()),
                        float(g.std()),

                        float(e.mean()),
                        float(e.std()),
                    ]
                )

        return cls._normalize(
            np.asarray(
                features,
                dtype=np.float32,
            )
        )

    @classmethod
    def environment(cls, path: Path):
        image = cls._load(path)
        return cls.environment_from_image(image)

    @classmethod
    def color_from_image(cls, image):
        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2HSV,
        )

        hist_h = cv2.calcHist(
            [hsv],
            [0],
            None,
            [16],
            [0, 180],
        )

        hist_s = cv2.calcHist(
            [hsv],
            [1],
            None,
            [16],
            [0, 256],
        )

        hist_v = cv2.calcHist(
            [hsv],
            [2],
            None,
            [16],
            [0, 256],
        )

        descriptor = np.concatenate(
            [
                hist_h.flatten(),
                hist_s.flatten(),
                hist_v.flatten(),
            ]
        ).astype(np.float32)

        return cls._normalize(descriptor)

    @classmethod
    def color(cls, path: Path):
        image = cls._load(path)
        return cls.color_from_image(image)

    @classmethod
    def spatial_from_image(cls, image):
        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        ).astype(np.float32) / 255.0

        descriptor = []

        h, w = gray.shape

        for gy_idx in range(4):
            for gx_idx in range(4):

                y1 = gy_idx * h // 4
                y2 = (gy_idx + 1) * h // 4

                x1 = gx_idx * w // 4
                x2 = (gx_idx + 1) * w // 4

                cell = gray[y1:y2, x1:x2]

                descriptor.extend(
                    [
                        float(cell.mean()),
                        float(cell.std()),
                    ]
                )

        return cls._normalize(
            np.asarray(
                descriptor,
                dtype=np.float32,
            )
        )

    @classmethod
    def spatial(cls, path: Path):
        image = cls._load(path)
        return cls.spatial_from_image(image)

    @classmethod
    def all_from_image(cls, image):
        """
        Calculate all compact descriptors from one already
        loaded/resized image.

        Returns:
            environment: 640
            color:       48
            spatial:     32
        """

        return (
            cls.environment_from_image(image),
            cls.color_from_image(image),
            cls.spatial_from_image(image),
        )

    @classmethod
    def all(cls, path: Path):
        image = cls._load(path)
        return cls.all_from_image(image)

class SceneAnalyzer:
    """
    v3.3 compact scene comparison.

    Weights:
        global       0.70
        environment  0.20
        color        0.07
        spatial      0.03

    Patch storage is disabled.
    """

    GLOBAL_WEIGHT = 0.70
    ENVIRONMENT_WEIGHT = 0.20
    COLOR_WEIGHT = 0.07
    SPATIAL_WEIGHT = 0.03

    def __init__(
        self,
        embedder,
        manager,
    ):
        self.embedder = embedder
        self.manager = manager

    @staticmethod
    def cosine(a, b):
        a = np.asarray(
            a,
            dtype=np.float32,
        ).reshape(-1)

        b = np.asarray(
            b,
            dtype=np.float32,
        ).reshape(-1)

        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)

        if na == 0.0 or nb == 0.0:
            return 0.0

        return float(
            np.dot(a, b)
            / (na * nb)
        )

    @staticmethod
    def descriptor_similarity(
        query,
        references,
    ):
        q = np.asarray(
            query,
            dtype=np.float32,
        ).reshape(-1)

        refs = np.asarray(
            references,
            dtype=np.float32,
        )

        if refs.ndim == 1:
            refs = refs.reshape(1, -1)

        if len(refs) == 0:
            return 0.0

        q_norm = np.linalg.norm(q)

        if q_norm == 0.0:
            return 0.0

        q = q / q_norm

        ref_norms = np.linalg.norm(
            refs,
            axis=1,
            keepdims=True,
        )

        ref_norms[
            ref_norms == 0.0
        ] = 1.0

        refs = refs / ref_norms

        scores = refs @ q

        k = max(
            3,
            int(len(scores) * 0.10),
        )

        k = min(
            k,
            len(scores),
        )

        return float(
            np.mean(
                np.sort(scores)[-k:]
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 04:02:00

Да. И по тому, что мы сейчас видим, **играться с весами — гораздо разумнее, чем возвращать patch-level**.

Сейчас у нас:

```text
GLOBAL       0.70
ENVIRONMENT  0.20
COLOR        0.07
SPATIAL      0.03
```

А проблема 87 ↔ 92 как раз показывает, что DINO global embedding слишком сильно ориентируется на общий визуальный контекст: широкий проспект, похожая композиция и т.п.

Но прежде чем менять веса, надо увидеть **реальные четыре компонента для спорных фотографий**. Тогда мы поймём, *какой именно компонент тянет 92 вверх*.

### 1. Сначала покажи остаток `scene_analyzer.py`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '360,550p' app/core/scene_analyzer.py
```

Это покажет точную формулу `final_score` и как выбирается `best_image`.

---

### 2. Но уже сейчас я бы протестировал несколько вариантов весов

Не менять код пока. Сделаем эксперимент:

| Вариант | Global | Environment | Color | Spatial |
|---|---:|---:|---:|---:|
| **A текущий** | 0.70 | 0.20 | 0.07 | 0.03 |
| **B** | 0.60 | 0.30 | 0.07 | 0.03 |
| **C** | 0.55 | 0.35 | 0.07 | 0.03 |
| **D** | 0.50 | 0.40 | 0.07 | 0.03 |
| **E** | 0.60 | 0.25 | 0.10 | 0.05 |

Мне особенно интересны **B/C/D**.

Почему:

- `global` — DINO, наиболее мощный, но именно он может путать разные адреса;
- `environment` — наши 8×8 локальные характеристики окружения;
- `color` — слабее, потому что освещение/время года могут меняться;
- `spatial` — полезный дополнительный сигнал, но сейчас он почти ничего не решает.

### 3. Важный момент

У нас уже есть очень хороший диагностический признак:

```text
87:
score ≈ 0.89
second ≈ 0.89
margin ≈ 0.001
```

То есть система **сама говорит, что не уверена**.

И это хорошо.

Нам не обязательно добиваться того, чтобы 87 всегда получал огромный score. Нам нужно добиться, чтобы:

```text
правильный адрес
    ↓
стабильно первый

неправильный похожий адрес
    ↓
второй

margin
    ↓
становится заметнее
```

То есть я бы оптимизировал не средний `SCORE`, а прежде всего **разделимость первого и второго кандидата**.

---

### 4. И ещё лучше — сделаем автоматический эксперимент

Можно не гадать с весами, а прогнать **все комбинации весов** на уже полученных данных и посмотреть:

```text
87 ↔ 92
84 ↔ 87
94 ↔ 95
91 ↔ 94
...
```

Например:

```text
GLOBAL  ENV    COLOR  SPATIAL
0.70    0.20   0.07   0.03
0.65    0.25   0.07   0.03
0.60    0.30   0.07   0.03
0.55    0.35   0.07   0.03
0.50    0.40   0.07   0.03
...
```

И получить таблицу:

```text
weights                  87/92 separation    ambiguous    NONE
0.70/0.20/0.07/0.03          ...
0.65/0.25/0.07/0.03          ...
0.60/0.30/0.07/0.03          ...
...
```

**Это будет намного полезнее ручного подбора.**

Но сначала дай вывод:

```bash
sed -n '360,550p' app/core/scene_analyzer.py
```

После этого я предложу точный эксперимент **без изменения текущей рабочей версии v3.3**.

---

### 👤 **User** — 2026-08-15 04:02:23

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '360,550p' app/core/scene_analyzer.py
                np.sort(scores)[-k:]
            )
        )

    def compare(
        self,
        image_path: Path,
        fingerprint_id: str,
        query_global=None,
        query_environment=None,
        query_color=None,
        query_spatial=None,
    ):
        """
        Compare one image against one fingerprint.

        For fast recognition the query descriptors can be
        supplied already calculated by the recognizer.

        If they are not supplied, calculate them here for
        backward compatibility with `analyze`.
        """

        data = self.manager.load(
            fingerprint_id
        )

        # --------------------------------------------------
        # GLOBAL DINO
        # --------------------------------------------------

        if query_global is None:
            query_global = (
                self.embedder.embed_paths(
                    [Path(image_path)]
                )[0]
            )

        query_global = np.asarray(
            query_global,
            dtype=np.float32,
        )

        global_score = self.cosine(
            query_global,
            data["centroid"],
        )

        image_scores = (
            data["embeddings"]
            @ query_global
        )

        best_index = int(
            np.argmax(image_scores)
        )

        best_image_score = float(
            image_scores[best_index]
        )

        image_names = (
            data["metadata"]
            .get(
                "image_names",
                [],
            )
        )

        if best_index < len(image_names):
            best_image = image_names[
                best_index
            ]
        else:
            best_image = str(
                best_index
            )

        # --------------------------------------------------
        # COMPACT DESCRIPTORS
        # --------------------------------------------------

        if (
            query_environment is None
            or query_color is None
            or query_spatial is None
        ):
            image = CompactDescriptor._load(
                Path(image_path)
            )

            (
                query_environment,
                query_color,
                query_spatial,
            ) = CompactDescriptor.all_from_image(
                image
            )

        environment_score = (
            self.descriptor_similarity(
                query_environment,
                data[
                    "environment_embeddings"
                ],
            )
        )

        color_score = (
            self.descriptor_similarity(
                query_color,
                data[
                    "color_embeddings"
                ],
            )
        )

        spatial_score = (
            self.descriptor_similarity(
                query_spatial,
                data[
                    "spatial_embeddings"
                ],
            )
        )

        # --------------------------------------------------
        # FINAL SCORE
        # --------------------------------------------------

        final_score = (
            self.GLOBAL_WEIGHT
            * global_score
            + self.ENVIRONMENT_WEIGHT
            * environment_score
            + self.COLOR_WEIGHT
            * color_score
            + self.SPATIAL_WEIGHT
            * spatial_score
        )

        return {
            "global_score": float(
                global_score
            ),

            "best_image_score": float(
                best_image_score
            ),

            "patch_score": 0.0,

            "color_score": float(
                color_score
            ),

            "spatial_score": float(
                spatial_score
            ),

            "environment_score": float(
                environment_score
            ),

            "final_score": float(
                final_score
            ),

            "best_image": best_image,

            "fingerprint_version": (
                data["metadata"]
                .get(
                    "version",
                    "3.3",
                )
            ),
        }

    def analyze(
        self,
        folder,
        fingerprint_id,
    ):
        from .image import image_files

        paths = image_files(folder)

        for path in paths:
            result = self.compare(
                Path(path),
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 04:02:23

Да, теперь картина полностью ясна. И здесь есть **важный момент**: менять веса вслепую не стоит.

Сейчас формула действительно простая:

```text
FINAL =
    0.70 × GLOBAL
  + 0.20 × ENVIRONMENT
  + 0.07 × COLOR
  + 0.03 × SPATIAL
```

Причём `ENVIRONMENT` — это не DINO patch-level. Это наш компактный 8×8×10 дескриптор, то есть 640 признаков, который смотрит на **локальные области изображения**.

### Я бы сделал следующий эксперимент

Не трогаем рабочий `scene_analyzer.py`.

Создадим отдельный скрипт, который на **тех же 262 фотографиях** возьмёт уже рассчитанные компоненты:

```text
global
environment
color
spatial
```

и пересчитает итог для разных весов.

Но есть ещё более важная вещь.

Сейчас:

```python
global_score = cosine(query_global, data["centroid"])
```

То есть для каждого адреса GLOBAL сравнивается **с центроидом всего адреса**.

А потом отдельно:

```python
best_image_score = max(
    data["embeddings"] @ query_global
)
```

Но `best_image_score` **вообще не участвует в final_score**.

Это потенциально очень интересное место.

---

## Что я предлагаю проверить

Сделать эксперимент сразу в двух направлениях.

### Эксперимент №1 — только веса

Например:

```text
A  0.70  0.20  0.07  0.03   ← сейчас
B  0.65  0.25  0.07  0.03
C  0.60  0.30  0.07  0.03
D  0.55  0.35  0.07  0.03
E  0.50  0.40  0.07  0.03
F  0.60  0.25  0.10  0.05
```

### Эксперимент №2 — GLOBAL сделать не только centroid

Вот это, на мой взгляд, **ещё интереснее**.

Сейчас у нас одновременно есть:

```text
global_score
    ↓
query ↔ centroid адреса
```

и

```text
best_image_score
    ↓
query ↔ ЛУЧШЕЕ конкретное фото адреса
```

Но второе мы выбрасываем.

Можно сделать, например:

```text
GLOBAL =
    70% centroid similarity
  + 30% best-image similarity
```

или:

```text
GLOBAL =
    50% centroid
  + 50% best-image
```

И затем уже применять наши environment/color/spatial.

Это может хорошо помочь именно в ситуации:

> 87 и 92 имеют похожий общий проспект, но конкретные фотографии окружения заметно отличаются.

Потому что **центроид сглаживает адрес**, а конкретный лучший кадр может содержать характерные объекты.

---

# Но сначала сделаем правильную диагностику

Нам нужно получить для спорной пары примерно такую таблицу:

```text
QUERY: Ленина 125-127 А (14).JPG

             87_v33       92_v33
------------------------------------
GLOBAL       0.91         0.90
ENVIRONMENT  0.82         0.61
COLOR        0.88         0.84
SPATIAL      0.91         0.87
BEST IMAGE   0.94         0.89
------------------------------------
FINAL        0.8887       0.8876
```

Тогда сразу станет понятно:

**если environment сильно различает 87 и 92 — увеличиваем его вес.**

Если же:

```text
ENVIRONMENT 0.89 / 0.88
```

то проблема не в весах — тогда надо менять сам дескриптор.

---

## И ещё один момент

У нас уже есть прекрасный набор для тестирования:

```text
87 ↔ 92
84 ↔ 87
94 ↔ 95
91 ↔ 94
79 ↔ 87
81 ↔ 84
92 ↔ 93
```

Это реальные конкурирующие адреса из твоего прогона.

Поэтому я бы **не оптимизировал систему по одному 87/92**.

Сделаем scoring benchmark по всем 262 изображениям и посмотрим:

```text
                    текущая
                    ↓
accuracy
top-1
top-2
mean margin
median margin
ambiguous
NO_MATCH

                    новый вариант
                    ↓
accuracy
top-1
top-2
mean margin
median margin
ambiguous
NO_MATCH
```

И отдельно:

```text
87 → 92 confusion
84 → 87 confusion
94 → 95 confusion
...
```

### Сейчас ничего в коде не меняем.

Следующий шаг — дать мне команду для создания **диагностического benchmark**, который будет использовать существующий v3.3 и выведет все `global/environment/color/spatial/best_image` для каждого изображения и кандидатов. После этого мы сможем подобрать веса математически, а не на глаз.

---

### 👤 **User** — 2026-08-15 04:03:27

давай

---

### 🤖 **Assistant** — 2026-08-15 04:03:28

Да. Сделаем **отдельный диагностический скрипт**, ничего в рабочем v3.3 не меняем.

Он возьмёт текущий `/tmp/recognition_test.log` и, главное, повторно рассчитает компоненты для **реальных 262 фотографий**, чтобы увидеть, почему, например, `87` конкурирует с `92`.

Сначала создай скрипт:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/benchmark_components.py <<'PY'
from pathlib import Path
import sys
import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.scene_analyzer import SceneAnalyzer, CompactDescriptor
from app.core.image import image_files

# ============================================================
# CONFIG
# ============================================================

INPUT = Path("data/input/test")

FINGERPRINTS = [
    f"{n}_v33"
    for n in range(78, 96)
]

TOP_K = 5

# ============================================================
# INIT
# ============================================================

settings = Settings()

embedder = SceneEmbedder(settings)
manager = FingerprintManager(settings)

analyzer = SceneAnalyzer(
    embedder,
    manager,
)

# ============================================================
# LOAD FINGERPRINTS
# ============================================================

print("=" * 100)
print("LOADING FINGERPRINTS")
print("=" * 100)

loaded = {}

for fp_id in FINGERPRINTS:
    try:
        data = manager.load(fp_id)
        loaded[fp_id] = data
        print(f"{fp_id:<12} OK")
    except Exception as exc:
        print(f"{fp_id:<12} ERROR: {exc}")

print()
print(f"Loaded: {len(loaded)} fingerprints")

# ============================================================
# IMAGES
# ============================================================

paths = image_files(INPUT)

print()
print("=" * 100)
print("INPUT")
print("=" * 100)
print(f"Images: {len(paths)}")

if not paths:
    print("ERROR: no images")
    sys.exit(1)

# ============================================================
# DINO
# ============================================================

print()
print("=" * 100)
print("DINO EMBEDDINGS")
print("=" * 100)

queries = embedder.embed_paths(paths)

queries = np.asarray(
    queries,
    dtype=np.float32,
)

if queries.ndim == 1:
    queries = queries.reshape(1, -1)

# ============================================================
# OUTPUT
# ============================================================

output = Path("output/benchmark_components")
output.mkdir(
    parents=True,
    exist_ok=True,
)

summary_file = output / "components.txt"

# ============================================================
# PROCESS
# ============================================================

with summary_file.open(
    "w",
    encoding="utf-8",
) as out:

    for index, (path, query_global) in enumerate(
        zip(paths, queries),
        1,
    ):

        print(
            f"\n[{index}/{len(paths)}] "
            f"{path.name}"
        )

        # --------------------------------------------
        # compact descriptors
        # --------------------------------------------

        image = CompactDescriptor._load(
            Path(path)
        )

        (
            query_environment,
            query_color,
            query_spatial,
        ) = CompactDescriptor.all_from_image(
            image
        )

        rows = []

        # --------------------------------------------
        # compare against fingerprints
        # --------------------------------------------

        for fp_id, data in loaded.items():

            global_score = analyzer.cosine(
                query_global,
                data["centroid"],
            )

            image_scores = (
                data["embeddings"]
                @ query_global
            )

            best_index = int(
                np.argmax(image_scores)
            )

            best_image_score = float(
                image_scores[best_index]
            )

            image_names = data["metadata"].get(
                "image_names",
                [],
            )

            if best_index < len(image_names):
                best_image = image_names[
                    best_index
                ]
            else:
                best_image = str(best_index)

            environment_score = (
                analyzer.descriptor_similarity(
                    query_environment,
                    data[
                        "environment_embeddings"
                    ],
                )
            )

            color_score = (
                analyzer.descriptor_similarity(
                    query_color,
                    data[
                        "color_embeddings"
                    ],
                )
            )

            spatial_score = (
                analyzer.descriptor_similarity(
                    query_spatial,
                    data[
                        "spatial_embeddings"
                    ],
                )
            )

            # Current v3.3
            final_score = (
                0.70 * global_score
                + 0.20 * environment_score
                + 0.07 * color_score
                + 0.03 * spatial_score
            )

            rows.append(
                {
                    "id": fp_id,
                    "final": final_score,
                    "global": global_score,
                    "environment": environment_score,
                    "color": color_score,
                    "spatial": spatial_score,
                    "best_image": best_image,
                    "best_image_score": best_image_score,
                }
            )

        rows.sort(
            key=lambda x: x["final"],
            reverse=True,
        )

        # --------------------------------------------
        # console
        # --------------------------------------------

        print(
            f"BEST: {rows[0]['id']} "
            f"score={rows[0]['final']:.4f}"
        )

        for rank, row in enumerate(
            rows[:TOP_K],
            1,
        ):
            print(
                f"{rank}. "
                f"{row['id']:<10} "
                f"FINAL={row['final']:.4f} "
                f"G={row['global']:.4f} "
                f"E={row['environment']:.4f} "
                f"C={row['color']:.4f} "
                f"S={row['spatial']:.4f} "
                f"BEST={row['best_image_score']:.4f}"
            )

        # --------------------------------------------
        # file
        # --------------------------------------------

        out.write("=" * 100 + "\n")
        out.write(
            f"IMAGE: {path.name}\n"
        )

        for rank, row in enumerate(
            rows[:TOP_K],
            1,
        ):
            out.write(
                f"{rank}. "
                f"{row['id']:<10} "
                f"FINAL={row['final']:.6f} "
                f"GLOBAL={row['global']:.6f} "
                f"ENV={row['environment']:.6f} "
                f"COLOR={row['color']:.6f} "
                f"SPATIAL={row['spatial']:.6f} "
                f"BEST={row['best_image_score']:.6f} "
                f"IMAGE={row['best_image']}\n"
            )

print()
print("=" * 100)
print("DONE")
print("=" * 100)
print(f"Saved: {summary_file}")
PY
```

Потом запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 /tmp/benchmark_components.py
```

### После завершения

Покажи мне:

```bash
sed -n '1,220p' output/benchmark_components/components.txt
```

Но **особенно интересны конкретные 87/92**. Поэтому можно сразу найти их конкуренции:

```bash
grep -nE \
"IMAGE:|87_v33|92_v33" \
output/benchmark_components/components.txt | head -200
```

И ещё лучше — посмотреть все случаи, где `87` и `92` находятся рядом:

```bash
grep -B1 -A5 \
"87_v33.*FINAL" \
output/benchmark_components/components.txt | grep -E \
"IMAGE:|87_v33|92_v33"
```

После этого мы увидим, например:

```text
             87              92
GLOBAL       0.91            0.90
ENV          0.84            0.63   ← !!!
COLOR        0.88            0.86
SPATIAL      0.91            0.89
BEST         0.94            0.90
```

и тогда уже будет понятно, **что именно надо усиливать**.

И отдельно я хочу проверить `BEST_IMAGE_SCORE`: сейчас система его вычисляет, но вообще **не использует в итоговом score**. Это потенциально очень сильный рычаг без увеличения размера fingerprint.

---

### 👤 **User** — 2026-08-15 04:03:57

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

python3 /tmp/benchmark_components.py
Traceback (most recent call last):
  File "/tmp/benchmark_components.py", line 5, in <module>
    from app.core.config import Settings
ModuleNotFoundError: No module named 'app'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

