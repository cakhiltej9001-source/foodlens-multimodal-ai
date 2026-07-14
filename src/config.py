from __future__ import annotations

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    gemini_api_key: str = Field(default="")
    usda_api_key: str = Field(default="DEMO_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash")
    database_path: str = Field(default="data/foodlens.db")
