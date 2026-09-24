import os

import httpx
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"


class GroqLookupError(Exception):
    """
    Raised whenever a Groq call fails for any reason (rate limit, timeout,
    network error, 5xx, malformed response). Per the "AI as an Enhancement"
    / Progressive Enhancement principles in docs/03_ARCHITECTURE.md, callers
    must catch this and fall back to non-AI behavior rather than let it
    propagate -- the app must keep working if the LLM is unavailable.
    """


def generate_chat_completion(system_prompt: str, user_prompt: str) -> str:
    if not GROQ_API_KEY:
        raise GroqLookupError("GROQ_API_KEY is not configured")
    try:
        response = httpx.post(
            CHAT_COMPLETIONS_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as exc:
        raise GroqLookupError(str(exc)) from exc
