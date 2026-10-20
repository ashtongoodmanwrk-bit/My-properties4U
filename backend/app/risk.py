"""Late-payment risk scoring.

The model is trained offline (scripts/train_risk_model.py) and saved as JSON, so the
API only needs plain Python to score a charge. It is a prototype trained on synthetic
data: see docs/ml.md.
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path

GRACE_DAYS = 3  # a charge counts as late if it is paid more than this many days after it is due
MIN_HISTORY = 3  # no score without at least this many earlier charges
LOW_RISK = 0.2
HIGH_RISK = 0.5
MODEL_PATH = Path(__file__).with_name("risk_model.json")

FEATURES = [
    "n_prev",
    "late_rate",
    "late_rate_last3",
    "last_late",
    "mean_days_late_last3",
    "partial_rate",
    "rent_k",
    "is_december",
]


@dataclass(frozen=True)
class PastCharge:
    days_late: int  # days between the due date and the payment that completed the charge
    partial: bool  # the charge needed more than one payment


def is_late(days_late: int) -> bool:
    return days_late > GRACE_DAYS


def can_score(history: list[PastCharge]) -> bool:
    return len(history) >= MIN_HISTORY


def features(history: list[PastCharge], rent: float, due_month: int) -> list[float]:
    """Features for the next charge, from earlier charges only (oldest first)."""
    if not can_score(history):
        raise ValueError(f"need at least {MIN_HISTORY} earlier charges")
    n = len(history)
    late = [is_late(h.days_late) for h in history]
    last3 = history[-3:]
    return [
        float(min(n, 12)),
        sum(late) / n,
        sum(late[-3:]) / len(last3),
        1.0 if late[-1] else 0.0,
        sum(min(max(h.days_late, 0), 30) for h in last3) / len(last3),
        sum(h.partial for h in history) / n,
        rent / 1000,
        1.0 if due_month == 12 else 0.0,
    ]


def load_model(path: Path = MODEL_PATH) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def probability(model: dict, x: list[float]) -> float:
    z = model["intercept"]
    for value, mean, scale, coef in zip(
        x, model["mean"], model["scale"], model["coef"], strict=True
    ):
        z += coef * (value - mean) / scale
    return 1 / (1 + math.exp(-z))


def band(p: float) -> str:
    if p < LOW_RISK:
        return "low"
    if p < HIGH_RISK:
        return "medium"
    return "high"
