## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 🤖 **Assistant** — 2026-08-15 04:03:58

Да, это просто из-за того, что Python запускает `/tmp/benchmark_components.py`, и `/tmp` становится первым элементом `sys.path`. Поэтому `app` из проекта не находится.

Самый простой вариант — **запустить с `PYTHONPATH`**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

PYTHONPATH="$PWD" python3 /tmp/benchmark_components.py
```

Но есть вероятность, что дальше всплывёт ещё одна проблема с тем, как в проекте создаются `Settings`/`SceneEmbedder`. Поэтому лучше сразу проверить импорт:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

PYTHONPATH="$PWD" python3 - <<'PY'
from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.scene_analyzer import SceneAnalyzer, CompactDescriptor

print("IMPORT OK")
print(Settings)
print(SceneEmbedder)
print(FingerprintManager)
print(SceneAnalyzer)
PY
```

Если получишь:

```text
IMPORT OK
```

тогда запускаем:

```bash
PYTHONPATH="$PWD" python3 /tmp/benchmark_components.py
```

### Если хочешь вообще убрать эту проблему

Можно добавить в начало `/tmp/benchmark_components.py` сразу после импортов:

```python
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent / "projects" / "scene_fingerprint_mvp_v02"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
```

Но **пока этого не делаем** — вариант с `PYTHONPATH` безопаснее и ничего в проекте не меняет.

Запусти сначала проверку `IMPORT OK` и пришли вывод.

---

### 👤 **User** — 2026-08-15 04:04:20

ролект в uv

---

### 🤖 **Assistant** — 2026-08-15 04:04:20

Да, тогда лучше запускать **через `uv`**, чтобы использовалось именно окружение проекта и его зависимости.

Из корня проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python /tmp/benchmark_components.py
```

Но для скрипта из `/tmp` всё равно может понадобиться путь к самому проекту. Поэтому надёжный вариант:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

PYTHONPATH="$PWD" uv run python /tmp/benchmark_components.py
```

### Сначала проверим импорт

```bash
cd ~/projects/scene_fingerprint_mvp_v02

PYTHONPATH="$PWD" uv run python - <<'PY'
from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.scene_analyzer import SceneAnalyzer, CompactDescriptor

print("IMPORT OK")
PY
```

Если:

```text
IMPORT OK
```

то запускаем benchmark:

```bash
PYTHONPATH="$PWD" uv run python /tmp/benchmark_components.py
```

**Ничего в проекте пока не меняем.** Это будет использовать существующий `.venv` и текущий v3.3.

---

### 👤 **User** — 2026-08-15 04:04:40

Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8458.93it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
Traceback (most recent call last):
  File "/tmp/benchmark_components.py", line 33, in <module>
    manager = FingerprintManager(settings)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: FingerprintManager.__init__() missing 1 required positional argument: 'embedder'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 04:04:40

Да, отлично — проект и `uv` работают. Ошибка только в конструкторе `FingerprintManager`: ему нужны **`settings` и `embedder`**.

У нас сейчас:

```python
manager = FingerprintManager(settings)
```

нужно:

```python
manager = FingerprintManager(settings, embedder)
```

Исправим одну строку.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -i 's/manager = FingerprintManager(settings)/manager = FingerprintManager(settings, embedder)/' /tmp/benchmark_components.py
```

Проверить:

```bash
grep -n "FingerprintManager" /tmp/benchmark_components.py
```

Должно быть:

```text
33:manager = FingerprintManager(settings, embedder)
```

И запускаем:

```bash
PYTHONPATH="$PWD" uv run python /tmp/benchmark_components.py
```

Скрипт должен пройти загрузку:

```text
LOADING FINGERPRINTS
78_v33       OK
79_v33       OK
...
95_v33       OK
```

и затем начать:

```text
INPUT
Images: 262

DINO EMBEDDINGS
...
```

**Пока ничего больше не меняем.** Нам нужен именно этот чистый benchmark текущего v3.3, чтобы потом уже экспериментировать с весами и `best_image_score`.

---

### 👤 **User** — 2026-08-15 12:05:27

[108/262] Ленина 125-127 А (1).JPG
BEST: 84_v33 score=0.8819
1. 84_v33     FINAL=0.8819 G=0.8712 E=0.8969 C=0.9076 S=0.9714 BEST=0.9443
2. 87_v33     FINAL=0.8577 G=0.8405 E=0.8947 C=0.8766 S=0.9696 BEST=0.8606
3. 79_v33     FINAL=0.8459 G=0.8275 E=0.8788 C=0.8834 S=0.9678 BEST=0.8309
4. 81_v33     FINAL=0.8430 G=0.8243 E=0.8885 C=0.8458 S=0.9690 BEST=0.8560
5. 83_v33     FINAL=0.8368 G=0.8291 E=0.8589 C=0.7967 S=0.9611 BEST=0.8366

[109/262] Ленина 125-127 А (10).JPG
BEST: 87_v33 score=0.8969
1. 87_v33     FINAL=0.8969 G=0.8883 E=0.9123 C=0.9054 S=0.9736 BEST=0.8938
2. 84_v33     FINAL=0.8950 G=0.8792 E=0.9218 C=0.9444 S=0.9687 BEST=0.9476
3. 79_v33     FINAL=0.8819 G=0.8691 E=0.8996 C=0.9225 S=0.9654 BEST=0.8709
4. 92_v33     FINAL=0.8776 G=0.8635 E=0.9076 C=0.8933 S=0.9694 BEST=0.8582
5. 83_v33     FINAL=0.8672 G=0.8606 E=0.8944 C=0.8155 S=0.9625 BEST=0.8704

[110/262] Ленина 125-127 А (11).JPG
BEST: 84_v33 score=0.8994
1. 84_v33     FINAL=0.8994 G=0.8848 E=0.9198 C=0.9586 S=0.9670 BEST=0.9487
2. 87_v33     FINAL=0.8934 G=0.8803 E=0.9130 C=0.9347 S=0.9711 BEST=0.8877
3. 79_v33     FINAL=0.8808 G=0.8664 E=0.8976 C=0.9425 S=0.9606 BEST=0.8657
4. 92_v33     FINAL=0.8732 G=0.8614 E=0.9018 C=0.8712 S=0.9644 BEST=0.8584
5. 81_v33     FINAL=0.8683 G=0.8603 E=0.8806 C=0.8760 S=0.9565 BEST=0.8736

[111/262] Ленина 125-127 А (12).JPG
BEST: 84_v33 score=0.8882
1. 84_v33     FINAL=0.8882 G=0.8680 E=0.9204 C=0.9650 S=0.9660 BEST=0.9461
2. 87_v33     FINAL=0.8757 G=0.8565 E=0.9036 C=0.9499 S=0.9647 BEST=0.8688
3. 79_v33     FINAL=0.8678 G=0.8470 E=0.8954 C=0.9549 S=0.9641 BEST=0.8529
4. 83_v33     FINAL=0.8555 G=0.8454 E=0.8782 C=0.8493 S=0.9541 BEST=0.8488
5. 92_v33     FINAL=0.8534 G=0.8401 E=0.8802 C=0.8638 S=0.9601 BEST=0.8373

[112/262] Ленина 125-127 А (13).JPG
BEST: 84_v33 score=0.9002
1. 84_v33     FINAL=0.9002 G=0.8854 E=0.9187 C=0.9646 S=0.9729 BEST=0.9485
2. 87_v33     FINAL=0.8870 G=0.8742 E=0.9064 C=0.9233 S=0.9705 BEST=0.8851
3. 79_v33     FINAL=0.8830 G=0.8696 E=0.8961 C=0.9421 S=0.9705 BEST=0.8651
4. 92_v33     FINAL=0.8703 G=0.8590 E=0.8857 C=0.8960 S=0.9714 BEST=0.8572
5. 81_v33     FINAL=0.8671 G=0.8531 E=0.8869 C=0.9083 S=0.9653 BEST=0.8761

[113/262] Ленина 125-127 А (14).JPG
BEST: 87_v33 score=0.8887
1. 87_v33     FINAL=0.8887 G=0.8766 E=0.9072 C=0.9218 S=0.9680 BEST=0.8831
2. 84_v33     FINAL=0.8876 G=0.8699 E=0.9105 C=0.9638 S=0.9694 BEST=0.9405
3. 79_v33     FINAL=0.8726 G=0.8529 E=0.9027 C=0.9395 S=0.9732 BEST=0.8525
4. 83_v33     FINAL=0.8601 G=0.8526 E=0.8844 C=0.8219 S=0.9616 BEST=0.8503
5. 92_v33     FINAL=0.8588 G=0.8416 E=0.8879 C=0.9003 S=0.9696 BEST=0.8400

[114/262] Ленина 125-127 А (15).JPG
BEST: 84_v33 score=0.8847
1. 84_v33     FINAL=0.8847 G=0.8720 E=0.9074 C=0.9100 S=0.9713 BEST=0.9429
2. 87_v33     FINAL=0.8615 G=0.8404 E=0.9089 C=0.8903 S=0.9722 BEST=0.8598
3. 79_v33     FINAL=0.8529 G=0.8251 E=0.9129 C=0.9058 S=0.9772 BEST=0.8281
4. 81_v33     FINAL=0.8443 G=0.8297 E=0.8728 C=0.8567 S=0.9644 BEST=0.8472
5. 83_v33     FINAL=0.8426 G=0.8319 E=0.8770 C=0.8001 S=0.9632 BEST=0.8377

[115/262] Ленина 125-127 А (16).JPG
BEST: 84_v33 score=0.8914
1. 84_v33     FINAL=0.8914 G=0.8752 E=0.9195 C=0.9381 S=0.9741 BEST=0.9419
2. 87_v33     FINAL=0.8827 G=0.8687 E=0.9119 C=0.9015 S=0.9721 BEST=0.8738
3. 79_v33     FINAL=0.8691 G=0.8482 E=0.9119 C=0.9129 S=0.9709 BEST=0.8501
4. 83_v33     FINAL=0.8648 G=0.8581 E=0.8885 C=0.8216 S=0.9645 BEST=0.8547
5. 92_v33     FINAL=0.8524 G=0.8425 E=0.8878 C=0.8003 S=0.9684 BEST=0.8406

[116/262] Ленина 125-127 А (17).JPG
BEST: 84_v33 score=0.8958
1. 84_v33     FINAL=0.8958 G=0.8825 E=0.9171 C=0.9358 S=0.9727 BEST=0.9421
2. 87_v33     FINAL=0.8932 G=0.8823 E=0.9144 C=0.9064 S=0.9777 BEST=0.8833
3. 79_v33     FINAL=0.8749 G=0.8553 E=0.9036 C=0.9482 S=0.9689 BEST=0.8520
4. 83_v33     FINAL=0.8731 G=0.8653 E=0.8977 C=0.8411 S=0.9667 BEST=0.8581
5. 92_v33     FINAL=0.8716 G=0.8599 E=0.9036 C=0.8548 S=0.9709 BEST=0.8523

[117/262] Ленина 125-127 А (8).JPG
BEST: 87_v33 score=0.8875
1. 87_v33     FINAL=0.8875 G=0.8737 E=0.9038 C=0.9446 S=0.9669 BEST=0.8827
2. 84_v33     FINAL=0.8817 G=0.8605 E=0.9126 C=0.9692 S=0.9675 BEST=0.9509
3. 79_v33     FINAL=0.8716 G=0.8520 E=0.8977 C=0.9504 S=0.9709 BEST=0.8537
4. 92_v33     FINAL=0.8637 G=0.8527 E=0.8808 C=0.8834 S=0.9628 BEST=0.8498
5. 83_v33     FINAL=0.8559 G=0.8459 E=0.8744 C=0.8599 S=0.9562 BEST=0.8501

[118/262] Ленина 125-127 А (9).JPG
BEST: 84_v33 score=0.8962
1. 84_v33     FINAL=0.8962 G=0.8758 E=0.9358 C=0.9515 S=0.9775 BEST=0.9431
2. 87_v33     FINAL=0.8914 G=0.8789 E=0.9113 C=0.9226 S=0.9763 BEST=0.8854
3. 92_v33     FINAL=0.8673 G=0.8513 E=0.9011 C=0.8841 S=0.9753 BEST=0.8478
4. 79_v33     FINAL=0.8663 G=0.8441 E=0.9052 C=0.9317 S=0.9735 BEST=0.8459
5. 83_v33     FINAL=0.8618 G=0.8512 E=0.8957 C=0.8256 S=0.9682 BEST=0.8486

я вижу, что тут при низкой уверенности можно нужно было использовать второго кандидата

---

### 🤖 **Assistant** — 2026-08-15 12:05:28

Да. И по этим данным это **очень хорошо видно**.

Для серии `Ленина 125-127 А` текущий алгоритм часто выбирает `84_v33`, хотя `87_v33` является вторым кандидатом и разница между ними очень мала. Например:

- `(10)` → `87` 0.8969 vs `84` 0.8950 → разница **0.0019**
- `(11)` → `84` 0.8994 vs `87` 0.8934 → **0.0060**
- `(14)` → `87` 0.8887 vs `84` 0.8876 → **0.0011**
- `(17)` → `84` 0.8958 vs `87` 0.8932 → **0.0026**
- `(9)` → `84` 0.8962 vs `87` 0.8914 → **0.0048**

То есть **по одному кадру определить адрес практически невозможно**, но у нас есть очень сильный дополнительный сигнал: **серия фотографий одной точки**.

### Я бы сейчас не менял веса

Сначала сделал бы **второй кандидат частью алгоритма**, но только при низком `MARGIN`.

Например:

```text
margin >= 0.04
    → берем TOP-1

