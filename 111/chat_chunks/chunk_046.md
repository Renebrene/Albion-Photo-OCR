## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 🤖 **Assistant** — 2026-08-15 15:10:10

Отлично. Теперь видно главное: **V38 ничего не вычисляет заново**, он просто читает готовый `neighbor_decision.csv`. Поэтому безопаснее всего сделать LLM-постпроцессор поверх этого CSV.

И я предлагаю немного изменить первоначальную идею: **не использовать только `margin < 0.005`**. В твоём выводе, например, `img_112` имеет margin `0.023`, но уже начинается очень подозрительная зона `84 ↔ 87`. Поэтому LLM должен видеть **локальные переходы + короткие группы + margin**.

Сначала создадим dry-run. Он **не меняет CSV и не сортирует фотографии**.

Выполни:

```bash id="f4p4qa"
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/llm_resolver_v01.py <<'PY'
#!/usr/bin/env python3

import csv
import json
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPORT = PROJECT / "output/neighbor_v37/neighbor_decision.csv"

MODEL = "qwen3:4b"

# Порог для явной неопределенности
MARGIN_HARD = 0.005

# Сколько кадров брать вокруг спорной точки
CONTEXT = 5

def load_rows():
    with open(REPORT, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    rows.sort(
        key=lambda r: int(
            "".join(c for c in Path(r["image"]).stem if c.isdigit())
        )
    )

    return rows

def find_uncertain_zones(rows):
    """
    Ищем:
      1. очень маленький margin
      2. короткие скачки TOP1
      3. oscillation между двумя кандидатами
    """

    triggers = set()

    # 1. Очень маленький margin
    for i, r in enumerate(rows):
        if float(r["margin"]) < MARGIN_HARD:
            triggers.add(i)

    # 2. TOP1 меняется между соседними кадрами
    for i in range(1, len(rows)):
        a = int(rows[i - 1]["v33"])
        b = int(rows[i]["v33"])

        if a != b:
            triggers.add(i)
            triggers.add(i - 1)

    # Объединяем близкие точки в зоны
    if not triggers:
        return []

    indices = sorted(triggers)

    zones = []
    start = indices[0]
    prev = indices[0]

    for idx in indices[1:]:
        if idx - prev <= 3:
            prev = idx
        else:
            zones.append((start, prev))
            start = idx
            prev = idx

    zones.append((start, prev))

    # Расширяем контекст
    result = []

    for start, end in zones:
        start = max(0, start - CONTEXT)
        end = min(len(rows) - 1, end + CONTEXT)

        # Не создаём дубликаты пересекающихся зон
        if result and start <= result[-1][1] + 1:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))

    return result

def build_zone(rows, start, end):
    zone = []

    for i in range(start, end + 1):
        r = rows[i]

        zone.append({
            "index": i,
            "image": r["image"],
            "top1": int(r["v33"]),
            "top2": int(r["second"]),
            "margin": round(float(r["margin"]), 6),
        })

    return zone

def ask_llm(zone):
    candidates = sorted({
        x["top1"] for x in zone
    } | {
        x["top2"] for x in zone
    })

    payload = {
        "task": (
            "Determine the most likely address/fingerprint for the "
            "uncertain sequence. The numbers are candidate address IDs. "
            "Choose ONLY from the supplied candidates. "
            "Use sequence continuity and TOP1/TOP2 margins. "
            "Do not invent an ID."
        ),
        "candidates": candidates,
        "sequence": zone,
        "output_format": {
            "decision": "integer candidate ID or null",
            "confidence": "number from 0 to 1",
            "action": "keep_original or override"
        }
    }

    prompt = f"""
You are a post-processing judge for an image recognition system.

The primary vision system has already produced TOP1 and TOP2 candidates.

Your job is NOT to recognize the image.
Your job is ONLY to resolve ambiguity using the sequence.

Rules:
1. Choose only an ID from the supplied candidate list.
2. Prefer a stable sequence over an isolated TOP1 outlier.
3. If the evidence is insufficient, use action="keep_original".
4. Never invent a new ID.
5. Return ONLY valid JSON.
6. "decision" is the address ID you believe is correct for the
   central uncertain area.
7. Confidence must be between 0 and 1.

Candidate IDs:
{json.dumps(candidates, ensure_ascii=False)}

Sequence:
{json.dumps(zone, ensure_ascii=False, indent=2)}

Return:
{{
  "decision": null,
  "confidence": 0.0,
  "action": "keep_original"
}}
"""

    result = subprocess.run(
        [
            "ollama",
            "run",
            MODEL,
            prompt,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return result.stdout.strip()

def main():
    print("=" * 80)
    print("LLM RESOLVER V01 — DRY RUN")
    print("=" * 80)
    print(f"Model: {MODEL}")
    print(f"Input: {REPORT}")
    print()

    rows = load_rows()

    print(f"Images: {len(rows)}")

    zones = find_uncertain_zones(rows)

    print(f"Candidate zones: {len(zones)}")
    print()

    for n, (start, end) in enumerate(zones, 1):

        zone = build_zone(rows, start, end)

        print("=" * 80)
        print(f"ZONE {n}/{len(zones)}")
        print(
            f"frames: {start}-{end} "
            f"({len(zone)} images)"
        )
        print("=" * 80)

        for x in zone:
            print(
                f"{x['index']:3d} "
                f"{x['image']:15s} "
                f"TOP1={x['top1']:>2} "
                f"TOP2={x['top2']:>2} "
                f"margin={x['margin']:.6f}"
            )

        print()
        print("--- QWEN3:4B ---")

        answer = ask_llm(zone)

        print(answer)
        print()

    print("=" * 80)
    print("DRY RUN COMPLETE")
    print("NO FILES WERE MODIFIED")
    print("=" * 80)

if __name__ == "__main__":
    main()
PY

chmod +x scripts/llm_resolver_v01.py

uv run python scripts/llm_resolver_v01.py
```

### Что сейчас должно произойти

Скрипт найдёт зоны примерно такого типа:

```text
ZONE
112  84 / 87
113  87 / 84
114  84 / 87
115  87 / 84
116  84 / 87
117  84 / 87
118  84 / 87
119  87 / 84
120  84 / 87
121  84 / 87
122  84 / 87
```

и отдаст эту информацию `qwen3:4b`.

**Важно:** пока LLM ничего не исправляет. Нам сейчас нужно посмотреть, насколько разумно она разбирает реальные зоны V38.

Пришли вывод `uv run python scripts/llm_resolver_v01.py`. По нему уже настроим **V02**, где LLM будет возвращать строго структурированный результат и только потом разрешим ей корректировать спорные кадры.

---

### 👤 **User** — 2026-08-15 15:14:38

стоит также учесть случаи, когда в серии могут быть 100% единичные фото других адресов - тогда присваивать однозначное значение, на дпроверку отправлять только если нет высокой степени уверенности

---

### 🤖 **Assistant** — 2026-08-15 15:14:39

Да, это **очень важное уточнение**. И оно меняет логику в правильную сторону.

Нам нельзя считать:

> «одиночный TOP1 среди другой серии = ошибка».

В реальной съёмке вполне может быть:

```text
84
84
84
91  ← действительно адрес 91
84
84
```

И мы **не должны принудительно превращать 91 в 84** только ради гладкости последовательности.

### Поэтому делаем двухуровневую систему

```text
                    DINO v33
                       │
                       ▼
                TOP1 / TOP2 / margin
                       │
             ┌─────────┴─────────┐
             │                   │
      высокая уверенность    низкая уверенность
             │                   │
             ▼                   ▼
       принять TOP1          LLM-судья
             │                   │
             │          ┌────────┴────────┐
             │          │                 │
             │      оставить TOP1     изменить
             │          │                 │
             └──────────┴─────────────────┘
                       │
                       ▼
                 FINAL ADDRESS
```

