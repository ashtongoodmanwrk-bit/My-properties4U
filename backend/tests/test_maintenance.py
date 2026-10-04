import threading
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import app

REQUEST = {
    "title": "Leaking kitchen tap",
    "description": "The cold tap drips constantly.",
    "category": "plumbing",
    "priority": "high",
}


def report(client, setup):
    r = client.post("/maintenance", headers=setup["tenant"], json=REQUEST)
    assert r.status_code == 201, r.text
    return r.json()


def move(client, setup, request_id, new_status, assigned_to=None):
    body = {"status": new_status}
    if assigned_to:
        body["assigned_to"] = assigned_to
    return client.patch(
        f"/maintenance/{request_id}", headers=setup["landlord"], json=body
    )


def test_tenant_reports_issue_on_their_own_unit(client, lease_setup):
    req = report(client, lease_setup)
    assert req["status"] == "submitted"
    assert req["unit_id"] == lease_setup["unit"]["id"]
    assert req["assigned_to"] is None


def test_landlord_cannot_report_issues(client, lease_setup):
    r = client.post("/maintenance", headers=lease_setup["landlord"], json=REQUEST)
    assert r.status_code == 403


def test_tenant_without_lease_cannot_report(client, lease_setup, make_user):
    stranger = make_user("t2@example.com", "tenant")
    assert client.post("/maintenance", headers=stranger, json=REQUEST).status_code == 403


def test_assigning_requires_a_contractor_name(client, lease_setup):
    req = report(client, lease_setup)
    assert move(client, lease_setup, req["id"], "assigned").status_code == 422


def test_full_workflow(client, lease_setup):
    req = report(client, lease_setup)
    rid = req["id"]
    r = move(client, lease_setup, rid, "assigned", "Bob the Plumber")
    assert r.status_code == 200 and r.json()["assigned_to"] == "Bob the Plumber"
    assert move(client, lease_setup, rid, "in_progress").json()["status"] == "in_progress"
    done = move(client, lease_setup, rid, "resolved").json()
    assert done["status"] == "resolved"
    assert done["resolved_at"] is not None


def test_cannot_skip_a_step(client, lease_setup):
    rid = report(client, lease_setup)["id"]
    assert move(client, lease_setup, rid, "in_progress").status_code == 409
    assert move(client, lease_setup, rid, "resolved").status_code == 409


def test_cannot_move_backwards_from_resolved(client, lease_setup):
    rid = report(client, lease_setup)["id"]
    move(client, lease_setup, rid, "assigned", "Bob")
    move(client, lease_setup, rid, "in_progress")
    move(client, lease_setup, rid, "resolved")
    assert move(client, lease_setup, rid, "in_progress").status_code == 409


def test_tenant_cannot_change_status(client, lease_setup):
    rid = report(client, lease_setup)["id"]
    r = client.patch(
        f"/maintenance/{rid}",
        headers=lease_setup["tenant"],
        json={"status": "assigned", "assigned_to": "Me"},
    )
    assert r.status_code == 403


def test_other_landlord_cannot_see_or_change_request(client, lease_setup, make_user):
    rid = report(client, lease_setup)["id"]
    other = make_user("other@example.com", "landlord")
    assert client.get(f"/maintenance/{rid}", headers=other).status_code == 404
    assert client.get("/maintenance", headers=other).json()["total"] == 0
    r = client.patch(
        f"/maintenance/{rid}", headers=other, json={"status": "assigned", "assigned_to": "X"}
    )
    assert r.status_code == 404


def test_tenants_only_see_their_own_requests(client, lease_setup, make_user):
    report(client, lease_setup)
    other = make_user("t2@example.com", "tenant")
    assert client.get("/maintenance", headers=other).json()["total"] == 0
    assert client.get("/maintenance", headers=lease_setup["tenant"]).json()["total"] == 1


def test_filter_by_status(client, lease_setup):
    first = report(client, lease_setup)["id"]
    report(client, lease_setup)
    move(client, lease_setup, first, "assigned", "Bob")
    landlord = lease_setup["landlord"]
    assert client.get("/maintenance?status=submitted", headers=landlord).json()["total"] == 1
    assert client.get("/maintenance?status=assigned", headers=landlord).json()["total"] == 1


def test_concurrent_assignments_only_one_succeeds(client, lease_setup):
    rid = report(client, lease_setup)["id"]
    landlord = lease_setup["landlord"]
    barrier = threading.Barrier(2)

    def attempt(name):
        with TestClient(app) as c:
            barrier.wait()
            return c.patch(
                f"/maintenance/{rid}",
                headers=landlord,
                json={"status": "assigned", "assigned_to": name},
            ).status_code

    with ThreadPoolExecutor(2) as pool:
        codes = sorted(pool.map(attempt, ["Contractor A", "Contractor B"]))
    assert codes == [200, 409]
