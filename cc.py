import os
import requests
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# SECURITY NOTE: never hardcode API keys in source files. Set this instead:
#   export GEMINI_API_KEY="your-key-here"        (Mac/Linux)
#   setx GEMINI_API_KEY "your-key-here"           (Windows)
# ---------------------------------------------------------------------------
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise SystemExit("Set the GEMINI_API_KEY environment variable before running this script.")

client = genai.Client(api_key=API_KEY)

headers = {
    "User-Agent": "MyNutritionProject - Version 2.0 - brijeshtorpakwar@gmail.com"
}


def explain_ingredients(ingredients_text: str) -> str:
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=f"Explain these food ingredients in simple terms for an everyday consumer:\n\n{ingredients_text}",
        config=types.GenerateContentConfig(
            system_instruction="Reply in exactly 55 words or fewer. Be clear and simple, no jargon."
        ),
    )
    return response.text.strip()


barcode = "8901719126468"


url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    data = response.json()

    if data.get("status") == 1:
        product = data["product"]

        ingredients_text = product.get("ingredients_text", "N/A")
        print(f"Ingredients         : {ingredients_text}")

        if ingredients_text and ingredients_text != "N/A":
            print("\nGenerating explanation...\n")
            explanation = explain_ingredients(ingredients_text)
            print(f"Explanation (Coco)  : {explanation}")
        else:
            print("\nNo ingredients text available to explain.")

    else:
        print("Product not found in the database.")

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