Но есть ещё один принцип:

### LLM не должна автоматически «сглаживать» последовательность

Она должна рассматривать **одиночный кадр как потенциально настоящий отдельный адрес**.

Например:

```text
84  84  84  91  84  84
```

Если `91` имеет высокий confidence:

```text
91
```

оставляем.

Если:

```text
84  84  84  91/84 margin=0.002  84  84
```

тогда отправляем на проверку.

---

## Я бы сформулировал правило так

**DINO решает всё, где есть высокая степень уверенности.**

LLM получает только:

1. низкий `margin`;
2. конфликт TOP1/TOP2;
3. нестабильность между соседними кадрами;
4. ситуацию, когда алгоритм сам не может уверенно выбрать.

А LLM получает право выбрать:

```text
KEEP
```

или

```text
OVERRIDE
```

или даже:

```text
UNCERTAIN
```

Причём **по умолчанию сохраняем DINO**.

---

### И ещё одно важное изменение

Не надо отправлять LLM всю последовательность из 256 кадров.

Мы формируем **локальное окно**, например:

```text
img_108 ... img_122
```

Но отдельно помечаем центральный подозрительный кадр:

```text
108  79
109  79
110  79
111  79

112  84   ← candidate
113  87
114  84
115  87
116  84
117  84
118  84
119  87
120  84
121  84
122  84

123  88
124  88
125  88
```

LLM должна отвечать не:

> «какой адрес здесь чаще встречается?»

а:

> **«Какие кадры действительно выглядят как ошибки классификации, а какие могут быть настоящими единичными кадрами другого адреса?»**

Это существенно лучше.

---

## Поэтому я бы изменил наш V01

Сейчас **не запускай предыдущий вариант дальше как финальную архитектуру**.

Следующая версия должна работать с каждым спорным кадром примерно так:

```text
DINO:
TOP1 = 87
TOP2 = 84
margin = 0.0008

Контекст:
84, 84, 84, 87, 84, 84, 84

LLM:

{
  "decision": 87,
  "action": "keep",
  "confidence": 0.91
}
```

То есть LLM может сказать:

**«Да, несмотря на соседей 84, этот кадр вполне может быть настоящим 87 — оставляем».**

А для действительно очевидного выброса:

```text
84 84 84 [87] 84 84 84
```

при слабом DINO:

```json
{
  "decision": 84,
  "action": "override",
  "confidence": 0.94
}
```

---

### Главное правило production

Я предлагаю зафиксировать:

**DINO — основной классификатор.**

**LLM — только арбитр неопределённости.**

**LLM никогда не исправляет уверенный DINO.**

И это как раз позволит сохранить возможность существования **реальных единичных фотографий другого адреса**.

Для следующей версии я бы ещё добавил в ответ LLM поле:

```text
reason = "isolated_valid_candidate"
```

или

```text
reason = "likely_outlier"
```

Но это уже для анализа качества, а не для принятия решения.

Если согласен, следующим шагом переделаем `llm_resolver_v01.py` именно под эту логику и прогоняем твои 256 кадров.

---

### 👤 **User** — 2026-08-15 15:16:53

для начала можно изучить логику llm И текущие результаты  DRY RUN COMPLETE
NO FILES WERE MODIFIED

---

### 🤖 **Assistant** — 2026-08-15 15:16:53

Да, именно так и лучше сделать. **Сначала посмотрим фактический dry-run**, не меняя алгоритм.

Пришли вывод начиная примерно с:

```text
================================================================================
LLM RESOLVER V01 — DRY RUN
```

и до:

```text
DRY RUN COMPLETE
NO FILES WERE MODIFIED
```

Я разберу по каждой зоне:

- что увидела `qwen3:4b`;
- где она правильно сохранила единичный другой адрес;
- где попыталась «сгладить» последовательность;
- насколько адекватно использует `TOP1/TOP2/margin`;
- какие случаи она правильно оставляет DINO;
- где её решение потенциально опасно.

И отдельно сравним с твоим исходным V38, **не внося пока никаких изменений в код**.

Если вывод большой — присылай целиком.

---

### 👤 **User** — 2026-08-15 15:17:55

для начала хватит ================================================================================
ZONE 1/8
frames: 1-23 (23 images)
================================================================================
  1 img_001.JPG     TOP1=85 TOP2=93 margin=0.072371
  2 img_002.JPG     TOP1=85 TOP2=94 margin=0.069999
  3 img_003.JPG     TOP1=85 TOP2=91 margin=0.062516
  4 img_004.JPG     TOP1=85 TOP2=91 margin=0.059694
  5 img_005.JPG     TOP1=85 TOP2=91 margin=0.062207
  6 img_006.JPG     TOP1=85 TOP2=93 margin=0.078912
  7 img_007.JPG     TOP1=89 TOP2=85 margin=0.010600
  8 img_008.JPG     TOP1=85 TOP2=94 margin=0.034371
  9 img_009.JPG     TOP1=85 TOP2=92 margin=0.088215
 10 img_010.JPG     TOP1=85 TOP2=91 margin=0.084300
 11 img_011.JPG     TOP1=85 TOP2=91 margin=0.087674
 12 img_012.JPG     TOP1=85 TOP2=93 margin=0.082867
 13 img_013.JPG     TOP1=85 TOP2=94 margin=0.093557
 14 img_014.JPG     TOP1=85 TOP2=94 margin=0.087421
 15 img_015.JPG     TOP1=85 TOP2=91 margin=0.083659
 16 img_016.JPG     TOP1=85 TOP2=91 margin=0.084794
 17 img_017.JPG     TOP1=85 TOP2=93 margin=0.069079
 18 img_018.JPG     TOP1=95 TOP2=78 margin=0.056516
 19 img_019.JPG     TOP1=95 TOP2=94 margin=0.056369
 20 img_020.JPG     TOP1=95 TOP2=94 margin=0.026987
 21 img_021.JPG     TOP1=95 TOP2=94 margin=0.054354
 22 img_022.JPG     TOP1=95 TOP2=78 margin=0.021743
 23 img_023.JPG     TOP1=95 TOP2=78 margin=0.041825

--- QWEN3:4B ---
Thinking...
Okay, let's tackle this problem. So, I'm a post-processing judge for an 
image recognition system. My job is to resolve ambiguity using the 
sequence of results from the primary vision system. The main thing here is 
that I shouldn't recognize the image myself, just use the sequence to pick 
the right ID from the candidate list.

First, the candidate IDs are [78, 85, 89, 91, 92, 93, 94, 95]. The 
sequence has 23 images, each with top1 and top2 candidates along with 
their margins.

The rules say: prefer a stable sequence over an isolated TOP1 outlier. If 
evidence is insufficient, use action="keep_original". Never invent a new 
ID. Return only valid JSON with decision, confidence, and action.

Looking at the sequence, most of the top1s are 85. Let me check how many 
times 85 is top1. Let's count:

From index 1 to 23:

1: top1=85
2: 85
3:85
4:85
5:85
6:85
7:89
8:85
9:85
10:85
11:85
12:85
13:85
14:85
15:85
16:85
17:85
18:95
19:95
20:95
21:95
22:95
23:95

So, from index 1 to 17, top1 is 85 (17 times), then index 18-23 top1 is 95 
(6 times). Wait, index 7 is 89, which is a top1 once. So 85 is top1 for 17 
images, 95 for 6, 89 once.

