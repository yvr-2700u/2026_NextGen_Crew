"""Age-wise nutrition warning table (Children / Adults / Elderly / Diabetics)
for Sugar, Salt, and Saturated Fat. Ported from the user's second app.py so
it can be called per-product inside the main Flask app.
"""

LIMITS = {
    "Sugar": {
        "Children": (10, 5),
        "Adults": (15, 5),
        "Elderly": (12, 5),
        "Diabetics": (5, 2.5),
    },
    "Salt": {
        "Children": (0.6, 0.3),
        "Adults": (1.25, 0.3),
        "Elderly": (1.0, 0.3),
        "Diabetics": (1.25, 0.3),
    },
    "Saturated Fat": {
        "Children": (4, 1.5),
        "Adults": (5, 1.5),
        "Elderly": (4.5, 1.5),
        "Diabetics": (4, 1.5),
    },
}

AGE_GROUPS = ["Children", "Adults", "Elderly", "Diabetics"]


def get_level(value, high, moderate):
    """Returns (label, css_class). 'N/A' when the nutrient wasn't reported
    at all, rather than silently treating missing data as LOW."""
    if value is None:
        return "N/A", "unknown"

    value = float(value)

    if value > high:
        return "HIGH", "high"
    elif value > moderate:
        return "MODERATE", "moderate"
    else:
        return "LOW", "low"


def get_nutrition_warnings(nutriments):
    """nutriments is the raw Open Food Facts 'nutriments' dict (per 100g)."""
    nutrient_values = {
        "Sugar": nutriments.get("sugars_100g"),
        "Salt": nutriments.get("salt_100g"),
        "Saturated Fat": nutriments.get("saturated-fat_100g"),
    }

    warnings = {}

    for nutrient, value in nutrient_values.items():
        warnings[nutrient] = {}
        for age, limits in LIMITS[nutrient].items():
            level, css = get_level(value, limits[0], limits[1])
            warnings[nutrient][age] = {"text": level, "class": css}

    return warnings
