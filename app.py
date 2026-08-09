import logging
import time

from flask import Flask, render_template, request, jsonify
from PIL import Image
from pyzbar.pyzbar import decode
import requests
import os

from health_score import score_from_product
from nutrition_warning import get_nutrition_warnings
from alternative_finder import get_alternative_and_comparison
from ingredient_explainer import explain_ingredients

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "FoodScanner/1.0 (com)"

}

SUGGEST_TIMEOUT = 8
SUGGEST_MAX_RETRIES = 2
SUGGEST_RETRY_BACKOFF_SECONDS = 1


@app.route("/suggest")
def suggest():

    query = request.args.get("q", "").strip()

    if len(query) < 2:
        return jsonify([])

    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 10,
        "fields": "code,product_name,brands,image_front_url"
    }

    data = None
    last_error = None

    for attempt in range(1, SUGGEST_MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=SUGGEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            break
        except Exception as e:
            last_error = e
            logger.warning(
                "/suggest: request failed for q=%r (attempt %s/%s): %s",
                query, attempt, SUGGEST_MAX_RETRIES, e
            )
            if attempt < SUGGEST_MAX_RETRIES:
                time.sleep(SUGGEST_RETRY_BACKOFF_SECONDS)

    if data is None:
        logger.error("/suggest: giving up for q=%r: %s", query, last_error)
        return jsonify([])

    suggestions = []
    seen_codes = set()

    for p in data.get("products", []):
        name = (p.get("product_name") or "").strip()
        code = (p.get("code") or "").strip()

        if not name or not code or code in seen_codes:
            continue

        seen_codes.add(code)
        suggestions.append({
            "code": code,
            "name": name,
            "brand": (p.get("brands") or "").strip(),
            "image": p.get("image_front_url", "")
        })

    return jsonify(suggestions[:10])


def format_product(product):
    nutriments = product.get("nutriments", {})
    return {
        "name": product.get("product_name", "N/A"),
        "brand": product.get("brands", "N/A"),
        "barcode": product.get("code", "N/A"),
        "ecoscore": (product.get("ecoscore_grade") or "N/A").upper(),
        "nova_group": product.get("nova_group", "N/A"),
        "country": product.get("countries", "N/A"),
        "category": product.get("categories", "N/A"),
        "image": product.get("image_front_url", ""),
        "ingredients": product.get("ingredients_text", "N/A"),
        "nutriscore": (product.get("nutriscore_grade") or "N/A").upper(),
        "calories": nutriments.get("energy-kcal_100g", "N/A"),
        "protein": nutriments.get("proteins_100g", "N/A"),
        "carbs": nutriments.get("carbohydrates_100g", "N/A"),
        "sugar": nutriments.get("sugars_100g", "N/A"),
        "fat": nutriments.get("fat_100g", "N/A"),
        "fiber": nutriments.get("fiber_100g", "N/A"),
        "salt": nutriments.get("salt_100g", "N/A"),
    }


def analyze_product(raw_product):
    """Runs format_product() plus the health score, age-wise nutrition
    warnings, and healthier-alternative lookup on a raw Open Food Facts
    product dict. Each extra piece is wrapped so a failure in one (e.g. the
    alternative search having no network) doesn't blank out the rest."""
    data = format_product(raw_product)

    try:
        data["health_score"] = score_from_product(raw_product)
    except Exception:
        logger.exception("health_score failed")
        data["health_score"] = None

    try:
        data["warnings"] = get_nutrition_warnings(raw_product.get("nutriments", {}))
    except Exception:
        logger.exception("get_nutrition_warnings failed")
        data["warnings"] = None

    try:
        result = get_alternative_and_comparison(raw_product)
        if result and result.get("search_unavailable"):
            data["alternative"] = None
            data["alternative_search_unavailable"] = True
        else:
            data["alternative"] = result
            data["alternative_search_unavailable"] = False
    except Exception:
        logger.exception("get_alternative_and_comparison failed")
        data["alternative"] = None
        data["alternative_search_unavailable"] = False

    try:
        data["ingredients_explained"] = explain_ingredients(data["ingredients"])
    except Exception:
        logger.exception("explain_ingredients failed")
        data["ingredients_explained"] = None

    return data


@app.route("/", methods=["GET", "POST"])
def home():
    product_data = {}

    if request.method == "POST":

        # Barcode entered manually (optional)
        barcode = request.form.get("barcode", "").strip()

        # Search by Product Name
        product_name = request.form.get("product_name", "").strip()

        if product_name:
            url = "https://world.openfoodfacts.org/cgi/search.pl"
            params = {
                "search_terms": product_name,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 1
            }

            try:
                response = requests.get(url, headers=HEADERS, params=params, timeout=10)

                if response.status_code != 200:
                    product_data = {
                        "name": f"API Error: HTTP {response.status_code}"
                    }
                else:
                    try:
                        data = response.json()
                        products = data.get("products") or []

                        if products:
                            product_data = analyze_product(products[0])
                        else:
                            product_data = {
                                "name": "Product not found."
                            }

                    except ValueError:
                        product_data = {
                            "name": "Invalid response received from OpenFoodFacts API."
                        }

            except Exception as e:
                product_data = {
                    "name": f"API Error: {e}"
                }

        else:
            # If no barcode entered, try uploaded image
            if barcode == "":
                file = request.files.get("barcode_image")

                if file and file.filename != "":
                    filename = "barcode.png"
                    file.save(filename)

                    try:
                        image = Image.open(filename).convert("RGB")
                        detected = decode(image)

                        if detected:
                            barcode = detected[0].data.decode("utf-8")
                            print("Detected Barcode:", barcode)
                        else:
                            product_data = {
                                "name": "No barcode detected in image."
                            }

                    except Exception as e:
                        product_data = {
                            "name": f"Error reading image: {e}"
                        }

                    if os.path.exists(filename):
                        os.remove(filename)

            # Search product if barcode found
            if barcode:
                url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

                try:
                    response = requests.get(url, headers=HEADERS, timeout=10)
                    data = response.json()

                    if data.get("status") == 1:
                        product_data = analyze_product(data["product"])
                    else:
                        product_data = {
                            "name": "Product not found.",
                            "brand": "", "country": "", "category": "",
                            "image": "", "ingredients": "", "nutriscore": "",
                            "calories": "", "protein": "", "carbs": "",
                            "sugar": "", "fat": "", "fiber": "", "salt": "",
                            "nova_group": ""
                        }

                except Exception as e:
                    product_data = {
                        "name": f"API Error: {e}"
                    }

    return render_template("index.html", product=product_data)


if __name__ == "__main__":
    app.run(debug=True)
