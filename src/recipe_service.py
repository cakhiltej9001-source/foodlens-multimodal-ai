from __future__ import annotations

from google import genai
from google.genai import types

from src.models import FoodAnalysis, RecipeCollection


def generate_recipes(
    analysis: FoodAnalysis,
    api_key: str,
    model: str,
    dietary_preference: str,
    cuisine: str,
    recipe_count: int = 3,
) -> RecipeCollection:
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing.")

    foods = [food.name for food in analysis.detected_foods]
    prompt = f"""
Create exactly {recipe_count} practical recipes inspired by the foods detected in this meal image.
Detected foods: {foods}
Detected dish: {analysis.dish_name}
Preferred dietary style: {dietary_preference}
Preferred cuisine: {cuisine}

Rules:
- The recipes may reuse detected foods or transform leftovers safely.
- Respect the stated dietary preference.
- Use common ingredients and clear quantities.
- Give concise, executable steps.
- Do not claim medical benefits.
- Mention when a recipe requires checking allergens.
""".strip()

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.55,
            response_mime_type="application/json",
            response_schema=RecipeCollection,
        ),
    )
    if getattr(response, "parsed", None):
        result = RecipeCollection.model_validate(response.parsed)
    elif response.text:
        result = RecipeCollection.model_validate_json(response.text)
    else:
        raise RuntimeError("Gemini returned an empty recipe response.")

    result.recipes = result.recipes[:recipe_count]
    return result
