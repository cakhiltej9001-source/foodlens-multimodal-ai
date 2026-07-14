from src.nutrition_service import food_match_score, scale_nutrients


def test_scale_nutrients_for_150_grams():
    result = scale_nutrients({"calories_kcal": 100, "protein_g": 8}, 150)
    assert result["calories_kcal"] == 150
    assert result["protein_g"] == 12


def test_match_score_prefers_related_description():
    related = food_match_score("brown rice", "Rice, brown, long-grain, cooked")
    unrelated = food_match_score("brown rice", "Ice cream, vanilla")
    assert related > unrelated
