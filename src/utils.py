from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image, ImageOps

NUTRITION_KEYS = [
    "calories_kcal",
    "protein_g",
    "carbs_g",
    "fat_g",
    "fiber_g",
    "sugar_g",
    "sodium_mg",
]


def compress_image(image: Image.Image, max_side: int = 1600, quality: int = 88) -> bytes:
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    scale = min(1.0, max_side / max(width, height))
    if scale < 1.0:
        image = image.resize((round(width * scale), round(height * scale)), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def nutrition_totals(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        key: round(sum(float(row.get(key, 0) or 0) for row in rows), 2)
        for key in NUTRITION_KEYS
    }


def safe_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return safe_json(value.model_dump())
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
