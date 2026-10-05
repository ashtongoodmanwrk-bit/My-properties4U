from decimal import Decimal

AS_OF = "2026-03-15"

REQUEST = {
    "title": "Leaking kitchen tap",
    "description": "The cold tap drips constantly.",
    "category": "plumbing",
    "priority": "high",
}


def summary(client, headers, **params):
    r = client.get("/dashboard/summary", headers=headers, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def pay(client, setup, charge_id, amount, key):
    r = client.post(
        "/payments",
        headers={**setup["tenant"], "Idempotency-Key": key},
        json={"rent_charge_id": charge_id, "amount": amount, "method": "card"},
    )
    assert r.status_code == 201, r.text


def test_dashboard_is_landlord_only(client, lease_setup):
    assert client.get("/dashboard/summary", headers=lease_setup["tenant"]).status_code == 403
    assert client.get("/dashboard/income", headers=lease_setup["tenant"]).status_code == 403
    assert client.get("/dashboard/summary").status_code == 401


def test_occupancy_rate(client, lease_setup):
    pid = lease_setup["property"]["id"]
    landlord = lease_setup["landlord"]
    r = client.post(
        f"/properties/{pid}/units",
        headers=landlord,
        json={"unit_number": "2B", "bedrooms": 1, "monthly_rent": "700.00"},
    )
    assert r.status_code == 201
    d = summary(client, landlord, as_of="2026-06-15")
    assert (d["total_units"], d["occupied_units"], d["occupancy_rate"]) == (2, 1, 50.0)
    d = summary(client, landlord, as_of="2027-06-15")
    assert d["occupied_units"] == 0 and d["occupancy_rate"] == 0.0


def test_expected_vs_collected_income(client, lease_setup):
    landlord = lease_setup["landlord"]
    d = summary(client, landlord, month="2026-03", as_of=AS_OF)
    assert Decimal(d["expected_income"]) == Decimal("950.00")
    assert Decimal(d["collected_income"]) == 0
    assert d["collection_rate"] == 0.0

    march = lease_setup["charges"][2]["id"]
    pay(client, lease_setup, march, "400.00", "dash-key-0001")
    d = summary(client, landlord, month="2026-03", as_of=AS_OF)
    assert Decimal(d["collected_income"]) == Decimal("400.00")
    assert d["collection_rate"] == 42.1


def test_overdue_amount_counts_unpaid_past_due_charges(client, lease_setup):
    march = lease_setup["charges"][2]["id"]
    pay(client, lease_setup, march, "400.00", "dash-key-0002")
    d = summary(client, lease_setup["landlord"], as_of=AS_OF)
    # Jan and Feb unpaid (950 each) plus 550 left on March.
    assert d["overdue_charges"] == 3
    assert Decimal(d["overdue_amount"]) == Decimal("2450.00")


def test_open_requests_by_status(client, lease_setup):
    landlord, tenant = lease_setup["landlord"], lease_setup["tenant"]
    first = client.post("/maintenance", headers=tenant, json=REQUEST).json()["id"]
    client.post("/maintenance", headers=tenant, json=REQUEST)
    client.patch(
        f"/maintenance/{first}",
        headers=landlord,
        json={"status": "assigned", "assigned_to": "Bob"},
    )
    d = summary(client, landlord, as_of=AS_OF)
    assert d["open_requests"] == {"submitted": 1, "assigned": 1, "in_progress": 0}
    assert d["open_requests_total"] == 2

    client.patch(f"/maintenance/{first}", headers=landlord, json={"status": "in_progress"})
    client.patch(f"/maintenance/{first}", headers=landlord, json={"status": "resolved"})
    d = summary(client, landlord, as_of=AS_OF)
    assert d["open_requests"] == {"submitted": 1, "assigned": 0, "in_progress": 0}
    assert d["open_requests_total"] == 1


def test_other_landlord_sees_an_empty_dashboard(client, lease_setup, make_user):
    other = make_user("other@example.com", "landlord")
    d = summary(client, other, as_of=AS_OF)
    assert d["total_units"] == 0
    assert d["occupancy_rate"] == 0.0
    assert Decimal(d["expected_income"]) == 0
    assert d["overdue_charges"] == 0
    assert d["open_requests_total"] == 0


def test_income_series_has_twelve_months(client, lease_setup):
    landlord = lease_setup["landlord"]
    march = lease_setup["charges"][2]["id"]
    pay(client, lease_setup, march, "400.00", "dash-key-0003")

    r = client.get("/dashboard/income", headers=landlord, params={"year": 2026})
    assert r.status_code == 200
    months = r.json()["months"]
    assert len(months) == 12
    assert all(Decimal(m["expected"]) == Decimal("950.00") for m in months)
    assert months[2]["month"] == "2026-03"
    assert Decimal(months[2]["collected"]) == Decimal("400.00")

    empty = client.get("/dashboard/income", headers=landlord, params={"year": 2025})
    assert all(Decimal(m["expected"]) == 0 for m in empty.json()["months"])
