import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import User
from app.models_leases import Lease, RentCharge

logger = logging.getLogger("jobs")


def mark_overdue(db: Session, today: date | None = None) -> int:
    """Flag unpaid charges whose due date has passed. Safe to run repeatedly.

    If a payment is in flight, the UPDATE waits for that row's lock, then
    re-checks the WHERE clause, so a charge that just became 'paid' is skipped.
    """
    today = today or date.today()
    result = db.execute(
        update(RentCharge)
        .where(
            RentCharge.status.in_(("pending", "partial")),
            RentCharge.due_date < today,
        )
        .values(status="overdue")
    )
    db.commit()
    return result.rowcount


def send_reminders(db: Session, today: date | None = None, days_ahead: int = 3) -> int:
    """Remind tenants about rent due within the next few days, once per charge.

    SKIP LOCKED lets two workers run side by side without double-sending.
    """
    today = today or date.today()
    rows = db.execute(
        select(RentCharge, User.email)
        .join(Lease, RentCharge.lease_id == Lease.id)
        .join(User, Lease.tenant_id == User.id)
        .where(
            RentCharge.status.in_(("pending", "partial")),
            RentCharge.due_date >= today,
            RentCharge.due_date <= today + timedelta(days=days_ahead),
            RentCharge.reminder_sent_at.is_(None),
        )
        .with_for_update(of=RentCharge, skip_locked=True)
    ).all()

    now = datetime.now(timezone.utc)
    for charge, email in rows:
        logger.info(
            "Reminder to %s: rent of %s is due on %s", email, charge.amount, charge.due_date
        )
        charge.reminder_sent_at = now
    db.commit()
    return len(rows)
