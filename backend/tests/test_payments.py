import threading
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app


def pay(client, tenant, charge_id, amount, key):
    return client.post(
        "/payments",
        headers={**tenant, "Idempotency-Key": key},
        json={"rent_charge_id": charge_id, "amount": amount, "method": "card"},
    )


def charge_status(client, setup, charge_id):
    items = client.get(f"/leases/{setup['lease']['id']}/charges", headers=setup["tenant"]).json()[
        "items"
    ]
    return next(c["status"] for c in items if c["id"] == charge_id)


def test_partial_then_full_payment(client, lease_setup):
    cid = lease_setup["charges"][0]["id"]
    t = lease_setup["tenant"]
    assert pay(client, t, cid, "400.00", "key-partial-1").status_code == 201
    assert charge_status(client, lease_setup, cid) == "partial"
    assert pay(client, t, cid, "550.00", "key-partial-2").status_code == 201
    assert charge_status(client, lease_setup, cid) == "paid"


def test_same_idempotency_key_returns_original_payment(client, lease_setup):
    cid = lease_setup["charges"][0]["id"]
    t = lease_setup["tenant"]
    first = pay(client, t, cid, "400.00", "key-replay-1")
    again = pay(client, t, cid, "400.00", "key-replay-1")
    assert first.status_code == 201
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]
    assert client.get("/payments", headers=t).json()["total"] == 1


def test_idempotency_key_reused_for_different_payment_is_rejected(client, lease_setup):
    cid = lease_setup["charges"][0]["id"]
    t = lease_setup["tenant"]
    pay(client, t, cid, "400.00", "key-reuse-1")
    assert pay(client, t, cid, "500.00", "key-reuse-1").status_code == 422


def test_overpayment_is_rejected(client, lease_setup):
    cid = lease_setup["charges"][0]["id"]
    t = lease_setup["tenant"]
    pay(client, t, cid, "400.00", "key-over-1")
    assert pay(client, t, cid, "600.00", "key-over-2").status_code == 422


def test_paying_a_paid_charge_conflicts(client, lease_setup):
    cid = lease_setup["charges"][0]["id"]
    t = lease_setup["tenant"]
    assert pay(client, t, cid, "950.00", "key-full-1").status_code == 201
    assert pay(client, t, cid, "10.00", "key-full-2").status_code == 409


def test_landlord_cannot_pay(client, lease_setup):
    cid = lease_setup["charges"][0]["id"]
    r = pay(client, lease_setup["landlord"], cid, "100.00", "key-landlord-1")
    assert r.status_code == 403


def test_other_tenant_cannot_pay_this_charge(client, lease_setup, make_user):
    other = make_user("t2@example.com", "tenant")
    cid = lease_setup["charges"][0]["id"]
    assert pay(client, other, cid, "100.00", "key-other-001").status_code == 404


def test_concurrent_full_payments_only_one_succeeds(lease_setup):
    tenant = lease_setup["tenant"]
    cid = lease_setup["charges"][0]["id"]
    barrier = threading.Barrier(2)

    def attempt(key):
        with TestClient(app) as c:
            barrier.wait()  # both requests are released at the same moment
            return pay(c, tenant, cid, "950.00", key).status_code

    with ThreadPoolExecutor(2) as pool:
        codes = sorted(pool.map(attempt, ["race-key-aaaaaaaa", "race-key-bbbbbbbb"]))
    assert codes == [201, 409]
