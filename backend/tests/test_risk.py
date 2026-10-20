from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import update

from app.database import SessionLocal
from app.models_leases import RentCharge
from app.models_payments import Payment
from app.risk import PastCharge, band, can_score, features, probability

# Only "last charge was late" matters: late gives p = 0.88, on time gives p = 0.12.
FAKE_MODEL = {
    "mean": [0.0] * 8,
    "scale": [1.0] * 8,
    "coef": [0, 0, 0, 4, 0, 0, 0, 0],
    "intercept": -2.0,
}


@pytest.fixture(autouse=True)
def fake_model(monkeypatch):
    monkeypatch.setattr("app.routers.risk.get_model", lambda: FAKE_MODEL)


def tenant_id(client, setup):
    return client.get("/auth/me", headers=setup["tenant"]).json()["id"]


def record_payment(charge, user_id, paid_on):
    with SessionLocal() as db:
        db.add(
            Payment(
                rent_charge_id=charge["id"],
                user_id=user_id,
                amount=Decimal(charge["amount"]),
                method="card",
                idempotency_key=f"risk-test-{charge['id']}",
                paid_at=datetime.combine(paid_on, time(12, 0), tzinfo=UTC),
            )
        )
        db.execute(update(RentCharge).where(RentCharge.id == charge["id"]).values(status="paid"))
        db.commit()


def pay_first(setup, user_id, count, days_late):
    for charge in setup["charges"][:count]:
        due = date.fromisoformat(charge["due_date"])
        record_payment(charge, user_id, due + timedelta(days=days_late))


def get_risk(client, headers, as_of):
    return client.get("/risk", params={"as_of": as_of}, headers=headers)


def test_late_history_scores_high(client, lease_setup):
    pay_first(lease_setup, tenant_id(client, lease_setup), 3, days_late=10)
    r = get_risk(client, lease_setup["landlord"], "2026-04-01")
    assert r.status_code == 200
    items = r.json()["items"]
    assert [i["due_date"] for i in items] == ["2026-04-01", "2026-05-01"]
    assert all(i["band"] == "high" for i in items)
    assert items[0]["probability"] == pytest.approx(0.881, abs=0.002)
    assert "synthetic" in r.json()["note"]


def test_punctual_history_scores_low(client, lease_setup):
    pay_first(lease_setup, tenant_id(client, lease_setup), 3, days_late=0)
    items = get_risk(client, lease_setup["landlord"], "2026-04-01").json()["items"]
    assert items
    assert all(i["band"] == "low" for i in items)
    assert items[0]["probability"] == pytest.approx(0.119, abs=0.002)


def test_too_little_history_is_not_scored(client, lease_setup):
    items = get_risk(client, lease_setup["landlord"], "2026-02-01").json()["items"]
    assert len(items) == 2
    assert all(i["band"] == "unknown" and i["probability"] is None for i in items)


def test_paid_charges_are_not_listed(client, lease_setup):
    uid = tenant_id(client, lease_setup)
    pay_first(lease_setup, uid, 4, days_late=0)
    items = get_risk(client, lease_setup["landlord"], "2026-04-01").json()["items"]
    assert [i["due_date"] for i in items] == ["2026-05-01"]


def test_only_landlords_can_read_risk(client, lease_setup):
    assert get_risk(client, lease_setup["tenant"], "2026-04-01").status_code == 403
    assert client.get("/risk").status_code == 401


def test_other_landlord_sees_nothing(client, lease_setup, make_user):
    other = make_user("other-risk@example.com", "landlord")
    body = get_risk(client, other, "2026-04-01").json()
    assert body["items"] == []
    assert body["total"] == 0


def test_features_use_only_earlier_charges():
    history = [PastCharge(0, False), PastCharge(10, False), PastCharge(12, True)]
    x = features(history, rent=1000, due_month=12)
    assert x == pytest.approx([3, 2 / 3, 2 / 3, 1, 22 / 3, 1 / 3, 1.0, 1.0])


def test_features_need_enough_history():
    short = [PastCharge(0, False), PastCharge(1, False)]
    assert not can_score(short)
    with pytest.raises(ValueError):
        features(short, rent=900, due_month=3)


def test_probability_and_bands():
    assert probability(FAKE_MODEL, [0, 0, 0, 1, 0, 0, 0, 0]) == pytest.approx(0.8808, abs=1e-3)
    assert band(0.1) == "low"
    assert band(0.2) == "medium"
    assert band(0.49) == "medium"
    assert band(0.5) == "high"
