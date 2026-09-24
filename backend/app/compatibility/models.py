from dataclasses import dataclass, field


@dataclass
class MenuItemInput:
    name: str
    ingredients: list[str]


@dataclass
class UserProfileInput:
    allergens: list[str] = field(default_factory=list)
    medical_restrictions: list[str] = field(default_factory=list)
    dietary_styles: list[str] = field(default_factory=list)
    nutrition_goals: list[str] = field(default_factory=list)


@dataclass
class SafetyResult:
    safety_score: int | None
    confidence: str  # "High" | "Medium" | "Low"
    detected_allergens: list[str] = field(default_factory=list)
    detected_restrictions: list[str] = field(default_factory=list)
    unknown_ingredients: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggested_modifications: list[str] = field(default_factory=list)
    questions_to_ask: list[str] = field(default_factory=list)


@dataclass
class GoalResult:
    goal_scores: dict[str, int] = field(default_factory=dict)
    unassessed_goals: list[str] = field(default_factory=list)
    unknown_ingredients: list[str] = field(default_factory=list)


@dataclass
class CompatibilityResult:
    compatibility_score: int | None
    safety_score: int | None
    goal_score: int | None  # average across selected goals, None if none selected
    confidence: str
    detected_allergens: list[str] = field(default_factory=list)
    detected_restrictions: list[str] = field(default_factory=list)
    goal_scores: dict[str, int] = field(default_factory=dict)
    unassessed_goals: list[str] = field(default_factory=list)
    unknown_ingredients: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggested_modifications: list[str] = field(default_factory=list)
    questions_to_ask: list[str] = field(default_factory=list)
