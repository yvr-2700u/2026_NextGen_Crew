"""Finds a healthier same-category alternative on Open Food Facts and builds
a side-by-side comparison. Ported from the user's
food_best_alternative_with_images.py, with print statements replaced by
return values, and a plain-language 'reason' generated locally (no external
AI call needed) so this works without any API key.

Reliability notes (why this used to work "sometimes"):
- Only the MOST SPECIFIC category tag was searched. Niche categories often
  have zero same-category products, so this silently returned "no
  alternative" for a large chunk of products. We now fall back through
  categories from most-specific to broadest.
- The India country filter could wipe out all candidates for a category
  that simply has no Indian-tagged products indexed. We now retry without
  it if the filtered search comes back empty.
- Missing nutrient fields default to 0, which used to look like a genuine
  improvement (0 < real_value). We now only count a metric if BOTH products
  actually report it.
- Network hiccups/rate limits used to look identical to "no candidates
  found". We now retry once and log failures instead of swallowing them.
"""

import logging
import time

import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "MyNutritionProject/2.0 (briil.com)"
}

BASE_URL = "https://world.openfoodfacts.org"

REQUEST_TIMEOUT = 12
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 1.5


class SearchBackendUnavailable(Exception):
    """Raised when Open Food Facts' search backend itself appears to be
    down (5xx / connection failure), as opposed to a normal 'no matching
    products' result. As of mid-2026 the legacy search backend that powers
    both /cgi/search.pl and /api/v2/search has been intermittently (and
    sometimes globally) returning 503s - this is an upstream OFF issue, not
    something retries on our side can fix. Distinguishing this lets the UI
    say 'search is temporarily unavailable' instead of the misleading
    'no healthier alternative was found'."""
    pass


def get_number(value, default=0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def nutrition(product):
    n = product.get("nutriments", {})
    return {
        "calories": get_number(n.get("energy-kcal_100g")),
        "protein": get_number(n.get("proteins_100g")),
        "sugar": get_number(n.get("sugars_100g")),
        "fat": get_number(n.get("fat_100g")),
        "sat_fat": get_number(n.get("saturated-fat_100g")),
        "salt": get_number(n.get("salt_100g")),
    }


def has_value(product, field):
    """True only if the product actually reports this nutrient (as opposed
    to it defaulting to 0 because the field was missing)."""
    n = product.get("nutriments", {})
    raw = n.get(field)
    return raw is not None and raw != ""


def nutriscore_value(grade):
    """Higher = better."""
    values = {"a": 5, "b": 4, "c": 3, "d": 2, "e": 1}
    return values.get(str(grade).lower(), 0)


def get_categories_by_specificity(product):
    """Returns cleaned category tags ordered from MOST specific to LEAST
    specific (Open Food Facts stores them broad -> narrow, so we reverse)."""
    categories = product.get("categories_tags_en") or []

    if not categories:
        text = product.get("categories", "")
        if text:
            categories = [x.strip() for x in text.split(",") if x.strip()]

    if not categories:
        return []

    cleaned = []
    for category in categories:
        category = str(category).strip().lower()
        if category.startswith("en:"):
            category = category[3:]
        if category and category not in cleaned:
            cleaned.append(category)

    return list(reversed(cleaned))


def _request_with_retry(url, params):
    last_error = None
    backend_down = False

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if response.status_code >= 500:
                backend_down = True
                last_error = requests.exceptions.HTTPError(
                    f"{response.status_code} server error from Open Food Facts search"
                )
                logger.warning(
                    "alternative_finder: OFF search backend returned %s (attempt %s/%s) - "
                    "this is an upstream outage, not a local bug",
                    response.status_code, attempt, MAX_RETRIES
                )
            else:
                response.raise_for_status()
                return response.json()
        except requests.exceptions.ConnectionError as e:
            backend_down = True
            last_error = e
            logger.warning(
                "alternative_finder: could not reach OFF search backend (attempt %s/%s): %s",
                attempt, MAX_RETRIES, e
            )
        except requests.exceptions.RequestException as e:
            last_error = e
            logger.warning(
                "alternative_finder: request failed (attempt %s/%s): %s",
                attempt, MAX_RETRIES, e
            )

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF_SECONDS)

    if backend_down:
        raise SearchBackendUnavailable(str(last_error))
    raise last_error


