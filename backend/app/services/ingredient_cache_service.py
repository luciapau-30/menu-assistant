from sqlalchemy.orm import Session

from app.compatibility.edamam_client import EdamamLookupError, lookup_ingredient
from app.models.ingredient_cache import IngredientCache


def get_or_fetch(db: Session, ingredient_name: str) -> IngredientCache:
    normalized_name = ingredient_name.strip().lower()

    cached = (
        db.query(IngredientCache)
        .filter(IngredientCache.ingredient_name == normalized_name)
        .first()
    )

    if cached is not None:
        return cached

    try:
        result = lookup_ingredient(normalized_name)
    except EdamamLookupError:
        # Transient failure (rate limit, timeout, network, 5xx) -- do not
        # persist this as a permanent "not found", just report it as
        # unavailable for this request and let the next lookup retry.
        return IngredientCache(
            ingredient_name=normalized_name,
            found=False,
            health_labels=[],
            nutrients={},
        )

    cache_entry = IngredientCache(
        ingredient_name=normalized_name,
        found=result is not None,
        health_labels=result["health_labels"] if result else [],
        nutrients=result["nutrients"] if result else {},
    )

    db.add(cache_entry)
    db.commit()
    db.refresh(cache_entry)

    return cache_entry