margin 0.02–0.04
    → TOP-1 и TOP-2 считаются неопределенными

margin < 0.02
    → обязательно рассматриваем TOP-2
```

А дальше самое интересное:

**не выбирать второй кандидат просто потому, что он второй.**

Нужно использовать **групповую согласованность фотографий**.

В твоём случае:

```text
Ленина 125-127 А (8)  → 87
Ленина 125-127 А (9)  → 84
Ленина 125-127 А (10) → 87
Ленина 125-127 А (11) → 84
...
```

Получается, что `84` и `87` конкурируют систематически.

Значит можно сделать механизм:

```text
TOP-1 = 84
TOP-2 = 87
margin = 0.0011

↓
низкая уверенность

↓
смотрим соседние/похожие фотографии

↓
если большинство таких кадров → 87
    корректируем результат на 87
```

### Но есть ещё более сильный вариант

У нас уже есть:

```text
G = global DINO
E = environment
C = color
S = spatial
BEST = лучший конкретный снимок
```

Для `(14)`:

```text
87:
FINAL 0.8887
G     0.8766
E     0.9072
C     0.9218
S     0.9680

84:
FINAL 0.8876
G     0.8699
E     0.9105
C     0.9638
S     0.9694
BEST  0.9405
```

Здесь `84` выигрывает в основном за счёт **color + best image**, а `87` выигрывает по **global DINO**.

А именно **global DINO сейчас имеет вес 0.70**.

То есть итоговая разница настолько маленькая, что дополнительные компактные признаки фактически начинают решать судьбу кандидата.

### Поэтому я предлагаю следующий эксперимент

Не трогать текущий рабочий `v33`.

Создать **v34 экспериментальный recognizer**, где при:

```text
MARGIN < 0.015
```

мы сохраняем TOP-2 и дополнительно считаем:

```text
D = разница global
E = разница environment
C = разница color
S = разница spatial
B = разница best_image
```

И выводим:

```text
TOP1 84_v33
TOP2 87_v33
MARGIN 0.0011

GLOBAL:      87 +0.0067
ENVIRONMENT: 84 +0.0033
COLOR:       84 +0.0420
SPATIAL:     84 +0.0014
BEST_IMAGE:  84 +0.0574

DECISION: AMBIGUOUS
```

Это позволит **не слепо передавать второй кандидат**, а понять, *почему* TOP-1 выиграл.

И я бы следующим шагом сделал ещё одну вещь: **автоматически найти все случаи `margin < 0.01` и сравнить TOP-1/TOP-2 по компонентам**. Тогда мы увидим, действительно ли второй кандидат систематически лучше по `G`, а первый вытягивается цветом/одним удачным эталонным снимком.

Это будет гораздо полезнее, чем сейчас сразу крутить веса.

---

### 👤 **User** — 2026-08-15 12:06:29

под весам кроме best и final Перевес правиьный

---

### 🤖 **Assistant** — 2026-08-15 12:06:30

Да. Если под «весами» ты имеешь в виду **веса компонентов `G / E / C / S`**, то по приведённым результатам я бы сказал:

**перевес сейчас в целом правильный.**

Текущая схема:

```text
GLOBAL       0.70
ENVIRONMENT  0.20
COLOR        0.07
SPATIAL      0.03
```

логична для нашей задачи, потому что:

- **G=0.70** — основной признак сцены через DINOv2. Это правильно.
- **E=0.20** — хорошо дополняет DINO именно информацией об окружении. Оставил бы.
- **C=0.07** — цвет полезен, но не должен сильно влиять. 7% нормально.
- **S=0.03** — пространственный дескриптор скорее вспомогательный. 3% нормально.

А вот **`BEST` я бы вообще не использовал как компонент финального решения**. Сейчас он выводится:

```text
BEST=0.9443
```

но в `final_score` он **не участвует**. И это хорошо.

### Что я вижу по твоим данным

Например `(14)`:

```text
87:
G = .8766
E = .9072
C = .9218
S = .9680

84:
G = .8699
E = .9105
C = .9638
S = .9694
```

При текущих весах:

```text
87 ≈ .8887
84 ≈ .8876
```

То есть система практически говорит:

> «Я не уверен. По глобальному признаку немного лучше 87, но компактные признаки слегка тянут к 84».

**Это именно то поведение, которое нам сейчас нужно.**

---

### Я бы пока НЕ менял веса

Главная проблема сейчас не в:

```text
0.70 / 0.20 / 0.07 / 0.03
```

а в том, что при:

```text
MARGIN = 0.001
MARGIN = 0.002
MARGIN = 0.005
```

система всё равно вынуждена сказать:

```text
MATCH = 84
```

Хотя фактически:

```text
84 ≈ 87
```

То есть нам нужно изменить **логику принятия решения**, а не формулу `FINAL`.

Я бы сделал:

```text
MARGIN >= 0.03
    → доверяем TOP-1

0.01 <= MARGIN < 0.03
    → TOP-1 с пониженной уверенностью

MARGIN < 0.01
    → TOP-1 и TOP-2 считаем практически равными
```

И именно в последнем случае запускать **разрешение конфликта между двумя кандидатами**.

Причём я бы сначала проверил это на всех 262 фотографиях, **не меняя ни одного веса**.

Тогда мы точно увидим, сколько ошибок можно убрать только логикой TOP-2.

---

### 👤 **User** — 2026-08-15 12:06:57

что дает best ?

---

### 🤖 **Assistant** — 2026-08-15 12:06:58

`BEST` — это **не отдельный признак сцены**, а показатель того, насколько конкретная фотография запроса похожа на **самую похожую отдельную фотографию внутри fingerprint**.

У тебя сейчас считается так:

```python
image_scores = data["embeddings"] @ query_global
best_index = np.argmax(image_scores)
best_image_score = image_scores[best_index]
```

То есть:

```text
BEST = max(cosine(query_DINO, каждый_эталонный_DINO))
```

### Пример

Для:

```text
Ленина 125-127 А (14).JPG
```

получилось:

```text
84_v33
G    = 0.8699
BEST = 0.9405
```

Это означает:

> Средний/центральный DINO-профиль адреса `84` похож на запрос на **0.8699**, но среди конкретных фотографий адреса `84` нашлась одна, похожая на него на **0.9405**.

Это очень полезная информация.

---

### Почему BEST может быть сильнее FINAL

Представь fingerprint `84` содержит 50 фотографий:

```text
84_001
84_002
84_003
...
84_050
```

Запрос может быть снят с совершенно другого ракурса.

Центроид:

```text
G = 0.87
```

но одна фотография:

```text
84_037 = 0.94
```

Это говорит:

> **«В базе есть конкретный кадр, визуально очень похожий на текущий».**

Для нашей задачи это потенциально очень сильный сигнал.

---

### Но есть опасность

`BEST` легко может оказаться случайным совпадением.

Например:

```text
84 BEST = 0.940
87 BEST = 0.883
```

это выглядит как очень сильное преимущество `84`.

Но если фотография `84_037` содержит похожее:

- небо;
- дерево;
- машину;
- рекламный щит;
- цвет фасада;
- геометрию дороги;

то это ещё **не означает, что адрес тот же**.

Именно поэтому сейчас правильно, что:

```text
BEST
```

**не входит в FINAL.**

---

### На самом деле BEST нам очень пригодится

Я бы использовал его не как вес, а как **дополнительный механизм подтверждения**.

Например:

```text
FINAL TOP1 = 84
FINAL TOP2 = 87

