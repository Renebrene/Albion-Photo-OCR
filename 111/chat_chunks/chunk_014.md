## СЕССИЯ: LORA

**Создано:** 2026-08-07 22:33:24
**Обновлено:** 2026-08-19 17:08:04
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a763210-b338-83ea-a6ba-645183fe112c](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a763210-b338-83ea-a6ba-645183fe112c)

---

### 🤖 **Assistant** — 2026-08-13 21:24:08

Отлично. **Вот теперь всё работает правильно.** Конфигурация DINOv2 успешно скачалась с обычного Hugging Face.

Ключевой результат:

```text
HF ENDPOINT: https://huggingface.co
SUCCESS
model_type: dinov2
hidden_size: 768
num_hidden_layers: 12
```

То есть:

- `.venv` исправлен;
- `transformers` установлен;
- Hugging Face доступен;
- `facebook/dinov2-base` найден;
- архитектура соответствует нашему `768`-мерному fingerprint;
- проблема с `hf-mirror.com` найдена.

### Но есть одна важная вещь

У тебя в `~/.bashrc` всё ещё стоит:

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

Поэтому после нового входа в терминал проблема **вернётся**.

Сейчас исправим это аккуратно.

Выполни:

```bash
sed -i 's/^export HF_ENDPOINT=https:\/\/hf-mirror.com/# export HF_ENDPOINT=https:\/\/hf-mirror.com/' ~/.bashrc
```

Проверь:

```bash
grep -n "HF_ENDPOINT" ~/.bashrc
```

Должно быть:

```text
120:# export HF_ENDPOINT=https://hf-mirror.com
```

Затем:

```bash
source ~/.bashrc
```

и:

```bash
echo "HF_ENDPOINT=$HF_ENDPOINT"
```

Должно быть пусто:

```text
HF_ENDPOINT=
```

---

## Теперь загружаем сам DINOv2

Запускаем **не fingerprint**, а сначала отдельный тест:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python -c "
import torch
from transformers import AutoModel

print('===== LOADING DINOv2 =====')
print('Model: facebook/dinov2-base')
print('Device: cuda')

model = AutoModel.from_pretrained('facebook/dinov2-base')
model = model.to('cuda')
model.eval()

print()
print('===== SUCCESS =====')
print('hidden size:', model.config.hidden_size)
print('layers:', model.config.num_hidden_layers)
print('GPU:', torch.cuda.get_device_name(0))
print('CUDA:', torch.cuda.is_available())
"
```

### Важный момент

При первом запуске сейчас может начаться скачивание:

```text
config.json
model.safetensors
...
```

Это **нормально**.

Модель `dinov2-base` будет сохранена в:

```text
~/.cache/huggingface/hub/
```

После этого повторно скачивать её не потребуется.

---

### И ещё

У нас сейчас `embedder.py` уже переведён обратно на:

```python
AutoImageProcessor
AutoModel
```

Это правильное направление для этого проекта. **Не возвращаемся к `torch.hub.load()`**, потому что тот вариант требует отдельной загрузки репозитория `facebookresearch/dinov2` через GitHub и именно он первоначально дал:

```text
RemoteDisconnected
```

После успешной загрузки модели следующим тестом проверим непосредственно:

```text
Image → DINOv2 → CLS → normalize → 768
```

и только потом запустим:

```bash
uv run scene-fingerprint create 83_v33 data/input/83
```

Сейчас выполни тест загрузки модели выше и пришли вывод.

---

### 👤 **User** — 2026-08-13 21:25:25

120:# export HF_ENDPOINT=https://hf-mirror.com
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ source ~/.bashrc
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python -c "
import torch
from transformers import AutoModel

print('===== LOADING DINOv2 =====')
print('Model: facebook/dinov2-base')
print('Device: cuda')

model = AutoModel.from_pretrained('facebook/dinov2-base')
model = model.to('cuda')
model.eval()

print()
print('===== SUCCESS =====')
print('hidden size:', model.config.hidden_size)
print('layers:', model.config.num_hidden_layers)
print('GPU:', torch.cuda.get_device_name(0))
print('CUDA:', torch.cuda.is_available())
"
===== LOADING DINOv2 =====
Model: facebook/dinov2-base
Device: cuda
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9070.13it/s]

===== SUCCESS =====
hidden size: 768
layers: 12
GPU: NVIDIA GeForce RTX 3060
CUDA: True
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-13 21:25:27

Отлично. **Модель теперь загружается полностью и работает на RTX 3060.** Проблема с окружением и загрузкой DINOv2 решена.

Получили:

```text
hidden size: 768
layers: 12
GPU: NVIDIA GeForce RTX 3060
CUDA: True
```

Предупреждение:

```text
Warning: You are sending unauthenticated requests...
```

**не является ошибкой.** Токен Hugging Face для нашей задачи не нужен.

Теперь не надо ничего переустанавливать. Следующий шаг — проверить именно `SceneEmbedder`, потому что модель отдельно уже работает.

### 1. Проверяем embedder

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python -c "
from app.core.config import Settings
from app.core.embedder import SceneEmbedder

print('===== SCENE EMBEDDER TEST =====')

settings = Settings()
embedder = SceneEmbedder(settings)

print()
print('===== EMBEDDER OK =====')
print('dimension:', embedder.dimension)
print('device:', embedder.device)
"
```

Ожидаем:

```text
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
...
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] Ready.
```

### 2. Если это пройдёт — сразу проверим реальное изображение

```bash
uv run python -c "
from pathlib import Path
from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from PIL import Image
import numpy as np

settings = Settings()
embedder = SceneEmbedder(settings)

images = sorted(
    Path('data/input/83').glob('*')
)

images = [
    p for p in images
    if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}
]

print()
print('===== INPUT =====')
print('images:', len(images))

img = Image.open(images[0]).convert('RGB')

print('file:', images[0])
print('size:', img.size)

embedding = embedder.embed_images([img])

print()
print('===== EMBEDDING =====')
print('shape:', embedding.shape)
print('dtype:', embedding.dtype)
print('norm:', np.linalg.norm(embedding[0]))
print('finite:', np.isfinite(embedding).all())
print('first 10:', embedding[0][:10])
"
```

Здесь особенно важно получить:

```text
shape: (1, 768)
dtype: float32
norm: ~1.0
finite: True
```

Если это будет так, значит цепочка:

**изображение → DINOv2 → CLS embedding → normalization → 768 float32**

полностью исправна.

После этого уже запускаем создание:

```bash
uv run scene-fingerprint create 83_v33 data/input/83
```

И **83_v33 должен создаться нормально**.

Сейчас пришли вывод первого теста `SceneEmbedder`.

---

### 👤 **User** — 2026-08-13 21:26:54

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -c "
from pathlib import Path
from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from PIL import Image
import numpy as np

settings = Settings()
embedder = SceneEmbedder(settings)

images = sorted(
    Path('data/input/83').glob('*')
)

images = [
    p for p in images
    if p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}
]

print()
print('===== INPUT =====')
print('images:', len(images))

"rint('first 10:', embedding[0][:10])g).all())
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8544.48it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.

===== INPUT =====
images: 68
file: data/input/83/22 (1).JPG
size: (3552, 2664)

===== EMBEDDING =====
shape: (1, 768)
dtype: float32
norm: 1.0
finite: True
first 10: [ 0.00780171  0.01416933  0.0170775  -0.04522822  0.02127102 -0.01737221
  0.04370104 -0.02614356 -0.06203886  0.02060117]
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run scene-fingerprint create 83_v33 data/input/83
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9509.83it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '83_v33' from 68 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] Saved: data/fingerprints/83_v33
[Fingerprint v3.3] global=(68, 768)
[Fingerprint v3.3] environment=(68, 640)
[Fingerprint v3.3] color=(68, 48)
[Fingerprint v3.3] spatial=(68, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "83_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 68,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "22 (1).JPG",
    "22 (10).JPG",
    "22 (11).JPG",
    "22 (12).JPG",
    "22 (13).JPG",
    "22 (14).JPG",
    "22 (15).JPG",
    "22 (16).JPG",
    "22 (17).JPG",
    "22 (18).JPG",
    "22 (19).JPG",
    "22 (2).JPG",
    "22 (20).JPG",
    "22 (21).JPG",
    "22 (22).JPG",
    "22 (23).JPG",
    "22 (24).JPG",
    "22 (25).JPG",
    "22 (26).JPG",
    "22 (27).JPG",
    "22 (28).JPG",
    "22 (29).JPG",
    "22 (3).JPG",
    "22 (30).JPG",
    "22 (31).JPG",
    "22 (32).JPG",
    "22 (33).JPG",
    "22 (34).JPG",
    "22 (35).JPG",
    "22 (36).JPG",
    "22 (37).JPG",
    "22 (38).JPG",
    "22 (39).JPG",
    "22 (4).JPG",
    "22 (40).JPG",
    "22 (41).JPG",
    "22 (42).JPG",
    "22 (43).JPG",
    "22 (44).JPG",
    "22 (45).JPG",
    "22 (46).JPG",
    "22 (47).JPG",
    "22 (48).JPG",
    "22 (49).JPG",
    "22 (5).JPG",
    "22 (50).JPG",
    "22 (51).JPG",
    "22 (6).JPG",
    "22 (7).JPG",
    "22 (8).JPG",
    "22 (9).JPG",
    "33 (1).JPG",
    "33 (10).JPG",
    "33 (11).JPG",
    "33 (12).JPG",
    "33 (13).JPG",
    "33 (2).JPG",
    "33 (3).JPG",
    "33 (4).JPG",
    "33 (5).JPG",
    "33 (6).JPG",
    "33 (7).JPG",
    "33 (8).JPG",
    "33 (9).JPG",
    "Нагибина 24 А (11).JPG",
    "Нагибина 24 А (23).JPG",
    "Нагибина 24 А (4).JPG",
    "Нагибина 24 А (49).JPG"
  ]
}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-13 21:26:58

Да. **Сейчас окружение полностью восстановлено, DINOv2 работает, и `83_v33` успешно создан.**

Ключевой тест прошёл идеально:

```text
shape: (1, 768)
dtype: float32
norm: 1.0
finite: True
```

А создание fingerprint завершилось:

```text
[Fingerprint v3.3] Saved: data/fingerprints/83_v33
```

Получили:

