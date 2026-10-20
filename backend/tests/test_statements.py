import csv
import io

from app.routers.statements import safe_cell

MONTH = "2026-03"


def read_rows(response):
    text = response.content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def march_charge(setup):
    return next(c for c in setup["charges"] if c["due_date"] == "2026-03-01")


def test_tenant_downloads_own_statement(client, lease_setup):
    r = client.get("/statements", params={"month": MONTH}, headers=lease_setup["tenant"])
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert 'filename="statement-2026-03.csv"' in r.headers["content-disposition"]
    rows = read_rows(r)
    assert len(rows) == 1
    row = rows[0]
    assert row["Property"] == "Oak Court"
    assert row["Unit"] == "1A"
    assert row["Due date"] == "2026-03-01"
    assert row["Amount"] == "950.00"
    assert row["Paid"] == "0.00"
    assert row["Outstanding"] == "950.00"
    assert row["Status"] == "pending"


def test_landlord_sees_payments_and_tenant(client, lease_setup):
    charge = march_charge(lease_setup)
    r = client.post(
        "/payments",
        headers={**lease_setup["tenant"], "Idempotency-Key": "stmt-test-0001"},
        json={"rent_charge_id": charge["id"], "amount": "400.00", "method": "card"},
    )
    assert r.status_code == 201, r.text
    rows = read_rows(
        client.get("/statements", params={"month": MONTH}, headers=lease_setup["landlord"])
    )
    assert len(rows) == 1
    assert rows[0]["Tenant"] == "tenant@example.com"
    assert rows[0]["Paid"] == "400.00"
    assert rows[0]["Outstanding"] == "550.00"
    assert rows[0]["Status"] == "partial"


def test_other_users_get_no_rows(client, lease_setup, make_user):
    other_landlord = make_user("other-landlord@example.com", "landlord")
    other_tenant = make_user("other-tenant@example.com", "tenant")
    for headers in (other_landlord, other_tenant):
        r = client.get("/statements", params={"month": MONTH}, headers=headers)
        assert r.status_code == 200
        assert read_rows(r) == []


def test_month_without_charges_is_empty(client, lease_setup):
    r = client.get("/statements", params={"month": "2025-12"}, headers=lease_setup["tenant"])
    assert r.status_code == 200
    assert read_rows(r) == []


def test_statement_requires_login(client):
    assert client.get("/statements", params={"month": MONTH}).status_code == 401


def test_invalid_month_is_rejected(client, lease_setup):
    for bad in ("2026-13", "March", "2026-3"):
        r = client.get("/statements", params={"month": bad}, headers=lease_setup["tenant"])
        assert r.status_code == 422, bad


def test_formula_text_is_neutralised(client, lease_setup, make_user):
    make_user("t3@example.com", "tenant")
    landlord = lease_setup["landlord"]
    prop = client.post(
        "/properties",
        headers=landlord,
        json={
            "name": "=SUM(1+1)",
            "address_line": "1 Test Road",
            "city": "Poole",
            "postcode": "BH2 2BB",
        },
    ).json()
    unit = client.post(
        f"/properties/{prop['id']}/units",
        headers=landlord,
        json={"unit_number": "2B", "bedrooms": 1, "monthly_rent": "700.00"},
    ).json()
    r = client.post(
        "/leases",
        headers=landlord,
        json={
            "unit_id": unit["id"],
            "tenant_email": "t3@example.com",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "due_day": 1,
        },
    )
    assert r.status_code == 201, r.text
    rows = read_rows(client.get("/statements", params={"month": MONTH}, headers=landlord))
    assert len(rows) == 2
    row = next(x for x in rows if x["Tenant"] == "t3@example.com")
    assert row["Property"] == "'=SUM(1+1)"


def test_safe_cell_prefixes_formula_characters():
    assert safe_cell("=1+1") == "'=1+1"
    assert safe_cell("+44") == "'+44"
    assert safe_cell("-5") == "'-5"
    assert safe_cell("@home") == "'@home"
    assert safe_cell("Oak Court") == "Oak Court"
