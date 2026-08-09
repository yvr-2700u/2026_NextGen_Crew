"""Predicts a 1-100 'Health & Sustainability Score' from Nutri-Score,
NOVA group, and Eco-Score. Ported from the user's hal.py so it can be
imported and reused inside the Flask app instead of run as a standalone
script.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

GRADE_MAP = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}

# Dummy dataset mimicking mapped Open Food Facts values:
# Nutri-Score (1:A to 5:E), NOVA (1 to 4), Eco-Score (1:A to 5:E)
# Target: Overall Health & Sustainability Index (1 to 100)
_TRAINING_DATA = pd.DataFrame(
    [
        {"nutri": 1, "nova": 1, "eco": 1, "target_score": 95},
        {"nutri": 1, "nova": 2, "eco": 2, "target_score": 85},
        {"nutri": 2, "nova": 2, "eco": 2, "target_score": 75},
        {"nutri": 3, "nova": 3, "eco": 3, "target_score": 55},
        {"nutri": 4, "nova": 4, "eco": 4, "target_score": 30},
        {"nutri": 5, "nova": 4, "eco": 5, "target_score": 10},
    ]
)

_X_train = _TRAINING_DATA[["nutri", "nova", "eco"]]
_y_train = _TRAINING_DATA["target_score"]

# Trained once, when this module is first imported.
_model = RandomForestRegressor(n_estimators=100, random_state=42)
_model.fit(_X_train, _y_train)


# Fallback per-component scores, used only when the full 3-feature model
# can't be used because one or more inputs is missing. These approximate
# the same scale the trained model produces for a "typical" product at
# each grade (see _TRAINING_DATA above), so a partial score stays roughly
# consistent with what the full model would have said.
_GRADE_SCORE = {1: 95, 2: 78, 3: 60, 4: 40, 5: 20}   # Nutri-Score / Eco-Score: A..E
_NOVA_SCORE = {1: 90, 2: 70, 3: 45, 4: 20}           # NOVA group: 1..4


def predict_health_score(nutri, nova, eco):
    """Predicts a 1-100 score from Nutri-Score (1-5), NOVA group (1-4), and
    Eco-Score (1-5). Any input can be -1 to mean "missing/invalid".

    - If all three are known, uses the trained RandomForest model.
    - If only some are known, averages the known components' individual
      scores instead of giving up - a product with a good Eco-Score but an
      unknown Nutri-Score still gets a real score, not a 0.
    - If none are known, returns None (nothing to show).
    """
    known = {}
    if nutri != -1:
        known["nutri"] = _GRADE_SCORE.get(nutri, 50)
    if nova != -1:
        known["nova"] = _NOVA_SCORE.get(nova, 50)
    if eco != -1:
        known["eco"] = _GRADE_SCORE.get(eco, 50)

    if not known:
        return None

    if len(known) == 3:
        features = pd.DataFrame([[nutri, nova, eco]], columns=["nutri", "nova", "eco"])
        prediction = _model.predict(features)[0]
        return round(float(np.clip(prediction, 1, 100)), 2)

    # Partial data: average whichever components we actually have.
    average = sum(known.values()) / len(known)
    return round(float(np.clip(average, 1, 100)), 2)


def score_from_product(raw_product):
    """Convenience wrapper: pulls nutriscore/nova/ecoscore straight off an
    Open Food Facts product dict and returns the 0-100 score."""
    nutri_grade = str(raw_product.get("nutriscore_grade", "")).strip().upper()
    eco_grade = str(raw_product.get("ecoscore_grade", "")).strip().upper()

    nova = raw_product.get("nova_group", -1)
    if not isinstance(nova, int):
        nova = -1

    nutri_num = GRADE_MAP.get(nutri_grade, -1)
    eco_num = GRADE_MAP.get(eco_grade, -1)

    return predict_health_score(nutri_num, nova, eco_num)
