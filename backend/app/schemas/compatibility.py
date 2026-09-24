from pydantic import BaseModel, Field
from app.schemas.extraction import ShortText


class CompatibilityCheckRequest(BaseModel):
    menu_item_name: ShortText
    ingredients: list[ShortText] = Field(min_length=1, max_length=60)


class CompatibilityCheckResponse(BaseModel):
    menu_item_name: str
    ingredients: list[str] = Field(default_factory=list)
    compatibility_score: int | None
    safety_score: int | None
    goal_score: int | None
    confidence: str
    detected_allergens: list[str]
    detected_restrictions: list[str]
    goal_scores: dict[str, int]
    unassessed_goals: list[str]
    unknown_ingredients: list[str]
    warnings: list[str]
    suggested_modifications: list[str]
    questions_to_ask: list[str]
