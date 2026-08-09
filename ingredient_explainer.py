"""Turns a raw (often French, on Open Food Facts) ingredients list into a
short plain-English explanation for an everyday consumer, using Gemini.
Ported from the user's cc.py so it can be called per-product inside the
main Flask app instead of run as a standalone script.

Requires the GEMINI_API_KEY environment variable to be set:
  export GEMINI_API_KEY="your-key-here"        (Mac/Linux)
  setx GEMINI_API_KEY "your-key-here"           (Windows)

If it isn't set, explain_ingredients() returns None instead of raising, so
the rest of the page still renders - the Ingredients box just falls back to
showing the raw ingredients text.
"""

import os

from google import genai
from google.genai import types

_API_KEY = os.environ.get("GEMINI_API_KEY")
_client = genai.Client(api_key=_API_KEY) if _API_KEY else None

_SYSTEM_INSTRUCTION = (
    "Reply in exactly 50 words or fewer, in English, even if the "
    "ingredients list is in another language (e.g. French, as Open Food "
    "Facts often provides). Be clear and simple, no jargon."
)


def explain_ingredients(ingredients_text: str):
    """Returns a short English explanation, or None if there's no API key
    configured or the text is missing."""
    if not _client or not ingredients_text or ingredients_text == "N/A":
        return None

    response = _client.models.generate_content(
        model="gemini-3.5-flash",
        contents=(
            "Explain these food ingredients in simple terms for an "
            f"everyday consumer:\n\n{ingredients_text}"
        ),
        config=types.GenerateContentConfig(system_instruction=_SYSTEM_INSTRUCTION),
    )
    return response.text.strip()
