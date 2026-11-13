# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import uuid
from typing import Any, Dict, List, Optional
from google.cloud import firestore, storage
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

MODEL = "gemini-3.8-flash"

# Hardcoded project ID string for Firestore and Cloud Storage
# Do NOT read from google.auth.default() or GOOGLE_CLOUD_PROJECT
PROJECT_ID = "qwiklabs-gcp-04-e95c51324d8a"
FIRESTORE_PROJECT = "qwiklabs-gcp-04-e95c51324d8a"
GCS_BUCKET_NAME = "recipe-concierge-assets-qwiklabs-gcp-04-e95c51324d8a"

_db: Optional[firestore.Client] = None
_storage_client: Optional[storage.Client] = None
_genai_client: Optional[genai.Client] = None

def get_firestore_client() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=FIRESTORE_PROJECT)
    return _db

def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client

def get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
    return _genai_client


def list_recipes(cuisine: Optional[str] = None, dietary_tag: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """List or search recipes from the recipe catalog in Firestore.

    Args:
        cuisine: Optional filter by cuisine (e.g. 'Mediterranean', 'Italian', 'Thai').
        dietary_tag: Optional filter by dietary tag (e.g. 'gluten-free', 'vegan', 'vegetarian').
        limit: Maximum number of recipes to return (default 10).

    Returns:
        A list of recipe summaries including id, title, cuisine, prep/cook times, and dietary tags.
    """
    db = get_firestore_client()
    recipes_ref = db.collection("recipes")
    docs = recipes_ref.limit(50).stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        
        # Apply filters in Python to allow flexible multi-tag querying
        if cuisine and cuisine.lower() not in data.get("cuisine", "").lower():
            continue
        if dietary_tag:
            tags = [t.lower() for t in data.get("dietary_tags", [])]
            if dietary_tag.lower() not in tags:
                continue

        results.append({
            "id": data.get("id"),
            "title": data.get("title"),
            "cuisine": data.get("cuisine"),
            "prep_time_minutes": data.get("prep_time_minutes"),
            "cook_time_minutes": data.get("cook_time_minutes"),
            "difficulty": data.get("difficulty"),
            "dietary_tags": data.get("dietary_tags", []),
            "servings": data.get("servings"),
        })
        if len(results) >= limit:
            break

    return results


def get_recipe_details(recipe_id: str) -> Dict[str, Any]:
    """Get complete details for a specific recipe including ingredients, instructions, and nutrition.

    Args:
        recipe_id: The unique identifier of the recipe (e.g. 'lemon-herb-roast-chicken', 'spicy-thai-basil-tofu-stir-fry').

    Returns:
        The full recipe object or an error message if not found.
    """
    db = get_firestore_client()
    doc = db.collection("recipes").document(recipe_id).get()
    if not doc.exists:
        return {"error": f"Recipe with id '{recipe_id}' not found."}
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def save_recipe(
    title: str,
    cuisine: str,
    servings: int,
    prep_time_minutes: int,
    cook_time_minutes: int,
    difficulty: str,
    dietary_tags: List[str],
    ingredients: List[Dict[str, Any]],
    instructions: List[str],
    calories_per_serving: Optional[int] = None,
) -> Dict[str, Any]:
    """Save or create a new recipe in the Firestore recipe catalog.

    Args:
        title: Title of the recipe (e.g. 'Crispy Garlic Tofu').
        cuisine: Cuisine type (e.g. 'Asian', 'Mediterranean', 'Mexican').
        servings: Number of servings.
        prep_time_minutes: Preparation time in minutes.
        cook_time_minutes: Cooking time in minutes.
        difficulty: Difficulty level ('easy', 'medium', 'hard').
        dietary_tags: List of tags such as ['vegan', 'gluten-free'].
        ingredients: List of ingredient dicts with 'item', 'amount', 'unit'.
        instructions: Step-by-step preparation and cooking instructions.
        calories_per_serving: Optional estimated calories per serving.

    Returns:
        A confirmation dict with the created recipe id and status.
    """
    db = get_firestore_client()
    # Generate slug ID from title
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    recipe_id = slug or "custom-recipe"

    recipe_data = {
        "id": recipe_id,
        "title": title,
        "cuisine": cuisine,
        "servings": servings,
        "prep_time_minutes": prep_time_minutes,
        "cook_time_minutes": cook_time_minutes,
        "difficulty": difficulty,
        "dietary_tags": dietary_tags,
        "ingredients": ingredients,
        "instructions": instructions,
        "nutrition_per_serving": {
            "calories": calories_per_serving if calories_per_serving is not None else 0
        },
    }

    db.collection("recipes").document(recipe_id).set(recipe_data)
    return {"status": "success", "recipe_id": recipe_id, "message": f"Recipe '{title}' saved successfully."}


def scale_recipe_servings(recipe_id: str, target_servings: int) -> Dict[str, Any]:
    """Scales all ingredient amounts of an existing recipe in Firestore to a target number of servings.

    Args:
        recipe_id: Unique recipe ID (e.g. 'creamy-tuscan-white-bean-skillet', 'lemon-herb-roast-chicken').
        target_servings: Desired number of servings (must be >= 1).

    Returns:
        A dictionary with original servings, target servings, scaling factor, and scaled ingredients list.
    """
    if target_servings < 1:
        return {"error": "Target servings must be at least 1."}

    recipe = get_recipe_details(recipe_id)
    if "error" in recipe:
        return recipe

    original_servings = recipe.get("servings", 1) or 1
    scale_factor = target_servings / original_servings

    scaled_ingredients = []
    for ing in recipe.get("ingredients", []):
        amount = ing.get("amount")
        unit = ing.get("unit", "")
        item = ing.get("item", "")

        if isinstance(amount, (int, float)):
            scaled_amount = round(amount * scale_factor, 2)
            # Clean display for whole numbers
            if scaled_amount == int(scaled_amount):
                scaled_amount = int(scaled_amount)
        else:
            scaled_amount = amount

        scaled_ingredients.append({
            "item": item,
            "original_amount": amount,
            "scaled_amount": scaled_amount,
            "unit": unit,
        })

    nutrition = recipe.get("nutrition_per_serving", {})

    return {
        "recipe_id": recipe_id,
        "title": recipe.get("title"),
        "original_servings": original_servings,
        "target_servings": target_servings,
        "scale_factor": round(scale_factor, 2),
        "scaled_ingredients": scaled_ingredients,
        "instructions": recipe.get("instructions", []),
        "nutrition_per_serving": nutrition,
    }


def search_online_recipes(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search for real recipes from an open online culinary database (TheMealDB).
    Use this when the user is searching for inspiration or recipes not currently in their local Firestore catalog.

    Args:
        query: Recipe or dish name to search for (e.g. 'pasta', 'curry', 'salmon', 'taco').
        limit: Maximum number of results to return (default 5).

    Returns:
        A list of matching recipe summaries with name, category, cuisine area, instructions, and ingredients.
    """
    import os
    import urllib.parse
    import urllib.request
    import json

    # Read API key from environment variable if provided, else use default free test tier '1'
    api_key = os.getenv("MEALDB_API_KEY", "1")
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php?s={encoded_query}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RecipeConcierge/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        return [{"error": f"Failed to fetch recipes from external database: {str(e)}"}]

    meals = data.get("meals")
    if not meals:
        return [{"message": f"No online recipes found matching '{query}'."}]

    results = []
    for meal in meals[:limit]:
        # Extract ingredients and measures
        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if ing and ing.strip():
                ingredients.append(f"{measure.strip() if measure else ''} {ing.strip()}".strip())

        results.append({
            "id": meal.get("idMeal"),
            "name": meal.get("strMeal"),
            "category": meal.get("strCategory"),
            "cuisine": meal.get("strArea"),
            "instructions": meal.get("strInstructions", "").strip(),
            "ingredients": ingredients,
            "thumbnail_url": meal.get("strMealThumb"),
        })

    return results


def generate_dish_image(
    dish_name: str,
    presentation_details: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Generates a high-quality culinary visual for a dish using gemini-3.1-flash-lite-image,
    saves it to the session artifacts for Playground viewing, uploads it directly to public Cloud Storage,
    and returns its public HTTPS URL.

    Args:
        dish_name: Name of the dish or recipe (e.g. 'Avocado & Quinoa Power Bowl', 'Lemon Herb Roasted Chicken').
        presentation_details: Optional extra visual styling (e.g. 'garnished with microgreens on a dark ceramic plate').
        tool_context: ADK ToolContext injected automatically by the runtime.

    Returns:
        A dict with the public image URL, artifact filename, and generation status.
    """
    client = get_genai_client()
    prompt = f"Professional appetizing food photography of {dish_name}"
    if presentation_details:
        prompt += f", {presentation_details}"
    prompt += ", beautifully plated, warm natural lighting, high resolution 1K"

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=[types.Modality.TEXT, types.Modality.IMAGE],
            ),
        )
    except Exception as e:
        return {"error": f"Image generation failed: {str(e)}"}

    image_bytes = None
    mime_type = "image/jpeg"
    if response.candidates and response.candidates[0].content:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                break

    if not image_bytes:
        return {"error": "Model did not return any image data."}

    # Generate a clean unique filename
    slug = re.sub(r'[^a-z0-9]+', '-', dish_name.lower()).strip('-')[:30]
    filename = f"{slug}-{uuid.uuid4().hex[:8]}.jpg"

    # 1. Save artifact so it shows up in Playground's Artifacts panel
    if tool_context is not None:
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception as e:
            # Non-fatal if context artifact saving fails
            pass

    # 2. Upload image bytes to public Cloud Storage bucket
    try:
        storage_client = get_storage_client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(f"dishes/{filename}")
        blob.upload_from_string(image_bytes, content_type=mime_type)
        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/dishes/{filename}"
    except Exception as e:
        return {"error": f"Failed to upload image to Cloud Storage: {str(e)}"}

    return {
        "status": "success",
        "dish_name": dish_name,
        "artifact_filename": filename,
        "public_url": public_url,
        "message": f"Generated image for '{dish_name}' and published to Cloud Storage.",
    }


