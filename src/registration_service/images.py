from __future__ import annotations

import json
from io import BytesIO
from uuid import uuid4

from PIL import Image, ImageDraw

from .config import settings


def save_original_image(image_bytes: bytes, suffix: str) -> str:
    settings.raw_image_dir.mkdir(parents=True, exist_ok=True)
    path = settings.raw_image_dir / f"{uuid4()}{suffix or '.bin'}"
    path.write_bytes(image_bytes)
    return str(path)


def _save_png(image: Image.Image) -> str:
    settings.raw_image_dir.mkdir(parents=True, exist_ok=True)
    path = settings.raw_image_dir / f"{uuid4()}.png"
    image.save(path)
    return str(path)


def parse_bounding_box(value: str | None) -> list[list[float]] | None:
    if not value:
        return None
    parsed = json.loads(value)
    if (
        not isinstance(parsed, list)
        or len(parsed) != 4
        or any(not isinstance(point, list) or len(point) != 2 for point in parsed)
    ):
        raise ValueError("bounding_box must contain exactly four [x, y] points")
    return [[float(point[0]), float(point[1])] for point in parsed]


def derive_images(image_bytes: bytes, bounding_box: list[list[float]]) -> tuple[str, str]:
    source = Image.open(BytesIO(image_bytes)).convert("RGB")
    points = [(x, y) for x, y in bounding_box]
    overlay = source.copy()
    ImageDraw.Draw(overlay).line(points + [points[0]], fill="red", width=max(2, source.width // 200))
    overlay_path = _save_png(overlay)

    top_width = ((points[1][0] - points[0][0]) ** 2 + (points[1][1] - points[0][1]) ** 2) ** 0.5
    bottom_width = ((points[2][0] - points[3][0]) ** 2 + (points[2][1] - points[3][1]) ** 2) ** 0.5
    left_height = ((points[3][0] - points[0][0]) ** 2 + (points[3][1] - points[0][1]) ** 2) ** 0.5
    right_height = ((points[2][0] - points[1][0]) ** 2 + (points[2][1] - points[1][1]) ** 2) ** 0.5
    width = max(1, round(max(top_width, bottom_width)))
    height = max(1, round(max(left_height, right_height)))
    quad = [
        points[0][0], points[0][1],
        points[3][0], points[3][1],
        points[2][0], points[2][1],
        points[1][0], points[1][1],
    ]
    warped = source.transform((width, height), Image.Transform.QUAD, quad, resample=Image.Resampling.BICUBIC)
    return overlay_path, _save_png(warped)