FINAL:
84 = 0.8876
87 = 0.8887

но:

BEST:
84 = 0.9405
87 = 0.8831
```

Тогда мы видим интересную ситуацию:

**по общей сцене кандидаты почти равны, но у 84 есть конкретный очень похожий эталон.**

Это уже повод изучить `84_XXX`.

А если будет:

```text
FINAL:
84 = 0.887
87 = 0.889

BEST:
84 = 0.891
87 = 0.940
```

то это уже **сильный аргумент в пользу 87**.

---

### Я бы даже сделал отдельный показатель

Не менять `FINAL`, а выводить:

```text
FINAL
GLOBAL
ENVIRONMENT
COLOR
SPATIAL
BEST
BEST_GAP
```

где:

```text
BEST_GAP = BEST - GLOBAL
```

Например:

```text
84:
G          0.8699
BEST       0.9405
BEST_GAP   +0.0706

87:
G          0.8766
BEST       0.8831
BEST_GAP   +0.0065
```

Это очень интересно.

У `84` **одна конкретная фотография сильно отличается от общего профиля fingerprint**, а у `87` конкретные фотографии более согласованы с его общим профилем.

Для нашего проекта это может стать полезным диагностическим признаком.

**Но я бы пока не включал BEST в веса.** Сначала посмотрим статистику `BEST` для правильных/сомнительных кандидатов.

---

### 👤 **User** — 2026-08-15 12:09:12

но если бы в случае с 84 best участвовал,  то не было бы ошибки. можно попробовать с  ним? отдельный прогон?

---

### 🤖 **Assistant** — 2026-08-15 12:09:14

Да, **отдельный прогон с `BEST` обязательно стоит сделать**. Причём я бы не менял текущий `v33`, а сделал экспериментальную формулу и сравнил результаты с текущей.

И важный момент: в твоём примере это действительно сработало бы:

```text
84: FINAL 0.8876  BEST 0.9405
87: FINAL 0.8887  BEST 0.8831
```

Если добавить `BEST` с небольшим весом, `84` станет первым.

### Я предлагаю не делать большой вес

Например:

```text
G       0.60
E       0.17
C       0.06
S       0.02
BEST    0.15
----------------
        1.00
```

Но здесь есть проблема: `BEST` и `G` оба происходят из DINO, поэтому **15% BEST может оказаться слишком большим**.

Я бы поэтому сделал сразу **три экспериментальных варианта**:

```text
A - текущий
G=.70 E=.20 C=.07 S=.03 BEST=0

B - BEST слабый
G=.66 E=.20 C=.07 S=.03 BEST=.04

C - BEST средний
G=.60 E=.20 C=.07 S=.03 BEST=.10
```

И прогнать все 262 фотографии.

Тогда получим примерно:

```text
CURRENT       78: 20
BEST 0.04     78: xx
BEST 0.10     78: xx
```

Но главное - не распределение адресов, а **сколько изменилось именно в сомнительных случаях**.

Особенно посмотрим:

```text
MARGIN < 0.01
MARGIN < 0.02
MARGIN < 0.03
```

И отдельно проверим серию:

```text
Ленина 125-127 А
```

---

### Ещё лучше

Я бы сделал не просто новый `FINAL`, а два результата:

```text
FINAL_CURRENT
FINAL_BEST
```

Например:

```text
Ленина 125-127 А (14)

CURRENT:
87  0.8887
84  0.8876

WITH BEST:
84  0.8955
87  0.8885

