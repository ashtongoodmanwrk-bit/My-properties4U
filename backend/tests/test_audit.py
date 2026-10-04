import pytest

from app.database import SessionLocal
from app.models import User
from app.security import hash_password


@pytest.fixture
def admin(client):
    with SessionLocal() as db:
        db.add(
            User(
                email="admin@example.com",
                password_hash=hash_password("Password123!"),
                full_name="Admin",
                role="admin",
            )
        )
        db.commit()
    r = client.post(
        "/auth/login",
        data={"username": "admin@example.com", "password": "Password123!"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def entries(client, admin, entity):
    r = client.get(f"/audit?entity={entity}", headers=admin)
    assert r.status_code == 200, r.text
    return r.json()


def test_only_admins_can_read_the_audit_log(client, lease_setup):
    assert client.get("/audit", headers=lease_setup["landlord"]).status_code == 403
    assert client.get("/audit", headers=lease_setup["tenant"]).status_code == 403
    assert client.get("/audit").status_code == 401


def test_lease_creation_is_logged(client, lease_setup, admin):
    data = entries(client, admin, "lease")
    assert data["total"] == 1
    entry = data["items"][0]
    assert entry["action"] == "create"
    assert entry["new_values"]["unit_id"] == lease_setup["unit"]["id"]
    assert entry["new_values"]["charges_generated"] == 12


def test_rejected_lease_writes_no_audit_entry(client, lease_setup, admin):
    body = {
        "unit_id": lease_setup["unit"]["id"],
        "tenant_email": "tenant@example.com",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "due_day": 1,
    }
    r = client.post("/leases", headers=lease_setup["landlord"], json=body)
    assert r.status_code == 409
    assert entries(client, admin, "lease")["total"] == 1


def test_payment_is_logged_once_even_if_replayed(client, lease_setup, admin):
    cid = lease_setup["charges"][0]["id"]
    for _ in range(2):
        r = client.post(
            "/payments",
            headers={**lease_setup["tenant"], "Idempotency-Key": "audit-key-0001"},
            json={"rent_charge_id": cid, "amount": "400.00", "method": "card"},
        )
        assert r.status_code in (200, 201)
    data = entries(client, admin, "payment")
    assert data["total"] == 1
    assert data["items"][0]["new_values"]["amount"] == "400.00"
    assert data["items"][0]["new_values"]["charge_status"] == "partial"


def test_maintenance_changes_record_old_and_new_values(client, lease_setup, admin):
    r = client.post(
        "/maintenance",
        headers=lease_setup["tenant"],
        json={
            "title": "Broken heater",
            "description": "No heat in the bedroom.",
            "category": "heating",
            "priority": "high",
        },
    )
    rid = r.json()["id"]
    r = client.patch(
        f"/maintenance/{rid}",
        headers=lease_setup["landlord"],
        json={"status": "assigned", "assigned_to": "Bob"},
    )
    assert r.status_code == 200

    data = entries(client, admin, "maintenance_request")
    assert data["total"] == 2
    change = next(e for e in data["items"] if e["action"] == "status_change")
    assert change["old_values"] == {"status": "submitted"}
    assert change["new_values"] == {"status": "assigned", "assigned_to": "Bob"}
