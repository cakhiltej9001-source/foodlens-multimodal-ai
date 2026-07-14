from __future__ import annotations

from io import BytesIO

from google import genai
from google.genai import types
from PIL import Image

from src.models import FoodAnalysis


SYSTEM_INSTRUCTION = """
You are a careful multimodal food-analysis assistant. Analyze only what is visually supported.
Separate composite meals into searchable food components when useful for nutrition lookup.
Estimate edible portion weight in grams conservatively. Confidence must be between 0 and 1.
List possible allergens only when plausible, and explicitly communicate uncertainty.
Do not provide medical advice and do not claim exact nutrition from the image.
""".strip()


def analyze_food_image(image_bytes: bytes, api_key: str, model: str) -> FoodAnalysis:
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing. Add it to your .env file.")

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    client = genai.Client(api_key=api_key)
    prompt = """
Analyze this food image and return structured data.

Requirements:
- Give the overall dish a concise name.
- Identify cuisine and meal type when reasonably inferable.
- Break the plate into separate foods suitable for USDA search. Example: rice, lentil curry, paneer curry, salad.
- For each item, estimate edible grams, preparation style, visible ingredients, and confidence.
- Do not invent hidden ingredients. Put possible hidden ingredients only in the uncertainty note.
- If the image is not food, return an empty detected_foods list and explain why.
""".strip()

    response = client.models.generate_content(
        model=model,
        contents=[prompt, image],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=FoodAnalysis,
        ),
    )

    if getattr(response, "parsed", None):
        analysis = FoodAnalysis.model_validate(response.parsed)
    elif response.text:
        analysis = FoodAnalysis.model_validate_json(response.text)
    else:
        raise RuntimeError("Gemini returned an empty response.")

    if not analysis.detected_foods:
        raise ValueError("No food was confidently detected in the image. Try a clearer photo.")
    return analysis