BEST DECISION:
84
```

Так мы **ничего не ломаем** и можем объективно сравнить.

Если хочешь, следующим сообщением дам **готовую команду/скрипт для проекта в `uv`**, который сделает этот отдельный прогон и сохранит результаты, не изменяя `recognizer.py` и `scene_analyzer.py`.

---

### 👤 **User** — 2026-08-15 12:10:25

давай сделай срипт для прогона с разными значениями весов, c best и без него. результаты сохрнаить в в читаемый файл и на основании него потом делать выводы

---

### 🤖 **Assistant** — 2026-08-15 12:10:25

Да. Сделаем **отдельный benchmark**, который вообще не трогает рабочий `v33`.

Он будет:

- прогонять все 262 изображения;
- считать `G / E / C / S / BEST`;
- тестировать несколько наборов весов;
- варианты **без BEST** и **с BEST**;
- сохранять полный читаемый результат;
- отдельно сохранять случаи, где решение изменилось;
- отдельно показывать низкий `MARGIN`;
- не менять `recognizer.py` и `scene_analyzer.py`.

Я бы сделал веса такими:

```text
A_CURRENT       G .70 E .20 C .07 S .03 BEST .00
B_BEST_02       G .68 E .20 C .07 S .03 BEST .02
C_BEST_05       G .65 E .20 C .07 S .03 BEST .05
D_BEST_10       G .60 E .20 C .07 S .03 BEST .10
E_BEST_15       G .55 E .20 C .07 S .03 BEST .15
```

То есть мы постепенно увеличиваем влияние `BEST`, не меняя остальные компоненты.

### 1. Создаём скрипт

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/benchmark_weights.py <<'PY'
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import sys
import numpy as np

from app.core.scene_analyzer import CompactDescriptor
from app.core.image import image_files
from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager

# ============================================================
# CONFIG
# ============================================================

INPUT = Path("data/input/test")
OUTPUT = Path("data/benchmark_weights")

TOP_K = 5
WORKERS = 6

# G + E + C + S + BEST = 1.0
WEIGHT_SETS = {
    "A_CURRENT":  (0.70, 0.20, 0.07, 0.03, 0.00),
    "B_BEST_02":  (0.68, 0.20, 0.07, 0.03, 0.02),
    "C_BEST_05":  (0.65, 0.20, 0.07, 0.03, 0.05),
    "D_BEST_10":  (0.60, 0.20, 0.07, 0.03, 0.10),
    "E_BEST_15":  (0.55, 0.20, 0.07, 0.03, 0.15),
}

# Margin thresholds for diagnostics
MARGINS = [0.01, 0.02, 0.03, 0.05]

# ============================================================
# HELPERS
# ============================================================

def cosine(a, b):
    a = np.asarray(a, dtype=np.float32).reshape(-1)
    b = np.asarray(b, dtype=np.float32).reshape(-1)

    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)

    if na == 0.0 or nb == 0.0:
        return 0.0

    return float(np.dot(a, b) / (na * nb))

def descriptor_similarity(query, references):
    q = np.asarray(query, dtype=np.float32).reshape(-1)
    refs = np.asarray(references, dtype=np.float32)

    if refs.ndim == 1:
        refs = refs.reshape(1, -1)

    if len(refs) == 0:
        return 0.0

    qn = np.linalg.norm(q)

    if qn == 0.0:
        return 0.0

    q = q / qn

    rn = np.linalg.norm(
        refs,
        axis=1,
        keepdims=True,
    )

    rn[rn == 0.0] = 1.0
    refs = refs / rn

    scores = refs @ q

    k = max(
        3,
        int(len(scores) * 0.10),
    )

    k = min(k, len(scores))

    return float(
        np.mean(
            np.sort(scores)[-k:]
        )
    )

# ============================================================
# LOAD
# ============================================================

print("=" * 90)
print("WEIGHT BENCHMARK")
print("=" * 90)
print()

print(f"INPUT:   {INPUT}")
print(f"OUTPUT:  {OUTPUT}")
print()

paths = image_files(INPUT)

if not paths:
    print("ERROR: no images found")
    sys.exit(1)

print(f"Images: {len(paths)}")
print()

settings = Settings()

embedder = SceneEmbedder(settings)

manager = FingerprintManager(
    settings,
    embedder,
)

fingerprint_ids = sorted(
    [
        p.name
        for p in Path(
            "data/fingerprints"
        ).iterdir()
        if p.is_dir()
        and p.name.endswith("_v33")
    ]
)

if not fingerprint_ids:
    print("ERROR: no *_v33 fingerprints found")
    sys.exit(1)

print(
    f"Fingerprints: {len(fingerprint_ids)}"
)
print(
    " ".join(fingerprint_ids)
)
print()

# ============================================================
# LOAD FINGERPRINT DATA ONCE
# ============================================================

loaded = {}

for fid in fingerprint_ids:
    print(f"Loading {fid} ...")

    data = manager.load(fid)

    loaded[fid] = data

print()
print("Fingerprints loaded.")
print()

# ============================================================
# CALCULATE QUERY DATA ONCE
# ============================================================

print(
    f"Calculating query descriptors "
    f"with {WORKERS} CPU workers..."
)

def calculate_query(path):
    path = Path(path)

    image = CompactDescriptor._load(path)

    env, color, spatial = (
        CompactDescriptor.all_from_image(
            image
        )
    )

    return (
        str(path),
        env,
        color,
        spatial,
    )

with ThreadPoolExecutor(
    max_workers=WORKERS
) as executor:

    descriptor_results = list(
        executor.map(
            calculate_query,
            paths,
        )
    )

descriptor_map = {
    path: {
        "environment": env,
        "color": color,
        "spatial": spatial,
    }
    for path, env, color, spatial
    in descriptor_results
}

# ============================================================
# DINO EMBEDDINGS
# ============================================================

print("Calculating DINO embeddings...")

query_embeddings = embedder.embed_paths(
    [Path(p) for p in paths]
)

query_map = {
    str(path): embedding
    for path, embedding
    in zip(paths, query_embeddings)
}

print("DINO embeddings ready.")
print()

# ============================================================
# BASE COMPONENT SCORES
# ============================================================

print("Calculating component scores...")

base_results = {}

for index, path in enumerate(paths, 1):

    path = Path(path)

    query_global = query_map[str(path)]

    desc = descriptor_map[str(path)]

    candidates = []

    for fid in fingerprint_ids:

        data = loaded[fid]

        G = cosine(
            query_global,
            data["centroid"],
        )

        E = descriptor_similarity(
            desc["environment"],
            data["environment_embeddings"],
        )

        C = descriptor_similarity(
            desc["color"],
            data["color_embeddings"],
        )

        S = descriptor_similarity(
            desc["spatial"],
            data["spatial_embeddings"],
        )

        image_scores = (
            data["embeddings"]
            @ query_global
        )

        best_index = int(
            np.argmax(image_scores)
        )

        BEST = float(
            image_scores[best_index]
        )

        image_names = (
            data["metadata"]
            .get("image_names", [])
        )

        if best_index < len(image_names):
            best_image = image_names[
                best_index
            ]
        else:
            best_image = str(best_index)

        candidates.append({
            "id": fid,
            "G": G,
            "E": E,
            "C": C,
            "S": S,
            "BEST": BEST,
            "best_image": best_image,
        })

    base_results[str(path)] = candidates

    if index % 25 == 0 or index == len(paths):
        print(
            f"  [{index}/{len(paths)}]"
        )

print()
print("Component calculation complete.")
print()

# ============================================================
# CALCULATE EACH WEIGHT SET
# ============================================================

all_results = {}

for set_name, weights in WEIGHT_SETS.items():

    wg, we, wc, ws, wb = weights

    print(
        f"Running {set_name}: "
        f"G={wg:.2f} "
        f"E={we:.2f} "
        f"C={wc:.2f} "
        f"S={ws:.2f} "
        f"BEST={wb:.2f}"
    )

    results = {}

    for path, candidates in base_results.items():

        ranked = []

        for c in candidates:

            final = (
                wg * c["G"]
                + we * c["E"]
                + wc * c["C"]
                + ws * c["S"]
                + wb * c["BEST"]
            )

            item = dict(c)
            item["FINAL"] = final

            ranked.append(item)

        ranked.sort(
            key=lambda x: x["FINAL"],
            reverse=True,
        )

        results[path] = ranked

    all_results[set_name] = results

# ============================================================
# OUTPUT
# ============================================================

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)

# ------------------------------------------------------------
# MAIN REPORT
# ------------------------------------------------------------

report = []

report.append("=" * 100)
report.append("SCENE FINGERPRINT WEIGHT BENCHMARK")
report.append("=" * 100)
report.append("")

report.append(
    f"Images: {len(paths)}"
)

report.append(
    f"Fingerprints: {len(fingerprint_ids)}"
)

report.append("")

report.append(
    "WEIGHTS:"
)

for name, w in WEIGHT_SETS.items():

    report.append(
        f"{name:12} "
        f"G={w[0]:.2f} "
        f"E={w[1]:.2f} "
        f"C={w[2]:.2f} "
        f"S={w[3]:.2f} "
        f"BEST={w[4]:.2f}"
    )

report.append("")
report.append("=" * 100)
report.append("")

# ------------------------------------------------------------
# DISTRIBUTION
# ------------------------------------------------------------

for set_name in WEIGHT_SETS:

    report.append(
        "=" * 100
    )

    report.append(
        f"RESULT DISTRIBUTION: {set_name}"
    )

    report.append(
        "=" * 100
    )

    counter = defaultdict(int)

    for path in paths:

        ranked = all_results[
            set_name
        ][str(path)]

        if ranked:
            counter[
                ranked[0]["id"]
            ] += 1

    for fid, count in sorted(
        counter.items(),
        key=lambda x: -x[1]
    ):

        pct = (
            count
            / len(paths)
            * 100
        )

        report.append(
            f"{fid:12} "
            f"{count:4d} "
            f"{pct:6.2f}%"
        )

    report.append("")

# ------------------------------------------------------------
# CHANGED DECISIONS
# ------------------------------------------------------------

current = all_results[
    "A_CURRENT"
]

for set_name in WEIGHT_SETS:

    if set_name == "A_CURRENT":
        continue

    report.append(
        "=" * 100
    )

    report.append(
        f"CHANGED DECISIONS: "
        f"A_CURRENT -> {set_name}"
    )

    report.append(
        "=" * 100
    )

    changes = []

    for path in paths:

        path = str(path)

        a = current[path]
        b = all_results[
            set_name
        ][path]

        if not a or not b:
            continue

        if a[0]["id"] != b[0]["id"]:

            changes.append(
                (
                    path,
                    a[0],
                    a[1],
                    b[0],
                    b[1],
                )
            )

    report.append(
        f"Changed: {len(changes)}"
    )

    report.append("")

    for path, a1, a2, b1, b2 in changes:

        report.append(
            Path(path).name
        )

        report.append(
            f"  CURRENT "
            f"{a1['id']:10} "
            f"{a1['FINAL']:.4f} "
            f"vs "
            f"{a2['id']:10} "
            f"{a2['FINAL']:.4f} "
            f"margin="
            f"{a1['FINAL']-a2['FINAL']:.4f}"
        )

        report.append(
            f"  NEW     "
            f"{b1['id']:10} "
            f"{b1['FINAL']:.4f} "
            f"vs "
            f"{b2['id']:10} "
            f"{b2['FINAL']:.4f} "
            f"margin="
            f"{b1['FINAL']-b2['FINAL']:.4f}"
        )

        report.append(
            f"  NEW TOP1 "
            f"G={b1['G']:.4f} "
            f"E={b1['E']:.4f} "
            f"C={b1['C']:.4f} "
            f"S={b1['S']:.4f} "
            f"BEST={b1['BEST']:.4f} "
            f"BEST_IMG={b1['best_image']}"
        )

        report.append(
            f"  NEW TOP2 "
            f"G={b2['G']:.4f} "
            f"E={b2['E']:.4f} "
            f"C={b2['C']:.4f} "
            f"S={b2['S']:.4f} "
            f"BEST={b2['BEST']:.4f} "
            f"BEST_IMG={b2['best_image']}"
        )

        report.append("")

# ------------------------------------------------------------
# LOW MARGIN
# ------------------------------------------------------------

for set_name in WEIGHT_SETS:

    report.append(
        "=" * 100
    )

    report.append(
        f"LOW MARGIN CASES: {set_name}"
    )

    report.append(
        "=" * 100
    )

    low = []

    for path in paths:

        ranked = all_results[
            set_name
        ][str(path)]

        if len(ranked) < 2:
            continue

        margin = (
            ranked[0]["FINAL"]
            - ranked[1]["FINAL"]
        )

        low.append(
            (
                margin,
                path,
                ranked[0],
                ranked[1],
            )
        )

    low.sort(
        key=lambda x: x[0]
    )

    for margin, path, first, second in low[:50]:

        report.append(
            f"{Path(path).name}"
        )

        report.append(
            f"  {first['id']:10} "
            f"{first['FINAL']:.4f} "
            f"G={first['G']:.4f} "
            f"E={first['E']:.4f} "
            f"C={first['C']:.4f} "
            f"S={first['S']:.4f} "
            f"BEST={first['BEST']:.4f}"
        )

        report.append(
            f"  {second['id']:10} "
            f"{second['FINAL']:.4f} "
            f"G={second['G']:.4f} "
            f"E={second['E']:.4f} "
            f"C={second['C']:.4f} "
            f"S={second['S']:.4f} "
            f"BEST={second['BEST']:.4f}"
        )

        report.append(
            f"  MARGIN={margin:.4f}"
        )

        report.append("")

# ------------------------------------------------------------
# FULL RESULTS
# ------------------------------------------------------------

report.append(
    "=" * 100
)

report.append(
    "FULL RESULTS"
)

report.append(
    "=" * 100
)

for path in paths:

    path = str(path)

    report.append(
        f"## {Path(path).name}"
    )

    for set_name in WEIGHT_SETS:

        ranked = all_results[
            set_name
        ][path]

        report.append(
            f"[{set_name}]"
        )

        for rank, c in enumerate(
            ranked[:TOP_K],
            1,
        ):

            report.append(
                f"{rank}. "
                f"{c['id']:10} "
                f"FINAL={c['FINAL']:.4f} "
                f"G={c['G']:.4f} "
                f"E={c['E']:.4f} "
                f"C={c['C']:.4f} "
                f"S={c['S']:.4f} "
                f"BEST={c['BEST']:.4f} "
                f"IMG={c['best_image']}"
            )

        report.append("")

    report.append("")

report_path = (
    OUTPUT
    / "benchmark_report.txt"
)

report_path.write_text(
    "\n".join(report),
    encoding="utf-8",
)

# ============================================================
# CSV-LIKE DATA
# ============================================================

csv_lines = [
    "image,weight_set,rank,id,final,G,E,C,S,BEST,best_image"
]

for path in paths:

    path = str(path)

    for set_name in WEIGHT_SETS:

        ranked = all_results[
            set_name
        ][path]

        for rank, c in enumerate(
            ranked[:TOP_K],
            1,
        ):

            csv_lines.append(
                ",".join([
                    Path(path).name.replace(",", " "),
                    set_name,
                    str(rank),
                    c["id"],
                    f"{c['FINAL']:.6f}",
                    f"{c['G']:.6f}",
                    f"{c['E']:.6f}",
                    f"{c['C']:.6f}",
                    f"{c['S']:.6f}",
                    f"{c['BEST']:.6f}",
                    c["best_image"].replace(",", " "),
                ])
            )

csv_path = (
    OUTPUT
    / "benchmark_results.csv"
)

csv_path.write_text(
    "\n".join(csv_lines),
    encoding="utf-8",
)

print()
print("=" * 90)
print("DONE")
print("=" * 90)
print()
print(
    f"Report: {report_path}"
)
print(
    f"CSV:    {csv_path}"
)
print()
PY
```

