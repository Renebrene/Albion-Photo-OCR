from dataclasses import dataclass
from pathlib import Path
import os
import torch

from app.preview import formats

@dataclass(frozen=True)
class Settings:
    host: str = os.getenv("SCENE_HOST", "127.0.0.1")
    port: int = int(os.getenv("SCENE_PORT", "8080"))
    data_dir: Path = Path(os.getenv("SCENE_DATA", "data"))
    model_name: str = os.getenv("SCENE_MODEL", "facebook/dinov2-base")
    device: str = os.getenv("SCENE_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    batch_size: int = int(os.getenv("SCENE_BATCH", "16"))

    preview_root: Path = Path(
        os.getenv("SCENE_PREVIEW_ROOT", str(data_dir / "preview"))
    )
    preview_small_size: int = int(
        os.getenv("SCENE_PREVIEW_SMALL_SIZE", "320")
    )
    preview_middle_size: int = int(
        os.getenv("SCENE_PREVIEW_MIDDLE_SIZE", "1280")
    )
    preview_workers: int = int(
        os.getenv("SCENE_PREVIEW_WORKERS", "0")
    )
    # Format of SMALL/MIDDLE previews: "webp" (default) or "jpeg".
    # WebP q80 measured -46 % against JPEG q90 at the same 1280 px with no
    # visible difference on 1:1 crops (docs/preview_experiment_20261022.md).
    preview_format: str = formats.normalize_format(
        os.getenv("SCENE_PREVIEW_FORMAT", formats.DEFAULT_FORMAT)
    )
    # Encode quality; None -> the format's own default (WebP 80, JPEG 90),
    # overridable with SCENE_PREVIEW_QUALITY.
    preview_quality: int | None = (
        int(os.environ["SCENE_PREVIEW_QUALITY"])
        if os.getenv("SCENE_PREVIEW_QUALITY", "").strip()
        else None
    )

    # DINO worker threads per batch. Default 1: measured on CPU, threads give
    # almost no wall-clock gain while inflating per-item time (GIL/CPU-bound).
    # 0 = automatic (half of logical CPUs) for experiments.
    dino_workers: int = int(
        os.getenv("SCENE_DINO_WORKERS", "1")
    )

    # Images per DINO forward pass in the batched path (1 = one image per call).
    dino_batch: int = int(
        os.getenv("SCENE_DINO_BATCH", "1")
    )

    @property
    def fingerprints_dir(self):
        return self.data_dir / "fingerprints"

settings = Settings()
