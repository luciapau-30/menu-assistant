# Piece of Mind — API Design

## Purpose

This document defines the API contract between the Piece of Mind frontend and backend systems.

The API enables communication between the React frontend, FastAPI backend, database, Vision Service, Compatibility Engine, and LLM Service.

The API follows REST principles and uses JSON for data exchange.

---

# API Design Principles

## REST Architecture

Piece of Mind uses RESTful API design because it provides:

* Clear endpoint structure
* Simple communication between frontend and backend
* Compatibility with modern web applications
* Easy testing and documentation

---

## JSON Communication

The frontend and backend communicate using JSON objects.

Example request:

```json
{
  "email": "user@email.com",
  "password": "password123"
}
```

Example response:

```json
{
  "message": "Account created successfully"
}
```

---

## Authentication

Protected endpoints require authentication.

Piece of Mind uses token-based authentication:

```text
User
 |
Login
 |
FastAPI
 |
JWT Token
 |
Authenticated Requests
```

The backend uses the token to identify the current user.

---

# API Versioning

All endpoints use versioning:

```
/api/v1
```

Versioning allows future API changes without breaking existing clients.

---

# Authentication Endpoints

## Create Account

### POST

```
/api/v1/auth/register
```

Creates a new Piece of Mind account.

### Request

```json
{
  "name": "Alex",
  "email": "alex@email.com",
  "password": "password123"
}
```

### Response

```json
{
  "message": "User created successfully",
  "user_id": 123
}
```

---

## Login

### POST

```
/api/v1/auth/login
```

Authenticates a user and returns an access token.

### Request

```json
{
  "email": "alex@email.com",
  "password": "password123"
}
```

### Response

```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer"
}
```

---

# User Profile Endpoints

## Get User Profile

### GET

```
/api/v1/profile
```

Returns the user's dietary profile and preferences.

### Response

```json
{
  "name": "Alex",
  "allergens": [
    "Gluten",
    "Dairy"
  ],
  "medical_restrictions": [
    "Celiac Disease"
  ],
  "dietary_styles": [
    "Gluten-Free"
  ],
  "nutrition_goals": [
    "High Protein",
    "Weight Loss"
  ],
  "preferences": {
    "cuisines": [
      "Japanese"
    ]
  }
}
```

---

## Update User Profile

### PUT

```
/api/v1/profile
```

Updates:

* Allergens
* Medical restrictions
* Dietary styles
* Nutrition goals
* Preferences

---

# Analysis Endpoints

## Upload Menu or Nutrition Label

### POST

```
/api/v1/analysis/upload
```

Uploads an image for analysis.

Supported uploads:

* Restaurant menus
* Nutrition labels
* Ingredient lists

### Request

Multipart form data:

```
image:
restaurant_menu.jpg

type:
MENU
```

### Response

```json
{
  "analysis_id": 456,
  "status": "PROCESSING"
}
```

---

## Get Analysis Status

### GET

```
/api/v1/analysis/{analysis_id}
```

Returns the current processing state.

### Response

```json
{
  "analysis_id": 456,
  "status": "COMPLETED"
}
```

Possible statuses:

* UPLOADED
* PROCESSING
* COMPLETED
* FAILED

---

# Compatibility Report Endpoints

## Get Reports From Analysis

### GET

```
/api/v1/analysis/{analysis_id}/reports
```

Returns all Compatibility Reports generated from an analysis.

A single menu analysis may contain multiple reports.

### Response

```json
[
  {
    "menu_item": "Chicken Bowl",
    "compatibility_score": 94,
    "safety_score": 100,
    "confidence": "High"
  },
  {
    "menu_item": "Cheeseburger",
    "compatibility_score": 52,
    "safety_score": 40,
    "confidence": "Medium"
  }
]
```

---

## Get Individual Compatibility Report

### GET

```
/api/v1/reports/{report_id}
```

Returns detailed compatibility information.

### Response

```json
{
  "menu_item": "Chicken Bowl",

  "compatibility_score": 94,

  "breakdown": {
    "safety": "No detected allergens",
    "goal_match": "High protein"
  },

  "warnings": [
    "Sauce ingredients unknown"
  ],

  "suggested_modifications": [
    "Remove cheese"
  ],

  "questions_to_ask": [
    "Is the sauce gluten-free?"
  ]
}
```

---

# Future AI Assistant Endpoint

## Chat With Compatibility Report

### POST

```
/api/v1/reports/{report_id}/chat
```

Allows users to ask questions about a recommendation.

Example:

User:

```
Can I make this dairy-free?
```

AI Response:

```
Removing cheese may make this meal compatible with your dairy restriction.
```

---

# Complete API Overview

```
Authentication

POST /auth/register
POST /auth/login


Profile

GET  /profile
PUT  /profile


Analysis

POST /analysis/upload
GET  /analysis/{id}


Compatibility

GET /analysis/{id}/reports
GET /reports/{id}


Future

POST /reports/{id}/chat
```

---

# Request Lifecycle Example

When a user uploads a menu:

```
1. User uploads image through React

          ↓

2. Frontend sends POST /analysis/upload

          ↓

3. FastAPI creates Analysis record

          ↓

4. Vision Service extracts menu information

          ↓

5. Compatibility Engine evaluates menu items

          ↓

6. Compatibility Reports are stored

          ↓

7. Frontend retrieves reports

          ↓

8. User views Compatibility Scores
```

---

# API Design Decisions

## Separate Analysis and Reports

A single upload can contain multiple food items.

Example:

```
Italian Restaurant Menu

Pizza → 80
Pasta → 72
Salad → 95
```

Therefore, one Analysis produces multiple Compatibility Reports.

---

## Asynchronous Processing

AI processing may take time.

Instead of keeping the user waiting, the system uses:

```
Upload
  ↓
Processing
  ↓
Results Available
```

The frontend can check status until the analysis is complete.

---

## API Versioning

Using `/api/v1` allows future versions of the API to evolve without breaking existing applications.

---

# Future Considerations

Potential future API additions:

* Restaurant search
* Saved meals
* Favorite restaurants
* User feedback
* Community corrections
* Nutrition provider integrations
* External developer API