### 2. Запускаем именно через `uv`

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python /tmp/benchmark_weights.py
```

Это важно — `/tmp/benchmark_weights.py` теперь запускается **в окружении проекта uv**, поэтому ошибки `No module named app` не будет.

---

После выполнения у нас будут:

```text
data/benchmark_weights/
├── benchmark_report.txt
└── benchmark_results.csv
```

**`benchmark_report.txt`** — основной файл, который мы потом будем вместе анализировать.

Особенно интересуют разделы:

```text
RESULT DISTRIBUTION
CHANGED DECISIONS
LOW MARGIN CASES
FULL RESULTS
```

И самое главное — `CHANGED DECISIONS`: там будет видно, **какие конкретно фотографии исправляются добавлением BEST, а какие, наоборот, начинают ошибочно переходить на другого кандидата**.

После прогона просто пришли сюда содержимое `benchmark_report.txt` (или первые/интересующие разделы), и уже по фактам выберем оптимальный вес `BEST`.

---

### 👤 **User** — 2026-08-15 12:16:27

| image                     | weight\_set | rank | id      | final    | G        | E        | C        | S        | BEST     | best\_image |
| ------------------------- | ----------- | ---- | ------- | -------- | -------- | -------- | -------- | -------- | -------- | ----------- |
| Ленина 125-127 А (1).JPG  | A\_CURRENT  | 1    | 84\_v33 | 0.881931 | 0.871238 | 0.896933 | 0.907643 | 0.97141  | 0.944307 | 84\_026.JPG |
| Ленина 125-127 А (1).JPG  | A\_CURRENT  | 2    | 87\_v33 | 0.857721 | 0.840461 | 0.89474  | 0.876607 | 0.969586 | 0.860633 | 87\_044.JPG |
| Ленина 125-127 А (1).JPG  | A\_CURRENT  | 3    | 79\_v33 | 0.845869 | 0.827497 | 0.878755 | 0.883387 | 0.967779 | 0.830886 | 79\_061.JPG |
| Ленина 125-127 А (1).JPG  | A\_CURRENT  | 4    | 81\_v33 | 0.842996 | 0.824315 | 0.888497 | 0.845792 | 0.969037 | 0.856003 | 81\_003.JPG |
| Ленина 125-127 А (1).JPG  | A\_CURRENT  | 5    | 83\_v33 | 0.836778 | 0.829145 | 0.858887 | 0.796654 | 0.9611   | 0.836615 | 83\_048.JPG |
| Ленина 125-127 А (1).JPG  | B\_BEST\_02 | 1    | 84\_v33 | 0.883392 | 0.871238 | 0.896933 | 0.907643 | 0.97141  | 0.944307 | 84\_026.JPG |
| Ленина 125-127 А (1).JPG  | B\_BEST\_02 | 2    | 87\_v33 | 0.858124 | 0.840461 | 0.89474  | 0.876607 | 0.969586 | 0.860633 | 87\_044.JPG |
| Ленина 125-127 А (1).JPG  | B\_BEST\_02 | 3    | 79\_v33 | 0.845937 | 0.827497 | 0.878755 | 0.883387 | 0.967779 | 0.830886 | 79\_061.JPG |
| Ленина 125-127 А (1).JPG  | B\_BEST\_02 | 4    | 81\_v33 | 0.84363  | 0.824315 | 0.888497 | 0.845792 | 0.969037 | 0.856003 | 81\_003.JPG |
| Ленина 125-127 А (1).JPG  | B\_BEST\_02 | 5    | 83\_v33 | 0.836927 | 0.829145 | 0.858887 | 0.796654 | 0.9611   | 0.836615 | 83\_048.JPG |
| Ленина 125-127 А (1).JPG  | C\_BEST\_05 | 1    | 84\_v33 | 0.885584 | 0.871238 | 0.896933 | 0.907643 | 0.97141  | 0.944307 | 84\_026.JPG |
| Ленина 125-127 А (1).JPG  | C\_BEST\_05 | 2    | 87\_v33 | 0.858729 | 0.840461 | 0.89474  | 0.876607 | 0.969586 | 0.860633 | 87\_044.JPG |
| Ленина 125-127 А (1).JPG  | C\_BEST\_05 | 3    | 79\_v33 | 0.846039 | 0.827497 | 0.878755 | 0.883387 | 0.967779 | 0.830886 | 79\_061.JPG |
| Ленина 125-127 А (1).JPG  | C\_BEST\_05 | 4    | 81\_v33 | 0.844581 | 0.824315 | 0.888497 | 0.845792 | 0.969037 | 0.856003 | 81\_003.JPG |
| Ленина 125-127 А (1).JPG  | C\_BEST\_05 | 5    | 83\_v33 | 0.837151 | 0.829145 | 0.858887 | 0.796654 | 0.9611   | 0.836615 | 83\_048.JPG |
| Ленина 125-127 А (1).JPG  | D\_BEST\_10 | 1    | 84\_v33 | 0.889237 | 0.871238 | 0.896933 | 0.907643 | 0.97141  | 0.944307 | 84\_026.JPG |
| Ленина 125-127 А (1).JPG  | D\_BEST\_10 | 2    | 87\_v33 | 0.859738 | 0.840461 | 0.89474  | 0.876607 | 0.969586 | 0.860633 | 87\_044.JPG |
| Ленина 125-127 А (1).JPG  | D\_BEST\_10 | 3    | 79\_v33 | 0.846208 | 0.827497 | 0.878755 | 0.883387 | 0.967779 | 0.830886 | 79\_061.JPG |
| Ленина 125-127 А (1).JPG  | D\_BEST\_10 | 4    | 81\_v33 | 0.846165 | 0.824315 | 0.888497 | 0.845792 | 0.969037 | 0.856003 | 81\_003.JPG |
| Ленина 125-127 А (1).JPG  | D\_BEST\_10 | 5    | 83\_v33 | 0.837525 | 0.829145 | 0.858887 | 0.796654 | 0.9611   | 0.836615 | 83\_048.JPG |
| Ленина 125-127 А (1).JPG  | E\_BEST\_15 | 1    | 84\_v33 | 0.892891 | 0.871238 | 0.896933 | 0.907643 | 0.97141  | 0.944307 | 84\_026.JPG |
| Ленина 125-127 А (1).JPG  | E\_BEST\_15 | 2    | 87\_v33 | 0.860746 | 0.840461 | 0.89474  | 0.876607 | 0.969586 | 0.860633 | 87\_044.JPG |
| Ленина 125-127 А (1).JPG  | E\_BEST\_15 | 3    | 81\_v33 | 0.84775  | 0.824315 | 0.888497 | 0.845792 | 0.969037 | 0.856003 | 81\_003.JPG |
| Ленина 125-127 А (1).JPG  | E\_BEST\_15 | 4    | 79\_v33 | 0.846378 | 0.827497 | 0.878755 | 0.883387 | 0.967779 | 0.830886 | 79\_061.JPG |
| Ленина 125-127 А (1).JPG  | E\_BEST\_15 | 5    | 83\_v33 | 0.837898 | 0.829145 | 0.858887 | 0.796654 | 0.9611   | 0.836615 | 83\_048.JPG |
| Ленина 125-127 А (10).JPG | A\_CURRENT  | 1    | 87\_v33 | 0.896861 | 0.888299 | 0.912319 | 0.9054   | 0.973646 | 0.893826 | 87\_011.JPG |
| Ленина 125-127 А (10).JPG | A\_CURRENT  | 2    | 84\_v33 | 0.894985 | 0.879235 | 0.921772 | 0.944351 | 0.968726 | 0.947581 | 84\_010.JPG |
| Ленина 125-127 А (10).JPG | A\_CURRENT  | 3    | 79\_v33 | 0.881853 | 0.869127 | 0.899626 | 0.922537 | 0.965374 | 0.870851 | 79\_040.JPG |
| Ленина 125-127 А (10).JPG | A\_CURRENT  | 4    | 92\_v33 | 0.877599 | 0.863514 | 0.90764  | 0.893281 | 0.969375 | 0.858195 | 92\_041.JPG |
| Ленина 125-127 А (10).JPG | A\_CURRENT  | 5    | 83\_v33 | 0.867235 | 0.860558 | 0.894422 | 0.815499 | 0.962493 | 0.870414 | 83\_048.JPG |
| Ленина 125-127 А (10).JPG | B\_BEST\_02 | 1    | 87\_v33 | 0.896971 | 0.888299 | 0.912319 | 0.9054   | 0.973646 | 0.893826 | 87\_011.JPG |
| Ленина 125-127 А (10).JPG | B\_BEST\_02 | 2    | 84\_v33 | 0.896352 | 0.879235 | 0.921772 | 0.944351 | 0.968726 | 0.947581 | 84\_010.JPG |
| Ленина 125-127 А (10).JPG | B\_BEST\_02 | 3    | 79\_v33 | 0.881888 | 0.869127 | 0.899626 | 0.922537 | 0.965374 | 0.870851 | 79\_040.JPG |
| Ленина 125-127 А (10).JPG | B\_BEST\_02 | 4    | 92\_v33 | 0.877492 | 0.863514 | 0.90764  | 0.893281 | 0.969375 | 0.858195 | 92\_041.JPG |
| Ленина 125-127 А (10).JPG | B\_BEST\_02 | 5    | 83\_v33 | 0.867432 | 0.860558 | 0.894422 | 0.815499 | 0.962493 | 0.870414 | 83\_048.JPG |
| Ленина 125-127 А (10).JPG | C\_BEST\_05 | 1    | 84\_v33 | 0.898402 | 0.879235 | 0.921772 | 0.944351 | 0.968726 | 0.947581 | 84\_010.JPG |
| Ленина 125-127 А (10).JPG | C\_BEST\_05 | 2    | 87\_v33 | 0.897137 | 0.888299 | 0.912319 | 0.9054   | 0.973646 | 0.893826 | 87\_011.JPG |
| Ленина 125-127 А (10).JPG | C\_BEST\_05 | 3    | 79\_v33 | 0.881939 | 0.869127 | 0.899626 | 0.922537 | 0.965374 | 0.870851 | 79\_040.JPG |
| Ленина 125-127 А (10).JPG | C\_BEST\_05 | 4    | 92\_v33 | 0.877333 | 0.863514 | 0.90764  | 0.893281 | 0.969375 | 0.858195 | 92\_041.JPG |
| Ленина 125-127 А (10).JPG | C\_BEST\_05 | 5    | 81\_v33 | 0.867769 | 0.858482 | 0.883792 | 0.862009 | 0.961677 | 0.876134 | 81\_003.JPG |
| Ленина 125-127 А (10).JPG | D\_BEST\_10 | 1    | 84\_v33 | 0.90182  | 0.879235 | 0.921772 | 0.944351 | 0.968726 | 0.947581 | 84\_010.JPG |
| Ленина 125-127 А (10).JPG | D\_BEST\_10 | 2    | 87\_v33 | 0.897413 | 0.888299 | 0.912319 | 0.9054   | 0.973646 | 0.893826 | 87\_011.JPG |
| Ленина 125-127 А (10).JPG | D\_BEST\_10 | 3    | 79\_v33 | 0.882025 | 0.869127 | 0.899626 | 0.922537 | 0.965374 | 0.870851 | 79\_040.JPG |
| Ленина 125-127 А (10).JPG | D\_BEST\_10 | 4    | 92\_v33 | 0.877067 | 0.863514 | 0.90764  | 0.893281 | 0.969375 | 0.858195 | 92\_041.JPG |
| Ленина 125-127 А (10).JPG | D\_BEST\_10 | 5    | 81\_v33 | 0.868652 | 0.858482 | 0.883792 | 0.862009 | 0.961677 | 0.876134 | 81\_003.JPG |
| Ленина 125-127 А (10).JPG | E\_BEST\_15 | 1    | 84\_v33 | 0.905237 | 0.879235 | 0.921772 | 0.944351 | 0.968726 | 0.947581 | 84\_010.JPG |
| Ленина 125-127 А (10).JPG | E\_BEST\_15 | 2    | 87\_v33 | 0.89769  | 0.888299 | 0.912319 | 0.9054   | 0.973646 | 0.893826 | 87\_011.JPG |
| Ленина 125-127 А (10).JPG | E\_BEST\_15 | 3    | 79\_v33 | 0.882112 | 0.869127 | 0.899626 | 0.922537 | 0.965374 | 0.870851 | 79\_040.JPG |
| Ленина 125-127 А (10).JPG | E\_BEST\_15 | 4    | 92\_v33 | 0.876801 | 0.863514 | 0.90764  | 0.893281 | 0.969375 | 0.858195 | 92\_041.JPG |
| Ленина 125-127 А (10).JPG | E\_BEST\_15 | 5    | 81\_v33 | 0.869534 | 0.858482 | 0.883792 | 0.862009 | 0.961677 | 0.876134 | 81\_003.JPG |
| Ленина 125-127 А (11).JPG | A\_CURRENT  | 1    | 84\_v33 | 0.899442 | 0.884825 | 0.919763 | 0.958573 | 0.967044 | 0.948665 | 84\_010.JPG |
| Ленина 125-127 А (11).JPG | A\_CURRENT  | 2    | 87\_v33 | 0.893362 | 0.880302 | 0.912957 | 0.934652 | 0.971132 | 0.887667 | 87\_007.JPG |
| Ленина 125-127 А (11).JPG | A\_CURRENT  | 3    | 79\_v33 | 0.880784 | 0.866403 | 0.897558 | 0.942451 | 0.960605 | 0.865742 | 79\_040.JPG |
| Ленина 125-127 А (11).JPG | A\_CURRENT  | 4    | 92\_v33 | 0.873244 | 0.861376 | 0.901832 | 0.871182 | 0.964409 | 0.858418 | 92\_041.JPG |
| Ленина 125-127 А (11).JPG | A\_CURRENT  | 5    | 81\_v33 | 0.868319 | 0.860275 | 0.880569 | 0.875963 | 0.956514 | 0.873649 | 81\_003.JPG |
| Ленина 125-127 А (11).JPG | B\_BEST\_02 | 1    | 84\_v33 | 0.900718 | 0.884825 | 0.919763 | 0.958573 | 0.967044 | 0.948665 | 84\_010.JPG |
| Ленина 125-127 А (11).JPG | B\_BEST\_02 | 2    | 87\_v33 | 0.893509 | 0.880302 | 0.912957 | 0.934652 | 0.971132 | 0.887667 | 87\_007.JPG |
| Ленина 125-127 А (11).JPG | B\_BEST\_02 | 3    | 79\_v33 | 0.880771 | 0.866403 | 0.897558 | 0.942451 | 0.960605 | 0.865742 | 79\_040.JPG |
| Ленина 125-127 А (11).JPG | B\_BEST\_02 | 4    | 92\_v33 | 0.873185 | 0.861376 | 0.901832 | 0.871182 | 0.964409 | 0.858418 | 92\_041.JPG |
| Ленина 125-127 А (11).JPG | B\_BEST\_02 | 5    | 81\_v33 | 0.868586 | 0.860275 | 0.880569 | 0.875963 | 0.956514 | 0.873649 | 81\_003.JPG |
| Ленина 125-127 А (11).JPG | C\_BEST\_05 | 1    | 84\_v33 | 0.902634 | 0.884825 | 0.919763 | 0.958573 | 0.967044 | 0.948665 | 84\_010.JPG |
| Ленина 125-127 А (11).JPG | C\_BEST\_05 | 2    | 87\_v33 | 0.89373  | 0.880302 | 0.912957 | 0.934652 | 0.971132 | 0.887667 | 87\_007.JPG |
| Ленина 125-127 А (11).JPG | C\_BEST\_05 | 3    | 79\_v33 | 0.880751 | 0.866403 | 0.897558 | 0.942451 | 0.960605 | 0.865742 | 79\_040.JPG |
| Ленина 125-127 А (11).JPG | C\_BEST\_05 | 4    | 92\_v33 | 0.873097 | 0.861376 | 0.901832 | 0.871182 | 0.964409 | 0.858418 | 92\_041.JPG |
| Ленина 125-127 А (11).JPG | C\_BEST\_05 | 5    | 81\_v33 | 0.868988 | 0.860275 | 0.880569 | 0.875963 | 0.956514 | 0.873649 | 81\_003.JPG |
| Ленина 125-127 А (11).JPG | D\_BEST\_10 | 1    | 84\_v33 | 0.905826 | 0.884825 | 0.919763 | 0.958573 | 0.967044 | 0.948665 | 84\_010.JPG |

---

### 🤖 **Assistant** — 2026-08-15 12:16:29

Да. И вот здесь уже видно **очень важную вещь**: `BEST` действительно может быть полезным дополнительным сигналом, но **не как полноценная замена `FINAL`**, а как усилитель в неоднозначных случаях.

### Что видно на этих результатах

Для `Ленина 125-127 А (10).JPG`:

| Вариант | 1 место | 2 место | Разница |
|---|---|---|---:|
| CURRENT | 87 | 84 | 0.00188 |
| BEST 0.02 | 87 | 84 | 0.00062 |
| BEST 0.05 | **84** | 87 | **0.00127** |
| BEST 0.10 | **84** | 87 | **0.00441** |
| BEST 0.15 | **84** | 87 | **0.00755** |

То есть:

**CURRENT:**
> 87 выигрывает только за счёт глобального DINO.

Но:

> 84 имеет `BEST = 0.9476` против `0.8938` у 87.

Это очень существенная разница — **+0.054** в пользу 84.

И именно здесь твоя мысль подтверждается экспериментом: если дать `BEST` достаточно заметный вес, **84 возвращается на первое место**.

---

### Но есть ещё более интересный момент

Посмотрим на компоненты:

**84:**

```text
G = 0.8792
E = 0.9218
C = 0.9444
S = 0.9687
BEST = 0.9476
```

**87:**

```text
G = 0.8883
E = 0.9123
C = 0.9054
S = 0.9736
BEST = 0.8938
```

То есть 87 выигрывает только:

- Global: +0.0091
- Spatial: +0.0049

А 84 выигрывает:

- Environment: +0.0095
- Color: **+0.0390**
- BEST: **+0.0538**

Это уже очень убедительный профиль.

По сути, система говорит:

> «По общему DINO 87 немного ближе, но по конкретному похожему кадру и по окружению/цвету 84 заметно ближе».

И это именно тот случай, где `BEST` способен исправлять ошибку первого кандидата.

---

## Я бы пока НЕ ставил BEST=0.15

Потому что мы пока видим только несколько фотографий.

`BEST=0.15` уже начинает довольно сильно вмешиваться в решение.

Я бы протестировал сетку:

```text
A  current:
G .70
E .20
C .07
S .03
B .00

