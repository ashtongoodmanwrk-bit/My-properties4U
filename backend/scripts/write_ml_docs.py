"""Write docs/ml.md from the saved model, so every number in it comes from the training run.

Run from the backend folder with the venv active:
    python -m scripts.write_ml_docs
"""

import json
from pathlib import Path

from app.risk import GRACE_DAYS, HIGH_RISK, LOW_RISK, MIN_HISTORY, MODEL_PATH

FENCE = "`" * 3
OUT = Path(__file__).resolve().parents[2] / "docs" / "ml.md"


def pct(value):
    return "n/a" if value is None else f"{value:.1%}"


def main() -> None:
    model = json.loads(MODEL_PATH.read_text())
    m = model["metrics"]
    bands = m["risk_bands"]
    rates = [
        bands[k]["actual_late_rate"]
        for k in ("low", "medium", "high")
        if bands[k]["actual_late_rate"] is not None
    ]
    rises = len(rates) == 3 and all(a <= b for a, b in zip(rates, rates[1:], strict=False))
    beats = m["roc_auc"] > m["baseline_last_late_roc_auc"]

    auc_line = (
        f"The model's ROC AUC ({m['roc_auc']}) is "
        f"{'higher than' if beats else 'not higher than'} the simple rule "
        f"'late again if the last charge was late' ({m['baseline_last_late_roc_auc']})."
    )
    band_line = (
        "The share of charges that were actually late rises from the low band to the "
        "medium band to the high band, which is what a useful ranking should show."
        if rises
        else "The share of charges that were actually late does not rise steadily across "
        "the bands, so the band labels should not be trusted."
    )

    coef_rows = sorted(zip(model["features"], model["coef"], strict=True), key=lambda r: -abs(r[1]))
    lines = [
        "# Late-payment risk (prototype)",
        "",
        "The landlord dashboard lists upcoming rent charges with an estimated chance of "
        "being paid late. This is a small machine-learning prototype. **It is trained on "
        "synthetic data, not on real tenants,** and it is indicative only.",
        "",
        "## What it predicts",
        "",
        f"Whether a rent charge will be completed more than {GRACE_DAYS} days after its "
        f"due date. Charges with fewer than {MIN_HISTORY} earlier charges on the same "
        "lease are not scored, because there is too little history.",
        "",
        "The features use only earlier charges on the same lease: the share paid late, "
        "the share late among the last three, whether the last one was late, the average "
        "days late over the last three, the share paid in parts, the rent, and whether the "
        "due month is December. No personal characteristics are used.",
        "",
        "## Why the data is synthetic",
        "",
        "The demo database is generated from a few fixed payment profiles, so a model "
        "trained on it would only learn rules written into the seed script. Instead, "
        "`backend/scripts/train_risk_model.py` simulates 800 tenants over 24 months, each "
        "with a hidden reliability trait, a rent effect, a December effect and streaks of "
        "hardship. The simulation contains the same kinds of effects the features measure, "
        "so good scores here show that the pipeline works. They do not show that real "
        "tenants behave this way.",
        "",
        "## How it was evaluated",
        "",
        "The model trains on months 1 to 16 and is tested on months 17 to 24, without "
        "shuffling, so it never sees the future. "
        f"The test set has {m['test_charges']} charges, and "
        f"{pct(m['late_rate_in_test'])} of them were paid late.",
        "",
        "| Measure | Model | Baseline: late again if last charge was late |",
        "|---|---|---|",
        f"| ROC AUC | {m['roc_auc']} | {m['baseline_last_late_roc_auc']} |",
        f"| Precision | {m['precision_at_0.5']} (threshold {HIGH_RISK}) "
        f"| {m['baseline_last_late_precision']} |",
        f"| Recall | {m['recall_at_0.5']} (threshold {HIGH_RISK}) "
        f"| {m['baseline_last_late_recall']} |",
        "",
        f"A rule of 'never late' would be right {pct(m['baseline_never_late_accuracy'])} "
        "of the time and would find no late payments at all, so accuracy is not used.",
        "",
        auc_line,
        "",
        f"Risk bands: low is under {LOW_RISK}, medium is under {HIGH_RISK}, high is "
        f"{HIGH_RISK} or more.",
        "",
        "| Band | Charges in test set | Share actually late |",
        "|---|---|---|",
        f"| Low | {bands['low']['charges']} | {pct(bands['low']['actual_late_rate'])} |",
        f"| Medium | {bands['medium']['charges']} | {pct(bands['medium']['actual_late_rate'])} |",
        f"| High | {bands['high']['charges']} | {pct(bands['high']['actual_late_rate'])} |",
        "",
        band_line,
        "",
        "Standardised coefficients (positive means more likely to be late):",
        "",
        "| Feature | Coefficient |",
        "|---|---|",
        *[f"| {name} | {coef:+.3f} |" for name, coef in coef_rows],
        "",
        "## Limits",
        "",
        "- It is trained on synthetic data. Real payment behaviour would need real data and "
        "new evaluation.",
        "- It is a score about people. It should start a conversation, never decide anything "
        "on its own, and a real deployment would need fairness checks and a legal review.",
        "- The model is a logistic regression saved as plain numbers in "
        "`backend/app/risk_model.json`. The API scores charges in pure Python, so the "
        "deployed app does not install any machine-learning libraries.",
        "",
        "## Retrain",
        "",
        f"{FENCE}powershell",
        "pip install -r requirements-ml.txt",
        "python -m scripts.train_risk_model",
        "python -m scripts.write_ml_docs",
        FENCE,
        "",
        "Restart the API after retraining, because it loads the model once.",
        "",
    ]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(auc_line)
    print(band_line)
    print("bands:", {k: v["actual_late_rate"] for k, v in bands.items()})


if __name__ == "__main__":
    main()
