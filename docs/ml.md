# Late-payment risk (prototype)

The landlord dashboard lists upcoming rent charges with an estimated chance of being paid late. This is a small machine-learning prototype. **It is trained on synthetic data, not on real tenants,** and it is indicative only.

## What it predicts

Whether a rent charge will be completed more than 3 days after its due date. Charges with fewer than 3 earlier charges on the same lease are not scored, because there is too little history.

The features use only earlier charges on the same lease: the share paid late, the share late among the last three, whether the last one was late, the average days late over the last three, the share paid in parts, the rent, and whether the due month is December. No personal characteristics are used.

## Why the data is synthetic

The demo database is generated from a few fixed payment profiles, so a model trained on it would only learn rules written into the seed script. Instead, `backend/scripts/train_risk_model.py` simulates 800 tenants over 24 months, each with a hidden reliability trait, a rent effect, a December effect and streaks of hardship. The simulation contains the same kinds of effects the features measure, so good scores here show that the pipeline works. They do not show that real tenants behave this way.

## How it was evaluated

The model trains on months 1 to 16 and is tested on months 17 to 24, without shuffling, so it never sees the future. The test set has 6400 charges, and 29.2% of them were paid late.

| Measure | Model | Baseline: late again if last charge was late |
|---|---|---|
| ROC AUC | 0.72 | 0.611 |
| Precision | 0.644 (threshold 0.5) | 0.454 |
| Recall | 0.232 (threshold 0.5) | 0.441 |

A rule of 'never late' would be right 70.8% of the time and would find no late payments at all, so accuracy is not used.

The model's ROC AUC (0.72) is higher than the simple rule 'late again if the last charge was late' (0.611).

Risk bands: low is under 0.2, medium is under 0.5, high is 0.5 or more.

| Band | Charges in test set | Share actually late |
|---|---|---|
| Low | 2020 | 13.4% |
| Medium | 3708 | 31.4% |
| High | 672 | 64.4% |

The share of charges that were actually late rises from the low band to the medium band to the high band, which is what a useful ranking should show.

Standardised coefficients (positive means more likely to be late):

| Feature | Coefficient |
|---|---|
| late_rate | +0.546 |
| rent_k | +0.144 |
| is_december | +0.142 |
| mean_days_late_last3 | +0.129 |
| last_late | +0.084 |
| partial_rate | -0.005 |
| n_prev | +0.004 |
| late_rate_last3 | -0.003 |

## Limits

- It is trained on synthetic data. Real payment behaviour would need real data and new evaluation.
- It is a score about people. It should start a conversation, never decide anything on its own, and a real deployment would need fairness checks and a legal review.
- The model is a logistic regression saved as plain numbers in `backend/app/risk_model.json`. The API scores charges in pure Python, so the deployed app does not install any machine-learning libraries.

## Retrain

```powershell
pip install -r requirements-ml.txt
python -m scripts.train_risk_model
python -m scripts.write_ml_docs
```

Restart the API after retraining, because it loads the model once.