B:
G .68
E .20
C .07
S .03
B .02

C:
G .65
E .20
C .07
S .03
B .05

D:
G .60
E .20
C .07
S .03
B .10

E:
G .55
E .20
C .07
S .03
B .15

F:
G .50
E .20
C .07
S .03
B .20
```

Но я бы добавил ещё **G**, где BEST вообще становится главным вторичным сигналом:

```text
G:
G .60
E .20
C .05
S .03
B .12
```

---

# И главное — нам надо оценивать не только процент правильных ответов

В нашем случае важны **три показателя**:

### 1. Correct Top-1

Сколько фотографий получили правильный адрес первым.

Это основной показатель.

### 2. Correct Top-2

Очень важен именно для нашей будущей логики.

Например:

```text
FINAL:

1. 87
2. 84
```

Если `87` имеет низкий margin, а `84` имеет значительно лучший `BEST`, система может сказать:

> **87 — первый кандидат, но 84 — сильный альтернативный кандидат.**

И тогда уже можно запускать дополнительный механизм.

### 3. Ошибочные уверенные решения

Это, на мой взгляд, **самый важный показатель**.

Например:

```text
правильный = 84

87:
FINAL 0.8969
```

Если система выдаёт 87 как:

```text
CONFIDENCE HIGH
```

— это плохо.

А если мы можем определить:

```text
87 / 84
margin = 0.0019
BEST:
84 = 0.9476
87 = 0.8938
```

то система должна понимать:

> **«Я не уверен. Надо посмотреть второго кандидата».**

---

# Я бы вообще не делал BEST постоянной частью FINAL

Это важный момент.

Мне сейчас больше нравится архитектура:

```text
                 DINO GLOBAL
                     │
                     ▼
              ┌─────────────┐
              │ TOP CANDIDATES│
              └──────┬──────┘
                     │
             margin маленький?
                     │
               YES ──┘
                     ▼
        ┌─────────────────────────┐
        │ дополнительный анализ   │
        │                         │
        │ Environment             │
        │ Color                   │
        │ Spatial                 │
        │ BEST IMAGE              │
        └────────────┬────────────┘
                     ▼
              окончательное решение