But the problem says the central uncertain area. Wait, the problem 
statement says "the central uncertain area" but since I'm not supposed to 
recognize the image, maybe the task is to find which ID is most consistent 
across the sequence.

The key here is rule 2: prefer a stable sequence over an isolated TOP1 
outlier. So, the majority here is 85. But there's a few outliers: index 7 
has top1=89, and indices 18-23 have top1=95.

But the problem says "resolve ambiguity using the sequence". The original 
system has produced TOP1 and TOP2 candidates, so the ambiguity is probably 
which ID is the correct one for the central area.

Wait, but the problem states that the primary vision system has already 
produced TOP1 and TOP2 candidates. So each image in the sequence has its 
own top1 and top2. The task is to determine which ID (from the candidate 
list) is correct for the central uncertain area, using the sequence.

Hmm, maybe the "central uncertain area" refers to the fact that there's 
some uncertainty in the image recognition, and the sequence of images 
helps to resolve that. But since I can't recognize the image, I have to 
look at the patterns in the sequence.

Rule 2 says prefer a stable sequence over an isolated TOP1 outlier. So, if 
there's a majority of the same top1, that's stable. Here, 85 is the top1 
in 17 out of 23 images. Then 95 is top1 in 6, and 89 once.

But the problem is that the candidate list includes 78, 85, 89, 91, 92, 
93, 94, 95. So the possible answers are these.

Wait, the original system's TOP1 is 85 in most images, but there's a few 
outliers. For example, image 18-23 have top1 as 95. So maybe the system is 
getting confused here.

But the task is to choose an ID from the candidate list. The question is: 
which ID is most likely correct based on the sequence.

Wait, but the problem says "the central uncertain area". Maybe the 
system's output has some uncertainty, and the sequence of images helps to 
resolve which ID is the correct one.

But according to the rules, I have to choose only from the candidate list, 
and prefer a stable sequence. So, the stable sequence here is that 85 is 
the top1 in 17 images. The others are less frequent.

But in the sequence, there's a few images where top1 is 95 (indices 
18-23), which is a bit of an outlier. However, the problem says "prefer a 
stable sequence over an isolated TOP1 outlier". So 85 is stable, even 
though there are some outliers.

Wait, but maybe the "isolated TOP1 outlier" refers to when the top1 is 
different from the majority. So in this case, 85 is the majority, so it's 
stable. The 95s are a group of 6, but they are in the later images. But 
the problem says "stable sequence", so if 85 is the top1 in 17 images, 
that's a stable majority.

But then, what about the top2? For example, in some images, the top2 is 
93, 94, 91, etc. The top2 might give clues about the actual correct ID.

Wait, but the problem states that the primary vision system has produced 
TOP1 and TOP2 candidates. So for each image, the top1 is the most likely, 
and top2 is the second.

The task is to resolve ambiguity for the central uncertain area. So 
perhaps the central uncertain area is the area that the system is unsure 
about, and by looking at the sequence of images, we can determine which ID 
is correct.

But since I can't recognize the image, I have to look at the patterns.

Another angle: the "margin" is the difference between top1 and top2. 
Higher margin means top1 is more confident.

For example, image 7 has margin 0.0106, which is low, so top1=89 is less 
confident.

But the problem is to choose the decision (the ID) that is most consistent 
across the sequence.

Let me think: the majority of the top1s are 85, so that's the most stable. 
The outliers are 89 (once) and 95 (six times). Wait, but 95 appears in six 
images as top1, which is a bit more than once. So maybe 95 is a group of 
outliers.

Wait, the problem says "prefer a stable sequence over an isolated TOP1 
outlier". So stable sequence here would be the one where the top1 is the 
same across many images.

In this case, 85 is top1 in 17 images, which is a stable sequence. The 
other top1s are less frequent.

However, there's a problem: in the last few images (18-23), the top1 is 
95. So maybe the system is shifting to 95 in the later images. But the 
majority is still 85.

But the problem states: "the central uncertain area". Maybe the 
uncertainty is in the system's output, so the correct ID is the one that 
appears most consistently.

Rule 3: If evidence is insufficient, use action="keep_original". But in 
this case, there's evidence (the majority is 85), so we don't need to keep 
original.

Wait, the problem says "the primary vision system has already produced 
TOP1 and TOP2 candidates". So the original decision would be the top1 from 
the first image? Or maybe the system's default.

Wait, the problem says: "Your job is NOT to recognize the image." So the 
original decision might be the top1 of the first image, but the problem 
states that the sequence is given, so perhaps the "original" here refers 
to keeping the previous decision.

But according to the problem's instruction, the action is "keep_original" 
if evidence is insufficient.

But in this case, the evidence (the sequence) shows that 85 is the most 
frequent top1, so the decision should be 85 with high confidence.

Wait, but looking at the top2s. For example, in image 18 (index 18), top1 
is 95, top2 is 78. So 78 is the second candidate here. But 78 is in the 
candidate list.

Hmm, but the problem is to choose which ID is correct. Let's see.

Wait, the problem says "the central uncertain area". Maybe the central 
area is the one that the system is uncertain about, and the sequence helps 
to resolve it. But since I can't recognize the image, I have to use the 
sequence.

Another approach: check if there's a pattern where the top1 is the same 
across multiple images, and the top2s are consistent.

For example, 85 is top1 in most images. The top2s vary: 93, 94, 91, etc. 
But 91 and 94 are common.

Wait, but the problem states that the candidate list is [78, 85, 89, 91, 
92, 93, 94, 95]. So the correct ID must be one of these.

The key here is that the primary vision system has produced TOP1 and TOP2. 
So for each image, the top1 is the most likely candidate, top2 is the 
next.

But the actual correct ID might be the one that is top1 in most images, 
but the problem is that sometimes the top1 is wrong.

But according to the rules, we have to prefer a stable sequence (i.e., the 
top1 that appears consistently across the sequence) over an isolated 
outlier.

In this case, 85 is the top1 in 17 out of 23 images, which is a majority. 
So that's stable.

The outliers are:

- 89: only in image 7 (index 7)

- 95: in images 18-23 (6 images)

So 95 is a bit more frequent than 89, but still, 85 is the majority.

But rule 2 says "prefer a stable sequence over an isolated TOP1 outlier". 
So the stable sequence here is 85, so decision should be 85.

But wait, in some images, the top2 is 95. For example, image 18 has 
top2=78, but images 19-23 have top2=94 and 78.

Hmm, but the problem is to choose the ID for the central uncertain area. 
Maybe the uncertainty is that the system's top1 varies, but the sequence 
shows that 85 is the most consistent.

Wait, but the problem says "the central uncertain area" — perhaps the 
system is uncertain about the correct ID, and the sequence helps to 
resolve which ID is correct.

Given that 85 is the top1 in 17 out of 23 images, that's a strong 
majority. So the decision should be 85.

But wait, the problem's example return shows "decision": null, 
"confidence": 0.0, "action": "keep_original". But that's probably a 
placeholder.

Wait, the problem says: "Return ONLY valid JSON." So in this case, since 
the evidence is sufficient (85 is the majority), we should choose 85 as 
decision.

Wait, but let me check the margins. The margin is the difference between 
top1 and top2. Higher margin means more confident.

For example, image 1 has margin 0.072371, which is a bit high. But the 
top1 is 85.

In images where the margin is low (e.g., image 7: margin 0.0106), the top1 
is less confident.

But the problem says to prefer a stable sequence. So even if some images 
have low confidence, the fact that 85 is top1 in most images makes it 
stable.

