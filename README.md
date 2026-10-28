# Piece of Mind

**Snap a photo of a restaurant menu and find out which dishes are safe for you before you order.**

Piece of Mind reads a menu, nutrition label or ingredient list with a vision model, lets you review what it extracted, and scores each dish against your allergies, medical restrictions and nutrition goals. I have celiac disease, and figuring out what I can eat away from home has always been stressful. This is the tool I wanted.

> **Status:** working backend and browser demo, 22 automated tests passing. Not deployed to production yet. See [what's next](#whats-next).

## How it works

```
 menu photo ──► LLM vision extraction ──► user reviews ingredients ──► compatibility scoring ──► saved report
                (Groq, versioned prompt)   (fixes mistakes before        (deterministic rules +
                                            anything is scored)           Edamam ingredient data)
```

1. **Extract.** A Groq vision model pulls out menu items and only the ingredients that are explicitly listed. It's told not to guess recipes.
2. **Review.** The user confirms or edits the extracted ingredients. The model never decides safety on its own.
3. **Score.** Each ingredient is looked up in Edamam (with a database cache) and checked against the user's profile:
   - Any allergen or medical-restriction conflict → score **0**, with the offending ingredients listed
   - Unknown ingredients or missing data → **"Not fully assessed"** instead of a falsely confident score
   - Otherwise → averaged nutrition-goal scores based on nutrient density
4. **Report.** You get a safety score, goal scores, confidence, warnings, suggested ingredient removals, and questions to ask restaurant staff about anything unknown.

The key design choice: **an LLM reads the menu, but deterministic code decides what's safe.** That keeps safety decisions explainable and testable.

## Engineering highlights

- **Layered FastAPI backend:** routes → services → models/schemas, with SQLAlchemy 2.0 and Alembic migrations on PostgreSQL
- **Auth:** Argon2 password hashing and JWT bearer tokens; every analysis is scoped to its owner
- **LLM evaluation harness** (`backend/evals/`): runs the extraction prompt against labeled fixture images and measures exact match, ingredient precision/recall, invented ingredients, latency and token usage
- **Resilient external calls:** ingredient lookups are cached, failed lookups stay retryable instead of being cached as misses, and AI-generated questions fall back to deterministic ones if the model fails
- **Isolated tests:** SQLite plus mocked providers, so the suite never touches real credentials or your dev database

## Tech stack

Python · FastAPI · PostgreSQL · SQLAlchemy · Alembic · Pydantic · Groq (Llama / vision) · Edamam API · Argon2 · JWT

## Run it locally

Requires Python 3.10+ and a PostgreSQL database.

```sh
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/piece_of_mind
JWT_SECRET_KEY=REPLACE_WITH_A_RANDOM_SECRET
EDAMAM_APP_ID=YOUR_APP_ID
EDAMAM_APP_KEY=YOUR_APP_KEY
GROQ_API_KEY=YOUR_API_KEY
```

```sh
alembic upgrade head
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/app/ for the demo, or http://127.0.0.1:8000/docs for the interactive API explorer.

**Tests** (from `backend/`):

```sh
python -m unittest discover -s tests -t . -v
```

## Documentation

| Doc | What's in it |
| --- | --- |
| [Overview & current status](docs/README.md) | Full feature list, scoring rules, endpoints, eval instructions |
| [Features](docs/02_FEATURES.md) | Product requirements |
| [Architecture](docs/03_ARCHITECTURE.md) | System design |
| [Database](docs/04_DATABASE.md) | Schema |
| [API](docs/05_API.md) | Endpoint reference |

## What's next

- A production frontend (the current UI is a lightweight demo)
- Background job queue so long extractions survive restarts
- Ranking a whole menu at once
- Scoring for dietary styles (vegan, keto, etc.), budget and preferences
- A larger eval set with real restaurant photos, blur and multilingual menus

## License

MIT
