# Piece of Mind

## Mission

Piece of Mind empowers people to make confident food decisions by analyzing restaurant menus and nutrition labels against their personal dietary profile. Rather than telling users what they *should* eat, the platform evaluates each food item's **compatibility** with a user's allergies, dietary restrictions, nutrition goals, budget, and personal preferences.

Our goal is to reduce uncertainty before someone orders or purchases food by providing transparent **Compatibility Reports** and actionable insights.

---

## Problem Statement

Millions of people live with food allergies, celiac disease, dietary restrictions, or specific nutrition goals. Unfortunately, restaurant menus often provide incomplete ingredient, allergen, or nutrition information, making it difficult to determine whether a meal is **compatible** with their individual needs.

Existing nutrition applications primarily focus on tracking food *after* it has been consumed. Piece of Mind focuses on helping users evaluate **meal compatibility before they order**.

---

## Current Implementation

The project currently contains a Python/FastAPI backend with SQLAlchemy models, PostgreSQL support, and Alembic database migrations. A small browser demo is served at `/app/`, and an isolated automated test suite covers scoring, authentication, uploads, extraction failures, review, and saved reports. The status below reflects the code as of September 23, 2026; it does not imply production deployment. External providers are mocked in automated API tests; live extraction evaluation is separate.

### Implemented in the Backend

* **Accounts and authentication:** registration, login, Argon2 password hashing, JWT access tokens, and an authenticated current-user endpoint.
* **Dietary profiles:** read and update allergens, medical restrictions, dietary styles, and nutrition goals. Selections are validated against database lookup tables, including an explicit `None` option.
* **Image uploads:** accept menu, nutrition-label, and ingredient-list images, save them locally, and create user-owned analysis records. Users can retrieve the status of their own uploads.
* **Ingredient-based compatibility checks:** accept a single menu item name and an explicit ingredient list, then evaluate them against the authenticated user's profile.
* **Ingredient data and caching:** retrieve health labels and nutrient data from Edamam and cache results in the database. Handled lookup failures remain retryable rather than being cached as permanent misses.
* **Compatibility reports:** return overall, safety, and goal scores; confidence; potential allergen and medical-restriction conflicts; unknown ingredients; unassessed goals; warnings; suggested ingredient removals; and questions to ask restaurant staff.
* **Nutrition-goal scoring:** use ingredient nutrient density per 100 g for High Protein, Muscle Gain, Low Carb, and Weight Loss. Weight Maintenance is marked unassessed because ingredient composition cannot assess daily calorie balance.
* **AI-assisted questions:** use Groq/Llama to phrase restaurant questions about unknown ingredients, with deterministic questions as a fallback for handled failures or invalid output.
* **Image extraction and review:** use a configurable Groq vision model to extract explicitly listed ingredients and source text. Users review or manually enter ingredients before scoring; recipe ingredients are not intentionally inferred.
* **Saved reports:** persist reviewed ingredients, compatibility results, and the profile used for each completed analysis.
* **Browser demo:** sign up/log in, edit a profile, upload and review images, generate reports, and reopen an analysis by its ID.
* **Database migrations:** define users, profile lookup tables and relationships, analysis records/results, and the ingredient cache.

### How the Current Flow Works

1. Open `/app/`, register or log in, and save dietary profile selections.
2. Upload a PNG, JPEG, or WebP image (maximum 4 MiB).
3. Extract menu items and explicitly listed ingredients, then review and correct them. If extraction fails, retry or enter ingredients manually.
4. Generate reports from the reviewed ingredients. Completed reports and a profile snapshot are saved and can be reopened by analysis ID.

The API also supports a direct single-item check without uploading an image. Extraction and report generation are synchronous requests. `UPLOADED` with an extraction payload means awaiting review; `PROCESSING` means work is in progress; `COMPLETED` contains saved reports; `FAILED` contains a retryable error. Completed analyses are immutable; upload again to analyze a revised profile or menu.

### Current Scoring Boundaries

* A detected allergen or medical-restriction conflict sets the overall compatibility score to **0**. Incomplete checks return `null` (displayed as “Not fully assessed”), not a perfect score. With complete data, the score is the average of nutrition-goal scores, or **100** when no goals were selected.
* Unknown ingredients, missing nutrient data for a selected goal, and unsupported profile selections prevent an overall score unless a conflict already warrants 0. Partial goal scores remain visible. Confidence describes ingredient lookup coverage, not AI extraction accuracy or a guarantee of safety.
* Nutrition scoring uses the fraction of assessed ingredients that meet each goal's thresholds. It does not account for portion sizes or estimate total dish calories and macros.
* Dietary styles are stored but not yet scored; selecting one produces an explicit warning and an incomplete assessment. Budget and additional personal preferences are not yet implemented.
* Direct `/compatibility/check` results are not saved; reviewed upload reports are saved through the analysis report endpoint.

### Available Endpoints

All endpoints except the root, registration, and login require bearer authentication.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Basic API running message |
| POST | `/api/v1/auth/register` | Create an account |
| POST | `/api/v1/auth/login` | Obtain an access token |
| GET | `/api/v1/auth/me` | Read the current user |
| GET | `/api/v1/profile` | Read the dietary profile |
| GET | `/api/v1/profile/options` | List available profile selections |
| PUT | `/api/v1/profile` | Replace profile selections |
| POST | `/api/v1/analysis/upload` | Upload an image and create an analysis record |
| GET | `/api/v1/analysis/{analysis_id}` | Read status, extraction, reports, and profile snapshot |
| POST | `/api/v1/analysis/{analysis_id}/extract` | Extract image content for review |
| POST | `/api/v1/analysis/{analysis_id}/report` | Score reviewed items and save reports |
| POST | `/api/v1/compatibility/check` | Evaluate a supplied menu item and ingredient list |