```

То есть **BEST не обязательно нужен для всех 262 фотографий**.

Для простых случаев:

```text
78 = 0.947
92 = 0.871
margin = 0.076
```

Зачем нам BEST?

Можно сразу принять `78`.

А вот:

```text
87 = 0.8969
84 = 0.8950
margin = 0.0019
```

— это как раз случай для дополнительного анализа.

---

## И ещё интереснее

У нас уже есть готовая информация:

```text
G
E
C
S
BEST
```

Поэтому следующим экспериментом я бы сделал **не просто подбор весов**, а сделал итоговый отчёт примерно такого вида:

```text
IMAGE: Ленина 125-127 А (10).JPG
EXPECTED: 84_v33

CURRENT
  TOP1: 87_v33       WRONG
  TOP2: 84_v33
  margin: 0.0019

BEST_05
  TOP1: 84_v33       CORRECT
  margin: 0.0013

BEST_10
  TOP1: 84_v33       CORRECT
  margin: 0.0044
```

А в конце:

```text
================================================================================
WEIGHT EXPERIMENT SUMMARY
================================================================================

WEIGHTS             TOP1 CORRECT    TOP2 CORRECT    WRONG HIGH-CONF
CURRENT             78.2%           94.1%           17
BEST_02             79.0%           94.5%           16
BEST_05             81.3%           95.2%           12
BEST_10             82.1%           95.8%            9
BEST_15             81.7%           95.4%           10
```

**Вот после такого отчёта уже можно принимать решение.**

Причём я бы отдельно посчитал:

```text
ALL 262
```

и:

```text
ONLY LOW-MARGIN CASES
margin < 0.02
margin < 0.03
margin < 0.05
```

Потому что вполне возможно, что `BEST=0.10` **почти ничего не улучшает на всём массиве**, зато исправляет большую часть именно сложных случаев.

И это будет гораздо более правильная стратегия для LORA: **быстрый DINO → первый кандидат → при сомнении BEST + компактные дескрипторы → окончательное присвоение адреса.**

---

### 👤 **User** — 2026-08-15 12:18:10

давай так

---

### 🤖 **Assistant** — 2026-08-15 12:18:11

Да. Тогда делаем **двухступенчатую схему** и эксперимент не трогаем основной `recognizer.py`.

### Что делаем

1. Берём уже рассчитанные результаты `G/E/C/S/BEST`.
2. Прогоняем несколько наборов весов:
   - `CURRENT` — без BEST
   - `BEST_02`
   - `BEST_05`
   - `BEST_10`
   - `BEST_15`
   - `BEST_20`
3. Для каждого варианта считаем:
   - TOP-1
   - TOP-2
   - ошибки
   - margin
   - отдельно случаи `margin < 0.02`, `< 0.03`, `< 0.05`
4. Отдельно покажем, **какие фотографии изменили кандидата**.
5. Особенно интересуют случаи, где:
   - CURRENT → неправильный;
   - вариант с BEST → правильный.
6. Основной код пока **не меняем**.

Но есть один важный момент: чтобы определить `CORRECT`, нам нужен эталонный адрес фотографии. В твоём наборе он фактически зашит в имени файла/исходной папке. Поэтому скрипт должен корректно извлекать настоящий номер.

Если текущий benchmark уже умеет определять эталон — используем его. Если нет, лучше сначала посмотреть его первые ~100 строк.

Дай:

```bash
sed -n '1,140p' /tmp/benchmark_components.py
```

И я дам тебе **готовую замену скрипта**, которая сразу создаст:

```text
/tmp/weight_experiment.txt
/tmp/weight_experiment.csv
```

и главное — сводную таблицу вроде:

```text
WEIGHT SET       TOP1       TOP2       LOW<.02   LOW<.03   LOW<.05
CURRENT          ...
BEST_02          ...
BEST_05          ...
BEST_10          ...
BEST_15          ...
BEST_20          ...
```

Плюс отдельный блок:

```text
CASES FIXED BY BEST
```

где будет видно конкретно:

```text
Ленина 125-127 А (10).JPG
CURRENT: 87_v33  WRONG
BEST_05: 84_v33  CORRECT
BEST_10: 84_v33  CORRECT
BEST_15: 84_v33  CORRECT
```

Это даст нам уже **объективное основание выбрать веса**, а не подбирать их по нескольким фотографиям.

---

### 👤 **User** — 2026-08-15 12:18:38

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '1,140p' /tmp/benchmark_components.py
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
manager = FingerprintManager(settings, embedder)

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

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 12:18:39

Да. Сейчас у тебя `/tmp/benchmark_components.py` уже почти готов. Но я бы сделал следующий прогон **не просто benchmark**, а полноценный эксперимент:

- `A_CURRENT` — текущие веса `G=.70 E=.20 C=.07 S=.03`
- `B_BEST_02` — добавить `BEST × .02`
- `C_BEST_05` — `BEST × .05`
- `D_BEST_10` — `BEST × .10`
- `E_BEST_15` — `BEST × .15`
- при этом **сохранять исходные G/E/C/S**
- для каждого изображения сохранять **TOP-5**
- отдельно считать, кто победил при каждом наборе весов
- отдельно сохранять случаи, когда `BEST` перевернул результат
- в конце сделать сводку по всем 262 фотографиям.

Но есть важный момент: если просто прибавлять `BEST`, сумма весов становится >1. Это не страшно для ранжирования, но лучше нормализовать веса. Поэтому предлагаю считать так:

```text
score =
(G*G + E*E + C*C + S*S + B*BEST)
/
(G+E+C+S+B)
```

Для текущего варианта:

```text
A_CURRENT
G=0.70 E=0.20 C=0.07 S=0.03 B=0
```

Для `BEST_10`:

```text
G=0.70 E=0.20 C=0.07 S=0.03 B=0.10
```

И **BEST не заменяет `best_image_score`**, а является дополнительным сигналом.

Особенно интересно будет посмотреть на твой пример:

```text
84:
G=.8792
E=.9218
C=.9444
S=.9687
BEST=.9476

