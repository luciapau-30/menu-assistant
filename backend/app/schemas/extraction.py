from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class ExtractedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ShortText
    # Only ingredients explicitly visible in the image. No recipe guesses.
    ingredients: list[ShortText] = Field(max_length=60)
    source_text: str = Field(max_length=4000)


class Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ExtractedItem] = Field(min_length=1, max_length=30)
    warnings: list[ShortText] = Field(default_factory=list, max_length=30)


class ReviewedItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ShortText
    ingredients: list[ShortText] = Field(min_length=1, max_length=60)


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ReviewedItem] = Field(min_length=1, max_length=30)