def search_same_category(category, current_code, restrict_to_india=True):
    if not category:
        return []

    url = f"{BASE_URL}/api/v2/search"
    params = {
        "categories_tags_en": category,
        "page": 1,
        "page_size": 50,
        "fields": (
            "code,product_name,brands,categories_tags_en,"
            "nutriscore_grade,nova_group,nutriments,image_front_url"
        ),
    }
    if restrict_to_india:
        params["countries_tags_en"] = "india"

    data = _request_with_retry(url, params)
    products = data.get("products", [])

    return [
        p for p in products
        if p.get("code") != current_code and p.get("product_name")
    ]


def better_than_current(candidate, current):
    c = nutrition(current)
    p = nutrition(candidate)
    improvements = 0

    if has_value(current, "sugars_100g") and has_value(candidate, "sugars_100g") and p["sugar"] < c["sugar"]:
        improvements += 1
    if has_value(current, "salt_100g") and has_value(candidate, "salt_100g") and p["salt"] < c["salt"]:
        improvements += 1
    if has_value(current, "saturated-fat_100g") and has_value(candidate, "saturated-fat_100g") and p["sat_fat"] < c["sat_fat"]:
        improvements += 1
    if has_value(current, "fat_100g") and has_value(candidate, "fat_100g") and p["fat"] < c["fat"]:
        improvements += 1
    if has_value(current, "proteins_100g") and has_value(candidate, "proteins_100g") and p["protein"] > c["protein"]:
        improvements += 1
    if nutriscore_value(candidate.get("nutriscore_grade")) > nutriscore_value(current.get("nutriscore_grade")):
        improvements += 1

    return improvements >= 2


def recommendation_score(candidate, current):
    c = nutrition(current)
    p = nutrition(candidate)
    score = 0

    if has_value(current, "sugars_100g") and has_value(candidate, "sugars_100g") and p["sugar"] < c["sugar"]:
        score += 3
    if has_value(current, "salt_100g") and has_value(candidate, "salt_100g") and p["salt"] < c["salt"]:
        score += 3
    if has_value(current, "saturated-fat_100g") and has_value(candidate, "saturated-fat_100g") and p["sat_fat"] < c["sat_fat"]:
        score += 3
    if has_value(current, "fat_100g") and has_value(candidate, "fat_100g") and p["fat"] < c["fat"]:
        score += 2
    if has_value(current, "energy-kcal_100g") and has_value(candidate, "energy-kcal_100g") and p["calories"] < c["calories"]:
        score += 1
    if has_value(current, "proteins_100g") and has_value(candidate, "proteins_100g") and p["protein"] > c["protein"]:
        score += 2

    candidate_grade = nutriscore_value(candidate.get("nutriscore_grade"))
    current_grade = nutriscore_value(current.get("nutriscore_grade"))
    if candidate_grade > current_grade:
        score += 5
    elif candidate_grade == current_grade and candidate_grade != 0:
        score += 1

    available = sum([p["sugar"] > 0, p["salt"] > 0, p["fat"] > 0, p["protein"] > 0])
    score += available

    return score


def _usable_candidates(candidates, current):
    usable = []
    for candidate in candidates:
        if not candidate.get("nutriments"):
            continue
        if better_than_current(candidate, current):
            candidate["_recommendation_score"] = recommendation_score(candidate, current)
            usable.append(candidate)
    return usable