87:
G=.8883
E=.9123
C=.9054
S=.9736
BEST=.8938
```

Текущая модель выбирает 87 из-за сильного `G`.

Но `BEST` явно говорит в пользу 84.

### Давай заменим `/tmp/benchmark_components.py` целиком

Выполни:

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

# ------------------------------------------------------------
# Weight sets
#
# Formula:
#
# score =
#   (G*G + E*E + C*C + S*S + B*BEST)
#   /
#   (G + E + C + S + B)
#
# ------------------------------------------------------------

WEIGHT_SETS = {
    "A_CURRENT": {
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.00,
    },

    "B_BEST_02": {
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.02,
    },

    "C_BEST_05": {
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.05,
    },

    "D_BEST_10": {
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.10,
    },

    "E_BEST_15": {
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.15,
    },

    "F_BEST_20": {
        "G": 0.70,
        "E": 0.20,
        "C": 0.07,
        "S": 0.03,
        "B": 0.20,
    },
}

# ============================================================
# INIT
# ============================================================

settings = Settings()

embedder = SceneEmbedder(settings)

manager = FingerprintManager(
    settings,
    embedder,
)

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
        print(
            f"{fp_id:<12} ERROR: {exc}"
        )

print()
print(
    f"Loaded: {len(loaded)} fingerprints"
)

# ============================================================
# IMAGES
# ============================================================

paths = image_files(INPUT)

print()
print("=" * 100)
print("INPUT")
print("=" * 100)
print(
    f"Images: {len(paths)}"
)

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
    queries = queries.reshape(
        1,
        -1,
    )

# ============================================================
# OUTPUT
# ============================================================

output = Path(
    "output/benchmark_components"
)

output.mkdir(
    parents=True,
    exist_ok=True,
)

summary_file = (
    output / "components.txt"
)

csv_file = (
    output / "components.csv"
)

# ============================================================
# SCORE
# ============================================================

def weighted_score(
    global_score,
    environment_score,
    color_score,
    spatial_score,
    best_image_score,
    weights,
):

    total_weight = (
        weights["G"]
        + weights["E"]
        + weights["C"]
        + weights["S"]
        + weights["B"]
    )

    if total_weight <= 0:
        return 0.0

    score = (
        weights["G"]
        * global_score
        + weights["E"]
        * environment_score
        + weights["C"]
        * color_score
        + weights["S"]
        * spatial_score
        + weights["B"]
        * best_image_score
    )

    return float(
        score / total_weight
    )

# ============================================================
# CSV HEADER
# ============================================================

csv_header = [
    "image",
    "weight_set",
    "rank",
    "id",
    "final",
    "G",
    "E",
    "C",
    "S",
    "BEST",
    "best_image",
]

# ============================================================
# PROCESS
# ============================================================

summary_rows = []

with summary_file.open(
    "w",
    encoding="utf-8",
) as out, csv_file.open(
    "w",
    encoding="utf-8",
) as csv:

    csv.write(
        ",".join(csv_header)
        + "\n"
    )

    for index, (
        path,
        query_global,
    ) in enumerate(
        zip(paths, queries),
        1,
    ):

        print(
            f"\n[{index}/{len(paths)}] "
            f"{path.name}"
        )

        out.write(
            "\n"
            + "=" * 100
            + "\n"
        )

        out.write(
            f"IMAGE: {path.name}\n"
        )

        # ----------------------------------------------------
        # descriptors
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # calculate component scores once
        # ----------------------------------------------------

        components = []

        for fingerprint_id, data in loaded.items():

            try:

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
                    image_scores[
                        best_index
                    ]
                )

                image_names = (
                    data["metadata"]
                    .get(
                        "image_names",
                        [],
                    )
                )

                if (
                    best_index
                    < len(image_names)
                ):
                    best_image = (
                        image_names[
                            best_index
                        ]
                    )
                else:
                    best_image = str(
                        best_index
                    )

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

                components.append(
                    {
                        "id": fingerprint_id,
                        "G": float(
                            global_score
                        ),
                        "E": float(
                            environment_score
                        ),
                        "C": float(
                            color_score
                        ),
                        "S": float(
                            spatial_score
                        ),
                        "BEST": float(
                            best_image_score
                        ),
                        "best_image": best_image,
                    }
                )

            except Exception as exc:

                print(
                    f"ERROR "
                    f"{fingerprint_id}: "
                    f"{exc}"
                )

        # ----------------------------------------------------
        # every weight set
        # ----------------------------------------------------

        for weight_name, weights in (
            WEIGHT_SETS.items()
        ):

            ranked = []

            for item in components:

                final = weighted_score(
                    item["G"],
                    item["E"],
                    item["C"],
                    item["S"],
                    item["BEST"],
                    weights,
                )

                row = dict(item)
                row["final"] = final

                ranked.append(row)

            ranked.sort(
                key=lambda x: x["final"],
                reverse=True,
            )

            # ------------------------------------------------
            # TOP K
            # ------------------------------------------------

            top = ranked[:TOP_K]

            winner = (
                top[0]["id"]
                if top
                else "NONE"
            )

            print(
                f"{weight_name:<14} "
                f"BEST={winner}"
            )

            out.write(
                "\n"
                f"[{weight_name}]\n"
            )

            for rank, item in enumerate(
                top,
                1,
            ):

                line = (
                    f"{rank}. "
                    f"{item['id']:<10} "
                    f"FINAL={item['final']:.6f} "
                    f"G={item['G']:.6f} "
                    f"E={item['E']:.6f} "
                    f"C={item['C']:.6f} "
                    f"S={item['S']:.6f} "
                    f"BEST={item['BEST']:.6f} "
                    f"IMG={item['best_image']}"
                )

                print(line)

                out.write(
                    line + "\n"
                )

                csv.write(
                    ",".join(
                        [
                            path.name.replace(
                                ",",
                                " ",
                            ),
                            weight_name,
                            str(rank),
                            item["id"],
                            f"{item['final']:.6f}",
                            f"{item['G']:.6f}",
                            f"{item['E']:.6f}",
                            f"{item['C']:.6f}",
                            f"{item['S']:.6f}",
                            f"{item['BEST']:.6f}",
                            item["best_image"].replace(
                                ",",
                                " ",
                            ),
                        ]
                    )
                    + "\n"
                )

            summary_rows.append(
                (
                    path.name,
                    weight_name,
                    winner,
                    top[0]["final"]
                    if top
                    else 0.0,
                )
            )

# ============================================================
# SUMMARY
# ============================================================

summary_file.write_text(
    summary_file.read_text(
        encoding="utf-8"
    )
    + "\n\n"
    + "=" * 100
    + "\n"
    + "WINNER SUMMARY\n"
    + "=" * 100
    + "\n",
    encoding="utf-8",
)

from collections import Counter

with summary_file.open(
    "a",
    encoding="utf-8",
) as out:

    for weight_name in WEIGHT_SETS:

        winners = [
            winner
            for image,
            ws,
            winner,
            score
            in summary_rows
            if ws == weight_name
        ]

        counts = Counter(winners)

        out.write(
            f"\n{weight_name}\n"
        )

        for fp, count in (
            counts.most_common()
        ):

            out.write(
                f"  {fp:<12} "
                f"{count:4d}\n"
            )

    # --------------------------------------------------------
    # winner changes
    # --------------------------------------------------------

    out.write(
        "\n"
        + "=" * 100
        + "\n"
        + "WINNER CHANGES\n"
        + "=" * 100
        + "\n"
    )

    images = sorted(
        set(
            image
            for image,
            ws,
            winner,
            score
            in summary_rows
        )
    )

    for image in images:

        winners = {}

        for (
            img,
            ws,
            winner,
            score,
        ) in summary_rows:

            if img == image:
                winners[ws] = winner

        current = winners.get(
            "A_CURRENT"
        )

        changed = []

        for ws, winner in winners.items():

            if (
                ws != "A_CURRENT"
                and winner != current
            ):
                changed.append(
                    f"{ws}={winner}"
                )

        if changed:

            out.write(
                f"\n{image}\n"
            )

            out.write(
                f"  CURRENT = {current}\n"
            )

            for value in changed:

                out.write(
                    f"  {value}\n"
                )

print()
print("=" * 100)
print("DONE")
print("=" * 100)
print(
    f"TXT: {summary_file}"
)
print(
    f"CSV: {csv_file}"
)
PY

uv run python /tmp/benchmark_components.py
```

После завершения получим:

```text
output/benchmark_components/
├── components.txt
└── components.csv
```

### Что особенно будем искать

Не просто какой вариант дал больший `FINAL`, а **стабильность решения**.

Например:

```text
CURRENT:
87

BEST_02:
87

BEST_05:
84

BEST_10:
84

BEST_15:
84
```

Это очень интересный случай. Значит `BEST` действительно вытаскивает правильного кандидата.

А если будет:

```text
CURRENT:
84

BEST_02:
84

BEST_05:
87

BEST_10:
87

BEST_15:
87
```

значит `BEST` начинает вредить.

И самое важное — мы посмотрим **на всех 262 фотографиях**, а не на одном примере.

После прогона просто пришли:

```bash
cat output/benchmark_components/components.txt
```

или лучше:

```bash
tail -200 output/benchmark_components/components.txt
```

и разберём, **какой вес BEST реально оптимален и стоит ли вообще его включать в основной алгоритм**.

---

### 👤 **User** — 2026-08-15 12:20:17

====================================================================================================
WINNER SUMMARY
====================================================================================================

A_CURRENT
  94_v33         24
  78_v33         20
  87_v33         20
  89_v33         20
  83_v33         18
  92_v33         18
  95_v33         17
  85_v33         17
  81_v33         16
  88_v33         16
  86_v33         15
  91_v33         13
  93_v33         12
  82_v33          9
  79_v33          8
  80_v33          8
  84_v33          8
  90_v33          3

B_BEST_02
  94_v33         24
  78_v33         20
  89_v33         20
  87_v33         19
  83_v33         18
  92_v33         18
  95_v33         17
  85_v33         17
  81_v33         16
  88_v33         16
  86_v33         15
  91_v33         13
  93_v33         12
  82_v33          9
  84_v33          9
  79_v33          8
  80_v33          8
  90_v33          3

C_BEST_05
  94_v33         24
  78_v33         20
  89_v33         20
  83_v33         18
  92_v33         18
  87_v33         18
  95_v33         17
  85_v33         17
  81_v33         16
  88_v33         16
  86_v33         15
  91_v33         13
  93_v33         12
  84_v33         10
  82_v33          9
  79_v33          8
  80_v33          8
  90_v33          3

D_BEST_10
  94_v33         24
  78_v33         20
  89_v33         20
  83_v33         18
  92_v33         18
  95_v33         17
  85_v33         17
  87_v33         17
  81_v33         16
  88_v33         16
  86_v33         15
  91_v33         13
  93_v33         12
  84_v33         11
  82_v33          9
  79_v33          8
  80_v33          8
  90_v33          3

E_BEST_15
  94_v33         24
  78_v33         20
  89_v33         20
  83_v33         18
  92_v33         18
  95_v33         17
  85_v33         17
  87_v33         17
  81_v33         16
  88_v33         16
  86_v33         15
  91_v33         13
  93_v33         12
  84_v33         11
  82_v33          9
  79_v33          8
  80_v33          8
  90_v33          3

F_BEST_20
  94_v33         24
  78_v33         20
  89_v33         20
  83_v33         18
  92_v33         18
  95_v33         17
  85_v33         17
  87_v33         17
  81_v33         16
  88_v33         16
  86_v33         15
  91_v33         13
  93_v33         12
  84_v33         11
  82_v33          9
  79_v33          8
  80_v33          8
  90_v33          3

====================================================================================================
WINNER CHANGES
====================================================================================================

Ленина 125-127 А (10).JPG
  CURRENT = 87_v33
  C_BEST_05=84_v33
  D_BEST_10=84_v33
  E_BEST_15=84_v33
  F_BEST_20=84_v33

Ленина 125-127 А (14).JPG
  CURRENT = 87_v33
  B_BEST_02=84_v33
  C_BEST_05=84_v33
  D_BEST_10=84_v33
  E_BEST_15=84_v33
  F_BEST_20=84_v33

Ленина 125-127 А (8).JPG
  CURRENT = 87_v33
  D_BEST_10=84_v33
  E_BEST_15=84_v33
  F_BEST_20=84_v33
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