The backend reads configuration from environment variables or `.env`: `DATABASE_URL`, `JWT_SECRET_KEY`, `EDAMAM_APP_ID`, `EDAMAM_APP_KEY`, and `GROQ_API_KEY`. `DATABASE_URL` and `JWT_SECRET_KEY` are required at startup. Missing Edamam credentials produce unknown ingredients; missing Groq credentials disable extraction and use fallback restaurant questions. Set `GROQ_VISION_MODEL` to override the default `qwen/qwen3.8-27b`, selected from [Groq’s vision documentation](https://console.groq.com/docs/vision). Optional JWT settings are `JWT_ALGORITHM` (default `HS256`) and `JWT_EXPIRE_MINUTES` (default `60`).

### Run Locally

Use Python 3.10+ and an existing PostgreSQL database. From the repository root:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` with your own configuration (never commit credentials):

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/piece_of_mind
JWT_SECRET_KEY=REPLACE_WITH_A_RANDOM_SECRET
EDAMAM_APP_ID=YOUR_APP_ID
EDAMAM_APP_KEY=YOUR_APP_KEY
GROQ_API_KEY=YOUR_API_KEY
GROQ_VISION_MODEL=qwen/qwen3.8-27b
```

Apply migrations, then start the backend:

```sh
alembic upgrade head
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/app/` for the demo or `/docs` for the API explorer. The demo keeps its access token in memory; refreshing the page requires logging in again. Save the analysis number to reopen results.

### Tests and Prompt Evaluation

From `backend/`:

```sh
python -m unittest discover -s tests -t . -v
```

Tests use SQLite and mocked providers, without reading real API credentials or modifying the development database. PostgreSQL-specific migrations and real provider behavior need separate verification. An optional browser smoke test (`python -m tests.browser_smoke`) uses mocked providers and requires Playwright plus installed Google Chrome.

Three synthetic image fixtures cover an explicit menu, dish names with no ingredient details, and an ingredient label. To evaluate the versioned extraction prompt against Groq:

```sh
python -m evals.run --live --delay 15 --output /tmp/extraction-results.json
```

This uses API quota. The output records schema-valid results, exact item/ingredient matches, ingredient precision/recall, invented ingredients, latency, provider token usage, and HTTP failures. Cost is only estimated when current per-million-token prices are supplied with `--input-price` and `--output-price`. Offline evaluation accepts `--predictions predictions.json` instead of `--live`; predictions are keyed by fixture ID. These simple fixtures are a starting benchmark, not evidence of accuracy on real restaurant photos. The [initial live run](../backend/evals/results/2026-09-23.json) matched the explicit menu exactly; the other two cases received HTTP 429 rate limits, so model accuracy across all three cases remains unmeasured.

### Still Planned / Known Limits

* Production frontend; the current UI is a lightweight same-origin demo.
* Durable background processing and recovery after process restarts. A server crash during a request can leave an analysis in `PROCESSING`; there is no worker queue or lease recovery yet.
* Whole-menu ranking (multiple reviewed items can already receive reports).
* Portion-aware meal nutrition estimates and structured nutrition-label values.
* Dietary-style, budget, and preference compatibility scoring.
* Broader personalized AI explanations beyond restaurant questions.
* Larger prompt benchmarks with real-world layouts, blur, multilingual menus, and adversarial image text.
* Full live integration checks against PostgreSQL and Edamam, plus deployment validation.

For more detail, see [Features](02_FEATURES.md), [Architecture](03_ARCHITECTURE.md), [Database](04_DATABASE.md), and [API](05_API.md). These documents also describe planned behavior; the implementation summary above distinguishes what currently exists.

---

## MVP Scope

The intended first version of Piece of Mind will allow users to (this is the target scope, not a completion checklist):

* Create an account
* Build a personalized dietary profile
* Upload a restaurant menu image
* Upload a nutrition label or ingredient list
* Analyze menu items using AI vision
* Estimate nutritional information when official values are unavailable
* Detect potential allergens
* Generate a **Compatibility Report** for every menu item
* Rank menu items by overall compatibility with the user's profile
* Suggest possible meal modifications
* Generate personalized AI explanations

---

## Design Principles

### Compatibility Over Judgment

Piece of Mind does not determine what is universally "healthy." Instead, it measures how **compatible** each food option is with an individual's allergies, dietary restrictions, nutrition goals, budget, and preferences. The application provides personalized guidance—not universal recommendations.

---

## Success Metrics

The MVP will be considered successful if a user can:

* Create a personalized profile in a few minutes.
* Upload a menu or nutrition label with minimal effort.
* Receive a **Compatibility Report** within seconds.
* Understand why a meal received its compatibility score.
* Feel more confident making a food decision before ordering.

---

## Future Vision

Piece of Mind aims to become the most trusted platform for evaluating **food compatibility**.

Whether someone is managing celiac disease, navigating food allergies, pursuing specific nutrition goals, or simply trying to make better-informed restaurant choices, Piece of Mind will provide personalized Compatibility Reports that make every food decision easier and more transparent.

Our long-term vision is simple:

> **Give everyone peace of mind by helping them understand how compatible every meal is with their unique needs.**
