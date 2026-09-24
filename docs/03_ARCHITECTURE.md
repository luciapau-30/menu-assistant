# Piece of Mind — System Architecture

## Purpose

This document describes the high-level architecture of Piece of Mind, the responsibilities of each system component, and the complete lifecycle of a request from image upload to Compatibility Report generation.

The architecture prioritizes modularity, maintainability, transparency, and deterministic decision-making while using AI to enhance—not replace—the user experience. My goal is to use purely calculations for the compatibility reports, and use AI to improve the user experience. 

---

# Architecture Overview

```text
                    User
                      │
                      ▼
              React Frontend
                      │
               HTTP Requests
                      │
                      ▼
               FastAPI Backend
                      │
     ┌────────────────┼────────────────┐
     │                │                │
     ▼                ▼                ▼
PostgreSQL      Vision Service   Compatibility Engine
                                        │
                                        ▼
                                 LLM Explanation
                                        │
                                        ▼
                              JSON Response
                                        │
                                        ▼
                                React Frontend
```

The application follows a layered architecture where each component has a single responsibility and communicates through clearly defined interfaces.

---

# Engineering Principles

## Single Responsibility

Every component has one clearly defined purpose.

* React manages the user interface.
* FastAPI deals with requests.
* PostgreSQL stores application data.
* Vision Service extracts structured information from images.
* Compatibility Engine evaluates menu items.
* LLM generates natural-language explanations.

---

## Separation of Concerns

Each layer of the application performs one category of work.

Presentation, business logic, AI services, and data persistence remain independent to simplify maintenance, testing, and future development.

---

## Deterministic Before Generative

Whenever a task can be solved reliably with deterministic software, it should be.

The Compatibility Engine is responsible for:

* Compatibility scoring
* Nutrition estimation
* Allergen detection
* Goal matching
* Meal ranking
* Suggested modifications
* Questions to ask the restaurant

Only after these calculations are complete is the structured output sent to the LLM for explanation.

---

## AI as an Enhancement

Artificial intelligence improves communication rather than making core decisions.

The application's recommendations are produced by deterministic software. The LLM translates those results into clear, personalized explanations and assists with follow-up questions.

---

## Progressive Enhancement

Piece of Mind should continue functioning even if AI services are unavailable.

Without the LLM, users should still receive:

* Compatibility Score
* Nutrition estimates
* Allergen warnings
* Suggested modifications
* Questions to ask the restaurant

The LLM enhances the experience but is not required for the application's core functionality.

---

## Transparency

Whenever information is estimated rather than verified, that uncertainty should be communicated clearly to the user.

Users should always understand which information comes from trusted sources and which is inferred.

---

# System Components

## React Frontend

Responsibilities:

* User authentication
* Profile management
* Image upload
* Display Compatibility Reports
* Display AI explanations
* Handle loading and error states

The frontend never performs compatibility calculations.

---

## FastAPI Backend

Responsibilities:

* Receive API requests
* Validate input
* Authenticate users
* Coordinate internal services
* Return structured API responses

The backend acts as the central coordinator for the application.

---

## PostgreSQL Database

Stores:

* User accounts
* Dietary profiles
* Uploaded image metadata
* Compatibility history
* Application settings

The database stores information but contains no business logic.

---

## Vision Service

Responsibilities:

* Process uploaded images
* Perform OCR
* Identify menu items
* Extract ingredient descriptions
* Return structured menu data

Example output:

```json
{
  "dish": "Grilled Salmon",
  "description": "Served with asparagus and rice"
}
```

---

## Compatibility Engine

The Compatibility Engine is the core of Piece of Mind.

Responsibilities include:

* Estimating nutritional information
* Detecting allergens
* Evaluating dietary restriction compatibility
* Evaluating nutrition goal compatibility
* Calculating Compatibility Scores
* Ranking menu items
* Generating suggested modifications

This component contains the primary business logic of the application.

Generating restaurant questions is handled by the LLM Service instead (see
below) — unlike the rest of this list, phrasing good clarifying questions
benefits from natural-language generation more than deterministic rules,
and the underlying facts it draws from (which ingredients are unknown,
which allergens/restrictions the user has) are still produced
deterministically by this component. This is an explicit exception to
"Deterministic Before Generative": the Compatibility Engine still decides
*what* needs verifying, the LLM only decides *how to phrase asking about
it*, and per Progressive Enhancement below, a deterministic fallback
question is always available if the LLM is unreachable.

