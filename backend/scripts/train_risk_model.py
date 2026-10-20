"""Train the late-payment risk model on synthetic data and save it as JSON.

Run from the backend folder with the venv active:
    python -m scripts.train_risk_model
"""

import json

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

from app.risk import (
    FEATURES,
    HIGH_RISK,
    LOW_RISK,
    MIN_HISTORY,
    MODEL_PATH,
    PastCharge,
    band,
    features,
    is_late,
)

N_TENANTS = 800
N_MONTHS = 24
TRAIN_MONTHS = 16  # train on months 1-16, test on months 17-24
SEED = 7


def sigmoid(z: float) -> float:
    return 1 / (1 + np.exp(-z))


def simulate(rng):
    """One row per charge: (month index, features, was it paid late)."""
    rows = []
    for _ in range(N_TENANTS):
        trait = rng.normal(-1.4, 1.0)  # how reliable this tenant is, hidden from the model
        rent = float(rng.uniform(600, 1800))
        hardship = 0.0  # a streak of bad months that fades over time
        history = []
        for m in range(N_MONTHS):
            calendar_month = m % 12 + 1
            hardship = 0.7 * hardship + rng.normal(0, 0.6)
            logit = trait + 0.5 * (rent - 1100) / 500 + hardship
            if calendar_month == 12:
                logit += 0.6
            if rng.random() < sigmoid(logit):
                days_late = 4 + int(rng.poisson(4))
                partial = bool(rng.random() < 0.3)
            else:
                days_late = int(rng.integers(-2, 3))
                partial = False
            if len(history) >= MIN_HISTORY:
                rows.append((m, features(history, rent, calendar_month), int(is_late(days_late))))
            history.append(PastCharge(days_late, partial))
    return rows


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = simulate(rng)
    months = np.array([r[0] for r in rows])
    X = np.array([r[1] for r in rows])
    y = np.array([r[2] for r in rows])
    train = months < TRAIN_MONTHS
    test = ~train

    scaler = StandardScaler().fit(X[train])
    model = LogisticRegression(max_iter=1000).fit(scaler.transform(X[train]), y[train])
    p = model.predict_proba(scaler.transform(X[test]))[:, 1]
    y_test = y[test]
    pred = (p >= HIGH_RISK).astype(int)
    last_late = X[test][:, FEATURES.index("last_late")].astype(int)

    bands = {}
    for name in ("low", "medium", "high"):
        mask = np.array([band(v) == name for v in p])
        bands[name] = {
            "charges": int(mask.sum()),
            "actual_late_rate": round(float(y_test[mask].mean()), 3) if mask.any() else None,
        }

    metrics = {
        "train_charges": int(train.sum()),
        "test_charges": int(test.sum()),
        "late_rate_in_test": round(float(y_test.mean()), 3),
        "roc_auc": round(float(roc_auc_score(y_test, p)), 3),
        "precision_at_0.5": round(float(precision_score(y_test, pred, zero_division=0)), 3),
        "recall_at_0.5": round(float(recall_score(y_test, pred, zero_division=0)), 3),
        "baseline_never_late_accuracy": round(float(1 - y_test.mean()), 3),
        "baseline_last_late_roc_auc": round(float(roc_auc_score(y_test, last_late)), 3),
        "baseline_last_late_precision": round(
            float(precision_score(y_test, last_late, zero_division=0)), 3
        ),
        "baseline_last_late_recall": round(
            float(recall_score(y_test, last_late, zero_division=0)), 3
        ),
        "risk_bands": bands,
        "bands_defined_as": f"low < {LOW_RISK}, medium < {HIGH_RISK}, high >= {HIGH_RISK}",
    }

    payload = {
        "trained_on": "synthetic data (see docs/ml.md)",
        "features": FEATURES,
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coef": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
        "metrics": metrics,
    }
    MODEL_PATH.write_text(json.dumps(payload, indent=2))

    print(f"Saved {MODEL_PATH}")
    for key, value in metrics.items():
        print(f"{key}: {value}")
    print("coefficients (standardised):")
    for name, coef in zip(FEATURES, model.coef_[0], strict=True):
        print(f"  {name}: {coef:+.3f}")


if __name__ == "__main__":
    main()