But the problem says "the central uncertain area". Maybe the system's 
output has some uncertainty, and the sequence is used to determine the 
correct ID.

Given all that, I think the decision should be 85.

Wait, but let me check the top2s. For example, in images where top1 is 85, 
the top2 varies. Maybe the actual correct ID is one of the top2s.

But the problem states that the primary vision system has produced TOP1 
and TOP2 candidates. So for each image, the top1 is the most likely, top2 
is the next.

If the system is correct, then the correct ID would be the one that is 
top1 in most images.

But in reality, the correct ID might be different. However, the problem 
says to choose from the candidate list based on the sequence.

Given that 85 is the top1 in 17 out of 23 images, that's a strong 
indicator.

Another angle: in the later images (18-23), the top1 is 95. So maybe the 
correct ID is 95, but that's only in 6 images. However, the majority is 
85.

But the problem says "prefer a stable sequence", so the stable sequence is 
85.

Therefore, the decision should be 85.

But wait, the problem says "the central uncertain area". Maybe the central 
area is the area that is uncertain, and the sequence helps to resolve 
which ID is correct.

In this case, if the system's output is uncertain, but the sequence shows 
that 85 is the most frequent top1, then 85 is the decision.

Therefore, I think the answer is 85.

But let's check the margins. For example, in images where the top1 is 85, 
the margin varies. The margin is the difference between top1 and top2 (in 
terms of confidence score?).

Assuming the margin is the difference in confidence scores, higher margin 
means top1 is more confident.

But regardless, the problem says to prefer the stable sequence.

So, the decision is 85, confidence high.

But the problem's instruction says: "If the question has a final answer, 
please place the answer in \boxed{}."

Wait, the user says: "You are given a question with a final answer. Please 
provide the answer in \boxed{}."

So the answer here is 85.

Wait, but let me recheck the images.

Image 1: top1=85, top2=93 (margin 0.072371)

Image 2: top1=85, top2=94 (margin 0.06...)

...

Image 7: top1=89, top2=95 (margin 0.0106)

Images 18-23: top1=95, top2=78 (images 18-20), top2=94 (images 21-23)

So 85 is the top1 in 17 images.

Therefore, the stable sequence is 85.

Thus, the answer is 85.

But wait, the problem says "the central uncertain area". Maybe the system 
is uncertain about the correct ID, and the sequence shows that 85 is the 
most consistent.

Yes, I think 85 is the answer.

**Final Answer**
\boxed{85}
...done thinking.

The task involves determining the correct ID from a given candidate list 
based on a sequence of images where each image provides a top1 and top2 
candidate. The goal is to identify which ID is most consistent across the 
sequence, as this represents the "central uncertain area" being resolved.

---

### **Key Observations from the Sequence**

- **Total Images**: 23
- **Top1 Candidates**:
  - **85**: Appears as top1 in **17 images** (a majority)
  - **95**: Appears as top1 in **6 images**
  - **89**: Appears as top1 in **1 image**
- **Top2 Candidates**: Vary across the sequence, with common values like 
91, 92, 93, 94, and 78.

The **margin** (difference between top1 and top2 confidence scores) is 
provided for each image. While some images have low margins (e.g., image 7 
with margin = 0.0106), the **overall pattern** shows that **85 is the most 
frequent top1** across the sequence.

---

### **Interpretation of the Rules**

- **Rule 2**: *Prefer a stable sequence over an isolated TOP1 outlier*.
  - A **stable sequence** is one where the top1 remains consistent across 
the majority of images.
  - Here, **85 is top1 in 17 out of 23 images**, which is a **clear 
majority** and thus represents a **stable sequence**.
  - The other candidates (e.g., 95 and 89) appear **less frequently** and 
are therefore **outliers**.

- **Rule 3**: *If evidence is insufficient, use action = "keep_original"*
  - In this case, **evidence is sufficient** (85 is the dominant top1), so 
we do **not** default to "keep_original".

- **Candidate List**: [78, 85, 89, 91, 92, 93, 94, 95]
  - Only **85** is the top1 in the **majority** of images and thus the 
most **consistent** and **stable** candidate.

---

### **Conclusion**

Given that **85** is the most frequently occurring top1 across the 
sequence and represents a **stable pattern**, it is the most appropriate 
decision for the "central uncertain area" in this context.

$$
\boxed{85}
$$

================================================================================
ZONE 2/8
frames: 28-65 (38 images)

---

### 🤖 **Assistant** — 2026-08-15 15:17:56

Да. Этого **достаточно для первого анализа**, и по Zone 1 уже видно важную проблему в текущей логике Qwen.

### Что сейчас делает Qwen

Он фактически применяет:

> «большинство TOP1 → правильный адрес».

Для Zone 1 это приводит к `85`, потому что:

- 85 — 16/17? фактически подавляющее большинство до кадра 17;
- 89 — единичный выброс на `img_007`;
- 95 — **не выброс**, а последовательная серия с `img_018–023`.

И вот это принципиально.

### Где LLM ошибается

LLM говорит:

> `95` — «outlier», потому что его меньше.

Но **временная структура важнее простого большинства**.

У нас:

```text
001 ───────── 006   85
007                89  ← подозрительный одиночный кадр
008 ───────── 017   85

018 ───────── 023   95  ← уже стабильная серия
```

То есть я бы не давал LLM право самостоятельно решать:

```text
17 × 85 > 6 × 95 → 85
```

Это слишком примитивно.

---

## Как я предлагаю построить постобработку

И главное — **DINOv2 вообще не трогаем, OCR не добавляем**.

Первый этап уже сделал свою работу:

```text
Фото
 ↓
DINOv2 / v33
 ↓
TOP1 + TOP2 + margin
 ↓
обычная сортировка
```

А LLM должна работать **только как арбитр исключений**.

### 1. Сначала автоматически выделяем уверенные кадры

Например:

```text
margin >= 0.05
```

и TOP1 стабилен → **не отправляем LLM**.

Это особенно важно для твоего условия:

> бывают 100% единичные фотографии другого адреса.

Например:

```text
85
85
85
85
85
95  ← уверенный margin 0.15
85
85
85
```

Здесь **95 должен остаться 95**.

LLM вообще не должна его менять только потому, что вокруг 85.

Это очень важный принцип.

---

# 2. Отдельно ищем действительно спорные места

Например:

```text
TOP1=84 TOP2=87 margin=0.004
TOP1=87 TOP2=84 margin=0.006
TOP1=84 TOP2=87 margin=0.002
TOP1=87 TOP2=84 margin=0.001
```

Вот это — идеальный кандидат для LLM.

Потому что DINO фактически говорит:

> «Я не знаю, 84 это или 87».

---

# 3. LLM получает не всю последовательность подряд

А **структурированный контекст спорной зоны**.

Например:

```text
ZONE

108  79 / 87  margin .075
109  79 / 92  margin .076
110  79 / 87  margin .099
111  79 / 87  margin .077

112  84 / 87  margin .023
113  87 / 84  margin .006
114  84 / 87  margin .004
115  87 / 84  margin .001
116  84 / 87  margin .007
117  84 / 87  margin .012
118  84 / 87  margin .014
119  87 / 84  margin .001
120  84 / 87  margin .023
121  84 / 87  margin .009
122  84 / 87  margin .003

123  88 / 92  margin .158
124  88 / 92  margin .119
125  88 / 87  margin .103
```

И вопрос LLM должен быть **не**:

> «Какой здесь адрес?»

А:

> «Какие TOP1 являются ошибками последовательности, а какие являются реальной сменой адреса?»

Это гораздо более подходящая задача для маленькой LLM.

---

# 4. Особенно важно научить её различать два случая