| Дескриптор | Размер |
|---|---:|
| Global DINOv2 | 68 × 768 |
| Environment | 68 × 640 |
| Color HSV | 68 × 48 |
| Spatial | 68 × 32 |
| Representatives | 16 |
| Patch tokens | **0** |

И веса сейчас:

```text
global       0.70
environment  0.20
color        0.07
spatial      0.03
```

### Что важно

Сейчас у нас **v3.3 Compact**, то есть patch-токены намеренно отключены:

```text
PATCH STORAGE = DISABLED
patch_tokens: 0
patch_storage: false
```

Это не ошибка. Более того, для текущего этапа это хорошо: мы сначала получили **стабильный baseline**.

### Но я бы сейчас не переходил сразу к следующему fingerprint

Нам нужно проверить самое главное — **как `83_v33` реально распознаёт фотографии**.

Иначе мы можем получить красивый fingerprint, но не знать, насколько хорошо работает matching.

Предлагаю следующим шагом сделать контрольный тест:

```text
83
 ↓
83_v33
 ↓
recognize
 ↓
Top-5
 ↓
score / threshold
```

Сначала проверим сами фотографии из `83` — ожидаем, что они будут уверенно находиться как `83_v33`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint recognize \
    data/input/83 \
    --fingerprint 83_v33 \
    --top-k 5 \
    --threshold 0.50
```

**Пришли весь вывод.**

После этого уже сможем понять, насколько хороша текущая формула `0.70/0.20/0.07/0.03` и нужно ли возвращать **patch tokens** в следующую версию.

---

### 👤 **User** — 2026-08-13 21:27:42

uv run scene-fingerprint recognize \
    data/input/83 \
    --fingerprint 83_v33 \
    --top-k 5 \
    --threshold 0.50
usage: scene-fingerprint [-h] {create,analyze,recognize} ...
scene-fingerprint: error: unrecognized arguments: --fingerprint 83_v33
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-13 21:27:44

Да, здесь моя ошибка: я дал неправильный синтаксис CLI. `--fingerprint` находится не на уровне `recognize` в твоей текущей версии CLI.

Ничего не сломалось — команда просто не принята аргументами.

Давай **не угадывать синтаксис**, а посмотрим реальную справку твоей версии.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint recognize --help
```

И сразу:

```bash
uv run scene-fingerprint --help
```

Пришли оба вывода.

По ним я дам **точно соответствующую твоему текущему CLI** команду для проверки `83_v33`.

Это особенно важно, потому что у нас уже есть рабочий `83_v33`, и сейчас лучше ничего не менять в коде и не запускать команды наугад.

---

### 👤 **User** — 2026-08-13 21:28:11

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint recognize --help
usage: scene-fingerprint recognize [-h] [--top-k TOP_K]
                                   [--threshold THRESHOLD] [--json]
                                   folder

positional arguments:
  folder                Folder with query images

options:
  -h, --help            show this help message and exit
  --top-k TOP_K         Number of candidates
  --threshold THRESHOLD
                        Minimum absolute match score
  --json                Output JSON
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run scene-fingerprint --help
usage: scene-fingerprint [-h] {create,analyze,recognize} ...

Scene fingerprinting and recognition v3.3 compact

positional arguments:
  {create,analyze,recognize}
    create              Create v3.3 compact fingerprint
    analyze             Analyze one fingerprint
    recognize           Recognize images

options:
  -h, --help            show this help message and exit
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-13 21:28:12

Отлично. Теперь синтаксис однозначен: `recognize` принимает **только папку**, а fingerprint, судя по CLI, выбирается автоматически из `data/fingerprints`.

То есть запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint recognize \
    data/input/83 \
    --top-k 5 \
    --threshold 0.50
```

Для первого теста я бы **не использовал `--json`**, чтобы увидеть обычный диагностический вывод.

### Что проверяем

У нас есть:

```text
data/fingerprints/83_v33
```

и:

```text
data/input/83
```

Поэтому ожидаем, что `83_v33` будет среди кандидатов с высоким score.

Запусти именно эту команду и пришли **весь вывод от `[SceneEmbedder]` до конца**:

```bash
uv run scene-fingerprint recognize \
    data/input/83 \
    --top-k 5 \
    --threshold 0.50
