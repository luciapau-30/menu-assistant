# Piece of Mind — Developer Handoff

Snapshot: September 23, 2026. Audience: the developer taking over implementation and finishing the MVP.

This document describes the working-tree implementation, its rationale, its limitations, and a proposed path to completion. It is not a claim that the application is deployed or production-ready. Where older design documents disagree with this handoff, check the current code first: some older documents describe intended behavior rather than implemented behavior.

## Contents

1. [Product and current state](#1-product-and-current-state)
2. [Getting the project running](#2-getting-the-project-running)
3. [Repository map and reading order](#3-repository-map-and-reading-order)
4. [Architecture and request lifecycle](#4-architecture-and-request-lifecycle)
5. [Accounts and dietary profiles](#5-accounts-and-dietary-profiles)
6. [Database and migrations](#6-database-and-migrations)
7. [Compatibility engine, precisely](#7-compatibility-engine-precisely)
8. [AI integration and prompting](#8-ai-integration-and-prompting)
9. [API contracts](#9-api-contracts)
10. [The mini frontend](#10-the-mini-frontend)
11. [Testing and evaluation evidence](#11-testing-and-evaluation-evidence)
12. [Known limitations and implementation traps](#12-known-limitations-and-implementation-traps)
13. [Recommended completion plan](#13-recommended-completion-plan)
14. [Troubleshooting](#14-troubleshooting)
15. [Handoff checklist](#15-handoff-checklist)

## 1. Product and current state

**Piece of Mind helps users evaluate food before they order or buy it.** It compares ingredients with a personal dietary profile and explains compatibility, uncertainty, and potential conflicts. Its organizing principle is “compatibility over judgment”: a meal is evaluated against an individual's needs, rather than assigned a universal healthy/unhealthy label.

The long-term scope includes allergies, medical restrictions, dietary styles, nutrition goals, budget, and personal preferences. Only some of these affect the current implementation.

### What exists

| Area | Current state |
| --- | --- |
| Accounts | Registration, password hashing, login, JWT bearer authentication, current-user endpoint |
| Profiles | Four categories backed by seeded lookup tables; read, replace, and list options |
| Uploads | Local image storage, size/signature checks, owned analysis records |
| Vision | Groq image extraction into validated item/ingredient JSON |
| Review | Browser editor for correcting names and ingredients before report generation |
| Compatibility | Deterministic ingredient checks and nutrition-goal heuristics |
| External food data | Edamam parser/nutrient requests and a PostgreSQL ingredient cache |
| AI questions | Groq-generated restaurant questions with deterministic fallback |
| Reports | Multiple reviewed items per analysis, saved results, saved profile snapshot |
| Browser interface | Plain HTML/CSS/JavaScript served by FastAPI at `/app/` |
| Tests | 22 automated unit/API/evaluation tests, plus an optional browser smoke test |
| Prompt benchmark | Three synthetic images, an evaluation runner, and one recorded live run |

### What “working” means here

The upload → extraction → review → saved-report flow exists in code and passed automated checks using mocked providers. One synthetic image was successfully extracted through the live Groq integration. Two other evaluation calls hit HTTP 429 rate limits.

That evidence does **not** establish accuracy on real menus, successful live Edamam integration, full PostgreSQL integration, or deployment readiness. The migration SQL was generated successfully during development; whether the user's current database has been migrated must be checked locally.

### Recent implementation decisions

The first backend stored uploads but did not process them. It also could produce a score of 100 when important information was missing. The recent implementation:

- Added `null` scores for incomplete assessments instead of presenting missing information as a perfect match.
- Changed Weight Maintenance from a neutral 50 to unassessed.
- Added structured vision extraction and an explicit ingredient review interface.
- Connected reviewed items to persisted reports and a fixed profile snapshot.
- Made missing provider credentials fail at feature use rather than preventing all application startup.
- Added tests, a small frontend, and a repeatable extraction benchmark.

## 2. Getting the project running

### Prerequisites

You need Python, a PostgreSQL database, and a terminal. Development verification used Python 3.13.5. The code uses Python 3.10+ syntax, but support across Python versions has not been systematically tested against the pinned dependencies.

PostgreSQL must already exist and be reachable. There is no Docker Compose setup or database-provisioning script in this repository. SQLite is used by tests, not as a supported drop-in application database: the ingredient cache uses PostgreSQL JSONB.

### First-time setup

From the repository root:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

**If the terminal is already in `backend`, skip `cd backend`.** If `.venv/bin/activate` does not exist, create the virtual environment before sourcing it. The interpreter-qualified commands below avoid ambiguity over which environment supplies `alembic` and `uvicorn`.

Create `backend/.env`. Substitute your own values; do not copy placeholders into a real deployment:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/piece_of_mind
JWT_SECRET_KEY=REPLACE_WITH_A_RANDOM_SECRET
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
EDAMAM_APP_ID=YOUR_EDAMAM_APP_ID
EDAMAM_APP_KEY=YOUR_EDAMAM_APP_KEY
GROQ_API_KEY=YOUR_GROQ_API_KEY
GROQ_VISION_MODEL=qwen/qwen3.8-27b
```

Generate a signing secret locally if needed:

```sh
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Apply the database migrations and start the API:

```sh
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Visit:

- `http://127.0.0.1:8000/app/` — browser demo.
- `http://127.0.0.1:8000/docs` — generated interactive API documentation.
- `http://127.0.0.1:8000/` — basic running message, not a database/provider health check.

Keep the terminal running while using the app. Stop the development server with Ctrl+C.

For later sessions, from `backend`:

```sh
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

### Configuration behavior

| Variable | Used for | Missing-value behavior |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy database connection | Startup/import fails |
| `JWT_SECRET_KEY` | Signing and verifying access tokens | Startup/import fails |
| `JWT_ALGORITHM` | Token algorithm | Defaults to `HS256` |
| `JWT_EXPIRE_MINUTES` | Token lifetime | Defaults to 60 minutes |
| `EDAMAM_APP_ID`, `EDAMAM_APP_KEY` | Food lookup | Lookup treated as unavailable; ingredients become unknown |
| `GROQ_API_KEY` | Vision and question generation | Extraction unavailable; restaurant questions fall back to rules |
| `GROQ_VISION_MODEL` | Vision model identifier | Defaults to the identifier shown above |

Model identifiers here describe the code snapshot, not a promise of continued provider availability. Check provider support before changing them. Configuration is read into module-level variables, so restart the server after changing `.env`.

The existing `.env` is private local configuration, not part of this handoff. No credential values are included here.

## 3. Repository map and reading order

Paths below are relative to the repository root.

```text
backend/
  requirements.txt          Pinned Python dependencies
  alembic.ini               Migration configuration
  alembic/versions/         Schema changes and lookup seeds
  app/
    main.py                 FastAPI setup, routers, static frontend mount
    core/                   Authentication helpers and local image storage
    database/connection.py  Engine, sessions, declarative model base
    models/                 SQLAlchemy database entities
    schemas/                Pydantic request/response and extraction contracts
    routes/                 HTTP endpoints and dependency injection
    services/               Use-case orchestration and persistence
    compatibility/          Deterministic checks, scores, Edamam adapter
    llm/                    Groq clients, extraction prompt, question prompt
    web/                    Demo HTML, CSS, and JavaScript
    uploads/                Runtime image files; ignored by Git
  tests/                    Automated tests and optional browser smoke
  evals/                    Synthetic images, expected data, evaluation runner
    results/                Recorded benchmark output

docs/
  README.md                 Product overview and implementation summary
  02_FEATURES.md            Feature specification, including planned features
  03_ARCHITECTURE.md        Architecture intentions and methodology
  04_DATABASE.md            Database design documentation
  05_API.md                 API design documentation
  06_DEVELOPER_HANDOFF.md   This document
```

Recommended code-reading order:

1. [Application entry point](../backend/app/main.py) and [analysis routes](../backend/app/routes/analysis.py).
2. [Analysis service](../backend/app/services/analysis_service.py) and [analysis model](../backend/app/models/analysis.py).
3. [Extraction schemas](../backend/app/schemas/extraction.py) and [vision client](../backend/app/llm/vision.py).
4. [Compatibility orchestration](../backend/app/services/compatibility_service.py).
5. [Safety checks](../backend/app/compatibility/safety.py), [goal checks](../backend/app/compatibility/goals.py), and [score combination](../backend/app/compatibility/scoring.py).
6. [Edamam client](../backend/app/compatibility/edamam_client.py) and [cache service](../backend/app/services/ingredient_cache_service.py).
7. [Browser client](../backend/app/web/app.js), followed by the tests.

### Repository handoff caveat

At the time this document was written, Git reported `backend/` as untracked, alongside existing documentation edits, a deleted root `README.md`, and other local changes. A developer receiving only the currently committed history may therefore not receive the implementation described here.

Before handing the repository to another developer, inspect `git status`, review intended files, and commit the relevant implementation deliberately. Do not accidentally include `.env`, virtual environments, uploaded images, or `.DS_Store`. This documentation task does not commit or clean up those existing changes.

## 4. Architecture and request lifecycle

The application is one FastAPI process with a database, local file storage, and two external integrations. There is no separate React build, worker queue, or background job service.

```mermaid
flowchart TD
    UI[Browser demo] --> API[FastAPI routes]
    API --> AUTH[JWT authentication]
    API --> PROFILE[Profile service]
    PROFILE --> DB[(PostgreSQL)]
    API --> UPLOAD[Upload and analysis service]
    UPLOAD --> FILES[Local image files]
    UPLOAD --> VISION[Groq vision extraction]
    VISION --> REVIEW[User reviews ingredients]
    REVIEW --> ENGINE[Deterministic compatibility engine]
    ENGINE --> CACHE[Ingredient cache]
    CACHE --> DB
    CACHE --> EDAMAM[Edamam food data]
    ENGINE --> QUESTIONS[Groq questions or rule fallback]
    QUESTIONS --> REPORT[Persist report and profile snapshot]
    REPORT --> DB
    REPORT --> UI
```

### Step A: upload

`POST /api/v1/analysis/upload` accepts multipart fields `image` and `type`. The storage helper reads at most 4 MiB plus one byte, rejects oversize files, recognizes PNG/JPEG/WebP signatures, chooses a UUID filename, and saves it under `backend/app/uploads/`.

The service creates an owned analysis record with status `UPLOADED`. Its `image_url` field is actually a local filesystem path, not a public URL.

### Step B: extract

`POST /api/v1/analysis/{id}/extract` claims the analysis and sets `PROCESSING`. It reads the image, calls Groq, validates the extraction schema, saves the extracted items and warnings, and returns the analysis to `UPLOADED` for review.

Extraction does not calculate compatibility and does not automatically create reports.

### Step C: review

The browser displays editable names and one ingredient per line, alongside source text. The user can remove items or add manually entered items. A dish name without listed ingredients is intentionally allowed in extraction; it must acquire at least one reviewed ingredient before report submission.

The API also allows manual report submission without successful extraction. Review is represented by the submitted corrected items, not by a separate review-status enum or a recorded review attestation.

### Step D: generate and save reports

`POST /api/v1/analysis/{id}/report` claims the analysis, snapshots the current profile, and constructs a fixed profile input used for every item in that request. Each item passes through the deterministic engine and optional question generation.

Only after all items have been processed does the service assign the report list and profile snapshot, set `COMPLETED`, and commit. A completed analysis remains unchanged through these endpoints; a new analysis is needed for a new evaluation.

### State meanings

| State | Meaning | Permitted processing behavior |
| --- | --- | --- |
| `UPLOADED`, no extraction | Image stored | Extract or manually submit reviewed items |
| `UPLOADED`, extraction present | Ready for review | Re-extract or submit reviewed items |
| `PROCESSING` | Extraction or report request has claimed the record | Another processing request receives 409 |
| `FAILED` | A handled processing failure was recorded | Retry extraction or report generation |
| `COMPLETED` | Reports and profile snapshot saved | Read results; processing endpoints return 409 |

`_claim_analysis()` performs a conditional update, rather than relying only on an earlier read, to prevent two requests from claiming the same available analysis. All access first checks ownership; another user's analysis returns 404.

Important failure semantics: caught processing failures generally return an analysis response with HTTP 200 and `status: "FAILED"`. Clients must inspect status and `error_message`, not only the HTTP status. Requests are synchronous. A process crash after claiming work can leave `PROCESSING` stuck; there is no durable recovery mechanism yet.

## 5. Accounts and dietary profiles

Registration validates the email through the schema, checks for an existing email, hashes the password using Argon2 through `pwdlib`, and saves the user. Login verifies the password and returns a signed JWT. Authenticated endpoints use an `Authorization: Bearer ...` header.

The four profile categories are:

| Category | Examples | Current scoring support |
| --- | --- | --- |
| `allergens` | Peanut, Dairy, Wheat, Sesame | Mapped to Edamam free-of labels |
| `medical_restrictions` | Celiac Disease, Lactose Intolerance, Low FODMAP | Mapped to Edamam labels |
| `dietary_styles` | Vegan, Vegetarian, Mediterranean | Stored, but explicitly unassessed |
| `nutrition_goals` | High Protein, Low Carb, Weight Loss | Heuristics; Weight Maintenance unassessed |

Use `/api/v1/profile/options` to obtain actual seeded values. Names are resolved against the database; do not invent alternative spellings in clients.

`PUT /api/v1/profile` replaces all four category selections. Omitted categories default to empty lists, so this is not a partial update. At least one selection across the whole profile is required. The literal string `"None"` is a seeded option and cannot be combined with another option in the same category. Unknown selection names return 400; schema validation failures return 422.

A newly registered user can still have no saved selections; report generation does not independently enforce profile completion. Decide whether the finished product should require an explicit “no restrictions” confirmation rather than silently accepting an untouched profile.

Password reset, email verification, refresh tokens, and server-side token revocation are not implemented. The browser's logout action reloads the page and discards its in-memory token.

## 6. Database and migrations

### Data model

| Table/group | Purpose |
| --- | --- |
| `users` | Name, unique email, password hash, creation timestamp |
| `allergens`, `medical_restrictions`, `dietary_styles`, `nutrition_goals` | Seeded selection vocabulary |
| Four `user_*` association tables | Many-to-many profile selections |
| `analyses` | Owner, type, local image path, status, timestamp, extraction, reports, profile snapshot, error |
| `ingredient_cache` | Normalized ingredient name, found flag, health labels, per-100g nutrients, fetch timestamp |

Extraction, reports, and profile snapshots use JSON columns on the analysis record. Ingredient labels and nutrients use PostgreSQL JSONB. Reports are not separate relational menu-item rows.

Stored results intentionally reflect the profile at analysis time. Editing a user's current profile must not rewrite old reports. The snapshot currently includes the user's name and the four category lists. It does not include a scoring-version identifier, provider provenance, or prompt version.

### Migration chain

| Revision | Change |
| --- | --- |
| `d959cb5123ae` | Baseline users table |
| `1c38887bedf9` | Profile lookup tables, associations, and initial selection seeds |
| `07d2ed9968cc` | Explicit None options |
| `d109f7c37a72` | Analysis table and enums |
| `fc8e5b064811` | Ingredient cache |
| `a832d610ea01` | Analysis extraction, reports, profile snapshot, error message |

From `backend`, useful commands are:

```sh
python -m alembic current
python -m alembic heads
python -m alembic history
python -m alembic upgrade head
```

If a database already contains manually created tables, establish its actual state before attempting to align it with Alembic. Do not use `stamp head` simply to silence an error: stamping does not create missing columns.

For new schema work, create a new migration and review it. Existing applied migration files should not be rewritten as a substitute for an upgrade. New model modules must be registered through imports in `alembic/env.py` for autogeneration to see them.

## 7. Compatibility engine, precisely

The business logic lives in `compatibility/`; LLM responses do not set compatibility scores. These are application heuristics, not validated clinical scoring formulas.

### Ingredient lookup

The cache normalizes names with `strip().lower()`. On a miss, the Edamam adapter:

1. Calls the Food Database parser with the ingredient text.
2. Uses only the first entry in `parsed`; it deliberately does not fall back to fuzzy `hints`.
3. Requests nutrients and health labels for 100 grams of the selected food.
4. Normalizes nutrient quantities using returned total weight.
5. Saves a reusable cache entry.

A successful “no match” is cached as `found=False`. A handled provider/configuration failure returns an unsaved unknown entry, allowing a later request to retry. Each HTTP request currently has a 10-second timeout.

Safety and goal checks each call the cache helper. With successful lookups, the second pass uses the cache. Unavailable lookups can be attempted again during the same report because failure entries are deliberately not persisted.

### Safety checks

`label_mapping.py` maps the application's selected categories to free-of labels. For example, Peanut maps to `PEANUT_FREE`, Wheat to `WHEAT_FREE`, and Celiac Disease to `GLUTEN_FREE`.

For a recognized ingredient, absence of a selected category's mapped free-of label is treated as a **potential conflict**. This is not independent proof that the ingredient contains the allergen; UI language should retain that distinction.

| Situation | `safety_score` |
| --- | --- |
| At least one potential mapped conflict | `0` |
| No conflict, but unknown ingredients, no ingredients, or unsupported profile selections | `null` |
| No detected conflict and no identified assessment gaps | `100` |

Unknown ingredients are collected separately. Unsupported dietary styles also produce a warning. Suggested modifications currently consist of `Remove {ingredient}` for offending ingredients. The application does not model cross-contact or establish that removal makes a prepared dish safe.

### Confidence

Confidence comes from ingredient lookup coverage, not model certainty:

- Empty ingredient input or unsupported profile selections: Low.
- Zero unknown ingredients: High.
- Unknown proportion greater than zero and at most 0.34: Medium.
- Larger unknown proportion: Low.

It does not measure extraction accuracy, portion accuracy, preparation safety, or complete recipe coverage. A partially transcribed recipe can have High lookup confidence for the few ingredients supplied.

### Nutrition-goal calculations

The input has ingredient names without amounts. Each known ingredient receives equal weight, regardless of its quantity in the meal.

| Goal | Favorable ingredient rule, using per-100g nutrient values |
| --- | --- |
| High Protein | Protein at least 15 g |
| Muscle Gain | Same rule as High Protein |
| Low Carb | Carbohydrate below 20 g |
| Weight Loss | Energy below 200 kcal AND either protein at least 10 g or fiber at least 3 g |
| Weight Maintenance | Unassessed; requires information beyond ingredient composition |

Nutrient keys used by the implementation are `PROCNT`, `CHOCDF`, `ENERC_KCAL`, and `FIBTG`. Missing required values yield an unassessed ingredient for that goal.

For each assessable goal:

```text
goal score = round(100 × favorable ingredient count / assessed ingredient count)
```

If any submitted ingredient lacks enough information for a selected goal, that goal also appears in `unassessed_goals`. A partial numeric score can still be present in `goal_scores`; clients must not mistake it for a fully assessed goal.

Example: chicken meets the protein threshold and rice does not, with both assessed. High Protein scores 50. If rice's protein value is missing instead, the partial High Protein score is 100, the goal is listed as unassessed, and the overall score is `null`.

### Combining scores

Order matters:

1. A safety conflict overrides everything: overall score 0 and aggregate `goal_score` null. Per-goal details remain in the response.
2. Otherwise, incomplete safety, unknown ingredients, or unassessed goals make the overall score null. An average of available goal scores may still be shown separately.
3. Otherwise, average the selected assessed goal scores.
4. With complete checks and no selected goals, return 100 because there is no scored goal to differentiate fit.

Never coerce null to zero or 100 in clients. Null means “not fully assessed”; zero is a scored result and can represent a conflict or poor goal fit. Preserve that distinction in sorting, filtering, and future rankings.

## 8. AI integration and prompting

There are two separate AI tasks, with different inputs and failure behavior.

### Vision extraction

Source: [vision.py](../backend/app/llm/vision.py). Prompt version: `menu-extraction-v1`.

The client sends a system instruction, an image-type instruction, and a base64 data URL containing the uploaded image. It requests a JSON object, temperature 0, a 6,000-token completion limit, and a 60-second HTTP timeout.

The prompt explicitly asks the model to:

- Extract only food information written in the image.
- Treat image text as data, not instructions.
- Avoid guessing recipes from dish names or photographs.
- Return item names, explicitly listed ingredients, and faithful source text.
- Return empty ingredient lists when ingredient details are missing.
- Avoid deciding allergens, safety, or nutrition.
- Report unreadable information and truncation as warnings.

The response must finish with `finish_reason == "stop"` and pass Pydantic validation. Extracted data allows 1–30 items, up to 60 ingredients per item, bounded text lengths, and no extra object fields. An empty overall item list fails validation and becomes an extraction failure rather than a usable empty menu.

Prompt constraints reduce unwanted behavior; they do not prove that every returned ingredient was present in the image. Schema validation checks structure, not factual grounding. Human review remains necessary, and larger evaluation sets are needed.

The code does not create a separate list of inferred ingredients. It instructs the model not to infer them at all. Future inference features must introduce explicit provenance rather than quietly mixing guesses into the current list.

### Restaurant questions

Sources: [questions.py](../backend/app/llm/questions.py) and [groq_client.py](../backend/app/llm/groq_client.py).

The text model is currently `llama-3.3-70b-versatile`. It receives the menu item name, unidentified ingredients, and selected allergen/medical concerns. The prompt requests short questions restricted to those facts, formatted as a JSON array of strings.

No unknown ingredients means no question-generation request. Otherwise, the deterministic safety pass has already created fallback questions. An HTTP failure, handled malformed response, invalid JSON, empty list, or invalid string entries causes those fallback questions to remain in place.

Validation does not establish that every concern is covered or that the language contains no invented assertions. This is a future evaluation target. There is no full report-explanation feature yet.

### How AI was used during development

An AI coding assistant helped inspect the code, document implementation status, add regression tests, connect extraction and report persistence, build the browser demo, and construct evaluation fixtures. This describes development assistance, not an additional runtime feature.

For the next developer, the reproducible prompt assets are the source-code prompt strings, schema definitions, benchmark fixtures, and recorded results. No separate comprehensive development-prompt transcript or prompt registry is maintained in the repository.

## 9. API contracts

The application mounts API routes under `/api/v1`. Except for registration and login, the endpoints below require bearer authentication. The root message, static demo, and default generated API docs are also publicly accessible.

| Method | Path after `/api/v1` | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Obtain token |
| GET | `/auth/me` | Current user |
| GET | `/profile` | Current selections |
| GET | `/profile/options` | Seeded selection names |
| PUT | `/profile` | Replace selections |
| POST | `/analysis/upload` | Store image; multipart `image`, `type` |
| GET | `/analysis/{id}` | Owned analysis and results |
| POST | `/analysis/{id}/extract` | Extract for review; no body |
| POST | `/analysis/{id}/report` | Save reports from reviewed items |
| POST | `/compatibility/check` | Direct single-item check; not persisted |

Upload types are exactly `MENU`, `NUTRITION_LABEL`, and `INGREDIENT_LIST`.

Example reviewed-report body:

```json
{
  "items": [
    {"name": "Garden Bowl", "ingredients": ["rice", "chickpeas", "spinach"]}
  ]
}
```

Each reviewed item needs a nonblank name and at least one nonblank ingredient. The request permits at most 30 items and 60 ingredients per item. Extraction may have empty ingredient lists, but reviewed report requests may not.

Example direct-check body:

```json
{
  "menu_item_name": "Garden Bowl",
  "ingredients": ["rice", "chickpeas", "spinach"]
}
```

An analysis response contains `analysis_id`, `status`, nullable `extraction`, nullable `reports`, nullable `profile_snapshot`, and nullable `error_message`.

Each report includes:

| Field | Interpretation |
| --- | --- |
| `menu_item_name`, `ingredients` | Reviewed inputs used for this result |
| `compatibility_score` | Overall integer score or null |
| `safety_score` | 0, 100, or null |
| `goal_score` | Aggregate goal score or null |
| `confidence` | High, Medium, or Low lookup coverage |
| `detected_allergens`, `detected_restrictions` | Potential mapped conflicts |
| `goal_scores` | Per-goal scores, possibly partial |
| `unassessed_goals` | Goals that could not be fully assessed |
| `unknown_ingredients` | Ingredients without usable lookup matches |
| `warnings` | Assessment gaps |
| `suggested_modifications` | Rule-generated removal suggestions |
| `questions_to_ask` | AI-enhanced or deterministic restaurant questions |

Common HTTP failures include 401 for invalid authentication, 404 for missing/not-owned analyses, 409 for claimed/completed analyses or duplicate registration, 413 for oversized images, 415 for unrecognized image signatures, and 422 for schema validation. Processing failures may instead be represented by the `FAILED` response state described earlier.

## 10. The mini frontend

The frontend is in `backend/app/web/` and is mounted by FastAPI through `StaticFiles`. It has no Node package installation, bundler, React dependency, or separate development server.

- `index.html` defines account, profile, upload, review, and results sections.
- `style.css` supplies responsive layout and visual styling.
- `app.js` performs requests, retains the token in memory, manages the active analysis ID, and renders results.

The user journey is account → profile → image → review → reports. Users may reopen an analysis by entering its ID. There is no history-list endpoint or dashboard yet, so saving the analysis number matters.

The browser uses same-origin `/api/v1/...` requests. A future separately hosted frontend will need explicit origin/deployment decisions; those are not configured here.

Dynamic provider/user text is rendered with `textContent`, not interpreted as HTML. Report failures preserve the current review editor so users can retry without immediately losing corrections. Refreshing the page still loses in-memory drafts and the access token.

The demo is useful for development, but it lacks image preview alongside extraction, autosaved drafts, a full session-expiration experience, and a complete history UI. Its profile selectors are basic multiple-select controls, not a finished onboarding experience.

## 11. Testing and evaluation evidence

### Automated suite

From `backend` with dependencies installed:

```sh
python -m unittest discover -s tests -t . -v
```

The last implementation verification passed 22 tests. This documentation-only handoff did not rerun application tests.

| File | Coverage |
| --- | --- |
| `tests/test_compatibility.py` | Conflict precedence; unknown/empty ingredients; unsupported styles; missing/partial nutrients; Weight Maintenance; score averages; malformed AI output and fallback |
| `tests/test_analysis.py` | Registration/login/profile; upload-review-report persistence; ownership; failure retry; partial-report prevention; duplicate claiming; upload/review validation; vision response validation |
| `tests/test_evaluation.py` | Benchmark detection of invented ingredients and missing items |

`tests/__init__.py` sets test database and credential environment variables before application imports. API tests use in-memory SQLite and exclude the PostgreSQL-specific ingredient-cache table, substituting mocked ingredient results. They do not demonstrate real cache-table behavior or PostgreSQL transaction behavior.

### Browser smoke

Install the optional tooling in your development environment, with Google Chrome already installed:

```sh
python -m pip install playwright
python -m tests.browser_smoke
```

This check passed registration, profile saving, upload, reviewed-name editing, report rendering, mobile-width overflow checks, and absence of JavaScript errors. It uses mocked providers and routes browser requests through the API test client. The upload bridge supplies a fixture file because browser interception can omit multipart file bytes. It is not a live-network end-to-end browser test.

Screenshots are written to `/tmp/pom-browser-desktop.png` and `/tmp/pom-browser-mobile.png`; these are temporary artifacts, not committed deliverables.

### Migration verification

The migration chain was rendered as PostgreSQL SQL without connecting to the development database. That validates migration generation, not successful application to a populated database. Add real PostgreSQL integration tests before relying on deployment automation.

### Prompt evaluation

The benchmark lives in `backend/evals/`:

- `cases.json` defines expected item names and ingredients.
- `images/explicit_menu.png` contains two dishes with explicit ingredients.
- `images/names_only.png` contains dish names without ingredient lists.
- `images/ingredient_label.png` contains a short ingredient label.
- `run.py` computes results and writes JSON.

Run live evaluation with:

```sh
python -m evals.run --live --delay 15 --output /tmp/extraction-results.json
```

This sends the synthetic images to Groq and consumes provider quota. Delaying requests does not guarantee avoidance of provider limits.

For offline evaluation, provide a JSON object mapping case IDs to extraction-shaped prediction objects:

```sh
python -m evals.run --predictions predictions.json --output /tmp/offline-results.json
```

Metrics include valid output, exact item/ingredient match, ingredient precision and recall, extra/missing items, invented ingredients, elapsed time, and provider token usage. Cost is null unless both `--input-price` and `--output-price` are supplied in dollars per million tokens.

Matching normalizes case and whitespace but does not resolve synonyms. Identical item names are collapsed into a dictionary by the evaluator. Both choices limit what the metrics capture. Offline latency is local validation time, not model latency.

The [recorded live result](../backend/evals/results/2026-09-23.json) contains one exact successful menu extraction and two HTTP 429 failures. Its 33% exact-match rate is an operational result for that run, **not** a clean estimate of model accuracy: two cases never produced usable outputs. Do not present it as a three-case accuracy benchmark on a resume or product page.

## 12. Known limitations and implementation traps

These are code-level observations or explicit gaps, not completed work.

### Processing and persistence

- **Stuck processing:** there are no worker leases, deadlines, restart recovery, or abandoned-job cleanup.
- **Long synchronous work:** up to 30 reviewed items can cause many sequential lookups and question requests in one HTTP request. A fast mocked test does not predict real latency.
- **Generic errors:** analysis processing catches broad exceptions and stores generic messages. Structured, sanitized diagnostic logging is still needed.
- **No processing version metadata:** saved reports do not record the scoring version or vision prompt/model that produced their source extraction.
- **No draft persistence:** extraction is saved, but user edits are only persisted as reviewed report inputs after successful completion.

### Cache and provider behavior

- **No expiry:** both positive and successful negative ingredient matches remain cached indefinitely; `fetched_at` is not used for refresh.
- **Cache insert races:** two concurrent misses can contend for the unique ingredient-name constraint; there is no upsert/retry handling.
- **Inner commits:** cache inserts call `db.commit()` on the shared session. Review transaction boundaries before adding more state changes around those calls.
- **No backoff:** provider rate limits are handled as failures, but the application does not honor `Retry-After` or implement coordinated backoff.
- **Limited diagnostics:** the public error is generic; authentication failures and rate limits may look identical in the UI.
- **Sensitive error strings:** the Edamam adapter places credentials in query parameters. Avoid logging raw HTTP exception URLs when adding diagnostics.

### Input and scoring

- **Signature checks only:** storage recognizes leading bytes; it does not fully decode images or check dimensions. Files may be orphaned if a later database insert fails.
- **Incomplete source menus:** explicitly listed ingredients are not necessarily a complete recipe. User review improves the input but does not establish completeness.
- **Equal ingredient weighting:** duplicates, repeated spellings, and tiny garnish ingredients can affect goal scoring disproportionately. There is no ingredient deduplication or quantity model.
- **Unsupported styles:** dietary styles are persisted but cause incomplete assessment; simply adding a dropdown value does not implement dietary support.
- **No meal totals:** there is no portion-level calorie/macro calculation, structured nutrition-facts extraction, budget comparison, or menu ranking.
- **Removal suggestions:** these are string templates, not verified substitutions or preparation guarantees.

### Account and frontend gaps

- No password reset, email verification, token refresh, or abuse controls are implemented.
- JWT subject conversion uses `int(user_id)` without separately handling a malformed numeric subject; include this in authentication hardening tests.
- No full session-expiration recovery, analysis history listing, edit-draft recovery, or image preview is implemented.
- A new account can bypass profile setup through the API; product behavior for an empty profile needs an explicit decision.

### Tests and dependencies

- Real Edamam response handling, cache persistence/races, migration application, and PostgreSQL behavior need additional integration coverage.
- The pinned requirements include a distribution named `app==0.0.1` even though this repository also defines its own `app` package. Review whether that dependency is necessary before the next dependency cleanup; it has not been removed here.
- Existing framework/dependency deprecation warnings were seen during testing. Address them during maintenance rather than confusing them with failing assertions.

## 13. Recommended completion plan

This order is proposed next work, not a claim that the items are implemented.

| Priority | Work | Completion criteria |
| --- | --- | --- |
| 1 | Establish reproducible checkout/setup | Intended code committed; fresh environment can install, migrate a disposable PostgreSQL database, and open `/app/` without undocumented steps |
| 2 | Validate real providers | Known ingredient lookups and extraction run with valid credentials; authentication, quota, timeout, and malformed-response behavior are separately tested and observable |
| 3 | Make processing recoverable | Durable job execution or bounded synchronous recovery; duplicate work prevented; crashed jobs recover; clients receive clear retry guidance |
| 4 | Strengthen cache behavior | Real PostgreSQL tests; concurrent miss handling; defined positive/negative expiry; controlled retries and transaction boundaries |
| 5 | Improve input provenance | Image preview, editable source linkage, draft saving, and explicit handling of omitted/uncertain ingredients |
| 6 | Finish dietary behavior | Defined and tested supported styles; explicit empty-profile behavior; unsupported selections remain visibly unassessed |
| 7 | Expand evaluation | Larger varied fixture set; rate-limit failures separated from quality metrics; prompt versions compared on the same dataset |
| 8 | Finish the user experience | History listing, token-expiry recovery, usable mobile selection controls, loading/retry states, and accessibility checks |
| 9 | Add remaining product scope | Defined menu-ranking policy, quantities/nutrition totals, budget/preferences, and broader explanations |
| 10 | Validate deployment | Persistent storage, environment configuration, migration procedure, backups, monitoring, and end-to-end checks in the intended environment |

### Suggested first work session

1. Read this handoff and run `git status` to establish what is actually in the checkout.
2. Create the local virtual environment and run the 22-test suite.
3. Migrate a disposable PostgreSQL database and verify the cache table with real database tests.
4. Walk through the mini frontend with a synthetic menu.
5. Inspect provider errors without printing credentials; identify whether the account can support the intended workload.
6. Choose the first small issue from priorities 2–4 and define its failure-path tests before changing behavior.

### Preserve these behaviors while finishing the code

- Missing evidence is not a perfect score.
- A detected conflict cannot be averaged away by good nutrition-goal scores.
- The LLM cannot assign compatibility scores.
- Extraction output is untrusted input and must be structurally validated.
- Manual input remains available when image extraction is unavailable.
- Transient lookup failures do not become permanent negative cache entries.
- Only the owner can access an analysis.
- Every item in a saved report uses the same recorded profile snapshot.
- Provider failure must not silently become a positive food-compatibility claim.

## 14. Troubleshooting

| Symptom | Likely explanation / next check |
| --- | --- |
| `cd: no such file or directory: backend` | Terminal is already inside `backend`; run `pwd` and skip the extra `cd` |
| `.venv/bin/activate` missing | Run `python3 -m venv .venv` from `backend` first |
| `command not found: alembic` or `uvicorn` | Activate the environment, install requirements, then use `python -m alembic` / `python -m uvicorn` |
| Missing `DATABASE_URL` / `JWT_SECRET_KEY` | Check local `.env` placement and restart the server; do not paste secrets into bug reports |
| Database connection or authentication failure | Check the PostgreSQL server, URL, credentials, and intended database before running migrations |
| Missing `analyses` result columns | Check `python -m alembic current` and migrate through `a832d610ea01` |
| Image extraction fails | Inspect sanitized provider status, image readability, model access, and quota; manual entry remains available |
| Recorded evaluation shows 429 | The observed live run hit provider rate limits; it does not demonstrate that the key expired |
| Every ingredient is unknown | Check Edamam configuration/connectivity and lookup responses; distinguish provider failure from cached successful no-match results |
| Report says “Not fully assessed” | Inspect unknown ingredients, unassessed goals, and unsupported profile warnings; this can be intended behavior |
| A 100 partial goal score accompanies a null overall score | One or more ingredients could not be assessed for that goal; the partial average is not the full assessment |
| Reprocessing returns 409 | Record is currently `PROCESSING` or already `COMPLETED` |
| `PROCESSING` never clears | Investigate whether the owning server request died; there is currently no automatic recovery. Do not reset a genuinely active request blindly |
| Refresh logs the user out | Token storage is intentionally in memory in the demo |
| `/` shows only a JSON message | Open `/app/` for the frontend |

Do not infer that a key is expired solely from a generic UI extraction error. The recorded failure evidence here is HTTP 429. A provider error-classification improvement would make troubleshooting much clearer.

## 15. Handoff checklist

Before another developer starts, make sure they have:

- The intended implementation files, not just an earlier README commit.
- This document and the current [project README](README.md).
- Their own local configuration or an approved method of obtaining development credentials.
- A known database migration state and a disposable integration-test database.
- The automated test command and its known coverage boundaries.
- The synthetic benchmark and the actual recorded provider-limit result.
- A decision on the next small deliverable, with explicit acceptance criteria.

The useful starting point is a functional development slice: accounts, profiles, reviewed image extraction, deterministic compatibility reports, saved results, and a small browser interface. The remaining work is to validate the live integrations, make execution reliable, broaden product coverage, and establish evidence that the finished experience behaves correctly under real inputs and failures.
