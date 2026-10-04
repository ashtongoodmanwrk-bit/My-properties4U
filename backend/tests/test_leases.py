LEASE_BODY = {
    "tenant_email": "tenant@example.com",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "due_day": 1,
}


def test_lease_generates_twelve_pending_charges(lease_setup):
    charges = lease_setup["charges"]
    assert len(charges) == 12
    assert all(c["status"] == "pending" for c in charges)
    assert all(c["amount"] == "950.00" for c in charges)
    assert charges[0]["due_date"] == "2026-01-01"
    assert charges[-1]["due_date"] == "2026-12-01"


def test_overlapping_lease_is_rejected(client, lease_setup):
    body = {**LEASE_BODY, "unit_id": lease_setup["unit"]["id"]}
    r = client.post("/leases", headers=lease_setup["landlord"], json=body)
    assert r.status_code == 409


def test_back_to_back_lease_is_allowed(client, lease_setup):
    body = {
        **LEASE_BODY,
        "unit_id": lease_setup["unit"]["id"],
        "start_date": "2027-01-01",
        "end_date": "2027-12-31",
    }
    r = client.post("/leases", headers=lease_setup["landlord"], json=body)
    assert r.status_code == 201


def test_tenant_cannot_create_lease(client, lease_setup):
    body = {**LEASE_BODY, "unit_id": lease_setup["unit"]["id"]}
    r = client.post("/leases", headers=lease_setup["tenant"], json=body)
    assert r.status_code == 403


def test_other_landlord_cannot_see_lease(client, lease_setup, make_user):
    other = make_user("other@example.com", "landlord")
    lid = lease_setup["lease"]["id"]
    assert client.get(f"/leases/{lid}", headers=other).status_code == 404
    assert client.get("/leases", headers=other).json()["total"] == 0


def test_tenant_sees_only_their_lease(client, lease_setup, make_user):
    other_tenant = make_user("t2@example.com", "tenant")
    assert client.get("/leases", headers=other_tenant).json()["total"] == 0
    assert client.get("/leases", headers=lease_setup["tenant"]).json()["total"] == 1
