def test_tenant_cannot_list_properties(client, make_user):
    tenant = make_user("t@example.com", "tenant")
    assert client.get("/properties", headers=tenant).status_code == 403


def test_other_landlord_cannot_see_property(client, lease_setup, make_user):
    other = make_user("other@example.com", "landlord")
    pid = lease_setup["property"]["id"]
    assert client.get(f"/properties/{pid}", headers=other).status_code == 404
    assert client.get("/properties", headers=other).json()["total"] == 0


def test_duplicate_unit_number_conflicts(client, lease_setup):
    pid = lease_setup["property"]["id"]
    r = client.post(
        f"/properties/{pid}/units",
        headers=lease_setup["landlord"],
        json={"unit_number": "1A", "bedrooms": 1, "monthly_rent": "500.00"},
    )
    assert r.status_code == 409
