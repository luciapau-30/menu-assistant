from pydantic import BaseModel, model_validator

CATEGORY_FIELDS = [
    "allergens",
    "medical_restrictions",
    "dietary_styles",
    "nutrition_goals",
]


class ProfileUpdate(BaseModel):
    allergens: list[str] = []
    medical_restrictions: list[str] = []
    dietary_styles: list[str] = []
    nutrition_goals: list[str] = []

    @model_validator(mode="after")
    def validate_selections(self):
        categories = {field: getattr(self, field) for field in CATEGORY_FIELDS}

        if not any(categories.values()):
            raise ValueError(
                "At least one selection is required across your profile"
            )

        for field, items in categories.items():
            if "None" in items and len(items) > 1:
                raise ValueError(
                    f"'None' cannot be combined with other selections in {field}"
                )

        return self


class ProfileResponse(BaseModel):
    name: str
    allergens: list[str]
    medical_restrictions: list[str]
    dietary_styles: list[str]
    nutrition_goals: list[str]
