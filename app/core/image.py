from pathlib import Path
from PIL import Image

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

def image_files(folder):
    folder = Path(folder)
    if not folder.exists():
        raise FileNotFoundError(f"Папка не существует: {folder}")
    return sorted(p for p in folder.rglob("*")
                  if p.is_file() and p.suffix.lower() in EXTENSIONS)

def load_image(path):
    with Image.open(path) as im:
        return im.convert("RGB")
