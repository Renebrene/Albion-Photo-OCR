from __future__ import annotations

import argparse
from pathlib import Path

import cv2


def detect_white_rectangles(
    image_path: str | Path,
    output_path: str | Path,
    min_area: int = 2000,
):
    image_path = Path(image_path)
    output_path = Path(output_path)

    image = cv2.imread(str(image_path))

    if image is None:
        raise FileNotFoundError(image_path)

    original = image.copy()

    # Уменьшаем изображение только для поиска кандидатов.
    # Сам оригинал при этом не изменяется.
    scale = 1.0

    max_width = 1600

    if image.shape[1] > max_width:
        scale = max_width / image.shape[1]

        image = cv2.resize(
            image,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA,
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Белые области.
    _, mask = cv2.threshold(
        gray,
        190,
        255,
        cv2.THRESH_BINARY,
    )

    # Немного объединяем разрывы внутри/по краям таблички.
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (7, 7),
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel,
    )

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    candidates = []

    for contour in contours:
        area = cv2.contourArea(contour)

        if area < min_area:
            continue

        perimeter = cv2.arcLength(
            contour,
            True,
        )

        if perimeter == 0:
            continue

        approx = cv2.approxPolyDP(
            contour,
            0.03 * perimeter,
            True,
        )

        x, y, w, h = cv2.boundingRect(contour)

        if w <= 0 or h <= 0:
            continue

        aspect = w / h

        # Табличка должна быть заметно прямоугольной.
        if aspect < 1.3 or aspect > 8.0:
            continue

        # Проверяем заполненность прямоугольника.
        rect_area = w * h
        fill_ratio = area / rect_area

        if fill_ratio < 0.45:
            continue

        candidates.append(
            {
                "contour": contour,
                "bbox": (x, y, w, h),
                "area": area,
                "aspect": aspect,
                "fill_ratio": fill_ratio,
                "corners": len(approx),
            }
        )

    # Сортируем крупные кандидаты первыми.
    candidates.sort(
        key=lambda item: item["area"],
        reverse=True,
    )

    # Рисуем кандидатов на уменьшенной фотографии.
    debug = image.copy()

    for index, candidate in enumerate(candidates):
        x, y, w, h = candidate["bbox"]

        cv2.rectangle(
            debug,
            (x, y),
            (x + w, y + h),
            (0, 0, 255),
            3,
        )

        label = (
            f"{index + 1} "
            f"A={candidate['area']:.0f} "
            f"R={candidate['aspect']:.2f}"
        )

        cv2.putText(
            debug,
            label,
            (x, max(25, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cv2.imwrite(
        str(output_path),
        debug,
    )

    return candidates


def main():
    parser = argparse.ArgumentParser(
        description="Detect white rectangular plate candidates"
    )

    parser.add_argument(
        "image",
        help="Input image",
    )

    parser.add_argument(
        "--output",
        default="data/ocr_debug/plate_candidates.jpg",
        help="Debug output image",
    )

    args = parser.parse_args()

    candidates = detect_white_rectangles(
        args.image,
        args.output,
    )

    print()
    print("=" * 70)
    print("WHITE RECTANGLE DETECTOR")
    print("=" * 70)

    print(f"Candidates: {len(candidates)}")

    for i, candidate in enumerate(candidates, 1):
        print(
            f"{i:02d}. "
            f"bbox={candidate['bbox']} "
            f"area={candidate['area']:.0f} "
            f"aspect={candidate['aspect']:.2f} "
            f"fill={candidate['fill_ratio']:.2f}"
        )

    print("=" * 70)
    print()
    print(f"Debug image: {args.output}")


if __name__ == "__main__":
    main()