---

## Compatibility Engine Methodology

This section documents how the Compatibility Engine actually calculates its
scores, as opposed to just the responsibilities listed above.

### Allergen & Medical Restriction Detection (Safety Score)

* Ingredient-level allergen/restriction data comes from a live integration
  with the **Edamam Food Database API**, not a hand-maintained list.
  Static ingredient→allergen lists were tried first and rejected: they
  don't scale to real-world ingredient names (e.g. "penne" needs to
  resolve to "contains wheat," "nut butter" needs to resolve to "contains
  peanut," and no fixed list can keep up with how food is actually named
  on menus).
* Every ingredient looked up is **cached** in our own database
  (`ingredient_cache` table) so the same ingredient is only ever queried
  from Edamam once, keeping usage well under their rate limits.
* Rule: if **any** ingredient is not confirmed free of an allergen/
  restriction the user has selected, `safety_score = 0` for that menu
  item. There is no partial credit or averaging — safety is a binary
  flag, not a preference, and "70% safe" is a meaningless (and
  dangerous) thing to tell someone with a severe allergy.
* An ingredient Edamam has no data for is tracked as **unknown**, not
  assumed safe. Unknown ingredients lower the report's confidence level
  and produce a warning (e.g. "sauce ingredients unknown, verify with
  restaurant") rather than silently passing.

### Nutrition Goal Matching (Goal Score)

* The Compatibility Engine has no portion/quantity data for a menu item
  (Vision Service extracts ingredient names, not amounts), so goal
  matching cannot calculate a dish's precise total nutrition. Instead it
  evaluates the dish's ingredient **composition** — whether it's built
  from ingredients that typically support a given goal — using each
  ingredient's per-100g nutrient density. This is communicated to users
  as an estimate, consistent with the Transparency principle above, not
  as lab-measured nutrition facts.
* Per-goal logic:
  * **High Protein** — ingredients with protein density ≥ ~15g/100g
    count as protein-rich; the more of the dish built from these, the
    higher the goal score.
  * **Low Carb** — ingredients with carb density ≥ ~20g/100g count
    against the goal; low-carb ingredients count for it.
  * **Muscle Gain** — scored like High Protein, but unlike Weight Loss it
    does not penalize higher calorie density, since muscle gain
    typically requires a calorie surplus rather than a deficit.
  * **Weight Loss** — rewards lower calorie density and higher
    fiber/protein content (satiety).
  * **Weight Maintenance** — always scored neutrally. Ingredient
    composition alone cannot meaningfully assess maintenance, which
    depends on total daily calorie intake rather than any single dish.

---

## LLM Service

Responsibilities:

* Explain Compatibility Scores
* Summarize compatibility findings
* Produce user-friendly recommendations
* Generating restaurant questions, phrased from facts the Compatibility
  Engine already determined (unknown ingredients, the user's specific
  allergens/restrictions) — the LLM does not decide what's unknown or
  risky, only how to phrase asking about it
* Support future conversational interactions

The LLM never determines compatibility or ranking.

### Implementation

Restaurant question generation runs on **Llama 3.3 70B via Groq's hosted
API** (chosen for its fast free-tier inference), called directly over
HTTPS rather than through an SDK. Per the Progressive Enhancement
principle above, this is never a hard dependency: `app/compatibility/safety.py`
always computes a deterministic, rule-based set of questions first: if
the Groq call fails, times out, or returns something that isn't valid
JSON, the deterministic questions are used unchanged and the request
still succeeds.

---

# Request Lifecycle

```text
User uploads image
        │
        ▼
React Frontend
        │
        ▼
FastAPI Backend
        │
        ▼
Vision Service
        │
        ▼
Structured Menu Data
        │
        ▼
Compatibility Engine
        │
        ▼
Compatibility Report
        │
        ▼
LLM Explanation
        │
        ▼
JSON Response
        │
        ▼
React Frontend
```

This pipeline ensures that every recommendation is generated through deterministic software before AI is used to explain the results.

---

# Future Architecture

As Piece of Mind evolves, individual services such as Vision, Compatibility, and LLM processing may be separated into independent microservices.

For Version 1, all services will remain within a single FastAPI application to simplify development, deployment, and maintenance.

The architecture has been intentionally designed so that future scaling can occur without major changes to the application's core structure.