import pytest
from pydantic import ValidationError

from src.models import DetectedFood


def test_food_confidence_range():
    with pytest.raises(ValidationError):
        DetectedFood(name="rice", estimated_grams=100, confidence=1.5)
