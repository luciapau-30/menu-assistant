import json

from app.llm.groq_client import GroqLookupError, generate_chat_completion

SYSTEM_PROMPT = (
    "You are a food safety assistant helping a restaurant customer. Given "
    "a menu item, a list of ingredients that could not be identified, and "
    "the user's specific allergens/dietary restrictions, write short, "
    "natural questions the user could ask restaurant staff to verify "
    "safety. Only ask about the unidentified ingredients listed and the "
    "user's stated concerns -- never invent ingredients or concerns that "
    "were not given to you. Respond with ONLY a JSON array of strings, "
    "no other text, no markdown formatting."
)


def generate_questions_with_llm(
    menu_item_name: str,
    unknown_ingredients: list[str],
    user_concerns: list[str],
) -> list[str] | None:
    """
    Generates restaurant questions for unidentified ingredients using
    Groq/Llama. Returns None (never raises) if the LLM call fails or
    returns something we can't trust, so callers can fall back to the
    deterministic question generator in app/compatibility/safety.py.
    """
    if not unknown_ingredients:
        return []

    user_prompt = (
        f"Menu item: {menu_item_name}\n"
        f"Unidentified ingredients: {', '.join(unknown_ingredients)}\n"
        "User's allergens/restrictions: "
        + (", ".join(user_concerns) if user_concerns else "none specified")
    )

    try:
        raw_response = generate_chat_completion(SYSTEM_PROMPT, user_prompt)
        questions = json.loads(raw_response)
    except (GroqLookupError, json.JSONDecodeError, TypeError):
        return None

    if not isinstance(questions, list) or not questions or not all(
        isinstance(q, str) and q.strip() for q in questions
    ):
        return None

    return questions