```

После этого разберём реальные scores и решим, **оставляем ли v3.3 Compact как baseline или возвращаем patch-level анализ**.

---

### 👤 **User** — 2026-08-13 21:31:10

[Recognizer] Fingerprints: 78_v33, 79_v33, 80_v33, 81_v33, 82_v33, 83_v33

## 22 (1).JPG

MATCH        83_v33
SCORE        0.9724
SECOND       0.8833
MARGIN       0.0891
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (1).JPG

TOP CANDIDATES
1. 83_v33         0.9724
2. 78_v33         0.8833
3. 79_v33         0.8722
4. 81_v33         0.8699
5. 82_v33         0.8225

## 22 (10).JPG

MATCH        83_v33
SCORE        0.9606
SECOND       0.8638
MARGIN       0.0968
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (10).JPG

TOP CANDIDATES
1. 83_v33         0.9606
2. 78_v33         0.8638
3. 79_v33         0.8562
4. 81_v33         0.8363
5. 80_v33         0.8023

## 22 (11).JPG

MATCH        83_v33
SCORE        0.9625
SECOND       0.8683
MARGIN       0.0942
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (11).JPG

TOP CANDIDATES
1. 83_v33         0.9625
2. 79_v33         0.8683
3. 78_v33         0.8473
4. 81_v33         0.8423
5. 80_v33         0.7863

## 22 (12).JPG

MATCH        83_v33
SCORE        0.9413
SECOND       0.8747
MARGIN       0.0666
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (12).JPG

TOP CANDIDATES
1. 83_v33         0.9413
2. 81_v33         0.8747
3. 78_v33         0.8549
4. 79_v33         0.8497
5. 82_v33         0.8256

## 22 (13).JPG

MATCH        83_v33
SCORE        0.9294
SECOND       0.8649
MARGIN       0.0646
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (13).JPG

TOP CANDIDATES
1. 83_v33         0.9294
2. 78_v33         0.8649
3. 79_v33         0.8232
4. 81_v33         0.8195
5. 82_v33         0.7755

## 22 (14).JPG

MATCH        83_v33
SCORE        0.9658
SECOND       0.8761
MARGIN       0.0897
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (14).JPG

TOP CANDIDATES
1. 83_v33         0.9658
2. 79_v33         0.8761
3. 78_v33         0.8659
4. 81_v33         0.8575
5. 80_v33         0.8168

## 22 (15).JPG

MATCH        83_v33
SCORE        0.9684
SECOND       0.8937
MARGIN       0.0748
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (15).JPG

TOP CANDIDATES
1. 83_v33         0.9684
2. 78_v33         0.8937
3. 79_v33         0.8637
4. 81_v33         0.8498
5. 82_v33         0.8100

## 22 (16).JPG

MATCH        83_v33
SCORE        0.9581
SECOND       0.8623
MARGIN       0.0958
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (16).JPG

TOP CANDIDATES
1. 83_v33         0.9581
2. 79_v33         0.8623
3. 78_v33         0.8448
4. 81_v33         0.8414
5. 80_v33         0.7855

## 22 (17).JPG

MATCH        83_v33
SCORE        0.9647
SECOND       0.8640
MARGIN       0.1007
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (17).JPG

TOP CANDIDATES
1. 83_v33         0.9647
2. 79_v33         0.8640
3. 81_v33         0.8544
4. 78_v33         0.8516
5. 80_v33         0.7934

## 22 (18).JPG

MATCH        83_v33
SCORE        0.9577
SECOND       0.8650
MARGIN       0.0927
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (18).JPG

TOP CANDIDATES
1. 83_v33         0.9577
2. 81_v33         0.8650
3. 78_v33         0.8629
4. 79_v33         0.8539
5. 80_v33         0.8046

## 22 (19).JPG

MATCH        83_v33
SCORE        0.9545
SECOND       0.8592
MARGIN       0.0953
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (19).JPG

TOP CANDIDATES
1. 83_v33         0.9545
2. 78_v33         0.8592
3. 81_v33         0.8553
4. 79_v33         0.8552
5. 82_v33         0.7795

## 22 (2).JPG

MATCH        83_v33
SCORE        0.9509
SECOND       0.8613
MARGIN       0.0896
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (2).JPG

TOP CANDIDATES
1. 83_v33         0.9509
2. 78_v33         0.8613
3. 81_v33         0.8371
4. 79_v33         0.8332
5. 82_v33         0.7965

## 22 (20).JPG

MATCH        83_v33
SCORE        0.9625
SECOND       0.8702
MARGIN       0.0923
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (20).JPG

TOP CANDIDATES
1. 83_v33         0.9625
2. 81_v33         0.8702
3. 78_v33         0.8694
4. 79_v33         0.8506
5. 80_v33         0.7897

## 22 (21).JPG

MATCH        83_v33
SCORE        0.9705
SECOND       0.8769
MARGIN       0.0936
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (21).JPG

TOP CANDIDATES
1. 83_v33         0.9705
2. 78_v33         0.8769
3. 79_v33         0.8582
4. 81_v33         0.8557
5. 80_v33         0.7802

## 22 (22).JPG

MATCH        83_v33
SCORE        0.9430
SECOND       0.8369
MARGIN       0.1061
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (22).JPG

TOP CANDIDATES
1. 83_v33         0.9430
2. 78_v33         0.8369
3. 79_v33         0.8329
4. 81_v33         0.8180
5. 82_v33         0.7588

## 22 (23).JPG

MATCH        83_v33
SCORE        0.9722
SECOND       0.8760
MARGIN       0.0962
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (23).JPG

TOP CANDIDATES
1. 83_v33         0.9722
2. 79_v33         0.8760
3. 78_v33         0.8696
4. 81_v33         0.8673
5. 82_v33         0.8232

## 22 (24).JPG

MATCH        83_v33
SCORE        0.9490
SECOND       0.8453
MARGIN       0.1037
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (24).JPG

TOP CANDIDATES
1. 83_v33         0.9490
2. 78_v33         0.8453
3. 79_v33         0.8395
4. 81_v33         0.8216
5. 80_v33         0.7702

## 22 (25).JPG

MATCH        83_v33
SCORE        0.9626
SECOND       0.8789
MARGIN       0.0837
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (25).JPG

TOP CANDIDATES
1. 83_v33         0.9626
2. 78_v33         0.8789
3. 79_v33         0.8510
4. 81_v33         0.8373
5. 82_v33         0.7897

## 22 (26).JPG

MATCH        83_v33
SCORE        0.9466
SECOND       0.8655
MARGIN       0.0811
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (26).JPG

TOP CANDIDATES
1. 83_v33         0.9466
2. 81_v33         0.8655
3. 78_v33         0.8608
4. 79_v33         0.8511
5. 80_v33         0.8387

## 22 (27).JPG

MATCH        83_v33
SCORE        0.9584
SECOND       0.8658
MARGIN       0.0926
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (27).JPG

TOP CANDIDATES
1. 83_v33         0.9584
2. 78_v33         0.8658
3. 79_v33         0.8574
4. 81_v33         0.8494
5. 80_v33         0.8064

## 22 (28).JPG

MATCH        83_v33
SCORE        0.9633
SECOND       0.8813
MARGIN       0.0819
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (28).JPG

TOP CANDIDATES
1. 83_v33         0.9633
2. 78_v33         0.8813
3. 79_v33         0.8681
4. 81_v33         0.8467
5. 80_v33         0.8015

## 22 (29).JPG

MATCH        83_v33
SCORE        0.9519
SECOND       0.8636
MARGIN       0.0883
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (29).JPG

TOP CANDIDATES
1. 83_v33         0.9519
2. 81_v33         0.8636
3. 78_v33         0.8627
4. 79_v33         0.8525
5. 82_v33         0.8051

## 22 (3).JPG

MATCH        83_v33
SCORE        0.9744
SECOND       0.8787
MARGIN       0.0957
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (3).JPG

TOP CANDIDATES
1. 83_v33         0.9744
2. 78_v33         0.8787
3. 79_v33         0.8784
4. 81_v33         0.8748
5. 82_v33         0.8244

## 22 (30).JPG

MATCH        83_v33
SCORE        0.9611
SECOND       0.8682
MARGIN       0.0929
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (30).JPG

TOP CANDIDATES
1. 83_v33         0.9611
2. 78_v33         0.8682
3. 79_v33         0.8563
4. 81_v33         0.8295
5. 80_v33         0.7960

## 22 (31).JPG

MATCH        83_v33
SCORE        0.9635
SECOND       0.8679
MARGIN       0.0956
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (31).JPG

TOP CANDIDATES
1. 83_v33         0.9635
2. 78_v33         0.8679
3. 79_v33         0.8553
4. 81_v33         0.8424
5. 80_v33         0.7888

## 22 (32).JPG

MATCH        83_v33
SCORE        0.9701
SECOND       0.8653
MARGIN       0.1049
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (32).JPG

TOP CANDIDATES
1. 83_v33         0.9701
2. 78_v33         0.8653
3. 79_v33         0.8564
4. 81_v33         0.8394
5. 80_v33         0.7811

## 22 (33).JPG

MATCH        83_v33
SCORE        0.9261
SECOND       0.8318
MARGIN       0.0943
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (33).JPG

TOP CANDIDATES
1. 83_v33         0.9261
2. 78_v33         0.8318
3. 81_v33         0.8226
4. 79_v33         0.8114
5. 82_v33         0.7790

## 22 (34).JPG

MATCH        83_v33
SCORE        0.9457
SECOND       0.8261
MARGIN       0.1197
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (34).JPG

TOP CANDIDATES
1. 83_v33         0.9457
2. 78_v33         0.8261
3. 79_v33         0.8161
4. 81_v33         0.8095
5. 80_v33         0.7509

## 22 (35).JPG

MATCH        83_v33
SCORE        0.9636
SECOND       0.8528
MARGIN       0.1107
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (35).JPG

TOP CANDIDATES
1. 83_v33         0.9636
2. 78_v33         0.8528
3. 79_v33         0.8476
4. 81_v33         0.8365
5. 80_v33         0.7858

## 22 (36).JPG

MATCH        83_v33
SCORE        0.9571
SECOND       0.8624
MARGIN       0.0947
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (36).JPG

TOP CANDIDATES
1. 83_v33         0.9571
2. 78_v33         0.8624
3. 81_v33         0.8617
4. 79_v33         0.8491
5. 82_v33         0.7968

## 22 (37).JPG

MATCH        83_v33
SCORE        0.9612
SECOND       0.8609
MARGIN       0.1004
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (37).JPG

TOP CANDIDATES
1. 83_v33         0.9612
2. 79_v33         0.8609
3. 78_v33         0.8533
4. 81_v33         0.8364
5. 80_v33         0.7856

## 22 (38).JPG

MATCH        83_v33
SCORE        0.9647
SECOND       0.8617
MARGIN       0.1030
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (38).JPG

TOP CANDIDATES
1. 83_v33         0.9647
2. 79_v33         0.8617
3. 78_v33         0.8540
4. 81_v33         0.8405
5. 80_v33         0.7886

## 22 (39).JPG

MATCH        83_v33
SCORE        0.9453
SECOND       0.8707
MARGIN       0.0746
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (39).JPG

TOP CANDIDATES
1. 83_v33         0.9453
2. 78_v33         0.8707
3. 81_v33         0.8610
4. 79_v33         0.8483
5. 82_v33         0.8077

## 22 (4).JPG

MATCH        83_v33
SCORE        0.9646
SECOND       0.8679
MARGIN       0.0967
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (4).JPG

TOP CANDIDATES
1. 83_v33         0.9646
2. 79_v33         0.8679
3. 81_v33         0.8673
4. 78_v33         0.8637
5. 82_v33         0.8162

## 22 (40).JPG

MATCH        83_v33
SCORE        0.9561
SECOND       0.8613
MARGIN       0.0948
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (40).JPG

TOP CANDIDATES
1. 83_v33         0.9561
2. 78_v33         0.8613
3. 79_v33         0.8550
4. 81_v33         0.8508
5. 80_v33         0.7952

## 22 (41).JPG

MATCH        83_v33
SCORE        0.9575
SECOND       0.8677
MARGIN       0.0898
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (41).JPG

TOP CANDIDATES
1. 83_v33         0.9575
2. 78_v33         0.8677
3. 79_v33         0.8327
4. 81_v33         0.8230
5. 82_v33         0.7816

## 22 (42).JPG

MATCH        83_v33
SCORE        0.9578
SECOND       0.8733
MARGIN       0.0845
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (42).JPG

TOP CANDIDATES
1. 83_v33         0.9578
2. 78_v33         0.8733
3. 81_v33         0.8627
4. 79_v33         0.8529
5. 80_v33         0.8026

## 22 (43).JPG

MATCH        83_v33
SCORE        0.9587
SECOND       0.8535
MARGIN       0.1053
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (43).JPG

TOP CANDIDATES
1. 83_v33         0.9587
2. 79_v33         0.8535
3. 81_v33         0.8515
4. 78_v33         0.8482
5. 82_v33         0.7804

## 22 (44).JPG

MATCH        83_v33
SCORE        0.9523
SECOND       0.8727
MARGIN       0.0795
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (44).JPG

TOP CANDIDATES
1. 83_v33         0.9523
2. 81_v33         0.8727
3. 79_v33         0.8552
4. 78_v33         0.8325
5. 82_v33         0.7904

## 22 (45).JPG

MATCH        83_v33
SCORE        0.9664
SECOND       0.8820
MARGIN       0.0844
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (45).JPG

TOP CANDIDATES
1. 83_v33         0.9664
2. 79_v33         0.8820
3. 78_v33         0.8781
4. 81_v33         0.8653
5. 82_v33         0.8057

## 22 (46).JPG

MATCH        83_v33
SCORE        0.9468
SECOND       0.8747
MARGIN       0.0721
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (46).JPG

TOP CANDIDATES
1. 83_v33         0.9468
2. 81_v33         0.8747
3. 79_v33         0.8559
4. 78_v33         0.8293
5. 82_v33         0.7998

## 22 (47).JPG

MATCH        83_v33
SCORE        0.9735
SECOND       0.8832
MARGIN       0.0903
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (47).JPG

TOP CANDIDATES
1. 83_v33         0.9735
2. 78_v33         0.8832
3. 79_v33         0.8734
4. 81_v33         0.8669
5. 82_v33         0.8001

## 22 (48).JPG

MATCH        83_v33
SCORE        0.9606
SECOND       0.8753
MARGIN       0.0853
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (48).JPG

TOP CANDIDATES
1. 83_v33         0.9606
2. 79_v33         0.8753
3. 81_v33         0.8727
4. 78_v33         0.8679
5. 80_v33         0.7982

## 22 (49).JPG

MATCH        83_v33
SCORE        0.9675
SECOND       0.8684
MARGIN       0.0991
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (49).JPG

TOP CANDIDATES
1. 83_v33         0.9675
2. 79_v33         0.8684
3. 78_v33         0.8639
4. 81_v33         0.8607
5. 82_v33         0.7921

## 22 (5).JPG

MATCH        83_v33
SCORE        0.9685
SECOND       0.8890
MARGIN       0.0795
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (5).JPG

TOP CANDIDATES
1. 83_v33         0.9685
2. 78_v33         0.8890
3. 79_v33         0.8781
4. 81_v33         0.8707
5. 82_v33         0.8318

## 22 (50).JPG

MATCH        83_v33
SCORE        0.9765
SECOND       0.8812
MARGIN       0.0953
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (50).JPG

TOP CANDIDATES
1. 83_v33         0.9765
2. 78_v33         0.8812
3. 79_v33         0.8779
4. 81_v33         0.8608
5. 82_v33         0.8090

## 22 (51).JPG

MATCH        83_v33
SCORE        0.9340
SECOND       0.8585
MARGIN       0.0755
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (51).JPG

TOP CANDIDATES
1. 83_v33         0.9340
2. 78_v33         0.8585
3. 79_v33         0.8327
4. 81_v33         0.8256
5. 82_v33         0.7894

## 22 (6).JPG

MATCH        83_v33
SCORE        0.9534
SECOND       0.8788
MARGIN       0.0746
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (6).JPG

TOP CANDIDATES
1. 83_v33         0.9534
2. 81_v33         0.8788
3. 78_v33         0.8671
4. 79_v33         0.8603
5. 80_v33         0.8166

## 22 (7).JPG

MATCH        83_v33
SCORE        0.9700
SECOND       0.8768
MARGIN       0.0932
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (7).JPG

TOP CANDIDATES
1. 83_v33         0.9700
2. 81_v33         0.8768
3. 79_v33         0.8734
4. 78_v33         0.8600
5. 82_v33         0.8137

## 22 (8).JPG

MATCH        83_v33
SCORE        0.9608
SECOND       0.8756
MARGIN       0.0852
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (8).JPG

TOP CANDIDATES
1. 83_v33         0.9608
2. 78_v33         0.8756
3. 81_v33         0.8575
4. 79_v33         0.8469
5. 82_v33         0.8097

## 22 (9).JPG

MATCH        83_v33
SCORE        0.9759
SECOND       0.8791
MARGIN       0.0968
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (9).JPG

TOP CANDIDATES
1. 83_v33         0.9759
2. 78_v33         0.8791
3. 79_v33         0.8672
4. 81_v33         0.8667
5. 82_v33         0.8184

## 33 (1).JPG

MATCH        83_v33
SCORE        0.9629
SECOND       0.8814
MARGIN       0.0815
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (1).JPG

TOP CANDIDATES
1. 83_v33         0.9629
2. 78_v33         0.8814
3. 79_v33         0.8698
4. 81_v33         0.8543
5. 80_v33         0.8176

## 33 (10).JPG

MATCH        83_v33
SCORE        0.9653
SECOND       0.8728
MARGIN       0.0925
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (10).JPG

TOP CANDIDATES
1. 83_v33         0.9653
2. 79_v33         0.8728
3. 78_v33         0.8590
4. 81_v33         0.8455
5. 80_v33         0.7981

## 33 (11).JPG

MATCH        83_v33
SCORE        0.9595
SECOND       0.8838
MARGIN       0.0757
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (11).JPG

TOP CANDIDATES
1. 83_v33         0.9595
2. 79_v33         0.8838
3. 78_v33         0.8835
4. 81_v33         0.8613
5. 80_v33         0.8153

## 33 (12).JPG

MATCH        83_v33
SCORE        0.9586
SECOND       0.8850
MARGIN       0.0736
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (12).JPG

TOP CANDIDATES
1. 83_v33         0.9586
2. 78_v33         0.8850
3. 79_v33         0.8766
4. 81_v33         0.8535
5. 80_v33         0.8288

## 33 (13).JPG

MATCH        83_v33
SCORE        0.9228
SECOND       0.8469
MARGIN       0.0759
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (13).JPG

TOP CANDIDATES
1. 83_v33         0.9228
2. 78_v33         0.8469
3. 79_v33         0.8234
4. 81_v33         0.7957
5. 82_v33         0.7504

## 33 (2).JPG

MATCH        83_v33
SCORE        0.8307
SECOND       0.7680
MARGIN       0.0627
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   33 (2).JPG

TOP CANDIDATES
1. 83_v33         0.8307
2. 78_v33         0.7680
3. 79_v33         0.7669
4. 80_v33         0.7494
5. 81_v33         0.7318

## 33 (3).JPG

MATCH        83_v33
SCORE        0.9308
SECOND       0.8545
MARGIN       0.0763
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (3).JPG

TOP CANDIDATES
1. 83_v33         0.9308
2. 79_v33         0.8545
3. 78_v33         0.8297
4. 81_v33         0.8112
5. 80_v33         0.7978

## 33 (4).JPG

MATCH        83_v33
SCORE        0.9644
SECOND       0.8724
MARGIN       0.0921
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (4).JPG

TOP CANDIDATES
1. 83_v33         0.9644
2. 79_v33         0.8724
3. 78_v33         0.8689
4. 81_v33         0.8608
5. 80_v33         0.8173

## 33 (5).JPG

MATCH        83_v33
SCORE        0.9533
SECOND       0.8870
MARGIN       0.0663
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (5).JPG

TOP CANDIDATES
1. 83_v33         0.9533
2. 78_v33         0.8870
3. 79_v33         0.8592
4. 81_v33         0.8351
5. 80_v33         0.8022

## 33 (6).JPG

MATCH        83_v33
SCORE        0.8347
SECOND       0.7794
MARGIN       0.0553
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   33 (6).JPG

TOP CANDIDATES
1. 83_v33         0.8347
2. 78_v33         0.7794
3. 79_v33         0.7363
4. 81_v33         0.7134
5. 82_v33         0.6883

## 33 (7).JPG

MATCH        83_v33
SCORE        0.9117
SECOND       0.8340
MARGIN       0.0777
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (7).JPG

TOP CANDIDATES
1. 83_v33         0.9117
2. 79_v33         0.8340
3. 78_v33         0.8326
4. 81_v33         0.7962
5. 80_v33         0.7737

## 33 (8).JPG

MATCH        83_v33
SCORE        0.9610
SECOND       0.8734
MARGIN       0.0876
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (8).JPG

TOP CANDIDATES
1. 83_v33         0.9610
2. 79_v33         0.8734
3. 78_v33         0.8671
4. 81_v33         0.8495
5. 80_v33         0.8044

## 33 (9).JPG

MATCH        83_v33
SCORE        0.9221
SECOND       0.8145
MARGIN       0.1076
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (9).JPG

TOP CANDIDATES
1. 83_v33         0.9221
2. 78_v33         0.8145
3. 79_v33         0.8127
4. 81_v33         0.7958
5. 82_v33         0.7412

## Нагибина 24 А (11).JPG

MATCH        83_v33
SCORE        0.9529
SECOND       0.8379
MARGIN       0.1150
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   Нагибина 24 А (11).JPG

TOP CANDIDATES
1. 83_v33         0.9529
2. 78_v33         0.8379
3. 79_v33         0.8306
4. 81_v33         0.8109
5. 80_v33         0.7610

## Нагибина 24 А (23).JPG

MATCH        83_v33
SCORE        0.9535
SECOND       0.8449
MARGIN       0.1086
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   Нагибина 24 А (23).JPG

TOP CANDIDATES
1. 83_v33         0.9535
2. 78_v33         0.8449
3. 79_v33         0.8373
4. 81_v33         0.8215
5. 80_v33         0.7799

## Нагибина 24 А (4).JPG

MATCH        83_v33
SCORE        0.9652
SECOND       0.8754
MARGIN       0.0898
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   Нагибина 24 А (4).JPG

TOP CANDIDATES
1. 83_v33         0.9652
2. 78_v33         0.8754
3. 81_v33         0.8614
4. 79_v33         0.8429
5. 80_v33         0.7954

## Нагибина 24 А (49).JPG

MATCH        83_v33
SCORE        0.9553
SECOND       0.8776
MARGIN       0.0777
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   Нагибина 24 А (49).JPG

TOP CANDIDATES
1. 83_v33         0.9553
2. 78_v33         0.8776
3. 81_v33         0.8645
4. 79_v33         0.8463
5. 80_v33         0.8009
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-13 21:31:15

Отлично. **Сейчас система работает корректно**, и результат `83_v33` выглядит очень убедительно.

### Что мы подтвердили

- DINOv2 `facebook/dinov2-base` загружается нормально.
- RTX 3060 используется через CUDA.
- Размер embedding: **768**.
- Fingerprint `83_v33` создан из **68 изображений**.
- Compact v3.3 работает:
  - global — 768
  - environment — 640
  - color — 48
  - spatial — 32
  - patch storage отключён.
- Распознавание сравнивает `83_v33` с существующими `78_v33 ... 83_v33`.

### Самое важное

Все **68/68 изображений** из папки `83` определились как `83_v33`.

Причём:

- практически все имеют score **0.92–0.98**
- даже самые слабые:
  - `33 (2).JPG` → **0.8307**
  - `33 (6).JPG` → **0.8347**
- остальные значительно выше.
- `83_v33` каждый раз занимает **1-е место**.
- Даже у слабых совпадений второй кандидат заметно ниже.

То есть на этом наборе:

> **100% изображений правильно классифицированы как fingerprint 83_v33.**

### Но есть важный нюанс

Это пока **не является полноценным тестом независимого распознавания**.

Мы дали системе:

```text
data/input/83
```

а fingerprint:

```text
83_v33
```

был **непосредственно построен из этих же 68 изображений**.

Поэтому результат:

```text
BEST IMAGE 22 (1).JPG
```

для изображения `22 (1).JPG` — ожидаемый результат. Система фактически узнаёт собственное изображение/собственный набор.

Именно поэтому сейчас нельзя делать вывод:

> «83_v33 умеет распознавать новые фотографии этой сцены с 97% точностью».

Пока мы доказали только, что **fingerprint корректно создан и способен воспроизводить исходный набор**.

---

## Следующий тест я бы сделал именно такой

Нужен **independent test**.

Например:

```text
data/input/
├── 78/
├── 79/
├── 80/
├── 81/
├── 82/
├── 83/
└── TEST/
```

В `TEST` кладём фотографии, **которых не было при создании fingerprint'ов**.

Например, 10–20 новых фотографий той же сцены/объекта 83.

Запускаем:

```bash
uv run scene-fingerprint recognize \
    data/input/TEST \
    --top-k 6 \
    --threshold 0.50
