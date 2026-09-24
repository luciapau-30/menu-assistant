import os

import httpx
from dotenv import load_dotenv

load_dotenv()

EDAMAM_APP_ID = os.getenv("EDAMAM_APP_ID")
EDAMAM_APP_KEY = os.getenv("EDAMAM_APP_KEY")

PARSER_URL = "https://api.edamam.com/api/food-database/v2/parser"
NUTRIENTS_URL = "https://api.edamam.com/api/food-database/v2/nutrients"

# "Gram" is documented by Edamam as a universally supported measure for
# any food, so requesting a fixed 100g avoids depending on whether a food
# happens to have its own default measure (some, like oils, don't).
GRAM_MEASURE_URI = "http://www.edamam.com/ontologies/edamam.owl#Measure_gram"


class EdamamLookupError(Exception):
    """
    Raised when a call to Edamam fails for a transient reason (rate limit,
    timeout, network error, 5xx) as opposed to Edamam successfully
    responding that it has no match for this ingredient. Callers should
    NOT treat this the same as "ingredient not found" -- in particular,
    it should never be cached as a permanent not-found result.
    """


def _search_food(name: str) -> str | None:
    try:
        response = httpx.get(
            PARSER_URL,
            params={"ingr": name, "app_id": EDAMAM_APP_ID, "app_key": EDAMAM_APP_KEY},
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise EdamamLookupError(str(exc)) from exc

    data = response.json()

    # Only trust "parsed" -- Edamam's own confident interpretation of the
    # query. "hints" are broader fuzzy-search suggestions (e.g. a made-up
    # ingredient name can still match something via hints); treating those
    # as a confirmed match risks reporting false safety on ingredients we
    # don't actually know anything about, so we deliberately do not fall
    # back to them.
    parsed = data.get("parsed") or []
    if parsed:
        return parsed[0]["food"]["foodId"]

    return None


def _get_nutrition(food_id: str) -> dict:
    try:
        response = httpx.post(
            NUTRIENTS_URL,
            params={"app_id": EDAMAM_APP_ID, "app_key": EDAMAM_APP_KEY},
            json={
                "ingredients": [
                    {"quantity": 100, "measureURI": GRAM_MEASURE_URI, "foodId": food_id}
                ]
            },
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise EdamamLookupError(str(exc)) from exc

    data = response.json()

    total_weight = data.get("totalWeight") or 0
    raw_nutrients = {
        code: values["quantity"]
        for code, values in data.get("totalNutrients", {}).items()
    }

    # Should already be ~100g since we requested it directly, but normalize
    # defensively using the actual weight Edamam computed just in case.
    nutrients_per_100g = (
        {code: (quantity / total_weight) * 100 for code, quantity in raw_nutrients.items()}
        if total_weight > 0
        else {}
    )

    return {
        "health_labels": data.get("healthLabels", []),
        "nutrients": nutrients_per_100g,
    }


def lookup_ingredient(name: str) -> dict | None:
    """
    Look up a single ingredient by name against the Edamam Food Database.
    Returns {"health_labels": [...], "nutrients": {...}}, or None if Edamam
    has no confident match for this name.
    """
    if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:
        raise EdamamLookupError("Edamam credentials are not configured")
    try:
        food_id = _search_food(name)
        if food_id is None:
            return None
        return _get_nutrition(food_id)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise EdamamLookupError("Malformed ingredient response") from exc
