# Piece of Mind — Features

This document defines the functional capabilities of Piece of Mind across each planned release. Features are organized by version to maintain a focused development process and prevent unnecessary scope expansion.

---

# Version 1 — Minimum Viable Product (MVP)

## User Accounts

* User registration
* Secure login and logout
* Password encryption
* Persistent user profiles

---

## Personalized Profile

Users can configure:

### Allergies

* Peanut
* Tree Nut
* Dairy
* Egg
* Soy
* Wheat
* Fish
* Shellfish
* Sesame

### Dietary Restrictions

* Celiac Disease
* Gluten-Free
* Vegetarian
* Vegan
* Halal
* Kosher
* Low Sodium

### Nutrition Goals

* Weight Loss
* Muscle Gain
* Maintenance
* High Protein
* Low Carb

### Optional Preferences

* Budget
* Favorite cuisines (future consideration)

---

## Menu Analysis

Users can upload:

* Restaurant menu images
* Nutrition labels
* Ingredient lists

The application will:

* Extract text from images
* Identify menu items
* Parse ingredient information
* Estimate nutrition when necessary

---

## Compatibility Engine

For every menu item, Piece of Mind will evaluate:

* Allergy compatibility
* Dietary restriction compatibility
* Nutrition goal compatibility
* Estimated nutrition
* Confidence level

Each menu item receives an Overall Compatibility Score.

---

## Compatibility Report

Each analyzed item includes:

* Overall Compatibility Score
* Safety assessment
* Estimated nutrition
* Detected allergens
* Goal compatibility
* Suggested modifications
* Questions to ask the restaurant
* AI-generated explanation

---

## User Experience

* Fast analysis
* Mobile-friendly interface
* Clear explanations
* Transparent confidence levels

---

# Version 2

Potential features include:

* QR code menu support
* Barcode scanning
* Saved favorite restaurants
* Saved favorite meals
* Restaurant search
* Meal history
* AI follow-up chat
* Multiple language support

---

# Version 3+

Potential future features:

* Verified restaurant partnerships
* Community-contributed menu corrections
* Grocery shopping assistant
* Travel mode
* Wearable integrations
* Healthcare and dietitian tools
* Personalized nutrition insights
* Family accounts
* Enterprise API

---

# Features Explicitly Out of Scope

The following are intentionally excluded from the MVP:

* Meal photo calorie estimation
* Workout tracking
* Fitness coaching
* Macro tracking
* Social media features
* Food delivery
* Recipe generation

These decisions help keep Version 1 focused on solving one problem exceptionally well: helping users confidently evaluate food compatibility before ordering.
