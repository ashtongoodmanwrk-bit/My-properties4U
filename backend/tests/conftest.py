import os

# Must be set before the app is imported, so every connection uses the test database.
os.environ["DATABASE_URL"] = "postgresql+psycopg://app:app@localhost:5432/property_mgmt_test"

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def database():
    assert engine.url.database.endswith("_test"), "Refusing to run on a non-test database"
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE payments, rent_charges, leases, units, properties, users "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_user(client):
    def _make(email, role, password="Password123!"):
        r = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Test User",
                "role": role,
            },
        )
        assert r.status_code == 201, r.text
        r = client.post("/auth/login", data={"username": email, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _make


@pytest.fixture
def lease_setup(client, make_user):
    """A landlord, a tenant, a property, a unit and a 12-month lease."""
    landlord = make_user("landlord@example.com", "landlord")
    tenant = make_user("tenant@example.com", "tenant")
    prop = client.post(
        "/properties",
        headers=landlord,
        json={
            "name": "Oak Court",
            "address_line": "12 Oak Street",
            "city": "Bournemouth",
            "postcode": "BH1 1AA",
        },
    ).json()
    unit = client.post(
        f"/properties/{prop['id']}/units",
        headers=landlord,
        json={"unit_number": "1A", "bedrooms": 2, "monthly_rent": "950.00"},
    ).json()
    r = client.post(
        "/leases",
        headers=landlord,
        json={
            "unit_id": unit["id"],
            "tenant_email": "tenant@example.com",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "due_day": 1,
        },
    )
    assert r.status_code == 201, r.text
    lease = r.json()
    charges = client.get(f"/leases/{lease['id']}/charges", headers=tenant).json()["items"]
    return {
        "landlord": landlord,
        "tenant": tenant,
        "property": prop,
        "unit": unit,
        "lease": lease,
        "charges": charges,
    }
