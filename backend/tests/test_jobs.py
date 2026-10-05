from datetime import date

from app.database import SessionLocal
from app.jobs import mark_overdue, send_reminders


def run(job, today):
    with SessionLocal() as db:
        return job(db, today=today)


def statuses(client, setup):
    items = client.get(f"/leases/{setup['lease']['id']}/charges", headers=setup["tenant"]).json()[
        "items"
    ]
    return [c["status"] for c in items]


def pay(client, setup, charge_id, amount, key):
    return client.post(
        "/payments",
        headers={**setup["tenant"], "Idempotency-Key": key},
        json={"rent_charge_id": charge_id, "amount": amount, "method": "card"},
    )


def test_past_due_unpaid_charges_become_overdue(client, lease_setup):
    assert run(mark_overdue, date(2026, 3, 15)) == 3  # Jan, Feb, Mar
    s = statuses(client, lease_setup)
    assert s[:3] == ["overdue"] * 3
    assert s[3:] == ["pending"] * 9


def test_overdue_job_is_idempotent(client, lease_setup):
    assert run(mark_overdue, date(2026, 3, 15)) == 3
    assert run(mark_overdue, date(2026, 3, 15)) == 0


def test_paid_charges_are_not_marked_overdue(client, lease_setup):
    first = lease_setup["charges"][0]["id"]
    assert pay(client, lease_setup, first, "950.00", "key-job-paid-1").status_code == 201
    assert run(mark_overdue, date(2026, 3, 15)) == 2
    assert statuses(client, lease_setup)[0] == "paid"


def test_partial_payment_keeps_charge_overdue_until_cleared(client, lease_setup):
    first = lease_setup["charges"][0]["id"]
    run(mark_overdue, date(2026, 3, 15))
    pay(client, lease_setup, first, "400.00", "key-job-part-1")
    assert statuses(client, lease_setup)[0] == "overdue"
    pay(client, lease_setup, first, "550.00", "key-job-part-2")
    assert statuses(client, lease_setup)[0] == "paid"


def test_reminders_sent_once_per_charge(client, lease_setup):
    # 29 March: only the 1 April charge is due within 3 days.
    assert run(send_reminders, date(2026, 3, 29)) == 1
    assert run(send_reminders, date(2026, 3, 29)) == 0


def test_no_reminder_for_paid_charge(client, lease_setup):
    april = lease_setup["charges"][3]["id"]
    assert pay(client, lease_setup, april, "950.00", "key-job-paid-2").status_code == 201
    assert run(send_reminders, date(2026, 3, 29)) == 0