def find_best_alternative(current):
    """Returns the highest-scoring same-category product, or None.

    Tries categories from most specific to broadest, and for each one tries
    an India-only search first, then falls back to a global search if that
    comes back empty. This avoids the old behaviour of giving up entirely
    just because the most specific category (or the country filter) had no
    matches for this particular product.
    """
    categories = get_categories_by_specificity(current)
    if not categories:
        return None

    current_code = current.get("code")
    saw_backend_outage = False

    for category in categories:
        for restrict_to_india in (True, False):
            try:
                candidates = search_same_category(category, current_code, restrict_to_india)
            except SearchBackendUnavailable as e:
                # Upstream OFF search is down - no point trying every other
                # category/country combination against a dead backend.
                logger.warning("alternative_finder: OFF search backend unavailable: %s", e)
                saw_backend_outage = True
                break
            except requests.exceptions.RequestException as e:
                logger.warning(
                    "alternative_finder: search failed for category=%r india_only=%s: %s",
                    category, restrict_to_india, e
                )
                continue

            usable = _usable_candidates(candidates, current)
            if usable:
                usable.sort(key=lambda x: x["_recommendation_score"], reverse=True)
                return usable[0]
        else:
            continue
        break

    if saw_backend_outage:
        raise SearchBackendUnavailable("Open Food Facts search backend is currently down")

    return None


def build_reason(candidate, current):
    """Plain-language explanation of why the alternative was picked -
    generated locally from the actual nutrient deltas."""
    c = nutrition(current)
    p = nutrition(candidate)
    points = []

    if has_value(current, "sugars_100g") and has_value(candidate, "sugars_100g") and p["sugar"] < c["sugar"]:
        points.append("less sugar")
    if has_value(current, "salt_100g") and has_value(candidate, "salt_100g") and p["salt"] < c["salt"]:
        points.append("less salt")
    if has_value(current, "saturated-fat_100g") and has_value(candidate, "saturated-fat_100g") and p["sat_fat"] < c["sat_fat"]:
        points.append("less saturated fat")
    if has_value(current, "proteins_100g") and has_value(candidate, "proteins_100g") and p["protein"] > c["protein"]:
        points.append("more protein")
    if nutriscore_value(candidate.get("nutriscore_grade")) > nutriscore_value(current.get("nutriscore_grade")):
        points.append("a better Nutri-Score")

    if not points:
        return "A comparable option in the same category."

    if len(points) == 1:
        joined = points[0]
    else:
        joined = ", ".join(points[:-1]) + " and " + points[-1]

    return f"Has {joined} than the scanned product."


def build_comparison_rows(current, candidate):
    c = nutrition(current)
    p = nutrition(candidate)
    return [
        {"label": "Calories (kcal)", "current": c["calories"], "alternative": p["calories"]},
        {"label": "Protein (g)", "current": c["protein"], "alternative": p["protein"]},
        {"label": "Sugar (g)", "current": c["sugar"], "alternative": p["sugar"]},
        {"label": "Fat (g)", "current": c["fat"], "alternative": p["fat"]},
        {"label": "Saturated Fat (g)", "current": c["sat_fat"], "alternative": p["sat_fat"]},
        {"label": "Salt (g)", "current": c["salt"], "alternative": p["salt"]},
        {
            "label": "Nutri-Score",
            "current": str(current.get("nutriscore_grade", "N/A")).upper(),
            "alternative": str(candidate.get("nutriscore_grade", "N/A")).upper(),
        },
    ]


def get_alternative_and_comparison(current_raw_product):
    """Top-level helper for the Flask app.

    Returns:
      - a dict describing the alternative, if one was found
      - None if the search worked but genuinely found nothing better
      - {"search_unavailable": True} if Open Food Facts' search backend
        itself is down (as opposed to just having no matches) - the
        template should show a distinct, honest message for this case
        rather than "no suitable alternative was found".
    """
    try:
        alternative = find_best_alternative(current_raw_product)
    except SearchBackendUnavailable:
        logger.warning("alternative_finder: search backend unavailable, surfacing to caller")
        return {"search_unavailable": True}
    except Exception:
        logger.exception("alternative_finder: unexpected failure")
        return None

    if not alternative:
        return None

    return {
        "name": alternative.get("product_name", "N/A"),
        "brand": alternative.get("brands", "N/A"),
        "image": alternative.get("image_front_url", ""),
        "reason": build_reason(alternative, current_raw_product),
        "comparison": build_comparison_rows(current_raw_product, alternative),
    }
