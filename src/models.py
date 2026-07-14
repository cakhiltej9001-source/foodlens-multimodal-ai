from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class DetectedFood(BaseModel):
    name: str = Field(description="Specific, searchable food name")
    estimated_grams: float = Field(default=100, ge=1, le=3000)
    confidence: float = Field(default=0.5, ge=0, le=1)
    preparation: str = Field(default="unknown")
    visible_ingredients: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Food name cannot be empty")
        return value


class FoodAnalysis(BaseModel):
    dish_name: str
    cuisine: str = "Unknown"
    meal_type: str = "Meal"
    description: str
    detected_foods: list[DetectedFood]
    allergens: list[str] = Field(default_factory=list)
    dietary_tags: list[str] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.5, ge=0, le=1)
    uncertainty_note: str = "Visual estimates may be inaccurate."


class NutritionRow(BaseModel):
    item_name: str
    matched_food: str
    fdc_id: int | None = None
    estimated_grams: float
    calories_kcal: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    fiber_g: float = 0
    sugar_g: float = 0
    sodium_mg: float = 0
    match_score: float = 0
    data_type: str = "Unknown"


class Recipe(BaseModel):
    name: str
    description: str
    servings: int = Field(default=2, ge=1, le=12)
    prep_time_minutes: int = Field(default=10, ge=0, le=300)
    cook_time_minutes: int = Field(default=20, ge=0, le=600)
    difficulty: str = "Easy"
    ingredients: list[str]
    steps: list[str]
    nutrition_note: str = ""


class RecipeCollection(BaseModel):
    recipes: list[Recipe]