### Случай A — ложный одиночный выброс

```text
85 85 85 85 89 85 85 85
```

→ `89` подозрительный.

### Случай B — реальный единичный кадр

```text
85 85 85 95 85 85 85
```

но при этом:

```text
margin(95) = 0.15
```

→ **оставляем 95**.

Иными словами:

**одиночность ≠ ошибка.**

Нужно учитывать **уверенность самого DINO**.

---

# 5. А вот Zone 1 очень интересна

Я бы пока **не просил Qwen менять результат Zone 1 автоматически**.

У нас:

```text
1–6    85
7      89   margin .0106
8–17   85
18–23  95
```

Здесь есть две разные ситуации:

### img_007

```text
89 / 85
margin = .0106
```

Очень вероятный выброс.

### img_018

```text
95 / 78
margin = .0565
```

А дальше:

```text
95 / 94 .056
95 / 94 .027
95 / 94 .054
95 / 78 .022
95 / 78 .042
```

Это уже **совсем другой случай**.

DINO не просто один раз случайно сказал 95. Он увидел **смену сцены и шесть последовательных кадров**.

Поэтому текущий ответ Qwen `85` я считаю плохим именно с точки зрения нашей будущей архитектуры.

---

## Какой должен быть контракт Qwen

Я бы сделал примерно так:

```json
{
  "changes": [
    {
      "frame": 7,
      "from": 85,
      "to": 89,
      "action": "keep",
      "confidence": 0.96
    }
  ]
}
```

То есть LLM **не назначает адрес всей зоны**.

Она только сообщает:

```text
этот кадр оставить
этот кадр считать выбросом
этот переход считать реальным
этот кадр не трогать
```

А уже Python принимает окончательное решение.

Это существенно безопаснее.

---

## И ещё один важный момент

Я бы вообще **не использовал Qwen3:4b как основной классификатор**.

Для твоей RTX 3060 12 GB его вполне можно использовать как **редкого арбитра**.

Схема получается:

```text
                    DINOv2 v33
                         │
                         ▼
                 TOP1 / TOP2 / margin
                         │
              ┌──────────┴──────────┐
              │                     │
        высокая уверенность      сомнение
              │                     │
              ▼                     ▼
          KEEP AS IS             Qwen 3 4B
                                    │
                                    ▼
                              решение только
                              по спорным кадрам
```

Причём Qwen будет запускаться не на 256 фотографиях, а, условно, на **нескольких зонах**.

Это даст нам одновременно:

- скорость;
- предсказуемость;
- отсутствие изменения уверенных результатов;
- возможность обрабатывать реальные переходы между адресами;
- использование LLM только там, где DINO действительно сомневается.

**И я бы сейчас не менял код.** Следующий правильный шаг — посмотреть **Zone 2/8** и остальные зоны, чтобы сначала понять, какие типы ошибок реально возникают. После этого уже зафиксируем правила отбора зон для Qwen и перепишем его prompt/выходной JSON.

---

### 👤 **User** — 2026-08-15 15:19:37

================================================================================
ZONE 2/8
frames: 28-65 (38 images)
================================================================================
 28 img_028.JPG     TOP1=95 TOP2=94 margin=0.059787
 29 img_029.JPG     TOP1=95 TOP2=94 margin=0.012399
 30 img_030.JPG     TOP1=95 TOP2=94 margin=0.054807
 31 img_031.JPG     TOP1=95 TOP2=94 margin=0.032756
 32 img_032.JPG     TOP1=95 TOP2=94 margin=0.048405
 33 img_033.JPG     TOP1=95 TOP2=94 margin=0.066634
 34 img_034.JPG     TOP1=82 TOP2=86 margin=0.089365
 35 img_035.JPG     TOP1=82 TOP2=80 margin=0.124883
 36 img_036.JPG     TOP1=82 TOP2=86 margin=0.123170
 37 img_037.JPG     TOP1=82 TOP2=86 margin=0.121100
 38 img_038.JPG     TOP1=82 TOP2=86 margin=0.129402
 39 img_039.JPG     TOP1=82 TOP2=86 margin=0.125009
 40 img_040.JPG     TOP1=82 TOP2=86 margin=0.124007
 41 img_041.JPG     TOP1=82 TOP2=80 margin=0.137992
 42 img_042.JPG     TOP1=82 TOP2=86 margin=0.137090
 43 img_043.JPG     TOP1=92 TOP2=93 margin=0.050515
 44 img_044.JPG     TOP1=92 TOP2=91 margin=0.047921
 45 img_045.JPG     TOP1=92 TOP2=83 margin=0.058778
 46 img_046.JPG     TOP1=92 TOP2=83 margin=0.037640
 47 img_047.JPG     TOP1=92 TOP2=83 margin=0.053973
 48 img_048.JPG     TOP1=89 TOP2=92 margin=0.015479
 49 img_049.JPG     TOP1=92 TOP2=93 margin=0.058042
 50 img_050.JPG     TOP1=92 TOP2=86 margin=0.042846
 51 img_051.JPG     TOP1=92 TOP2=93 margin=0.054863
 52 img_052.JPG     TOP1=92 TOP2=83 margin=0.044789
 53 img_053.JPG     TOP1=92 TOP2=89 margin=0.030184
 54 img_054.JPG     TOP1=92 TOP2=93 margin=0.045520
 55 img_055.JPG     TOP1=92 TOP2=83 margin=0.053832
 56 img_056.JPG     TOP1=92 TOP2=93 margin=0.056275
 57 img_057.JPG     TOP1=89 TOP2=92 margin=0.017843
 58 img_058.JPG     TOP1=92 TOP2=89 margin=0.026014
 59 img_059.jpg     TOP1=95 TOP2=92 margin=0.013838
 60 img_060.JPG     TOP1=81 TOP2=84 margin=0.051434
 61 img_061.JPG     TOP1=81 TOP2=84 margin=0.066338
 62 img_062.JPG     TOP1=81 TOP2=84 margin=0.066601
 63 img_063.JPG     TOP1=81 TOP2=84 margin=0.061724
 64 img_064.JPG     TOP1=81 TOP2=84 margin=0.062949
 65 img_065.JPG     TOP1=81 TOP2=84 margin=0.075336

--- QWEN3:4B ---
Thinking...
We are given a sequence of images with their top1 and top2 candidates and 
margins.
 The candidate IDs are: [80, 81, 82, 83, 84, 86, 89, 91, 92, 93, 94, 95]

 We are to choose an ID from the candidate list for the central uncertain 
area (but note: the problem says we don't recognize the image, we resolve 
ambiguity using the sequence).

 Steps:
 1. We are to look for a stable sequence that can help us decide. The rule 
says: "Prefer a stable sequence over an isolated TOP1 outlier."

 2. We have two main groups of images:
    - The first 6 images (index 28 to 33) have top1=95 and top2=94 (with 
margins around 0.01 to 0.06)
    - Then from index 34 to 65, we have a mix.

 3. However, note that the problem says: "Your job is ONLY to resolve 
ambiguity using the sequence." and we are to return a decision for the 
central uncertain area.

 4. But what is the central uncertain area? The problem doesn't specify. 
However, the context is that the primary system has produced TOP1 and TOP2 
for each image. We are to use the sequence to decide which ID is correct 
for the uncertain area.

 5. The problem states: "decision" is the address ID you believe is 
correct for the central uncertain area.

 6. Since the problem does not specify which area is central, we must 
infer that the entire sequence is the context for the uncertainty.

 7. Looking at the sequence, we see that the top1 candidates are changing. 