```

И смотрим уже не на `self-match`, а на:

```text
TEST_01.jpg
MATCH        83_v33
SCORE        0.78
SECOND       78_v33
MARGIN       0.21
```

Вот это уже будет **настоящий тест Scene Fingerprint**.

---

### И ещё один очень важный тест

У нас сейчас:

```text
global       0.70
environment  0.20
color        0.07
spatial      0.03
```

И я бы **пока не менял эти веса**.

Сначала нужно получить baseline на независимых изображениях.

После этого мы сможем проверить:

1. насколько хорошо работает `global`;
2. помогает ли `environment`;
3. не мешает ли `color`;
4. насколько полезен `spatial`;
5. где проходит реальный порог `CONFIDENT / PROBABLE / UNKNOWN`;
6. насколько сильно похожие сцены `78–82` путаются с `83`.

### Сейчас проект находится в очень хорошем состоянии

Особенно важно, что мы наконец устранили проблему с Hugging Face:

```text
HF_ENDPOINT=https://hf-mirror.com
```

был причиной первоначальной проблемы. После отключения:

```text
HF ENDPOINT: https://huggingface.co
```

DINOv2 нормально загрузился и заработал.

**Я бы сейчас ничего в коде не менял.** Следующий шаг — именно независимый тест, чтобы не испортить рабочую v3.3.

Если у тебя есть **новые фотографии для 83**, которые не входили в эти 68, давай прогоняем их — это будет гораздо более показательный тест.

---

### 👤 **User** — 2026-08-13 22:04:54

[Recognizer] Fingerprints: 78_v33, 79_v33, 80_v33, 81_v33, 82_v33, 83_v33

## 00 (1).JPG

MATCH        78_v33
SCORE        0.9475
SECOND       0.8808
MARGIN       0.0667
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo040.JPG

TOP CANDIDATES
1. 78_v33         0.9475
2. 83_v33         0.8808
3. 79_v33         0.8522
4. 81_v33         0.8403
5. 82_v33         0.8302
6. 80_v33         0.8167

## 00 (10).JPG

MATCH        78_v33
SCORE        0.9384
SECOND       0.8669
MARGIN       0.0715
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo042.JPG

TOP CANDIDATES
1. 78_v33         0.9384
2. 83_v33         0.8669
3. 79_v33         0.8652
4. 82_v33         0.8636
5. 80_v33         0.8490
6. 81_v33         0.8234

## 00 (11).JPG

MATCH        78_v33
SCORE        0.9336
SECOND       0.8818
MARGIN       0.0519
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo044.JPG

TOP CANDIDATES
1. 78_v33         0.9336
2. 83_v33         0.8818
3. 79_v33         0.8590
4. 82_v33         0.8476
5. 80_v33         0.8355
6. 81_v33         0.8354

## 00 (12).JPG

MATCH        78_v33
SCORE        0.9301
SECOND       0.8894
MARGIN       0.0406
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo040.JPG

TOP CANDIDATES
1. 78_v33         0.9301
2. 83_v33         0.8894
3. 79_v33         0.8562
4. 81_v33         0.8326
5. 82_v33         0.8278
6. 80_v33         0.8224

## 00 (2).JPG

MATCH        78_v33
SCORE        0.9375
SECOND       0.8818
MARGIN       0.0556
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo010.JPG

TOP CANDIDATES
1. 78_v33         0.9375
2. 83_v33         0.8818
3. 79_v33         0.8445
4. 82_v33         0.8166
5. 81_v33         0.8157
6. 80_v33         0.8031

## 00 (3).JPG

MATCH        78_v33
SCORE        0.9057
SECOND       0.8427
MARGIN       0.0629
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo012.JPG

TOP CANDIDATES
1. 78_v33         0.9057
2. 83_v33         0.8427
3. 82_v33         0.8207
4. 79_v33         0.8117
5. 80_v33         0.7841
6. 81_v33         0.7790

## 00 (4).JPG

MATCH        78_v33
SCORE        0.9513
SECOND       0.8834
MARGIN       0.0679
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo043.JPG

TOP CANDIDATES
1. 78_v33         0.9513
2. 83_v33         0.8834
3. 79_v33         0.8543
4. 82_v33         0.8258
5. 81_v33         0.8251
6. 80_v33         0.8212

## 00 (5).JPG

MATCH        78_v33
SCORE        0.9300
SECOND       0.8736
MARGIN       0.0564
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo042.JPG

TOP CANDIDATES
1. 78_v33         0.9300
2. 83_v33         0.8736
3. 79_v33         0.8566
4. 81_v33         0.8177
5. 80_v33         0.8168
6. 82_v33         0.8161

## 00 (6).JPG

MATCH        78_v33
SCORE        0.9470
SECOND       0.8847
MARGIN       0.0623
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo040.JPG

TOP CANDIDATES
1. 78_v33         0.9470
2. 83_v33         0.8847
3. 79_v33         0.8606
4. 82_v33         0.8371
5. 81_v33         0.8367
6. 80_v33         0.8251

## 00 (7).JPG

MATCH        78_v33
SCORE        0.9341
SECOND       0.8733
MARGIN       0.0608
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo042.JPG

TOP CANDIDATES
1. 78_v33         0.9341
2. 83_v33         0.8733
3. 79_v33         0.8682
4. 82_v33         0.8517
5. 81_v33         0.8416
6. 80_v33         0.8365

## 00 (8).JPG

MATCH        79_v33
SCORE        0.9177
SECOND       0.8583
MARGIN       0.0594
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   00 (46).JPG

TOP CANDIDATES
1. 79_v33         0.9177
2. 83_v33         0.8583
3. 78_v33         0.8383
4. 81_v33         0.8180
5. 80_v33         0.7975
6. 82_v33         0.7770

## 00 (9).JPG

MATCH        78_v33
SCORE        0.9364
SECOND       0.8713
MARGIN       0.0651
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo042.JPG

TOP CANDIDATES
1. 78_v33         0.9364
2. 83_v33         0.8713
3. 82_v33         0.8704
4. 79_v33         0.8599
5. 80_v33         0.8401
6. 81_v33         0.8155

## 1 Конной Армии 32 А (1).JPG

MATCH        81_v33
SCORE        0.9250
SECOND       0.8347
MARGIN       0.0904
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   36.JPG

TOP CANDIDATES
1. 81_v33         0.9250
2. 83_v33         0.8347
3. 79_v33         0.8324
4. 78_v33         0.8254
5. 82_v33         0.8068
6. 80_v33         0.7942

## 1 Конной Армии 32 А (10).JPG

MATCH        81_v33
SCORE        0.9359
SECOND       0.8425
MARGIN       0.0933
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   23.JPG

TOP CANDIDATES
1. 81_v33         0.9359
2. 83_v33         0.8425
3. 79_v33         0.8142
4. 78_v33         0.7848
5. 80_v33         0.7776
6. 82_v33         0.7711

## 1 Конной Армии 32 А (11).JPG

MATCH        81_v33
SCORE        0.9321
SECOND       0.8582
MARGIN       0.0740
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   23.JPG

TOP CANDIDATES
1. 81_v33         0.9321
2. 83_v33         0.8582
3. 79_v33         0.8309
4. 78_v33         0.8188
5. 80_v33         0.7962
6. 82_v33         0.7930

## 1 Конной Армии 32 А (12).JPG

MATCH        81_v33
SCORE        0.9312
SECOND       0.8526
MARGIN       0.0786
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   29.JPG

TOP CANDIDATES
1. 81_v33         0.9312
2. 83_v33         0.8526
3. 79_v33         0.8242
4. 80_v33         0.7930
5. 78_v33         0.7925
6. 82_v33         0.7745

## 1 Конной Армии 32 А (35).JPG

MATCH        81_v33
SCORE        0.9198
SECOND       0.8193
MARGIN       0.1005
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   26.JPG

TOP CANDIDATES
1. 81_v33         0.9198
2. 80_v33         0.8193
3. 82_v33         0.8184
4. 79_v33         0.8182
5. 83_v33         0.8159
6. 78_v33         0.8086

## 1 Конной Армии 32 А (36).JPG

MATCH        81_v33
SCORE        0.9220
SECOND       0.8717
MARGIN       0.0504
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   38.JPG

TOP CANDIDATES
1. 81_v33         0.9220
2. 83_v33         0.8717
3. 79_v33         0.8706
4. 78_v33         0.8693
5. 82_v33         0.8327
6. 80_v33         0.8171

## 1 Конной Армии 32 А (37).JPG

MATCH        81_v33
SCORE        0.8811
SECOND       0.8299
MARGIN       0.0511
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   38.JPG

TOP CANDIDATES
1. 81_v33         0.8811
2. 79_v33         0.8299
3. 78_v33         0.8285
4. 83_v33         0.8252
5. 80_v33         0.8113
6. 82_v33         0.8042

## 1 Конной Армии 32 А (38).JPG

MATCH        81_v33
SCORE        0.8874
SECOND       0.8583
MARGIN       0.0291
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   38.JPG

TOP CANDIDATES
1. 81_v33         0.8874
2. 79_v33         0.8583
3. 78_v33         0.8569
4. 82_v33         0.8474
5. 83_v33         0.8421
6. 80_v33         0.8143

## 1 Конной Армии 32 А (39).JPG

MATCH        81_v33
SCORE        0.9328
SECOND       0.8541
MARGIN       0.0787
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   36.JPG

TOP CANDIDATES
1. 81_v33         0.9328
2. 79_v33         0.8541
3. 83_v33         0.8508
4. 78_v33         0.8369
5. 82_v33         0.8338
6. 80_v33         0.8174

## 1 Конной Армии 32 А (6).JPG

MATCH        81_v33
SCORE        0.9389
SECOND       0.8492
MARGIN       0.0897
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   23.JPG

TOP CANDIDATES
1. 81_v33         0.9389
2. 83_v33         0.8492
3. 79_v33         0.8314
4. 80_v33         0.8011
5. 82_v33         0.7990
6. 78_v33         0.7975

## 1 Конной Армии 32 А (7).JPG

MATCH        81_v33
SCORE        0.9358
SECOND       0.8435
MARGIN       0.0923
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   18.JPG

TOP CANDIDATES
1. 81_v33         0.9358
2. 83_v33         0.8435
3. 79_v33         0.8236
4. 78_v33         0.7835
5. 82_v33         0.7816
6. 80_v33         0.7757

## 1 Конной Армии 32 А (8).JPG

MATCH        81_v33
SCORE        0.9306
SECOND       0.8594
MARGIN       0.0712
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   23.JPG

TOP CANDIDATES
1. 81_v33         0.9306
2. 83_v33         0.8594
3. 79_v33         0.8444
4. 82_v33         0.8278
5. 78_v33         0.8202
6. 80_v33         0.8099

## 1 Конной Армии 32 А (9).JPG

MATCH        81_v33
SCORE        0.9354
SECOND       0.8482
MARGIN       0.0872
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   23.JPG

TOP CANDIDATES
1. 81_v33         0.9354
2. 83_v33         0.8482
3. 79_v33         0.8227
4. 82_v33         0.7875
5. 78_v33         0.7846
6. 80_v33         0.7730

## 1 Конной Армии А (16).JPG

MATCH        81_v33
SCORE        0.9003
SECOND       0.7850
MARGIN       0.1153
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   41.JPG

TOP CANDIDATES
1. 81_v33         0.9003
2. 79_v33         0.7850
3. 83_v33         0.7816
4. 78_v33         0.7535
5. 82_v33         0.7384
6. 80_v33         0.7370

## 1 Конной Армии А (17).JPG

MATCH        81_v33
SCORE        0.8994
SECOND       0.7838
MARGIN       0.1156
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   64.JPG

TOP CANDIDATES
1. 81_v33         0.8994
2. 79_v33         0.7838
3. 83_v33         0.7799
4. 78_v33         0.7420
5. 80_v33         0.7393
6. 82_v33         0.7315

## 1 Конной Армии А (18).JPG

MATCH        81_v33
SCORE        0.8889
SECOND       0.7652
MARGIN       0.1237
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   64.JPG

TOP CANDIDATES
1. 81_v33         0.8889
2. 79_v33         0.7652
3. 83_v33         0.7651
4. 78_v33         0.7330
5. 80_v33         0.7193
6. 82_v33         0.7124

## Добровольского 17 А (34).JPG

MATCH        82_v33
SCORE        0.8977
SECOND       0.7966
MARGIN       0.1012
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   52.JPG

TOP CANDIDATES
1. 82_v33         0.8977
2. 78_v33         0.7966
3. 80_v33         0.7651
4. 81_v33         0.7634
5. 79_v33         0.7602
6. 83_v33         0.7533

## Добровольского 17 А (35).JPG

MATCH        82_v33
SCORE        0.9520
SECOND       0.8273
MARGIN       0.1246
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   57.JPG

TOP CANDIDATES
1. 82_v33         0.9520
2. 80_v33         0.8273
3. 79_v33         0.8147
4. 78_v33         0.8139
5. 81_v33         0.8055
6. 83_v33         0.7716

## Добровольского 17 А (36).JPG

MATCH        82_v33
SCORE        0.9509
SECOND       0.8251
MARGIN       0.1258
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   55.JPG

TOP CANDIDATES
1. 82_v33         0.9509
2. 80_v33         0.8251
3. 78_v33         0.8059
4. 79_v33         0.7973
5. 81_v33         0.7951
6. 83_v33         0.7560

## Добровольского 17 А (37).JPG

MATCH        82_v33
SCORE        0.9571
SECOND       0.8362
MARGIN       0.1210
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   55.JPG

TOP CANDIDATES
1. 82_v33         0.9571
2. 80_v33         0.8362
3. 78_v33         0.8180
4. 79_v33         0.8117
5. 81_v33         0.8073
6. 83_v33         0.7699

## Добровольского 17 А (38).JPG

MATCH        82_v33
SCORE        0.9460
SECOND       0.8116
MARGIN       0.1344
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   57.JPG

TOP CANDIDATES
1. 82_v33         0.9460
2. 80_v33         0.8116
3. 78_v33         0.7968
4. 79_v33         0.7893
5. 81_v33         0.7800
6. 83_v33         0.7401

## Добровольского 17 А (59).JPG

MATCH        82_v33
SCORE        0.9467
SECOND       0.8128
MARGIN       0.1339
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   53.JPG

TOP CANDIDATES
1. 82_v33         0.9467
2. 80_v33         0.8128
3. 78_v33         0.7953
4. 81_v33         0.7859
5. 79_v33         0.7783
6. 83_v33         0.7444

## Добровольского 17 А (60).JPG

MATCH        82_v33
SCORE        0.9569
SECOND       0.8259
MARGIN       0.1311
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   54.JPG

TOP CANDIDATES
1. 82_v33         0.9569
2. 80_v33         0.8259
3. 78_v33         0.8045
4. 81_v33         0.8005
5. 79_v33         0.7864
6. 83_v33         0.7627

## Добровольского 17 А (61).JPG

MATCH        82_v33
SCORE        0.9531
SECOND       0.8152
MARGIN       0.1378
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   55.JPG

TOP CANDIDATES
1. 82_v33         0.9531
2. 80_v33         0.8152
3. 78_v33         0.7848
4. 81_v33         0.7737
5. 79_v33         0.7662
6. 83_v33         0.7312

## Добровольского 17 А (63).JPG

MATCH        82_v33
SCORE        0.9514
SECOND       0.8133
MARGIN       0.1381
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   57.JPG

TOP CANDIDATES
1. 82_v33         0.9514
2. 80_v33         0.8133
3. 78_v33         0.7933
4. 81_v33         0.7813
5. 79_v33         0.7710
6. 83_v33         0.7367

## Комарова 20 Добровольского Б (4).JPG

MATCH        79_v33
SCORE        0.6004
SECOND       0.5539
MARGIN       0.0464
CONFIDENCE   NO_MATCH
STATUS       NO_MATCH
BEST IMAGE   00 (65).JPG

TOP CANDIDATES
1. 79_v33         0.6004
2. 83_v33         0.5539
3. 82_v33         0.5501
4. 78_v33         0.5376
5. 81_v33         0.5308
6. 80_v33         0.5216

## Комарова 20 Добровольского Б (5).JPG

MATCH        79_v33
SCORE        0.9485
SECOND       0.8578
MARGIN       0.0907
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   00 (46).JPG

TOP CANDIDATES
1. 79_v33         0.9485
2. 83_v33         0.8578
3. 81_v33         0.8362
4. 78_v33         0.8345
5. 82_v33         0.8131
6. 80_v33         0.8063

## Комарова 20 Добровольского Б (6).JPG

MATCH        79_v33
SCORE        0.9529
SECOND       0.8507
MARGIN       0.1022
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   00 (44).JPG

TOP CANDIDATES
1. 79_v33         0.9529
2. 83_v33         0.8507
3. 81_v33         0.8353
4. 78_v33         0.8302
5. 82_v33         0.8083
6. 80_v33         0.8020

## Комарова 28 А (1).JPG

MATCH        80_v33
SCORE        0.9069
SECOND       0.8176
MARGIN       0.0893
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   031.JPG

TOP CANDIDATES
1. 80_v33         0.9069
2. 79_v33         0.8176
3. 81_v33         0.8080
4. 83_v33         0.8059
5. 78_v33         0.7944
6. 82_v33         0.7892

## Комарова 28 А (2).JPG

MATCH        80_v33
SCORE        0.9328
SECOND       0.8641
MARGIN       0.0687
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   037.JPG

TOP CANDIDATES
1. 80_v33         0.9328
2. 79_v33         0.8641
3. 82_v33         0.8412
4. 81_v33         0.8376
5. 83_v33         0.8310
6. 78_v33         0.8279

## Комарова 28 А (3).JPG

MATCH        80_v33
SCORE        0.9295
SECOND       0.8366
MARGIN       0.0929
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   005.JPG

TOP CANDIDATES
1. 80_v33         0.9295
2. 82_v33         0.8366
3. 81_v33         0.8136
4. 79_v33         0.8123
5. 78_v33         0.7985
6. 83_v33         0.7776

## Комарова 28 А (4).JPG

MATCH        80_v33
SCORE        0.9295
SECOND       0.8386
MARGIN       0.0910
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   034.JPG

TOP CANDIDATES
1. 80_v33         0.9295
2. 82_v33         0.8386
3. 79_v33         0.8063
4. 81_v33         0.8000
5. 78_v33         0.7878
6. 83_v33         0.7750

## Комарова 28 А (5).JPG

MATCH        80_v33
SCORE        0.9202
SECOND       0.8105
MARGIN       0.1098
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   034.JPG

TOP CANDIDATES
1. 80_v33         0.9202
2. 79_v33         0.8105
3. 83_v33         0.8090
4. 81_v33         0.8088
5. 78_v33         0.8059
6. 82_v33         0.8040

## Комарова 28 А (6).JPG

MATCH        80_v33
SCORE        0.9054
SECOND       0.8451
MARGIN       0.0603
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   003.JPG

TOP CANDIDATES
1. 80_v33         0.9054
2. 79_v33         0.8451
3. 83_v33         0.8358
4. 81_v33         0.8239
5. 78_v33         0.8209
6. 82_v33         0.8141

## Комарова Добровольского А (1).JPG

MATCH        82_v33
SCORE        0.8765
SECOND       0.8754
MARGIN       0.0011
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   11.JPG

TOP CANDIDATES
1. 82_v33         0.8765
2. 79_v33         0.8754
3. 83_v33         0.8735
4. 78_v33         0.8710
5. 81_v33         0.8558
6. 80_v33         0.8509

## Комарова Добровольского А (42).JPG

MATCH        83_v33
SCORE        0.8752
SECOND       0.8751
MARGIN       0.0001
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   22 (6).JPG

TOP CANDIDATES
1. 83_v33         0.8752
2. 79_v33         0.8751
3. 81_v33         0.8747
4. 82_v33         0.8709
5. 78_v33         0.8696
6. 80_v33         0.8495

## Комарова Добровольского А (8).JPG

MATCH        83_v33
SCORE        0.8824
SECOND       0.8702
MARGIN       0.0122
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   22 (3).JPG

TOP CANDIDATES
1. 83_v33         0.8824
2. 78_v33         0.8702
3. 79_v33         0.8629
4. 81_v33         0.8575
5. 82_v33         0.8502
6. 80_v33         0.8344

## Комарова Добровольского Б (17).JPG

MATCH        79_v33
SCORE        0.9450
SECOND       0.8655
MARGIN       0.0795
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   00 (46).JPG

TOP CANDIDATES
1. 79_v33         0.9450
2. 83_v33         0.8655
3. 78_v33         0.8500
4. 81_v33         0.8304
5. 82_v33         0.7943
6. 80_v33         0.7942

## Комарова Добровольского Б (20).JPG

MATCH        79_v33
SCORE        0.9365
SECOND       0.8235
MARGIN       0.1129
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   00 (44).JPG

TOP CANDIDATES
1. 79_v33         0.9365
2. 83_v33         0.8235
3. 78_v33         0.8065
4. 81_v33         0.8054
5. 82_v33         0.7966
6. 80_v33         0.7767

## Комарова Добровольского Б (23).JPG

MATCH        79_v33
SCORE        0.9452
SECOND       0.8513
MARGIN       0.0939
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   00 (44).JPG

TOP CANDIDATES
1. 79_v33         0.9452
2. 83_v33         0.8513
3. 78_v33         0.8460
4. 81_v33         0.8425
5. 82_v33         0.8257
6. 80_v33         0.8106

## Комарова Добровольского Б (5).JPG

MATCH        79_v33
SCORE        0.9484
SECOND       0.8505
MARGIN       0.0978
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   00 (46).JPG

TOP CANDIDATES
1. 79_v33         0.9484
2. 83_v33         0.8505
3. 78_v33         0.8343
4. 81_v33         0.8219
5. 82_v33         0.7836
6. 80_v33         0.7801

## Космонавтов 13 Комарова А (15).JPG

MATCH        78_v33
SCORE        0.9338
SECOND       0.8822
MARGIN       0.0516
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo025.JPG

TOP CANDIDATES
1. 78_v33         0.9338
2. 83_v33         0.8822
3. 79_v33         0.8247
4. 82_v33         0.8147
5. 81_v33         0.8130
6. 80_v33         0.7709

## Космонавтов 13 Комарова А (18).JPG

MATCH        78_v33
SCORE        0.9493
SECOND       0.8727
MARGIN       0.0766
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo079.JPG

TOP CANDIDATES
1. 78_v33         0.9493
2. 83_v33         0.8727
3. 82_v33         0.8497
4. 79_v33         0.8417
5. 81_v33         0.8319
6. 80_v33         0.8293

## Космонавтов 13 Комарова А (3).JPG

MATCH        78_v33
SCORE        0.9431
SECOND       0.8745
MARGIN       0.0686
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo075.JPG

TOP CANDIDATES
1. 78_v33         0.9431
2. 83_v33         0.8745
3. 82_v33         0.8624
4. 79_v33         0.8495
5. 81_v33         0.8266
6. 80_v33         0.8183

## Космонавтов 13 Комарова А (9).JPG

MATCH        78_v33
SCORE        0.9492
SECOND       0.8933
MARGIN       0.0559
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   photo075.JPG

TOP CANDIDATES
1. 78_v33         0.9492
2. 83_v33         0.8933
3. 79_v33         0.8554
4. 82_v33         0.8420
5. 81_v33         0.8314
6. 80_v33         0.8091

## Ленина 125-127 А (1).JPG

MATCH        79_v33
SCORE        0.8453
SECOND       0.8431
MARGIN       0.0023
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   00 (64).JPG

TOP CANDIDATES
1. 79_v33         0.8453
2. 81_v33         0.8431
3. 83_v33         0.8368
4. 78_v33         0.7759
5. 82_v33         0.7640
6. 80_v33         0.7633

## Ленина 125-127 А (10).JPG

MATCH        79_v33
SCORE        0.8814
SECOND       0.8672
MARGIN       0.0142
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   00 (45).JPG

TOP CANDIDATES
1. 79_v33         0.8814
2. 83_v33         0.8672
3. 81_v33         0.8670
4. 78_v33         0.8279
5. 82_v33         0.8097
6. 80_v33         0.7940

## Ленина 125-127 А (11).JPG

MATCH        79_v33
SCORE        0.8804
SECOND       0.8684
MARGIN       0.0120
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   00 (45).JPG

TOP CANDIDATES
1. 79_v33         0.8804
2. 81_v33         0.8684
3. 83_v33         0.8659
4. 78_v33         0.8202
5. 82_v33         0.7967
6. 80_v33         0.7911

## Ленина 125-127 А (12).JPG

MATCH        79_v33
SCORE        0.8672
SECOND       0.8555
MARGIN       0.0118
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   00 (45).JPG

TOP CANDIDATES
1. 79_v33         0.8672
2. 83_v33         0.8555
3. 81_v33         0.8447
4. 78_v33         0.7998
5. 82_v33         0.7778
6. 80_v33         0.7727

## Ленина 125-127 А (13).JPG

MATCH        79_v33
SCORE        0.8826
SECOND       0.8672
MARGIN       0.0154
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   00 (64).JPG

TOP CANDIDATES
1. 79_v33         0.8826
2. 81_v33         0.8672
3. 83_v33         0.8623
4. 78_v33         0.8205
5. 82_v33         0.8044
6. 80_v33         0.7973

## Ленина 125-127 А (14).JPG

MATCH        79_v33
SCORE        0.8721
SECOND       0.8601
MARGIN       0.0119
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   00 (45).JPG

TOP CANDIDATES
1. 79_v33         0.8721
2. 83_v33         0.8601
3. 81_v33         0.8498
4. 78_v33         0.8165
5. 82_v33         0.7840
6. 80_v33         0.7726

## Ленина 125-127 А (15).JPG

MATCH        79_v33
SCORE        0.8524
SECOND       0.8443
MARGIN       0.0081
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   00 (1).JPG

TOP CANDIDATES
1. 79_v33         0.8524
2. 81_v33         0.8443
3. 83_v33         0.8426
4. 78_v33         0.7772
5. 82_v33         0.7568
6. 80_v33         0.7504

## Ленина 125-127 А (16).JPG

MATCH        79_v33
SCORE        0.8684
SECOND       0.8648
MARGIN       0.0037
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   00 (1).JPG

TOP CANDIDATES
1. 79_v33         0.8684
2. 83_v33         0.8648
3. 81_v33         0.8475
4. 78_v33         0.8028
5. 82_v33         0.7604
6. 80_v33         0.7590

## Ленина 125-127 А (17).JPG

MATCH        79_v33
SCORE        0.8743
SECOND       0.8731
MARGIN       0.0012
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   00 (45).JPG

TOP CANDIDATES
1. 79_v33         0.8743
2. 83_v33         0.8731
3. 81_v33         0.8539
4. 78_v33         0.8184
5. 82_v33         0.7800
6. 80_v33         0.7694

## Ленина 125-127 А (8).JPG

MATCH        79_v33
SCORE        0.8710
SECOND       0.8559
MARGIN       0.0151
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   00 (45).JPG

TOP CANDIDATES
1. 79_v33         0.8710
2. 83_v33         0.8559
3. 81_v33         0.8431
4. 78_v33         0.8113
5. 82_v33         0.7829
6. 80_v33         0.7767

## Ленина 125-127 А (9).JPG

MATCH        79_v33
SCORE        0.8657
SECOND       0.8618
MARGIN       0.0039
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   00 (45).JPG

TOP CANDIDATES
1. 79_v33         0.8657
2. 83_v33         0.8618
3. 81_v33         0.8542
4. 78_v33         0.8142
5. 82_v33         0.7909
6. 80_v33         0.7741

## Ленина Ашхабадский А (1).JPG

MATCH        78_v33
SCORE        0.8187
SECOND       0.8006
MARGIN       0.0181
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo012.JPG

TOP CANDIDATES
1. 78_v33         0.8187
2. 81_v33         0.8006
3. 83_v33         0.7930
4. 79_v33         0.7730
5. 80_v33         0.7646
6. 82_v33         0.7579

## Ленина Ашхабадский А (23).JPG

MATCH        78_v33
SCORE        0.8224
SECOND       0.8165
MARGIN       0.0060
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   photo014.JPG

TOP CANDIDATES
1. 78_v33         0.8224
2. 81_v33         0.8165
3. 80_v33         0.8029
4. 79_v33         0.7991
5. 83_v33         0.7952
6. 82_v33         0.7623

## Ленина Ашхабадский А (24).JPG

MATCH        78_v33
SCORE        0.8484
SECOND       0.8225
MARGIN       0.0259
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo041.JPG

TOP CANDIDATES
1. 78_v33         0.8484
2. 81_v33         0.8225
3. 83_v33         0.8213
4. 79_v33         0.8153
5. 80_v33         0.7945
6. 82_v33         0.7713

## Ленина Ашхабадский А (25).JPG

MATCH        78_v33
SCORE        0.8413
SECOND       0.8046
MARGIN       0.0367
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo014.JPG

TOP CANDIDATES
1. 78_v33         0.8413
2. 79_v33         0.8046
3. 83_v33         0.8044
4. 81_v33         0.8044
5. 80_v33         0.7721
6. 82_v33         0.7583

## Ленина Ашхабадский А (26).JPG

MATCH        78_v33
SCORE        0.8459
SECOND       0.8178
MARGIN       0.0280
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo041.JPG

TOP CANDIDATES
1. 78_v33         0.8459
2. 79_v33         0.8178
3. 81_v33         0.8136
4. 83_v33         0.8106
5. 80_v33         0.7967
6. 82_v33         0.7652

## Ленина Ашхабадский А (27).JPG

MATCH        78_v33
SCORE        0.8207
SECOND       0.7947
MARGIN       0.0259
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo014.JPG

TOP CANDIDATES
1. 78_v33         0.8207
2. 79_v33         0.7947
3. 81_v33         0.7937
4. 83_v33         0.7886
5. 80_v33         0.7704
6. 82_v33         0.7409

## Ленина Ашхабадский А (28).JPG

MATCH        78_v33
SCORE        0.8171
SECOND       0.8046
MARGIN       0.0125
CONFIDENCE   AMBIGUOUS
STATUS       AMBIGUOUS
BEST IMAGE   photo014.JPG

TOP CANDIDATES
1. 78_v33         0.8171
2. 81_v33         0.8046
3. 79_v33         0.7976
4. 83_v33         0.7891
5. 80_v33         0.7753
6. 82_v33         0.7432

## Ленина Ашхабадский А (3).JPG

MATCH        78_v33
SCORE        0.7067
SECOND       0.7032
MARGIN       0.0035
CONFIDENCE   NO_MATCH
STATUS       NO_MATCH
BEST IMAGE   photo018.JPG

TOP CANDIDATES
1. 78_v33         0.7067
2. 81_v33         0.7032
3. 79_v33         0.6832
4. 83_v33         0.6752
5. 80_v33         0.6720
6. 82_v33         0.6528

## Ленина Ашхабадский А (4).JPG

MATCH        78_v33
SCORE        0.7987
SECOND       0.7671
MARGIN       0.0316
CONFIDENCE   NO_MATCH
STATUS       NO_MATCH
BEST IMAGE   photo018.JPG

TOP CANDIDATES
1. 78_v33         0.7987
2. 81_v33         0.7671
3. 83_v33         0.7607
4. 79_v33         0.7512
5. 80_v33         0.7416
6. 82_v33         0.7375

## Ленина Ашхабадский А (43).JPG

MATCH        78_v33
SCORE        0.8383
SECOND       0.8189
MARGIN       0.0194
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo061.JPG

TOP CANDIDATES
1. 78_v33         0.8383
2. 81_v33         0.8189
3. 83_v33         0.8085
4. 79_v33         0.8016
5. 80_v33         0.7693
6. 82_v33         0.7569

## Ленина Ашхабадский А (44).JPG

MATCH        78_v33
SCORE        0.8314
SECOND       0.7976
MARGIN       0.0338
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo061.JPG

TOP CANDIDATES
1. 78_v33         0.8314
2. 83_v33         0.7976
3. 81_v33         0.7962
4. 79_v33         0.7892
5. 80_v33         0.7735
6. 82_v33         0.7571

## Ленина Ашхабадский А (45).JPG

MATCH        78_v33
SCORE        0.8204
SECOND       0.7949
MARGIN       0.0255
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo012.JPG

TOP CANDIDATES
1. 78_v33         0.8204
2. 83_v33         0.7949
3. 81_v33         0.7915
4. 79_v33         0.7789
5. 80_v33         0.7539
6. 82_v33         0.7477

## Ленина Ашхабадский А (5).JPG

MATCH        78_v33
SCORE        0.8715
SECOND       0.8355
MARGIN       0.0360
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo061.JPG

TOP CANDIDATES
1. 78_v33         0.8715
2. 83_v33         0.8355
3. 81_v33         0.8345
4. 79_v33         0.8217
5. 80_v33         0.8002
6. 82_v33         0.7866

## Ленина Ашхабадский А (6).JPG

MATCH        78_v33
SCORE        0.8309
SECOND       0.8146
MARGIN       0.0163
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo033.JPG

TOP CANDIDATES
1. 78_v33         0.8309
2. 81_v33         0.8146
3. 79_v33         0.8058
4. 83_v33         0.8021
5. 80_v33         0.7744
6. 82_v33         0.7578

## Ленина Ашхабадский А (7).JPG

MATCH        80_v33
SCORE        0.6034
SECOND       0.5871
MARGIN       0.0164
CONFIDENCE   NO_MATCH
STATUS       NO_MATCH
BEST IMAGE   036.JPG

TOP CANDIDATES
1. 80_v33         0.6034
2. 78_v33         0.5871
3. 81_v33         0.5850
4. 82_v33         0.5792
5. 79_v33         0.5766
6. 83_v33         0.5549

## Ленина Ашхабадский А (8).JPG

MATCH        78_v33
SCORE        0.8513
SECOND       0.8267
MARGIN       0.0246
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo021.JPG

TOP CANDIDATES
1. 78_v33         0.8513
2. 81_v33         0.8267
3. 83_v33         0.8166
4. 82_v33         0.8063
5. 80_v33         0.8046
6. 79_v33         0.8034

## Ленина Ашхабадский А2 (1).JPG

MATCH        78_v33
SCORE        0.8324
SECOND       0.7912
MARGIN       0.0412
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo012.JPG

TOP CANDIDATES
1. 78_v33         0.8324
2. 81_v33         0.7912
3. 83_v33         0.7782
4. 79_v33         0.7777
5. 82_v33         0.7694
6. 80_v33         0.7468

## Ленина Ашхабадский А2 (2).JPG

MATCH        78_v33
SCORE        0.8438
SECOND       0.8115
MARGIN       0.0322
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   photo061.JPG

TOP CANDIDATES
1. 78_v33         0.8438
2. 81_v33         0.8115
3. 79_v33         0.7913
4. 83_v33         0.7902
5. 80_v33         0.7782
6. 82_v33         0.7773

## Нагибина 24 А (1).JPG

MATCH        83_v33
SCORE        0.9295
SECOND       0.8733
MARGIN       0.0562
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (1).JPG

TOP CANDIDATES
1. 83_v33         0.9295
2. 78_v33         0.8733
3. 79_v33         0.8350
4. 81_v33         0.8347
5. 82_v33         0.7892
6. 80_v33         0.7738

## Нагибина 24 А (10).JPG

MATCH        83_v33
SCORE        0.9479
SECOND       0.8806
MARGIN       0.0674
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (4).JPG

TOP CANDIDATES
1. 83_v33         0.9479
2. 78_v33         0.8806
3. 79_v33         0.8639
4. 81_v33         0.8588
5. 82_v33         0.8164
6. 80_v33         0.8007

## Нагибина 24 А (11).JPG

MATCH        83_v33
SCORE        0.9339
SECOND       0.8836
MARGIN       0.0502
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (1).JPG

TOP CANDIDATES
1. 83_v33         0.9339
2. 78_v33         0.8836
3. 79_v33         0.8512
4. 81_v33         0.8451
5. 82_v33         0.8104
6. 80_v33         0.7834

## Нагибина 24 А (12).JPG

MATCH        83_v33
SCORE        0.8842
SECOND       0.8586
MARGIN       0.0256
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   Нагибина 24 А (4).JPG

TOP CANDIDATES
1. 83_v33         0.8842
2. 81_v33         0.8586
3. 78_v33         0.8511
4. 79_v33         0.8100
5. 80_v33         0.7935
6. 82_v33         0.7886

## Нагибина 24 А (13).JPG

MATCH        83_v33
SCORE        0.8830
SECOND       0.8648
MARGIN       0.0181
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   22 (6).JPG

TOP CANDIDATES
1. 83_v33         0.8830
2. 81_v33         0.8648
3. 78_v33         0.8454
4. 79_v33         0.8174
5. 80_v33         0.7992
6. 82_v33         0.7861

## Нагибина 24 А (2).JPG

MATCH        83_v33
SCORE        0.9028
SECOND       0.8441
MARGIN       0.0587
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   Нагибина 24 А (4).JPG

TOP CANDIDATES
1. 83_v33         0.9028
2. 78_v33         0.8441
3. 81_v33         0.8425
4. 79_v33         0.8087
5. 82_v33         0.7809
6. 80_v33         0.7760

## Нагибина 24 А (3).JPG

MATCH        83_v33
SCORE        0.8820
SECOND       0.8339
MARGIN       0.0481
CONFIDENCE   PROBABLE
STATUS       PROBABLE_MATCH
BEST IMAGE   22 (6).JPG

TOP CANDIDATES
1. 83_v33         0.8820
2. 81_v33         0.8339
3. 78_v33         0.8211
4. 79_v33         0.8006
5. 82_v33         0.7827
6. 80_v33         0.7747

## Нагибина 24 А (30).JPG

MATCH        83_v33
SCORE        0.9270
SECOND       0.8687
MARGIN       0.0583
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (21).JPG

TOP CANDIDATES
1. 83_v33         0.9270
2. 78_v33         0.8687
3. 81_v33         0.8405
4. 79_v33         0.8373
5. 82_v33         0.7821
6. 80_v33         0.7537

## Нагибина 24 А (31).JPG

MATCH        83_v33
SCORE        0.9225
SECOND       0.8644
MARGIN       0.0581
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (21).JPG

TOP CANDIDATES
1. 83_v33         0.9225
2. 78_v33         0.8644
3. 81_v33         0.8381
4. 79_v33         0.8338
5. 82_v33         0.7826
6. 80_v33         0.7540

## Нагибина 24 А (32).JPG

MATCH        83_v33
SCORE        0.9200
SECOND       0.8626
MARGIN       0.0575
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (21).JPG

TOP CANDIDATES
1. 83_v33         0.9200
2. 78_v33         0.8626
3. 81_v33         0.8388
4. 79_v33         0.8347
5. 82_v33         0.7779
6. 80_v33         0.7521

## Нагибина 24 А (33).JPG

MATCH        83_v33
SCORE        0.9195
SECOND       0.8610
MARGIN       0.0585
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (21).JPG

TOP CANDIDATES
1. 83_v33         0.9195
2. 78_v33         0.8610
3. 79_v33         0.8293
4. 81_v33         0.8281
5. 82_v33         0.7707
6. 80_v33         0.7421

## Нагибина 24 А (34).JPG

MATCH        83_v33
SCORE        0.9227
SECOND       0.8804
MARGIN       0.0423
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (15).JPG

TOP CANDIDATES
1. 83_v33         0.9227
2. 78_v33         0.8804
3. 79_v33         0.8275
4. 81_v33         0.8251
5. 82_v33         0.7861
6. 80_v33         0.7503

## Нагибина 24 А (35).JPG

MATCH        83_v33
SCORE        0.9207
SECOND       0.8545
MARGIN       0.0662
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (1).JPG

TOP CANDIDATES
1. 83_v33         0.9207
2. 78_v33         0.8545
3. 81_v33         0.8274
4. 79_v33         0.8113
5. 82_v33         0.7682
6. 80_v33         0.7550

## Нагибина 24 А (4).JPG

MATCH        83_v33
SCORE        0.9127
SECOND       0.8580
MARGIN       0.0547
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   Нагибина 24 А (4).JPG

TOP CANDIDATES
1. 83_v33         0.9127
2. 78_v33         0.8580
3. 81_v33         0.8501
4. 79_v33         0.8301
5. 82_v33         0.8002
6. 80_v33         0.7835

## Нагибина 24 А (5).JPG

MATCH        83_v33
SCORE        0.9039
SECOND       0.8433
MARGIN       0.0606
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   22 (8).JPG

TOP CANDIDATES
1. 83_v33         0.9039
2. 78_v33         0.8433
3. 79_v33         0.8109
4. 81_v33         0.8064
5. 82_v33         0.7611
6. 80_v33         0.7257

## Нагибина 24 А (8).JPG

MATCH        83_v33
SCORE        0.9317
SECOND       0.8561
MARGIN       0.0756
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (4).JPG

TOP CANDIDATES
1. 83_v33         0.9317
2. 78_v33         0.8561
3. 79_v33         0.8452
4. 81_v33         0.8352
5. 82_v33         0.7923
6. 80_v33         0.7564

## Нагибина 24 А (9).JPG

MATCH        83_v33
SCORE        0.9150
SECOND       0.8454
MARGIN       0.0696
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   33 (4).JPG

TOP CANDIDATES
1. 83_v33         0.9150
2. 78_v33         0.8454
3. 81_v33         0.8453
4. 79_v33         0.8272
5. 82_v33         0.7904
6. 80_v33         0.7585
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

