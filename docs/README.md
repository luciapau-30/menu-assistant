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

The project currently contains a Python/FastAPI backend with SQLAlchemy models, PostgreSQL support, and Alembic database migrations. No frontend or automated test suite is present in the repository yet. The status below reflects the code as of September 23, 2026; it does not imply deployment or end-to-end verification.

### Implemented in the Backend

* **Accounts and authentication:** registration, login, Argon2 password hashing, JWT access tokens, and an authenticated current-user endpoint.
* **Dietary profiles:** read and update allergens, medical restrictions, dietary styles, and nutrition goals. Selections are validated against database lookup tables, including an explicit `None` option.
* **Image uploads:** accept menu, nutrition-label, and ingredient-list images, save them locally, and create user-owned analysis records. Users can retrieve the status of their own uploads.
* **Ingredient-based compatibility checks:** accept a single menu item name and an explicit ingredient list, then evaluate them against the authenticated user's profile.
* **Ingredient data and caching:** retrieve health labels and nutrient data from Edamam and cache results in the database. Handled lookup failures remain retryable rather than being cached as permanent misses.
* **Compatibility reports:** return overall, safety, and goal scores; confidence; potential allergen and medical-restriction conflicts; unknown ingredients; unassessed goals; warnings; suggested ingredient removals; and questions to ask restaurant staff.
* **Nutrition-goal scoring:** use ingredient nutrient density per 100 g for High Protein, Muscle Gain, Low Carb, and Weight Loss. Weight Maintenance currently receives a neutral score of 50.
* **AI-assisted questions:** use Groq/Llama to phrase restaurant questions about unknown ingredients, with deterministic questions as a fallback for handled failures or invalid output.
* **Database migrations:** define users, profile lookup tables and relationships, analysis records, and the ingredient cache.

### How the Current Flow Works

1. Register and log in to obtain a bearer token.
2. Save dietary profile selections.
3. Submit a menu item name and ingredient list to `/api/v1/compatibility/check`.
4. The backend looks up ingredients, checks potential conflicts, scores supported nutrition goals, and returns a report.

Image uploading is currently a separate flow: uploads are saved with status `UPLOADED`. The code does not yet extract menu items or ingredients from images, advance analysis through processing, or connect an uploaded image to a compatibility report.

### Current Scoring Boundaries

* A detected allergen or medical-restriction conflict sets the overall compatibility score to **0**. Otherwise, the score is the average of assessed nutrition-goal scores, or **100** when no goal scores are available.
* Unknown ingredients lower the reported confidence and produce warnings, but do not automatically lower the numerical compatibility score. The score must be read alongside these fields; it is not a guarantee of food safety.
* Nutrition scoring uses the fraction of assessed ingredients that meet each goal's thresholds. It does not account for portion sizes or estimate total dish calories and macros.
* Dietary styles are stored in profiles but are not yet applied by the scoring engine. Budget and additional personal preferences are not yet implemented.
* Compatibility reports are returned directly by the check endpoint; they are not yet persisted as completed analysis results.

### Available Endpoints

All endpoints except the root, registration, and login require bearer authentication.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Basic API running message |
| POST | `/api/v1/auth/register` | Create an account |
| POST | `/api/v1/auth/login` | Obtain an access token |
| GET | `/api/v1/auth/me` | Read the current user |
| GET | `/api/v1/profile` | Read the dietary profile |
| PUT | `/api/v1/profile` | Replace profile selections |
| POST | `/api/v1/analysis/upload` | Upload an image and create an analysis record |
| GET | `/api/v1/analysis/{analysis_id}` | Read an owned analysis record's status |
| POST | `/api/v1/compatibility/check` | Evaluate a supplied menu item and ingredient list |

The backend reads configuration from environment variables or `.env`: `DATABASE_URL`, `JWT_SECRET_KEY`, `EDAMAM_APP_ID`, `EDAMAM_APP_KEY`, and `GROQ_API_KEY`. All five are currently required at import/startup, even though AI question generation has a runtime fallback. Optional JWT settings are `JWT_ALGORITHM` (default `HS256`) and `JWT_EXPIRE_MINUTES` (default `60`).

### Still Planned

* A frontend for account setup, profile editing, uploads, and report viewing.
* AI vision/OCR for extracting menu items, nutrition labels, and ingredient lists from uploaded images.
* An end-to-end analysis pipeline that processes uploads and stores completed reports.
* Whole-menu analysis and ranking of multiple items.
* Portion-aware meal nutrition estimates.
* Dietary-style, budget, and preference compatibility scoring.
* Broader personalized AI explanations beyond restaurant questions.
* Automated tests and end-to-end validation of the complete user flow.

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