We need to see if there is a dominant pattern.

 8. Rule 3: If the evidence is insufficient, use action="keep_original". 
But note: we are returning a decision. However, the example return says: 
{"decision": null, "confidence": 0.0, "action": "keep_original"}

 9. Let's analyze the sequence:

    - The first part (index 28-33): 95 is consistently top1 (with top2=94) 
for 6 images. This is a stable pattern for 95.

    - Then, from index 34 to 42: 
        index 34: top1=82, top2=86
        index 35: top1=82, top2=80
        index 36: top1=82, top2=86
        ... and so on until index 42: top1=82, top2=86 (with top2 
sometimes 80, but 82 is stable)

        So 82 is the top1 for 9 consecutive images (index 34 to 42) with 
top2 being 86 or 80.

    - Then, index 43 to 58: 
        index 43: top1=92, top2=93
        index 44: top1=92, top2=91
        index 45: top1=92, top2=83
        ... and so on until index 58: top1=92, top2=89

        So 92 is the top1 for 16 images (index 43 to 58) with varying 
top2.

    - Then, index 59: top1=95, top2=92 -> so 95 is top1 again.

    - Then, index 60 to 65: top1=81, top2=84 (with top2 sometimes 84, but 
note: 81 is top1 for 6 images)

 10. We have three dominant candidates that appear in the top1 for long 
stretches:
      - 95: 6 images (28-33)
      - 82: 9 images (34-42)
      - 92: 16 images (43-58)
      - 81: 6 images (60-65)

 11. The problem says: "Prefer a stable sequence over an isolated TOP1 
outlier". The most stable sequence is 92 (16 images). However, note that 
the sequence has a gap: index 59 is 95 and then index 60-65 is 81.

 12. But the problem says: "the central uncertain area". We don't know 
what the central area is. However, the problem might be that the primary 
system has a candidate for the entire sequence? 

 13. Alternatively, the problem might be that the entire sequence is the 
context for the uncertainty in the central area. We are to pick the ID 
that is most consistent across the sequence.

 14. However, note the rule: "Never invent a new ID". So we must choose 
from the candidate list.

 15. Let's see what the problem says: "Your job is ONLY to resolve 
ambiguity using the sequence." -> meaning we have to use the sequence to 
decide.

 16. The problem does not specify which image is the central one. But the 
sequence is given as a list of images. We are to return a decision for the 
central uncertain area. Since the problem doesn't specify which area, we 
have to interpret.

 17. Another idea: the problem might be that the primary system has 
produced a set of candidates for a particular image, and we are given the 
sequence of images (with their top1 and top2) to help resolve which 
candidate is correct for the central uncertain area (which might be the 
entire scene?).

 18. But the problem says: "the central uncertain area" -> so it's one 
area in the image? However, we don't have the image. We only have the 
sequence of images.

 19. Given the complexity, and the rule that if evidence is insufficient, 
use "keep_original", and the example return is {"decision": null, 
"confidence": 0.0, "action": "keep_original"}, we might be in the case of 
insufficient evidence.

 20. Why insufficient?
     - The sequence shows multiple candidates: 81, 82, 89, 92, 93, 94, 95 
are all appearing.
     - There is no single candidate that is top1 for the entire sequence. 
The top1 changes.

 21. However, note the rule: "Prefer a stable sequence over an isolated 
TOP1 outlier". We can look for the candidate that has the highest 
stability (i.e., longest consecutive top1) and then see if it is the one 
that is most consistent.

     - Candidate 92: 16 consecutive images (index 43 to 58) as top1. This 
is the longest run.
     - Candidate 82: 9 consecutive images (index 34 to 42) -> but note: 
index 43 is 92, so it breaks at 43.
     - Candidate 95: 6 images (index 28 to 33) -> then breaks at 34.

     So 92 has the longest stable run.

 22. But the problem says: "the central uncertain area". Without knowing 
which area is central, we might assume that the entire sequence is the 
context for the uncertainty. However, the problem states that the primary 
system has already produced TOP1 and TOP2 for each image. We are to decide 
for the central uncertain area.

 23. Another interpretation: the problem might be that the primary system 
has one candidate for the entire image (but we don't have the image). 
Actually, the problem says: "the primary vision system has already 
produced TOP1 and TOP2 candidates". So for each image, they have a top1 
and top2.

 24. We are to return a decision for the central uncertain area. Since we 
don't have the image, we have to rely on the sequence to see which 
candidate is most likely to be the correct one for the central area.

 25. However, the problem does not specify which image is the central one. 
So we have to assume that the entire sequence is the context for the 
uncertainty.

 26. Given the above, the most stable candidate is 92 (with 16 consecutive 
top1). But note: the sequence has a gap at the end (index 59 and 60-65). 
However, 92 was the top1 for 16 images without interruption.

 27. But wait: the problem says "central uncertain area". Maybe the 
central area is the entire image? Then we have to choose a candidate that 
is the most common in the sequence? Or the one that is most stable?

 28. Let's count the top1s:
        81: 6 times (index 60-65)
        82: 9 times (index 34-42)
        89: 1 time (index 58)
        92: 16 times (index 43-58) -> note: index 43 to 58 is 16 images? 
            index 43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58 -> 16
        93: 1 time (index 43)
        94: 6 times (index 28-33)
        95: 6 times (index 28-33) and 1 time (index 59) -> total 7

     So 92 has the highest frequency (16).

 29. However, the problem says: "Prefer a stable sequence" (meaning 
consecutive) over an isolated outlier. So consecutive stability is more 
important than total frequency.

 30. The consecutive stability for 92 is 16 (the longest run). 

 31. Therefore, we might decide that 92 is the most likely candidate for 
the central uncertain area.

 32. But wait: the problem says: "the central uncertain area". Without 
knowing the context, we have to assume that the entire sequence is the 
context for the uncertainty. However, the problem might be that the 
primary system has a candidate for the entire scene (one image) but the 
sequence is given to help? Actually, the problem states: "the primary 
vision system has already produced TOP1 and TOP2 candidates" for each 
image in the sequence.

 33. I think the intended meaning is: the primary system has produced a 
candidate for the entire scene (one image) but we don't have that image. 
Instead, we have a sequence of images (with their top1 and top2) to help 
resolve the uncertainty.

 34. However, the problem does not specify the image. So we are to return 
the best candidate we can find from the sequence.

 35. Given the above, I would choose 92 as the decision.

 36. But the problem says: "Return: { ... }" and the example return is 
with null and keep_original. Why?

 37. Let me re-read the problem: "You are given a sequence of images with 
their top1 and top2 candidates". The problem does not specify what the 
central uncertain area is. Without knowing which area is central, we 
cannot be sure.

 38. Also, note: the problem says "if the evidence is insufficient". We 
have evidence that 92 is the most stable. So evidence is sufficient?

 39. However, the problem says: "the central uncertain area". If the 
central area is the entire scene, then we have multiple images and we can 
see that the sequence has a dominant pattern. But if the central area is a 
specific part of the image, we don't have that information.

 40. Given the problem's example return (which is the same as the one 
provided in the problem: {"decision": null, "confidence": 0.0, "action": 
"keep_original"}), it might be that the problem expects that because the 
sequence is ambiguous (multiple candidates) and we don't have enough to be 
sure, we keep the original.

 41. But note: the problem says: "Return: { ... }" and then shows that 
example. So perhaps the problem expects that we return the example.

 42. Why would they return that example? Because the problem says: "if the 
evidence is insufficient". 

 43. Let's see: the problem says "the central uncertain area". Without 
knowing what that area is, and without knowing the context of the entire 
scene, we cannot be confident.

 44. Also, note that the sequence has a gap: the top1 changes from 92 to 
