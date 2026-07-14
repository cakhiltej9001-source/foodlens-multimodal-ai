from PIL import Image

from src.utils import compress_image, nutrition_totals


def test_compress_image_returns_jpeg_bytes():
    image = Image.new("RGB", (2400, 1200), "white")
    output = compress_image(image, max_side=800)
    assert output[:2] == b"\xff\xd8"
    assert len(output) > 100


def test_nutrition_totals():
    totals = nutrition_totals([
        {"calories_kcal": 120, "protein_g": 4},
        {"calories_kcal": 80, "protein_g": 6},
    ])
    assert totals["calories_kcal"] == 200
    assert totals["protein_g"] == 10
