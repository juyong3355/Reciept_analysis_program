from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageOps


def _content_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    gray = ImageOps.grayscale(image)
    background = Image.new("L", gray.size, 255)
    difference = ImageChops.difference(gray, background)
    mask = difference.point(lambda value: 255 if value > 12 else 0)
    return mask.getbbox()


def preprocess_for_ocr(
    source_path: str | Path,
    output_path: str | Path,
    scale: float = 1.5,
) -> tuple[Path, dict[str, float | int]]:
    source = Path(source_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        original_width, original_height = image.size
        bbox = _content_bbox(image)
        if bbox:
            padding = max(12, round(min(image.size) * 0.01))
            left = max(0, bbox[0] - padding)
            top = max(0, bbox[1] - padding)
            right = min(image.width, bbox[2] + padding)
            bottom = min(image.height, bbox[3] + padding)
            image = image.crop((left, top, right, bottom))
        else:
            left = top = 0
        gray = ImageOps.grayscale(image)
        gray = ImageOps.autocontrast(gray, cutoff=1)
        gray = ImageEnhance.Contrast(gray).enhance(1.15)
        if scale != 1:
            gray = gray.resize(
                (round(gray.width * scale), round(gray.height * scale)),
                Image.Resampling.LANCZOS,
            )
        gray.save(output, format="PNG", optimize=True)
    return output, {
        "original_width": original_width,
        "original_height": original_height,
        "crop_left": left,
        "crop_top": top,
        "scale": scale,
    }