95 (at index 59) and then to 81. So there is no single candidate that 
dominates the entire sequence.

 45. The problem says: "Prefer a stable sequence over an isolated TOP1 
outlier". We found a stable sequence for 92 (16 images) but then it 
breaks. However, the entire sequence is not stable.

 46. Given the complexity and the fact that the problem provides an 
example return, I think the intended answer is to use "keep_original" 
because the evidence is insufficient to be confident.

 47. Why? Because the problem does not specify which image is the central 
one. We have a sequence of 65 images? But the central uncertain area might 
be a specific part that we don't have information for.

 48. Alternatively, the problem might be that the primary system has 
produced a candidate for the entire scene (one image) but we don't have 
that image. The sequence of images is provided to help resolve the 
candidate for that one image? But the problem says: "the primary vision 
system has already produced TOP1 and TOP2 candidates" (plural) for each 
image? 

 49. I think the problem is designed such that we have to return the 
example because the evidence is insufficient.

 50. Let me check the candidate list: [80, 81, 82, 83, 84, 86, 89, 91, 92, 
93, 94, 95]

     We don't have 80, 83, 86, 89, 91 in the top1 as much? But they are in 
the top2.

 51. The problem says: "the central uncertain area". Without knowing what 
that area is, we cannot decide. Therefore, we return the example.

 52. The problem states: "Return: { ... }" and then shows the example. So 
it's likely that the expected answer is the example.

 53. Why? Because the problem says: "if the evidence is insufficient, use 
action='keep_original'".

 54. Given the above, I will return the example.

 Conclusion: 
   We return: {"decision": null, "confidence": 0.0, "action": 
"keep_original"}

 Why? Because the problem does not specify what the central uncertain area 
is, and the evidence from the sequence is ambiguous (multiple candidates 
with different runs) so we don't have enough to be confident.

 However, note: the problem says "the central uncertain area". If we 
assume that the entire sequence is the context for the uncertainty of the 
central area, then we have a candidate (92) that is the most stable. But 
the problem might be designed to have the answer as the example.

 Given the problem's example return is provided as the answer for the 
return, and the problem says "Return: ...", I think they want that.

 Let me see the problem statement again: it says "Return: { ... }" and 
then they write the JSON. So they are giving the expected format and the 
example.

 Therefore, I will output:

 {
   "decision": null,
   "confidence": 0.0,
   "action": "keep_original"
 }

 But note: the problem says "You are given a sequence ...". And the 
problem says "if the evidence is insufficient". 

 Since the problem does not specify what the central uncertain area is, 
and the sequence doesn't tell us which area is central, we have 
insufficient evidence.

 So the answer is the example.

 Let's write it.
...done thinking.

{
  "decision": null,
  "confidence": 0.0,
  "action": "keep_original"
}

---

### 🤖 **Assistant** — 2026-08-15 15:19:38

Вот Zone 2 как раз подтверждает, что **текущий prompt для Qwen надо менять**.

Здесь ответ `keep_original` — не потому, что данных мало, а потому что Qwen **не понял задачу** и начал рассуждать о том, что такое «central uncertain area».

На самом деле структура очень хорошо читается:

```text
28–33   95 × 6
34–42   82 × 9
43–58   92 × 16
59      95 × 1
60–65   81 × 6
```

То есть это практически идеальный пример **нескольких последовательных адресов**, а не одной зоны, для которой надо выбрать один ID.

### Что здесь видно

```text
95 ──────┐
         └── 82 ─────────┐
                         └── 92 ─────────────────┐
                                                 └─ 95
                                                    └── 81 ─────
```

И внутри:

- `img_048` → `89`, но margin всего **0.015** → очень вероятный выброс;
- `img_057` → `89`, margin **0.0178** → тоже вероятный выброс;
- `img_059` → `95`, margin **0.0138** → подозрительный переходный кадр;
- остальные серии имеют достаточно хорошие margins.

То есть **LLM здесь вообще не должна выбирать один адрес для всей Zone 2**.

Она должна анализировать **переходы и выбросы**.

### Поэтому архитектуру я бы теперь зафиксировал так

**DINO делает основное распознавание.**

LLM получает только:

1. короткую последовательность вокруг подозрительного перехода;
2. TOP1;
3. TOP2;
4. margin;
5. длину соседних серий;
6. желательно — уже рассчитанные Python-признаки.

И отвечает, например:

```json
{
  "decisions": [
    {
      "frame": 48,
      "action": "replace",
      "from": 89,
      "to": 92,
      "confidence": 0.95
    },
    {
      "frame": 57,
      "action": "replace",
      "from": 89,
      "to": 92,
      "confidence": 0.96
    },
    {
      "frame": 59,
      "action": "keep",
      "id": 95,
      "confidence": 0.72
    }
  ]
}
```

Причём **Python потом проверяет решение LLM**, а не наоборот.

---

Самое важное: **Zone 1 + Zone 2 уже дают нам достаточно материала, чтобы сначала переделать логику LLM, не трогая DINO.**

И я бы пока **не запускал остальные 6 зон через Qwen**. Сначала исправим постановку задачи: не «выбери адрес зоны», а **«найди подозрительные TOP1 внутри уже сформированной последовательности и предложи корректировку только там, где DINO не уверен»**.

---

### 👤 **User** — 2026-08-15 15:20:18

а **«найди подозрительные TOP1 внутри уже сформированной последовательности и предложи корректировку только там, где DINO не уверен»**.

---

### 🤖 **Assistant** — 2026-08-15 15:20:19

Да. **Именно эту логику я бы сейчас и закрепил.**

Причём с твоим дополнительным правилом:

> **Если DINO уверен — LLM не имеет права вмешиваться, даже если кадр единичный.**

Получается двухуровневая система:

```text
DINO v33
   │
   ├── высокая уверенность ──────────────► ОСТАВИТЬ
   │                                     
   └── низкая уверенность / конфликт ───► LLM
                                              │
                                              ├─ это реальная смена адреса
                                              ├─ это выброс
                                              └─ недостаточно данных → оставить
```

### Для Zone 2

Например:

```text
43  92  margin .0505
44  92  margin .0479
45  92  margin .0588
46  92  margin .0376
47  92  margin .0540
48  89  margin .0155   ← LLM
49  92  margin .0580
50  92  margin .0428
...
56  92  margin .0563
57  89  margin .0178   ← LLM
58  92  margin .0260   ← возможно LLM
59  95  margin .0138   ← LLM
60  81  margin .0514
61  81  margin .0663
```

LLM видит:

```text
92 92 92 92 92
89
92 92 92 92 92 92 92
89
92
95
81 81 81
```

И должна понять:

- `89` на 48 → почти наверняка выброс;
- `89` на 57 → почти наверняка выброс;
- `95` на 59 → **не обязательно ошибка**, потому что дальше начинается новая стабильная серия `81`;
- переход `92 → 95 → 81` может быть реальным изменением адреса.

То есть LLM должна **не сглаживать последовательность вслепую**.

---

### И ещё лучше: LLM не должна видеть всю 38-кадровую Zone

Python сначала делает предварительный фильтр.

Например:

```text
margin < 0.025
```

или

```text
TOP1 изменился
```

или

```text
одиночный TOP1 между двумя одинаковыми адресами
```

или

```text
TOP1 ↔ TOP2 скачет между двумя ID
```

И только тогда формируется небольшой контекст:

```text
44  92 / 91  .0479
45  92 / 83  .0588
46  92 / 83  .0376
47  92 / 83  .0540
48  89 / 92  .0155   ← TARGET
49  92 / 93  .0580
50  92 / 86  .0428
51  92 / 93  .0549
```

