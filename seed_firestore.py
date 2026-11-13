#!/usr/bin/env python3
"""Seed script for Firestore recipe catalog."""
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-e95c51324d8a"

RECIPES = [
    {
        "id": "lemon-herb-roast-chicken",
        "title": "Lemon Herb Roasted Chicken",
        "cuisine": "Mediterranean",
        "servings": 4,
        "prep_time_minutes": 15,
        "cook_time_minutes": 50,
        "difficulty": "easy",
        "dietary_tags": ["gluten-free", "high-protein", "dairy-free"],
        "ingredients": [
            {"item": "chicken thighs", "amount": 4, "unit": "pieces"},
            {"item": "lemon", "amount": 2, "unit": "whole"},
            {"item": "olive oil", "amount": 2, "unit": "tbsp"},
            {"item": "fresh rosemary", "amount": 2, "unit": "sprigs"},
            {"item": "garlic", "amount": 4, "unit": "cloves"},
            {"item": "sea salt", "amount": 1, "unit": "tsp"},
            {"item": "black pepper", "amount": 0.5, "unit": "tsp"},
        ],
        "instructions": [
            "Preheat oven to 400°F (200°C).",
            "Pat chicken thighs dry with paper towels.",
            "Toss chicken with olive oil, minced garlic, chopped rosemary, salt, and pepper.",
            "Arrange in baking dish with lemon slices tucked around.",
            "Roast for 45-50 minutes until skin is crisp and internal temperature hits 165°F.",
        ],
        "nutrition_per_serving": {
            "calories": 420,
            "protein_g": 36,
            "carbs_g": 4,
            "fat_g": 28,
        },
    },
    {
        "id": "creamy-tuscan-white-bean-skillet",
        "title": "Creamy Tuscan White Bean Skillet",
        "cuisine": "Italian",
        "servings": 2,
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "difficulty": "easy",
        "dietary_tags": ["vegetarian", "gluten-free", "high-fiber"],
        "ingredients": [
            {"item": "cannellini beans", "amount": 1, "unit": "can (15 oz)"},
            {"item": "sun-dried tomatoes", "amount": 0.33, "unit": "cup"},
            {"item": "baby spinach", "amount": 2, "unit": "cups"},
            {"item": "coconut milk or heavy cream", "amount": 0.5, "unit": "cup"},
            {"item": "garlic", "amount": 3, "unit": "cloves"},
            {"item": "vegetable broth", "amount": 0.25, "unit": "cup"},
            {"item": "parmesan or nutritional yeast", "amount": 2, "unit": "tbsp"},
        ],
        "instructions": [
            "Sauté minced garlic and sliced sun-dried tomatoes in 1 tbsp olive oil for 1-2 minutes.",
            "Add rinsed cannellini beans and vegetable broth, simmering for 3 minutes.",
            "Stir in cream and spinach; simmer until spinach wilts and sauce thickens.",
            "Season with salt, freshly cracked pepper, and parmesan.",
        ],
        "nutrition_per_serving": {
            "calories": 340,
            "protein_g": 14,
            "carbs_g": 38,
            "fat_g": 16,
        },
    },
    {
        "id": "spicy-thai-basil-tofu-stir-fry",
        "title": "Spicy Thai Basil Tofu Stir-Fry",
        "cuisine": "Thai",
        "servings": 2,
        "prep_time_minutes": 15,
        "cook_time_minutes": 10,
        "difficulty": "medium",
        "dietary_tags": ["vegan", "dairy-free", "vegetarian"],
        "ingredients": [
            {"item": "extra firm tofu", "amount": 14, "unit": "oz"},
            {"item": "Thai basil leaves", "amount": 1, "unit": "cup"},
            {"item": "garlic", "amount": 4, "unit": "cloves"},
            {"item": "Thai bird's eye chili", "amount": 2, "unit": "chilis"},
            {"item": "tamari or soy sauce", "amount": 2, "unit": "tbsp"},
            {"item": "maple syrup", "amount": 1, "unit": "tsp"},
            {"item": "bell pepper", "amount": 1, "unit": "sliced"},
        ],
        "instructions": [
            "Press tofu to drain excess moisture and crumble into bite-sized pieces.",
            "Heat oil in wok over high heat; stir-fry minced garlic and chilies until fragrant (30 seconds).",
            "Add crumbled tofu and sliced bell pepper; cook until edges brown (5-6 minutes).",
            "Pour in sauce mixture and toss. Remove from heat and immediately fold in fresh Thai basil until wilted.",
        ],
        "nutrition_per_serving": {
            "calories": 290,
            "protein_g": 20,
            "carbs_g": 12,
            "fat_g": 18,
        },
    },
    {
        "id": "avocado-quinoa-power-bowl",
        "title": "Avocado & Quinoa Power Bowl",
        "cuisine": "Contemporary",
        "servings": 2,
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "difficulty": "easy",
        "dietary_tags": ["vegan", "gluten-free", "healthy"],
        "ingredients": [
            {"item": "quinoa", "amount": 1, "unit": "cup cooked"},
            {"item": "avocado", "amount": 1, "unit": "diced"},
            {"item": "cucumber", "amount": 1, "unit": "diced"},
            {"item": "cherry tomatoes", "amount": 1, "unit": "cup halved"},
            {"item": "tahini lemon dressing", "amount": 3, "unit": "tbsp"},
            {"item": "roasted pumpkin seeds", "amount": 2, "unit": "tbsp"},
        ],
        "instructions": [
            "Divide warm or chilled cooked quinoa between two bowls.",
            "Arrange diced avocado, cucumber, and cherry tomatoes neatly on top.",
            "Drizzle generously with tahini lemon dressing.",
            "Top with toasted pumpkin seeds and flaky sea salt.",
        ],
        "nutrition_per_serving": {
            "calories": 380,
            "protein_g": 11,
            "carbs_g": 42,
            "fat_g": 22,
        },
    },
]

def seed():
    print(f"Connecting to Firestore with hardcoded PROJECT_ID: {PROJECT_ID}")
    db = firestore.Client(project=PROJECT_ID)
    recipes_ref = db.collection("recipes")
    for recipe in RECIPES:
        doc_id = recipe["id"]
        recipes_ref.document(doc_id).set(recipe)
        print(f"✓ Seeded recipe: {doc_id} ('{recipe['title']}')")
    print("Done seeding Firestore!")

if __name__ == "__main__":
    seed()
