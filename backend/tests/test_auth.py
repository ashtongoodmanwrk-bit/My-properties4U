def test_register_duplicate_email_conflicts(client, make_user):
    make_user("a@example.com", "landlord")
    r = client.post(
        "/auth/register",
        json={
            "email": "a@example.com",
            "password": "Password123!",
            "full_name": "Again",
            "role": "landlord",
        },
    )
    assert r.status_code == 409


def test_cannot_register_as_admin(client):
    r = client.post(
        "/auth/register",
        json={
            "email": "evil@example.com",
            "password": "Password123!",
            "full_name": "Evil",
            "role": "admin",
        },
    )
    assert r.status_code == 422


def test_me_requires_a_token(client):
    assert client.get("/auth/me").status_code == 401


def test_wrong_password_is_rejected(client, make_user):
    make_user("a@example.com", "landlord")
    r = client.post(
        "/auth/login", data={"username": "a@example.com", "password": "WrongPass999"}
    )
    assert r.status_code == 401