Так Qwen3:4b получает **конкретную задачу**, а не 38 строк для свободного философствования.

### И я бы добавил жёсткое правило

LLM может изменить `TOP1` **только на один из кандидатов, уже присутствующих в данных**.

Никаких:

> «Я считаю, что это, вероятно, 87».

Если 87 нет среди кандидатов — такого решения нет.

---

И ещё одно: **Qwen вообще не должен принимать решение о нормальных кадрах**. Его задача — только исправление подозрительных мест.

Это позволит сохранить главное преимущество нынешнего v33: **обычные 95–99% случаев работают быстро и детерминированно, а LLM занимается только сложными случаями.**

---

### 👤 **User** — 2026-08-15 15:21:42

и мы еще не используем best - по идее вместо LLM в спорных случаях выбросов посмотреть на него

---

### 🤖 **Assistant** — 2026-08-15 15:21:42

Да. **И это, на мой взгляд, нужно сделать до LLM.** Более того, возможно, после этого LLM понадобится значительно реже.

У нас уже есть `TOP1`, `TOP2`, `margin`, но мы пока фактически не используем **BEST-кандидата** как отдельный источник решения.

Я бы построил постобработку так:

```text
                 DINO v33
                    │
                    ▼
             TOP1 / TOP2 / margin
                    │
          ┌─────────┴─────────┐
          │                   │
     высокая уверенность    спорный кадр
          │                   │
          ▼                   ▼
       TOP1 оставить       смотрим BEST
                              │
                     ┌────────┴────────┐
                     │                 │
               BEST подтверждает   BEST не помогает
                     │                 │
                     ▼                 ▼
                 исправить          LLM Qwen 4B
                                       │
                              ┌────────┴────────┐
                              │                 │
                         уверенное решение   сомнение
                              │                 │
                              ▼                 ▼
                           исправить        оставить DINO
```

### Особенно интересны одиночные выбросы

Например:

```text
92
92
92
89   ← TOP1
92
92
92
```

Если у `89`:

```text
TOP1 = 89
TOP2 = 92
margin = 0.015
BEST = 92
```

то **LLM вообще не нужна**.

Можно автоматически сказать:

> TOP1=89 — слабый. BEST=92 подтверждается соседней последовательностью → присвоить 92.

---

### А вот сложный случай

Например:

```text
92
92
92
89
95
81
81
81
```

Здесь BEST может показать, что:

- 89 действительно плохой кандидат;
- 95 может быть реальным переходным адресом;
- 81 — уже следующий адрес.

Тогда LLM нужна только для **конкретного перехода**, а не для всей серии.

---

### Получается очень хорошая иерархия

**Уровень 1 — DINO v33**

Основное распознавание.

**Уровень 2 — BEST**

Используем существующий `best`, не добавляя новую нейросеть.

**Уровень 3 — последовательность**

Смотрим соседей и длину серий.

**Уровень 4 — Qwen3:4b**

Только если:

> DINO + BEST + sequence не смогли однозначно решить.

И это гораздо правильнее, чем сразу отдавать спорные кадры LLM.

---

Я бы сейчас сделал именно так: **сначала разберём, что именно уже означает `best` в текущем коде v37/v38 и какие данные он выдаёт**, а потом добавим BEST в dry-run, **ничего пока не меняя в сортировке**.

Тогда на тех же 256 кадрах увидим:

```text
DINO TOP1
DINO TOP2
BEST
margin
neighbor context
→ решение
```

и станет сразу видно, сколько спорных случаев реально закрывает BEST без Qwen.

---

### 👤 **User** — 2026-08-15 15:23:23

давай

---

### 🤖 **Assistant** — 2026-08-15 15:23:23

Да. Начнём **только с анализа**, ничего не меняем.

Нам нужно выяснить, что именно сейчас в проекте называется `best`, где оно рассчитывается и попадает ли оно уже в CSV/отчёт.

Запусти из проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "============================================================"
echo "1. SEARCH: best"
echo "============================================================"

grep -RniE '\bbest\b|best_candidate|best_score|BEST' \
    app scripts \
    --exclude='*.pyc' \
    2>/dev/null | head -300

echo
echo "============================================================"
echo "2. V37 SCRIPT"
echo "============================================================"

sed -n '1,320p' scripts/sort_neighbor_v37.py

echo
echo "============================================================"
echo "3. V36 SCRIPT"
echo "============================================================"

sed -n '1,320p' scripts/sort_neighbor_v36.py

echo
echo "============================================================"
echo "4. REPORT HEADER"
echo "============================================================"

head -5 output/neighbor_v37/neighbor_decision.csv

echo
echo "============================================================"
echo "5. CSV COLUMNS"
echo "============================================================"

python - <<'PY'
import csv

p = "output/neighbor_v37/neighbor_decision.csv"

with open(p, encoding="utf-8") as f:
    r = csv.DictReader(f)
    print(r.fieldnames)
PY
```

### Что особенно хотим увидеть

Нас интересует, есть ли уже что-нибудь вроде:

```text
best
best_id
best_score
best_candidate
candidate_scores
```

и **на каком этапе оно рассчитывается**.

Если `best` уже есть внутри распознавания, идеально — тогда мы не добавляем новую логику DINO вообще.

После этого я хочу сделать отдельный **DRY RUN**, примерно такого вида:

```text
FRAME   TOP1  TOP2  MARGIN   BEST   NEIGHBOR       RESULT
----------------------------------------------------------
048     89    92    .0155    92     92 92 92      -> 92
057     89    92    .0178    92     92 92 92      -> 92
059     95    92    .0138    95     92 -> 95 -> 81 -> ?
```

И тогда мы объективно увидим:

**сколько спорных кадров закрывается самим BEST + последовательностью и сколько действительно нужно отдавать Qwen.**

Пока **не меняем ни DINO, ни v33, ни сортировку, ни LLM**. Сначала посмотрим существующий `best`.

---

### 👤 **User** — 2026-08-15 15:23:50

ye\\uv

---

### 🤖 **Assistant** — 2026-08-15 15:23:52

Да, именно через `uv`. Если ты имел в виду запуск команд Python через `uv`, используй:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import csv

p = "output/neighbor_v37/neighbor_decision.csv"

with open(p, encoding="utf-8") as f:
    r = csv.DictReader(f)
    print(r.fieldnames)
PY
```

А для поиска `best` обычный `grep` — без разницы, `uv` тут не нужен:

```bash
grep -RniE '\bbest\b|best_candidate|best_score|BEST' \
    app scripts \
    --exclude='*.pyc' \
    2>/dev/null | head -300
```

Пришли вывод — разберём, **что уже умеет `best` и можно ли им заменить LLM на части спорных случаев**.

---

### 👤 **User** — 2026-08-15 15:24:22

grep -RniE '\bbest\b|best_candidate|best_score|BEST' \
    app scripts \
    --exclude='*.pyc' \
    2>/dev/null | head -300

---

### 🤖 **Assistant** — 2026-08-15 15:24:23

Да, это именно команда поиска. Запусти её из корня проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE '\bbest\b|best_candidate|best_score|BEST' \
    app scripts \
    --exclude='*.pyc' \
    2>/dev/null | head -300
```

**Пришли весь вывод.** По нему определим:

1. где сейчас вычисляется `best`;
2. какие данные ему доступны;
3. можно ли использовать `best` для исправления спорных `TOP1`;
4. какие случаи всё-таки оставить для `Qwen3:4b`;
5. и главное — **ничего пока не меняем в коде**.

---

