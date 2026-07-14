"""Offline smoke test: validates imports and local helper logic without using API calls."""
from pathlib import Path
import sys

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import DetectedFood
from src.nutrition_service import scale_nutrients
from src.utils import compress_image


def main() -> None:
    food = DetectedFood(name="cooked rice", estimated_grams=150, confidence=0.9)
    assert food.name == "cooked rice"
    assert scale_nutrients({"calories_kcal": 130}, 150)["calories_kcal"] == 195
    assert compress_image(Image.new("RGB", (100, 100), "white"))[:2] == b"\xff\xd8"
    print("FoodLens AI smoke test passed.")


if __name__ == "__main__":
    main()