AGENT_ENGINE_ID = "projects/640123829561/locations/us-east1/reasoningEngines/1108086718961025024"
SANDBOX_RESOURCE_NAME = "projects/640123829561/locations/us-east1/reasoningEngines/1108086718961025024/sandboxEnvironments/8321908841520300032"


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, send the session to Memory Bank for extraction."""
    try:
        await callback_context.add_session_to_memory()
    except ValueError as e:
        if "memory service is not available" in str(e).lower():
            pass
        else:
            raise
    return None


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are Recipe Concierge, a helpful and knowledgeable culinary assistant. "
        "CRITICAL FOR USER SAFETY: You must always remember, track, and strictly honor all user allergies and food intolerances "
        "(e.g., peanuts, tree nuts, dairy/lactose, gluten/celiac, shellfish, soy, eggs, etc.) across all conversations. "
        "Whenever a user mentions any allergy, intolerance, or medical dietary restriction, commit it to memory and never "
        "suggest, include, or substitute any ingredient containing that allergen. "
        "You also remember general dietary preferences, favorite ingredients, and cooking habits from previous conversations "
        "to proactively personalize all your meal suggestions and recipes. "
        "You help home cooks discover recipes, plan meals according to dietary preferences, "
        "scale recipes to any target serving size, look up cooking instructions, and save custom recipes. "
        "You can search local saved recipes with list_recipes, explore dishes from the web with search_online_recipes, "
        "and generate photorealistic visuals of any dish using generate_dish_image. "
        "You can also write and execute Python code in your secure Agent Engine Sandbox to perform precise recipe conversions, "
        "unit calculations, complex nutrition math, or meal planning optimizations."
    ),
    tools=[
        PreloadMemoryTool(),
        list_recipes,
        get_recipe_details,
        scale_recipe_servings,
        save_recipe,
        search_online_recipes,
        generate_dish_image,
    ],
    code_executor=AgentEngineSandboxCodeExecutor(
        sandbox_resource_name=SANDBOX_RESOURCE_NAME,
        agent_engine_resource_name=AGENT_ENGINE_ID,
    ),
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
