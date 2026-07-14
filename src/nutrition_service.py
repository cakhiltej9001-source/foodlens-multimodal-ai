from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.models import DetectedFood, NutritionRow

USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

NUTRIENT_NUMBERS = {
    "calories_kcal": "1008",
    "protein_g": "1003",
    "fat_g": "1004",
    "carbs_g": "1005",
    "fiber_g": "1079",
    "sugar_g": "2000",
    "sodium_mg": "1093",
}

NUTRIENT_NAME_FALLBACKS = {
    "calories_kcal": ["energy"],
    "protein_g": ["protein"],
    "fat_g": ["total lipid (fat)", "total fat"],
    "carbs_g": ["carbohydrate, by difference", "carbohydrate"],
    "fiber_g": ["fiber, total dietary", "dietary fiber"],
    "sugar_g": ["sugars, total including nlea", "sugars, total"],
    "sodium_mg": ["sodium, na", "sodium"],
}


def _session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "FoodLensAI/1.0 (educational project)"})
    return session


def _normalize(text: str) -> str:
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    return " ".join(text.split())


def food_match_score(query: str, candidate: str) -> float:
    q = _normalize(query)
    c = _normalize(candidate)
    if not q or not c:
        return 0.0
    sequence = SequenceMatcher(None, q, c).ratio()
    q_tokens, c_tokens = set(q.split()), set(c.split())
    overlap = len(q_tokens & c_tokens) / max(len(q_tokens), 1)
    starts = 1.0 if c.startswith(q) or q.startswith(c) else 0.0
    return max(0.0, min(1.0, 0.50 * sequence + 0.40 * overlap + 0.10 * starts))


def search_usda_food(query: str, api_key: str) -> dict[str, Any] | None:
    if not api_key:
        raise ValueError("USDA_API_KEY is missing.")

    payload = {
        "query": query,
        "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
        "pageSize": 12,
        "pageNumber": 1,
        "sortBy": "dataType.keyword",
        "sortOrder": "asc",
    }
    response = _session().post(
        USDA_SEARCH_URL,
        params={"api_key": api_key},
        json=payload,
        timeout=20,
    )
    if response.status_code == 429:
        raise RuntimeError("USDA API rate limit reached. Add your own free USDA API key or retry later.")
    response.raise_for_status()
    foods = response.json().get("foods", [])
    if not foods:
        return None

    priority = {"Foundation": 0.06, "SR Legacy": 0.05, "Survey (FNDDS)": 0.04}
    ranked = []
    for food in foods:
        description = food.get("description", "")
        score = food_match_score(query, description) + priority.get(food.get("dataType", ""), 0)
        ranked.append((score, food))
    ranked.sort(key=lambda item: item[0], reverse=True)
    best_score, best_food = ranked[0]
    best_food["_match_score"] = min(best_score, 1.0)
    return best_food


def _nutrient_value(food: dict[str, Any], key: str) -> float:
    nutrients = food.get("foodNutrients", []) or []
    target_number = NUTRIENT_NUMBERS[key]

    # Prefer the stable USDA nutrient number.
    for nutrient in nutrients:
        if str(nutrient.get("nutrientNumber", "")) == target_number:
            value = float(nutrient.get("value") or 0)
            unit = str(nutrient.get("unitName", "")).upper()
            if key == "calories_kcal" and unit == "KJ":
                return value / 4.184
            return value

    # Fall back to names because some responses omit nutrient numbers.
    fallback_names = NUTRIENT_NAME_FALLBACKS[key]
    for nutrient in nutrients:
        name = str(nutrient.get("nutrientName", "")).lower().strip()
        if any(name == candidate or name.startswith(candidate) for candidate in fallback_names):
            value = float(nutrient.get("value") or 0)
            unit = str(nutrient.get("unitName", "")).upper()
            if key == "calories_kcal" and unit == "KJ":
                return value / 4.184
            return value
    return 0.0


def scale_nutrients(per_100g: dict[str, float], grams: float) -> dict[str, float]:
    factor = max(float(grams), 0.0) / 100.0
    return {key: round(float(value) * factor, 2) for key, value in per_100g.items()}


def build_nutrition_report(foods: list[DetectedFood], api_key: str) -> list[NutritionRow]:
    rows: list[NutritionRow] = []
    for item in foods:
        match = search_usda_food(item.name, api_key)
        if not match:
            rows.append(
                NutritionRow(
                    item_name=item.name,
                    matched_food="No USDA match",
                    estimated_grams=item.estimated_grams,
                    match_score=0,
                )
            )
            continue

        per_100g = {key: _nutrient_value(match, key) for key in NUTRIENT_NUMBERS}
        scaled = scale_nutrients(per_100g, item.estimated_grams)
        rows.append(
            NutritionRow(
                item_name=item.name,
                matched_food=match.get("description", "Unknown food"),
                fdc_id=match.get("fdcId"),
                estimated_grams=item.estimated_grams,
                match_score=float(match.get("_match_score", 0)),
                data_type=match.get("dataType", "Unknown"),
                **scaled,
            )
        )
    return rows
