### 🛠️ **Решение проблемы с DINOv2 через `torch.hub`**

#### 1. **Проверка текущей реализации `SceneEmbedder`**
Твой текущий `embedder.py` использует `torch.hub.load` для загрузки модели DINOv2. Однако:

- **`torch.hub.load("facebookresearch/dinov2", "dinov2_vitb14")`** — **не существует** в репозитории [facebookresearch/dinov2](https://github.com/facebookresearch/dinov2).
- Вместо этого, в репозитории есть **`dinov2_vitb14`** как **предобученная модель**, но она **не доступна через `torch.hub`**.
- `torch.hub` ожидает **модель в формате `torch.hub.load("repo", "model_name")`**, но DINOv2 **не поддерживает этот формат**.

---

### 🚫 **Причина ошибки `RemoteDisconnected`**
- Ты пытаешься загрузить модель через `torch.hub`, но:
  - Репозиторий `facebookresearch/dinov2` **не содержит** модель `dinov2_vitb14` в формате, который поддерживает `torch.hub`.
  - `torch.hub` не может найти модель и пытается загрузить её с GitHub, но соединение прерывается.

---

### ✅ **Вариант 1: Использовать Hugging Face (рекомендуется)**

Если ты хочешь **оставить архитектуру `SceneEmbedder`**, но **исправить проблему с загрузкой модели**, используй **`transformers`** (как в старой версии):

#### ✅ **Изменения в `embedder.py`**
```python
from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

class SceneEmbedder:
    """DINOv2 ViT-B/14 global embedding service.

    v3.2 Compact deliberately does NOT extract or store
    DINO patch tokens.

    Output:
        global embedding: [N, 768]
    """

    def __init__(self, settings):
        self.settings = settings
        self.device = torch.device(settings.device)

        print(f"[SceneEmbedder] device={self.device}")

        if self.device.type == "cuda":
            print(
                f"[SceneEmbedder] GPU="
                f"{torch.cuda.get_device_name(0)}"
            )
            print(
                f"[SceneEmbedder] VRAM="
                f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
            )

        print("[SceneEmbedder] Loading DINOv2...")

        # Используем Hugging Face для загрузки модели
        self.processor = AutoImageProcessor.from_pretrained("facebook/dinov2-vitb14")
        self.model = AutoModel.from_pretrained("facebook/dinov2-vitb14")
        self.model = self.model.to(self.device).eval()

        self.dimension = 768

        self.transform = transforms.Compose([
            transforms.Resize(
                256,
                interpolation=transforms.InterpolationMode.BICUBIC,
            ),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        print(
            f"[SceneEmbedder] embedding dimension="
            f"{self.dimension}"
        )
        print(
            "[SceneEmbedder] patch extraction=DISABLED "
            "(v3.2 compact)"
        )
        print("[SceneEmbedder] Ready.")

    def _prepare_batch(self, images):
        return torch.stack([
            self.transform(image)
            for image in images
        ]).to(
            self.device,
            non_blocking=True,
        )

    @torch.inference_mode()
    def embed_images(
        self,
        images: list[Image.Image],
        batch_size=None,
    ):
        batch_size = (
            batch_size
            or self.settings.batch_size
        )

        vectors = []

        for i in range(
            0,
            len(images),
            batch_size,
        ):
            batch_images = images[
                i:i + batch_size
            ]

            batch = self._prepare_batch(
                batch_images
            )

            features = self.model(batch)

            features = torch.nn.functional.normalize(
                features,
                dim=1,
            )

            vectors.append(
                features.float()
                .cpu()
                .numpy()
            )

        if not vectors:
            return np.empty(
                (0, self.dimension),
                dtype=np.float32,
            )

        return np.concatenate(
            vectors,
            axis=0,
        ).astype("float32")

    def embed_paths(self, paths):
        from .image import load_image

        images = [
            load_image(path)
            for path in paths
        ]

        return self.embed_images(images)
```

---

### 🔄 **Вариант 2: Использовать `torch.hub` (если нужно)**

Если ты хочешь **оставить `torch.hub`**, нужно:

1. **Скачать модель вручную**:
   ```bash
   # Скачай модель DINOv2
   wget https://dl.fbaipublicfiles.com/dinov2/dinov2_vitb14_pretrain.pth
   ```

2. **Указать путь к модели в `torch.hub`**:
   ```python
   import torch
   from torch.hub import download_url_to_file

   # Скачай модель вручную
   model_path = "dinov2_vitb14_pretrain.pth"
   download_url_to_file(
       "https://dl.fbaipublicfiles.com/dinov2/dinov2_vitb14_pretrain.pth",
       model_path
   )

   # Загрузи модель
   model = torch.hub.load(
       "facebookresearch/dinov2",
       "dinov2_vitb14",
       pretrained=True,
       model_path=model_path
   )
   ```

---

### 🧠 **Важные моменты**
- **`torch.hub` не поддерживает DINOv2** в текущем виде.
- **Hugging Face** — **более стабильный и удобный способ** для загрузки DINOv2.
- Если ты хочешь **оставить `torch.hub`**, нужно **скачать модель вручную** и указать её путь.

---

### 📌 **Дополнительно**
- Убедись, что у тебя установлены:
  ```bash
  pip install torch torchvision
  ```
- Проверь, что у тебя есть доступ к интернету и что GitHub не блокирует запросы.

Если ты хочешь, я могу помочь **создать `83_v33`**, используя **Hugging Face** или **ручную загрузку модели**.