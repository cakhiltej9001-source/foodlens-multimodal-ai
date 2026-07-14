from __future__ import annotations

import json
import os
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError

from src.config import AppConfig
from src.database import init_db, list_recent_analyses, save_analysis
from src.models import DetectedFood, FoodAnalysis
from src.nutrition_service import build_nutrition_report
from src.recipe_service import generate_recipes
from src.utils import compress_image, nutrition_totals, safe_json
from src.vision_service import analyze_food_image

load_dotenv()

st.set_page_config(
    page_title="FoodLens AI",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 3rem;}
.hero {
    padding: 1.2rem 1.4rem;
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(255,153,0,.16), rgba(46,204,113,.12));
    border: 1px solid rgba(120,120,120,.22);
    margin-bottom: 1rem;
}
.hero h1 {margin: 0 0 .25rem 0;}
.hero p {margin: 0; opacity: .82;}
.small-muted {opacity: .72; font-size: .9rem;}
.warning-card {
    border-left: 4px solid #f39c12;
    padding: .8rem 1rem;
    background: rgba(243,156,18,.08);
    border-radius: 8px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def get_secret(name: str, default: str = "") -> str:
    """Read a value from Streamlit secrets first, then environment variables."""
    try:
        value = st.secrets.get(name, "")
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def load_config() -> AppConfig:
    return AppConfig(
        gemini_api_key=get_secret("GEMINI_API_KEY"),
        usda_api_key=get_secret("USDA_API_KEY", "DEMO_KEY"),
        gemini_model=get_secret("GEMINI_MODEL", "gemini-2.5-flash"),
        database_path=get_secret("DATABASE_PATH", "data/foodlens.db"),
    )


def clear_results() -> None:
    for key in ["analysis", "nutrition_rows", "recipes", "image_bytes", "image_name"]:
        st.session_state.pop(key, None)


config = load_config()
init_db(config.database_path)

st.markdown(
    """
    <div class="hero">
      <h1>🍽️ FoodLens AI</h1>
      <p>Upload or photograph a meal to detect foods, estimate nutrition from USDA FoodData Central, and generate personalized recipes.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ Settings")
    model_name = st.text_input("Gemini model", value=config.gemini_model)
    dietary_preference = st.selectbox(
        "Dietary preference",
        ["No preference", "Vegetarian", "Vegan", "High-protein", "Gluten-free", "Low-sodium"],
    )
    target_cuisine = st.selectbox(
        "Recipe style",
        ["Any", "Indian", "South Indian", "Mediterranean", "Asian", "Continental", "Healthy fusion"],
    )
    recipe_count = st.slider("Number of recipes", 1, 4, 3)
    st.divider()
    st.caption("API status")
    st.write("✅ Gemini key detected" if config.gemini_api_key else "❌ Gemini key missing")
    st.write("✅ USDA key detected" if config.usda_api_key else "❌ USDA key missing")
    if config.usda_api_key == "DEMO_KEY":
        st.caption("Using USDA DEMO_KEY. Add your free key for higher limits.")
    st.divider()
    if st.button("🧹 Clear current result", use_container_width=True):
        clear_results()
        st.rerun()

input_tab, camera_tab = st.tabs(["📤 Upload image", "📷 Use camera"])
with input_tab:
    uploaded = st.file_uploader(
        "Choose a food image",
        type=["jpg", "jpeg", "png", "webp"],
        help="Use a clear, well-lit image. Maximum recommended size: 10 MB.",
    )
with camera_tab:
    captured = st.camera_input("Take a picture of your meal")

image_file = captured or uploaded

if image_file is not None:
    try:
        raw_bytes = image_file.getvalue()
        image = Image.open(BytesIO(raw_bytes)).convert("RGB")
        compressed = compress_image(image, max_side=1600, quality=88)
        st.session_state.image_bytes = compressed
        st.session_state.image_name = getattr(image_file, "name", "camera_capture.jpg")
        preview_col, info_col = st.columns([1.25, 1])
        with preview_col:
            st.image(compressed, caption="Selected food image", use_container_width=True)
        with info_col:
            st.subheader("Ready to analyze")
            st.write(f"Image size: **{image.width} × {image.height} px**")
            st.write(f"Compressed request size: **{len(compressed) / 1024:.1f} KB**")
            st.markdown(
                '<div class="warning-card">Nutrition values are estimates, not medical advice. Portion size and hidden ingredients may be misidentified.</div>',
                unsafe_allow_html=True,
            )
            analyze_clicked = st.button(
                "🔍 Analyze food",
                type="primary",
                use_container_width=True,
                disabled=not bool(config.gemini_api_key),
            )

        if analyze_clicked:
            clear_results()
            st.session_state.image_bytes = compressed
            st.session_state.image_name = getattr(image_file, "name", "camera_capture.jpg")
            try:
                with st.status("Running multimodal analysis…", expanded=True) as status:
                    st.write("1. Sending the image to Gemini Vision")
                    analysis = analyze_food_image(
                        image_bytes=compressed,
                        api_key=config.gemini_api_key,
                        model=model_name.strip() or config.gemini_model,
                    )
                    st.write("2. Matching detected foods with USDA FoodData Central")
                    nutrition_rows = build_nutrition_report(
                        foods=analysis.detected_foods,
                        api_key=config.usda_api_key,
                    )
                    st.write("3. Generating recipe recommendations")
                    recipes = generate_recipes(
                        analysis=analysis,
                        api_key=config.gemini_api_key,
                        model=model_name.strip() or config.gemini_model,
                        dietary_preference=dietary_preference,
                        cuisine=target_cuisine,
                        recipe_count=recipe_count,
                    )
                    status.update(label="Analysis complete", state="complete", expanded=False)

                st.session_state.analysis = analysis.model_dump()
                st.session_state.nutrition_rows = [row.model_dump() for row in nutrition_rows]
                st.session_state.recipes = recipes.model_dump()
                save_analysis(
                    db_path=config.database_path,
                    image_name=st.session_state.image_name,
                    analysis=st.session_state.analysis,
                    nutrition=st.session_state.nutrition_rows,
                    recipes=st.session_state.recipes,
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Analysis failed: {exc}")
                st.info("Check your API key, model name, internet connection, and API quota. Then try again.")
    except UnidentifiedImageError:
        st.error("The selected file is not a valid image.")
    except Exception as exc:
        st.error(f"Could not load the image: {exc}")
else:
    st.info("Upload an image or take a camera photo to begin.")

if "analysis" in st.session_state:
    analysis = FoodAnalysis.model_validate(st.session_state.analysis)
    nutrition_rows = st.session_state.get("nutrition_rows", [])
    recipes_data = st.session_state.get("recipes", {"recipes": []})

    st.divider()
    st.header("Results")
    overview_tab, nutrition_tab, recipes_tab, json_tab = st.tabs(
        ["🧠 Detection", "📊 Nutrition", "👩‍🍳 Recipes", "🧾 JSON"]
    )

    with overview_tab:
        metric_cols = st.columns(4)
        metric_cols[0].metric("Dish", analysis.dish_name)
        metric_cols[1].metric("Cuisine", analysis.cuisine)
        metric_cols[2].metric("Detected items", len(analysis.detected_foods))
        metric_cols[3].metric("Confidence", f"{analysis.overall_confidence * 100:.0f}%")
        st.write(analysis.description)

        food_df = pd.DataFrame([food.model_dump() for food in analysis.detected_foods])
        food_df = food_df.rename(
            columns={
                "name": "Food item",
                "estimated_grams": "Estimated grams",
                "confidence": "Confidence",
                "preparation": "Preparation",
                "visible_ingredients": "Visible ingredients",
            }
        )
        food_df["Confidence"] = (food_df["Confidence"] * 100).round(0).astype(int).astype(str) + "%"
        st.dataframe(food_df, use_container_width=True, hide_index=True)

        if analysis.allergens:
            st.warning("Possible allergens: " + ", ".join(analysis.allergens))
        if analysis.dietary_tags:
            st.write("Dietary tags: " + " · ".join(analysis.dietary_tags))
        st.caption(analysis.uncertainty_note)

        with st.expander("✏️ Correct detected foods and recalculate nutrition"):
            editable_df = pd.DataFrame(
                [
                    {"Food item": f.name, "Estimated grams": float(f.estimated_grams)}
                    for f in analysis.detected_foods
                ]
            )
            edited = st.data_editor(
                editable_df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Food item": st.column_config.TextColumn(required=True),
                    "Estimated grams": st.column_config.NumberColumn(min_value=1.0, max_value=3000.0, step=5.0),
                },
            )
            if st.button("Recalculate from USDA", use_container_width=True):
                corrected_foods = [
                    DetectedFood(
                        name=str(row["Food item"]).strip(),
                        estimated_grams=float(row["Estimated grams"]),
                        confidence=1.0,
                        preparation="User corrected",
                        visible_ingredients=[],
                    )
                    for _, row in edited.dropna().iterrows()
                    if str(row.get("Food item", "")).strip()
                ]
                try:
                    with st.spinner("Recalculating nutrition…"):
                        corrected_rows = build_nutrition_report(corrected_foods, config.usda_api_key)
                    st.session_state.nutrition_rows = [r.model_dump() for r in corrected_rows]
                    st.success("Nutrition recalculated.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not recalculate: {exc}")

    with nutrition_tab:
        if not nutrition_rows:
            st.warning("No nutrition matches were returned. Try editing the detected food names.")
        else:
            totals = nutrition_totals(nutrition_rows)
            cols = st.columns(7)
            labels = [
                ("Calories", "calories_kcal", "kcal"),
                ("Protein", "protein_g", "g"),
                ("Carbs", "carbs_g", "g"),
                ("Fat", "fat_g", "g"),
                ("Fiber", "fiber_g", "g"),
                ("Sugar", "sugar_g", "g"),
                ("Sodium", "sodium_mg", "mg"),
            ]
            for col, (label, key, unit) in zip(cols, labels):
                col.metric(label, f"{totals.get(key, 0):.1f} {unit}")

            nutrition_df = pd.DataFrame(nutrition_rows)
            shown_columns = [
                "item_name", "matched_food", "estimated_grams", "calories_kcal",
                "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g",
                "sodium_mg", "match_score", "data_type"
            ]
            nutrition_df = nutrition_df[[c for c in shown_columns if c in nutrition_df.columns]]
            nutrition_df = nutrition_df.rename(
                columns={
                    "item_name": "Detected item",
                    "matched_food": "USDA match",
                    "estimated_grams": "Grams",
                    "calories_kcal": "Calories (kcal)",
                    "protein_g": "Protein (g)",
                    "carbs_g": "Carbs (g)",
                    "fat_g": "Fat (g)",
                    "fiber_g": "Fiber (g)",
                    "sugar_g": "Sugar (g)",
                    "sodium_mg": "Sodium (mg)",
                    "match_score": "Match score",
                    "data_type": "USDA data type",
                }
            )
            if "Match score" in nutrition_df.columns:
                nutrition_df["Match score"] = (nutrition_df["Match score"] * 100).round(0).astype(int).astype(str) + "%"
            st.dataframe(nutrition_df, use_container_width=True, hide_index=True)
            st.caption("USDA nutrient values are scaled from the matched reference food using the AI-estimated portion weight.")

    with recipes_tab:
        recipe_list = recipes_data.get("recipes", [])
        if not recipe_list:
            st.warning("No recipes were generated.")
        for idx, recipe in enumerate(recipe_list, start=1):
            with st.expander(f"{idx}. {recipe['name']}", expanded=idx == 1):
                st.write(recipe.get("description", ""))
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Servings", recipe.get("servings", "—"))
                c2.metric("Prep", f"{recipe.get('prep_time_minutes', 0)} min")
                c3.metric("Cook", f"{recipe.get('cook_time_minutes', 0)} min")
                c4.metric("Difficulty", recipe.get("difficulty", "—"))
                st.subheader("Ingredients")
                for ingredient in recipe.get("ingredients", []):
                    st.markdown(f"- {ingredient}")
                st.subheader("Steps")
                for step_no, step in enumerate(recipe.get("steps", []), start=1):
                    st.markdown(f"**{step_no}.** {step}")
                if recipe.get("nutrition_note"):
                    st.info(recipe["nutrition_note"])

    with json_tab:
        export = {
            "analysis": st.session_state.analysis,
            "nutrition": st.session_state.nutrition_rows,
            "recipes": st.session_state.recipes,
        }
        st.json(export)
        st.download_button(
            "⬇️ Download result JSON",
            data=json.dumps(safe_json(export), indent=2, ensure_ascii=False),
            file_name="foodlens_result.json",
            mime="application/json",
        )

with st.expander("🕘 Recent local analyses"):
    history = list_recent_analyses(config.database_path, limit=10)
    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        st.caption("No saved analyses yet.")

st.divider()
st.caption(
    "FoodLens AI is an educational portfolio project. Food recognition, serving sizes, allergens, and nutrition can be inaccurate. "
    "Do not use it for diagnosis, allergy safety decisions, or medical nutrition planning."
)
