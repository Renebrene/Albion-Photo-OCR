"""Сгенерировать демонстрационные фото с рекламными щитами.

Ничего не читает из базы и не пишет в неё: просто создаёт JPEG-файлы, чтобы
на пустой установке было что показать (грид, превью, детекция щитов).

Запуск (в контейнере или локально):
    python scripts/make_demo_images.py /photos --count 12
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1600, 1200

BRANDS = [
    ("РЯЗАНКА", "СКИДКА 1+1", "139 ₽", (200, 30, 40)),
    ("МТС", "СЕМЕЙНЫЙ ЗАЩИТНИК", "СКИДКА 100%", (220, 40, 60)),
    ("ОЗОН", "ДОСТАВКА ЗА 30 МИНУТ", "ПРОМОКОД OZON", (40, 90, 200)),
    ("БЕТСИТИ", "СУПЕРЛИГА ПО ФУТЗАЛУ", "БОНУС 100%", (20, 40, 90)),
    ("ЕДИНАЯ РОССИЯ", "НАРОДНАЯ ПРОГРАММА", "18-19-20 СЕНТЯБРЯ", (30, 90, 180)),
    ("ВОЛЬНЫЙ ДОН", "ПУТЕШЕСТВИЕ ПО ДОНУ", "VISITDON.RU", (30, 120, 90)),
    ("T2", "ТРОЙНОЙ БЕЗЛИМИТ", "390 ₽/МЕС", (30, 30, 30)),
    ("МАГНИТ", "ЧУДО КОКТЕЙЛЬ", "-19%", (200, 40, 120)),
    ("СБЕР МОБАЙЛ", "ТАРИФ ДЛЯ ВСЕХ", "390 ₽", (30, 160, 80)),
    ("OZON BANK", "КРЕДИТНАЯ КАРТА", "ДО 140 ДНЕЙ", (40, 70, 180)),
]

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def draw_scene(index: int, brand: tuple, billboard: bool) -> Image.Image:
    rng = random.Random(1000 + index)
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    # Небо и земля.
    top = (150 + rng.randint(0, 60), 190 + rng.randint(0, 40), 235)
    draw.rectangle([0, 0, WIDTH, 780], fill=top)
    draw.rectangle([0, 780, WIDTH, HEIGHT], fill=(95, 100, 105))

    # Дома.
    x = 0
    while x < WIDTH:
        width = rng.randint(150, 320)
        height = rng.randint(300, 620)
        color = (
            rng.randint(130, 210),
            rng.randint(120, 190),
            rng.randint(100, 170),
        )
        draw.rectangle([x, 780 - height, x + width, 780], fill=color)
        for wy in range(780 - height + 30, 760, 70):
            for wx in range(x + 20, x + width - 30, 55):
                draw.rectangle([wx, wy, wx + 26, wy + 34], fill=(60, 70, 90))
        x += width + rng.randint(10, 40)

    # Дорога и разметка.
    draw.rectangle([0, 900, WIDTH, HEIGHT], fill=(65, 65, 70))
    for dash in range(0, WIDTH, 120):
        draw.rectangle([dash, 1050, dash + 60, 1064], fill=(230, 230, 230))

    if billboard:
        name, line1, line2, accent = brand
        bw, bh = 760, 380
        bx = rng.randint(380, WIDTH - bw - 120)
        by = rng.randint(250, 430)

        # Опора.
        draw.rectangle(
            [bx + bw // 2 - 18, by + bh, bx + bw // 2 + 18, 900],
            fill=(90, 90, 95),
        )
        draw.rectangle([bx, by, bx + bw, by + bh], fill=accent)
        draw.rectangle([bx, by, bx + bw, by + bh], outline=(245, 245, 245), width=8)

        draw.text((bx + 40, by + 34), name, font=font(76), fill=(255, 255, 255))
        draw.text((bx + 40, by + 150), line1, font=font(52), fill=(255, 255, 255))
        draw.text((bx + 40, by + 246), line2, font=font(64), fill=(255, 230, 80))

    # Пара машин для правдоподобия.
    for car in range(rng.randint(1, 3)):
        cx = rng.randint(100, WIDTH - 300)
        cy = 860 + car * 70
        draw.rounded_rectangle(
            [cx, cy, cx + 220, cy + 70], radius=18, fill=(rng.randint(30, 220), 60, 60)
        )
        draw.ellipse([cx + 30, cy + 50, cx + 80, cy + 96], fill=(20, 20, 20))
        draw.ellipse([cx + 140, cy + 50, cx + 190, cy + 96], fill=(20, 20, 20))

    return image


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="каталог для JPEG-файлов")
    parser.add_argument("--count", type=int, default=12)
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    created = 0

    for index in range(max(1, args.count)):
        # Последние два кадра — негативы без щита (проверка ложных срабатываний).
        billboard = index < max(1, args.count) - 2
        brand = BRANDS[index % len(BRANDS)]
        image = draw_scene(index, brand, billboard)
        path = output / f"demo_{index + 1:02d}.jpg"
        image.save(path, format="JPEG", quality=88, optimize=True)
        created += 1
        print(f"created {path}")

    print(f"done: {created} file(s) in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
