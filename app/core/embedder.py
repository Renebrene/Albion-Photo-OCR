from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel


class SceneEmbedder:
    """DINOv2 ViT-B/14 global embedding service.

    Uses Hugging Face Transformers instead of torch.hub.

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

        self.model_name = settings.model_name

        print(
            f"[SceneEmbedder] Loading DINOv2: "
            f"{self.model_name}"
        )

        self.processor = AutoImageProcessor.from_pretrained(
            self.model_name
        )

        self.model = AutoModel.from_pretrained(
            self.model_name
        )

        self.model = self.model.to(self.device)
        self.model.eval()

        self.dimension = 768

        print(
            f"[SceneEmbedder] embedding dimension="
            f"{self.dimension}"
        )
        print(
            "[SceneEmbedder] patch extraction=DISABLED "
            "(compact)"
        )
        print("[SceneEmbedder] Ready.")

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

            inputs = self.processor(
                images=batch_images,
                return_tensors="pt",
            )

            inputs = {
                key: value.to(
                    self.device,
                    non_blocking=True,
                )
                for key, value in inputs.items()
            }

            outputs = self.model(**inputs)

            # DINOv2 CLS token.
            features = outputs.last_hidden_state[:, 0, :]

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
