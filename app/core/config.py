from dataclasses import dataclass
from pathlib import Path
import os
import torch

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

    @property
    def fingerprints_dir(self):
        return self.data_dir / "fingerprints"

settings = Settings()
