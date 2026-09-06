from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

from paddleocr import PaddleOCR


@dataclass
class OCRResult:
    text: str
    confidence: float
    bbox: list


class OCRPipeline:
    """
    Базовый OCR-модуль.

    На этом этапе:
    - принимает фотографию;
    - запускает PaddleOCR;
    - возвращает весь найденный текст.

    Поиск белой таблички и SQL пока НЕ реализованы.
    """

    def __init__(self, lang: str = "ru"):
        self.lang = lang

        print("[OCR] Initializing PaddleOCR...")
        self.ocr = PaddleOCR(
            lang=self.lang,
            use_gpu=False,
        )
        print("[OCR] Ready. Device=CPU")

    def recognize(self, image_path: str | Path) -> list[OCRResult]:
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        start = time.perf_counter()

        result = self.ocr.ocr(
            str(image_path),
            cls=True,
        )

        elapsed = time.perf_counter() - start

        results = []

        if result and result[0]:
            for line in result[0]:
                bbox = line[0]
                text = line[1][0]
                confidence = float(line[1][1])

                results.append(
                    OCRResult(
                        text=text,
                        confidence=confidence,
                        bbox=bbox,
                    )
                )

        print(f"[OCR] Image: {image_path.name}")
        print(f"[OCR] Time: {elapsed:.3f} sec")
        print(f"[OCR] Text regions: {len(results)}")

        return results


def main():
    parser = argparse.ArgumentParser(
        description="Basic PaddleOCR test"
    )

    parser.add_argument(
        "image",
        help="Path to image",
    )

    parser.add_argument(
        "--lang",
        default="ru",
        help="OCR language",
    )

    args = parser.parse_args()

    ocr = OCRPipeline(
        lang=args.lang,
    )

    results = ocr.recognize(
        args.image,
    )

    print()
    print("=" * 70)
    print("OCR RESULT")
    print("=" * 70)

    if not results:
        print("No text detected.")
    else:
        for i, item in enumerate(results, 1):
            print(
                f"{i:02d}. "
                f"text={item.text!r} "
                f"confidence={item.confidence:.4f}"
            )

    print("=" * 70)


if __name__ == "__main__":
    main()
